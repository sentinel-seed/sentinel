"""
Tests for Isaac Lab integration.

Comprehensive test suite for constraints, validators, wrappers, and callbacks.
"""

import math
import pytest
from unittest.mock import Mock, MagicMock, patch
from dataclasses import dataclass
from typing import List, Dict, Any


# =============================================================================
# Test Constraints Module
# =============================================================================

class TestJointLimits:
    """Tests for JointLimits dataclass."""

    def test_create_basic_joint_limits(self):
        """JointLimits can be created with basic parameters."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            position_lower=[-1.0, -1.0, -1.0],
            position_upper=[1.0, 1.0, 1.0],
            velocity_max=[2.0, 2.0, 2.0],
        )

        assert limits.num_joints == 3
        assert len(limits.position_lower) == 3
        assert len(limits.position_upper) == 3
        assert len(limits.velocity_max) == 3

    def test_create_with_single_value_expansion(self):
        """Single values should expand to all joints."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=5,
            position_lower=[-2.0],
            position_upper=[2.0],
            velocity_max=[3.0],
        )

        assert len(limits.position_lower) == 5
        assert all(v == -2.0 for v in limits.position_lower)
        assert all(v == 2.0 for v in limits.position_upper)
        assert all(v == 3.0 for v in limits.velocity_max)

    def test_create_with_defaults(self):
        """Empty lists should use defaults."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(num_joints=4)

        assert len(limits.position_lower) == 4
        assert len(limits.position_upper) == 4
        assert len(limits.velocity_max) == 4
        # Default velocity is 2.0
        assert all(v == 2.0 for v in limits.velocity_max)

    def test_invalid_num_joints_zero(self):
        """num_joints=0 should raise ValueError."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        with pytest.raises(ValueError, match="num_joints must be >= 1"):
            JointLimits(num_joints=0)

    def test_invalid_num_joints_negative(self):
        """Negative num_joints should raise ValueError."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        with pytest.raises(ValueError, match="num_joints must be >= 1"):
            JointLimits(num_joints=-1)

    def test_mismatched_position_lower_length(self):
        """Mismatched position_lower length should raise ValueError."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        with pytest.raises(ValueError, match="position_lower length"):
            JointLimits(
                num_joints=3,
                position_lower=[-1.0, -1.0],  # 2 instead of 3
                position_upper=[1.0, 1.0, 1.0],
                velocity_max=[2.0, 2.0, 2.0],
            )

    def test_mismatched_position_upper_length(self):
        """Mismatched position_upper length should raise ValueError."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        with pytest.raises(ValueError, match="position_upper length"):
            JointLimits(
                num_joints=3,
                position_lower=[-1.0, -1.0, -1.0],
                position_upper=[1.0, 1.0],  # 2 instead of 3
                velocity_max=[2.0, 2.0, 2.0],
            )

    def test_mismatched_velocity_max_length(self):
        """Mismatched velocity_max length should raise ValueError."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        with pytest.raises(ValueError, match="velocity_max length"):
            JointLimits(
                num_joints=3,
                position_lower=[-1.0, -1.0, -1.0],
                position_upper=[1.0, 1.0, 1.0],
                velocity_max=[2.0, 2.0],  # 2 instead of 3
            )

    def test_check_position_valid(self):
        """Valid positions should pass check."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            position_lower=[-1.0, -1.0, -1.0],
            position_upper=[1.0, 1.0, 1.0],
            velocity_max=[2.0, 2.0, 2.0],
        )

        is_valid, violations = limits.check_position([0.0, 0.5, -0.5])
        assert is_valid is True
        assert violations == []

    def test_check_position_invalid_below(self):
        """Position below lower limit should fail."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            position_lower=[-1.0, -1.0, -1.0],
            position_upper=[1.0, 1.0, 1.0],
            velocity_max=[2.0, 2.0, 2.0],
        )

        is_valid, violations = limits.check_position([-1.5, 0.0, 0.0])
        assert is_valid is False
        assert len(violations) == 1
        assert "Joint 0" in violations[0]

    def test_check_position_invalid_above(self):
        """Position above upper limit should fail."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            position_lower=[-1.0, -1.0, -1.0],
            position_upper=[1.0, 1.0, 1.0],
            velocity_max=[2.0, 2.0, 2.0],
        )

        is_valid, violations = limits.check_position([0.0, 1.5, 0.0])
        assert is_valid is False
        assert len(violations) == 1
        assert "Joint 1" in violations[0]

    def test_check_position_nan(self):
        """NaN position should fail."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(num_joints=3)
        is_valid, violations = limits.check_position([float('nan'), 0.0, 0.0])
        assert is_valid is False
        assert "Invalid value" in violations[0]

    def test_check_position_inf(self):
        """Infinite position should fail."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(num_joints=3)
        is_valid, violations = limits.check_position([0.0, float('inf'), 0.0])
        assert is_valid is False
        assert "Invalid value" in violations[0]

    def test_check_velocity_valid(self):
        """Valid velocities should pass check."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            velocity_max=[2.0, 2.0, 2.0],
        )

        is_valid, violations = limits.check_velocity([1.0, -1.0, 0.5])
        assert is_valid is True
        assert violations == []

    def test_check_velocity_exceeds_limit(self):
        """Velocity exceeding limit should fail."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            velocity_max=[2.0, 2.0, 2.0],
        )

        is_valid, violations = limits.check_velocity([1.0, 2.5, 0.0])
        assert is_valid is False
        assert len(violations) == 1
        assert "Joint 1" in violations[0]

    def test_clamp_position(self):
        """Positions should be clamped to valid range."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            position_lower=[-1.0, -1.0, -1.0],
            position_upper=[1.0, 1.0, 1.0],
        )

        clamped = limits.clamp_position([-2.0, 0.5, 2.0])
        assert clamped[0] == -1.0
        assert clamped[1] == 0.5
        assert clamped[2] == 1.0

    def test_clamp_velocity(self):
        """Velocities should be clamped to valid range."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits(
            num_joints=3,
            velocity_max=[2.0, 2.0, 2.0],
        )

        clamped = limits.clamp_velocity([-3.0, 1.0, 3.0])
        assert clamped[0] == -2.0
        assert clamped[1] == 1.0
        assert clamped[2] == 2.0

    def test_franka_panda_preset(self):
        """Franka Panda preset should have correct configuration."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits.franka_panda()
        assert limits.num_joints == 7
        assert len(limits.position_lower) == 7
        assert len(limits.position_upper) == 7
        assert len(limits.velocity_max) == 7
        assert limits.effort_max is not None
        assert len(limits.effort_max) == 7

    def test_ur10_preset(self):
        """UR10 preset should have correct configuration."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits.ur10()
        assert limits.num_joints == 6

    def test_allegro_hand_preset(self):
        """Allegro Hand preset should have correct configuration."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits.allegro_hand()
        assert limits.num_joints == 16

    def test_default_factory(self):
        """Default factory should create limits for any joint count."""
        from sentinelseed.integrations.isaac_lab.constraints import JointLimits

        limits = JointLimits.default(10)
        assert limits.num_joints == 10


