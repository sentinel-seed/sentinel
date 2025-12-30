"""Sentinel integration for Coinbase AgentKit.

This module provides a SentinelActionProvider that adds THSP safety validation
to any AgentKit-powered AI agent.

Example:
    >>> from coinbase_agentkit import AgentKit
    >>> from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider
    >>>
    >>> agent = AgentKit(
    ...     action_providers=[
    ...         sentinel_action_provider(strict_mode=True),
    ...     ]
    ... )
"""

from .schemas import (
    AnalyzeRiskSchema,
    CheckComplianceSchema,
    ComplianceFramework,
    RiskLevel,
    ScanSecretsSchema,
    ValidateOutputSchema,
    ValidatePromptSchema,
    ValidateTransactionSchema,
)
from .sentinel_action_provider import (
    SentinelActionProvider,
    sentinel_action_provider,
)

__all__ = [
    # Provider
    "SentinelActionProvider",
    "sentinel_action_provider",
    # Schemas
    "ValidatePromptSchema",
    "ValidateTransactionSchema",
    "ScanSecretsSchema",
    "CheckComplianceSchema",
    "AnalyzeRiskSchema",
    "ValidateOutputSchema",
    # Enums
    "RiskLevel",
    "ComplianceFramework",
]
