"""
Humanoid Robot Safety Constraints.

This module provides kinematic and dynamic constraints specific to humanoid robots.
It defines limb configurations, joint limits, velocity limits, and operational
boundaries for safe humanoid operation.

The constraints are designed to work with:
- General bipedal humanoids (28-50+ DOF)
- Specific platforms (Tesla Optimus, Boston Dynamics Atlas, Figure 01/02)
- Both industrial and personal care applications

References:
    - ISO 10218:2025 (industrial robots - now includes humanoids)
    - ISO 13482 (personal care robots)
    - ISO/TS 15066 (collaborative safety - force/power limiting)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
import math

logger = logging.getLogger("sentinelseed.humanoid.constraints")

# Configuration constants
DEFAULT_CONTACT_TIME = 0.1  # seconds
MIN_CONTACT_TIME = 0.01  # seconds (minimum for force calculation)


class HumanoidLimb(str, Enum):
    """Limbs of a humanoid robot."""
    HEAD = "head"
    TORSO = "torso"
    LEFT_ARM = "left_arm"
    RIGHT_ARM = "right_arm"
    LEFT_HAND = "left_hand"
    RIGHT_HAND = "right_hand"
    LEFT_LEG = "left_leg"
    RIGHT_LEG = "right_leg"
    LEFT_FOOT = "left_foot"
    RIGHT_FOOT = "right_foot"


class JointType(str, Enum):
    """Types of joints in a humanoid."""
    REVOLUTE = "revolute"    # Rotational joint (most common)
    PRISMATIC = "prismatic"  # Linear joint (some grippers)
    SPHERICAL = "spherical"  # Ball joint (simplified shoulder/hip)
    FIXED = "fixed"          # No motion


@dataclass
class JointSpec:
    """
    Specification for a single joint.

    Attributes:
        name: Joint identifier
        joint_type: Type of joint (revolute, prismatic, etc.)
        limb: Which limb this joint belongs to
        position_min: Minimum position (rad for revolute, m for prismatic)
        position_max: Maximum position
        velocity_max: Maximum velocity (rad/s or m/s)
        acceleration_max: Maximum acceleration
        torque_max: Maximum torque/force (Nm or N)
        is_safety_critical: Whether this joint is safety-critical
    """
    name: str
    joint_type: JointType
    limb: HumanoidLimb
    position_min: float
    position_max: float
    velocity_max: float
    acceleration_max: float = 10.0
    torque_max: float = 100.0
    is_safety_critical: bool = False

    def is_position_valid(self, position: float) -> bool:
        """Check if position is within limits."""
        return self.position_min <= position <= self.position_max

    def is_velocity_valid(self, velocity: float) -> bool:
        """Check if velocity is within limits."""
        return abs(velocity) <= self.velocity_max

    def clamp_position(self, position: float) -> float:
        """Clamp position to valid range."""
        return max(self.position_min, min(self.position_max, position))

    def clamp_velocity(self, velocity: float) -> float:
        """Clamp velocity to valid range."""
        return max(-self.velocity_max, min(self.velocity_max, velocity))


@dataclass
class LimbSpec:
    """
    Specification for a humanoid limb.

    Attributes:
        limb: Limb identifier
        joints: List of joints in this limb
        mass: Total mass of the limb (kg)
        length: Approximate length of the limb (m)
        max_reach: Maximum reach from base (m)
        end_effector_mass: Mass of the end effector (hand/foot) (kg)
    """
    limb: HumanoidLimb
    joints: List[JointSpec] = field(default_factory=list)
    mass: float = 5.0
    length: float = 0.5
    max_reach: float = 0.7
    end_effector_mass: float = 0.5

    @property
    def num_dof(self) -> int:
        """Number of degrees of freedom in this limb."""
        return len([j for j in self.joints if j.joint_type != JointType.FIXED])

    def get_joint(self, name: str) -> Optional[JointSpec]:
        """Get a joint by name."""
        for joint in self.joints:
            if joint.name == name:
                return joint
        return None


@dataclass
class OperationalLimits:
    """
    Operational limits for the entire humanoid.

    Based on ISO 10218:2025 and ISO 13482 requirements.

    Attributes:
        max_walking_speed: Maximum walking speed (m/s)
        max_running_speed: Maximum running speed (m/s) - if capable
        max_arm_speed: Maximum end-effector speed for arms (m/s)
        max_contact_force: Maximum allowed contact force with humans (N)
        max_payload: Maximum payload capacity (kg)
        min_stability_margin: Minimum stability margin (m)
        emergency_stop_time: Maximum time to full stop (s)
        max_operating_height: Maximum height during operation (m)
    """
    max_walking_speed: float = 1.5     # m/s (~5.4 km/h)
    max_running_speed: float = 3.0     # m/s (~10.8 km/h)
    max_arm_speed: float = 2.0         # m/s (end effector)
    max_contact_force: float = 50.0    # N (conservative for neck contact)
    max_payload: float = 20.0          # kg
    min_stability_margin: float = 0.05  # m (ZMP margin)
    emergency_stop_time: float = 0.5   # seconds
    max_operating_height: float = 2.0  # m

    @classmethod
    def industrial(cls) -> "OperationalLimits":
        """Limits for industrial environment (ISO 10218)."""
        return cls(
            max_walking_speed=1.0,
            max_running_speed=0.0,  # No running in industrial
            max_arm_speed=1.5,
            max_contact_force=50.0,
            max_payload=20.0,
            min_stability_margin=0.1,
            emergency_stop_time=0.3,
        )

    @classmethod
    def personal_care(cls) -> "OperationalLimits":
        """Limits for personal care environment (ISO 13482)."""
        return cls(
            max_walking_speed=0.8,
            max_running_speed=0.0,
            max_arm_speed=1.0,
            max_contact_force=35.0,  # More conservative
            max_payload=10.0,
            min_stability_margin=0.15,
            emergency_stop_time=0.3,
        )

    @classmethod
    def research(cls) -> "OperationalLimits":
        """Less restrictive limits for research environments."""
        return cls(
            max_walking_speed=2.0,
            max_running_speed=5.0,
            max_arm_speed=3.0,
            max_contact_force=100.0,
            max_payload=30.0,
            min_stability_margin=0.03,
            emergency_stop_time=0.5,
        )


@dataclass
class SafetyZone:
    """
    Spatial safety zone for humanoid operation.

    Attributes:
        name: Zone identifier
        x_min, x_max: X-axis boundaries (m)
        y_min, y_max: Y-axis boundaries (m)
        z_min, z_max: Z-axis boundaries (m)
        max_speed_in_zone: Speed limit within this zone (m/s)
        human_presence_expected: Whether humans may be in this zone
        requires_reduced_speed: Whether speed reduction is required
    """
    name: str = "default"
    x_min: float = -10.0
    x_max: float = 10.0
    y_min: float = -10.0
    y_max: float = 10.0
    z_min: float = 0.0
    z_max: float = 3.0
    max_speed_in_zone: float = 1.0
    human_presence_expected: bool = True
    requires_reduced_speed: bool = False

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if a point is within the zone."""
        return (
            self.x_min <= x <= self.x_max and
            self.y_min <= y <= self.y_max and
            self.z_min <= z <= self.z_max
        )

    @classmethod
    def collaborative_workspace(cls, size: float = 3.0) -> "SafetyZone":
        """Zone where human-robot collaboration occurs."""
        half = size / 2
        return cls(
            name="collaborative",
            x_min=-half, x_max=half,
            y_min=-half, y_max=half,
            z_min=0.0, z_max=2.0,
            max_speed_in_zone=0.5,
            human_presence_expected=True,
            requires_reduced_speed=True,
        )

    @classmethod
    def restricted_zone(cls) -> "SafetyZone":
        """High-speed zone where humans should not enter."""
        return cls(
            name="restricted",
            x_min=-5.0, x_max=5.0,
            y_min=-5.0, y_max=5.0,
            z_min=0.0, z_max=3.0,
            max_speed_in_zone=2.0,
            human_presence_expected=False,
            requires_reduced_speed=False,
        )


