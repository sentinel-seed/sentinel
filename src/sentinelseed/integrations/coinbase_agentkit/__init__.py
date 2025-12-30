"""
Sentinel integration for Coinbase AgentKit.

This module provides a SentinelActionProvider that adds THSP safety validation
to any AgentKit-powered AI agent.

Usage:
    from coinbase_agentkit import AgentKit
    from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider

    agent = AgentKit(
        action_providers=[
            sentinel_action_provider(),
            # ... other providers
        ]
    )
"""

from .provider import SentinelActionProvider, sentinel_action_provider
from .schemas import (
    ValidatePromptSchema,
    ValidateTransactionSchema,
    ScanSecretsSchema,
    CheckComplianceSchema,
)

__all__ = [
    "SentinelActionProvider",
    "sentinel_action_provider",
    "ValidatePromptSchema",
    "ValidateTransactionSchema",
    "ScanSecretsSchema",
    "CheckComplianceSchema",
]
