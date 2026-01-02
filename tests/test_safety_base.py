"""
Comprehensive tests for the Safety Base Module.

Tests cover:
- SafetyLevel enum and comparisons
- ViolationType enum and properties
- SafetyResult dataclass and methods
- SafetyValidator abstract base class
"""

import pytest
from typing import Any, Dict, Optional

from sentinelseed.safety.base import (
    SafetyLevel,
    ViolationType,
    SafetyResult,
    SafetyValidator,
    __version__,
)


# =============================================================================
# SafetyLevel Tests
# =============================================================================

class TestSafetyLevel:
    """Tests for SafetyLevel enum."""

    def test_all_values_exist(self):
        """Test that all expected safety levels exist."""
        assert SafetyLevel.SAFE.value == "safe"
        assert SafetyLevel.WARNING.value == "warning"
        assert SafetyLevel.DANGEROUS.value == "dangerous"
        assert SafetyLevel.BLOCKED.value == "blocked"
        assert SafetyLevel.CRITICAL.value == "critical"

    def test_ordering_less_than(self):
        """Test SafetyLevel ordering (less than)."""
        assert SafetyLevel.SAFE < SafetyLevel.WARNING
        assert SafetyLevel.WARNING < SafetyLevel.DANGEROUS
        assert SafetyLevel.DANGEROUS < SafetyLevel.BLOCKED
        assert SafetyLevel.BLOCKED < SafetyLevel.CRITICAL

    def test_ordering_greater_than(self):
        """Test SafetyLevel ordering (greater than)."""
        assert SafetyLevel.CRITICAL > SafetyLevel.BLOCKED
        assert SafetyLevel.BLOCKED > SafetyLevel.DANGEROUS
        assert SafetyLevel.DANGEROUS > SafetyLevel.WARNING
        assert SafetyLevel.WARNING > SafetyLevel.SAFE

    def test_ordering_less_equal(self):
        """Test SafetyLevel ordering (less than or equal)."""
        assert SafetyLevel.SAFE <= SafetyLevel.SAFE
        assert SafetyLevel.SAFE <= SafetyLevel.WARNING
        assert SafetyLevel.WARNING <= SafetyLevel.DANGEROUS

    def test_ordering_greater_equal(self):
        """Test SafetyLevel ordering (greater than or equal)."""
        assert SafetyLevel.CRITICAL >= SafetyLevel.CRITICAL
        assert SafetyLevel.CRITICAL >= SafetyLevel.BLOCKED
        assert SafetyLevel.BLOCKED >= SafetyLevel.DANGEROUS

    def test_ordering_with_non_safetylevel(self):
        """Test that comparing with non-SafetyLevel returns NotImplemented."""
        assert SafetyLevel.SAFE.__lt__("safe") == NotImplemented
        assert SafetyLevel.SAFE.__gt__(1) == NotImplemented

    def test_requires_action_property(self):
        """Test requires_action property."""
        assert SafetyLevel.SAFE.requires_action is False
        assert SafetyLevel.WARNING.requires_action is False
        assert SafetyLevel.DANGEROUS.requires_action is True
        assert SafetyLevel.BLOCKED.requires_action is True
        assert SafetyLevel.CRITICAL.requires_action is True

    def test_is_emergency_property(self):
        """Test is_emergency property."""
        assert SafetyLevel.SAFE.is_emergency is False
        assert SafetyLevel.WARNING.is_emergency is False
        assert SafetyLevel.DANGEROUS.is_emergency is False
        assert SafetyLevel.BLOCKED.is_emergency is False
        assert SafetyLevel.CRITICAL.is_emergency is True

    def test_max_function(self):
        """Test that max() works with SafetyLevel ordering."""
        levels = [SafetyLevel.SAFE, SafetyLevel.WARNING, SafetyLevel.DANGEROUS]
        assert max(levels) == SafetyLevel.DANGEROUS

    def test_min_function(self):
        """Test that min() works with SafetyLevel ordering."""
        levels = [SafetyLevel.SAFE, SafetyLevel.WARNING, SafetyLevel.DANGEROUS]
        assert min(levels) == SafetyLevel.SAFE

    def test_sorted_function(self):
        """Test that sorted() works with SafetyLevel ordering."""
        levels = [SafetyLevel.DANGEROUS, SafetyLevel.SAFE, SafetyLevel.WARNING]
        sorted_levels = sorted(levels)
        assert sorted_levels == [
            SafetyLevel.SAFE,
            SafetyLevel.WARNING,
            SafetyLevel.DANGEROUS,
        ]