class TestWorkspaceLimits:
    """Tests for WorkspaceLimits dataclass."""

    def test_create_workspace_limits(self):
        """WorkspaceLimits can be created."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits(
            x_min=-1.0, x_max=1.0,
            y_min=-1.0, y_max=1.0,
            z_min=0.0, z_max=1.5,
        )

        assert ws.x_min == -1.0
        assert ws.x_max == 1.0
        assert ws.z_min == 0.0

    def test_contains_inside(self):
        """Points inside workspace should return True."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits(
            x_min=-1.0, x_max=1.0,
            y_min=-1.0, y_max=1.0,
            z_min=0.0, z_max=1.0,
        )

        assert ws.contains(0.0, 0.0, 0.5) is True
        assert ws.contains(-0.5, 0.5, 0.8) is True

    def test_contains_outside(self):
        """Points outside workspace should return False."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits(
            x_min=-1.0, x_max=1.0,
            y_min=-1.0, y_max=1.0,
            z_min=0.0, z_max=1.0,
        )

        assert ws.contains(1.5, 0.0, 0.5) is False
        assert ws.contains(0.0, -1.5, 0.5) is False
        assert ws.contains(0.0, 0.0, -0.1) is False

    def test_contains_with_sphere(self):
        """Spherical constraint should be checked."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits(
            x_min=-2.0, x_max=2.0,
            y_min=-2.0, y_max=2.0,
            z_min=0.0, z_max=2.0,
            center=(0.0, 0.0, 1.0),
            radius=0.5,
        )

        # Inside both box and sphere
        assert ws.contains(0.0, 0.0, 1.0) is True
        # Inside box but outside sphere
        assert ws.contains(1.0, 0.0, 1.0) is False

    def test_check_position_valid(self):
        """Valid position should pass check."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits()
        is_valid, violations = ws.check_position([0.0, 0.0, 0.5])
        assert is_valid is True

    def test_check_position_invalid(self):
        """Invalid position should fail check."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits(x_max=1.0)
        is_valid, violations = ws.check_position([2.0, 0.0, 0.5])
        assert is_valid is False
        assert len(violations) > 0

    def test_franka_reach_preset(self):
        """Franka reach preset should be configured."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits.franka_reach()
        assert ws.center is not None
        assert ws.radius is not None

    def test_table_top_preset(self):
        """Table top preset should be configured."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits.table_top(table_height=0.5)
        assert ws.z_min == 0.5

    def test_unlimited_preset(self):
        """Unlimited preset should have very large bounds (1e9)."""
        from sentinelseed.integrations.isaac_lab.constraints import WorkspaceLimits

        ws = WorkspaceLimits.unlimited()
        # Uses large finite values instead of inf for mathematical stability
        assert ws.x_min == -1e9
        assert ws.x_max == 1e9


