"""
Training Callbacks for Isaac Lab RL Frameworks.

This module provides callbacks that can be used with popular RL frameworks
to monitor safety during training. The callbacks collect statistics about
safety violations and can be used for logging to tensorboard, wandb, etc.

Callbacks:
    - SentinelCallback: Base callback class
    - SentinelSB3Callback: Callback for Stable-Baselines3
    - SentinelRLGamesCallback: Callback for RL-Games
    - create_wandb_callback: Factory for WandB logging callback

Usage:
    # With Stable-Baselines3
    from sentinelseed.integrations.isaac_lab import SentinelSB3Callback

    callback = SentinelSB3Callback(env, log_interval=100)
    model.learn(total_timesteps=10000, callback=callback)

References:
    - Isaac Lab Training: https://isaac-sim.github.io/IsaacLab/main/source/tutorials/03_envs/run_rl_training.html
    - SB3 Callbacks: https://stable-baselines3.readthedocs.io/en/master/guide/callbacks.html
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Union

from sentinelseed.integrations.isaac_lab.validators import (
    ActionValidationResult,
    SafetyLevel,
)
from sentinelseed.integrations.isaac_lab.wrappers import (
    SentinelSafetyWrapper,
    SafetyStatistics,
)

logger = logging.getLogger("sentinelseed.isaac_lab")


@dataclass
class TrainingMetrics:
    """
    Aggregated training metrics for logging.

    Attributes:
        steps: Total training steps
        episodes: Total episodes
        violation_rate: Violations per step
        violations_by_gate: Count per THSP gate
        block_rate: Actions blocked per step
        clamp_rate: Actions clamped per step
        unsafe_episode_rate: Episodes with violations
    """
    steps: int = 0
    episodes: int = 0
    violations: int = 0
    violations_by_gate: Dict[str, int] = field(default_factory=lambda: {
        "truth": 0, "harm": 0, "scope": 0, "purpose": 0
    })
    blocked: int = 0
    clamped: int = 0
    unsafe_episodes: int = 0

    @property
    def violation_rate(self) -> float:
        """Violations per step."""
        return self.violations / max(1, self.steps)

    @property
    def block_rate(self) -> float:
        """Blocked actions per step."""
        return self.blocked / max(1, self.steps)

    @property
    def clamp_rate(self) -> float:
        """Clamped actions per step."""
        return self.clamped / max(1, self.steps)

    @property
    def unsafe_episode_rate(self) -> float:
        """Episodes with violations per total episodes."""
        return self.unsafe_episodes / max(1, self.episodes)

    def to_dict(self) -> Dict[str, float]:
        """Convert to dict for logging."""
        return {
            "sentinel/steps": self.steps,
            "sentinel/episodes": self.episodes,
            "sentinel/violations": self.violations,
            "sentinel/violation_rate": self.violation_rate,
            "sentinel/blocked": self.blocked,
            "sentinel/block_rate": self.block_rate,
            "sentinel/clamped": self.clamped,
            "sentinel/clamp_rate": self.clamp_rate,
            "sentinel/unsafe_episodes": self.unsafe_episodes,
            "sentinel/unsafe_episode_rate": self.unsafe_episode_rate,
            "sentinel/gate_truth_violations": self.violations_by_gate["truth"],
            "sentinel/gate_harm_violations": self.violations_by_gate["harm"],
            "sentinel/gate_scope_violations": self.violations_by_gate["scope"],
            "sentinel/gate_purpose_violations": self.violations_by_gate["purpose"],
        }

    def update_from_stats(self, stats: Dict[str, Any]):
        """Update metrics from SafetyStatistics dict."""
        self.steps = stats.get("total_steps", self.steps)
        self.violations = stats.get("violations_total", self.violations)
        self.blocked = stats.get("actions_blocked", self.blocked)
        self.clamped = stats.get("actions_clamped", self.clamped)
        self.unsafe_episodes = stats.get("episodes_with_violations", self.unsafe_episodes)

        gate_violations = stats.get("violations_by_gate", {})
        for gate in ["truth", "harm", "scope", "purpose"]:
            if gate in gate_violations:
                self.violations_by_gate[gate] = gate_violations[gate]


class SentinelCallback(ABC):
    """
    Base callback class for RL training monitoring.

    Subclasses should implement framework-specific methods.

    Args:
        env: Environment wrapped with SentinelSafetyWrapper
        log_interval: Log metrics every N steps
        on_log: Optional callback for logging
    """

    def __init__(
        self,
        env: Any,
        log_interval: int = 100,
        on_log: Optional[Callable[[Dict[str, float]], None]] = None,
    ):
        self.env = env
        self.log_interval = log_interval
        self.on_log = on_log
        self.metrics = TrainingMetrics()
        self._last_log_step = 0

        # Find the safety wrapper
        self.safety_wrapper = self._find_safety_wrapper(env)
        if self.safety_wrapper is None:
            logger.warning(
                "No SentinelSafetyWrapper found in environment chain. "
                "Callback will have limited functionality."
            )

    def _find_safety_wrapper(self, env: Any) -> Optional[SentinelSafetyWrapper]:
        """Find SentinelSafetyWrapper in the environment chain."""
        current = env
        while current is not None:
            if isinstance(current, SentinelSafetyWrapper):
                return current
            if hasattr(current, 'env'):
                current = current.env
            else:
                break
        return None

    def update_metrics(self):
        """Update metrics from the safety wrapper."""
        if self.safety_wrapper:
            stats = self.safety_wrapper.get_stats()
            self.metrics.update_from_stats(stats)

    def should_log(self) -> bool:
        """Check if we should log at this step."""
        if self.log_interval <= 0:
            return False
        return (
            self.metrics.steps > 0 and
            self.metrics.steps - self._last_log_step >= self.log_interval
        )

    def log_metrics(self):
        """Log current metrics."""
        metrics_dict = self.metrics.to_dict()

        if self.on_log:
            self.on_log(metrics_dict)
        else:
            logger.info(f"Sentinel metrics: {metrics_dict}")

        self._last_log_step = self.metrics.steps

    @abstractmethod
    def on_step(self) -> bool:
        """Called after each step. Return False to stop training."""
        pass

    @abstractmethod
    def on_episode_end(self):
        """Called at the end of each episode."""
        pass


class SentinelSB3Callback(SentinelCallback):
    """
    Callback for Stable-Baselines3.

    This callback can be passed to model.learn() to monitor safety
    during training.

    Example:
        from stable_baselines3 import PPO
        from sentinelseed.integrations.isaac_lab import (
            SentinelSafetyWrapper,
            SentinelSB3Callback,
        )

        env = SentinelSafetyWrapper(base_env, mode="clamp")
        model = PPO("MlpPolicy", env)

        callback = SentinelSB3Callback(env, log_interval=1000)
        model.learn(total_timesteps=100000, callback=callback)
    """

    def __init__(
        self,
        env: Any,
        log_interval: int = 100,
        on_log: Optional[Callable[[Dict[str, float]], None]] = None,
        tensorboard_log: bool = True,
    ):
        super().__init__(env, log_interval, on_log)
        self.tensorboard_log = tensorboard_log
        self._sb3_callback = None

    def get_sb3_callback(self):
        """
        Get a Stable-Baselines3 compatible callback object.

        Returns:
            BaseCallback subclass for use with model.learn()
        """
        try:
            from stable_baselines3.common.callbacks import BaseCallback
        except ImportError:
            logger.error(
                "stable-baselines3 not installed. "
                "Install with: pip install stable-baselines3"
            )
            return None

        parent = self

        class _SB3Callback(BaseCallback):
            def __init__(self):
                super().__init__()
                self._prev_episode_count = 0

            def _on_step(self) -> bool:
                parent.update_metrics()
                parent.metrics.steps = self.num_timesteps

                # Count completed episodes from infos (correct way in SB3)
                # SB3 VecEnv stores episode info in 'infos' when episodes end
                infos = self.locals.get("infos", [])
                for info in infos:
                    if info is not None and "episode" in info:
                        # Episode completed - info["episode"] contains stats
                        parent.on_episode_end()

                if parent.should_log():
                    parent.log_metrics()

                    # Log to tensorboard if available
                    if parent.tensorboard_log and self.logger is not None:
                        for key, value in parent.metrics.to_dict().items():
                            self.logger.record(key, value)

                return True

            def _on_rollout_end(self) -> None:
                # Note: This is called at end of each rollout, NOT episode
                # Episode counting is handled in _on_step via infos
                pass

        if self._sb3_callback is None:
            self._sb3_callback = _SB3Callback()

        return self._sb3_callback

    def on_step(self) -> bool:
        """Called after each step."""
        self.update_metrics()
        if self.should_log():
            self.log_metrics()
        return True

    def on_episode_end(self):
        """Called at episode end."""
        self.metrics.episodes += 1


class SentinelRLGamesCallback(SentinelCallback):
    """
    Callback for RL-Games framework.

    RL-Games is the default framework used in Isaac Lab for training.

    Example:
        from sentinelseed.integrations.isaac_lab import SentinelRLGamesCallback

        callback = SentinelRLGamesCallback(env)

        # In your training config
        train_cfg["callbacks"] = [callback.get_rl_games_callback()]
    """

    def __init__(
        self,
        env: Any,
        log_interval: int = 100,
        on_log: Optional[Callable[[Dict[str, float]], None]] = None,
    ):
        super().__init__(env, log_interval, on_log)

    def get_rl_games_callback(self) -> Callable:
        """
        Get a callback function for RL-Games.

        Returns:
            Callback function compatible with RL-Games
        """
        parent = self

        def callback(locals_dict: Dict[str, Any], globals_dict: Dict[str, Any]):
            parent.update_metrics()

            # Get step from RL-Games locals
            if 'step' in locals_dict:
                parent.metrics.steps = locals_dict['step']

            if parent.should_log():
                parent.log_metrics()

        return callback

    def on_step(self) -> bool:
        """Called after each step."""
        self.update_metrics()
        if self.should_log():
            self.log_metrics()
        return True

    def on_episode_end(self):
        """Called at episode end."""
        self.metrics.episodes += 1


def create_wandb_callback(
    env: Any,
    project: str = "isaac-lab-safety",
    log_interval: int = 100,
    **wandb_kwargs,
) -> SentinelCallback:
    """
    Create a callback that logs to Weights & Biases.

    Args:
        env: Environment with safety wrapper
        project: WandB project name
        log_interval: Log every N steps
        **wandb_kwargs: Additional arguments for wandb.init()

    Returns:
        Configured callback

    Example:
        callback = create_wandb_callback(
            env,
            project="my-robot-training",
            entity="my-team",
        )
        model.learn(callback=callback.get_sb3_callback())
    """
    try:
        import wandb
    except ImportError:
        logger.error("wandb not installed. Install with: pip install wandb")
        raise

    # Initialize wandb
    if wandb.run is None:
        wandb.init(project=project, **wandb_kwargs)

    def log_to_wandb(metrics: Dict[str, float]):
        try:
            wandb.log(metrics)
        except Exception as e:
            logger.warning(f"Failed to log to WandB: {e}")

    return SentinelSB3Callback(
        env=env,
        log_interval=log_interval,
        on_log=log_to_wandb,
    )


def create_tensorboard_callback(
    env: Any,
    log_dir: str = "./tensorboard_logs",
    log_interval: int = 100,
) -> SentinelCallback:
    """
    Create a callback that logs to TensorBoard.

    Args:
        env: Environment with safety wrapper
        log_dir: Directory for tensorboard logs
        log_interval: Log every N steps

    Returns:
        Configured callback
    """
    try:
        from torch.utils.tensorboard import SummaryWriter
    except ImportError:
        logger.error(
            "tensorboard not installed. Install with: pip install tensorboard"
        )
        raise

    writer = SummaryWriter(log_dir=log_dir)

    def log_to_tensorboard(metrics: Dict[str, float]):
        try:
            step = int(metrics.get("sentinel/steps", 0))
            for key, value in metrics.items():
                writer.add_scalar(key, value, step)
            writer.flush()
        except Exception as e:
            logger.warning(f"Failed to log to TensorBoard: {e}")

    return SentinelSB3Callback(
        env=env,
        log_interval=log_interval,
        on_log=log_to_tensorboard,
        tensorboard_log=False,  # Use our custom logger
    )
