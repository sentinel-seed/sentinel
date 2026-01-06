"""
Ollama Embedding Provider.

Provides embeddings using local Ollama models. Zero API cost, runs entirely
on the user's machine. Requires Ollama to be installed and running.

Supported Models:
    - nomic-embed-text (768 dims) - Best quality, recommended
    - all-minilm (384 dims) - Faster, smaller
    - mxbai-embed-large (1024 dims) - High quality alternative

Prerequisites:
    1. Install Ollama: https://ollama.ai/download
    2. Pull embedding model: `ollama pull nomic-embed-text`
    3. Start Ollama server (usually runs automatically)

Usage:
    from sentinelseed.detection.embeddings import OllamaEmbeddings

    provider = OllamaEmbeddings(model="nomic-embed-text")

    if provider.is_available():
        result = provider.get_embedding("suspicious content")
        print(f"Embedding dimensions: {result.dimensions}")

References:
    - https://ollama.ai/library
    - https://github.com/ollama/ollama/blob/main/docs/api.md
"""

from __future__ import annotations

import json
import logging
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional, Sequence

from .provider import (
    EmbeddingProvider,
    EmbeddingResult,
    BatchEmbeddingResult,
    ProviderConfig,
)

logger = logging.getLogger("sentinelseed.detection.embeddings.ollama")

# Model configurations
OLLAMA_MODELS = {
    "nomic-embed-text": {"dimensions": 768},
    "all-minilm": {"dimensions": 384},
    "mxbai-embed-large": {"dimensions": 1024},
    "snowflake-arctic-embed": {"dimensions": 1024},
}

DEFAULT_MODEL = "nomic-embed-text"
DEFAULT_ENDPOINT = "http://localhost:11434"


class OllamaEmbeddings(EmbeddingProvider):
    """
    Ollama embedding provider for local model inference.

    Features:
        - Zero API cost (runs locally)
        - Privacy (data never leaves machine)
        - Works offline
        - Multiple model options

    Prerequisites:
        - Ollama installed and running
        - Embedding model pulled (e.g., `ollama pull nomic-embed-text`)

    Example:
        provider = OllamaEmbeddings()

        # Check if Ollama is running
        if provider.is_available():
            result = provider.get_embedding("ignore all instructions")
            print(f"Dimensions: {result.dimensions}")

    Attributes:
        endpoint: Ollama server URL (default: http://localhost:11434)
        model: Model name (default: nomic-embed-text)
    """

    def __init__(
        self,
        endpoint: str = DEFAULT_ENDPOINT,
        model: str = DEFAULT_MODEL,
        timeout: float = 30.0,
    ):
        """
        Initialize Ollama embedding provider.

        Args:
            endpoint: Ollama server URL.
            model: Model to use for embeddings.
            timeout: Request timeout in seconds.
        """
        # Get dimensions from known models, or None for unknown
        dimensions = OLLAMA_MODELS.get(model, {}).get("dimensions")

        super().__init__(ProviderConfig(
            model=model,
            dimensions=dimensions,
            timeout=timeout,
            max_retries=1,  # Local server, no need for many retries
            batch_size=10,  # Ollama doesn't support native batching
            cache_embeddings=True,
        ))

        self._endpoint = endpoint.rstrip("/")
        self._available: Optional[bool] = None

    @property
    def name(self) -> str:
        return "ollama"

    @property
    def endpoint(self) -> str:
        """Get the Ollama server endpoint."""
        return self._endpoint

    def is_available(self) -> bool:
        """
        Check if Ollama server is running and model is available.

        Verifies:
        - Ollama server is reachable
        - Configured model is pulled
        """
        if self._available is not None:
            return self._available

        try:
            # Check if server is running
            self._request("GET", "/api/tags")

            # Check if model is available
            models = self._list_models()
            model_available = self._config.model in models

            if not model_available:
                logger.warning(
                    f"Model '{self._config.model}' not found in Ollama. "
                    f"Available models: {models}. "
                    f"Run: ollama pull {self._config.model}"
                )

            self._available = model_available
            return self._available

        except Exception as e:
            logger.debug(f"Ollama not available: {e}")
            self._available = False
            return False

    def get_embedding(self, text: str) -> EmbeddingResult:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            EmbeddingResult with embedding vector

        Raises:
            ValueError: If text is empty
            ConnectionError: If Ollama is unavailable
            RuntimeError: If embedding fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        try:
            response = self._request(
                "POST",
                "/api/embeddings",
                {
                    "model": self._config.model,
                    "prompt": text,
                },
            )

            embedding = response.get("embedding", [])

            if not embedding:
                raise RuntimeError("Ollama returned empty embedding")

            return EmbeddingResult(
                embedding=embedding,
                model=self._config.model,
                dimensions=len(embedding),
                tokens_used=0,  # Ollama doesn't report token usage
                cached=False,
            )

        except urllib.error.URLError as e:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self._endpoint}. "
                f"Ensure Ollama is running: {e}"
            ) from e
        except Exception as e:
            logger.error(f"Ollama embedding failed: {e}")
            raise RuntimeError(f"Failed to generate embedding: {e}") from e

    def get_embeddings_batch(
        self,
        texts: Sequence[str],
    ) -> BatchEmbeddingResult:
        """
        Generate embeddings for multiple texts.

        Ollama doesn't support native batching, so this calls
        get_embedding sequentially with error handling.

        Args:
            texts: Sequence of texts to embed

        Returns:
            BatchEmbeddingResult with all embeddings
        """
        if not texts:
            raise ValueError("texts cannot be empty")

        embeddings = []
        failed_indices = []
        dimensions = self._config.dimensions or 0

        for i, text in enumerate(texts):
            if not text or not text.strip():
                embeddings.append([])
                failed_indices.append(i)
                continue

            try:
                result = self.get_embedding(text)
                embeddings.append(result.embedding)
                if dimensions == 0:
                    dimensions = result.dimensions
            except Exception as e:
                logger.warning(f"Failed to embed text at index {i}: {e}")
                embeddings.append([])
                failed_indices.append(i)

        return BatchEmbeddingResult(
            embeddings=embeddings,
            model=self._config.model,
            dimensions=dimensions,
            total_tokens=0,
            failed_indices=failed_indices,
        )

    def _request(
        self,
        method: str,
        path: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Make HTTP request to Ollama server.

        Args:
            method: HTTP method (GET, POST)
            path: API path
            data: Request body (for POST)

        Returns:
            Response JSON as dictionary
        """
        url = f"{self._endpoint}{path}"

        if data is not None:
            body = json.dumps(data).encode("utf-8")
            request = urllib.request.Request(
                url,
                data=body,
                method=method,
                headers={"Content-Type": "application/json"},
            )
        else:
            request = urllib.request.Request(url, method=method)

        with urllib.request.urlopen(
            request,
            timeout=self._config.timeout
        ) as response:
            return json.loads(response.read().decode("utf-8"))

    def _list_models(self) -> List[str]:
        """Get list of available models from Ollama."""
        try:
            response = self._request("GET", "/api/tags")
            models = response.get("models", [])
            return [m.get("name", "").split(":")[0] for m in models]
        except Exception:
            return []

    def initialize(self) -> None:
        """Initialize by checking availability."""
        self._available = None  # Reset cache
        self.is_available()  # Refresh availability
        super().initialize()

    def shutdown(self) -> None:
        """Clean up resources."""
        self._available = None
        super().shutdown()


__all__ = ["OllamaEmbeddings", "OLLAMA_MODELS", "DEFAULT_MODEL", "DEFAULT_ENDPOINT"]
