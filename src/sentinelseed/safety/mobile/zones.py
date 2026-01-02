"""
Spatial Safety Zones for Mobile Robots.

Provides 3D bounding box safety zones for restricting robot operation
to defined areas. Common use cases:
- Indoor navigation (room boundaries)
- Outdoor operation (geofencing)
- Drone altitude limits
- Restricted areas

The coordinate system follows ROS conventions:
- x: forward (positive) / backward (negative)
- y: left (positive) / right (negative)
- z: up (positive) / down (negative)
"""

from dataclasses import dataclass, field
import math

from sentinelseed.safety.mobile.velocity import ValidationError

# Default zone dimensions
DEFAULT_ROOM_SIZE = 10.0   # meters - typical room/lab size
DEFAULT_MAX_ALTITUDE = 2.0  # meters - safe ceiling clearance


@dataclass
class SafetyZone:
    """
    3D spatial safety zone for mobile robot operation.

    Defines a rectangular bounding box within which the robot is
    allowed to operate. Positions outside this zone are considered
    unsafe.

    Attributes:
        min_x: Minimum x coordinate (meters)
        max_x: Maximum x coordinate (meters)
        min_y: Minimum y coordinate (meters)
        max_y: Maximum y coordinate (meters)
        min_z: Minimum z coordinate (meters)
        max_z: Maximum z coordinate (meters)

    Example:
        # Create a 10m x 10m room with 3m ceiling
        zone = SafetyZone.indoor(room_size=10.0)

        # Check if robot is within zone
        if zone.contains(x=2.0, y=-1.5, z=0.0):
            print("Robot is in safe zone")

        # Create unlimited zone (no spatial restrictions)
        unlimited = SafetyZone.unlimited()

    Raises:
        ValidationError: If min > max for any axis, or values are NaN
    """
    min_x: float = -DEFAULT_ROOM_SIZE / 2
    max_x: float = DEFAULT_ROOM_SIZE / 2
    min_y: float = -DEFAULT_ROOM_SIZE / 2
    max_y: float = DEFAULT_ROOM_SIZE / 2
    min_z: float = 0.0
    max_z: float = DEFAULT_MAX_ALTITUDE

    # Internal flag to skip validation for special zones
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
        """
        Check if a position is within the safety zone.

        Args:
            x: X coordinate (meters)
            y: Y coordinate (meters)
            z: Z coordinate (meters), defaults to 0.0

        Returns:
            True if position is within zone, False otherwise
        """
        # NaN values are never within any zone
        if math.isnan(x) or math.isnan(y) or math.isnan(z):
            return False

        return (
            self.min_x <= x <= self.max_x and
            self.min_y <= y <= self.max_y and
            self.min_z <= z <= self.max_z
        )

    def distance_to_boundary(self, x: float, y: float, z: float = 0.0) -> float:
        """
        Calculate distance to nearest boundary.

        Positive distance means inside the zone.
        Negative distance means outside the zone.

        Args:
            x: X coordinate (meters)
            y: Y coordinate (meters)
            z: Z coordinate (meters)

        Returns:
            Distance to nearest boundary (negative if outside)
        """
        if math.isnan(x) or math.isnan(y) or math.isnan(z):
            return float('-inf')

        # Calculate distance to each boundary (positive = inside)
        distances = [
            x - self.min_x,  # distance from min_x
            self.max_x - x,  # distance from max_x
            y - self.min_y,  # distance from min_y
            self.max_y - y,  # distance from max_y
            z - self.min_z,  # distance from min_z
            self.max_z - z,  # distance from max_z
        ]

        # Minimum distance (negative if outside any boundary)
        return min(distances)

    def clamp_position(self, x: float, y: float, z: float = 0.0) -> tuple:
        """
        Clamp a position to within the safety zone.

        Args:
            x: X coordinate (meters)
            y: Y coordinate (meters)
            z: Z coordinate (meters)

        Returns:
            Tuple of (x, y, z) clamped to zone boundaries
        """
        return (
            max(self.min_x, min(self.max_x, x)),
            max(self.min_y, min(self.max_y, y)),
            max(self.min_z, min(self.max_z, z)),
        )

    @property
    def center(self) -> tuple:
        """Get the center point of the zone."""
        return (
            (self.min_x + self.max_x) / 2,
            (self.min_y + self.max_y) / 2,
            (self.min_z + self.max_z) / 2,
        )

    @property
    def dimensions(self) -> tuple:
        """Get the dimensions (width, depth, height) of the zone."""
        return (
            self.max_x - self.min_x,
            self.max_y - self.min_y,
            self.max_z - self.min_z,
        )

    @property
    def volume(self) -> float:
        """Get the volume of the zone in cubic meters."""
        w, d, h = self.dimensions
        return w * d * h

    @classmethod
    def unlimited(cls) -> "SafetyZone":
        """
        Create an unlimited safety zone.

        Use this when spatial restrictions are not needed, but you
        still want to use the SafetyZone interface for consistency.

        Note: Uses very large finite values (1 billion meters) instead
        of infinity to avoid potential issues with math operations.

        Returns:
            SafetyZone with effectively no boundaries
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
        """
        Create an indoor safety zone (room).

        Creates a square room centered at origin with typical
        indoor ceiling height (3 meters).

        Args:
            room_size: Room width/depth in meters

        Returns:
            SafetyZone configured for indoor operation

        Raises:
            ValidationError: If room_size is not positive

        Example:
            # Small lab (5m x 5m)
            zone = SafetyZone.indoor(room_size=5.0)

            # Large warehouse (50m x 50m)
            zone = SafetyZone.indoor(room_size=50.0)
        """
        if room_size <= 0:
            raise ValidationError(
                f"room_size must be positive (got {room_size})",
                field="room_size",
            )
        half = room_size / 2
        return cls(
            min_x=-half,
            max_x=half,
            min_y=-half,
            max_y=half,
            min_z=0.0,
            max_z=3.0,  # Standard ceiling height
        )

    @classmethod
    def outdoor(
        cls,
        width: float = 100.0,
        depth: float = 100.0,
        max_altitude: float = 50.0,
    ) -> "SafetyZone":
        """
        Create an outdoor safety zone (geofence).

        Creates a rectangular outdoor area centered at origin
        with configurable altitude limit.

        Args:
            width: Zone width in meters (x-axis)
            depth: Zone depth in meters (y-axis)
            max_altitude: Maximum altitude in meters

        Returns:
            SafetyZone configured for outdoor operation

        Raises:
            ValidationError: If any dimension is not positive

        Example:
            # Small drone flight zone
            zone = SafetyZone.outdoor(
                width=50.0,
                depth=50.0,
                max_altitude=30.0,
            )
        """
        for name, value in [("width", width), ("depth", depth), ("max_altitude", max_altitude)]:
            if value <= 0:
                raise ValidationError(
                    f"{name} must be positive (got {value})",
                    field=name,
                )
        return cls(
            min_x=-width / 2,
            max_x=width / 2,
            min_y=-depth / 2,
            max_y=depth / 2,
            min_z=0.0,
            max_z=max_altitude,
        )

    @classmethod
    def corridor(
        cls,
        length: float = 20.0,
        width: float = 2.0,
        height: float = 3.0,
    ) -> "SafetyZone":
        """
        Create a corridor safety zone.

        Creates a narrow rectangular zone, useful for hallway
        navigation or constrained paths.

        Args:
            length: Corridor length in meters (x-axis)
            width: Corridor width in meters (y-axis)
            height: Corridor height in meters

        Returns:
            SafetyZone configured for corridor navigation
        """
        for name, value in [("length", length), ("width", width), ("height", height)]:
            if value <= 0:
                raise ValidationError(
                    f"{name} must be positive (got {value})",
                    field=name,
                )
        return cls(
            min_x=-length / 2,
            max_x=length / 2,
            min_y=-width / 2,
            max_y=width / 2,
            min_z=0.0,
            max_z=height,
        )

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "min_x": self.min_x,
            "max_x": self.max_x,
            "min_y": self.min_y,
            "max_y": self.max_y,
            "min_z": self.min_z,
            "max_z": self.max_z,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SafetyZone":
        """Create from dictionary."""
        return cls(
            min_x=data.get("min_x", -DEFAULT_ROOM_SIZE / 2),
            max_x=data.get("max_x", DEFAULT_ROOM_SIZE / 2),
            min_y=data.get("min_y", -DEFAULT_ROOM_SIZE / 2),
            max_y=data.get("max_y", DEFAULT_ROOM_SIZE / 2),
            min_z=data.get("min_z", 0.0),
            max_z=data.get("max_z", DEFAULT_MAX_ALTITUDE),
        )


__all__ = [
    "SafetyZone",
    "DEFAULT_ROOM_SIZE",
    "DEFAULT_MAX_ALTITUDE",
]
