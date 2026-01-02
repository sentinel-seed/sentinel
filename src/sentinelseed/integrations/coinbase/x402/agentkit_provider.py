"""Sentinel x402 Action Provider for Coinbase AgentKit.

This module provides an ActionProvider that adds Sentinel safety validation
to x402 payment flows in AgentKit-powered AI agents.

The provider wraps the standard x402 provider to add THSP gates before
any payment is executed, ensuring AI agents can't make unsafe payments.

Example:
    >>> from coinbase_agentkit import AgentKit
    >>> from sentinelseed.integrations.x402 import sentinel_x402_action_provider
    >>>
    >>> agent = AgentKit(
    ...     action_providers=[
    ...         sentinel_x402_action_provider(strict_mode=True),
    ...     ]
    ... )
"""

from __future__ import annotations

from json import dumps
from typing import Any, Literal

from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
)

try:
    from coinbase_agentkit import ActionProvider as _AgentKitActionProvider, create_action
    from coinbase_agentkit.network import Network

    AGENTKIT_AVAILABLE = True
except ImportError:
    AGENTKIT_AVAILABLE = False
    _AgentKitActionProvider = None

    class Network:
        """Fallback Network class."""

        network_id: str = ""

    def create_action(name: str, description: str, schema: type):
        def decorator(func):
            return func

        return decorator


from .config import SentinelX402Config, get_default_config
from .middleware import SentinelX402Middleware
from .schemas import (
    CheckEndpointSafetySchema,
    ConfigureSpendingLimitsSchema,
    GetAuditLogSchema,
    GetSpendingSummarySchema,
    ResetSpendingSchema,
    SafeX402RequestSchema,
    ValidatePaymentSchema,
)
from .types import PaymentDecision, PaymentRequirementsModel, PaymentRiskLevel


# Build base classes dynamically
_PROVIDER_BASES = (_AgentKitActionProvider, SentinelIntegration) if AGENTKIT_AVAILABLE else (SentinelIntegration,)


