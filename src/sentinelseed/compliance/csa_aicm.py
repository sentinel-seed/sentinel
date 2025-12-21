"""
CSA AI Controls Matrix (AICM) Compliance Checker using Sentinel THSP.

This module provides tools to assess AI system outputs against
CSA AI Controls Matrix requirements.

The CSA AICM (v1.0, July 2025) is a vendor-agnostic framework with:
- 18 security domains
- 243 control objectives
- 5 analytical pillars
- 9 threat categories

THSP gates provide behavioral-level controls that support several domains:
- Truth Gate: Model Security, Data Security, Governance
- Harm Gate: Threat Management, Application Security, Data Security
- Scope Gate: Application Security, IAM, Threat Management
- Purpose Gate: Supply Chain, Transparency, Accountability

Reference: https://cloudsecurityalliance.org/artifacts/ai-controls-matrix
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger("sentinelseed.compliance.csa_aicm")


class AICMDomain(str, Enum):
    """CSA AI Controls Matrix 18 security domains."""
    AUDIT_ASSURANCE = "audit_assurance"
    APPLICATION_INTERFACE_SECURITY = "application_interface_security"
    BUSINESS_CONTINUITY = "business_continuity"
    CHANGE_CONTROL = "change_control"
    CRYPTOGRAPHY = "cryptography"
    DATACENTER_SECURITY = "datacenter_security"
    DATA_SECURITY_PRIVACY = "data_security_privacy"
    GOVERNANCE_RISK_COMPLIANCE = "governance_risk_compliance"
    HUMAN_RESOURCES = "human_resources"
    IAM = "identity_access_management"
    INTEROPERABILITY = "interoperability_portability"
    INFRASTRUCTURE_SECURITY = "infrastructure_security"
    LOGGING_MONITORING = "logging_monitoring"
    MODEL_SECURITY = "model_security"
    SECURITY_INCIDENT_MANAGEMENT = "security_incident_management"
    SUPPLY_CHAIN = "supply_chain_transparency_accountability"
    THREAT_VULNERABILITY = "threat_vulnerability_management"
    ENDPOINT_MANAGEMENT = "endpoint_management"


class ThreatCategory(str, Enum):
    """CSA AICM 9 threat categories."""
    MODEL_MANIPULATION = "model_manipulation"
    DATA_POISONING = "data_poisoning"
    SENSITIVE_DATA_DISCLOSURE = "sensitive_data_disclosure"
    MODEL_THEFT = "model_theft"
    SERVICE_FAILURES = "service_failures"
    INSECURE_SUPPLY_CHAINS = "insecure_supply_chains"
    INSECURE_APPS_PLUGINS = "insecure_apps_plugins"
    DENIAL_OF_SERVICE = "denial_of_service"
    LOSS_OF_GOVERNANCE = "loss_of_governance"


class CoverageLevel(str, Enum):
    """THSP coverage level for AICM domains."""
    STRONG = "strong"
    MODERATE = "moderate"
    INDIRECT = "indirect"
    NOT_APPLICABLE = "not_applicable"


class Severity(str, Enum):
    """Severity levels for compliance findings."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_string(cls, value: str) -> "Severity":
        """Convert string to Severity enum."""
        if isinstance(value, cls):
            return value
        normalized = value.lower().strip() if isinstance(value, str) else ""
        for member in cls:
            if member.value == normalized:
                return member
        raise ValueError(f"Invalid severity '{value}'")


