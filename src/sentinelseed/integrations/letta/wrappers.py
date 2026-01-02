"""
Letta Client Wrappers for Sentinel THSP validation.

This module provides wrapper classes that intercept Letta client operations
and add THSP safety validation.

Classes:
    - SentinelLettaClient: Main wrapper for Letta client
    - SentinelAgentsAPI: Wrapper for agents.* operations
    - SentinelMessagesAPI: Wrapper for agents.messages.* operations

Functions:
    - create_safe_agent: Factory for creating agents with safety tools
"""

from typing import Any, Dict, List, Literal, Optional, Union
from dataclasses import dataclass, field
import logging

from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
    ValidationResult,
)

_logger = logging.getLogger("sentinelseed.integrations.letta")

# Type hints for Letta - actual import is deferred
Letta = Any
AsyncLetta = Any

# Valid configuration values
VALID_MODES = ("block", "flag", "log")
VALID_PROVIDERS = ("openai", "anthropic")
DEFAULT_HIGH_RISK_TOOLS = ["send_message", "run_code", "web_search"]


def _validate_mode(mode: str) -> None:
    """Validate mode is supported."""
    if mode not in VALID_MODES:
        raise ValueError(f"Invalid mode '{mode}'. Must be one of: {VALID_MODES}")


def _validate_provider(provider: str) -> None:
    """Validate provider is supported."""
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider '{provider}'. Must be one of: {VALID_PROVIDERS}")


def _sanitize_for_log(text: str, max_length: int = 50) -> str:
    """Sanitize text for logging to avoid exposing sensitive content."""
    if not text:
        return "<empty>"
    return f"[{len(text)} chars]"


@dataclass
class BlockedResponse:
    """Response returned when content is blocked by safety validation."""
    blocked: bool = True
    safety_validation: Dict = field(default_factory=dict)
    messages: List = field(default_factory=list)
    reason: str = ""


@dataclass
class SafetyConfig:
    """Configuration for Sentinel safety validation in Letta."""

    api_key: Optional[str] = None
    """API key for semantic validation (OpenAI or Anthropic)."""

    provider: str = "openai"
    """LLM provider for validation."""

    model: Optional[str] = None
    """Model to use for validation."""

    mode: Literal["block", "flag", "log"] = "block"
    """
    How to handle unsafe content:
    - block: Prevent execution and return error
    - flag: Allow but add safety metadata
    - log: Only log warnings, don't interfere
    """

    validate_input: bool = True
    """Validate user input messages."""

    validate_output: bool = True
    """Validate agent responses."""

    validate_tool_calls: bool = True
    """Validate tool execution requests."""

    memory_integrity: bool = False
    """Enable memory integrity checking with HMAC."""

    memory_secret: Optional[str] = None
    """Secret key for memory integrity HMAC."""

    high_risk_tools: List[str] = field(default_factory=lambda: [
        "send_message", "run_code", "web_search",
    ])
    """Tools that require extra validation."""