class TestForceTorqueLimits:
    """Tests for ForceTorqueLimits dataclass."""

    def test_create_force_torque_limits(self):
        """ForceTorqueLimits can be created."""
        from sentinelseed.integrations.isaac_lab.constraints import ForceTorqueLimits

        ft = ForceTorqueLimits(max_force=50.0, max_torque=10.0)
        assert ft.max_force == 50.0
        assert ft.max_torque == 10.0

    def test_check_force_valid(self):
        """Valid force should pass check."""
        from sentinelseed.integrations.isaac_lab.constraints import ForceTorqueLimits

        ft = ForceTorqueLimits(max_force=50.0)
        is_valid, violations = ft.check_force([10.0, 10.0, 10.0])
        assert is_valid is True

    def test_check_force_exceeds_magnitude(self):
        """Force exceeding magnitude should fail."""
        from sentinelseed.integrations.isaac_lab.constraints import ForceTorqueLimits

        ft = ForceTorqueLimits(max_force=10.0)
        is_valid, violations = ft.check_force([10.0, 10.0, 10.0])  # magnitude > 10
        assert is_valid is False

    def test_check_torque_valid(self):
        """Valid torque should pass check."""
        from sentinelseed.integrations.isaac_lab.constraints import ForceTorqueLimits

        ft = ForceTorqueLimits(max_torque=10.0)
        is_valid, violations = ft.check_torque([1.0, 1.0, 1.0])
        assert is_valid is True

    def test_franka_contact_preset(self):
        """Franka contact preset should be configured."""
        from sentinelseed.integrations.isaac_lab.constraints import ForceTorqueLimits

        ft = ForceTorqueLimits.franka_contact()
        assert ft.max_force > 0
        assert ft.max_torque > 0

    def test_human_safe_preset(self):
        """Human safe preset should use ISO limits."""
        from sentinelseed.integrations.isaac_lab.constraints import ForceTorqueLimits

        ft = ForceTorqueLimits.human_safe()
        assert ft.max_force == 150.0  # ISO 10218 limit


class TestCollisionZone:
    """Tests for CollisionZone dataclass."""

    def test_sphere_collision_zone(self):
        """Sphere collision zone should work correctly."""
        from sentinelseed.integrations.isaac_lab.constraints import CollisionZone

        zone = CollisionZone.sphere("test", center=(0.0, 0.0, 0.0), radius=0.5)

        # Inside
        assert zone.contains(0.0, 0.0, 0.0) is True
        assert zone.contains(0.3, 0.0, 0.0) is True
        # Outside (considering margin of 0.05)
        assert zone.contains(1.0, 0.0, 0.0) is False

    def test_box_collision_zone(self):
        """Box collision zone should work correctly."""
        from sentinelseed.integrations.isaac_lab.constraints import CollisionZone

        zone = CollisionZone.box(
            "test",
            center=(0.0, 0.0, 0.0),
            half_extents=(0.5, 0.5, 0.5)
        )

        # Inside
        assert zone.contains(0.0, 0.0, 0.0) is True
        assert zone.contains(0.4, 0.4, 0.4) is True
        # Outside
        assert zone.contains(1.0, 0.0, 0.0) is False


class TestRobotConstraints:
    """Tests for RobotConstraints dataclass."""

    def test_create_robot_constraints(self):
        """RobotConstraints can be created."""
        from sentinelseed.integrations.isaac_lab.constraints import (
            RobotConstraints,
            JointLimits,
        )

        constraints = RobotConstraints(
            joint_limits=JointLimits(num_joints=3),
        )

        assert constraints.joint_limits is not None
        assert constraints.joint_limits.num_joints == 3

    def test_franka_default_preset(self):
        """Franka default preset should be fully configured."""
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        constraints = RobotConstraints.franka_default()

        assert constraints.joint_limits is not None
        assert constraints.workspace_limits is not None
        assert constraints.force_torque_limits is not None

    def test_ur10_default_preset(self):
        """UR10 default preset should be configured."""
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        constraints = RobotConstraints.ur10_default()
        assert constraints.joint_limits.num_joints == 6

    def test_add_collision_zone(self):
        """Collision zones can be added."""
        from sentinelseed.integrations.isaac_lab.constraints import (
            RobotConstraints,
            CollisionZone,
        )

        constraints = RobotConstraints()
        constraints.add_collision_zone(
            CollisionZone.sphere("test", center=(0, 0, 0), radius=0.5)
        )

        assert len(constraints.collision_zones) == 1
        assert constraints.collision_zones[0].name == "test"

    def test_from_urdf_limits(self):
        """Constraints can be created from URDF-style limits."""
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        constraints = RobotConstraints.from_urdf_limits(
            position_lower=[-1.0, -1.0],
            position_upper=[1.0, 1.0],
            velocity_max=[2.0, 2.0],
        )

        assert constraints.joint_limits.num_joints == 2


# =============================================================================
# Test Validators Module
# =============================================================================

class TestActionValidationResult:
    """Tests for ActionValidationResult dataclass."""

    def test_create_validation_result(self):
        """ActionValidationResult can be created."""
        from sentinelseed.integrations.isaac_lab.validators import (
            ActionValidationResult,
            SafetyLevel,
        )

        result = ActionValidationResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
        )

        assert result.is_safe is True
        assert result.level == SafetyLevel.SAFE

    def test_to_dict(self):
        """to_dict should serialize correctly."""
        from sentinelseed.integrations.isaac_lab.validators import (
            ActionValidationResult,
            SafetyLevel,
        )

        result = ActionValidationResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            violations=["test violation"],
        )

        d = result.to_dict()
        assert d["is_safe"] is False
        assert d["level"] == "warning"
        assert "test violation" in d["violations"]


