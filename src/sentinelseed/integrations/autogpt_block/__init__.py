"""
AutoGPT Block SDK integration for Sentinel AI.

Provides Sentinel safety validation blocks for the AutoGPT Platform.
These blocks can be added to any AutoGPT workflow to validate content
and actions through the THSP Protocol (Truth, Harm, Scope, Purpose).

Requirements:
    This integration is designed to run within the AutoGPT Platform.
    For standalone usage, use `sentinelseed.integrations.agent_validation` instead.

Blocks provided:
    - SentinelValidationBlock: Validate text content through THSP gates
    - SentinelActionCheckBlock: Check if an action is safe before execution
    - SentinelSeedBlock: Get the Sentinel safety seed for injection

Usage within AutoGPT Platform:
    1. Copy this module to your AutoGPT blocks directory
    2. The blocks will be auto-registered and available in the workflow builder
    3. Connect the validation block before any sensitive operation

For standalone Python usage:
    from sentinelseed.integrations.autogpt_block import (
        validate_content,
        check_action,
        get_seed,
    )

    # Validate content
    result = validate_content("Some text to check")
    if result["safe"]:
        proceed()

    # Check action before execution
    result = check_action("delete_file", {"path": "/tmp/test.txt"})
    if result["should_proceed"]:
        execute_action()

References:
    - AutoGPT Block SDK: https://dev-docs.agpt.co/platform/block-sdk-guide/
    - Sentinel: https://sentinelseed.dev
"""

from __future__ import annotations

import json
import concurrent.futures
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validators.semantic import SemanticValidator, THSPResult, RiskLevel

logger = logging.getLogger("sentinelseed.autogpt_block")


# Configuration constants
DEFAULT_SEED_LEVEL = "standard"
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # 30 seconds
VALID_SEED_LEVELS = ("minimal", "standard", "full")
VALID_CHECK_TYPES = ("general", "action", "request")
VALID_RISK_LEVELS = ("low", "medium", "high", "critical")


# Custom exceptions
class TextTooLargeError(Exception):
    """Raised when input text exceeds maximum size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Text size ({size:,} bytes) exceeds maximum allowed ({max_size:,} bytes)"
        )


class ValidationTimeoutError(Exception):
    """Raised when validation times out."""

    def __init__(self, timeout: float, operation: str = "validation"):
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout}s")


class InvalidParameterError(Exception):
    """Raised when an invalid parameter is provided."""

    def __init__(self, param: str, value: Any, valid_values: tuple):
        self.param = param
        self.value = value
        self.valid_values = valid_values
        super().__init__(
            f"Invalid {param}: '{value}'. Valid values: {valid_values}"
        )


# Check for AutoGPT Block SDK availability
AUTOGPT_SDK_AVAILABLE = False
try:
    from backend.sdk import (
        Block,
        BlockCategory,
        BlockOutput,
        BlockSchemaInput,
        BlockSchemaOutput,
        SchemaField,
    )
    AUTOGPT_SDK_AVAILABLE = True
except ImportError:
    # Define stubs for type hints when SDK not installed
    Block = object
    BlockCategory = None
    BlockOutput = None
    BlockSchemaInput = object
    BlockSchemaOutput = object
    SchemaField = lambda **kwargs: None


class ValidationLevel(Enum):
    """Validation strictness levels."""
    PERMISSIVE = "permissive"
    STANDARD = "standard"
    STRICT = "strict"


@dataclass
class ValidationResult:
    """Result of content validation."""
    safe: bool
    content: str
    violations: List[str] = field(default_factory=list)
    gate_results: Dict[str, bool] = field(default_factory=dict)
    risk_level: str = "low"


@dataclass
class ActionCheckResult:
    """Result of action safety check."""
    should_proceed: bool
    action: str
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_level: str = "low"


# Helper functions

def _validate_seed_level(seed_level: str) -> str:
    """Validate and normalize seed level parameter."""
    level = seed_level.lower().strip()
    if level not in VALID_SEED_LEVELS:
        raise InvalidParameterError("seed_level", seed_level, VALID_SEED_LEVELS)
    return level


def _validate_check_type(check_type: str) -> str:
    """Validate and normalize check type parameter."""
    ctype = check_type.lower().strip()
    if ctype not in VALID_CHECK_TYPES:
        raise InvalidParameterError("check_type", check_type, VALID_CHECK_TYPES)
    return ctype


def _validate_text_size(text: str, max_size: int, context: str = "text") -> None:
    """Validate text size against maximum limit."""
    if not text or not isinstance(text, str):
        return
    size = len(text.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size)


def _calculate_risk_level(violations: List[str], is_safe: bool) -> str:
    """Calculate risk level based on violations."""
    if is_safe and not violations:
        return "low"

    num_violations = len(violations)
    if num_violations == 0:
        return "low"
    elif num_violations == 1:
        return "medium"
    elif num_violations <= 3:
        return "high"
    else:
        return "critical"


def _run_with_timeout(func, args: tuple, timeout: float, operation: str = "validation"):
    """Run a function with timeout protection."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(func, *args)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            raise ValidationTimeoutError(timeout, operation)


