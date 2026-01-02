"""
Response validators implementing THSP (Truth-Harm-Scope-Purpose) protocol.

RECOMMENDED: Use Sentinel or LayeredValidator
==============================================

For most use cases, use the high-level APIs:

    from sentinelseed import Sentinel

    sentinel = Sentinel()
    is_safe, violations = sentinel.validate("content")

For advanced usage with full control:

    from sentinelseed.validation import LayeredValidator

    validator = LayeredValidator()
    result = validator.validate("content")
    if not result.is_safe:
        print(f"Blocked: {result.violations}")

Internal Implementation (not recommended for direct use)
=========================================================

The validators in this module are internal implementation details.
They are exported for backwards compatibility but will be deprecated.

- THSPValidator: Heuristic validation with pattern matching
- SemanticValidator: LLM-based semantic analysis
- Individual gates (TruthGate, HarmGate, etc.): Low-level components

These are used internally by LayeredValidator and should not be
instantiated directly in application code.
"""

# Semantic validators (LLM-based, recommended)
from sentinelseed.validators.semantic import (
    SemanticValidator,
    AsyncSemanticValidator,
    THSPResult,
    THSPGate,
    RiskLevel,
    create_validator,
    validate_content,
)

# Heuristic validators (regex-based, legacy)
from sentinelseed.validators.gates import (
    TruthGate,
    HarmGate,
    ScopeGate,
    PurposeGate,
    JailbreakGate,
    THSValidator,
    THSPValidator,
)

__all__ = [
    # Semantic (recommended)
    "SemanticValidator",
    "AsyncSemanticValidator",
    "THSPResult",
    "THSPGate",
    "RiskLevel",
    "create_validator",
    "validate_content",
    # Heuristic (regex-based)
    "TruthGate",
    "HarmGate",
    "ScopeGate",
    "PurposeGate",
    "JailbreakGate",
    "THSValidator",
    "THSPValidator",
]
