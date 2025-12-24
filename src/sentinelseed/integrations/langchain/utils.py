"""
Utility functions and classes for LangChain integration.

Provides:
- Logger management
- Text sanitization
- Thread-safe data structures
- LangChain availability checking
- Shared validation executor for efficient thread pooling
"""

from typing import Any, Callable, Dict, List, Optional, Protocol, TypeVar, Union
import asyncio
import atexit
import logging
import re
import threading
import concurrent.futures
from collections import deque
from functools import wraps

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
DEFAULT_MAX_VIOLATIONS = 1000
DEFAULT_SEED_LEVEL = "standard"
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # 30 seconds
DEFAULT_STREAMING_VALIDATION_INTERVAL = 500  # chars between incremental validations
DEFAULT_EXECUTOR_MAX_WORKERS = 4  # shared executor thread pool size

# Module logger
_module_logger = logging.getLogger("sentinelseed.langchain")


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
        instances of SentinelCallback, SentinelGuard, and SentinelChain.
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
                        thread_name_prefix="sentinel-validator"
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
#
# These functions provide async-native validation without blocking the event loop.
# They use the shared ValidationExecutor for controlled thread pool management.
#

async def run_sync_with_timeout_async(
    fn: Callable[..., T],
    args: tuple = (),
    kwargs: Optional[Dict[str, Any]] = None,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
) -> T:
    """
    Run a synchronous function asynchronously with timeout.

    Uses the shared ValidationExecutor thread pool to run the function
    without blocking the event loop, with proper timeout handling.

    Note:
        This function delegates to ValidationExecutor.run_with_timeout_async()
        to ensure all async operations use the same controlled thread pool.

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

    Example:
        async def validate_async(text):
            result = await run_sync_with_timeout_async(
                sentinel.validate,
                args=(text,),
                timeout=30.0
            )
            return result
    """
    executor = get_validation_executor()
    return await executor.run_with_timeout_async(
        fn, args=args, kwargs=kwargs, timeout=timeout
    )


# ============================================================================
# Exception Classes
# ============================================================================

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


class ConfigurationError(Exception):
    """Raised when configuration parameters are invalid."""

    def __init__(self, param_name: str, expected: str, got: Any):
        self.param_name = param_name
        self.expected = expected
        self.got = got
        super().__init__(
            f"Invalid configuration: '{param_name}' expected {expected}, got {type(got).__name__}"
        )


# ============================================================================
# Configuration Validation
# ============================================================================

