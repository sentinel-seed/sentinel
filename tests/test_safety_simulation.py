"""
Comprehensive tests for the Simulation Safety Module.

Tests cover:
- JointLimits validation and factory methods
- WorkspaceLimits validation and containment
- ForceTorqueLimits validation
- CollisionZone containment checks
- RobotConstraints container
- ActionType enum
- BatchValidationResult
"""

import math
import pytest

from sentinelseed.safety.base import SafetyLevel
from sentinelseed.safety.simulation import (
    JointLimits,
    WorkspaceLimits,
    ForceTorqueLimits,
    CollisionZone,
    RobotConstraints,
    ConstraintViolationType,
    ActionType,
    BatchValidationResult,
)


# =============================================================================
# JointLimits Tests
# =============================================================================

class TestJointLimits:
    """Tests for JointLimits dataclass."""

    def test_default_limits(self):
        """Test default limits creation."""
        limits = JointLimits.default(num_joints=6)
        assert limits.num_joints == 6
        assert len(limits.position_lower) == 6
        assert len(limits.position_upper) == 6
        assert len(limits.velocity_max) == 6

    def test_invalid_num_joints(self):
        """Test that invalid num_joints raises error."""
        with pytest.raises(ValueError):
            JointLimits(num_joints=0)
        with pytest.raises(ValueError):
            JointLimits(num_joints=-1)

    def test_length_mismatch_rejected(self):
        """Test that mismatched list lengths are rejected."""
        with pytest.raises(ValueError):
            JointLimits(
                num_joints=6,
                position_lower=[-1.0] * 4,  # Wrong length
                position_upper=[1.0] * 6,
            )

    def test_single_value_expansion(self):
        """Test that single values are expanded to all joints."""
        limits = JointLimits(
            num_joints=4,
            position_lower=[-2.0],  # Single value
            position_upper=[2.0],   # Single value
            velocity_max=[1.5],     # Single value
        )
        assert limits.position_lower == [-2.0, -2.0, -2.0, -2.0]
        assert limits.position_upper == [2.0, 2.0, 2.0, 2.0]
        assert limits.velocity_max == [1.5, 1.5, 1.5, 1.5]

    def test_franka_panda_preset(self):
        """Test Franka Panda preset."""
        limits = JointLimits.franka_panda()
        assert limits.num_joints == 7
        assert len(limits.position_lower) == 7
        assert limits.effort_max is not None

    def test_ur10_preset(self):
        """Test UR10 preset."""
        limits = JointLimits.ur10()
        assert limits.num_joints == 6
        assert len(limits.velocity_max) == 6

    def test_allegro_hand_preset(self):
        """Test Allegro Hand preset."""
        limits = JointLimits.allegro_hand()
        assert limits.num_joints == 16

    def test_check_position_valid(self):
        """Test position checking for valid positions."""
        limits = JointLimits.default(num_joints=3)
        is_valid, violations = limits.check_position([0.0, 0.5, -0.5])
        assert is_valid is True
        assert len(violations) == 0

    def test_check_position_invalid(self):
        """Test position checking for invalid positions."""
        limits = JointLimits.default(num_joints=3)
        is_valid, violations = limits.check_position([10.0, 0.0, 0.0])  # Exceeds pi
        assert is_valid is False
        assert len(violations) > 0

    def test_check_position_nan(self):
        """Test position checking for NaN values."""
        limits = JointLimits.default(num_joints=3)
        is_valid, violations = limits.check_position([float('nan'), 0.0, 0.0])
        assert is_valid is False
        assert any("Invalid" in v for v in violations)

    def test_check_velocity_valid(self):
        """Test velocity checking for valid velocities."""
        limits = JointLimits.default(num_joints=3)
        is_valid, violations = limits.check_velocity([1.0, -1.0, 0.5])
        assert is_valid is True

    def test_check_velocity_invalid(self):
        """Test velocity checking for invalid velocities."""
        limits = JointLimits.default(num_joints=3)
        is_valid, violations = limits.check_velocity([5.0, 0.0, 0.0])  # Exceeds 2.0
        assert is_valid is False

    def test_clamp_position(self):
        """Test position clamping."""
        limits = JointLimits.default(num_joints=3)
        clamped = limits.clamp_position([10.0, -10.0, 0.0])
        assert clamped[0] == pytest.approx(math.pi)
        assert clamped[1] == pytest.approx(-math.pi)
        assert clamped[2] == 0.0

    def test_clamp_velocity(self):
        """Test velocity clamping."""
        limits = JointLimits.default(num_joints=3)
        clamped = limits.clamp_velocity([5.0, -5.0, 1.0])
        assert clamped[0] == 2.0
        assert clamped[1] == -2.0
        assert clamped[2] == 1.0


