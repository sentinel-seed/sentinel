"""
Robot Safety Constraints for Simulation Environments.

Provides dataclasses for defining physical constraints and safety limits
for robotic systems in simulation environments. These constraints are
designed for use with RL training and can handle both single and batch
validation efficiently.

The constraints support:
- PyTorch tensors (GPU-accelerated)
- NumPy arrays
- Python lists
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import math

# Try to import torch for tensor operations
try:
    import torch
    TORCH_AVAILABLE = True
except (ImportError, AttributeError):
    TORCH_AVAILABLE = False
    torch = None

# Try to import numpy as fallback
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except (ImportError, AttributeError):
    NUMPY_AVAILABLE = False
    np = None


class ConstraintViolationType(Enum):
    """
    Types of constraint violations in simulation.

    Maps to physical constraint types for reporting and handling.
    """
    NONE = "none"
    JOINT_POSITION = "joint_position"
    JOINT_VELOCITY = "joint_velocity"
    WORKSPACE = "workspace"
    FORCE = "force"
    TORQUE = "torque"
    COLLISION = "collision"
    INVALID_VALUE = "invalid_value"


@dataclass
class JointLimits:
    """
    Joint position and velocity limits for a robot.

    Defines the safe operating range for each joint. Values can be provided
    as lists (one per joint) or as single values (applied to all joints).

    Attributes:
        num_joints: Number of joints in the robot
        position_lower: Lower position limits (rad or m) per joint
        position_upper: Upper position limits (rad or m) per joint
        velocity_max: Maximum velocity (rad/s or m/s) per joint
        acceleration_max: Maximum acceleration per joint (optional)
        effort_max: Maximum effort/torque per joint (optional)

    Example:
        # Franka Panda (7 DOF)
        limits = JointLimits.franka_panda()

        # Custom robot with 6 joints
        limits = JointLimits(
            num_joints=6,
            position_lower=[-3.14] * 6,
            position_upper=[3.14] * 6,
            velocity_max=[2.0] * 6,
        )

        # Check positions
        is_valid, violations = limits.check_position([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    """
    num_joints: int
    position_lower: List[float] = field(default_factory=list)
    position_upper: List[float] = field(default_factory=list)
    velocity_max: List[float] = field(default_factory=list)
    acceleration_max: Optional[List[float]] = None
    effort_max: Optional[List[float]] = None

    def __post_init__(self):
        """Validate and normalize limits after initialization."""
        if self.num_joints < 1:
            raise ValueError(f"num_joints must be >= 1, got {self.num_joints}")

        # Expand single values to per-joint lists
        if len(self.position_lower) == 1:
            self.position_lower = self.position_lower * self.num_joints
        if len(self.position_upper) == 1:
            self.position_upper = self.position_upper * self.num_joints
        if len(self.velocity_max) == 1:
            self.velocity_max = self.velocity_max * self.num_joints

        # Set defaults if empty
        if not self.position_lower:
            self.position_lower = [-math.pi] * self.num_joints
        if not self.position_upper:
            self.position_upper = [math.pi] * self.num_joints
        if not self.velocity_max:
            self.velocity_max = [2.0] * self.num_joints

        # Validate lengths
        if len(self.position_lower) != self.num_joints:
            raise ValueError(
                f"position_lower length ({len(self.position_lower)}) "
                f"must match num_joints ({self.num_joints})"
            )
        if len(self.position_upper) != self.num_joints:
            raise ValueError(
                f"position_upper length ({len(self.position_upper)}) "
                f"must match num_joints ({self.num_joints})"
            )
        if len(self.velocity_max) != self.num_joints:
            raise ValueError(
                f"velocity_max length ({len(self.velocity_max)}) "
                f"must match num_joints ({self.num_joints})"
            )

    def check_position(self, positions: Union[List[float], Any]) -> Tuple[bool, List[str]]:
        """
        Check if joint positions are within limits.

        Args:
            positions: Joint positions to check (list, numpy array, or torch tensor)

        Returns:
            Tuple of (is_valid, list of violation messages)
        """
        violations = []
        pos_list = self._to_list(positions)

        for i, pos in enumerate(pos_list):
            if math.isnan(pos) or math.isinf(pos):
                violations.append(f"Joint {i}: Invalid value {pos}")
            elif pos < self.position_lower[i]:
                violations.append(
                    f"Joint {i}: Position {pos:.3f} < lower limit {self.position_lower[i]:.3f}"
                )
            elif pos > self.position_upper[i]:
                violations.append(
                    f"Joint {i}: Position {pos:.3f} > upper limit {self.position_upper[i]:.3f}"
                )

        return len(violations) == 0, violations

    def check_velocity(self, velocities: Union[List[float], Any]) -> Tuple[bool, List[str]]:
        """
        Check if joint velocities are within limits.

        Args:
            velocities: Joint velocities to check (list, numpy array, or torch tensor)

        Returns:
            Tuple of (is_valid, list of violation messages)
        """
        violations = []
        vel_list = self._to_list(velocities)

        for i, vel in enumerate(vel_list):
            if math.isnan(vel) or math.isinf(vel):
                violations.append(f"Joint {i}: Invalid velocity {vel}")
            elif abs(vel) > self.velocity_max[i]:
                violations.append(
                    f"Joint {i}: Velocity {vel:.3f} exceeds limit {self.velocity_max[i]:.3f}"
                )

        return len(violations) == 0, violations

    def clamp_position(self, positions: Union[List[float], Any]) -> Any:
        """
        Clamp positions to valid range.

        Preserves the input type (tensor, array, or list).
        """
        return self._clamp_values(positions, self.position_lower, self.position_upper)

    def clamp_velocity(self, velocities: Union[List[float], Any]) -> Any:
        """
        Clamp velocities to valid range.

        Preserves the input type (tensor, array, or list).
        """
        neg_limits = [-v for v in self.velocity_max]
        return self._clamp_values(velocities, neg_limits, self.velocity_max)

    def _to_list(self, values: Any) -> List[float]:
        """Convert tensor/array to list."""
        if TORCH_AVAILABLE and isinstance(values, torch.Tensor):
            return values.detach().cpu().tolist()
        elif NUMPY_AVAILABLE and isinstance(values, np.ndarray):
            return values.tolist()
        return list(values)

    def _clamp_values(
        self,
        values: Any,
        lower: List[float],
        upper: List[float]
    ) -> Any:
        """Clamp values to range, preserving input type."""
        if TORCH_AVAILABLE and isinstance(values, torch.Tensor):
            lower_t = torch.tensor(lower, device=values.device, dtype=values.dtype)
            upper_t = torch.tensor(upper, device=values.device, dtype=values.dtype)
            return torch.clamp(values, lower_t, upper_t)
        elif NUMPY_AVAILABLE and isinstance(values, np.ndarray):
            return np.clip(values, lower, upper)
        else:
            return [max(l, min(u, v)) for v, l, u in zip(values, lower, upper)]

    @classmethod
    def franka_panda(cls) -> "JointLimits":
        """
        Create limits for Franka Emika Panda robot (7 DOF).

        Based on official Franka specifications.
        """
        return cls(
            num_joints=7,
            position_lower=[-2.8973, -1.7628, -2.8973, -3.0718, -2.8973, -0.0175, -2.8973],
            position_upper=[2.8973, 1.7628, 2.8973, -0.0698, 2.8973, 3.7525, 2.8973],
            velocity_max=[2.1750, 2.1750, 2.1750, 2.1750, 2.6100, 2.6100, 2.6100],
            effort_max=[87.0, 87.0, 87.0, 87.0, 12.0, 12.0, 12.0],
        )

    @classmethod
    def ur10(cls) -> "JointLimits":
        """
        Create limits for Universal Robots UR10 (6 DOF).

        Based on official UR specifications.
        """
        return cls(
            num_joints=6,
            position_lower=[-2 * math.pi] * 6,
            position_upper=[2 * math.pi] * 6,
            velocity_max=[2.094] * 6,  # 120 deg/s
            effort_max=[330.0, 330.0, 150.0, 54.0, 54.0, 54.0],
        )

    @classmethod
    def allegro_hand(cls) -> "JointLimits":
        """Create limits for Allegro Hand (16 DOF)."""
        return cls(
            num_joints=16,
            position_lower=[-0.47, -0.196, -0.174, -0.227] * 4,
            position_upper=[0.47, 1.61, 1.709, 1.618] * 4,
            velocity_max=[7.0] * 16,
        )

    @classmethod
    def default(cls, num_joints: int) -> "JointLimits":
        """Create default limits for arbitrary number of joints."""
        return cls(
            num_joints=num_joints,
            position_lower=[-math.pi] * num_joints,
            position_upper=[math.pi] * num_joints,
            velocity_max=[2.0] * num_joints,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "num_joints": self.num_joints,
            "position_lower": self.position_lower,
            "position_upper": self.position_upper,
            "velocity_max": self.velocity_max,
            "acceleration_max": self.acceleration_max,
            "effort_max": self.effort_max,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "JointLimits":
        """Create JointLimits from dictionary."""
        return cls(
            num_joints=data["num_joints"],
            position_lower=data["position_lower"],
            position_upper=data["position_upper"],
            velocity_max=data["velocity_max"],
            acceleration_max=data.get("acceleration_max"),
            effort_max=data.get("effort_max"),
        )


@dataclass
class WorkspaceLimits:
    """
    Cartesian workspace boundaries for end-effector.

    Defines the safe region where the robot's end-effector can operate.
    Supports both box (rectangular) and spherical constraints.

    Attributes:
        x_min, x_max: X-axis limits (meters)
        y_min, y_max: Y-axis limits (meters)
        z_min, z_max: Z-axis limits (meters)
        center: Optional center point for spherical workspace
        radius: Optional radius for spherical workspace

    Example:
        # Standard tabletop workspace
        workspace = WorkspaceLimits.table_top()

        # Franka reaching workspace
        workspace = WorkspaceLimits.franka_reach()

        # Check if position is valid
        if workspace.contains(0.5, 0.0, 0.3):
            print("Position is valid")
    """
    x_min: float = -1.0
    x_max: float = 1.0
    y_min: float = -1.0
    y_max: float = 1.0
    z_min: float = 0.0
    z_max: float = 1.5

    # Optional spherical workspace
    center: Optional[Tuple[float, float, float]] = None
    radius: Optional[float] = None

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if a point is within the workspace."""
        # Check box constraints
        in_box = (
            self.x_min <= x <= self.x_max and
            self.y_min <= y <= self.y_max and
            self.z_min <= z <= self.z_max
        )

        # Check spherical constraint if defined
        if self.center is not None and self.radius is not None:
            cx, cy, cz = self.center
            dist = math.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)
            in_sphere = dist <= self.radius
            return in_box and in_sphere

        return in_box

    def check_position(
        self,
        positions: Union[List[float], Tuple[float, float, float], Any]
    ) -> Tuple[bool, List[str]]:
        """
        Check if position is within workspace.

        Args:
            positions: XYZ position (3 values)

        Returns:
            Tuple of (is_valid, list of violation messages)
        """
        violations = []

        if hasattr(positions, '__len__') and len(positions) >= 3:
            x, y, z = positions[0], positions[1], positions[2]
        else:
            violations.append("Invalid position format (expected 3 values)")
            return False, violations

        if x < self.x_min:
            violations.append(f"X {x:.3f} < min {self.x_min:.3f}")
        elif x > self.x_max:
            violations.append(f"X {x:.3f} > max {self.x_max:.3f}")

        if y < self.y_min:
            violations.append(f"Y {y:.3f} < min {self.y_min:.3f}")
        elif y > self.y_max:
            violations.append(f"Y {y:.3f} > max {self.y_max:.3f}")

        if z < self.z_min:
            violations.append(f"Z {z:.3f} < min {self.z_min:.3f}")
        elif z > self.z_max:
            violations.append(f"Z {z:.3f} > max {self.z_max:.3f}")

        if self.center is not None and self.radius is not None:
            cx, cy, cz = self.center
            dist = math.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)
            if dist > self.radius:
                violations.append(
                    f"Distance {dist:.3f} > radius {self.radius:.3f} from center"
                )

        return len(violations) == 0, violations

    @classmethod
    def franka_reach(cls) -> "WorkspaceLimits":
        """Workspace for Franka Panda reaching tasks."""
        return cls(
            x_min=0.25, x_max=0.75,
            y_min=-0.5, y_max=0.5,
            z_min=0.0, z_max=0.8,
            center=(0.5, 0.0, 0.4),
            radius=0.5,
        )

    @classmethod
    def table_top(cls, table_height: float = 0.0) -> "WorkspaceLimits":
        """Standard tabletop manipulation workspace."""
        return cls(
            x_min=-0.5, x_max=0.5,
            y_min=-0.5, y_max=0.5,
            z_min=table_height, z_max=table_height + 0.5,
        )

    @classmethod
    def unlimited(cls) -> "WorkspaceLimits":
        """No workspace restrictions."""
        large_val = 1e9
        return cls(
            x_min=-large_val, x_max=large_val,
            y_min=-large_val, y_max=large_val,
            z_min=-large_val, z_max=large_val,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "x_min": self.x_min, "x_max": self.x_max,
            "y_min": self.y_min, "y_max": self.y_max,
            "z_min": self.z_min, "z_max": self.z_max,
            "center": self.center,
            "radius": self.radius,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkspaceLimits":
        """Create WorkspaceLimits from dictionary."""
        return cls(
            x_min=data["x_min"], x_max=data["x_max"],
            y_min=data["y_min"], y_max=data["y_max"],
            z_min=data["z_min"], z_max=data["z_max"],
            center=tuple(data["center"]) if data.get("center") else None,
            radius=data.get("radius"),
        )


@dataclass
class ForceTorqueLimits:
    """
    Force and torque limits for safe operation.

    Used for contact-rich tasks and collision detection.

    Attributes:
        max_force: Maximum force magnitude (N)
        max_torque: Maximum torque magnitude (Nm)
        max_force_per_axis: Per-axis force limits [fx, fy, fz]
        max_torque_per_axis: Per-axis torque limits [tx, ty, tz]

    Example:
        # Safe limits for human collaboration (ISO 10218)
        limits = ForceTorqueLimits.human_safe()

        # Check force
        is_valid, violations = limits.check_force([10.0, 5.0, 20.0])
    """
    max_force: float = 50.0
    max_torque: float = 10.0
    max_force_per_axis: Optional[Tuple[float, float, float]] = None
    max_torque_per_axis: Optional[Tuple[float, float, float]] = None

    def check_force(
        self,
        force: Union[List[float], Tuple[float, float, float], Any]
    ) -> Tuple[bool, List[str]]:
        """Check if force is within limits."""
        violations = []

        if hasattr(force, '__len__') and len(force) >= 3:
            fx, fy, fz = force[0], force[1], force[2]
        else:
            violations.append("Invalid force format")
            return False, violations

        magnitude = math.sqrt(fx**2 + fy**2 + fz**2)
        if magnitude > self.max_force:
            violations.append(f"Force magnitude {magnitude:.2f}N > limit {self.max_force:.2f}N")

        if self.max_force_per_axis:
            if abs(fx) > self.max_force_per_axis[0]:
                violations.append(f"Fx {fx:.2f} exceeds limit {self.max_force_per_axis[0]:.2f}")
            if abs(fy) > self.max_force_per_axis[1]:
                violations.append(f"Fy {fy:.2f} exceeds limit {self.max_force_per_axis[1]:.2f}")
            if abs(fz) > self.max_force_per_axis[2]:
                violations.append(f"Fz {fz:.2f} exceeds limit {self.max_force_per_axis[2]:.2f}")

        return len(violations) == 0, violations

    def check_torque(
        self,
        torque: Union[List[float], Tuple[float, float, float], Any]
    ) -> Tuple[bool, List[str]]:
        """Check if torque is within limits."""
        violations = []

        if hasattr(torque, '__len__') and len(torque) >= 3:
            tx, ty, tz = torque[0], torque[1], torque[2]
        else:
            violations.append("Invalid torque format")
            return False, violations

        magnitude = math.sqrt(tx**2 + ty**2 + tz**2)
        if magnitude > self.max_torque:
            violations.append(f"Torque magnitude {magnitude:.2f}Nm > limit {self.max_torque:.2f}Nm")

        return len(violations) == 0, violations

    @classmethod
    def franka_contact(cls) -> "ForceTorqueLimits":
        """Safe limits for Franka contact tasks."""
        return cls(
            max_force=30.0,
            max_torque=5.0,
            max_force_per_axis=(20.0, 20.0, 30.0),
        )

    @classmethod
    def human_safe(cls) -> "ForceTorqueLimits":
        """ISO 10218 collaborative robot limits for human safety."""
        return cls(
            max_force=150.0,
            max_torque=10.0,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_force": self.max_force,
            "max_torque": self.max_torque,
            "max_force_per_axis": self.max_force_per_axis,
            "max_torque_per_axis": self.max_torque_per_axis,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForceTorqueLimits":
        """Create ForceTorqueLimits from dictionary."""
        return cls(
            max_force=data["max_force"],
            max_torque=data["max_torque"],
            max_force_per_axis=tuple(data["max_force_per_axis"]) if data.get("max_force_per_axis") else None,
            max_torque_per_axis=tuple(data["max_torque_per_axis"]) if data.get("max_torque_per_axis") else None,
        )


@dataclass
class CollisionZone:
    """
    A region to avoid for collision prevention.

    Supports sphere, box, and cylinder shapes.

    Attributes:
        name: Zone identifier
        shape: 'sphere', 'box', or 'cylinder'
        center: Center position (x, y, z)
        dimensions: Shape-specific dimensions
            - sphere: (radius,)
            - box: (half_x, half_y, half_z)
            - cylinder: (radius, half_height)
        margin: Additional safety margin

    Example:
        # Spherical obstacle
        zone = CollisionZone.sphere("object", center=(0.5, 0.0, 0.3), radius=0.1)

        # Check collision
        if zone.contains(0.5, 0.0, 0.3):
            print("Collision detected!")
    """
    name: str
    shape: str  # 'sphere', 'box', 'cylinder'
    center: Tuple[float, float, float]
    dimensions: Tuple[float, ...]
    margin: float = 0.05

    def contains(self, x: float, y: float, z: float) -> bool:
        """Check if a point is inside the collision zone (including margin)."""
        cx, cy, cz = self.center

        if self.shape == "sphere":
            radius = self.dimensions[0] + self.margin
            dist = math.sqrt((x - cx)**2 + (y - cy)**2 + (z - cz)**2)
            return dist <= radius

        elif self.shape == "box":
            hx = self.dimensions[0] + self.margin
            hy = self.dimensions[1] + self.margin
            hz = self.dimensions[2] + self.margin
            return (
                abs(x - cx) <= hx and
                abs(y - cy) <= hy and
                abs(z - cz) <= hz
            )

        elif self.shape == "cylinder":
            radius = self.dimensions[0] + self.margin
            half_h = self.dimensions[1] + self.margin
            dist_xy = math.sqrt((x - cx)**2 + (y - cy)**2)
            return dist_xy <= radius and abs(z - cz) <= half_h

        return False

    @classmethod
    def sphere(
        cls,
        name: str,
        center: Tuple[float, float, float],
        radius: float,
        margin: float = 0.05,
    ) -> "CollisionZone":
        """Create a spherical collision zone."""
        return cls(name=name, shape="sphere", center=center, dimensions=(radius,), margin=margin)

    @classmethod
    def box(
        cls,
        name: str,
        center: Tuple[float, float, float],
        half_extents: Tuple[float, float, float],
        margin: float = 0.05,
    ) -> "CollisionZone":
        """Create a box collision zone."""
        return cls(name=name, shape="box", center=center, dimensions=half_extents, margin=margin)

    @classmethod
    def cylinder(
        cls,
        name: str,
        center: Tuple[float, float, float],
        radius: float,
        half_height: float,
        margin: float = 0.05,
    ) -> "CollisionZone":
        """Create a cylindrical collision zone."""
        return cls(
            name=name,
            shape="cylinder",
            center=center,
            dimensions=(radius, half_height),
            margin=margin,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "shape": self.shape,
            "center": self.center,
            "dimensions": self.dimensions,
            "margin": self.margin,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CollisionZone":
        """Create CollisionZone from dictionary."""
        return cls(
            name=data["name"],
            shape=data["shape"],
            center=tuple(data["center"]),
            dimensions=tuple(data["dimensions"]),
            margin=data.get("margin", 0.05),
        )


@dataclass
class RobotConstraints:
    """
    Container for all robot safety constraints.

    This is the main configuration object for simulation safety validation.

    Attributes:
        joint_limits: Joint position and velocity limits
        workspace_limits: Cartesian workspace boundaries
        force_torque_limits: Force and torque limits
        collision_zones: List of regions to avoid
        action_scale: Scale factor for normalized actions
        require_purpose: Require explicit purpose for actions

    Example:
        # Quick setup for Franka Panda
        constraints = RobotConstraints.franka_default()

        # Custom constraints
        constraints = RobotConstraints(
            joint_limits=JointLimits.franka_panda(),
            workspace_limits=WorkspaceLimits.franka_reach(),
            force_torque_limits=ForceTorqueLimits.human_safe(),
        )

        # Add collision zones
        constraints.add_collision_zone(
            CollisionZone.sphere("object", (0.5, 0.0, 0.3), 0.1)
        )
    """
    joint_limits: Optional[JointLimits] = None
    workspace_limits: Optional[WorkspaceLimits] = None
    force_torque_limits: Optional[ForceTorqueLimits] = None
    collision_zones: List[CollisionZone] = field(default_factory=list)
    action_scale: float = 1.0
    require_purpose: bool = False

    @classmethod
    def franka_default(cls) -> "RobotConstraints":
        """Default safe constraints for Franka Panda."""
        return cls(
            joint_limits=JointLimits.franka_panda(),
            workspace_limits=WorkspaceLimits.franka_reach(),
            force_torque_limits=ForceTorqueLimits.franka_contact(),
        )

    @classmethod
    def ur10_default(cls) -> "RobotConstraints":
        """Default safe constraints for UR10."""
        return cls(
            joint_limits=JointLimits.ur10(),
            workspace_limits=WorkspaceLimits.table_top(),
            force_torque_limits=ForceTorqueLimits.human_safe(),
        )

    @classmethod
    def allegro_default(cls) -> "RobotConstraints":
        """Default safe constraints for Allegro Hand."""
        return cls(
            joint_limits=JointLimits.allegro_hand(),
        )

    @classmethod
    def from_urdf_limits(
        cls,
        position_lower: List[float],
        position_upper: List[float],
        velocity_max: List[float],
    ) -> "RobotConstraints":
        """Create constraints from URDF-style joint limits."""
        num_joints = len(position_lower)
        return cls(
            joint_limits=JointLimits(
                num_joints=num_joints,
                position_lower=position_lower,
                position_upper=position_upper,
                velocity_max=velocity_max,
            ),
        )

    def add_collision_zone(self, zone: CollisionZone) -> "RobotConstraints":
        """Add a collision zone and return self for chaining."""
        self.collision_zones.append(zone)
        return self

    def check_collision(self, x: float, y: float, z: float) -> Tuple[bool, List[str]]:
        """
        Check if a position collides with any zone.

        Returns:
            Tuple of (has_collision, list of colliding zone names)
        """
        collisions = []
        for zone in self.collision_zones:
            if zone.contains(x, y, z):
                collisions.append(zone.name)
        return len(collisions) > 0, collisions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "joint_limits": self.joint_limits.to_dict() if self.joint_limits else None,
            "workspace_limits": self.workspace_limits.to_dict() if self.workspace_limits else None,
            "force_torque_limits": self.force_torque_limits.to_dict() if self.force_torque_limits else None,
            "collision_zones": [z.to_dict() for z in self.collision_zones],
            "action_scale": self.action_scale,
            "require_purpose": self.require_purpose,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RobotConstraints":
        """Create RobotConstraints from dictionary."""
        joint_limits = None
        if data.get("joint_limits"):
            joint_limits = JointLimits.from_dict(data["joint_limits"])

        workspace_limits = None
        if data.get("workspace_limits"):
            workspace_limits = WorkspaceLimits.from_dict(data["workspace_limits"])

        force_torque_limits = None
        if data.get("force_torque_limits"):
            force_torque_limits = ForceTorqueLimits.from_dict(data["force_torque_limits"])

        collision_zones = []
        for zone_data in data.get("collision_zones", []):
            collision_zones.append(CollisionZone.from_dict(zone_data))

        return cls(
            joint_limits=joint_limits,
            workspace_limits=workspace_limits,
            force_torque_limits=force_torque_limits,
            collision_zones=collision_zones,
            action_scale=data.get("action_scale", 1.0),
            require_purpose=data.get("require_purpose", False),
        )


__all__ = [
    "ConstraintViolationType",
    "JointLimits",
    "WorkspaceLimits",
    "ForceTorqueLimits",
    "CollisionZone",
    "RobotConstraints",
]
