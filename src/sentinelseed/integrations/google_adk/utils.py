"""Utility functions for Google ADK Sentinel integration.

This module provides shared utilities for the Google ADK integration,
including content extraction, validation helpers, and thread-safe data
structures.
"""

from __future__ import annotations

import logging
import threading
import time
from collections import deque
from typing import TYPE_CHECKING, Any, Callable

if TYPE_CHECKING:
    from sentinelseed import Sentinel

# Constants
DEFAULT_SEED_LEVEL = "standard"
DEFAULT_MAX_TEXT_SIZE = 100_000  # 100KB
DEFAULT_VALIDATION_TIMEOUT = 5.0  # seconds
DEFAULT_MAX_VIOLATIONS = 1000
VALID_SEED_LEVELS = ("minimal", "standard", "full")

# Try to import ADK dependencies at module level
try:
    from google.adk.agents import Agent, LlmAgent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models import LlmRequest, LlmResponse
    from google.adk.plugins.base_plugin import BasePlugin
    from google.adk.tools.tool_context import ToolContext
    from google.genai import types

    ADK_AVAILABLE = True
except ImportError:
    ADK_AVAILABLE = False
    Agent = None
    LlmAgent = None
    CallbackContext = None
    LlmRequest = None
    LlmResponse = None
    BasePlugin = None
    ToolContext = None
    types = None


class ConfigurationError(ValueError):
    """Raised when configuration parameters are invalid."""


class TextTooLargeError(ValueError):
    """Raised when input text exceeds the maximum allowed size."""

    def __init__(self, size: int, max_size: int, context: str = "input"):
        self.size = size
        self.max_size = max_size
        self.context = context
        super().__init__(
            f"{context.capitalize()} size ({size:,} bytes) exceeds "
            f"maximum ({max_size:,} bytes)"
        )


class ValidationTimeoutError(TimeoutError):
    """Raised when validation exceeds the timeout limit."""

    def __init__(self, timeout: float):
        self.timeout = timeout
        super().__init__(f"Validation timed out after {timeout:.1f} seconds")


class ThreadSafeDeque:
    """Thread-safe deque with maximum size limit.

    Provides a bounded, thread-safe collection for storing violations
    and other records with automatic oldest-first eviction.
    """

    def __init__(self, maxlen: int = DEFAULT_MAX_VIOLATIONS):
        self._deque: deque[dict[str, Any]] = deque(maxlen=maxlen)
        self._lock = threading.Lock()

    def append(self, item: dict[str, Any]) -> None:
        """Append item to deque, evicting oldest if full."""
        with self._lock:
            self._deque.append(item)

    def to_list(self) -> list[dict[str, Any]]:
        """Return a copy of all items as a list."""
        with self._lock:
            return list(self._deque)

    def clear(self) -> None:
        """Remove all items."""
        with self._lock:
            self._deque.clear()

    def __len__(self) -> int:
        with self._lock:
            return len(self._deque)


class SentinelLogger:
    """Simple logger protocol for Sentinel integration."""

    def debug(self, msg: str, *args: Any) -> None:
        """Log debug message."""
        pass

    def info(self, msg: str, *args: Any) -> None:
        """Log info message."""
        pass

    def warning(self, msg: str, *args: Any) -> None:
        """Log warning message."""
        pass

    def error(self, msg: str, *args: Any) -> None:
        """Log error message."""
        pass


class DefaultLogger(SentinelLogger):
    """Default logger using Python's logging module."""

    def __init__(self, name: str = "sentinel.google_adk"):
        self._logger = logging.getLogger(name)

    def debug(self, msg: str, *args: Any) -> None:
        self._logger.debug(msg, *args)

    def info(self, msg: str, *args: Any) -> None:
        self._logger.info(msg, *args)

    def warning(self, msg: str, *args: Any) -> None:
        self._logger.warning(msg, *args)

    def error(self, msg: str, *args: Any) -> None:
        self._logger.error(msg, *args)


# Module-level logger
_logger: SentinelLogger = DefaultLogger()