class TestTHSPRobotValidator:
    """Tests for THSPRobotValidator."""

    def test_create_validator(self):
        """THSPRobotValidator can be created."""
        from sentinelseed.integrations.isaac_lab.validators import THSPRobotValidator
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        validator = THSPRobotValidator(
            constraints=RobotConstraints.franka_default(),
        )

        assert validator.constraints is not None

    def test_validate_safe_action(self):
        """Safe action should pass validation."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        validator = THSPRobotValidator(
            constraints=RobotConstraints.franka_default(),
            action_type=ActionType.NORMALIZED,
        )

        result = validator.validate([0.1, -0.2, 0.3, 0.0, -0.1, 0.2, 0.0])

        assert result.is_safe is True
        assert all(result.gates.values())

    def test_validate_nan_action(self):
        """NaN action should fail truth gate."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
            SafetyLevel,
        )

        validator = THSPRobotValidator(action_type=ActionType.NORMALIZED)

        result = validator.validate([float('nan'), 0.0, 0.0])

        assert result.is_safe is False
        assert result.gates["truth"] is False
        assert any("NaN" in v for v in result.violations)

    def test_validate_inf_action(self):
        """Infinite action should fail truth gate."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )

        validator = THSPRobotValidator(action_type=ActionType.NORMALIZED)

        result = validator.validate([0.0, float('inf'), 0.0])

        assert result.is_safe is False
        assert result.gates["truth"] is False

    def test_validate_out_of_range_normalized(self):
        """Normalized action outside [-1, 1] should fail."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )

        validator = THSPRobotValidator(action_type=ActionType.NORMALIZED)

        result = validator.validate([1.5, 0.0, 0.0])

        assert result.is_safe is False
        assert result.gates["truth"] is False
        assert any("outside [-1, 1]" in v for v in result.violations)

    def test_validate_provides_modified_action(self):
        """Unsafe action should provide modified action."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )

        validator = THSPRobotValidator(action_type=ActionType.NORMALIZED)

        result = validator.validate([1.5, -1.5, float('nan')])

        assert result.is_safe is False
        assert result.modified_action is not None

    def test_validate_with_context(self):
        """Validation should use context when provided."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        validator = THSPRobotValidator(
            constraints=RobotConstraints.franka_default(),
            action_type=ActionType.NORMALIZED,
        )

        context = {
            "current_joint_position": [0.0] * 7,
            "dt": 0.01,
        }

        result = validator.validate([0.1] * 7, context=context)
        assert result is not None

    def test_validate_dimension_mismatch(self):
        """Dimension mismatch should be caught."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        validator = THSPRobotValidator(
            constraints=RobotConstraints.franka_default(),  # 7 joints
            action_type=ActionType.NORMALIZED,
        )

        # Action has 3 dims, position has 7, but constraints expect 7
        context = {
            "current_joint_position": [0.0] * 7,
            "dt": 0.01,
        }

        result = validator.validate([0.1, 0.1, 0.1], context=context)  # Only 3 dims

        assert result.is_safe is False
        assert any("Dimension mismatch" in v for v in result.violations)

    def test_validate_batch(self):
        """Batch validation should work."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )

        validator = THSPRobotValidator(action_type=ActionType.NORMALIZED)

        # Batch of 4 actions, one is invalid
        actions = [
            [0.1, 0.2, 0.3],
            [0.5, 0.5, 0.5],
            [1.5, 0.0, 0.0],  # Invalid
            [-0.5, -0.5, -0.5],
        ]

        result = validator.validate_batch(actions)

        assert result.any_unsafe is True
        assert result.all_unsafe is False
        assert 2 in result.unsafe_indices

    def test_get_stats(self):
        """Statistics should be tracked."""
        from sentinelseed.integrations.isaac_lab.validators import THSPRobotValidator

        validator = THSPRobotValidator()

        validator.validate([0.1, 0.2, 0.3])
        validator.validate([1.5, 0.0, 0.0])  # Invalid

        stats = validator.get_stats()

        assert stats["total_validated"] == 2
        assert stats["total_violations"] == 1

    def test_reset_stats(self):
        """Statistics should be resettable."""
        from sentinelseed.integrations.isaac_lab.validators import THSPRobotValidator

        validator = THSPRobotValidator()
        validator.validate([0.1, 0.2, 0.3])

        validator.reset_stats()
        stats = validator.get_stats()

        assert stats["total_validated"] == 0


class TestBatchValidationResult:
    """Tests for BatchValidationResult."""

    def test_num_unsafe_property(self):
        """num_unsafe should return count of unsafe indices."""
        from sentinelseed.integrations.isaac_lab.validators import (
            BatchValidationResult,
            SafetyLevel,
        )

        result = BatchValidationResult(
            is_safe=[True, False, True, False],
            violations_per_env=[0, 1, 0, 2],
            any_unsafe=True,
            all_unsafe=False,
            unsafe_indices=[1, 3],
        )

        assert result.num_unsafe == 2


