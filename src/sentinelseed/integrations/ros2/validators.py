"""
Robot Safety Validation Rules for ROS2.

This module provides THSP-adapted validation rules for robotic systems.
The rules focus on physical safety, operational limits, and purpose validation.

Uses the core THSPValidator for text/command validation, with additional
robotics-specific physical safety checks layered on top.

Architecture:
    This module uses the centralized safety classes from:
    - sentinelseed.safety.base: SafetyLevel
    - sentinelseed.safety.mobile: VelocityLimits, SafetyZone, ValidationError

Classes:
    - VelocityLimits: Linear and angular velocity constraints (from safety.mobile)
    - SafetyZone: Spatial boundaries for safe operation (from safety.mobile)
    - CommandValidationResult: Result of command validation
    - RobotSafetyRules: THSP rules adapted for robotics
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import logging
import math
import re

logger = logging.getLogger("sentinelseed.integrations.ros2.validators")

# Import centralized safety classes
from sentinelseed.safety.base import SafetyLevel
from sentinelseed.safety.mobile import (
    VelocityLimits,
    SafetyZone,
    ValidationError,
    DEFAULT_MAX_LINEAR_VEL,
    DEFAULT_MAX_ANGULAR_VEL,
    DEFAULT_ROOM_SIZE,
    DEFAULT_MAX_ALTITUDE,
)

# Import LayeredValidator for text validation (replaces direct THSPValidator usage)
try:
    from sentinelseed.validation import (
        LayeredValidator,
        ValidationConfig,
        ValidationResult as ValResult,
        ValidationLayer,
    )
    LAYERED_VALIDATOR_AVAILABLE = True
except (ImportError, AttributeError):
    LayeredValidator = None
    ValidationConfig = None
    LAYERED_VALIDATOR_AVAILABLE = False


# Validation constants
# Modes:
#   - block: Emergency stop on unsafe command (Cat 0/STO)
#   - clamp: Limit velocity to safe maximum (SLS)
#   - warn: Log violation but pass command unchanged (monitor only)
#   - ramp: Gradual deceleration (SS1) - planned for future version
VALID_MODES = ("block", "clamp", "warn")
VALID_MSG_TYPES = ("twist", "string")


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
        validator: Optional["LayeredValidator"] = None,
    ):
        self.velocity_limits = velocity_limits or VelocityLimits()
        self.safety_zone = safety_zone or SafetyZone()
        self.require_purpose = require_purpose
        self.emergency_stop_on_violation = emergency_stop_on_violation

        # Initialize LayeredValidator for text/command validation
        self._validator = validator
        if self._validator is None and LAYERED_VALIDATOR_AVAILABLE and LayeredValidator is not None:
            try:
                config = ValidationConfig(
                    use_heuristic=True,
                    use_semantic=False,  # ROS2 nodes typically need fast validation
                )
                self._validator = LayeredValidator(config=config)
            except (ImportError, RuntimeError) as e:
                logger.debug(f"Text validator not available, using local patterns only: {e}")

        # Compile robotics-specific patterns (used in addition to core)
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

        Uses the core THSPValidator for comprehensive text validation (jailbreaks,
        prompt injection, harmful content, etc.), plus robotics-specific patterns.

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

        # Step 1: Use LayeredValidator for comprehensive text validation
        # This catches jailbreaks, prompt injection, SQL injection, XSS, etc.
        if self._validator is not None:
            try:
                val_result = self._validator.validate(command)
                if not val_result.is_safe:
                    # Map violations to gates - if any violation, mark harm gate as failed
                    gates["harm"] = False
                    violations.extend(val_result.violations)
            except (RuntimeError, ValueError) as e:
                logger.warning(f"Text validation failed, using robotics patterns only: {e}")

        # Step 2: Apply robotics-specific patterns (additional checks)
        # Harm Gate: Check for dangerous robot-specific patterns
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
