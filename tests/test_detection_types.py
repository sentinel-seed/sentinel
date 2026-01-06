"""
Tests for sentinelseed.detection.types module.

This module tests the core type definitions used by the Validation 360 architecture.
Tests verify functional correctness, not just structural validity.

Test Categories:
    1. Enum Values: Correct values and string representation
    2. Enum Properties: severity (AttackType), gate (CheckFailureType)
    3. THSP Gate Mapping: Correct mapping to Truth/Harm/Scope/Purpose
    4. Immutability: frozen dataclasses cannot be modified
    5. Factory Methods: safe(), attack_detected(), seed_failure(), nothing_detected()
    6. Computed Properties: is_safe, detection_count, gates_failed, etc.
    7. Serialization: to_dict() produces correct output
    8. Validation: confidence clamping, sequence to tuple conversion
"""

import pytest
from typing import Dict, Any

from sentinelseed.detection.types import (
    DetectionMode,
    AttackType,
    CheckFailureType,
    DetectionResult,
    InputValidationResult,
    OutputValidationResult,
)


# =============================================================================
# DetectionMode Tests
# =============================================================================

class TestDetectionMode:
    """Tests for DetectionMode enum."""

    def test_values_exist(self):
        """Verify all expected values exist."""
        assert DetectionMode.INPUT.value == "input"
        assert DetectionMode.OUTPUT.value == "output"
        assert DetectionMode.UNKNOWN.value == "unknown"

    def test_string_inheritance(self):
        """DetectionMode should be a string enum for easy serialization."""
        assert isinstance(DetectionMode.INPUT, str)
        assert DetectionMode.INPUT == "input"

    def test_all_modes_covered(self):
        """Verify we have exactly 3 modes."""
        assert len(DetectionMode) == 3


# =============================================================================
# AttackType Tests
# =============================================================================

class TestAttackType:
    """Tests for AttackType enum."""

    def test_values_exist(self):
        """Verify all attack types exist with correct values."""
        expected = {
            "JAILBREAK": "jailbreak",
            "INJECTION": "injection",
            "MANIPULATION": "manipulation",
            "HARMFUL_REQUEST": "harmful_request",
            "EVASION": "evasion",
            "STRUCTURAL": "structural",
            "UNKNOWN": "unknown",
        }
        for name, value in expected.items():
            assert getattr(AttackType, name).value == value

    def test_string_inheritance(self):
        """AttackType should be a string enum."""
        assert isinstance(AttackType.JAILBREAK, str)
        assert AttackType.JAILBREAK == "jailbreak"

    def test_all_types_count(self):
        """Verify we have exactly 7 attack types."""
        assert len(AttackType) == 7


class TestAttackTypeSeverity:
    """Tests for AttackType.severity property."""

    def test_critical_severity_types(self):
        """JAILBREAK, INJECTION, HARMFUL_REQUEST are critical."""
        critical_types = [
            AttackType.JAILBREAK,
            AttackType.INJECTION,
            AttackType.HARMFUL_REQUEST,
        ]
        for attack_type in critical_types:
            assert attack_type.severity == "critical", \
                f"{attack_type} should be critical"

    def test_high_severity_types(self):
        """MANIPULATION, EVASION are high severity."""
        high_types = [
            AttackType.MANIPULATION,
            AttackType.EVASION,
        ]
        for attack_type in high_types:
            assert attack_type.severity == "high", \
                f"{attack_type} should be high severity"

    def test_medium_severity_types(self):
        """STRUCTURAL, UNKNOWN are medium severity."""
        medium_types = [
            AttackType.STRUCTURAL,
            AttackType.UNKNOWN,
        ]
        for attack_type in medium_types:
            assert attack_type.severity == "medium", \
                f"{attack_type} should be medium severity"

    def test_severity_is_string(self):
        """Severity should return a string."""
        for attack_type in AttackType:
            assert isinstance(attack_type.severity, str)
            assert attack_type.severity in ("critical", "high", "medium", "low")


