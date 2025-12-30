"""THSP validators for x402 payment validation.

This module implements the four THSP gates (Truth, Harm, Scope, Purpose)
specifically adapted for x402 payment validation.

Each gate evaluates a different aspect of payment safety:
    - TRUTH: Is the payment request legitimate and well-formed?
    - HARM: Could this payment cause harm (malicious recipient, etc.)?
    - SCOPE: Is this payment within acceptable limits?
    - PURPOSE: Does this payment serve a legitimate purpose?
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any
from urllib.parse import urlparse

from .config import (
    KNOWN_USDC_CONTRACTS,
    KNOWN_USDT_CONTRACTS,
    SUSPICIOUS_URL_PATTERNS,
    SentinelX402Config,
)
from .types import (
    PaymentRequirementsModel,
    PaymentRiskLevel,
    SpendingRecord,
    SupportedNetwork,
    THSPGate,
    THSPGateResult,
)


class PaymentValidator(ABC):
    """Abstract base class for payment validators."""

    @property
    @abstractmethod
    def gate(self) -> THSPGate:
        """Return the THSP gate this validator implements."""
        ...

    @abstractmethod
    def validate(
        self,
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
        wallet_address: str,
        config: SentinelX402Config,
        context: dict[str, Any] | None = None,
    ) -> THSPGateResult:
        """Validate a payment against this gate.

        Args:
            payment_requirements: The x402 payment requirements
            endpoint: The endpoint URL requesting payment
            wallet_address: The wallet address making the payment
            config: Sentinel x402 configuration
            context: Additional context (spending records, history, etc.)

        Returns:
            THSPGateResult with pass/fail and reasoning
        """
        ...


class TruthGateValidator(PaymentValidator):
    """TRUTH gate: Validates payment request legitimacy and correctness.

    Checks:
        - Payment requirements are well-formed
        - Endpoint URL is valid and uses HTTPS
        - Network is supported
        - Asset contract is verified
        - Amount is valid (non-negative, parseable)
    """

    @property
    def gate(self) -> THSPGate:
        return THSPGate.TRUTH

    def validate(
        self,
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
        wallet_address: str,
        config: SentinelX402Config,
        context: dict[str, Any] | None = None,
    ) -> THSPGateResult:
        """Validate truthfulness of payment request."""
        issues: list[str] = []

        # Check endpoint URL validity
        try:
            parsed = urlparse(endpoint)
            if not parsed.scheme or not parsed.netloc:
                issues.append("Invalid endpoint URL format")
            elif config.validation.require_https and parsed.scheme != "https":
                issues.append(f"Endpoint uses {parsed.scheme} instead of HTTPS")
        except Exception:
            issues.append("Failed to parse endpoint URL")

        # Check network is supported
        try:
            network = SupportedNetwork(payment_requirements.network)
            if network not in config.allowed_networks:
                issues.append(f"Network {network.value} is not in allowed networks")
        except ValueError:
            issues.append(f"Unknown network: {payment_requirements.network}")

        # Verify asset contract address
        if config.validation.verify_contract_addresses:
            asset_addr = payment_requirements.asset.lower()
            network_str = payment_requirements.network

            try:
                network = SupportedNetwork(network_str)
                known_usdc = KNOWN_USDC_CONTRACTS.get(network, "").lower()
                known_usdt = KNOWN_USDT_CONTRACTS.get(network, "").lower()

                if asset_addr and asset_addr not in [known_usdc, known_usdt, ""]:
                    # Unknown asset contract - flag but don't fail
                    issues.append(f"Unverified asset contract: {asset_addr[:10]}...")
            except ValueError:
                pass  # Already flagged above

        # Validate amount
        try:
            amount = payment_requirements.get_amount_float()
            if amount < 0:
                issues.append("Payment amount is negative")
            elif amount == 0:
                issues.append("Payment amount is zero")
        except Exception:
            issues.append("Failed to parse payment amount")

        # Check pay_to address format
        pay_to = payment_requirements.pay_to
        if not pay_to:
            issues.append("Missing payment recipient address")
        elif not self._is_valid_address(pay_to):
            issues.append("Invalid recipient address format")

        passed = len(issues) == 0
        reason = None if passed else "; ".join(issues)

        return THSPGateResult(
            gate=THSPGate.TRUTH,
            passed=passed,
            reason=reason,
            details={"issues": issues} if issues else None,
        )

    def _is_valid_address(self, address: str) -> bool:
        """Check if address is a valid Ethereum address format."""
        if not address:
            return False
        # Basic Ethereum address validation
        return bool(re.match(r"^0x[a-fA-F0-9]{40}$", address))


class HarmGateValidator(PaymentValidator):
    """HARM gate: Validates payment won't cause harm.

    Checks:
        - Recipient is not on blocklist
        - Endpoint is not malicious
        - No suspicious patterns in URL
        - Contract is not flagged as malicious
    """

    @property
    def gate(self) -> THSPGate:
        return THSPGate.HARM

    def validate(
        self,
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
        wallet_address: str,
        config: SentinelX402Config,
        context: dict[str, Any] | None = None,
    ) -> THSPGateResult:
        """Validate payment won't cause harm."""
        issues: list[str] = []
        risk_factors: list[str] = []

        # Check recipient against blocklist
        pay_to = payment_requirements.pay_to.lower()
        blocked_addresses = [addr.lower() for addr in config.blocked_addresses]

        if pay_to in blocked_addresses:
            issues.append(f"Recipient address is blocked: {pay_to[:10]}...")

        # Check endpoint against blocklist
        for blocked in config.blocked_endpoints:
            if blocked.lower() in endpoint.lower():
                issues.append(f"Endpoint matches blocklist pattern: {blocked}")

        # Check for suspicious URL patterns
        for pattern in SUSPICIOUS_URL_PATTERNS:
            if re.search(pattern, endpoint, re.IGNORECASE):
                risk_factors.append(f"URL matches suspicious pattern")
                break

        # Check if endpoint uses IP address directly
        try:
            parsed = urlparse(endpoint)
            netloc = parsed.netloc.split(":")[0]  # Remove port
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", netloc):
                risk_factors.append("Endpoint uses direct IP address instead of domain")
        except Exception:
            pass

        # If context includes known malicious data, check it
        if context:
            known_scams = context.get("known_scam_addresses", [])
            if pay_to in [addr.lower() for addr in known_scams]:
                issues.append("Recipient identified as known scam address")

        passed = len(issues) == 0
        reason = None if passed else "; ".join(issues)

        return THSPGateResult(
            gate=THSPGate.HARM,
            passed=passed,
            reason=reason,
            details={
                "issues": issues,
                "risk_factors": risk_factors,
            } if issues or risk_factors else None,
        )


