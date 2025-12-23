"""
Robot Safety Validation Rules for ROS2.

This module provides THSP-adapted validation rules for robotic systems.
The rules focus on physical safety, operational limits, and purpose validation.

Classes:
    - VelocityLimits: Linear and angular velocity constraints
    - SafetyZone: Spatial boundaries for safe operation
    - CommandValidationResult: Result of command validation
    - RobotSafetyRules: THSP rules adapted for robotics
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import math
import re


# Validation constants
# Modes:
#   - block: Emergency stop on unsafe command (Cat 0/STO)
#   - clamp: Limit velocity to safe maximum (SLS)
#   - warn: Log violation but pass command unchanged (monitor only)
#   - ramp: Gradual deceleration (SS1) - planned for future version
VALID_MODES = ("block", "clamp", "warn")
VALID_MSG_TYPES = ("twist", "string")
DEFAULT_MAX_LINEAR_VEL = 1.0
DEFAULT_MAX_ANGULAR_VEL = 0.5
DEFAULT_ROOM_SIZE = 10.0
DEFAULT_MAX_ALTITUDE = 2.0


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


class SafetyLevel(Enum):
    """Safety level classification for robot commands."""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


@dataclass
class VelocityLimits:
    """
    Velocity limits for robot safety.

    Attributes:
        max_linear_x: Max forward/backward velocity (m/s)
        max_linear_y: Max lateral velocity (m/s), 0 for differential drive
        max_linear_z: Max vertical velocity (m/s), 0 for ground robots
        max_angular_x: Max roll rate (rad/s)
        max_angular_y: Max pitch rate (rad/s)
        max_angular_z: Max yaw rate (rad/s)

    Raises:
        ValidationError: If any limit is negative
    """
    max_linear_x: float = DEFAULT_MAX_LINEAR_VEL
    max_linear_y: float = 0.0
    max_linear_z: float = 0.0
    max_angular_x: float = 0.0
    max_angular_y: float = 0.0
    max_angular_z: float = DEFAULT_MAX_ANGULAR_VEL

    def __post_init__(self):
        """Validate all limits are non-negative."""
        fields = [
            ("max_linear_x", self.max_linear_x),
            ("max_linear_y", self.max_linear_y),
            ("max_linear_z", self.max_linear_z),
            ("max_angular_x", self.max_angular_x),
            ("max_angular_y", self.max_angular_y),
            ("max_angular_z", self.max_angular_z),
        ]
        for name, value in fields:
            if value < 0:
                raise ValidationError(
                    f"{name} cannot be negative (got {value})",
                    field=name,
                )
            if math.isnan(value) or math.isinf(value):
                raise ValidationError(
                    f"{name} must be a finite number (got {value})",
                    field=name,
                )

    @classmethod
    def differential_drive(
        cls,
        max_linear: float = DEFAULT_MAX_LINEAR_VEL,
        max_angular: float = DEFAULT_MAX_ANGULAR_VEL,
    ) -> "VelocityLimits":
        """Create limits for a differential drive robot."""
        return cls(
            max_linear_x=max_linear,
            max_linear_y=0.0,
            max_linear_z=0.0,
            max_angular_x=0.0,
            max_angular_y=0.0,
            max_angular_z=max_angular,
        )

    @classmethod
    def omnidirectional(
        cls,
        max_linear: float = DEFAULT_MAX_LINEAR_VEL,
        max_angular: float = DEFAULT_MAX_ANGULAR_VEL,
    ) -> "VelocityLimits":
        """Create limits for an omnidirectional robot."""
        return cls(
            max_linear_x=max_linear,
            max_linear_y=max_linear,
            max_linear_z=0.0,
            max_angular_x=0.0,
            max_angular_y=0.0,
            max_angular_z=max_angular,
        )

    @classmethod
    def drone(
        cls,
        max_linear: float = 2.0,
        max_vertical: float = 1.0,
        max_angular: float = 1.0,
    ) -> "VelocityLimits":
        """Create limits for a drone/UAV."""
        return cls(
            max_linear_x=max_linear,
            max_linear_y=max_linear,
            max_linear_z=max_vertical,
            max_angular_x=max_angular,
            max_angular_y=max_angular,
            max_angular_z=max_angular,
        )


@dataclass
class SafetyZone:
    """
    Spatial safety zone for the robot.

    Attributes:
        min_x: Minimum x coordinate (meters)
        max_x: Maximum x coordinate (meters)
        min_y: Minimum y coordinate (meters)
        max_y: Maximum y coordinate (meters)
        min_z: Minimum z coordinate (meters)
        max_z: Maximum z coordinate (meters)

    Raises:
        ValidationError: If min > max for any axis
    """
    min_x: float = -DEFAULT_ROOM_SIZE / 2
    max_x: float = DEFAULT_ROOM_SIZE / 2
    min_y: float = -DEFAULT_ROOM_SIZE / 2
    max_y: float = DEFAULT_ROOM_SIZE / 2
    min_z: float = 0.0
    max_z: float = DEFAULT_MAX_ALTITUDE

    # Flag to skip validation for unlimited zones
    _skip_validation: bool = field(default=False, repr=False)

    def __post_init__(self):
        """Validate min <= max for all axes."""
        if self._skip_validation:
            return

        axes = [
            ("x", self.min_x, self.max_x),
            ("y", self.min_y, self.max_y),
            ("z", self.min_z, self.max_z),
        ]
        for axis, min_val, max_val in axes:
            if math.isnan(min_val) or math.isnan(max_val):
                raise ValidationError(
                    f"{axis} axis contains NaN values",
                    field=f"min_{axis}/max_{axis}",
                )
            if min_val > max_val:
                raise ValidationError(
                    f"min_{axis} ({min_val}) cannot be greater than max_{axis} ({max_val})",
                    field=f"min_{axis}",
                )

    def contains(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a position is within the safety zone."""
        if math.isnan(x) or math.isnan(y) or math.isnan(z):
            return False
        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            self.min_z <= z <= self.max_z
        )

    @classmethod
    def unlimited(cls) -> "SafetyZone":
        """
        Create unlimited safety zone.

        Note: Uses very large finite values instead of inf to avoid
        potential issues with mathematical operations.
        """
        large_val = 1e9  # 1 billion meters
        return cls(
            min_x=-large_val,
            max_x=large_val,
            min_y=-large_val,
            max_y=large_val,
            min_z=-large_val,
            max_z=large_val,
            _skip_validation=False,
        )

    @classmethod
    def indoor(cls, room_size: float = DEFAULT_ROOM_SIZE) -> "SafetyZone":
        """Create indoor safety zone."""
        if room_size <= 0:
            raise ValidationError(
                f"room_size must be positive (got {room_size})",
                field="room_size",
            )
        half = room_size / 2
        return cls(
            min_x=-half, max_x=half,
            min_y=-half, max_y=half,
            min_z=0.0, max_z=3.0,
        )


