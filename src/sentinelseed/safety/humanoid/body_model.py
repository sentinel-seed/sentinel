"""
Human Body Model with ISO/TS 15066 Contact Force Limits.

This module provides a body model with biomechanical force and pressure limits
for safe human-robot interaction. The limits are based on pain onset thresholds
from the University of Mainz study, which forms the basis of ISO/TS 15066
(now integrated into ISO 10218-2:2025).

The model defines 29 body regions with specific force limits for:
- Quasi-static contact: When body part is clamped/trapped
- Transient contact: When body part can recoil freely (typically 2x quasi-static)

References:
    - ISO/TS 15066:2016 "Robots and robotic devices - Collaborative robots"
    - ISO 10218-2:2025 "Robotics - Safety requirements - Part 2"
    - University of Mainz pain onset study (100 subjects, 29 body areas)
    - PMC8850785: "A Statistical Model to Determine Biomechanical Limits"
"""

from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Dict, List, Optional, Tuple


class BodyRegion(str, Enum):
    """
    Body regions as defined in ISO/TS 15066 Annex A.

    The 29 body areas are grouped into 12 regions for ease of use.
    """
    # Head and Neck
    SKULL_FOREHEAD = "skull_forehead"
    SKULL_TEMPLE = "skull_temple"
    FACE = "face"
    NECK_FRONT = "neck_front"
    NECK_SIDE = "neck_side"
    NECK_BACK = "neck_back"

    # Trunk
    SHOULDER = "shoulder"
    CHEST_STERNUM = "chest_sternum"
    CHEST_PECTORAL = "chest_pectoral"
    ABDOMEN = "abdomen"
    PELVIS = "pelvis"
    BACK_UPPER = "back_upper"
    BACK_LOWER = "back_lower"

    # Upper Extremities
    UPPER_ARM_DELTOID = "upper_arm_deltoid"
    UPPER_ARM_HUMERUS = "upper_arm_humerus"
    ELBOW = "elbow"
    FOREARM_MUSCLE = "forearm_muscle"
    FOREARM_BONE = "forearm_bone"
    WRIST = "wrist"
    HAND_PALM = "hand_palm"
    HAND_BACK = "hand_back"
    FINGER = "finger"

    # Lower Extremities
    THIGH_FRONT = "thigh_front"
    THIGH_BACK = "thigh_back"
    KNEE = "knee"
    SHIN = "shin"
    CALF = "calf"
    ANKLE = "ankle"
    FOOT = "foot"


@dataclass
class ContactLimits:
    """
    Force and pressure limits for a specific body region.

    Based on ISO/TS 15066 Annex A biomechanical data from University of Mainz.

    Attributes:
        region: The body region these limits apply to
        force_quasi_static: Maximum force (N) for quasi-static contact (clamping)
        force_transient: Maximum force (N) for transient contact (impact)
        pressure_quasi_static: Maximum pressure (N/cm²) for quasi-static contact
        pressure_transient: Maximum pressure (N/cm²) for transient contact
        effective_mass: Effective mass of the body part (kg) for impact calculations
        notes: Additional notes about the limits
    """
    region: BodyRegion
    force_quasi_static: float  # N
    force_transient: float     # N
    pressure_quasi_static: Optional[float] = None  # N/cm²
    pressure_transient: Optional[float] = None     # N/cm²
    effective_mass: Optional[float] = None         # kg
    notes: str = ""

    @property
    def force_ratio(self) -> float:
        """Ratio of transient to quasi-static force limit."""
        if self.force_quasi_static > 0:
            return self.force_transient / self.force_quasi_static
        return 0.0


