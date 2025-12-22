"""
Anthropic SDK integration for Sentinel AI.

Provides wrappers for the official Anthropic Python SDK that inject
Sentinel safety seeds and validate inputs/outputs using semantic LLM analysis.

This follows the official Anthropic SDK specification:
https://github.com/anthropics/anthropic-sdk-python

Usage:
    from sentinelseed.integrations.anthropic_sdk import SentinelAnthropic

    # Option 1: Use wrapper client (recommended)
    client = SentinelAnthropic(
        validation_model="claude-3-5-haiku-20241022",  # Model for validation
    )
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}]
    )

    # Option 2: Wrap existing client
    from anthropic import Anthropic
    from sentinelseed.integrations.anthropic_sdk import wrap_anthropic_client

    client = Anthropic()
    safe_client = wrap_anthropic_client(client)

    # Option 3: Just inject seed (no runtime validation)
    from sentinelseed.integrations.anthropic_sdk import inject_seed

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        system=inject_seed("You are a helpful assistant"),
        messages=[...]
    )
"""

from typing import Any, Dict, List, Optional, Tuple, Union, Iterator, AsyncIterator, Protocol
import os
import logging

from sentinelseed import Sentinel
from sentinelseed.validators.gates import THSPValidator


# Default validation model - using current Haiku model
DEFAULT_VALIDATION_MODEL = "claude-3-5-haiku-20241022"

# Default limits
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # 30 seconds


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


def _validate_text_size(
    text: str, max_size: int = DEFAULT_MAX_TEXT_SIZE, context: str = "text"
) -> None:
    """
    Validate text size against maximum limit.

    Args:
        text: Text to validate
        max_size: Maximum allowed size in bytes
        context: Context for error message

    Raises:
        TextTooLargeError: If text exceeds maximum size
    """
    if not text or not isinstance(text, str):
        return
    size = len(text.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size)


# Logger interface for custom logging
class SentinelLogger(Protocol):
    """Protocol for custom logger implementations."""

    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class DefaultLogger:
    """Default logger using Python's logging module."""

    def __init__(self, name: str = "sentinelseed.anthropic_sdk"):
        self._logger = logging.getLogger(name)

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)


# Module-level logger (can be replaced)
_logger: SentinelLogger = DefaultLogger()


def set_logger(logger: SentinelLogger) -> None:
    """
    Set a custom logger for the Anthropic SDK integration.

    Args:
        logger: Logger instance implementing SentinelLogger protocol

    Example:
        import logging

        class MyLogger:
            def debug(self, msg): logging.debug(f"[SENTINEL] {msg}")
            def info(self, msg): logging.info(f"[SENTINEL] {msg}")
            def warning(self, msg): logging.warning(f"[SENTINEL] {msg}")
            def error(self, msg): logging.error(f"[SENTINEL] {msg}")

        set_logger(MyLogger())
    """
    global _logger
    _logger = logger


def get_logger() -> SentinelLogger:
    """Get the current logger instance."""
    return _logger


# Import semantic validators (optional - may not be available)
try:
    from sentinelseed.validators.semantic import (
        SemanticValidator,
        AsyncSemanticValidator,
        THSPResult,
    )
    SEMANTIC_VALIDATOR_AVAILABLE = True
except ImportError:
    SemanticValidator = None
    AsyncSemanticValidator = None
    THSPResult = None
    SEMANTIC_VALIDATOR_AVAILABLE = False


# Check for Anthropic SDK availability
ANTHROPIC_AVAILABLE = False
_Anthropic = None
_AsyncAnthropic = None

try:
    from anthropic import Anthropic as _Anthropic, AsyncAnthropic as _AsyncAnthropic
    from anthropic.types import Message, MessageStreamEvent
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Message = None
    MessageStreamEvent = None


