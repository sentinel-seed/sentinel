"""
OpenAI Agents SDK integration for Sentinel AI.

Provides guardrails and agent wrappers for the OpenAI Agents SDK
that implement THSP (Truth, Harm, Scope, Purpose) validation.

This follows the official OpenAI Agents SDK specification:
https://openai.github.io/openai-agents-python/

Requirements:
    pip install openai-agents sentinelseed

Usage:
    from sentinelseed.integrations.openai_agents import (
        create_sentinel_agent,
        sentinel_input_guardrail,
        sentinel_output_guardrail,
    )

    # Create agent with Sentinel protection
    agent = create_sentinel_agent(
        name="Safe Assistant",
        instructions="You help users with tasks",
        tools=[my_tool],
    )

    # Or add guardrails to existing agent
    from agents import Agent

    agent = Agent(
        name="My Agent",
        instructions="...",
        input_guardrails=[sentinel_input_guardrail()],
        output_guardrails=[sentinel_output_guardrail()],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    TypeVar,
    Union,
    TYPE_CHECKING,
)

# Sentinel imports
try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel

# Check for OpenAI Agents SDK availability
AGENTS_SDK_AVAILABLE = False
try:
    from agents import (
        Agent,
        Runner,
        InputGuardrail,
        OutputGuardrail,
        GuardrailFunctionOutput,
        ModelSettings,
    )
    from agents.exceptions import (
        InputGuardrailTripwireTriggered,
        OutputGuardrailTripwireTriggered,
    )

    AGENTS_SDK_AVAILABLE = True
except ImportError:
    Agent = None
    Runner = None
    InputGuardrail = None
    OutputGuardrail = None
    GuardrailFunctionOutput = None
    ModelSettings = None
    InputGuardrailTripwireTriggered = None
    OutputGuardrailTripwireTriggered = None

if TYPE_CHECKING:
    from agents import Agent as AgentType
    from agents.run_context import RunContextWrapper

__all__ = [
    # Core classes
    "SentinelGuardrailConfig",
    "SentinelValidationResult",
    # Guardrail factories
    "sentinel_input_guardrail",
    "sentinel_output_guardrail",
    # Agent creation
    "create_sentinel_agent",
    "inject_sentinel_instructions",
    # Exceptions
    "SentinelGuardrailTriggered",
    # Constants
    "AGENTS_SDK_AVAILABLE",
]


# Type variable for context
TContext = TypeVar("TContext")


class SentinelGuardrailTriggered(Exception):
    """
    Raised when Sentinel guardrail blocks an input or output.

    Attributes:
        gate: Which THSP gate was violated (truth, harm, scope, purpose)
        message: Human-readable explanation
        details: Full validation result
    """

    def __init__(
        self,
        gate: str,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ):
        self.gate = gate
        self.message = message
        self.details = details or {}
        super().__init__(f"[{gate.upper()}] {message}")


@dataclass
class SentinelGuardrailConfig:
    """
    Configuration for Sentinel guardrails.

    Attributes:
        seed_level: Sentinel seed level (minimal, standard, full)
        block_on_violation: Whether to trigger tripwire on violation
        log_violations: Whether to log violations to console
        include_reasoning: Whether to include THSP reasoning in output_info
        gates_to_check: Which gates to validate (default: all)
    """

    seed_level: str = "standard"
    block_on_violation: bool = True
    log_violations: bool = True
    include_reasoning: bool = True
    gates_to_check: List[str] = field(
        default_factory=lambda: ["truth", "harm", "scope", "purpose"]
    )

    def __post_init__(self):
        valid_levels = ("minimal", "standard", "full")
        if self.seed_level not in valid_levels:
            raise ValueError(
                f"seed_level must be one of {valid_levels}, got '{self.seed_level}'"
            )

        valid_gates = {"truth", "harm", "scope", "purpose"}
        for gate in self.gates_to_check:
            if gate.lower() not in valid_gates:
                raise ValueError(
                    f"Invalid gate '{gate}'. Valid gates: {valid_gates}"
                )


@dataclass
class SentinelValidationResult:
    """
    Result of Sentinel THSP validation.

    Attributes:
        is_safe: Whether content passed all gates
        violated_gate: Which gate was violated (if any)
        reasoning: Explanation of the validation result
        confidence: Confidence score (0.0-1.0)
        gates_passed: List of gates that passed
        gates_failed: List of gates that failed
    """

    is_safe: bool
    violated_gate: Optional[str] = None
    reasoning: str = ""
    confidence: float = 1.0
    gates_passed: List[str] = field(default_factory=list)
    gates_failed: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_safe": self.is_safe,
            "violated_gate": self.violated_gate,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
        }


def _validate_content(
    content: str,
    sentinel: Sentinel,
    config: SentinelGuardrailConfig,
) -> SentinelValidationResult:
    """
    Validate content against THSP gates.

    Args:
        content: Text to validate
        sentinel: Sentinel instance
        config: Guardrail configuration

    Returns:
        SentinelValidationResult with validation outcome
    """
    gates_passed = []
    gates_failed = []
    violated_gate = None
    reasoning = ""

    # Use Sentinel's validate method
    try:
        result = sentinel.validate_request(content)

        if result.get("should_proceed", True):
            # All gates passed
            gates_passed = config.gates_to_check.copy()
            return SentinelValidationResult(
                is_safe=True,
                gates_passed=gates_passed,
                gates_failed=[],
                reasoning="Content passed all THSP gates",
                confidence=1.0,
            )
        else:
            # Determine which gate failed
            concerns = result.get("concerns", [])
            reasoning = "; ".join(concerns) if concerns else "Validation failed"

            # Map concerns to gates
            concern_text = reasoning.lower()
            if "truth" in concern_text or "deception" in concern_text or "false" in concern_text:
                violated_gate = "truth"
            elif "harm" in concern_text or "dangerous" in concern_text or "unsafe" in concern_text:
                violated_gate = "harm"
            elif "scope" in concern_text or "boundary" in concern_text or "authority" in concern_text:
                violated_gate = "scope"
            elif "purpose" in concern_text or "benefit" in concern_text or "legitimate" in concern_text:
                violated_gate = "purpose"
            else:
                violated_gate = "harm"  # Default fallback

            # Determine which gates passed/failed
            for gate in config.gates_to_check:
                if gate == violated_gate:
                    gates_failed.append(gate)
                else:
                    gates_passed.append(gate)

            return SentinelValidationResult(
                is_safe=False,
                violated_gate=violated_gate,
                reasoning=reasoning,
                confidence=0.9,
                gates_passed=gates_passed,
                gates_failed=gates_failed,
            )

    except Exception as e:
        # On error, fail safe
        return SentinelValidationResult(
            is_safe=False,
            violated_gate="error",
            reasoning=f"Validation error: {str(e)}",
            confidence=0.5,
            gates_passed=[],
            gates_failed=["error"],
        )


def sentinel_input_guardrail(
    config: Optional[SentinelGuardrailConfig] = None,
    sentinel: Optional[Sentinel] = None,
    name: str = "sentinel_thsp_input",
    run_in_parallel: bool = False,
) -> "InputGuardrail":
    """
    Create a Sentinel input guardrail for OpenAI Agents SDK.

    Validates user input against THSP gates before agent processing.

    Args:
        config: Guardrail configuration
        sentinel: Sentinel instance (created if not provided)
        name: Name for tracing
        run_in_parallel: Whether to run parallel with agent (default: False for safety)

    Returns:
        InputGuardrail instance

    Example:
        from agents import Agent
        from sentinelseed.integrations.openai_agents import sentinel_input_guardrail

        agent = Agent(
            name="Safe Agent",
            instructions="You help users",
            input_guardrails=[sentinel_input_guardrail()],
        )
    """
    if not AGENTS_SDK_AVAILABLE:
        raise ImportError(
            "openai-agents package not installed. "
            "Install with: pip install openai-agents"
        )

    config = config or SentinelGuardrailConfig()
    sentinel = sentinel or Sentinel(seed_level=config.seed_level)

    async def guardrail_function(
        ctx: "RunContextWrapper",
        agent: "AgentType",
        input_data: Union[str, List[Any]],
    ) -> "GuardrailFunctionOutput":
        """Sentinel THSP input validation guardrail."""
        # Extract text from input
        if isinstance(input_data, str):
            text = input_data
        elif isinstance(input_data, list):
            # Handle list of message items
            text_parts = []
            for item in input_data:
                if hasattr(item, "content"):
                    text_parts.append(str(item.content))
                elif isinstance(item, dict) and "content" in item:
                    text_parts.append(str(item["content"]))
                elif isinstance(item, str):
                    text_parts.append(item)
            text = " ".join(text_parts)
        else:
            text = str(input_data)

        # Validate content
        result = _validate_content(text, sentinel, config)

        # Log if configured
        if config.log_violations and not result.is_safe:
            print(
                f"[SENTINEL] Input blocked - Gate: {result.violated_gate}, "
                f"Reason: {result.reasoning}"
            )

        # Build output info
        output_info = result.to_dict() if config.include_reasoning else None

        return GuardrailFunctionOutput(
            output_info=output_info,
            tripwire_triggered=config.block_on_violation and not result.is_safe,
        )

    return InputGuardrail(
        guardrail_function=guardrail_function,
        name=name,
        run_in_parallel=run_in_parallel,
    )


def sentinel_output_guardrail(
    config: Optional[SentinelGuardrailConfig] = None,
    sentinel: Optional[Sentinel] = None,
    name: str = "sentinel_thsp_output",
) -> "OutputGuardrail":
    """
    Create a Sentinel output guardrail for OpenAI Agents SDK.

    Validates agent output against THSP gates before returning to user.

    Args:
        config: Guardrail configuration
        sentinel: Sentinel instance (created if not provided)
        name: Name for tracing

    Returns:
        OutputGuardrail instance

    Example:
        from agents import Agent
        from sentinelseed.integrations.openai_agents import sentinel_output_guardrail

        agent = Agent(
            name="Safe Agent",
            instructions="You help users",
            output_guardrails=[sentinel_output_guardrail()],
        )
    """
    if not AGENTS_SDK_AVAILABLE:
        raise ImportError(
            "openai-agents package not installed. "
            "Install with: pip install openai-agents"
        )

    config = config or SentinelGuardrailConfig()
    sentinel = sentinel or Sentinel(seed_level=config.seed_level)

    async def guardrail_function(
        ctx: "RunContextWrapper",
        agent: "AgentType",
        output: Any,
    ) -> "GuardrailFunctionOutput":
        """Sentinel THSP output validation guardrail."""
        # Extract text from output
        if isinstance(output, str):
            text = output
        elif hasattr(output, "content"):
            text = str(output.content)
        elif hasattr(output, "text"):
            text = str(output.text)
        elif isinstance(output, dict):
            text = str(output.get("content", output.get("text", str(output))))
        else:
            text = str(output)

        # Validate content
        result = _validate_content(text, sentinel, config)

        # Log if configured
        if config.log_violations and not result.is_safe:
            print(
                f"[SENTINEL] Output blocked - Gate: {result.violated_gate}, "
                f"Reason: {result.reasoning}"
            )

        # Build output info
        output_info = result.to_dict() if config.include_reasoning else None

        return GuardrailFunctionOutput(
            output_info=output_info,
            tripwire_triggered=config.block_on_violation and not result.is_safe,
        )

    return OutputGuardrail(
        guardrail_function=guardrail_function,
        name=name,
    )


def inject_sentinel_instructions(
    instructions: Optional[str] = None,
    seed_level: str = "standard",
    sentinel: Optional[Sentinel] = None,
) -> str:
    """
    Inject Sentinel seed into agent instructions.

    Prepends the Sentinel alignment seed to the provided instructions.

    Args:
        instructions: Base agent instructions
        seed_level: Seed level to use (minimal, standard, full)
        sentinel: Sentinel instance (created if not provided)

    Returns:
        Instructions with Sentinel seed prepended

    Example:
        from agents import Agent
        from sentinelseed.integrations.openai_agents import inject_sentinel_instructions

        agent = Agent(
            name="Safe Agent",
            instructions=inject_sentinel_instructions("You help users with coding"),
        )
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)
    seed = sentinel.get_seed()

    if instructions:
        return f"{seed}\n\n---\n\n{instructions}"
    return seed


