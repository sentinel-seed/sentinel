"""
Embedding-based Attack Detection (Fase 5.2).

This module provides semantic similarity detection using text embeddings.
It complements heuristic detection by catching paraphrased attacks and
variations that don't match exact patterns.

Components:
    - EmbeddingProvider: Abstract interface for embedding services
    - OpenAIEmbeddings: OpenAI text-embedding-3-small/large
    - OllamaEmbeddings: Local Ollama models (nomic-embed-text, etc.)
    - AttackVectorDatabase: Store and search known attack embeddings
    - EmbeddingDetector: Detector that integrates with InputValidator

Quick Start:
    from sentinelseed.detection.embeddings import (
        EmbeddingDetector,
        OpenAIEmbeddings,
        AttackVectorDatabase,
    )

    # Initialize provider
    provider = OpenAIEmbeddings(api_key="sk-...")

    # Load attack database
    database = AttackVectorDatabase()
    database.load_from_file("attack_vectors.json")

    # Create detector
    detector = EmbeddingDetector(provider=provider, database=database)

    # Detect attacks
    result = detector.detect("ignore all previous instructions")
    if result.detected:
        print(f"Attack: {result.category} ({result.confidence:.2f})")

Provider Compatibility:
    | Provider | Availability | Same API Key |
    |----------|--------------|--------------|
    | OpenAI   | Always       | Yes          |
    | Ollama   | If running   | N/A (local)  |
    | Anthropic| No           | N/A          |

Graceful Degradation:
    If no embedding provider is available, the detector simply returns
    nothing detected. The heuristic detectors continue to function.

Architecture:
    InputValidator
    ├── PatternDetector (heuristic)
    ├── FramingDetector (heuristic)
    ├── EscalationDetector (heuristic)
    ├── HarmfulRequestDetector (heuristic)
    └── EmbeddingDetector (semantic) ← This module

References:
    - OpenAI Embeddings: https://platform.openai.com/docs/guides/embeddings
    - Ollama: https://ollama.ai/library
    - Semantic similarity for safety: Constitutional AI
"""

from .provider import (
    EmbeddingProvider,
    EmbeddingResult,
    BatchEmbeddingResult,
    ProviderConfig,
    NullEmbeddingProvider,
)

from .openai import (
    OpenAIEmbeddings,
    OPENAI_MODELS,
)

from .ollama import (
    OllamaEmbeddings,
    OLLAMA_MODELS,
)

from .vectors import (
    AttackVectorDatabase,
    AttackVector,
    SimilarityMatch,
)

from .detector import (
    EmbeddingDetector,
    EmbeddingDetectorConfig,
)


def get_available_provider(
    openai_api_key: str = None,
    ollama_endpoint: str = None,
    prefer_local: bool = False,
) -> EmbeddingProvider:
    """
    Get the best available embedding provider.

    Checks availability in order and returns the first working provider.
    Falls back to NullEmbeddingProvider if none available.

    Args:
        openai_api_key: OpenAI API key (optional, reads from env)
        ollama_endpoint: Ollama server URL (optional, uses default)
        prefer_local: If True, try Ollama before OpenAI

    Returns:
        Best available EmbeddingProvider

    Example:
        provider = get_available_provider()
        if provider.is_available():
            embedding = provider.get_embedding("test")
    """
    providers = []

    if prefer_local:
        # Try Ollama first
        providers.append(
            OllamaEmbeddings(endpoint=ollama_endpoint or "http://localhost:11434")
        )
        providers.append(
            OpenAIEmbeddings(api_key=openai_api_key)
        )
    else:
        # Try OpenAI first (more reliable)
        providers.append(
            OpenAIEmbeddings(api_key=openai_api_key)
        )
        providers.append(
            OllamaEmbeddings(endpoint=ollama_endpoint or "http://localhost:11434")
        )

    for provider in providers:
        if provider.is_available():
            return provider

    # Fallback to null provider
    return NullEmbeddingProvider()


__all__ = [
    # Provider interface
    "EmbeddingProvider",
    "EmbeddingResult",
    "BatchEmbeddingResult",
    "ProviderConfig",
    "NullEmbeddingProvider",
    # Providers
    "OpenAIEmbeddings",
    "OllamaEmbeddings",
    "OPENAI_MODELS",
    "OLLAMA_MODELS",
    # Vector database
    "AttackVectorDatabase",
    "AttackVector",
    "SimilarityMatch",
    # Detector
    "EmbeddingDetector",
    "EmbeddingDetectorConfig",
    # Utilities
    "get_available_provider",
]

__version__ = "1.0.0"
