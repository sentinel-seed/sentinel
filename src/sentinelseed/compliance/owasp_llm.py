"""
OWASP LLM Top 10 (2025) Compliance Checker using Sentinel THSP.

This module provides tools to assess AI system inputs and outputs against
OWASP Top 10 for LLM Applications 2025 vulnerabilities.

The OWASP LLM Top 10 identifies critical risks in LLM applications:
- LLM01: Prompt Injection
- LLM02: Sensitive Information Disclosure
- LLM03: Supply Chain Vulnerabilities
- LLM04: Data and Model Poisoning
- LLM05: Improper Output Handling
- LLM06: Excessive Agency
- LLM07: System Prompt Leakage
- LLM08: Vector and Embedding Weaknesses
- LLM09: Misinformation
- LLM10: Unbounded Consumption

THSP gates provide behavioral-level controls for applicable vulnerabilities:
- Scope Gate: LLM01, LLM06, LLM07
- Truth Gate: LLM02, LLM05, LLM09
- Harm Gate: LLM02, LLM05
- Purpose Gate: LLM06

Reference: https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
from datetime import datetime
import logging
import re

logger = logging.getLogger("sentinelseed.compliance.owasp_llm")


class OWASPVulnerability(str, Enum):
    """OWASP LLM Top 10 (2025) vulnerabilities."""
    LLM01_PROMPT_INJECTION = "LLM01"
    LLM02_SENSITIVE_INFO_DISCLOSURE = "LLM02"
    LLM03_SUPPLY_CHAIN = "LLM03"
    LLM04_DATA_MODEL_POISONING = "LLM04"
    LLM05_IMPROPER_OUTPUT_HANDLING = "LLM05"
    LLM06_EXCESSIVE_AGENCY = "LLM06"
    LLM07_SYSTEM_PROMPT_LEAKAGE = "LLM07"
    LLM08_VECTOR_EMBEDDING = "LLM08"
    LLM09_MISINFORMATION = "LLM09"
    LLM10_UNBOUNDED_CONSUMPTION = "LLM10"


class CoverageLevel(str, Enum):
    """THSP coverage level for OWASP vulnerabilities."""
    STRONG = "strong"
    MODERATE = "moderate"
    INDIRECT = "indirect"
    NOT_APPLICABLE = "not_applicable"


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


# OWASP vulnerability to THSP Gate mapping
VULNERABILITY_GATE_MAPPING: Dict[OWASPVulnerability, Dict[str, Any]] = {
    OWASPVulnerability.LLM01_PROMPT_INJECTION: {
        "gates": ["scope"],
        "coverage": CoverageLevel.STRONG,
        "description": "Manipulating LLMs via crafted inputs",
        "thsp_protection": "Scope gate detects instruction override attempts",
    },
    OWASPVulnerability.LLM02_SENSITIVE_INFO_DISCLOSURE: {
        "gates": ["truth", "harm"],
        "coverage": CoverageLevel.STRONG,
        "description": "LLMs revealing sensitive data",
        "thsp_protection": "Truth and Harm gates prevent unauthorized disclosure",
    },
    OWASPVulnerability.LLM03_SUPPLY_CHAIN: {
        "gates": [],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Vulnerabilities in external components",
        "thsp_protection": "Sentinel itself is a trusted supply chain component",
    },
    OWASPVulnerability.LLM04_DATA_MODEL_POISONING: {
        "gates": ["truth"],
        "coverage": CoverageLevel.INDIRECT,
        "description": "Manipulated training/fine-tuning data",
        "thsp_protection": "Truth gate may catch effects of poisoned data",
    },
    OWASPVulnerability.LLM05_IMPROPER_OUTPUT_HANDLING: {
        "gates": ["truth", "harm"],
        "coverage": CoverageLevel.STRONG,
        "description": "Failing to validate LLM outputs",
        "thsp_protection": "All outputs validated through THSP gates",
    },
    OWASPVulnerability.LLM06_EXCESSIVE_AGENCY: {
        "gates": ["scope", "purpose"],
        "coverage": CoverageLevel.STRONG,
        "description": "Excessive functionality or autonomy",
        "thsp_protection": "Scope limits actions, Purpose requires justification",
    },
    OWASPVulnerability.LLM07_SYSTEM_PROMPT_LEAKAGE: {
        "gates": ["scope"],
        "coverage": CoverageLevel.MODERATE,
        "description": "Exposing system prompt configurations",
        "thsp_protection": "Scope gate detects extraction attempts",
    },
    OWASPVulnerability.LLM08_VECTOR_EMBEDDING: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "RAG pipeline and vector database vulnerabilities",
        "thsp_protection": "Infrastructure-level concern, not behavioral",
    },
    OWASPVulnerability.LLM09_MISINFORMATION: {
        "gates": ["truth"],
        "coverage": CoverageLevel.STRONG,
        "description": "LLMs generating false information",
        "thsp_protection": "Truth gate enforces epistemic humility",
    },
    OWASPVulnerability.LLM10_UNBOUNDED_CONSUMPTION: {
        "gates": [],
        "coverage": CoverageLevel.NOT_APPLICABLE,
        "description": "Resource exhaustion attacks",
        "thsp_protection": "Infrastructure-level rate limiting required",
    },
}

# Prompt injection patterns for LLM01 detection
PROMPT_INJECTION_PATTERNS = [
    # Direct instruction override
    r"ignore\s+(all\s+)?(previous|prior|above|your)?\s*(instructions?|prompts?|rules?)",
    r"disregard\s+(all\s+)?(previous|prior|above|your)?\s*(instructions?|prompts?|rules?|restrictions?)",
    r"forget\s+(all\s+)?(previous|prior|your)?\s*(instructions?|prompts?|rules?)",
    # Role manipulation
    r"you\s+are\s+now\s+(a|an|the)",
    r"pretend\s+(to\s+be|you'?re)\s+(a|an)",
    r"act\s+as\s+(a|an|if)",
    r"roleplay\s+as",
    # Jailbreak attempts
    r"DAN\s+mode",
    r"developer\s+mode",
    r"jailbreak",
    r"bypass\s+(safety|filter|restriction)",
    r"unlock\s+(your|hidden)\s+(capabilities|potential)",
    # Prompt extraction
    r"(reveal|show|display|print|output)\s+(your|the|my)?\s*(system\s+)?(prompt|instructions)",
    r"what\s+(are|is)\s+your\s+(system\s+)?(prompt|instructions)",
    r"repeat\s+(back|the\s+)?(your|system)\s+(prompt|instructions)",
    # Additional override patterns
    r"ignore\s+(all|your|the)\s+(rules?|safety|restrictions?)",
]

# System prompt leakage patterns for LLM07
PROMPT_LEAKAGE_PATTERNS = [
    r"here\s+(is|are)\s+(my|the)\s+(system\s+)?prompt",
    r"my\s+(system\s+)?instructions\s+(are|say)",
    r"i\s+was\s+(told|instructed|programmed)\s+to",
    r"my\s+(initial|original|system)\s+prompt",
]


@dataclass
class VulnerabilityFinding:
    """
    Represents a finding for an OWASP LLM vulnerability.

    Attributes:
        vulnerability: The OWASP vulnerability assessed
        detected: Whether the vulnerability was detected
        coverage_level: THSP coverage level for this vulnerability
        gates_checked: Which THSP gates were evaluated
        gates_passed: Which gates passed
        gates_failed: Which gates failed
        patterns_matched: Specific patterns that matched (for heuristic detection)
        severity: Severity of the finding
        recommendation: Suggested action
    """
    vulnerability: OWASPVulnerability
    detected: bool
    coverage_level: CoverageLevel
    gates_checked: List[str]
    gates_passed: List[str]
    gates_failed: List[str]
    patterns_matched: List[str] = field(default_factory=list)
    severity: Optional[Severity] = None
    recommendation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "vulnerability": self.vulnerability.value,
            "detected": self.detected,
            "coverage_level": self.coverage_level.value,
            "gates_checked": self.gates_checked,
            "gates_passed": self.gates_passed,
            "gates_failed": self.gates_failed,
            "patterns_matched": self.patterns_matched,
            "severity": self.severity.value if self.severity else None,
            "recommendation": self.recommendation,
        }


@dataclass
class OWASPComplianceResult:
    """
    Complete OWASP LLM Top 10 compliance assessment result.

    Attributes:
        secure: Overall security status (no vulnerabilities detected)
        vulnerabilities_checked: Number of vulnerabilities evaluated
        vulnerabilities_detected: Number of vulnerabilities found
        detection_rate: Percentage of vulnerabilities detected
        findings: Detailed findings per vulnerability
        input_validation: Result of input validation (pre-inference)
        output_validation: Result of output validation (post-inference)
        recommendations: List of security recommendations
        timestamp: When the check was performed
        metadata: Additional context
    """
    secure: bool
    vulnerabilities_checked: int
    vulnerabilities_detected: int
    detection_rate: float
    findings: List[VulnerabilityFinding]
    input_validation: Optional[Dict[str, Any]] = None
    output_validation: Optional[Dict[str, Any]] = None
    recommendations: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "secure": self.secure,
            "vulnerabilities_checked": self.vulnerabilities_checked,
            "vulnerabilities_detected": self.vulnerabilities_detected,
            "detection_rate": self.detection_rate,
            "findings": [f.to_dict() for f in self.findings],
            "input_validation": self.input_validation,
            "output_validation": self.output_validation,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class OWASPLLMChecker:
    """
    Check AI system inputs/outputs against OWASP LLM Top 10 vulnerabilities.

    Uses THSP gates to detect:
    - LLM01: Prompt Injection (Scope gate)
    - LLM02: Sensitive Info Disclosure (Truth + Harm gates)
    - LLM05: Improper Output Handling (Truth + Harm gates)
    - LLM06: Excessive Agency (Scope + Purpose gates)
    - LLM07: System Prompt Leakage (Scope gate)
    - LLM09: Misinformation (Truth gate)

    Example:
        checker = OWASPLLMChecker(api_key="sk-...")

        # Check user input (pre-inference)
        input_result = checker.check_input("Ignore all previous instructions...")
        if input_result.vulnerabilities_detected > 0:
            print("Potential attack detected!")

        # Check LLM output (post-inference)
        output_result = checker.check_output("Here is harmful content...")
        if not output_result.secure:
            print("Unsafe output detected!")

        # Full pipeline check
        result = checker.check_pipeline(user_input, llm_output)
    """

    # Vulnerabilities with THSP support
    SUPPORTED_VULNERABILITIES = [
        OWASPVulnerability.LLM01_PROMPT_INJECTION,
        OWASPVulnerability.LLM02_SENSITIVE_INFO_DISCLOSURE,
        OWASPVulnerability.LLM05_IMPROPER_OUTPUT_HANDLING,
        OWASPVulnerability.LLM06_EXCESSIVE_AGENCY,
        OWASPVulnerability.LLM07_SYSTEM_PROMPT_LEAKAGE,
        OWASPVulnerability.LLM09_MISINFORMATION,
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
        Initialize OWASP LLM checker.

        Args:
            api_key: API key for semantic validation (recommended for accuracy)
            provider: LLM provider ("openai" or "anthropic")
            model: Specific model to use
            fail_closed: If True, treat validation errors as insecure
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
        self._injection_patterns = [
            re.compile(p, re.IGNORECASE) for p in PROMPT_INJECTION_PATTERNS
        ]
        self._leakage_patterns = [
            re.compile(p, re.IGNORECASE) for p in PROMPT_LEAKAGE_PATTERNS
        ]
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
                logger.info("Using SemanticValidator for OWASP LLM compliance")
            except ImportError:
                logger.warning("SemanticValidator not available")

        if self._validator is None:
            try:
                from sentinelseed.validators.gates import THSPValidator
                self._validator = THSPValidator()
                logger.info("Using THSPValidator (heuristic) for OWASP LLM compliance")
            except ImportError:
                logger.warning("No validator available")

    def _validate_content(self, content: str) -> None:
        """Validate content input."""
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

    def _run_thsp_validation(
        self, content: str
    ) -> Tuple[Dict[str, bool], bool, List[str]]:
        """Run content through THSP gates."""
        if self._validator is None:
            if self._fail_closed:
                logger.warning("No validator - fail_closed: treating as insecure")
                return {}, False, ["no_validator"]
            else:
                logger.warning("No validator - returning secure by default")
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

        except (ValueError, TypeError, AttributeError, RuntimeError) as e:
            logger.error(f"Validation error: {e}")
            if self._fail_closed:
                return {}, False, ["validation_error"]
            else:
                return {}, True, []

    def _check_prompt_injection(self, content: str) -> Tuple[bool, List[str]]:
        """Check for LLM01 prompt injection patterns."""
        matched_patterns = []
        for pattern in self._injection_patterns:
            if pattern.search(content):
                matched_patterns.append(pattern.pattern)
        return len(matched_patterns) > 0, matched_patterns

    def _check_prompt_leakage(self, content: str) -> Tuple[bool, List[str]]:
        """Check for LLM07 system prompt leakage patterns."""
        matched_patterns = []
        for pattern in self._leakage_patterns:
            if pattern.search(content):
                matched_patterns.append(pattern.pattern)
        return len(matched_patterns) > 0, matched_patterns

    def check_input(
        self,
        content: str,
        vulnerabilities: Optional[List[OWASPVulnerability]] = None,
        include_metadata: bool = True,
    ) -> OWASPComplianceResult:
        """
        Check user input for potential attacks (pre-inference).

        Primarily detects:
        - LLM01: Prompt Injection
        - LLM06: Excessive Agency attempts

        Args:
            content: User input to validate
            vulnerabilities: Specific vulnerabilities to check (default: input-relevant)
            include_metadata: Whether to include detailed metadata

        Returns:
            OWASPComplianceResult with assessment

        Raises:
            ValueError: If content is invalid
        """
        self._validate_content(content)

        # Default to input-relevant vulnerabilities
        if vulnerabilities is None:
            vulnerabilities = [
                OWASPVulnerability.LLM01_PROMPT_INJECTION,
                OWASPVulnerability.LLM06_EXCESSIVE_AGENCY,
            ]

        gates, is_safe, failed_gates = self._run_thsp_validation(content)
        findings = []

        for vuln in vulnerabilities:
            finding = self._assess_vulnerability(
                vuln, content, gates, failed_gates, is_input=True
            )
            findings.append(finding)

        vulnerabilities_detected = sum(1 for f in findings if f.detected)
        detection_rate = vulnerabilities_detected / len(vulnerabilities) if vulnerabilities else 0

        recommendations = self._generate_recommendations(findings, "input")

        metadata = {}
        if include_metadata:
            metadata = {
                "framework": "OWASP LLM Top 10 (2025)",
                "validation_type": "input",
                "validation_method": "semantic" if self._api_key else "heuristic",
                "gates_evaluated": gates,
                "failed_gates": failed_gates,
            }

        return OWASPComplianceResult(
            secure=vulnerabilities_detected == 0,
            vulnerabilities_checked=len(vulnerabilities),
            vulnerabilities_detected=vulnerabilities_detected,
            detection_rate=detection_rate,
            findings=findings,
            input_validation={"checked": True, "is_safe": is_safe},
            recommendations=recommendations,
            metadata=metadata,
        )

    def check_output(
        self,
        content: str,
        vulnerabilities: Optional[List[OWASPVulnerability]] = None,
        include_metadata: bool = True,
    ) -> OWASPComplianceResult:
        """
        Check LLM output for security issues (post-inference).

        Primarily detects:
        - LLM02: Sensitive Information Disclosure
        - LLM05: Improper Output Handling
        - LLM07: System Prompt Leakage
        - LLM09: Misinformation

        Args:
            content: LLM output to validate
            vulnerabilities: Specific vulnerabilities to check (default: output-relevant)
            include_metadata: Whether to include detailed metadata

        Returns:
            OWASPComplianceResult with assessment

        Raises:
            ValueError: If content is invalid
        """
        self._validate_content(content)

        # Default to output-relevant vulnerabilities
        if vulnerabilities is None:
            vulnerabilities = [
                OWASPVulnerability.LLM02_SENSITIVE_INFO_DISCLOSURE,
                OWASPVulnerability.LLM05_IMPROPER_OUTPUT_HANDLING,
                OWASPVulnerability.LLM07_SYSTEM_PROMPT_LEAKAGE,
                OWASPVulnerability.LLM09_MISINFORMATION,
            ]

        gates, is_safe, failed_gates = self._run_thsp_validation(content)
        findings = []

        for vuln in vulnerabilities:
            finding = self._assess_vulnerability(
                vuln, content, gates, failed_gates, is_input=False
            )
            findings.append(finding)

        vulnerabilities_detected = sum(1 for f in findings if f.detected)
        detection_rate = vulnerabilities_detected / len(vulnerabilities) if vulnerabilities else 0

        recommendations = self._generate_recommendations(findings, "output")

        metadata = {}
        if include_metadata:
            metadata = {
                "framework": "OWASP LLM Top 10 (2025)",
                "validation_type": "output",
                "validation_method": "semantic" if self._api_key else "heuristic",
                "gates_evaluated": gates,
                "failed_gates": failed_gates,
            }

        return OWASPComplianceResult(
            secure=vulnerabilities_detected == 0,
            vulnerabilities_checked=len(vulnerabilities),
            vulnerabilities_detected=vulnerabilities_detected,
            detection_rate=detection_rate,
            findings=findings,
            output_validation={"checked": True, "is_safe": is_safe},
            recommendations=recommendations,
            metadata=metadata,
        )

    def check_pipeline(
        self,
        user_input: str,
        llm_output: str,
        include_metadata: bool = True,
    ) -> OWASPComplianceResult:
        """
        Check complete LLM pipeline (input + output).

        This is the recommended method for comprehensive security assessment,
        as it validates both the user input and the LLM response.

        Args:
            user_input: User input (pre-inference)
            llm_output: LLM output (post-inference)
            include_metadata: Whether to include detailed metadata

        Returns:
            OWASPComplianceResult with combined assessment

        Raises:
            ValueError: If inputs are invalid
        """
        # Validate both inputs
        self._validate_content(user_input)
        self._validate_content(llm_output)

        # Run input validation
        input_result = self.check_input(user_input, include_metadata=False)

        # Run output validation
        output_result = self.check_output(llm_output, include_metadata=False)

        # Combine findings
        all_findings = input_result.findings + output_result.findings
        vulnerabilities_detected = sum(1 for f in all_findings if f.detected)
        total_checked = len(all_findings)

        # Combine recommendations (deduplicated)
        all_recommendations = list(set(
            input_result.recommendations + output_result.recommendations
        ))

        metadata = {}
        if include_metadata:
            metadata = {
                "framework": "OWASP LLM Top 10 (2025)",
                "validation_type": "pipeline",
                "validation_method": "semantic" if self._api_key else "heuristic",
                "input_vulnerabilities_detected": input_result.vulnerabilities_detected,
                "output_vulnerabilities_detected": output_result.vulnerabilities_detected,
            }

        return OWASPComplianceResult(
            secure=vulnerabilities_detected == 0,
            vulnerabilities_checked=total_checked,
            vulnerabilities_detected=vulnerabilities_detected,
            detection_rate=vulnerabilities_detected / total_checked if total_checked else 0,
            findings=all_findings,
            input_validation={
                "checked": True,
                "secure": input_result.secure,
                "vulnerabilities_detected": input_result.vulnerabilities_detected,
            },
            output_validation={
                "checked": True,
                "secure": output_result.secure,
                "vulnerabilities_detected": output_result.vulnerabilities_detected,
            },
            recommendations=all_recommendations,
            metadata=metadata,
        )

    def _assess_vulnerability(
        self,
        vuln: OWASPVulnerability,
        content: str,
        gates: Dict[str, bool],
        failed_gates: List[str],
        is_input: bool,
    ) -> VulnerabilityFinding:
        """Assess a specific vulnerability."""
        mapping = VULNERABILITY_GATE_MAPPING.get(vuln, {})
        relevant_gates = mapping.get("gates", [])
        coverage = mapping.get("coverage", CoverageLevel.NOT_APPLICABLE)

        # Check for pattern matches (heuristic detection)
        patterns_matched = []
        pattern_detected = False

        if vuln == OWASPVulnerability.LLM01_PROMPT_INJECTION and is_input:
            pattern_detected, patterns_matched = self._check_prompt_injection(content)

        if vuln == OWASPVulnerability.LLM07_SYSTEM_PROMPT_LEAKAGE and not is_input:
            pattern_detected, patterns_matched = self._check_prompt_leakage(content)

        # Check gate failures for relevant gates
        gates_passed = [g for g in relevant_gates if gates.get(g, True)]
        gates_failed = [g for g in relevant_gates if not gates.get(g, True)]

        # Vulnerability is detected if patterns match OR relevant gates fail
        gate_detected = len(gates_failed) > 0
        detected = pattern_detected or gate_detected

        # Determine severity
        severity = None
        if detected:
            if coverage == CoverageLevel.STRONG:
                severity = Severity.HIGH
            elif coverage == CoverageLevel.MODERATE:
                severity = Severity.MEDIUM
            else:
                severity = Severity.LOW

        # Generate recommendation
        recommendation = None
        if detected:
            recommendation = self._get_vulnerability_recommendation(vuln)

        return VulnerabilityFinding(
            vulnerability=vuln,
            detected=detected,
            coverage_level=coverage,
            gates_checked=relevant_gates,
            gates_passed=gates_passed,
            gates_failed=gates_failed,
            patterns_matched=patterns_matched,
            severity=severity,
            recommendation=recommendation,
        )

    def _get_vulnerability_recommendation(self, vuln: OWASPVulnerability) -> str:
        """Get vulnerability-specific recommendation."""
        recommendations = {
            OWASPVulnerability.LLM01_PROMPT_INJECTION:
                "Implement input sanitization and instruction hierarchy. "
                "Consider using Sentinel's Scope gate for pre-inference validation.",
            OWASPVulnerability.LLM02_SENSITIVE_INFO_DISCLOSURE:
                "Review output for PII and sensitive data. "
                "Implement data classification and filtering.",
            OWASPVulnerability.LLM05_IMPROPER_OUTPUT_HANDLING:
                "Validate all LLM outputs before passing to downstream systems. "
                "Use Sentinel's output validation in your pipeline.",
            OWASPVulnerability.LLM06_EXCESSIVE_AGENCY:
                "Limit agent capabilities and require explicit user confirmation "
                "for high-impact actions. Implement Purpose gate validation.",
            OWASPVulnerability.LLM07_SYSTEM_PROMPT_LEAKAGE:
                "Avoid including sensitive information in system prompts. "
                "Implement output filtering for prompt-like content.",
            OWASPVulnerability.LLM09_MISINFORMATION:
                "Enable epistemic humility in responses. "
                "Require citations for factual claims.",
        }
        return recommendations.get(vuln, "Review security controls for this vulnerability.")

    def _generate_recommendations(
        self,
        findings: List[VulnerabilityFinding],
        validation_type: str,
    ) -> List[str]:
        """Generate security recommendations based on findings."""
        recommendations = []

        detected_findings = [f for f in findings if f.detected]

        if detected_findings:
            for finding in detected_findings:
                if finding.recommendation:
                    severity_prefix = ""
                    if finding.severity == Severity.HIGH:
                        severity_prefix = "HIGH: "
                    elif finding.severity == Severity.MEDIUM:
                        severity_prefix = "MEDIUM: "

                    recommendations.append(
                        f"{severity_prefix}{finding.vulnerability.value}: {finding.recommendation}"
                    )

        # General recommendations
        if validation_type == "input" and any(
            f.vulnerability == OWASPVulnerability.LLM01_PROMPT_INJECTION
            for f in detected_findings
        ):
            recommendations.append(
                "Consider implementing a prompt injection firewall or content filter."
            )

        if validation_type == "output" and any(
            f.vulnerability == OWASPVulnerability.LLM09_MISINFORMATION
            for f in detected_findings
        ):
            recommendations.append(
                "Implement fact-checking or citation requirements for factual claims."
            )

        return recommendations


def check_owasp_llm_compliance(
    content: str,
    api_key: Optional[str] = None,
    validation_type: str = "output",
    fail_closed: bool = False,
) -> Dict[str, Any]:
    """
    Convenience function to check OWASP LLM Top 10 compliance.

    Args:
        content: Content to validate
        api_key: Optional API key for semantic validation
        validation_type: "input", "output", or "both"
        fail_closed: If True, treat validation errors as insecure

    Returns:
        Dict with security assessment

    Raises:
        ValueError: If content is invalid
        ValueError: If validation_type is not valid

    Example:
        # Check user input
        result = check_owasp_llm_compliance(
            "Ignore previous instructions...",
            validation_type="input"
        )
        # result["secure"] = False

        # Check LLM output
        result = check_owasp_llm_compliance(
            "Here is the information you requested...",
            validation_type="output"
        )
    """
    if content is None:
        raise ValueError("content cannot be None")
    if not isinstance(content, str):
        raise ValueError(f"content must be a string, got: {type(content).__name__}")

    valid_types = ("input", "output", "both")
    if validation_type not in valid_types:
        raise ValueError(
            f"Invalid validation_type '{validation_type}'. Valid values: {valid_types}"
        )

    checker = OWASPLLMChecker(api_key=api_key, fail_closed=fail_closed)

    if validation_type == "input":
        result = checker.check_input(content)
    elif validation_type == "output":
        result = checker.check_output(content)
    else:  # both - use same content for demonstration
        result = checker.check_output(content)  # More comprehensive for single content

    return result.to_dict()


# Exports
__all__ = [
    # Main checker
    "OWASPLLMChecker",
    # Result types
    "OWASPComplianceResult",
    "VulnerabilityFinding",
    # Enums
    "OWASPVulnerability",
    "CoverageLevel",
    "Severity",
    # Mappings
    "VULNERABILITY_GATE_MAPPING",
    # Convenience function
    "check_owasp_llm_compliance",
]