# =============================================================================
# ViolationType Tests
# =============================================================================

class TestViolationType:
    """Tests for ViolationType enum."""

    def test_all_base_values_exist(self):
        """Test that all base violation types exist."""
        assert ViolationType.NONE.value == "none"
        assert ViolationType.JOINT_POSITION.value == "joint_position"
        assert ViolationType.JOINT_VELOCITY.value == "joint_velocity"
        assert ViolationType.FORCE.value == "force"
        assert ViolationType.TORQUE.value == "torque"
        assert ViolationType.WORKSPACE.value == "workspace"
        assert ViolationType.COLLISION.value == "collision"
        assert ViolationType.INVALID_VALUE.value == "invalid_value"

    def test_thsp_gate_values(self):
        """Test THSP gate violation types."""
        assert ViolationType.TRUTH_VIOLATION.value == "truth"
        assert ViolationType.HARM_VIOLATION.value == "harm"
        assert ViolationType.SCOPE_VIOLATION.value == "scope"
        assert ViolationType.PURPOSE_VIOLATION.value == "purpose"

    def test_domain_specific_values(self):
        """Test domain-specific violation types."""
        # Humanoid
        assert ViolationType.BALANCE.value == "balance"
        assert ViolationType.CONTACT_FORCE.value == "contact_force"
        assert ViolationType.FALL_RISK.value == "fall_risk"

        # Mobile
        assert ViolationType.VELOCITY_LIMIT.value == "velocity_limit"
        assert ViolationType.ALTITUDE_LIMIT.value == "altitude_limit"

        # Simulation
        assert ViolationType.ACTION_SPACE.value == "action_space"
        assert ViolationType.EPISODE_TERMINATION.value == "episode_termination"

    def test_gate_property_thsp_violations(self):
        """Test gate property for THSP violation types."""
        assert ViolationType.TRUTH_VIOLATION.gate == "truth"
        assert ViolationType.HARM_VIOLATION.gate == "harm"
        assert ViolationType.SCOPE_VIOLATION.gate == "scope"
        assert ViolationType.PURPOSE_VIOLATION.gate == "purpose"

    def test_gate_property_physical_violations(self):
        """Test gate property for physical violations."""
        assert ViolationType.JOINT_POSITION.gate == "scope"
        assert ViolationType.JOINT_VELOCITY.gate == "scope"
        assert ViolationType.FORCE.gate == "harm"
        assert ViolationType.TORQUE.gate == "harm"

    def test_gate_property_input_violations(self):
        """Test gate property for input validation violations."""
        assert ViolationType.INVALID_VALUE.gate == "truth"
        assert ViolationType.INVALID_TYPE.gate == "truth"
        assert ViolationType.MISSING_REQUIRED.gate == "truth"

    def test_gate_property_none(self):
        """Test gate property returns None for NONE type."""
        assert ViolationType.NONE.gate is None

    def test_is_physical_property(self):
        """Test is_physical property."""
        assert ViolationType.JOINT_POSITION.is_physical is True
        assert ViolationType.JOINT_VELOCITY.is_physical is True
        assert ViolationType.FORCE.is_physical is True
        assert ViolationType.TORQUE.is_physical is True
        assert ViolationType.VELOCITY_LIMIT.is_physical is True

        assert ViolationType.WORKSPACE.is_physical is False
        assert ViolationType.COLLISION.is_physical is False
        assert ViolationType.INVALID_VALUE.is_physical is False

    def test_is_spatial_property(self):
        """Test is_spatial property."""
        assert ViolationType.WORKSPACE.is_spatial is True
        assert ViolationType.COLLISION.is_spatial is True
        assert ViolationType.ZONE.is_spatial is True
        assert ViolationType.ALTITUDE_LIMIT.is_spatial is True

        assert ViolationType.JOINT_POSITION.is_spatial is False
        assert ViolationType.FORCE.is_spatial is False


# =============================================================================
# SafetyResult Tests
# =============================================================================

