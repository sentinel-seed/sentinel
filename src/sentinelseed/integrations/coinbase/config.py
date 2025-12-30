"""
Coinbase Integration Configuration.

Centralized configuration for Sentinel's Coinbase ecosystem integration,
including AgentKit guardrails and x402 payment validation.

This module provides:
- Chain-specific configurations (EVM networks)
- Security profiles with spending limits
- Action whitelists/blacklists
- DeFi risk parameters

Based on patterns from:
- Coinbase AgentKit: https://github.com/coinbase/agentkit
- Alchemy AI Agents: https://www.alchemy.com/ai-agents
- Enkrypt AI Guardrails: https://www.enkryptai.com
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, FrozenSet, List, Optional, Set


class ChainType(Enum):
    """Supported blockchain network types."""

    # EVM Networks
    ETHEREUM_MAINNET = "ethereum-mainnet"
    ETHEREUM_SEPOLIA = "ethereum-sepolia"
    BASE_MAINNET = "base-mainnet"
    BASE_SEPOLIA = "base-sepolia"
    POLYGON_MAINNET = "polygon-mainnet"
    POLYGON_AMOY = "polygon-amoy"
    ARBITRUM_MAINNET = "arbitrum-mainnet"
    ARBITRUM_SEPOLIA = "arbitrum-sepolia"
    OPTIMISM_MAINNET = "optimism-mainnet"
    OPTIMISM_SEPOLIA = "optimism-sepolia"
    AVALANCHE_MAINNET = "avalanche-mainnet"
    AVALANCHE_FUJI = "avalanche-fuji"

    # SVM Networks
    SOLANA_MAINNET = "solana-mainnet"
    SOLANA_DEVNET = "solana-devnet"

    @property
    def is_testnet(self) -> bool:
        """Check if this is a testnet."""
        testnet_keywords = ("sepolia", "amoy", "fuji", "devnet")
        return any(kw in self.value for kw in testnet_keywords)

    @property
    def is_evm(self) -> bool:
        """Check if this is an EVM-compatible network."""
        return self.value not in ("solana-mainnet", "solana-devnet")

    @property
    def native_token(self) -> str:
        """Get the native token symbol for this chain."""
        token_map = {
            "ethereum": "ETH",
            "base": "ETH",
            "polygon": "MATIC",
            "arbitrum": "ETH",
            "optimism": "ETH",
            "avalanche": "AVAX",
            "solana": "SOL",
        }
        for prefix, token in token_map.items():
            if self.value.startswith(prefix):
                return token
        return "ETH"


class SecurityProfile(Enum):
    """Pre-configured security profiles."""

    PERMISSIVE = "permissive"  # High limits, minimal restrictions
    STANDARD = "standard"      # Balanced security (recommended)
    STRICT = "strict"          # Low limits, more restrictions
    PARANOID = "paranoid"      # Minimal limits, maximum restrictions


class RiskLevel(Enum):
    """Risk levels for actions and transactions."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    def __lt__(self, other: "RiskLevel") -> bool:
        order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
        return order.index(self) < order.index(other)

    def __le__(self, other: "RiskLevel") -> bool:
        return self == other or self < other


@dataclass(frozen=True)
class SpendingLimits:
    """
    Spending limits configuration.

    All amounts are in USD equivalent for consistency across chains.
    """

    max_single_transaction: float = 100.0
    max_daily_total: float = 500.0
    max_hourly_total: float = 200.0
    max_transactions_per_hour: int = 10
    max_transactions_per_day: int = 50
    confirmation_threshold: float = 25.0  # Require confirmation above this

    def exceeds_single(self, amount: float) -> bool:
        """Check if amount exceeds single transaction limit."""
        return amount > self.max_single_transaction

    def requires_confirmation(self, amount: float) -> bool:
        """Check if amount requires human confirmation."""
        return amount > self.confirmation_threshold