class SentinelMessagesAPI:
    """
    Wrapper for Letta agents.messages API with safety validation.

    Intercepts message creation and streaming to validate content
    before and after agent processing.
    """

    def __init__(
        self,
        messages_api: Any,
        agent_id: str,
        config: SafetyConfig,
        validator: Any,
    ):
        self._api = messages_api
        self._agent_id = agent_id
        self._config = config
        self._validator = validator

    def create(
        self,
        agent_id: Optional[str] = None,
        input: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Any:
        """
        Send message to agent with safety validation.

        Validates input before sending and output after receiving.
        """
        target_agent = agent_id or self._agent_id

        # Validate input
        if self._config.validate_input:
            content = input
            if not content and messages and isinstance(messages, (list, tuple)) and len(messages) > 0:
                first_msg = messages[0]
                if isinstance(first_msg, dict):
                    content = first_msg.get("content", "")
            if content:
                validation = self._validate_content(content, "input")
                is_safe = validation.get("is_safe")
                if is_safe is False:
                    if self._config.mode == "block":
                        return self._create_blocked_response(validation, "input")
                    elif self._config.mode == "log":
                        _logger.warning(f"Unsafe input detected: {_sanitize_for_log(content)}")
                elif is_safe is None and self._config.mode == "log":
                    _logger.warning("Input validation unavailable - proceeding with caution")

        # Execute original
        response = self._api.create(
            agent_id=target_agent,
            input=input,
            messages=messages,
            **kwargs,
        )

        # Handle None response
        if response is None:
            _logger.warning("API returned None response")
            return response

        # Validate output
        if self._config.validate_output:
            response_messages = getattr(response, "messages", None)
            if response_messages and isinstance(response_messages, (list, tuple)):
                for msg in response_messages:
                    msg_content = getattr(msg, "content", None)
                    if msg_content:
                        validation = self._validate_content(str(msg_content), "output")
                        is_safe = validation.get("is_safe")
                        if is_safe is False:
                            if self._config.mode == "block":
                                return self._create_blocked_response(validation, "output")
                            elif self._config.mode == "flag":
                                try:
                                    msg.safety_validation = validation
                                except AttributeError:
                                    pass  # Can't set attribute on some objects
                            elif self._config.mode == "log":
                                _logger.warning(f"Unsafe output detected: {_sanitize_for_log(str(msg_content))}")

        return response

    def stream(
        self,
        agent_id: Optional[str] = None,
        messages: Optional[List[Dict]] = None,
        **kwargs,
    ):
        """
        Stream messages with safety validation.

        Note: Output validation is not possible during streaming.
        Consider using create() for full input/output validation.
        """
        target_agent = agent_id or self._agent_id

        # Validate input
        if self._config.validate_input and messages and isinstance(messages, (list, tuple)):
            for msg in messages:
                if isinstance(msg, dict):
                    content = msg.get("content", "")
                    if content:
                        validation = self._validate_content(content, "input")
                        is_safe = validation.get("is_safe")
                        if is_safe is False and self._config.mode == "block":
                            raise SafetyBlockedError(
                                message=f"Input blocked by Sentinel: {validation.get('reasoning', 'Safety violation')}",
                                validation_result=validation,
                                context="input",
                            )
                        elif is_safe is None and self._config.mode == "log":
                            _logger.warning("Stream input validation unavailable - proceeding with caution")

        # Stream original (output validation not possible during stream)
        return self._api.stream(
            agent_id=target_agent,
            messages=messages,
            **kwargs,
        )

    def _validate_content(self, content: str, context: str) -> Dict[str, Any]:
        """Validate content using configured validator (LayeredValidator)."""
        if self._validator is None:
            return {"is_safe": None, "method": "none", "reasoning": "No validator available"}

        try:
            result = self._validator.validate(content)

            # Handle ValidationResult from LayeredValidator
            if hasattr(result, "is_safe"):
                return {
                    "is_safe": result.is_safe,
                    "gates": {},  # Gate details in violations
                    "reasoning": result.violations[0] if result.violations else "Validation passed",
                    "failed_gates": result.violations or [],
                    "method": result.layer.value if hasattr(result, "layer") and result.layer else "layered",
                    "context": context,
                    "risk_level": result.risk_level.value if hasattr(result, "risk_level") and result.risk_level else "unknown",
                }
            elif isinstance(result, dict):
                # Backwards compatibility for dict results
                return {
                    "is_safe": result.get("safe", result.get("is_safe", True)),
                    "gates": result.get("gates", {}),
                    "reasoning": result.get("reasoning", "Validation"),
                    "failed_gates": result.get("issues", result.get("violations", [])),
                    "method": result.get("method", "unknown"),
                    "context": context,
                }
        except (ValueError, TypeError, RuntimeError, AttributeError, KeyError) as e:
            _logger.warning(f"Validation error: {type(e).__name__}")
            return {
                "is_safe": None,
                "method": "error",
                "reasoning": "Validation error occurred",
                "context": context,
            }

        return {"is_safe": None, "method": "none", "reasoning": "Validation returned no result"}

    def _create_blocked_response(self, validation: Dict, context: str) -> BlockedResponse:
        """Create a blocked response object."""
        return BlockedResponse(
            blocked=True,
            safety_validation=validation,
            messages=[],
            reason=f"Blocked by Sentinel THSP validation ({context}): {validation.get('reasoning', 'Safety violation')}",
        )

    def __getattr__(self, name: str) -> Any:
        """Forward unknown attributes to underlying API."""
        return getattr(self._api, name)


class SentinelAgentsAPI:
    """
    Wrapper for Letta agents API with safety features.

    Provides access to wrapped messages API and tool management.
    """

    def __init__(
        self,
        agents_api: Any,
        config: SafetyConfig,
        validator: Any,
    ):
        self._api = agents_api
        self._config = config
        self._validator = validator
        self._message_apis: Dict[str, SentinelMessagesAPI] = {}

    def create(
        self,
        tools: Optional[List[str]] = None,
        tool_rules: Optional[List[Dict]] = None,
        **kwargs,
    ) -> Any:
        """
        Create agent with optional safety tool injection.

        If config.validate_tool_calls is True, adds sentinel_safety_check
        tool to the agent automatically.
        """
        tools = list(tools) if tools else []
        tool_rules = list(tool_rules) if tool_rules else []

        # Create agent
        agent = self._api.create(
            tools=tools,
            tool_rules=tool_rules,
            **kwargs,
        )

        # Configure approval for high-risk tools
        if self._config.validate_tool_calls and hasattr(self._api, "tools"):
            tools_api = getattr(self._api, "tools", None)
            if tools_api and hasattr(tools_api, "modify_approval"):
                for tool_name in self._config.high_risk_tools:
                    if tool_name in tools:
                        try:
                            tools_api.modify_approval(
                                agent_id=agent.id,
                                tool_name=tool_name,
                                requires_approval=True,
                            )
                        except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                            _logger.debug(f"Could not set approval for {tool_name}: {type(e).__name__}")

        return agent

    def messages(self, agent_id: str) -> SentinelMessagesAPI:
        """Get wrapped messages API for an agent."""
        if agent_id not in self._message_apis:
            base_messages = self._api.messages
            self._message_apis[agent_id] = SentinelMessagesAPI(
                base_messages,
                agent_id,
                self._config,
                self._validator,
            )
        return self._message_apis[agent_id]

    def __getattr__(self, name: str) -> Any:
        """Forward unknown attributes to underlying API."""
        return getattr(self._api, name)


class SentinelLettaClient(SentinelIntegration):
    """
    Wrapper for Letta client with Sentinel THSP safety validation.

    Intercepts client operations to add safety checks at multiple points:
    - Message input validation
    - Agent response validation
    - Tool call validation (via approval mechanism)
    - Memory integrity (optional)

    Inherits from SentinelIntegration for standardized validation via
    LayeredValidator.

    Args:
        client: Base Letta client instance
        api_key: API key for semantic validation (OpenAI or Anthropic)
        provider: LLM provider for validation
        model: Model to use for validation
        mode: How to handle unsafe content ("block", "flag", "log")
        validate_input: Validate user messages
        validate_output: Validate agent responses
        validate_tool_calls: Enable approval for high-risk tools
        memory_integrity: Enable memory integrity checking
        memory_secret: Secret for memory HMAC
        high_risk_tools: List of tools requiring extra validation
        validator: Optional LayeredValidator for dependency injection (testing)

    Example:
        from letta_client import Letta
        from sentinelseed.integrations.letta import SentinelLettaClient

        base = Letta(api_key="letta-key")
        client = SentinelLettaClient(
            base,
            api_key="openai-key",
            mode="block"
        )

        agent = client.agents.create(
            model="openai/gpt-4o-mini",
            memory_blocks=[...]
        )

        # Messages are automatically validated
        response = client.agents.messages(agent.id).create(
            input="Hello!"
        )
    """

    _integration_name = "letta"

    def __init__(
        self,
        client: Any,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "log"] = "block",
        validate_input: bool = True,
        validate_output: bool = True,
        validate_tool_calls: bool = True,
        memory_integrity: bool = False,
        memory_secret: Optional[str] = None,
        high_risk_tools: Optional[List[str]] = None,
        validator: Optional[LayeredValidator] = None,
    ):
        # Validate inputs
        if client is None:
            raise ValueError("client cannot be None")

        _validate_mode(mode)
        _validate_provider(provider)

        # Create LayeredValidator if not provided
        if validator is None:
            use_semantic = api_key is not None
            config = ValidationConfig(
                use_heuristic=True,
                use_semantic=use_semantic,
                semantic_api_key=api_key,
                semantic_provider=provider,
                semantic_model=model,
            )
            validator = LayeredValidator(config=config)

        # Initialize SentinelIntegration
        super().__init__(validator=validator)

        self._client = client

        # Build config
        self._config = SafetyConfig(
            api_key=api_key,
            provider=provider,
            model=model,
            mode=mode,
            validate_input=validate_input,
            validate_output=validate_output,
            validate_tool_calls=validate_tool_calls,
            memory_integrity=memory_integrity,
            memory_secret=memory_secret,
            high_risk_tools=high_risk_tools or DEFAULT_HIGH_RISK_TOOLS.copy(),
        )

        # Wrap agents API - pass self.validator instead of self._validator
        if not hasattr(client, 'agents'):
            raise ValueError("client must have an 'agents' attribute")

        self._agents = SentinelAgentsAPI(
            client.agents,
            self._config,
            self.validator,  # Use inherited validator property
        )

    @property
    def agents(self) -> SentinelAgentsAPI:
        """Get wrapped agents API."""
        return self._agents

    @property
    def config(self) -> SafetyConfig:
        """Get safety configuration."""
        return self._config

    def __getattr__(self, name: str) -> Any:
        """Forward unknown attributes to underlying client."""
        return getattr(self._client, name)


