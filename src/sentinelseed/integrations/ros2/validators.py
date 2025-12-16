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
    """
    max_linear_x: float = 1.0
    max_linear_y: float = 0.0
    max_linear_z: float = 0.0
    max_angular_x: float = 0.0
    max_angular_y: float = 0.0
    max_angular_z: float = 0.5

    @classmethod
    def differential_drive(cls, max_linear: float = 1.0, max_angular: float = 0.5):
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
    def omnidirectional(cls, max_linear: float = 1.0, max_angular: float = 0.5):
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
    def drone(cls, max_linear: float = 2.0, max_vertical: float = 1.0, max_angular: float = 1.0):
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
    """
    min_x: float = -10.0
    max_x: float = 10.0
    min_y: float = -10.0
    max_y: float = 10.0
    min_z: float = 0.0
    max_z: float = 2.0

    def contains(self, x: float, y: float, z: float = 0.0) -> bool:
        """Check if a position is within the safety zone."""
        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            self.min_z <= z <= self.max_z
        )

    @classmethod
    def unlimited(cls):
        """Create unlimited safety zone."""
        return cls(
            min_x=float('-inf'),
            max_x=float('inf'),
            min_y=float('-inf'),
            max_y=float('inf'),
            min_z=float('-inf'),
            max_z=float('inf'),
        )

    @classmethod
    def indoor(cls, room_size: float = 10.0):
        """Create indoor safety zone."""
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
        scope_violations = self._check_scope_gate()
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
        """
        violations = []
        gates = {"truth": True, "harm": True, "scope": True, "purpose": True}

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
        total_linear = math.sqrt(linear_x**2 + linear_y**2 + linear_z**2)
        max_total_linear = math.sqrt(limits.max_linear_x**2 + limits.max_linear_y**2 + limits.max_linear_z**2)
        if total_linear > max_total_linear * 1.1:
            violations.append(f"[HARM] Combined velocity magnitude too high: {total_linear:.2f}")

        return violations

    def _check_scope_gate(self) -> List[str]:
        """Check operational scope boundaries (Scope Gate)."""
        violations = []
        # Position checking would require odometry integration
        # For now, scope gate is placeholder for position validation
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