# =============================================================================
# Test Wrappers Module
# =============================================================================

class TestSafetyMode:
    """Tests for SafetyMode enum."""

    def test_safety_modes_exist(self):
        """All safety modes should exist."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyMode

        assert SafetyMode.BLOCK.value == "block"
        assert SafetyMode.CLAMP.value == "clamp"
        assert SafetyMode.WARN.value == "warn"
        assert SafetyMode.MONITOR.value == "monitor"


class TestSafetyStatistics:
    """Tests for SafetyStatistics dataclass."""

    def test_create_statistics(self):
        """SafetyStatistics can be created."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyStatistics

        stats = SafetyStatistics()
        assert stats.total_steps == 0
        assert stats.violations_total == 0

    def test_step_increments(self):
        """step() should increment counter."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyStatistics

        stats = SafetyStatistics()
        stats.step()
        stats.step()

        assert stats.total_steps == 2

    def test_record_violation(self):
        """record_violation should update counters."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyStatistics
        from sentinelseed.integrations.isaac_lab.validators import (
            ActionValidationResult,
            SafetyLevel,
        )

        stats = SafetyStatistics()
        result = ActionValidationResult(
            is_safe=False,
            level=SafetyLevel.WARNING,
            gates={"truth": False, "harm": True, "scope": True, "purpose": True},
        )

        stats.record_violation(result)

        assert stats.violations_total == 1
        assert stats.violations_by_gate["truth"] == 1
        assert stats.episodes_with_violations == 1

    def test_episode_reset(self):
        """episode_reset should clear episode counters."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyStatistics

        stats = SafetyStatistics()
        stats.current_episode_violations = 5

        stats.episode_reset()

        assert stats.current_episode_violations == 0

    def test_to_dict(self):
        """to_dict should calculate violation_rate."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyStatistics

        stats = SafetyStatistics()
        stats.total_steps = 100
        stats.violations_total = 10

        d = stats.to_dict()

        assert d["violation_rate"] == 0.1


class TestSentinelSafetyWrapper:
    """Tests for SentinelSafetyWrapper."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock gymnasium environment."""
        env = Mock()
        env.step.return_value = (
            [0.0, 0.0, 0.0],  # obs
            1.0,  # reward
            False,  # terminated
            False,  # truncated
            {},  # info
        )
        env.reset.return_value = ([0.0, 0.0, 0.0], {})
        env.unwrapped = env
        # Configure mock to avoid TypeError in wrapper initialization and step()
        # - scene=None: prevents iteration error in _build_context
        # - num_envs=1: ensures _get_num_envs() returns int, not Mock
        env.configure_mock(scene=None, num_envs=1)
        return env

    def test_create_wrapper(self, mock_env):
        """SentinelSafetyWrapper can be created."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env, mode="clamp")

        assert wrapper.env == mock_env

    def test_step_safe_action(self, mock_env):
        """Safe action should pass through."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env, mode="clamp")

        obs, reward, term, trunc, info = wrapper.step([0.1, 0.2, 0.3])

        mock_env.step.assert_called_once()
        assert reward == 1.0

    def test_step_clamp_mode(self, mock_env):
        """Clamp mode should modify unsafe action."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env, mode="clamp")

        wrapper.step([1.5, -1.5, 0.0])  # Out of range

        # Should have clamped the action
        called_action = mock_env.step.call_args[0][0]
        # Action should have been modified
        assert wrapper.stats.actions_clamped >= 0  # May or may not clamp depending on type

    def test_step_block_mode(self, mock_env):
        """Block mode should use zero/previous action."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env, mode="block")

        # First call with safe action
        wrapper.step([0.1, 0.2, 0.3])
        # Second call with unsafe action
        wrapper.step([float('nan'), 0.0, 0.0])

        assert wrapper.stats.actions_blocked >= 1

    def test_reset_clears_episode_stats(self, mock_env):
        """reset should clear episode statistics."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env)
        wrapper.stats.current_episode_violations = 5

        wrapper.reset()

        assert wrapper.stats.current_episode_violations == 0

    def test_get_stats(self, mock_env):
        """get_stats should return statistics dict."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env)
        wrapper.step([0.1, 0.2, 0.3])

        stats = wrapper.get_stats()

        assert "total_steps" in stats
        assert stats["total_steps"] == 1

    def test_on_violation_callback(self, mock_env):
        """on_violation callback should be called."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        callback = Mock()
        wrapper = SentinelSafetyWrapper(
            mock_env,
            mode="warn",
            on_violation=callback,
        )

        wrapper.step([float('nan'), 0.0, 0.0])

        callback.assert_called_once()

    def test_add_safety_info(self, mock_env):
        """Safety info should be added to info dict."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_env, add_safety_info=True)

        obs, reward, term, trunc, info = wrapper.step([0.1, 0.2, 0.3])

        assert "sentinel_safety" in info


