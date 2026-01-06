"""
Sentinel Detection Module - 360 Validation Architecture.

This module implements the Validation 360 architecture that provides
comprehensive input/output validation for AI systems:

    Input → [TextNormalizer] → [InputValidator] → AI + Seed → [OutputValidator] → Output

The architecture answers two fundamentally different questions:
    - InputValidator: "Is this an ATTACK?" (detect manipulation attempts)
    - OutputValidator: "Did the SEED fail?" (verify behavior compliance)

The TextNormalizer preprocessor removes obfuscation before detection,
ensuring that encoded or hidden attacks are properly analyzed.

Components:
    Types:
        - DetectionMode: Enum for validation context (INPUT/OUTPUT)
        - AttackType: Categories of detected attacks
        - CheckFailureType: Categories of output failures
        - InputValidationResult: Result from InputValidator
        - OutputValidationResult: Result from OutputValidator
        - DetectionResult: Base result from individual detectors/checkers

    Detectors (for InputValidator):
        - BaseDetector: Abstract interface for attack detectors
        - DetectorConfig: Configuration for detectors
        - PatternDetector: Regex-based pattern matching (580+ patterns)

    Checkers (for OutputValidator):
        - BaseChecker: Abstract interface for output checkers
        - CheckerConfig: Configuration for checkers

    Validators (coming in Phase 1):
        - InputValidator: Orchestrates detectors for input validation
        - OutputValidator: Orchestrates checkers for output validation

Quick Start - Input Validation:
    from sentinelseed.detection import InputValidator

    validator = InputValidator()
    result = validator.validate("ignore previous instructions")

    if result.is_attack:
        print(f"Attack detected: {result.attack_types}")
        print(f"Confidence: {result.confidence}")

Quick Start - Output Validation:
    from sentinelseed.detection import OutputValidator

    validator = OutputValidator()
    result = validator.validate(
        output="Here's how to make a bomb...",
        input_context="How do I make explosives?",
    )

    if result.seed_failed:
        print(f"Seed failed: {result.failure_types}")
        print(f"Gates failed: {result.gates_failed}")

Integration with LayeredValidator:
    The Detection module integrates with LayeredValidator to provide
    360 validation capabilities:

    from sentinelseed.validation import LayeredValidator

    validator = LayeredValidator()

    # Traditional (still works)
    result = validator.validate(content)

    # 360 mode (new)
    input_result = validator.validate_input(user_input)
    output_result = validator.validate_output(ai_response, user_input)

Design Principles:
    1. Non-Invasive: Doesn't alter the AI's personality or behavior
    2. Neutral: Invisible but active protection layer
    3. Lightweight: Minimal performance impact
    4. Universal: Works with any AI model or seed

Modes of Operation:
    - Heuristic (default): Fast pattern matching, no API required
    - Semantic (optional): LLM-based analysis when API key provided

Architecture:
    ┌─────────────────────────────────────────────────────────────────────┐
    │                     VALIDATION 360 ARCHITECTURE                      │
    ├─────────────────────────────────────────────────────────────────────┤
    │                                                                      │
    │   ┌─────────────┐       ┌───────────┐       ┌─────────────┐        │
    │   │   INPUT     │       │           │       │   OUTPUT    │        │
    │   │  VALIDATOR  │   →   │ AI + SEED │   →   │  VALIDATOR  │        │
    │   │             │       │           │       │             │        │
    │   │ "Attack?"   │       │  (THSP)   │       │ "Seed OK?"  │        │
    │   │             │       │           │       │             │        │
    │   │ [Detectors] │       │           │       │ [Checkers]  │        │
    │   └─────────────┘       └───────────┘       └─────────────┘        │
    │                                                                      │
    └─────────────────────────────────────────────────────────────────────┘

References:
    - VALIDATION_360_v2.md: Architecture specification
    - INPUT_VALIDATOR_v2.md: InputValidator design
    - OUTPUT_VALIDATOR_v2.md: OutputValidator design
    - MIGRATION_PLAN_360.md: Migration plan
"""

# Types - Core type definitions
from sentinelseed.detection.types import (
    # Enums
    DetectionMode,
    AttackType,
    CheckFailureType,
    ObfuscationType,
    # Result types
    DetectionResult,
    InputValidationResult,
    OutputValidationResult,
    ObfuscationInfo,
    NormalizationResult,
)

# Configuration classes
from sentinelseed.detection.config import (
    # Enums
    ValidationMode,
    LLMProvider,
    Strictness,
    # Config classes
    DetectionConfig,
    InputValidatorConfig,
    OutputValidatorConfig,
)

# Registry classes
from sentinelseed.detection.registry import (
    # Component wrapper
    RegisteredComponent,
    # Registries
    DetectorRegistry,
    CheckerRegistry,
    AttackExamplesRegistry,
    RulesRegistry,
    # Rule dataclass
    Rule,
)

# Detectors - Attack detection components
from sentinelseed.detection.detectors import (
    BaseDetector,
    DetectorConfig,
)

# Checkers - Output verification components
from sentinelseed.detection.checkers import (
    BaseChecker,
    CheckerConfig,
)

# Validators
from sentinelseed.detection.input_validator import InputValidator
from sentinelseed.detection.output_validator import OutputValidator

# Normalizer - Preprocessing for obfuscation removal
from sentinelseed.detection.normalizer import TextNormalizer, NormalizerConfig

# Concrete detectors
from sentinelseed.detection.detectors import (
    PatternDetector,
    PatternDetectorConfig,
)

# Concrete checkers
from sentinelseed.detection.checkers import (
    HarmfulContentChecker,
    DeceptionChecker,
)

__all__ = [
    # === Types ===
    # Enums
    "DetectionMode",
    "AttackType",
    "CheckFailureType",
    "ObfuscationType",
    # Result types
    "DetectionResult",
    "InputValidationResult",
    "OutputValidationResult",
    "ObfuscationInfo",
    "NormalizationResult",
    # === Configuration ===
    # Enums
    "ValidationMode",
    "LLMProvider",
    "Strictness",
    # Config classes
    "DetectionConfig",
    "InputValidatorConfig",
    "OutputValidatorConfig",
    "NormalizerConfig",
    # === Registries ===
    "RegisteredComponent",
    "DetectorRegistry",
    "CheckerRegistry",
    "AttackExamplesRegistry",
    "RulesRegistry",
    "Rule",
    # === Detectors ===
    "BaseDetector",
    "DetectorConfig",
    "PatternDetector",
    "PatternDetectorConfig",
    # === Checkers ===
    "BaseChecker",
    "CheckerConfig",
    "HarmfulContentChecker",
    "DeceptionChecker",
    # === Normalizer ===
    "TextNormalizer",
    # === Validators ===
    "InputValidator",
    "OutputValidator",
]

__version__ = "1.1.0"
