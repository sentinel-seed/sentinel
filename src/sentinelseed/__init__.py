"""
Sentinel AI - Practical AI Alignment for Developers

A comprehensive AI safety toolkit providing:
- Alignment seeds (system prompts that improve AI safety)
- Response validation (THSP gates: Truth, Harm, Scope, Purpose)
- Memory integrity checking (defense against memory injection)
- Fiduciary AI principles (duty of loyalty and care)
- Regulatory compliance (EU AI Act, OWASP LLM Top 10)
- Provider integrations (OpenAI, Anthropic)
- Framework integrations (LangChain, LangGraph, CrewAI, LlamaIndex, Virtuals, AutoGPT, Garak, OpenGuardrails, Letta)

Quick Start:
    from sentinelseed import Sentinel

    # Create a sentinel instance
    sentinel = Sentinel()

    # Get an alignment seed
    seed = sentinel.get_seed("standard")

    # Or use the chat wrapper directly
    response = sentinel.chat("Hello, how can you help me?")

Memory Integrity (for AI agents):
    from sentinelseed.memory import MemoryIntegrityChecker

    checker = MemoryIntegrityChecker(secret_key="your-secret")
    signed = checker.sign_entry(MemoryEntry(content="User data"))
    result = checker.verify_entry(signed)

Fiduciary AI (ensure AI acts in user's best interest):
    from sentinelseed.fiduciary import FiduciaryValidator, UserContext

    validator = FiduciaryValidator()
    result = validator.validate_action(
        action="Recommend high-risk investment",
        user_context=UserContext(risk_tolerance="low")
    )
    if not result.compliant:
        print(f"Fiduciary violation: {result.violations}")

EU AI Act Compliance:
    from sentinelseed.compliance import EUAIActComplianceChecker

    checker = EUAIActComplianceChecker(api_key="...")
    result = checker.check_compliance(
        content="Based on your social behavior...",
        context="financial",
        system_type="high_risk"
    )
    if not result.compliant:
        print(f"Violations: {result.article_5_violations}")

Framework Integrations:
    from sentinelseed.integrations.virtuals import SentinelSafetyWorker
    from sentinelseed.integrations.langchain import SentinelCallback
    from sentinelseed.integrations.langgraph import SentinelSafetyNode
    from sentinelseed.integrations.crewai import safe_agent, SentinelCrew
    from sentinelseed.integrations.openguardrails import OpenGuardrailsValidator
    from sentinelseed.integrations.openai_agents import create_sentinel_agent
    from sentinelseed.integrations.letta import SentinelLettaClient

Documentation: https://sentinelseed.dev/docs
GitHub: https://github.com/sentinel-seed/sentinel
"""

from sentinelseed.core import Sentinel, SeedLevel
from sentinelseed.validators.gates import TruthGate, HarmGate, ScopeGate, THSValidator
from sentinelseed.memory import (
    MemoryIntegrityChecker,
    MemoryEntry,
    SignedMemoryEntry,
    MemoryTamperingDetected,
)
from sentinelseed.fiduciary import (
    FiduciaryValidator,
    FiduciaryGuard,
    FiduciaryResult,
    UserContext,
    validate_fiduciary,
    is_fiduciary_compliant,
)
from sentinelseed.compliance import (
    EUAIActComplianceChecker,
    ComplianceResult,
    RiskLevel,
    SystemType,
    check_eu_ai_act_compliance,
)

__version__ = "2.11.1"


def get_seed(level: str = "standard") -> str:
    """Convenience function to get an alignment seed.

    Args:
        level: Seed level - 'minimal', 'standard', or 'full'

    Returns:
        The seed content as a string.

    Example:
        >>> from sentinelseed import get_seed
        >>> seed = get_seed("standard")
        >>> print(len(seed))
        4521
    """
    sentinel = Sentinel()
    return sentinel.get_seed(level)


__all__ = [
    # Core
    "Sentinel",
    "SeedLevel",
    "get_seed",
    # Validators
    "TruthGate",
    "HarmGate",
    "ScopeGate",
    "THSValidator",
    # Memory Integrity
    "MemoryIntegrityChecker",
    "MemoryEntry",
    "SignedMemoryEntry",
    "MemoryTamperingDetected",
    # Fiduciary AI
    "FiduciaryValidator",
    "FiduciaryGuard",
    "FiduciaryResult",
    "UserContext",
    "validate_fiduciary",
    "is_fiduciary_compliant",
    # Compliance
    "EUAIActComplianceChecker",
    "ComplianceResult",
    "RiskLevel",
    "SystemType",
    "check_eu_ai_act_compliance",
]
