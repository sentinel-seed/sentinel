"""
Gymnasium Wrappers for Isaac Lab Safety.

This module provides gymnasium-compatible wrappers that add THSP safety
validation to Isaac Lab environments. The wrappers intercept actions
before they are applied and validate them through safety gates.

Wrappers:
    - SentinelSafetyWrapper: Main safety wrapper with full THSP validation
    - ActionClampingWrapper: Simple wrapper that only clamps actions
    - SafetyMonitorWrapper: Non-blocking wrapper for monitoring only

Usage:
    import gymnasium as gym
    from sentinelseed.integrations.isaac_lab import SentinelSafetyWrapper

    env = gym.make("Isaac-Reach-Franka-v0", cfg=cfg)
    env = SentinelSafetyWrapper(env, mode="clamp")
    # Now all actions are validated before execution

References:
    - Isaac Lab Wrapping: https://isaac-sim.github.io/IsaacLab/main/source/how-to/wrap_rl_env.html
    - Gymnasium Wrappers: https://gymnasium.farama.org/tutorials/gymnasium_basics/implementing_custom_wrappers/
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from sentinelseed.integrations.isaac_lab.constraints import (
    RobotConstraints,
    JointLimits,
    WorkspaceLimits,
)
from sentinelseed.integrations.isaac_lab.validators import (
    THSPRobotValidator,
    ActionValidationResult,
    BatchValidationResult,
    SafetyLevel,
    ActionType,
)

logger = logging.getLogger("sentinelseed.isaac_lab")

# Try to import gymnasium
try:
    import gymnasium as gym
    from gymnasium import Wrapper
    from gymnasium.core import ActType, ObsType
    GYMNASIUM_AVAILABLE = True
except (ImportError, AttributeError):
    GYMNASIUM_AVAILABLE = False
    gym = None

    # Mock Wrapper class
    class Wrapper:
        def __init__(self, env):
            self.env = env

        def step(self, action):
            return self.env.step(action)

        def reset(self, **kwargs):
            return self.env.reset(**kwargs)

        @property
        def unwrapped(self):
            return self.env.unwrapped if hasattr(self.env, 'unwrapped') else self.env

# Try to import torch
try:
    import torch
    TORCH_AVAILABLE = True
except (ImportError, AttributeError):
    TORCH_AVAILABLE = False
    torch = None

# Try to import numpy
try:
    import numpy as np
    NUMPY_AVAILABLE = True
except (ImportError, AttributeError):
    NUMPY_AVAILABLE = False
    np = None


class SafetyMode(Enum):
    """
    Safety enforcement mode.

    Modes:
        - BLOCK: Reject unsafe actions entirely (use zero or previous action)
        - CLAMP: Project unsafe actions to safe region
        - WARN: Log violations but execute action unchanged
        - MONITOR: Collect statistics without any intervention
    """
    BLOCK = "block"
    CLAMP = "clamp"
    WARN = "warn"
    MONITOR = "monitor"


@dataclass
class SafetyStatistics:
    """
    Statistics collected by the safety wrapper.

    Attributes:
        total_steps: Total number of environment steps
        violations_total: Total number of safety violations
        violations_by_gate: Violations per THSP gate
        actions_blocked: Number of actions that were blocked
        actions_clamped: Number of actions that were clamped
        episodes_with_violations: Number of episodes with at least one violation
        current_episode_violations: Violations in current episode
    """
    total_steps: int = 0
    violations_total: int = 0
    violations_by_gate: Dict[str, int] = field(default_factory=lambda: {
        "truth": 0, "harm": 0, "scope": 0, "purpose": 0
    })
    actions_blocked: int = 0
    actions_clamped: int = 0
    episodes_with_violations: int = 0
    current_episode_violations: int = 0
    _current_episode_had_violation: bool = False

    def record_violation(self, result: ActionValidationResult):
        """Record a validation result with violations."""
        self.violations_total += 1
        self.current_episode_violations += 1

        for gate, passed in result.gates.items():
            if not passed:
                self.violations_by_gate[gate] += 1

        if not self._current_episode_had_violation:
            self._current_episode_had_violation = True
            self.episodes_with_violations += 1

    def record_block(self):
        """Record an action that was blocked."""
        self.actions_blocked += 1

    def record_clamp(self):
        """Record an action that was clamped."""
        self.actions_clamped += 1

    def step(self):
        """Record a step."""
        self.total_steps += 1

    def episode_reset(self):
        """Reset episode-level counters."""
        self.current_episode_violations = 0
        self._current_episode_had_violation = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "total_steps": self.total_steps,
            "violations_total": self.violations_total,
            "violations_by_gate": self.violations_by_gate.copy(),
            "actions_blocked": self.actions_blocked,
            "actions_clamped": self.actions_clamped,
            "episodes_with_violations": self.episodes_with_violations,
            "violation_rate": (
                self.violations_total / self.total_steps
                if self.total_steps > 0 else 0.0
            ),
        }


class SentinelSafetyWrapper(Wrapper):
    """
    Main safety wrapper for Isaac Lab environments.

    This wrapper intercepts actions in the step() method and validates them
    through THSP gates. Depending on the mode, it can block, clamp, or just
    warn about unsafe actions.

    The wrapper is compatible with Isaac Lab's ManagerBasedRLEnv and DirectRLEnv
    classes, as well as any gymnasium-compatible environment.

    Args:
        env: The environment to wrap
        constraints: Robot safety constraints
        mode: Safety enforcement mode ('block', 'clamp', 'warn', 'monitor')
        action_type: Type of actions (for validation)
        on_violation: Optional callback for violations
        log_violations: Log violations to console
        add_safety_info: Add safety info to step() extras dict

    Example:
        # Basic usage
        env = gym.make("Isaac-Reach-Franka-v0", cfg=cfg)
        env = SentinelSafetyWrapper(
            env,
            constraints=RobotConstraints.franka_default(),
            mode="clamp",
        )

        # With custom callback
        def on_violation(result):
            print(f"Violation: {result.reasoning}")

        env = SentinelSafetyWrapper(
            env,
            constraints=RobotConstraints.franka_default(),
            mode="warn",
            on_violation=on_violation,
        )
    """

    def __init__(
        self,
        env: Any,
        constraints: Optional[RobotConstraints] = None,
        mode: Union[str, SafetyMode] = SafetyMode.CLAMP,
        action_type: ActionType = ActionType.NORMALIZED,
        on_violation: Optional[Callable[[ActionValidationResult], None]] = None,
        log_violations: bool = True,
        add_safety_info: bool = True,
    ):
        super().__init__(env)

        # Parse mode
        if isinstance(mode, str):
            mode = SafetyMode(mode.lower())
        self.mode = mode

        # Create validator
        self.constraints = constraints or RobotConstraints()
        self.validator = THSPRobotValidator(
            constraints=self.constraints,
            action_type=action_type,
            strict_mode=(mode == SafetyMode.BLOCK),
            log_violations=log_violations,
        )

        self.on_violation = on_violation
        self.add_safety_info = add_safety_info

        # Statistics
        self.stats = SafetyStatistics()

        # Store last action for block mode
        self._last_safe_action = None
        self._num_envs = self._get_num_envs()

        logger.info(
            f"SentinelSafetyWrapper initialized: mode={mode.value}, "
            f"num_envs={self._num_envs}"
        )

    def _get_num_envs(self) -> int:
        """Get number of parallel environments."""
        if hasattr(self.env, 'num_envs'):
            return self.env.num_envs
        elif hasattr(self.env, 'unwrapped') and hasattr(self.env.unwrapped, 'num_envs'):
            return self.env.unwrapped.num_envs
        return 1

    def step(
        self,
        action: Any,
    ) -> Tuple[Any, Any, Any, Any, Dict[str, Any]]:
        """
        Execute one environment step with safety validation.

        Args:
            action: The action to execute

        Returns:
            Tuple of (observation, reward, terminated, truncated, info)
            where info may contain safety information if add_safety_info=True
        """
        self.stats.step()

        # Build context for validation
        context = self._build_context()

        # Validate action
        if self._num_envs > 1:
            # Build contexts for each environment in the batch
            contexts = self._build_batch_contexts()
            result = self.validator.validate_batch(action, contexts=contexts)
            is_safe = not result.any_unsafe
            modified_action = result.modified_actions
            level = result.level
        else:
            result = self.validator.validate(action, context)
            is_safe = result.is_safe
            modified_action = result.modified_action
            level = result.level

        # Handle unsafe action based on mode
        action_to_use = action

        if not is_safe:
            if isinstance(result, ActionValidationResult):
                self.stats.record_violation(result)

            if self.on_violation:
                self.on_violation(result)

            if self.mode == SafetyMode.BLOCK:
                self.stats.record_block()
                action_to_use = self._get_blocked_action(action)

            elif self.mode == SafetyMode.CLAMP:
                if modified_action is not None:
                    self.stats.record_clamp()
                    action_to_use = modified_action

            elif self.mode == SafetyMode.WARN:
                # Log but don't modify
                if isinstance(result, ActionValidationResult):
                    logger.warning(f"Unsafe action: {result.reasoning}")

            # MONITOR mode: do nothing

        # Store last safe action
        if is_safe or self.mode == SafetyMode.CLAMP:
            self._last_safe_action = action_to_use

        # Execute step
        obs, reward, terminated, truncated, info = self.env.step(action_to_use)

        # Add safety info to extras
        if self.add_safety_info:
            info = self._add_safety_info(info, result, action_to_use, action)

        return obs, reward, terminated, truncated, info

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Any, Dict[str, Any]]:
        """
        Reset the environment and clear episode-level statistics.

        Args:
            seed: Random seed
            options: Reset options

        Returns:
            Tuple of (observation, info)
        """
        self.stats.episode_reset()
        self._last_safe_action = None

        return self.env.reset(seed=seed, options=options)

    def _build_context(self) -> Dict[str, Any]:
        """Build context dict for validation from environment state."""
        context = {}

        # Try to get current joint state
        unwrapped = self.env.unwrapped if hasattr(self.env, 'unwrapped') else self.env

        if hasattr(unwrapped, 'scene'):
            scene = unwrapped.scene
            # Get articulation if available
            if hasattr(scene, 'articulations'):
                for name, articulation in scene.articulations.items():
                    if hasattr(articulation, 'data'):
                        data = articulation.data
                        # Check joint_pos exists and has at least one element
                        if hasattr(data, 'joint_pos') and len(data.joint_pos) > 0:
                            context['current_joint_position'] = data.joint_pos[0]
                        # Check joint_vel exists and has at least one element
                        if hasattr(data, 'joint_vel') and len(data.joint_vel) > 0:
                            context['current_joint_velocity'] = data.joint_vel[0]
                        break

        # Get physics dt
        if hasattr(unwrapped, 'physics_dt'):
            context['dt'] = unwrapped.physics_dt
        elif hasattr(unwrapped, 'cfg') and hasattr(unwrapped.cfg, 'sim'):
            context['dt'] = unwrapped.cfg.sim.dt

        return context

    def _build_batch_contexts(self) -> Optional[List[Dict[str, Any]]]:
        """
        Build context dicts for each environment in a vectorized batch.

        Returns:
            List of context dicts, one per environment, or None if unavailable.
        """
        unwrapped = self.env.unwrapped if hasattr(self.env, 'unwrapped') else self.env

        # Get physics dt (shared across all envs)
        dt = None
        if hasattr(unwrapped, 'physics_dt'):
            dt = unwrapped.physics_dt
        elif hasattr(unwrapped, 'cfg') and hasattr(unwrapped.cfg, 'sim'):
            dt = unwrapped.cfg.sim.dt

        contexts = []

        # Try to get per-environment state from Isaac Lab scene
        if hasattr(unwrapped, 'scene'):
            scene = unwrapped.scene
            if hasattr(scene, 'articulations'):
                for name, articulation in scene.articulations.items():
                    if hasattr(articulation, 'data'):
                        data = articulation.data
                        # Build context for each environment
                        for i in range(self._num_envs):
                            ctx = {}
                            if dt is not None:
                                ctx['dt'] = dt

                            # Get joint state for this environment
                            if hasattr(data, 'joint_pos') and len(data.joint_pos) > i:
                                ctx['current_joint_position'] = data.joint_pos[i]
                            if hasattr(data, 'joint_vel') and len(data.joint_vel) > i:
                                ctx['current_joint_velocity'] = data.joint_vel[i]

                            contexts.append(ctx)
                        break

        # If we couldn't get per-env contexts, return None (validator will handle)
        if len(contexts) != self._num_envs:
            return None

        return contexts

    def _get_blocked_action(self, action: Any) -> Any:
        """Get action to use when blocking."""
        # Use last safe action if available
        if self._last_safe_action is not None:
            return self._last_safe_action

        # Otherwise use zero action
        if TORCH_AVAILABLE and isinstance(action, torch.Tensor):
            return torch.zeros_like(action)
        elif NUMPY_AVAILABLE and isinstance(action, np.ndarray):
            return np.zeros_like(action)
        else:
            return [0.0] * len(action)

    def _add_safety_info(
        self,
        info: Dict[str, Any],
        result: Union[ActionValidationResult, BatchValidationResult],
        action_used: Any,
        original_action: Any,
    ) -> Dict[str, Any]:
        """Add safety information to info dict."""
        if info is None:
            info = {}

        if isinstance(result, ActionValidationResult):
            info["sentinel_safety"] = {
                "is_safe": result.is_safe,
                "level": result.level.value,
                "gates": result.gates,
                "violations": result.violations,
                "action_modified": result.modified_action is not None,
            }
        else:
            info["sentinel_safety"] = {
                "any_unsafe": result.any_unsafe,
                "num_unsafe": result.num_unsafe,
                "level": result.level.value,
                "unsafe_indices": result.unsafe_indices,
            }

        return info

    def get_stats(self) -> Dict[str, Any]:
        """Get safety statistics."""
        return self.stats.to_dict()

    def get_validator_stats(self) -> Dict[str, Any]:
        """Get validator-level statistics."""
        return self.validator.get_stats()


class ActionClampingWrapper(Wrapper):
    """
    Simple wrapper that only clamps actions to safe ranges.

    This is a lightweight alternative to SentinelSafetyWrapper when
    you only need action clamping without full THSP validation.

    Args:
        env: The environment to wrap
        joint_limits: Joint position/velocity limits
        clamp_to_normalized: Clamp to [-1, 1] for normalized actions

    Example:
        env = gym.make("Isaac-Reach-Franka-v0", cfg=cfg)
        env = ActionClampingWrapper(
            env,
            joint_limits=JointLimits.franka_panda(),
        )
    """

    def __init__(
        self,
        env: Any,
        joint_limits: Optional[JointLimits] = None,
        clamp_to_normalized: bool = True,
    ):
        super().__init__(env)
        self.joint_limits = joint_limits
        self.clamp_to_normalized = clamp_to_normalized

    def step(self, action: Any) -> Tuple[Any, Any, Any, Any, Dict[str, Any]]:
        """Execute step with clamped action."""
        clamped = self._clamp_action(action)
        return self.env.step(clamped)

    def _clamp_action(self, action: Any) -> Any:
        """Clamp action to safe range."""
        if self.clamp_to_normalized:
            if TORCH_AVAILABLE and isinstance(action, torch.Tensor):
                action = torch.clamp(action, -1.0, 1.0)
            elif NUMPY_AVAILABLE and isinstance(action, np.ndarray):
                action = np.clip(action, -1.0, 1.0)
            else:
                action = [max(-1.0, min(1.0, a)) for a in action]

        if self.joint_limits:
            action = self.joint_limits.clamp_velocity(action)

        return action


class SafetyMonitorWrapper(Wrapper):
    """
    Non-blocking wrapper that monitors safety without intervening.

    Useful for collecting safety statistics during training without
    affecting the learning process.

    Args:
        env: The environment to wrap
        constraints: Robot safety constraints
        on_violation: Callback for violations
        log_interval: Log statistics every N steps (0 to disable)

    Example:
        def on_violation(result):
            wandb.log({"safety_violation": 1})

        env = SafetyMonitorWrapper(
            env,
            constraints=RobotConstraints.franka_default(),
            on_violation=on_violation,
            log_interval=1000,
        )
    """

    def __init__(
        self,
        env: Any,
        constraints: Optional[RobotConstraints] = None,
        on_violation: Optional[Callable[[ActionValidationResult], None]] = None,
        log_interval: int = 0,
    ):
        super().__init__(env)

        self.validator = THSPRobotValidator(
            constraints=constraints or RobotConstraints(),
            log_violations=False,
        )
        self.on_violation = on_violation
        self.log_interval = log_interval
        self.stats = SafetyStatistics()

    def step(self, action: Any) -> Tuple[Any, Any, Any, Any, Dict[str, Any]]:
        """Execute step and monitor safety."""
        self.stats.step()

        # Validate without modifying
        result = self.validator.validate(action)

        if not result.is_safe:
            self.stats.record_violation(result)
            if self.on_violation:
                self.on_violation(result)

        # Log periodically
        if self.log_interval > 0 and self.stats.total_steps % self.log_interval == 0:
            logger.info(f"Safety stats: {self.stats.to_dict()}")

        # Execute original action unchanged
        return self.env.step(action)

    def reset(self, **kwargs) -> Tuple[Any, Dict[str, Any]]:
        """Reset environment and episode stats."""
        self.stats.episode_reset()
        return self.env.reset(**kwargs)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitoring statistics."""
        return self.stats.to_dict()