def get_logger() -> SentinelLogger:
    """Get the current logger instance."""
    return _logger


def set_logger(logger: SentinelLogger) -> None:
    """Set a custom logger instance."""
    global _logger
    _logger = logger


def require_adk() -> None:
    """Verify Google ADK is installed.

    Raises:
        ImportError: If Google ADK is not installed.
    """
    if not ADK_AVAILABLE:
        raise ImportError(
            "Google ADK is required for this integration. "
            "Install it with: pip install google-adk"
        )


def validate_configuration(
    max_text_size: int,
    validation_timeout: float,
    seed_level: str,
    fail_closed: bool,
    block_on_failure: bool,
    log_violations: bool,
) -> None:
    """Validate configuration parameters.

    Args:
        max_text_size: Maximum text size in bytes.
        validation_timeout: Timeout in seconds.
        seed_level: Safety level (minimal, standard, full).
        fail_closed: Whether to block on errors.
        block_on_failure: Whether to block on validation failures.
        log_violations: Whether to log violations.

    Raises:
        ConfigurationError: If any parameter is invalid.
    """
    if not isinstance(max_text_size, int) or max_text_size <= 0:
        raise ConfigurationError(
            f"max_text_size must be a positive integer, got {max_text_size}"
        )

    if not isinstance(validation_timeout, (int, float)) or validation_timeout <= 0:
        raise ConfigurationError(
            f"validation_timeout must be a positive number, got {validation_timeout}"
        )

    if seed_level.lower() not in VALID_SEED_LEVELS:
        raise ConfigurationError(
            f"seed_level must be one of {VALID_SEED_LEVELS}, got '{seed_level}'"
        )

    if not isinstance(fail_closed, bool):
        raise ConfigurationError(
            f"fail_closed must be a boolean, got {type(fail_closed).__name__}"
        )

    if not isinstance(block_on_failure, bool):
        raise ConfigurationError(
            f"block_on_failure must be a boolean, got {type(block_on_failure).__name__}"
        )

    if not isinstance(log_violations, bool):
        raise ConfigurationError(
            f"log_violations must be a boolean, got {type(log_violations).__name__}"
        )


def validate_text_size(text: str, max_size: int, context: str = "input") -> None:
    """Validate that text does not exceed maximum size.

    Args:
        text: Text to validate.
        max_size: Maximum allowed size in bytes.
        context: Context for error message (e.g., "input", "output").

    Raises:
        TextTooLargeError: If text exceeds max_size.
    """
    size = len(text.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size, context)


def extract_text_from_llm_request(llm_request: Any) -> str:
    """Extract text content from an LlmRequest.

    Handles various message formats in the LlmRequest.contents list.

    Args:
        llm_request: The LlmRequest object.

    Returns:
        Extracted text content, or empty string if none found.
    """
    if not hasattr(llm_request, "contents") or not llm_request.contents:
        return ""

    # Find the last user message
    for content in reversed(llm_request.contents):
        if hasattr(content, "role") and content.role == "user":
            if hasattr(content, "parts") and content.parts:
                parts_text = []
                for part in content.parts:
                    if hasattr(part, "text") and part.text:
                        parts_text.append(part.text)
                return " ".join(parts_text)

    # Fallback: try to get text from any content
    texts = []
    for content in llm_request.contents:
        if hasattr(content, "parts"):
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    texts.append(part.text)
    return " ".join(texts)


def extract_text_from_llm_response(llm_response: Any) -> str:
    """Extract text content from an LlmResponse.

    Args:
        llm_response: The LlmResponse object.

    Returns:
        Extracted text content, or empty string if none found.
    """
    if not llm_response:
        return ""

    # Try content attribute
    if hasattr(llm_response, "content"):
        content = llm_response.content
        if hasattr(content, "parts"):
            texts = []
            for part in content.parts:
                if hasattr(part, "text") and part.text:
                    texts.append(part.text)
            return " ".join(texts)
        if isinstance(content, str):
            return content

    # Try text attribute directly
    if hasattr(llm_response, "text") and llm_response.text:
        return llm_response.text

    return ""