# =============================================================================
# CheckFailureType Tests
# =============================================================================

class TestCheckFailureType:
    """Tests for CheckFailureType enum."""

    def test_values_exist(self):
        """Verify all failure types exist with correct values."""
        expected = {
            "HARMFUL_CONTENT": "harmful_content",
            "DECEPTIVE_CONTENT": "deceptive_content",
            "SCOPE_VIOLATION": "scope_violation",
            "PURPOSE_VIOLATION": "purpose_violation",
            "BYPASS_INDICATOR": "bypass_indicator",
            "POLICY_VIOLATION": "policy_violation",
            "UNKNOWN": "unknown",
        }
        for name, value in expected.items():
            assert getattr(CheckFailureType, name).value == value

    def test_all_types_count(self):
        """Verify we have exactly 7 failure types."""
        assert len(CheckFailureType) == 7


class TestCheckFailureTypeGate:
    """Tests for CheckFailureType.gate property - THSP mapping."""

    def test_truth_gate_mapping(self):
        """DECEPTIVE_CONTENT maps to truth gate."""
        assert CheckFailureType.DECEPTIVE_CONTENT.gate == "truth"

    def test_harm_gate_mapping(self):
        """HARMFUL_CONTENT maps to harm gate."""
        assert CheckFailureType.HARMFUL_CONTENT.gate == "harm"

    def test_scope_gate_mapping(self):
        """SCOPE_VIOLATION, BYPASS_INDICATOR, POLICY_VIOLATION map to scope gate."""
        scope_types = [
            CheckFailureType.SCOPE_VIOLATION,
            CheckFailureType.BYPASS_INDICATOR,
            CheckFailureType.POLICY_VIOLATION,
        ]
        for failure_type in scope_types:
            assert failure_type.gate == "scope", \
                f"{failure_type} should map to scope gate"

    def test_purpose_gate_mapping(self):
        """PURPOSE_VIOLATION maps to purpose gate."""
        assert CheckFailureType.PURPOSE_VIOLATION.gate == "purpose"

    def test_unknown_gate_mapping(self):
        """UNKNOWN maps to unknown gate."""
        assert CheckFailureType.UNKNOWN.gate == "unknown"

    def test_gate_is_string(self):
        """Gate should return a string."""
        for failure_type in CheckFailureType:
            assert isinstance(failure_type.gate, str)

    def test_thsp_coverage(self):
        """All four THSP gates should be represented."""
        gates = {ft.gate for ft in CheckFailureType}
        assert "truth" in gates, "Truth gate not represented"
        assert "harm" in gates, "Harm gate not represented"
        assert "scope" in gates, "Scope gate not represented"
        assert "purpose" in gates, "Purpose gate not represented"


# =============================================================================
# DetectionResult Tests
# =============================================================================

class TestDetectionResult:
    """Tests for DetectionResult dataclass."""

    def test_basic_creation(self):
        """Can create with required fields."""
        result = DetectionResult(
            detected=True,
            detector_name="test_detector",
            detector_version="1.0.0",
        )
        assert result.detected is True
        assert result.detector_name == "test_detector"
        assert result.detector_version == "1.0.0"

    def test_default_values(self):
        """Default values are correctly set."""
        result = DetectionResult(
            detected=False,
            detector_name="test",
            detector_version="1.0",
        )
        assert result.confidence == 0.0
        assert result.category == "unknown"
        assert result.description == ""
        assert result.evidence is None
        assert result.metadata == {}

    def test_full_creation(self):
        """Can create with all fields."""
        result = DetectionResult(
            detected=True,
            detector_name="pattern_detector",
            detector_version="2.1.0",
            confidence=0.95,
            category="jailbreak",
            description="Detected jailbreak attempt",
            evidence="ignore previous instructions",
            metadata={"pattern_id": "P001"},
        )
        assert result.confidence == 0.95
        assert result.category == "jailbreak"
        assert result.evidence == "ignore previous instructions"
        assert result.metadata["pattern_id"] == "P001"


