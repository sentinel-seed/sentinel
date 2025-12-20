"""
Utility functions for OpenAI Agents SDK integration.

Provides logging, constants, and helper functions.
"""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from typing import Any, Callable, Optional, Protocol, Union


# Default max input size (characters) to prevent token limit issues
DEFAULT_MAX_INPUT_SIZE = 32000

# Default max violations to keep in memory
DEFAULT_MAX_VIOLATIONS_LOG = 1000

# Default validation timeout in seconds
DEFAULT_VALIDATION_TIMEOUT = 30.0


class SentinelLogger(Protocol):
    """Protocol for custom logger implementations."""

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        ...

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        ...

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        ...

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        ...


class DefaultLogger:
    """
    Default logger implementation with sanitization.

    Truncates sensitive content and redacts potential PII patterns.
    """

    def __init__(
        self,
        name: str = "sentinel.openai_agents",
        level: int = logging.INFO,
        max_content_length: int = 200,
        redact_patterns: bool = True,
    ):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(level)
        self._max_content_length = max_content_length
        self._redact_patterns = redact_patterns

        # PII patterns to redact
        self._pii_patterns = [
            (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
            (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE]'),
            (re.compile(r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'), '[SSN]'),
            (re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b'), '[CARD]'),
            (re.compile(r'\b(?:sk-|pk-)[a-zA-Z0-9]{32,}\b'), '[API_KEY]'),
        ]

        # Add handler if none exists
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(
                logging.Formatter('[SENTINEL] %(levelname)s: %(message)s')
            )
            self._logger.addHandler(handler)

    def _sanitize(self, msg: str) -> str:
        """Sanitize message by truncating and redacting PII."""
        if not msg:
            return msg

        # Truncate long content
        if len(msg) > self._max_content_length:
            msg = msg[:self._max_content_length] + f"... [truncated, {len(msg)} chars total]"

        # Redact PII patterns
        if self._redact_patterns:
            for pattern, replacement in self._pii_patterns:
                msg = pattern.sub(replacement, msg)

        return msg

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.info(self._sanitize(msg), *args, **kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(self._sanitize(msg), *args, **kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.error(self._sanitize(msg), *args, **kwargs)

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(self._sanitize(msg), *args, **kwargs)


# Module-level logger instance with thread-safe access
_logger: Optional[SentinelLogger] = None
_logger_lock = threading.Lock()


def get_logger() -> SentinelLogger:
    """
    Get the current logger instance (thread-safe).

    Uses double-checked locking pattern for efficiency.
    """
    global _logger
    if _logger is None:
        with _logger_lock:
            # Double-check after acquiring lock
            if _logger is None:
                _logger = DefaultLogger()
    return _logger


def set_logger(logger: SentinelLogger) -> None:
    """
    Set a custom logger implementation (thread-safe).

    Args:
        logger: Logger implementing the SentinelLogger protocol

    Example:
        import logging

        custom_logger = logging.getLogger("my_app.sentinel")
        set_logger(custom_logger)
    """
    global _logger
    with _logger_lock:
        _logger = logger


def require_agents_sdk() -> None:
    """
    Raise ImportError if OpenAI Agents SDK is not installed.

    Call this at the start of functions that require the SDK.
    """
    try:
        import agents  # noqa: F401
    except ImportError:
        raise ImportError(
            "openai-agents package not installed. "
            "Install with: pip install openai-agents"
        )


def truncate_text(text: str, max_length: int = DEFAULT_MAX_INPUT_SIZE) -> str:
    """
    Truncate text to maximum length with indicator.

    Args:
        text: Text to truncate
        max_length: Maximum character length

    Returns:
        Truncated text with indicator if truncated
    """
    if len(text) <= max_length:
        return text

    return text[:max_length] + f"\n\n[Content truncated: {len(text)} chars total, showing first {max_length}]"


def extract_text_from_input(input_data: Any) -> str:
    """
    Extract text content from various input formats.

    Handles strings, lists of messages, dicts, and objects with content attributes.
    Returns empty string for None or empty input.

    Args:
        input_data: Input in any supported format

    Returns:
        Extracted text as string (empty string if input is None/empty)
    """
    # Handle None and empty cases
    if input_data is None:
        return ""

    if isinstance(input_data, str):
        return input_data

    if isinstance(input_data, list):
        if not input_data:  # Empty list
            return ""
        text_parts = []
        for item in input_data:
            if item is None:
                continue
            if hasattr(item, "content"):
                content = item.content
                if content is not None:
                    text_parts.append(str(content))
            elif isinstance(item, dict) and "content" in item:
                content = item["content"]
                if content is not None:
                    text_parts.append(str(content))
            elif isinstance(item, str):
                text_parts.append(item)
            else:
                text_parts.append(str(item))
        return " ".join(text_parts)

    if hasattr(input_data, "content"):
        content = input_data.content
        return str(content) if content is not None else ""

    if hasattr(input_data, "text"):
        text = input_data.text
        return str(text) if text is not None else ""

    if isinstance(input_data, dict):
        content = input_data.get("content", input_data.get("text"))
        if content is not None:
            return str(content)
        # If content/text is None or not present, return empty string
        # rather than stringifying the dict
        return ""

    return str(input_data)
