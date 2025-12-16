"""
Isaac Lab Integration Examples.

This module demonstrates how to use the Sentinel safety integration with
Isaac Lab environments. The examples can be run standalone (mock mode) or
with Isaac Lab installed.

Examples:
    1. Basic constraint validation
    2. Safety wrapper with clamp mode
    3. Safety wrapper with block mode
    4. Monitor mode for data collection
    5. Custom constraints for specific robots
    6. Batch validation for vectorized environments
    7. Training callback integration
    8. Isaac Lab environment integration (requires Isaac Lab)

Usage:
    python -m sentinelseed.integrations.isaac_lab.example

Note:
    Examples 1-7 run without Isaac Lab installed (mock mode).
    Example 8 requires Isaac Lab and NVIDIA Isaac Sim.
"""

import logging
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinelseed.isaac_lab.example")


def example_1_basic_constraints():
    """
    Example 1: Basic constraint validation.

    Demonstrates how to define and validate robot constraints.
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Constraint Validation")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.constraints import (
        JointLimits,
        WorkspaceLimits,
        ForceTorqueLimits,
        RobotConstraints,
        CollisionZone,
    )

    # Create constraints for Franka Panda
    joint_limits = JointLimits.franka_panda()
    print(f"Franka Panda joint limits: {joint_limits.num_joints} joints")
    print(f"  Position range: [{joint_limits.position_lower[0]:.2f}, {joint_limits.position_upper[0]:.2f}] rad (joint 0)")
    print(f"  Max velocity: {joint_limits.velocity_max[0]:.2f} rad/s (joint 0)")

    # Check valid positions
    valid_pos = [0.0, 0.0, 0.0, -1.5, 0.0, 1.5, 0.0]
    is_valid, violations = joint_limits.check_position(valid_pos)
    print(f"\nValid positions: is_valid={is_valid}")

    # Check invalid positions
    invalid_pos = [3.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]  # Joint 0 out of range
    is_valid, violations = joint_limits.check_position(invalid_pos)
    print(f"Invalid positions: is_valid={is_valid}")
    if violations:
        print(f"  Violations: {violations[0]}")

    # Create workspace limits
    workspace = WorkspaceLimits.franka_reach()
    print(f"\nWorkspace limits: X[{workspace.x_min}, {workspace.x_max}], Y[{workspace.y_min}, {workspace.y_max}]")

    # Check workspace
    in_workspace = workspace.contains(0.4, 0.0, 0.3)
    print(f"Point (0.4, 0.0, 0.3) in workspace: {in_workspace}")

    out_of_workspace = workspace.contains(1.5, 0.0, 0.3)
    print(f"Point (1.5, 0.0, 0.3) in workspace: {out_of_workspace}")

    # Combined constraints
    constraints = RobotConstraints(
        joint_limits=joint_limits,
        workspace_limits=workspace,
        force_torque_limits=ForceTorqueLimits.franka_contact(),
    )

    # Add collision zone
    constraints.add_collision_zone(
        CollisionZone.sphere("obstacle", center=(0.5, 0.2, 0.3), radius=0.1)
    )

    print(f"\nRobotConstraints configured with {len(constraints.collision_zones)} collision zone(s)")
    print("Example 1 complete.")


def example_2_clamp_mode():
    """
    Example 2: Safety wrapper with clamp mode.

    Demonstrates how actions are clamped to safe values.
    """
    print("\n" + "=" * 60)
    print("Example 2: Safety Wrapper - Clamp Mode")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints
    from sentinelseed.integrations.isaac_lab.validators import (
        THSPRobotValidator,
        ActionType,
    )

    # Create validator with normalized action type
    constraints = RobotConstraints.franka_default()
    validator = THSPRobotValidator(
        constraints=constraints,
        action_type=ActionType.NORMALIZED,
    )

    # Test with safe action
    safe_action = [0.1, -0.2, 0.3, 0.0, -0.1, 0.2, 0.0]
    result = validator.validate(safe_action)
    print(f"Safe action: is_safe={result.is_safe}, level={result.level.value}")
    print(f"  Gates: {result.gates}")

    # Test with unsafe action (out of normalized range)
    unsafe_action = [1.5, -0.2, 0.3, 0.0, -0.1, 0.2, 0.0]  # 1.5 > 1.0
    result = validator.validate(unsafe_action)
    print(f"\nUnsafe action: is_safe={result.is_safe}, level={result.level.value}")
    print(f"  Violations: {result.violations}")
    if result.modified_action:
        print(f"  Clamped action: {result.modified_action}")

    # Test with NaN/Inf
    invalid_action = [float('nan'), -0.2, 0.3, float('inf'), -0.1, 0.2, 0.0]
    result = validator.validate(invalid_action)
    print(f"\nInvalid action (NaN/Inf): is_safe={result.is_safe}, level={result.level.value}")
    print(f"  Violations: {result.violations[:2]}...")  # First 2 violations

    print("\nExample 2 complete.")


def example_3_block_mode():
    """
    Example 3: Safety wrapper with block mode.

    Demonstrates how dangerous actions are blocked entirely.
    """
    print("\n" + "=" * 60)
    print("Example 3: Safety Wrapper - Block Mode")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.constraints import (
        RobotConstraints,
        JointLimits,
    )
    from sentinelseed.integrations.isaac_lab.validators import (
        THSPRobotValidator,
        ActionType,
    )

    # Create validator in strict mode with high action scale
    constraints = RobotConstraints(
        joint_limits=JointLimits.franka_panda(),
        action_scale=3.0,  # Actions scaled by 3.0 (high for demonstration)
    )
    validator = THSPRobotValidator(
        constraints=constraints,
        action_type=ActionType.NORMALIZED,
        strict_mode=True,
    )

    # Safe action
    action = [0.2, -0.1, 0.0, 0.3, -0.2, 0.1, 0.0]
    result = validator.validate(action)
    print(f"Safe action: is_safe={result.is_safe}")

    # Dangerous action (exceeds velocity limits when scaled: 0.8 * 3.0 = 2.4 > 2.175)
    dangerous_action = [0.8, 0.8, 0.8, 0.8, 0.5, 0.5, 0.5]
    result = validator.validate(dangerous_action)
    print(f"\nDangerous action: is_safe={result.is_safe}, level={result.level.value}")
    print(f"  Reasoning: {result.reasoning}")

    print("\nExample 3 complete.")


def example_4_monitor_mode():
    """
    Example 4: Monitor mode for data collection.

    Demonstrates passive monitoring without intervention.
    """
    print("\n" + "=" * 60)
    print("Example 4: Monitor Mode (Passive Collection)")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints
    from sentinelseed.integrations.isaac_lab.validators import (
        THSPRobotValidator,
        ActionType,
    )

    # Create validator
    validator = THSPRobotValidator(
        constraints=RobotConstraints.franka_default(),
        action_type=ActionType.NORMALIZED,
        log_violations=False,  # Silent for monitoring
    )

    # Simulate training loop
    import random
    random.seed(42)

    for step in range(100):
        # Generate random action (some will be unsafe)
        action = [random.uniform(-1.2, 1.2) for _ in range(7)]
        result = validator.validate(action)

    # Get statistics
    stats = validator.get_stats()
    print(f"Total validated: {stats['total_validated']}")
    print(f"Total violations: {stats['total_violations']}")
    print(f"Violation rate: {stats['total_violations'] / stats['total_validated']:.2%}")
    print(f"Gate failures: {stats['gate_failures']}")

    print("\nExample 4 complete.")


def example_5_custom_robot():
    """
    Example 5: Custom constraints for specific robots.

    Demonstrates creating constraints for custom robot configurations.
    """
    print("\n" + "=" * 60)
    print("Example 5: Custom Robot Constraints")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.constraints import (
        JointLimits,
        WorkspaceLimits,
        ForceTorqueLimits,
        RobotConstraints,
        CollisionZone,
    )

    # Custom 4-DOF SCARA robot
    scara_joints = JointLimits(
        num_joints=4,
        position_lower=[-2.5, -2.5, 0.0, -3.14],  # Joint 3 is prismatic
        position_upper=[2.5, 2.5, 0.3, 3.14],
        velocity_max=[3.0, 3.0, 0.5, 4.0],
    )

    scara_workspace = WorkspaceLimits(
        x_min=-0.6, x_max=0.6,
        y_min=-0.6, y_max=0.6,
        z_min=0.0, z_max=0.3,
    )

    scara_constraints = RobotConstraints(
        joint_limits=scara_joints,
        workspace_limits=scara_workspace,
        action_scale=1.5,
    )

    # Add table collision zone
    scara_constraints.add_collision_zone(
        CollisionZone.box("table", center=(0.0, 0.0, -0.05), half_extents=(0.8, 0.8, 0.05))
    )

    print(f"SCARA robot: {scara_joints.num_joints} joints")
    print(f"Workspace: X[{scara_workspace.x_min}, {scara_workspace.x_max}]")
    print(f"Collision zones: {len(scara_constraints.collision_zones)}")

    # Also show UR10 preset
    ur10 = RobotConstraints.ur10_default()
    print(f"\nUR10 preset: {ur10.joint_limits.num_joints} joints")
    print(f"Max velocity: {ur10.joint_limits.velocity_max[0]:.3f} rad/s")

    print("\nExample 5 complete.")


def example_6_batch_validation():
    """
    Example 6: Batch validation for vectorized environments.

    Demonstrates efficient validation of multiple environments.
    """
    print("\n" + "=" * 60)
    print("Example 6: Batch Validation (Vectorized Environments)")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.constraints import RobotConstraints
    from sentinelseed.integrations.isaac_lab.validators import (
        THSPRobotValidator,
        ActionType,
    )

    try:
        import numpy as np
        has_numpy = True
    except ImportError:
        has_numpy = False
        print("NumPy not available, using lists")

    validator = THSPRobotValidator(
        constraints=RobotConstraints.franka_default(),
        action_type=ActionType.NORMALIZED,
        log_violations=False,
    )

    # Simulate batch of 8 environments
    num_envs = 8
    action_dim = 7

    if has_numpy:
        # Create batch with some unsafe actions
        actions = np.random.uniform(-0.8, 0.8, (num_envs, action_dim))
        actions[2, 0] = 1.5  # Make env 2 unsafe
        actions[5, 3] = float('nan')  # Make env 5 invalid
    else:
        import random
        random.seed(42)
        actions = [[random.uniform(-0.8, 0.8) for _ in range(action_dim)] for _ in range(num_envs)]
        actions[2][0] = 1.5
        actions[5][3] = float('nan')

    # Batch validate
    result = validator.validate_batch(actions)

    print(f"Batch size: {num_envs}")
    print(f"Any unsafe: {result.any_unsafe}")
    print(f"All unsafe: {result.all_unsafe}")
    print(f"Unsafe indices: {result.unsafe_indices}")
    print(f"Level: {result.level.value}")

    if has_numpy:
        print(f"Is safe per env: {result.is_safe}")
        print(f"Violations per env: {result.violations_per_env}")

    print("\nExample 6 complete.")


def example_7_training_callback():
    """
    Example 7: Training callback integration.

    Demonstrates how to use callbacks during RL training.
    """
    print("\n" + "=" * 60)
    print("Example 7: Training Callback Integration")
    print("=" * 60)

    from sentinelseed.integrations.isaac_lab.callbacks import (
        TrainingMetrics,
        SentinelSB3Callback,
    )

    # Create mock environment (in real usage, this would be Isaac Lab env)
    class MockEnv:
        def __init__(self):
            self.num_envs = 4

    # Create metrics
    metrics = TrainingMetrics()

    # Simulate training
    for step in range(100):
        metrics.steps = step
        if step % 10 == 0:
            metrics.violations += 1
            metrics.violations_by_gate["harm"] += 1

    metrics.episodes = 10
    metrics.unsafe_episodes = 3

    # Get metrics dict
    metrics_dict = metrics.to_dict()
    print("Training Metrics:")
    print(f"  Steps: {metrics_dict['sentinel/steps']}")
    print(f"  Violation rate: {metrics_dict['sentinel/violation_rate']:.2%}")
    print(f"  Unsafe episode rate: {metrics_dict['sentinel/unsafe_episode_rate']:.2%}")
    print(f"  Gate violations: harm={metrics_dict['sentinel/gate_harm_violations']}")

    # Show callback creation (won't run without env)
    print("\nCallback creation (mock):")
    print("  callback = SentinelSB3Callback(env, log_interval=100)")
    print("  model.learn(callback=callback.get_sb3_callback())")

    print("\nExample 7 complete.")


def example_8_isaac_lab():
    """
    Example 8: Full Isaac Lab integration.

    NOTE: This requires Isaac Lab to be installed.
    """
    print("\n" + "=" * 60)
    print("Example 8: Isaac Lab Environment Integration")
    print("=" * 60)

    try:
        # Check if Isaac Lab is available
        from isaaclab.app import AppLauncher
        ISAAC_LAB_AVAILABLE = True
    except ImportError:
        ISAAC_LAB_AVAILABLE = False

    if not ISAAC_LAB_AVAILABLE:
        print("Isaac Lab not installed. Showing usage pattern instead.\n")
        print("""
