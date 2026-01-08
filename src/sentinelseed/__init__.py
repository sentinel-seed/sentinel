"""
Sentinel AI - Practical AI Alignment for Developers

A comprehensive AI safety toolkit providing:
- Alignment seeds (system prompts that improve AI safety)
- Response validation (THSP gates: Truth, Harm, Scope, Purpose)
- Memory integrity checking (defense against memory injection)
- Fiduciary AI principles (duty of loyalty and care)
- Database query validation (defense against data exfiltration)
- Regulatory compliance (EU AI Act, OWASP LLM Top 10)
- Provider integrations (OpenAI, Anthropic)
- Framework integrations (LangChain, LangGraph, CrewAI, LlamaIndex, Virtuals, AutoGPT, Garak, OpenGuardrails, Letta)

Quick Start:
    from sentinelseed import Sentinel

    # Create a sentinel instance
    sentinel = Sentinel()

    # Get an alignment seed
    seed = sentinel.get_seed("standard")

    # Validate content
    is_safe, violations = sentinel.validate("Some content to check")

    # Or use the chat wrapper directly
    response = sentinel.chat("Hello, how can you help me?")

Layered Validation (advanced):
    from sentinelseed.validation import LayeredValidator

    # Heuristic only (no API required)
    validator = LayeredValidator()
    result = validator.validate("content to check")

    # With semantic validation
    validator = LayeredValidator(
        semantic_api_key="sk-...",
        use_semantic=True,
    )
    result = validator.validate("content")
    if not result.is_safe:
        print(f"Blocked: {result.violations}")

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

Database Guard (protect against data exfiltration):
    from sentinelseed.database import DatabaseGuard

    guard = DatabaseGuard(
        max_rows_per_query=1000,
        require_where_clause=True,
    )
    result = guard.validate("SELECT name FROM users WHERE id = 1")
    if result.blocked:
        print(f"Query blocked: {result.reason}")

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

import warnings

# Core - always available
from sentinelseed.core import Sentinel, SeedLevel
from sentinelseed.core.interfaces import Validator, AsyncValidator
from sentinelseed.core.exceptions import (
    SentinelError,
    ValidationError,
    ConfigurationError,
    IntegrationError,
)

# v3.0 architecture - unified 3-gate validation
from sentinelseed.core import (
    SentinelValidator,
    SentinelConfig,
    SentinelObserver,
    SentinelResult,
    ObservationResult,
)

# Validation - recommended API for advanced usage
from sentinelseed.validation import (
    LayeredValidator,
    AsyncLayeredValidator,
    ValidationResult,
    ValidationConfig,
    ValidationLayer,
)
from sentinelseed.validation.types import RiskLevel as ValidationRiskLevel

# Memory Integrity
from sentinelseed.memory import (
    MemoryIntegrityChecker,
    MemoryEntry,
    SignedMemoryEntry,
    MemoryTamperingDetected,
)

# Fiduciary AI
from sentinelseed.fiduciary import (
    FiduciaryValidator,
    FiduciaryGuard,
    FiduciaryResult,
    UserContext,
    validate_fiduciary,
    is_fiduciary_compliant,
)

# Compliance
from sentinelseed.compliance import (
    EUAIActComplianceChecker,
    ComplianceResult,
    RiskLevel,
    SystemType,
    check_eu_ai_act_compliance,
)

# Database Guard
from sentinelseed.database import (
    DatabaseGuard,
    QueryBlocked,
    QueryValidationResult,
    validate_query,
    is_safe_query,
)

__version__ = "2.23.0"

# Deprecated exports - kept for backwards compatibility
# These will be removed in version 3.0.0
_DEPRECATED_VALIDATORS = {
    "TruthGate": "Use Sentinel or LayeredValidator instead. TruthGate is an internal implementation detail.",
    "HarmGate": "Use Sentinel or LayeredValidator instead. HarmGate is an internal implementation detail.",
    "ScopeGate": "Use Sentinel or LayeredValidator instead. ScopeGate is an internal implementation detail.",
    "PurposeGate": "Use Sentinel or LayeredValidator instead. PurposeGate is an internal implementation detail.",
    "JailbreakGate": "JailbreakGate is deprecated. Its functionality is now integrated into TruthGate and ScopeGate.",
    "THSValidator": "Use Sentinel or LayeredValidator instead. THSValidator is an internal implementation detail.",
    "THSPValidator": "Use Sentinel or LayeredValidator instead. THSPValidator is an internal implementation detail.",
}


def __getattr__(name: str):
    """
    Lazy loading with deprecation warnings for internal validators.

    This follows PEP 562 for module-level __getattr__.
    """
    if name in _DEPRECATED_VALIDATORS:
        warnings.warn(
            f"{name} is deprecated and will be removed in version 3.0.0. "
            f"{_DEPRECATED_VALIDATORS[name]}",
            DeprecationWarning,
            stacklevel=2,
        )
        from sentinelseed.validators import gates
        return getattr(gates, name)

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


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
    # Core Interfaces (for type hints and DI)
    "Validator",
    "AsyncValidator",
    # Core Exceptions
    "SentinelError",
    "ValidationError",
    "ConfigurationError",
    "IntegrationError",
    # v3.0 architecture - unified 3-gate validation
    "SentinelValidator",
    "SentinelConfig",
    "SentinelObserver",
    "SentinelResult",
    "ObservationResult",
    # Validation (recommended for advanced usage)
    "LayeredValidator",
    "AsyncLayeredValidator",
    "ValidationResult",
    "ValidationConfig",
    "ValidationLayer",
    "ValidationRiskLevel",
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
    # Database Guard
    "DatabaseGuard",
    "QueryBlocked",
    "QueryValidationResult",
    "validate_query",
    "is_safe_query",
    # Deprecated (will be removed in 3.0.0) - use Sentinel or LayeredValidator instead
    "TruthGate",
    "HarmGate",
    "ScopeGate",
    "PurposeGate",
    "JailbreakGate",
    "THSValidator",
    "THSPValidator",
]
