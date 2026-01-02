"""Type definitions for Sentinel x402 integration.

This module defines all types used in the x402 payment validation layer,
following the x402 protocol specification and Sentinel THSP framework.

References:
    - x402 Protocol: https://github.com/coinbase/x402
    - x402 Types: https://github.com/coinbase/x402/blob/main/python/x402/src/x402/types.py
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

# Import THSPGate from validators (canonical source)
from sentinelseed.validators.semantic import THSPGate


class PaymentRiskLevel(str, Enum):
    """Risk levels for x402 payment validation.

    Levels are ordered by severity:
        SAFE < CAUTION < HIGH < CRITICAL < BLOCKED
    """

    SAFE = "safe"
    CAUTION = "caution"
    HIGH = "high"
    CRITICAL = "critical"
    BLOCKED = "blocked"

    def __lt__(self, other: "PaymentRiskLevel") -> bool:
        """Enable comparison between risk levels."""
        order = [self.SAFE, self.CAUTION, self.HIGH, self.CRITICAL, self.BLOCKED]
        return order.index(self) < order.index(other)


class PaymentDecision(str, Enum):
    """Decision outcome for payment validation."""

    APPROVE = "approve"
    REQUIRE_CONFIRMATION = "require_confirmation"
    REJECT = "reject"
    BLOCK = "block"


# THSPGate is imported from sentinelseed.validators.semantic (canonical source)


class SupportedNetwork(str, Enum):
    """Supported blockchain networks for x402 payments.

    Based on x402 SDK supported networks.
    """

    BASE = "base"
    BASE_SEPOLIA = "base-sepolia"
    AVALANCHE = "avalanche"
    AVALANCHE_FUJI = "avalanche-fuji"


# Network to chain ID mapping (from x402 SDK)
NETWORK_CHAIN_IDS: dict[SupportedNetwork, int] = {
    SupportedNetwork.BASE_SEPOLIA: 84532,
    SupportedNetwork.BASE: 8453,
    SupportedNetwork.AVALANCHE_FUJI: 43113,
    SupportedNetwork.AVALANCHE: 43114,
}


@dataclass
class THSPGateResult:
    """Result of a single THSP gate evaluation."""

    gate: THSPGate
    passed: bool
    reason: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class PaymentValidationResult:
    """Complete result of validating an x402 payment request.

    Attributes:
        decision: The validation decision (approve, reject, etc.)
        risk_level: Assessed risk level of the payment
        gates: Results from each THSP gate
        issues: List of detected issues
        recommendations: Suggested actions for the user/agent
        max_approved_amount: Maximum amount approved (if any)
        requires_confirmation: Whether user confirmation is needed
        blocked_reason: Reason for blocking (if blocked)
        metadata: Additional validation metadata
    """

    decision: PaymentDecision
    risk_level: PaymentRiskLevel
    gates: dict[THSPGate, THSPGateResult]
    issues: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)
    max_approved_amount: float | None = None
    requires_confirmation: bool = False
    blocked_reason: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        """Check if payment is approved (with or without confirmation)."""
        return self.decision in [PaymentDecision.APPROVE, PaymentDecision.REQUIRE_CONFIRMATION]

    @property
    def all_gates_passed(self) -> bool:
        """Check if all THSP gates passed."""
        return all(gate.passed for gate in self.gates.values())

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "decision": self.decision.value,
            "risk_level": self.risk_level.value,
            "gates": {
                gate.value: {
                    "passed": result.passed,
                    "reason": result.reason,
                }
                for gate, result in self.gates.items()
            },
            "issues": self.issues,
            "recommendations": self.recommendations,
            "max_approved_amount": self.max_approved_amount,
            "requires_confirmation": self.requires_confirmation,
            "blocked_reason": self.blocked_reason,
            "metadata": self.metadata,
        }


@dataclass
class PaymentAuditEntry:
    """Audit log entry for a payment event.

    Used for tracking and compliance purposes.
    """

    timestamp: datetime
    wallet_address: str
    endpoint: str
    amount: float
    asset: str
    network: SupportedNetwork | str
    pay_to: str
    decision: PaymentDecision
    risk_level: PaymentRiskLevel
    transaction_hash: str | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "wallet_address": self.wallet_address,
            "endpoint": self.endpoint,
            "amount": self.amount,
            "asset": self.asset,
            "network": self.network if isinstance(self.network, str) else self.network.value,
            "pay_to": self.pay_to,
            "decision": self.decision.value,
            "risk_level": self.risk_level.value,
            "transaction_hash": self.transaction_hash,
            "error": self.error,
            "metadata": self.metadata,
        }


class PaymentRequirementsModel(BaseModel):
    """Pydantic model for x402 payment requirements.

    Matches the x402 SDK PaymentRequirements type.
    """

    scheme: str
    network: str
    max_amount_required: str
    resource: str
    description: str = ""
    mime_type: str = ""
    output_schema: Any | None = None
    pay_to: str
    max_timeout_seconds: int
    asset: str
    extra: dict[str, Any] | None = None

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )

    def get_amount_float(self) -> float:
        """Get max_amount_required as float.

        Handles conversion from atomic units based on typical stablecoin decimals (6).
        """
        try:
            atomic_amount = int(self.max_amount_required)
            # USDC and most stablecoins use 6 decimals
            return atomic_amount / 1_000_000
        except (ValueError, TypeError):
            return 0.0


class EndpointReputation(BaseModel):
    """Reputation data for an x402-protected endpoint."""

    endpoint: str
    trust_score: float = Field(ge=0.0, le=1.0, default=0.5)
    total_payments: int = 0
    successful_payments: int = 0
    failed_payments: int = 0
    avg_payment_amount: float = 0.0
    last_seen: datetime | None = None
    flags: list[str] = Field(default_factory=list)
    verified: bool = False

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    @property
    def success_rate(self) -> float:
        """Calculate payment success rate."""
        if self.total_payments == 0:
            return 0.0
        return self.successful_payments / self.total_payments


class SpendingRecord(BaseModel):
    """Track spending for rate limiting and budget enforcement."""

    wallet_address: str
    period_start: datetime
    period_type: Literal["daily", "weekly", "monthly"]
    total_spent: float = 0.0
    transaction_count: int = 0
    payments: list[dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    def add_payment(self, amount: float, endpoint: str, tx_hash: str | None = None) -> None:
        """Record a payment."""
        self.total_spent += amount
        self.transaction_count += 1
        self.payments.append({
            "amount": amount,
            "endpoint": endpoint,
            "tx_hash": tx_hash,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