# Full Isaac Lab usage example:

from isaaclab.app import AppLauncher

# Initialize simulation
app_launcher = AppLauncher(headless=True)
simulation_app = app_launcher.app

import gymnasium as gym
import isaaclab_tasks
from isaaclab_tasks.utils import load_cfg_from_registry

from sentinelseed.integrations.isaac_lab import (
    SentinelSafetyWrapper,
    RobotConstraints,
    SafetyMode,
)

# Create environment
cfg = load_cfg_from_registry("Isaac-Reach-Franka-v0", "env_cfg_entry_point")
env = gym.make("Isaac-Reach-Franka-v0", cfg=cfg)

# Wrap with safety
env = SentinelSafetyWrapper(
    env,
    constraints=RobotConstraints.franka_default(),
    mode=SafetyMode.CLAMP,
)

# Run training (example with SB3)
from stable_baselines3 import PPO
from sentinelseed.integrations.isaac_lab import SentinelSB3Callback

model = PPO("MlpPolicy", env, verbose=1)
callback = SentinelSB3Callback(env, log_interval=1000)
model.learn(total_timesteps=100000, callback=callback.get_sb3_callback())

# Get safety statistics
print(env.get_stats())

simulation_app.close()
""")
    else:
        print("Isaac Lab is available. See README.md for full usage.")

    print("\nExample 8 complete.")


def run_all_examples():
    """Run all examples."""
    print("\n" + "=" * 60)
    print("Sentinel Isaac Lab Integration Examples")
    print("=" * 60)
    print("\nRunning all examples...\n")

    try:
        example_1_basic_constraints()
        example_2_clamp_mode()
        example_3_block_mode()
        example_4_monitor_mode()
        example_5_custom_robot()
        example_6_batch_validation()
        example_7_training_callback()
        example_8_isaac_lab()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\nExample failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    run_all_examples()