@dataclass
class HumanoidConstraints:
    """
    Complete constraint specification for a humanoid robot.

    This is the main configuration object that combines all constraints.

    Attributes:
        name: Robot name/model
        total_dof: Total degrees of freedom
        total_mass: Total robot mass (kg)
        height: Standing height (m)
        limbs: Specification for each limb
        operational_limits: Operational safety limits
        safety_zones: List of defined safety zones
        contact_force_limit: Default contact force limit (N)
        requires_balance_check: Whether balance must be monitored
        allows_running: Whether running gaits are permitted
    """
    name: str
    total_dof: int
    total_mass: float
    height: float
    limbs: Dict[HumanoidLimb, LimbSpec] = field(default_factory=dict)
    operational_limits: OperationalLimits = field(default_factory=OperationalLimits)
    safety_zones: List[SafetyZone] = field(default_factory=list)
    contact_force_limit: float = 50.0
    requires_balance_check: bool = True
    allows_running: bool = False

    def get_limb(self, limb: HumanoidLimb) -> Optional[LimbSpec]:
        """Get specification for a specific limb."""
        return self.limbs.get(limb)

    def get_joint(self, limb: HumanoidLimb, joint_name: str) -> Optional[JointSpec]:
        """Get a specific joint from a limb."""
        limb_spec = self.get_limb(limb)
        if limb_spec:
            return limb_spec.get_joint(joint_name)
        return None

    def get_all_joints(self) -> List[JointSpec]:
        """Get all joints across all limbs."""
        joints = []
        for limb_spec in self.limbs.values():
            joints.extend(limb_spec.joints)
        return joints

    def get_safety_critical_joints(self) -> List[JointSpec]:
        """Get all safety-critical joints."""
        return [j for j in self.get_all_joints() if j.is_safety_critical]

    def is_position_in_safe_zone(self, x: float, y: float, z: float) -> Tuple[bool, Optional[SafetyZone]]:
        """
        Check if a position is within any safety zone.

        Returns:
            Tuple of (is_in_zone, zone) where zone is the matching zone or None
        """
        for zone in self.safety_zones:
            if zone.contains(x, y, z):
                return True, zone
        return False, None

    def get_max_speed_at_position(self, x: float, y: float, z: float) -> float:
        """Get the maximum allowed speed at a given position."""
        in_zone, zone = self.is_position_in_safe_zone(x, y, z)
        if in_zone and zone:
            return zone.max_speed_in_zone
        return self.operational_limits.max_walking_speed

    def check_joint_positions(
        self,
        positions: Dict[str, float],
    ) -> Tuple[bool, List[str]]:
        """
        Check if joint positions are within limits.

        Args:
            positions: Dict mapping joint names to positions

        Returns:
            Tuple of (all_valid, list of violation messages)
        """
        violations = []
        for joint in self.get_all_joints():
            if joint.name in positions:
                pos = positions[joint.name]
                if not joint.is_position_valid(pos):
                    violations.append(
                        f"Joint {joint.name}: position {pos:.3f} outside "
                        f"[{joint.position_min:.3f}, {joint.position_max:.3f}]"
                    )
        return len(violations) == 0, violations

    def check_joint_velocities(
        self,
        velocities: Dict[str, float],
    ) -> Tuple[bool, List[str]]:
        """
        Check if joint velocities are within limits.

        Args:
            velocities: Dict mapping joint names to velocities

        Returns:
            Tuple of (all_valid, list of violation messages)
        """
        violations = []
        for joint in self.get_all_joints():
            if joint.name in velocities:
                vel = velocities[joint.name]
                if not joint.is_velocity_valid(vel):
                    violations.append(
                        f"Joint {joint.name}: velocity {vel:.3f} exceeds "
                        f"limit {joint.velocity_max:.3f}"
                    )
        return len(violations) == 0, violations

    def estimate_end_effector_force(
        self,
        limb: HumanoidLimb,
        velocity: float,
        contact_time: float = DEFAULT_CONTACT_TIME,
    ) -> float:
        """
        Estimate contact force for a limb at given velocity.

        Uses simple F = m*v/t model for impact estimation.

        Args:
            limb: The limb making contact
            velocity: Impact velocity (m/s)
            contact_time: Contact duration (s)

        Returns:
            Estimated force in Newtons

        Raises:
            TypeError: If limb is not a HumanoidLimb
            ValueError: If limb is not found in this robot's configuration
        """
        if not isinstance(limb, HumanoidLimb):
            raise TypeError(
                f"limb must be HumanoidLimb, got {type(limb).__name__}"
            )

        if velocity < 0:
            logger.warning(f"Negative velocity {velocity} provided, using absolute value")
            velocity = abs(velocity)

        if contact_time <= 0:
            raise ValueError(f"contact_time must be positive, got {contact_time}")

        limb_spec = self.get_limb(limb)
        if not limb_spec:
            raise ValueError(
                f"Limb {limb.value} not found in robot configuration. "
                f"Available limbs: {list(self.limbs.keys())}"
            )

        mass = limb_spec.end_effector_mass
        safe_contact_time = max(contact_time, MIN_CONTACT_TIME)
        return (mass * velocity) / safe_contact_time


