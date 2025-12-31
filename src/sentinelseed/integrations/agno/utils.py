"""Utilities for Sentinel-Agno integration.

This module provides shared utilities, exceptions, and helper functions
for the Agno integration. All components follow Google Python Style Guide
and Azure SDK design patterns.

Components:
    - Custom exceptions (ConfigurationError, ValidationTimeoutError, etc.)
    - Configuration validation utilities
    - Content extraction from Agno RunInput objects
    - Thread-safe data structures for violation tracking
    - Logging utilities

Example:
    from sentinelseed.integrations.agno.utils import (
        validate_configuration,
        extract_content,
        ConfigurationError,
    )

    try:
        validate_configuration(max_text_size=100000, timeout=5.0)
    except ConfigurationError as e:
        print(f"Invalid configuration: {e}")
"""

from __future__ import annotations

import atexit
import concurrent.futures
import logging
import threading
from collections import deque
from typing import TYPE_CHECKING, Any, Callable, TypeVar

if TYPE_CHECKING:
    pass

# Type variable for generic functions
T = TypeVar("T")

# Module-level logger
_logger = logging.getLogger("sentinelseed.integrations.agno")

# Constants following Google style (CAPS_WITH_UNDER)
DEFAULT_MAX_TEXT_SIZE = 100_000
DEFAULT_VALIDATION_TIMEOUT = 5.0
DEFAULT_SEED_LEVEL = "standard"
MAX_VIOLATIONS_STORED = 1000
VALID_SEED_LEVELS = frozenset({"minimal", "standard", "full"})


# =============================================================================
# EXCEPTIONS
# =============================================================================


class ConfigurationError(Exception):
    """Raised when integration configuration is invalid.

    This exception indicates a programming error in the configuration
    parameters passed to Sentinel guardrails. It should be raised during
    initialization, not during runtime validation.

    Attributes:
        parameter: The name of the invalid parameter.
        value: The invalid value that was provided.
        reason: Human-readable explanation of why the value is invalid.

    Example:
        raise ConfigurationError(
            parameter="max_text_size",
            value=-1,
            reason="must be a positive integer",
        )
    """

    def __init__(
        self,
        parameter: str,
        value: Any,
        reason: str,
    ) -> None:
        self.parameter = parameter
        self.value = value
        self.reason = reason
        message = f"Invalid configuration for '{parameter}': {reason} (got {value!r})"
        super().__init__(message)


class ValidationTimeoutError(Exception):
    """Raised when validation exceeds the configured timeout.

    This exception is raised when the THSP validation takes longer than
    the specified timeout. The behavior after this exception depends on
    the fail_closed configuration:
    - fail_closed=True: Block the input
    - fail_closed=False: Allow the input (fail-open)

    Attributes:
        timeout: The timeout value in seconds that was exceeded.
        operation: Description of the operation that timed out.

    Example:
        raise ValidationTimeoutError(timeout=5.0, operation="THSP validation")
    """

    def __init__(
        self,
        timeout: float,
        operation: str = "validation",
    ) -> None:
        self.timeout = timeout
        self.operation = operation
        message = f"{operation.capitalize()} timed out after {timeout:.1f}s"
        super().__init__(message)


class TextTooLargeError(Exception):
    """Raised when input text exceeds the maximum allowed size.

    This exception provides a fast-fail mechanism to prevent processing
    of excessively large inputs that could cause performance issues or
    resource exhaustion.

    Attributes:
        size: The actual size of the input in bytes.
        max_size: The maximum allowed size in bytes.
        context: Additional context about where the error occurred.

    Example:
        raise TextTooLargeError(
            size=500000,
            max_size=100000,
            context="input validation",
        )
    """

    def __init__(
        self,
        size: int,
        max_size: int,
        context: str = "",
    ) -> None:
        self.size = size
        self.max_size = max_size
        self.context = context
        message = f"Text too large: {size:,} bytes exceeds limit of {max_size:,} bytes"
        if context:
            message = f"{context}: {message}"
        super().__init__(message)


# =============================================================================
# CONFIGURATION VALIDATION
# =============================================================================