def inject_seed(
    system_prompt: Optional[str] = None,
    seed_level: str = "standard",
    sentinel: Optional[Sentinel] = None,
) -> str:
    """
    Inject Sentinel seed into a system prompt.

    Use this to add THSP safety guidelines to any system prompt
    before sending to the Anthropic API.

    This function does NOT require the Anthropic SDK to be installed.

    Args:
        system_prompt: Original system prompt (can be None)
        seed_level: Seed level to use ("minimal", "standard", "full")
        sentinel: Sentinel instance (creates default if None)

    Returns:
        System prompt with Sentinel seed prepended

    Example:
        from anthropic import Anthropic
        from sentinelseed.integrations.anthropic_sdk import inject_seed

        client = Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=inject_seed("You are a helpful coding assistant"),
            messages=[{"role": "user", "content": "Help me with Python"}]
        )
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)
    seed = sentinel.get_seed()

    if system_prompt:
        return f"{seed}\n\n---\n\n{system_prompt}"
    return seed


def _is_async_client(client: Any) -> bool:
    """
    Determine if a client is an async Anthropic client.

    Uses isinstance check when possible, falls back to class name check.
    """
    if _AsyncAnthropic is not None:
        if isinstance(client, _AsyncAnthropic):
            return True

    # Fallback: check if client has async methods
    if hasattr(client, 'messages'):
        messages = client.messages
        if hasattr(messages, 'create'):
            import asyncio
            return asyncio.iscoroutinefunction(messages.create)

    return False


def wrap_anthropic_client(
    client: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    enable_seed_injection: bool = True,
    validate_input: bool = True,
    validate_output: bool = True,
    validation_model: str = DEFAULT_VALIDATION_MODEL,
    use_heuristic_fallback: bool = True,
    logger: Optional[SentinelLogger] = None,
    block_unsafe_output: bool = False,
    fail_closed: bool = False,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
) -> "SentinelAnthropicWrapper":
    """
    Wrap an existing Anthropic client with Sentinel safety.

    Args:
        client: Anthropic or AsyncAnthropic client instance
        sentinel: Sentinel instance (creates default if None)
        seed_level: Seed level to use ("minimal", "standard", "full")
        enable_seed_injection: Whether to inject seed into system prompts
        validate_input: Whether to validate input messages
        validate_output: Whether to validate output messages
        validation_model: Model to use for semantic validation
        use_heuristic_fallback: Use local heuristic validation as fallback
        logger: Custom logger instance
        block_unsafe_output: Block response if output validation fails (default: False)
        fail_closed: Block on validation error instead of fail-open (default: False)
        validation_timeout: Timeout in seconds for semantic validation (default: 30.0)
        max_text_size: Maximum text size in bytes (default: 50KB)

    Returns:
        Wrapped client with Sentinel protection
    """
    return SentinelAnthropicWrapper(
        client=client,
        sentinel=sentinel,
        seed_level=seed_level,
        enable_seed_injection=enable_seed_injection,
        validate_input=validate_input,
        validate_output=validate_output,
        validation_model=validation_model,
        use_heuristic_fallback=use_heuristic_fallback,
        logger=logger,
        block_unsafe_output=block_unsafe_output,
        fail_closed=fail_closed,
        validation_timeout=validation_timeout,
        max_text_size=max_text_size,
    )


def _create_blocked_response(message: str, gate: Optional[str] = None) -> Dict[str, Any]:
    """Create a blocked response object."""
    return {
        "id": "blocked",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": message}],
        "model": "sentinel-blocked",
        "stop_reason": "sentinel_blocked",
        "sentinel_blocked": True,
        "sentinel_gate": gate,
    }


class BlockedStreamIterator:
    """
    Iterator that yields a single blocked event for stream responses.

    This provides consistent behavior between create() and stream()
    when input is blocked.
    """

    def __init__(self, message: str, gate: Optional[str] = None):
        self._message = message
        self._gate = gate
        self._yielded = False

    def __iter__(self):
        return self

    def __next__(self):
        if self._yielded:
            raise StopIteration
        self._yielded = True
        return _create_blocked_response(self._message, self._gate)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class AsyncBlockedStreamIterator:
    """Async version of BlockedStreamIterator."""

    def __init__(self, message: str, gate: Optional[str] = None):
        self._message = message
        self._gate = gate
        self._yielded = False

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._yielded:
            raise StopAsyncIteration
        self._yielded = True
        return _create_blocked_response(self._message, self._gate)

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class _SentinelMessages:
    """Wrapper for synchronous messages API with semantic validation."""

    def __init__(
        self,
        messages_api: Any,
        sentinel: Sentinel,
        enable_seed_injection: bool,
        validate_input: bool,
        validate_output: bool,
        semantic_validator: Optional[Any],
        heuristic_validator: Optional[THSPValidator],
        logger: SentinelLogger,
        block_unsafe_output: bool = False,
        fail_closed: bool = False,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    ):
        self._messages = messages_api
        self._sentinel = sentinel
        self._enable_seed_injection = enable_seed_injection
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._semantic_validator = semantic_validator
        self._heuristic_validator = heuristic_validator
        self._logger = logger
        self._seed = sentinel.get_seed()
        self._block_unsafe_output = block_unsafe_output
        self._fail_closed = fail_closed
        self._validation_timeout = validation_timeout
        self._max_text_size = max_text_size

    def _validate_content(self, content: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate content using heuristic and/or semantic validation.

        Returns:
            Tuple of (is_safe, violated_gate, reasoning)
        """
        # Track if at least one validation passed
        heuristic_passed = False
        semantic_passed = False
        semantic_error = False

        # First, validate text size
        try:
            _validate_text_size(content, self._max_text_size)
        except TextTooLargeError as e:
            return False, "scope", f"Text too large: {e}"

        # Then, try heuristic validation (fast, no API call)
        if self._heuristic_validator:
            result = self._heuristic_validator.validate(content)
            if not result["safe"]:
                failed_gates = [g for g, s in result["gates"].items() if s == "fail"]
                gate = failed_gates[0] if failed_gates else "unknown"
                issues = result.get("issues", [])
                reasoning = issues[0] if issues else "Heuristic validation failed"
                return False, gate, reasoning
            heuristic_passed = True

        # Then, try semantic validation (slower, uses API) with timeout
        if self._semantic_validator:
            import concurrent.futures

            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(
                        self._semantic_validator.validate_request, content
                    )
                    result = future.result(timeout=self._validation_timeout)
                    if not result.is_safe:
                        return False, result.violated_gate, result.reasoning
                    semantic_passed = True
            except concurrent.futures.TimeoutError:
                self._logger.error(
                    f"Semantic validation timed out after {self._validation_timeout}s"
                )
                semantic_error = True
                if self._fail_closed:
                    return False, "timeout", f"Validation timed out after {self._validation_timeout}s"
                # Fail-open: continue only if heuristic passed
            except Exception as e:
                self._logger.error(f"Semantic validation error: {e}")
                semantic_error = True
                if self._fail_closed:
                    return False, "error", f"Validation error: {e}"
                # Fail-open: continue only if heuristic passed

        # Determine final result based on what passed
        if not self._heuristic_validator and not self._semantic_validator:
            # No validators configured, pass through
            return True, None, None

        if semantic_passed or heuristic_passed:
            # At least one validation passed
            return True, None, None

        # Semantic failed/timed out and heuristic was not configured
        # This means no validation actually passed
        if semantic_error and not heuristic_passed:
            return False, "validation_incomplete", "Semantic validation failed and no heuristic fallback available"

        return True, None, None

    def create(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Create a message with Sentinel validation.

        Args:
            model: Model to use
            max_tokens: Maximum tokens in response
            messages: Conversation messages
            system: System prompt (seed will be prepended)
            **kwargs: Additional API parameters

        Returns:
            Message response from API, or blocked response if validation fails
        """
        # Validate input messages
        if self._validate_input:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    is_safe, gate, reasoning = self._validate_content(content)
                    if not is_safe:
                        self._logger.warning(f"Input blocked: {gate} - {reasoning}")
                        return _create_blocked_response(
                            f"Input blocked by Sentinel THSP validation. "
                            f"Gate failed: {gate}. "
                            f"Reason: {reasoning}",
                            gate=gate,
                        )

        # Inject seed into system prompt
        if self._enable_seed_injection:
            if system:
                system = f"{self._seed}\n\n---\n\n{system}"
            else:
                system = self._seed

        # Make API call
        response = self._messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system,
            **kwargs,
        )

        # Validate output
        if self._validate_output and hasattr(response, 'content'):
            for block in response.content:
                if hasattr(block, 'text'):
                    is_safe, gate, reasoning = self._validate_content(block.text)
                    if not is_safe:
                        self._logger.warning(
                            f"Output validation concern: {gate} - {reasoning}"
                        )
                        if self._block_unsafe_output:
                            return _create_blocked_response(
                                f"Output blocked by Sentinel THSP validation. "
                                f"Gate failed: {gate}. "
                                f"Reason: {reasoning}",
                                gate=gate,
                            )

        return response

    def stream(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        **kwargs,
    ) -> Iterator[Any]:
        """
        Stream a message with Sentinel validation.

        Returns a blocked iterator if input validation fails,
        otherwise streams the response.
        """
        # Validate input
        if self._validate_input:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    is_safe, gate, reasoning = self._validate_content(content)
                    if not is_safe:
                        self._logger.warning(f"Stream input blocked: {gate} - {reasoning}")
                        return BlockedStreamIterator(
                            f"Input blocked by Sentinel. "
                            f"Gate: {gate}. "
                            f"Reason: {reasoning}",
                            gate=gate,
                        )

        # Inject seed
        if self._enable_seed_injection:
            if system:
                system = f"{self._seed}\n\n---\n\n{system}"
            else:
                system = self._seed

        # Stream response
        return self._messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system,
            **kwargs,
        )


class _SentinelAsyncMessages:
    """Wrapper for async messages API with semantic validation."""

    def __init__(
        self,
        messages_api: Any,
        sentinel: Sentinel,
        enable_seed_injection: bool,
        validate_input: bool,
        validate_output: bool,
        semantic_validator: Optional[Any],
        heuristic_validator: Optional[THSPValidator],
        logger: SentinelLogger,
        block_unsafe_output: bool = False,
        fail_closed: bool = False,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    ):
        self._messages = messages_api
        self._sentinel = sentinel
        self._enable_seed_injection = enable_seed_injection
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._semantic_validator = semantic_validator
        self._heuristic_validator = heuristic_validator
        self._logger = logger
        self._seed = sentinel.get_seed()
        self._block_unsafe_output = block_unsafe_output
        self._fail_closed = fail_closed
        self._validation_timeout = validation_timeout
        self._max_text_size = max_text_size

    async def _validate_content(self, content: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate content using heuristic and/or semantic validation.

        Returns:
            Tuple of (is_safe, violated_gate, reasoning)
        """
        import asyncio

        # Track if at least one validation passed
        heuristic_passed = False
        semantic_passed = False
        semantic_error = False

        # First, validate text size
        try:
            _validate_text_size(content, self._max_text_size)
        except TextTooLargeError as e:
            return False, "scope", f"Text too large: {e}"

        # Then, try heuristic validation (fast, no API call)
        if self._heuristic_validator:
            result = self._heuristic_validator.validate(content)
            if not result["safe"]:
                failed_gates = [g for g, s in result["gates"].items() if s == "fail"]
                gate = failed_gates[0] if failed_gates else "unknown"
                issues = result.get("issues", [])
                reasoning = issues[0] if issues else "Heuristic validation failed"
                return False, gate, reasoning
            heuristic_passed = True

        # Then, try semantic validation (slower, uses API) with timeout
        if self._semantic_validator:
            try:
                result = await asyncio.wait_for(
                    self._semantic_validator.validate_request(content),
                    timeout=self._validation_timeout,
                )
                if not result.is_safe:
                    return False, result.violated_gate, result.reasoning
                semantic_passed = True
            except asyncio.TimeoutError:
                self._logger.error(
                    f"Async semantic validation timed out after {self._validation_timeout}s"
                )
                semantic_error = True
                if self._fail_closed:
                    return False, "timeout", f"Validation timed out after {self._validation_timeout}s"
                # Fail-open: continue only if heuristic passed
            except Exception as e:
                self._logger.error(f"Async semantic validation error: {e}")
                semantic_error = True
                if self._fail_closed:
                    return False, "error", f"Validation error: {e}"
                # Fail-open: continue only if heuristic passed

        # Determine final result based on what passed
        if not self._heuristic_validator and not self._semantic_validator:
            # No validators configured, pass through
            return True, None, None

        if semantic_passed or heuristic_passed:
            # At least one validation passed
            return True, None, None

        # Semantic failed/timed out and heuristic was not configured
        # This means no validation actually passed
        if semantic_error and not heuristic_passed:
            return False, "validation_incomplete", "Semantic validation failed and no heuristic fallback available"

        return True, None, None

    async def create(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Async create message with Sentinel validation."""
        # Validate input messages
        if self._validate_input:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    is_safe, gate, reasoning = await self._validate_content(content)
                    if not is_safe:
                        self._logger.warning(f"Input blocked: {gate} - {reasoning}")
                        return _create_blocked_response(
                            f"Input blocked by Sentinel THSP validation. "
                            f"Gate failed: {gate}. "
                            f"Reason: {reasoning}",
                            gate=gate,
                        )

        # Inject seed
        if self._enable_seed_injection:
            if system:
                system = f"{self._seed}\n\n---\n\n{system}"
            else:
                system = self._seed

        # Make API call
        response = await self._messages.create(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system,
            **kwargs,
        )

        # Validate output
        if self._validate_output and hasattr(response, 'content'):
            for block in response.content:
                if hasattr(block, 'text'):
                    is_safe, gate, reasoning = await self._validate_content(block.text)
                    if not is_safe:
                        self._logger.warning(
                            f"Output validation concern: {gate} - {reasoning}"
                        )
                        if self._block_unsafe_output:
                            return _create_blocked_response(
                                f"Output blocked by Sentinel THSP validation. "
                                f"Gate failed: {gate}. "
                                f"Reason: {reasoning}",
                                gate=gate,
                            )

        return response

    async def stream(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        **kwargs,
    ) -> AsyncIterator[Any]:
        """
        Async stream message with Sentinel validation.

        Returns an async blocked iterator if input validation fails.
        """
        # Validate input
        if self._validate_input:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    is_safe, gate, reasoning = await self._validate_content(content)
                    if not is_safe:
                        self._logger.warning(f"Stream input blocked: {gate} - {reasoning}")
                        return AsyncBlockedStreamIterator(
                            f"Input blocked by Sentinel. "
                            f"Gate: {gate}. "
                            f"Reason: {reasoning}",
                            gate=gate,
                        )

        # Inject seed
        if self._enable_seed_injection:
            if system:
                system = f"{self._seed}\n\n---\n\n{system}"
            else:
                system = self._seed

        # Stream response
        return self._messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system,
            **kwargs,
        )


class SentinelAnthropic:
    """
    Sentinel-wrapped Anthropic client with semantic validation.

    Drop-in replacement for the Anthropic client that automatically
    injects Sentinel safety seeds and validates messages using LLM analysis.

    Example:
        from sentinelseed.integrations.anthropic_sdk import SentinelAnthropic

        client = SentinelAnthropic()

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello, Claude"}]
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        enable_seed_injection: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validation_model: str = DEFAULT_VALIDATION_MODEL,
        use_heuristic_fallback: bool = True,
        logger: Optional[SentinelLogger] = None,
        block_unsafe_output: bool = False,
        fail_closed: bool = False,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        **kwargs,
    ):
        """
        Initialize Sentinel Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level to use ("minimal", "standard", "full")
            enable_seed_injection: Whether to inject seed into system prompts
            validate_input: Whether to validate input messages (semantic LLM)
            validate_output: Whether to validate output messages (semantic LLM)
            validation_model: Model to use for semantic validation
            use_heuristic_fallback: Use local heuristic validation as fallback/complement
            logger: Custom logger instance
            block_unsafe_output: Block response if output validation fails (default: False)
            fail_closed: Block on validation error instead of fail-open (default: False)
            validation_timeout: Timeout in seconds for semantic validation (default: 30.0)
            max_text_size: Maximum text size in bytes (default: 50KB)
            **kwargs: Additional arguments for Anthropic client
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = _Anthropic(api_key=self._api_key, **kwargs)
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._enable_seed_injection = enable_seed_injection
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._validation_model = validation_model
        self._logger = logger or _logger
        self._block_unsafe_output = block_unsafe_output
        self._fail_closed = fail_closed
        self._validation_timeout = validation_timeout
        self._max_text_size = max_text_size

        # Heuristic validator (always available, no API calls)
        self._heuristic_validator = THSPValidator() if use_heuristic_fallback else None

        # Semantic validator using Anthropic (optional)
        self._semantic_validator = None
        if (validate_input or validate_output) and SEMANTIC_VALIDATOR_AVAILABLE:
            try:
                self._semantic_validator = SemanticValidator(
                    provider="anthropic",
                    model=validation_model,
                    api_key=self._api_key,
                )
            except Exception as e:
                self._logger.warning(f"Could not initialize semantic validator: {e}")

        # Create messages wrapper
        self.messages = _SentinelMessages(
            self._client.messages,
            self._sentinel,
            self._enable_seed_injection,
            self._validate_input,
            self._validate_output,
            self._semantic_validator,
            self._heuristic_validator,
            self._logger,
            block_unsafe_output=block_unsafe_output,
            fail_closed=fail_closed,
            validation_timeout=validation_timeout,
            max_text_size=max_text_size,
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped client."""
        return getattr(self._client, name)


class SentinelAsyncAnthropic:
    """
    Sentinel-wrapped async Anthropic client with semantic validation.

    Async version of SentinelAnthropic for use with asyncio.

    Example:
        from sentinelseed.integrations.anthropic_sdk import SentinelAsyncAnthropic

        client = SentinelAsyncAnthropic()

        message = await client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello, Claude"}]
        )
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        enable_seed_injection: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validation_model: str = DEFAULT_VALIDATION_MODEL,
        use_heuristic_fallback: bool = True,
        logger: Optional[SentinelLogger] = None,
        block_unsafe_output: bool = False,
        fail_closed: bool = False,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        **kwargs,
    ):
        """
        Initialize async Sentinel Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level to use ("minimal", "standard", "full")
            enable_seed_injection: Whether to inject seed into system prompts
            validate_input: Whether to validate input messages (semantic LLM)
            validate_output: Whether to validate output messages (semantic LLM)
            validation_model: Model to use for semantic validation
            use_heuristic_fallback: Use local heuristic validation as fallback/complement
            logger: Custom logger instance
            block_unsafe_output: Block response if output validation fails (default: False)
            fail_closed: Block on validation error instead of fail-open (default: False)
            validation_timeout: Timeout in seconds for semantic validation (default: 30.0)
            max_text_size: Maximum text size in bytes (default: 50KB)
            **kwargs: Additional arguments for Anthropic client
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = _AsyncAnthropic(api_key=self._api_key, **kwargs)
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._enable_seed_injection = enable_seed_injection
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._validation_model = validation_model
        self._logger = logger or _logger
        self._block_unsafe_output = block_unsafe_output
        self._fail_closed = fail_closed
        self._validation_timeout = validation_timeout
        self._max_text_size = max_text_size

        # Heuristic validator
        self._heuristic_validator = THSPValidator() if use_heuristic_fallback else None

        # Async semantic validator
        self._semantic_validator = None
        if (validate_input or validate_output) and SEMANTIC_VALIDATOR_AVAILABLE:
            try:
                self._semantic_validator = AsyncSemanticValidator(
                    provider="anthropic",
                    model=validation_model,
                    api_key=self._api_key,
                )
            except Exception as e:
                self._logger.warning(f"Could not initialize async semantic validator: {e}")

        # Create async messages wrapper
        self.messages = _SentinelAsyncMessages(
            self._client.messages,
            self._sentinel,
            self._enable_seed_injection,
            self._validate_input,
            self._validate_output,
            self._semantic_validator,
            self._heuristic_validator,
            self._logger,
            block_unsafe_output=block_unsafe_output,
            fail_closed=fail_closed,
            validation_timeout=validation_timeout,
            max_text_size=max_text_size,
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped client."""
        return getattr(self._client, name)


class SentinelAnthropicWrapper:
    """
    Generic wrapper for existing Anthropic clients with semantic validation.

    Used by wrap_anthropic_client() to wrap any Anthropic client instance.
    Supports both sync and async clients.

    Example:
        from anthropic import Anthropic, AsyncAnthropic
        from sentinelseed.integrations.anthropic_sdk import SentinelAnthropicWrapper

        # Wrap sync client
        client = Anthropic()
        wrapped = SentinelAnthropicWrapper(client)

        # Wrap async client
        async_client = AsyncAnthropic()
        wrapped_async = SentinelAnthropicWrapper(async_client)
    """

    def __init__(
        self,
        client: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        enable_seed_injection: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validation_model: str = DEFAULT_VALIDATION_MODEL,
        use_heuristic_fallback: bool = True,
        logger: Optional[SentinelLogger] = None,
        block_unsafe_output: bool = False,
        fail_closed: bool = False,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    ):
        self._client = client
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._enable_seed_injection = enable_seed_injection
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._logger = logger or _logger
        self._block_unsafe_output = block_unsafe_output
        self._fail_closed = fail_closed
        self._validation_timeout = validation_timeout
        self._max_text_size = max_text_size

        # Get API key from client or environment
        api_key = getattr(client, '_api_key', None) or os.environ.get("ANTHROPIC_API_KEY")

        # Determine if async client using robust check
        is_async = _is_async_client(client)

        # Heuristic validator
        heuristic_validator = THSPValidator() if use_heuristic_fallback else None

        # Create appropriate validator and messages wrapper
        if is_async:
            semantic_validator = None
            if (validate_input or validate_output) and SEMANTIC_VALIDATOR_AVAILABLE:
                try:
                    semantic_validator = AsyncSemanticValidator(
                        provider="anthropic",
                        model=validation_model,
                        api_key=api_key,
                    )
                except Exception as e:
                    self._logger.warning(f"Could not initialize async semantic validator: {e}")

            self.messages = _SentinelAsyncMessages(
                client.messages,
                self._sentinel,
                self._enable_seed_injection,
                self._validate_input,
                self._validate_output,
                semantic_validator,
                heuristic_validator,
                self._logger,
                block_unsafe_output=block_unsafe_output,
                fail_closed=fail_closed,
                validation_timeout=validation_timeout,
                max_text_size=max_text_size,
            )
        else:
            semantic_validator = None
            if (validate_input or validate_output) and SEMANTIC_VALIDATOR_AVAILABLE:
                try:
                    semantic_validator = SemanticValidator(
                        provider="anthropic",
                        model=validation_model,
                        api_key=api_key,
                    )
                except Exception as e:
                    self._logger.warning(f"Could not initialize semantic validator: {e}")

            self.messages = _SentinelMessages(
                client.messages,
                self._sentinel,
                self._enable_seed_injection,
                self._validate_input,
                self._validate_output,
                semantic_validator,
                heuristic_validator,
                self._logger,
                block_unsafe_output=block_unsafe_output,
                fail_closed=fail_closed,
                validation_timeout=validation_timeout,
                max_text_size=max_text_size,
            )

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped client."""
        return getattr(self._client, name)


def create_safe_client(
    api_key: Optional[str] = None,
    seed_level: str = "standard",
    async_client: bool = False,
    validation_model: str = DEFAULT_VALIDATION_MODEL,
    use_heuristic_fallback: bool = True,
    logger: Optional[SentinelLogger] = None,
    block_unsafe_output: bool = False,
    fail_closed: bool = False,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
) -> Union[SentinelAnthropic, SentinelAsyncAnthropic]:
    """
    Create a Sentinel-protected Anthropic client.

    Convenience function for the most common use case.

    Args:
        api_key: Anthropic API key
        seed_level: Seed level to use ("minimal", "standard", "full")
        async_client: Whether to create async client
        validation_model: Model to use for semantic validation
        use_heuristic_fallback: Use local heuristic validation
        logger: Custom logger instance
        block_unsafe_output: Block response if output validation fails (default: False)
        fail_closed: Block on validation error instead of fail-open (default: False)
        validation_timeout: Timeout in seconds for semantic validation (default: 30.0)
        max_text_size: Maximum text size in bytes (default: 50KB)

    Returns:
        SentinelAnthropic or SentinelAsyncAnthropic instance

    Example:
        from sentinelseed.integrations.anthropic_sdk import create_safe_client

        client = create_safe_client()
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": "Hello!"}]
        )
    """
    if async_client:
        return SentinelAsyncAnthropic(
            api_key=api_key,
            seed_level=seed_level,
            validation_model=validation_model,
            use_heuristic_fallback=use_heuristic_fallback,
            logger=logger,
            block_unsafe_output=block_unsafe_output,
            fail_closed=fail_closed,
            validation_timeout=validation_timeout,
            max_text_size=max_text_size,
        )
    return SentinelAnthropic(
        api_key=api_key,
        seed_level=seed_level,
        validation_model=validation_model,
        use_heuristic_fallback=use_heuristic_fallback,
        logger=logger,
        block_unsafe_output=block_unsafe_output,
        fail_closed=fail_closed,
        validation_timeout=validation_timeout,
        max_text_size=max_text_size,
    )


__all__ = [
    # Main classes
    "SentinelAnthropic",
    "SentinelAsyncAnthropic",
    "SentinelAnthropicWrapper",
    # Functions
    "wrap_anthropic_client",
    "inject_seed",
    "create_safe_client",
    # Logging
    "SentinelLogger",
    "set_logger",
    "get_logger",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
    # Constants
    "ANTHROPIC_AVAILABLE",
    "SEMANTIC_VALIDATOR_AVAILABLE",
    "DEFAULT_VALIDATION_MODEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
]
