"""
Agent Validation - Framework-agnostic safety validation for autonomous agents.

This module provides reusable safety validation components that work with ANY
autonomous agent framework. Uses semantic LLM-based validation for accurate,
context-aware safety analysis.

Components:
    - SafetyValidator: Core validation using semantic LLM analysis
    - AsyncSafetyValidator: Async version for async frameworks
    - ExecutionGuard: Decorator/wrapper for protected function execution
    - safety_check: Standalone function for quick validation

Usage:

    # Pattern 1: Validation component in your agent
    from sentinelseed.integrations.agent_validation import SafetyValidator

    class MyAgent:
        def __init__(self):
            self.safety = SafetyValidator(
                provider="openai",  # or "anthropic"
                model="gpt-4o-mini",
            )

        def execute(self, action):
            result = self.safety.validate_action(action)
            if not result.should_proceed:
                return f"Blocked: {result.reasoning}"
            # proceed with action

    # Pattern 2: Decorator for protected functions
    from sentinelseed.integrations.agent_validation import ExecutionGuard

    guard = ExecutionGuard(provider="openai")

    @guard.protected
    def execute_command(cmd):
        # your logic
        pass

    # Pattern 3: Quick standalone check
    from sentinelseed.integrations.agent_validation import safety_check

    result = safety_check("Delete all files", provider="openai")
    if not result["safe"]:
        print(f"Blocked: {result['reasoning']}")
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from functools import wraps
from collections import deque
import asyncio
import logging
import time

from sentinelseed import Sentinel
from sentinelseed.validators.semantic import (
    SemanticValidator,
    AsyncSemanticValidator,
    THSPResult,
    RiskLevel,
)

logger = logging.getLogger("sentinelseed.agent_validation")

# Valid providers
VALID_PROVIDERS = ("openai", "anthropic")

# Default limits
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_HISTORY_LIMIT = 1000
DEFAULT_VALIDATION_TIMEOUT = 30.0  # seconds


class TextTooLargeError(ValueError):
    """Raised when input text exceeds the maximum allowed size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Text size ({size:,} bytes) exceeds maximum allowed ({max_size:,} bytes)"
        )


class ValidationTimeoutError(TimeoutError):
    """Raised when validation exceeds the configured timeout."""

    def __init__(self, timeout: float):
        self.timeout = timeout
        super().__init__(f"Validation timed out after {timeout:.1f} seconds")


class InvalidProviderError(ValueError):
    """Raised when an invalid provider is specified."""

    def __init__(self, provider: str):
        self.provider = provider
        super().__init__(
            f"Invalid provider '{provider}'. Must be one of: {', '.join(VALID_PROVIDERS)}"
        )


@dataclass
class ValidationResult:
    """
    Result of a safety validation check.

    Attributes:
        safe: Whether the action passed safety checks
        action: The action that was validated (truncated)
        concerns: List of safety concerns identified
        risk_level: Assessed risk level
        should_proceed: Whether to proceed with the action
        reasoning: Explanation of the decision
        gate_results: Per-gate validation results
    """

    safe: bool
    action: str
    concerns: List[str] = field(default_factory=list)
    risk_level: str = "low"
    should_proceed: bool = True
    reasoning: str = ""
    gate_results: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_thsp(cls, thsp_result: THSPResult, action: str) -> "ValidationResult":
        """Create ValidationResult from THSPResult."""
        concerns = []
        if not thsp_result.truth_passes:
            concerns.append("Failed Truth gate: potential deception")
        if not thsp_result.harm_passes:
            concerns.append("Failed Harm gate: could cause harm")
        if not thsp_result.scope_passes:
            concerns.append("Failed Scope gate: exceeds boundaries")
        if not thsp_result.purpose_passes:
            concerns.append("Failed Purpose gate: no legitimate purpose")

        risk_str = (
            thsp_result.risk_level.value
            if isinstance(thsp_result.risk_level, RiskLevel)
            else thsp_result.risk_level
        )

        return cls(
            safe=thsp_result.is_safe,
            action=str(action)[:100] if action else "unknown",
            concerns=concerns,
            risk_level=risk_str,
            should_proceed=thsp_result.is_safe,
            reasoning=thsp_result.reasoning,
            gate_results=thsp_result.gate_results,
        )

    @classmethod
    def error_result(cls, action: str, error: Exception) -> "ValidationResult":
        """Create a ValidationResult for an error condition."""
        return cls(
            safe=False,
            action=action[:100] if action else "unknown",
            concerns=[f"Validation error: {type(error).__name__}"],
            risk_level="high",
            should_proceed=False,
            reasoning=f"Validation failed due to error: {str(error)}",
            gate_results={
                "truth": False,
                "harm": False,
                "scope": False,
                "purpose": False,
            },
        )