# Domain to THSP Gate mapping
DOMAIN_GATE_MAPPING: Dict[AICMDomain, Dict[str, Any]] = {
    AICMDomain.MODEL_SECURITY: {
        "gates": ["truth", "harm", "scope", "purpose"],
        "coverage": CoverageLevel.STRONG,
        "description": "Model integrity, adversarial robustness, output validation"
    },
    AICMDomain.GOVERNANCE_RISK_COMPLIANCE: {
        "gates": ["truth", "harm", "scope", "purpose"],
        "coverage": CoverageLevel.STRONG,
        "description": "Risk assessment, policy enforcement, ethical guidelines"
    },
    AICMDomain.SUPPLY_CHAIN: {
        "gates": ["purpose", "truth"],
        "coverage": CoverageLevel.STRONG,
        "description": "Accountability, transparency, decision justification"
    },
    AICMDomain.DATA_SECURITY_PRIVACY: {
        "gates": ["truth", "harm"],
        "coverage": CoverageLevel.MODERATE,
        "description": "PII protection, privacy by design"
    },
    AICMDomain.THREAT_VULNERABILITY: {
        "gates": ["scope", "harm"],
        "coverage": CoverageLevel.MODERATE,
        "description": "Threat detection, attack surface reduction"
    },
    AICMDomain.APPLICATION_INTERFACE_SECURITY: {
        "gates": ["scope", "harm"],
        "coverage": CoverageLevel.MODERATE,
        "description": "Input validation, output sanitization"
    },
    AICMDomain.AUDIT_ASSURANCE: {
        "gates": ["purpose"],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Validation data for audit trails"
    },
    AICMDomain.IAM: {
        "gates": ["scope"],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Privilege escalation detection"
    },
    AICMDomain.LOGGING_MONITORING: {
        "gates": [],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Validation results can be logged"
    },
    AICMDomain.SECURITY_INCIDENT_MANAGEMENT: {
        "gates": ["harm"],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Incident data from blocked actions"
    },
    # Not applicable domains
    AICMDomain.BUSINESS_CONTINUITY: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Operational resilience - infrastructure level"
    },
    AICMDomain.CHANGE_CONTROL: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Configuration management - infrastructure level"
    },
    AICMDomain.CRYPTOGRAPHY: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Encryption - infrastructure level"
    },
    AICMDomain.DATACENTER_SECURITY: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Physical security - infrastructure level"
    },
    AICMDomain.HUMAN_RESOURCES: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Personnel security - infrastructure level"
    },
    AICMDomain.INTEROPERABILITY: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "System integration - infrastructure level"
    },
    AICMDomain.INFRASTRUCTURE_SECURITY: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Network/compute security - infrastructure level"
    },
    AICMDomain.ENDPOINT_MANAGEMENT: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Device management - infrastructure level"
    },
}

# Threat category to THSP Gate mapping
THREAT_GATE_MAPPING: Dict[ThreatCategory, Dict[str, Any]] = {
    ThreatCategory.MODEL_MANIPULATION: {
        "gates": ["scope"],
        "coverage": CoverageLevel.STRONG,
        "description": "Prompt injection, jailbreak detection"
    },
    ThreatCategory.SENSITIVE_DATA_DISCLOSURE: {
        "gates": ["harm"],
        "coverage": CoverageLevel.STRONG,
        "description": "PII and sensitive data blocking"
    },
    ThreatCategory.LOSS_OF_GOVERNANCE: {
        "gates": ["purpose"],
        "coverage": CoverageLevel.STRONG,
        "description": "Accountability and decision justification"
    },
    ThreatCategory.INSECURE_APPS_PLUGINS: {
        "gates": ["scope"],
        "coverage": CoverageLevel.MODERATE,
        "description": "Boundary enforcement for extensions"
    },
    ThreatCategory.DATA_POISONING: {
        "gates": ["truth"],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Output validation may catch poisoned data effects"
    },
    ThreatCategory.INSECURE_SUPPLY_CHAINS: {
        "gates": ["purpose"],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Sentinel itself is a trusted component"
    },
    ThreatCategory.MODEL_THEFT: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Infrastructure-level protection"
    },
    ThreatCategory.SERVICE_FAILURES: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Availability - infrastructure level"
    },
    ThreatCategory.DENIAL_OF_SERVICE: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Rate limiting - infrastructure level"
    },
}


