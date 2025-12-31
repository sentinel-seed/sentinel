"""Sentinel guardrails for Agno AI agents.

This module provides THSP-based guardrails that integrate natively with
Agno's guardrail system. The guardrails validate inputs and outputs
against the Truth, Harm, Scope, and Purpose gates.

Classes:
    SentinelGuardrail: Input validation guardrail (pre_hook).
    SentinelOutputGuardrail: Output validation guardrail.

Example:
    from sentinelseed.integrations.agno import SentinelGuardrail
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    agent = Agent(
        name="Safe Agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        pre_hooks=[SentinelGuardrail()],
    )

    response = agent.run("Hello, how can you help me?")

Note:
    SentinelGuardrail extends Agno's BaseGuardrail class, providing native
    integration with Agno's agent lifecycle. It is designed to work
    alongside Agno's built-in guardrails (PII, prompt injection, etc.).
"""

from __future__ import annotations

import time
import threading
from typing import TYPE_CHECKING, Any

from .utils import (
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_SEED_LEVEL,
    DEFAULT_VALIDATION_TIMEOUT,
    ConfigurationError,
    TextTooLargeError,
    ThreadSafeDeque,
    ValidationTimeoutError,
    create_empty_stats,
    extract_content,
    format_violation,
    get_logger,
    get_validation_executor,
    log_fail_open_warning,
    validate_configuration,
    validate_text_size,
)

if TYPE_CHECKING:
    from sentinelseed import Sentinel

# Try to import Agno dependencies at module level
# This determines the base class for SentinelGuardrail
try:
    from agno.exceptions import CheckTrigger, InputCheckError, OutputCheckError
    from agno.guardrails import BaseGuardrail

    _AGNO_AVAILABLE = True
    _BASE_CLASS = BaseGuardrail
except ImportError:
    _AGNO_AVAILABLE = False
    _BASE_CLASS = object  # Fallback for type checking only
    BaseGuardrail = None
    InputCheckError = None
    OutputCheckError = None
    CheckTrigger = None


_logger = get_logger("guardrails")


def _require_agno() -> None:
    """Verify Agno is installed, raising ImportError if not.

    Raises:
        ImportError: If Agno is not installed.
    """
    if not _AGNO_AVAILABLE:
        raise ImportError(
            "Agno is required for this integration. "
            "Install it with: pip install agno"
        )


