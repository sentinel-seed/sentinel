"""
Retry Logic for Sentinel API Calls.

Implements exponential backoff with jitter for resilient API calls.
Differentiates between retriable errors (rate limits, timeouts) and
non-retriable errors (authentication, invalid requests).

Example:
    from sentinelseed.core.retry import RetryConfig, with_retry

    config = RetryConfig(
        max_attempts=3,
        initial_delay=1.0,
        max_delay=30.0,
    )

    @with_retry(config)
    def call_api():
        ...
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from typing import Callable, Optional, Set, Type, TypeVar, Any

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
    before_sleep_log,
    RetryError,
)

logger = logging.getLogger("sentinelseed.core.retry")

T = TypeVar("T")


class RetryableErrorType(Enum):
    """Classification of API errors for retry decisions."""

    RATE_LIMIT = "rate_limit"  # 429 - always retry with backoff
    TIMEOUT = "timeout"  # Request timeout - retry
    SERVER_ERROR = "server_error"  # 5xx - retry
    CONNECTION_ERROR = "connection_error"  # Network issues - retry
    AUTHENTICATION = "authentication"  # 401/403 - never retry
    INVALID_REQUEST = "invalid_request"  # 400 - never retry
    UNKNOWN = "unknown"  # Classify as retriable by default


# Exceptions that should trigger retry
RETRIABLE_EXCEPTIONS: Set[str] = {
    # OpenAI
    "RateLimitError",
    "APITimeoutError",
    "APIConnectionError",
    "InternalServerError",
    # Anthropic
    "RateLimitError",
    "APIConnectionError",
    "InternalServerError",
    # Generic
    "Timeout",
    "ConnectionError",
    "TimeoutError",
}

# Exceptions that should NOT trigger retry
NON_RETRIABLE_EXCEPTIONS: Set[str] = {
    # OpenAI
    "AuthenticationError",
    "PermissionDeniedError",
    "BadRequestError",
    "NotFoundError",
    # Anthropic
    "AuthenticationError",
    "PermissionDeniedError",
    "BadRequestError",
}


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.

    Attributes:
        enabled: Whether retry is enabled
        max_attempts: Maximum number of attempts (including initial)
        initial_delay: Initial delay in seconds before first retry
        max_delay: Maximum delay in seconds between retries
        exponential_base: Base for exponential backoff (default 2)
        jitter: Add randomness to delays to prevent thundering herd

    Example delays with default config (base=2, initial=1, max=30):
        Attempt 1: immediate
        Attempt 2: ~1-2s delay
        Attempt 3: ~2-4s delay
        Attempt 4: ~4-8s delay
        Attempt 5: ~8-16s delay (capped at max_delay)
    """

    enabled: bool = True
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        """Validate configuration."""
        if self.max_attempts < 1:
            raise ValueError("max_attempts must be at least 1")
        if self.initial_delay < 0:
            raise ValueError("initial_delay must be non-negative")
        if self.max_delay < self.initial_delay:
            raise ValueError("max_delay must be >= initial_delay")
        if self.exponential_base < 1:
            raise ValueError("exponential_base must be >= 1")


# Default configurations for different scenarios
DEFAULT_RETRY_CONFIG = RetryConfig()

AGGRESSIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=5,
    initial_delay=0.5,
    max_delay=60.0,
)

CONSERVATIVE_RETRY_CONFIG = RetryConfig(
    max_attempts=2,
    initial_delay=2.0,
    max_delay=10.0,
)

NO_RETRY_CONFIG = RetryConfig(enabled=False)


@dataclass
class RetryStats:
    """Statistics about retry attempts."""

    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_retries: int = 0
    retries_by_error_type: dict = field(default_factory=dict)

    def record_success(self, attempts: int) -> None:
        """Record a successful call."""
        self.total_calls += 1
        self.successful_calls += 1
        self.total_retries += max(0, attempts - 1)

    def record_failure(self, attempts: int, error_type: str) -> None:
        """Record a failed call."""
        self.total_calls += 1
        self.failed_calls += 1
        self.total_retries += max(0, attempts - 1)
        self.retries_by_error_type[error_type] = (
            self.retries_by_error_type.get(error_type, 0) + 1
        )

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls

    @property
    def avg_retries_per_call(self) -> float:
        """Calculate average retries per call."""
        if self.total_calls == 0:
            return 0.0
        return self.total_retries / self.total_calls


def classify_error(exception: Exception) -> RetryableErrorType:
    """
    Classify an exception to determine if it should be retried.

    Args:
        exception: The exception to classify

    Returns:
        RetryableErrorType indicating how to handle the error
    """
    error_name = type(exception).__name__

    # Check for rate limit (special handling)
    if "RateLimit" in error_name or "429" in str(exception):
        return RetryableErrorType.RATE_LIMIT

    # Check for timeout
    if "Timeout" in error_name or "timeout" in str(exception).lower():
        return RetryableErrorType.TIMEOUT

    # Check for server errors
    if "InternalServer" in error_name or "5" in str(getattr(exception, "status_code", "")):
        return RetryableErrorType.SERVER_ERROR

    # Check for connection errors
    if "Connection" in error_name:
        return RetryableErrorType.CONNECTION_ERROR

    # Check for authentication errors
    if "Authentication" in error_name or "Permission" in error_name:
        return RetryableErrorType.AUTHENTICATION

    # Check for invalid request
    if "BadRequest" in error_name or "NotFound" in error_name:
        return RetryableErrorType.INVALID_REQUEST

    return RetryableErrorType.UNKNOWN


