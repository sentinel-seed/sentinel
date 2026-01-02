"""
Safety Base Module - Core Abstractions for All Safety Validators.

This module provides the foundational classes and types used across all
safety validation subsystems in Sentinel. It defines:

- SafetyLevel: Universal safety classification enum
- ViolationType: Types of safety violations detected
- SafetyResult: Base result class for all validations
- SafetyValidator: Abstract base class for validators

These abstractions enable consistent safety validation across different
domains (humanoid robots, mobile robots, RL simulation) while allowing
domain-specific extensions.

Architecture:
    SafetyValidator (ABC)
    ├── HumanoidSafetyValidator (safety/humanoid/)
    ├── MobileRobotValidator (safety/mobile/) [via integrations/ros2]
    └── SimulationValidator (safety/simulation/) [via integrations/isaac_lab]

Usage:
    from sentinelseed.safety.base import SafetyLevel, SafetyResult, SafetyValidator

    class MyValidator(SafetyValidator):
        def validate(self, action, context=None):
            # Custom validation logic
            return SafetyResult(is_safe=True, level=SafetyLevel.SAFE)

References:
    - ISO 10218:2025 - Industrial robot safety
    - ISO 13482 - Personal care robot safety
    - ISO/TS 15066 - Collaborative robot safety
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
import logging

__version__ = "1.0.0"

logger = logging.getLogger("sentinelseed.safety.base")


class SafetyLevel(Enum):
    """
    Universal safety level classification.

    These levels represent the severity of a safety assessment result
    and determine the appropriate system response.

    Levels:
        SAFE: Action is fully compliant with all safety requirements.
              System may proceed normally.

        WARNING: Action has minor concerns but is within acceptable limits.
                 System may proceed with caution and logging.

        DANGEROUS: Action poses significant risk of harm or damage.
                   System should block or modify the action.

        BLOCKED: Action is explicitly prohibited by safety policy.
                 System must reject and not execute.

        CRITICAL: Immediate danger requiring emergency response.
                  System must engage emergency stop procedures.

    Example:
        result = validator.validate(action)
        if result.level == SafetyLevel.DANGEROUS:
            action = result.modified_action or emergency_stop()

    Ordering:
        SAFE < WARNING < DANGEROUS < BLOCKED < CRITICAL
        (from least to most severe)
    """
    SAFE = "safe"
    WARNING = "warning"
    DANGEROUS = "dangerous"
    BLOCKED = "blocked"
    CRITICAL = "critical"

    def __lt__(self, other: "SafetyLevel") -> bool:
        """Compare safety levels by severity."""
        if not isinstance(other, SafetyLevel):
            return NotImplemented
        order = [
            SafetyLevel.SAFE,
            SafetyLevel.WARNING,
            SafetyLevel.DANGEROUS,
            SafetyLevel.BLOCKED,
            SafetyLevel.CRITICAL,
        ]
        return order.index(self) < order.index(other)

    def __le__(self, other: "SafetyLevel") -> bool:
        """Compare safety levels by severity."""
        return self == other or self < other

    def __gt__(self, other: "SafetyLevel") -> bool:
        """Compare safety levels by severity."""
        if not isinstance(other, SafetyLevel):
            return NotImplemented
        return not self <= other

    def __ge__(self, other: "SafetyLevel") -> bool:
        """Compare safety levels by severity."""
        return self == other or self > other

    @property
    def requires_action(self) -> bool:
        """Whether this level requires corrective action."""
        return self in (SafetyLevel.DANGEROUS, SafetyLevel.BLOCKED, SafetyLevel.CRITICAL)

    @property
    def is_emergency(self) -> bool:
        """Whether this level requires emergency response."""
        return self == SafetyLevel.CRITICAL


class ViolationType(Enum):
    """
    Types of safety violations that can be detected.

    These violation types help categorize and respond to different
    kinds of safety issues. They map to specific THSP gates and
    physical constraints.

    Categories:
        - NONE: No violation (placeholder for clean results)
        - Physical limits: Joint, force, torque constraints
        - Spatial limits: Workspace, collision, zone violations
        - Input validation: Invalid values or types
        - THSP gates: Truth, Harm, Scope, Purpose violations
        - Domain-specific: Balance, contact force, fall risk

    Example:
        if ViolationType.JOINT_VELOCITY in result.violation_types:
            # Handle velocity limit exceeded
            apply_velocity_scaling(action)
    """
    # No violation
    NONE = "none"

    # Physical limits
    JOINT_POSITION = "joint_position"
    JOINT_VELOCITY = "joint_velocity"
    JOINT_ACCELERATION = "joint_acceleration"
    FORCE = "force"
    TORQUE = "torque"

    # Spatial limits
    WORKSPACE = "workspace"
    COLLISION = "collision"
    ZONE = "zone"

    # Input validation
    INVALID_VALUE = "invalid_value"
    INVALID_TYPE = "invalid_type"
    MISSING_REQUIRED = "missing_required"

    # THSP gate violations
    TRUTH_VIOLATION = "truth"
    HARM_VIOLATION = "harm"
    SCOPE_VIOLATION = "scope"
    PURPOSE_VIOLATION = "purpose"

    # Humanoid-specific
    BALANCE = "balance"
    CONTACT_FORCE = "contact_force"
    FALL_RISK = "fall_risk"

    # Mobile robot-specific
    VELOCITY_LIMIT = "velocity_limit"
    ALTITUDE_LIMIT = "altitude_limit"

    # Simulation-specific
    ACTION_SPACE = "action_space"
    EPISODE_TERMINATION = "episode_termination"

    @property
    def gate(self) -> Optional[str]:
        """Get the THSP gate this violation corresponds to, if any."""
        gate_mapping = {
            ViolationType.TRUTH_VIOLATION: "truth",
            ViolationType.INVALID_VALUE: "truth",
            ViolationType.INVALID_TYPE: "truth",
            ViolationType.MISSING_REQUIRED: "truth",
            ViolationType.HARM_VIOLATION: "harm",
            ViolationType.FORCE: "harm",
            ViolationType.TORQUE: "harm",
            ViolationType.CONTACT_FORCE: "harm",
            ViolationType.COLLISION: "harm",
            ViolationType.SCOPE_VIOLATION: "scope",
            ViolationType.JOINT_POSITION: "scope",
            ViolationType.JOINT_VELOCITY: "scope",
            ViolationType.JOINT_ACCELERATION: "scope",
            ViolationType.WORKSPACE: "scope",
            ViolationType.ZONE: "scope",
            ViolationType.VELOCITY_LIMIT: "scope",
            ViolationType.ALTITUDE_LIMIT: "scope",
            ViolationType.ACTION_SPACE: "scope",
            ViolationType.PURPOSE_VIOLATION: "purpose",
            ViolationType.BALANCE: "harm",
            ViolationType.FALL_RISK: "harm",
        }
        return gate_mapping.get(self)

    @property
    def is_physical(self) -> bool:
        """Whether this is a physical constraint violation."""
        return self in (
            ViolationType.JOINT_POSITION,
            ViolationType.JOINT_VELOCITY,
            ViolationType.JOINT_ACCELERATION,
            ViolationType.FORCE,
            ViolationType.TORQUE,
            ViolationType.VELOCITY_LIMIT,
        )

    @property
    def is_spatial(self) -> bool:
        """Whether this is a spatial constraint violation."""
        return self in (
            ViolationType.WORKSPACE,
            ViolationType.COLLISION,
            ViolationType.ZONE,
            ViolationType.ALTITUDE_LIMIT,
        )


def _default_gates() -> Dict[str, bool]:
    """Create default gates dictionary."""
    return {"truth": True, "harm": True, "scope": True, "purpose": True}


@dataclass
class SafetyResult:
    """
    Base result class for all safety validations.

    This dataclass provides a consistent structure for reporting
    safety validation outcomes across all domains. Specialized
    validators may extend this with domain-specific fields.

    Attributes:
        is_safe: Overall safety determination. True if action is safe.
        level: Safety level classification (SafetyLevel enum).
        gates: Results of individual THSP gates (truth, harm, scope, purpose).
        violations: Human-readable list of violation messages.
        violation_types: List of ViolationType enums for programmatic handling.
        reasoning: Explanation of the safety determination.
        confidence: Confidence score (0.0-1.0) for the assessment.
        modified_action: Suggested safe alternative action, if applicable.
        metadata: Additional domain-specific information.

    Example:
        result = SafetyResult(
            is_safe=False,
            level=SafetyLevel.DANGEROUS,
            gates={"truth": True, "harm": False, "scope": True, "purpose": True},
            violations=["Joint velocity exceeds safe limit"],
            violation_types=[ViolationType.JOINT_VELOCITY],
            reasoning="Left elbow velocity 3.5 rad/s exceeds limit 2.0 rad/s",
        )

        if not result.is_safe:
            if result.modified_action:
                execute(result.modified_action)
            else:
                emergency_stop()
    """
    is_safe: bool
    level: SafetyLevel
    gates: Dict[str, bool] = field(default_factory=_default_gates)
    violations: List[str] = field(default_factory=list)
    violation_types: List[ViolationType] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 1.0
    modified_action: Optional[Any] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate fields after initialization."""
        # Ensure confidence is in valid range
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")

        # Ensure level is SafetyLevel
        if isinstance(self.level, str):
            self.level = SafetyLevel(self.level)

        # Ensure violation_types contains ViolationType
        normalized_types = []
        for vt in self.violation_types:
            if isinstance(vt, str):
                normalized_types.append(ViolationType(vt))
            else:
                normalized_types.append(vt)
        self.violation_types = normalized_types

    @property
    def failed_gates(self) -> List[str]:
        """Get list of gates that failed validation."""
        return [gate for gate, passed in self.gates.items() if not passed]

    @property
    def passed_gates(self) -> List[str]:
        """Get list of gates that passed validation."""
        return [gate for gate, passed in self.gates.items() if passed]

    @property
    def has_violations(self) -> bool:
        """Whether any violations were detected."""
        return len(self.violations) > 0

    @property
    def primary_violation(self) -> Optional[str]:
        """Get the first/primary violation message, if any."""
        return self.violations[0] if self.violations else None

    @property
    def primary_violation_type(self) -> Optional[ViolationType]:
        """Get the first/primary violation type, if any."""
        return self.violation_types[0] if self.violation_types else None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert to dictionary for serialization.

        Returns:
            Dictionary with all fields serialized to basic types.
        """
        return {
            "is_safe": self.is_safe,
            "level": self.level.value,
            "gates": self.gates.copy(),
            "violations": list(self.violations),
            "violation_types": [vt.value for vt in self.violation_types],
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "metadata": self.metadata.copy(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SafetyResult":
        """
        Create SafetyResult from dictionary.

        Args:
            data: Dictionary with serialized fields.

        Returns:
            SafetyResult instance.
        """
        return cls(
            is_safe=data["is_safe"],
            level=SafetyLevel(data["level"]),
            gates=data.get("gates", _default_gates()),
            violations=data.get("violations", []),
            violation_types=[ViolationType(vt) for vt in data.get("violation_types", [])],
            reasoning=data.get("reasoning", ""),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def safe(cls, reasoning: str = "Action passes all safety gates.") -> "SafetyResult":
        """
        Create a safe result.

        Args:
            reasoning: Optional explanation.

        Returns:
            SafetyResult with is_safe=True and level=SAFE.
        """
        return cls(
            is_safe=True,
            level=SafetyLevel.SAFE,
            reasoning=reasoning,
        )

    @classmethod
    def unsafe(
        cls,
        level: SafetyLevel,
        violations: List[str],
        violation_types: Optional[List[ViolationType]] = None,
        failed_gates: Optional[List[str]] = None,
        reasoning: str = "",
        modified_action: Optional[Any] = None,
    ) -> "SafetyResult":
        """
        Create an unsafe result.

        Args:
            level: Safety level (should be WARNING, DANGEROUS, BLOCKED, or CRITICAL).
            violations: List of violation messages.
            violation_types: Optional list of violation type enums.
            failed_gates: Optional list of failed gate names.
            reasoning: Explanation of the determination.
            modified_action: Optional safe alternative action.

        Returns:
            SafetyResult with is_safe=False.
        """
        gates = _default_gates()
        if failed_gates:
            for gate in failed_gates:
                if gate in gates:
                    gates[gate] = False

        return cls(
            is_safe=False,
            level=level,
            gates=gates,
            violations=violations,
            violation_types=violation_types or [],
            reasoning=reasoning or (violations[0] if violations else "Validation failed"),
            modified_action=modified_action,
        )

    def merge_with(self, other: "SafetyResult") -> "SafetyResult":
        """
        Merge this result with another, taking the worse outcome.

        Useful for combining results from multiple validation checks.

        Args:
            other: Another SafetyResult to merge with.

        Returns:
            New SafetyResult with combined violations and worse level.
        """
        # Combine gates (AND)
        merged_gates = {}
        for gate in set(self.gates.keys()) | set(other.gates.keys()):
            merged_gates[gate] = self.gates.get(gate, True) and other.gates.get(gate, True)

        # Take worse level
        merged_level = max(self.level, other.level)

        # Combine violations
        merged_violations = list(self.violations) + list(other.violations)
        merged_types = list(self.violation_types) + list(other.violation_types)

        # Determine overall safety
        merged_safe = self.is_safe and other.is_safe

        # Take lower confidence
        merged_confidence = min(self.confidence, other.confidence)

        # Combine reasoning
        if self.reasoning and other.reasoning:
            merged_reasoning = f"{self.reasoning}; {other.reasoning}"
        else:
            merged_reasoning = self.reasoning or other.reasoning

        return SafetyResult(
            is_safe=merged_safe,
            level=merged_level,
            gates=merged_gates,
            violations=merged_violations,
            violation_types=merged_types,
            reasoning=merged_reasoning,
            confidence=merged_confidence,
            modified_action=self.modified_action or other.modified_action,
            metadata={**self.metadata, **other.metadata},
        )


class SafetyValidator(ABC):
    """
    Abstract base class for all safety validators.

    This class defines the interface that all safety validators must implement.
    It provides common functionality for statistics tracking and ensures
    consistent behavior across different validation domains.

    Subclasses must implement:
        - validate(action, context): Core validation method

    Subclasses may override:
        - get_stats(): Return validation statistics
        - reset_stats(): Reset statistics counters
        - validate_batch(actions, contexts): Batch validation (optional)

    Example:
        class MyValidator(SafetyValidator):
            def __init__(self, max_velocity: float):
                self.max_velocity = max_velocity
                self._stats = {"validated": 0, "blocked": 0}

            def validate(self, action, context=None):
                self._stats["validated"] += 1
                if action.velocity > self.max_velocity:
                    self._stats["blocked"] += 1
                    return SafetyResult.unsafe(
                        level=SafetyLevel.DANGEROUS,
                        violations=["Velocity exceeds limit"],
                        violation_types=[ViolationType.VELOCITY_LIMIT],
                    )
                return SafetyResult.safe()

    Thread Safety:
        Implementations should be thread-safe if they will be used in
        multi-threaded environments. Consider using locks for statistics
        and shared state.
    """

    @abstractmethod
    def validate(
        self,
        action: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> SafetyResult:
        """
        Validate an action through safety gates.

        This is the core method that all validators must implement.
        It should check the action against all applicable safety
        constraints and return a SafetyResult.

        Args:
            action: The action to validate. Type depends on domain:
                   - Humanoid: HumanoidAction or joint dict
                   - Mobile: Twist/velocity command
                   - Simulation: Tensor/array of actions
            context: Optional contextual information for validation:
                    - current_state: Current robot/env state
                    - purpose: Stated purpose of the action
                    - dt: Time step for predictions
                    - etc.

        Returns:
            SafetyResult with validation outcome, violations, and
            optionally a modified safe action.

        Raises:
            ValueError: If action is invalid or None.
            TypeError: If action type is not supported.
        """
        pass

    def validate_batch(
        self,
        actions: Any,
        contexts: Optional[List[Dict[str, Any]]] = None,
    ) -> List[SafetyResult]:
        """
        Validate a batch of actions.

        Default implementation validates each action individually.
        Subclasses may override for optimized batch processing.

        Args:
            actions: Batch of actions (list, array, or tensor).
            contexts: Optional list of contexts per action.

        Returns:
            List of SafetyResult, one per action.
        """
        results = []
        num_actions = len(actions)
        for i in range(num_actions):
            action = actions[i]
            context = contexts[i] if contexts else None
            results.append(self.validate(action, context))
        return results

    def get_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics.

        Returns:
            Dictionary with statistics. Default keys:
            - total_validated: Number of validations performed
            - total_blocked: Number of actions blocked
            - gate_failures: Dict of failure counts per gate
        """
        return getattr(self, "_stats", {}).copy()

    def reset_stats(self) -> None:
        """
        Reset validation statistics to initial state.

        Call this to clear accumulated statistics, e.g., between
        episodes in RL or at the start of a new session.
        """
        if hasattr(self, "_stats"):
            # Preserve structure, reset values
            for key in self._stats:
                if isinstance(self._stats[key], dict):
                    for subkey in self._stats[key]:
                        self._stats[key][subkey] = 0
                elif isinstance(self._stats[key], (int, float)):
                    self._stats[key] = 0

    def _init_stats(self) -> Dict[str, Any]:
        """
        Initialize default statistics structure.

        Subclasses can override to add domain-specific stats.

        Returns:
            Dictionary with initial statistics.
        """
        return {
            "total_validated": 0,
            "total_blocked": 0,
            "gate_failures": {
                "truth": 0,
                "harm": 0,
                "scope": 0,
                "purpose": 0,
            },
        }

    def _update_stats(self, result: SafetyResult) -> None:
        """
        Update statistics based on validation result.

        Args:
            result: The SafetyResult from validation.
        """
        if not hasattr(self, "_stats"):
            self._stats = self._init_stats()

        self._stats["total_validated"] = self._stats.get("total_validated", 0) + 1

        if not result.is_safe:
            self._stats["total_blocked"] = self._stats.get("total_blocked", 0) + 1

            gate_failures = self._stats.get("gate_failures", {})
            for gate, passed in result.gates.items():
                if not passed:
                    gate_failures[gate] = gate_failures.get(gate, 0) + 1
            self._stats["gate_failures"] = gate_failures


__all__ = [
    # Version
    "__version__",
    # Enums
    "SafetyLevel",
    "ViolationType",
    # Result class
    "SafetyResult",
    # Validator base
    "SafetyValidator",
]