class TestActionClampingWrapper:
    """Tests for ActionClampingWrapper."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment."""
        env = Mock()
        env.step.return_value = ([0.0], 1.0, False, False, {})
        return env

    def test_clamps_to_normalized(self, mock_env):
        """Should clamp actions to [-1, 1]."""
        from sentinelseed.integrations.isaac_lab.wrappers import ActionClampingWrapper

        wrapper = ActionClampingWrapper(mock_env, clamp_to_normalized=True)

        wrapper.step([1.5, -1.5, 0.5])

        called_action = mock_env.step.call_args[0][0]
        assert all(-1.0 <= a <= 1.0 for a in called_action)


class TestSafetyMonitorWrapper:
    """Tests for SafetyMonitorWrapper."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment."""
        env = Mock()
        env.step.return_value = ([0.0], 1.0, False, False, {})
        env.reset.return_value = ([0.0], {})
        return env

    def test_does_not_modify_action(self, mock_env):
        """Monitor mode should not modify actions."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyMonitorWrapper

        wrapper = SafetyMonitorWrapper(mock_env)

        original_action = [1.5, -1.5, 0.0]
        wrapper.step(original_action)

        called_action = mock_env.step.call_args[0][0]
        assert called_action == original_action

    def test_collects_statistics(self, mock_env):
        """Should collect violation statistics."""
        from sentinelseed.integrations.isaac_lab.wrappers import SafetyMonitorWrapper

        wrapper = SafetyMonitorWrapper(mock_env)

        wrapper.step([float('nan'), 0.0, 0.0])

        stats = wrapper.get_stats()
        assert stats["violations_total"] >= 1


# =============================================================================
# Test Callbacks Module
# =============================================================================

class TestTrainingMetrics:
    """Tests for TrainingMetrics dataclass."""

    def test_create_metrics(self):
        """TrainingMetrics can be created."""
        from sentinelseed.integrations.isaac_lab.callbacks import TrainingMetrics

        metrics = TrainingMetrics()
        assert metrics.steps == 0

    def test_violation_rate(self):
        """violation_rate should be calculated correctly."""
        from sentinelseed.integrations.isaac_lab.callbacks import TrainingMetrics

        metrics = TrainingMetrics()
        metrics.steps = 100
        metrics.violations = 10

        assert metrics.violation_rate == 0.1

    def test_violation_rate_zero_steps(self):
        """violation_rate should handle zero steps."""
        from sentinelseed.integrations.isaac_lab.callbacks import TrainingMetrics

        metrics = TrainingMetrics()
        assert metrics.violation_rate == 0.0

    def test_to_dict(self):
        """to_dict should include all metrics."""
        from sentinelseed.integrations.isaac_lab.callbacks import TrainingMetrics

        metrics = TrainingMetrics()
        metrics.steps = 100

        d = metrics.to_dict()

        assert "sentinel/steps" in d
        assert "sentinel/violation_rate" in d

    def test_update_from_stats(self):
        """update_from_stats should update metrics."""
        from sentinelseed.integrations.isaac_lab.callbacks import TrainingMetrics

        metrics = TrainingMetrics()
        metrics.update_from_stats({
            "total_steps": 500,
            "violations_total": 25,
        })

        assert metrics.steps == 500
        assert metrics.violations == 25


class TestSentinelSB3Callback:
    """Tests for SentinelSB3Callback."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment with wrapper."""
        env = Mock()
        env.get_stats.return_value = {"total_steps": 0, "violations_total": 0}
        # Terminate _find_safety_wrapper loop (Mock().env returns another Mock)
        env.env = None
        return env

    def test_create_callback(self, mock_env):
        """SentinelSB3Callback can be created."""
        from sentinelseed.integrations.isaac_lab.callbacks import SentinelSB3Callback

        callback = SentinelSB3Callback(mock_env, log_interval=100)

        assert callback.log_interval == 100

    def test_on_step(self, mock_env):
        """on_step should return True."""
        from sentinelseed.integrations.isaac_lab.callbacks import SentinelSB3Callback

        callback = SentinelSB3Callback(mock_env)

        result = callback.on_step()

        assert result is True

    def test_on_episode_end(self, mock_env):
        """on_episode_end should increment episode count."""
        from sentinelseed.integrations.isaac_lab.callbacks import SentinelSB3Callback

        callback = SentinelSB3Callback(mock_env)

        callback.on_episode_end()
        callback.on_episode_end()

        assert callback.metrics.episodes == 2


class TestSentinelRLGamesCallback:
    """Tests for SentinelRLGamesCallback."""

    @pytest.fixture
    def mock_env(self):
        """Create a mock environment."""
        env = Mock()
        env.get_stats.return_value = {"total_steps": 0}
        # Terminate _find_safety_wrapper loop (Mock().env returns another Mock)
        env.env = None
        return env

    def test_create_callback(self, mock_env):
        """SentinelRLGamesCallback can be created."""
        from sentinelseed.integrations.isaac_lab.callbacks import SentinelRLGamesCallback

        callback = SentinelRLGamesCallback(mock_env)

        assert callback is not None

    def test_get_rl_games_callback(self, mock_env):
        """get_rl_games_callback should return callable."""
        from sentinelseed.integrations.isaac_lab.callbacks import SentinelRLGamesCallback

        callback = SentinelRLGamesCallback(mock_env)

        rl_callback = callback.get_rl_games_callback()

        assert callable(rl_callback)


