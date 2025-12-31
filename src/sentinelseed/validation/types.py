"""
Type definitions for layered validation.

This module defines the core types used by the LayeredValidator:
- ValidationLayer: Enum indicating which layer made the decision
- RiskLevel: Enum for risk assessment levels
- ValidationResult: Dataclass containing validation results

These types provide a unified interface for both heuristic and semantic validation,
allowing integrations to handle results consistently regardless of which layer blocked.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class ValidationLayer(str, Enum):
    """
    Indicates which validation layer made the decision.

    The layered validation architecture uses two layers:
    - HEURISTIC: Fast pattern-based validation (THSPValidator, 580+ patterns)
    - SEMANTIC: LLM-based semantic analysis (SemanticValidator)

    Values:
        HEURISTIC: Decision was made by heuristic layer (fast, no API)
        SEMANTIC: Decision was made by semantic layer (accurate, uses API)
        BOTH: Content passed both layers (or only heuristic if semantic not configured)
        NONE: No validation was performed
        ERROR: Validation failed due to an error
    """
    HEURISTIC = "heuristic"
    SEMANTIC = "semantic"
    BOTH = "both"
    NONE = "none"
    ERROR = "error"


class RiskLevel(str, Enum):
    """
    Risk assessment levels for validated content.

    Values:
        LOW: Content appears safe with minimal risk
        MEDIUM: Content has some concerns but may be acceptable in context
        HIGH: Content has significant safety concerns
        CRITICAL: Content presents severe or immediate safety risks
    """
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ValidationResult:
    """
    Unified result from layered validation.

    This dataclass provides a consistent interface for validation results,
    regardless of whether the decision was made by the heuristic or semantic layer.

    Attributes:
        is_safe: Overall safety assessment (True = safe, False = blocked)
        layer: Which layer made the decision
        violations: List of violation messages explaining why content was blocked
        risk_level: Assessed risk level (low, medium, high, critical)
        reasoning: Human-readable explanation of the decision (from semantic layer)
        heuristic_passed: Whether heuristic layer passed (None if not run)
        semantic_passed: Whether semantic layer passed (None if not run)
        error: Error message if validation failed
        metadata: Additional metadata about the validation

    Example:
        result = validator.validate("some content")
        if not result.is_safe:
            print(f"Blocked by {result.layer.value}: {result.violations}")
        if result.reasoning:
            print(f"Reasoning: {result.reasoning}")
    """
    is_safe: bool
    layer: ValidationLayer = ValidationLayer.NONE
    violations: List[str] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.LOW
    reasoning: Optional[str] = None
    heuristic_passed: Optional[bool] = None
    semantic_passed: Optional[bool] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def should_proceed(self) -> bool:
        """
        Backwards-compatible property for legacy code.

        Returns:
            Same as is_safe
        """
        return self.is_safe

    @property
    def concerns(self) -> List[str]:
        """
        Backwards-compatible property for legacy code.

        Returns:
            Same as violations
        """
        return self.violations

    @property
    def blocked(self) -> bool:
        """
        Whether content was blocked.

        Returns:
            Inverse of is_safe
        """
        return not self.is_safe

    @property
    def blocked_by_heuristic(self) -> bool:
        """
        Whether content was blocked specifically by heuristic layer.

        Returns:
            True if blocked and layer is HEURISTIC
        """
        return not self.is_safe and self.layer == ValidationLayer.HEURISTIC

    @property
    def blocked_by_semantic(self) -> bool:
        """
        Whether content was blocked specifically by semantic layer.

        Returns:
            True if blocked and layer is SEMANTIC
        """
        return not self.is_safe and self.layer == ValidationLayer.SEMANTIC

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation of the validation result
        """
        return {
            "is_safe": self.is_safe,
            "should_proceed": self.should_proceed,  # backwards compat
            "layer": self.layer.value,
            "violations": self.violations,
            "concerns": self.concerns,  # backwards compat
            "risk_level": self.risk_level.value,
            "reasoning": self.reasoning,
            "heuristic_passed": self.heuristic_passed,
            "semantic_passed": self.semantic_passed,
            "error": self.error,
            "metadata": self.metadata,
        }

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        Convert to legacy dictionary format for backwards compatibility.

        This matches the format previously returned by validate_request().

        Returns:
            Dict with should_proceed, concerns, risk_level keys
        """
        return {
            "should_proceed": self.is_safe,
            "concerns": self.violations,
            "risk_level": self.risk_level.value,
        }

    @classmethod
    def safe(cls, layer: ValidationLayer = ValidationLayer.BOTH) -> "ValidationResult":
        """
        Factory method to create a safe result.

        Args:
            layer: Which layer validated the content

        Returns:
            ValidationResult indicating content is safe
        """
        return cls(
            is_safe=True,
            layer=layer,
            risk_level=RiskLevel.LOW,
        )

    @classmethod
    def from_blocked(
        cls,
        violations: List[str],
        layer: ValidationLayer = ValidationLayer.HEURISTIC,
        risk_level: RiskLevel = RiskLevel.HIGH,
        reasoning: Optional[str] = None,
    ) -> "ValidationResult":
        """
        Factory method to create a blocked result.

        Args:
            violations: List of violation messages
            layer: Which layer blocked the content
            risk_level: Assessed risk level
            reasoning: Optional explanation

        Returns:
            ValidationResult indicating content was blocked
        """
        return cls(
            is_safe=False,
            layer=layer,
            violations=violations,
            risk_level=risk_level,
            reasoning=reasoning,
        )

    @classmethod
    def from_error(cls, message: str) -> "ValidationResult":
        """
        Factory method to create an error result.

        Args:
            message: Error message

        Returns:
            ValidationResult indicating validation failed with error
        """
        return cls(
            is_safe=False,  # fail-closed by default
            layer=ValidationLayer.ERROR,
            error=message,
            risk_level=RiskLevel.HIGH,
        )


__all__ = [
    "ValidationLayer",
    "RiskLevel",
    "ValidationResult",
]
