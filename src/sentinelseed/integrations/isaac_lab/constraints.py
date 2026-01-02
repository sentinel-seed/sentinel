"""
Robot Safety Constraints for Isaac Lab Integration.

This module re-exports the constraint classes from the centralized
safety.simulation module for backward compatibility.

Architecture:
    All constraint classes are now defined in sentinelseed.safety.simulation.
    This module provides backward-compatible imports.

Classes:
    - JointLimits: Position and velocity limits for robot joints
    - WorkspaceLimits: Cartesian workspace boundaries
    - ForceTorqueLimits: Force and torque safety limits
    - CollisionZone: Regions to avoid
    - RobotConstraints: Container for all robot constraints
    - ConstraintViolationType: Types of constraint violations

Migration Note:
    New code should import directly from sentinelseed.safety.simulation:

        from sentinelseed.safety.simulation import (
            JointLimits,
            RobotConstraints,
            # ...
        )

References:
    - Isaac Lab Articulation: https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.assets.html
    - Isaac Lab Controllers: https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.controllers.html
"""

# Re-export from centralized location for backward compatibility
from sentinelseed.safety.simulation.constraints import (
    ConstraintViolationType,
    JointLimits,
    WorkspaceLimits,
    ForceTorqueLimits,
    CollisionZone,
    RobotConstraints,
)

__all__ = [
    "ConstraintViolationType",
    "JointLimits",
    "WorkspaceLimits",
    "ForceTorqueLimits",
    "CollisionZone",
    "RobotConstraints",
]