def validate_config_types(
    max_text_size: Any = None,
    validation_timeout: Any = None,
    fail_closed: Any = None,
    max_violations: Any = None,
    streaming_validation_interval: Any = None,
    **kwargs: Any
) -> None:
    """
    Validate configuration parameter types.

    Raises ConfigurationError if any parameter has an invalid type.
    None values are skipped (not validated).

    Args:
        max_text_size: Expected int > 0
        validation_timeout: Expected float/int > 0
        fail_closed: Expected bool
        max_violations: Expected int > 0
        streaming_validation_interval: Expected int > 0
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

    if validation_timeout is not None:
        if not isinstance(validation_timeout, (int, float)) or validation_timeout <= 0:
            raise ConfigurationError(
                "validation_timeout",
                "positive number",
                validation_timeout
            )

    if fail_closed is not None:
        if not isinstance(fail_closed, bool):
            raise ConfigurationError(
                "fail_closed",
                "boolean",
                fail_closed
            )

    if max_violations is not None:
        if not isinstance(max_violations, int) or max_violations <= 0:
            raise ConfigurationError(
                "max_violations",
                "positive integer",
                max_violations
            )

    if streaming_validation_interval is not None:
        if not isinstance(streaming_validation_interval, int) or streaming_validation_interval <= 0:
            raise ConfigurationError(
                "streaming_validation_interval",
                "positive integer",
                streaming_validation_interval
            )


def warn_fail_open_default(logger: 'SentinelLogger', component: str) -> None:
    """
    Log a warning about fail-open default behavior.

    This warning is logged once per component to alert users about
    the security implications of fail-open mode.

    Args:
        logger: Logger instance to use
        component: Name of the component (e.g., "SentinelCallback")
    """
    logger.debug(
        f"[SENTINEL] {component} initialized with fail_closed=False (fail-open mode). "
        "Validation errors will allow content through. "
        "Set fail_closed=True for stricter security."
    )


# ============================================================================
# Text Size Validation
# ============================================================================

def validate_text_size(
    text: str,
    max_size: int = DEFAULT_MAX_TEXT_SIZE,
    context: str = "text"
) -> None:
    """
    Validate that text does not exceed maximum size.

    Args:
        text: Text to validate
        max_size: Maximum allowed size in bytes
        context: Context for error message

    Raises:
        TextTooLargeError: If text exceeds max_size
    """
    if not text or not isinstance(text, str):
        return

    size = len(text.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size)


# ============================================================================
# LangChain Availability
# ============================================================================

LANGCHAIN_AVAILABLE = False
SystemMessage = None
HumanMessage = None
AIMessage = None
BaseMessage = None
BaseCallbackHandler = object

try:
    from langchain_core.callbacks.base import BaseCallbackHandler as _BaseCallbackHandler
    from langchain_core.messages import (
        SystemMessage as _SystemMessage,
        HumanMessage as _HumanMessage,
        AIMessage as _AIMessage,
        BaseMessage as _BaseMessage,
    )
    BaseCallbackHandler = _BaseCallbackHandler
    SystemMessage = _SystemMessage
    HumanMessage = _HumanMessage
    AIMessage = _AIMessage
    BaseMessage = _BaseMessage
    LANGCHAIN_AVAILABLE = True
except (ImportError, AttributeError) as e:
    if isinstance(e, AttributeError):
        _module_logger.warning(
            f"LangChain installed but langchain_core has incompatible structure: {e}"
        )
    try:
        from langchain.callbacks.base import BaseCallbackHandler as _BaseCallbackHandler
        from langchain.schema import (
            SystemMessage as _SystemMessage,
            HumanMessage as _HumanMessage,
            AIMessage as _AIMessage,
            BaseMessage as _BaseMessage,
        )
        BaseCallbackHandler = _BaseCallbackHandler
        SystemMessage = _SystemMessage
        HumanMessage = _HumanMessage
        AIMessage = _AIMessage
        BaseMessage = _BaseMessage
        LANGCHAIN_AVAILABLE = True
    except (ImportError, AttributeError) as e2:
        if isinstance(e2, AttributeError):
            _module_logger.warning(
                f"LangChain installed but has incompatible structure: {e2}"
            )
        else:
            _module_logger.warning(
                "LangChain not installed. Install with: pip install langchain langchain-core"
            )


def require_langchain(func_name: str = "this function") -> None:
    """
    Raise ImportError if LangChain is not available.

    Args:
        func_name: Name of function/class requiring LangChain

    Raises:
        ImportError: If LangChain is not installed
    """
    if not LANGCHAIN_AVAILABLE:
        raise ImportError(
            f"LangChain is required for {func_name}. "
            "Install with: pip install langchain langchain-core"
        )


# ============================================================================
# Logger Protocol and Management
# ============================================================================

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
    Set custom logger for the LangChain integration.

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


# ============================================================================
# Text Sanitization
# ============================================================================

# Pre-compiled regex patterns for performance
_EMAIL_PATTERN = re.compile(r'[\w.-]+@[\w.-]+\.\w+')
_PHONE_PATTERN = re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b')
_TOKEN_PATTERN = re.compile(r'\b[a-zA-Z0-9]{32,}\b')


def sanitize_text(
    text: str,
    max_length: int = 200,
    sanitize: bool = False
) -> str:
    """
    Truncate and optionally sanitize text for logging.

    Args:
        text: Text to process
        max_length: Maximum length before truncation
        sanitize: If True, replace potentially sensitive patterns

    Returns:
        Processed text safe for logging
    """
    if not text:
        return ""

    result = text[:max_length] + ("..." if len(text) > max_length else "")

    if sanitize:
        result = _EMAIL_PATTERN.sub('[EMAIL]', result)
        result = _PHONE_PATTERN.sub('[PHONE]', result)
        result = _TOKEN_PATTERN.sub('[TOKEN]', result)

    return result


# ============================================================================
# Thread-Safe Data Structures
# ============================================================================

class ThreadSafeDeque:
    """
    Thread-safe deque with bounded size.

    Provides thread-safe append, iteration, and clearing operations.
    """

    def __init__(self, maxlen: int = DEFAULT_MAX_VIOLATIONS):
        self._deque: deque = deque(maxlen=maxlen)
        self._lock = threading.RLock()

    def append(self, item: Any) -> None:
        """Thread-safe append."""
        with self._lock:
            self._deque.append(item)

    def extend(self, items: List[Any]) -> None:
        """Thread-safe extend."""
        with self._lock:
            self._deque.extend(items)

    def clear(self) -> None:
        """Thread-safe clear."""
        with self._lock:
            self._deque.clear()

    def to_list(self) -> List[Any]:
        """Thread-safe conversion to list (creates copy)."""
        with self._lock:
            return list(self._deque)

    def __len__(self) -> int:
        """Thread-safe length."""
        with self._lock:
            return len(self._deque)

    def __iter__(self):
        """
        Thread-safe iteration (creates snapshot).

        Note: Iterates over a copy to avoid holding lock during iteration.
        """
        with self._lock:
            items = list(self._deque)
        return iter(items)


# ============================================================================
# Message Utilities
# ============================================================================

def extract_content(message: Any) -> str:
    """
    Extract text content from various message formats.

    Args:
        message: LangChain message, dict, or other format

    Returns:
        Extracted text content
    """
    if hasattr(message, 'content'):
        return message.content
    elif isinstance(message, dict):
        return message.get('content', '')
    elif isinstance(message, str):
        return message
    else:
        return str(message)


def get_message_role(message: Any) -> Optional[str]:
    """
    Get role from various message formats.

    Args:
        message: LangChain message or dict

    Returns:
        Role string or None
    """
    if isinstance(message, dict):
        return message.get("role")
    elif hasattr(message, "type"):
        return message.type
    elif SystemMessage is not None and isinstance(message, SystemMessage):
        return "system"
    elif HumanMessage is not None and isinstance(message, HumanMessage):
        return "human"
    elif AIMessage is not None and isinstance(message, AIMessage):
        return "ai"
    return None


def is_system_message(message: Any) -> bool:
    """Check if message is a system message."""
    if isinstance(message, dict):
        return message.get('role') == 'system'
    elif hasattr(message, 'type') and message.type == 'system':
        return True
    elif SystemMessage is not None and isinstance(message, SystemMessage):
        return True
    return False


# ============================================================================
# Validation Result Types
# ============================================================================

class ValidationResult:
    """Structured validation result."""

    __slots__ = ('safe', 'stage', 'type', 'risk_level', 'concerns', 'text')

    def __init__(
        self,
        safe: bool,
        stage: str,
        type: str,  # "input" or "output"
        risk_level: str = "unknown",
        concerns: Optional[List[str]] = None,
        text: str = ""
    ):
        self.safe = safe
        self.stage = stage
        self.type = type
        self.risk_level = risk_level
        self.concerns = concerns or []
        self.text = text

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "safe": self.safe,
            "stage": self.stage,
            "type": self.type,
            "risk_level": self.risk_level,
            "concerns": self.concerns,
            "text": self.text,
        }


class ViolationRecord:
    """Structured violation record."""

    __slots__ = ('stage', 'text', 'concerns', 'risk_level', 'timestamp')

    def __init__(
        self,
        stage: str,
        text: str,
        concerns: List[str],
        risk_level: str,
        timestamp: Optional[float] = None
    ):
        import time
        self.stage = stage
        self.text = text
        self.concerns = concerns
        self.risk_level = risk_level
        self.timestamp = timestamp or time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "stage": self.stage,
            "text": self.text,
            "concerns": self.concerns,
            "risk_level": self.risk_level,
            "timestamp": self.timestamp,
        }


# ============================================================================
# Exports
# ============================================================================

__all__ = [
    # Constants
    "DEFAULT_MAX_VIOLATIONS",
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "DEFAULT_STREAMING_VALIDATION_INTERVAL",
    "DEFAULT_EXECUTOR_MAX_WORKERS",
    "LANGCHAIN_AVAILABLE",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
    "ConfigurationError",
    # LangChain types
    "BaseCallbackHandler",
    "SystemMessage",
    "HumanMessage",
    "AIMessage",
    "BaseMessage",
    # Functions
    "require_langchain",
    "get_logger",
    "set_logger",
    "sanitize_text",
    "extract_content",
    "get_message_role",
    "is_system_message",
    "validate_text_size",
    "validate_config_types",
    "warn_fail_open_default",
    "get_validation_executor",
    "run_sync_with_timeout_async",
    # Classes
    "SentinelLogger",
    "ThreadSafeDeque",
    "ValidationResult",
    "ViolationRecord",
    "ValidationExecutor",
]