# =============================================================================
# WorkspaceLimits Tests
# =============================================================================

class TestWorkspaceLimits:
    """Tests for WorkspaceLimits dataclass."""

    def test_default_values(self):
        """Test default workspace values."""
        ws = WorkspaceLimits()
        assert ws.x_min == -1.0
        assert ws.x_max == 1.0
        assert ws.z_max == 1.5

    def test_contains_inside(self):
        """Test contains for position inside workspace."""
        ws = WorkspaceLimits()
        assert ws.contains(0.0, 0.0, 0.5) is True

    def test_contains_outside(self):
        """Test contains for position outside workspace."""
        ws = WorkspaceLimits()
        assert ws.contains(2.0, 0.0, 0.5) is False

    def test_contains_with_sphere(self):
        """Test contains with spherical constraint."""
        ws = WorkspaceLimits.franka_reach()
        # Center should be inside
        assert ws.contains(0.5, 0.0, 0.4) is True
        # Far from center should be outside sphere
        assert ws.contains(0.25, -0.5, 0.0) is False

    def test_check_position_valid(self):
        """Test position checking for valid position."""
        ws = WorkspaceLimits()
        is_valid, violations = ws.check_position([0.0, 0.0, 0.5])
        assert is_valid is True

    def test_check_position_invalid(self):
        """Test position checking for invalid position."""
        ws = WorkspaceLimits()
        is_valid, violations = ws.check_position([2.0, 0.0, 0.5])
        assert is_valid is False
        assert any("X" in v for v in violations)

    def test_franka_reach_preset(self):
        """Test Franka reach preset."""
        ws = WorkspaceLimits.franka_reach()
        assert ws.center is not None
        assert ws.radius is not None

    def test_table_top_preset(self):
        """Test tabletop preset."""
        ws = WorkspaceLimits.table_top(table_height=0.5)
        assert ws.z_min == 0.5

    def test_unlimited_preset(self):
        """Test unlimited preset."""
        ws = WorkspaceLimits.unlimited()
        # Should contain any reasonable position
        assert ws.contains(1000.0, 1000.0, 1000.0) is True


# =============================================================================
# ForceTorqueLimits Tests
# =============================================================================

class TestForceTorqueLimits:
    """Tests for ForceTorqueLimits dataclass."""

    def test_default_values(self):
        """Test default force/torque values."""
        ft = ForceTorqueLimits()
        assert ft.max_force == 50.0
        assert ft.max_torque == 10.0

    def test_check_force_valid(self):
        """Test force checking for valid force."""
        ft = ForceTorqueLimits()
        is_valid, violations = ft.check_force([10.0, 10.0, 10.0])
        assert is_valid is True

    def test_check_force_magnitude_exceeded(self):
        """Test force checking when magnitude exceeded."""
        ft = ForceTorqueLimits(max_force=10.0)
        is_valid, violations = ft.check_force([10.0, 10.0, 10.0])  # ~17.3N
        assert is_valid is False

    def test_check_force_per_axis(self):
        """Test per-axis force limits."""
        ft = ForceTorqueLimits(
            max_force=100.0,
            max_force_per_axis=(10.0, 10.0, 10.0),
        )
        is_valid, violations = ft.check_force([15.0, 0.0, 0.0])
        assert is_valid is False
        assert any("Fx" in v for v in violations)

    def test_check_torque_valid(self):
        """Test torque checking for valid torque."""
        ft = ForceTorqueLimits()
        is_valid, violations = ft.check_torque([1.0, 1.0, 1.0])
        assert is_valid is True

    def test_check_torque_exceeded(self):
        """Test torque checking when exceeded."""
        ft = ForceTorqueLimits(max_torque=5.0)
        is_valid, violations = ft.check_torque([5.0, 5.0, 5.0])  # ~8.7Nm
        assert is_valid is False

    def test_franka_contact_preset(self):
        """Test Franka contact preset."""
        ft = ForceTorqueLimits.franka_contact()
        assert ft.max_force == 30.0
        assert ft.max_force_per_axis is not None

    def test_human_safe_preset(self):
        """Test human-safe preset."""
        ft = ForceTorqueLimits.human_safe()
        assert ft.max_force == 150.0  # ISO limit