def create_sentinel_agent(
    name: str,
    instructions: Optional[str] = None,
    model: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    handoffs: Optional[List[Any]] = None,
    model_settings: Optional[Any] = None,
    seed_level: str = "standard",
    guardrail_config: Optional[SentinelGuardrailConfig] = None,
    inject_seed: bool = True,
    add_input_guardrail: bool = True,
    add_output_guardrail: bool = True,
    input_guardrail_parallel: bool = False,
    sentinel: Optional[Sentinel] = None,
    **kwargs,
) -> "Agent":
    """
    Create an OpenAI Agent with Sentinel protection.

    This is the recommended way to create Sentinel-protected agents.
    It combines seed injection with input/output guardrails.

    Args:
        name: Agent name
        instructions: Base agent instructions (seed prepended if inject_seed=True)
        model: Model to use (e.g., "gpt-4o")
        tools: List of tools for the agent
        handoffs: List of agents for handoff
        model_settings: Model configuration
        seed_level: Sentinel seed level
        guardrail_config: Guardrail configuration
        inject_seed: Whether to inject seed into instructions
        add_input_guardrail: Whether to add input guardrail
        add_output_guardrail: Whether to add output guardrail
        input_guardrail_parallel: Whether input guardrail runs in parallel
        sentinel: Sentinel instance (shared across guardrails)
        **kwargs: Additional Agent parameters

    Returns:
        Agent instance with Sentinel protection

    Example:
        from sentinelseed.integrations.openai_agents import create_sentinel_agent
        from agents import Runner

        agent = create_sentinel_agent(
            name="Code Helper",
            instructions="You help users write Python code",
            model="gpt-4o",
            seed_level="standard",
        )

        result = await Runner.run(agent, "Help me sort a list")
        print(result.final_output)
    """
    if not AGENTS_SDK_AVAILABLE:
        raise ImportError(
            "openai-agents package not installed. "
            "Install with: pip install openai-agents"
        )

    # Create shared Sentinel instance
    sentinel = sentinel or Sentinel(seed_level=seed_level)
    config = guardrail_config or SentinelGuardrailConfig(seed_level=seed_level)

    # Prepare instructions
    if inject_seed:
        final_instructions = inject_sentinel_instructions(
            instructions=instructions,
            sentinel=sentinel,
        )
    else:
        final_instructions = instructions

    # Build guardrails list
    input_guardrails = list(kwargs.pop("input_guardrails", []))
    output_guardrails = list(kwargs.pop("output_guardrails", []))

    if add_input_guardrail:
        input_guardrails.append(
            sentinel_input_guardrail(
                config=config,
                sentinel=sentinel,
                run_in_parallel=input_guardrail_parallel,
            )
        )

    if add_output_guardrail:
        output_guardrails.append(
            sentinel_output_guardrail(
                config=config,
                sentinel=sentinel,
            )
        )

    # Create agent
    return Agent(
        name=name,
        instructions=final_instructions,
        model=model,
        tools=tools or [],
        handoffs=handoffs or [],
        model_settings=model_settings,
        input_guardrails=input_guardrails,
        output_guardrails=output_guardrails,
        **kwargs,
    )


