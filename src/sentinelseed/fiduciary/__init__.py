"""
Fiduciary AI Module for Sentinel

Implements fiduciary principles for AI systems, ensuring they act in the
best interest of users with duties of loyalty and care.

Based on research from:
- "Designing Fiduciary Artificial Intelligence" (ACM FAccT 2023)
- "Fiduciary Principles in AI" (Boston University Law)
- Montreal AI Ethics Institute guidelines

Key Principles:
1. Duty of Loyalty: AI must act in the user's best interest, not its own
2. Duty of Care: AI must exercise reasonable competence and diligence
3. Transparency: Decisions must be explainable, not black-box
4. Conflict Avoidance: Detect and disclose conflicts of interest
5. Confidentiality: Protect user information and privacy

Six-Step Fiduciary Framework:
1. CONTEXT - Understand the user's situation and needs
2. IDENTIFICATION - Identify the user's objectives and constraints
3. ASSESSMENT - Evaluate options against user's interests
4. AGGREGATION - Combine multiple factors appropriately
5. LOYALTY - Ensure actions serve user, not AI/provider
6. CARE - Verify competence and diligence in execution

Example:
    from sentinelseed.fiduciary import FiduciaryValidator

    validator = FiduciaryValidator()

    # Check if an action is fiduciary-compliant
    result = validator.validate_action(
        action="recommend_investment",
        user_context={"risk_tolerance": "low", "goal": "retirement"},
        proposed_action={"type": "high_risk_stock", "amount": 10000}
    )

    if not result.compliant:
        print(f"Fiduciary violation: {result.violations}")

Documentation: https://sentinelseed.dev/docs/fiduciary
Research: https://dl.acm.org/doi/fullHtml/10.1145/3617694.3623230
"""

from __future__ import annotations

import functools
import logging
import re
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("sentinelseed.fiduciary")


class Severity(str, Enum):
    """Severity levels for fiduciary violations"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Convert string to Severity, with fallback to MEDIUM."""
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown severity '{value}', defaulting to MEDIUM")
            return cls.MEDIUM


class RiskTolerance(str, Enum):
    """User risk tolerance levels"""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"

    @classmethod
    def from_string(cls, value: str) -> "RiskTolerance":
        """Convert string to RiskTolerance, with fallback to MODERATE."""
        try:
            return cls(value.lower())
        except ValueError:
            logger.warning(f"Unknown risk tolerance '{value}', defaulting to MODERATE")
            return cls.MODERATE


class FiduciaryDuty(str, Enum):
    """Core fiduciary duties"""
    LOYALTY = "loyalty"        # Act in user's best interest
    CARE = "care"              # Exercise competence and diligence
    TRANSPARENCY = "transparency"  # Explain decisions clearly
    CONFIDENTIALITY = "confidentiality"  # Protect user information
    PRUDENCE = "prudence"      # Make reasonable decisions
    DISCLOSURE = "disclosure"  # Disclose conflicts and risks


class ViolationType(str, Enum):
    """Types of fiduciary violations"""
    CONFLICT_OF_INTEREST = "conflict_of_interest"
    SELF_DEALING = "self_dealing"
    MISALIGNED_RECOMMENDATION = "misaligned_recommendation"
    INADEQUATE_DISCLOSURE = "inadequate_disclosure"
    PRIVACY_VIOLATION = "privacy_violation"
    LACK_OF_TRANSPARENCY = "lack_of_transparency"
    INCOMPETENT_ACTION = "incompetent_action"
    UNDISCLOSED_RISK = "undisclosed_risk"
    USER_HARM = "user_harm"


class FiduciaryStep(str, Enum):
    """Six-step fiduciary framework"""
    CONTEXT = "context"             # Understand user situation
    IDENTIFICATION = "identification"  # Identify objectives
    ASSESSMENT = "assessment"       # Evaluate options
    AGGREGATION = "aggregation"     # Combine factors
    LOYALTY = "loyalty"             # Ensure user-centric
    CARE = "care"                   # Verify execution


