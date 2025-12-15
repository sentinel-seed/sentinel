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

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("sentinelseed.fiduciary")


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
    severity: str  # "low", "medium", "high", "critical"
    step: Optional[FiduciaryStep] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "duty": self.duty.value,
            "type": self.type.value,
            "description": self.description,
            "severity": self.severity,
            "step": self.step.value if self.step else None,
            "recommendation": self.recommendation,
        }


@dataclass
class FiduciaryResult:
    """Result of fiduciary validation"""
    compliant: bool
    violations: List[Violation] = field(default_factory=list)
    passed_duties: List[FiduciaryDuty] = field(default_factory=list)
    explanations: Dict[str, str] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

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
    risk_tolerance: str = "moderate"  # low, moderate, high
    preferences: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)
    sensitive_topics: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UserContext":
        return cls(
            user_id=data.get("user_id"),
            goals=data.get("goals", []),
            constraints=data.get("constraints", []),
            risk_tolerance=data.get("risk_tolerance", "moderate"),
            preferences=data.get("preferences", {}),
            history=data.get("history", []),
            sensitive_topics=data.get("sensitive_topics", []),
        )


class ConflictDetector:
    """
    Detects conflicts of interest in AI actions.

    Identifies situations where AI might be acting in its own interest
    or the provider's interest rather than the user's.
    """

    # Patterns that indicate potential conflicts
    CONFLICT_PATTERNS = [
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
    PROVIDER_BENEFIT_KEYWORDS = {
        "affiliate", "commission", "sponsored", "partner",
        "premium", "upgrade", "subscribe", "monetize",
    }

    def __init__(self, custom_patterns: Optional[List[Tuple[str, str]]] = None):
        self.patterns = list(self.CONFLICT_PATTERNS)
        if custom_patterns:
            self.patterns.extend(custom_patterns)
        self._compile_patterns()

    def _compile_patterns(self):
        """Compile regex patterns"""
        self._compiled = [(re.compile(p, re.IGNORECASE), t) for p, t in self.patterns]

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
        """
        violations = []
        text = f"{action} {context or ''}"

        # Check patterns
        for pattern, conflict_type in self._compiled:
            if pattern.search(text):
                violations.append(Violation(
                    duty=FiduciaryDuty.LOYALTY,
                    type=ViolationType.CONFLICT_OF_INTEREST,
                    description=f"Potential {conflict_type.replace('_', ' ')} detected",
                    severity="medium",
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
                description=f"Undisclosed potential benefit indicators: {', '.join(found_keywords)}",
                severity="low",
                step=FiduciaryStep.LOYALTY,
                recommendation="Clearly disclose any commercial relationships",
            ))

        return violations


class FiduciaryValidator:
    """
    Validates AI actions against fiduciary duties.

    Ensures AI systems act with loyalty and care toward users,
    following the six-step fiduciary framework.

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
        Args:
            strict_mode: If True, flag any potential violation
            require_all_duties: If True, all duties must pass
            custom_rules: Additional validation rules (callable(action, context) -> violations)
        """
        self.strict_mode = strict_mode
        self.require_all_duties = require_all_duties
        self.custom_rules = custom_rules or []
        self.conflict_detector = ConflictDetector()

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
        """
        context = user_context or UserContext()
        violations = []
        passed_duties = []
        explanations = {}

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

        # Run custom rules
        for rule in self.custom_rules:
            try:
                custom_violations = rule(action, context)
                if custom_violations:
                    violations.extend(custom_violations)
            except Exception as e:
                logger.warning(f"Custom rule error: {e}")

        # Determine compliance
        if self.require_all_duties:
            compliant = len(violations) == 0
        else:
            # Compliant if no high/critical violations
            compliant = not any(
                v.severity in ["high", "critical"] for v in violations
            )

        if self.strict_mode:
            compliant = len(violations) == 0

        # Calculate confidence
        confidence = 1.0 - (len(violations) * 0.15)
        confidence = max(0.0, min(1.0, confidence))

        return FiduciaryResult(
            compliant=compliant,
            violations=violations,
            passed_duties=passed_duties,
            explanations=explanations,
            confidence=confidence,
        )

    def _check_context(self, action: str, context: UserContext) -> List[Violation]:
        """Check if action considers user context"""
        violations = []

        # Check if action matches risk tolerance
        action_lower = action.lower()
        high_risk_indicators = ["high risk", "aggressive", "volatile", "speculative"]
        low_risk_context = context.risk_tolerance == "low"

        if low_risk_context and any(ind in action_lower for ind in high_risk_indicators):
            violations.append(Violation(
                duty=FiduciaryDuty.CARE,
                type=ViolationType.MISALIGNED_RECOMMENDATION,
                description="High-risk action proposed for low-risk-tolerance user",
                severity="high",
                step=FiduciaryStep.CONTEXT,
                recommendation="Propose actions matching user's risk tolerance",
            ))

        return violations

    def _check_identification(self, action: str, context: UserContext) -> List[Violation]:
        """Check if user objectives are properly identified"""
        violations = []

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
                    # e.g., "reduce expenses" vs "increase security" should NOT trigger
                    # but "reduce expenses" vs "increase spending" SHOULD trigger
                    shared_subjects = (goal_words | action_words) & subjects
                    if shared_subjects:
                        violations.append(Violation(
                            duty=FiduciaryDuty.LOYALTY,
                            type=ViolationType.MISALIGNED_RECOMMENDATION,
                            description=f"Action may contradict user goal '{goal}' (conflicting intent on: {', '.join(shared_subjects)})",
                            severity="medium",
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
        """Check if action aligns with user interests"""
        violations = []

        # Check for potential user harm
        harm_indicators = [
            "loss", "damage", "harm", "risk", "danger",
            "penalty", "fee", "cost", "expense",
        ]
        action_lower = action.lower()
        harm_found = [h for h in harm_indicators if h in action_lower]

        if harm_found and not any(
            d in action_lower for d in ["minimize", "reduce", "avoid", "prevent"]
        ):
            violations.append(Violation(
                duty=FiduciaryDuty.CARE,
                type=ViolationType.UNDISCLOSED_RISK,
                description=f"Potential user harm indicators: {', '.join(harm_found)}",
                severity="medium",
                step=FiduciaryStep.ASSESSMENT,
                recommendation="Clearly disclose risks and potential downsides",
            ))

        return violations

    def _check_care(self, action: str, context: UserContext) -> List[Violation]:
        """Check duty of care - competence and diligence"""
        violations = []

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
                severity="low",
                step=FiduciaryStep.CARE,
                recommendation="Provide more specific and confident guidance",
            ))

        return violations

    def _check_transparency(self, action: str) -> List[Violation]:
        """Check transparency and explainability"""
        violations = []

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
                severity="medium",
                step=FiduciaryStep.CARE,
                recommendation="Provide clear reasoning for recommendations",
            ))

        return violations

    def _check_confidentiality(self, action: str, context: UserContext) -> List[Violation]:
        """Check protection of user information"""
        violations = []

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
                    severity="high",
                    step=FiduciaryStep.CARE,
                    recommendation="Protect user's sensitive information",
                ))

        return violations