def create_sentinel_guardrails(
    config: Optional[SentinelGuardrailConfig] = None,
    seed_level: str = "standard",
    input_parallel: bool = False,
) -> tuple:
    """
    Create a pair of Sentinel guardrails for use with existing agents.

    Args:
        config: Guardrail configuration
        seed_level: Seed level if config not provided
        input_parallel: Whether input guardrail runs in parallel

    Returns:
        Tuple of (input_guardrail, output_guardrail)

    Example:
        from agents import Agent
        from sentinelseed.integrations.openai_agents import create_sentinel_guardrails

        input_guard, output_guard = create_sentinel_guardrails()

        agent = Agent(
            name="My Agent",
            instructions="...",
            input_guardrails=[input_guard],
            output_guardrails=[output_guard],
        )
    """
    if not AGENTS_SDK_AVAILABLE:
        raise ImportError(
            "openai-agents package not installed. "
            "Install with: pip install openai-agents"
        )

    config = config or SentinelGuardrailConfig(seed_level=seed_level)
    sentinel = Sentinel(seed_level=config.seed_level)

    input_guard = sentinel_input_guardrail(
        config=config,
        sentinel=sentinel,
        run_in_parallel=input_parallel,
    )

    output_guard = sentinel_output_guardrail(
        config=config,
        sentinel=sentinel,
    )

    return input_guard, output_guard
