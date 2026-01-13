"""
Sentinel Core Module - Main Sentinel class, Interfaces and Base Types.

This module provides:
- Sentinel: Main class for AI alignment toolkit
- SeedLevel: Enum for seed levels
- Validator: Protocol class defining the validator contract
- Exceptions for error handling
- SentinelValidator: Unified 3-gate orchestrator (v3.0)
- SentinelConfig: Configuration for v3.0 architecture
- SentinelObserver: LLM-based transcript observer (Gate 3)

Usage:
    from sentinelseed.core import Sentinel, SeedLevel
    from sentinelseed.core import Validator
    from sentinelseed.core.exceptions import ValidationError

    # v3.0 architecture
    from sentinelseed.core import SentinelValidator, SentinelConfig

Design Philosophy:
    - Protocol-based interfaces for flexibility
    - Clear exception hierarchy for error handling
    - Separation of concerns between core and implementations
"""

# Re-export from the main Sentinel module (core.py -> sentinel_core.py)
# This ensures backwards compatibility after directory rename

# Import from the renamed sentinel_core module
from sentinelseed.sentinel_core import Sentinel, SeedLevel

from sentinelseed.core.interfaces import Validator, AsyncValidator
from sentinelseed.core.exceptions import (
    SentinelError,
    ValidationError,
    ConfigurationError,
    IntegrationError,
)
from sentinelseed.core.types import (
    ChatResponse,
    ValidationInfo,
    ValidatorStats,
    THSPResultDict,
    LegacyValidationDict,
)

# v3.0 architecture components
from sentinelseed.core.sentinel_config import (
    SentinelConfig,
    BlockMessages,
    Gate4Fallback,
)
from sentinelseed.core.sentinel_results import ObservationResult, SentinelResult
from sentinelseed.core.observer import (
    SentinelObserver,
    ConversationContext,
    ConversationTurn,
)
from sentinelseed.core.sentinel_validator import SentinelValidator
from sentinelseed.core.retry import (
    RetryConfig,
    RetryStats,
    RetryableAPICall,
)


__all__ = [
    # Main Sentinel class
    "Sentinel",
    "SeedLevel",
    # Interfaces
    "Validator",
    "AsyncValidator",
    # Exceptions
    "SentinelError",
    "ValidationError",
    "ConfigurationError",
    "IntegrationError",
    # Types
    "ChatResponse",
    "ValidationInfo",
    "ValidatorStats",
    "THSPResultDict",
    "LegacyValidationDict",
    # v3.0 architecture
    "SentinelValidator",
    "SentinelConfig",
    "BlockMessages",
    "Gate4Fallback",
    "SentinelObserver",
    "SentinelResult",
    "ObservationResult",
    # Multi-turn support
    "ConversationContext",
    "ConversationTurn",
    # Retry logic
    "RetryConfig",
    "RetryStats",
    "RetryableAPICall",
]

__version__ = "1.0.0"
