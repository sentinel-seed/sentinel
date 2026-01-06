"""
Type definitions for the Detection module (Validation 360).

This module defines the core types used by InputValidator and OutputValidator:

- DetectionMode: Enum indicating the validation context (input/output)
- AttackType: Enum categorizing detected attack patterns
- CheckFailureType: Enum categorizing output validation failures
- DetectionResult: Base result for individual detector/checker outputs
- InputValidationResult: Result from InputValidator (attack detection)
- OutputValidationResult: Result from OutputValidator (behavior verification)

Architecture:
    The Detection module implements the 360 validation architecture:

    Input → [InputValidator] → AI + Seed → [OutputValidator] → Output

    InputValidator: Detects ATTACKS (jailbreaks, injections, manipulation)
    OutputValidator: Detects FAILURES (seed bypass, harmful content, deception)

Design Principles:
    1. Immutable results - All result types are frozen dataclasses
    2. Factory methods - Convenient creation patterns (safe(), unsafe(), etc.)
    3. Serialization - Full to_dict() support for logging and APIs
    4. Backwards compatible - Works with existing ValidationResult where needed
    5. Type safety - Complete type hints for static analysis

References:
    - VALIDATION_360_v2.md: Architecture specification
    - INPUT_VALIDATOR_v2.md: InputValidator design
    - OUTPUT_VALIDATOR_v2.md: OutputValidator design
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Sequence


class DetectionMode(str, Enum):
    """
    Indicates the validation context/mode.

    The 360 architecture distinguishes between input and output validation
    because they answer fundamentally different questions:

    - INPUT: "Is this an ATTACK?" (detect manipulation attempts)
    - OUTPUT: "Did the SEED fail?" (verify behavior compliance)

    Values:
        INPUT: Validating user input before processing
        OUTPUT: Validating AI response after generation
        UNKNOWN: Mode not specified (should be avoided)
    """
    INPUT = "input"
    OUTPUT = "output"
    UNKNOWN = "unknown"


class AttackType(str, Enum):
    """
    Categorization of detected attack patterns.

    These categories help in understanding the nature of detected threats
    and enable targeted countermeasures and metrics.

    Categories:
        JAILBREAK: Attempts to bypass system instructions
            - "Ignore previous instructions"
            - "You are now DAN"
            - Role-playing exploits

        INJECTION: Attempts to inject malicious content
            - Prompt injection
            - Command injection patterns
            - Delimiter manipulation

        MANIPULATION: Social engineering and deception
            - Authority impersonation
            - Urgency exploitation
            - Emotional manipulation

        HARMFUL_REQUEST: Direct requests for harmful content
            - Violence instructions
            - Illegal activities
            - Dangerous information

        EVASION: Attempts to evade detection
            - Encoding tricks (base64, rot13)
            - Language switching
            - Synonym substitution

        STRUCTURAL: Structural manipulation techniques
            - Nested instructions
            - Context overflow
            - Format exploitation

        UNKNOWN: Attack detected but not categorized
    """
    JAILBREAK = "jailbreak"
    INJECTION = "injection"
    MANIPULATION = "manipulation"
    HARMFUL_REQUEST = "harmful_request"
    EVASION = "evasion"
    STRUCTURAL = "structural"
    UNKNOWN = "unknown"

    @property
    def severity(self) -> str:
        """
        Get the default severity level for this attack type.

        Returns:
            Severity level: "critical", "high", "medium", or "low"
        """
        severity_map = {
            AttackType.JAILBREAK: "critical",
            AttackType.INJECTION: "critical",
            AttackType.MANIPULATION: "high",
            AttackType.HARMFUL_REQUEST: "critical",
            AttackType.EVASION: "high",
            AttackType.STRUCTURAL: "medium",
            AttackType.UNKNOWN: "medium",
        }
        return severity_map.get(self, "medium")


class CheckFailureType(str, Enum):
    """
    Categorization of output validation failures.

    These indicate that the seed/safety measures failed to prevent
    problematic content from being generated.

    Categories:
        HARMFUL_CONTENT: Output contains harmful material
            - Violence, abuse, dangerous instructions
            - Maps to THSP Harm gate failure

        DECEPTIVE_CONTENT: Output contains deception
            - Misinformation, fake content
            - Maps to THSP Truth gate failure

        SCOPE_VIOLATION: Output exceeds intended scope
            - Acting outside defined role
            - Maps to THSP Scope gate failure

        PURPOSE_VIOLATION: Output lacks legitimate purpose
            - Unnecessary harmful detail
            - Maps to THSP Purpose gate failure

        BYPASS_INDICATOR: Signs that a jailbreak succeeded
            - AI acknowledging override
            - Apologetic harmful content

        POLICY_VIOLATION: Violates specific policy rules
            - Custom rules defined by configuration

        UNKNOWN: Failure detected but not categorized
    """
    HARMFUL_CONTENT = "harmful_content"
    DECEPTIVE_CONTENT = "deceptive_content"
    SCOPE_VIOLATION = "scope_violation"
    PURPOSE_VIOLATION = "purpose_violation"
    BYPASS_INDICATOR = "bypass_indicator"
    POLICY_VIOLATION = "policy_violation"
    UNKNOWN = "unknown"

    @property
    def gate(self) -> str:
        """
        Get the THSP gate this failure type corresponds to.

        Returns:
            Gate name: "truth", "harm", "scope", or "purpose"
        """
        gate_map = {
            CheckFailureType.HARMFUL_CONTENT: "harm",
            CheckFailureType.DECEPTIVE_CONTENT: "truth",
            CheckFailureType.SCOPE_VIOLATION: "scope",
            CheckFailureType.PURPOSE_VIOLATION: "purpose",
            CheckFailureType.BYPASS_INDICATOR: "scope",
            CheckFailureType.POLICY_VIOLATION: "scope",
            CheckFailureType.UNKNOWN: "unknown",
        }
        return gate_map.get(self, "unknown")


@dataclass(frozen=True)
class DetectionResult:
    """
    Base result from an individual detector or checker.

    This is the output from a single detection component (e.g., PatternDetector,
    DeceptionChecker). Multiple DetectionResults are aggregated into
    InputValidationResult or OutputValidationResult.

    Attributes:
        detected: Whether something was detected (attack or failure)
        detector_name: Name of the detector/checker that produced this result
        detector_version: Version of the detector/checker
        confidence: Confidence score (0.0 to 1.0)
        category: Category of detection (AttackType or CheckFailureType as string)
        description: Human-readable description of what was detected
        evidence: Specific text or pattern that triggered detection
        metadata: Additional detector-specific information

    Example:
        result = DetectionResult(
            detected=True,
            detector_name="pattern_detector",
            detector_version="1.0.0",
            confidence=0.95,
            category="jailbreak",
            description="Detected jailbreak attempt: 'ignore previous instructions'",
            evidence="ignore previous instructions",
        )
    """
    detected: bool
    detector_name: str
    detector_version: str
    confidence: float = 0.0
    category: str = "unknown"
    description: str = ""
    evidence: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            # Using object.__setattr__ because dataclass is frozen
            object.__setattr__(
                self,
                "confidence",
                max(0.0, min(1.0, self.confidence))
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        return {
            "detected": self.detected,
            "detector_name": self.detector_name,
            "detector_version": self.detector_version,
            "confidence": self.confidence,
            "category": self.category,
            "description": self.description,
            "evidence": self.evidence,
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def nothing_detected(
        cls,
        detector_name: str,
        detector_version: str,
    ) -> "DetectionResult":
        """
        Factory method for when nothing was detected.

        Args:
            detector_name: Name of the detector
            detector_version: Version of the detector

        Returns:
            DetectionResult with detected=False
        """
        return cls(
            detected=False,
            detector_name=detector_name,
            detector_version=detector_version,
            confidence=0.0,
        )


@dataclass(frozen=True)
class InputValidationResult:
    """
    Result from InputValidator - attack detection on input.

    This represents the aggregated result from all detectors run on user input.
    The key question answered: "Is this an ATTACK?"

    Attributes:
        is_attack: Whether an attack was detected
        attack_types: List of detected attack categories
        detections: Individual detection results from each detector
        confidence: Overall confidence score (max of individual confidences)
        blocked: Whether the input should be blocked
        violations: Human-readable list of violation descriptions
        mode: Always DetectionMode.INPUT
        metadata: Additional information about the validation

    Properties:
        is_safe: Inverse of is_attack (for compatibility)
        primary_attack_type: First attack type if any, else None
        detection_count: Number of positive detections

    Example:
        result = InputValidationResult(
            is_attack=True,
            attack_types=[AttackType.JAILBREAK],
            detections=[detection1, detection2],
            confidence=0.95,
            blocked=True,
            violations=["Detected jailbreak: 'ignore previous instructions'"],
        )

        if result.is_attack:
            log_attack(result.attack_types)
            return block_response()
    """
    is_attack: bool
    attack_types: Sequence[AttackType] = field(default_factory=list)
    detections: Sequence[DetectionResult] = field(default_factory=list)
    confidence: float = 0.0
    blocked: bool = False
    violations: Sequence[str] = field(default_factory=list)
    mode: DetectionMode = DetectionMode.INPUT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure immutability and validate fields."""
        # Convert mutable sequences to tuples for immutability
        if not isinstance(self.attack_types, tuple):
            object.__setattr__(self, "attack_types", tuple(self.attack_types))
        if not isinstance(self.detections, tuple):
            object.__setattr__(self, "detections", tuple(self.detections))
        if not isinstance(self.violations, tuple):
            object.__setattr__(self, "violations", tuple(self.violations))

        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self,
                "confidence",
                max(0.0, min(1.0, self.confidence))
            )

    @property
    def is_safe(self) -> bool:
        """
        Whether the input is considered safe (no attack detected).

        This is the inverse of is_attack, provided for compatibility
        with code expecting ValidationResult-style interface.

        Returns:
            True if no attack detected, False otherwise
        """
        return not self.is_attack

    @property
    def primary_attack_type(self) -> Optional[AttackType]:
        """
        Get the primary (first) attack type if any.

        Returns:
            First AttackType in attack_types, or None if empty
        """
        return self.attack_types[0] if self.attack_types else None

    @property
    def detection_count(self) -> int:
        """
        Count of positive detections.

        Returns:
            Number of DetectionResults with detected=True
        """
        return sum(1 for d in self.detections if d.detected)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        return {
            "is_attack": self.is_attack,
            "is_safe": self.is_safe,
            "attack_types": [at.value for at in self.attack_types],
            "confidence": self.confidence,
            "blocked": self.blocked,
            "violations": list(self.violations),
            "mode": self.mode.value,
            "detection_count": self.detection_count,
            "detections": [d.to_dict() for d in self.detections],
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def safe(cls) -> "InputValidationResult":
        """
        Factory method for safe input (no attack detected).

        Returns:
            InputValidationResult indicating input is safe
        """
        return cls(
            is_attack=False,
            blocked=False,
            confidence=0.0,
        )

    @classmethod
    def attack_detected(
        cls,
        attack_types: Sequence[AttackType],
        violations: Sequence[str],
        detections: Sequence[DetectionResult],
        confidence: float = 1.0,
        block: bool = True,
    ) -> "InputValidationResult":
        """
        Factory method for when an attack is detected.

        Args:
            attack_types: Types of attacks detected
            violations: Human-readable violation descriptions
            detections: Individual detection results
            confidence: Confidence score (0.0 to 1.0)
            block: Whether to block the input

        Returns:
            InputValidationResult indicating attack detected
        """
        return cls(
            is_attack=True,
            attack_types=attack_types,
            detections=detections,
            confidence=confidence,
            blocked=block,
            violations=violations,
        )


@dataclass(frozen=True)
class OutputValidationResult:
    """
    Result from OutputValidator - behavior verification on output.

    This represents the aggregated result from all checkers run on AI output.
    The key question answered: "Did the SEED fail?"

    Attributes:
        seed_failed: Whether the seed/safety measures failed
        failure_types: List of detected failure categories
        checks: Individual check results from each checker
        confidence: Overall confidence score
        blocked: Whether the output should be blocked
        violations: Human-readable list of failure descriptions
        input_context: Original input for context (if provided)
        mode: Always DetectionMode.OUTPUT
        metadata: Additional information about the validation

    Properties:
        is_safe: Inverse of seed_failed (for compatibility)
        gates_failed: List of THSP gates that failed
        primary_failure_type: First failure type if any, else None

    Example:
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
            checks=[check1, check2],
            confidence=0.90,
            blocked=True,
            violations=["Output contains harmful instructions"],
            input_context="How to hack...",
        )

        if result.seed_failed:
            log_seed_failure(result.failure_types)
            return block_and_alert()
    """
    seed_failed: bool
    failure_types: Sequence[CheckFailureType] = field(default_factory=list)
    checks: Sequence[DetectionResult] = field(default_factory=list)
    confidence: float = 0.0
    blocked: bool = False
    violations: Sequence[str] = field(default_factory=list)
    input_context: Optional[str] = None
    mode: DetectionMode = DetectionMode.OUTPUT
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure immutability and validate fields."""
        # Convert mutable sequences to tuples for immutability
        if not isinstance(self.failure_types, tuple):
            object.__setattr__(self, "failure_types", tuple(self.failure_types))
        if not isinstance(self.checks, tuple):
            object.__setattr__(self, "checks", tuple(self.checks))
        if not isinstance(self.violations, tuple):
            object.__setattr__(self, "violations", tuple(self.violations))

        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self,
                "confidence",
                max(0.0, min(1.0, self.confidence))
            )

    @property
    def is_safe(self) -> bool:
        """
        Whether the output is considered safe (seed worked).

        This is the inverse of seed_failed, provided for compatibility
        with code expecting ValidationResult-style interface.

        Returns:
            True if seed worked, False if seed failed
        """
        return not self.seed_failed

    @property
    def gates_failed(self) -> List[str]:
        """
        Get list of THSP gates that failed based on failure types.

        Returns:
            Unique list of failed gate names
        """
        gates = set()
        for ft in self.failure_types:
            gates.add(ft.gate)
        return list(gates)

    @property
    def primary_failure_type(self) -> Optional[CheckFailureType]:
        """
        Get the primary (first) failure type if any.

        Returns:
            First CheckFailureType in failure_types, or None if empty
        """
        return self.failure_types[0] if self.failure_types else None

    @property
    def check_count(self) -> int:
        """
        Count of positive check failures.

        Returns:
            Number of DetectionResults with detected=True
        """
        return sum(1 for c in self.checks if c.detected)

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        return {
            "seed_failed": self.seed_failed,
            "is_safe": self.is_safe,
            "failure_types": [ft.value for ft in self.failure_types],
            "gates_failed": self.gates_failed,
            "confidence": self.confidence,
            "blocked": self.blocked,
            "violations": list(self.violations),
            "input_context": self.input_context,
            "mode": self.mode.value,
            "check_count": self.check_count,
            "checks": [c.to_dict() for c in self.checks],
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def safe(cls, input_context: Optional[str] = None) -> "OutputValidationResult":
        """
        Factory method for safe output (seed worked).

        Args:
            input_context: Original input for context

        Returns:
            OutputValidationResult indicating output is safe
        """
        return cls(
            seed_failed=False,
            blocked=False,
            confidence=0.0,
            input_context=input_context,
        )

    @classmethod
    def seed_failure(
        cls,
        failure_types: Sequence[CheckFailureType],
        violations: Sequence[str],
        checks: Sequence[DetectionResult],
        confidence: float = 1.0,
        input_context: Optional[str] = None,
        block: bool = True,
    ) -> "OutputValidationResult":
        """
        Factory method for when the seed failed.

        Args:
            failure_types: Types of failures detected
            violations: Human-readable failure descriptions
            checks: Individual check results
            confidence: Confidence score (0.0 to 1.0)
            input_context: Original input for context
            block: Whether to block the output

        Returns:
            OutputValidationResult indicating seed failed
        """
        return cls(
            seed_failed=True,
            failure_types=failure_types,
            checks=checks,
            confidence=confidence,
            blocked=block,
            violations=violations,
            input_context=input_context,
        )


class ObfuscationType(str, Enum):
    """
    Categorization of text obfuscation techniques.

    These categories represent techniques used to hide malicious content
    from detection systems while remaining interpretable by LLMs.

    Based on research:
        - "Bypassing Prompt Injection and Jailbreak Detection in LLM Guardrails"
          (arXiv:2504.11168) - Tested 6 guardrail systems
        - "Special-Character Adversarial Attacks on Open-Source Language Models"
          (arXiv:2508.14070) - Unicode attack patterns
        - "StructuralSleight: Automated Jailbreak Attacks" (arXiv:2406.08754)
          - 94.62% ASR on GPT-4o

    Categories:
        ENCODING: Text encoded in alternative formats
            - Base64, hexadecimal, ROT-13
            - ASR: High (models can decode)

        UNICODE_CONTROL: Invisible/control Unicode characters
            - Zero-width spaces (U+200B-U+200D)
            - Bidirectional overrides (U+202E, U+202D)
            - ASR: 44-99% depending on technique

        UNICODE_SUBSTITUTION: Character substitution via Unicode
            - Fullwidth characters (U+FF00-U+FFEF)
            - Mathematical alphanumeric (U+1D400-U+1D7FF)
            - Homoglyphs from different scripts
            - ASR: 44-76%

        LEETSPEAK: Alphanumeric character substitution
            - h4ck3r, l33t, p@ssw0rd
            - ASR: 81-95%

        TEXT_MANIPULATION: Structural text manipulation
            - Excessive spaces (h e l l o)
            - Reversed text
            - Character fragmentation
            - ASR: Variable

        MIXED: Multiple obfuscation techniques combined
            - Higher evasion potential
            - Harder to normalize

        UNKNOWN: Obfuscation detected but not categorized
    """
    ENCODING = "encoding"
    UNICODE_CONTROL = "unicode_control"
    UNICODE_SUBSTITUTION = "unicode_substitution"
    LEETSPEAK = "leetspeak"
    TEXT_MANIPULATION = "text_manipulation"
    MIXED = "mixed"
    UNKNOWN = "unknown"

    @property
    def risk_level(self) -> str:
        """
        Get the risk level associated with this obfuscation type.

        Obfuscation itself isn't harmful, but indicates intent to evade
        detection. Risk levels reflect likelihood of malicious intent.

        Returns:
            Risk level: "high", "medium", or "low"
        """
        risk_map = {
            ObfuscationType.ENCODING: "high",
            ObfuscationType.UNICODE_CONTROL: "high",
            ObfuscationType.UNICODE_SUBSTITUTION: "medium",
            ObfuscationType.LEETSPEAK: "medium",
            ObfuscationType.TEXT_MANIPULATION: "low",
            ObfuscationType.MIXED: "high",
            ObfuscationType.UNKNOWN: "medium",
        }
        return risk_map.get(self, "medium")


@dataclass(frozen=True)
class ObfuscationInfo:
    """
    Information about a detected obfuscation technique.

    This captures details about a single obfuscation technique found
    in the text, including what was found and how it was normalized.

    Attributes:
        type: The category of obfuscation
        technique: Specific technique name (e.g., "base64", "zero_width")
        original: The original obfuscated text segment
        normalized: The normalized/decoded text segment
        confidence: Confidence that this is obfuscation (0.0-1.0)
        position: Start position in original text (optional)
        metadata: Additional technique-specific information

    Example:
        info = ObfuscationInfo(
            type=ObfuscationType.ENCODING,
            technique="base64",
            original="SGVsbG8gd29ybGQ=",
            normalized="Hello world",
            confidence=0.95,
        )
    """
    type: ObfuscationType
    technique: str
    original: str
    normalized: str
    confidence: float = 0.0
    position: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate fields after initialization."""
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self,
                "confidence",
                max(0.0, min(1.0, self.confidence))
            )

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        return {
            "type": self.type.value,
            "technique": self.technique,
            "original": self.original,
            "normalized": self.normalized,
            "confidence": self.confidence,
            "position": self.position,
            "metadata": dict(self.metadata) if self.metadata else {},
        }


