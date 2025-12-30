"""Sentinel x402 payment validation integration.

This module provides THSP safety validation for x402 payment protocol,
enabling AI agents to make safe, validated payments.

x402 is an HTTP-native payment protocol by Coinbase that uses the
HTTP 402 status code for machine-to-machine payments.

Components:
    - SentinelX402Middleware: Main validation middleware
    - SentinelX402ActionProvider: AgentKit action provider
    - sentinel_x402_hooks: httpx event hooks
    - THSPPaymentValidator: THSP gate validators

Quick Start:
    >>> from sentinelseed.integrations.x402 import SentinelX402Middleware
    >>>
    >>> middleware = SentinelX402Middleware()
    >>> result = middleware.validate_payment(
    ...     endpoint="https://api.example.com/paid",
    ...     payment_requirements=payment_req,
    ...     wallet_address="0x123...",
    ... )
    >>> if result.is_approved:
    ...     print("Payment safe to proceed")

With AgentKit:
    >>> from coinbase_agentkit import AgentKit
    >>> from sentinelseed.integrations.x402 import sentinel_x402_action_provider
    >>>
    >>> agent = AgentKit(
    ...     action_providers=[
    ...         sentinel_x402_action_provider(security_profile="strict"),
    ...     ]
    ... )

With httpx hooks:
    >>> import httpx
    >>> from eth_account import Account
    >>> from sentinelseed.integrations.x402 import sentinel_x402_hooks
    >>>
    >>> account = Account.from_key("0x...")
    >>> client = httpx.AsyncClient()
    >>> client.event_hooks = sentinel_x402_hooks(account)

References:
    - x402 Protocol: https://github.com/coinbase/x402
    - x402 Documentation: https://docs.cdp.coinbase.com/x402
"""

# Configuration
from .config import (
    ConfirmationThresholds,
    SentinelX402Config,
    SpendingLimits,
    ValidationConfig,
    get_default_config,
)

# Types
from .types import (
    EndpointReputation,
    PaymentAuditEntry,
    PaymentDecision,
    PaymentRequirementsModel,
    PaymentRiskLevel,
    PaymentValidationResult,
    SpendingRecord,
    SupportedNetwork,
    THSPGate,
    THSPGateResult,
)

# Validators
from .validators import (
    HarmGateValidator,
    PaymentValidator,
    PurposeGateValidator,
    ScopeGateValidator,
    THSPPaymentValidator,
    TruthGateValidator,
)

# Middleware
from .middleware import (
    PaymentBlockedError,
    PaymentConfirmationRequired,
    PaymentRejectedError,
    SentinelX402Middleware,
    create_sentinel_x402_middleware,
)

# Hooks
from .hooks import (
    SentinelHttpxHooks,
    SentinelRequestsAdapter,
    create_sentinel_x402_client,
    parse_payment_required_response,
    select_payment_option,
    sentinel_x402_adapter,
    sentinel_x402_hooks,
)

# AgentKit Provider
from .agentkit_provider import (
    SentinelX402ActionProvider,
    sentinel_x402_action_provider,
)

__all__ = [
    # Configuration
    "SentinelX402Config",
    "SpendingLimits",
    "ConfirmationThresholds",
    "ValidationConfig",
    "get_default_config",
    # Types
    "PaymentRiskLevel",
    "PaymentDecision",
    "THSPGate",
    "THSPGateResult",
    "PaymentValidationResult",
    "PaymentAuditEntry",
    "PaymentRequirementsModel",
    "EndpointReputation",
    "SpendingRecord",
    "SupportedNetwork",
    # Validators
    "PaymentValidator",
    "TruthGateValidator",
    "HarmGateValidator",
    "ScopeGateValidator",
    "PurposeGateValidator",
    "THSPPaymentValidator",
    # Middleware
    "SentinelX402Middleware",
    "create_sentinel_x402_middleware",
    "PaymentBlockedError",
    "PaymentRejectedError",
    "PaymentConfirmationRequired",
    # Hooks
    "sentinel_x402_hooks",
    "sentinel_x402_adapter",
    "create_sentinel_x402_client",
    "SentinelHttpxHooks",
    "SentinelRequestsAdapter",
    "parse_payment_required_response",
    "select_payment_option",
    # AgentKit
    "SentinelX402ActionProvider",
    "sentinel_x402_action_provider",
]