class TestSafetyResult:
    """Tests for SafetyResult dataclass."""

    def test_basic_creation(self):
        """Test basic SafetyResult creation."""
        result = SafetyResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
        )
        assert result.is_safe is True
        assert result.level == SafetyLevel.SAFE
        assert result.violations == []
        assert result.violation_types == []
        assert result.confidence == 1.0

    def test_default_gates(self):
        """Test default gates are all True."""
        result = SafetyResult(is_safe=True, level=SafetyLevel.SAFE)
        assert result.gates == {
            "truth": True,
            "harm": True,
            "scope": True,
            "purpose": True,
        }

    def test_custom_gates(self):
        """Test custom gates values."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.DANGEROUS,
            gates={"truth": True, "harm": False, "scope": True, "purpose": True},
        )
        assert result.gates["harm"] is False
        assert result.gates["truth"] is True

    def test_violations_list(self):
        """Test violations list."""
        violations = ["Joint velocity exceeded", "Workspace boundary reached"]
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            violations=violations,
        )
        assert len(result.violations) == 2
        assert "Joint velocity exceeded" in result.violations

    def test_violation_types_list(self):
        """Test violation_types list."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.DANGEROUS,
            violation_types=[ViolationType.JOINT_VELOCITY, ViolationType.WORKSPACE],
        )
        assert len(result.violation_types) == 2
        assert ViolationType.JOINT_VELOCITY in result.violation_types

    def test_string_violation_types_normalized(self):
        """Test that string violation types are converted to enum."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            violation_types=["joint_velocity", "workspace"],
        )
        assert result.violation_types[0] == ViolationType.JOINT_VELOCITY
        assert result.violation_types[1] == ViolationType.WORKSPACE

    def test_string_level_normalized(self):
        """Test that string level is converted to enum."""
        result = SafetyResult(
            is_safe=True,
            level="safe",
        )
        assert result.level == SafetyLevel.SAFE

    def test_confidence_validation_valid(self):
        """Test that valid confidence values are accepted."""
        result = SafetyResult(is_safe=True, level=SafetyLevel.SAFE, confidence=0.85)
        assert result.confidence == 0.85

    def test_confidence_validation_invalid(self):
        """Test that invalid confidence values raise error."""
        with pytest.raises(ValueError, match="confidence"):
            SafetyResult(is_safe=True, level=SafetyLevel.SAFE, confidence=1.5)

        with pytest.raises(ValueError, match="confidence"):
            SafetyResult(is_safe=True, level=SafetyLevel.SAFE, confidence=-0.1)

    def test_modified_action(self):
        """Test modified_action field."""
        modified = {"velocity": 0.5}
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            modified_action=modified,
        )
        assert result.modified_action == {"velocity": 0.5}

    def test_metadata(self):
        """Test metadata field."""
        result = SafetyResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            metadata={"timestamp": 123456, "validator": "test"},
        )
        assert result.metadata["timestamp"] == 123456
        assert result.metadata["validator"] == "test"

    def test_failed_gates_property(self):
        """Test failed_gates property."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.DANGEROUS,
            gates={"truth": True, "harm": False, "scope": False, "purpose": True},
        )
        assert "harm" in result.failed_gates
        assert "scope" in result.failed_gates
        assert "truth" not in result.failed_gates

    def test_passed_gates_property(self):
        """Test passed_gates property."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            gates={"truth": True, "harm": False, "scope": True, "purpose": True},
        )
        assert "truth" in result.passed_gates
        assert "scope" in result.passed_gates
        assert "harm" not in result.passed_gates

    def test_has_violations_property(self):
        """Test has_violations property."""
        result_with = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            violations=["Something wrong"],
        )
        assert result_with.has_violations is True

        result_without = SafetyResult(is_safe=True, level=SafetyLevel.SAFE)
        assert result_without.has_violations is False

    def test_primary_violation_property(self):
        """Test primary_violation property."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            violations=["First error", "Second error"],
        )
        assert result.primary_violation == "First error"

        empty = SafetyResult(is_safe=True, level=SafetyLevel.SAFE)
        assert empty.primary_violation is None

    def test_primary_violation_type_property(self):
        """Test primary_violation_type property."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            violation_types=[ViolationType.FORCE, ViolationType.TORQUE],
        )
        assert result.primary_violation_type == ViolationType.FORCE

        empty = SafetyResult(is_safe=True, level=SafetyLevel.SAFE)
        assert empty.primary_violation_type is None

    def test_to_dict(self):
        """Test to_dict serialization."""
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.DANGEROUS,
            gates={"truth": True, "harm": False, "scope": True, "purpose": True},
            violations=["Force exceeded"],
            violation_types=[ViolationType.FORCE],
            reasoning="Force 100N exceeds limit 50N",
            confidence=0.95,
            metadata={"source": "test"},
        )
        d = result.to_dict()

        assert d["is_safe"] is False
        assert d["level"] == "dangerous"
        assert d["gates"]["harm"] is False
        assert "Force exceeded" in d["violations"]
        assert "force" in d["violation_types"]
        assert d["reasoning"] == "Force 100N exceeds limit 50N"
        assert d["confidence"] == 0.95
        assert d["metadata"]["source"] == "test"

    def test_from_dict(self):
        """Test from_dict deserialization."""
        d = {
            "is_safe": False,
            "level": "warning",
            "gates": {"truth": True, "harm": True, "scope": False, "purpose": True},
            "violations": ["Out of bounds"],
            "violation_types": ["workspace"],
            "reasoning": "Position outside workspace",
            "confidence": 0.9,
            "metadata": {"id": 42},
        }
        result = SafetyResult.from_dict(d)

        assert result.is_safe is False
        assert result.level == SafetyLevel.WARNING
        assert result.gates["scope"] is False
        assert "Out of bounds" in result.violations
        assert ViolationType.WORKSPACE in result.violation_types
        assert result.confidence == 0.9
        assert result.metadata["id"] == 42

    def test_safe_factory(self):
        """Test safe() factory method."""
        result = SafetyResult.safe()
        assert result.is_safe is True
        assert result.level == SafetyLevel.SAFE
        assert result.violations == []

        result_with_reason = SafetyResult.safe("All checks passed")
        assert result_with_reason.reasoning == "All checks passed"

    def test_unsafe_factory(self):
        """Test unsafe() factory method."""
        result = SafetyResult.unsafe(
            level=SafetyLevel.DANGEROUS,
            violations=["Velocity too high"],
            violation_types=[ViolationType.VELOCITY_LIMIT],
            failed_gates=["scope"],
            reasoning="Exceeded velocity limit",
        )
        assert result.is_safe is False
        assert result.level == SafetyLevel.DANGEROUS
        assert "Velocity too high" in result.violations
        assert result.gates["scope"] is False
        assert result.gates["truth"] is True  # Not in failed_gates

    def test_unsafe_factory_with_modified_action(self):
        """Test unsafe() factory with modified_action."""
        modified = {"velocity": 0.5}
        result = SafetyResult.unsafe(
            level=SafetyLevel.WARNING,
            violations=["Clamped velocity"],
            modified_action=modified,
        )
        assert result.modified_action == modified

    def test_merge_with_both_safe(self):
        """Test merge_with when both results are safe."""
        r1 = SafetyResult.safe("Check 1 passed")
        r2 = SafetyResult.safe("Check 2 passed")
        merged = r1.merge_with(r2)

        assert merged.is_safe is True
        assert merged.level == SafetyLevel.SAFE

    def test_merge_with_one_unsafe(self):
        """Test merge_with when one result is unsafe."""
        r1 = SafetyResult.safe()
        r2 = SafetyResult.unsafe(
            level=SafetyLevel.WARNING,
            violations=["Minor issue"],
        )
        merged = r1.merge_with(r2)

        assert merged.is_safe is False
        assert merged.level == SafetyLevel.WARNING
        assert "Minor issue" in merged.violations

    def test_merge_with_both_unsafe(self):
        """Test merge_with when both results are unsafe."""
        r1 = SafetyResult.unsafe(
            level=SafetyLevel.WARNING,
            violations=["Issue 1"],
            failed_gates=["scope"],
        )
        r2 = SafetyResult.unsafe(
            level=SafetyLevel.DANGEROUS,
            violations=["Issue 2"],
            failed_gates=["harm"],
        )
        merged = r1.merge_with(r2)

        assert merged.is_safe is False
        assert merged.level == SafetyLevel.DANGEROUS  # Takes worse
        assert "Issue 1" in merged.violations
        assert "Issue 2" in merged.violations
        assert merged.gates["scope"] is False
        assert merged.gates["harm"] is False

    def test_merge_with_confidence(self):
        """Test merge_with takes lower confidence."""
        r1 = SafetyResult(is_safe=True, level=SafetyLevel.SAFE, confidence=0.9)
        r2 = SafetyResult(is_safe=True, level=SafetyLevel.SAFE, confidence=0.7)
        merged = r1.merge_with(r2)

        assert merged.confidence == 0.7

    def test_merge_with_metadata(self):
        """Test merge_with combines metadata."""
        r1 = SafetyResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            metadata={"a": 1},
        )
        r2 = SafetyResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            metadata={"b": 2},
        )
        merged = r1.merge_with(r2)

        assert merged.metadata["a"] == 1
        assert merged.metadata["b"] == 2


# =============================================================================
# SafetyValidator Tests
# =============================================================================

class MockValidator(SafetyValidator):
    """Mock validator for testing."""

    def __init__(self, always_safe: bool = True, threshold: float = 1.0):
        self.always_safe = always_safe
        self.threshold = threshold
        self._stats = self._init_stats()

    def validate(
        self,
        action: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> SafetyResult:
        """Mock validation that checks action value against threshold."""
        if self.always_safe:
            result = SafetyResult.safe()
            self._update_stats(result)
            return result

        # Simple validation: action should be a number less than threshold
        if isinstance(action, (int, float)):
            if action > self.threshold:
                result = SafetyResult.unsafe(
                    level=SafetyLevel.DANGEROUS,
                    violations=[f"Value {action} exceeds threshold {self.threshold}"],
                    violation_types=[ViolationType.INVALID_VALUE],
                    failed_gates=["scope"],
                )
                self._update_stats(result)
                return result

        result = SafetyResult.safe()
        self._update_stats(result)
        return result


class TestSafetyValidator:
    """Tests for SafetyValidator abstract base class."""

    def test_cannot_instantiate_directly(self):
        """Test that SafetyValidator cannot be instantiated directly."""
        with pytest.raises(TypeError):
            SafetyValidator()

    def test_mock_validator_safe(self):
        """Test mock validator returns safe result."""
        validator = MockValidator(always_safe=True)
        result = validator.validate({"test": "action"})

        assert result.is_safe is True
        assert result.level == SafetyLevel.SAFE

    def test_mock_validator_unsafe(self):
        """Test mock validator returns unsafe result."""
        validator = MockValidator(always_safe=False, threshold=1.0)
        result = validator.validate(2.0)

        assert result.is_safe is False
        assert result.level == SafetyLevel.DANGEROUS

    def test_get_stats(self):
        """Test get_stats returns statistics."""
        validator = MockValidator()
        validator.validate(1)
        validator.validate(2)
        stats = validator.get_stats()

        assert stats["total_validated"] == 2

    def test_reset_stats(self):
        """Test reset_stats clears statistics."""
        validator = MockValidator()
        validator.validate(1)
        validator.validate(2)
        validator.reset_stats()
        stats = validator.get_stats()

        assert stats["total_validated"] == 0

    def test_stats_update_on_violation(self):
        """Test statistics are updated on violations."""
        validator = MockValidator(always_safe=False, threshold=1.0)
        validator.validate(0.5)  # Safe
        validator.validate(2.0)  # Unsafe
        stats = validator.get_stats()

        assert stats["total_validated"] == 2
        assert stats["total_blocked"] == 1

    def test_validate_batch_default_implementation(self):
        """Test default validate_batch implementation."""
        validator = MockValidator(always_safe=False, threshold=1.0)
        actions = [0.5, 1.5, 0.8, 2.0]
        results = validator.validate_batch(actions)

        assert len(results) == 4
        assert results[0].is_safe is True
        assert results[1].is_safe is False
        assert results[2].is_safe is True
        assert results[3].is_safe is False

    def test_validate_batch_with_contexts(self):
        """Test validate_batch with contexts."""
        validator = MockValidator()
        actions = [1, 2, 3]
        contexts = [{"id": 1}, {"id": 2}, {"id": 3}]
        results = validator.validate_batch(actions, contexts)

        assert len(results) == 3
        for result in results:
            assert result.is_safe is True

    def test_init_stats_structure(self):
        """Test _init_stats creates correct structure."""
        validator = MockValidator()
        stats = validator._init_stats()

        assert "total_validated" in stats
        assert "total_blocked" in stats
        assert "gate_failures" in stats
        assert "truth" in stats["gate_failures"]
        assert "harm" in stats["gate_failures"]
        assert "scope" in stats["gate_failures"]
        assert "purpose" in stats["gate_failures"]


# =============================================================================
# Module Tests
# =============================================================================

class TestModule:
    """Tests for module-level attributes."""

    def test_version_exists(self):
        """Test __version__ is defined."""
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_version_format(self):
        """Test __version__ follows semver format."""
        parts = __version__.split(".")
        assert len(parts) >= 2
        for part in parts[:2]:
            assert part.isdigit()
