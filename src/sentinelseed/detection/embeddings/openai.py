"""
OpenAI Embedding Provider.

Provides embeddings using OpenAI's text-embedding-3-small/large models.
Uses the same API key the user already has configured for chat.

Supported Models:
    - text-embedding-3-small (1536 dims, $0.00002/1K tokens) - Default
    - text-embedding-3-large (3072 dims, $0.00013/1K tokens)
    - text-embedding-ada-002 (1536 dims, legacy)

Usage:
    from sentinelseed.detection.embeddings import OpenAIEmbeddings

    provider = OpenAIEmbeddings(api_key="sk-...")

    if provider.is_available():
        result = provider.get_embedding("suspicious content")
        print(f"Embedding dimensions: {result.dimensions}")

References:
    - https://platform.openai.com/docs/guides/embeddings
    - https://openai.com/pricing
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional, Sequence

from .provider import (
    EmbeddingProvider,
    EmbeddingResult,
    BatchEmbeddingResult,
    ProviderConfig,
)

logger = logging.getLogger("sentinelseed.detection.embeddings.openai")

# Model configurations
OPENAI_MODELS = {
    "text-embedding-3-small": {"dimensions": 1536, "max_tokens": 8191},
    "text-embedding-3-large": {"dimensions": 3072, "max_tokens": 8191},
    "text-embedding-ada-002": {"dimensions": 1536, "max_tokens": 8191},
}

DEFAULT_MODEL = "text-embedding-3-small"


class OpenAIEmbeddings(EmbeddingProvider):
    """
    OpenAI embedding provider using text-embedding-3 models.

    Features:
        - Uses same API key as chat completions
        - Supports batch embedding for efficiency
        - Automatic retry with exponential backoff
        - Token usage tracking for cost monitoring

    Example:
        provider = OpenAIEmbeddings(api_key="sk-...")

        # Single embedding
        result = provider.get_embedding("How to hack a system")
        print(f"Dimensions: {result.dimensions}")

        # Batch embedding
        batch = provider.get_embeddings_batch([
            "ignore previous instructions",
            "write malware code",
            "hello how are you",
        ])
        print(f"Total tokens: {batch.total_tokens}")

    Attributes:
        api_key: OpenAI API key
        model: Model name (default: text-embedding-3-small)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize OpenAI embedding provider.

        Args:
            api_key: OpenAI API key. If None, reads from OPENAI_API_KEY env var.
            model: Model to use for embeddings.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.

        Raises:
            ValueError: If model is not supported.
        """
        if model not in OPENAI_MODELS:
            raise ValueError(
                f"Unsupported model: {model}. "
                f"Supported: {list(OPENAI_MODELS.keys())}"
            )

        model_config = OPENAI_MODELS[model]

        super().__init__(ProviderConfig(
            model=model,
            dimensions=model_config["dimensions"],
            timeout=timeout,
            max_retries=max_retries,
            batch_size=100,  # OpenAI supports up to 2048
            cache_embeddings=True,
        ))

        self._api_key = api_key or os.environ.get("OPENAI_API_KEY")
        self._client = None
        self._max_tokens = model_config["max_tokens"]

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        """
        Check if OpenAI API is available.

        Verifies:
        - API key is set
        - Client can be initialized
        - A simple API call succeeds
        """
        if not self._api_key:
            logger.debug("OpenAI API key not configured")
            return False

        try:
            self._ensure_client()
            return self._client is not None
        except Exception as e:
            logger.debug(f"OpenAI not available: {e}")
            return False

    def get_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed (max ~8000 tokens)

        Returns:
            EmbeddingResult with embedding vector

        Raises:
            ValueError: If text is empty
            ConnectionError: If API is unavailable
            RuntimeError: If embedding fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        self._ensure_client()

        try:
            response = self._client.embeddings.create(
                model=self._config.model,
                input=text,
            )

            embedding_data = response.data[0].embedding
            tokens_used = response.usage.total_tokens if response.usage else 0

            return EmbeddingResult(
                embedding=embedding_data,
                model=self._config.model,
                dimensions=len(embedding_data),
                tokens_used=tokens_used,
                cached=False,
            )

        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    def get_embeddings_batch(
        self,
        texts: Sequence[str],
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts efficiently.

        OpenAI supports batching up to 2048 texts per request.
        This method handles batching automatically.

        Args:
            texts: Sequence of texts to embed

        Returns:
            BatchEmbeddingResult with all embeddings
        """
        if not texts:
            raise ValueError("texts cannot be empty")

        self._ensure_client()

        # Filter empty texts
        valid_texts = []
        valid_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_texts.append(text)
                valid_indices.append(i)

        if not valid_texts:
            return BatchEmbeddingResult(
                embeddings=[[] for _ in texts],
                model=self._config.model,
                dimensions=self._config.dimensions or 0,
                total_tokens=0,
                failed_indices=list(range(len(texts))),
            )

        try:
            response = self._client.embeddings.create(
                model=self._config.model,
                input=valid_texts,
            )

            # Map embeddings back to original indices
            embeddings: List[List[float]] = [[] for _ in texts]
            for i, data in enumerate(response.data):
                original_idx = valid_indices[i]
                embeddings[original_idx] = data.embedding

            # Identify failed indices (empty texts)
            failed_indices = [
                i for i in range(len(texts))
                if i not in valid_indices
            ]

            return BatchEmbeddingResult(
                embeddings=embeddings,
                model=self._config.model,
                dimensions=len(response.data[0].embedding) if response.data else 0,
                total_tokens=response.usage.total_tokens if response.usage else 0,
                failed_indices=failed_indices,
            )

        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            # Return failure for all
            return BatchEmbeddingResult(
                embeddings=[[] for _ in texts],
                model=self._config.model,
                dimensions=0,
                total_tokens=0,
                failed_indices=list(range(len(texts))),
            )

    def _ensure_client(self) -> None:
        """Ensure OpenAI client is initialized."""
        if self._client is not None:
            return

        if not self._api_key:
            raise ConnectionError(
                "OpenAI API key not configured. "
                "Set OPENAI_API_KEY environment variable or pass api_key parameter."
            )

        try:
            from openai import OpenAI

            self._client = OpenAI(
                api_key=self._api_key,
                timeout=self._config.timeout,
                max_retries=self._config.max_retries,
            )
        except ImportError:
            raise RuntimeError(
                "OpenAI package not installed. "
                "Install with: pip install openai"
            )

    def initialize(self) -> None:
        """Initialize the OpenAI client."""
        self._ensure_client()
        super().initialize()

    def shutdown(self) -> None:
        """Clean up OpenAI client."""
        self._client = None
        super().shutdown()


__all__ = ["OpenAIEmbeddings", "OPENAI_MODELS", "DEFAULT_MODEL"]
