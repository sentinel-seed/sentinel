"""
Sentinel Compliance Module.

Provides compliance checking tools for AI regulations and standards.

Currently supported:
- EU AI Act (Regulation 2024/1689)
- CSA AI Controls Matrix (AICM v1.0)
- OWASP LLM Top 10 (2025)

Usage:
    # EU AI Act
    from sentinelseed.compliance import EUAIActComplianceChecker

    checker = EUAIActComplianceChecker(api_key="...")
    result = checker.check_compliance(content, context="healthcare")

    # Or use convenience function:
    from sentinelseed.compliance import check_eu_ai_act_compliance
    result = check_eu_ai_act_compliance(content, api_key="...")

    # CSA AI Controls Matrix
    from sentinelseed.compliance import CSAAICMComplianceChecker, AICMDomain

    checker = CSAAICMComplianceChecker(api_key="...")
    result = checker.check_compliance(content, domains=[AICMDomain.MODEL_SECURITY])

    # Or use convenience function:
    from sentinelseed.compliance import check_csa_aicm_compliance
    result = check_csa_aicm_compliance(content, api_key="...")

    # OWASP LLM Top 10
    from sentinelseed.compliance import OWASPLLMChecker

    checker = OWASPLLMChecker(api_key="...")

    # Check user input (pre-inference)
    input_result = checker.check_input(user_input)

    # Check LLM output (post-inference)
    output_result = checker.check_output(llm_response)

    # Check full pipeline
    pipeline_result = checker.check_pipeline(user_input, llm_response)

    # Or use convenience function:
    from sentinelseed.compliance import check_owasp_llm_compliance
    result = check_owasp_llm_compliance(content, validation_type="output")

    # With fail_closed mode (strict):
    checker = EUAIActComplianceChecker(api_key="...", fail_closed=True)
"""

from sentinelseed.compliance.eu_ai_act import (
    EUAIActComplianceChecker,
    ComplianceResult,
    RiskAssessment,
    Article5Violation,
    RiskLevel,
    SystemType,
    OversightModel,
    Severity,
    check_eu_ai_act_compliance,
)

from sentinelseed.compliance.csa_aicm import (
    CSAAICMComplianceChecker,
    AICMComplianceResult,
    DomainFinding,
    ThreatAssessment,
    AICMDomain,
    ThreatCategory,
    CoverageLevel,
    DOMAIN_GATE_MAPPING,
    THREAT_GATE_MAPPING,
    check_csa_aicm_compliance,
)

from sentinelseed.compliance.owasp_llm import (
    OWASPLLMChecker,
    OWASPComplianceResult,
    VulnerabilityFinding,
    OWASPVulnerability,
    CoverageLevel as OWASPCoverageLevel,
    VULNERABILITY_GATE_MAPPING,
    check_owasp_llm_compliance,
)

__all__ = [
    # EU AI Act
    "EUAIActComplianceChecker",
    "ComplianceResult",
    "RiskAssessment",
    "Article5Violation",
    "RiskLevel",
    "SystemType",
    "OversightModel",
    "Severity",
    "check_eu_ai_act_compliance",
    # CSA AI Controls Matrix
    "CSAAICMComplianceChecker",
    "AICMComplianceResult",
    "DomainFinding",
    "ThreatAssessment",
    "AICMDomain",
    "ThreatCategory",
    "CoverageLevel",
    "DOMAIN_GATE_MAPPING",
    "THREAT_GATE_MAPPING",
    "check_csa_aicm_compliance",
    # OWASP LLM Top 10
    "OWASPLLMChecker",
    "OWASPComplianceResult",
    "VulnerabilityFinding",
    "OWASPVulnerability",
    "OWASPCoverageLevel",
    "VULNERABILITY_GATE_MAPPING",
    "check_owasp_llm_compliance",
]
