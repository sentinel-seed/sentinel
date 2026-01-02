"""Sentinel x402 payment validation middleware.

This module provides the main middleware class that integrates Sentinel
safety validation with x402 payment flows.

The middleware can be used:
    1. Standalone for manual payment validation
    2. With x402 SDK hooks for automatic validation
    3. With AgentKit as an action provider

Example:
    >>> from sentinelseed.integrations.coinbase.x402 import SentinelX402Middleware
    >>>
    >>> middleware = SentinelX402Middleware()
    >>> result = middleware.validate_payment(
    ...     endpoint="https://api.example.com/data",
    ...     payment_requirements=payment_req,
    ...     wallet_address="0x123...",
    ... )
    >>> if result.is_approved:
    ...     print("Payment approved")
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from json import dumps
from threading import Lock
from typing import Any, Callable

from .config import SentinelX402Config, get_default_config
from .types import (
    PaymentAuditEntry,
    PaymentDecision,
    PaymentRequirementsModel,
    PaymentRiskLevel,
    PaymentValidationResult,
    SpendingRecord,
    THSPGate,
    THSPGateResult,
)
from .validators import THSPPaymentValidator

logger = logging.getLogger(__name__)


class SentinelX402Middleware:
    """Main Sentinel middleware for x402 payment validation.

    This class provides comprehensive payment validation using the THSP
    framework, with support for spending limits, rate limiting, and
    audit logging.

    Attributes:
        config: The middleware configuration
        validator: The THSP validator instance

    Example:
        >>> # Basic usage
        >>> middleware = SentinelX402Middleware()
        >>> result = middleware.validate_payment(...)
        >>>
        >>> # With custom config
        >>> from sentinelseed.integrations.coinbase.x402.config import get_default_config
        >>> config = get_default_config("strict")
        >>> middleware = SentinelX402Middleware(config=config)
        >>>
        >>> # Using lifecycle hooks
        >>> middleware.before_payment_hook(endpoint, payment_req, wallet)
        >>> # ... payment executes ...
        >>> middleware.after_payment_hook(endpoint, payment_proof, success)
    """

    def __init__(
        self,
        config: SentinelX402Config | None = None,
        on_payment_blocked: Callable[[PaymentValidationResult], None] | None = None,
        on_payment_approved: Callable[[PaymentValidationResult], None] | None = None,
        on_confirmation_required: Callable[[PaymentValidationResult], bool] | None = None,
    ) -> None:
        """Initialize the middleware.

        Args:
            config: Middleware configuration. If None, uses default config.
            on_payment_blocked: Callback when a payment is blocked
            on_payment_approved: Callback when a payment is approved
            on_confirmation_required: Callback to get user confirmation.
                Should return True if user confirms, False otherwise.
        """
        self.config = config or get_default_config("standard")
        self.validator = THSPPaymentValidator()

        # Callbacks
        self._on_blocked = on_payment_blocked
        self._on_approved = on_payment_approved
        self._on_confirmation = on_confirmation_required

        # State tracking (thread-safe)
        self._lock = Lock()
        self._spending_records: dict[str, dict[str, SpendingRecord]] = defaultdict(dict)
        self._hourly_counts: dict[str, list[datetime]] = defaultdict(list)
        self._endpoint_history: dict[str, list[datetime]] = defaultdict(list)
        self._recipient_history: dict[str, list[datetime]] = defaultdict(list)
        self._audit_log: list[PaymentAuditEntry] = []

    def validate_payment(
        self,
        endpoint: str,
        payment_requirements: PaymentRequirementsModel | dict[str, Any],
        wallet_address: str,
    ) -> PaymentValidationResult:
        """Validate a payment request through THSP gates.

        This is the main entry point for payment validation.

        Args:
            endpoint: The URL of the endpoint requesting payment
            payment_requirements: x402 payment requirements (model or dict)
            wallet_address: The wallet address making the payment

        Returns:
            PaymentValidationResult with decision and details
        """
        # Convert dict to model if needed
        if isinstance(payment_requirements, dict):
            payment_requirements = PaymentRequirementsModel(**payment_requirements)

        # Build validation context
        context = self._build_validation_context(wallet_address, endpoint)

        # Run THSP validation
        gate_results = self.validator.validate_payment(
            payment_requirements=payment_requirements,
            endpoint=endpoint,
            wallet_address=wallet_address,
            config=self.config,
            context=context,
        )

        # Calculate risk level
        risk_level = self.validator.calculate_risk_level(
            gate_results=gate_results,
            payment_requirements=payment_requirements,
            config=self.config,
        )

        # Determine decision
        decision = self._determine_decision(
            gate_results=gate_results,
            risk_level=risk_level,
            payment_requirements=payment_requirements,
        )

        # Build result
        result = self._build_result(
            decision=decision,
            risk_level=risk_level,
            gate_results=gate_results,
            payment_requirements=payment_requirements,
            endpoint=endpoint,
        )

        # Trigger callbacks
        self._trigger_callbacks(result)

        # Log for audit
        if self.config.validation.audit_all_payments:
            self._log_audit(
                wallet_address=wallet_address,
                endpoint=endpoint,
                payment_requirements=payment_requirements,
                result=result,
            )

        return result

    def before_payment_hook(
        self,
        endpoint: str,
        payment_requirements: PaymentRequirementsModel | dict[str, Any],
        wallet_address: str,
    ) -> PaymentValidationResult:
        """x402 lifecycle hook: called before payment execution.

        This hook integrates with x402 SDK's lifecycle system.

        Args:
            endpoint: The endpoint URL
            payment_requirements: The x402 payment requirements
            wallet_address: The wallet address

        Returns:
            PaymentValidationResult

        Raises:
            PaymentBlockedError: If payment is blocked
        """
        result = self.validate_payment(
            endpoint=endpoint,
            payment_requirements=payment_requirements,
            wallet_address=wallet_address,
        )

        if result.decision == PaymentDecision.BLOCK:
            raise PaymentBlockedError(
                f"Payment blocked: {result.blocked_reason}",
                result=result,
            )

        if result.decision == PaymentDecision.REJECT:
            raise PaymentRejectedError(
                f"Payment rejected: {'; '.join(result.issues)}",
                result=result,
            )

        return result

    def after_payment_hook(
        self,
        endpoint: str,
        wallet_address: str,
        amount: float,
        asset: str,
        network: str,
        pay_to: str,
        success: bool,
        transaction_hash: str | None = None,
        error: str | None = None,
    ) -> None:
        """x402 lifecycle hook: called after payment execution.

        This hook records the payment for tracking and updates state.

        Args:
            endpoint: The endpoint URL
            wallet_address: The wallet address
            amount: The payment amount
            asset: The asset used for payment
            network: The network used
            pay_to: The recipient address
            success: Whether the payment succeeded
            transaction_hash: The transaction hash (if successful)
            error: Error message (if failed)
        """
        with self._lock:
            # Record spending
            if success:
                self._record_spending(wallet_address, amount, endpoint)
                self._record_endpoint_interaction(endpoint)
                self._record_recipient_interaction(pay_to)

            # Log audit entry
            entry = PaymentAuditEntry(
                timestamp=datetime.now(timezone.utc),
                wallet_address=wallet_address,
                endpoint=endpoint,
                amount=amount,
                asset=asset,
                network=network,
                pay_to=pay_to,
                decision=PaymentDecision.APPROVE if success else PaymentDecision.REJECT,
                risk_level=PaymentRiskLevel.SAFE,  # Already validated
                transaction_hash=transaction_hash,
                error=error,
            )
            self._audit_log.append(entry)

            logger.info(
                f"Payment {'succeeded' if success else 'failed'}: "
                f"${amount:.2f} to {endpoint}"
            )

    def get_spending_summary(self, wallet_address: str) -> dict[str, Any]:
        """Get spending summary for a wallet.

        Args:
            wallet_address: The wallet address

        Returns:
            Dictionary with spending statistics
        """
        with self._lock:
            records = self._spending_records.get(wallet_address, {})
            daily = records.get("daily")

            return {
                "wallet_address": wallet_address,
                "daily_spent": daily.total_spent if daily else 0.0,
                "daily_transactions": daily.transaction_count if daily else 0,
                "daily_limit": self.config.spending_limits.max_daily_total,
                "daily_remaining": (
                    self.config.spending_limits.max_daily_total - (daily.total_spent if daily else 0.0)
                ),
                "hourly_transactions": len(self._hourly_counts.get(wallet_address, [])),
                "hourly_limit": self.config.spending_limits.max_transactions_per_hour,
            }

    def get_audit_log(
        self,
        wallet_address: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get audit log entries.

        Args:
            wallet_address: Filter by wallet address (optional)
            limit: Maximum entries to return

        Returns:
            List of audit log entries as dictionaries
        """
        with self._lock:
            entries = self._audit_log
            if wallet_address:
                entries = [e for e in entries if e.wallet_address == wallet_address]
            return [e.to_dict() for e in entries[-limit:]]

    def reset_spending(self, wallet_address: str | None = None) -> None:
        """Reset spending records.

        Args:
            wallet_address: Specific wallet to reset, or None for all
        """
        with self._lock:
            if wallet_address:
                self._spending_records.pop(wallet_address, None)
                self._hourly_counts.pop(wallet_address, None)
            else:
                self._spending_records.clear()
                self._hourly_counts.clear()

    # Private helper methods

    def _build_validation_context(
        self,
        wallet_address: str,
        endpoint: str,
    ) -> dict[str, Any]:
        """Build context dictionary for validators."""
        with self._lock:
            # Get or create daily spending record
            records = self._spending_records.get(wallet_address, {})
            daily_record = records.get("daily")

            # Check if record is stale (from previous day)
            if daily_record and daily_record.period_start.date() != datetime.now(timezone.utc).date():
                daily_record = None
                records.pop("daily", None)

            # Clean up old hourly counts
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
            hourly_timestamps = self._hourly_counts.get(wallet_address, [])
            hourly_timestamps = [ts for ts in hourly_timestamps if ts > one_hour_ago]
            self._hourly_counts[wallet_address] = hourly_timestamps

            return {
                "daily_spending": daily_record,
                "hourly_transaction_count": len(hourly_timestamps),
                "endpoint_history": dict(self._endpoint_history),
                "recipient_history": dict(self._recipient_history),
            }

    def _determine_decision(
        self,
        gate_results: dict[THSPGate, THSPGateResult],
        risk_level: PaymentRiskLevel,
        payment_requirements: PaymentRequirementsModel,
    ) -> PaymentDecision:
        """Determine the payment decision based on validation results."""
        # Check for blocking conditions
        if risk_level == PaymentRiskLevel.BLOCKED:
            return PaymentDecision.BLOCK

        if risk_level == PaymentRiskLevel.CRITICAL:
            return PaymentDecision.REJECT

        # Check for confirmation requirement
        amount = payment_requirements.get_amount_float()
        thresholds = self.config.confirmation_thresholds

        needs_confirmation = (
            amount > thresholds.amount_threshold or
            risk_level == PaymentRiskLevel.HIGH or
            risk_level == PaymentRiskLevel.CAUTION
        )

        if needs_confirmation:
            # If we have a confirmation callback, use it
            if self._on_confirmation:
                return PaymentDecision.REQUIRE_CONFIRMATION
            # Otherwise, auto-approve with caution
            if risk_level in [PaymentRiskLevel.SAFE, PaymentRiskLevel.CAUTION]:
                return PaymentDecision.APPROVE
            return PaymentDecision.REQUIRE_CONFIRMATION

        return PaymentDecision.APPROVE

    def _build_result(
        self,
        decision: PaymentDecision,
        risk_level: PaymentRiskLevel,
        gate_results: dict[THSPGate, THSPGateResult],
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
    ) -> PaymentValidationResult:
        """Build the validation result object."""
        issues: list[str] = []
        recommendations: list[str] = []

        # Collect issues from failed gates
        for gate, result in gate_results.items():
            if not result.passed and result.reason:
                issues.append(f"[{gate.value.upper()}] {result.reason}")

        # Generate recommendations
        if decision == PaymentDecision.BLOCK:
            recommendations.append("Do not proceed with this payment")
            recommendations.append("Consider reporting this endpoint/address")
        elif decision == PaymentDecision.REJECT:
            recommendations.append("Review the issues and adjust payment parameters")
        elif decision == PaymentDecision.REQUIRE_CONFIRMATION:
            recommendations.append("Verify payment details before confirming")
            amount = payment_requirements.get_amount_float()
            recommendations.append(f"Payment amount: ${amount:.2f}")
        else:
            recommendations.append("Payment appears safe to proceed")

        # Determine blocked reason
        blocked_reason = None
        if decision == PaymentDecision.BLOCK:
            harm_result = gate_results.get(THSPGate.HARM)
            if harm_result and not harm_result.passed:
                blocked_reason = harm_result.reason

        return PaymentValidationResult(
            decision=decision,
            risk_level=risk_level,
            gates=gate_results,
            issues=issues,
            recommendations=recommendations,
            max_approved_amount=(
                payment_requirements.get_amount_float()
                if decision in [PaymentDecision.APPROVE, PaymentDecision.REQUIRE_CONFIRMATION]
                else None
            ),
            requires_confirmation=decision == PaymentDecision.REQUIRE_CONFIRMATION,
            blocked_reason=blocked_reason,
            metadata={
                "endpoint": endpoint,
                "amount": payment_requirements.get_amount_float(),
                "asset": payment_requirements.asset,
                "network": payment_requirements.network,
                "pay_to": payment_requirements.pay_to,
            },
        )

    def _trigger_callbacks(self, result: PaymentValidationResult) -> None:
        """Trigger appropriate callbacks based on result."""
        try:
            if result.decision == PaymentDecision.BLOCK and self._on_blocked:
                self._on_blocked(result)
            elif result.decision == PaymentDecision.APPROVE and self._on_approved:
                self._on_approved(result)
        except Exception as e:
            logger.error(f"Callback error: {e}")

    def _record_spending(
        self,
        wallet_address: str,
        amount: float,
        endpoint: str,
    ) -> None:
        """Record spending for a wallet."""
        records = self._spending_records[wallet_address]

        # Get or create daily record
        daily = records.get("daily")
        if not daily or daily.period_start.date() != datetime.now(timezone.utc).date():
            daily = SpendingRecord(
                wallet_address=wallet_address,
                period_start=datetime.now(timezone.utc),
                period_type="daily",
            )
            records["daily"] = daily

        daily.add_payment(amount, endpoint)

        # Record hourly transaction
        self._hourly_counts[wallet_address].append(datetime.now(timezone.utc))

    def _record_endpoint_interaction(self, endpoint: str) -> None:
        """Record interaction with an endpoint."""
        self._endpoint_history[endpoint].append(datetime.now(timezone.utc))

    def _record_recipient_interaction(self, recipient: str) -> None:
        """Record interaction with a recipient address."""
        if recipient is None:
            return
        recipient = recipient.lower()
        self._recipient_history[recipient].append(datetime.now(timezone.utc))

    def _log_audit(
        self,
        wallet_address: str,
        endpoint: str,
        payment_requirements: PaymentRequirementsModel,
        result: PaymentValidationResult,
    ) -> None:
        """Log an audit entry."""
        entry = PaymentAuditEntry(
            timestamp=datetime.now(timezone.utc),
            wallet_address=wallet_address,
            endpoint=endpoint,
            amount=payment_requirements.get_amount_float(),
            asset=payment_requirements.asset,
            network=payment_requirements.network,
            pay_to=payment_requirements.pay_to,
            decision=result.decision,
            risk_level=result.risk_level,
            metadata={"issues": result.issues},
        )
        self._audit_log.append(entry)


class PaymentBlockedError(Exception):
    """Raised when a payment is blocked by Sentinel."""

    def __init__(self, message: str, result: PaymentValidationResult) -> None:
        super().__init__(message)
        self.result = result


class PaymentRejectedError(Exception):
    """Raised when a payment is rejected by Sentinel."""

    def __init__(self, message: str, result: PaymentValidationResult) -> None:
        super().__init__(message)
        self.result = result


class PaymentConfirmationRequired(Exception):
    """Raised when a payment requires user confirmation."""

    def __init__(self, message: str, result: PaymentValidationResult) -> None:
        super().__init__(message)
        self.result = result


def create_sentinel_x402_middleware(
    profile: str = "standard",
    **kwargs: Any,
) -> SentinelX402Middleware:
    """Factory function to create middleware with a security profile.

    Args:
        profile: Security profile ("permissive", "standard", "strict", "paranoid")
        **kwargs: Additional arguments passed to SentinelX402Middleware

    Returns:
        Configured SentinelX402Middleware instance

    Example:
        >>> middleware = create_sentinel_x402_middleware("strict")
        >>> result = middleware.validate_payment(...)
    """
    config = get_default_config(profile)  # type: ignore
    return SentinelX402Middleware(config=config, **kwargs)