@dataclass
class CommandValidationResult:
    """
    Result of command validation through THSP gates.

    Attributes:
        is_safe: Whether the command is safe to execute
        level: Safety level classification
        gates: Results of individual THSP gates
        violations: List of violation messages
        modified_command: Command after applying safety limits (if any)
        reasoning: Explanation of the validation result
    """
    is_safe: bool
    level: SafetyLevel
    gates: Dict[str, bool] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    modified_command: Optional[Any] = None
    reasoning: str = ""


class RobotSafetyRules:
    """
    THSP safety rules adapted for robotic systems.

    The four gates are interpreted for robotics:
    - Truth: Command matches actual capability/intent
    - Harm: Command could cause physical harm (collision, injury)
    - Scope: Command is within operational boundaries
    - Purpose: Command serves a legitimate purpose

    Args:
        velocity_limits: Maximum allowed velocities
        safety_zone: Spatial operation boundaries
        require_purpose: Require explicit purpose for high-risk commands
        emergency_stop_on_violation: Stop robot on any violation
    """

    # Patterns suggesting dangerous commands in string messages
    DANGEROUS_COMMAND_PATTERNS = [
        r"(max|full|maximum)\s+speed",
        r"ignore\s+(limits|safety|boundaries)",
        r"disable\s+(safety|limits)",
        r"override\s+(safety|limits)",
        r"force\s+(through|past)",
        r"ram\s+into",
        r"collide\s+with",
    ]

    # Patterns for purpose violations (commands without legitimate purpose)
    PURPOSELESS_PATTERNS = [
        r"spin\s+(forever|continuously|indefinitely)",
        r"drive\s+(randomly|aimlessly)",
        r"waste\s+(power|battery|energy)",
        r"just\s+because",
        r"for\s+no\s+reason",
    ]

    def __init__(
        self,
        velocity_limits: Optional[VelocityLimits] = None,
        safety_zone: Optional[SafetyZone] = None,
        require_purpose: bool = False,
        emergency_stop_on_violation: bool = True,
    ):
        self.velocity_limits = velocity_limits or VelocityLimits()
        self.safety_zone = safety_zone or SafetyZone()
        self.require_purpose = require_purpose
        self.emergency_stop_on_violation = emergency_stop_on_violation

        # Compile patterns
        self._danger_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.DANGEROUS_COMMAND_PATTERNS
        ]
        self._purpose_patterns = [
            re.compile(p, re.IGNORECASE) for p in self.PURPOSELESS_PATTERNS
        ]

    def validate_velocity(
        self,
        linear_x: float = 0.0,
        linear_y: float = 0.0,
        linear_z: float = 0.0,
        angular_x: float = 0.0,
        angular_y: float = 0.0,
        angular_z: float = 0.0,
        purpose: Optional[str] = None,
        current_position: Optional[Tuple[float, float, float]] = None,
    ) -> CommandValidationResult:
        """
        Validate a velocity command through THSP gates.

        Args:
            linear_x: Forward/backward velocity (m/s)
            linear_y: Lateral velocity (m/s)
            linear_z: Vertical velocity (m/s)
            angular_x: Roll rate (rad/s)
            angular_y: Pitch rate (rad/s)
            angular_z: Yaw rate (rad/s)
            purpose: Optional purpose description
            current_position: Optional (x, y, z) tuple of current robot position in meters.
                              If provided, Scope Gate validates position is within safety_zone.

        Returns:
            CommandValidationResult with validation details
        """
        violations = []
        gates = {"truth": True, "harm": True, "scope": True, "purpose": True}

        # Truth Gate: Check if command is within physical capabilities
        truth_violations = self._check_truth_gate(
            linear_x, linear_y, linear_z, angular_x, angular_y, angular_z
        )
        if truth_violations:
            gates["truth"] = False
            violations.extend(truth_violations)

        # Harm Gate: Check for dangerous velocities
        harm_violations = self._check_harm_gate(
            linear_x, linear_y, linear_z, angular_x, angular_y, angular_z
        )
        if harm_violations:
            gates["harm"] = False
            violations.extend(harm_violations)

        # Scope Gate: Check operational boundaries
        scope_violations = self._check_scope_gate(current_position)
        if scope_violations:
            gates["scope"] = False
            violations.extend(scope_violations)

        # Purpose Gate: Check for legitimate purpose
        purpose_violations = self._check_purpose_gate(purpose)
        if purpose_violations:
            gates["purpose"] = False
            violations.extend(purpose_violations)

        is_safe = all(gates.values())

        # Determine safety level
        if is_safe:
            level = SafetyLevel.SAFE
        elif gates["harm"] is False:
            level = SafetyLevel.DANGEROUS
        elif gates["purpose"] is False and self.require_purpose:
            level = SafetyLevel.BLOCKED
        else:
            level = SafetyLevel.WARNING

        # Apply safety limits if violations occurred
        modified = None
        if not is_safe and self.emergency_stop_on_violation and level == SafetyLevel.DANGEROUS:
            # Emergency stop
            modified = {
                "linear": {"x": 0.0, "y": 0.0, "z": 0.0},
                "angular": {"x": 0.0, "y": 0.0, "z": 0.0},
            }
        elif not is_safe:
            # Clamp to limits
            modified = {
                "linear": {
                    "x": self._clamp(linear_x, -self.velocity_limits.max_linear_x, self.velocity_limits.max_linear_x),
                    "y": self._clamp(linear_y, -self.velocity_limits.max_linear_y, self.velocity_limits.max_linear_y),
                    "z": self._clamp(linear_z, -self.velocity_limits.max_linear_z, self.velocity_limits.max_linear_z),
                },
                "angular": {
                    "x": self._clamp(angular_x, -self.velocity_limits.max_angular_x, self.velocity_limits.max_angular_x),
                    "y": self._clamp(angular_y, -self.velocity_limits.max_angular_y, self.velocity_limits.max_angular_y),
                    "z": self._clamp(angular_z, -self.velocity_limits.max_angular_z, self.velocity_limits.max_angular_z),
                },
            }

        reasoning = self._generate_reasoning(violations, level)

        return CommandValidationResult(
            is_safe=is_safe,
            level=level,
            gates=gates,
            violations=violations,
            modified_command=modified,
            reasoning=reasoning,
        )

    def validate_string_command(self, command: str) -> CommandValidationResult:
        """
        Validate a string command through THSP gates.

        This is useful for natural language commands sent to the robot.

        Args:
            command: String command to validate

        Returns:
            CommandValidationResult with validation details

        Raises:
            ValueError: If command is None
        """
        if command is None:
            raise ValueError("command cannot be None")

        violations = []
        gates = {"truth": True, "harm": True, "scope": True, "purpose": True}

        # Handle empty command
        if not command or not command.strip():
            return CommandValidationResult(
                is_safe=True,
                level=SafetyLevel.SAFE,
                gates=gates,
                violations=[],
                reasoning="Empty command - no action required.",
            )

        # Harm Gate: Check for dangerous patterns
        for pattern in self._danger_patterns:
            if pattern.search(command):
                gates["harm"] = False
                violations.append(f"[HARM] Dangerous command pattern: {pattern.pattern}")

        # Purpose Gate: Check for purposeless commands
        for pattern in self._purpose_patterns:
            if pattern.search(command):
                gates["purpose"] = False
                violations.append(f"[PURPOSE] Command lacks legitimate purpose: {pattern.pattern}")

        is_safe = all(gates.values())

        if is_safe:
            level = SafetyLevel.SAFE
        elif gates["harm"] is False:
            level = SafetyLevel.DANGEROUS
        else:
            level = SafetyLevel.WARNING

        reasoning = self._generate_reasoning(violations, level)

        return CommandValidationResult(
            is_safe=is_safe,
            level=level,
            gates=gates,
            violations=violations,
            reasoning=reasoning,
        )

    def _check_truth_gate(
        self,
        linear_x: float,
        linear_y: float,
        linear_z: float,
        angular_x: float,
        angular_y: float,
        angular_z: float,
    ) -> List[str]:
        """Check if command matches robot capabilities (Truth Gate)."""
        violations = []

        # Check for impossible values (NaN, inf)
        values = [linear_x, linear_y, linear_z, angular_x, angular_y, angular_z]
        names = ["linear_x", "linear_y", "linear_z", "angular_x", "angular_y", "angular_z"]

        for name, value in zip(names, values):
            if math.isnan(value):
                violations.append(f"[TRUTH] Invalid NaN value for {name}")
            elif math.isinf(value):
                violations.append(f"[TRUTH] Invalid infinite value for {name}")

        # Check for non-zero values on constrained axes
        if linear_y != 0 and self.velocity_limits.max_linear_y == 0:
            violations.append(f"[TRUTH] Lateral movement requested but robot is differential drive (linear_y={linear_y})")
        if linear_z != 0 and self.velocity_limits.max_linear_z == 0:
            violations.append(f"[TRUTH] Vertical movement requested but robot is ground-based (linear_z={linear_z})")

        return violations

    def _check_harm_gate(
        self,
        linear_x: float,
        linear_y: float,
        linear_z: float,
        angular_x: float,
        angular_y: float,
        angular_z: float,
    ) -> List[str]:
        """Check for potentially harmful velocities (Harm Gate)."""
        violations = []
        limits = self.velocity_limits

        # Check velocity limits (potential for collision/injury)
        # Note: Skip checks where limit is 0 - those are handled by Truth Gate
        # (robot physically can't move in that direction)
        if abs(linear_x) > limits.max_linear_x:
            violations.append(f"[HARM] Excessive forward velocity: {linear_x} > {limits.max_linear_x}")
        if limits.max_linear_y > 0 and abs(linear_y) > limits.max_linear_y:
            violations.append(f"[HARM] Excessive lateral velocity: {linear_y} > {limits.max_linear_y}")
        if limits.max_linear_z > 0 and abs(linear_z) > limits.max_linear_z:
            violations.append(f"[HARM] Excessive vertical velocity: {linear_z} > {limits.max_linear_z}")
        if limits.max_angular_x > 0 and abs(angular_x) > limits.max_angular_x:
            violations.append(f"[HARM] Excessive roll rate: {angular_x} > {limits.max_angular_x}")
        if limits.max_angular_y > 0 and abs(angular_y) > limits.max_angular_y:
            violations.append(f"[HARM] Excessive pitch rate: {angular_y} > {limits.max_angular_y}")
        if abs(angular_z) > limits.max_angular_z:
            violations.append(f"[HARM] Excessive yaw rate: {angular_z} > {limits.max_angular_z}")

        # Check for dangerous velocity combinations
        # Skip NaN/inf values (already caught by truth gate)
        if not any(math.isnan(v) or math.isinf(v) for v in [linear_x, linear_y, linear_z]):
            total_linear = math.sqrt(linear_x**2 + linear_y**2 + linear_z**2)
            max_total_linear = math.sqrt(
                limits.max_linear_x**2 + limits.max_linear_y**2 + limits.max_linear_z**2
            )
            # Only check magnitude if there's a meaningful limit
            if max_total_linear > 0 and total_linear > max_total_linear * 1.1:
                violations.append(f"[HARM] Combined velocity magnitude too high: {total_linear:.2f}")

        return violations

    def _check_scope_gate(
        self, current_position: Optional[Tuple[float, float, float]]
    ) -> List[str]:
        """
        Check operational scope boundaries (Scope Gate).

        Args:
            current_position: Optional (x, y, z) tuple of current robot position.
                              If None, scope validation is skipped (position unknown).

        Returns:
            List of violation messages if position is outside safety zone.
        """
        violations = []

        if current_position is None:
            # Position unknown - cannot validate scope
            # This is acceptable: many robots don't have localization
            return violations

        # Validate position format
        try:
            if not hasattr(current_position, '__iter__') or isinstance(current_position, str):
                violations.append(
                    f"[SCOPE] Invalid position format: expected (x, y, z) tuple, got {type(current_position).__name__}"
                )
                return violations

            pos_list = list(current_position)
            if len(pos_list) != 3:
                violations.append(
                    f"[SCOPE] Invalid position format: expected 3 values (x, y, z), got {len(pos_list)}"
                )
                return violations

            x, y, z = pos_list

            # Validate each coordinate is a number
            for name, val in [("x", x), ("y", y), ("z", z)]:
                if val is None:
                    violations.append(f"[SCOPE] Position {name} is None")
                    return violations
                if not isinstance(val, (int, float)):
                    violations.append(
                        f"[SCOPE] Position {name} must be a number, got {type(val).__name__}"
                    )
                    return violations

            x, y, z = float(x), float(y), float(z)

        except (TypeError, ValueError) as e:
            violations.append(f"[SCOPE] Invalid position: {e}")
            return violations

        # Check for invalid position values (NaN, inf)
        if any(math.isnan(v) or math.isinf(v) for v in (x, y, z)):
            violations.append(f"[SCOPE] Invalid position values: ({x}, {y}, {z})")
            return violations

        # Check if position is within safety zone
        if not self.safety_zone.contains(x, y, z):
            violations.append(
                f"[SCOPE] Position ({x:.2f}, {y:.2f}, {z:.2f}) is outside safety zone "
                f"[x: {self.safety_zone.min_x:.1f} to {self.safety_zone.max_x:.1f}, "
                f"y: {self.safety_zone.min_y:.1f} to {self.safety_zone.max_y:.1f}, "
                f"z: {self.safety_zone.min_z:.1f} to {self.safety_zone.max_z:.1f}]"
            )

        return violations

    def _check_purpose_gate(self, purpose: Optional[str]) -> List[str]:
        """Check for legitimate purpose (Purpose Gate)."""
        violations = []

        if self.require_purpose and not purpose:
            violations.append("[PURPOSE] Command requires explicit purpose but none provided")
        elif purpose:
            # Check for purposeless indicators
            for pattern in self._purpose_patterns:
                if pattern.search(purpose):
                    violations.append(f"[PURPOSE] Purpose lacks legitimacy: {pattern.pattern}")

        return violations

    def _clamp(self, value: float, min_val: float, max_val: float) -> float:
        """Clamp value to range."""
        return max(min_val, min(max_val, value))

    def _generate_reasoning(self, violations: List[str], level: SafetyLevel) -> str:
        """Generate human-readable reasoning."""
        if not violations:
            return "Command passes all THSP safety gates."

        if level == SafetyLevel.DANGEROUS:
            return f"DANGEROUS: {len(violations)} violation(s) detected. {violations[0]}"
        elif level == SafetyLevel.BLOCKED:
            return f"BLOCKED: Command lacks required purpose. {violations[0]}"
        else:
            return f"WARNING: {len(violations)} issue(s) detected. {violations[0]}"