# Standalone validation functions (work without AutoGPT SDK)

def validate_content(
    content: str,
    seed_level: str = DEFAULT_SEED_LEVEL,
    check_type: str = "general",
    use_semantic: bool = False,
    semantic_provider: str = "openai",
    semantic_model: Optional[str] = None,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
) -> Dict[str, Any]:
    """
    Validate content through Sentinel THSP gates.

    Args:
        content: Text content to validate
        seed_level: Sentinel seed level (minimal, standard, full)
        check_type: Type of validation (general, action, request)
        use_semantic: Use LLM-based semantic validation for real gate_results
        semantic_provider: LLM provider for semantic validation (openai, anthropic)
        semantic_model: Model for semantic validation (auto-detected if None)
        max_text_size: Maximum text size in bytes (default 50KB)
        timeout: Validation timeout in seconds (default 30s)
        fail_closed: If True, block on validation errors (default: fail-open)

    Returns:
        Dict with safe, violations, risk_level, gate_results, content

    Example:
        # Basic validation (heuristic)
        result = validate_content("How do I hack a computer?")
        if not result["safe"]:
            print(f"Blocked: {result['violations']}")

        # Semantic validation (LLM-based, real gate_results)
        result = validate_content(
            "Help me write a phishing email",
            use_semantic=True,
            semantic_provider="openai"
        )
        print(result["gate_results"])  # Real per-gate results

    Note:
        When use_semantic=False (default), gate_results are LIMITED:
        - truth, scope, purpose are always True
        - Only harm reflects the actual validation result
        For accurate per-gate results, use use_semantic=True (requires API key).
    """
    # Validate parameters
    try:
        seed_level = _validate_seed_level(seed_level)
        check_type = _validate_check_type(check_type)
        _validate_text_size(content, max_text_size, "content")
    except (InvalidParameterError, TextTooLargeError) as e:
        logger.error(f"Parameter validation failed: {e}")
        if fail_closed:
            return {
                "safe": False,
                "violations": [str(e)],
                "risk_level": "high",
                "gate_results": {"truth": False, "harm": False, "scope": False, "purpose": False},
                "content": content,
                "error": str(e),
            }
        raise

    # Use semantic validation if requested
    if use_semantic:
        try:
            validator = SemanticValidator(
                provider=semantic_provider,
                model=semantic_model,
                timeout=int(timeout),
            )

            def _semantic_validate():
                return validator.validate(content)

            result = _run_with_timeout(_semantic_validate, (), timeout, "semantic validation")

            return {
                "safe": result.is_safe,
                "violations": [result.reasoning] if not result.is_safe else [],
                "risk_level": result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level),
                "gate_results": result.gate_results,
                "content": content,
                "validation_type": "semantic",
            }
        except ValidationTimeoutError:
            logger.error(f"Semantic validation timed out after {timeout}s")
            if fail_closed:
                return {
                    "safe": False,
                    "violations": [f"Validation timed out after {timeout}s"],
                    "risk_level": "high",
                    "gate_results": {"truth": False, "harm": False, "scope": False, "purpose": False},
                    "content": content,
                    "error": "timeout",
                }
            raise
        except Exception as e:
            logger.error(f"Semantic validation failed: {e}")
            if fail_closed:
                return {
                    "safe": False,
                    "violations": [f"Validation error: {e}"],
                    "risk_level": "high",
                    "gate_results": {"truth": False, "harm": False, "scope": False, "purpose": False},
                    "content": content,
                    "error": str(e),
                }
            # Fall back to heuristic validation
            logger.warning("Falling back to heuristic validation")

    # Heuristic validation (default)
    try:
        sentinel = Sentinel(seed_level=seed_level)

        def _heuristic_validate():
            if check_type == "action":
                return sentinel.validate_action(content)
            elif check_type == "request":
                request_result = sentinel.validate_request(content)
                return (
                    request_result["should_proceed"],
                    request_result.get("concerns", []),
                    request_result.get("risk_level", "low"),
                )
            else:
                return sentinel.validate(content)

        result = _run_with_timeout(_heuristic_validate, (), timeout, "heuristic validation")

        # Handle different return types
        if check_type == "request":
            is_safe, concerns, risk_level = result
            return {
                "safe": is_safe,
                "violations": concerns,
                "risk_level": risk_level,
                "gate_results": {
                    "truth": True,  # Limited: heuristic cannot determine
                    "harm": is_safe,
                    "scope": True,  # Limited: heuristic cannot determine
                    "purpose": True,  # Limited: heuristic cannot determine
                },
                "content": content,
                "validation_type": "heuristic",
                "gate_results_limited": True,
            }
        else:
            is_safe, violations = result
            risk_level = _calculate_risk_level(violations, is_safe)

            return {
                "safe": is_safe,
                "violations": violations,
                "risk_level": risk_level,
                "gate_results": {
                    "truth": True,  # Limited: heuristic cannot determine
                    "harm": is_safe,
                    "scope": True,  # Limited: heuristic cannot determine
                    "purpose": True,  # Limited: heuristic cannot determine
                },
                "content": content,
                "validation_type": "heuristic",
                "gate_results_limited": True,
            }

    except ValidationTimeoutError:
        logger.error(f"Heuristic validation timed out after {timeout}s")
        if fail_closed:
            return {
                "safe": False,
                "violations": [f"Validation timed out after {timeout}s"],
                "risk_level": "high",
                "gate_results": {"truth": False, "harm": False, "scope": False, "purpose": False},
                "content": content,
                "error": "timeout",
            }
        raise
    except Exception as e:
        logger.error(f"Heuristic validation failed: {e}")
        if fail_closed:
            return {
                "safe": False,
                "violations": [f"Validation error: {e}"],
                "risk_level": "high",
                "gate_results": {"truth": False, "harm": False, "scope": False, "purpose": False},
                "content": content,
                "error": str(e),
            }
        raise