class SafetyBlockedError(Exception):
    """Exception raised when content is blocked by safety validation."""

    def __init__(
        self,
        message: str,
        validation_result: Optional[Dict[str, Any]] = None,
        context: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.validation_result = validation_result or {}
        self.context = context

    def __str__(self) -> str:
        if self.context:
            return f"{self.message} (context: {self.context})"
        return self.message


def create_safe_agent(
    client: Any,
    validator_api_key: Optional[str] = None,
    validator_provider: str = "openai",
    model: str = "openai/gpt-4o-mini",
    embedding: str = "openai/text-embedding-3-small",
    memory_blocks: Optional[List[Dict[str, str]]] = None,
    tools: Optional[List[str]] = None,
    include_safety_tool: bool = True,
    safety_tool_name: str = "sentinel_safety_check",
    high_risk_tools: Optional[List[str]] = None,
    **kwargs,
) -> Any:
    """
    Factory function to create a Letta agent with safety features.

    Creates an agent with:
    - Built-in sentinel_safety_check tool (optional)
    - Approval required for high-risk tools
    - Default safety-focused memory blocks

    Args:
        client: Letta client instance
        validator_api_key: API key for semantic validation
        validator_provider: Provider for validation ("openai" or "anthropic")
        model: Model for agent
        embedding: Embedding model
        memory_blocks: Custom memory blocks (defaults provided if None)
        tools: List of tool names to attach
        include_safety_tool: Whether to add sentinel_safety_check tool
        safety_tool_name: Name of the safety tool
        high_risk_tools: Tools requiring approval
        **kwargs: Additional args for agents.create()

    Returns:
        Created agent state

    Example:
        from letta_client import Letta
        from sentinelseed.integrations.letta import create_safe_agent

        client = Letta(api_key="...")
        agent = create_safe_agent(
            client,
            validator_api_key="sk-...",
            memory_blocks=[
                {"label": "human", "value": "User info"},
                {"label": "persona", "value": "I am a helpful assistant"},
            ]
        )
    """
    # Default memory blocks with safety context
    if memory_blocks is None:
        memory_blocks = [
            {
                "label": "human",
                "value": "The user interacting with this agent.",
            },
            {
                "label": "persona",
                "value": (
                    "I am a helpful AI assistant with built-in safety validation. "
                    "Before taking actions or providing information, I verify "
                    "that my responses pass the THSP safety protocol: Truth, "
                    "Harm, Scope, and Purpose gates."
                ),
            },
        ]

    # Build tools list
    tools = list(tools) if tools else []

    # Add safety tool if requested
    if include_safety_tool:
        try:
            from sentinelseed.integrations.letta.tools import create_sentinel_tool
            safety_tool = create_sentinel_tool(
                client,
                api_key=validator_api_key,
                provider=validator_provider,
            )
            if safety_tool.name not in tools:
                tools.append(safety_tool.name)
        except (ValueError, TypeError, AttributeError, RuntimeError, ImportError) as e:
            _logger.warning(f"Could not create safety tool: {type(e).__name__}")

    # Create agent
    agent = client.agents.create(
        model=model,
        embedding=embedding,
        memory_blocks=memory_blocks,
        tools=tools,
        **kwargs,
    )

    # Set approval for high-risk tools
    high_risk = high_risk_tools if high_risk_tools is not None else ["run_code", "web_search"]
    if hasattr(client, 'agents') and hasattr(client.agents, 'tools'):
        tools_api = getattr(client.agents, 'tools', None)
        if tools_api and hasattr(tools_api, 'modify_approval'):
            for tool_name in high_risk:
                if tool_name in tools:
                    try:
                        tools_api.modify_approval(
                            agent_id=agent.id,
                            tool_name=tool_name,
                            requires_approval=True,
                        )
                    except (ValueError, TypeError, AttributeError, RuntimeError) as e:
                        _logger.debug(f"Could not set approval for {tool_name}: {type(e).__name__}")

    return agent
