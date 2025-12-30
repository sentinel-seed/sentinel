"""
Sentinel AgentKit Integration.

Provides security guardrails for Coinbase AgentKit through:
- SentinelActionProvider: ActionProvider with THSP validation
- Action wrappers for safe execution
- Pydantic schemas for input validation

This is the main integration point for AgentKit users.

Example:
    from coinbase_agentkit import AgentKit
    from sentinelseed.integrations.coinbase.agentkit import (
        SentinelActionProvider,
        sentinel_action_provider,
    )

    # Create provider
    provider = sentinel_action_provider(security_profile="strict")

    # Add to AgentKit
    agent = AgentKit(
        action_providers=[provider],
    )
"""

from .action_provider import (
    SentinelActionProvider,
    sentinel_action_provider,
)
from .schemas import (
    ValidateTransactionSchema,
    ValidateAddressSchema,
    CheckActionSafetySchema,
    GetSpendingSummarySchema,
    AssessDeFiRiskSchema,
    ConfigureGuardrailsSchema,
)
from .wrappers import (
    safe_action,
    create_safe_action_wrapper,
    SentinelActionWrapper,
)

__all__ = [
    # Action Provider
    "SentinelActionProvider",
    "sentinel_action_provider",
    # Schemas
    "ValidateTransactionSchema",
    "ValidateAddressSchema",
    "CheckActionSafetySchema",
    "GetSpendingSummarySchema",
    "AssessDeFiRiskSchema",
    "ConfigureGuardrailsSchema",
    # Wrappers
    "safe_action",
    "create_safe_action_wrapper",
    "SentinelActionWrapper",
]