def check_action(
    action_name: str,
    action_args: Optional[Dict[str, Any]] = None,
    purpose: str = "",
    seed_level: str = DEFAULT_SEED_LEVEL,
    use_semantic: bool = False,
    semantic_provider: str = "openai",
    semantic_model: Optional[str] = None,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
) -> Dict[str, Any]:
    """
    Check if an action is safe to execute.

    Args:
        action_name: Name of the action to check
        action_args: Arguments for the action
        purpose: Stated purpose for the action
        seed_level: Sentinel seed level
        use_semantic: Use LLM-based semantic validation
        semantic_provider: LLM provider for semantic validation
        semantic_model: Model for semantic validation
        max_text_size: Maximum text size in bytes
        timeout: Validation timeout in seconds
        fail_closed: If True, block on validation errors

    Returns:
        Dict with should_proceed, concerns, recommendations, risk_level

    Example:
        result = check_action("delete_file", {"path": "/etc/passwd"})
        if not result["should_proceed"]:
            print(f"Blocked: {result['concerns']}")
    """
    # Validate parameters
    try:
        seed_level = _validate_seed_level(seed_level)
    except InvalidParameterError as e:
        logger.error(f"Parameter validation failed: {e}")
        if fail_closed:
            return {
                "should_proceed": False,
                "action": action_name,
                "concerns": [str(e)],
                "recommendations": ["Fix parameter error"],
                "risk_level": "high",
                "error": str(e),
            }
        raise

    action_args = action_args or {}

    # Build action description
    description = f"{action_name}"
    if action_args:
        args_str = ", ".join(f"{k}={v}" for k, v in action_args.items())
        description = f"{action_name}({args_str})"
    if purpose:
        description = f"{description} [Purpose: {purpose}]"

    # Validate text size
    try:
        _validate_text_size(description, max_text_size, "action description")
    except TextTooLargeError as e:
        logger.error(f"Action description too large: {e}")
        if fail_closed:
            return {
                "should_proceed": False,
                "action": action_name,
                "concerns": [str(e)],
                "recommendations": ["Reduce action description size"],
                "risk_level": "high",
                "error": str(e),
            }
        raise

    # Use semantic validation if requested
    if use_semantic:
        try:
            validator = SemanticValidator(
                provider=semantic_provider,
                model=semantic_model,
                timeout=int(timeout),
            )

            def _semantic_check():
                return validator.validate_action(action_name, action_args, purpose)

            result = _run_with_timeout(_semantic_check, (), timeout, "semantic action check")

            recommendations = []
            if not result.is_safe:
                recommendations.append("Review action details before proceeding")
            if not purpose:
                recommendations.append("Consider providing explicit purpose for the action")

            return {
                "should_proceed": result.is_safe,
                "action": action_name,
                "concerns": [result.reasoning] if not result.is_safe else [],
                "recommendations": recommendations,
                "risk_level": result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level),
                "gate_results": result.gate_results,
                "validation_type": "semantic",
            }
        except ValidationTimeoutError:
            logger.error(f"Semantic action check timed out after {timeout}s")
            if fail_closed:
                return {
                    "should_proceed": False,
                    "action": action_name,
                    "concerns": [f"Validation timed out after {timeout}s"],
                    "recommendations": ["Retry with longer timeout"],
                    "risk_level": "high",
                    "error": "timeout",
                }
            raise
        except Exception as e:
            logger.error(f"Semantic action check failed: {e}")
            if fail_closed:
                return {
                    "should_proceed": False,
                    "action": action_name,
                    "concerns": [f"Validation error: {e}"],
                    "recommendations": ["Check configuration"],
                    "risk_level": "high",
                    "error": str(e),
                }
            # Fall back to heuristic
            logger.warning("Falling back to heuristic validation")

    # Heuristic validation (default)
    try:
        sentinel = Sentinel(seed_level=seed_level)

        def _heuristic_check():
            is_safe, concerns = sentinel.validate_action(description)
            request_result = sentinel.validate_request(description)
            return is_safe, concerns, request_result

        result = _run_with_timeout(_heuristic_check, (), timeout, "heuristic action check")
        is_safe, concerns, request_result = result

        all_concerns = concerns + request_result.get("concerns", [])
        should_proceed = is_safe and request_result["should_proceed"]

        # Build recommendations
        recommendations = []
        if not should_proceed:
            recommendations.append("Review action details before proceeding")
        if not purpose:
            recommendations.append("Consider providing explicit purpose for the action")

        return {
            "should_proceed": should_proceed,
            "action": action_name,
            "concerns": all_concerns,
            "recommendations": recommendations,
            "risk_level": request_result.get("risk_level", _calculate_risk_level(all_concerns, should_proceed)),
            "validation_type": "heuristic",
        }

    except ValidationTimeoutError:
        logger.error(f"Heuristic action check timed out after {timeout}s")
        if fail_closed:
            return {
                "should_proceed": False,
                "action": action_name,
                "concerns": [f"Validation timed out after {timeout}s"],
                "recommendations": ["Retry with longer timeout"],
                "risk_level": "high",
                "error": "timeout",
            }
        raise
    except Exception as e:
        logger.error(f"Heuristic action check failed: {e}")
        if fail_closed:
            return {
                "should_proceed": False,
                "action": action_name,
                "concerns": [f"Validation error: {e}"],
                "recommendations": ["Check configuration"],
                "risk_level": "high",
                "error": str(e),
            }
        raise