@dataclass
class DomainFinding:
    """
    Represents a compliance finding for an AICM domain.

    Attributes:
        domain: The AICM domain assessed
        compliant: Whether the content complies with domain requirements
        coverage_level: THSP coverage level for this domain
        gates_checked: Which THSP gates were evaluated
        gates_passed: Which gates passed
        gates_failed: Which gates failed
        severity: Severity of any findings
        recommendation: Suggested action
    """
    domain: AICMDomain
    compliant: bool
    coverage_level: CoverageLevel
    gates_checked: List[str]
    gates_passed: List[str]
    gates_failed: List[str]
    severity: Optional[Severity] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "domain": self.domain.value,
            "compliant": self.compliant,
            "coverage_level": self.coverage_level.value,
            "gates_checked": self.gates_checked,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "severity": self.severity.value if self.severity else None,
            "recommendation": self.recommendation,
        }


@dataclass
class ThreatAssessment:
    """
    Represents threat assessment against AICM threat categories.

    Attributes:
        threats_mitigated: Threat categories addressed by THSP
        threats_detected: Specific threats detected in content
        overall_threat_score: 0.0 (low) to 1.0 (high)
    """
    threats_mitigated: List[ThreatCategory]
    threats_detected: List[str]
    overall_threat_score: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "threats_mitigated": [t.value for t in self.threats_mitigated],
            "threats_detected": self.threats_detected,
            "overall_threat_score": self.overall_threat_score,
        }


