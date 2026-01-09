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
    THSPResult,
    RiskLevel,
)
from sentinelseed.validation import (
    LayeredValidator,
    AsyncLayeredValidator,
    ValidationConfig,
    ValidationResult as LayeredValidationResult,
)
from sentinelseed.integrations._base import SentinelIntegration, AsyncSentinelIntegration

logger = logging.getLogger("sentinelseed.agent_validation")

# Version
__version__ = "2.23.1"

# Valid providers
VALID_PROVIDERS = ("openai", "anthropic")

# Valid seed levels
VALID_SEED_LEVELS = ("minimal", "standard", "full")

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


class SafetyValidator(SentinelIntegration):
    """
    Core safety validation component using semantic LLM analysis.

    Uses THSP Protocol (Truth, Harm, Scope, Purpose) with real LLM
    semantic analysis - not regex pattern matching.

    Inherits from SentinelIntegration for standardized validation via
    LayeredValidator.

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

    _integration_name = "agent_validation"
    name = "SentinelSafetyValidator"
    description = "AI safety validation using semantic THSP analysis"

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        seed_level: str = "standard",
        log_checks: bool = True,
        record_history: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        use_layered: bool = True,
        use_heuristic: bool = True,
        validator: Optional[LayeredValidator] = None,
        # Deprecated parameter - kept for backward compatibility
        block_unsafe: Optional[bool] = None,
    ):
        """
        Initialize the safety validator.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            seed_level: Seed level for seed injection ("minimal", "standard", "full")
            log_checks: Whether to log safety checks to console
            record_history: Whether to record validations in history (default: True)
            max_text_size: Maximum text size in bytes (default: 50KB)
            history_limit: Maximum history entries (default: 1000, must be >= 0)
            validation_timeout: Timeout for validation in seconds (default: 30)
            fail_closed: If True, validation errors result in blocking (default: False)
            use_layered: Use LayeredValidator (heuristic + semantic) (default: True)
            use_heuristic: Enable heuristic validation in layered mode (default: True)
            validator: Optional LayeredValidator for dependency injection (testing)
            block_unsafe: DEPRECATED - This parameter is ignored. Will be removed in v3.0.

        Raises:
            InvalidProviderError: If provider is not valid
            ValueError: If seed_level, validation_timeout, max_text_size, or history_limit are invalid
        """
        # Deprecation warning for block_unsafe
        if block_unsafe is not None:
            import warnings
            warnings.warn(
                "block_unsafe parameter is deprecated and ignored. "
                "It will be removed in v3.0. All unsafe actions are always blocked.",
                DeprecationWarning,
                stacklevel=2,
            )
        # Validate provider
        if provider not in VALID_PROVIDERS:
            raise InvalidProviderError(provider)

        # Validate seed_level
        if seed_level not in VALID_SEED_LEVELS:
            raise ValueError(
                f"Invalid seed_level '{seed_level}'. Must be one of: {', '.join(VALID_SEED_LEVELS)}"
            )

        # Validate parameters
        if validation_timeout <= 0:
            raise ValueError("validation_timeout must be positive")
        if max_text_size <= 0:
            raise ValueError("max_text_size must be positive")
        if history_limit < 0:
            raise ValueError("history_limit must be non-negative")

        # Create LayeredValidator if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=use_heuristic,
                use_semantic=bool(api_key),
                semantic_provider=provider,
                semantic_model=model,
                semantic_api_key=api_key,
                max_text_size=max_text_size,
                validation_timeout=validation_timeout,
                fail_closed=fail_closed,
            )
            validator = LayeredValidator(config=config)

        # Initialize SentinelIntegration
        super().__init__(validator=validator)

        self.provider = provider
        self.model = model
        self.log_checks = log_checks
        self.record_history = record_history
        self._seed_level = seed_level  # Use _seed_level (inherited property is read-only)
        self.max_text_size = max_text_size
        self.history_limit = history_limit
        self.validation_timeout = validation_timeout
        self.fail_closed = fail_closed
        self.use_layered = use_layered
        self.use_heuristic = use_heuristic

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
        Validate an agent action using LayeredValidator or semantic LLM analysis.

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

            # Combine action and purpose for validation
            content = f"{action} {purpose}".strip() if purpose else action

            # Use LayeredValidator for validation
            layered_result = self._validator.validate(content)
            result = ValidationResult(
                safe=layered_result.is_safe,
                action=action[:100],
                concerns=layered_result.violations,
                risk_level=layered_result.risk_level.value,
                should_proceed=layered_result.is_safe,
                reasoning=layered_result.reasoning or "",
                gate_results={"layer": layered_result.layer.value},
            )

        except (TextTooLargeError, ValidationTimeoutError, ValueError, TypeError):
            # Re-raise validation errors (input validation, size, timeout)
            raise
        except (RuntimeError, AttributeError, ConnectionError, OSError) as e:
            logger.error(f"[SENTINEL] Validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(action, e)
            else:
                # Fail open: allow but log warning
                result = ValidationResult(
                    safe=True,
                    action=action[:100],
                    concerns=["Validation error (fail-open)"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning="Validation encountered error but fail_closed=False",
                    gate_results={},
                )

        # Record history if enabled (separate from logging)
        if self.record_history:
            self._check_history.append(result)

        # Log warning if enabled and action blocked
        if self.log_checks and not result.should_proceed:
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

            # Use LayeredValidator for validation
            content = f"Agent thought: {thought}"
            layered_result = self._validator.validate(content)
            result = ValidationResult(
                safe=layered_result.is_safe,
                action=f"thought: {thought[:50]}...",
                concerns=layered_result.violations,
                risk_level=layered_result.risk_level.value,
                should_proceed=layered_result.is_safe,
                reasoning=layered_result.reasoning or "",
                gate_results={"layer": layered_result.layer.value},
            )

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except (RuntimeError, AttributeError, ConnectionError, OSError) as e:
            logger.error(f"[SENTINEL] Thought validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"thought: {thought[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"thought: {thought[:50]}...",
                    concerns=["Validation error (fail-open)"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning="Validation encountered error but fail_closed=False",
                    gate_results={},
                )

        # Record history if enabled
        if self.record_history:
            self._check_history.append(result)

        # Log warning if enabled and blocked
        if self.log_checks and not result.should_proceed:
            logger.warning(f"[SENTINEL] Thought blocked: {result.reasoning}")

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

            # Use LayeredValidator for validation
            content = f"Agent output to user: {output}"
            layered_result = self._validator.validate(content)
            result = ValidationResult(
                safe=layered_result.is_safe,
                action=f"output: {output[:50]}...",
                concerns=layered_result.violations,
                risk_level=layered_result.risk_level.value,
                should_proceed=layered_result.is_safe,
                reasoning=layered_result.reasoning or "",
                gate_results={"layer": layered_result.layer.value},
            )

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except (RuntimeError, AttributeError, ConnectionError, OSError) as e:
            logger.error(f"[SENTINEL] Output validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"output: {output[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"output: {output[:50]}...",
                    concerns=["Validation error (fail-open)"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning="Validation encountered error but fail_closed=False",
                    gate_results={},
                )

        # Record history if enabled
        if self.record_history:
            self._check_history.append(result)

        # Log warning if enabled and blocked
        if self.log_checks and not result.should_proceed:
            logger.warning(f"[SENTINEL] Output blocked: {result.reasoning}")

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

        return {
            "total_checks": len(history),
            "blocked": blocked,
            "allowed": len(history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(history) if history else 0,
            "provider": self.provider,
            "model": self.model,
            "seed_level": self.seed_level,
            "history_limit": self.history_limit,
            "max_text_size": self.max_text_size,
            "validation_timeout": self.validation_timeout,
            "fail_closed": self.fail_closed,
            "use_layered": self.use_layered,
            "use_heuristic": self.use_heuristic,
        }


class AsyncSafetyValidator(AsyncSentinelIntegration):
    """
    Async version of SafetyValidator for use with async frameworks.

    Inherits from AsyncSentinelIntegration for standardized async validation.

    Example:
        validator = AsyncSafetyValidator(provider="openai")
        result = await validator.validate_action("transfer funds")
    """

    _integration_name = "agent_validation_async"

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        seed_level: str = "standard",
        log_checks: bool = True,
        record_history: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        history_limit: int = DEFAULT_HISTORY_LIMIT,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        use_layered: bool = True,
        use_heuristic: bool = True,
        validator: Optional[AsyncLayeredValidator] = None,
        # Deprecated parameter - kept for backward compatibility
        block_unsafe: Optional[bool] = None,
    ):
        """
        Initialize the async safety validator.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            seed_level: Seed level for seed injection ("minimal", "standard", "full")
            log_checks: Whether to log safety checks to console
            record_history: Whether to record validations in history (default: True)
            max_text_size: Maximum text size in bytes (default: 50KB)
            history_limit: Maximum history entries (default: 1000, must be >= 0)
            validation_timeout: Timeout for validation in seconds (default: 30)
            fail_closed: If True, validation errors result in blocking (default: False)
            use_layered: Use LayeredValidator (heuristic + semantic) (default: True)
            use_heuristic: Enable heuristic validation in layered mode (default: True)
            validator: Optional AsyncLayeredValidator for dependency injection (testing)
            block_unsafe: DEPRECATED - This parameter is ignored. Will be removed in v3.0.

        Raises:
            InvalidProviderError: If provider is not valid
            ValueError: If seed_level, validation_timeout, max_text_size, or history_limit are invalid
        """
        # Deprecation warning for block_unsafe
        if block_unsafe is not None:
            import warnings
            warnings.warn(
                "block_unsafe parameter is deprecated and ignored. "
                "It will be removed in v3.0. All unsafe actions are always blocked.",
                DeprecationWarning,
                stacklevel=2,
            )

        # Validate provider
        if provider not in VALID_PROVIDERS:
            raise InvalidProviderError(provider)

        # Validate seed_level
        if seed_level not in VALID_SEED_LEVELS:
            raise ValueError(
                f"Invalid seed_level '{seed_level}'. Must be one of: {', '.join(VALID_SEED_LEVELS)}"
            )

        # Validate parameters
        if validation_timeout <= 0:
            raise ValueError("validation_timeout must be positive")
        if max_text_size <= 0:
            raise ValueError("max_text_size must be positive")
        if history_limit < 0:
            raise ValueError("history_limit must be non-negative")

        # Create AsyncLayeredValidator if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=use_heuristic,
                use_semantic=bool(api_key),
                semantic_provider=provider,
                semantic_model=model,
                semantic_api_key=api_key,
                validation_timeout=validation_timeout,
                fail_closed=fail_closed,
                max_text_size=max_text_size,
            )
            validator = AsyncLayeredValidator(config=config)

        # Initialize AsyncSentinelIntegration
        super().__init__(validator=validator)

        self.provider = provider
        self.model = model
        self.log_checks = log_checks
        self.record_history = record_history
        self._seed_level = seed_level  # Use _seed_level (inherited property is read-only)
        self.max_text_size = max_text_size
        self.history_limit = history_limit
        self.validation_timeout = validation_timeout
        self.fail_closed = fail_closed
        self.use_layered = use_layered
        self.use_heuristic = use_heuristic

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
        """Async validate an agent action using inherited AsyncLayeredValidator."""
        try:
            self._validate_text_size(action, "action")
            if purpose:
                self._validate_text_size(purpose, "purpose")

            # Combine action and purpose for validation (matches sync behavior)
            content = f"{action} {purpose}".strip() if purpose else action

            # Use inherited async validate method from AsyncSentinelIntegration
            layered_result = await asyncio.wait_for(
                self.avalidate(content),
                timeout=self.validation_timeout,
            )

            # Convert LayeredValidationResult to agent_validation.ValidationResult
            result = ValidationResult(
                safe=layered_result.is_safe,
                action=action[:100],
                concerns=layered_result.violations,
                risk_level=layered_result.risk_level.value if hasattr(layered_result.risk_level, 'value') else str(layered_result.risk_level),
                should_proceed=layered_result.is_safe,
                reasoning="; ".join(layered_result.violations) if layered_result.violations else "Action passed validation",
                gate_results=layered_result.details.get("gate_results", {}) if hasattr(layered_result, 'details') and layered_result.details else {},
            )

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except asyncio.TimeoutError:
            raise ValidationTimeoutError(self.validation_timeout)
        except asyncio.CancelledError:
            # Re-raise cancellation - should not be caught
            raise
        except (RuntimeError, AttributeError, ConnectionError, OSError) as e:
            logger.error(f"[SENTINEL] Async validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(action, e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=action[:100],
                    concerns=["Validation error (fail-open)"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning="Validation encountered error but fail_closed=False",
                    gate_results={},
                )

        # Record history if enabled (separate from logging)
        if self.record_history:
            self._check_history.append(result)

        # Log warning if enabled and action blocked
        if self.log_checks and not result.should_proceed:
            logger.warning(f"[SENTINEL] Action blocked: {result.reasoning}")

        return result

    async def validate_thought(self, thought: str) -> ValidationResult:
        """Async validate agent thoughts using inherited AsyncLayeredValidator."""
        try:
            self._validate_text_size(thought, "thought")

            # Use inherited async validate method
            layered_result = await asyncio.wait_for(
                self.avalidate(f"Agent thought: {thought}"),
                timeout=self.validation_timeout,
            )

            # Convert to agent_validation.ValidationResult
            result = ValidationResult(
                safe=layered_result.is_safe,
                action=f"thought: {thought[:50]}...",
                concerns=layered_result.violations,
                risk_level=layered_result.risk_level.value if hasattr(layered_result.risk_level, 'value') else str(layered_result.risk_level),
                should_proceed=layered_result.is_safe,
                reasoning="; ".join(layered_result.violations) if layered_result.violations else "Thought passed validation",
                gate_results=layered_result.details.get("gate_results", {}) if hasattr(layered_result, 'details') and layered_result.details else {},
            )

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except asyncio.TimeoutError:
            raise ValidationTimeoutError(self.validation_timeout)
        except asyncio.CancelledError:
            raise
        except (RuntimeError, AttributeError, ConnectionError, OSError) as e:
            logger.error(f"[SENTINEL] Async thought validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"thought: {thought[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"thought: {thought[:50]}...",
                    concerns=["Validation error (fail-open)"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning="Validation encountered error but fail_closed=False",
                    gate_results={},
                )

        # Record history if enabled
        if self.record_history:
            self._check_history.append(result)

        # Log warning if enabled and blocked
        if self.log_checks and not result.should_proceed:
            logger.warning(f"[SENTINEL] Thought blocked: {result.reasoning}")

        return result

    async def validate_output(self, output: str) -> ValidationResult:
        """Async validate agent output using inherited AsyncLayeredValidator."""
        try:
            self._validate_text_size(output, "output")

            # Use inherited async validate method
            layered_result = await asyncio.wait_for(
                self.avalidate(f"Agent output to user: {output}"),
                timeout=self.validation_timeout,
            )

            # Convert to agent_validation.ValidationResult
            result = ValidationResult(
                safe=layered_result.is_safe,
                action=f"output: {output[:50]}...",
                concerns=layered_result.violations,
                risk_level=layered_result.risk_level.value if hasattr(layered_result.risk_level, 'value') else str(layered_result.risk_level),
                should_proceed=layered_result.is_safe,
                reasoning="; ".join(layered_result.violations) if layered_result.violations else "Output passed validation",
                gate_results=layered_result.details.get("gate_results", {}) if hasattr(layered_result, 'details') and layered_result.details else {},
            )

        except (TextTooLargeError, ValueError, TypeError):
            raise
        except asyncio.TimeoutError:
            raise ValidationTimeoutError(self.validation_timeout)
        except asyncio.CancelledError:
            raise
        except (RuntimeError, AttributeError, ConnectionError, OSError) as e:
            logger.error(f"[SENTINEL] Async output validation error: {e}")
            if self.fail_closed:
                result = ValidationResult.error_result(f"output: {output[:50]}...", e)
            else:
                result = ValidationResult(
                    safe=True,
                    action=f"output: {output[:50]}...",
                    concerns=["Validation error (fail-open)"],
                    risk_level="medium",
                    should_proceed=True,
                    reasoning="Validation encountered error but fail_closed=False",
                    gate_results={},
                )

        # Record history if enabled
        if self.record_history:
            self._check_history.append(result)

        # Log warning if enabled and blocked
        if self.log_checks and not result.should_proceed:
            logger.warning(f"[SENTINEL] Output blocked: {result.reasoning}")

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
        high_risk = sum(1 for c in history if c.risk_level == "high")

        return {
            "total_checks": len(history),
            "blocked": blocked,
            "allowed": len(history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(history) if history else 0,
            "provider": self.provider,
            "model": self.model,
            "seed_level": self.seed_level,
            "history_limit": self.history_limit,
            "max_text_size": self.max_text_size,
            "validation_timeout": self.validation_timeout,
            "fail_closed": self.fail_closed,
            "use_layered": self.use_layered,
            "use_heuristic": self.use_heuristic,
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
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        action_extractor: Optional[Callable[..., str]] = None,
        # Deprecated parameter - kept for backward compatibility
        block_unsafe: Optional[bool] = None,
    ):
        """
        Initialize execution guard.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            max_text_size: Maximum text size in bytes
            validation_timeout: Timeout for validation in seconds
            fail_closed: If True, validation errors result in blocking
            action_extractor: Custom function to extract action from args/kwargs
            block_unsafe: DEPRECATED - This parameter is ignored. Will be removed in v3.0.
        """
        # Deprecation warning for block_unsafe
        if block_unsafe is not None:
            import warnings
            warnings.warn(
                "block_unsafe parameter is deprecated and ignored. "
                "It will be removed in v3.0. All unsafe actions are always blocked.",
                DeprecationWarning,
                stacklevel=2,
            )

        self.validator = SafetyValidator(
            provider=provider,
            model=model,
            api_key=api_key,
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
    # Version
    "__version__",
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
    "VALID_SEED_LEVELS",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_HISTORY_LIMIT",
    "DEFAULT_VALIDATION_TIMEOUT",
    # Backward compatibility
    "SafetyCheckResult",
    "SentinelSafetyComponent",
    "SentinelGuard",
]
