"""
Comprehensive tests for the Mobile Robot Safety Module.

Tests cover:
- VelocityLimits validation and factory methods
- SafetyZone validation and containment checks
- Preset configurations for different robot types
"""

import math
import pytest

from sentinelseed.safety.mobile import (
    VelocityLimits,
    SafetyZone,
    ValidationError,
    DEFAULT_MAX_LINEAR_VEL,
    DEFAULT_MAX_ANGULAR_VEL,
    DEFAULT_ROOM_SIZE,
    DEFAULT_MAX_ALTITUDE,
)


# =============================================================================
# VelocityLimits Tests
# =============================================================================

class TestVelocityLimits:
    """Tests for VelocityLimits dataclass."""

    def test_default_values(self):
        """Test default velocity limits."""
        limits = VelocityLimits()
        assert limits.max_linear_x == DEFAULT_MAX_LINEAR_VEL
        assert limits.max_linear_y == 0.0
        assert limits.max_linear_z == 0.0
        assert limits.max_angular_x == 0.0
        assert limits.max_angular_y == 0.0
        assert limits.max_angular_z == DEFAULT_MAX_ANGULAR_VEL

    def test_custom_values(self):
        """Test custom velocity limits."""
        limits = VelocityLimits(
            max_linear_x=2.0,
            max_linear_y=1.5,
            max_linear_z=1.0,
            max_angular_x=0.5,
            max_angular_y=0.5,
            max_angular_z=1.0,
        )
        assert limits.max_linear_x == 2.0
        assert limits.max_linear_y == 1.5
        assert limits.max_linear_z == 1.0
        assert limits.max_angular_z == 1.0

    def test_negative_value_rejected(self):
        """Test that negative limits are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VelocityLimits(max_linear_x=-1.0)
        assert "cannot be negative" in str(exc_info.value)
        assert exc_info.value.field == "max_linear_x"

    def test_nan_value_rejected(self):
        """Test that NaN limits are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VelocityLimits(max_linear_x=float('nan'))
        assert "finite number" in str(exc_info.value)

    def test_inf_value_rejected(self):
        """Test that infinite limits are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            VelocityLimits(max_angular_z=float('inf'))
        assert "finite number" in str(exc_info.value)

    def test_differential_drive_preset(self):
        """Test differential drive preset."""
        limits = VelocityLimits.differential_drive(max_linear=0.5, max_angular=1.0)
        assert limits.max_linear_x == 0.5
        assert limits.max_linear_y == 0.0  # No lateral movement
        assert limits.max_linear_z == 0.0  # Ground robot
        assert limits.max_angular_z == 1.0

    def test_omnidirectional_preset(self):
        """Test omnidirectional preset."""
        limits = VelocityLimits.omnidirectional(max_linear=0.8, max_angular=1.5)
        assert limits.max_linear_x == 0.8
        assert limits.max_linear_y == 0.8  # Same as x for omni
        assert limits.max_linear_z == 0.0  # Ground robot
        assert limits.max_angular_z == 1.5

    def test_drone_preset(self):
        """Test drone preset."""
        limits = VelocityLimits.drone(max_linear=5.0, max_vertical=2.0, max_angular=2.0)
        assert limits.max_linear_x == 5.0
        assert limits.max_linear_y == 5.0
        assert limits.max_linear_z == 2.0  # Different for vertical
        assert limits.max_angular_x == 2.0
        assert limits.max_angular_y == 2.0
        assert limits.max_angular_z == 2.0

    def test_clamp_velocity_within_limits(self):
        """Test clamping velocities within limits."""
        limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)
        result = limits.clamp_velocity(0.5, 0.0, 0.0, 0.0, 0.0, 0.3)
        assert result == (0.5, 0.0, 0.0, 0.0, 0.0, 0.3)

    def test_clamp_velocity_exceeds_limits(self):
        """Test clamping velocities that exceed limits."""
        limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)
        result = limits.clamp_velocity(2.0, 0.5, 0.0, 0.0, 0.0, 1.0)
        assert result[0] == 1.0  # Clamped from 2.0
        assert result[1] == 0.0  # Clamped to 0 (limit is 0)
        assert result[5] == 0.5  # Clamped from 1.0

    def test_clamp_velocity_negative(self):
        """Test clamping negative velocities."""
        limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)
        result = limits.clamp_velocity(-2.0, 0.0, 0.0, 0.0, 0.0, -1.0)
        assert result[0] == -1.0  # Clamped from -2.0
        assert result[5] == -0.5  # Clamped from -1.0

    def test_check_velocity_valid(self):
        """Test checking valid velocities."""
        limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)
        is_valid, violations = limits.check_velocity(0.5, 0.0, 0.0, 0.0, 0.0, 0.3)
        assert is_valid is True
        assert len(violations) == 0

    def test_check_velocity_invalid(self):
        """Test checking invalid velocities."""
        limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)
        is_valid, violations = limits.check_velocity(2.0, 0.0, 0.0, 0.0, 0.0, 1.0)
        assert is_valid is False
        assert len(violations) == 2  # linear_x and angular_z

    def test_check_velocity_nan(self):
        """Test checking NaN velocities."""
        limits = VelocityLimits()
        is_valid, violations = limits.check_velocity(float('nan'), 0.0, 0.0, 0.0, 0.0, 0.0)
        assert is_valid is False
        assert any("invalid value" in v for v in violations)

    def test_check_velocity_constrained_axis(self):
        """Test checking velocity on constrained axis."""
        limits = VelocityLimits.differential_drive()  # max_linear_y = 0
        is_valid, violations = limits.check_velocity(0.0, 0.5, 0.0, 0.0, 0.0, 0.0)
        assert is_valid is False
        assert any("not allowed" in v for v in violations)

    def test_to_dict(self):
        """Test serialization to dictionary."""
        limits = VelocityLimits.drone(max_linear=3.0, max_vertical=1.5, max_angular=1.0)
        d = limits.to_dict()
        assert d["max_linear_x"] == 3.0
        assert d["max_linear_z"] == 1.5
        assert d["max_angular_z"] == 1.0

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {"max_linear_x": 2.0, "max_angular_z": 1.0}
        limits = VelocityLimits.from_dict(d)
        assert limits.max_linear_x == 2.0
        assert limits.max_angular_z == 1.0
        assert limits.max_linear_y == 0.0  # Default


# =============================================================================
# SafetyZone Tests
# =============================================================================

class TestSafetyZone:
    """Tests for SafetyZone dataclass."""

    def test_default_values(self):
        """Test default safety zone values."""
        zone = SafetyZone()
        assert zone.min_x == -DEFAULT_ROOM_SIZE / 2
        assert zone.max_x == DEFAULT_ROOM_SIZE / 2
        assert zone.min_z == 0.0
        assert zone.max_z == DEFAULT_MAX_ALTITUDE

    def test_custom_values(self):
        """Test custom safety zone values."""
        zone = SafetyZone(min_x=-10, max_x=10, min_y=-5, max_y=5, min_z=0, max_z=3)
        assert zone.min_x == -10
        assert zone.max_x == 10
        assert zone.max_z == 3

    def test_min_greater_than_max_rejected(self):
        """Test that min > max is rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyZone(min_x=5, max_x=-5)
        assert "cannot be greater than" in str(exc_info.value)

    def test_nan_value_rejected(self):
        """Test that NaN values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyZone(min_x=float('nan'))
        assert "NaN" in str(exc_info.value)

    def test_contains_inside(self):
        """Test contains for position inside zone."""
        zone = SafetyZone.indoor(room_size=10.0)
        assert zone.contains(0.0, 0.0, 0.0) is True
        assert zone.contains(4.0, 4.0, 2.0) is True
        assert zone.contains(-4.0, -4.0, 1.0) is True

    def test_contains_outside(self):
        """Test contains for position outside zone."""
        zone = SafetyZone.indoor(room_size=10.0)
        assert zone.contains(10.0, 0.0, 0.0) is False  # Outside x
        assert zone.contains(0.0, 10.0, 0.0) is False  # Outside y
        assert zone.contains(0.0, 0.0, 10.0) is False  # Outside z

    def test_contains_boundary(self):
        """Test contains for position on boundary."""
        zone = SafetyZone.indoor(room_size=10.0)
        assert zone.contains(5.0, 0.0, 0.0) is True  # On max_x boundary
        assert zone.contains(-5.0, 0.0, 0.0) is True  # On min_x boundary

    def test_contains_nan(self):
        """Test contains returns False for NaN positions."""
        zone = SafetyZone()
        assert zone.contains(float('nan'), 0.0, 0.0) is False
        assert zone.contains(0.0, float('nan'), 0.0) is False
        assert zone.contains(0.0, 0.0, float('nan')) is False

    def test_unlimited_preset(self):
        """Test unlimited safety zone preset."""
        zone = SafetyZone.unlimited()
        # Should contain any reasonable position
        assert zone.contains(1000000.0, 1000000.0, 1000000.0) is True
        assert zone.contains(-1000000.0, -1000000.0, -1000000.0) is True

    def test_indoor_preset(self):
        """Test indoor safety zone preset."""
        zone = SafetyZone.indoor(room_size=10.0)
        assert zone.min_x == -5.0
        assert zone.max_x == 5.0
        assert zone.max_z == 3.0  # Indoor ceiling

    def test_indoor_preset_invalid_size(self):
        """Test indoor preset with invalid room size."""
        with pytest.raises(ValidationError):
            SafetyZone.indoor(room_size=0)
        with pytest.raises(ValidationError):
            SafetyZone.indoor(room_size=-5)

    def test_outdoor_preset(self):
        """Test outdoor safety zone preset."""
        zone = SafetyZone.outdoor(width=100.0, depth=50.0, max_altitude=30.0)
        assert zone.min_x == -50.0
        assert zone.max_x == 50.0
        assert zone.min_y == -25.0
        assert zone.max_y == 25.0
        assert zone.max_z == 30.0

    def test_corridor_preset(self):
        """Test corridor safety zone preset."""
        zone = SafetyZone.corridor(length=20.0, width=2.0, height=3.0)
        assert zone.min_x == -10.0
        assert zone.max_x == 10.0
        assert zone.min_y == -1.0
        assert zone.max_y == 1.0
        assert zone.max_z == 3.0

    def test_distance_to_boundary_inside(self):
        """Test distance to boundary from inside."""
        zone = SafetyZone(min_x=-5, max_x=5, min_y=-5, max_y=5, min_z=0, max_z=3)
        dist = zone.distance_to_boundary(0.0, 0.0, 1.0)
        assert dist > 0  # Inside, so positive

    def test_distance_to_boundary_outside(self):
        """Test distance to boundary from outside."""
        zone = SafetyZone(min_x=-5, max_x=5, min_y=-5, max_y=5, min_z=0, max_z=3)
        dist = zone.distance_to_boundary(10.0, 0.0, 1.0)
        assert dist < 0  # Outside, so negative

    def test_distance_to_boundary_nan(self):
        """Test distance to boundary with NaN position."""
        zone = SafetyZone()
        dist = zone.distance_to_boundary(float('nan'), 0.0, 0.0)
        assert dist == float('-inf')

    def test_clamp_position_inside(self):
        """Test clamping position already inside zone."""
        zone = SafetyZone.indoor(room_size=10.0)
        result = zone.clamp_position(1.0, 2.0, 1.0)
        assert result == (1.0, 2.0, 1.0)

    def test_clamp_position_outside(self):
        """Test clamping position outside zone."""
        zone = SafetyZone.indoor(room_size=10.0)
        result = zone.clamp_position(10.0, 10.0, 10.0)
        assert result[0] == 5.0  # Clamped to max_x
        assert result[1] == 5.0  # Clamped to max_y
        assert result[2] == 3.0  # Clamped to max_z (indoor ceiling)

    def test_center_property(self):
        """Test center property."""
        zone = SafetyZone(min_x=-10, max_x=10, min_y=-5, max_y=5, min_z=0, max_z=4)
        assert zone.center == (0.0, 0.0, 2.0)

    def test_dimensions_property(self):
        """Test dimensions property."""
        zone = SafetyZone(min_x=-10, max_x=10, min_y=-5, max_y=5, min_z=0, max_z=4)
        assert zone.dimensions == (20.0, 10.0, 4.0)

    def test_volume_property(self):
        """Test volume property."""
        zone = SafetyZone(min_x=-5, max_x=5, min_y=-5, max_y=5, min_z=0, max_z=2)
        assert zone.volume == 10.0 * 10.0 * 2.0  # 200 cubic meters

    def test_to_dict(self):
        """Test serialization to dictionary."""
        zone = SafetyZone.indoor(room_size=10.0)
        d = zone.to_dict()
        assert d["min_x"] == -5.0
        assert d["max_x"] == 5.0
        assert d["max_z"] == 3.0

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        d = {"min_x": -10, "max_x": 10, "min_z": 0, "max_z": 5}
        zone = SafetyZone.from_dict(d)
        assert zone.min_x == -10
        assert zone.max_x == 10
        assert zone.max_z == 5


# =============================================================================
# Module Tests
# =============================================================================

class TestModule:
    """Tests for module-level imports and constants."""

    def test_constants_exist(self):
        """Test that all constants are defined."""
        assert DEFAULT_MAX_LINEAR_VEL > 0
        assert DEFAULT_MAX_ANGULAR_VEL > 0
        assert DEFAULT_ROOM_SIZE > 0
        assert DEFAULT_MAX_ALTITUDE > 0

    def test_validation_error_attributes(self):
        """Test ValidationError attributes."""
        error = ValidationError("test message", field="test_field")
        assert error.message == "test message"
        assert error.field == "test_field"
        assert str(error) == "test message"

    def test_imports_from_safety(self):
        """Test that mobile can be imported from safety module."""
        from sentinelseed.safety import mobile
        assert hasattr(mobile, "VelocityLimits")
        assert hasattr(mobile, "SafetyZone")
