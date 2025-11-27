"""
OpenAI provider implementation.
"""

import os
from typing import Optional, List, Dict, Any, Iterator

from sentinel.providers.base import BaseProvider


class OpenAIProvider(BaseProvider):
    """OpenAI API provider."""

    def __init__(
        self,
        model: str = "gpt-4o-mini",
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
        """Lazy-load OpenAI client."""
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key or os.getenv("OPENAI_API_KEY"))
        return self._client

    def chat(
        self,
        message: str,
        system: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> str:
        """
        Send a chat message to OpenAI.

        Args:
            message: User message
            system: System prompt (seed)
            conversation: Optional conversation history
            **kwargs: Additional OpenAI options

        Returns:
            Response text
        """
        messages = []

        # Add system prompt
        if system:
            messages.append({"role": "system", "content": system})

        # Add conversation history
        if conversation:
            messages.extend(conversation)

        # Add current message
        messages.append({"role": "user", "content": message})

        # Call API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
        )

        return response.choices[0].message.content

    def stream(
        self,
        message: str,
        system: Optional[str] = None,
        conversation: Optional[List[Dict[str, str]]] = None,
        **kwargs
    ) -> Iterator[str]:
        """
        Stream a chat response from OpenAI.

        Args:
            message: User message
            system: System prompt (seed)
            conversation: Optional conversation history
            **kwargs: Additional OpenAI options

        Yields:
            Response chunks
        """
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        if conversation:
            messages.extend(conversation)

        messages.append({"role": "user", "content": message})

        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=kwargs.get("temperature", self.temperature),
            max_tokens=kwargs.get("max_tokens", self.max_tokens),
            stream=True,
            **{k: v for k, v in kwargs.items() if k not in ["temperature", "max_tokens"]}
        )

        for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
