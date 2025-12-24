"""
Utility functions and classes for DSPy integration.

Provides:
- ValidationExecutor: Shared thread pool for efficient validation
- Logger management
- Parameter validation helpers
- Text size validation
- Async timeout utilities

This module mirrors the patterns from the LangChain integration
to ensure consistency across all Sentinel integrations.
"""

from typing import Any, Callable, Dict, Optional, Protocol, TypeVar
import asyncio
import atexit
import logging
import threading
import concurrent.futures

# Type variable for generic validation functions
T = TypeVar('T')

# =============================================================================
# Default Configuration
# =============================================================================
#
# IMPORTANT SECURITY NOTE:
# - DEFAULT_FAIL_CLOSED = False means validation errors allow content through
# - For security-critical applications, set fail_closed=True explicitly
# - This is a deliberate trade-off: availability over security by default
#
DEFAULT_SEED_LEVEL = "standard"
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # 30 seconds
DEFAULT_EXECUTOR_MAX_WORKERS = 4  # shared executor thread pool size

# Valid parameter values
VALID_SEED_LEVELS = ("minimal", "standard", "full")
VALID_MODES = ("block", "flag", "heuristic")
VALID_PROVIDERS = ("openai", "anthropic")
VALID_GATES = ("truth", "harm", "scope", "purpose")

# Safety confidence levels (ordered from lowest to highest)
# - "none": No validation was performed (error/timeout in fail-open mode)
# - "low": Heuristic validation only (pattern-based, ~50% accuracy)
# - "medium": Semantic validation with fallback (some uncertainty)
# - "high": Full semantic validation completed successfully
VALID_CONFIDENCE_LEVELS = ("none", "low", "medium", "high")
CONFIDENCE_NONE = "none"
CONFIDENCE_LOW = "low"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_HIGH = "high"

# Module logger
_module_logger = logging.getLogger("sentinelseed.integrations.dspy")


# =============================================================================
# Exception Classes
# =============================================================================

class DSPyNotAvailableError(ImportError):
    """Raised when DSPy is not installed but required."""

    def __init__(self):
        super().__init__(
            "dspy is required for this integration. "
            "Install with: pip install dspy"
        )