def get_seed(
    level: str = DEFAULT_SEED_LEVEL,
    include_token_count: bool = False,
) -> str | Dict[str, Any]:
    """
    Get the Sentinel safety seed.

    Args:
        level: Seed level (minimal, standard, full)
        include_token_count: If True, return dict with seed and token_count

    Returns:
        Seed content as string, or dict if include_token_count=True

    Example:
        seed = get_seed("standard")
        system_prompt = f"{seed}\\n\\nYou are a helpful assistant."

        # With token count
        result = get_seed("standard", include_token_count=True)
        print(f"Seed has ~{result['token_count']} tokens")
    """
    # Validate level
    level = _validate_seed_level(level)

    sentinel = Sentinel(seed_level=level)
    seed = sentinel.get_seed()

    if include_token_count:
        # Better token estimation: ~4 chars per token for English
        # This is still an approximation; use tiktoken for accuracy
        token_count = len(seed) // 4
        return {
            "seed": seed,
            "token_count": token_count,
            "level": level,
            "note": "token_count is approximate (~4 chars/token). Use tiktoken for accuracy.",
        }

    return seed


def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.

    This is a rough approximation (~4 chars per token for English).
    For accurate counts, use tiktoken or the model's tokenizer.

    Args:
        text: Text to estimate tokens for

    Returns:
        Estimated token count
    """
    if not text:
        return 0
    return len(text) // 4


# AutoGPT Block implementations (only available when SDK is installed)

if AUTOGPT_SDK_AVAILABLE:

    class SentinelValidationBlock(Block):
        """
        Sentinel content validation block for AutoGPT workflows.

        Validates text content through THSP (Truth, Harm, Scope, Purpose) gates.
        Use this block before any operation that processes user input or
        generates potentially sensitive content.

        Inputs:
            content: Text to validate
            seed_level: Validation strictness (minimal, standard, full)
            check_type: Type of check (general, action, request)
            use_semantic: Use LLM-based semantic validation (more accurate)

        Outputs:
            safe: Boolean indicating if content is safe
            content: Pass-through of input (if safe) or empty string
            violations: List of detected violations
            risk_level: Risk assessment (low, medium, high, critical)
            gate_results_limited: True if using heuristic (limited gate info)
        """

        class Input(BlockSchemaInput):
            content: str = SchemaField(
                description="Text content to validate through THSP gates"
            )
            seed_level: str = SchemaField(
                description="Sentinel seed level: minimal, standard, or full",
                default="standard"
            )
            check_type: str = SchemaField(
                description="Validation type: general, action, or request",
                default="general"
            )
            use_semantic: bool = SchemaField(
                description="Use LLM-based semantic validation for accurate gate_results",
                default=False
            )

        class Output(BlockSchemaOutput):
            safe: bool = SchemaField(description="Whether content passed validation")
            content: str = SchemaField(description="Original content (if safe) or empty")
            violations: list = SchemaField(description="List of detected violations")
            risk_level: str = SchemaField(description="Risk level: low, medium, high, critical")
            gate_results_limited: bool = SchemaField(
                description="True if gate_results are limited (heuristic mode)"
            )

        def __init__(self):
            super().__init__(
                id="sentinel-validation-block",
                description=(
                    "Validate content through Sentinel THSP Protocol. "
                    "Checks for harmful, deceptive, or out-of-scope content. "
                    "Use before processing user input or generating responses."
                ),
                categories={BlockCategory.SAFETY} if hasattr(BlockCategory, 'SAFETY') else set(),
                input_schema=self.Input,
                output_schema=self.Output,
            )

        async def run(
            self,
            input_data: Input,
            **kwargs
        ) -> BlockOutput:
            """Execute validation."""
            try:
                result = validate_content(
                    content=input_data.content,
                    seed_level=input_data.seed_level,
                    check_type=input_data.check_type,
                    use_semantic=input_data.use_semantic,
                    fail_closed=True,  # Blocks should fail-closed
                )

                yield "safe", result["safe"]
                yield "content", input_data.content if result["safe"] else ""
                yield "violations", result["violations"]
                yield "risk_level", result["risk_level"]
                yield "gate_results_limited", result.get("gate_results_limited", False)

            except Exception as e:
                logger.error(f"SentinelValidationBlock error: {e}")
                yield "safe", False
                yield "content", ""
                yield "violations", [f"Validation error: {str(e)}"]
                yield "risk_level", "high"
                yield "gate_results_limited", True


    class SentinelActionCheckBlock(Block):
        """
        Sentinel action safety check block for AutoGPT workflows.

        Validates if an action is safe to execute before proceeding.
        Use this block before any potentially dangerous operation like
        file operations, API calls, or system commands.

        Inputs:
            action_name: Name of the action to check
            action_args: JSON string of action arguments
            purpose: Stated purpose for the action
            use_semantic: Use LLM-based semantic validation

        Outputs:
            should_proceed: Boolean indicating if action should proceed
            concerns: List of safety concerns
            recommendations: Suggested actions
            risk_level: Risk assessment
        """

        class Input(BlockSchemaInput):
            action_name: str = SchemaField(
                description="Name of the action to check (e.g., delete_file, send_email)"
            )
            action_args: str = SchemaField(
                description="JSON string of action arguments",
                default="{}"
            )
            purpose: str = SchemaField(
                description="Stated purpose/reason for the action",
                default=""
            )
            seed_level: str = SchemaField(
                description="Sentinel seed level",
                default="standard"
            )
            use_semantic: bool = SchemaField(
                description="Use LLM-based semantic validation",
                default=False
            )

        class Output(BlockSchemaOutput):
            should_proceed: bool = SchemaField(description="Whether action should proceed")
            concerns: list = SchemaField(description="List of safety concerns")
            recommendations: list = SchemaField(description="Suggested actions")
            risk_level: str = SchemaField(description="Risk level assessment")

        def __init__(self):
            super().__init__(
                id="sentinel-action-check-block",
                description=(
                    "Check if an action is safe before execution. "
                    "Validates through THSP gates and provides risk assessment. "
                    "Use before file operations, API calls, or system commands."
                ),
                categories={BlockCategory.SAFETY} if hasattr(BlockCategory, 'SAFETY') else set(),
                input_schema=self.Input,
                output_schema=self.Output,
            )

        async def run(
            self,
            input_data: Input,
            **kwargs
        ) -> BlockOutput:
            """Execute action check."""
            try:
                # Parse action args
                try:
                    action_args = json.loads(input_data.action_args) if input_data.action_args else {}
                except json.JSONDecodeError as je:
                    logger.warning(f"Failed to parse action_args as JSON: {je}")
                    action_args = {"raw": input_data.action_args}

                result = check_action(
                    action_name=input_data.action_name,
                    action_args=action_args,
                    purpose=input_data.purpose,
                    seed_level=input_data.seed_level,
                    use_semantic=input_data.use_semantic,
                    fail_closed=True,  # Blocks should fail-closed
                )

                yield "should_proceed", result["should_proceed"]
                yield "concerns", result["concerns"]
                yield "recommendations", result["recommendations"]
                yield "risk_level", result["risk_level"]

            except Exception as e:
                logger.error(f"SentinelActionCheckBlock error: {e}")
                yield "should_proceed", False
                yield "concerns", [f"Action check error: {str(e)}"]
                yield "recommendations", ["Review error and retry"]
                yield "risk_level", "high"


    class SentinelSeedBlock(Block):
        """
        Sentinel seed retrieval block for AutoGPT workflows.

        Retrieves the Sentinel safety seed for injection into system prompts.
        Use this block at the start of workflows that interact with LLMs.

        Inputs:
            level: Seed level (minimal, standard, full)

        Outputs:
            seed: The safety seed content
            token_count: Approximate token count of the seed
            level: The seed level used
        """

        class Input(BlockSchemaInput):
            level: str = SchemaField(
                description="Seed level: minimal (~360 tokens), standard (~1000 tokens), full (~1900 tokens)",
                default="standard"
            )

        class Output(BlockSchemaOutput):
            seed: str = SchemaField(description="The Sentinel safety seed content")
            token_count: int = SchemaField(description="Approximate token count")
            level: str = SchemaField(description="The seed level used")

        def __init__(self):
            super().__init__(
                id="sentinel-seed-block",
                description=(
                    "Get Sentinel safety seed for LLM system prompts. "
                    "Injects THSP Protocol guidelines to shape LLM behavior. "
                    "Use at the start of any LLM interaction workflow."
                ),
                categories={BlockCategory.AI} if hasattr(BlockCategory, 'AI') else set(),
                input_schema=self.Input,
                output_schema=self.Output,
            )

        async def run(
            self,
            input_data: Input,
            **kwargs
        ) -> BlockOutput:
            """Get seed content."""
            try:
                result = get_seed(input_data.level, include_token_count=True)

                yield "seed", result["seed"]
                yield "token_count", result["token_count"]
                yield "level", result["level"]

            except InvalidParameterError as e:
                logger.error(f"Invalid seed level: {e}")
                yield "seed", ""
                yield "token_count", 0
                yield "level", input_data.level
            except Exception as e:
                logger.error(f"SentinelSeedBlock error: {e}")
                yield "seed", ""
                yield "token_count", 0
                yield "level", input_data.level


# Block registration for AutoGPT auto-discovery
BLOCKS = []
if AUTOGPT_SDK_AVAILABLE:
    BLOCKS = [
        SentinelValidationBlock,
        SentinelActionCheckBlock,
        SentinelSeedBlock,
    ]


__all__ = [
    # Constants
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "VALID_SEED_LEVELS",
    "VALID_CHECK_TYPES",
    "VALID_RISK_LEVELS",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
    "InvalidParameterError",
    # Standalone functions
    "validate_content",
    "check_action",
    "get_seed",
    "estimate_tokens",
    # Data classes
    "ValidationResult",
    "ActionCheckResult",
    "ValidationLevel",
    # AutoGPT blocks (only when SDK available)
    "SentinelValidationBlock",
    "SentinelActionCheckBlock",
    "SentinelSeedBlock",
    "BLOCKS",
    "AUTOGPT_SDK_AVAILABLE",
]