class HumanBodyModel:
    """
    Human body model with biomechanical contact limits.

    This class provides access to ISO/TS 15066 compliant force and pressure
    limits for all 29 body regions. Use this to validate that robot contact
    forces are within safe thresholds.

    The limits are based on pain onset thresholds - actual injury would occur
    at higher forces, but the standard uses pain onset as the safety threshold.

    Example:
        body = HumanBodyModel()

        # Check if a force is safe for chest contact
        limits = body.get_limits(BodyRegion.CHEST_STERNUM)
        force = 100  # Newtons
        is_safe = force <= limits.force_transient
        print(f"Contact force {force}N is safe: {is_safe}")

        # Get the most sensitive region
        most_sensitive = body.get_most_sensitive_region()
        print(f"Most sensitive: {most_sensitive.region.value} at {most_sensitive.force_quasi_static}N")
    """

    # Biomechanical limits based on ISO/TS 15066 Annex A and Mainz study
    # Values are pain onset thresholds for 75th percentile
    # Quasi-static = clamping situation, Transient = free recoil impact
    # Force ratio transient/quasi-static is approximately 1.5-2.0x
    _LIMITS: Dict[BodyRegion, ContactLimits] = {
        # Head and Neck - Most sensitive regions, require extra caution
        BodyRegion.SKULL_FOREHEAD: ContactLimits(
            region=BodyRegion.SKULL_FOREHEAD,
            force_quasi_static=110.0,
            force_transient=150.0,
            pressure_quasi_static=130.0,
            pressure_transient=180.0,
            effective_mass=4.4,
            notes="Rigid bone structure, moderate sensitivity",
        ),
        BodyRegion.SKULL_TEMPLE: ContactLimits(
            region=BodyRegion.SKULL_TEMPLE,
            force_quasi_static=60.0,
            force_transient=90.0,
            pressure_quasi_static=110.0,
            pressure_transient=150.0,
            effective_mass=4.4,
            notes="CRITICAL: Very sensitive area, thin bone",
        ),
        BodyRegion.FACE: ContactLimits(
            region=BodyRegion.FACE,
            force_quasi_static=50.0,
            force_transient=75.0,
            pressure_quasi_static=100.0,
            pressure_transient=145.0,
            effective_mass=4.4,
            notes="CRITICAL: Sensitive soft tissue and orbital bones",
        ),
        BodyRegion.NECK_FRONT: ContactLimits(
            region=BodyRegion.NECK_FRONT,
            force_quasi_static=35.0,
            force_transient=55.0,
            pressure_quasi_static=80.0,
            pressure_transient=120.0,
            effective_mass=1.2,
            notes="CRITICAL: Trachea and carotid arteries - avoid contact",
        ),
        BodyRegion.NECK_SIDE: ContactLimits(
            region=BodyRegion.NECK_SIDE,
            force_quasi_static=45.0,
            force_transient=70.0,
            pressure_quasi_static=90.0,
            pressure_transient=135.0,
            effective_mass=1.2,
            notes="CRITICAL: Carotid arteries and jugular",
        ),
        BodyRegion.NECK_BACK: ContactLimits(
            region=BodyRegion.NECK_BACK,
            force_quasi_static=50.0,
            force_transient=70.0,
            pressure_quasi_static=100.0,
            pressure_transient=140.0,
            effective_mass=1.2,
            notes="C7 vertebra region",
        ),

        # Trunk
        BodyRegion.SHOULDER: ContactLimits(
            region=BodyRegion.SHOULDER,
            force_quasi_static=60.0,
            force_transient=100.0,
            pressure_quasi_static=120.0,
            pressure_transient=200.0,
            effective_mass=40.0,
            notes="Shoulder joint area",
        ),
        BodyRegion.CHEST_STERNUM: ContactLimits(
            region=BodyRegion.CHEST_STERNUM,
            force_quasi_static=80.0,
            force_transient=110.0,
            pressure_quasi_static=140.0,
            pressure_transient=190.0,
            effective_mass=40.0,
            notes="Rigid bone over heart - moderate sensitivity",
        ),
        BodyRegion.CHEST_PECTORAL: ContactLimits(
            region=BodyRegion.CHEST_PECTORAL,
            force_quasi_static=100.0,
            force_transient=140.0,
            pressure_quasi_static=150.0,
            pressure_transient=210.0,
            effective_mass=40.0,
            notes="Pectoral muscle region",
        ),
        BodyRegion.ABDOMEN: ContactLimits(
            region=BodyRegion.ABDOMEN,
            force_quasi_static=60.0,
            force_transient=90.0,
            pressure_quasi_static=110.0,
            pressure_transient=160.0,
            effective_mass=40.0,
            notes="Soft tissue over internal organs - sensitive",
        ),
        BodyRegion.PELVIS: ContactLimits(
            region=BodyRegion.PELVIS,
            force_quasi_static=100.0,
            force_transient=160.0,
            pressure_quasi_static=150.0,
            pressure_transient=240.0,
            effective_mass=40.0,
            notes="Hip bone region",
        ),
        BodyRegion.BACK_UPPER: ContactLimits(
            region=BodyRegion.BACK_UPPER,
            force_quasi_static=100.0,
            force_transient=150.0,
            pressure_quasi_static=150.0,
            pressure_transient=220.0,
            effective_mass=40.0,
            notes="Upper back muscle and spine",
        ),
        BodyRegion.BACK_LOWER: ContactLimits(
            region=BodyRegion.BACK_LOWER,
            force_quasi_static=110.0,
            force_transient=180.0,
            pressure_quasi_static=160.0,
            pressure_transient=260.0,
            effective_mass=40.0,
            notes="L5 lumbar vertebra region",
        ),

        # Upper Extremities
        BodyRegion.UPPER_ARM_DELTOID: ContactLimits(
            region=BodyRegion.UPPER_ARM_DELTOID,
            force_quasi_static=100.0,
            force_transient=150.0,
            pressure_quasi_static=150.0,
            pressure_transient=225.0,
            effective_mass=3.0,
            notes="Deltoid muscle region",
        ),
        BodyRegion.UPPER_ARM_HUMERUS: ContactLimits(
            region=BodyRegion.UPPER_ARM_HUMERUS,
            force_quasi_static=70.0,
            force_transient=150.0,
            pressure_quasi_static=130.0,
            pressure_transient=280.0,
            effective_mass=3.0,
            notes="Humerus bone - sensitive to direct contact",
        ),
        BodyRegion.ELBOW: ContactLimits(
            region=BodyRegion.ELBOW,
            force_quasi_static=70.0,
            force_transient=120.0,
            pressure_quasi_static=130.0,
            pressure_transient=220.0,
            effective_mass=2.0,
            notes="Elbow joint and ulnar nerve",
        ),
        BodyRegion.FOREARM_MUSCLE: ContactLimits(
            region=BodyRegion.FOREARM_MUSCLE,
            force_quasi_static=100.0,
            force_transient=170.0,
            pressure_quasi_static=160.0,
            pressure_transient=270.0,
            effective_mass=1.5,
            notes="Forearm flexor/extensor muscles",
        ),
        BodyRegion.FOREARM_BONE: ContactLimits(
            region=BodyRegion.FOREARM_BONE,
            force_quasi_static=100.0,
            force_transient=180.0,
            pressure_quasi_static=160.0,
            pressure_transient=290.0,
            effective_mass=1.5,
            notes="Radial bone region",
        ),
        BodyRegion.WRIST: ContactLimits(
            region=BodyRegion.WRIST,
            force_quasi_static=80.0,
            force_transient=140.0,
            pressure_quasi_static=150.0,
            pressure_transient=260.0,
            effective_mass=0.6,
            notes="Wrist joint",
        ),
        BodyRegion.HAND_PALM: ContactLimits(
            region=BodyRegion.HAND_PALM,
            force_quasi_static=150.0,
            force_transient=330.0,
            pressure_quasi_static=200.0,
            pressure_transient=440.0,
            effective_mass=0.6,
            notes="Palm - relatively tolerant",
        ),
        BodyRegion.HAND_BACK: ContactLimits(
            region=BodyRegion.HAND_BACK,
            force_quasi_static=150.0,
            force_transient=250.0,
            pressure_quasi_static=200.0,
            pressure_transient=330.0,
            effective_mass=0.6,
            notes="Dorsum of hand",
        ),
        BodyRegion.FINGER: ContactLimits(
            region=BodyRegion.FINGER,
            force_quasi_static=150.0,
            force_transient=390.0,
            pressure_quasi_static=250.0,
            pressure_transient=650.0,
            effective_mass=0.1,
            notes="Finger pad - high tolerance",
        ),

        # Lower Extremities
        BodyRegion.THIGH_FRONT: ContactLimits(
            region=BodyRegion.THIGH_FRONT,
            force_quasi_static=140.0,
            force_transient=200.0,
            pressure_quasi_static=180.0,
            pressure_transient=260.0,
            effective_mass=12.0,
            notes="Quadriceps muscle region",
        ),
        BodyRegion.THIGH_BACK: ContactLimits(
            region=BodyRegion.THIGH_BACK,
            force_quasi_static=140.0,
            force_transient=220.0,
            pressure_quasi_static=180.0,
            pressure_transient=280.0,
            effective_mass=12.0,
            notes="Hamstring muscle region",
        ),
        BodyRegion.KNEE: ContactLimits(
            region=BodyRegion.KNEE,
            force_quasi_static=160.0,
            force_transient=270.0,
            pressure_quasi_static=200.0,
            pressure_transient=340.0,
            effective_mass=5.0,
            notes="Kneecap (patella)",
        ),
        BodyRegion.SHIN: ContactLimits(
            region=BodyRegion.SHIN,
            force_quasi_static=150.0,
            force_transient=260.0,
            pressure_quasi_static=200.0,
            pressure_transient=340.0,
            effective_mass=4.0,
            notes="Shin bone (tibia) - sensitive to direct impact",
        ),
        BodyRegion.CALF: ContactLimits(
            region=BodyRegion.CALF,
            force_quasi_static=130.0,
            force_transient=260.0,
            pressure_quasi_static=180.0,
            pressure_transient=360.0,
            effective_mass=4.0,
            notes="Calf muscle region",
        ),
        BodyRegion.ANKLE: ContactLimits(
            region=BodyRegion.ANKLE,
            force_quasi_static=100.0,
            force_transient=180.0,
            pressure_quasi_static=160.0,
            pressure_transient=290.0,
            effective_mass=1.0,
            notes="Ankle joint",
        ),
        BodyRegion.FOOT: ContactLimits(
            region=BodyRegion.FOOT,
            force_quasi_static=130.0,
            force_transient=230.0,
            pressure_quasi_static=190.0,
            pressure_transient=340.0,
            effective_mass=1.0,
            notes="Top of foot (dorsum)",
        ),
    }

    # Critical regions requiring extra safety measures
    CRITICAL_REGIONS = frozenset([
        BodyRegion.SKULL_TEMPLE,
        BodyRegion.FACE,
        BodyRegion.NECK_FRONT,
        BodyRegion.NECK_SIDE,
    ])

    def __init__(self, safety_factor: float = 1.0):
        """
        Initialize the human body model.

        Args:
            safety_factor: Multiplier for safety margins (1.0 = standard limits,
                          0.8 = 20% more conservative, etc.)
        """
        if not 0.1 <= safety_factor <= 2.0:
            raise ValueError("safety_factor must be between 0.1 and 2.0")
        self.safety_factor = safety_factor

    def get_limits(self, region: BodyRegion) -> ContactLimits:
        """
        Get contact limits for a specific body region.

        Args:
            region: The body region to get limits for

        Returns:
            ContactLimits with force and pressure thresholds
        """
        return self._LIMITS[region]

    def get_safe_force(
        self,
        region: BodyRegion,
        contact_type: str = "transient",
    ) -> float:
        """
        Get the maximum safe force for a body region.

        Args:
            region: The body region
            contact_type: Either "transient" (impact) or "quasi_static" (clamping)

        Returns:
            Maximum safe force in Newtons, adjusted by safety factor
        """
        limits = self._LIMITS[region]
        if contact_type == "transient":
            return limits.force_transient * self.safety_factor
        else:
            return limits.force_quasi_static * self.safety_factor

    def get_safe_pressure(
        self,
        region: BodyRegion,
        contact_type: str = "transient",
    ) -> Optional[float]:
        """
        Get the maximum safe pressure for a body region.

        Args:
            region: The body region
            contact_type: Either "transient" (impact) or "quasi_static" (clamping)

        Returns:
            Maximum safe pressure in N/cm², adjusted by safety factor
        """
        limits = self._LIMITS[region]
        if contact_type == "transient":
            if limits.pressure_transient:
                return limits.pressure_transient * self.safety_factor
        else:
            if limits.pressure_quasi_static:
                return limits.pressure_quasi_static * self.safety_factor
        return None

    def is_force_safe(
        self,
        region: BodyRegion,
        force: float,
        contact_type: str = "transient",
    ) -> bool:
        """
        Check if a contact force is within safe limits.

        Args:
            region: The body region being contacted
            force: The contact force in Newtons
            contact_type: Either "transient" or "quasi_static"

        Returns:
            True if force is within safe limits
        """
        safe_force = self.get_safe_force(region, contact_type)
        return force <= safe_force

    def get_most_sensitive_region(self) -> ContactLimits:
        """
        Get the body region with lowest force tolerance.

        Returns:
            ContactLimits for the most sensitive region
        """
        return min(
            self._LIMITS.values(),
            key=lambda x: x.force_quasi_static,
        )

    def get_all_regions(self) -> List[BodyRegion]:
        """Get list of all body regions."""
        return list(BodyRegion)

    def get_regions_by_sensitivity(self) -> List[Tuple[BodyRegion, float]]:
        """
        Get all regions sorted by sensitivity (lowest tolerance first).

        Returns:
            List of (region, quasi_static_force) tuples sorted by sensitivity
        """
        return sorted(
            [(r, l.force_quasi_static) for r, l in self._LIMITS.items()],
            key=lambda x: x[1],
        )

    def is_critical_region(self, region: BodyRegion) -> bool:
        """
        Check if a region is classified as critical.

        Critical regions (head, neck) require extra safety measures.
        """
        return region in self.CRITICAL_REGIONS

    def get_global_minimum_force(self, contact_type: str = "transient") -> float:
        """
        Get the minimum safe force across all body regions.

        This is the most conservative limit - if force stays below this,
        contact with any body part is considered safe.

        Args:
            contact_type: Either "transient" or "quasi_static"

        Returns:
            Minimum force limit in Newtons
        """
        if contact_type == "transient":
            return min(l.force_transient for l in self._LIMITS.values()) * self.safety_factor
        else:
            return min(l.force_quasi_static for l in self._LIMITS.values()) * self.safety_factor

    def estimate_impact_force(
        self,
        mass: float,
        velocity: float,
        contact_time: float = 0.1,
    ) -> float:
        """
        Estimate impact force from collision parameters.

        Simple momentum-based estimate: F = m * v / t

        Args:
            mass: Effective mass of impacting object (kg)
            velocity: Impact velocity (m/s)
            contact_time: Duration of contact (s), typically 0.05-0.2s

        Returns:
            Estimated impact force in Newtons
        """
        if contact_time <= 0:
            raise ValueError("contact_time must be positive")
        return (mass * velocity) / contact_time

    def check_impact_safety(
        self,
        region: BodyRegion,
        robot_mass: float,
        robot_velocity: float,
        contact_time: float = 0.1,
    ) -> Tuple[bool, float, float]:
        """
        Check if an impact would be safe for a given body region.

        Args:
            region: Body region that would be contacted
            robot_mass: Effective mass of robot part (kg)
            robot_velocity: Velocity at impact (m/s)
            contact_time: Estimated contact duration (s)

        Returns:
            Tuple of (is_safe, estimated_force, safe_limit)
        """
        estimated_force = self.estimate_impact_force(robot_mass, robot_velocity, contact_time)
        safe_limit = self.get_safe_force(region, "transient")
        is_safe = estimated_force <= safe_limit
        return is_safe, estimated_force, safe_limit


