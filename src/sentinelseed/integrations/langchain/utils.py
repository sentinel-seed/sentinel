"""
Utility functions and classes for LangChain integration.

Provides:
- Logger management
- Text sanitization
- Thread-safe data structures
- LangChain availability checking
"""

from typing import Any, Dict, List, Optional, Protocol
import logging
import re
import threading
from collections import deque

# Default configuration
DEFAULT_MAX_VIOLATIONS = 1000
DEFAULT_SEED_LEVEL = "standard"
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # 30 seconds
DEFAULT_STREAMING_VALIDATION_INTERVAL = 500  # chars between incremental validations

# Module logger
_module_logger = logging.getLogger("sentinelseed.langchain")


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
except ImportError:
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
    except ImportError:
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
    "LANGCHAIN_AVAILABLE",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
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
    # Classes
    "SentinelLogger",
    "ThreadSafeDeque",
    "ValidationResult",
    "ViolationRecord",
]
