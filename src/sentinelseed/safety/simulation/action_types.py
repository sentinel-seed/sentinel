"""
Action Types and Batch Validation for Simulation.

Provides classification of action types used in RL environments and
batch validation results for efficient vectorized environment handling.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

# Import base types
from sentinelseed.safety.base import SafetyLevel


class ActionType(Enum):
    """
    Classification of action types in RL environments.

    Different action types require different validation strategies:
    - Position commands need joint limit checking
    - Velocity commands need rate limiting
    - Normalized actions need scaling before validation
    - Torque/effort commands need effort limit checking

    Attributes:
        JOINT_POSITION: Absolute joint positions (rad or m)
        JOINT_VELOCITY: Joint velocities (rad/s or m/s)
        JOINT_POSITION_DELTA: Incremental position changes
        JOINT_EFFORT: Direct effort/torque commands (alias: TORQUE)
        NORMALIZED: Actions in [-1, 1] range (gym standard)
        CARTESIAN: End-effector position/orientation (generic)
        CARTESIAN_POSE: End-effector pose (position + orientation)
        CARTESIAN_VELOCITY: End-effector velocity
        TORQUE: Direct torque commands (alias: JOINT_EFFORT)
        UNKNOWN: Unknown action type (fallback)

    Example:
        action_type = ActionType.NORMALIZED
        if action_type == ActionType.NORMALIZED:
            # Scale actions before validation
            scaled_actions = actions * action_scale
    """
    # Joint space actions
    JOINT_POSITION = "joint_position"
    JOINT_VELOCITY = "joint_velocity"
    JOINT_POSITION_DELTA = "joint_position_delta"
    JOINT_EFFORT = "joint_effort"

    # Cartesian space actions
    CARTESIAN = "cartesian"
    CARTESIAN_POSE = "cartesian_pose"
    CARTESIAN_VELOCITY = "cartesian_velocity"

    # Special types
    NORMALIZED = "normalized"
    TORQUE = "torque"
    UNKNOWN = "unknown"

    @property
    def needs_scaling(self) -> bool:
        """Whether this action type needs to be scaled before validation."""
        return self == ActionType.NORMALIZED

    @property
    def is_velocity_based(self) -> bool:
        """Whether this action type represents velocities."""
        return self in (
            ActionType.JOINT_VELOCITY,
            ActionType.JOINT_POSITION_DELTA,
            ActionType.CARTESIAN_VELOCITY,
        )

    @property
    def is_position_based(self) -> bool:
        """Whether this action type represents positions."""
        return self in (
            ActionType.JOINT_POSITION,
            ActionType.CARTESIAN,
            ActionType.CARTESIAN_POSE,
        )

    @property
    def is_effort_based(self) -> bool:
        """Whether this action type represents effort/torque commands."""
        return self in (ActionType.JOINT_EFFORT, ActionType.TORQUE)


@dataclass
class BatchValidationResult:
    """
    Result of batch validation for vectorized environments.

    Holds validation results for multiple environments simultaneously,
    supporting efficient RL training workflows.

    Attributes:
        is_safe: Per-environment safety flags (list of bool or tensor)
        levels: Per-environment safety levels
        violations: Per-environment violation counts
        violation_details: Detailed violation messages per environment
        modified_actions: Actions after safety modifications (if any)
        stats: Aggregate statistics across the batch

    Example:
        results = validator.validate_batch(actions)
        if not all(results.is_safe):
            # Handle unsafe environments
            unsafe_envs = [i for i, safe in enumerate(results.is_safe) if not safe]
            print(f"Unsafe environments: {unsafe_envs}")

            # Use modified actions if available
            if results.modified_actions is not None:
                actions = results.modified_actions
    """
    is_safe: List[bool]
    levels: List[SafetyLevel]
    violations: List[int] = field(default_factory=list)
    violation_details: List[List[str]] = field(default_factory=list)
    modified_actions: Optional[Any] = None
    stats: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Ensure consistent list lengths."""
        n = len(self.is_safe)

        if not self.violations:
            self.violations = [0] * n
        if not self.violation_details:
            self.violation_details = [[] for _ in range(n)]

        # Calculate default stats
        if not self.stats:
            self.stats = self._calculate_stats()

    def _calculate_stats(self) -> Dict[str, Any]:
        """Calculate aggregate statistics."""
        n = len(self.is_safe)
        if n == 0:
            return {"total": 0, "safe": 0, "unsafe": 0, "safe_ratio": 1.0}

        safe_count = sum(self.is_safe)
        return {
            "total": n,
            "safe": safe_count,
            "unsafe": n - safe_count,
            "safe_ratio": safe_count / n,
            "total_violations": sum(self.violations),
        }

    @property
    def num_environments(self) -> int:
        """Number of environments in the batch."""
        return len(self.is_safe)

    @property
    def all_safe(self) -> bool:
        """Whether all environments are safe."""
        return all(self.is_safe)

    @property
    def any_unsafe(self) -> bool:
        """Whether any environment is unsafe."""
        return not self.all_safe

    @property
    def safe_ratio(self) -> float:
        """Ratio of safe environments."""
        if not self.is_safe:
            return 1.0
        return sum(self.is_safe) / len(self.is_safe)

    @property
    def unsafe_indices(self) -> List[int]:
        """Indices of unsafe environments."""
        return [i for i, safe in enumerate(self.is_safe) if not safe]

    @property
    def safe_indices(self) -> List[int]:
        """Indices of safe environments."""
        return [i for i, safe in enumerate(self.is_safe) if safe]

    def get_worst_level(self) -> SafetyLevel:
        """Get the worst (highest severity) safety level in the batch."""
        if not self.levels:
            return SafetyLevel.SAFE
        return max(self.levels)

    @classmethod
    def all_safe_result(cls, num_envs: int) -> "BatchValidationResult":
        """Create a result where all environments are safe."""
        return cls(
            is_safe=[True] * num_envs,
            levels=[SafetyLevel.SAFE] * num_envs,
        )

    @classmethod
    def from_single_results(
        cls,
        results: List[Dict[str, Any]],
        modified_actions: Optional[Any] = None,
    ) -> "BatchValidationResult":
        """
        Create from a list of individual validation results.

        Args:
            results: List of dicts with 'is_safe', 'level', 'violations' keys
            modified_actions: Optional modified actions for the batch

        Returns:
            BatchValidationResult aggregating all individual results
        """
        return cls(
            is_safe=[r.get("is_safe", True) for r in results],
            levels=[r.get("level", SafetyLevel.SAFE) for r in results],
            violations=[len(r.get("violations", [])) for r in results],
            violation_details=[r.get("violations", []) for r in results],
            modified_actions=modified_actions,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_safe": self.is_safe,
            "levels": [level.value for level in self.levels],
            "violations": self.violations,
            "stats": self.stats,
        }


__all__ = [
    "ActionType",
    "BatchValidationResult",
]