# Convenience functions

@lru_cache(maxsize=16)
def get_body_model(safety_factor: float = 1.0) -> HumanBodyModel:
    """
    Get a cached human body model instance.

    Uses LRU cache to avoid creating new instances for the same safety factor.
    For custom models, instantiate HumanBodyModel directly.

    Args:
        safety_factor: Safety margin multiplier (0.0-1.0)

    Returns:
        HumanBodyModel instance

    Raises:
        ValueError: If safety_factor is not in valid range
    """
    if not 0.0 <= safety_factor <= 1.0:
        raise ValueError(f"safety_factor must be 0.0-1.0, got {safety_factor}")
    return HumanBodyModel(safety_factor=safety_factor)


def is_contact_safe(
    region: BodyRegion,
    force: float,
    contact_type: str = "transient",
    safety_factor: float = 1.0,
) -> bool:
    """
    Quick check if a contact force is safe.

    Args:
        region: Body region being contacted
        force: Contact force in Newtons
        contact_type: "transient" or "quasi_static"
        safety_factor: Safety margin multiplier

    Returns:
        True if contact is safe
    """
    model = HumanBodyModel(safety_factor=safety_factor)
    return model.is_force_safe(region, force, contact_type)


__all__ = [
    "BodyRegion",
    "ContactLimits",
    "HumanBodyModel",
    "get_body_model",
    "is_contact_safe",
]