@dataclass
class Violation:
    """A fiduciary duty violation"""
    duty: FiduciaryDuty
    type: ViolationType
    description: str
    severity: Severity
    step: Optional[FiduciaryStep] = None
    recommendation: Optional[str] = None

    def __post_init__(self):
        """Validate and convert severity to enum if needed."""
        if isinstance(self.severity, str):
            self.severity = Severity.from_string(self.severity)

    def to_dict(self) -> Dict[str, Any]:
        """Convert violation to dictionary."""
        return {
            "duty": self.duty.value,
            "type": self.type.value,
            "description": self.description,
            "severity": self.severity.value if isinstance(self.severity, Severity) else self.severity,
            "step": self.step.value if self.step else None,
            "recommendation": self.recommendation,
        }

    def is_blocking(self) -> bool:
        """Check if this violation should block the action."""
        return self.severity in (Severity.HIGH, Severity.CRITICAL)


@dataclass
class FiduciaryResult:
    """Result of fiduciary validation"""
    compliant: bool
    violations: List[Violation] = field(default_factory=list)
    passed_duties: List[FiduciaryDuty] = field(default_factory=list)
    explanations: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "compliant": self.compliant,
            "violations": [v.to_dict() for v in self.violations],
            "passed_duties": [d.value for d in self.passed_duties],
            "explanations": self.explanations,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
        }


@dataclass
class UserContext:
    """User context for fiduciary assessment"""
    user_id: Optional[str] = None
    goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    sensitive_topics: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate and convert risk_tolerance to enum if needed."""
        if isinstance(self.risk_tolerance, str):
            self.risk_tolerance = RiskTolerance.from_string(self.risk_tolerance)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserContext":
        """Create UserContext from dictionary."""
        risk_tol = data.get("risk_tolerance", "moderate")
        if isinstance(risk_tol, str):
            risk_tol = RiskTolerance.from_string(risk_tol)

        return cls(
            user_id=data.get("user_id"),
            goals=data.get("goals", []),
            constraints=data.get("constraints", []),
            risk_tolerance=risk_tol,
            preferences=data.get("preferences", {}),
            history=data.get("history", []),
            sensitive_topics=data.get("sensitive_topics", []),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "user_id": self.user_id,
            "goals": self.goals,
            "constraints": self.constraints,
            "risk_tolerance": self.risk_tolerance.value if isinstance(self.risk_tolerance, RiskTolerance) else self.risk_tolerance,
            "preferences": self.preferences,
            "history": self.history,
            "sensitive_topics": self.sensitive_topics,
        }


class ConflictDetector:
    """
    Detects conflicts of interest in AI actions.

    Identifies situations where AI might be acting in its own interest
    or the provider's interest rather than the user's.

    Thread Safety:
        This class is thread-safe for detection operations.
        Pattern compilation happens during initialization.
    """

    # Patterns that indicate potential conflicts
    # Format: (regex_pattern, conflict_type_name)
    CONFLICT_PATTERNS: List[tuple] = [
        # Self-promotion
        (r"(recommend|suggest|use)\s+(our|my|this)\s+(service|product|platform)", "self_dealing"),
        (r"(upgrade|subscribe|buy)\s+(premium|pro|paid)", "self_dealing"),
        # Steering away from competitors
        (r"(don't|avoid|never)\s+(use|try)\s+\w+\s+(competitor|alternative)", "competitive_steering"),
        # Data harvesting
        (r"(share|provide|give)\s+(your|personal)\s+(data|information|details)", "data_harvesting"),
        # Engagement maximization
        (r"(stay|spend more|engage)\s+(longer|more time)", "engagement_optimization"),
    ]

    # Keywords indicating potential provider benefit over user benefit
    PROVIDER_BENEFIT_KEYWORDS: frozenset = frozenset({
        "affiliate", "commission", "sponsored", "partner",
        "premium", "upgrade", "subscribe", "monetize",
    })

    def __init__(self, custom_patterns: Optional[List[tuple]] = None):
        """
        Initialize conflict detector.

        Args:
            custom_patterns: Additional patterns as list of (regex, conflict_type) tuples

        Raises:
            TypeError: If custom_patterns is not a list of tuples
            ValueError: If pattern format is invalid
        """
        self.patterns = list(self.CONFLICT_PATTERNS)

        if custom_patterns is not None:
            if not isinstance(custom_patterns, list):
                raise TypeError(
                    f"custom_patterns must be a list, got {type(custom_patterns).__name__}"
                )
            for i, pattern in enumerate(custom_patterns):
                if not isinstance(pattern, tuple) or len(pattern) != 2:
                    raise ValueError(
                        f"Pattern at index {i} must be (regex, type) tuple, got {pattern}"
                    )
                regex, conflict_type = pattern
                if not isinstance(regex, str) or not isinstance(conflict_type, str):
                    raise ValueError(
                        f"Pattern at index {i} must contain strings, got ({type(regex).__name__}, {type(conflict_type).__name__})"
                    )
            self.patterns.extend(custom_patterns)

        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for efficient matching."""
        self._compiled: List[tuple] = []
        for pattern, conflict_type in self.patterns:
            try:
                compiled = re.compile(pattern, re.IGNORECASE)
                self._compiled.append((compiled, conflict_type))
            except re.error as e:
                logger.error(f"Invalid regex pattern '{pattern}': {e}")
                raise ValueError(f"Invalid regex pattern '{pattern}': {e}")

    def detect(
        self,
        action: str,
        context: Optional[str] = None,
    ) -> List[Violation]:
        """
        Detect conflicts of interest in an action.

        Args:
            action: The proposed action or recommendation
            context: Additional context

        Returns:
            List of detected violations

        Raises:
            TypeError: If action is not a string
        """
        if action is None:
            raise TypeError("action cannot be None")
        if not isinstance(action, str):
            raise TypeError(f"action must be a string, got {type(action).__name__}")

        violations: List[Violation] = []
        text = f"{action} {context or ''}".strip()

        if not text:
            return violations

        # Check patterns
        for pattern, conflict_type in self._compiled:
            if pattern.search(text):
                violations.append(Violation(
                    duty=FiduciaryDuty.LOYALTY,
                    type=ViolationType.CONFLICT_OF_INTEREST,
                    description=f"Potential {conflict_type.replace('_', ' ')} detected",
                    severity=Severity.MEDIUM,
                    step=FiduciaryStep.LOYALTY,
                    recommendation="Disclose any conflicts and prioritize user interest",
                ))

        # Check for provider benefit keywords
        text_lower = text.lower()
        found_keywords = [k for k in self.PROVIDER_BENEFIT_KEYWORDS if k in text_lower]
        if found_keywords:
            violations.append(Violation(
                duty=FiduciaryDuty.DISCLOSURE,
                type=ViolationType.INADEQUATE_DISCLOSURE,
                description=f"Undisclosed potential benefit indicators: {', '.join(sorted(found_keywords))}",
                severity=Severity.LOW,
                step=FiduciaryStep.LOYALTY,
                recommendation="Clearly disclose any commercial relationships",
            ))

        return violations


