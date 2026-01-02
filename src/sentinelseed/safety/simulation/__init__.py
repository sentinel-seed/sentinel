"""
Simulation Safety Module.

Provides safety constraints and validation for robotic simulation environments,
particularly designed for reinforcement learning with Isaac Lab/Sim.

This module provides:
- Joint limits: Position and velocity constraints per joint
- Workspace limits: Cartesian boundaries for end-effector
- Force/torque limits: Contact force safety limits
- Collision zones: Regions to avoid
- Action types: Classification of RL action spaces

Key Features:
    - Batch validation for vectorized environments
    - Support for torch tensors and numpy arrays
    - Presets for common robots (Franka Panda, UR10, Allegro Hand)
    - THSP-based validation for robot actions

Quick Start:
    from sentinelseed.safety.simulation import (
        JointLimits,
        WorkspaceLimits,
        RobotConstraints,
        ActionType,
    )

    # Create constraints for Franka Panda
    constraints = RobotConstraints.franka_default()

    # Or build custom constraints
    constraints = RobotConstraints(
        joint_limits=JointLimits.franka_panda(),
        workspace_limits=WorkspaceLimits.franka_reach(),
    )

    # Check joint positions
    is_valid, violations = constraints.joint_limits.check_position(positions)

Classes:
    - JointLimits: Position and velocity limits per joint
    - WorkspaceLimits: Cartesian workspace boundaries
    - ForceTorqueLimits: Force and torque safety limits
    - CollisionZone: Regions to avoid
    - RobotConstraints: Container for all constraints
    - ActionType: Classification of action types
    - BatchValidationResult: Results for batch validation

References:
    - Isaac Lab: https://isaac-sim.github.io/IsaacLab/
    - ISO 10218: Industrial robot safety
"""

from sentinelseed.safety.simulation.constraints import (
    JointLimits,
    WorkspaceLimits,
    ForceTorqueLimits,
    CollisionZone,
    RobotConstraints,
    ConstraintViolationType,
)

from sentinelseed.safety.simulation.action_types import (
    ActionType,
    BatchValidationResult,
)

__version__ = "1.0.0"

__all__ = [
    # Version
    "__version__",
    # Constraints
    "JointLimits",
    "WorkspaceLimits",
    "ForceTorqueLimits",
    "CollisionZone",
    "RobotConstraints",
    "ConstraintViolationType",
    # Action types
    "ActionType",
    "BatchValidationResult",
]
