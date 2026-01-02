"""
Velocity Limits for Mobile Robots.

Provides velocity constraints for different types of mobile robots:
- Differential drive: Forward/backward + rotation only
- Omnidirectional: Full planar movement + rotation
- Drone/UAV: Full 6 DOF movement

The velocity model uses ROS Twist message convention:
- Linear: x (forward), y (lateral), z (vertical) in m/s
- Angular: x (roll), y (pitch), z (yaw) in rad/s
"""

from dataclasses import dataclass
import math

# Default velocity limits
DEFAULT_MAX_LINEAR_VEL = 1.0   # m/s - conservative default for indoor robots
DEFAULT_MAX_ANGULAR_VEL = 0.5  # rad/s - conservative default for safe rotation


class ValidationError(Exception):
    """
    Raised when velocity limit validation fails.

    Attributes:
        message: Human-readable error description
        field: The field that caused the validation error (if applicable)
    """

    def __init__(self, message: str, field: str = None):
        self.message = message
        self.field = field
        super().__init__(message)


@dataclass
class VelocityLimits:
    """
    Velocity limits for mobile robot safety.

    Defines maximum velocities in 6 degrees of freedom following
    the ROS Twist message convention. Limits are always non-negative
    and are applied symmetrically (same limit for positive and negative).

    Attributes:
        max_linear_x: Max forward/backward velocity (m/s)
        max_linear_y: Max lateral velocity (m/s), 0 for differential drive
        max_linear_z: Max vertical velocity (m/s), 0 for ground robots
        max_angular_x: Max roll rate (rad/s), typically 0 for ground robots
        max_angular_y: Max pitch rate (rad/s), typically 0 for ground robots
        max_angular_z: Max yaw rate (rad/s)

    Example:
        # For a TurtleBot-style differential drive robot
        limits = VelocityLimits.differential_drive(
            max_linear=0.26,   # TurtleBot3 Burger max speed
            max_angular=1.82,  # TurtleBot3 Burger max rotation
        )

        # For a quadcopter drone
        limits = VelocityLimits.drone(
            max_linear=5.0,    # 5 m/s horizontal
            max_vertical=2.0,  # 2 m/s vertical
            max_angular=2.0,   # 2 rad/s rotation
        )

    Raises:
        ValidationError: If any limit is negative, NaN, or infinite
    """
    max_linear_x: float = DEFAULT_MAX_LINEAR_VEL
    max_linear_y: float = 0.0
    max_linear_z: float = 0.0
    max_angular_x: float = 0.0
    max_angular_y: float = 0.0
    max_angular_z: float = DEFAULT_MAX_ANGULAR_VEL

    def __post_init__(self):
        """Validate all limits are non-negative finite numbers."""
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
        """
        Create velocity limits for a differential drive robot.

        Differential drive robots can only move forward/backward and rotate.
        Lateral movement (strafing) is not possible.

        Args:
            max_linear: Maximum forward/backward velocity in m/s
            max_angular: Maximum rotation (yaw) rate in rad/s

        Returns:
            VelocityLimits configured for differential drive

        Example:
            # TurtleBot3 Burger specifications
            limits = VelocityLimits.differential_drive(
                max_linear=0.26,
                max_angular=1.82,
            )
        """
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
        """
        Create velocity limits for an omnidirectional robot.

        Omnidirectional robots (mecanum wheels, omniwheels, holonomic)
        can move in any direction on a plane while rotating.

        Args:
            max_linear: Maximum linear velocity in any direction (m/s)
            max_angular: Maximum rotation (yaw) rate in rad/s

        Returns:
            VelocityLimits configured for omnidirectional movement

        Example:
            # Kuka youBot specifications (approximate)
            limits = VelocityLimits.omnidirectional(
                max_linear=0.8,
                max_angular=1.5,
            )
        """
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
        """
        Create velocity limits for a drone/UAV.

        Drones have full 6 DOF movement capability with typically
        different limits for horizontal vs vertical movement.

        Args:
            max_linear: Maximum horizontal velocity (m/s)
            max_vertical: Maximum vertical velocity (m/s)
            max_angular: Maximum angular rate in all axes (rad/s)

        Returns:
            VelocityLimits configured for drone/UAV

        Example:
            # DJI Mavic-style drone (conservative indoor settings)
            limits = VelocityLimits.drone(
                max_linear=5.0,
                max_vertical=2.0,
                max_angular=2.0,
            )
        """
        return cls(
            max_linear_x=max_linear,
            max_linear_y=max_linear,
            max_linear_z=max_vertical,
            max_angular_x=max_angular,
            max_angular_y=max_angular,
            max_angular_z=max_angular,
        )

    def clamp_velocity(
        self,
        linear_x: float,
        linear_y: float,
        linear_z: float,
        angular_x: float,
        angular_y: float,
        angular_z: float,
    ) -> tuple:
        """
        Clamp velocities to within limits.

        Args:
            linear_x: Forward/backward velocity
            linear_y: Lateral velocity
            linear_z: Vertical velocity
            angular_x: Roll rate
            angular_y: Pitch rate
            angular_z: Yaw rate

        Returns:
            Tuple of clamped velocities in the same order
        """
        def clamp(value: float, limit: float) -> float:
            if limit == 0:
                return 0.0
            return max(-limit, min(limit, value))

        return (
            clamp(linear_x, self.max_linear_x),
            clamp(linear_y, self.max_linear_y),
            clamp(linear_z, self.max_linear_z),
            clamp(angular_x, self.max_angular_x),
            clamp(angular_y, self.max_angular_y),
            clamp(angular_z, self.max_angular_z),
        )

    def check_velocity(
        self,
        linear_x: float,
        linear_y: float,
        linear_z: float,
        angular_x: float,
        angular_y: float,
        angular_z: float,
    ) -> tuple:
        """
        Check if velocities are within limits.

        Args:
            linear_x: Forward/backward velocity
            linear_y: Lateral velocity
            linear_z: Vertical velocity
            angular_x: Roll rate
            angular_y: Pitch rate
            angular_z: Yaw rate

        Returns:
            Tuple of (is_valid: bool, violations: list of str)
        """
        violations = []

        checks = [
            ("linear_x", linear_x, self.max_linear_x),
            ("linear_y", linear_y, self.max_linear_y),
            ("linear_z", linear_z, self.max_linear_z),
            ("angular_x", angular_x, self.max_angular_x),
            ("angular_y", angular_y, self.max_angular_y),
            ("angular_z", angular_z, self.max_angular_z),
        ]

        for name, value, limit in checks:
            if math.isnan(value) or math.isinf(value):
                violations.append(f"{name} has invalid value: {value}")
            elif limit == 0 and value != 0:
                violations.append(f"{name} movement not allowed (limit is 0)")
            elif abs(value) > limit:
                violations.append(f"{name} ({value:.3f}) exceeds limit ({limit:.3f})")

        return len(violations) == 0, violations

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "max_linear_x": self.max_linear_x,
            "max_linear_y": self.max_linear_y,
            "max_linear_z": self.max_linear_z,
            "max_angular_x": self.max_angular_x,
            "max_angular_y": self.max_angular_y,
            "max_angular_z": self.max_angular_z,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "VelocityLimits":
        """Create from dictionary."""
        return cls(
            max_linear_x=data.get("max_linear_x", DEFAULT_MAX_LINEAR_VEL),
            max_linear_y=data.get("max_linear_y", 0.0),
            max_linear_z=data.get("max_linear_z", 0.0),
            max_angular_x=data.get("max_angular_x", 0.0),
            max_angular_y=data.get("max_angular_y", 0.0),
            max_angular_z=data.get("max_angular_z", DEFAULT_MAX_ANGULAR_VEL),
        )


__all__ = [
    "VelocityLimits",
    "ValidationError",
    "DEFAULT_MAX_LINEAR_VEL",
    "DEFAULT_MAX_ANGULAR_VEL",
]