class ScopeGateValidator(PaymentValidator):
    """SCOPE gate: Validates payment is within acceptable limits.

    Checks:
        - Amount within single payment limit
        - Amount within daily/weekly/monthly limits
        - Transaction count within rate limits
        - Not exceeding spending velocity limits
    """

    @property
    def gate(self) -> THSPGate:
        return THSPGate.SCOPE

    def validate(
        self,
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
        wallet_address: str,
        config: SentinelX402Config,
        context: dict[str, Any] | None = None,
    ) -> THSPGateResult:
        """Validate payment is within scope limits."""
        issues: list[str] = []
        warnings: list[str] = []

        if not config.validation.enable_spending_limits:
            return THSPGateResult(
                gate=THSPGate.SCOPE,
                passed=True,
                reason=None,
                details={"note": "Spending limits disabled"},
            )

        amount = payment_requirements.get_amount_float()
        limits = config.spending_limits

        # Check single payment limit
        if amount > limits.max_single_payment:
            issues.append(
                f"Amount ${amount:.2f} exceeds single payment limit ${limits.max_single_payment:.2f}"
            )

        # Check spending records from context
        if context and config.validation.enable_spending_limits:
            daily_record: SpendingRecord | None = context.get("daily_spending")
            hourly_count: int = context.get("hourly_transaction_count", 0)

            if daily_record:
                # Check daily total
                projected_daily = daily_record.total_spent + amount
                if projected_daily > limits.max_daily_total:
                    issues.append(
                        f"Payment would exceed daily limit: "
                        f"${projected_daily:.2f} > ${limits.max_daily_total:.2f}"
                    )

                # Check daily transaction count
                if daily_record.transaction_count >= limits.max_transactions_per_day:
                    issues.append(
                        f"Daily transaction limit reached: {daily_record.transaction_count}"
                    )
                elif daily_record.transaction_count >= limits.max_transactions_per_day * 0.8:
                    warnings.append("Approaching daily transaction limit")

            # Check hourly rate limit
            if config.validation.enable_rate_limiting:
                if hourly_count >= limits.max_transactions_per_hour:
                    issues.append(
                        f"Hourly rate limit exceeded: {hourly_count} transactions"
                    )
                elif hourly_count >= limits.max_transactions_per_hour * 0.8:
                    warnings.append("Approaching hourly rate limit")

        passed = len(issues) == 0
        reason = None if passed else "; ".join(issues)

        return THSPGateResult(
            gate=THSPGate.SCOPE,
            passed=passed,
            reason=reason,
            details={
                "amount": amount,
                "issues": issues,
                "warnings": warnings,
                "limits": {
                    "max_single": limits.max_single_payment,
                    "max_daily": limits.max_daily_total,
                },
            },
        )


