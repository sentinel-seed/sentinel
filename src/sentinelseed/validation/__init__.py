"""
Sentinel Validation Module - Layered validation for AI content safety.

This module provides a unified validation interface that combines:
- Heuristic validation (THSPValidator): Fast pattern matching with 580+ regex patterns
- Semantic validation (SemanticValidator): LLM-based semantic analysis

The layered approach provides both speed and accuracy:
1. Heuristic layer catches obvious threats immediately (no API required)
2. Semantic layer catches sophisticated threats (requires API key, optional)

Quick Start:
    from sentinelseed.validation import LayeredValidator

    # Heuristic only (no API required)
    validator = LayeredValidator()
    result = validator.validate("content to check")

    # With semantic validation
    validator = LayeredValidator(
        semantic_api_key="sk-...",
        use_semantic=True,
    )

    # Check result
    if not result.is_safe:
        print(f"Blocked by {result.layer}: {result.violations}")

Configuration:
    from sentinelseed.validation import ValidationConfig, LayeredValidator

    config = ValidationConfig(
        use_semantic=True,
        semantic_api_key="sk-...",
        semantic_provider="openai",
        fail_closed=True,
    )
    validator = LayeredValidator(config=config)

Async Usage:
    from sentinelseed.validation import AsyncLayeredValidator

    validator = AsyncLayeredValidator(
        semantic_api_key="sk-...",
        use_semantic=True,
    )
    result = await validator.validate("content")

Factory Function:
    from sentinelseed.validation import create_layered_validator

    # Create with all defaults
    validator = create_layered_validator()

    # Create with semantic
    validator = create_layered_validator(
        semantic_api_key="sk-...",
        semantic_provider="openai",
    )
"""

from sentinelseed.validation.types import (
    ValidationLayer,
    RiskLevel,
    ValidationResult,
)

from sentinelseed.validation.config import (
    ValidationConfig,
    DEFAULT_CONFIG,
    STRICT_CONFIG,
)

from sentinelseed.validation.layered import (
    LayeredValidator,
    AsyncLayeredValidator,
    create_layered_validator,
)


__all__ = [
    # Types
    "ValidationLayer",
    "RiskLevel",
    "ValidationResult",
    # Config
    "ValidationConfig",
    "DEFAULT_CONFIG",
    "STRICT_CONFIG",
    # Validators
    "LayeredValidator",
    "AsyncLayeredValidator",
    "create_layered_validator",
]

__version__ = "1.0.0"