class TextTooLargeError(Exception):
    """Raised when input text exceeds maximum allowed size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Text size ({size:,} bytes) exceeds maximum allowed ({max_size:,} bytes)"
        )


class ValidationTimeoutError(Exception):
    """Raised when validation exceeds timeout."""

    def __init__(self, timeout: float, operation: str = "validation"):
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout}s")


class HeuristicFallbackError(Exception):
    """
    Raised when heuristic fallback is required but not allowed.

    This occurs when:
    - No API key is provided for semantic validation
    - allow_heuristic_fallback=False (default)

    To fix, either:
    1. Provide an API key for semantic validation
    2. Set allow_heuristic_fallback=True to explicitly allow degraded validation
    3. Set mode="heuristic" to use heuristic validation intentionally
    """

    def __init__(self, component: str):
        self.component = component
        super().__init__(
            f"{component} requires an API key for semantic validation. "
            "Either provide an api_key, set allow_heuristic_fallback=True, "
            "or use mode='heuristic' explicitly."
        )


class InvalidParameterError(Exception):
    """Raised when an invalid parameter value is provided."""

    def __init__(self, param: str, value: Any, valid_values: tuple):
        self.param = param
        self.value = value
        self.valid_values = valid_values
        super().__init__(
            f"Invalid {param}: '{value}'. Valid values: {valid_values}"
        )


class ConfigurationError(Exception):
    """Raised when configuration parameters are invalid."""

    def __init__(self, param_name: str, expected: str, got: Any):
        self.param_name = param_name
        self.expected = expected
        self.got = got
        super().__init__(
            f"Invalid configuration: '{param_name}' expected {expected}, got {type(got).__name__}"
        )


# =============================================================================
# Logger Protocol and Management
# =============================================================================

class SentinelLogger(Protocol):
    """Protocol for custom loggers."""
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class _DefaultLogger:
    """Default logger implementation using module logger."""

    def debug(self, message: str) -> None:
        _module_logger.debug(message)

    def info(self, message: str) -> None:
        _module_logger.info(message)

    def warning(self, message: str) -> None:
        _module_logger.warning(message)

    def error(self, message: str) -> None:
        _module_logger.error(message)


# Global logger instance
_logger: SentinelLogger = _DefaultLogger()
_logger_lock = threading.Lock()


def get_logger() -> SentinelLogger:
    """Get the current global logger instance."""
    with _logger_lock:
        return _logger


def set_logger(logger: SentinelLogger) -> None:
    """
    Set custom logger for the DSPy integration.

    Args:
        logger: Object implementing debug, info, warning, error methods

    Example:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        set_logger(logging.getLogger("my_app.sentinel"))
    """
    global _logger
    with _logger_lock:
        _logger = logger


# =============================================================================
# Shared Validation Executor
# =============================================================================
#
# This singleton manages a persistent ThreadPoolExecutor to avoid the overhead
# of creating a new executor for each validation call. The executor is lazily
# initialized and automatically cleaned up on process exit.
#

class ValidationExecutor:
    """
    Singleton manager for a shared ThreadPoolExecutor.

    Provides efficient thread pool management for synchronous validation
    operations that need timeout support. Uses lazy initialization and
    automatic cleanup.

    Usage:
        executor = ValidationExecutor.get_instance()
        result = executor.run_with_timeout(fn, args, timeout=30.0)

    Thread Safety:
        All methods are thread-safe. The executor is shared across all
        instances of SentinelGuard, SentinelPredict, and SentinelChainOfThought.
    """

    _instance: Optional['ValidationExecutor'] = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = DEFAULT_EXECUTOR_MAX_WORKERS):
        """Initialize executor (called only once via get_instance)."""
        self._max_workers = max_workers
        self._executor: Optional[concurrent.futures.ThreadPoolExecutor] = None
        self._executor_lock = threading.Lock()
        self._shutdown = False

    @classmethod
    def get_instance(cls, max_workers: int = DEFAULT_EXECUTOR_MAX_WORKERS) -> 'ValidationExecutor':
        """
        Get or create the singleton executor instance.

        Args:
            max_workers: Maximum worker threads (only used on first call)

        Returns:
            Shared ValidationExecutor instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(max_workers)
                    # Register cleanup on process exit
                    atexit.register(cls._instance.shutdown)
        return cls._instance

    def _get_executor(self) -> concurrent.futures.ThreadPoolExecutor:
        """Get or create the underlying executor (lazy initialization)."""
        if self._executor is None:
            with self._executor_lock:
                if self._executor is None and not self._shutdown:
                    self._executor = concurrent.futures.ThreadPoolExecutor(
                        max_workers=self._max_workers,
                        thread_name_prefix="sentinel-dspy-validator"
                    )
        return self._executor

    def run_with_timeout(
        self,
        fn: Callable[..., T],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    ) -> T:
        """
        Run a function with timeout in the shared thread pool.

        Args:
            fn: Function to execute
            args: Positional arguments for fn
            kwargs: Keyword arguments for fn
            timeout: Maximum time to wait in seconds

        Returns:
            Result of fn(*args, **kwargs)

        Raises:
            ValidationTimeoutError: If timeout exceeded
            Exception: Any exception raised by fn
        """
        if self._shutdown:
            raise RuntimeError("ValidationExecutor has been shut down")

        kwargs = kwargs or {}
        executor = self._get_executor()

        future = executor.submit(fn, *args, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            future.cancel()
            raise ValidationTimeoutError(timeout, f"executing {fn.__name__}")

    async def run_with_timeout_async(
        self,
        fn: Callable[..., T],
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    ) -> T:
        """
        Run a function asynchronously with timeout using the shared thread pool.

        This method uses the same controlled thread pool as run_with_timeout,
        avoiding the creation of unbounded threads via asyncio.to_thread().

        Args:
            fn: Function to execute
            args: Positional arguments for fn
            kwargs: Keyword arguments for fn
            timeout: Maximum time to wait in seconds

        Returns:
            Result of fn(*args, **kwargs)

        Raises:
            ValidationTimeoutError: If timeout exceeded
            RuntimeError: If executor has been shut down
            Exception: Any exception raised by fn
        """
        if self._shutdown:
            raise RuntimeError("ValidationExecutor has been shut down")

        kwargs = kwargs or {}
        executor = self._get_executor()

        # Submit to our controlled thread pool
        future = executor.submit(fn, *args, **kwargs)

        # Wrap the concurrent.futures.Future as asyncio.Future
        # This allows async/await without creating additional threads
        async_future = asyncio.wrap_future(future)

        try:
            result = await asyncio.wait_for(async_future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            future.cancel()
            raise ValidationTimeoutError(timeout, f"executing {fn.__name__}")

    def shutdown(self, wait: bool = True) -> None:
        """
        Shutdown the executor.

        Called automatically on process exit, but can be called manually
        for testing or resource management.

        Args:
            wait: Whether to wait for pending tasks to complete
        """
        with self._executor_lock:
            self._shutdown = True
            if self._executor is not None:
                self._executor.shutdown(wait=wait)
                self._executor = None

    @classmethod
    def reset_instance(cls) -> None:
        """
        Reset the singleton instance (for testing only).

        This shuts down the existing executor and clears the singleton,
        allowing a fresh instance to be created on next get_instance() call.
        """
        with cls._lock:
            if cls._instance is not None:
                cls._instance.shutdown(wait=True)
                cls._instance = None


# Convenience function for getting the shared executor
def get_validation_executor() -> ValidationExecutor:
    """Get the shared validation executor instance."""
    return ValidationExecutor.get_instance()


# =============================================================================
# Async Validation Helpers
# =============================================================================

async def run_with_timeout_async(
    fn: Callable[..., T],
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
) -> T:
    """
    Run a synchronous function asynchronously with timeout.

    Uses the shared ValidationExecutor thread pool to run the function
    without blocking the event loop, with proper timeout handling.

    Args:
        fn: Synchronous function to execute
        args: Positional arguments for fn
        kwargs: Keyword arguments for fn
        timeout: Maximum time to wait in seconds

    Returns:
        Result of fn(*args, **kwargs)

    Raises:
        ValidationTimeoutError: If timeout exceeded
        Exception: Any exception raised by fn
    """
    executor = get_validation_executor()
    return await executor.run_with_timeout_async(
        fn, args=args, kwargs=kwargs, timeout=timeout
    )


# =============================================================================
# Parameter Validation
# =============================================================================

def validate_mode(mode: str) -> str:
    """
    Validate mode parameter.

    Args:
        mode: Mode to validate

    Returns:
        Validated mode string

    Raises:
        InvalidParameterError: If mode is invalid
    """
    if mode not in VALID_MODES:
        raise InvalidParameterError("mode", mode, VALID_MODES)
    return mode


def validate_provider(provider: str) -> str:
    """
    Validate provider parameter.

    Args:
        provider: Provider to validate

    Returns:
        Validated provider string

    Raises:
        InvalidParameterError: If provider is invalid
    """
    if provider not in VALID_PROVIDERS:
        raise InvalidParameterError("provider", provider, VALID_PROVIDERS)
    return provider


def validate_gate(gate: str) -> str:
    """
    Validate gate parameter.

    Args:
        gate: Gate to validate

    Returns:
        Validated gate string

    Raises:
        InvalidParameterError: If gate is invalid
    """
    if gate not in VALID_GATES:
        raise InvalidParameterError("gate", gate, VALID_GATES)
    return gate


def validate_text_size(content: str, max_size: int = DEFAULT_MAX_TEXT_SIZE) -> None:
    """
    Validate text size is within limits.

    Args:
        content: Text to validate
        max_size: Maximum allowed size in bytes

    Raises:
        TextTooLargeError: If text exceeds max_size
    """
    if not content:
        return
    size = len(content.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size)


def validate_config_types(
    max_text_size: Any = None,
    timeout: Any = None,
    fail_closed: Any = None,
    **kwargs: Any
) -> None:
    """
    Validate configuration parameter types.

    Raises ConfigurationError if any parameter has an invalid type.
    None values are skipped (not validated).

    Args:
        max_text_size: Expected int > 0
        timeout: Expected float/int > 0
        fail_closed: Expected bool
        **kwargs: Ignored (allows passing extra params)

    Raises:
        ConfigurationError: If any parameter has invalid type or value
    """
    if max_text_size is not None:
        if not isinstance(max_text_size, int) or max_text_size <= 0:
            raise ConfigurationError(
                "max_text_size",
                "positive integer",
                max_text_size
            )

    if timeout is not None:
        if not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ConfigurationError(
                "timeout",
                "positive number",
                timeout
            )

    if fail_closed is not None:
        if not isinstance(fail_closed, bool):
            raise ConfigurationError(
                "fail_closed",
                "boolean",
                fail_closed
            )


def warn_fail_open_default(logger: SentinelLogger, component: str) -> None:
    """
    Log a warning about fail-open default behavior.

    This warning is logged once per component to alert users about
    the security implications of fail-open mode.

    Args:
        logger: Logger instance to use
        component: Name of the component (e.g., "SentinelGuard")
    """
    logger.debug(
        f"[SENTINEL] {component} initialized with fail_closed=False (fail-open mode). "
        "Validation errors will allow content through. "
        "Set fail_closed=True for stricter security."
    )


# =============================================================================
# DSPy Availability
# =============================================================================

def require_dspy(func_name: str = "this function") -> None:
    """
    Raise DSPyNotAvailableError if DSPy is not installed.

    Args:
        func_name: Name of function/class requiring DSPy

    Raises:
        DSPyNotAvailableError: If DSPy is not installed
    """
    try:
        import dspy  # noqa: F401
    except (ImportError, AttributeError):
        raise DSPyNotAvailableError()


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Constants
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "DEFAULT_EXECUTOR_MAX_WORKERS",
    "VALID_SEED_LEVELS",
    "VALID_MODES",
    "VALID_PROVIDERS",
    "VALID_GATES",
    # Confidence levels
    "VALID_CONFIDENCE_LEVELS",
    "CONFIDENCE_NONE",
    "CONFIDENCE_LOW",
    "CONFIDENCE_MEDIUM",
    "CONFIDENCE_HIGH",
    # Exceptions
    "DSPyNotAvailableError",
    "TextTooLargeError",
    "ValidationTimeoutError",
    "InvalidParameterError",
    "ConfigurationError",
    "HeuristicFallbackError",
    # Logger
    "SentinelLogger",
    "get_logger",
    "set_logger",
    # Executor
    "ValidationExecutor",
    "get_validation_executor",
    "run_with_timeout_async",
    # Validation helpers
    "validate_mode",
    "validate_provider",
    "validate_gate",
    "validate_text_size",
    "validate_config_types",
    "warn_fail_open_default",
    "require_dspy",
]