@dataclass(frozen=True)
class ChainConfig:
    """
    Chain-specific configuration.

    Different chains may have different security requirements.
    Testnets are more permissive by default.
    """

    chain_type: ChainType
    spending_limits: SpendingLimits
    blocked_contracts: FrozenSet[str] = field(default_factory=frozenset)
    allowed_contracts: FrozenSet[str] = field(default_factory=frozenset)  # Empty = all allowed
    max_gas_price_gwei: Optional[float] = None  # None = no limit
    require_verified_contracts: bool = False

    @classmethod
    def for_testnet(cls, chain_type: ChainType) -> "ChainConfig":
        """Create permissive config for testnet."""
        return cls(
            chain_type=chain_type,
            spending_limits=SpendingLimits(
                max_single_transaction=10000.0,  # High for testing
                max_daily_total=50000.0,
                max_hourly_total=20000.0,
                max_transactions_per_hour=100,
                max_transactions_per_day=500,
                confirmation_threshold=1000.0,
            ),
            require_verified_contracts=False,
        )

    @classmethod
    def for_mainnet(cls, chain_type: ChainType, profile: SecurityProfile) -> "ChainConfig":
        """Create config for mainnet based on security profile."""
        limits_map = {
            SecurityProfile.PERMISSIVE: SpendingLimits(
                max_single_transaction=1000.0,
                max_daily_total=5000.0,
                max_hourly_total=2000.0,
                max_transactions_per_hour=50,
                max_transactions_per_day=200,
                confirmation_threshold=100.0,
            ),
            SecurityProfile.STANDARD: SpendingLimits(
                max_single_transaction=100.0,
                max_daily_total=500.0,
                max_hourly_total=200.0,
                max_transactions_per_hour=10,
                max_transactions_per_day=50,
                confirmation_threshold=25.0,
            ),
            SecurityProfile.STRICT: SpendingLimits(
                max_single_transaction=25.0,
                max_daily_total=100.0,
                max_hourly_total=50.0,
                max_transactions_per_hour=5,
                max_transactions_per_day=20,
                confirmation_threshold=10.0,
            ),
            SecurityProfile.PARANOID: SpendingLimits(
                max_single_transaction=10.0,
                max_daily_total=50.0,
                max_hourly_total=25.0,
                max_transactions_per_hour=3,
                max_transactions_per_day=10,
                confirmation_threshold=5.0,
            ),
        }

        return cls(
            chain_type=chain_type,
            spending_limits=limits_map[profile],
            require_verified_contracts=profile in (SecurityProfile.STRICT, SecurityProfile.PARANOID),
        )


# High-risk AgentKit actions that require extra validation
HIGH_RISK_ACTIONS: FrozenSet[str] = frozenset([
    # Wallet actions
    "native_transfer",

    # ERC20 actions
    "transfer",
    "approve",

    # ERC721 actions
    "transfer",  # NFT transfer

    # CDP Wallet actions
    "deploy_contract",
    "deploy_token",
    "trade",

    # DeFi actions - Compound
    "supply",
    "withdraw",
    "borrow",
    "repay",

    # DeFi actions - Morpho
    "deposit",
    "withdraw",

    # DeFi actions - Aave
    "supply",
    "withdraw",
    "borrow",

    # Superfluid
    "create_flow",

    # WOW actions
    "buy_token",
    "sell_token",
    "create_token",

    # WETH
    "wrap_eth",

    # SSH (extremely high risk)
    "ssh_connect",
    "remote_shell",
    "sftp_upload",
])

# Read-only actions that are always safe
SAFE_ACTIONS: FrozenSet[str] = frozenset([
    # Wallet
    "get_wallet_details",
    "get_balance",

    # ERC20/ERC721
    "get_balance",

    # CDP API
    "fetch_price",
    "fetch_base_scan",

    # Pyth
    "fetch_price",
    "fetch_price_feed_id",

    # Compound
    "get_portfolio",

    # Superfluid
    "get_flow",

    # Twitter (read-only)
    "account_details",
    "account_mentions",

    # Basename
    "register_basename",  # Low risk, just domain registration

    # SSH (read-only)
    "ssh_status",
    "ssh_list_connections",
])

# Actions that should always be blocked
BLOCKED_ACTIONS: FrozenSet[str] = frozenset([
    # These are dangerous patterns, not actual AgentKit actions
    "drain_wallet",
    "transfer_all",
    "approve_unlimited",
    "export_private_key",
    "reveal_seed_phrase",
])

# Known malicious contract addresses (EVM)
# This is a starter list - should be expanded with real threat intel
KNOWN_MALICIOUS_ADDRESSES: FrozenSet[str] = frozenset([
    # Placeholder - add real malicious addresses from threat intel feeds
    "0x0000000000000000000000000000000000000000",  # Null address (burn)
])

# DeFi protocols with their risk levels
DEFI_PROTOCOL_RISK: Dict[str, RiskLevel] = {
    # Established protocols - lower risk
    "compound": RiskLevel.MEDIUM,
    "aave": RiskLevel.MEDIUM,
    "uniswap": RiskLevel.MEDIUM,

    # Newer protocols - higher risk
    "morpho": RiskLevel.HIGH,
    "superfluid": RiskLevel.HIGH,
    "wow": RiskLevel.HIGH,
}