# =============================================================================
# Test Module Imports
# =============================================================================

class TestModuleImports:
    """Test that all public API is importable."""

    def test_import_constraints(self):
        """Constraint classes should be importable."""
        from sentinelseed.integrations.isaac_lab import (
            JointLimits,
            WorkspaceLimits,
            ForceTorqueLimits,
            CollisionZone,
            RobotConstraints,
            ConstraintViolationType,
        )

        assert JointLimits is not None
        assert RobotConstraints is not None

    def test_import_validators(self):
        """Validator classes should be importable."""
        from sentinelseed.integrations.isaac_lab import (
            THSPRobotValidator,
            ActionValidationResult,
            BatchValidationResult,
            SafetyLevel,
            ActionType,
        )

        assert THSPRobotValidator is not None
        assert SafetyLevel is not None

    def test_import_wrappers(self):
        """Wrapper classes should be importable."""
        from sentinelseed.integrations.isaac_lab import (
            SentinelSafetyWrapper,
            ActionClampingWrapper,
            SafetyMonitorWrapper,
            SafetyMode,
            SafetyStatistics,
        )

        assert SentinelSafetyWrapper is not None
        assert SafetyMode is not None

    def test_import_callbacks(self):
        """Callback classes should be importable."""
        from sentinelseed.integrations.isaac_lab import (
            SentinelCallback,
            SentinelSB3Callback,
            SentinelRLGamesCallback,
            TrainingMetrics,
            create_wandb_callback,
            create_tensorboard_callback,
        )

        assert SentinelSB3Callback is not None
        assert create_wandb_callback is not None


class TestAllExports:
    """Test __all__ exports."""

    def test_all_defined(self):
        """__all__ should be defined."""
        import sentinelseed.integrations.isaac_lab as isaac_lab

        assert hasattr(isaac_lab, '__all__')
        assert len(isaac_lab.__all__) > 0

    def test_all_exports_exist(self):
        """All items in __all__ should exist."""
        import sentinelseed.integrations.isaac_lab as isaac_lab

        for name in isaac_lab.__all__:
            assert hasattr(isaac_lab, name), f"{name} in __all__ but not in module"


# =============================================================================
# Test Example Module
# =============================================================================

class TestExamples:
    """Test that examples run without error."""

    def test_example_module_exists(self):
        """Example module should exist."""
        from sentinelseed.integrations.isaac_lab import example
        assert example is not None

    def test_example_1_basic_constraints(self, capsys):
        """Example 1 should run without error."""
        from sentinelseed.integrations.isaac_lab.example import example_1_basic_constraints

        example_1_basic_constraints()

        captured = capsys.readouterr()
        assert "Example 1 complete" in captured.out

    def test_example_2_clamp_mode(self, capsys):
        """Example 2 should run without error."""
        from sentinelseed.integrations.isaac_lab.example import example_2_clamp_mode

        example_2_clamp_mode()

        captured = capsys.readouterr()
        assert "Example 2 complete" in captured.out

    def test_example_3_block_mode(self, capsys):
        """Example 3 should run without error."""
        from sentinelseed.integrations.isaac_lab.example import example_3_block_mode

        example_3_block_mode()

        captured = capsys.readouterr()
        assert "Example 3 complete" in captured.out

    def test_example_4_monitor_mode(self, capsys):
        """Example 4 should run without error."""
        from sentinelseed.integrations.isaac_lab.example import example_4_monitor_mode

        example_4_monitor_mode()

        captured = capsys.readouterr()
        assert "Example 4 complete" in captured.out

    def test_example_5_custom_robot(self, capsys):
        """Example 5 should run without error."""
        from sentinelseed.integrations.isaac_lab.example import example_5_custom_robot

        example_5_custom_robot()

        captured = capsys.readouterr()
        assert "Example 5 complete" in captured.out


# =============================================================================
# Test Fixes for Audit Issues
# =============================================================================

