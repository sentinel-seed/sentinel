"""
EU AI Act Compliance Checker using Sentinel THSP.

This module provides tools to assess AI system outputs against
EU AI Act (Regulation 2024/1689) requirements.

The EU AI Act establishes a risk-based regulatory framework:
- Article 5: Prohibited practices (effective Feb 2025)
- Article 6: High-risk classification
- Article 9: Risk management system
- Article 10: Data governance
- Article 13: Transparency
- Article 14: Human oversight
- Article 15: Accuracy, robustness, cybersecurity

THSP gates provide behavioral-level controls that support compliance:
- Truth Gate: Accuracy, transparency
- Harm Gate: Prohibited practices, risk assessment
- Scope Gate: Operational boundaries, human oversight
- Purpose Gate: Legitimate benefit justification
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger("sentinelseed.compliance.eu_ai_act")


class RiskLevel(str, Enum):
    """EU AI Act risk levels."""
    UNACCEPTABLE = "unacceptable"
    HIGH = "high"
    LIMITED = "limited"
    MINIMAL = "minimal"


class SystemType(str, Enum):
    """AI system type classification."""
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"
    MINIMAL_RISK = "minimal_risk"
    GPAI = "general_purpose_ai"


class OversightModel(str, Enum):
    """Human oversight models per Article 14."""
    HITL = "human_in_the_loop"
    HOTL = "human_on_the_loop"
    HIC = "human_in_command"


@dataclass
class Article5Violation:
    """Represents a potential Article 5 violation."""
    article_reference: str
    description: str
    severity: str  # "critical", "high", "medium"
    gate_failed: str
    recommendation: str


@dataclass
class RiskAssessment:
    """Article 9 risk assessment result."""
    context: str
    risk_factors: List[str]
    risk_score: float  # 0.0 = low, 1.0 = high
    mitigation_recommended: bool
    gates_evaluated: Dict[str, bool]


@dataclass
class ComplianceResult:
    """
    Complete EU AI Act compliance assessment result.

    Attributes:
        compliant: Overall compliance status
        risk_level: Determined risk level
        article_5_violations: List of potential Article 5 issues
        article_9_risk_assessment: Risk management assessment
        article_14_oversight_required: Whether human oversight is needed
        recommendations: List of compliance recommendations
        timestamp: When the check was performed
        metadata: Additional context
    """
    compliant: bool
    risk_level: RiskLevel
    article_5_violations: List[Article5Violation]
    article_9_risk_assessment: RiskAssessment
    article_14_oversight_required: bool
    recommendations: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "compliant": self.compliant,
            "risk_level": self.risk_level.value,
            "article_5_violations": [
                {
                    "article_reference": v.article_reference,
                    "description": v.description,
                    "severity": v.severity,
                    "gate_failed": v.gate_failed,
                    "recommendation": v.recommendation
                }
                for v in self.article_5_violations
            ],
            "article_9_risk_assessment": {
                "context": self.article_9_risk_assessment.context,
                "risk_factors": self.article_9_risk_assessment.risk_factors,
                "risk_score": self.article_9_risk_assessment.risk_score,
                "mitigation_recommended": self.article_9_risk_assessment.mitigation_recommended,
            },
            "article_14_oversight_required": self.article_14_oversight_required,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "metadata": self.metadata
        }


class EUAIActComplianceChecker:
    """
    Check AI system outputs against EU AI Act requirements.

    Uses THSP gates to assess compliance with:
    - Article 5: Prohibited practices
    - Article 9: Risk management
    - Article 13: Transparency
    - Article 14: Human oversight requirements

    Example:
        checker = EUAIActComplianceChecker(api_key="sk-...")

        result = checker.check_compliance(
            content="Based on your social behavior, your score is...",
            context="financial",
            system_type=SystemType.HIGH_RISK
        )

        if not result.compliant:
            print(f"Violations: {result.article_5_violations}")
            print(f"Recommendations: {result.recommendations}")
    """

    # Article 5 prohibited practice patterns
    PROHIBITED_PATTERNS = {
        "subliminal": {
            "keywords": ["subliminal", "subconscious", "hidden influence", "beyond awareness"],
            "article": "5(1)(a)",
            "description": "Subliminal or manipulative techniques"
        },
        "exploitation": {
            "keywords": ["exploit vulnerability", "target elderly", "target disabled", "exploit poverty"],
            "article": "5(1)(b)",
            "description": "Exploitation of vulnerabilities"
        },
        "social_scoring": {
            "keywords": ["social score", "behavior score", "citizen score", "trustworthiness score"],
            "article": "5(1)(c)",
            "description": "Social scoring systems"
        },
        "predictive_policing": {
            "keywords": ["criminal profile", "crime prediction", "risk of offense", "likely to commit"],
            "article": "5(1)(d)",
            "description": "Predictive policing based on profiling"
        },
        "facial_scraping": {
            "keywords": ["scrape faces", "facial database", "collect biometric", "mass surveillance"],
            "article": "5(1)(e)",
            "description": "Untargeted facial image scraping"
        },
        "emotion_workplace": {
            "keywords": ["detect emotion", "workplace emotion", "employee sentiment", "student emotion"],
            "article": "5(1)(f)",
            "description": "Emotion recognition in workplace/education"
        },
        "biometric_categorization": {
            "keywords": ["infer race", "deduce religion", "categorize sexuality", "biometric inference"],
            "article": "5(1)(g)",
            "description": "Biometric categorization of protected characteristics"
        },
        "realtime_biometric": {
            "keywords": ["real-time identification", "live facial recognition", "realtime biometric", "public space surveillance", "live biometric scan"],
            "article": "5(1)(h)",
            "description": "Real-time remote biometric identification in public spaces"
        }
    }

    # High-risk contexts per Annex III
    HIGH_RISK_CONTEXTS = [
        "biometric", "critical_infrastructure", "education", "employment",
        "essential_services", "law_enforcement", "migration", "justice",
        "democratic_processes", "healthcare"
    ]

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
    ):
        """
        Initialize compliance checker.

        Args:
            api_key: API key for semantic validation (recommended for accuracy)
            provider: LLM provider ("openai" or "anthropic")
            model: Specific model to use
        """
        self._api_key = api_key
        self._provider = provider
        self._model = model
        self._validator = None
        self._init_validator()

    def _init_validator(self):
        """Initialize the appropriate validator."""
        if self._api_key:
            try:
                from sentinelseed.validators.semantic import SemanticValidator
                self._validator = SemanticValidator(
                    provider=self._provider,
                    model=self._model,
                    api_key=self._api_key,
                )
                logger.info("Using SemanticValidator for EU AI Act compliance")
            except ImportError:
                logger.warning("SemanticValidator not available")

        if self._validator is None:
            try:
                from sentinelseed.validators.gates import THSPValidator
                self._validator = THSPValidator()
                logger.info("Using THSPValidator (heuristic) for EU AI Act compliance")
            except ImportError:
                logger.warning("No validator available")

    def check_compliance(
        self,
        content: str,
        context: str = "general",
        system_type: SystemType = SystemType.HIGH_RISK,
        include_metadata: bool = True,
    ) -> ComplianceResult:
        """
        Check content against EU AI Act requirements.

        Args:
            content: AI system output to validate
            context: Usage context (general, healthcare, employment, etc.)
            system_type: Risk classification of the AI system
            include_metadata: Whether to include detailed metadata

        Returns:
            ComplianceResult with detailed assessment
        """
        # Perform THSP validation
        gates, is_safe, failed_gates = self._validate_content(content)

        # Article 5: Check prohibited practices
        article_5_violations = self._check_article_5(content, gates, failed_gates)

        # Article 9: Risk assessment
        risk_assessment = self._assess_risk(gates, context)

        # Article 14: Determine oversight requirement
        oversight_required = self._check_oversight_requirement(
            gates, system_type, is_safe, context
        )

        # Determine risk level
        risk_level = self._determine_risk_level(article_5_violations, gates, context)

        # Generate recommendations
        recommendations = self._generate_recommendations(
            article_5_violations, gates, system_type, context
        )

        # Determine overall compliance
        compliant = (
            len(article_5_violations) == 0 and
            is_safe and
            risk_level != RiskLevel.UNACCEPTABLE
        )

        # Build metadata
        metadata = {}
        if include_metadata:
            metadata = {
                "validation_method": "semantic" if self._api_key else "heuristic",
                "gates_evaluated": gates,
                "failed_gates": failed_gates,
                "context_is_high_risk": context.lower() in self.HIGH_RISK_CONTEXTS,
                "system_type": system_type.value,
            }

        return ComplianceResult(
            compliant=compliant,
            risk_level=risk_level,
            article_5_violations=article_5_violations,
            article_9_risk_assessment=risk_assessment,
            article_14_oversight_required=oversight_required,
            recommendations=recommendations,
            metadata=metadata
        )

    def _validate_content(self, content: str) -> tuple:
        """Validate content through THSP gates."""
        if self._validator is None:
            logger.warning("No validator available - returning safe by default")
            return {}, True, []

        try:
            result = self._validator.validate(content)

            if hasattr(result, "is_safe"):
                # SemanticValidator - returns booleans directly
                return result.gate_results, result.is_safe, result.failed_gates
            else:
                # THSPValidator (dict) - returns strings "pass"/"fail"
                gates_raw = result.get("gates", {})
                # Convert "pass"/"fail" strings to booleans
                gates = {k: (v == "pass") for k, v in gates_raw.items()}
                is_safe = result.get("safe", True)
                # Extract gate names that failed (issues contains messages)
                failed = [k for k, v in gates.items() if not v]
                return gates, is_safe, failed

        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {}, True, []

    def _check_article_5(
        self,
        content: str,
        gates: Dict[str, bool],
        failed_gates: List[str]
    ) -> List[Article5Violation]:
        """Check for Article 5 prohibited practice violations."""
        violations = []
        content_lower = content.lower()

        # Check for prohibited patterns in content
        for practice_id, practice in self.PROHIBITED_PATTERNS.items():
            for keyword in practice["keywords"]:
                if keyword in content_lower:
                    violations.append(Article5Violation(
                        article_reference=f"Article {practice['article']}",
                        description=practice["description"],
                        severity="critical",
                        gate_failed="harm" if "exploit" in keyword or "manipul" in keyword else "scope",
                        recommendation=f"Remove or modify content related to: {keyword}"
                    ))
                    break  # One match per practice is enough

        # Check gate failures for implicit violations
        if not gates.get("harm", True) and "harm" in failed_gates:
            if not any(v.gate_failed == "harm" for v in violations):
                violations.append(Article5Violation(
                    article_reference="Article 5(1)(a-b)",
                    description="Potential manipulation or harm detected by THSP",
                    severity="high",
                    gate_failed="harm",
                    recommendation="Review content for potential harm or manipulation"
                ))

        if not gates.get("purpose", True) and "purpose" in failed_gates:
            # Note: Article 5(1)(c) is about social scoring, not purpose
            # Purpose gate failures relate to Article 9 (Risk Management)
            violations.append(Article5Violation(
                article_reference="Article 9",
                description="No legitimate purpose identified - risk management review required",
                severity="medium",
                gate_failed="purpose",
                recommendation="Document legitimate purpose per Article 9 risk management requirements"
            ))

        return violations

    def _assess_risk(
        self,
        gates: Dict[str, bool],
        context: str
    ) -> RiskAssessment:
        """Perform Article 9 risk assessment."""
        risk_factors = []

        if not gates.get("truth", True):
            risk_factors.append("Accuracy risk: Output may contain inaccurate information")

        if not gates.get("harm", True):
            risk_factors.append("Safety risk: Output may cause harm to individuals")

        if not gates.get("scope", True):
            risk_factors.append("Boundary risk: Output exceeds appropriate operational scope")

        if not gates.get("purpose", True):
            risk_factors.append("Justification risk: No clear legitimate benefit identified")

        # Context-specific risks
        if context.lower() in self.HIGH_RISK_CONTEXTS:
            risk_factors.append(f"Context risk: '{context}' is classified as high-risk per Annex III")

        # Calculate risk score (0.0 = low, 1.0 = high)
        gate_failures = sum(1 for v in gates.values() if not v)
        context_risk = 0.2 if context.lower() in self.HIGH_RISK_CONTEXTS else 0
        risk_score = min(1.0, (gate_failures / 4) + context_risk)

        return RiskAssessment(
            context=context,
            risk_factors=risk_factors,
            risk_score=risk_score,
            mitigation_recommended=len(risk_factors) > 0,
            gates_evaluated=gates
        )

    def _check_oversight_requirement(
        self,
        gates: Dict[str, bool],
        system_type: SystemType,
        is_safe: bool,
        context: str
    ) -> bool:
        """Determine if human oversight is required per Article 14."""

        # High-risk systems always require oversight capability
        if system_type == SystemType.HIGH_RISK:
            return True

        # High-risk contexts require oversight
        if context.lower() in self.HIGH_RISK_CONTEXTS:
            return True

        # Any gate failure triggers oversight
        if not is_safe:
            return True

        # Purpose gate failure specifically triggers oversight
        if not gates.get("purpose", True):
            return True

        # Harm gate failure requires human review
        if not gates.get("harm", True):
            return True

        return False

    def _determine_risk_level(
        self,
        violations: List[Article5Violation],
        gates: Dict[str, bool],
        context: str
    ) -> RiskLevel:
        """Determine EU AI Act risk level."""

        # Critical Article 5 violations = unacceptable
        critical_violations = [v for v in violations if v.severity == "critical"]
        if len(critical_violations) > 0:
            return RiskLevel.UNACCEPTABLE

        # High-risk context with issues = high
        if context.lower() in self.HIGH_RISK_CONTEXTS:
            if len(violations) > 0 or not all(gates.values()):
                return RiskLevel.HIGH
            return RiskLevel.HIGH  # Still high due to context

        # Multiple gate failures = high risk
        failed_count = sum(1 for v in gates.values() if not v)
        if failed_count >= 2:
            return RiskLevel.HIGH

        # Single gate failure or non-critical violation = limited risk
        if failed_count == 1 or len(violations) > 0:
            return RiskLevel.LIMITED

        return RiskLevel.MINIMAL

    def _generate_recommendations(
        self,
        violations: List[Article5Violation],
        gates: Dict[str, bool],
        system_type: SystemType,
        context: str
    ) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []

        # Critical: Address Article 5 violations first
        if len(violations) > 0:
            critical = [v for v in violations if v.severity == "critical"]
            if critical:
                recommendations.append(
                    "CRITICAL: Address Article 5 prohibited practice violations immediately"
                )
            else:
                recommendations.append(
                    "HIGH: Review and address potential Article 5 issues"
                )

        # Gate-specific recommendations
        if not gates.get("truth", True):
            recommendations.append(
                "Article 15: Implement accuracy verification measures"
            )

        if not gates.get("harm", True):
            recommendations.append(
                "Article 9: Add harm mitigation controls to risk management system"
            )

        if not gates.get("scope", True):
            recommendations.append(
                "Article 14: Implement operational boundary enforcement"
            )

        if not gates.get("purpose", True):
            recommendations.append(
                "Article 11: Document legitimate purpose in technical documentation"
            )

        # System type recommendations
        if system_type == SystemType.HIGH_RISK:
            recommendations.extend([
                "Article 14: Ensure human oversight capability is implemented",
                "Article 11: Maintain complete technical documentation",
                "Article 12: Implement automatic logging and record-keeping",
                "Article 17: Establish quality management system"
            ])

        # Context recommendations
        if context.lower() in self.HIGH_RISK_CONTEXTS:
            recommendations.append(
                f"Annex III: Context '{context}' requires conformity assessment"
            )

        return recommendations


def check_eu_ai_act_compliance(
    content: str,
    api_key: Optional[str] = None,
    context: str = "general",
    system_type: str = "high_risk"
) -> Dict[str, Any]:
    """
    Convenience function to check EU AI Act compliance.

    Args:
        content: AI system output to validate
        api_key: Optional API key for semantic validation
        context: Usage context
        system_type: Risk classification ("high_risk", "limited_risk", "minimal_risk")

    Returns:
        Dict with compliance assessment

    Example:
        result = check_eu_ai_act_compliance(
            "Your social score is 650 based on your online behavior",
            api_key="sk-...",
            context="financial"
        )
        # result["compliant"] = False
        # result["risk_level"] = "unacceptable"
    """
    type_map = {
        "high_risk": SystemType.HIGH_RISK,
        "limited_risk": SystemType.LIMITED_RISK,
        "minimal_risk": SystemType.MINIMAL_RISK,
        "gpai": SystemType.GPAI
    }

    checker = EUAIActComplianceChecker(api_key=api_key)
    result = checker.check_compliance(
        content=content,
        context=context,
        system_type=type_map.get(system_type, SystemType.HIGH_RISK)
    )

    return result.to_dict()


# Export for convenience
__all__ = [
    "EUAIActComplianceChecker",
    "ComplianceResult",
    "RiskAssessment",
    "Article5Violation",
    "RiskLevel",
    "SystemType",
    "OversightModel",
    "check_eu_ai_act_compliance",
]