@dataclass
class SentinelCoinbaseConfig:
    """
    Main configuration for Sentinel's Coinbase integration.

    This is the central configuration object that controls all
    security behavior for AgentKit and x402 integrations.

    Example:
        from sentinelseed.integrations.coinbase import SentinelCoinbaseConfig

        # Use default standard profile
        config = SentinelCoinbaseConfig()

        # Or customize
        config = SentinelCoinbaseConfig(
            security_profile=SecurityProfile.STRICT,
            blocked_addresses={"0xbad..."},
            require_purpose_for_transfers=True,
        )
    """

    # Security profile (affects all limits)
    security_profile: SecurityProfile = SecurityProfile.STANDARD

    # Chain configurations (auto-generated if not provided)
    chain_configs: Dict[ChainType, ChainConfig] = field(default_factory=dict)

    # Global blocked addresses (applied to all chains)
    blocked_addresses: Set[str] = field(default_factory=set)

    # Action controls
    blocked_actions: Set[str] = field(default_factory=lambda: set(BLOCKED_ACTIONS))
    allowed_actions: Set[str] = field(default_factory=set)  # Empty = all allowed

    # Behavior settings
    require_purpose_for_transfers: bool = True
    require_confirmation_for_high_value: bool = True
    block_unlimited_approvals: bool = True
    strict_address_validation: bool = True

    # Logging and audit
    log_all_validations: bool = True
    store_validation_history: bool = True
    max_history_size: int = 1000

    # x402 specific
    enable_x402_validation: bool = True
    x402_auto_confirm_below: float = 1.0  # Auto-confirm payments below $1

    def __post_init__(self) -> None:
        """Initialize chain configs if not provided."""
        if not self.chain_configs:
            self._init_default_chain_configs()

        # Add known malicious addresses
        self.blocked_addresses.update(KNOWN_MALICIOUS_ADDRESSES)

    def _init_default_chain_configs(self) -> None:
        """Initialize default chain configurations based on security profile."""
        for chain_type in ChainType:
            if chain_type.is_testnet:
                self.chain_configs[chain_type] = ChainConfig.for_testnet(chain_type)
            else:
                self.chain_configs[chain_type] = ChainConfig.for_mainnet(
                    chain_type, self.security_profile
                )

    def get_chain_config(self, chain: ChainType) -> ChainConfig:
        """Get configuration for a specific chain."""
        if chain not in self.chain_configs:
            # Create on-demand if not exists
            if chain.is_testnet:
                self.chain_configs[chain] = ChainConfig.for_testnet(chain)
            else:
                self.chain_configs[chain] = ChainConfig.for_mainnet(
                    chain, self.security_profile
                )
        return self.chain_configs[chain]

    def is_action_allowed(self, action: str) -> bool:
        """Check if an action is allowed."""
        action_lower = action.lower()

        # Check blocked first
        if action_lower in self.blocked_actions:
            return False

        # If whitelist is set, action must be in it
        if self.allowed_actions:
            return action_lower in self.allowed_actions

        return True

    def is_high_risk_action(self, action: str) -> bool:
        """Check if an action is considered high risk."""
        return action.lower() in HIGH_RISK_ACTIONS

    def is_safe_action(self, action: str) -> bool:
        """Check if an action is read-only/safe."""
        return action.lower() in SAFE_ACTIONS

    def is_address_blocked(self, address: str) -> bool:
        """Check if an address is blocked."""
        return address.lower() in {a.lower() for a in self.blocked_addresses}


def get_default_config(profile: str = "standard") -> SentinelCoinbaseConfig:
    """
    Get a default configuration for a security profile.

    Args:
        profile: One of "permissive", "standard", "strict", "paranoid"

    Returns:
        SentinelCoinbaseConfig with appropriate settings

    Example:
        config = get_default_config("strict")
    """
    profile_enum = SecurityProfile(profile.lower())
    return SentinelCoinbaseConfig(security_profile=profile_enum)


__all__ = [
    # Enums
    "ChainType",
    "SecurityProfile",
    "RiskLevel",
    # Dataclasses
    "SpendingLimits",
    "ChainConfig",
    "SentinelCoinbaseConfig",
    # Constants
    "HIGH_RISK_ACTIONS",
    "SAFE_ACTIONS",
    "BLOCKED_ACTIONS",
    "KNOWN_MALICIOUS_ADDRESSES",
    "DEFI_PROTOCOL_RISK",
    # Functions
    "get_default_config",
]