class FiduciaryValidator:
    """
    Validates AI actions against fiduciary duties.

    Ensures AI systems act with loyalty and care toward users,
    following the six-step fiduciary framework.

    Thread Safety:
        This class is thread-safe. Statistics tracking uses locks
        to prevent race conditions.

    Example:
        validator = FiduciaryValidator()

        result = validator.validate_action(
            action="Recommend high-risk investment",
            user_context=UserContext(risk_tolerance="low"),
        )

        if not result.compliant:
            for v in result.violations:
                print(f"{v.duty}: {v.description}")
    """

    def __init__(
        self,
        strict_mode: bool = False,
        require_all_duties: bool = False,
        custom_rules: Optional[List[Callable]] = None,
    ):
        """
        Initialize the fiduciary validator.

        Args:
            strict_mode: If True, any violation makes action non-compliant
            require_all_duties: If True, all duties must pass for compliance
            custom_rules: Additional validation rules (callable(action, context) -> List[Violation])

        Raises:
            TypeError: If custom_rules contains non-callable items
        """
        self.strict_mode = strict_mode
        self.require_all_duties = require_all_duties

        # Validate custom rules
        if custom_rules is not None:
            if not isinstance(custom_rules, list):
                raise TypeError(
                    f"custom_rules must be a list, got {type(custom_rules).__name__}"
                )
            for i, rule in enumerate(custom_rules):
                if not callable(rule):
                    raise TypeError(
                        f"custom_rules[{i}] must be callable, got {type(rule).__name__}"
                    )
        self.custom_rules = custom_rules or []

        self.conflict_detector = ConflictDetector()

        # Thread-safe statistics
        self._stats_lock = threading.Lock()
        self._stats = {
            "total_validated": 0,
            "total_compliant": 0,
            "total_violations": 0,
            "custom_rule_errors": 0,
        }

    def validate_action(
        self,
        action: str,
        user_context: Optional[UserContext] = None,
        proposed_outcome: Optional[Dict[str, Any]] = None,
    ) -> FiduciaryResult:
        """
        Validate an action against fiduciary duties.

        Args:
            action: Description of the action
            user_context: User's context and preferences
            proposed_outcome: Expected outcome of the action

        Returns:
            FiduciaryResult with compliance status and any violations

        Raises:
            TypeError: If action is not a string
            ValueError: If action is empty
        """
        # Validate input
        if action is None:
            raise TypeError("action cannot be None")
        if not isinstance(action, str):
            raise TypeError(f"action must be a string, got {type(action).__name__}")
        if not action.strip():
            raise ValueError("action cannot be empty")

        # Convert dict to UserContext if needed
        if isinstance(user_context, dict):
            user_context = UserContext.from_dict(user_context)

        context = user_context or UserContext()
        violations: List[Violation] = []
        passed_duties: List[FiduciaryDuty] = []
        explanations: Dict[str, str] = {}

        # Step 1: CONTEXT - Validate understanding of user situation
        ctx_violations = self._check_context(action, context)
        violations.extend(ctx_violations)
        if not ctx_violations:
            passed_duties.append(FiduciaryDuty.PRUDENCE)
            explanations["context"] = "User context properly considered"

        # Step 2: IDENTIFICATION - Check if user objectives are identified
        id_violations = self._check_identification(action, context)
        violations.extend(id_violations)
        if not id_violations:
            explanations["identification"] = "User objectives identified"

        # Step 3-4: ASSESSMENT & AGGREGATION - Check alignment with user interests
        align_violations = self._check_alignment(action, context, proposed_outcome)
        violations.extend(align_violations)
        if not align_violations:
            explanations["alignment"] = "Action aligned with user interests"

        # Step 5: LOYALTY - Check for conflicts of interest
        loyalty_violations = self.conflict_detector.detect(action)
        violations.extend(loyalty_violations)
        if not loyalty_violations:
            passed_duties.append(FiduciaryDuty.LOYALTY)
            explanations["loyalty"] = "No conflicts of interest detected"

        # Step 6: CARE - Check competence and diligence
        care_violations = self._check_care(action, context)
        violations.extend(care_violations)
        if not care_violations:
            passed_duties.append(FiduciaryDuty.CARE)
            explanations["care"] = "Due care exercised"

        # Additional checks
        transparency_violations = self._check_transparency(action)
        violations.extend(transparency_violations)
        if not transparency_violations:
            passed_duties.append(FiduciaryDuty.TRANSPARENCY)

        confidentiality_violations = self._check_confidentiality(action, context)
        violations.extend(confidentiality_violations)
        if not confidentiality_violations:
            passed_duties.append(FiduciaryDuty.CONFIDENTIALITY)

        # Run custom rules with proper error handling
        for i, rule in enumerate(self.custom_rules):
            try:
                custom_violations = rule(action, context)
                if custom_violations:
                    # Validate that custom rule returns List[Violation]
                    for v in custom_violations:
                        if isinstance(v, Violation):
                            violations.append(v)
                        else:
                            logger.warning(
                                f"Custom rule {i} returned non-Violation: {type(v).__name__}"
                            )
            except Exception as e:
                logger.warning(f"Custom rule {i} error: {e}")
                with self._stats_lock:
                    self._stats["custom_rule_errors"] += 1

        # Determine compliance
        if self.require_all_duties:
            compliant = len(violations) == 0
        else:
            # Compliant if no high/critical violations
            compliant = not any(v.is_blocking() for v in violations)

        if self.strict_mode:
            compliant = len(violations) == 0

        # Calculate confidence based on violation count and severity
        confidence = 1.0
        for v in violations:
            if v.severity == Severity.CRITICAL:
                confidence -= 0.25
            elif v.severity == Severity.HIGH:
                confidence -= 0.20
            elif v.severity == Severity.MEDIUM:
                confidence -= 0.10
            else:
                confidence -= 0.05
        confidence = max(0.0, min(1.0, confidence))

        # Update statistics
        with self._stats_lock:
            self._stats["total_validated"] += 1
            self._stats["total_violations"] += len(violations)
            if compliant:
                self._stats["total_compliant"] += 1

        return FiduciaryResult(
            compliant=compliant,
            violations=violations,
            passed_duties=passed_duties,
            explanations=explanations,
            confidence=confidence,
        )

    def get_stats(self) -> Dict[str, int]:
        """Get validation statistics (thread-safe copy)."""
        with self._stats_lock:
            return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset validation statistics (thread-safe)."""
        with self._stats_lock:
            self._stats = {
                "total_validated": 0,
                "total_compliant": 0,
                "total_violations": 0,
                "custom_rule_errors": 0,
            }

    def _check_context(self, action: str, context: UserContext) -> List[Violation]:
        """
        Check if action considers user context.

        Gate 1: CONTEXT - Understand the user's situation and needs.
        """
        violations: List[Violation] = []

        # Check if action matches risk tolerance
        action_lower = action.lower()
        high_risk_indicators = ["high risk", "aggressive", "volatile", "speculative"]
        is_low_risk_user = context.risk_tolerance == RiskTolerance.LOW

        if is_low_risk_user and any(ind in action_lower for ind in high_risk_indicators):
            violations.append(Violation(
                duty=FiduciaryDuty.CARE,
                type=ViolationType.MISALIGNED_RECOMMENDATION,
                description="High-risk action proposed for low-risk-tolerance user",
                severity=Severity.HIGH,
                step=FiduciaryStep.CONTEXT,
                recommendation="Propose actions matching user's risk tolerance",
            ))

        return violations

    def _check_identification(self, action: str, context: UserContext) -> List[Violation]:
        """
        Check if user objectives are properly identified.

        Gate 2: IDENTIFICATION - Identify the user's objectives and constraints.
        """
        violations: List[Violation] = []

        # Check if action contradicts stated goals using semantic matching
        action_lower = action.lower()
        action_words = set(action_lower.split())

        for goal in context.goals:
            goal_lower = goal.lower()
            goal_words = set(goal_lower.split())

            # Define contradiction pairs with the SAME subject/topic requirement
            # Format: (goal_verb, action_verb, common_subjects)
            contradictions = [
                ("save", "spend", {"money", "funds", "budget", "savings", "cash"}),
                ("reduce", "increase", {"cost", "costs", "expense", "expenses", "spending", "risk", "debt"}),
                ("minimize", "maximize", {"cost", "costs", "expense", "expenses", "risk", "loss"}),
                ("avoid", "seek", {"risk", "debt", "loss", "exposure"}),
                ("cut", "raise", {"cost", "costs", "expense", "expenses", "spending"}),
                ("lower", "raise", {"cost", "costs", "expense", "expenses", "risk"}),
            ]

            for goal_verb, action_verb, subjects in contradictions:
                # Check if goal contains the verb and action contains the opposite
                if goal_verb in goal_lower and action_verb in action_lower:
                    # Require that both share at least one subject word to avoid false positives
                    shared_subjects = (goal_words | action_words) & subjects
                    if shared_subjects:
                        violations.append(Violation(
                            duty=FiduciaryDuty.LOYALTY,
                            type=ViolationType.MISALIGNED_RECOMMENDATION,
                            description=f"Action may contradict user goal '{goal}' (conflicting intent on: {', '.join(sorted(shared_subjects))})",
                            severity=Severity.MEDIUM,
                            step=FiduciaryStep.IDENTIFICATION,
                            recommendation="Align action with stated user goals",
                        ))
                        break  # One violation per goal is enough

        return violations

    def _check_alignment(
        self,
        action: str,
        context: UserContext,
        proposed_outcome: Optional[Dict[str, Any]],
    ) -> List[Violation]:
        """
        Check if action aligns with user interests.

        Gates 3-4: ASSESSMENT & AGGREGATION - Evaluate options against user's interests.
        """
        violations: List[Violation] = []

        # Check for potential user harm
        harm_indicators = [
            "loss", "damage", "harm", "risk", "danger",
            "penalty", "fee", "cost", "expense",
        ]
        mitigation_indicators = ["minimize", "reduce", "avoid", "prevent", "protect"]
        action_lower = action.lower()
        harm_found = [h for h in harm_indicators if h in action_lower]

        if harm_found and not any(d in action_lower for d in mitigation_indicators):
            violations.append(Violation(
                duty=FiduciaryDuty.CARE,
                type=ViolationType.UNDISCLOSED_RISK,
                description=f"Potential user harm indicators: {', '.join(sorted(harm_found))}",
                severity=Severity.MEDIUM,
                step=FiduciaryStep.ASSESSMENT,
                recommendation="Clearly disclose risks and potential downsides",
            ))

        return violations

    def _check_care(self, action: str, context: UserContext) -> List[Violation]:
        """
        Check duty of care - competence and diligence.

        Gate 6: CARE - Verify competence and diligence in execution.
        """
        violations: List[Violation] = []

        # Check for vague or non-specific actions
        vague_indicators = [
            "maybe", "possibly", "might", "could",
            "probably", "perhaps", "uncertain",
        ]
        action_lower = action.lower()

        vague_count = sum(1 for v in vague_indicators if v in action_lower)
        if vague_count >= 2:
            violations.append(Violation(
                duty=FiduciaryDuty.CARE,
                type=ViolationType.INCOMPETENT_ACTION,
                description="Action appears vague or uncertain",
                severity=Severity.LOW,
                step=FiduciaryStep.CARE,
                recommendation="Provide more specific and confident guidance",
            ))

        return violations

    def _check_transparency(self, action: str) -> List[Violation]:
        """
        Check transparency and explainability.

        Ensures decisions are not black-box but properly explained.
        """
        violations: List[Violation] = []

        # Check for unexplained recommendations
        unexplained_patterns = [
            "just do", "trust me", "don't worry about",
            "you don't need to know", "it's complicated",
        ]
        action_lower = action.lower()

        if any(p in action_lower for p in unexplained_patterns):
            violations.append(Violation(
                duty=FiduciaryDuty.TRANSPARENCY,
                type=ViolationType.LACK_OF_TRANSPARENCY,
                description="Action lacks proper explanation",
                severity=Severity.MEDIUM,
                step=FiduciaryStep.CARE,
                recommendation="Provide clear reasoning for recommendations",
            ))

        return violations

    def _check_confidentiality(self, action: str, context: UserContext) -> List[Violation]:
        """
        Check protection of user information.

        Ensures user's sensitive information is protected.
        """
        violations: List[Violation] = []

        # Check for sharing sensitive information
        share_patterns = ["share", "send", "post", "publish", "disclose"]
        action_lower = action.lower()

        for topic in context.sensitive_topics:
            topic_lower = topic.lower()
            if topic_lower in action_lower and any(p in action_lower for p in share_patterns):
                violations.append(Violation(
                    duty=FiduciaryDuty.CONFIDENTIALITY,
                    type=ViolationType.PRIVACY_VIOLATION,
                    description=f"Action may expose sensitive topic: {topic}",
                    severity=Severity.HIGH,
                    step=FiduciaryStep.CARE,
                    recommendation="Protect user's sensitive information",
                ))

        return violations


class FiduciaryGuard:
    """
    High-level guard for enforcing fiduciary principles.

    Wraps functions or actions with fiduciary validation.

    Thread Safety:
        This class is thread-safe. Decision logging uses locks
        to prevent race conditions.

    Example:
        guard = FiduciaryGuard()

        @guard.protect
        def recommend_investment(user_id: str, amount: float) -> str:
            return f"Invest {amount} in stocks"

        # The function will be validated before execution
        result = recommend_investment("user123", 1000)
    """

    def __init__(
        self,
        validator: Optional[FiduciaryValidator] = None,
        block_on_violation: bool = True,
        log_decisions: bool = True,
        max_log_size: int = 1000,
    ):
        """
        Initialize the fiduciary guard.

        Args:
            validator: FiduciaryValidator instance to use
            block_on_violation: If True, raise exception on violation
            log_decisions: If True, log all decisions
            max_log_size: Maximum number of entries in decision log
        """
        self.validator = validator or FiduciaryValidator()
        self.block_on_violation = block_on_violation
        self.log_decisions = log_decisions
        self.max_log_size = max_log_size

        # Thread-safe decision log
        self._log_lock = threading.Lock()
        self._decision_log: List[Dict[str, Any]] = []

    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with fiduciary validation.

        Args:
            func: Function to protect

        Returns:
            Wrapped function with validation
        """
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Build action description from function and args
            action = f"{func.__name__}({args}, {kwargs})"

            # Get user context if provided
            context = kwargs.get("user_context") or UserContext()
            if isinstance(context, dict):
                context = UserContext.from_dict(context)

            # Validate
            result = self.validator.validate_action(action, context)

            # Log decision
            if self.log_decisions:
                self._add_log_entry({
                    "function": func.__name__,
                    "args": str(args),
                    "kwargs": str(kwargs),
                    "compliant": result.compliant,
                    "violations": len(result.violations),
                    "timestamp": result.timestamp,
                })

            # Block if non-compliant
            if not result.compliant and self.block_on_violation:
                violation_summary = "; ".join(
                    v.description for v in result.violations
                )
                raise FiduciaryViolationError(
                    f"Fiduciary violation in {func.__name__}: {violation_summary}",
                    result=result,
                )

            return func(*args, **kwargs)

        return wrapper

    def _add_log_entry(self, entry: Dict[str, Any]) -> None:
        """Add entry to decision log (thread-safe)."""
        with self._log_lock:
            self._decision_log.append(entry)
            # Trim log if it exceeds max size
            if len(self._decision_log) > self.max_log_size:
                self._decision_log = self._decision_log[-self.max_log_size:]

    def validate_and_execute(
        self,
        action: Callable,
        user_context: Optional[UserContext] = None,
        action_description: Optional[str] = None,
    ) -> tuple:
        """
        Validate an action and execute if compliant.

        Args:
            action: Callable to execute
            user_context: User context for validation
            action_description: Human-readable description

        Returns:
            Tuple of (action result, fiduciary result)

        Raises:
            TypeError: If action is not callable
            FiduciaryViolationError: If action is non-compliant and blocking
        """
        if not callable(action):
            raise TypeError(f"action must be callable, got {type(action).__name__}")

        desc = action_description or f"Execute {getattr(action, '__name__', 'anonymous')}"
        result = self.validator.validate_action(desc, user_context)

        if not result.compliant and self.block_on_violation:
            raise FiduciaryViolationError(
                f"Fiduciary violation: {[v.description for v in result.violations]}",
                result=result,
            )

        action_result = action()
        return action_result, result

    @property
    def decision_log(self) -> List[Dict[str, Any]]:
        """Get copy of fiduciary decisions log (thread-safe)."""
        with self._log_lock:
            return list(self._decision_log)

    def clear_log(self) -> None:
        """Clear the decision log (thread-safe)."""
        with self._log_lock:
            self._decision_log.clear()


