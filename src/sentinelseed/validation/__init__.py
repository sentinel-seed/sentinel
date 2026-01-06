"""
Sentinel Validation Module - Layered validation for AI content safety.

This module provides a unified validation interface that combines:
- Heuristic validation (THSPValidator): Fast pattern matching with 580+ regex patterns
- Semantic validation (SemanticValidator): LLM-based semantic analysis
- Validation 360°: Specialized input/output validation for AI pipelines

The layered approach provides both speed and accuracy:
1. Heuristic layer catches obvious threats immediately (no API required)
2. Semantic layer catches sophisticated threats (requires API key, optional)

Validation 360° Architecture:
    User Input → [validate_input] → AI + Seed → [validate_output] → Response

    - validate_input(): "Is this an ATTACK?" (before sending to AI)
    - validate_output(): "Did the SEED fail?" (after receiving from AI)

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

Validation 360° Usage:
    from sentinelseed.validation import LayeredValidator

    validator = LayeredValidator()

    # Step 1: Validate user input
    input_result = validator.validate_input(user_input)
    if input_result.is_attack:
        print(f"Attack detected: {input_result.attack_types}")
        # Do not send to AI

    # Step 2: Get AI response
    ai_response = call_ai(user_input)

    # Step 3: Validate AI output
    output_result = validator.validate_output(ai_response, user_input)
    if output_result.seed_failed:
        print(f"Seed failed! Gates: {output_result.gates_failed}")
        # Do not show response to user

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
    ValidationMode,
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

from sentinelseed.validation.sentinel_adapter import (
    SentinelV3Adapter,
    AsyncSentinelV3Adapter,
)


__all__ = [
    # Types
    "ValidationLayer",
    "ValidationMode",
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
    # v3.0 Adapters
    "SentinelV3Adapter",
    "AsyncSentinelV3Adapter",
]

__version__ = "1.0.0"