class TestDetectionResultImmutability:
    """Tests for DetectionResult immutability (frozen=True)."""

    def test_cannot_modify_detected(self):
        """Cannot modify detected field."""
        result = DetectionResult(
            detected=False,
            detector_name="test",
            detector_version="1.0",
        )
        with pytest.raises(Exception):
            result.detected = True

    def test_cannot_modify_confidence(self):
        """Cannot modify confidence field."""
        result = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
            confidence=0.5,
        )
        with pytest.raises(Exception):
            result.confidence = 0.9


class TestDetectionResultConfidenceValidation:
    """Tests for DetectionResult confidence clamping."""

    def test_confidence_above_one_clamped(self):
        """Confidence > 1.0 is clamped to 1.0."""
        result = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
            confidence=1.5,
        )
        assert result.confidence == 1.0

    def test_confidence_below_zero_clamped(self):
        """Confidence < 0.0 is clamped to 0.0."""
        result = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
            confidence=-0.5,
        )
        assert result.confidence == 0.0

    def test_confidence_at_boundaries(self):
        """Confidence at 0.0 and 1.0 remains unchanged."""
        result_zero = DetectionResult(
            detected=False,
            detector_name="test",
            detector_version="1.0",
            confidence=0.0,
        )
        result_one = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
            confidence=1.0,
        )
        assert result_zero.confidence == 0.0
        assert result_one.confidence == 1.0


class TestDetectionResultFactoryMethods:
    """Tests for DetectionResult factory methods."""

    def test_nothing_detected(self):
        """nothing_detected() creates correct result."""
        result = DetectionResult.nothing_detected(
            detector_name="my_detector",
            detector_version="2.0.0",
        )
        assert result.detected is False
        assert result.detector_name == "my_detector"
        assert result.detector_version == "2.0.0"
        assert result.confidence == 0.0


class TestDetectionResultSerialization:
    """Tests for DetectionResult.to_dict()."""

    def test_to_dict_structure(self):
        """to_dict() returns correct structure."""
        result = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
            confidence=0.8,
            category="injection",
            description="SQL injection detected",
            evidence="DROP TABLE",
            metadata={"line": 42},
        )
        d = result.to_dict()

        assert d["detected"] is True
        assert d["detector_name"] == "test"
        assert d["detector_version"] == "1.0"
        assert d["confidence"] == 0.8
        assert d["category"] == "injection"
        assert d["description"] == "SQL injection detected"
        assert d["evidence"] == "DROP TABLE"
        assert d["metadata"]["line"] == 42

    def test_to_dict_empty_metadata(self):
        """to_dict() handles empty metadata correctly."""
        result = DetectionResult(
            detected=False,
            detector_name="test",
            detector_version="1.0",
        )
        d = result.to_dict()
        assert d["metadata"] == {}

    def test_to_dict_is_serializable(self):
        """to_dict() output can be serialized to JSON."""
        import json
        result = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
            metadata={"nested": {"key": "value"}},
        )
        # Should not raise
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)


# =============================================================================
# InputValidationResult Tests
# =============================================================================

class TestInputValidationResult:
    """Tests for InputValidationResult dataclass."""

    def test_basic_creation(self):
        """Can create with required field."""
        result = InputValidationResult(is_attack=False)
        assert result.is_attack is False

    def test_default_values(self):
        """Default values are correctly set."""
        result = InputValidationResult(is_attack=False)
        assert result.attack_types == ()
        assert result.detections == ()
        assert result.confidence == 0.0
        assert result.blocked is False
        assert result.violations == ()
        assert result.mode == DetectionMode.INPUT
        assert result.metadata == {}

    def test_mode_always_input(self):
        """Mode is always INPUT for InputValidationResult."""
        result = InputValidationResult(is_attack=True)
        assert result.mode == DetectionMode.INPUT