@dataclass
class AICMComplianceResult:
    """
    Complete CSA AICM compliance assessment result.

    Attributes:
        compliant: Overall compliance status
        domains_assessed: Number of domains evaluated
        domains_compliant: Number of domains passing
        compliance_rate: Percentage of domains compliant
        domain_findings: Detailed findings per domain
        threat_assessment: Threat category analysis
        recommendations: List of compliance recommendations
        timestamp: When the check was performed
        metadata: Additional context
    """
    compliant: bool
    domains_assessed: int
    domains_compliant: int
    compliance_rate: float
    domain_findings: List[DomainFinding]
    threat_assessment: ThreatAssessment
    recommendations: List[str]
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "compliant": self.compliant,
            "domains_assessed": self.domains_assessed,
            "domains_compliant": self.domains_compliant,
            "compliance_rate": self.compliance_rate,
            "domain_findings": [f.to_dict() for f in self.domain_findings],
            "threat_assessment": self.threat_assessment.to_dict(),
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class CSAAICMComplianceChecker:
    """
    Check AI system outputs against CSA AI Controls Matrix requirements.

    Uses THSP gates to assess compliance with applicable AICM domains:
    - Domain 14: Model Security (Strong)
    - Domain 8: Governance, Risk and Compliance (Strong)
    - Domain 16: Supply Chain, Transparency, Accountability (Strong)
    - Domain 7: Data Security and Privacy (Moderate)
    - Domain 17: Threat and Vulnerability Management (Moderate)
    - Domain 2: Application and Interface Security (Moderate)

    Example:
        checker = CSAAICMComplianceChecker(api_key="sk-...")

        result = checker.check_compliance(
            content="Based on user data analysis...",
            domains=[AICMDomain.MODEL_SECURITY, AICMDomain.DATA_SECURITY_PRIVACY]
        )

        if not result.compliant:
            print(f"Issues found in {result.domains_assessed - result.domains_compliant} domains")
            print(f"Recommendations: {result.recommendations}")
    """

    # Domains with THSP support
    SUPPORTED_DOMAINS = [
        AICMDomain.MODEL_SECURITY,
        AICMDomain.GOVERNANCE_RISK_COMPLIANCE,
        AICMDomain.SUPPLY_CHAIN,
        AICMDomain.DATA_SECURITY_PRIVACY,
        AICMDomain.THREAT_VULNERABILITY,
        AICMDomain.APPLICATION_INTERFACE_SECURITY,
        AICMDomain.AUDIT_ASSURANCE,
        AICMDomain.IAM,
        AICMDomain.LOGGING_MONITORING,
        AICMDomain.SECURITY_INCIDENT_MANAGEMENT,
    ]

    # Default maximum content size (50KB)
    DEFAULT_MAX_CONTENT_SIZE = 50 * 1024

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        fail_closed: bool = False,
        max_content_size: int = DEFAULT_MAX_CONTENT_SIZE,
    ):
        """
        Initialize compliance checker.

        Args:
            api_key: API key for semantic validation (recommended for accuracy)
            provider: LLM provider ("openai" or "anthropic")
            model: Specific model to use
            fail_closed: If True, treat validation errors as non-compliant
            max_content_size: Maximum content size in bytes (default 50KB)

        Raises:
            ValueError: If provider is not "openai" or "anthropic"
            ValueError: If max_content_size is not positive
        """
        valid_providers = ("openai", "anthropic")
        if provider not in valid_providers:
            raise ValueError(
                f"Invalid provider '{provider}'. Valid providers: {valid_providers}"
            )

        if not isinstance(max_content_size, int) or max_content_size <= 0:
            raise ValueError(
                f"max_content_size must be a positive integer, got: {max_content_size}"
            )

        self._api_key = api_key
        self._provider = provider
        self._model = model
        self._fail_closed = fail_closed
        self._max_content_size = max_content_size
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
                logger.info("Using SemanticValidator for CSA AICM compliance")
            except ImportError:
                logger.warning("SemanticValidator not available")

        if self._validator is None:
            try:
                from sentinelseed.validators.gates import THSPValidator
                self._validator = THSPValidator()
                logger.info("Using THSPValidator (heuristic) for CSA AICM compliance")
            except ImportError:
                logger.warning("No validator available")

    def check_compliance(
        self,
        content: str,
        domains: Optional[List[AICMDomain]] = None,
        include_metadata: bool = True,
    ) -> AICMComplianceResult:
        """
        Check content against CSA AICM requirements.

        Args:
            content: AI system output to validate
            domains: Specific domains to check (default: all supported)
            include_metadata: Whether to include detailed metadata

        Returns:
            AICMComplianceResult with detailed assessment

        Raises:
            ValueError: If content is None, empty, or not a string
            ValueError: If content exceeds max_content_size
        """
        # Validate content
        if content is None:
            raise ValueError("content cannot be None")
        if not isinstance(content, str):
            raise ValueError(f"content must be a string, got: {type(content).__name__}")
        if len(content.strip()) == 0:
            raise ValueError("content cannot be empty or whitespace only")
        if len(content.encode("utf-8")) > self._max_content_size:
            raise ValueError(
                f"content size ({len(content.encode('utf-8'))} bytes) exceeds "
                f"maximum allowed ({self._max_content_size} bytes)"
            )

        # Default to all supported domains
        if domains is None:
            domains = self.SUPPORTED_DOMAINS

        # Filter to only supported domains
        domains = [d for d in domains if d in self.SUPPORTED_DOMAINS]

        # Perform THSP validation
        gates, is_safe, failed_gates = self._validate_content(content)

        # Assess each domain
        domain_findings = []
        for domain in domains:
            finding = self._assess_domain(domain, gates)
            domain_findings.append(finding)

        # Threat assessment
        threat_assessment = self._assess_threats(content, gates, failed_gates)

        # Generate recommendations
        recommendations = self._generate_recommendations(domain_findings, gates)

        # Calculate compliance metrics
        domains_compliant = sum(1 for f in domain_findings if f.compliant)
        compliance_rate = domains_compliant / len(domains) if domains else 0

        # Overall compliance (all assessed domains must pass)
        compliant = all(f.compliant for f in domain_findings) and is_safe

        # Build metadata
        metadata = {}
        if include_metadata:
            metadata = {
                "framework": "CSA AI Controls Matrix v1.0",
                "validation_method": "semantic" if self._api_key else "heuristic",
                "gates_evaluated": gates,
                "failed_gates": failed_gates,
                "supported_domains": [d.value for d in self.SUPPORTED_DOMAINS],
            }

        return AICMComplianceResult(
            compliant=compliant,
            domains_assessed=len(domains),
            domains_compliant=domains_compliant,
            compliance_rate=compliance_rate,
            domain_findings=domain_findings,
            threat_assessment=threat_assessment,
            recommendations=recommendations,
            metadata=metadata,
        )

    def _validate_content(
        self, content: str
    ) -> Tuple[Dict[str, bool], bool, List[str]]:
        """Validate content through THSP gates."""
        if self._validator is None:
            if self._fail_closed:
                logger.warning("No validator - fail_closed: treating as non-compliant")
                return {}, False, ["no_validator"]
            else:
                logger.warning("No validator - returning safe by default")
                return {}, True, []

        try:
            result = self._validator.validate(content)

            if hasattr(result, "is_safe"):
                return result.gate_results, result.is_safe, result.failed_gates
            else:
                gates_raw = result.get("gates", {})
                gates = {k: (v == "pass") for k, v in gates_raw.items()}
                is_safe = result.get("safe", True)
                failed = [k for k, v in gates.items() if not v]
                return gates, is_safe, failed

        except Exception as e:
            logger.error(f"Validation error: {e}")
            if self._fail_closed:
                return {}, False, ["validation_error"]
            else:
                return {}, True, []

    def _assess_domain(
        self,
        domain: AICMDomain,
        gates: Dict[str, bool]
    ) -> DomainFinding:
        """Assess compliance for a specific domain."""
        mapping = DOMAIN_GATE_MAPPING.get(domain, {})
        relevant_gates = mapping.get("gates", [])
        coverage = mapping.get("coverage", CoverageLevel.NOT_APPLICABLE)

        if not relevant_gates or coverage == CoverageLevel.NOT_APPLICABLE:
            return DomainFinding(
                domain=domain,
                compliant=True,  # N/A domains are considered compliant
                coverage_level=coverage,
                gates_checked=[],
                gates_passed=[],
                gates_failed=[],
                recommendation="Domain not applicable to THSP - use infrastructure controls"
            )

        gates_passed = [g for g in relevant_gates if gates.get(g, True)]
        gates_failed = [g for g in relevant_gates if not gates.get(g, True)]

        compliant = len(gates_failed) == 0

        severity = None
        recommendation = None

        if not compliant:
            if coverage == CoverageLevel.STRONG:
                severity = Severity.HIGH
            elif coverage == CoverageLevel.MODERATE:
                severity = Severity.MEDIUM
            else:
                severity = Severity.LOW

            recommendation = self._get_domain_recommendation(domain, gates_failed)

        return DomainFinding(
            domain=domain,
            compliant=compliant,
            coverage_level=coverage,
            gates_checked=relevant_gates,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            severity=severity,
            recommendation=recommendation,
        )

    def _get_domain_recommendation(
        self,
        domain: AICMDomain,
        failed_gates: List[str]
    ) -> str:
        """Get domain-specific recommendation."""
        recommendations = {
            AICMDomain.MODEL_SECURITY: "Implement additional model security controls: input sanitization, output filtering, adversarial testing",
            AICMDomain.GOVERNANCE_RISK_COMPLIANCE: "Review governance policies and risk management procedures",
            AICMDomain.SUPPLY_CHAIN: "Document decision accountability and ensure transparency requirements",
            AICMDomain.DATA_SECURITY_PRIVACY: "Review data handling practices and privacy controls",
            AICMDomain.THREAT_VULNERABILITY: "Conduct threat assessment and implement additional mitigations",
            AICMDomain.APPLICATION_INTERFACE_SECURITY: "Strengthen input validation and output sanitization",
            AICMDomain.AUDIT_ASSURANCE: "Ensure validation results are logged for audit trails",
            AICMDomain.IAM: "Review access controls and boundary enforcement",
            AICMDomain.LOGGING_MONITORING: "Implement comprehensive logging of THSP validation events",
            AICMDomain.SECURITY_INCIDENT_MANAGEMENT: "Establish incident response procedures for blocked actions",
        }
        return recommendations.get(domain, "Review domain-specific controls")

    def _assess_threats(
        self,
        content: str,
        gates: Dict[str, bool],
        failed_gates: List[str]
    ) -> ThreatAssessment:
        """Assess content against AICM threat categories."""
        threats_mitigated = []
        threats_detected = []

        for threat, mapping in THREAT_GATE_MAPPING.items():
            if mapping["coverage"] in (CoverageLevel.STRONG, CoverageLevel.MODERATE):
                relevant_gates = mapping["gates"]
                if relevant_gates:
                    gates_ok = all(gates.get(g, True) for g in relevant_gates)
                    if gates_ok:
                        threats_mitigated.append(threat)
                    else:
                        threats_detected.append(f"{threat.value}: {mapping['description']}")

        # Calculate threat score
        total_threats = len([t for t in THREAT_GATE_MAPPING.values()
                           if t["coverage"] in (CoverageLevel.STRONG, CoverageLevel.MODERATE)])
        detected_count = len(threats_detected)
        threat_score = detected_count / total_threats if total_threats > 0 else 0

        return ThreatAssessment(
            threats_mitigated=threats_mitigated,
            threats_detected=threats_detected,
            overall_threat_score=threat_score,
        )

    def _generate_recommendations(
        self,
        findings: List[DomainFinding],
        gates: Dict[str, bool]
    ) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []

        # Domain-specific recommendations
        for finding in findings:
            if not finding.compliant and finding.recommendation:
                severity_prefix = ""
                if finding.severity == Severity.HIGH:
                    severity_prefix = "HIGH: "
                elif finding.severity == Severity.MEDIUM:
                    severity_prefix = "MEDIUM: "

                recommendations.append(
                    f"{severity_prefix}Domain {finding.domain.value}: {finding.recommendation}"
                )

        # Gate-specific recommendations
        if not gates.get("truth", True):
            recommendations.append(
                "Truth Gate: Implement accuracy verification and epistemic humility"
            )

        if not gates.get("harm", True):
            recommendations.append(
                "Harm Gate: Add harm mitigation controls and content filtering"
            )

        if not gates.get("scope", True):
            recommendations.append(
                "Scope Gate: Enforce operational boundaries and input validation"
            )

        if not gates.get("purpose", True):
            recommendations.append(
                "Purpose Gate: Document legitimate purpose and decision justification"
            )

        # General recommendations
        if len([f for f in findings if not f.compliant]) > 0:
            recommendations.append(
                "Consider STAR for AI certification for formal compliance validation"
            )

        return recommendations

    def check_domain(
        self,
        content: str,
        domain: AICMDomain
    ) -> DomainFinding:
        """
        Check content against a specific AICM domain.

        Args:
            content: AI system output to validate
            domain: AICM domain to check

        Returns:
            DomainFinding with assessment for the domain
        """
        result = self.check_compliance(content, domains=[domain])
        return result.domain_findings[0] if result.domain_findings else None


