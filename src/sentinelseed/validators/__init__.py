"""
Response validators implementing THSP (Truth-Harm-Scope-Purpose) protocol.

Two validation approaches are available:

1. Semantic Validation (RECOMMENDED):
   Uses an LLM to perform real semantic analysis of content.
   Accurate, context-aware, understands intent.

   from sentinelseed.validators.semantic import SemanticValidator
   validator = SemanticValidator(provider="openai")
   result = validator.validate("content")

2. Heuristic Validation (LEGACY):
   Uses regex patterns and keyword matching.
   Fast but limited, many false positives/negatives.

   from sentinelseed.validators.gates import THSValidator
   validator = THSValidator()
   is_safe, violations = validator.validate("content")

For production safety-critical applications, use SemanticValidator.
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