class TestInputValidationResultImmutability:
    """Tests for InputValidationResult immutability."""

    def test_sequences_converted_to_tuples(self):
        """Lists are converted to tuples for immutability."""
        result = InputValidationResult(
            is_attack=True,
            attack_types=[AttackType.JAILBREAK, AttackType.INJECTION],
            violations=["Violation 1", "Violation 2"],
        )
        # Should be tuples, not lists
        assert isinstance(result.attack_types, tuple)
        assert isinstance(result.violations, tuple)

    def test_cannot_modify_is_attack(self):
        """Cannot modify is_attack field."""
        result = InputValidationResult(is_attack=False)
        with pytest.raises(Exception):
            result.is_attack = True


class TestInputValidationResultConfidenceValidation:
    """Tests for InputValidationResult confidence clamping."""

    def test_confidence_clamped_to_valid_range(self):
        """Confidence outside [0, 1] is clamped."""
        result_high = InputValidationResult(is_attack=True, confidence=2.0)
        result_low = InputValidationResult(is_attack=True, confidence=-1.0)
        assert result_high.confidence == 1.0
        assert result_low.confidence == 0.0


class TestInputValidationResultProperties:
    """Tests for InputValidationResult computed properties."""

    def test_is_safe_when_no_attack(self):
        """is_safe is True when is_attack is False."""
        result = InputValidationResult(is_attack=False)
        assert result.is_safe is True

    def test_is_safe_when_attack(self):
        """is_safe is False when is_attack is True."""
        result = InputValidationResult(is_attack=True)
        assert result.is_safe is False

    def test_primary_attack_type_with_attacks(self):
        """primary_attack_type returns first attack type."""
        result = InputValidationResult(
            is_attack=True,
            attack_types=[AttackType.INJECTION, AttackType.JAILBREAK],
        )
        assert result.primary_attack_type == AttackType.INJECTION

    def test_primary_attack_type_no_attacks(self):
        """primary_attack_type returns None when no attacks."""
        result = InputValidationResult(is_attack=False)
        assert result.primary_attack_type is None

    def test_detection_count(self):
        """detection_count counts positive detections."""
        detections = [
            DetectionResult(detected=True, detector_name="d1", detector_version="1.0"),
            DetectionResult(detected=False, detector_name="d2", detector_version="1.0"),
            DetectionResult(detected=True, detector_name="d3", detector_version="1.0"),
        ]
        result = InputValidationResult(
            is_attack=True,
            detections=detections,
        )
        assert result.detection_count == 2


class TestInputValidationResultFactoryMethods:
    """Tests for InputValidationResult factory methods."""

    def test_safe_factory(self):
        """safe() creates a safe result."""
        result = InputValidationResult.safe()
        assert result.is_attack is False
        assert result.is_safe is True
        assert result.blocked is False
        assert result.confidence == 0.0
        assert result.attack_types == ()

    def test_attack_detected_factory(self):
        """attack_detected() creates attack result."""
        detection = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
        )
        result = InputValidationResult.attack_detected(
            attack_types=[AttackType.JAILBREAK],
            violations=["Jailbreak detected"],
            detections=[detection],
            confidence=0.95,
            block=True,
        )
        assert result.is_attack is True
        assert result.is_safe is False
        assert result.blocked is True
        assert result.confidence == 0.95
        assert AttackType.JAILBREAK in result.attack_types
        assert "Jailbreak detected" in result.violations

    def test_attack_detected_default_block(self):
        """attack_detected() blocks by default."""
        result = InputValidationResult.attack_detected(
            attack_types=[AttackType.INJECTION],
            violations=["Injection"],
            detections=[],
        )
        assert result.blocked is True

    def test_attack_detected_no_block(self):
        """attack_detected() can be configured not to block."""
        result = InputValidationResult.attack_detected(
            attack_types=[AttackType.STRUCTURAL],
            violations=["Structural"],
            detections=[],
            block=False,
        )
        assert result.blocked is False