class FiduciaryViolationError(Exception):
    """Exception raised when a fiduciary violation is detected"""

    def __init__(self, message: str, result: FiduciaryResult):
        super().__init__(message)
        self.result = result


# Convenience functions

def validate_fiduciary(
    action: str,
    user_context: Optional[Dict[str, Any]] = None,
) -> FiduciaryResult:
    """
    Convenience function for one-off fiduciary validation.

    Args:
        action: Description of the action
        user_context: User context as dictionary

    Returns:
        FiduciaryResult
    """
    validator = FiduciaryValidator()
    context = UserContext.from_dict(user_context or {})
    return validator.validate_action(action, context)


def is_fiduciary_compliant(
    action: str,
    user_context: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    Quick check if an action is fiduciary-compliant.

    Args:
        action: Description of the action
        user_context: User context as dictionary

    Returns:
        True if compliant
    """
    result = validate_fiduciary(action, user_context)
    return result.compliant


__all__ = [
    # Main classes
    "FiduciaryValidator",
    "FiduciaryGuard",
    "ConflictDetector",
    # Data classes
    "FiduciaryResult",
    "UserContext",
    "Violation",
    # Enums
    "Severity",
    "RiskTolerance",
    "FiduciaryDuty",
    "ViolationType",
    "FiduciaryStep",
    # Exception
    "FiduciaryViolationError",
    # Convenience functions
    "validate_fiduciary",
    "is_fiduciary_compliant",
]
