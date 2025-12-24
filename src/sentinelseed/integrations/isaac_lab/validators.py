"""
THSP Validation for Isaac Lab Robot Actions.

This module provides THSP-adapted validation for robotic actions in Isaac Lab
environments. The four gates are interpreted for reinforcement learning:

- Truth: Action is physically valid (not NaN/Inf, within action space)
- Harm: Action won't cause damage (within velocity/force limits)
- Scope: Action is within operational boundaries (workspace, joint limits)
- Purpose: Action contributes to task objective (optional)

Classes:
    - ActionValidationResult: Result of action validation
    - THSPRobotValidator: Main validator for robot actions
    - BatchValidationResult: Batch validation for vectorized environments

References:
    - Isaac Lab Environments: https://isaac-sim.github.io/IsaacLab/main/source/api/lab/isaaclab.envs.html
    - Safe RL: https://arxiv.org/abs/2108.06266
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union
import math
import logging

from sentinelseed.integrations.isaac_lab.constraints import (
    RobotConstraints,
    JointLimits,
    WorkspaceLimits,
    ForceTorqueLimits,
    CollisionZone,
    ConstraintViolationType,
)

logger = logging.getLogger("sentinelseed.isaac_lab")

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


class SafetyLevel(Enum):
    """Safety level classification for actions."""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"


class ActionType(Enum):
    """Type of robot action being validated."""
    JOINT_POSITION = "joint_position"
    JOINT_VELOCITY = "joint_velocity"
    JOINT_EFFORT = "joint_effort"
    CARTESIAN_POSE = "cartesian_pose"
    CARTESIAN_VELOCITY = "cartesian_velocity"
    NORMALIZED = "normalized"  # Actions in [-1, 1] range
    UNKNOWN = "unknown"


@dataclass
class ActionValidationResult:
    """
    Result of action validation through THSP gates.

    Attributes:
        is_safe: Whether the action is safe to execute
        level: Safety level classification
        gates: Results of individual THSP gates
        violations: List of violation messages
        violation_types: Types of violations detected
        modified_action: Action after safety modifications (if any)
        reasoning: Human-readable explanation
        confidence: Confidence score (0-1) for the validation
    """
    is_safe: bool
    level: SafetyLevel
    gates: Dict[str, bool] = field(default_factory=dict)
    violations: List[str] = field(default_factory=list)
    violation_types: List[ConstraintViolationType] = field(default_factory=list)
    modified_action: Optional[Any] = None
    reasoning: str = ""
    confidence: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "is_safe": self.is_safe,
            "level": self.level.value,
            "gates": self.gates,
            "violations": self.violations,
            "violation_types": [v.value for v in self.violation_types],
            "reasoning": self.reasoning,
            "confidence": self.confidence,
        }


@dataclass
class BatchValidationResult:
    """
    Validation result for batched actions (vectorized environments).

    Attributes:
        is_safe: Boolean tensor indicating safety per environment
        violations_per_env: Count of violations per environment
        any_unsafe: Whether any action is unsafe
        all_unsafe: Whether all actions are unsafe
        unsafe_indices: Indices of unsafe actions
        modified_actions: Actions after safety modifications
    """
    is_safe: Any  # torch.Tensor or np.ndarray of bools
    violations_per_env: Any  # Count per environment
    any_unsafe: bool
    all_unsafe: bool
    unsafe_indices: List[int]
    modified_actions: Optional[Any] = None
    level: SafetyLevel = SafetyLevel.SAFE

    @property
    def num_unsafe(self) -> int:
        """Number of unsafe actions in batch."""
        return len(self.unsafe_indices)


class THSPRobotValidator:
    """
    THSP validation for robot actions in Isaac Lab environments.

    The validator checks actions through four gates:
    1. Truth Gate: Action is physically valid
    2. Harm Gate: Action won't cause damage
    3. Scope Gate: Action is within boundaries
    4. Purpose Gate: Action has legitimate purpose (optional)

    Args:
        constraints: Robot constraints to validate against
        action_type: Type of actions being validated
        strict_mode: If True, any violation blocks the action
        log_violations: If True, log violations to console

    Example:
        validator = THSPRobotValidator(
            constraints=RobotConstraints.franka_default(),
            action_type=ActionType.JOINT_POSITION,
        )
        result = validator.validate(action)
        if not result.is_safe:
            action = result.modified_action or zero_action
    """

    def __init__(
        self,
        constraints: Optional[RobotConstraints] = None,
        action_type: ActionType = ActionType.NORMALIZED,
        strict_mode: bool = False,
        log_violations: bool = True,
    ):
        self.constraints = constraints or RobotConstraints()
        self.action_type = action_type
        self.strict_mode = strict_mode
        self.log_violations = log_violations

        # Statistics
        self._stats = {
            "total_validated": 0,
            "total_violations": 0,
            "gate_failures": {
                "truth": 0,
                "harm": 0,
                "scope": 0,
                "purpose": 0,
            },
        }

    def validate(
        self,
        action: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> ActionValidationResult:
        """
        Validate a single action through THSP gates.

        Args:
            action: The action to validate (tensor, array, or list)
            context: Optional context for validation (current state, purpose, etc.)

        Returns:
            ActionValidationResult with validation details
        """
        self._stats["total_validated"] += 1
        context = context or {}

        violations = []
        violation_types = []
        gates = {"truth": True, "harm": True, "scope": True, "purpose": True}

        # Convert action to list for validation
        action_list = self._to_list(action)

        # Gate 1: Truth - Is the action physically valid?
        truth_pass, truth_violations, truth_types = self._check_truth_gate(action_list)
        if not truth_pass:
            gates["truth"] = False
            violations.extend(truth_violations)
            violation_types.extend(truth_types)
            self._stats["gate_failures"]["truth"] += 1

        # Gate 2: Harm - Will the action cause damage?
        harm_pass, harm_violations, harm_types = self._check_harm_gate(action_list, context)
        if not harm_pass:
            gates["harm"] = False
            violations.extend(harm_violations)
            violation_types.extend(harm_types)
            self._stats["gate_failures"]["harm"] += 1

        # Gate 3: Scope - Is the action within boundaries?
        scope_pass, scope_violations, scope_types = self._check_scope_gate(action_list, context)
        if not scope_pass:
            gates["scope"] = False
            violations.extend(scope_violations)
            violation_types.extend(scope_types)
            self._stats["gate_failures"]["scope"] += 1

        # Gate 4: Purpose - Does the action have legitimate purpose?
        if self.constraints.require_purpose:
            purpose_pass, purpose_violations = self._check_purpose_gate(context)
            if not purpose_pass:
                gates["purpose"] = False
                violations.extend(purpose_violations)
                self._stats["gate_failures"]["purpose"] += 1

        # Determine overall safety
        is_safe = all(gates.values())

        if not is_safe:
            self._stats["total_violations"] += 1

        # Determine safety level
        if is_safe:
            level = SafetyLevel.SAFE
        elif not gates["harm"]:
            level = SafetyLevel.DANGEROUS
        elif not gates["purpose"] and self.constraints.require_purpose:
            level = SafetyLevel.BLOCKED
        else:
            level = SafetyLevel.WARNING

        # Compute modified action if needed
        modified_action = None
        if not is_safe:
            modified_action = self._compute_safe_action(action, action_list, violation_types)

        # Generate reasoning
        reasoning = self._generate_reasoning(violations, level)

        if self.log_violations and violations:
            logger.warning(f"Action validation: {reasoning}")

        return ActionValidationResult(
            is_safe=is_safe,
            level=level,
            gates=gates,
            violations=violations,
            violation_types=violation_types,
            modified_action=modified_action,
            reasoning=reasoning,
        )

    def validate_batch(
        self,
        actions: Any,
        contexts: Optional[List[Dict[str, Any]]] = None,
    ) -> BatchValidationResult:
        """
        Validate a batch of actions for vectorized environments.

        Args:
            actions: Batch of actions (shape: [num_envs, action_dim])
            contexts: Optional list of contexts per environment

        Returns:
            BatchValidationResult with per-environment validation
        """
        if TORCH_AVAILABLE and isinstance(actions, torch.Tensor):
            num_envs = actions.shape[0]
            is_safe = torch.ones(num_envs, dtype=torch.bool, device=actions.device)
            violations_per_env = torch.zeros(num_envs, dtype=torch.int32, device=actions.device)
        elif NUMPY_AVAILABLE and isinstance(actions, np.ndarray):
            num_envs = actions.shape[0]
            is_safe = np.ones(num_envs, dtype=bool)
            violations_per_env = np.zeros(num_envs, dtype=np.int32)
        else:
            num_envs = len(actions)
            is_safe = [True] * num_envs
            violations_per_env = [0] * num_envs

        unsafe_indices = []
        modified_actions = None
        any_dangerous = False

        # Validate each environment's action
        for i in range(num_envs):
            if TORCH_AVAILABLE and isinstance(actions, torch.Tensor):
                action = actions[i]
            elif NUMPY_AVAILABLE and isinstance(actions, np.ndarray):
                action = actions[i]
            else:
                action = actions[i]

            context = contexts[i] if contexts else None
            result = self.validate(action, context)

            if not result.is_safe:
                is_safe[i] = False
                violations_per_env[i] = len(result.violations)
                unsafe_indices.append(i)

                if result.level == SafetyLevel.DANGEROUS:
                    any_dangerous = True

                # Store modified action
                if result.modified_action is not None:
                    if modified_actions is None:
                        modified_actions = self._clone_actions(actions)
                    modified_actions[i] = result.modified_action

        # Determine overall level
        if len(unsafe_indices) == 0:
            level = SafetyLevel.SAFE
        elif any_dangerous:
            level = SafetyLevel.DANGEROUS
        else:
            level = SafetyLevel.WARNING

        any_unsafe = len(unsafe_indices) > 0
        all_unsafe = len(unsafe_indices) == num_envs

        return BatchValidationResult(
            is_safe=is_safe,
            violations_per_env=violations_per_env,
            any_unsafe=any_unsafe,
            all_unsafe=all_unsafe,
            unsafe_indices=unsafe_indices,
            modified_actions=modified_actions,
            level=level,
        )

    def _check_truth_gate(
        self,
        action: List[float],
    ) -> Tuple[bool, List[str], List[ConstraintViolationType]]:
        """
        Gate 1: Truth - Check if action is physically valid.

        Validates:
        - No NaN or Inf values
        - Values are within expected range for action type
        """
        violations = []
        types = []

        # Check for invalid values
        for i, val in enumerate(action):
            if math.isnan(val):
                violations.append(f"[TRUTH] Action dim {i}: NaN value")
                types.append(ConstraintViolationType.INVALID_VALUE)
            elif math.isinf(val):
                violations.append(f"[TRUTH] Action dim {i}: Infinite value")
                types.append(ConstraintViolationType.INVALID_VALUE)

        # Check normalized action range
        if self.action_type == ActionType.NORMALIZED:
            for i, val in enumerate(action):
                if not math.isnan(val) and not math.isinf(val):
                    if abs(val) > 1.0 + 1e-6:  # Small tolerance
                        violations.append(
                            f"[TRUTH] Action dim {i}: Value {val:.3f} outside [-1, 1]"
                        )
                        types.append(ConstraintViolationType.INVALID_VALUE)

        return len(violations) == 0, violations, types

    def _check_harm_gate(
        self,
        action: List[float],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str], List[ConstraintViolationType]]:
        """
        Gate 2: Harm - Check if action could cause damage.

        Validates:
        - Joint velocities within safe limits
        - Forces/torques within safe limits
        - No collision risk
        """
        violations = []
        types = []

        # Check joint velocity limits
        if (self.action_type in (ActionType.JOINT_VELOCITY, ActionType.NORMALIZED)
                and self.constraints.joint_limits):

            num_joints = self.constraints.joint_limits.num_joints

            # Validate action has enough dimensions before processing
            if len(action) < num_joints:
                violations.append(
                    f"[HARM] Action has {len(action)} dims, expected {num_joints} for velocity check"
                )
                types.append(ConstraintViolationType.INVALID_VALUE)
                return len(violations) == 0, violations, types

            # For normalized actions, scale by typical velocity
            if self.action_type == ActionType.NORMALIZED:
                scaled_action = [
                    action[i] * self.constraints.action_scale
                    for i in range(num_joints)
                ]
            else:
                scaled_action = [action[i] for i in range(num_joints)]

            valid, vel_violations = self.constraints.joint_limits.check_velocity(scaled_action)
            if not valid:
                for v in vel_violations:
                    violations.append(f"[HARM] {v}")
                    types.append(ConstraintViolationType.JOINT_VELOCITY)

        # Check force/torque limits if current readings available
        if self.constraints.force_torque_limits:
            current_force = context.get("current_force")
            if current_force is not None:
                valid, force_violations = self.constraints.force_torque_limits.check_force(
                    current_force
                )
                if not valid:
                    for v in force_violations:
                        violations.append(f"[HARM] {v}")
                        types.append(ConstraintViolationType.FORCE)

        return len(violations) == 0, violations, types

    def _check_scope_gate(
        self,
        action: List[float],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str], List[ConstraintViolationType]]:
        """
        Gate 3: Scope - Check if action is within boundaries.

        Validates:
        - Joint positions within limits
        - End-effector within workspace
        - No collision zones violated
        """
        violations = []
        types = []

        # Check joint position limits
        if (self.action_type == ActionType.JOINT_POSITION
                and self.constraints.joint_limits):
            valid, pos_violations = self.constraints.joint_limits.check_position(action)
            if not valid:
                for v in pos_violations:
                    violations.append(f"[SCOPE] {v}")
                    types.append(ConstraintViolationType.JOINT_POSITION)

        # Check predicted position for normalized/velocity actions
        if self.action_type in (ActionType.NORMALIZED, ActionType.JOINT_VELOCITY):
            current_position = context.get("current_joint_position")
            if current_position is not None and self.constraints.joint_limits:
                # Convert to list if needed
                pos_list = self._to_list(current_position)
                num_joints = self.constraints.joint_limits.num_joints

                # Validate dimensions match
                if len(pos_list) < num_joints or len(action) < num_joints:
                    violations.append(
                        f"[SCOPE] Dimension mismatch: position has {len(pos_list)}, "
                        f"action has {len(action)}, expected {num_joints}"
                    )
                    types.append(ConstraintViolationType.INVALID_VALUE)
                else:
                    # Predict next position (use only the required joints)
                    dt = context.get("dt", 0.01)
                    scale = self.constraints.action_scale if self.action_type == ActionType.NORMALIZED else 1.0
                    predicted = [
                        pos_list[i] + action[i] * scale * dt
                        for i in range(num_joints)
                    ]
                    valid, pos_violations = self.constraints.joint_limits.check_position(predicted)
                    if not valid:
                        for v in pos_violations:
                            violations.append(f"[SCOPE] Predicted: {v}")
                            types.append(ConstraintViolationType.JOINT_POSITION)

        # Check workspace limits
        if self.constraints.workspace_limits:
            current_ee_pos = context.get("current_ee_position")
            if current_ee_pos is not None:
                valid, ws_violations = self.constraints.workspace_limits.check_position(
                    current_ee_pos
                )
                if not valid:
                    for v in ws_violations:
                        violations.append(f"[SCOPE] Workspace: {v}")
                        types.append(ConstraintViolationType.WORKSPACE)

        # Check collision zones
        if self.constraints.collision_zones:
            current_ee_pos = context.get("current_ee_position")
            if current_ee_pos is not None:
                x, y, z = current_ee_pos[0], current_ee_pos[1], current_ee_pos[2]
                for zone in self.constraints.collision_zones:
                    if zone.contains(x, y, z):
                        violations.append(f"[SCOPE] Inside collision zone: {zone.name}")
                        types.append(ConstraintViolationType.COLLISION)

        return len(violations) == 0, violations, types

    def _check_purpose_gate(
        self,
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        Gate 4: Purpose - Check if action has legitimate purpose.

        This gate is optional and requires context about the task goal.
        """
        violations = []

        purpose = context.get("purpose")
        if self.constraints.require_purpose and not purpose:
            violations.append("[PURPOSE] Action lacks explicit purpose")

        return len(violations) == 0, violations

    def _compute_safe_action(
        self,
        original: Any,
        action_list: List[float],
        violation_types: List[ConstraintViolationType],
    ) -> Any:
        """Compute a safe version of the action."""
        # Start with original action
        if TORCH_AVAILABLE and isinstance(original, torch.Tensor):
            safe_action = original.clone()
        elif NUMPY_AVAILABLE and isinstance(original, np.ndarray):
            safe_action = original.copy()
        else:
            safe_action = list(action_list)

        # Fix invalid values (NaN, Inf)
        if ConstraintViolationType.INVALID_VALUE in violation_types:
            safe_action = self._fix_invalid_values(safe_action)
            # Also clamp to valid range for normalized actions
            if self.action_type == ActionType.NORMALIZED:
                safe_action = self._clamp_normalized(safe_action)

        # Clamp to joint limits
        if (ConstraintViolationType.JOINT_VELOCITY in violation_types
                and self.constraints.joint_limits):
            if self.action_type == ActionType.NORMALIZED:
                # Clamp to [-1, 1] for normalized actions
                safe_action = self._clamp_normalized(safe_action)
            else:
                safe_action = self.constraints.joint_limits.clamp_velocity(safe_action)

        if (ConstraintViolationType.JOINT_POSITION in violation_types
                and self.constraints.joint_limits):
            safe_action = self.constraints.joint_limits.clamp_position(safe_action)

        return safe_action

    def _fix_invalid_values(self, action: Any) -> Any:
        """Replace NaN and Inf values with zeros."""
        if TORCH_AVAILABLE and isinstance(action, torch.Tensor):
            action = torch.nan_to_num(action, nan=0.0, posinf=0.0, neginf=0.0)
        elif NUMPY_AVAILABLE and isinstance(action, np.ndarray):
            action = np.nan_to_num(action, nan=0.0, posinf=0.0, neginf=0.0)
        else:
            action = [0.0 if (math.isnan(v) or math.isinf(v)) else v for v in action]
        return action

    def _clamp_normalized(self, action: Any) -> Any:
        """Clamp action to [-1, 1] range."""
        if TORCH_AVAILABLE and isinstance(action, torch.Tensor):
            return torch.clamp(action, -1.0, 1.0)
        elif NUMPY_AVAILABLE and isinstance(action, np.ndarray):
            return np.clip(action, -1.0, 1.0)
        else:
            return [max(-1.0, min(1.0, v)) for v in action]

    def _to_list(self, action: Any) -> List[float]:
        """Convert action to list for validation."""
        if TORCH_AVAILABLE and isinstance(action, torch.Tensor):
            return action.detach().cpu().flatten().tolist()
        elif NUMPY_AVAILABLE and isinstance(action, np.ndarray):
            return action.flatten().tolist()
        return list(action)

    def _clone_actions(self, actions: Any) -> Any:
        """Create a copy of the actions tensor/array."""
        if TORCH_AVAILABLE and isinstance(actions, torch.Tensor):
            return actions.clone()
        elif NUMPY_AVAILABLE and isinstance(actions, np.ndarray):
            return actions.copy()
        return [list(a) for a in actions]

    def _generate_reasoning(
        self,
        violations: List[str],
        level: SafetyLevel,
    ) -> str:
        """Generate human-readable reasoning."""
        if not violations:
            return "Action passes all THSP safety gates."

        if level == SafetyLevel.DANGEROUS:
            return f"DANGEROUS: {len(violations)} violation(s). {violations[0]}"
        elif level == SafetyLevel.BLOCKED:
            return f"BLOCKED: {violations[0]}"
        else:
            return f"WARNING: {len(violations)} issue(s). {violations[0]}"

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self._stats.copy()

    def reset_stats(self):
        """Reset validation statistics."""
        self._stats = {
            "total_validated": 0,
            "total_violations": 0,
            "gate_failures": {
                "truth": 0,
                "harm": 0,
                "scope": 0,
                "purpose": 0,
            },
        }