def validate_configuration(
    max_text_size: int,
    validation_timeout: float,
    seed_level: str,
    fail_closed: bool,
    block_on_failure: bool,
    log_violations: bool,
) -> None:
    """Validate all configuration parameters.

    This function performs comprehensive validation of all configuration
    parameters before they are used. It follows the Azure SDK pattern of
    validating client parameters strictly to prevent malformed requests.

    Args:
        max_text_size: Maximum input size in bytes. Must be positive.
        validation_timeout: Timeout in seconds. Must be positive.
        seed_level: Safety level. Must be 'minimal', 'standard', or 'full'.
        fail_closed: Whether to block on validation errors.
        block_on_failure: Whether to block on THSP failures.
        log_violations: Whether to log violations.

    Raises:
        ConfigurationError: If any parameter is invalid.

    Example:
        validate_configuration(
            max_text_size=100000,
            validation_timeout=5.0,
            seed_level="standard",
            fail_closed=False,
            block_on_failure=True,
            log_violations=True,
        )
    """
    # Validate max_text_size
    if not isinstance(max_text_size, int):
        raise ConfigurationError(
            parameter="max_text_size",
            value=max_text_size,
            reason="must be an integer",
        )
    if max_text_size <= 0:
        raise ConfigurationError(
            parameter="max_text_size",
            value=max_text_size,
            reason="must be a positive integer",
        )

    # Validate validation_timeout
    if not isinstance(validation_timeout, (int, float)):
        raise ConfigurationError(
            parameter="validation_timeout",
            value=validation_timeout,
            reason="must be a number",
        )
    if validation_timeout <= 0:
        raise ConfigurationError(
            parameter="validation_timeout",
            value=validation_timeout,
            reason="must be positive",
        )

    # Validate seed_level
    if not isinstance(seed_level, str):
        raise ConfigurationError(
            parameter="seed_level",
            value=seed_level,
            reason="must be a string",
        )
    if seed_level.lower() not in VALID_SEED_LEVELS:
        raise ConfigurationError(
            parameter="seed_level",
            value=seed_level,
            reason=f"must be one of {sorted(VALID_SEED_LEVELS)}",
        )

    # Validate boolean parameters
    if not isinstance(fail_closed, bool):
        raise ConfigurationError(
            parameter="fail_closed",
            value=fail_closed,
            reason="must be a boolean",
        )
    if not isinstance(block_on_failure, bool):
        raise ConfigurationError(
            parameter="block_on_failure",
            value=block_on_failure,
            reason="must be a boolean",
        )
    if not isinstance(log_violations, bool):
        raise ConfigurationError(
            parameter="log_violations",
            value=log_violations,
            reason="must be a boolean",
        )