class TestInputValidationResultSerialization:
    """Tests for InputValidationResult.to_dict()."""

    def test_to_dict_structure(self):
        """to_dict() returns correct structure."""
        detection = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
        )
        result = InputValidationResult(
            is_attack=True,
            attack_types=[AttackType.JAILBREAK],
            detections=[detection],
            confidence=0.9,
            blocked=True,
            violations=["Test violation"],
        )
        d = result.to_dict()

        assert d["is_attack"] is True
        assert d["is_safe"] is False
        assert d["attack_types"] == ["jailbreak"]
        assert d["confidence"] == 0.9
        assert d["blocked"] is True
        assert d["violations"] == ["Test violation"]
        assert d["mode"] == "input"
        assert d["detection_count"] == 1
        assert len(d["detections"]) == 1

    def test_to_dict_is_serializable(self):
        """to_dict() output can be serialized to JSON."""
        import json
        result = InputValidationResult.safe()
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)


# =============================================================================
# OutputValidationResult Tests
# =============================================================================

class TestOutputValidationResult:
    """Tests for OutputValidationResult dataclass."""

    def test_basic_creation(self):
        """Can create with required field."""
        result = OutputValidationResult(seed_failed=False)
        assert result.seed_failed is False

    def test_default_values(self):
        """Default values are correctly set."""
        result = OutputValidationResult(seed_failed=False)
        assert result.failure_types == ()
        assert result.checks == ()
        assert result.confidence == 0.0
        assert result.blocked is False
        assert result.violations == ()
        assert result.input_context is None
        assert result.mode == DetectionMode.OUTPUT
        assert result.metadata == {}

    def test_mode_always_output(self):
        """Mode is always OUTPUT for OutputValidationResult."""
        result = OutputValidationResult(seed_failed=True)
        assert result.mode == DetectionMode.OUTPUT

    def test_input_context_preserved(self):
        """Input context is preserved when provided."""
        result = OutputValidationResult(
            seed_failed=False,
            input_context="What is 2+2?",
        )
        assert result.input_context == "What is 2+2?"


class TestOutputValidationResultImmutability:
    """Tests for OutputValidationResult immutability."""

    def test_sequences_converted_to_tuples(self):
        """Lists are converted to tuples for immutability."""
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
            violations=["Harmful content detected"],
        )
        assert isinstance(result.failure_types, tuple)
        assert isinstance(result.violations, tuple)


class TestOutputValidationResultProperties:
    """Tests for OutputValidationResult computed properties."""

    def test_is_safe_when_seed_works(self):
        """is_safe is True when seed_failed is False."""
        result = OutputValidationResult(seed_failed=False)
        assert result.is_safe is True

    def test_is_safe_when_seed_fails(self):
        """is_safe is False when seed_failed is True."""
        result = OutputValidationResult(seed_failed=True)
        assert result.is_safe is False

    def test_primary_failure_type_with_failures(self):
        """primary_failure_type returns first failure type."""
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[
                CheckFailureType.DECEPTIVE_CONTENT,
                CheckFailureType.HARMFUL_CONTENT,
            ],
        )
        assert result.primary_failure_type == CheckFailureType.DECEPTIVE_CONTENT

    def test_primary_failure_type_no_failures(self):
        """primary_failure_type returns None when no failures."""
        result = OutputValidationResult(seed_failed=False)
        assert result.primary_failure_type is None

    def test_check_count(self):
        """check_count counts positive checks."""
        checks = [
            DetectionResult(detected=True, detector_name="c1", detector_version="1.0"),
            DetectionResult(detected=False, detector_name="c2", detector_version="1.0"),
        ]
        result = OutputValidationResult(
            seed_failed=True,
            checks=checks,
        )
        assert result.check_count == 1


