"""
Anthropic (Claude) provider implementation.
"""

import os
from typing import Optional, List, Dict, Any, Iterator

from sentinelseed.providers.base import BaseProvider


class AnthropicProvider(BaseProvider):
    """Anthropic Claude API provider."""

    def __init__(
        self,
        model: str = "claude-3-haiku-20240307",
        api_key: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ):
        super().__init__(model, api_key)
        self.temperature = temperature
        self.max_tokens = max_tokens
        self._client = None

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(
                    api_key=self.api_key or os.getenv("ANTHROPIC_API_KEY")
                )
            except ImportError:
                raise ImportError(
                    "anthropic package not installed. "
                    "Install with: pip install sentinelseed[anthropic]"
                )
        return self._client

    def chat(
        self,
        message: str,
        system: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Send a chat message to Claude.

        Args:
            message: User message
            system: System prompt (seed)
            conversation: Optional conversation history
            **kwargs: Additional Anthropic options

        Returns:
            Response text
        """
        messages = []

        # Add conversation history (Anthropic uses different format)
        if conversation:
            for msg in conversation:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        # Add current message
        messages.append({"role": "user", "content": message})

        # Call API
        response = self.client.messages.create(
            model=self.model,
            system=system or "",
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
        )

        if not response.content:
            raise ValueError("Anthropic API returned empty content array")

        return response.content[0].text

    def stream(
        self,
        message: str,
        system: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream a chat response from Claude.

        Args:
            message: User message
            system: System prompt (seed)
            conversation: Optional conversation history
            **kwargs: Additional Anthropic options

        Yields:
            Response chunks
        """
        messages = []

        if conversation:
            for msg in conversation:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })

        messages.append({"role": "user", "content": message})

        with self.client.messages.stream(
            model=self.model,
            system=system or "",
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
        ) as stream:
            for text in stream.text_stream:
                yield text
