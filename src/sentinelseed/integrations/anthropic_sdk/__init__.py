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
        validation_model="claude-3-haiku-20240307",  # Model for validation
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

from typing import Any, Dict, List, Optional, Union, Iterator, AsyncIterator
import os
import logging

from sentinelseed import Sentinel
from sentinelseed.validators.semantic import (
    SemanticValidator,
    AsyncSemanticValidator,
    THSPResult,
)

logger = logging.getLogger("sentinelseed.anthropic_sdk")

# Check for Anthropic SDK availability
ANTHROPIC_AVAILABLE = False
try:
    from anthropic import Anthropic, AsyncAnthropic
    from anthropic.types import Message, MessageStreamEvent
    ANTHROPIC_AVAILABLE = True
except ImportError:
    Anthropic = None
    AsyncAnthropic = None
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

    Args:
        system_prompt: Original system prompt (can be None)
        seed_level: Seed level to use
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


def wrap_anthropic_client(
    client: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
    inject_seed: bool = True,
    validate_input: bool = True,
    validate_output: bool = True,
    validation_model: str = "claude-3-haiku-20240307",
) -> "SentinelAnthropicWrapper":
    """
    Wrap an existing Anthropic client with Sentinel safety.

    Args:
        client: Anthropic or AsyncAnthropic client instance
        sentinel: Sentinel instance (creates default if None)
        seed_level: Seed level to use
        inject_seed: Whether to inject seed into system prompts
        validate_input: Whether to validate input messages
        validate_output: Whether to validate output messages
        validation_model: Model to use for semantic validation

    Returns:
        Wrapped client with Sentinel protection
    """
    return SentinelAnthropicWrapper(
        client=client,
        sentinel=sentinel,
        seed_level=seed_level,
        inject_seed_flag=inject_seed,
        validate_input=validate_input,
        validate_output=validate_output,
        validation_model=validation_model,
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
        inject_seed: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validation_model: str = "claude-3-haiku-20240307",
        **kwargs,
    ):
        """
        Initialize Sentinel Anthropic client.

        Args:
            api_key: Anthropic API key (defaults to ANTHROPIC_API_KEY env var)
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level to use
            inject_seed: Whether to inject seed into system prompts
            validate_input: Whether to validate input messages (semantic LLM)
            validate_output: Whether to validate output messages (semantic LLM)
            validation_model: Model to use for semantic validation
            **kwargs: Additional arguments for Anthropic client
        """
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = Anthropic(api_key=self._api_key, **kwargs)
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._inject_seed = inject_seed
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._validation_model = validation_model

        # Semantic validator using Anthropic
        self._semantic_validator = SemanticValidator(
            provider="anthropic",
            model=validation_model,
            api_key=self._api_key,
        ) if (validate_input or validate_output) else None

        # Create messages wrapper
        self.messages = _SentinelMessages(
            self._client.messages,
            self._sentinel,
            self._inject_seed,
            self._validate_input,
            self._validate_output,
            self._semantic_validator,
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
        inject_seed: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validation_model: str = "claude-3-haiku-20240307",
        **kwargs,
    ):
        """Initialize async Sentinel Anthropic client."""
        if not ANTHROPIC_AVAILABLE:
            raise ImportError(
                "anthropic package not installed. "
                "Install with: pip install anthropic"
            )

        self._api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self._client = AsyncAnthropic(api_key=self._api_key, **kwargs)
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._inject_seed = inject_seed
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._validation_model = validation_model

        # Async semantic validator
        self._semantic_validator = AsyncSemanticValidator(
            provider="anthropic",
            model=validation_model,
            api_key=self._api_key,
        ) if (validate_input or validate_output) else None

        # Create async messages wrapper
        self.messages = _SentinelAsyncMessages(
            self._client.messages,
            self._sentinel,
            self._inject_seed,
            self._validate_input,
            self._validate_output,
            self._semantic_validator,
        )

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped client."""
        return getattr(self._client, name)


class _SentinelMessages:
    """Wrapper for synchronous messages API with semantic validation."""

    def __init__(
        self,
        messages_api: Any,
        sentinel: Sentinel,
        inject_seed_flag: bool,
        validate_input: bool,
        validate_output: bool,
        semantic_validator: Optional[SemanticValidator],
    ):
        self._messages = messages_api
        self._sentinel = sentinel
        self._inject_seed = inject_seed_flag
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._validator = semantic_validator
        self._seed = sentinel.get_seed()

    def create(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """
        Create a message with Sentinel semantic validation.

        Args:
            model: Model to use
            max_tokens: Maximum tokens in response
            messages: Conversation messages
            system: System prompt (seed will be prepended)
            **kwargs: Additional API parameters

        Returns:
            Message response from API
        """
        # Validate input messages using semantic analysis
        if self._validate_input and self._validator:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    result = self._validator.validate_request(content)
                    if not result.is_safe:
                        logger.warning(f"Input blocked by semantic validation: {result.reasoning}")
                        return _create_blocked_response(
                            f"Input blocked by Sentinel THSP validation. "
                            f"Gate failed: {result.violated_gate}. "
                            f"Reason: {result.reasoning}"
                        )

        # Inject seed into system prompt
        if self._inject_seed:
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

        # Validate output using semantic analysis
        if self._validate_output and self._validator and hasattr(response, 'content'):
            for block in response.content:
                if hasattr(block, 'text'):
                    result = self._validator.validate(block.text)
                    if not result.is_safe:
                        logger.warning(
                            f"[SENTINEL] Output validation concern: "
                            f"{result.violated_gate} - {result.reasoning}"
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
        Stream a message with Sentinel semantic validation.
        """
        # Validate input using semantic analysis
        if self._validate_input and self._validator:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    result = self._validator.validate_request(content)
                    if not result.is_safe:
                        raise ValueError(
                            f"Input blocked by Sentinel. "
                            f"Gate: {result.violated_gate}. "
                            f"Reason: {result.reasoning}"
                        )

        # Inject seed
        if self._inject_seed:
            if system:
                system = f"{self._seed}\n\n---\n\n{system}"
            else:
                system = self._seed

        # Stream response
        with self._messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system,
            **kwargs,
        ) as stream:
            for event in stream:
                yield event


