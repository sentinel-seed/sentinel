"""
Humanoid Robot Safety Module.

This module provides safety validation for humanoid robots, implementing:
- ISO/TS 15066 compliant contact force limits
- Humanoid-specific kinematic constraints
- Balance monitoring and fall detection
- THSP validation for humanoid actions
- Pre-configured presets for popular humanoids

Supported Platforms:
    - Tesla Optimus (Gen 2)
    - Boston Dynamics Atlas (Electric)
    - Figure 02
    - Generic humanoid configuration

Quick Start:
    from sentinelseed.safety.humanoid import (
        HumanoidSafetyValidator,
        HumanoidAction,
        tesla_optimus,
    )

    # Create validator with Optimus constraints
    validator = HumanoidSafetyValidator(
        constraints=tesla_optimus(environment="industrial"),
    )

    # Validate an action
    action = HumanoidAction(
        joint_velocities={"left_elbow_pitch": 2.0},
        purpose="Pick up part from conveyor",
    )

    result = validator.validate(action)
    if result.is_safe:
        print("Action approved")
    else:
        print(f"Blocked: {result.reasoning}")

References:
    - ISO 10218:2025 - Industrial robot safety
    - ISO 13482 - Personal care robot safety
    - ISO/TS 15066 - Collaborative robot safety
    - PMC8850785 - Biomechanical force limits study
"""

# Body model - ISO/TS 15066 contact force limits
from sentinelseed.safety.humanoid.body_model import (
    BodyRegion,
    ContactLimits,
    HumanBodyModel,
)

# Constraints - Humanoid kinematics and operational limits
from sentinelseed.safety.humanoid.constraints import (
    HumanoidLimb,
    JointType,
    JointSpec,
    LimbSpec,
    OperationalLimits,
    SafetyZone,
    HumanoidConstraints,
    create_generic_humanoid,
)

# Balance - ZMP/CoM monitoring and fall detection
from sentinelseed.safety.humanoid.balance import (
    # Constants
    DEFAULT_MAX_HISTORY,
    DEFAULT_ZMP_MARGIN_WARNING,
    DEFAULT_ZMP_MARGIN_CRITICAL,
    DEFAULT_MAX_TILT_ANGLE,
    DEFAULT_MAX_ANGULAR_RATE,
    DEFAULT_MAX_COM_VELOCITY,
    DEFAULT_FALL_DETECTION_THRESHOLD,
    DEFAULT_MIN_COM_HEIGHT_RATIO,
    DEFAULT_PREDICTION_HORIZON,
    # Enums
    BalanceState,
    SafeState,
    FallDirection,
    # Data classes
    ZMPState,
    CoMState,
    IMUReading,
    BalanceMonitorConfig,
    BalanceAssessment,
    # Classes
    BalanceMonitor,
    SafeStateManager,
)

# Validators - THSP validation for humanoid actions
from sentinelseed.safety.humanoid.validators import (
    SafetyLevel,
    ViolationType,
    HumanoidAction,
    ValidationResult,
    HumanoidSafetyValidator,
    validate_humanoid_action,
)

# Presets - Pre-configured humanoid robots
from sentinelseed.safety.humanoid.presets import (
    tesla_optimus,
    boston_dynamics_atlas,
    figure_02,
    get_preset,
    list_presets,
)


__version__ = "1.0.0"

__all__ = [
    # Version
    "__version__",
    # Body model
    "BodyRegion",
    "ContactLimits",
    "HumanBodyModel",
    # Constraints
    "HumanoidLimb",
    "JointType",
    "JointSpec",
    "LimbSpec",
    "OperationalLimits",
    "SafetyZone",
    "HumanoidConstraints",
    "create_generic_humanoid",
    # Balance constants
    "DEFAULT_MAX_HISTORY",
    "DEFAULT_ZMP_MARGIN_WARNING",
    "DEFAULT_ZMP_MARGIN_CRITICAL",
    "DEFAULT_MAX_TILT_ANGLE",
    "DEFAULT_MAX_ANGULAR_RATE",
    "DEFAULT_MAX_COM_VELOCITY",
    "DEFAULT_FALL_DETECTION_THRESHOLD",
    "DEFAULT_MIN_COM_HEIGHT_RATIO",
    "DEFAULT_PREDICTION_HORIZON",
    # Balance enums and classes
    "BalanceState",
    "SafeState",
    "FallDirection",
    "ZMPState",
    "CoMState",
    "IMUReading",
    "BalanceMonitorConfig",
    "BalanceAssessment",
    "BalanceMonitor",
    "SafeStateManager",
    # Validators
    "SafetyLevel",
    "ViolationType",
    "HumanoidAction",
    "ValidationResult",
    "HumanoidSafetyValidator",
    "validate_humanoid_action",
    # Presets
    "tesla_optimus",
    "boston_dynamics_atlas",
    "figure_02",
    "get_preset",
    "list_presets",
]