def is_retriable(exception: Exception) -> bool:
    """
    Determine if an exception should trigger a retry.

    Args:
        exception: The exception to check

    Returns:
        True if the exception is retriable, False otherwise
    """
    error_type = classify_error(exception)
    return error_type in {
        RetryableErrorType.RATE_LIMIT,
        RetryableErrorType.TIMEOUT,
        RetryableErrorType.SERVER_ERROR,
        RetryableErrorType.CONNECTION_ERROR,
        RetryableErrorType.UNKNOWN,  # Retry unknown errors by default
    }


def create_retry_decorator(config: RetryConfig):
    """
    Create a tenacity retry decorator with the given configuration.

    Args:
        config: RetryConfig with retry parameters

    Returns:
        A decorator that can be applied to functions
    """
    if not config.enabled:
        # Return identity decorator if retry is disabled
        def no_retry(func):
            return func
        return no_retry

    return retry(
        stop=stop_after_attempt(config.max_attempts),
        wait=wait_exponential_jitter(
            initial=config.initial_delay,
            max=config.max_delay,
            exp_base=config.exponential_base,
            jitter=config.initial_delay if config.jitter else 0,
        ),
        retry=retry_if_exception_type(Exception),  # Filter in before_sleep
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )


class RetryableAPICall:
    """
    Context manager and decorator for retriable API calls.

    Provides retry logic with exponential backoff, proper error classification,
    and statistics tracking.

    Example as decorator:
        @RetryableAPICall(config)
        def call_api():
            ...

    Example as context manager:
        with RetryableAPICall(config) as retry_ctx:
            result = retry_ctx.execute(call_api, *args, **kwargs)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """
        Initialize with retry configuration.

        Args:
            config: RetryConfig, uses DEFAULT_RETRY_CONFIG if None
        """
        self.config = config or DEFAULT_RETRY_CONFIG
        self.stats = RetryStats()
        self._current_attempt = 0

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Use as decorator."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return self.execute(func, *args, **kwargs)
        return wrapper

    def __enter__(self) -> "RetryableAPICall":
        """Use as context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager."""
        return False  # Don't suppress exceptions

    def execute(self, func: Callable[..., T], *args, **kwargs) -> T:
        """
        Execute a function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            Exception: The last exception if all retries fail
        """
        if not self.config.enabled:
            return func(*args, **kwargs)

        last_exception: Optional[Exception] = None
        self._current_attempt = 0

        for attempt in range(1, self.config.max_attempts + 1):
            self._current_attempt = attempt

            try:
                result = func(*args, **kwargs)
                self.stats.record_success(attempt)
                return result

            except Exception as e:
                last_exception = e
                error_type = classify_error(e)

                # Check if we should retry
                if not is_retriable(e):
                    logger.warning(
                        f"Non-retriable error on attempt {attempt}: "
                        f"{error_type.value} - {type(e).__name__}: {e}"
                    )
                    self.stats.record_failure(attempt, error_type.value)
                    raise

                # Check if we have more attempts
                if attempt >= self.config.max_attempts:
                    logger.error(
                        f"All {self.config.max_attempts} attempts failed: "
                        f"{type(e).__name__}: {e}"
                    )
                    self.stats.record_failure(attempt, error_type.value)
                    raise

                # Calculate delay with exponential backoff
                delay = self._calculate_delay(attempt)

                logger.warning(
                    f"Attempt {attempt}/{self.config.max_attempts} failed: "
                    f"{error_type.value} - {type(e).__name__}. "
                    f"Retrying in {delay:.2f}s..."
                )

                # Wait before retry
                import time
                time.sleep(delay)

        # Should not reach here, but just in case
        if last_exception:
            raise last_exception
        raise RuntimeError("Retry loop ended without result or exception")

    def _calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay before next retry using exponential backoff.

        Args:
            attempt: Current attempt number (1-indexed)

        Returns:
            Delay in seconds
        """
        # Exponential backoff: initial * base^(attempt-1)
        delay = self.config.initial_delay * (
            self.config.exponential_base ** (attempt - 1)
        )

        # Cap at max delay
        delay = min(delay, self.config.max_delay)

        # Add jitter if enabled (±25%)
        if self.config.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)


def with_retry(
    config: Optional[RetryConfig] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator to add retry logic to a function.

    Args:
        config: RetryConfig, uses DEFAULT_RETRY_CONFIG if None

    Returns:
        Decorator function

    Example:
        @with_retry(RetryConfig(max_attempts=5))
        def call_external_api():
            ...
    """
    retry_handler = RetryableAPICall(config)
    return retry_handler