# =============================================================================
# CollisionZone Tests
# =============================================================================

class TestCollisionZone:
    """Tests for CollisionZone dataclass."""

    def test_sphere_contains_inside(self):
        """Test sphere containment for point inside."""
        zone = CollisionZone.sphere("test", center=(0.0, 0.0, 0.0), radius=1.0)
        assert zone.contains(0.0, 0.0, 0.0) is True
        assert zone.contains(0.5, 0.0, 0.0) is True

    def test_sphere_contains_outside(self):
        """Test sphere containment for point outside."""
        zone = CollisionZone.sphere("test", center=(0.0, 0.0, 0.0), radius=1.0)
        assert zone.contains(2.0, 0.0, 0.0) is False

    def test_sphere_margin(self):
        """Test sphere margin is applied."""
        zone = CollisionZone.sphere("test", center=(0.0, 0.0, 0.0), radius=1.0, margin=0.1)
        # Point at radius 1.05 should be inside (radius + margin = 1.1)
        assert zone.contains(1.05, 0.0, 0.0) is True

    def test_box_contains_inside(self):
        """Test box containment for point inside."""
        zone = CollisionZone.box("test", center=(0.0, 0.0, 0.0), half_extents=(1.0, 1.0, 1.0))
        assert zone.contains(0.0, 0.0, 0.0) is True
        assert zone.contains(0.5, 0.5, 0.5) is True

    def test_box_contains_outside(self):
        """Test box containment for point outside."""
        zone = CollisionZone.box("test", center=(0.0, 0.0, 0.0), half_extents=(1.0, 1.0, 1.0))
        assert zone.contains(2.0, 0.0, 0.0) is False

    def test_cylinder_contains_inside(self):
        """Test cylinder containment for point inside."""
        zone = CollisionZone.cylinder("test", center=(0.0, 0.0, 0.5), radius=0.5, half_height=0.5)
        assert zone.contains(0.0, 0.0, 0.5) is True

    def test_cylinder_contains_outside(self):
        """Test cylinder containment for point outside."""
        zone = CollisionZone.cylinder("test", center=(0.0, 0.0, 0.5), radius=0.5, half_height=0.5)
        assert zone.contains(1.0, 0.0, 0.5) is False  # Outside radius
        assert zone.contains(0.0, 0.0, 2.0) is False  # Outside height


# =============================================================================
# RobotConstraints Tests
# =============================================================================

