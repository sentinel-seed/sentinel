"""
THSP Validation for Humanoid Robot Actions.

This module provides THSP (Truth, Harm, Scope, Purpose) validation
specifically designed for humanoid robots. It combines:

- Joint and velocity validation (from constraints)
- Contact force validation (from ISO/TS 15066 body model)
- Balance safety validation (from balance module)
- Human proximity safety checks

The four gates are interpreted for humanoid robotics:
- Truth: Action is physically possible for the humanoid
- Harm: Action won't cause injury to humans or damage to robot
- Scope: Action is within operational and spatial boundaries
- Purpose: Action serves a legitimate task objective

References:
    - ISO 10218:2025 - Industrial robot safety
    - ISO 13482 - Personal care robot safety
    - ISO/TS 15066 - Collaborative robot safety
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import logging
import math
import threading

from sentinelseed.safety.humanoid.body_model import (
    HumanBodyModel,
    BodyRegion,
)
from sentinelseed.safety.humanoid.constraints import (
    HumanoidConstraints,
    HumanoidLimb,
)
from sentinelseed.safety.humanoid.balance import (
    BalanceMonitor,
    BalanceAssessment,
    BalanceState,
)

logger = logging.getLogger("sentinelseed.humanoid.validators")

# Configuration constants
DEFAULT_COLLABORATIVE_VELOCITY = 0.5  # m/s (ISO/TS 15066 conservative)
DEFAULT_BODY_MODEL_SAFETY_FACTOR = 0.9  # 10% safety margin
DANGEROUS_PURPOSE_PATTERNS = frozenset([
    "harm", "hurt", "injure", "attack", "hit",
    "damage", "destroy", "break", "kill", "maim",
])


class SafetyLevel(str, Enum):
    """Safety level classification for humanoid actions."""
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    CRITICAL = "critical"
    BLOCKED = "blocked"


class ViolationType(str, Enum):
    """Types of safety violations."""
    JOINT_LIMIT = "joint_limit"
    VELOCITY_LIMIT = "velocity_limit"
    CONTACT_FORCE = "contact_force"
    BALANCE = "balance"
    WORKSPACE = "workspace"
    PROXIMITY = "proximity"
    PURPOSE = "purpose"
    INVALID_ACTION = "invalid_action"


@dataclass
class HumanoidAction:
    """
    Representation of a humanoid robot action.

    Attributes:
        joint_positions: Target joint positions (rad or m)
        joint_velocities: Target joint velocities (rad/s or m/s)
        end_effector_velocities: Velocities of end effectors (m/s)
        expected_contact_force: Expected contact force if any (N)
        contact_region: Human body region expected to contact
        robot_position: Current robot position (x, y, z) in world frame
        purpose: Description of action purpose
        is_collaborative: Whether action involves human collaboration
    """
    joint_positions: Optional[Dict[str, float]] = None
    joint_velocities: Optional[Dict[str, float]] = None
    end_effector_velocities: Optional[Dict[HumanoidLimb, float]] = None
    expected_contact_force: Optional[float] = None
    contact_region: Optional[BodyRegion] = None
    robot_position: Optional[Tuple[float, float, float]] = None
    purpose: Optional[str] = None
    is_collaborative: bool = False


@dataclass
class ValidationResult:
    """
    Result of THSP validation for a humanoid action.

    Attributes:
        is_safe: Whether the action is safe to execute
        level: Safety level classification
        gates: Results of individual THSP gates
        violations: List of violation details
        modified_action: Action after safety modifications (if any)
        reasoning: Human-readable explanation
        balance_assessment: Balance state assessment if checked
        contact_assessment: Contact force assessment if checked
    """
    is_safe: bool
    level: SafetyLevel
    gates: Dict[str, bool] = field(default_factory=lambda: {
        "truth": True, "harm": True, "scope": True, "purpose": True
    })
    violations: List[Dict[str, Any]] = field(default_factory=list)
    modified_action: Optional[HumanoidAction] = None
    reasoning: str = ""
    balance_assessment: Optional[BalanceAssessment] = None
    contact_assessment: Optional[Dict[str, Any]] = None

    def add_violation(
        self,
        gate: str,
        violation_type: ViolationType,
        description: str,
        severity: str = "medium",
    ):
        """Add a violation to the result."""
        self.violations.append({
            "gate": gate,
            "type": violation_type.value,
            "description": description,
            "severity": severity,
        })
        self.gates[gate] = False


class HumanoidSafetyValidator:
    """
    THSP validator for humanoid robot actions.

    Validates actions through four gates:
    1. Truth: Is the action physically possible?
    2. Harm: Could it cause injury or damage?
    3. Scope: Is it within operational boundaries?
    4. Purpose: Does it serve a legitimate goal?

    Example:
        from sentinelseed.safety.humanoid import (
            HumanoidSafetyValidator,
            HumanoidAction,
        )
        from sentinelseed.safety.humanoid.presets import tesla_optimus

        validator = HumanoidSafetyValidator(
            constraints=tesla_optimus(),
        )

        action = HumanoidAction(
            joint_velocities={"left_elbow": 2.0},
            purpose="Pick up object",
        )

        result = validator.validate(action)
        if not result.is_safe:
            print(f"Action blocked: {result.reasoning}")
    """

    def __init__(
        self,
        constraints: Optional[HumanoidConstraints] = None,
        body_model: Optional[HumanBodyModel] = None,
        balance_monitor: Optional[BalanceMonitor] = None,
        strict_mode: bool = False,
        require_purpose: bool = False,
        log_violations: bool = True,
        collaborative_velocity: float = DEFAULT_COLLABORATIVE_VELOCITY,
    ):
        """
        Initialize the humanoid safety validator.

        Args:
            constraints: Humanoid robot constraints
            body_model: Human body model for contact force limits
            balance_monitor: Balance monitoring system
            strict_mode: If True, any violation blocks the action
            require_purpose: If True, require explicit purpose for actions
            log_violations: If True, log violations to console
            collaborative_velocity: Max end effector speed for collaborative work (m/s)

        Raises:
            TypeError: If arguments are of wrong type
            ValueError: If collaborative_velocity is not positive
        """
        # Validate types
        if constraints is not None and not isinstance(constraints, HumanoidConstraints):
            raise TypeError(
                f"constraints must be HumanoidConstraints, got {type(constraints).__name__}"
            )
        if body_model is not None and not isinstance(body_model, HumanBodyModel):
            raise TypeError(
                f"body_model must be HumanBodyModel, got {type(body_model).__name__}"
            )
        if balance_monitor is not None and not isinstance(balance_monitor, BalanceMonitor):
            raise TypeError(
                f"balance_monitor must be BalanceMonitor, got {type(balance_monitor).__name__}"
            )
        if collaborative_velocity <= 0:
            raise ValueError("collaborative_velocity must be positive")

        self.constraints = constraints
        self.body_model = body_model or HumanBodyModel(
            safety_factor=DEFAULT_BODY_MODEL_SAFETY_FACTOR
        )
        self.balance_monitor = balance_monitor
        self.strict_mode = strict_mode
        self.require_purpose = require_purpose
        self.log_violations = log_violations
        self.collaborative_velocity = collaborative_velocity

        # Thread safety for statistics
        self._stats_lock = threading.Lock()
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
        action: HumanoidAction,
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate a humanoid action through THSP gates.

        Args:
            action: The action to validate
            context: Additional context for validation

        Returns:
            ValidationResult with validation details

        Raises:
            TypeError: If action is not a HumanoidAction
        """
        # Validate input
        if action is None:
            raise TypeError("action cannot be None")
        if not isinstance(action, HumanoidAction):
            raise TypeError(
                f"action must be HumanoidAction, got {type(action).__name__}"
            )

        with self._stats_lock:
            self._stats["total_validated"] += 1

        context = context or {}

        result = ValidationResult(is_safe=True, level=SafetyLevel.SAFE)

        # Gate 1: Truth - Is the action physically possible?
        self._check_truth_gate(action, result, context)

        # Gate 2: Harm - Could it cause injury or damage?
        self._check_harm_gate(action, result, context)

        # Gate 3: Scope - Is it within boundaries?
        self._check_scope_gate(action, result, context)

        # Gate 4: Purpose - Does it serve a legitimate goal?
        self._check_purpose_gate(action, result, context)

        # Determine overall safety
        result.is_safe = all(result.gates.values())

        # Update statistics
        with self._stats_lock:
            if not result.is_safe:
                self._stats["total_violations"] += 1
            # Update gate failure counts
            for gate, passed in result.gates.items():
                if not passed:
                    self._stats["gate_failures"][gate] += 1

        # Determine safety level
        result.level = self._determine_level(result)

        # Generate reasoning
        result.reasoning = self._generate_reasoning(result)

        # Log if configured
        if self.log_violations and result.violations:
            logger.warning(f"Humanoid action validation: {result.reasoning}")

        return result

    def _check_truth_gate(
        self,
        action: HumanoidAction,
        result: ValidationResult,
        context: Dict[str, Any],
    ) -> None:
        """
        Gate 1: Truth - Validate physical possibility.

        Checks:
        - Joint positions within mechanical limits
        - Velocities within actuator capabilities
        - No NaN/Inf values
        """
        # Check joint positions
        if action.joint_positions and self.constraints:
            valid, violations = self.constraints.check_joint_positions(
                action.joint_positions
            )
            if not valid:
                for v in violations:
                    result.add_violation(
                        "truth",
                        ViolationType.JOINT_LIMIT,
                        v,
                        "high",
                    )

        # Check joint velocities
        if action.joint_velocities and self.constraints:
            valid, violations = self.constraints.check_joint_velocities(
                action.joint_velocities
            )
            if not valid:
                for v in violations:
                    result.add_violation(
                        "truth",
                        ViolationType.VELOCITY_LIMIT,
                        v,
                        "high",
                    )

        # Check for invalid values in positions
        if action.joint_positions:
            for name, pos in action.joint_positions.items():
                if math.isnan(pos) or math.isinf(pos):
                    result.add_violation(
                        "truth",
                        ViolationType.INVALID_ACTION,
                        f"Invalid position value for {name}: {pos}",
                        "critical",
                    )

        # Check for invalid values in velocities
        if action.joint_velocities:
            for name, vel in action.joint_velocities.items():
                if math.isnan(vel) or math.isinf(vel):
                    result.add_violation(
                        "truth",
                        ViolationType.INVALID_ACTION,
                        f"Invalid velocity value for {name}: {vel}",
                        "critical",
                    )

    def _check_harm_gate(
        self,
        action: HumanoidAction,
        result: ValidationResult,
        context: Dict[str, Any],
    ) -> None:
        """
        Gate 2: Harm - Validate safety for humans and robot.

        Checks:
        - Contact force within ISO/TS 15066 limits
        - End effector velocities in collaborative zones
        - Balance stability
        """
        # Check contact force limits
        if action.expected_contact_force is not None:
            contact_region = action.contact_region or BodyRegion.CHEST_STERNUM

            # Get contact type from context
            contact_type = context.get("contact_type", "transient")

            safe_force = self.body_model.get_safe_force(
                contact_region,
                contact_type,
            )

            if action.expected_contact_force > safe_force:
                result.add_violation(
                    "harm",
                    ViolationType.CONTACT_FORCE,
                    f"Contact force {action.expected_contact_force:.1f}N exceeds "
                    f"safe limit {safe_force:.1f}N for {contact_region.value}",
                    "critical",
                )

                result.contact_assessment = {
                    "region": contact_region.value,
                    "expected_force": action.expected_contact_force,
                    "safe_limit": safe_force,
                    "contact_type": contact_type,
                    "is_safe": False,
                }
            else:
                result.contact_assessment = {
                    "region": contact_region.value,
                    "expected_force": action.expected_contact_force,
                    "safe_limit": safe_force,
                    "contact_type": contact_type,
                    "is_safe": True,
                }

        # Check end effector velocities for collaborative work
        if action.is_collaborative and action.end_effector_velocities:
            max_collab_velocity = self.collaborative_velocity
            if self.constraints:
                max_collab_velocity = min(
                    max_collab_velocity,
                    self.constraints.operational_limits.max_arm_speed * 0.5,
                )

            for limb, velocity in action.end_effector_velocities.items():
                if velocity > max_collab_velocity:
                    result.add_violation(
                        "harm",
                        ViolationType.VELOCITY_LIMIT,
                        f"End effector velocity {velocity:.2f} m/s exceeds "
                        f"collaborative limit {max_collab_velocity:.2f} m/s for {limb.value}",
                        "high",
                    )

        # Check balance if monitor is available
        if self.balance_monitor:
            balance = self.balance_monitor.assess_balance()
            result.balance_assessment = balance

            if not balance.is_safe:
                severity = "high" if balance.state == BalanceState.UNSTABLE else "critical"
                result.add_violation(
                    "harm",
                    ViolationType.BALANCE,
                    f"Balance issue: {balance.state.value}. {balance.recommended_action}",
                    severity,
                )

    def _check_scope_gate(
        self,
        action: HumanoidAction,
        result: ValidationResult,
        context: Dict[str, Any],
    ) -> None:
        """
        Gate 3: Scope - Validate operational boundaries.

        Checks:
        - Robot position within safety zones
        - Respecting zone-specific speed limits
        - Within operational workspace
        """
        if action.robot_position and self.constraints:
            x, y, z = action.robot_position
            in_zone, zone = self.constraints.is_position_in_safe_zone(x, y, z)

            if not in_zone:
                result.add_violation(
                    "scope",
                    ViolationType.WORKSPACE,
                    f"Robot position ({x:.2f}, {y:.2f}, {z:.2f}) outside defined safety zones",
                    "high",
                )

            elif zone and zone.requires_reduced_speed:
                # Check if velocities exceed zone limits
                max_speed = zone.max_speed_in_zone
                if action.end_effector_velocities:
                    for limb, vel in action.end_effector_velocities.items():
                        if vel > max_speed:
                            result.add_violation(
                                "scope",
                                ViolationType.VELOCITY_LIMIT,
                                f"Velocity {vel:.2f} m/s exceeds zone limit "
                                f"{max_speed:.2f} m/s in {zone.name}",
                                "medium",
                            )

        # Check height limit
        if action.robot_position and self.constraints:
            _, _, z = action.robot_position
            max_height = self.constraints.operational_limits.max_operating_height
            if z > max_height:
                result.add_violation(
                    "scope",
                    ViolationType.WORKSPACE,
                    f"Height {z:.2f}m exceeds limit {max_height:.2f}m",
                    "medium",
                )

    def _check_purpose_gate(
        self,
        action: HumanoidAction,
        result: ValidationResult,
        context: Dict[str, Any],
    ) -> None:
        """
        Gate 4: Purpose - Validate legitimate purpose.

        Checks:
        - Action has stated purpose (if required)
        - Purpose is not obviously malicious
        - Action serves a beneficial goal
        """
        if self.require_purpose and not action.purpose:
            result.add_violation(
                "purpose",
                ViolationType.PURPOSE,
                "Action requires explicit purpose but none provided",
                "medium",
            )
            return  # Early return since there's no purpose to check

        # Check for obviously problematic purposes
        if action.purpose:
            purpose_lower = action.purpose.lower()

            for pattern in DANGEROUS_PURPOSE_PATTERNS:
                if pattern in purpose_lower:
                    result.add_violation(
                        "purpose",
                        ViolationType.PURPOSE,
                        f"Purpose contains concerning pattern: '{pattern}'",
                        "critical",
                    )
                    break  # Only add one violation per purpose

    def _determine_level(self, result: ValidationResult) -> SafetyLevel:
        """Determine safety level from violations."""
        if not result.violations:
            return SafetyLevel.SAFE

        # Check for critical violations
        has_critical = any(
            v.get("severity") == "critical" for v in result.violations
        )
        if has_critical:
            return SafetyLevel.CRITICAL

        # Check for high severity violations
        has_high = any(
            v.get("severity") == "high" for v in result.violations
        )
        if has_high:
            return SafetyLevel.DANGEROUS

        # Check harm gate specifically
        if not result.gates["harm"]:
            return SafetyLevel.DANGEROUS

        # Check purpose gate
        if not result.gates["purpose"] and self.require_purpose:
            return SafetyLevel.BLOCKED

        return SafetyLevel.WARNING

    def _generate_reasoning(self, result: ValidationResult) -> str:
        """Generate human-readable reasoning."""
        if not result.violations:
            return "Action passes all THSP safety gates for humanoid operation."

        violation_count = len(result.violations)
        first_violation = result.violations[0]["description"]

        if result.level == SafetyLevel.CRITICAL:
            return f"CRITICAL: {violation_count} violation(s). {first_violation}"
        elif result.level == SafetyLevel.DANGEROUS:
            return f"DANGEROUS: {violation_count} violation(s). {first_violation}"
        elif result.level == SafetyLevel.BLOCKED:
            return f"BLOCKED: Action lacks required purpose. {first_violation}"
        else:
            return f"WARNING: {violation_count} issue(s). {first_violation}"

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics (thread-safe copy)."""
        with self._stats_lock:
            return {
                "total_validated": self._stats["total_validated"],
                "total_violations": self._stats["total_violations"],
                "gate_failures": self._stats["gate_failures"].copy(),
            }

    def reset_stats(self) -> None:
        """Reset validation statistics (thread-safe)."""
        with self._stats_lock:
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


def validate_humanoid_action(
    action: HumanoidAction,
    constraints: Optional[HumanoidConstraints] = None,
    strict: bool = False,
) -> ValidationResult:
    """
    Convenience function for one-off humanoid action validation.

    Args:
        action: Action to validate
        constraints: Optional humanoid constraints
        strict: If True, any violation blocks action

    Returns:
        ValidationResult
    """
    validator = HumanoidSafetyValidator(
        constraints=constraints,
        strict_mode=strict,
    )
    return validator.validate(action)


__all__ = [
    # Constants
    "DEFAULT_COLLABORATIVE_VELOCITY",
    "DEFAULT_BODY_MODEL_SAFETY_FACTOR",
    "DANGEROUS_PURPOSE_PATTERNS",
    # Enums
    "SafetyLevel",
    "ViolationType",
    # Data classes
    "HumanoidAction",
    "ValidationResult",
    # Classes
    "HumanoidSafetyValidator",
    # Functions
    "validate_humanoid_action",
]
