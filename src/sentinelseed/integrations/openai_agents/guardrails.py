"""
Guardrail implementations for OpenAI Agents SDK.

Provides layered input and output guardrails using THSP validation:
1. Heuristic layer: Fast regex-based validation (580+ patterns, <10ms, free)
2. Semantic layer: LLM-based validation for nuanced cases (1-5s, ~$0.0005/call)

The heuristic layer runs first. If it blocks, the semantic layer is skipped
(unless skip_semantic_if_heuristic_blocks=False in config).
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime, timezone
from typing import Any, List, Optional, TYPE_CHECKING, Union

from sentinelseed.validation import LayeredValidator, ValidationConfig


class ValidationTimeoutError(Exception):
    """Raised when validation times out."""

    def __init__(self, timeout: float, operation: str = "validation"):
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout}s")

from .config import SentinelGuardrailConfig, THSP_GUARDRAIL_INSTRUCTIONS
from .models import (
    THSPValidationOutput,
    ValidationMetadata,
    ViolationRecord,
    get_violations_log,
    require_thsp_validation_output,
    get_reasoning_safe,
    truncate_reasoning,
    PydanticNotAvailableError,
)
from .sanitization import create_validation_prompt
from .utils import (
    extract_text_from_input,
    get_logger,
    require_agents_sdk,
    truncate_text,
)

if TYPE_CHECKING:
    from agents import Agent, InputGuardrail, OutputGuardrail, GuardrailFunctionOutput
    from agents.run_context import RunContextWrapper


# Check SDK availability at module level
AGENTS_SDK_AVAILABLE = False
try:
    from agents import (
        Agent,
        Runner,
        InputGuardrail,
        OutputGuardrail,
        GuardrailFunctionOutput,
    )

    AGENTS_SDK_AVAILABLE = True
except (ImportError, AttributeError):
    # AttributeError: SDK installed but with incompatible structure
    Agent = None
    Runner = None
    InputGuardrail = None
    OutputGuardrail = None
    GuardrailFunctionOutput = None


class ValidationParseError(Exception):
    """Raised when validation output cannot be parsed."""

    def __init__(self, details: str = ""):
        self.details = details
        super().__init__(f"Failed to parse validation output. {details}")


def _validate_result(validation: Any, output_type: type) -> "THSPValidationOutput":
    """
    Validate and ensure the result from final_output_as is usable.

    Args:
        validation: The result from final_output_as
        output_type: Expected output type class

    Returns:
        Valid THSPValidationOutput instance

    Raises:
        ValidationParseError: If validation is None or invalid
    """
    if validation is None:
        raise ValidationParseError("final_output_as returned None")

    # Check for required attributes
    required_attrs = ["is_safe", "truth_passes", "harm_passes", "scope_passes", "purpose_passes"]
    missing = [attr for attr in required_attrs if not hasattr(validation, attr)]
    if missing:
        raise ValidationParseError(f"Missing required attributes: {missing}")

    return validation


def _create_guardrail_agent(config: SentinelGuardrailConfig) -> "Agent":
    """
    Create the internal guardrail agent for THSP validation.

    This agent performs semantic analysis of content using an LLM.

    Raises:
        ImportError: If OpenAI Agents SDK is not installed
        PydanticNotAvailableError: If Pydantic is not available
    """
    require_agents_sdk()

    # Ensure THSPValidationOutput is available (requires Pydantic)
    output_type = require_thsp_validation_output()

    return Agent(
        name="Sentinel THSP Validator",
        instructions=THSP_GUARDRAIL_INSTRUCTIONS,
        model=config.guardrail_model,
        output_type=output_type,
    )


def _determine_tripwire(
    validation: "THSPValidationOutput",
    config: SentinelGuardrailConfig,
) -> bool:
    """
    Determine if tripwire should be triggered based on validation result.

    Logic:
    - If block_on_violation is False, never trigger tripwire
    - If require_all_gates is True, trigger if ANY gate fails (is_safe=False)
    - If require_all_gates is False, trigger only if harm gate fails

    Args:
        validation: The validation output from guardrail agent
        config: Guardrail configuration

    Returns:
        True if tripwire should trigger (block the request)
    """
    # If blocking is disabled, never trigger
    if not config.block_on_violation:
        return False

    # Determine which condition to check
    if config.require_all_gates:
        # All gates must pass - use the overall is_safe flag
        return not validation.is_safe
    else:
        # Only harm gate is required
        return not validation.harm_passes


def _log_violation(
    validation: "THSPValidationOutput",
    content: str,
    is_input: bool,
    config: SentinelGuardrailConfig,
    metadata: dict,
) -> None:
    """
    Log a validation violation with proper sanitization.

    Args:
        validation: The validation result
        content: Original content (will be hashed, not stored)
        is_input: True for input validation
        config: Configuration
        metadata: Sanitization metadata
    """
    logger = get_logger()

    # Create sanitized log message
    content_type = "Input" if is_input else "Output"
    gate = getattr(validation, "violated_gate", None) or "unknown"
    risk = getattr(validation, "risk_level", "unknown")

    # Safely extract and truncate reasoning
    reasoning = get_reasoning_safe(validation)
    reasoning_summary = truncate_reasoning(reasoning, max_length=100)

    logger.warning(
        f"{content_type} blocked - Gate: {gate}, Risk: {risk}, "
        f"Injection detected: {metadata.get('injection_detected', False)}"
    )

    # Record to violations log
    violations_log = get_violations_log(config.max_violations_log)
    record = ViolationRecord(
        timestamp=datetime.now(timezone.utc),
        gate_violated=getattr(validation, "violated_gate", None),
        risk_level=risk,
        reasoning_summary=reasoning_summary,
        content_hash=hashlib.sha256(content.encode()).hexdigest(),
        was_input=is_input,
        injection_detected=metadata.get("injection_detected", False),
    )
    violations_log.add(record)


def sentinel_input_guardrail(
    config: Optional[SentinelGuardrailConfig] = None,
    name: str = "sentinel_thsp_input",
    run_in_parallel: bool = False,
) -> "InputGuardrail":
    """
    Create a Sentinel input guardrail with semantic LLM validation.

    Uses a dedicated guardrail agent to perform THSP validation on user input.
    Input is sanitized to prevent prompt injection attacks.

    Args:
        config: Guardrail configuration
        name: Name for tracing
        run_in_parallel: Whether to run parallel with agent
                        (False recommended for safety - blocks before agent runs)

    Returns:
        InputGuardrail instance

    Raises:
        ImportError: If openai-agents package is not installed

    Example:
        from agents import Agent
        from sentinelseed.integrations.openai_agents import sentinel_input_guardrail

        agent = Agent(
            name="Safe Agent",
            instructions="You help users",
            input_guardrails=[sentinel_input_guardrail()],
        )
    """
    require_agents_sdk()

    config = config or SentinelGuardrailConfig()
    guardrail_agent = _create_guardrail_agent(config)
    logger = get_logger()

    # Get the output type for validation
    output_type = require_thsp_validation_output()

    # Create heuristic validator if enabled (shared across calls)
    heuristic_validator = None
    if config.use_heuristic:
        heuristic_config = ValidationConfig(
            use_heuristic=True,
            use_semantic=False,  # Semantic is handled by the guardrail agent
        )
        heuristic_validator = LayeredValidator(config=heuristic_config)

    async def guardrail_function(
        ctx: "RunContextWrapper",
        agent: "Agent",
        input_data: Union[str, List[Any]],
    ) -> "GuardrailFunctionOutput":
        """Layered THSP input validation with heuristic + semantic layers."""
        start_time = time.time()

        # Extract text from input (handles None/empty safely)
        text = extract_text_from_input(input_data)

        # Handle empty input - allow through but flag it
        if not text or not text.strip():
            logger.debug("Empty input received, allowing through")
            return GuardrailFunctionOutput(
                output_info={
                    "is_safe": True,
                    "gates": {"truth": True, "harm": True, "scope": True, "purpose": True},
                    "violated_gate": None,
                    "reasoning": "Empty input - no validation needed",
                    "risk_level": "low",
                    "injection_detected": False,
                    "was_truncated": False,
                    "validation_time_ms": (time.time() - start_time) * 1000,
                    "layer": "none",
                },
                tripwire_triggered=False,
            )

        # ============================================================
        # LAYER 1: Heuristic Validation (fast, free)
        # ============================================================
        if heuristic_validator is not None:
            heuristic_result = heuristic_validator.validate(text)
            heuristic_time = (time.time() - start_time) * 1000

            if not heuristic_result.is_safe:
                logger.debug(f"Input blocked by heuristic layer: {heuristic_result.violations}")

                # Map heuristic violations to THSP gates
                violated_gate = "scope"  # Default for jailbreak/injection patterns
                if any("harm" in v.lower() for v in heuristic_result.violations):
                    violated_gate = "harm"
                elif any("truth" in v.lower() or "decept" in v.lower() for v in heuristic_result.violations):
                    violated_gate = "truth"

                # Log violation if configured
                if config.log_violations:
                    violations_log = get_violations_log(config.max_violations_log)
                    record = ViolationRecord(
                        timestamp=datetime.now(timezone.utc),
                        gate_violated=violated_gate,
                        risk_level=heuristic_result.risk_level.value if hasattr(heuristic_result.risk_level, 'value') else str(heuristic_result.risk_level),
                        reasoning_summary=f"Heuristic: {heuristic_result.violations[0][:100]}" if heuristic_result.violations else "Heuristic block",
                        content_hash=hashlib.sha256(text.encode()).hexdigest(),
                        was_input=True,
                        injection_detected=any("jailbreak" in v.lower() or "injection" in v.lower() for v in heuristic_result.violations),
                    )
                    violations_log.add(record)

                # If skip_semantic_if_heuristic_blocks, return immediately
                if config.skip_semantic_if_heuristic_blocks:
                    return GuardrailFunctionOutput(
                        output_info={
                            "is_safe": False,
                            "gates": {
                                "truth": violated_gate != "truth",
                                "harm": violated_gate != "harm",
                                "scope": violated_gate != "scope",
                                "purpose": True,
                            },
                            "violated_gate": violated_gate,
                            "reasoning": f"Blocked by heuristic layer: {', '.join(heuristic_result.violations)}",
                            "risk_level": heuristic_result.risk_level.value if hasattr(heuristic_result.risk_level, 'value') else str(heuristic_result.risk_level),
                            "injection_detected": any("jailbreak" in v.lower() or "injection" in v.lower() for v in heuristic_result.violations),
                            "was_truncated": False,
                            "validation_time_ms": heuristic_time,
                            "layer": "heuristic",
                        },
                        tripwire_triggered=config.block_on_violation,
                    )
                # Otherwise, continue to semantic layer for confirmation

        # ============================================================
        # LAYER 2: Semantic Validation (LLM-based, precise)
        # ============================================================

        # Create sanitized validation prompt
        validation_prompt, metadata = create_validation_prompt(
            content=text,
            content_type="INPUT",
            max_length=config.max_input_size,
        )

        try:
            # Run validation with timeout
            try:
                result = await asyncio.wait_for(
                    Runner.run(
                        guardrail_agent,
                        validation_prompt,
                        context=ctx.context,
                    ),
                    timeout=config.validation_timeout,
                )
            except asyncio.TimeoutError:
                raise ValidationTimeoutError(
                    config.validation_timeout,
                    "input validation"
                )

            raw_validation = result.final_output_as(output_type)

            # Validate the result is usable
            validation = _validate_result(raw_validation, output_type)

            # If injection was detected, mark scope as failed
            if metadata.get("injection_detected") and validation.is_safe:
                # Override - injection attempts should fail scope gate
                original_reasoning = get_reasoning_safe(validation)
                logger.warning(
                    f"Injection attempt detected but validation passed. "
                    f"Overriding scope gate. Reason: {metadata.get('injection_reason')}"
                )
                validation = output_type(
                    is_safe=False,
                    truth_passes=validation.truth_passes,
                    harm_passes=validation.harm_passes,
                    scope_passes=False,  # Injection = scope violation
                    purpose_passes=validation.purpose_passes,
                    violated_gate="scope",
                    reasoning=f"Injection attempt detected: {metadata.get('injection_reason')}. {original_reasoning}",
                    risk_level="high",
                    injection_attempt_detected=True,
                )

            # Determine tripwire
            tripwire = _determine_tripwire(validation, config)

            # Log violation if configured
            if config.log_violations and not validation.is_safe:
                _log_violation(validation, text, is_input=True, config=config, metadata=metadata)

            validation_time = (time.time() - start_time) * 1000

            # Safely extract reasoning for output
            reasoning = get_reasoning_safe(validation)

            return GuardrailFunctionOutput(
                output_info={
                    "is_safe": validation.is_safe,
                    "gates": {
                        "truth": validation.truth_passes,
                        "harm": validation.harm_passes,
                        "scope": validation.scope_passes,
                        "purpose": validation.purpose_passes,
                    },
                    "violated_gate": validation.violated_gate,
                    "reasoning": reasoning,
                    "risk_level": getattr(validation, "risk_level", "unknown"),
                    "injection_detected": metadata.get("injection_detected", False),
                    "was_truncated": metadata.get("was_truncated", False),
                    "validation_time_ms": validation_time,
                    "layer": "semantic",
                },
                tripwire_triggered=tripwire,
            )

        except Exception as e:
            logger.error(f"Validation error: {type(e).__name__}: {str(e)[:100]}")

            # Fail-safe or fail-open based on config
            should_block = not config.fail_open

            return GuardrailFunctionOutput(
                output_info={
                    "is_safe": config.fail_open,
                    "error": f"{type(e).__name__}: {str(e)[:100]}",
                    "reasoning": "Validation failed - " + (
                        "blocking for safety" if should_block else "allowing (fail_open=True)"
                    ),
                    "layer": "error",
                },
                tripwire_triggered=should_block and config.block_on_violation,
            )

    return InputGuardrail(
        guardrail_function=guardrail_function,
        name=name,
        run_in_parallel=run_in_parallel,
    )


def sentinel_output_guardrail(
    config: Optional[SentinelGuardrailConfig] = None,
    name: str = "sentinel_thsp_output",
) -> "OutputGuardrail":
    """
    Create a Sentinel output guardrail with semantic LLM validation.

    Uses a dedicated guardrail agent to perform THSP validation on agent output.

    Args:
        config: Guardrail configuration
        name: Name for tracing

    Returns:
        OutputGuardrail instance

    Raises:
        ImportError: If openai-agents package is not installed

    Example:
        from agents import Agent
        from sentinelseed.integrations.openai_agents import sentinel_output_guardrail

        agent = Agent(
            name="Safe Agent",
            instructions="You help users",
            output_guardrails=[sentinel_output_guardrail()],
        )
    """
    require_agents_sdk()

    config = config or SentinelGuardrailConfig()
    guardrail_agent = _create_guardrail_agent(config)
    logger = get_logger()

    # Get the output type for validation
    output_type = require_thsp_validation_output()

    # Create heuristic validator if enabled (shared across calls)
    heuristic_validator = None
    if config.use_heuristic:
        heuristic_config = ValidationConfig(
            use_heuristic=True,
            use_semantic=False,  # Semantic is handled by the guardrail agent
        )
        heuristic_validator = LayeredValidator(config=heuristic_config)

    async def guardrail_function(
        ctx: "RunContextWrapper",
        agent: "Agent",
        output: Any,
    ) -> "GuardrailFunctionOutput":
        """Layered THSP output validation with heuristic + semantic layers."""
        start_time = time.time()

        # Extract text from output (handles None/empty safely)
        text = extract_text_from_input(output)

        # Handle empty output - allow through but flag it
        if not text or not text.strip():
            logger.debug("Empty output received, allowing through")
            return GuardrailFunctionOutput(
                output_info={
                    "is_safe": True,
                    "gates": {"truth": True, "harm": True, "scope": True, "purpose": True},
                    "violated_gate": None,
                    "reasoning": "Empty output - no validation needed",
                    "risk_level": "low",
                    "was_truncated": False,
                    "validation_time_ms": (time.time() - start_time) * 1000,
                    "layer": "none",
                },
                tripwire_triggered=False,
            )

        # ============================================================
        # LAYER 1: Heuristic Validation (fast, free)
        # ============================================================
        if heuristic_validator is not None:
            heuristic_result = heuristic_validator.validate(text)
            heuristic_time = (time.time() - start_time) * 1000

            if not heuristic_result.is_safe:
                logger.debug(f"Output blocked by heuristic layer: {heuristic_result.violations}")

                # Map heuristic violations to THSP gates
                violated_gate = "harm"  # Default for output violations
                if any("truth" in v.lower() or "decept" in v.lower() for v in heuristic_result.violations):
                    violated_gate = "truth"
                elif any("scope" in v.lower() for v in heuristic_result.violations):
                    violated_gate = "scope"

                # Log violation if configured
                if config.log_violations:
                    violations_log = get_violations_log(config.max_violations_log)
                    record = ViolationRecord(
                        timestamp=datetime.now(timezone.utc),
                        gate_violated=violated_gate,
                        risk_level=heuristic_result.risk_level.value if hasattr(heuristic_result.risk_level, 'value') else str(heuristic_result.risk_level),
                        reasoning_summary=f"Heuristic: {heuristic_result.violations[0][:100]}" if heuristic_result.violations else "Heuristic block",
                        content_hash=hashlib.sha256(text.encode()).hexdigest(),
                        was_input=False,
                        injection_detected=False,
                    )
                    violations_log.add(record)

                # If skip_semantic_if_heuristic_blocks, return immediately
                if config.skip_semantic_if_heuristic_blocks:
                    return GuardrailFunctionOutput(
                        output_info={
                            "is_safe": False,
                            "gates": {
                                "truth": violated_gate != "truth",
                                "harm": violated_gate != "harm",
                                "scope": violated_gate != "scope",
                                "purpose": True,
                            },
                            "violated_gate": violated_gate,
                            "reasoning": f"Blocked by heuristic layer: {', '.join(heuristic_result.violations)}",
                            "risk_level": heuristic_result.risk_level.value if hasattr(heuristic_result.risk_level, 'value') else str(heuristic_result.risk_level),
                            "was_truncated": False,
                            "validation_time_ms": heuristic_time,
                            "layer": "heuristic",
                        },
                        tripwire_triggered=config.block_on_violation,
                    )
                # Otherwise, continue to semantic layer for confirmation

        # ============================================================
        # LAYER 2: Semantic Validation (LLM-based, precise)
        # ============================================================

        # Create sanitized validation prompt
        validation_prompt, metadata = create_validation_prompt(
            content=text,
            content_type="OUTPUT",
            max_length=config.max_input_size,
        )

        try:
            # Run validation with timeout
            try:
                result = await asyncio.wait_for(
                    Runner.run(
                        guardrail_agent,
                        validation_prompt,
                        context=ctx.context,
                    ),
                    timeout=config.validation_timeout,
                )
            except asyncio.TimeoutError:
                raise ValidationTimeoutError(
                    config.validation_timeout,
                    "output validation"
                )

            raw_validation = result.final_output_as(output_type)

            # Validate the result is usable
            validation = _validate_result(raw_validation, output_type)

            # Determine tripwire
            tripwire = _determine_tripwire(validation, config)

            # Log violation if configured
            if config.log_violations and not validation.is_safe:
                _log_violation(validation, text, is_input=False, config=config, metadata=metadata)

            validation_time = (time.time() - start_time) * 1000

            # Safely extract reasoning for output
            reasoning = get_reasoning_safe(validation)

            return GuardrailFunctionOutput(
                output_info={
                    "is_safe": validation.is_safe,
                    "gates": {
                        "truth": validation.truth_passes,
                        "harm": validation.harm_passes,
                        "scope": validation.scope_passes,
                        "purpose": validation.purpose_passes,
                    },
                    "violated_gate": validation.violated_gate,
                    "reasoning": reasoning,
                    "risk_level": getattr(validation, "risk_level", "unknown"),
                    "was_truncated": metadata.get("was_truncated", False),
                    "validation_time_ms": validation_time,
                    "layer": "semantic",
                },
                tripwire_triggered=tripwire,
            )

        except Exception as e:
            logger.error(f"Output validation error: {type(e).__name__}: {str(e)[:100]}")

            # Fail-safe or fail-open based on config
            should_block = not config.fail_open

            return GuardrailFunctionOutput(
                output_info={
                    "is_safe": config.fail_open,
                    "error": f"{type(e).__name__}: {str(e)[:100]}",
                    "reasoning": "Validation failed - " + (
                        "blocking for safety" if should_block else "allowing (fail_open=True)"
                    ),
                    "layer": "error",
                },
                tripwire_triggered=should_block and config.block_on_violation,
            )

    return OutputGuardrail(
        guardrail_function=guardrail_function,
        name=name,
    )


def create_sentinel_guardrails(
    config: Optional[SentinelGuardrailConfig] = None,
    input_parallel: bool = False,
) -> tuple:
    """
    Create a pair of Sentinel guardrails for use with existing agents.

    Args:
        config: Guardrail configuration (shared between both guardrails)
        input_parallel: Whether input guardrail runs in parallel

    Returns:
        Tuple of (input_guardrail, output_guardrail)

    Raises:
        ImportError: If openai-agents package is not installed

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
    require_agents_sdk()

    config = config or SentinelGuardrailConfig()

    input_guard = sentinel_input_guardrail(
        config=config,
        run_in_parallel=input_parallel,
    )

    output_guard = sentinel_output_guardrail(config=config)

    return input_guard, output_guard