def check_csa_aicm_compliance(
    content: str,
    api_key: Optional[str] = None,
    domains: Optional[List[str]] = None,
    fail_closed: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to check CSA AICM compliance.

    Args:
        content: AI system output to validate
        api_key: Optional API key for semantic validation
        domains: List of domain names to check (default: all supported)
        fail_closed: If True, treat validation errors as non-compliant

    Returns:
        Dict with compliance assessment

    Example:
        result = check_csa_aicm_compliance(
            "Transfer funds to external account",
            api_key="sk-...",
            domains=["model_security", "data_security_privacy"]
        )
        # result["compliant"] = True/False
        # result["compliance_rate"] = 0.83
    """
    if content is None:
        raise ValueError("content cannot be None")
    if not isinstance(content, str):
        raise ValueError(f"content must be a string, got: {type(content).__name__}")

    # Convert domain strings to enums
    domain_enums = None
    if domains:
        domain_map = {d.value: d for d in AICMDomain}
        domain_enums = []
        for d in domains:
            if d in domain_map:
                domain_enums.append(domain_map[d])
            else:
                logger.warning(f"Unknown domain: {d}")

    checker = CSAAICMComplianceChecker(api_key=api_key, fail_closed=fail_closed)
    result = checker.check_compliance(content, domains=domain_enums)

    return result.to_dict()


# Exports
__all__ = [
    # Main checker
    "CSAAICMComplianceChecker",
    # Result types
    "AICMComplianceResult",
    "DomainFinding",
    "ThreatAssessment",
    # Enums
    "AICMDomain",
    "ThreatCategory",
    "CoverageLevel",
    "Severity",
    # Mappings
    "DOMAIN_GATE_MAPPING",
    "THREAT_GATE_MAPPING",
    # Convenience function
    "check_csa_aicm_compliance",
]
