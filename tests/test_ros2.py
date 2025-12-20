"""
Comprehensive tests for Sentinel ROS2 Integration.

Tests cover:
- Module attributes (__version__, __all__)
- Constants validation
- VelocityLimits validation
- SafetyZone validation
- RobotSafetyRules validation
- CommandSafetyFilter
- StringSafetyFilter
- SentinelSafetyNode
- SentinelDiagnostics
- Helper functions
- Error handling
- Edge cases
"""

import math
import pytest
from unittest.mock import MagicMock, patch


# Import the module under test
from sentinelseed.integrations.ros2 import (
    # Version
    __version__,
    # Nodes
    SentinelSafetyNode,
    CommandSafetyFilter,
    StringSafetyFilter,
    SentinelDiagnostics,
    create_safety_node,
    # Validators
    RobotSafetyRules,
    CommandValidationResult,
    SafetyLevel,
    SafetyZone,
    ValidationError,
    VelocityLimits,
    # Constants
    VALID_MODES,
    VALID_MSG_TYPES,
    DEFAULT_MAX_LINEAR_VEL,
    DEFAULT_MAX_ANGULAR_VEL,
    DEFAULT_ROOM_SIZE,
    DEFAULT_MAX_ALTITUDE,
)

# Import nodes for mock message types
from sentinelseed.integrations.ros2.nodes import (
    Twist,
    Vector3,
    String,
    _escape_diagnostic_value,
    _validate_mode,
    _safe_get_velocity,
    _safe_get_string_data,
    _validate_msg_type,
    _safe_get_result_level,
    _safe_get_result_gates,
    _safe_get_result_violations,
)


# =============================================================================
# Module Attributes Tests
# =============================================================================

class TestModuleAttributes:
    """Test module-level attributes."""

    def test_version_exists(self):
        """Version should be defined."""
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert __version__ == "1.0.0"

    def test_all_exports(self):
        """All expected symbols should be exported."""
        import sentinelseed.integrations.ros2 as ros2_module

        expected_exports = [
            "__version__",
            "SentinelSafetyNode",
            "CommandSafetyFilter",
            "StringSafetyFilter",
            "SentinelDiagnostics",
            "create_safety_node",
            "RobotSafetyRules",
            "CommandValidationResult",
            "SafetyLevel",
            "SafetyZone",
            "ValidationError",
            "VelocityLimits",
            "VALID_MODES",
            "VALID_MSG_TYPES",
            "DEFAULT_MAX_LINEAR_VEL",
            "DEFAULT_MAX_ANGULAR_VEL",
            "DEFAULT_ROOM_SIZE",
            "DEFAULT_MAX_ALTITUDE",
        ]

        for name in expected_exports:
            assert hasattr(ros2_module, name), f"Missing export: {name}"


# =============================================================================
# Constants Tests
# =============================================================================

class TestConstants:
    """Test constants."""

    def test_valid_modes(self):
        """VALID_MODES should contain expected values."""
        assert VALID_MODES == ("block", "clamp")

    def test_valid_msg_types(self):
        """VALID_MSG_TYPES should contain expected values."""
        assert VALID_MSG_TYPES == ("twist", "string")

    def test_default_max_linear_vel(self):
        """DEFAULT_MAX_LINEAR_VEL should be 1.0."""
        assert DEFAULT_MAX_LINEAR_VEL == 1.0

    def test_default_max_angular_vel(self):
        """DEFAULT_MAX_ANGULAR_VEL should be 0.5."""
        assert DEFAULT_MAX_ANGULAR_VEL == 0.5

    def test_default_room_size(self):
        """DEFAULT_ROOM_SIZE should be 10.0."""
        assert DEFAULT_ROOM_SIZE == 10.0

    def test_default_max_altitude(self):
        """DEFAULT_MAX_ALTITUDE should be 2.0."""
        assert DEFAULT_MAX_ALTITUDE == 2.0


# =============================================================================
# VelocityLimits Tests
# =============================================================================