def create_generic_humanoid(
    name: str = "generic_humanoid",
    total_dof: int = 28,
    total_mass: float = 70.0,
    height: float = 1.7,
) -> HumanoidConstraints:
    """
    Create constraints for a generic humanoid robot.

    This provides a reasonable default configuration that can be customized.

    Args:
        name: Robot name
        total_dof: Total degrees of freedom
        total_mass: Total mass in kg
        height: Standing height in meters

    Returns:
        HumanoidConstraints instance
    """
    # Create limb specifications
    limbs = {}

    # Head (2 DOF - pan/tilt)
    limbs[HumanoidLimb.HEAD] = LimbSpec(
        limb=HumanoidLimb.HEAD,
        joints=[
            JointSpec("head_pan", JointType.REVOLUTE, HumanoidLimb.HEAD,
                     -1.57, 1.57, 2.0, is_safety_critical=True),
            JointSpec("head_tilt", JointType.REVOLUTE, HumanoidLimb.HEAD,
                     -0.5, 0.7, 2.0, is_safety_critical=True),
        ],
        mass=4.0,
        length=0.25,
    )

    # Torso (2 DOF - pitch/yaw)
    limbs[HumanoidLimb.TORSO] = LimbSpec(
        limb=HumanoidLimb.TORSO,
        joints=[
            JointSpec("torso_pitch", JointType.REVOLUTE, HumanoidLimb.TORSO,
                     -0.3, 0.3, 1.0),
            JointSpec("torso_yaw", JointType.REVOLUTE, HumanoidLimb.TORSO,
                     -0.5, 0.5, 1.0),
        ],
        mass=25.0,
        length=0.5,
    )

    # Arms (6 DOF each - shoulder 3, elbow 1, wrist 2)
    for side, limb_id in [("left", HumanoidLimb.LEFT_ARM), ("right", HumanoidLimb.RIGHT_ARM)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(f"{side}_shoulder_pitch", JointType.REVOLUTE, limb_id,
                         -2.09, 2.09, 2.5),
                JointSpec(f"{side}_shoulder_roll", JointType.REVOLUTE, limb_id,
                         -1.57, 0.5, 2.5),
                JointSpec(f"{side}_shoulder_yaw", JointType.REVOLUTE, limb_id,
                         -1.57, 1.57, 2.5),
                JointSpec(f"{side}_elbow", JointType.REVOLUTE, limb_id,
                         -2.27, 0.0, 2.5),
                JointSpec(f"{side}_wrist_pitch", JointType.REVOLUTE, limb_id,
                         -1.0, 1.0, 3.0),
                JointSpec(f"{side}_wrist_roll", JointType.REVOLUTE, limb_id,
                         -1.57, 1.57, 3.0),
            ],
            mass=4.0,
            length=0.6,
            max_reach=0.8,
            end_effector_mass=0.6,
        )

    # Legs (6 DOF each - hip 3, knee 1, ankle 2)
    for side, limb_id in [("left", HumanoidLimb.LEFT_LEG), ("right", HumanoidLimb.RIGHT_LEG)]:
        limbs[limb_id] = LimbSpec(
            limb=limb_id,
            joints=[
                JointSpec(f"{side}_hip_yaw", JointType.REVOLUTE, limb_id,
                         -0.5, 0.5, 2.0, is_safety_critical=True),
                JointSpec(f"{side}_hip_roll", JointType.REVOLUTE, limb_id,
                         -0.5, 0.5, 2.0, is_safety_critical=True),
                JointSpec(f"{side}_hip_pitch", JointType.REVOLUTE, limb_id,
                         -1.57, 0.5, 2.0, is_safety_critical=True),
                JointSpec(f"{side}_knee", JointType.REVOLUTE, limb_id,
                         0.0, 2.6, 2.5, is_safety_critical=True),
                JointSpec(f"{side}_ankle_pitch", JointType.REVOLUTE, limb_id,
                         -0.8, 0.5, 2.0, is_safety_critical=True),
                JointSpec(f"{side}_ankle_roll", JointType.REVOLUTE, limb_id,
                         -0.4, 0.4, 2.0, is_safety_critical=True),
            ],
            mass=12.0,
            length=0.9,
            end_effector_mass=1.0,
        )

    return HumanoidConstraints(
        name=name,
        total_dof=total_dof,
        total_mass=total_mass,
        height=height,
        limbs=limbs,
        operational_limits=OperationalLimits(),
        safety_zones=[SafetyZone.collaborative_workspace()],
    )


__all__ = [
    # Constants
    "DEFAULT_CONTACT_TIME",
    "MIN_CONTACT_TIME",
    # Enums
    "HumanoidLimb",
    "JointType",
    # Data classes
    "JointSpec",
    "LimbSpec",
    "OperationalLimits",
    "SafetyZone",
    # Classes
    "HumanoidConstraints",
    # Functions
    "create_generic_humanoid",
]