class TestRobotConstraints:
    """Tests for RobotConstraints container."""

    def test_empty_constraints(self):
        """Test empty constraints creation."""
        constraints = RobotConstraints()
        assert constraints.joint_limits is None
        assert constraints.workspace_limits is None
        assert constraints.collision_zones == []

    def test_franka_default_preset(self):
        """Test Franka default preset."""
        constraints = RobotConstraints.franka_default()
        assert constraints.joint_limits is not None
        assert constraints.joint_limits.num_joints == 7
        assert constraints.workspace_limits is not None
        assert constraints.force_torque_limits is not None

    def test_ur10_default_preset(self):
        """Test UR10 default preset."""
        constraints = RobotConstraints.ur10_default()
        assert constraints.joint_limits is not None
        assert constraints.joint_limits.num_joints == 6

    def test_allegro_default_preset(self):
        """Test Allegro default preset."""
        constraints = RobotConstraints.allegro_default()
        assert constraints.joint_limits is not None
        assert constraints.joint_limits.num_joints == 16

    def test_from_urdf_limits(self):
        """Test creation from URDF-style limits."""
        constraints = RobotConstraints.from_urdf_limits(
            position_lower=[-1.0] * 4,
            position_upper=[1.0] * 4,
            velocity_max=[2.0] * 4,
        )
        assert constraints.joint_limits.num_joints == 4

    def test_add_collision_zone(self):
        """Test adding collision zones."""
        constraints = RobotConstraints()
        zone = CollisionZone.sphere("obstacle", (0.5, 0.0, 0.5), 0.1)
        constraints.add_collision_zone(zone)
        assert len(constraints.collision_zones) == 1

    def test_add_collision_zone_chaining(self):
        """Test collision zone chaining."""
        constraints = (
            RobotConstraints()
            .add_collision_zone(CollisionZone.sphere("o1", (0.0, 0.0, 0.0), 0.1))
            .add_collision_zone(CollisionZone.sphere("o2", (1.0, 0.0, 0.0), 0.1))
        )
        assert len(constraints.collision_zones) == 2

    def test_check_collision(self):
        """Test collision checking."""
        constraints = RobotConstraints()
        constraints.add_collision_zone(CollisionZone.sphere("obstacle", (0.5, 0.0, 0.5), 0.1))

        has_collision, names = constraints.check_collision(0.5, 0.0, 0.5)
        assert has_collision is True
        assert "obstacle" in names

        has_collision, names = constraints.check_collision(0.0, 0.0, 0.0)
        assert has_collision is False


# =============================================================================
# ActionType Tests
# =============================================================================

class TestActionType:
    """Tests for ActionType enum."""

    def test_all_types_exist(self):
        """Test all action types are defined."""
        # Joint space
        assert ActionType.JOINT_POSITION.value == "joint_position"
        assert ActionType.JOINT_VELOCITY.value == "joint_velocity"
        assert ActionType.JOINT_POSITION_DELTA.value == "joint_position_delta"
        assert ActionType.JOINT_EFFORT.value == "joint_effort"

        # Cartesian space
        assert ActionType.CARTESIAN.value == "cartesian"
        assert ActionType.CARTESIAN_POSE.value == "cartesian_pose"
        assert ActionType.CARTESIAN_VELOCITY.value == "cartesian_velocity"

        # Special types
        assert ActionType.NORMALIZED.value == "normalized"
        assert ActionType.TORQUE.value == "torque"
        assert ActionType.UNKNOWN.value == "unknown"

    def test_needs_scaling_property(self):
        """Test needs_scaling property."""
        assert ActionType.NORMALIZED.needs_scaling is True
        assert ActionType.JOINT_POSITION.needs_scaling is False
        assert ActionType.UNKNOWN.needs_scaling is False

    def test_is_velocity_based_property(self):
        """Test is_velocity_based property."""
        assert ActionType.JOINT_VELOCITY.is_velocity_based is True
        assert ActionType.JOINT_POSITION_DELTA.is_velocity_based is True
        assert ActionType.CARTESIAN_VELOCITY.is_velocity_based is True
        assert ActionType.JOINT_POSITION.is_velocity_based is False

    def test_is_position_based_property(self):
        """Test is_position_based property."""
        assert ActionType.JOINT_POSITION.is_position_based is True
        assert ActionType.CARTESIAN.is_position_based is True
        assert ActionType.CARTESIAN_POSE.is_position_based is True
        assert ActionType.JOINT_VELOCITY.is_position_based is False

    def test_is_effort_based_property(self):
        """Test is_effort_based property."""
        assert ActionType.JOINT_EFFORT.is_effort_based is True
        assert ActionType.TORQUE.is_effort_based is True
        assert ActionType.JOINT_POSITION.is_effort_based is False


# =============================================================================
# BatchValidationResult Tests
# =============================================================================

