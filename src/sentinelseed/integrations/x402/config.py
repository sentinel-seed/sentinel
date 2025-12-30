"""Configuration and constants for Sentinel x402 integration.

This module contains default configurations, blocklists, and constants
for the x402 payment validation middleware.

Security Note:
    Blocklists should be regularly updated from trusted sources.
    Consider integrating with external threat intelligence feeds.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from .types import SupportedNetwork


@dataclass
class SpendingLimits:
    """Spending limits configuration.

    Attributes:
        max_single_payment: Maximum amount for a single payment (USD)
        max_daily_total: Maximum total daily spending (USD)
        max_weekly_total: Maximum total weekly spending (USD)
        max_monthly_total: Maximum total monthly spending (USD)
        max_transactions_per_day: Maximum number of transactions per day
        max_transactions_per_hour: Maximum transactions per hour (rate limiting)
    """

    max_single_payment: float = 100.0
    max_daily_total: float = 500.0
    max_weekly_total: float = 2000.0
    max_monthly_total: float = 5000.0
    max_transactions_per_day: int = 50
    max_transactions_per_hour: int = 10


@dataclass
class ConfirmationThresholds:
    """Thresholds for requiring user confirmation.

    Attributes:
        amount_threshold: Payments above this amount require confirmation (USD)
        unknown_endpoint_threshold: Lower threshold for unknown endpoints (USD)
        new_recipient_threshold: Lower threshold for first-time recipients (USD)
        high_risk_threshold: Lower threshold for high-risk payments (USD)
    """

    amount_threshold: float = 10.0
    unknown_endpoint_threshold: float = 5.0
    new_recipient_threshold: float = 5.0
    high_risk_threshold: float = 1.0


@dataclass
class ValidationConfig:
    """Configuration for payment validation behavior.

    Attributes:
        strict_mode: Enable stricter validation rules
        allow_unknown_endpoints: Allow payments to unverified endpoints
        allow_unknown_recipients: Allow payments to new recipient addresses
        require_https: Require HTTPS for endpoint URLs
        verify_contract_addresses: Verify asset contract addresses
        check_endpoint_reputation: Query endpoint reputation service
        enable_spending_limits: Enable spending limit enforcement
        enable_rate_limiting: Enable transaction rate limiting
        audit_all_payments: Log all payment attempts for audit
    """

    strict_mode: bool = False
    allow_unknown_endpoints: bool = True
    allow_unknown_recipients: bool = True
    require_https: bool = True
    verify_contract_addresses: bool = True
    check_endpoint_reputation: bool = False
    enable_spending_limits: bool = True
    enable_rate_limiting: bool = True
    audit_all_payments: bool = True


@dataclass
class SentinelX402Config:
    """Complete configuration for Sentinel x402 middleware.

    Example:
        >>> config = SentinelX402Config(
        ...     spending_limits=SpendingLimits(max_single_payment=50.0),
        ...     validation=ValidationConfig(strict_mode=True),
        ... )
    """

    spending_limits: SpendingLimits = field(default_factory=SpendingLimits)
    confirmation_thresholds: ConfirmationThresholds = field(default_factory=ConfirmationThresholds)
    validation: ValidationConfig = field(default_factory=ValidationConfig)
    blocked_endpoints: list[str] = field(default_factory=list)
    blocked_addresses: list[str] = field(default_factory=list)
    allowed_networks: list[SupportedNetwork] = field(
        default_factory=lambda: list(SupportedNetwork)
    )
    allowed_assets: list[str] = field(default_factory=lambda: ["USDC", "USDT", "DAI"])

    def __post_init__(self) -> None:
        """Initialize with default blocklists if empty."""
        if not self.blocked_addresses:
            self.blocked_addresses = list(DEFAULT_BLOCKED_ADDRESSES)


# Known malicious addresses (curated blocklist)
# Sources: Internal research, community reports, blockchain analytics
DEFAULT_BLOCKED_ADDRESSES: set[str] = {
    # Placeholder - in production, integrate with threat intelligence feeds
    # "0x000000000000000000000000000000000000dead",
}

# Known malicious or suspicious endpoints
DEFAULT_BLOCKED_ENDPOINTS: set[str] = {
    # Placeholder - in production, maintain curated blocklist
}

# Suspicious patterns in endpoint URLs
SUSPICIOUS_URL_PATTERNS: list[str] = [
    r".*phishing.*",
    r".*scam.*",
    r".*hack.*",
    r".*malware.*",
    r".*\.ru/",  # High-risk TLD (use with caution)
    r".*\.cn/",  # High-risk TLD (use with caution)
    r".*bit\.ly/.*",  # URL shorteners can hide malicious destinations
    r".*tinyurl\.com/.*",
    r".*\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}.*",  # Direct IP addresses
]

# Known legitimate USDC contract addresses by network
KNOWN_USDC_CONTRACTS: dict[SupportedNetwork, str] = {
    SupportedNetwork.BASE: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    SupportedNetwork.BASE_SEPOLIA: "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
    SupportedNetwork.AVALANCHE: "0xB97EF9Ef8734C71904D8002F8b6Bc66Dd9c48a6E",
    SupportedNetwork.AVALANCHE_FUJI: "0x5425890298aed601595a70AB815c96711a31Bc65",
}

# Known legitimate USDT contract addresses by network
KNOWN_USDT_CONTRACTS: dict[SupportedNetwork, str] = {
    SupportedNetwork.BASE: "0xfde4C96c8593536E31F229EA8f37b2ADa2699bb2",
    SupportedNetwork.AVALANCHE: "0x9702230A8Ea53601f5cD2dc00fDBc13d4dF4A8c7",
}

# Facilitator endpoints (official x402 facilitators)
KNOWN_FACILITATORS: dict[str, str] = {
    "coinbase": "https://x402.org/facilitator",
    "coinbase_testnet": "https://x402.org/facilitator",
}

# Risk weights for different payment attributes
PAYMENT_RISK_WEIGHTS: dict[str, float] = {
    "high_amount": 0.3,
    "unknown_endpoint": 0.2,
    "unknown_recipient": 0.2,
    "new_network": 0.1,
    "rate_limit_warning": 0.15,
    "suspicious_pattern": 0.4,
    "unverified_contract": 0.25,
}

# Stablecoin decimal places (for amount conversion)
TOKEN_DECIMALS: dict[str, int] = {
    "USDC": 6,
    "USDT": 6,
    "DAI": 18,
}


def get_default_config(
    profile: Literal["permissive", "standard", "strict", "paranoid"] = "standard",
) -> SentinelX402Config:
    """Get a pre-configured config based on security profile.

    Args:
        profile: Security profile to use:
            - permissive: Minimal restrictions, for testing
            - standard: Balanced security and usability
            - strict: Higher security, more confirmations required
            - paranoid: Maximum security, blocks most automated payments

    Returns:
        SentinelX402Config with appropriate settings.

    Example:
        >>> config = get_default_config("strict")
        >>> config.spending_limits.max_single_payment
        25.0
    """
    if profile == "permissive":
        return SentinelX402Config(
            spending_limits=SpendingLimits(
                max_single_payment=1000.0,
                max_daily_total=5000.0,
            ),
            confirmation_thresholds=ConfirmationThresholds(
                amount_threshold=100.0,
            ),
            validation=ValidationConfig(
                strict_mode=False,
                allow_unknown_endpoints=True,
                allow_unknown_recipients=True,
                enable_spending_limits=False,
            ),
        )
    elif profile == "standard":
        return SentinelX402Config()  # Default values
    elif profile == "strict":
        return SentinelX402Config(
            spending_limits=SpendingLimits(
                max_single_payment=25.0,
                max_daily_total=100.0,
            ),
            confirmation_thresholds=ConfirmationThresholds(
                amount_threshold=5.0,
                unknown_endpoint_threshold=1.0,
            ),
            validation=ValidationConfig(
                strict_mode=True,
                allow_unknown_endpoints=False,
                require_https=True,
            ),
        )
    elif profile == "paranoid":
        return SentinelX402Config(
            spending_limits=SpendingLimits(
                max_single_payment=10.0,
                max_daily_total=50.0,
                max_transactions_per_day=10,
                max_transactions_per_hour=3,
            ),
            confirmation_thresholds=ConfirmationThresholds(
                amount_threshold=1.0,
                unknown_endpoint_threshold=0.5,
                new_recipient_threshold=0.5,
                high_risk_threshold=0.1,
            ),
            validation=ValidationConfig(
                strict_mode=True,
                allow_unknown_endpoints=False,
                allow_unknown_recipients=False,
                check_endpoint_reputation=True,
            ),
        )
    else:
        raise ValueError(f"Unknown profile: {profile}")