def extract_tool_input_text(tool_args: dict[str, Any]) -> str:
    """Extract text content from tool arguments.

    Args:
        tool_args: Dictionary of tool arguments.

    Returns:
        Concatenated text from text-like arguments.
    """
    if not tool_args:
        return ""

    texts = []
    for key, value in tool_args.items():
        if isinstance(value, str):
            texts.append(value)
        elif isinstance(value, dict):
            # Recursively extract from nested dicts
            texts.append(extract_tool_input_text(value))
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, str):
                    texts.append(item)

    return " ".join(texts)


def create_blocked_response(message: str) -> Any:
    """Create an LlmResponse that blocks the request.

    Args:
        message: The message to include in the response.

    Returns:
        An LlmResponse object with the blocked message.

    Raises:
        ImportError: If ADK is not available.
    """
    require_adk()

    return LlmResponse(
        content=types.Content(
            role="model",
            parts=[types.Part(text=message)],
        )
    )


def create_empty_stats() -> dict[str, Any]:
    """Create an empty statistics dictionary.

    Returns:
        Dictionary with zeroed statistics.
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
    source: str = "unknown",
) -> dict[str, Any]:
    """Format a violation record for logging.

    Args:
        content: The content that was flagged.
        concerns: List of concerns identified.
        risk_level: Risk level (low, medium, high, critical).
        gates: THSP gate results.
        source: Source of the violation (model, tool, etc.).

    Returns:
        Formatted violation dictionary.
    """
    # Truncate content for logging (max 500 chars)
    preview = content[:500] + "..." if len(content) > 500 else content

    return {
        "content_preview": preview,
        "concerns": concerns,
        "risk_level": risk_level,
        "gates": gates,
        "source": source,
        "timestamp": time.time(),
    }


def log_fail_open_warning(component_name: str) -> None:
    """Log a warning about fail-open mode.

    Args:
        component_name: Name of the component in fail-open mode.
    """
    _logger.warning(
        "%s is running in fail-open mode. Validation errors will allow "
        "content through. Set fail_closed=True for security-critical "
        "applications.",
        component_name,
    )


class ValidationExecutor:
    """Executor for running validations with timeout support.

    Provides thread-based timeout execution for synchronous validation
    functions.
    """

    def __init__(self, max_workers: int = 4):
        self._max_workers = max_workers
        self._executor = None

    def _get_executor(self):
        """Lazy initialization of ThreadPoolExecutor."""
        if self._executor is None:
            from concurrent.futures import ThreadPoolExecutor
            self._executor = ThreadPoolExecutor(max_workers=self._max_workers)
        return self._executor

    def run_with_timeout(
        self,
        fn: Callable[..., Any],
        args: tuple = (),
        kwargs: dict | None = None,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    ) -> Any:
        """Run a function with timeout.

        Args:
            fn: Function to execute.
            args: Positional arguments.
            kwargs: Keyword arguments.
            timeout: Timeout in seconds.

        Returns:
            Function result.

        Raises:
            ValidationTimeoutError: If timeout is exceeded.
        """
        kwargs = kwargs or {}
        executor = self._get_executor()
        future = executor.submit(fn, *args, **kwargs)

        try:
            return future.result(timeout=timeout)
        except TimeoutError:
            future.cancel()
            raise ValidationTimeoutError(timeout)

    def shutdown(self) -> None:
        """Shutdown the executor."""
        if self._executor is not None:
            self._executor.shutdown(wait=False)
            self._executor = None


# Global validation executor
_validation_executor: ValidationExecutor | None = None


def get_validation_executor() -> ValidationExecutor:
    """Get or create the global validation executor."""
    global _validation_executor
    if _validation_executor is None:
        _validation_executor = ValidationExecutor()
    return _validation_executor


def shutdown_validation_executor() -> None:
    """Shutdown the global validation executor."""
    global _validation_executor
    if _validation_executor is not None:
        _validation_executor.shutdown()
        _validation_executor = None
