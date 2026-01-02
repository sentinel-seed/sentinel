"""
Mobile Robot Safety Module.

Provides velocity limits and spatial safety zones for mobile robots including:
- Differential drive robots (wheeled robots that turn by varying wheel speeds)
- Omnidirectional robots (robots that can move in any direction)
- Drones/UAVs (aerial vehicles with 6 DOF movement)

This module is used by the ROS2 integration but can be used independently
for any mobile robot application.

Quick Start:
    from sentinelseed.safety.mobile import (
        VelocityLimits,
        SafetyZone,
    )

    # Create limits for a differential drive robot
    limits = VelocityLimits.differential_drive(max_linear=1.0, max_angular=0.5)

    # Create limits for a drone
    drone_limits = VelocityLimits.drone(max_linear=2.0, max_vertical=1.0)

    # Create an indoor safety zone
    zone = SafetyZone.indoor(room_size=10.0)

    # Check if a position is within the zone
    if zone.contains(x=1.0, y=2.0, z=0.5):
        print("Position is safe")

Classes:
    - VelocityLimits: 6 DOF velocity constraints (linear x/y/z, angular x/y/z)
    - SafetyZone: Spatial boundaries for safe operation

Exceptions:
    - ValidationError: Raised when validation constraints are violated

Constants:
    - DEFAULT_MAX_LINEAR_VEL: Default maximum linear velocity (1.0 m/s)
    - DEFAULT_MAX_ANGULAR_VEL: Default maximum angular velocity (0.5 rad/s)
    - DEFAULT_ROOM_SIZE: Default indoor room size (10.0 m)
    - DEFAULT_MAX_ALTITUDE: Default maximum altitude (2.0 m)
"""

from sentinelseed.safety.mobile.velocity import (
    VelocityLimits,
    ValidationError,
    DEFAULT_MAX_LINEAR_VEL,
    DEFAULT_MAX_ANGULAR_VEL,
)

from sentinelseed.safety.mobile.zones import (
    SafetyZone,
    DEFAULT_ROOM_SIZE,
    DEFAULT_MAX_ALTITUDE,
)

__version__ = "1.0.0"

__all__ = [
    # Version
    "__version__",
    # Classes
    "VelocityLimits",
    "SafetyZone",
    # Exceptions
    "ValidationError",
    # Constants
    "DEFAULT_MAX_LINEAR_VEL",
    "DEFAULT_MAX_ANGULAR_VEL",
    "DEFAULT_ROOM_SIZE",
    "DEFAULT_MAX_ALTITUDE",
]
