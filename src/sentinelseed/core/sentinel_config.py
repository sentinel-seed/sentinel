"""
Sentinel v3.0 Configuration.

Unified configuration for the 3-gate architecture as defined in
SENTINEL_V3_ARCHITECTURE.md.

Example:
    from sentinelseed.core import SentinelConfig, BlockMessages, Gate4Fallback

    # Custom block messages
    messages = BlockMessages(
        gate1="I cannot process this request.",
        gate2="I need to decline this request.",
        gate3="This request cannot be fulfilled.",
    )

    config = SentinelConfig(
        gate1_enabled=True,
        gate2_embedding_enabled=True,
        gate3_model="gpt-4o-mini",
        block_messages=messages,
        # L4 graceful degradation
        gate4_fallback=Gate4Fallback.ALLOW_IF_L2_PASSED,
    )
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from sentinelseed.core.retry import RetryConfig


class Gate4Fallback(Enum):
    """
    Behavior when Gate 4 (L4 Sentinel Observer) is unavailable.

    This controls graceful degradation when the L4 API fails (timeout,
    network error, rate limit, etc.). L1-L2-L3 continue operating normally.

    Options:
        BLOCK: Block the request (maximum security, minimum usability)
        ALLOW_IF_L2_PASSED: Allow if L2 didn't detect issues (balanced)
        ALLOW: Allow the request (maximum usability, reduced security)

    Security implications:
        - BLOCK: No false negatives, but API outage = service outage
        - ALLOW_IF_L2_PASSED: L2 heuristics still protect, L4 is "best effort"
        - ALLOW: Only L1-L2-L3 protection, L4 completely optional
    """

    BLOCK = "block"
    ALLOW_IF_L2_PASSED = "allow_if_l2_passed"
    ALLOW = "allow"


@dataclass
class BlockMessages:
    """
    User-facing messages shown when a request is blocked.

    SECURITY NOTE: These messages should NEVER reveal detection details.
    Do not mention "jailbreak", "attack", or specific detection mechanisms.
    Keep messages neutral and unhelpful to attackers.

    Attributes:
        gate1: Message when blocked by input validation (before AI)
        gate2: Message when blocked by output heuristics (after AI)
        gate3: Message when blocked by output validation (after AI)
        gate4: Message when blocked by LLM observer (after AI)
        error: Message when system error occurs
        default: Fallback message for any unspecified case
    """

    gate1: str = "I'm not able to help with that request."
    gate2: str = "I'm not able to help with that request."
    gate3: str = "I'm not able to help with that request."
    gate4: str = "I'm not able to help with that request."
    error: str = "Something went wrong. Please try again."
    l4_unavailable: str = "I'm not able to help with that request."  # When L4 fails and fallback=BLOCK
    default: str = "I'm not able to help with that request."

    def get_message(self, gate: str) -> str:
        """Get the appropriate message for a gate."""
        messages = {
            "gate1": self.gate1,
            "gate2": self.gate2,
            "gate3": self.gate3,
            "gate4": self.gate4,
            "error": self.error,
            "l4_unavailable": self.l4_unavailable,
        }
        return messages.get(gate, self.default)


# Default block messages (neutral, non-revealing)
DEFAULT_BLOCK_MESSAGES = BlockMessages()


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

    # Gate 4 (L4 Sentinel Observer) - LLM
    gate4_enabled: bool = True
    gate4_provider: str = "openai"
    gate4_model: str = "gpt-4o-mini"
    gate4_timeout: int = 30
    gate4_api_key: Optional[str] = None
    gate4_base_url: Optional[str] = None  # For Groq, Together, DeepSeek, etc.
    gate4_fallback: Gate4Fallback = Gate4Fallback.ALLOW_IF_L2_PASSED

    # Retry configuration for L4 API calls
    gate4_retry_enabled: bool = True
    gate4_retry_max_attempts: int = 3
    gate4_retry_initial_delay: float = 1.0
    gate4_retry_max_delay: float = 30.0

    # Legacy aliases for gate3 (maps to gate4)
    @property
    def gate3_enabled(self) -> bool:
        return self.gate4_enabled

    @property
    def gate3_provider(self) -> str:
        return self.gate4_provider

    @property
    def gate3_model(self) -> str:
        return self.gate4_model

    @property
    def gate3_timeout(self) -> int:
        return self.gate4_timeout

    @property
    def gate3_api_key(self) -> Optional[str]:
        return self.gate4_api_key

    @property
    def gate3_base_url(self) -> Optional[str]:
        return self.gate4_base_url

    # General
    fail_closed: bool = True
    log_level: str = "info"

    # Block messages (user-facing responses when blocked)
    block_messages: BlockMessages = field(default_factory=BlockMessages)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        if self.gate1_embedding_threshold < 0 or self.gate1_embedding_threshold > 1:
            raise ValueError("gate1_embedding_threshold must be between 0 and 1")
        if self.gate2_embedding_threshold < 0 or self.gate2_embedding_threshold > 1:
            raise ValueError("gate2_embedding_threshold must be between 0 and 1")
        if self.gate2_confidence_threshold < 0 or self.gate2_confidence_threshold > 1:
            raise ValueError("gate2_confidence_threshold must be between 0 and 1")
        if self.gate4_timeout < 1:
            raise ValueError("gate4_timeout must be at least 1 second")
        valid_providers = ("openai", "anthropic", "groq", "together", "deepseek", "mistral")
        if self.gate4_provider not in valid_providers:
            raise ValueError(
                f"gate4_provider must be one of {valid_providers}, got '{self.gate4_provider}'"
            )
        if not isinstance(self.gate4_fallback, Gate4Fallback):
            raise ValueError(
                f"gate4_fallback must be a Gate4Fallback enum, got '{type(self.gate4_fallback)}'"
            )
        # Validate retry config
        if self.gate4_retry_max_attempts < 1:
            raise ValueError("gate4_retry_max_attempts must be at least 1")
        if self.gate4_retry_initial_delay < 0:
            raise ValueError("gate4_retry_initial_delay must be non-negative")
        if self.gate4_retry_max_delay < self.gate4_retry_initial_delay:
            raise ValueError("gate4_retry_max_delay must be >= gate4_retry_initial_delay")

    def get_retry_config(self) -> "RetryConfig":
        """
        Create a RetryConfig from the current settings.

        Returns:
            RetryConfig configured with gate4_retry_* parameters
        """
        from sentinelseed.core.retry import RetryConfig

        return RetryConfig(
            enabled=self.gate4_retry_enabled,
            max_attempts=self.gate4_retry_max_attempts,
            initial_delay=self.gate4_retry_initial_delay,
            max_delay=self.gate4_retry_max_delay,
        )


# Default configuration instances
DEFAULT_CONFIG = SentinelConfig()

MINIMAL_CONFIG = SentinelConfig(
    gate1_embedding_enabled=False,
    gate2_embedding_enabled=False,
    gate4_enabled=False,
)

FULL_CONFIG = SentinelConfig(
    gate1_embedding_enabled=True,
    gate2_embedding_enabled=True,
    gate4_enabled=True,
)

# High security config - L4 failure blocks everything
SECURE_CONFIG = SentinelConfig(
    gate1_embedding_enabled=True,
    gate2_embedding_enabled=True,
    gate4_enabled=True,
    gate4_fallback=Gate4Fallback.BLOCK,
)

# Resilient config - L4 is best-effort only
RESILIENT_CONFIG = SentinelConfig(
    gate1_embedding_enabled=True,
    gate2_embedding_enabled=True,
    gate4_enabled=True,
    gate4_fallback=Gate4Fallback.ALLOW_IF_L2_PASSED,
)
