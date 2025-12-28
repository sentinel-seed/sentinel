"""
OWASP Top 10 for Agentic Applications (2026) Compliance Checker using Sentinel THSP.

This module provides tools to assess AI agent systems against
OWASP Top 10 for Agentic Applications vulnerabilities.

The OWASP Agentic Top 10 (released December 2025) identifies critical risks
in autonomous AI agent systems:
- ASI01: Agent Goal Hijack
- ASI02: Tool Misuse and Exploitation
- ASI03: Identity and Privilege Abuse
- ASI04: Agentic Supply Chain Vulnerabilities
- ASI05: Unexpected Code Execution
- ASI06: Memory and Context Poisoning
- ASI07: Insecure Inter Agent Communication
- ASI08: Cascading Failures
- ASI09: Human Agent Trust Exploitation
- ASI10: Rogue Agents

THSP gates provide behavioral-level controls for applicable vulnerabilities:
- Truth Gate: ASI08, ASI09
- Harm Gate: ASI09
- Scope Gate: ASI01, ASI02
- Purpose Gate: ASI01, ASI10

Reference: https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging

logger = logging.getLogger("sentinelseed.compliance.owasp_agentic")


class AgenticVulnerability(str, Enum):
    """OWASP Top 10 for Agentic Applications (2026) vulnerabilities."""
    ASI01_AGENT_GOAL_HIJACK = "ASI01"
    ASI02_TOOL_MISUSE_EXPLOITATION = "ASI02"
    ASI03_IDENTITY_PRIVILEGE_ABUSE = "ASI03"
    ASI04_SUPPLY_CHAIN = "ASI04"
    ASI05_UNEXPECTED_CODE_EXECUTION = "ASI05"
    ASI06_MEMORY_CONTEXT_POISONING = "ASI06"
    ASI07_INSECURE_INTER_AGENT_COMM = "ASI07"
    ASI08_CASCADING_FAILURES = "ASI08"
    ASI09_HUMAN_AGENT_TRUST = "ASI09"
    ASI10_ROGUE_AGENTS = "ASI10"


# Official vulnerability names per OWASP documentation
VULNERABILITY_NAMES: Dict[AgenticVulnerability, str] = {
    AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK: "Agent Goal Hijack",
    AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION: "Tool Misuse and Exploitation",
    AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE: "Identity and Privilege Abuse",
    AgenticVulnerability.ASI04_SUPPLY_CHAIN: "Agentic Supply Chain Vulnerabilities",
    AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION: "Unexpected Code Execution",
    AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING: "Memory and Context Poisoning",
    AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM: "Insecure Inter Agent Communication",
    AgenticVulnerability.ASI08_CASCADING_FAILURES: "Cascading Failures",
    AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST: "Human Agent Trust Exploitation",
    AgenticVulnerability.ASI10_ROGUE_AGENTS: "Rogue Agents",
}


class CoverageLevel(str, Enum):
    """Sentinel coverage level for OWASP Agentic vulnerabilities."""
    FULL = "full"
    PARTIAL = "partial"
    NOT_COVERED = "not_covered"


class Severity(str, Enum):
    """Severity levels for vulnerability findings."""
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


# Vulnerability to THSP Gate and Sentinel component mapping
VULNERABILITY_COVERAGE: Dict[AgenticVulnerability, Dict[str, Any]] = {
    AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK: {
        "gates": ["purpose", "scope"],
        "coverage": CoverageLevel.FULL,
        "component": "THSP Purpose Gate",
        "description": "Validates that actions serve legitimate, authorized purposes",
        "attack_example": "Indirect prompt injection causing data exfiltration (EchoLeak)",
    },
    AgenticVulnerability.ASI02_TOOL_MISUSE_EXPLOITATION: {
        "gates": ["scope"],
        "coverage": CoverageLevel.FULL,
        "component": "THSP Scope Gate",
        "description": "Validates actions are within authorized boundaries",
        "attack_example": "Agents using legitimate tools destructively (Amazon Q exploit)",
    },
    AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE: {
        "gates": ["scope"],
        "coverage": CoverageLevel.PARTIAL,
        "component": "Database Guard",
        "description": "Query validation prevents unauthorized data access",
        "attack_example": "Cached SSH keys in agent memory, token leakage",
    },
    AgenticVulnerability.ASI04_SUPPLY_CHAIN: {
        "gates": [],
        "coverage": CoverageLevel.PARTIAL,
        "component": "Memory Shield (integrity)",
        "description": "HMAC integrity verification for stored data",
        "attack_example": "GitHub MCP exploit, malicious prompt templates",
    },
    AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION: {
        "gates": [],
        "coverage": CoverageLevel.NOT_COVERED,
        "component": None,
        "description": "Requires runtime sandboxing (Docker, gVisor, etc.)",
        "attack_example": "AutoGPT RCE vulnerability",
    },
    AgenticVulnerability.ASI06_MEMORY_CONTEXT_POISONING: {
        "gates": ["truth"],
        "coverage": CoverageLevel.FULL,
        "component": "Memory Shield",
        "description": "HMAC-SHA256 signing and verification for memory entries",
        "attack_example": "Gemini Memory Attack, RAG poisoning",
    },
    AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM: {
        "gates": [],
        "coverage": CoverageLevel.NOT_COVERED,
        "component": None,
        "description": "Requires network-level mTLS, service mesh",
        "attack_example": "Spoofed agent identities, replayed messages",
    },
    AgenticVulnerability.ASI08_CASCADING_FAILURES: {
        "gates": ["truth"],
        "coverage": CoverageLevel.PARTIAL,
        "component": "THSP Truth Gate",
        "description": "Validates factual accuracy before propagation",
        "attack_example": "Hallucinating planners issuing destructive tasks",
    },
    AgenticVulnerability.ASI09_HUMAN_AGENT_TRUST: {
        "gates": ["truth", "harm"],
        "coverage": CoverageLevel.FULL,
        "component": "THSP Truth + Harm Gates, Fiduciary AI Module",
        "description": "Ensures agent acts in user's best interest",
        "attack_example": "Coding assistants introducing subtle backdoors",
    },
    AgenticVulnerability.ASI10_ROGUE_AGENTS: {
        "gates": ["truth", "harm", "scope", "purpose"],
        "coverage": CoverageLevel.FULL,
        "component": "THSP Protocol + Anti-Self-Preservation",
        "description": "Four-gate validation with explicit anti-self-preservation principle",
        "attack_example": "Agents continuing data exfiltration post-compromise",
    },
}


@dataclass
class AgenticFinding:
    """
    Represents a finding for an OWASP Agentic vulnerability.

    Attributes:
        vulnerability: The OWASP Agentic vulnerability assessed
        name: Official vulnerability name
        protected: Whether Sentinel provides protection
        coverage_level: Sentinel coverage level for this vulnerability
        component: Sentinel component providing protection
        gates_relevant: Which THSP gates are relevant
        severity: Severity if vulnerability detected
        recommendation: Suggested action
        attack_example: Real-world attack example from OWASP
    """
    vulnerability: AgenticVulnerability
    name: str
    protected: bool
    coverage_level: CoverageLevel
    component: Optional[str]
    gates_relevant: List[str]
    severity: Optional[Severity] = None
    recommendation: Optional[str] = None
    attack_example: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "vulnerability": self.vulnerability.value,
            "name": self.name,
            "protected": self.protected,
            "coverage_level": self.coverage_level.value,
            "component": self.component,
            "gates_relevant": self.gates_relevant,
            "severity": self.severity.value if self.severity else None,
            "recommendation": self.recommendation,
            "attack_example": self.attack_example,
        }


@dataclass
class AgenticComplianceResult:
    """
    Complete OWASP Agentic Top 10 compliance assessment result.

    Attributes:
        overall_coverage: Percentage of vulnerabilities with protection
        full_coverage_count: Number with full coverage
        partial_coverage_count: Number with partial coverage
        not_covered_count: Number not covered
        findings: Detailed findings per vulnerability
        recommendations: List of security recommendations
        timestamp: When the check was performed
        metadata: Additional context
    """
    overall_coverage: float
    full_coverage_count: int
    partial_coverage_count: int
    not_covered_count: int
    findings: List[AgenticFinding]
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "overall_coverage": self.overall_coverage,
            "full_coverage_count": self.full_coverage_count,
            "partial_coverage_count": self.partial_coverage_count,
            "not_covered_count": self.not_covered_count,
            "findings": [f.to_dict() for f in self.findings],
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class OWASPAgenticChecker:
    """
    Assess Sentinel's coverage of OWASP Top 10 for Agentic Applications.

    This checker evaluates which vulnerabilities Sentinel protects against
    and provides recommendations for additional security measures.

    The OWASP Agentic Top 10 (2026) focuses on autonomous AI agent risks:
    - 5 vulnerabilities with FULL coverage (50%)
    - 3 vulnerabilities with PARTIAL coverage (30%)
    - 2 vulnerabilities NOT covered (20%)

    Example:
        checker = OWASPAgenticChecker()

        # Get complete coverage assessment
        result = checker.get_coverage_assessment()
        print(f"Overall coverage: {result.overall_coverage}%")

        # Check specific vulnerability
        finding = checker.check_vulnerability(
            AgenticVulnerability.ASI01_AGENT_GOAL_HIJACK
        )
        print(f"Protected: {finding.protected}")

        # Get recommendations for gaps
        gaps = checker.get_coverage_gaps()
        for gap in gaps:
            print(f"{gap.name}: {gap.recommendation}")
    """

    # Framework info
    FRAMEWORK_NAME = "OWASP Top 10 for Agentic Applications"
    FRAMEWORK_VERSION = "2026"
    RELEASE_DATE = "December 2025"
    REFERENCE_URL = "https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/"

    def __init__(self):
        """Initialize OWASP Agentic checker."""
        self._coverage_data = VULNERABILITY_COVERAGE

    def get_coverage_assessment(
        self,
        include_metadata: bool = True,
    ) -> AgenticComplianceResult:
        """
        Get complete coverage assessment for all 10 vulnerabilities.

        Args:
            include_metadata: Whether to include detailed metadata

        Returns:
            AgenticComplianceResult with full assessment
        """
        findings = []
        full_count = 0
        partial_count = 0
        not_covered_count = 0

        for vuln in AgenticVulnerability:
            finding = self.check_vulnerability(vuln)
            findings.append(finding)

            if finding.coverage_level == CoverageLevel.FULL:
                full_count += 1
            elif finding.coverage_level == CoverageLevel.PARTIAL:
                partial_count += 1
            else:
                not_covered_count += 1

        # Calculate overall coverage (full = 100%, partial = 50%)
        total = len(AgenticVulnerability)
        coverage_score = (full_count * 100 + partial_count * 50) / total

        recommendations = self._generate_recommendations(findings)

        metadata = {}
        if include_metadata:
            metadata = {
                "framework": self.FRAMEWORK_NAME,
                "version": self.FRAMEWORK_VERSION,
                "release_date": self.RELEASE_DATE,
                "reference_url": self.REFERENCE_URL,
                "total_vulnerabilities": total,
                "sentinel_components_used": self._get_components_used(findings),
            }

        return AgenticComplianceResult(
            overall_coverage=coverage_score,
            full_coverage_count=full_count,
            partial_coverage_count=partial_count,
            not_covered_count=not_covered_count,
            findings=findings,
            recommendations=recommendations,
            metadata=metadata,
        )

    def check_vulnerability(
        self,
        vulnerability: AgenticVulnerability,
    ) -> AgenticFinding:
        """
        Check coverage for a specific vulnerability.

        Args:
            vulnerability: The OWASP Agentic vulnerability to check

        Returns:
            AgenticFinding with assessment details
        """
        data = self._coverage_data.get(vulnerability, {})

        coverage = data.get("coverage", CoverageLevel.NOT_COVERED)
        protected = coverage != CoverageLevel.NOT_COVERED

        severity = None
        recommendation = None

        if not protected:
            severity = Severity.HIGH
            recommendation = self._get_gap_recommendation(vulnerability)
        elif coverage == CoverageLevel.PARTIAL:
            severity = Severity.MEDIUM
            recommendation = self._get_partial_recommendation(vulnerability)

        return AgenticFinding(
            vulnerability=vulnerability,
            name=VULNERABILITY_NAMES.get(vulnerability, vulnerability.value),
            protected=protected,
            coverage_level=coverage,
            component=data.get("component"),
            gates_relevant=data.get("gates", []),
            severity=severity,
            recommendation=recommendation,
            attack_example=data.get("attack_example"),
        )

    def get_coverage_gaps(self) -> List[AgenticFinding]:
        """
        Get list of vulnerabilities not fully covered.

        Returns:
            List of findings for partial or not covered vulnerabilities
        """
        gaps = []
        for vuln in AgenticVulnerability:
            finding = self.check_vulnerability(vuln)
            if finding.coverage_level != CoverageLevel.FULL:
                gaps.append(finding)
        return gaps

    def get_full_coverage_vulnerabilities(self) -> List[AgenticFinding]:
        """
        Get list of vulnerabilities with full coverage.

        Returns:
            List of findings for fully covered vulnerabilities
        """
        covered = []
        for vuln in AgenticVulnerability:
            finding = self.check_vulnerability(vuln)
            if finding.coverage_level == CoverageLevel.FULL:
                covered.append(finding)
        return covered

    def _get_gap_recommendation(self, vuln: AgenticVulnerability) -> str:
        """Get recommendation for uncovered vulnerability."""
        recommendations = {
            AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION:
                "Use container isolation (Docker, gVisor), language sandboxes "
                "(Pyodide, Deno), or OS controls (seccomp, AppArmor) for code execution.",
            AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM:
                "Implement service mesh (Istio, Linkerd) with mTLS, "
                "message signing, and API gateway authentication.",
        }
        return recommendations.get(
            vuln,
            "Implement additional security controls for this vulnerability."
        )

    def _get_partial_recommendation(self, vuln: AgenticVulnerability) -> str:
        """Get recommendation for partially covered vulnerability."""
        recommendations = {
            AgenticVulnerability.ASI03_IDENTITY_PRIVILEGE_ABUSE:
                "Add runtime credential rotation, cross-agent permission isolation, "
                "and token scope enforcement. Database Guard provides query validation.",
            AgenticVulnerability.ASI04_SUPPLY_CHAIN:
                "Add MCP server verification, plugin signature validation, "
                "and dependency scanning. Memory Shield provides integrity checking.",
            AgenticVulnerability.ASI08_CASCADING_FAILURES:
                "Implement circuit breakers (Resilience4j, Polly), rate limiting, "
                "and workflow isolation. Truth Gate validates factual accuracy.",
        }
        return recommendations.get(
            vuln,
            "Review coverage gaps and implement additional controls."
        )

    def _generate_recommendations(
        self,
        findings: List[AgenticFinding],
    ) -> List[str]:
        """Generate overall recommendations based on findings."""
        recommendations = []

        not_covered = [f for f in findings if f.coverage_level == CoverageLevel.NOT_COVERED]
        partial = [f for f in findings if f.coverage_level == CoverageLevel.PARTIAL]

        if not_covered:
            recommendations.append(
                f"NOT COVERED ({len(not_covered)}): "
                f"{', '.join(f.vulnerability.value for f in not_covered)} - "
                "Requires external security controls."
            )

        if partial:
            recommendations.append(
                f"PARTIAL ({len(partial)}): "
                f"{', '.join(f.vulnerability.value for f in partial)} - "
                "Consider enhancing with additional controls."
            )

        # Specific recommendations
        if any(f.vulnerability == AgenticVulnerability.ASI05_UNEXPECTED_CODE_EXECUTION
               for f in not_covered):
            recommendations.append(
                "Code Execution: Use Docker, gVisor, or Pyodide for sandboxing."
            )

        if any(f.vulnerability == AgenticVulnerability.ASI07_INSECURE_INTER_AGENT_COMM
               for f in not_covered):
            recommendations.append(
                "Inter-Agent Security: Implement service mesh with mTLS."
            )

        # Key principle from OWASP
        recommendations.append(
            "Apply OWASP's 'Least Agency' principle: Only grant agents "
            "the minimum autonomy required to perform safe, bounded tasks."
        )

        return recommendations

    def _get_components_used(self, findings: List[AgenticFinding]) -> List[str]:
        """Get list of Sentinel components providing protection."""
        components = set()
        for finding in findings:
            if finding.component:
                components.add(finding.component)
        return sorted(list(components))


def get_owasp_agentic_coverage() -> Dict[str, Any]:
    """
    Convenience function to get OWASP Agentic coverage assessment.

    Returns:
        Dict with coverage assessment

    Example:
        result = get_owasp_agentic_coverage()
        print(f"Coverage: {result['overall_coverage']}%")
        print(f"Full: {result['full_coverage_count']}")
        print(f"Partial: {result['partial_coverage_count']}")
        print(f"Not covered: {result['not_covered_count']}")
    """
    checker = OWASPAgenticChecker()
    result = checker.get_coverage_assessment()
    return result.to_dict()


def check_agentic_vulnerability(
    vulnerability_id: str,
) -> Dict[str, Any]:
    """
    Check coverage for a specific OWASP Agentic vulnerability.

    Args:
        vulnerability_id: Vulnerability ID (e.g., "ASI01", "ASI02")

    Returns:
        Dict with vulnerability assessment

    Raises:
        ValueError: If vulnerability_id is invalid

    Example:
        result = check_agentic_vulnerability("ASI01")
        print(f"Protected: {result['protected']}")
        print(f"Component: {result['component']}")
    """
    # Find the vulnerability by ID
    vuln_id = vulnerability_id.upper().strip()
    vuln = None

    for v in AgenticVulnerability:
        if v.value == vuln_id:
            vuln = v
            break

    if vuln is None:
        valid_ids = [v.value for v in AgenticVulnerability]
        raise ValueError(
            f"Invalid vulnerability_id '{vulnerability_id}'. "
            f"Valid IDs: {valid_ids}"
        )

    checker = OWASPAgenticChecker()
    finding = checker.check_vulnerability(vuln)
    return finding.to_dict()


# Exports
__all__ = [
    # Main checker
    "OWASPAgenticChecker",
    # Result types
    "AgenticComplianceResult",
    "AgenticFinding",
    # Enums
    "AgenticVulnerability",
    "CoverageLevel",
    "Severity",
    # Constants
    "VULNERABILITY_COVERAGE",
    "VULNERABILITY_NAMES",
    # Convenience functions
    "get_owasp_agentic_coverage",
    "check_agentic_vulnerability",
]