def validate_text_size(
    text: str,
    max_size: int,
    context: str = "",
) -> None:
    """Validate that text does not exceed maximum size.

    This is a fast-path check that runs before expensive THSP validation.
    It prevents resource exhaustion from excessively large inputs.

    Args:
        text: The text to validate.
        max_size: Maximum allowed size in bytes.
        context: Optional context for error messages.

    Raises:
        TextTooLargeError: If text exceeds max_size.
        TypeError: If text is not a string.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str, got {type(text).__name__}")

    size = len(text.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size=size, max_size=max_size, context=context)


# =============================================================================
# CONTENT EXTRACTION
# =============================================================================


def extract_content(run_input: Any) -> str | None:
    """Extract text content from Agno RunInput object.

    This function handles various input formats that Agno might provide,
    extracting the text content for validation. It follows a defensive
    approach, returning None for unrecognized formats rather than raising.

    Args:
        run_input: An Agno RunInput object or compatible structure.
            Expected to have an 'input_content' attribute.

    Returns:
        The extracted text content as a string, or None if extraction fails.

    Example:
        content = extract_content(run_input)
        if content is not None:
            is_safe, violations = sentinel.validate(content)
    """
    if run_input is None:
        return None

    # Try input_content attribute (primary Agno pattern)
    if hasattr(run_input, "input_content"):
        content = run_input.input_content
        if isinstance(content, str):
            return content
        if content is None:
            return None
        # Try to convert to string
        try:
            return str(content)
        except Exception:
            _logger.debug("Failed to convert input_content to string")
            return None

    # Try content attribute (fallback)
    if hasattr(run_input, "content"):
        content = run_input.content
        if isinstance(content, str):
            return content

    # Try dict-like access
    if isinstance(run_input, dict):
        for key in ("input_content", "content", "text", "message"):
            if key in run_input:
                value = run_input[key]
                if isinstance(value, str):
                    return value

    # Try string conversion as last resort
    if isinstance(run_input, str):
        return run_input

    _logger.debug(
        "Could not extract content from run_input of type %s",
        type(run_input).__name__,
    )
    return None


def extract_messages(run_input: Any) -> list[str]:
    """Extract all message contents from a RunInput.

    For multi-message inputs, this function extracts all text content
    from each message in the conversation.

    Args:
        run_input: An Agno RunInput object that may contain messages.

    Returns:
        List of message contents as strings. Empty list if no messages found.
    """
    messages: list[str] = []

    if run_input is None:
        return messages

    # Try messages attribute
    if hasattr(run_input, "messages"):
        raw_messages = run_input.messages
        if isinstance(raw_messages, (list, tuple)):
            for msg in raw_messages:
                content = _extract_message_content(msg)
                if content:
                    messages.append(content)

    # If no messages found, try single content extraction
    if not messages:
        content = extract_content(run_input)
        if content:
            messages.append(content)

    return messages


def _extract_message_content(message: Any) -> str | None:
    """Extract content from a single message object.

    Args:
        message: A message object (dict, object with content attr, or string).

    Returns:
        The message content as string, or None if extraction fails.
    """
    if message is None:
        return None

    if isinstance(message, str):
        return message

    if isinstance(message, dict):
        return message.get("content")

    if hasattr(message, "content"):
        content = message.content
        if isinstance(content, str):
            return content

    return None


# =============================================================================
# THREAD-SAFE DATA STRUCTURES
# =============================================================================


class ThreadSafeDeque:
    """Thread-safe deque for storing violations and logs.

    This class provides a bounded, thread-safe deque for storing
    validation violations and other log entries. It follows the
    pattern from the LangChain integration.

    Attributes:
        maxlen: Maximum number of items to store.

    Example:
        violations = ThreadSafeDeque(maxlen=1000)
        violations.append({"type": "harm", "content": "..."})
        all_violations = violations.to_list()
    """

    def __init__(self, maxlen: int | None = MAX_VIOLATIONS_STORED) -> None:
        """Initialize thread-safe deque.

        Args:
            maxlen: Maximum number of items. None for unlimited.
        """
        self._deque: deque[Any] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, item: Any) -> None:
        """Append an item to the deque (thread-safe).

        Args:
            item: The item to append.
        """
        with self._lock:
            self._deque.append(item)

    def extend(self, items: list[Any]) -> None:
        """Extend the deque with multiple items (thread-safe).

        Args:
            items: List of items to append.
        """
        with self._lock:
            self._deque.extend(items)

    def to_list(self) -> list[Any]:
        """Return a thread-safe copy as a list.

        Returns:
            List containing all items in the deque.
        """
        with self._lock:
            return list(self._deque)

    def clear(self) -> None:
        """Clear all items from the deque (thread-safe)."""
        with self._lock:
            self._deque.clear()

    def __len__(self) -> int:
        """Return the number of items (thread-safe).

        Returns:
            Number of items in the deque.
        """
        with self._lock:
            return len(self._deque)


# =============================================================================
# VALIDATION EXECUTOR (Singleton)
# =============================================================================


class ValidationExecutor:
    """Singleton executor for timeout-protected validation.

    This class provides a shared ThreadPoolExecutor for running
    validation operations with timeout protection. Using a singleton
    avoids the overhead of creating new thread pools for each validation.

    The executor is automatically shut down on program exit via atexit.

    Example:
        executor = ValidationExecutor.get_instance()
        try:
            is_safe, violations = executor.run_with_timeout(
                fn=sentinel.validate,
                args=("user input",),
                timeout=5.0,
            )
        except ValidationTimeoutError:
            handle_timeout()
    """

    _instance: ValidationExecutor | None = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        """Initialize the executor.

        Note:
            Do not call directly. Use get_instance() instead.
        """
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=4,
            thread_name_prefix="sentinel-agno-",
        )
        self._shutdown = False

    @classmethod
    def get_instance(cls) -> ValidationExecutor:
        """Get the singleton executor instance.

        Returns:
            The shared ValidationExecutor instance.

        Note:
            Thread-safe lazy initialization.
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    atexit.register(cls._instance.shutdown)
        return cls._instance

    def run_with_timeout(
        self,
        fn: Callable[..., T],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] | None = None,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    ) -> T:
        """Run a function with timeout protection.

        Args:
            fn: The function to execute.
            args: Positional arguments for the function.
            kwargs: Keyword arguments for the function.
            timeout: Maximum execution time in seconds.

        Returns:
            The function's return value.

        Raises:
            ValidationTimeoutError: If execution exceeds timeout.
            Exception: Any exception raised by the function.
        """
        if self._shutdown:
            raise RuntimeError("Executor has been shut down")

        kwargs = kwargs or {}
        future = self._executor.submit(fn, *args, **kwargs)

        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise ValidationTimeoutError(
                timeout=timeout,
                operation="THSP validation",
            ) from None

    def shutdown(self) -> None:
        """Shut down the executor.

        Note:
            Called automatically on program exit via atexit.
        """
        if not self._shutdown:
            self._shutdown = True
            self._executor.shutdown(wait=False)