class TestOutputValidationResultGatesFailed:
    """Tests for OutputValidationResult.gates_failed property."""

    def test_gates_failed_single_failure(self):
        """gates_failed returns correct gate for single failure."""
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
        )
        assert "harm" in result.gates_failed

    def test_gates_failed_multiple_failures(self):
        """gates_failed returns unique gates."""
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[
                CheckFailureType.HARMFUL_CONTENT,  # harm
                CheckFailureType.DECEPTIVE_CONTENT,  # truth
                CheckFailureType.SCOPE_VIOLATION,  # scope
            ],
        )
        gates = result.gates_failed
        assert "harm" in gates
        assert "truth" in gates
        assert "scope" in gates
        # Should be unique
        assert len(gates) == 3

    def test_gates_failed_with_duplicate_gates(self):
        """gates_failed deduplicates gates."""
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[
                CheckFailureType.SCOPE_VIOLATION,  # scope
                CheckFailureType.BYPASS_INDICATOR,  # scope
                CheckFailureType.POLICY_VIOLATION,  # scope
            ],
        )
        gates = result.gates_failed
        # All map to scope, should be deduplicated
        assert len(gates) == 1
        assert gates[0] == "scope"

    def test_gates_failed_empty_when_no_failures(self):
        """gates_failed is empty when no failure types."""
        result = OutputValidationResult(seed_failed=False)
        assert result.gates_failed == []

    def test_gates_failed_all_thsp_gates(self):
        """gates_failed can represent all THSP gates."""
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[
                CheckFailureType.DECEPTIVE_CONTENT,  # truth
                CheckFailureType.HARMFUL_CONTENT,  # harm
                CheckFailureType.SCOPE_VIOLATION,  # scope
                CheckFailureType.PURPOSE_VIOLATION,  # purpose
            ],
        )
        gates = set(result.gates_failed)
        assert gates == {"truth", "harm", "scope", "purpose"}


class TestOutputValidationResultFactoryMethods:
    """Tests for OutputValidationResult factory methods."""

    def test_safe_factory(self):
        """safe() creates a safe result."""
        result = OutputValidationResult.safe()
        assert result.seed_failed is False
        assert result.is_safe is True
        assert result.blocked is False
        assert result.confidence == 0.0

    def test_safe_factory_with_context(self):
        """safe() preserves input context."""
        result = OutputValidationResult.safe(input_context="test input")
        assert result.input_context == "test input"

    def test_seed_failure_factory(self):
        """seed_failure() creates failure result."""
        check = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
        )
        result = OutputValidationResult.seed_failure(
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
            violations=["Harmful content detected"],
            checks=[check],
            confidence=0.88,
            input_context="malicious input",
            block=True,
        )
        assert result.seed_failed is True
        assert result.is_safe is False
        assert result.blocked is True
        assert result.confidence == 0.88
        assert CheckFailureType.HARMFUL_CONTENT in result.failure_types
        assert result.input_context == "malicious input"

    def test_seed_failure_default_block(self):
        """seed_failure() blocks by default."""
        result = OutputValidationResult.seed_failure(
            failure_types=[CheckFailureType.DECEPTIVE_CONTENT],
            violations=["Deception"],
            checks=[],
        )
        assert result.blocked is True


class TestOutputValidationResultSerialization:
    """Tests for OutputValidationResult.to_dict()."""

    def test_to_dict_structure(self):
        """to_dict() returns correct structure."""
        check = DetectionResult(
            detected=True,
            detector_name="test",
            detector_version="1.0",
        )
        result = OutputValidationResult(
            seed_failed=True,
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
            checks=[check],
            confidence=0.9,
            blocked=True,
            violations=["Harmful output"],
            input_context="bad input",
        )
        d = result.to_dict()

        assert d["seed_failed"] is True
        assert d["is_safe"] is False
        assert d["failure_types"] == ["harmful_content"]
        assert d["gates_failed"] == ["harm"]
        assert d["confidence"] == 0.9
        assert d["blocked"] is True
        assert d["violations"] == ["Harmful output"]
        assert d["input_context"] == "bad input"
        assert d["mode"] == "output"
        assert d["check_count"] == 1
        assert len(d["checks"]) == 1

    def test_to_dict_is_serializable(self):
        """to_dict() output can be serialized to JSON."""
        import json
        result = OutputValidationResult.safe()
        json_str = json.dumps(result.to_dict())
        assert isinstance(json_str, str)


