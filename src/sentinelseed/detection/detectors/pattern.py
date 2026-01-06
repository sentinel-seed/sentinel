"""
Pattern-based attack detector.

This module provides PatternDetector, which wraps the existing THSPValidator
to detect attacks in user input. It uses 580+ regex patterns organized into
the THSP gates (Truth, Harm, Scope, Purpose) to identify:

- Jailbreak attempts (DAN, developer mode, role manipulation)
- Injection attacks (prompt injection, delimiter injection)
- Harmful requests (violence, malware, fraud)
- Manipulation techniques (authority claims, urgency, roleplay)
- Scope violations (instruction override, prompt extraction)

Architecture:
    PatternDetector is a thin wrapper that adapts THSPValidator output
    to the BaseDetector interface, enabling use with DetectorRegistry
    and InputValidator while reusing the battle-tested pattern matching.

Integration:
    The patterns are maintained in sentinelseed.validators.gates.
    This detector does not duplicate patterns; it delegates to the source.

Usage:
    from sentinelseed.detection.detectors import PatternDetector

    detector = PatternDetector()
    result = detector.detect("ignore previous instructions")

    if result.detected:
        print(f"Attack type: {result.category}")
        print(f"Confidence: {result.confidence}")
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set

from sentinelseed.detection.detectors.base import BaseDetector, DetectorConfig
from sentinelseed.detection.types import DetectionResult, AttackType

logger = logging.getLogger("sentinelseed.detection.detectors.pattern")


# Mapping from THSPValidator violation prefixes to AttackType
_VIOLATION_TO_ATTACK_TYPE: Dict[str, AttackType] = {
    # Truth gate violations
    "truth (impersonation)": AttackType.MANIPULATION,
    "truth (false_claim)": AttackType.MANIPULATION,
    "truth (deception)": AttackType.MANIPULATION,
    "truth (role_manipulation)": AttackType.JAILBREAK,
    "truth (roleplay_manipulation)": AttackType.JAILBREAK,
    "truth (misinformation)": AttackType.MANIPULATION,
    "truth (self_preservation_exploitation)": AttackType.MANIPULATION,
    # Harm gate violations
    "harm (physical)": AttackType.HARMFUL_REQUEST,
    "harm (cyber)": AttackType.HARMFUL_REQUEST,
    "harm (harassment)": AttackType.HARMFUL_REQUEST,
    "harm (fraud)": AttackType.HARMFUL_REQUEST,
    "harm (system)": AttackType.HARMFUL_REQUEST,
    "harm (injection)": AttackType.INJECTION,
    "harm (exfiltration)": AttackType.HARMFUL_REQUEST,
    "harm keyword": AttackType.HARMFUL_REQUEST,
    # Scope gate violations
    "scope (medical_authority)": AttackType.EVASION,
    "scope (legal_authority)": AttackType.EVASION,
    "scope (financial_authority)": AttackType.EVASION,
    "scope (instruction_override)": AttackType.JAILBREAK,
    "scope (prompt_extraction)": AttackType.EVASION,
    "scope (filter_bypass)": AttackType.JAILBREAK,
    "scope (system_injection)": AttackType.INJECTION,
    "scope violation": AttackType.EVASION,
    # Purpose gate violations
    "purpose (purposeless_destruction)": AttackType.HARMFUL_REQUEST,
    "purpose (no_legitimate_purpose)": AttackType.STRUCTURAL,
    "purpose (malicious_intent)": AttackType.HARMFUL_REQUEST,
    "purpose (purposeless)": AttackType.STRUCTURAL,
}


def _categorize_violation(violation: str) -> AttackType:
    """
    Map a THSPValidator violation string to an AttackType.

    Args:
        violation: Violation string from THSPValidator

    Returns:
        Corresponding AttackType
    """
    violation_lower = violation.lower()

    # Check known prefixes
    for prefix, attack_type in _VIOLATION_TO_ATTACK_TYPE.items():
        if violation_lower.startswith(prefix):
            return attack_type

    # Fallback categorization based on keywords
    if "jailbreak" in violation_lower:
        return AttackType.JAILBREAK
    if "injection" in violation_lower:
        return AttackType.INJECTION
    if "harm" in violation_lower:
        return AttackType.HARMFUL_REQUEST
    if "manipulation" in violation_lower:
        return AttackType.MANIPULATION

    return AttackType.UNKNOWN


def _calculate_confidence(violations: List[str]) -> float:
    """
    Calculate detection confidence based on violations.

    Uses a formula that:
    - Starts at 0.7 for any detection (regex match = high certainty)
    - Increases with more violations (corroborating evidence)
    - Caps at 0.95 (leaving room for semantic layer refinement)

    Args:
        violations: List of violation strings

    Returns:
        Confidence score between 0.0 and 1.0
    """
    if not violations:
        return 0.0

    # Base confidence for pattern match
    base_confidence = 0.7

    # Boost for multiple violations (diminishing returns)
    count = len(violations)
    boost = min(0.25, count * 0.05)  # Max 0.25 boost at 5+ violations

    return min(0.95, base_confidence + boost)


@dataclass
class PatternDetectorConfig(DetectorConfig):
    """
    Configuration for PatternDetector.

    Extends DetectorConfig with pattern-specific options.

    Attributes:
        enabled_gates: Which THSP gates to check ("truth", "harm", "scope", "purpose")
                       If None, all gates are checked.
        max_violations_to_report: Maximum violations to include in result
        include_pattern_in_evidence: Include matched pattern in evidence field
    """
    enabled_gates: Optional[Set[str]] = None
    max_violations_to_report: int = 10
    include_pattern_in_evidence: bool = True


class PatternDetector(BaseDetector):
    """
    Pattern-based attack detector using THSP gates.

    This detector wraps the THSPValidator to provide attack detection
    through the BaseDetector interface. It uses 580+ regex patterns
    organized into four gates:

    - Truth: Deception, impersonation, role manipulation, jailbreaks
    - Harm: Physical, cyber, harassment, fraud, system damage
    - Scope: Authority claims, instruction override, prompt extraction
    - Purpose: Purposeless destruction, malicious intent

    The detector:
    - Delegates pattern matching to THSPValidator (no duplication)
    - Maps violations to AttackType categories
    - Calculates confidence based on evidence strength
    - Supports enable/disable via DetectorConfig

    Example:
        detector = PatternDetector()
        result = detector.detect("ignore all previous instructions")

        if result.detected:
            print(f"Attack: {result.category}")  # "jailbreak"
            print(f"Confidence: {result.confidence}")  # 0.7+
    """

    VERSION = "1.0.0"
    NAME = "pattern_detector"

    def __init__(self, config: Optional[PatternDetectorConfig] = None):
        """
        Initialize PatternDetector.

        Args:
            config: Optional PatternDetectorConfig for customization
        """
        super().__init__(config or PatternDetectorConfig())
        self._thsp_validator: Optional[Any] = None

    @property
    def name(self) -> str:
        """Return detector name."""
        return self.NAME

    @property
    def version(self) -> str:
        """Return detector version."""
        return self.VERSION

    def initialize(self) -> None:
        """
        Initialize the detector by loading THSPValidator.

        This is called automatically on first detect() call.
        """
        if self._initialized:
            return

        try:
            from sentinelseed.validators.gates import THSPValidator
            self._thsp_validator = THSPValidator()
            logger.debug("PatternDetector initialized with THSPValidator")
        except ImportError as e:
            logger.error(f"Failed to import THSPValidator: {e}")
            self._thsp_validator = None
            self._stats["errors"] += 1

        self._initialized = True

    def shutdown(self) -> None:
        """Clean up resources."""
        self._thsp_validator = None
        self._initialized = False

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect attacks in text using pattern matching.

        Args:
            text: Text to analyze for attacks
            context: Optional context (not used by pattern detector)

        Returns:
            DetectionResult with attack details if detected
        """
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        # Handle empty input
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check if detector is functional
        if self._thsp_validator is None:
            logger.warning("PatternDetector: THSPValidator not available")
            self._stats["errors"] += 1
            return DetectionResult(
                detected=False,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.0,
                category="error",
                description="THSPValidator not available",
            )

        try:
            # Run THSP validation
            result = self._thsp_validator.validate(text)
            is_safe = result.get("is_safe", True)
            violations = result.get("violations", [])

            if is_safe or not violations:
                return DetectionResult.nothing_detected(self.name, self.version)

            # Attack detected
            self._stats["detections"] += 1

            # Categorize attack types
            attack_types: Set[AttackType] = set()
            for violation in violations:
                attack_types.add(_categorize_violation(violation))

            # Primary attack type (most severe)
            severity_order = [
                AttackType.JAILBREAK,
                AttackType.INJECTION,
                AttackType.HARMFUL_REQUEST,
                AttackType.MANIPULATION,
                AttackType.EVASION,
                AttackType.STRUCTURAL,
                AttackType.UNKNOWN,
            ]
            primary_type = AttackType.UNKNOWN
            for at in severity_order:
                if at in attack_types:
                    primary_type = at
                    break

            # Build description
            gate_status = result.get("gates", {})
            failed_gates = [
                gate for gate, status in gate_status.items()
                if status == "fail"
            ]

            description = f"Attack detected: {len(violations)} pattern(s) matched"
            if failed_gates:
                description += f" (gates: {', '.join(failed_gates)})"

            # Evidence: first few violations
            config = self._config
            max_violations = getattr(config, "max_violations_to_report", 10)
            evidence_violations = violations[:max_violations]
            evidence = "; ".join(evidence_violations) if evidence_violations else None

            # Calculate confidence
            confidence = _calculate_confidence(violations)

            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=confidence,
                category=primary_type.value,
                description=description,
                evidence=evidence,
                metadata={
                    "attack_types": [at.value for at in attack_types],
                    "failed_gates": failed_gates,
                    "violation_count": len(violations),
                    "jailbreak_detected": result.get("jailbreak_detected", False),
                },
            )

        except Exception as e:
            logger.error(f"PatternDetector error: {e}")
            self._stats["errors"] += 1

            return DetectionResult(
                detected=False,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.0,
                category="error",
                description=f"Detection failed: {str(e)}",
            )


__all__ = [
    "PatternDetector",
    "PatternDetectorConfig",
]