class SentinelX402ActionProvider(*_PROVIDER_BASES):
    """Sentinel safety provider for x402 payments in AgentKit.

    Inherits from ActionProvider (Coinbase) and SentinelIntegration for
    standardized validation via LayeredValidator.

    This provider adds THSP validation gates to x402 payment flows,
    ensuring AI agents validate payments before execution.

    Actions:
        - sentinel_x402_validate_payment: Validate a payment before execution
        - sentinel_x402_get_spending_summary: Get spending statistics
        - sentinel_x402_configure_limits: Configure spending limits
        - sentinel_x402_check_endpoint: Check if endpoint is safe
        - sentinel_x402_safe_request: Make a safe x402 request
        - sentinel_x402_get_audit_log: Get payment audit log
        - sentinel_x402_reset_spending: Reset spending records
    """

    _integration_name = "coinbase_x402"

    def __init__(
        self,
        config: SentinelX402Config | None = None,
        security_profile: Literal["permissive", "standard", "strict", "paranoid"] = "standard",
        validator: LayeredValidator | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            config: Custom configuration (overrides security_profile)
            security_profile: Pre-defined security profile to use
            validator: Optional LayeredValidator for dependency injection (testing)
        """
        # Create LayeredValidator if not provided
        if validator is None:
            val_config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,
            )
            validator = LayeredValidator(config=val_config)

        # Initialize parent classes explicitly
        if AGENTKIT_AVAILABLE and _AgentKitActionProvider is not None:
            _AgentKitActionProvider.__init__(self, "sentinel_x402", [])
        SentinelIntegration.__init__(self, validator=validator)

        if config:
            self.config = config
        else:
            self.config = get_default_config(security_profile)

        self.middleware = SentinelX402Middleware(config=self.config)
        self._wallet_address: str | None = None

    def supports_network(self, network: Network) -> bool:
        """Check if network is supported.

        Returns:
            True for all networks (safety validation is network-agnostic)
        """
        return True

    @create_action(
        name="sentinel_x402_validate_payment",
        description="""Validate an x402 payment request before execution using THSP gates.

This action should be called BEFORE any x402 payment to ensure it's safe.

Checks performed:
- TRUTH: Payment request is well-formed and legitimate
- HARM: Recipient/endpoint is not malicious
- SCOPE: Amount is within spending limits
- PURPOSE: Payment serves a legitimate purpose

Returns validation result with decision (approve/reject/block/require_confirmation).

Example: Before paying $5 to api.weather.io, validate with this action first.""",
        schema=ValidatePaymentSchema,
    )
    def validate_payment(self, args: dict[str, Any]) -> str:
        """Validate an x402 payment request.

        Args:
            args: Validation parameters

        Returns:
            JSON string with validation result
        """
        try:
            validated_args = ValidatePaymentSchema(**args)

            # Build payment requirements
            payment_req = PaymentRequirementsModel(
                scheme=validated_args.scheme,
                network=validated_args.network,
                max_amount_required=validated_args.amount,
                resource=validated_args.endpoint,
                description=validated_args.description,
                mime_type="",
                pay_to=validated_args.pay_to,
                max_timeout_seconds=300,
                asset=validated_args.asset,
            )

            # Get wallet address
            wallet = self._wallet_address or "unknown"

            # Validate
            result = self.middleware.validate_payment(
                endpoint=validated_args.endpoint,
                payment_requirements=payment_req,
                wallet_address=wallet,
            )

            return dumps({
                "decision": result.decision.value,
                "approved": result.is_approved,
                "risk_level": result.risk_level.value,
                "requires_confirmation": result.requires_confirmation,
                "issues": result.issues,
                "recommendations": result.recommendations,
                "gates": {
                    gate.value: {
                        "passed": gate_result.passed,
                        "reason": gate_result.reason,
                    }
                    for gate, gate_result in result.gates.items()
                },
                "amount_usd": payment_req.get_amount_float(),
            }, indent=2)

        except Exception as e:
            return dumps({
                "decision": "error",
                "approved": False,
                "error": f"Validation error: {e!s}",
            }, indent=2)

    @create_action(
        name="sentinel_x402_get_spending_summary",
        description="""Get a summary of spending for the current wallet.

Returns:
- Daily amount spent
- Daily transactions count
- Remaining daily allowance
- Hourly transaction count
- Configured limits

Use this to check how much spending capacity remains before making payments.""",
        schema=GetSpendingSummarySchema,
    )
    def get_spending_summary(self, args: dict[str, Any]) -> str:
        """Get spending summary.

        Args:
            args: Query parameters

        Returns:
            JSON string with spending summary
        """
        try:
            validated_args = GetSpendingSummarySchema(**args)
            wallet = validated_args.wallet_address or self._wallet_address or "unknown"

            summary = self.middleware.get_spending_summary(wallet)

            return dumps({
                "success": True,
                "summary": summary,
            }, indent=2)

        except Exception as e:
            return dumps({
                "success": False,
                "error": f"Error getting summary: {e!s}",
            }, indent=2)

    @create_action(
        name="sentinel_x402_configure_limits",
        description="""Configure spending limits for x402 payments.

You can adjust:
- max_single_payment: Maximum USD for one payment
- max_daily_total: Maximum USD per day
- max_transactions_per_day: Transaction count limit

These limits help prevent accidental overspending by AI agents.""",
        schema=ConfigureSpendingLimitsSchema,
    )
    def configure_limits(self, args: dict[str, Any]) -> str:
        """Configure spending limits.

        Args:
            args: New limit values

        Returns:
            JSON string confirming new limits
        """
        try:
            validated_args = ConfigureSpendingLimitsSchema(**args)

            if validated_args.max_single_payment is not None:
                self.config.spending_limits.max_single_payment = validated_args.max_single_payment

            if validated_args.max_daily_total is not None:
                self.config.spending_limits.max_daily_total = validated_args.max_daily_total

            if validated_args.max_transactions_per_day is not None:
                self.config.spending_limits.max_transactions_per_day = validated_args.max_transactions_per_day

            return dumps({
                "success": True,
                "message": "Spending limits updated",
                "limits": {
                    "max_single_payment": self.config.spending_limits.max_single_payment,
                    "max_daily_total": self.config.spending_limits.max_daily_total,
                    "max_transactions_per_day": self.config.spending_limits.max_transactions_per_day,
                },
            }, indent=2)

        except Exception as e:
            return dumps({
                "success": False,
                "error": f"Error configuring limits: {e!s}",
            }, indent=2)

    @create_action(
        name="sentinel_x402_check_endpoint",
        description="""Check if an endpoint is safe for x402 payments.

This performs a preliminary safety check on an endpoint before
even attempting a request. Use this to pre-screen endpoints.

Returns safety assessment and any known issues with the endpoint.""",
        schema=CheckEndpointSafetySchema,
    )
    def check_endpoint(self, args: dict[str, Any]) -> str:
        """Check endpoint safety.

        Args:
            args: Endpoint to check

        Returns:
            JSON string with safety assessment
        """
        try:
            validated_args = CheckEndpointSafetySchema(**args)
            endpoint = validated_args.endpoint

            issues: list[str] = []
            warnings: list[str] = []

            # Check blocklist
            for blocked in self.config.blocked_endpoints:
                if blocked.lower() in endpoint.lower():
                    issues.append(f"Endpoint matches blocked pattern: {blocked}")

            # Check HTTPS
            if self.config.validation.require_https and not endpoint.startswith("https://"):
                issues.append("Endpoint does not use HTTPS")

            # Check for IP address
            import re
            from urllib.parse import urlparse

            try:
                parsed = urlparse(endpoint)
                netloc = parsed.netloc.split(":")[0]
                if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", netloc):
                    warnings.append("Endpoint uses IP address instead of domain")
            except Exception:
                issues.append("Invalid URL format")

            is_safe = len(issues) == 0

            return dumps({
                "endpoint": endpoint,
                "is_safe": is_safe,
                "issues": issues,
                "warnings": warnings,
                "recommendation": (
                    "Endpoint appears safe for payments"
                    if is_safe
                    else "Review issues before proceeding"
                ),
            }, indent=2)

        except Exception as e:
            return dumps({
                "is_safe": False,
                "error": f"Error checking endpoint: {e!s}",
            }, indent=2)

    @create_action(
        name="sentinel_x402_get_audit_log",
        description="""Get the audit log of x402 payment validations.

Returns recent payment validation attempts with:
- Timestamp
- Amount and destination
- Decision (approved/rejected/blocked)
- Risk level assessed

Useful for reviewing payment history and debugging issues.""",
        schema=GetAuditLogSchema,
    )
    def get_audit_log(self, args: dict[str, Any]) -> str:
        """Get audit log.

        Args:
            args: Query parameters

        Returns:
            JSON string with audit entries
        """
        try:
            validated_args = GetAuditLogSchema(**args)

            entries = self.middleware.get_audit_log(
                wallet_address=validated_args.wallet_address,
                limit=validated_args.limit,
            )

            return dumps({
                "success": True,
                "count": len(entries),
                "entries": entries,
            }, indent=2)

        except Exception as e:
            return dumps({
                "success": False,
                "error": f"Error getting audit log: {e!s}",
            }, indent=2)

    @create_action(
        name="sentinel_x402_reset_spending",
        description="""Reset spending records for a wallet.

WARNING: This clears all spending tracking. Use with caution.

Requires confirm=True to execute. Optionally specify wallet_address
to reset only that wallet, otherwise resets all wallets.""",
        schema=ResetSpendingSchema,
    )
    def reset_spending(self, args: dict[str, Any]) -> str:
        """Reset spending records.

        Args:
            args: Reset parameters

        Returns:
            JSON string confirming reset
        """
        try:
            validated_args = ResetSpendingSchema(**args)

            if not validated_args.confirm:
                return dumps({
                    "success": False,
                    "error": "Must set confirm=True to reset spending records",
                }, indent=2)

            self.middleware.reset_spending(validated_args.wallet_address)

            return dumps({
                "success": True,
                "message": (
                    f"Reset spending for {validated_args.wallet_address}"
                    if validated_args.wallet_address
                    else "Reset all spending records"
                ),
            }, indent=2)

        except Exception as e:
            return dumps({
                "success": False,
                "error": f"Error resetting spending: {e!s}",
            }, indent=2)

    def set_wallet_address(self, address: str) -> None:
        """Set the current wallet address for validation context.

        Args:
            address: The wallet address
        """
        self._wallet_address = address


def sentinel_x402_action_provider(
    config: SentinelX402Config | None = None,
    security_profile: Literal["permissive", "standard", "strict", "paranoid"] = "standard",
) -> SentinelX402ActionProvider:
    """Create a Sentinel x402 action provider for AgentKit.

    Args:
        config: Custom configuration (optional)
        security_profile: Security profile if no config provided

    Returns:
        Configured SentinelX402ActionProvider

    Example:
        >>> from coinbase_agentkit import AgentKit
        >>> from sentinelseed.integrations.x402 import sentinel_x402_action_provider
        >>>
        >>> # With default settings
        >>> provider = sentinel_x402_action_provider()
        >>>
        >>> # With strict security
        >>> provider = sentinel_x402_action_provider(security_profile="strict")
        >>>
        >>> # Use with AgentKit
        >>> agent = AgentKit(action_providers=[provider])
    """
    return SentinelX402ActionProvider(
        config=config,
        security_profile=security_profile,
    )