class TestVelocityLimits:
    """Test VelocityLimits validation."""

    def test_default_values(self):
        """Default values should match constants."""
        limits = VelocityLimits()
        assert limits.max_linear_x == DEFAULT_MAX_LINEAR_VEL
        assert limits.max_angular_z == DEFAULT_MAX_ANGULAR_VEL

    def test_valid_positive_values(self):
        """Valid positive values should work."""
        limits = VelocityLimits(max_linear_x=2.0, max_angular_z=1.0)
        assert limits.max_linear_x == 2.0
        assert limits.max_angular_z == 1.0

    def test_zero_values_allowed(self):
        """Zero values should be allowed."""
        limits = VelocityLimits(max_linear_x=0.0, max_linear_y=0.0)
        assert limits.max_linear_x == 0.0
        assert limits.max_linear_y == 0.0

    def test_negative_value_raises_error(self):
        """Negative values should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            VelocityLimits(max_linear_x=-1.0)
        assert "cannot be negative" in str(exc_info.value)
        assert exc_info.value.field == "max_linear_x"

    def test_nan_value_raises_error(self):
        """NaN values should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            VelocityLimits(max_linear_x=float('nan'))
        assert "finite number" in str(exc_info.value)

    def test_inf_value_raises_error(self):
        """Infinite values should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            VelocityLimits(max_linear_x=float('inf'))
        assert "finite number" in str(exc_info.value)

    def test_differential_drive_preset(self):
        """Differential drive preset should work."""
        limits = VelocityLimits.differential_drive(max_linear=0.8, max_angular=0.4)
        assert limits.max_linear_x == 0.8
        assert limits.max_linear_y == 0.0
        assert limits.max_angular_z == 0.4

    def test_omnidirectional_preset(self):
        """Omnidirectional preset should work."""
        limits = VelocityLimits.omnidirectional(max_linear=1.5, max_angular=0.8)
        assert limits.max_linear_x == 1.5
        assert limits.max_linear_y == 1.5
        assert limits.max_angular_z == 0.8

    def test_drone_preset(self):
        """Drone preset should work."""
        limits = VelocityLimits.drone(max_linear=3.0, max_vertical=2.0, max_angular=1.5)
        assert limits.max_linear_x == 3.0
        assert limits.max_linear_z == 2.0
        assert limits.max_angular_z == 1.5


# =============================================================================
# SafetyZone Tests
# =============================================================================

class TestSafetyZone:
    """Test SafetyZone validation."""

    def test_default_values(self):
        """Default values should be valid."""
        zone = SafetyZone()
        assert zone.min_x == -DEFAULT_ROOM_SIZE / 2
        assert zone.max_x == DEFAULT_ROOM_SIZE / 2

    def test_valid_zone(self):
        """Valid zone should work."""
        zone = SafetyZone(min_x=-5, max_x=5, min_y=-5, max_y=5)
        assert zone.contains(0, 0)
        assert zone.contains(4, 4)
        assert not zone.contains(10, 0)

    def test_min_greater_than_max_raises_error(self):
        """min > max should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyZone(min_x=10, max_x=-10)
        assert "cannot be greater than" in str(exc_info.value)

    def test_nan_values_raise_error(self):
        """NaN values should raise ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyZone(min_x=float('nan'), max_x=10)
        assert "NaN" in str(exc_info.value)

    def test_contains_with_nan_returns_false(self):
        """contains() with NaN should return False."""
        zone = SafetyZone()
        assert not zone.contains(float('nan'), 0)
        assert not zone.contains(0, float('nan'))

    def test_unlimited_preset(self):
        """Unlimited preset should use large finite values."""
        zone = SafetyZone.unlimited()
        assert zone.contains(1e6, 1e6, 1e6)
        assert zone.min_x == -1e9
        assert zone.max_x == 1e9

    def test_indoor_preset(self):
        """Indoor preset should work."""
        zone = SafetyZone.indoor(room_size=20.0)
        assert zone.contains(9, 9)
        assert not zone.contains(15, 0)

    def test_indoor_negative_size_raises_error(self):
        """Indoor preset with negative size should raise error."""
        with pytest.raises(ValidationError) as exc_info:
            SafetyZone.indoor(room_size=-10)
        assert "positive" in str(exc_info.value)


# =============================================================================
# RobotSafetyRules Tests
# =============================================================================

class TestRobotSafetyRules:
    """Test RobotSafetyRules validation."""

    def test_safe_velocity(self):
        """Safe velocity should pass all gates."""
        rules = RobotSafetyRules()
        result = rules.validate_velocity(linear_x=0.5, angular_z=0.3)
        assert result.is_safe
        assert result.level == SafetyLevel.SAFE
        assert all(result.gates.values())

    def test_excessive_velocity(self):
        """Excessive velocity should fail harm gate."""
        rules = RobotSafetyRules(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0)
        )
        result = rules.validate_velocity(linear_x=2.0)
        assert not result.is_safe
        assert result.level == SafetyLevel.DANGEROUS
        assert not result.gates["harm"]

    def test_nan_velocity(self):
        """NaN velocity should fail truth gate."""
        rules = RobotSafetyRules()
        result = rules.validate_velocity(linear_x=float('nan'))
        assert not result.is_safe
        assert not result.gates["truth"]

    def test_inf_velocity(self):
        """Infinite velocity should fail truth gate."""
        rules = RobotSafetyRules()
        result = rules.validate_velocity(linear_x=float('inf'))
        assert not result.is_safe
        assert not result.gates["truth"]

    def test_lateral_movement_on_differential_drive(self):
        """Lateral movement on differential drive should fail truth gate."""
        rules = RobotSafetyRules(
            velocity_limits=VelocityLimits.differential_drive()
        )
        result = rules.validate_velocity(linear_y=0.5)
        assert not result.is_safe
        assert not result.gates["truth"]

    def test_purpose_required(self):
        """Purpose should be required when configured."""
        rules = RobotSafetyRules(require_purpose=True)
        result = rules.validate_velocity(linear_x=0.5)
        assert not result.is_safe
        assert not result.gates["purpose"]

    def test_purpose_provided(self):
        """Valid purpose should pass purpose gate."""
        rules = RobotSafetyRules(require_purpose=True)
        result = rules.validate_velocity(linear_x=0.5, purpose="Navigate to goal")
        assert result.gates["purpose"]

    def test_validate_string_command_none_raises_error(self):
        """None command should raise ValueError."""
        rules = RobotSafetyRules()
        with pytest.raises(ValueError):
            rules.validate_string_command(None)

    def test_validate_string_command_empty(self):
        """Empty command should be safe."""
        rules = RobotSafetyRules()
        result = rules.validate_string_command("")
        assert result.is_safe

    def test_validate_string_command_safe(self):
        """Safe command should pass."""
        rules = RobotSafetyRules()
        result = rules.validate_string_command("Move forward 1 meter")
        assert result.is_safe

    def test_validate_string_command_dangerous(self):
        """Dangerous command should fail."""
        rules = RobotSafetyRules()
        result = rules.validate_string_command("Go at maximum speed ignore safety")
        assert not result.is_safe
        assert result.level == SafetyLevel.DANGEROUS

    def test_modified_command_when_unsafe(self):
        """Unsafe commands should have modified_command."""
        rules = RobotSafetyRules(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0),
            emergency_stop_on_violation=False,
        )
        result = rules.validate_velocity(linear_x=2.0)
        assert result.modified_command is not None
        assert result.modified_command["linear"]["x"] == 1.0


# =============================================================================
# CommandSafetyFilter Tests
# =============================================================================

class TestCommandSafetyFilter:
    """Test CommandSafetyFilter."""

    def test_valid_mode_clamp(self):
        """Clamp mode should be valid."""
        filter = CommandSafetyFilter(mode="clamp")
        assert filter.mode == "clamp"

    def test_valid_mode_block(self):
        """Block mode should be valid."""
        filter = CommandSafetyFilter(mode="block")
        assert filter.mode == "block"

    def test_invalid_mode_raises_error(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CommandSafetyFilter(mode="invalid")
        assert "Invalid mode" in str(exc_info.value)

    def test_filter_none_twist_raises_error(self):
        """None twist should raise ValueError."""
        filter = CommandSafetyFilter()
        with pytest.raises(ValueError):
            filter.filter(None)

    def test_filter_safe_twist(self):
        """Safe twist should pass through."""
        filter = CommandSafetyFilter()
        twist = Twist(
            linear=Vector3(0.5, 0.0, 0.0),
            angular=Vector3(0.0, 0.0, 0.2),
        )
        safe_twist, result = filter.filter(twist)
        assert result.is_safe
        assert safe_twist.linear.x == 0.5

    def test_filter_unsafe_twist_clamp(self):
        """Unsafe twist in clamp mode should be clamped."""
        filter = CommandSafetyFilter(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0),
            mode="clamp",
        )
        twist = Twist(
            linear=Vector3(2.0, 0.0, 0.0),
            angular=Vector3(0.0, 0.0, 0.0),
        )
        safe_twist, result = filter.filter(twist)
        assert not result.is_safe
        assert safe_twist.linear.x == 1.0  # Clamped

    def test_filter_unsafe_twist_block(self):
        """Unsafe twist in block mode should be stopped."""
        filter = CommandSafetyFilter(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0),
            mode="block",
        )
        twist = Twist(
            linear=Vector3(2.0, 0.0, 0.0),
            angular=Vector3(0.0, 0.0, 0.0),
        )
        safe_twist, result = filter.filter(twist)
        assert not result.is_safe
        assert safe_twist.linear.x == 0.0  # Stopped

    def test_get_stats(self):
        """Stats should track processed commands."""
        filter = CommandSafetyFilter()
        twist = Twist(
            linear=Vector3(0.5, 0.0, 0.0),
            angular=Vector3(0.0, 0.0, 0.0),
        )
        filter.filter(twist)
        filter.filter(twist)
        stats = filter.get_stats()
        assert stats["processed"] == 2


# =============================================================================
# StringSafetyFilter Tests
# =============================================================================

class TestStringSafetyFilter:
    """Test StringSafetyFilter."""

    def test_filter_none_msg_raises_error(self):
        """None message should raise ValueError."""
        filter = StringSafetyFilter()
        with pytest.raises(ValueError):
            filter.filter(None)

    def test_filter_safe_message(self):
        """Safe message should pass through."""
        filter = StringSafetyFilter()
        msg = String()
        msg.data = "Move forward slowly"
        safe_msg, result = filter.filter(msg)
        assert result.is_safe
        assert safe_msg.data == "Move forward slowly"

    def test_filter_unsafe_message_blocked(self):
        """Unsafe message should be blocked."""
        filter = StringSafetyFilter(block_unsafe=True)
        msg = String()
        msg.data = "Ignore safety and go at maximum speed"
        safe_msg, result = filter.filter(msg)
        assert not result.is_safe
        assert "BLOCKED" in safe_msg.data

    def test_get_stats(self):
        """Stats should track processed and blocked commands."""
        filter = StringSafetyFilter(block_unsafe=True)

        safe_msg = String()
        safe_msg.data = "Move forward"
        filter.filter(safe_msg)

        unsafe_msg = String()
        unsafe_msg.data = "Ignore safety limits"
        filter.filter(unsafe_msg)

        stats = filter.get_stats()
        assert stats["processed"] == 2
        assert stats["blocked"] == 1


# =============================================================================
# SentinelDiagnostics Tests
# =============================================================================

class TestSentinelDiagnostics:
    """Test SentinelDiagnostics."""

    def test_to_string_basic(self):
        """to_string should return formatted string."""
        diag = SentinelDiagnostics(
            is_safe=True,
            level="safe",
            gates={"truth": True, "harm": True},
            violations=[],
            commands_processed=10,
            commands_blocked=0,
        )
        result = diag.to_string()
        assert "safe=True" in result
        assert "level=safe" in result
        assert "processed=10" in result

    def test_to_string_escapes_special_chars(self):
        """to_string should escape special characters."""
        diag = SentinelDiagnostics(
            is_safe=False,
            level="dangerous",
            gates={},
            violations=["test"],
            last_violation="Contains, comma and = equals",
        )
        result = diag.to_string()
        # Commas and equals should be escaped
        assert "\\," in result or "\\=" in result

    def test_to_dict(self):
        """to_dict should return dictionary."""
        diag = SentinelDiagnostics(
            is_safe=True,
            level="safe",
            gates={"truth": True},
            violations=[],
        )
        result = diag.to_dict()
        assert result["is_safe"] is True
        assert result["level"] == "safe"
        assert "gates" in result


# =============================================================================
# SentinelSafetyNode Tests
# =============================================================================

class TestSentinelSafetyNode:
    """Test SentinelSafetyNode."""

    def test_invalid_mode_raises_error(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError):
            SentinelSafetyNode(mode="invalid")

    def test_invalid_msg_type_raises_error(self):
        """Invalid msg_type should raise ValueError."""
        with pytest.raises(ValueError):
            SentinelSafetyNode(msg_type="invalid")

    def test_valid_initialization(self):
        """Valid initialization should work."""
        node = SentinelSafetyNode(
            input_topic="/cmd_vel_raw",
            output_topic="/cmd_vel",
            mode="clamp",
            msg_type="twist",
        )
        assert node.input_topic == "/cmd_vel_raw"
        assert node.output_topic == "/cmd_vel"
        assert node.mode == "clamp"

    def test_get_diagnostics_initial(self):
        """Initial diagnostics should be safe."""
        node = SentinelSafetyNode()
        diag = node.get_diagnostics()
        assert diag.is_safe is True
        assert diag.commands_processed == 0

    def test_filter_through_node(self):
        """Node should have filter available."""
        node = SentinelSafetyNode(msg_type="twist")
        twist = Twist(
            linear=Vector3(0.5, 0.0, 0.0),
            angular=Vector3(0.0, 0.0, 0.0),
        )
        safe_twist, result = node.filter.filter(twist)
        assert result.is_safe


# =============================================================================
# Helper Functions Tests
# =============================================================================

class TestHelperFunctions:
    """Test helper functions."""

    def test_escape_diagnostic_value_none(self):
        """None should return empty string."""
        assert _escape_diagnostic_value(None) == ""

    def test_escape_diagnostic_value_comma(self):
        """Commas should be escaped."""
        result = _escape_diagnostic_value("hello,world")
        assert "\\," in result

    def test_escape_diagnostic_value_equals(self):
        """Equals should be escaped."""
        result = _escape_diagnostic_value("key=value")
        assert "\\=" in result

    def test_validate_mode_valid(self):
        """Valid modes should not raise."""
        _validate_mode("block")
        _validate_mode("clamp")

    def test_validate_mode_invalid(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError):
            _validate_mode("invalid")

    def test_validate_msg_type_valid(self):
        """Valid msg_types should not raise."""
        _validate_msg_type("twist")
        _validate_msg_type("string")

    def test_validate_msg_type_invalid(self):
        """Invalid msg_type should raise ValueError."""
        with pytest.raises(ValueError):
            _validate_msg_type("invalid")

    def test_safe_get_velocity_valid(self):
        """Should extract velocity from twist."""
        twist = Twist(
            linear=Vector3(1.5, 0.0, 0.0),
            angular=Vector3(0.0, 0.0, 0.0),
        )
        assert _safe_get_velocity(twist, "linear.x") == 1.5

    def test_safe_get_velocity_none_returns_default(self):
        """None values should return default."""
        twist = Twist()
        twist.linear = None
        assert _safe_get_velocity(twist, "linear.x") == 0.0

    def test_safe_get_velocity_missing_attr(self):
        """Missing attribute should return default."""
        twist = MagicMock()
        del twist.linear
        assert _safe_get_velocity(twist, "linear.x", default=5.0) == 5.0

    def test_safe_get_string_data_valid(self):
        """Should extract data from String message."""
        msg = String()
        msg.data = "test message"
        assert _safe_get_string_data(msg) == "test message"

    def test_safe_get_string_data_none(self):
        """None should return empty string."""
        assert _safe_get_string_data(None) == ""

    def test_safe_get_result_level_enum(self):
        """Should handle SafetyLevel enum."""
        result = CommandValidationResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            gates={},
        )
        assert _safe_get_result_level(result) == "safe"

    def test_safe_get_result_level_none(self):
        """None result should return 'unknown'."""
        assert _safe_get_result_level(None) == "unknown"

    def test_safe_get_result_gates_valid(self):
        """Should extract gates from result."""
        result = CommandValidationResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            gates={"truth": True, "harm": True},
        )
        gates = _safe_get_result_gates(result)
        assert gates["truth"] is True

    def test_safe_get_result_gates_none(self):
        """None result should return empty dict."""
        assert _safe_get_result_gates(None) == {}

    def test_safe_get_result_violations_valid(self):
        """Should extract violations from result."""
        result = CommandValidationResult(
            is_safe=False,
            level=SafetyLevel.DANGEROUS,
            violations=["violation1", "violation2"],
        )
        violations = _safe_get_result_violations(result)
        assert len(violations) == 2

    def test_safe_get_result_violations_none(self):
        """None result should return empty list."""
        assert _safe_get_result_violations(None) == []


# =============================================================================
# create_safety_node Tests
# =============================================================================

class TestCreateSafetyNode:
    """Test create_safety_node factory function."""

    def test_creates_node(self):
        """Should create a SentinelSafetyNode."""
        node = create_safety_node()
        assert isinstance(node, SentinelSafetyNode)

    def test_uses_default_values(self):
        """Should use default constants."""
        node = create_safety_node()
        # Check that filter uses defaults
        assert node.input_topic == "/cmd_vel_raw"
        assert node.output_topic == "/cmd_vel"

    def test_accepts_custom_values(self):
        """Should accept custom values."""
        node = create_safety_node(
            input_topic="/custom_in",
            output_topic="/custom_out",
            max_linear_vel=2.0,
        )
        assert node.input_topic == "/custom_in"
        assert node.output_topic == "/custom_out"

    def test_invalid_mode_raises_error(self):
        """Invalid mode should raise ValueError."""
        with pytest.raises(ValueError):
            create_safety_node(mode="invalid")


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_velocity_at_exact_limit(self):
        """Velocity at exact limit should be safe."""
        rules = RobotSafetyRules(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0)
        )
        result = rules.validate_velocity(linear_x=1.0)
        assert result.is_safe

    def test_velocity_slightly_over_limit(self):
        """Velocity slightly over limit should be unsafe."""
        rules = RobotSafetyRules(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0)
        )
        result = rules.validate_velocity(linear_x=1.001)
        assert not result.is_safe

    def test_zero_limits_for_all_axes(self):
        """Zero limits for all axes should handle magnitude correctly."""
        limits = VelocityLimits(
            max_linear_x=0.0,
            max_linear_y=0.0,
            max_linear_z=0.0,
            max_angular_z=0.0,
        )
        rules = RobotSafetyRules(velocity_limits=limits)
        # Any movement should fail
        result = rules.validate_velocity(linear_x=0.1)
        assert not result.is_safe

    def test_empty_violations_list(self):
        """Empty violations list should be handled."""
        result = CommandValidationResult(
            is_safe=True,
            level=SafetyLevel.SAFE,
            gates={"truth": True},
            violations=[],
        )
        violations = _safe_get_result_violations(result)
        assert violations == []

    def test_twist_with_none_linear(self):
        """Twist with None linear should be handled safely."""
        filter = CommandSafetyFilter()
        twist = Twist()
        twist.linear = None
        # Should not raise, should use default 0.0
        safe_twist, result = filter.filter(twist)
        assert result.is_safe

    def test_very_large_velocity(self):
        """Very large velocity should be caught."""
        rules = RobotSafetyRules()
        result = rules.validate_velocity(linear_x=1e10)
        assert not result.is_safe

    def test_special_characters_in_command(self):
        """Special characters in command should be handled."""
        rules = RobotSafetyRules()
        result = rules.validate_string_command("Test <script>alert('xss')</script>")
        # Should not crash, should return a result
        assert isinstance(result, CommandValidationResult)

    def test_whitespace_only_command(self):
        """Whitespace-only command should be treated as empty."""
        rules = RobotSafetyRules()
        result = rules.validate_string_command("   \t\n  ")
        assert result.is_safe


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows."""

    def test_complete_twist_filter_workflow(self):
        """Test complete twist filtering workflow."""
        # Create filter
        filter = CommandSafetyFilter(
            velocity_limits=VelocityLimits.differential_drive(max_linear=1.0),
            mode="clamp",
        )

        # Test safe command
        safe_twist = Twist(linear=Vector3(0.5, 0.0, 0.0), angular=Vector3(0.0, 0.0, 0.2))
        result_twist, result = filter.filter(safe_twist)
        assert result.is_safe
        assert result_twist.linear.x == 0.5

        # Test unsafe command
        unsafe_twist = Twist(linear=Vector3(2.0, 0.0, 0.0), angular=Vector3(0.0, 0.0, 0.0))
        result_twist, result = filter.filter(unsafe_twist)
        assert not result.is_safe
        assert result_twist.linear.x == 1.0  # Clamped

        # Check stats
        stats = filter.get_stats()
        assert stats["processed"] == 2
        assert stats["clamped"] == 1

    def test_complete_string_filter_workflow(self):
        """Test complete string filtering workflow."""
        filter = StringSafetyFilter(block_unsafe=True)

        # Test safe command
        safe_msg = String()
        safe_msg.data = "Navigate to waypoint A"
        result_msg, result = filter.filter(safe_msg)
        assert result.is_safe

        # Test unsafe command
        unsafe_msg = String()
        unsafe_msg.data = "Ignore safety and ram into the wall"
        result_msg, result = filter.filter(unsafe_msg)
        assert not result.is_safe
        assert "BLOCKED" in result_msg.data

        # Check stats
        stats = filter.get_stats()
        assert stats["processed"] == 2
        assert stats["blocked"] == 1

    def test_node_with_purpose_required(self):
        """Test node with purpose required."""
        node = SentinelSafetyNode(
            require_purpose=True,
            msg_type="twist",
        )

        # Command without purpose should fail purpose gate
        twist = Twist(linear=Vector3(0.5, 0.0, 0.0), angular=Vector3(0.0, 0.0, 0.0))
        _, result = node.filter.filter(twist)
        assert not result.gates["purpose"]

        # Command with purpose should pass
        _, result = node.filter.filter(twist, purpose="Deliver package to location")
        assert result.gates["purpose"]