class FiduciaryGuard:
    """
    High-level guard for enforcing fiduciary principles.

    Wraps functions or actions with fiduciary validation.

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
    ):
        self.validator = validator or FiduciaryValidator()
        self.block_on_violation = block_on_violation
        self.log_decisions = log_decisions
        self._decision_log: List[Dict[str, Any]] = []

    def protect(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with fiduciary validation.

        Args:
            func: Function to protect

        Returns:
            Wrapped function with validation
        """
        import functools

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
                self._decision_log.append({
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

    def validate_and_execute(
        self,
        action: Callable,
        user_context: Optional[UserContext] = None,
        action_description: Optional[str] = None,
    ) -> Tuple[Any, FiduciaryResult]:
        """
        Validate an action and execute if compliant.

        Args:
            action: Callable to execute
            user_context: User context for validation
            action_description: Human-readable description

        Returns:
            Tuple of (action result, fiduciary result)
        """
        desc = action_description or f"Execute {action.__name__}"
        result = self.validator.validate_action(desc, user_context)

        if not result.compliant and self.block_on_violation:
            raise FiduciaryViolationError(
                f"Fiduciary violation: {result.violations}",
                result=result,
            )

        action_result = action()
        return action_result, result

    @property
    def decision_log(self) -> List[Dict[str, Any]]:
        """Get log of fiduciary decisions"""
        return self._decision_log.copy()


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
    "FiduciaryDuty",
    "ViolationType",
    "FiduciaryStep",
    # Exception
    "FiduciaryViolationError",
    # Convenience functions
    "validate_fiduciary",
    "is_fiduciary_compliant",
]