class TestBatchValidationResult:
    """Tests for BatchValidationResult dataclass."""

    def test_basic_creation(self):
        """Test basic batch result creation."""
        result = BatchValidationResult(
            is_safe=[True, False, True],
            levels=[SafetyLevel.SAFE, SafetyLevel.DANGEROUS, SafetyLevel.SAFE],
        )
        assert result.num_environments == 3
        assert result.all_safe is False
        assert result.any_unsafe is True

    def test_all_safe_result(self):
        """Test all_safe_result factory."""
        result = BatchValidationResult.all_safe_result(num_envs=5)
        assert result.num_environments == 5
        assert result.all_safe is True
        assert all(level == SafetyLevel.SAFE for level in result.levels)

    def test_safe_ratio(self):
        """Test safe_ratio calculation."""
        result = BatchValidationResult(
            is_safe=[True, True, False, False],
            levels=[SafetyLevel.SAFE] * 4,
        )
        assert result.safe_ratio == 0.5

    def test_unsafe_indices(self):
        """Test unsafe_indices property."""
        result = BatchValidationResult(
            is_safe=[True, False, True, False],
            levels=[SafetyLevel.SAFE] * 4,
        )
        assert result.unsafe_indices == [1, 3]

    def test_safe_indices(self):
        """Test safe_indices property."""
        result = BatchValidationResult(
            is_safe=[True, False, True, False],
            levels=[SafetyLevel.SAFE] * 4,
        )
        assert result.safe_indices == [0, 2]

    def test_get_worst_level(self):
        """Test get_worst_level method."""
        result = BatchValidationResult(
            is_safe=[True, False, False],
            levels=[SafetyLevel.SAFE, SafetyLevel.WARNING, SafetyLevel.DANGEROUS],
        )
        assert result.get_worst_level() == SafetyLevel.DANGEROUS

    def test_stats_calculated(self):
        """Test stats are calculated on creation."""
        result = BatchValidationResult(
            is_safe=[True, True, False],
            levels=[SafetyLevel.SAFE, SafetyLevel.SAFE, SafetyLevel.WARNING],
        )
        assert result.stats["total"] == 3
        assert result.stats["safe"] == 2
        assert result.stats["unsafe"] == 1

    def test_from_single_results(self):
        """Test from_single_results factory."""
        single_results = [
            {"is_safe": True, "level": SafetyLevel.SAFE, "violations": []},
            {"is_safe": False, "level": SafetyLevel.DANGEROUS, "violations": ["error"]},
        ]
        result = BatchValidationResult.from_single_results(single_results)
        assert result.num_environments == 2
        assert result.is_safe == [True, False]
        assert result.violations == [0, 1]


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Tests for to_dict/from_dict methods."""

    def test_joint_limits_roundtrip(self):
        """Test JointLimits serialization roundtrip."""
        original = JointLimits.franka_panda()
        data = original.to_dict()
        restored = JointLimits.from_dict(data)

        assert restored.num_joints == original.num_joints
        assert restored.position_lower == original.position_lower
        assert restored.position_upper == original.position_upper
        assert restored.velocity_max == original.velocity_max

    def test_joint_limits_from_dict_minimal(self):
        """Test JointLimits.from_dict with minimal data."""
        data = {
            "num_joints": 3,
            "position_lower": [-1.0, -1.0, -1.0],
            "position_upper": [1.0, 1.0, 1.0],
            "velocity_max": [2.0, 2.0, 2.0],
        }
        jl = JointLimits.from_dict(data)
        assert jl.num_joints == 3
        assert jl.acceleration_max is None
        assert jl.effort_max is None

    def test_workspace_limits_roundtrip(self):
        """Test WorkspaceLimits serialization roundtrip."""
        original = WorkspaceLimits.franka_reach()
        data = original.to_dict()
        restored = WorkspaceLimits.from_dict(data)

        assert restored.x_min == original.x_min
        assert restored.x_max == original.x_max
        assert restored.center == original.center
        assert restored.radius == original.radius

    def test_workspace_limits_from_dict_without_sphere(self):
        """Test WorkspaceLimits.from_dict without spherical constraints."""
        data = {
            "x_min": -1.0, "x_max": 1.0,
            "y_min": -1.0, "y_max": 1.0,
            "z_min": 0.0, "z_max": 1.0,
            "center": None,
            "radius": None,
        }
        ws = WorkspaceLimits.from_dict(data)
        assert ws.center is None
        assert ws.radius is None

    def test_force_torque_limits_roundtrip(self):
        """Test ForceTorqueLimits serialization roundtrip."""
        original = ForceTorqueLimits.franka_contact()
        data = original.to_dict()
        restored = ForceTorqueLimits.from_dict(data)

        assert restored.max_force == original.max_force
        assert restored.max_torque == original.max_torque
        assert restored.max_force_per_axis == original.max_force_per_axis

    def test_force_torque_limits_from_dict_minimal(self):
        """Test ForceTorqueLimits.from_dict with minimal data."""
        data = {
            "max_force": 100.0,
            "max_torque": 20.0,
            "max_force_per_axis": None,
            "max_torque_per_axis": None,
        }
        ft = ForceTorqueLimits.from_dict(data)
        assert ft.max_force == 100.0
        assert ft.max_force_per_axis is None

    def test_collision_zone_sphere_roundtrip(self):
        """Test CollisionZone sphere serialization roundtrip."""
        original = CollisionZone.sphere("obstacle", center=(0.5, 0.0, 0.3), radius=0.1)
        data = original.to_dict()
        restored = CollisionZone.from_dict(data)

        assert restored.name == original.name
        assert restored.shape == original.shape
        assert restored.center == original.center
        assert restored.dimensions == original.dimensions
        assert restored.margin == original.margin

    def test_collision_zone_box_roundtrip(self):
        """Test CollisionZone box serialization roundtrip."""
        original = CollisionZone.box("table", center=(0.0, 0.0, -0.1), half_extents=(0.5, 0.5, 0.1))
        data = original.to_dict()
        restored = CollisionZone.from_dict(data)

        assert restored.name == original.name
        assert restored.shape == "box"
        assert restored.dimensions == (0.5, 0.5, 0.1)

    def test_collision_zone_cylinder_roundtrip(self):
        """Test CollisionZone cylinder serialization roundtrip."""
        original = CollisionZone.cylinder("pillar", center=(1.0, 0.0, 0.5), radius=0.1, half_height=0.5)
        data = original.to_dict()
        restored = CollisionZone.from_dict(data)

        assert restored.name == original.name
        assert restored.shape == "cylinder"
        assert restored.dimensions == (0.1, 0.5)

    def test_robot_constraints_roundtrip(self):
        """Test RobotConstraints serialization roundtrip."""
        original = RobotConstraints.franka_default()
        original.add_collision_zone(CollisionZone.sphere("obj", (0.5, 0.0, 0.3), 0.1))

        data = original.to_dict()
        restored = RobotConstraints.from_dict(data)

        assert restored.joint_limits is not None
        assert restored.workspace_limits is not None
        assert restored.force_torque_limits is not None
        assert len(restored.collision_zones) == 1
        assert restored.collision_zones[0].name == "obj"
        assert restored.action_scale == original.action_scale

    def test_robot_constraints_from_dict_empty(self):
        """Test RobotConstraints.from_dict with empty data."""
        data = {
            "joint_limits": None,
            "workspace_limits": None,
            "force_torque_limits": None,
            "collision_zones": [],
            "action_scale": 2.0,
            "require_purpose": True,
        }
        rc = RobotConstraints.from_dict(data)
        assert rc.joint_limits is None
        assert rc.workspace_limits is None
        assert rc.action_scale == 2.0
        assert rc.require_purpose is True


# =============================================================================
# Module Tests
# =============================================================================

class TestModule:
    """Tests for module-level imports."""

    def test_imports_from_safety(self):
        """Test that simulation can be imported from safety module."""
        from sentinelseed.safety import simulation
        assert hasattr(simulation, "JointLimits")
        assert hasattr(simulation, "RobotConstraints")
        assert hasattr(simulation, "ActionType")

    def test_constraint_violation_type(self):
        """Test ConstraintViolationType enum."""
        assert ConstraintViolationType.JOINT_POSITION.value == "joint_position"
        assert ConstraintViolationType.COLLISION.value == "collision"