class SentinelGuardrail(_BASE_CLASS):
    """Sentinel THSP guardrail for Agno agents.

    This guardrail validates inputs against the THSP protocol (Truth, Harm,
    Scope, Purpose) before they are processed by the LLM. It inherits from
    Agno's BaseGuardrail to integrate natively with Agno's agent lifecycle.

    The guardrail performs layered validation:
    1. Size check (fast, prevents resource exhaustion)
    2. THSP validation with timeout protection
    3. Gate analysis and violation recording

    Attributes:
        sentinel: The Sentinel instance used for validation.
        seed_level: The safety level being used.
        block_on_failure: Whether unsafe content is blocked.
        fail_closed: Whether validation errors cause blocking.

    Example:
        from sentinelseed.integrations.agno import SentinelGuardrail
        from agno.agent import Agent

        # Basic usage
        guardrail = SentinelGuardrail()
        agent = Agent(name="Safe", model=model, pre_hooks=[guardrail])

        # With custom configuration
        guardrail = SentinelGuardrail(
            seed_level="full",
            block_on_failure=True,
            fail_closed=True,
            max_text_size=50000,
        )

        # Access violation records
        violations = guardrail.get_violations()
        stats = guardrail.get_stats()

    Note:
        By default, fail_closed=False (fail-open mode). This means
        validation errors (timeouts, exceptions) will allow content
        through with a warning. For security-critical applications,
        set fail_closed=True.
    """

    def __init__(
        self,
        sentinel: Sentinel | None = None,
        seed_level: str = DEFAULT_SEED_LEVEL,
        block_on_failure: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        log_violations: bool = True,
    ) -> None:
        """Initialize the Sentinel guardrail.

        Args:
            sentinel: Optional Sentinel instance. If not provided, a new
                instance is created with the specified seed_level.
            seed_level: Safety level for the seed. One of 'minimal',
                'standard', or 'full'. Defaults to 'standard'.
            block_on_failure: If True, raises InputCheckError when THSP
                validation fails. If False, logs warnings but allows
                content. Defaults to True.
            max_text_size: Maximum input size in bytes. Inputs exceeding
                this limit are blocked immediately. Defaults to 100,000.
            validation_timeout: Maximum time in seconds for THSP validation.
                Defaults to 5.0 seconds.
            fail_closed: If True, validation errors (timeouts, exceptions)
                cause content to be blocked. If False (default), errors
                are logged and content is allowed (fail-open).
            log_violations: If True, violations are recorded and available
                via get_violations(). Defaults to True.

        Raises:
            ConfigurationError: If any configuration parameter is invalid.
            ImportError: If Agno is not installed.

        Note:
            The fail_closed parameter represents a security vs. availability
            trade-off. The default (False) prioritizes availability. Set to
            True for security-critical applications.
        """
        # Verify Agno is installed before proceeding
        _require_agno()

        # Call parent class __init__ if it exists
        if hasattr(super(), "__init__"):
            super().__init__()

        # Validate configuration before storing
        validate_configuration(
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            seed_level=seed_level,
            fail_closed=fail_closed,
            block_on_failure=block_on_failure,
            log_violations=log_violations,
        )

        # Initialize Sentinel
        if sentinel is not None:
            self._sentinel = sentinel
        else:
            from sentinelseed import Sentinel

            self._sentinel = Sentinel(seed_level=seed_level)

        # Store configuration
        self._seed_level = seed_level.lower()
        self._block_on_failure = block_on_failure
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed
        self._log_violations = log_violations

        # Initialize tracking
        self._violations = ThreadSafeDeque()
        self._stats = create_empty_stats()
        self._stats_lock = threading.Lock()

        # Log fail-open warning if applicable
        if not fail_closed:
            log_fail_open_warning("SentinelGuardrail")

        _logger.debug(
            "SentinelGuardrail initialized: seed_level=%s, block=%s, fail_closed=%s",
            seed_level,
            block_on_failure,
            fail_closed,
        )

    @property
    def sentinel(self) -> Sentinel:
        """The Sentinel instance used for validation."""
        return self._sentinel

    @property
    def seed_level(self) -> str:
        """The safety level being used."""
        return self._seed_level

    @property
    def block_on_failure(self) -> bool:
        """Whether unsafe content is blocked."""
        return self._block_on_failure

    @property
    def fail_closed(self) -> bool:
        """Whether validation errors cause blocking."""
        return self._fail_closed

    def check(self, run_input: Any) -> None:
        """Validate input against THSP protocol (synchronous).

        This method is called by Agno before the input is sent to the LLM.
        It performs layered validation:

        1. Extract text content from RunInput
        2. Check text size (fast, prevents resource exhaustion)
        3. Run THSP validation with timeout protection
        4. Analyze gate results and record violations

        Args:
            run_input: Agno RunInput object containing the input to validate.

        Raises:
            InputCheckError: When input fails THSP validation and
                block_on_failure=True. Contains a descriptive message
                and CheckTrigger.INPUT_NOT_ALLOWED.

        Note:
            This method is called automatically by Agno when the guardrail
            is attached as a pre_hook. Do not call directly unless testing.
        """
        start_time = time.perf_counter()

        try:
            # Extract content
            content = extract_content(run_input)
            if content is None or content.strip() == "":
                _logger.debug("Empty or None content, skipping validation")
                self._update_stats(allowed=True, validation_time=0.0)
                return

            # Perform validation
            result = self._validate_content(content)

            # Calculate validation time
            validation_time = (time.perf_counter() - start_time) * 1000

            if result is None:
                # Content is safe
                self._update_stats(allowed=True, validation_time=validation_time)
                return

            # Content was blocked
            self._update_stats(
                allowed=False,
                validation_time=validation_time,
                gate_failures=result.get("gate_failures"),
            )

            if self._block_on_failure:
                self._raise_input_check_error(result)

        except Exception as e:
            # Handle unexpected errors
            if InputCheckError is not None and isinstance(e, InputCheckError):
                raise

            validation_time = (time.perf_counter() - start_time) * 1000
            _logger.error("Unexpected error during validation: %s", e)
            self._update_stats(error=True, validation_time=validation_time)

            if self._fail_closed and self._block_on_failure:
                self._raise_input_check_error({
                    "reason": f"Validation error: {e}",
                    "concerns": [str(e)],
                    "risk_level": "unknown",
                })

    async def async_check(self, run_input: Any) -> None:
        """Validate input against THSP protocol (asynchronous).

        This is the async version of check(). Agno automatically calls
        this method when using agent.arun() instead of agent.run().

        The validation logic is identical to check(), but runs in an
        async-compatible way using asyncio.to_thread for CPU-bound
        THSP validation.

        Args:
            run_input: Agno RunInput object containing the input to validate.

        Raises:
            InputCheckError: When input fails THSP validation and
                block_on_failure=True.

        Note:
            The actual THSP validation is CPU-bound and runs in a thread
            pool to avoid blocking the event loop.
        """
        import asyncio

        start_time = time.perf_counter()

        try:
            # Extract content
            content = extract_content(run_input)
            if content is None or content.strip() == "":
                _logger.debug("Empty or None content, skipping validation")
                self._update_stats(allowed=True, validation_time=0.0)
                return

            # Run validation in thread pool to avoid blocking event loop
            result = await asyncio.to_thread(self._validate_content, content)

            # Calculate validation time
            validation_time = (time.perf_counter() - start_time) * 1000

            if result is None:
                # Content is safe
                self._update_stats(allowed=True, validation_time=validation_time)
                return

            # Content was blocked
            self._update_stats(
                allowed=False,
                validation_time=validation_time,
                gate_failures=result.get("gate_failures"),
            )

            if self._block_on_failure:
                self._raise_input_check_error(result)

        except Exception as e:
            if InputCheckError is not None and isinstance(e, InputCheckError):
                raise

            validation_time = (time.perf_counter() - start_time) * 1000
            _logger.error("Unexpected error during async validation: %s", e)
            self._update_stats(error=True, validation_time=validation_time)

            if self._fail_closed and self._block_on_failure:
                self._raise_input_check_error({
                    "reason": f"Validation error: {e}",
                    "concerns": [str(e)],
                    "risk_level": "unknown",
                })

    def _validate_content(self, content: str) -> dict[str, Any] | None:
        """Internal method to validate content.

        This method implements the layered validation logic:
        1. Size check (fast)
        2. THSP validation with timeout
        3. Result analysis

        Args:
            content: The text content to validate.

        Returns:
            None if content is safe, or a dict with violation details.
        """
        # Layer 1: Size check (fast, no external calls)
        try:
            validate_text_size(content, self._max_text_size, "input")
        except TextTooLargeError as e:
            _logger.warning("Input exceeds size limit: %s", e)
            return {
                "reason": str(e),
                "concerns": [f"Text too large: {e.size:,} bytes"],
                "risk_level": "high",
                "gate_failures": {},
            }

        # Layer 2: THSP validation with timeout
        try:
            executor = get_validation_executor()
            check_result = executor.run_with_timeout(
                fn=self._sentinel.validate_request,
                args=(content,),
                timeout=self._validation_timeout,
            )
        except ValidationTimeoutError as e:
            _logger.warning("Validation timeout: %s", e)
            self._update_stats(timeout=True)
            if self._fail_closed:
                return {
                    "reason": str(e),
                    "concerns": ["Validation timed out"],
                    "risk_level": "unknown",
                    "gate_failures": {},
                }
            return None  # Fail-open: allow on timeout

        # Layer 3: Analyze result
        if check_result.get("should_proceed", True):
            return None  # Content is safe

        # Content is unsafe - extract details
        concerns = check_result.get("concerns", [])
        risk_level = check_result.get("risk_level", "high")

        # Extract gate failures
        gate_failures = {}
        gates = check_result.get("gates", {})
        for gate_name in ("truth", "harm", "scope", "purpose"):
            if not gates.get(gate_name, True):
                gate_failures[gate_name] = True

        # Record violation if enabled
        if self._log_violations:
            violation = format_violation(
                content=content,
                concerns=concerns,
                risk_level=risk_level,
                gates=gates,
            )
            self._violations.append(violation)

        return {
            "reason": f"THSP validation failed: {', '.join(concerns[:3])}",
            "concerns": concerns,
            "risk_level": risk_level,
            "gate_failures": gate_failures,
        }

    def _raise_input_check_error(self, result: dict[str, Any]) -> None:
        """Raise an InputCheckError with violation details.

        Args:
            result: Validation result dict with reason, concerns, etc.

        Raises:
            InputCheckError: Always raised with appropriate details.
        """
        message = result.get("reason", "Input failed Sentinel validation")
        concerns = result.get("concerns", [])
        risk_level = result.get("risk_level", "high")

        # Build detailed message
        if concerns:
            message = f"{message}\nConcerns: {', '.join(concerns[:5])}"
        message = f"{message}\nRisk level: {risk_level}"

        raise InputCheckError(
            message,
            check_trigger=CheckTrigger.INPUT_NOT_ALLOWED,
        )

    def _update_stats(
        self,
        allowed: bool | None = None,
        timeout: bool = False,
        error: bool = False,
        validation_time: float = 0.0,
        gate_failures: dict[str, bool] | None = None,
    ) -> None:
        """Update internal statistics (thread-safe).

        Args:
            allowed: Whether content was allowed (True) or blocked (False).
            timeout: Whether a timeout occurred.
            error: Whether an error occurred.
            validation_time: Validation time in milliseconds.
            gate_failures: Dict of gate names that failed.
        """
        with self._stats_lock:
            self._stats["total_validations"] += 1

            if allowed is True:
                self._stats["allowed_count"] += 1
            elif allowed is False:
                self._stats["blocked_count"] += 1

            if timeout:
                self._stats["timeout_count"] += 1
            if error:
                self._stats["error_count"] += 1

            # Update gate failure counts
            if gate_failures:
                for gate_name, failed in gate_failures.items():
                    if failed and gate_name in self._stats["gate_failures"]:
                        self._stats["gate_failures"][gate_name] += 1

            # Update average validation time (exponential moving average)
            total = self._stats["total_validations"]
            if total == 1:
                self._stats["avg_validation_time_ms"] = validation_time
            else:
                alpha = 0.1  # Smoothing factor
                self._stats["avg_validation_time_ms"] = (
                    alpha * validation_time
                    + (1 - alpha) * self._stats["avg_validation_time_ms"]
                )

    def get_violations(self) -> list[dict[str, Any]]:
        """Get list of recorded violations.

        Returns:
            List of violation dictionaries, each containing:
            - content_preview: Truncated content that was flagged
            - concerns: List of concerns identified
            - risk_level: Risk level (low, medium, high, critical)
            - gates: THSP gate results
            - timestamp: Unix timestamp

        Example:
            violations = guardrail.get_violations()
            for v in violations:
                print(f"Risk: {v['risk_level']}, Concerns: {v['concerns']}")
        """
        return self._violations.to_list()

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary containing:
            - total_validations: Total number of validations performed
            - blocked_count: Number of inputs blocked
            - allowed_count: Number of inputs allowed
            - timeout_count: Number of validation timeouts
            - error_count: Number of validation errors
            - gate_failures: Dict of failure counts per gate
            - avg_validation_time_ms: Average validation time in ms

        Example:
            stats = guardrail.get_stats()
            print(f"Block rate: {stats['blocked_count']/stats['total_validations']:.1%}")
        """
        with self._stats_lock:
            return dict(self._stats)

    def clear_violations(self) -> None:
        """Clear all recorded violations."""
        self._violations.clear()

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        with self._stats_lock:
            self._stats = create_empty_stats()


class SentinelOutputGuardrail:
    """Sentinel output guardrail for Agno agents.

    This guardrail validates LLM outputs before they are returned to the
    user. It can be called manually to validate responses, providing
    detailed validation results.

    Unlike SentinelGuardrail which raises exceptions on unsafe content,
    this guardrail returns validation results, allowing the caller to
    decide how to handle unsafe outputs.

    Note:
        This class does NOT inherit from BaseGuardrail because Agno's
        guardrail system is designed for input validation (pre_hooks).
        Output validation is typically done manually after receiving
        the agent response.

    Attributes:
        sentinel: The Sentinel instance used for validation.
        seed_level: The safety level being used.

    Example:
        from sentinelseed.integrations.agno import SentinelOutputGuardrail

        guardrail = SentinelOutputGuardrail()

        # Manual validation of agent output
        response = agent.run("Generate a story")
        result = guardrail.validate_output(response.content)

        if not result["safe"]:
            print(f"Output flagged: {result['concerns']}")

    Note:
        Output validation is typically less strict than input validation,
        as the model's output is already constrained by the system prompt
        and input validation.
    """

    def __init__(
        self,
        sentinel: Sentinel | None = None,
        seed_level: str = DEFAULT_SEED_LEVEL,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        log_violations: bool = True,
    ) -> None:
        """Initialize the output guardrail.

        Args:
            sentinel: Optional Sentinel instance. If not provided, a new
                instance is created with the specified seed_level.
            seed_level: Safety level for the seed. One of 'minimal',
                'standard', or 'full'. Defaults to 'standard'.
            max_text_size: Maximum output size in bytes. Outputs exceeding
                this limit are flagged. Defaults to 100,000.
            validation_timeout: Maximum time in seconds for validation.
                Defaults to 5.0 seconds.
            log_violations: If True, violations are recorded. Defaults to True.

        Raises:
            ConfigurationError: If any configuration parameter is invalid.
        """
        # Validate configuration
        validate_configuration(
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            seed_level=seed_level,
            fail_closed=False,  # Not used for output
            block_on_failure=True,  # Not used for output
            log_violations=log_violations,
        )

        # Initialize Sentinel
        if sentinel is not None:
            self._sentinel = sentinel
        else:
            from sentinelseed import Sentinel

            self._sentinel = Sentinel(seed_level=seed_level)

        self._seed_level = seed_level.lower()
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._log_violations = log_violations
        self._violations = ThreadSafeDeque()

        _logger.debug("SentinelOutputGuardrail initialized: seed_level=%s", seed_level)

    @property
    def sentinel(self) -> Sentinel:
        """The Sentinel instance used for validation."""
        return self._sentinel

    @property
    def seed_level(self) -> str:
        """The safety level being used."""
        return self._seed_level

    def validate_output(self, output: str | Any) -> dict[str, Any]:
        """Validate LLM output.

        This method validates the output content and returns a result
        dictionary. Unlike the input guardrail, it does not raise
        exceptions, allowing the caller to decide how to handle the result.

        Args:
            output: The output to validate. Can be a string or an object
                with a 'content' attribute.

        Returns:
            Dictionary containing:
            - safe: bool - Whether the output passed validation
            - should_proceed: bool - Alias for safe
            - concerns: list[str] - List of concerns if unsafe
            - risk_level: str - Risk level (low, medium, high, critical)
            - gates: dict - THSP gate results
            - validation_time_ms: float - Validation time in milliseconds
            - error: str | None - Error message if validation failed

        Example:
            result = guardrail.validate_output(response.content)
            if result["safe"]:
                return response
            else:
                return "I cannot provide that response."
        """
        start_time = time.perf_counter()

        # Extract content
        if isinstance(output, str):
            content = output
        elif hasattr(output, "content"):
            content = output.content if isinstance(output.content, str) else str(output.content)
        else:
            content = str(output)

        # Handle empty content
        if not content or content.strip() == "":
            return self._create_result(
                safe=True,
                validation_time=(time.perf_counter() - start_time) * 1000,
            )

        # Size check
        try:
            validate_text_size(content, self._max_text_size, "output")
        except TextTooLargeError as e:
            return self._create_result(
                safe=False,
                concerns=[f"Output too large: {e.size:,} bytes"],
                risk_level="high",
                validation_time=(time.perf_counter() - start_time) * 1000,
            )

        # THSP validation
        try:
            executor = get_validation_executor()
            check_result = executor.run_with_timeout(
                fn=self._sentinel.validate,
                args=(content,),
                timeout=self._validation_timeout,
            )
        except ValidationTimeoutError as e:
            return self._create_result(
                safe=True,  # Fail-open for outputs
                error=str(e),
                validation_time=(time.perf_counter() - start_time) * 1000,
            )
        except Exception as e:
            _logger.error("Output validation error: %s", e)
            return self._create_result(
                safe=True,  # Fail-open for outputs
                error=str(e),
                validation_time=(time.perf_counter() - start_time) * 1000,
            )

        # Analyze result
        is_safe, violations = check_result if isinstance(check_result, tuple) else (check_result, [])

        if isinstance(is_safe, dict):
            # Handle dict return format
            safe = is_safe.get("is_safe", is_safe.get("should_proceed", True))
            concerns = is_safe.get("concerns", is_safe.get("violations", []))
            risk_level = is_safe.get("risk_level", "medium")
            gates = is_safe.get("gates", {})
        else:
            safe = bool(is_safe)
            concerns = violations if isinstance(violations, list) else []
            risk_level = "low" if safe else "medium"
            gates = {}

        validation_time = (time.perf_counter() - start_time) * 1000

        # Record violation if unsafe
        if not safe and self._log_violations:
            violation = format_violation(
                content=content,
                concerns=concerns,
                risk_level=risk_level,
                gates=gates,
            )
            self._violations.append(violation)

        return self._create_result(
            safe=safe,
            concerns=concerns,
            risk_level=risk_level,
            gates=gates,
            validation_time=validation_time,
        )

    async def async_validate_output(self, output: str | Any) -> dict[str, Any]:
        """Validate LLM output asynchronously.

        This is the async version of validate_output(). Use this when
        calling from an async context.

        Args:
            output: The output to validate.

        Returns:
            Same as validate_output().
        """
        import asyncio

        return await asyncio.to_thread(self.validate_output, output)

    def _create_result(
        self,
        safe: bool,
        concerns: list[str] | None = None,
        risk_level: str = "low",
        gates: dict[str, bool] | None = None,
        validation_time: float = 0.0,
        error: str | None = None,
    ) -> dict[str, Any]:
        """Create a standardized result dictionary.

        Args:
            safe: Whether the content is safe.
            concerns: List of concerns if unsafe.
            risk_level: Risk level string.
            gates: THSP gate results.
            validation_time: Validation time in ms.
            error: Error message if any.

        Returns:
            Standardized result dictionary.
        """
        return {
            "safe": safe,
            "should_proceed": safe,  # Alias for compatibility
            "concerns": concerns or [],
            "risk_level": risk_level,
            "gates": gates or {},
            "validation_time_ms": validation_time,
            "error": error,
        }

    def get_violations(self) -> list[dict[str, Any]]:
        """Get list of recorded violations.

        Returns:
            List of violation dictionaries.
        """
        return self._violations.to_list()

    def clear_violations(self) -> None:
        """Clear all recorded violations."""
        self._violations.clear()


# Aliases for convenience
InputGuardrail = SentinelGuardrail
OutputGuardrail = SentinelOutputGuardrail
