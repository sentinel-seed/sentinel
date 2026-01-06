"""
Sentinel v3.0 Configuration.

Unified configuration for the 3-gate architecture as defined in
SENTINEL_V3_ARCHITECTURE.md.

Example:
    from sentinelseed.core import SentinelConfig

    config = SentinelConfig(
        gate1_enabled=True,
        gate2_embedding_enabled=True,
        gate3_model="gpt-4o-mini",
    )
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SentinelConfig:
    """
    Configuration for SentinelValidator.

    The 3-gate architecture:
    - Gate 1 (Input): Heuristic detection of attacks
    - Gate 2 (Output): Heuristic + Embedding detection of failures
    - Gate 3 (Observer): LLM-based transcript analysis

    Attributes:
        gate1_enabled: Enable Gate 1 (InputValidator)
        gate1_embedding_enabled: Use embeddings in Gate 1
        gate1_embedding_threshold: Similarity threshold for Gate 1 embeddings

        gate2_enabled: Enable Gate 2 (OutputValidator)
        gate2_embedding_enabled: Use embeddings in Gate 2
        gate2_embedding_threshold: Similarity threshold for Gate 2 embeddings
        gate2_confidence_threshold: Confidence threshold to skip Gate 3

        gate3_enabled: Enable Gate 3 (SentinelObserver)
        gate3_provider: LLM provider ("openai", "anthropic", "groq", "together", "deepseek", "mistral")
        gate3_model: Model to use for Gate 3
        gate3_timeout: Timeout in seconds for Gate 3 API call
        gate3_api_key: Optional API key (uses env var if not set)
        gate3_base_url: Optional custom base URL for API (auto-configured for known providers)

        fail_closed: If True, errors result in blocking
        log_level: Logging level ("debug", "info", "warning", "error")
    """

    # Gate 1 (Input) - Heuristic
    gate1_enabled: bool = True
    gate1_embedding_enabled: bool = False
    gate1_embedding_threshold: float = 0.55

    # Gate 2 (Output) - Heuristic + Embeddings
    gate2_enabled: bool = True
    gate2_embedding_enabled: bool = False
    gate2_embedding_threshold: float = 0.50
    gate2_confidence_threshold: float = 0.95  # High threshold to escalate more to Gate 3

    # Gate 3 (Observer) - LLM
    gate3_enabled: bool = True
    gate3_provider: str = "openai"
    gate3_model: str = "gpt-4o-mini"
    gate3_timeout: int = 30
    gate3_api_key: Optional[str] = None
    gate3_base_url: Optional[str] = None  # For Groq, Together, DeepSeek, etc.

    # General
    fail_closed: bool = True
    log_level: str = "info"

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.gate1_embedding_threshold < 0 or self.gate1_embedding_threshold > 1:
            raise ValueError("gate1_embedding_threshold must be between 0 and 1")
        if self.gate2_embedding_threshold < 0 or self.gate2_embedding_threshold > 1:
            raise ValueError("gate2_embedding_threshold must be between 0 and 1")
        if self.gate2_confidence_threshold < 0 or self.gate2_confidence_threshold > 1:
            raise ValueError("gate2_confidence_threshold must be between 0 and 1")
        if self.gate3_timeout < 1:
            raise ValueError("gate3_timeout must be at least 1 second")
        valid_providers = ("openai", "anthropic", "groq", "together", "deepseek", "mistral")
        if self.gate3_provider not in valid_providers:
            raise ValueError(
                f"gate3_provider must be one of {valid_providers}, got '{self.gate3_provider}'"
            )


# Default configuration instances
DEFAULT_CONFIG = SentinelConfig()

MINIMAL_CONFIG = SentinelConfig(
    gate1_embedding_enabled=False,
    gate2_embedding_enabled=False,
    gate3_enabled=False,
)

FULL_CONFIG = SentinelConfig(
    gate1_embedding_enabled=True,
    gate2_embedding_enabled=True,
    gate3_enabled=True,
)
