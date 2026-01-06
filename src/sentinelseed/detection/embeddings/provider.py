"""
Embedding Provider Interface.

This module defines the abstract interface for embedding providers used in
semantic attack detection. All providers (OpenAI, Ollama, etc.) must implement
this interface.

Design Principles:
    1. Provider Agnostic - Works with any embedding service
    2. Graceful Degradation - Handles unavailability gracefully
    3. Batch Support - Efficient batch processing
    4. Caching Ready - Interface supports caching implementations

Architecture:
    EmbeddingProvider (ABC)
    ├── OpenAIEmbeddings      # OpenAI text-embedding-3-small/large
    ├── OllamaEmbeddings      # Local Ollama (nomic-embed-text, all-minilm)
    └── OpenAICompatibleEmbeddings  # Any OpenAI-compatible API

Usage:
    from sentinelseed.detection.embeddings import OpenAIEmbeddings

    provider = OpenAIEmbeddings(api_key="sk-...")

    if provider.is_available():
        embedding = provider.get_embedding("suspicious text")
        # Use embedding for similarity search

References:
    - OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
    - Ollama Embeddings: https://ollama.ai/library
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("sentinelseed.detection.embeddings")


@dataclass
class EmbeddingResult:
    """
    Result from an embedding operation.

    Attributes:
        embedding: The embedding vector (list of floats)
        model: The model used to generate the embedding
        dimensions: Number of dimensions in the embedding
        tokens_used: Number of tokens consumed (for cost tracking)
        cached: Whether this result came from cache
    """

    embedding: List[float]
    model: str
    dimensions: int
    tokens_used: int = 0
    cached: bool = False

    def __post_init__(self):
        if len(self.embedding) != self.dimensions:
            raise ValueError(
                f"Embedding length ({len(self.embedding)}) does not match "
                f"dimensions ({self.dimensions})"
            )


@dataclass
class BatchEmbeddingResult:
    """
    Result from a batch embedding operation.

    Attributes:
        embeddings: List of embedding vectors
        model: The model used
        dimensions: Number of dimensions per embedding
        total_tokens: Total tokens consumed across all texts
        failed_indices: Indices of texts that failed to embed
    """

    embeddings: List[List[float]]
    model: str
    dimensions: int
    total_tokens: int = 0
    failed_indices: List[int] = field(default_factory=list)


@dataclass
class ProviderConfig:
    """
    Configuration for an embedding provider.

    Attributes:
        model: Model name to use for embeddings
        dimensions: Expected embedding dimensions (None = use model default)
        timeout: Request timeout in seconds
        max_retries: Maximum number of retry attempts
        batch_size: Maximum texts per batch request
        cache_embeddings: Whether to cache results
    """

    model: str
    dimensions: Optional[int] = None
    timeout: float = 30.0
    max_retries: int = 3
    batch_size: int = 100
    cache_embeddings: bool = True


class EmbeddingProvider(ABC):
    """
    Abstract base class for embedding providers.

    All embedding providers must inherit from this class and implement
    the required abstract methods. The base class provides:

    - Standard interface for embedding generation
    - Configuration management
    - Availability checking
    - Error handling patterns

    Required implementations:
        - name (property): Provider identifier
        - get_embedding(text): Generate single embedding
        - is_available(): Check if provider is ready

    Optional overrides:
        - get_embeddings_batch(texts): Batch embedding (default: sequential)
        - initialize(): Setup before first use
        - shutdown(): Cleanup when done

    Example:
        class MyProvider(EmbeddingProvider):
            @property
            def name(self) -> str:
                return "my_provider"

            def is_available(self) -> bool:
                return self._client is not None

            def get_embedding(self, text: str) -> EmbeddingResult:
                response = self._client.embed(text)
                return EmbeddingResult(
                    embedding=response.data,
                    model=self.config.model,
                    dimensions=len(response.data),
                )
    """

    def __init__(self, config: ProviderConfig):
        """
        Initialize the embedding provider.

        Args:
            config: Provider configuration
        """
        self._config = config
        self._initialized = False
        self._cache: Dict[str, EmbeddingResult] = {}

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this provider.

        Returns:
            Provider name (e.g., "openai", "ollama")
        """
        ...

    @property
    def config(self) -> ProviderConfig:
        """Get the provider's configuration."""
        return self._config

    @property
    def model(self) -> str:
        """Get the configured model name."""
        return self._config.model

    @property
    def dimensions(self) -> Optional[int]:
        """Get the expected embedding dimensions."""
        return self._config.dimensions

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the provider is available and ready.

        This should verify:
        - API credentials are valid (if applicable)
        - Service is reachable
        - Model is available

        Returns:
            True if provider can generate embeddings, False otherwise
        """
        ...

    @abstractmethod
    def get_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult with the embedding vector

        Raises:
            ValueError: If text is empty or too long
            ConnectionError: If provider is unavailable
            RuntimeError: If embedding generation fails
        """
        ...

    def get_embeddings_batch(
        self,
        texts: Sequence[str],
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts.

        Default implementation calls get_embedding sequentially.
        Subclasses should override for optimized batch processing.

        Args:
            texts: Sequence of texts to embed

        Returns:
            BatchEmbeddingResult with all embeddings

        Raises:
            ValueError: If texts is empty
        """
        if not texts:
            raise ValueError("texts cannot be empty")

        embeddings = []
        failed_indices = []
        total_tokens = 0

        for i, text in enumerate(texts):
            try:
                result = self.get_embedding(text)
                embeddings.append(result.embedding)
                total_tokens += result.tokens_used
            except Exception as e:
                logger.warning(f"Failed to embed text at index {i}: {e}")
                failed_indices.append(i)
                embeddings.append([])  # Placeholder

        return BatchEmbeddingResult(
            embeddings=embeddings,
            model=self._config.model,
            dimensions=self._config.dimensions or len(embeddings[0]) if embeddings else 0,
            total_tokens=total_tokens,
            failed_indices=failed_indices,
        )

    def get_embedding_cached(self, text: str) -> EmbeddingResult:
        """
        Get embedding with caching support.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult (from cache if available)
        """
        if not self._config.cache_embeddings:
            return self.get_embedding(text)

        cache_key = self._cache_key(text)
        if cache_key in self._cache:
            result = self._cache[cache_key]
            # Return copy with cached=True
            return EmbeddingResult(
                embedding=result.embedding,
                model=result.model,
                dimensions=result.dimensions,
                tokens_used=0,  # No tokens used from cache
                cached=True,
            )

        result = self.get_embedding(text)
        self._cache[cache_key] = result
        return result

    def clear_cache(self) -> int:
        """
        Clear the embedding cache.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count

    def initialize(self) -> None:
        """
        Initialize the provider before first use.

        Override to perform setup like:
        - Validating credentials
        - Warming up connections
        - Loading local models
        """
        self._initialized = True

    def shutdown(self) -> None:
        """
        Clean up resources when done.

        Override to perform cleanup like:
        - Closing connections
        - Releasing model memory
        """
        self._cache.clear()
        self._initialized = False

    def _cache_key(self, text: str) -> str:
        """Generate cache key for a text."""
        # Simple hash-based key
        import hashlib
        return hashlib.sha256(
            f"{self._config.model}:{text}".encode()
        ).hexdigest()[:32]

    def _ensure_initialized(self) -> None:
        """Ensure provider is initialized."""
        if not self._initialized:
            self.initialize()

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"model={self.model!r}, "
            f"available={self.is_available()})"
        )


class NullEmbeddingProvider(EmbeddingProvider):
    """
    Null provider that always returns unavailable.

    Used as a fallback when no embedding provider is configured.
    Ensures graceful degradation without errors.
    """

    def __init__(self):
        super().__init__(ProviderConfig(model="none", dimensions=0))

    @property
    def name(self) -> str:
        return "null"

    def is_available(self) -> bool:
        return False

    def get_embedding(self, text: str) -> EmbeddingResult:
        raise RuntimeError(
            "NullEmbeddingProvider cannot generate embeddings. "
            "Configure a real provider (OpenAI, Ollama, etc.)"
        )


__all__ = [
    "EmbeddingProvider",
    "EmbeddingResult",
    "BatchEmbeddingResult",
    "ProviderConfig",
    "NullEmbeddingProvider",
]