def get_validation_executor() -> ValidationExecutor:
    """Get the shared validation executor.

    This is a convenience function for getting the singleton executor.

    Returns:
        The shared ValidationExecutor instance.
    """
    return ValidationExecutor.get_instance()


# =============================================================================
# LOGGING UTILITIES
# =============================================================================


def get_logger(name: str | None = None) -> logging.Logger:
    """Get a logger for the Agno integration.

    Args:
        name: Optional suffix for the logger name.

    Returns:
        A configured logger instance.
    """
    if name:
        return logging.getLogger(f"sentinelseed.integrations.agno.{name}")
    return _logger


def log_fail_open_warning(component: str) -> None:
    """Log a warning about fail-open default behavior.

    This function logs a warning when fail_closed=False is used,
    making the security trade-off explicit to operators.

    Args:
        component: Name of the component using fail-open mode.
    """
    _logger.warning(
        "%s: Using fail-open mode (fail_closed=False). "
        "Validation errors will allow content through. "
        "For security-critical applications, set fail_closed=True.",
        component,
    )


# =============================================================================
# STATISTICS UTILITIES
# =============================================================================


def create_empty_stats() -> dict[str, Any]:
    """Create an empty statistics dictionary.

    Returns:
        Dictionary with initialized statistics fields.
    """
    return {
        "total_validations": 0,
        "blocked_count": 0,
        "allowed_count": 0,
        "timeout_count": 0,
        "error_count": 0,
        "gate_failures": {
            "truth": 0,
            "harm": 0,
            "scope": 0,
            "purpose": 0,
        },
        "avg_validation_time_ms": 0.0,
    }


def format_violation(
    content: str,
    concerns: list[str],
    risk_level: str,
    gates: dict[str, bool],
    timestamp: float | None = None,
) -> dict[str, Any]:
    """Format a violation record for storage.

    Args:
        content: The content that was flagged (may be truncated).
        concerns: List of concerns identified.
        risk_level: Risk level (low, medium, high, critical).
        gates: THSP gate results.
        timestamp: Unix timestamp (defaults to current time).

    Returns:
        Formatted violation dictionary.
    """
    import time

    # Truncate content for storage
    max_content_len = 200
    truncated = content[:max_content_len]
    if len(content) > max_content_len:
        truncated += "..."

    return {
        "content_preview": truncated,
        "concerns": concerns,
        "risk_level": risk_level,
        "gates": gates,
        "timestamp": timestamp or time.time(),
    }