# =============================================================================
# Integration Tests
# =============================================================================

class TestValidation360Integration:
    """Integration tests verifying 360 architecture coherence."""

    def test_input_and_output_results_differ(self):
        """InputValidationResult and OutputValidationResult have distinct purposes."""
        input_result = InputValidationResult(is_attack=True)
        output_result = OutputValidationResult(seed_failed=True)

        # Different modes
        assert input_result.mode == DetectionMode.INPUT
        assert output_result.mode == DetectionMode.OUTPUT

        # Different primary attributes
        assert hasattr(input_result, "is_attack")
        assert hasattr(output_result, "seed_failed")

    def test_detection_result_works_with_both(self):
        """DetectionResult can be used by both InputValidationResult and OutputValidationResult."""
        detection = DetectionResult(
            detected=True,
            detector_name="shared_detector",
            detector_version="1.0.0",
            confidence=0.85,
        )

        input_result = InputValidationResult(
            is_attack=True,
            detections=[detection],
        )
        output_result = OutputValidationResult(
            seed_failed=True,
            checks=[detection],
        )

        assert input_result.detection_count == 1
        assert output_result.check_count == 1

    def test_attack_types_and_failure_types_are_distinct(self):
        """AttackType (input) and CheckFailureType (output) are different enums."""
        # They should not have overlapping values that cause confusion
        attack_values = {at.value for at in AttackType}
        failure_values = {ft.value for ft in CheckFailureType}

        # Unknown is acceptable overlap
        shared = attack_values & failure_values
        assert shared == {"unknown"}, \
            f"Only 'unknown' should be shared, found: {shared}"

    def test_full_360_flow_simulation(self):
        """Simulate a complete 360 validation flow."""
        # Step 1: Input validation (attack detected)
        input_detection = DetectionResult(
            detected=True,
            detector_name="pattern_detector",
            detector_version="1.0.0",
            confidence=0.92,
            category=AttackType.JAILBREAK.value,
            description="Jailbreak pattern: 'ignore instructions'",
            evidence="ignore previous instructions",
        )

        input_result = InputValidationResult.attack_detected(
            attack_types=[AttackType.JAILBREAK],
            violations=["Jailbreak attempt detected"],
            detections=[input_detection],
            confidence=0.92,
            block=False,  # Let's see what AI produces
        )

        # Verify input validation result
        assert input_result.is_attack is True
        assert input_result.primary_attack_type == AttackType.JAILBREAK
        assert input_result.detection_count == 1

        # Step 2: Output validation (seed failed)
        output_check = DetectionResult(
            detected=True,
            detector_name="harmful_content_checker",
            detector_version="1.0.0",
            confidence=0.88,
            category=CheckFailureType.HARMFUL_CONTENT.value,
            description="AI produced harmful instructions",
        )

        output_result = OutputValidationResult.seed_failure(
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
            violations=["Output contains harmful content"],
            checks=[output_check],
            confidence=0.88,
            input_context="ignore previous instructions",
            block=True,
        )

        # Verify output validation result
        assert output_result.seed_failed is True
        assert output_result.primary_failure_type == CheckFailureType.HARMFUL_CONTENT
        assert "harm" in output_result.gates_failed
        assert output_result.input_context == "ignore previous instructions"

        # Step 3: Verify serialization works for both
        input_dict = input_result.to_dict()
        output_dict = output_result.to_dict()

        assert input_dict["mode"] == "input"
        assert output_dict["mode"] == "output"
        assert input_dict["attack_types"] == ["jailbreak"]
        assert output_dict["failure_types"] == ["harmful_content"]
