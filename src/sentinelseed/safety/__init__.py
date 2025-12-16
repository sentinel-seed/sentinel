"""
Sentinel Safety Module

Provides safety validation for physical systems including robots and humanoids.

Submodules:
    - humanoid: Humanoid robot safety (ISO/TS 15066, balance, THSP)

Quick Start:
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

__all__ = [
    'humanoid',
]