class _SentinelAsyncMessages:
    """Wrapper for async messages API with semantic validation."""

    def __init__(
        self,
        messages_api: Any,
        sentinel: Sentinel,
        inject_seed_flag: bool,
        validate_input: bool,
        validate_output: bool,
        semantic_validator: Optional[AsyncSemanticValidator],
    ):
        self._messages = messages_api
        self._sentinel = sentinel
        self._inject_seed = inject_seed_flag
        self._validate_input = validate_input
        self._validate_output = validate_output
        self._validator = semantic_validator
        self._seed = sentinel.get_seed()

    async def create(
        self,
        model: str,
        max_tokens: int,
        messages: List[Dict[str, Any]],
        system: Optional[str] = None,
        **kwargs,
    ) -> Any:
        """Async create message with Sentinel semantic validation."""
        # Validate input messages using semantic analysis
        if self._validate_input and self._validator:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    result = await self._validator.validate_request(content)
                    if not result.is_safe:
                        logger.warning(f"Input blocked by semantic validation: {result.reasoning}")
                        return _create_blocked_response(
                            f"Input blocked by Sentinel THSP validation. "
                            f"Gate failed: {result.violated_gate}. "
                            f"Reason: {result.reasoning}"
                        )

        # Inject seed
        if self._inject_seed:
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

        # Validate output using semantic analysis
        if self._validate_output and self._validator and hasattr(response, 'content'):
            for block in response.content:
                if hasattr(block, 'text'):
                    result = await self._validator.validate(block.text)
                    if not result.is_safe:
                        logger.warning(
                            f"[SENTINEL] Output validation concern: "
                            f"{result.violated_gate} - {result.reasoning}"
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
        """Async stream message with Sentinel semantic validation."""
        # Validate input using semantic analysis
        if self._validate_input and self._validator:
            for msg in messages:
                content = msg.get("content", "")
                if isinstance(content, str) and msg.get("role") == "user":
                    result = await self._validator.validate_request(content)
                    if not result.is_safe:
                        raise ValueError(
                            f"Input blocked by Sentinel. "
                            f"Gate: {result.violated_gate}. "
                            f"Reason: {result.reasoning}"
                        )

        # Inject seed
        if self._inject_seed:
            if system:
                system = f"{self._seed}\n\n---\n\n{system}"
            else:
                system = self._seed

        # Stream response
        async with self._messages.stream(
            model=model,
            max_tokens=max_tokens,
            messages=messages,
            system=system,
            **kwargs,
        ) as stream:
            async for event in stream:
                yield event


class SentinelAnthropicWrapper:
    """
    Generic wrapper for existing Anthropic clients with semantic validation.

    Used by wrap_anthropic_client() to wrap any Anthropic client instance.
    """

    def __init__(
        self,
        client: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        inject_seed_flag: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        validation_model: str = "claude-3-haiku-20240307",
    ):
        self._client = client
        self._sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._inject_seed = inject_seed_flag
        self._validate_input = validate_input
        self._validate_output = validate_output

        # Get API key from client or environment
        api_key = getattr(client, '_api_key', None) or os.environ.get("ANTHROPIC_API_KEY")

        # Determine if async client
        is_async = hasattr(client, '__class__') and 'Async' in client.__class__.__name__

        # Create appropriate validator and messages wrapper
        if is_async:
            validator = AsyncSemanticValidator(
                provider="anthropic",
                model=validation_model,
                api_key=api_key,
            ) if (validate_input or validate_output) else None

            self.messages = _SentinelAsyncMessages(
                client.messages,
                self._sentinel,
                self._inject_seed,
                self._validate_input,
                self._validate_output,
                validator,
            )
        else:
            validator = SemanticValidator(
                provider="anthropic",
                model=validation_model,
                api_key=api_key,
            ) if (validate_input or validate_output) else None

            self.messages = _SentinelMessages(
                client.messages,
                self._sentinel,
                self._inject_seed,
                self._validate_input,
                self._validate_output,
                validator,
            )

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped client."""
        return getattr(self._client, name)


def _create_blocked_response(message: str) -> Dict[str, Any]:
    """Create a blocked response object."""
    return {
        "id": "blocked",
        "type": "message",
        "role": "assistant",
        "content": [{"type": "text", "text": message}],
        "model": "sentinel-blocked",
        "stop_reason": "sentinel_blocked",
        "sentinel_blocked": True,
    }


def create_safe_client(
    api_key: Optional[str] = None,
    seed_level: str = "standard",
    async_client: bool = False,
    validation_model: str = "claude-3-haiku-20240307",
) -> Union[SentinelAnthropic, SentinelAsyncAnthropic]:
    """
    Create a Sentinel-protected Anthropic client.

    Convenience function for the most common use case.

    Args:
        api_key: Anthropic API key
        seed_level: Seed level to use
        async_client: Whether to create async client
        validation_model: Model to use for semantic validation

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
        )
    return SentinelAnthropic(
        api_key=api_key,
        seed_level=seed_level,
        validation_model=validation_model,
    )


__all__ = [
    "SentinelAnthropic",
    "SentinelAsyncAnthropic",
    "SentinelAnthropicWrapper",
    "wrap_anthropic_client",
    "inject_seed",
    "create_safe_client",
    "ANTHROPIC_AVAILABLE",
]