class PurposeGateValidator(PaymentValidator):
    """PURPOSE gate: Validates payment serves legitimate purpose.

    Checks:
        - Endpoint has been seen before (trust)
        - Recipient has received payments before (familiarity)
        - Payment description makes sense
        - Resource being purchased is appropriate
    """

    @property
    def gate(self) -> THSPGate:
        return THSPGate.PURPOSE

    def validate(
        self,
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
        wallet_address: str,
        config: SentinelX402Config,
        context: dict[str, Any] | None = None,
    ) -> THSPGateResult:
        """Validate payment serves legitimate purpose."""
        concerns: list[str] = []
        flags: list[str] = []

        # Check if endpoint is known/trusted
        is_known_endpoint = False
        if context:
            endpoint_history = context.get("endpoint_history", {})
            is_known_endpoint = endpoint in endpoint_history
            if not is_known_endpoint and not config.validation.allow_unknown_endpoints:
                concerns.append("Payment to unknown/unverified endpoint")

            # Check if recipient is familiar
            recipient_history = context.get("recipient_history", {})
            pay_to = payment_requirements.pay_to.lower()
            is_known_recipient = pay_to in recipient_history

            if not is_known_recipient and not config.validation.allow_unknown_recipients:
                concerns.append("Payment to unknown recipient address")
            elif not is_known_recipient:
                flags.append("First payment to this recipient")

        # Check payment description for red flags
        description = payment_requirements.description.lower()
        suspicious_terms = [
            "urgent", "immediate", "secret", "private key",
            "password", "seed phrase", "recovery",
        ]
        for term in suspicious_terms:
            if term in description:
                concerns.append(f"Suspicious term in description: '{term}'")

        # Check resource makes sense
        resource = payment_requirements.resource
        if not resource:
            flags.append("No resource specified for payment")

        # In strict mode, any flags become concerns
        if config.validation.strict_mode:
            concerns.extend(flags)
            flags = []

        passed = len(concerns) == 0
        reason = None if passed else "; ".join(concerns)

        return THSPGateResult(
            gate=THSPGate.PURPOSE,
            passed=passed,
            reason=reason,
            details={
                "concerns": concerns,
                "flags": flags,
                "is_known_endpoint": is_known_endpoint if context else None,
            },
        )


class THSPPaymentValidator:
    """Main validator orchestrating all THSP gates for payment validation.

    This class combines all four gates and provides the main validation
    entry point for the x402 middleware.

    Example:
        >>> validator = THSPPaymentValidator()
        >>> result = validator.validate_payment(
        ...     payment_requirements=payment_req,
        ...     endpoint="https://api.example.com/data",
        ...     wallet_address="0x123...",
        ...     config=config,
        ... )
        >>> if result.all_gates_passed:
        ...     print("Payment approved")
    """

    def __init__(self) -> None:
        """Initialize with all THSP gate validators."""
        self._validators: list[PaymentValidator] = [
            TruthGateValidator(),
            HarmGateValidator(),
            ScopeGateValidator(),
            PurposeGateValidator(),
        ]

    def validate_payment(
        self,
        payment_requirements: PaymentRequirementsModel,
        endpoint: str,
        wallet_address: str,
        config: SentinelX402Config,
        context: dict[str, Any] | None = None,
    ) -> dict[THSPGate, THSPGateResult]:
        """Run all THSP gates on a payment request.

        Args:
            payment_requirements: The x402 payment requirements
            endpoint: The endpoint URL requesting payment
            wallet_address: The wallet address making the payment
            config: Sentinel x402 configuration
            context: Additional context (spending records, history, etc.)

        Returns:
            Dictionary mapping each gate to its result
        """
        results: dict[THSPGate, THSPGateResult] = {}

        for validator in self._validators:
            try:
                result = validator.validate(
                    payment_requirements=payment_requirements,
                    endpoint=endpoint,
                    wallet_address=wallet_address,
                    config=config,
                    context=context,
                )
                results[validator.gate] = result
            except Exception as e:
                # If a validator fails, mark that gate as failed
                results[validator.gate] = THSPGateResult(
                    gate=validator.gate,
                    passed=False,
                    reason=f"Validator error: {e!s}",
                )

        return results

    def calculate_risk_level(
        self,
        gate_results: dict[THSPGate, THSPGateResult],
        payment_requirements: PaymentRequirementsModel,
        config: SentinelX402Config,
    ) -> PaymentRiskLevel:
        """Calculate overall risk level from gate results.

        Risk levels:
            - BLOCKED: Any critical failure (HARM gate failed)
            - CRITICAL: Multiple gates failed
            - HIGH: One gate failed (not HARM)
            - CAUTION: All gates passed but with warnings
            - SAFE: All gates passed cleanly

        Args:
            gate_results: Results from all THSP gates
            payment_requirements: The payment requirements
            config: Sentinel x402 configuration

        Returns:
            Calculated PaymentRiskLevel
        """
        failed_gates = [gate for gate, result in gate_results.items() if not result.passed]

        # HARM gate failure is always BLOCKED
        if THSPGate.HARM in failed_gates:
            return PaymentRiskLevel.BLOCKED

        # Multiple failures is CRITICAL
        if len(failed_gates) >= 2:
            return PaymentRiskLevel.CRITICAL

        # Single failure is HIGH
        if len(failed_gates) == 1:
            return PaymentRiskLevel.HIGH

        # Check for warnings/flags even when passed
        has_warnings = any(
            result.details and (
                result.details.get("warnings") or
                result.details.get("flags") or
                result.details.get("risk_factors")
            )
            for result in gate_results.values()
        )

        # Check amount against confirmation threshold
        amount = payment_requirements.get_amount_float()
        if amount > config.confirmation_thresholds.amount_threshold:
            return PaymentRiskLevel.CAUTION

        if has_warnings:
            return PaymentRiskLevel.CAUTION

        return PaymentRiskLevel.SAFE