@dataclass(frozen=True)
class NormalizationResult:
    """
    Result from TextNormalizer preprocessing.

    This represents the output of the normalization phase, which runs
    BEFORE detectors to remove obfuscation and enable accurate detection.

    The normalization pipeline:
        1. Detect obfuscation techniques present in text
        2. Apply normalizations (decode, remove, substitute)
        3. Return normalized text + metadata about what was found

    Attributes:
        normalized_text: Text after normalization (for detectors to analyze)
        original_text: Original input text (preserved for reference)
        is_obfuscated: Whether any obfuscation was detected
        obfuscations: List of detected obfuscation techniques
        confidence: Overall confidence of obfuscation detection (0.0-1.0)
        normalization_applied: Whether any normalization was actually applied
        metadata: Additional information about the normalization process

    Properties:
        obfuscation_types: Unique set of ObfuscationType values detected
        obfuscation_count: Number of obfuscation techniques found
        primary_obfuscation: The highest-confidence obfuscation if any
        risk_level: Overall risk level based on obfuscation types

    Example:
        result = NormalizationResult(
            normalized_text="How to make a bomb",
            original_text="SG93IHRvIG1ha2UgYSBib21i",  # Base64
            is_obfuscated=True,
            obfuscations=[
                ObfuscationInfo(
                    type=ObfuscationType.ENCODING,
                    technique="base64",
                    original="SG93IHRvIG1ha2UgYSBib21i",
                    normalized="How to make a bomb",
                    confidence=0.98,
                )
            ],
            confidence=0.98,
        )

        if result.is_obfuscated:
            # Increase suspicion - why encode innocent content?
            risk_boost = 0.2
    """
    normalized_text: str
    original_text: str
    is_obfuscated: bool = False
    obfuscations: Sequence[ObfuscationInfo] = field(default_factory=list)
    confidence: float = 0.0
    normalization_applied: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Ensure immutability and validate fields."""
        # Convert mutable sequence to tuple for immutability
        if not isinstance(self.obfuscations, tuple):
            object.__setattr__(self, "obfuscations", tuple(self.obfuscations))

        # Validate confidence
        if not 0.0 <= self.confidence <= 1.0:
            object.__setattr__(
                self,
                "confidence",
                max(0.0, min(1.0, self.confidence))
            )

    @property
    def obfuscation_types(self) -> List[ObfuscationType]:
        """
        Get unique obfuscation types detected.

        Returns:
            List of unique ObfuscationType values
        """
        seen = set()
        types = []
        for obs in self.obfuscations:
            if obs.type not in seen:
                seen.add(obs.type)
                types.append(obs.type)
        return types

    @property
    def obfuscation_count(self) -> int:
        """
        Count of obfuscation techniques found.

        Returns:
            Number of ObfuscationInfo entries
        """
        return len(self.obfuscations)

    @property
    def primary_obfuscation(self) -> Optional[ObfuscationInfo]:
        """
        Get the highest-confidence obfuscation if any.

        Returns:
            ObfuscationInfo with highest confidence, or None
        """
        if not self.obfuscations:
            return None
        return max(self.obfuscations, key=lambda o: o.confidence)

    @property
    def risk_level(self) -> str:
        """
        Get overall risk level based on obfuscation types.

        Returns:
            "high", "medium", "low", or "none"
        """
        if not self.is_obfuscated:
            return "none"

        # If multiple types, it's high risk (deliberate evasion)
        if len(self.obfuscation_types) > 1:
            return "high"

        # Otherwise, use the risk level of the primary obfuscation
        primary = self.primary_obfuscation
        if primary:
            return primary.type.risk_level

        return "medium"

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dict representation suitable for JSON serialization
        """
        return {
            "normalized_text": self.normalized_text,
            "original_text": self.original_text,
            "is_obfuscated": self.is_obfuscated,
            "obfuscations": [o.to_dict() for o in self.obfuscations],
            "obfuscation_types": [t.value for t in self.obfuscation_types],
            "obfuscation_count": self.obfuscation_count,
            "confidence": self.confidence,
            "normalization_applied": self.normalization_applied,
            "risk_level": self.risk_level,
            "metadata": dict(self.metadata) if self.metadata else {},
        }

    @classmethod
    def no_obfuscation(cls, text: str) -> "NormalizationResult":
        """
        Factory method for text with no obfuscation.

        Args:
            text: The original (and normalized) text

        Returns:
            NormalizationResult indicating no obfuscation found
        """
        return cls(
            normalized_text=text,
            original_text=text,
            is_obfuscated=False,
            normalization_applied=False,
            confidence=0.0,
        )

    @classmethod
    def obfuscation_found(
        cls,
        original_text: str,
        normalized_text: str,
        obfuscations: Sequence[ObfuscationInfo],
        confidence: Optional[float] = None,
    ) -> "NormalizationResult":
        """
        Factory method for text with obfuscation detected.

        Args:
            original_text: The original obfuscated text
            normalized_text: The normalized/decoded text
            obfuscations: List of detected obfuscation techniques
            confidence: Overall confidence (defaults to max of obfuscations)

        Returns:
            NormalizationResult indicating obfuscation found
        """
        if confidence is None and obfuscations:
            confidence = max(o.confidence for o in obfuscations)
        elif confidence is None:
            confidence = 0.0

        return cls(
            normalized_text=normalized_text,
            original_text=original_text,
            is_obfuscated=True,
            obfuscations=obfuscations,
            confidence=confidence,
            normalization_applied=normalized_text != original_text,
        )


__all__ = [
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
]
