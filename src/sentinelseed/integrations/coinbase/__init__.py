"""
Sentinel Coinbase Integration.

Comprehensive security integration for the Coinbase ecosystem including:
- AgentKit guardrails (ActionProvider with THSP validation)
- x402 payment validation (HTTP 402 payment protocol)
- EVM address and transaction validation

This is a unified integration that provides security for AI agents
operating in the Coinbase ecosystem.

Installation:
    pip install sentinelseed

    # For full AgentKit support:
    pip install sentinelseed coinbase-agentkit

    # For x402 support:
    pip install sentinelseed x402 httpx

Quick Start - AgentKit:
    from coinbase_agentkit import AgentKit
    from sentinelseed.integrations.coinbase import sentinel_action_provider

    # Create security provider
    provider = sentinel_action_provider(security_profile="strict")

    # Add to your agent
    agent = AgentKit(action_providers=[provider])

Quick Start - x402 Payments:
    from sentinelseed.integrations.coinbase import SentinelX402Middleware

    middleware = SentinelX402Middleware()
    result = middleware.validate_payment(
        endpoint="https://api.example.com/paid",
        payment_requirements=payment_req,
        wallet_address="0x123...",
    )

Documentation:
    https://sentinelseed.dev/docs/coinbase

References:
    - Coinbase AgentKit: https://github.com/coinbase/agentkit
    - x402 Protocol: https://github.com/coinbase/x402
    - Sentinel: https://sentinelseed.dev
"""

from __future__ import annotations

__version__ = "1.0.0"
__author__ = "Sentinel Team"

# Configuration
from .config import (
    ChainType,
    SecurityProfile,
    RiskLevel,
    SpendingLimits,
    ChainConfig,
    SentinelCoinbaseConfig,
    get_default_config,
    HIGH_RISK_ACTIONS,
    SAFE_ACTIONS,
    BLOCKED_ACTIONS,
)

# Validators
from .validators import (
    # Address validation
    AddressValidationResult,
    is_valid_evm_address,
    is_valid_checksum_address,
    to_checksum_address,
    validate_address,
    # Transaction validation
    TransactionValidationResult,
    TransactionValidator,
    validate_transaction,
    # DeFi validation
    DeFiRiskAssessment,
    DeFiValidator,
    assess_defi_risk,
)

# AgentKit Integration
from .agentkit import (
    SentinelActionProvider,
    sentinel_action_provider,
    # Schemas
    ValidateTransactionSchema,
    ValidateAddressSchema,
    CheckActionSafetySchema,
    GetSpendingSummarySchema,
    AssessDeFiRiskSchema,
    ConfigureGuardrailsSchema,
    # Wrappers
    safe_action,
    create_safe_action_wrapper,
    SentinelActionWrapper,
)

# x402 Integration
from .x402 import (
    # Core types
    PaymentDecision,
    PaymentRiskLevel,
    PaymentValidationResult,
    THSPGate,
    THSPGateResult,
    PaymentRequirementsModel,
    # Config
    SentinelX402Config,
    SpendingLimits as X402SpendingLimits,
    ConfirmationThresholds,
    ValidationConfig,
    get_default_config as get_x402_config,
    # Middleware
    SentinelX402Middleware,
    # Hooks
    sentinel_x402_hooks,
    # Action Provider
    SentinelX402ActionProvider,
    sentinel_x402_action_provider,
    # Exceptions
    PaymentBlockedError,
    PaymentRejectedError,
    PaymentConfirmationRequired,
)


__all__ = [
    # Version
    "__version__",

    # Configuration
    "ChainType",
    "SecurityProfile",
    "RiskLevel",
    "SpendingLimits",
    "ChainConfig",
    "SentinelCoinbaseConfig",
    "get_default_config",
    "HIGH_RISK_ACTIONS",
    "SAFE_ACTIONS",
    "BLOCKED_ACTIONS",

    # Address Validation
    "AddressValidationResult",
    "is_valid_evm_address",
    "is_valid_checksum_address",
    "to_checksum_address",
    "validate_address",

    # Transaction Validation
    "TransactionValidationResult",
    "TransactionValidator",
    "validate_transaction",

    # DeFi Validation
    "DeFiRiskAssessment",
    "DeFiValidator",
    "assess_defi_risk",

    # AgentKit Integration
    "SentinelActionProvider",
    "sentinel_action_provider",
    "ValidateTransactionSchema",
    "ValidateAddressSchema",
    "CheckActionSafetySchema",
    "GetSpendingSummarySchema",
    "AssessDeFiRiskSchema",
    "ConfigureGuardrailsSchema",
    "safe_action",
    "create_safe_action_wrapper",
    "SentinelActionWrapper",

    # x402 Integration
    "PaymentDecision",
    "PaymentRiskLevel",
    "PaymentValidationResult",
    "THSPGate",
    "THSPGateResult",
    "PaymentRequirementsModel",
    "SentinelX402Config",
    "X402SpendingLimits",
    "ConfirmationThresholds",
    "ValidationConfig",
    "get_x402_config",
    "SentinelX402Middleware",
    "sentinel_x402_hooks",
    "SentinelX402ActionProvider",
    "sentinel_x402_action_provider",
    "PaymentBlockedError",
    "PaymentRejectedError",
    "PaymentConfirmationRequired",
]
