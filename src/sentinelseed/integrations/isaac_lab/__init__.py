"""
Sentinel Isaac Lab Integration - Safety Middleware for Robot Learning.

This integration provides THSP-based safety validation for Isaac Lab
robot learning environments. It wraps gymnasium environments to validate
actions through safety gates before they are executed.

Architecture:
    [RL Agent] --action--> [SentinelSafetyWrapper] --validated--> [Isaac Lab Env]
                                    |
                                    v
                            [THSP Validation]
                            - Truth: Valid action?
                            - Harm: Dangerous velocity/force?
                            - Scope: Within workspace?
                            - Purpose: Legitimate goal?

Modules:
    - constraints: Robot safety constraints (joint limits, workspace, etc.)
    - validators: THSP validation for robot actions
    - wrappers: Gymnasium wrappers for safety enforcement
    - callbacks: Training callbacks for RL frameworks

Quick Start:
    from sentinelseed.integrations.isaac_lab import (
        SentinelSafetyWrapper,
        RobotConstraints,
    )

    # Wrap your Isaac Lab environment
    env = SentinelSafetyWrapper(
        base_env,
        constraints=RobotConstraints.franka_default(),
        mode="clamp",  # or "block", "warn", "monitor"
    )

    # Actions are now validated through THSP gates
    obs, reward, done, truncated, info = env.step(action)

Requirements:
    - gymnasium (or gym) for wrapper base
    - torch or numpy for tensor operations
    - Isaac Lab (optional, for full environment support)
    - stable-baselines3 (optional, for SB3 callbacks)

References:
    - Isaac Lab: https://isaac-sim.github.io/IsaacLab/
    - Gymnasium Wrappers: https://gymnasium.farama.org/
    - Safe RL: https://arxiv.org/abs/2108.06266
"""

# Constraints
from sentinelseed.integrations.isaac_lab.constraints import (
    JointLimits,
    WorkspaceLimits,
    ForceTorqueLimits,
    CollisionZone,
    RobotConstraints,
    ConstraintViolationType,
)

# Validators
from sentinelseed.integrations.isaac_lab.validators import (
    THSPRobotValidator,
    ActionValidationResult,
    BatchValidationResult,
    SafetyLevel,
    ActionType,
)

# Wrappers
from sentinelseed.integrations.isaac_lab.wrappers import (
    SentinelSafetyWrapper,
    ActionClampingWrapper,
    SafetyMonitorWrapper,
    SafetyMode,
    SafetyStatistics,
)

# Callbacks
from sentinelseed.integrations.isaac_lab.callbacks import (
    SentinelCallback,
    SentinelSB3Callback,
    SentinelRLGamesCallback,
    TrainingMetrics,
    create_wandb_callback,
    create_tensorboard_callback,
)

__all__ = [
    # Constraints
    'JointLimits',
    'WorkspaceLimits',
    'ForceTorqueLimits',
    'CollisionZone',
    'RobotConstraints',
    'ConstraintViolationType',
    # Validators
    'THSPRobotValidator',
    'ActionValidationResult',
    'BatchValidationResult',
    'SafetyLevel',
    'ActionType',
    # Wrappers
    'SentinelSafetyWrapper',
    'ActionClampingWrapper',
    'SafetyMonitorWrapper',
    'SafetyMode',
    'SafetyStatistics',
    # Callbacks
    'SentinelCallback',
    'SentinelSB3Callback',
    'SentinelRLGamesCallback',
    'TrainingMetrics',
    'create_wandb_callback',
    'create_tensorboard_callback',
]