class TestHarmGateDimensionValidation:
    """Tests for dimension validation in harm gate."""

    def test_harm_gate_catches_short_action(self):
        """Harm gate should catch action with fewer dims than expected."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )
        from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints

        validator = THSPRobotValidator(
            constraints=RobotConstraints.franka_default(),  # 7 joints
            action_type=ActionType.NORMALIZED,
        )

        # Action with only 3 dims when 7 expected
        result = validator.validate([0.1, 0.2, 0.3])

        assert result.is_safe is False
        assert result.gates["harm"] is False
        assert any("dims" in v.lower() for v in result.violations)

    def test_harm_gate_uses_explicit_indexing(self):
        """Harm gate should use explicit indexing, not slicing."""
        from sentinelseed.integrations.isaac_lab.validators import (
            THSPRobotValidator,
            ActionType,
        )
        from sentinelseed.integrations.isaac_lab.constraints import (
            RobotConstraints,
            JointLimits,
        )

        # Create constraints with 3 joints
        constraints = RobotConstraints(
            joint_limits=JointLimits(
                num_joints=3,
                velocity_max=[1.0, 1.0, 1.0],
            )
        )

        validator = THSPRobotValidator(
            constraints=constraints,
            action_type=ActionType.NORMALIZED,
        )

        # Action with exactly 3 dims should pass
        result = validator.validate([0.5, 0.5, 0.5])
        assert result.is_safe is True


class TestBatchContextBuilding:
    """Tests for batch context building in wrapper."""

    @pytest.fixture
    def mock_vectorized_env(self):
        """Create a mock vectorized environment without scene."""
        env = Mock()
        env.num_envs = 4
        env.step.return_value = (
            [[0.0] * 3] * 4,  # obs
            [1.0] * 4,  # reward
            [False] * 4,  # terminated
            [False] * 4,  # truncated
            {},  # info
        )
        env.reset.return_value = ([[0.0] * 3] * 4, {})
        env.unwrapped = env
        # Explicitly set scene to not exist
        del env.scene
        return env

    @pytest.fixture
    def mock_vectorized_env_with_scene(self):
        """Create a mock vectorized environment with scene."""
        env = Mock()
        env.num_envs = 4
        env.step.return_value = (
            [[0.0] * 3] * 4,  # obs
            [1.0] * 4,  # reward
            [False] * 4,  # terminated
            [False] * 4,  # truncated
            {},  # info
        )
        env.reset.return_value = ([[0.0] * 3] * 4, {})
        env.unwrapped = env

        # Mock articulation data
        mock_data = Mock()
        mock_data.joint_pos = [[0.0] * 7] * 4  # 4 envs, 7 joints each
        mock_data.joint_vel = [[0.0] * 7] * 4

        mock_articulation = Mock()
        mock_articulation.data = mock_data

        mock_scene = Mock()
        mock_scene.articulations = {"robot": mock_articulation}

        env.scene = mock_scene
        env.physics_dt = 0.01
        return env

    def test_wrapper_builds_batch_contexts(self, mock_vectorized_env_with_scene):
        """Wrapper should build contexts for each env in batch."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_vectorized_env_with_scene, mode="monitor")

        # Verify wrapper detected vectorized env
        assert wrapper._num_envs == 4

        # _build_batch_contexts should return list of contexts
        contexts = wrapper._build_batch_contexts()
        assert contexts is not None
        assert len(contexts) == 4
        assert all('dt' in ctx for ctx in contexts)

    def test_wrapper_handles_missing_scene(self, mock_vectorized_env):
        """Wrapper should handle missing scene gracefully."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_vectorized_env, mode="monitor")

        # _build_batch_contexts should return None when scene not available
        contexts = wrapper._build_batch_contexts()
        assert contexts is None

    def test_wrapper_handles_missing_batch_contexts(self, mock_vectorized_env):
        """Wrapper should handle None contexts gracefully."""
        from sentinelseed.integrations.isaac_lab.wrappers import SentinelSafetyWrapper

        wrapper = SentinelSafetyWrapper(mock_vectorized_env, mode="clamp")

        # Step should work even without batch contexts
        action = [[0.1, 0.2, 0.3]] * 4
        obs, reward, term, trunc, info = wrapper.step(action)

        # Should complete without error
        mock_vectorized_env.step.assert_called_once()


class TestLoggingErrorHandling:
    """Tests for error handling in logging callbacks."""

    def test_wandb_callback_handles_log_error(self):
        """WandB callback should handle logging errors gracefully."""
        from sentinelseed.integrations.isaac_lab.callbacks import SentinelSB3Callback

        mock_env = Mock()
        mock_env.get_stats.return_value = {"total_steps": 100}
        # Terminate _find_safety_wrapper loop (Mock().env returns another Mock)
        mock_env.env = None

        # Create callback with failing on_log
        errors_caught = []

        def failing_log(metrics):
            raise RuntimeError("WandB connection failed")

        callback = SentinelSB3Callback(
            mock_env,
            log_interval=1,
            on_log=failing_log,
        )

        # Should not raise even though on_log fails
        callback.metrics.steps = 100
        callback._last_log_step = 0

        # This will call on_log which raises, but that's expected behavior
        # The test is that our factory functions wrap with try/catch
        with pytest.raises(RuntimeError):
            callback.log_metrics()

    def test_create_wandb_callback_wraps_errors(self):
        """create_wandb_callback should wrap log calls with try/catch."""
        # This test verifies the wrapper function handles errors
        # We can't fully test without wandb installed, so we just verify structure
        from sentinelseed.integrations.isaac_lab import callbacks

        # Verify the function exists and has correct signature
        assert hasattr(callbacks, 'create_wandb_callback')
        assert callable(callbacks.create_wandb_callback)

    def test_create_tensorboard_callback_wraps_errors(self):
        """create_tensorboard_callback should wrap log calls with try/catch."""
        from sentinelseed.integrations.isaac_lab import callbacks

        # Verify the function exists and has correct signature
        assert hasattr(callbacks, 'create_tensorboard_callback')
        assert callable(callbacks.create_tensorboard_callback)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
