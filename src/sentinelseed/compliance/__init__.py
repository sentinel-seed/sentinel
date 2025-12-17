"""
Sentinel Compliance Module.

Provides compliance checking tools for AI regulations and standards.

Currently supported:
- EU AI Act (Regulation 2024/1689)

Usage:
    from sentinelseed.compliance import EUAIActComplianceChecker

    checker = EUAIActComplianceChecker(api_key="...")
    result = checker.check_compliance(content, context="healthcare")

    # Or use convenience function:
    from sentinelseed.compliance import check_eu_ai_act_compliance
    result = check_eu_ai_act_compliance(content, api_key="...")
"""

from sentinelseed.compliance.eu_ai_act import (
    EUAIActComplianceChecker,
    ComplianceResult,
    RiskAssessment,
    Article5Violation,
    RiskLevel,
    SystemType,
    OversightModel,
    check_eu_ai_act_compliance,
)

__all__ = [
    # Main checker
    "EUAIActComplianceChecker",
    # Result types
    "ComplianceResult",
    "RiskAssessment",
    "Article5Violation",
    # Enums
    "RiskLevel",
    "SystemType",
    "OversightModel",
    # Convenience function
    "check_eu_ai_act_compliance",
]
