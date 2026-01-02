"""
Sentinel Safety Module

Provides safety validation for physical systems including robots and humanoids.

Base Classes (safety.base):
    - SafetyLevel: Universal safety classification enum
    - ViolationType: Types of safety violations
    - SafetyResult: Base result class for all validations
    - SafetyValidator: Abstract base class for validators

Submodules:
    - humanoid: Humanoid robot safety (ISO/TS 15066, balance, THSP)
    - mobile: Mobile robot safety (velocity limits, spatial zones) [via integrations]
    - simulation: Simulation safety (batch validation, RL) [via integrations]

Quick Start (Base Classes):
    from sentinelseed.safety import (
        SafetyLevel,
        ViolationType,
        SafetyResult,
        SafetyValidator,
    )

    # Create a custom validator
    class MyValidator(SafetyValidator):
        def validate(self, action, context=None):
            if action.is_valid():
                return SafetyResult.safe()
            return SafetyResult.unsafe(
                level=SafetyLevel.DANGEROUS,
                violations=["Invalid action"],
            )

Quick Start (Humanoid):
    from sentinelseed.safety.humanoid import (
        HumanoidSafetyValidator,
        HumanoidAction,
        tesla_optimus,
        boston_dynamics_atlas,
        figure_02,
    )

    # Create validator for Tesla Optimus
    validator = HumanoidSafetyValidator(
        constraints=tesla_optimus(environment="industrial"),
    )

    # Validate an action
    action = HumanoidAction(
        joint_velocities={"left_elbow_pitch": 1.5},
        purpose="Pick up object",
    )

    result = validator.validate(action)
    if not result.is_safe:
        print(f"Blocked: {result.reasoning}")
"""

# Base classes - available at top level
from sentinelseed.safety.base import (
    SafetyLevel,
    ViolationType,
    SafetyResult,
    SafetyValidator,
)

__all__ = [
    # Base classes
    "SafetyLevel",
    "ViolationType",
    "SafetyResult",
    "SafetyValidator",
    # Submodules
    "humanoid",
    "mobile",
    "simulation",
]