class SafetyValidator:
    """
    Core safety validation component using semantic LLM analysis.

    Uses THSP Protocol (Truth, Harm, Scope, Purpose) with real LLM
    semantic analysis - not regex pattern matching.

    Example:
        from sentinelseed.integrations.agent_validation import SafetyValidator

        validator = SafetyValidator(provider="openai", model="gpt-4o-mini")

        # Validate action
        result = validator.validate_action("transfer 100 SOL to address")
        if result.should_proceed:
            execute_transfer()
        else:
            print(f"Blocked: {result.reasoning}")
    """

    name = "SentinelSafetyValidator"
    description = "AI safety validation using semantic THSP analysis"

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        seed_level: str = "standard",
        block_unsafe: bool = True,
        log_checks: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        """
        Initialize the safety validator.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            seed_level: Seed level for seed injection
            block_unsafe: Whether to block unsafe actions
            log_checks: Whether to log safety checks
            max_text_size: Maximum text size in bytes (default: 50KB)
            history_limit: Maximum history entries (default: 1000)
            validation_timeout: Timeout for validation in seconds (default: 30)
            fail_closed: If True, validation errors result in blocking (default: False)
        """
        # Validate provider
        if provider not in VALID_PROVIDERS:
            raise InvalidProviderError(provider)

        # Validate parameters
        if validation_timeout <= 0:
            raise ValueError("validation_timeout must be positive")
        if max_text_size <= 0:
            raise ValueError("max_text_size must be positive")

        self.provider = provider
        self.model = model
        self.block_unsafe = block_unsafe
        self.log_checks = log_checks
        self.seed_level = seed_level
        self.max_text_size = max_text_size
        self.history_limit = history_limit
        self.validation_timeout = validation_timeout
        self.fail_closed = fail_closed

        # Semantic validator for real LLM-based analysis
        self._semantic = SemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )

        # Sentinel for seed retrieval
        self._sentinel = Sentinel(seed_level=seed_level)

        # History tracking with limit (deque for O(1) append and automatic eviction)
        self._check_history: deque = deque(maxlen=history_limit)

    def _validate_text_size(self, text: str, field_name: str = "text") -> None:
        """Validate that text is a valid string and doesn't exceed maximum size."""
        if text is None:
            raise ValueError(f"{field_name} cannot be None")
        if not isinstance(text, str):
            raise TypeError(f"{field_name} must be a string, got {type(text).__name__}")
        size = len(text.encode("utf-8"))
        if size > self.max_text_size:
            raise TextTooLargeError(size, self.max_text_size)

    def validate_action(
        self,
        action: str,
        purpose: str = "",
    ) -> ValidationResult:
        """
        Validate an agent action using semantic LLM analysis.

        Args:
            action: Action description or command to validate
            purpose: Optional stated purpose for the action

        Returns:
            ValidationResult with detailed safety assessment

        Raises:
            TextTooLargeError: If action exceeds max_text_size
            ValidationTimeoutError: If validation exceeds timeout
        """
        try:
            # Validate input size
            self._validate_text_size(action, "action")
            if purpose:
                self._validate_text_size(purpose, "purpose")

            # Semantic validation through LLM with timeout
            start_time = time.time()
            thsp_result = self._semantic.validate_action(
                action_name=action,
                purpose=purpose,
            )
            elapsed = time.time() - start_time

            if elapsed > self.validation_timeout:
                raise ValidationTimeoutError(self.validation_timeout)

            result = ValidationResult.from_thsp(thsp_result, action)

        except (TextTooLargeError, ValidationTimeoutError, ValueError, TypeError):
            # Re-raise validation errors (input validation, size, timeout)
            raise
        except Exception as e:
            logger.error(f"[SENTINEL] Validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(action, e)
            else:
                # Fail open: allow but log warning
                result = ValidationResult(
                    safe=True,
                    action=action[:100],
                    concerns=[f"Validation error (fail-open): {str(e)}"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning=f"Validation encountered error but fail_closed=False: {str(e)}",
                    gate_results={},
                )

        # Log if enabled
        if self.log_checks:
            self._check_history.append(result)
            if not result.should_proceed:
                logger.warning(f"[SENTINEL] Action blocked: {result.reasoning}")

        return result

    def validate_thought(self, thought: str) -> ValidationResult:
        """
        Validate agent thoughts/reasoning for safety concerns.

        Args:
            thought: Agent's thought or reasoning text

        Returns:
            ValidationResult

        Raises:
            TextTooLargeError: If thought exceeds max_text_size
        """
        try:
            self._validate_text_size(thought, "thought")

            thsp_result = self._semantic.validate(f"Agent thought: {thought}")
            result = ValidationResult.from_thsp(thsp_result, f"thought: {thought[:50]}...")

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except Exception as e:
            logger.error(f"[SENTINEL] Thought validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"thought: {thought[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"thought: {thought[:50]}...",
                    concerns=[f"Validation error (fail-open): {str(e)}"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning=f"Validation encountered error but fail_closed=False: {str(e)}",
                    gate_results={},
                )

        if self.log_checks:
            self._check_history.append(result)

        return result

    def validate_output(self, output: str) -> ValidationResult:
        """
        Validate agent output before returning to user.

        Args:
            output: Agent's output text

        Returns:
            ValidationResult

        Raises:
            TextTooLargeError: If output exceeds max_text_size
        """
        try:
            self._validate_text_size(output, "output")

            thsp_result = self._semantic.validate(f"Agent output to user: {output}")
            result = ValidationResult.from_thsp(thsp_result, f"output: {output[:50]}...")

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except Exception as e:
            logger.error(f"[SENTINEL] Output validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"output: {output[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"output: {output[:50]}...",
                    concerns=[f"Validation error (fail-open): {str(e)}"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning=f"Validation encountered error but fail_closed=False: {str(e)}",
                    gate_results={},
                )

        if self.log_checks:
            self._check_history.append(result)

        return result

    def get_seed(self) -> str:
        """
        Get Sentinel seed for injection into agent system prompt.

        Returns:
            Seed content string
        """
        return self._sentinel.get_seed()

    def get_history(self) -> List[ValidationResult]:
        """Get history of safety checks (returns a copy)."""
        return list(self._check_history)

    def clear_history(self) -> None:
        """Clear check history."""
        self._check_history.clear()

    @property
    def check_history(self) -> List[ValidationResult]:
        """Backward-compatible property for check_history."""
        return list(self._check_history)

    def get_stats(self) -> Dict[str, Any]:
        """Get safety check statistics."""
        history = list(self._check_history)
        if not history:
            return {"total_checks": 0}

        blocked = sum(1 for c in history if not c.should_proceed)
        high_risk = sum(1 for c in history if c.risk_level == "high")

        semantic_stats = self._semantic.get_stats()

        return {
            "total_checks": len(history),
            "blocked": blocked,
            "allowed": len(history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(history) if history else 0,
            "provider": semantic_stats.get("provider"),
            "model": semantic_stats.get("model"),
            "history_limit": self.history_limit,
            "max_text_size": self.max_text_size,
            "validation_timeout": self.validation_timeout,
            "fail_closed": self.fail_closed,
        }


class AsyncSafetyValidator:
    """
    Async version of SafetyValidator for use with async frameworks.

    Example:
        validator = AsyncSafetyValidator(provider="openai")
        result = await validator.validate_action("transfer funds")
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        seed_level: str = "standard",
        block_unsafe: bool = True,
        log_checks: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        """
        Initialize the async safety validator.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            seed_level: Seed level for seed injection
            block_unsafe: Whether to block unsafe actions
            log_checks: Whether to log safety checks
            max_text_size: Maximum text size in bytes (default: 50KB)
            history_limit: Maximum history entries (default: 1000)
            validation_timeout: Timeout for validation in seconds (default: 30)
            fail_closed: If True, validation errors result in blocking (default: False)
        """
        # Validate provider
        if provider not in VALID_PROVIDERS:
            raise InvalidProviderError(provider)

        # Validate parameters
        if validation_timeout <= 0:
            raise ValueError("validation_timeout must be positive")
        if max_text_size <= 0:
            raise ValueError("max_text_size must be positive")

        self.provider = provider
        self.model = model
        self.block_unsafe = block_unsafe
        self.log_checks = log_checks
        self.seed_level = seed_level
        self.max_text_size = max_text_size
        self.history_limit = history_limit
        self.validation_timeout = validation_timeout
        self.fail_closed = fail_closed

        self._semantic = AsyncSemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )

        self._sentinel = Sentinel(seed_level=seed_level)
        self._check_history: deque = deque(maxlen=history_limit)

    def _validate_text_size(self, text: str, field_name: str = "text") -> None:
        """Validate that text is a valid string and doesn't exceed maximum size."""
        if text is None:
            raise ValueError(f"{field_name} cannot be None")
        if not isinstance(text, str):
            raise TypeError(f"{field_name} must be a string, got {type(text).__name__}")
        size = len(text.encode("utf-8"))
        if size > self.max_text_size:
            raise TextTooLargeError(size, self.max_text_size)

    async def validate_action(
        self,
        action: str,
        purpose: str = "",
    ) -> ValidationResult:
        """Async validate an agent action."""
        try:
            self._validate_text_size(action, "action")
            if purpose:
                self._validate_text_size(purpose, "purpose")

            # Async validation with timeout
            thsp_result = await asyncio.wait_for(
                self._semantic.validate_action(
                    action_name=action,
                    purpose=purpose,
                ),
                timeout=self.validation_timeout,
            )

            result = ValidationResult.from_thsp(thsp_result, action)

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except asyncio.TimeoutError:
            raise ValidationTimeoutError(self.validation_timeout)
        except Exception as e:
            logger.error(f"[SENTINEL] Async validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(action, e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=action[:100],
                    concerns=[f"Validation error (fail-open): {str(e)}"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning=f"Validation encountered error but fail_closed=False: {str(e)}",
                    gate_results={},
                )

        if self.log_checks:
            self._check_history.append(result)
            if not result.should_proceed:
                logger.warning(f"[SENTINEL] Action blocked: {result.reasoning}")

        return result

    async def validate_thought(self, thought: str) -> ValidationResult:
        """Async validate agent thoughts."""
        try:
            self._validate_text_size(thought, "thought")

            thsp_result = await asyncio.wait_for(
                self._semantic.validate(f"Agent thought: {thought}"),
                timeout=self.validation_timeout,
            )
            result = ValidationResult.from_thsp(thsp_result, f"thought: {thought[:50]}...")

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except asyncio.TimeoutError:
            raise ValidationTimeoutError(self.validation_timeout)
        except Exception as e:
            logger.error(f"[SENTINEL] Async thought validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"thought: {thought[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"thought: {thought[:50]}...",
                    concerns=[f"Validation error (fail-open): {str(e)}"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning=f"Validation encountered error but fail_closed=False: {str(e)}",
                    gate_results={},
                )

        if self.log_checks:
            self._check_history.append(result)

        return result

    async def validate_output(self, output: str) -> ValidationResult:
        """Async validate agent output."""
        try:
            self._validate_text_size(output, "output")

            thsp_result = await asyncio.wait_for(
                self._semantic.validate(f"Agent output to user: {output}"),
                timeout=self.validation_timeout,
            )
            result = ValidationResult.from_thsp(thsp_result, f"output: {output[:50]}...")

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except asyncio.TimeoutError:
            raise ValidationTimeoutError(self.validation_timeout)
        except Exception as e:
            logger.error(f"[SENTINEL] Async output validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"output: {output[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"output: {output[:50]}...",
                    concerns=[f"Validation error (fail-open): {str(e)}"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning=f"Validation encountered error but fail_closed=False: {str(e)}",
                    gate_results={},
                )

        if self.log_checks:
            self._check_history.append(result)

        return result

    def get_seed(self) -> str:
        """Get Sentinel seed for injection."""
        return self._sentinel.get_seed()

    def get_history(self) -> List[ValidationResult]:
        """Get history of safety checks (returns a copy)."""
        return list(self._check_history)

    def clear_history(self) -> None:
        """Clear check history."""
        self._check_history.clear()

    @property
    def check_history(self) -> List[ValidationResult]:
        """Backward-compatible property for check_history."""
        return list(self._check_history)

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        history = list(self._check_history)
        if not history:
            return {"total_checks": 0}

        blocked = sum(1 for c in history if not c.should_proceed)
        return {
            "total_checks": len(history),
            "blocked": blocked,
            "allowed": len(history) - blocked,
            "block_rate": blocked / len(history) if history else 0,
            "history_limit": self.history_limit,
            "max_text_size": self.max_text_size,
            "validation_timeout": self.validation_timeout,
            "fail_closed": self.fail_closed,
        }


class ExecutionGuard:
    """
    Execution guard for protecting function calls with semantic validation.

    Example:
        guard = ExecutionGuard(provider="openai")

        @guard.protected
        def execute_command(command: str):
            # Your command execution logic
            return result

        result = execute_command("list files")  # Validated before running
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        block_unsafe: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        action_extractor: Optional[Callable[..., str]] = None,
    ):
        """
        Initialize execution guard.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            block_unsafe: Whether to block unsafe actions
            max_text_size: Maximum text size in bytes
            validation_timeout: Timeout for validation in seconds
            fail_closed: If True, validation errors result in blocking
            action_extractor: Custom function to extract action from args/kwargs
        """
        self.validator = SafetyValidator(
            provider=provider,
            model=model,
            api_key=api_key,
            block_unsafe=block_unsafe,
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            fail_closed=fail_closed,
        )
        self._action_extractor = action_extractor

    def _extract_action(self, args: tuple, kwargs: dict) -> str:
        """
        Extract action description from function arguments.

        Uses custom extractor if provided, otherwise uses smart extraction.
        """
        if self._action_extractor:
            return self._action_extractor(*args, **kwargs)

        # Smart extraction: try common patterns
        if args:
            first_arg = args[0]
            # Handle string directly
            if isinstance(first_arg, str):
                return first_arg
            # Handle dict with common keys
            if isinstance(first_arg, dict):
                for key in ("action", "command", "query", "text", "message", "content"):
                    if key in first_arg:
                        return str(first_arg[key])
                return str(first_arg)
            # Handle objects with common attributes
            for attr in ("action", "command", "query", "text", "message", "content"):
                if hasattr(first_arg, attr):
                    return str(getattr(first_arg, attr))
            return str(first_arg)

        # Try kwargs with common keys
        for key in ("action", "command", "query", "text", "message", "content"):
            if key in kwargs:
                return str(kwargs[key])

        # Fallback: stringify kwargs
        return str(kwargs) if kwargs else "unknown_action"

    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with semantic validation.

        Args:
            func: Function to protect

        Returns:
            Protected function that validates before execution
        """

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Validate original input before extraction
            if args:
                first_arg = args[0]
                if first_arg is None:
                    return {
                        "success": False,
                        "blocked": True,
                        "reason": "action cannot be None",
                        "error_type": "ValueError",
                    }
                # Only reject if not a supported type (string, dict, or object with action attr)
                if not isinstance(first_arg, (str, dict)) and not hasattr(first_arg, 'action'):
                    return {
                        "success": False,
                        "blocked": True,
                        "reason": f"action must be string, dict, or object with action attribute, got {type(first_arg).__name__}",
                        "error_type": "TypeError",
                    }

            # Extract action using smart extraction
            action = self._extract_action(args, kwargs)

            # Pre-validation
            try:
                check = self.validator.validate_action(action)
            except (TextTooLargeError, ValidationTimeoutError, ValueError, TypeError) as e:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": str(e),
                    "error_type": type(e).__name__,
                }

            if not check.should_proceed:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": check.reasoning,
                    "concerns": check.concerns,
                    "gate_results": check.gate_results,
                }

            # Execute the function
            result = func(*args, **kwargs)

            # Post-validation for string outputs
            if isinstance(result, str):
                try:
                    output_check = self.validator.validate_output(result)
                except (TextTooLargeError, ValidationTimeoutError) as e:
                    return {
                        "success": False,
                        "blocked": True,
                        "reason": str(e),
                        "error_type": type(e).__name__,
                        "original_output": result[:100],
                    }

                if not output_check.should_proceed:
                    return {
                        "success": False,
                        "blocked": True,
                        "reason": output_check.reasoning,
                        "original_output": result[:100],
                    }

            return result

        return wrapper

    def check(self, action: str) -> ValidationResult:
        """Check an action without executing."""
        return self.validator.validate_action(action)

    def get_stats(self) -> Dict[str, Any]:
        """Get guard statistics."""
        return self.validator.get_stats()


def safety_check(
    action: str,
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
) -> Dict[str, Any]:
    """
    Standalone safety check function using semantic analysis.

    Args:
        action: Action to validate
        provider: LLM provider ("openai" or "anthropic")
        model: Model to use
        api_key: API key
        max_text_size: Maximum text size in bytes
        validation_timeout: Timeout for validation in seconds

    Returns:
        Dict with safe, concerns, risk_level, reasoning, gate_results

    Example:
        result = safety_check("Delete all files in /tmp", provider="openai")
        if not result["safe"]:
            print(f"Blocked: {result['reasoning']}")
    """
    validator = SafetyValidator(
        provider=provider,
        model=model,
        api_key=api_key,
        log_checks=False,
        max_text_size=max_text_size,
        validation_timeout=validation_timeout,
    )

    result = validator.validate_action(action)

    return {
        "safe": result.safe,
        "concerns": result.concerns,
        "risk_level": result.risk_level,
        "action": result.action,
        "reasoning": result.reasoning,
        "gate_results": result.gate_results,
        "should_proceed": result.should_proceed,
    }


# Aliases for backward compatibility
SafetyCheckResult = ValidationResult
SentinelSafetyComponent = SafetyValidator
SentinelGuard = ExecutionGuard


__all__ = [
    # Main classes
    "ValidationResult",
    "SafetyValidator",
    "AsyncSafetyValidator",
    "ExecutionGuard",
    "safety_check",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
    "InvalidProviderError",
    # Constants
    "VALID_PROVIDERS",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_HISTORY_LIMIT",
    "DEFAULT_VALIDATION_TIMEOUT",
    # Backward compatibility
    "SafetyCheckResult",
    "SentinelSafetyComponent",
    "SentinelGuard",
]
