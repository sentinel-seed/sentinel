"""
Sentinel ActionProvider for Coinbase AgentKit.

Provides security guardrails as an ActionProvider that can be added
to any AgentKit-powered AI agent. Implements comprehensive validation
using THSP Protocol and EVM-specific checks.

This is the main integration point for AgentKit users.

Based on official AgentKit provider patterns from:
https://github.com/coinbase/agentkit/tree/master/python/coinbase-agentkit

Example:
    from coinbase_agentkit import AgentKit
    from sentinelseed.integrations.coinbase.agentkit import sentinel_action_provider

    # Create provider with strict security
    provider = sentinel_action_provider(security_profile="strict")

    # Add to AgentKit agent
    agent = AgentKit(action_providers=[provider])
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
    ValidationResult,
)

# Try to import AgentKit
try:
    from coinbase_agentkit import ActionProvider as _AgentKitActionProvider
    from coinbase_agentkit import create_action
    from coinbase_agentkit.network import Network

    AGENTKIT_AVAILABLE = True
except ImportError:
    AGENTKIT_AVAILABLE = False
    _AgentKitActionProvider = None

    # Fallback types for development/testing
    class Network:
        """Fallback Network class."""

        network_id: str = ""
        protocol_family: str = ""

    def create_action(name: str, description: str, schema: type):
        """Fallback decorator."""
        def decorator(func):
            return func
        return decorator


# Import validators
from ..config import (
    ChainType,
    SecurityProfile,
    SentinelCoinbaseConfig,
    get_default_config,
)
from ..validators.address import validate_address
from ..validators.defi import DeFiValidator, assess_defi_risk
from ..validators.transaction import TransactionValidator

# Import schemas
from .schemas import (
    AssessDeFiRiskSchema,
    BlockAddressSchema,
    CheckActionSafetySchema,
    ConfigureGuardrailsSchema,
    GetSpendingSummarySchema,
    GetValidationHistorySchema,
    UnblockAddressSchema,
    ValidateAddressSchema,
    ValidateTransactionSchema,
)

logger = logging.getLogger("sentinelseed.coinbase.agentkit")


# Build the base classes tuple dynamically
_PROVIDER_BASES = (_AgentKitActionProvider, SentinelIntegration) if AGENTKIT_AVAILABLE else (SentinelIntegration,)


class SentinelActionProvider(*_PROVIDER_BASES):
    """
    Sentinel security ActionProvider for Coinbase AgentKit.

    Inherits from ActionProvider (Coinbase) and SentinelIntegration for
    standardized validation via LayeredValidator.

    Provides the following security actions:
    - sentinel_validate_transaction: Validate before any transfer
    - sentinel_validate_address: Validate address format and status
    - sentinel_check_action_safety: Check if any action is safe
    - sentinel_get_spending_summary: Get spending limits and usage
    - sentinel_assess_defi_risk: Assess DeFi operation risk
    - sentinel_configure_guardrails: Adjust security settings
    - sentinel_block_address: Block a malicious address
    - sentinel_unblock_address: Remove address from blocklist
    - sentinel_get_validation_history: Get validation audit log

    Example:
        provider = SentinelActionProvider()

        # Validate before transfer
        result = provider.validate_transaction({
            "action": "native_transfer",
            "from_address": "0x123...",
            "to_address": "0x456...",
            "amount": 50.0,
        })
    """

    _integration_name = "coinbase_agentkit"

    def __init__(
        self,
        config: Optional[SentinelCoinbaseConfig] = None,
        wallet_address: Optional[str] = None,
        validator: Optional[LayeredValidator] = None,
    ):
        """
        Initialize the Sentinel ActionProvider.

        Args:
            config: Security configuration. Uses default if not provided.
            wallet_address: Default wallet address for operations.
            validator: Optional LayeredValidator for dependency injection (testing).
        """
        # Create LayeredValidator if not provided
        if validator is None:
            val_config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,  # Coinbase uses heuristic by default
            )
            validator = LayeredValidator(config=val_config)

        # Initialize parent classes explicitly
        if AGENTKIT_AVAILABLE and _AgentKitActionProvider is not None:
            _AgentKitActionProvider.__init__(
                self,
                name="sentinel",
                action_providers=[],
            )
        SentinelIntegration.__init__(self, validator=validator)

        self.config = config or get_default_config()
        self.wallet_address = wallet_address

        # Initialize validators
        self.transaction_validator = TransactionValidator(config=self.config)
        self.defi_validator = DeFiValidator()

        logger.info(
            f"SentinelActionProvider initialized with profile: {self.config.security_profile.value}"
        )

    def supports_network(self, network: Network) -> bool:
        """
        Check if this provider supports a network.

        Sentinel supports all networks (validation is network-agnostic).
        """
        return True

    # =========================================================================
    # Action: Validate Transaction
    # =========================================================================

    @create_action(
        name="sentinel_validate_transaction",
        description=(
            "Validate a transaction before execution. ALWAYS call this before "
            "native_transfer, transfer, approve, or any financial operation. "
            "Returns whether the transaction is safe, requires confirmation, "
            "or should be blocked."
        ),
        schema=ValidateTransactionSchema,
    )
    def validate_transaction(self, args: dict[str, Any]) -> str:
        """Validate a transaction before execution."""
        try:
            validated = ValidateTransactionSchema(**args)

            # Map chain enum to ChainType
            chain = ChainType(validated.chain.value)

            # Validate using transaction validator
            result = self.transaction_validator.validate(
                action=validated.action,
                from_address=validated.from_address,
                to_address=validated.to_address,
                amount=validated.amount,
                chain=chain,
                token_address=validated.token_address,
                approval_amount=validated.approval_amount,
                purpose=validated.purpose,
            )

            # Also run THSP validation using inherited validate() if purpose provided
            thsp_concerns = []
            if validated.purpose:
                thsp_result: ValidationResult = self.validate(validated.purpose)
                if not thsp_result.is_safe:
                    thsp_concerns = thsp_result.violations or []

            response = {
                "decision": result.decision.value,
                "approved": result.is_approved,
                "should_proceed": result.should_proceed,
                "requires_confirmation": result.requires_confirmation,
                "risk_level": result.risk_level.value,
                "concerns": result.concerns + thsp_concerns,
                "recommendations": result.recommendations,
                "blocked_reason": result.blocked_reason,
            }

            return json.dumps(response, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Transaction validation error: {e}")
            return json.dumps({
                "error": "Validation error occurred",
                "decision": "block",
                "approved": False,
            })

    # =========================================================================
    # Action: Validate Address
    # =========================================================================

    @create_action(
        name="sentinel_validate_address",
        description=(
            "Validate an Ethereum address format and checksum. "
            "Also checks if the address is on the blocklist."
        ),
        schema=ValidateAddressSchema,
    )
    def validate_address_action(self, args: dict[str, Any]) -> str:
        """Validate an address."""
        try:
            validated = ValidateAddressSchema(**args)

            result = validate_address(
                validated.address,
                require_checksum=validated.require_checksum,
            )

            is_blocked = self.config.is_address_blocked(validated.address)

            response = {
                "valid": result.valid and not is_blocked,
                "status": result.status.value,
                "is_checksummed": result.is_checksummed,
                "checksum_address": result.checksum_address,
                "is_blocked": is_blocked,
                "warnings": result.warnings,
            }

            if is_blocked:
                response["blocked_reason"] = "Address is on the blocklist"

            return json.dumps(response, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Address validation error: {e}")
            return json.dumps({
                "error": "Validation error occurred",
                "valid": False,
            })

    # =========================================================================
    # Action: Check Action Safety
    # =========================================================================

    @create_action(
        name="sentinel_check_action_safety",
        description=(
            "Check if any AgentKit action is safe to execute. "
            "Use before sensitive operations to verify they pass security checks."
        ),
        schema=CheckActionSafetySchema,
    )
    def check_action_safety(self, args: dict[str, Any]) -> str:
        """Check if an action is safe."""
        try:
            validated = CheckActionSafetySchema(**args)

            concerns = []
            recommendations = []

            # Check if action is allowed
            if not self.config.is_action_allowed(validated.action_name):
                return json.dumps({
                    "safe": False,
                    "blocked": True,
                    "reason": f"Action '{validated.action_name}' is not allowed",
                })

            # Check risk level
            is_high_risk = self.config.is_high_risk_action(validated.action_name)
            is_safe_action = self.config.is_safe_action(validated.action_name)

            if is_high_risk:
                concerns.append(f"'{validated.action_name}' is a high-risk action")
                if self.config.require_purpose_for_transfers and not validated.purpose:
                    concerns.append("High-risk actions require a stated purpose")

            # Run THSP validation on purpose if provided using inherited validate()
            if validated.purpose:
                thsp_result: ValidationResult = self.validate(validated.purpose)
                if not thsp_result.is_safe:
                    concerns.extend(thsp_result.violations or [])

            # Check args if provided
            if validated.action_args:
                args_str = json.dumps(validated.action_args)
                thsp_result: ValidationResult = self.validate(args_str)
                if not thsp_result.is_safe:
                    concerns.append("Suspicious content detected in action arguments")

            response = {
                "safe": len(concerns) == 0,
                "action": validated.action_name,
                "is_high_risk": is_high_risk,
                "is_safe_action": is_safe_action,
                "concerns": concerns,
                "recommendations": recommendations,
            }

            return json.dumps(response, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Action safety check error: {e}")
            return json.dumps({
                "error": "Safety check error occurred",
                "safe": False,
            })

    # =========================================================================
    # Action: Get Spending Summary
    # =========================================================================

    @create_action(
        name="sentinel_get_spending_summary",
        description=(
            "Get spending summary for a wallet including current usage "
            "and remaining limits."
        ),
        schema=GetSpendingSummarySchema,
    )
    def get_spending_summary(self, args: dict[str, Any]) -> str:
        """Get spending summary."""
        try:
            validated = GetSpendingSummarySchema(**args)

            wallet = validated.wallet_address or self.wallet_address
            if not wallet:
                return json.dumps({
                    "error": "No wallet address provided",
                    "success": False,
                })

            summary = self.transaction_validator.get_spending_summary(wallet)

            return json.dumps({
                "success": True,
                "wallet": wallet[:10] + "..." + wallet[-6:],
                "summary": summary,
            }, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Spending summary error: {e}")
            return json.dumps({
                "error": "Error occurred during spending summary",
                "success": False,
            })

    # =========================================================================
    # Action: Assess DeFi Risk
    # =========================================================================

    @create_action(
        name="sentinel_assess_defi_risk",
        description=(
            "Assess the risk of a DeFi operation. Use before supply, borrow, "
            "trade, or other DeFi actions to understand the risks."
        ),
        schema=AssessDeFiRiskSchema,
    )
    def assess_defi_risk_action(self, args: dict[str, Any]) -> str:
        """Assess DeFi operation risk."""
        try:
            validated = AssessDeFiRiskSchema(**args)

            assessment = self.defi_validator.assess(
                protocol=validated.protocol,
                action=validated.action,
                amount=validated.amount,
                collateral_ratio=validated.collateral_ratio,
                apy=validated.apy,
                token_address=validated.token_address,
            )

            return json.dumps({
                "protocol": assessment.protocol.value,
                "action": assessment.action_type.value,
                "risk_level": assessment.risk_level.value,
                "risk_score": round(assessment.risk_score, 1),
                "is_high_risk": assessment.is_high_risk,
                "risk_factors": assessment.risk_factors,
                "warnings": assessment.warnings,
                "recommendations": assessment.recommendations,
            }, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"DeFi risk assessment error: {e}")
            return json.dumps({
                "error": "Assessment error occurred",
                "risk_level": "critical",
            })

    # =========================================================================
    # Action: Configure Guardrails
    # =========================================================================

    @create_action(
        name="sentinel_configure_guardrails",
        description=(
            "Configure security guardrails. Adjust spending limits, "
            "security profile, and other settings."
        ),
        schema=ConfigureGuardrailsSchema,
    )
    def configure_guardrails(self, args: dict[str, Any]) -> str:
        """Configure guardrails."""
        try:
            validated = ConfigureGuardrailsSchema(**args)
            changes = []

            if validated.security_profile:
                self.config.security_profile = SecurityProfile(validated.security_profile.value)
                self.config._init_default_chain_configs()
                changes.append(f"Security profile set to: {validated.security_profile.value}")

            if validated.block_unlimited_approvals is not None:
                self.config.block_unlimited_approvals = validated.block_unlimited_approvals
                changes.append(f"Block unlimited approvals: {validated.block_unlimited_approvals}")

            if validated.require_purpose is not None:
                self.config.require_purpose_for_transfers = validated.require_purpose
                changes.append(f"Require purpose: {validated.require_purpose}")

            # Note: Spending limits are per-chain and immutable in the current design
            # To change them, create a new config with different limits

            return json.dumps({
                "success": True,
                "changes": changes,
                "current_profile": self.config.security_profile.value,
            }, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Configure guardrails error: {e}")
            return json.dumps({
                "error": "Configuration error occurred",
                "success": False,
            })

    # =========================================================================
    # Action: Block Address
    # =========================================================================

    @create_action(
        name="sentinel_block_address",
        description="Add an address to the blocklist.",
        schema=BlockAddressSchema,
    )
    def block_address(self, args: dict[str, Any]) -> str:
        """Block an address."""
        try:
            validated = BlockAddressSchema(**args)

            self.config.blocked_addresses.add(validated.address.lower())

            return json.dumps({
                "success": True,
                "address": validated.address,
                "action": "blocked",
                "reason": validated.reason or "Manual block",
            })

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Block address error: {e}")
            return json.dumps({
                "error": "Error occurred during block address",
                "success": False,
            })

    # =========================================================================
    # Action: Unblock Address
    # =========================================================================

    @create_action(
        name="sentinel_unblock_address",
        description="Remove an address from the blocklist.",
        schema=UnblockAddressSchema,
    )
    def unblock_address(self, args: dict[str, Any]) -> str:
        """Unblock an address."""
        try:
            validated = UnblockAddressSchema(**args)

            address_lower = validated.address.lower()
            if address_lower in self.config.blocked_addresses:
                self.config.blocked_addresses.remove(address_lower)
                return json.dumps({
                    "success": True,
                    "address": validated.address,
                    "action": "unblocked",
                })
            else:
                return json.dumps({
                    "success": False,
                    "address": validated.address,
                    "reason": "Address was not blocked",
                })

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Unblock address error: {e}")
            return json.dumps({
                "error": "Error occurred during unblock address",
                "success": False,
            })

    # =========================================================================
    # Action: Get Validation History
    # =========================================================================

    @create_action(
        name="sentinel_get_validation_history",
        description="Get validation history for auditing and debugging.",
        schema=GetValidationHistorySchema,
    )
    def get_validation_history(self, args: dict[str, Any]) -> str:
        """Get validation history."""
        try:
            validated = GetValidationHistorySchema(**args)

            history = self.transaction_validator._validation_history

            # Filter and limit
            filtered = []
            for result in reversed(history):
                if len(filtered) >= validated.limit:
                    break

                is_approved = result.is_approved
                if is_approved and not validated.include_approved:
                    continue
                if not is_approved and not validated.include_rejected:
                    continue

                filtered.append({
                    "decision": result.decision.value,
                    "risk_level": result.risk_level.value,
                    "concerns": result.concerns[:3],  # Limit concerns for brevity
                    "blocked_reason": result.blocked_reason,
                })

            stats = self.transaction_validator.get_validation_stats()

            return json.dumps({
                "total_validations": stats.get("total", 0),
                "approval_rate": round(stats.get("approval_rate", 1.0) * 100, 1),
                "recent_validations": filtered,
            }, indent=2)

        except (ValueError, TypeError, KeyError, AttributeError, RuntimeError) as e:
            logger.error(f"Get validation history error: {e}")
            return json.dumps({
                "error": "Error occurred during get validation history",
            })

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def record_transaction(self, from_address: str, amount: float) -> None:
        """
        Record a completed transaction for spending tracking.

        Call this after a transaction is successfully executed.
        """
        self.transaction_validator.record_completed_transaction(from_address, amount)

    def reset_spending(self, wallet: Optional[str] = None) -> None:
        """Reset spending counters."""
        self.transaction_validator.reset_spending(wallet)


def sentinel_action_provider(
    security_profile: str = "standard",
    wallet_address: Optional[str] = None,
    **kwargs: Any,
) -> SentinelActionProvider:
    """
    Create a SentinelActionProvider with the specified security profile.

    Args:
        security_profile: One of "permissive", "standard", "strict", "paranoid"
        wallet_address: Default wallet address for operations
        **kwargs: Additional configuration options

    Returns:
        Configured SentinelActionProvider

    Example:
        from coinbase_agentkit import AgentKit
        from sentinelseed.integrations.coinbase.agentkit import sentinel_action_provider

        provider = sentinel_action_provider(security_profile="strict")
        agent = AgentKit(action_providers=[provider])
    """
    config = get_default_config(security_profile)

    # Apply any additional kwargs
    if kwargs.get("blocked_addresses"):
        config.blocked_addresses.update(kwargs["blocked_addresses"])

    if kwargs.get("block_unlimited_approvals") is not None:
        config.block_unlimited_approvals = kwargs["block_unlimited_approvals"]

    if kwargs.get("require_purpose") is not None:
        config.require_purpose_for_transfers = kwargs["require_purpose"]

    return SentinelActionProvider(
        config=config,
        wallet_address=wallet_address,
    )


__all__ = [
    "SentinelActionProvider",
    "sentinel_action_provider",
    "AGENTKIT_AVAILABLE",
    "THSP_AVAILABLE",
]
