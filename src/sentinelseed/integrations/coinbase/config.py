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
from typing import Any, Dict, FrozenSet, List, Optional, Set, Union


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


@dataclass
class SpendingLimits:
    """
    Spending limits configuration.

    All amounts are in USD equivalent for consistency across chains.
    Fully customizable - modify any field directly or use helper methods.

    Example:
        # Create with defaults
        limits = SpendingLimits()

        # Customize directly
        limits.max_single_transaction = 500.0
        limits.max_daily_total = 2000.0

        # Or use fluent API
        limits = SpendingLimits().configure(
            max_single=500.0,
            max_daily=2000.0,
            confirm_above=50.0,
        )
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

    def configure(
        self,
        max_single: Optional[float] = None,
        max_daily: Optional[float] = None,
        max_hourly: Optional[float] = None,
        max_tx_per_hour: Optional[int] = None,
        max_tx_per_day: Optional[int] = None,
        confirm_above: Optional[float] = None,
    ) -> "SpendingLimits":
        """
        Configure limits with a fluent API. Returns self for chaining.

        Args:
            max_single: Maximum single transaction amount (USD)
            max_daily: Maximum daily total (USD)
            max_hourly: Maximum hourly total (USD)
            max_tx_per_hour: Maximum transactions per hour
            max_tx_per_day: Maximum transactions per day
            confirm_above: Require confirmation for amounts above this (USD)

        Returns:
            Self for method chaining

        Example:
            limits = SpendingLimits().configure(
                max_single=1000.0,
                max_daily=5000.0,
                confirm_above=100.0,
            )
        """
        if max_single is not None:
            self.max_single_transaction = max_single
        if max_daily is not None:
            self.max_daily_total = max_daily
        if max_hourly is not None:
            self.max_hourly_total = max_hourly
        if max_tx_per_hour is not None:
            self.max_transactions_per_hour = max_tx_per_hour
        if max_tx_per_day is not None:
            self.max_transactions_per_day = max_tx_per_day
        if confirm_above is not None:
            self.confirmation_threshold = confirm_above
        return self

    def copy(self) -> "SpendingLimits":
        """Create a copy of these limits."""
        return SpendingLimits(
            max_single_transaction=self.max_single_transaction,
            max_daily_total=self.max_daily_total,
            max_hourly_total=self.max_hourly_total,
            max_transactions_per_hour=self.max_transactions_per_hour,
            max_transactions_per_day=self.max_transactions_per_day,
            confirmation_threshold=self.confirmation_threshold,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "max_single_transaction": self.max_single_transaction,
            "max_daily_total": self.max_daily_total,
            "max_hourly_total": self.max_hourly_total,
            "max_transactions_per_hour": self.max_transactions_per_hour,
            "max_transactions_per_day": self.max_transactions_per_day,
            "confirmation_threshold": self.confirmation_threshold,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SpendingLimits":
        """Create from dictionary."""
        return cls(
            max_single_transaction=data.get("max_single_transaction", 100.0),
            max_daily_total=data.get("max_daily_total", 500.0),
            max_hourly_total=data.get("max_hourly_total", 200.0),
            max_transactions_per_hour=data.get("max_transactions_per_hour", 10),
            max_transactions_per_day=data.get("max_transactions_per_day", 50),
            confirmation_threshold=data.get("confirmation_threshold", 25.0),
        )


@dataclass
class ChainConfig:
    """
    Chain-specific configuration.

    Different chains may have different security requirements.
    Testnets are more permissive by default. Fully editable at runtime.

    Example:
        # Get config and customize
        config = ChainConfig.for_mainnet(ChainType.BASE_MAINNET, SecurityProfile.STANDARD)

        # Edit limits directly
        config.spending_limits.max_single_transaction = 500.0

        # Or use fluent API
        config.set_limits(max_single=500.0, max_daily=2000.0)

        # Block a contract
        config.block_contract("0xbad...")
    """

    chain_type: ChainType
    spending_limits: SpendingLimits = field(default_factory=SpendingLimits)
    blocked_contracts: Set[str] = field(default_factory=set)
    allowed_contracts: Set[str] = field(default_factory=set)  # Empty = all allowed
    max_gas_price_gwei: Optional[float] = None  # None = no limit
    require_verified_contracts: bool = False

    def set_limits(
        self,
        max_single: Optional[float] = None,
        max_daily: Optional[float] = None,
        max_hourly: Optional[float] = None,
        max_tx_per_hour: Optional[int] = None,
        max_tx_per_day: Optional[int] = None,
        confirm_above: Optional[float] = None,
    ) -> "ChainConfig":
        """
        Set spending limits with a fluent API. Returns self for chaining.

        Example:
            config.set_limits(max_single=500.0, max_daily=2000.0)
        """
        self.spending_limits.configure(
            max_single=max_single,
            max_daily=max_daily,
            max_hourly=max_hourly,
            max_tx_per_hour=max_tx_per_hour,
            max_tx_per_day=max_tx_per_day,
            confirm_above=confirm_above,
        )
        return self

    def block_contract(self, address: str) -> "ChainConfig":
        """Add a contract to the blocklist. Returns self for chaining."""
        if address is None:
            return self
        self.blocked_contracts.add(address.lower())
        return self

    def unblock_contract(self, address: str) -> "ChainConfig":
        """Remove a contract from the blocklist. Returns self for chaining."""
        if address is None:
            return self
        self.blocked_contracts.discard(address.lower())
        return self

    def allow_contract(self, address: str) -> "ChainConfig":
        """Add a contract to the allowlist. Returns self for chaining."""
        if address is None:
            return self
        self.allowed_contracts.add(address.lower())
        return self

    def set_gas_limit(self, max_gwei: Optional[float]) -> "ChainConfig":
        """Set maximum gas price in gwei. None = no limit."""
        self.max_gas_price_gwei = max_gwei
        return self

    def is_contract_blocked(self, address: str) -> bool:
        """Check if a contract is blocked."""
        if address is None:
            return False
        return address.lower() in self.blocked_contracts

    def is_contract_allowed(self, address: str) -> bool:
        """Check if a contract is allowed (or if allowlist is empty = all allowed)."""
        if not self.allowed_contracts:
            return True
        if address is None:
            return False
        return address.lower() in self.allowed_contracts

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
        if action is None:
            return False
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
        if action is None:
            return True  # Unknown actions are high risk
        return action.lower() in HIGH_RISK_ACTIONS

    def is_safe_action(self, action: str) -> bool:
        """Check if an action is read-only/safe."""
        if action is None:
            return False  # Unknown actions are not safe
        return action.lower() in SAFE_ACTIONS

    def is_address_blocked(self, address: str) -> bool:
        """Check if an address is blocked."""
        if address is None:
            return False
        return address.lower() in {a.lower() for a in self.blocked_addresses}

    # =========================================================================
    # Fluent Configuration API
    # =========================================================================

    def set_limits(
        self,
        chain: Optional[ChainType] = None,
        max_single: Optional[float] = None,
        max_daily: Optional[float] = None,
        max_hourly: Optional[float] = None,
        max_tx_per_hour: Optional[int] = None,
        max_tx_per_day: Optional[int] = None,
        confirm_above: Optional[float] = None,
    ) -> "SentinelCoinbaseConfig":
        """
        Set spending limits for a specific chain or all chains.

        Args:
            chain: Specific chain to configure, or None for all mainnets
            max_single: Maximum single transaction (USD)
            max_daily: Maximum daily total (USD)
            max_hourly: Maximum hourly total (USD)
            max_tx_per_hour: Maximum transactions per hour
            max_tx_per_day: Maximum transactions per day
            confirm_above: Require confirmation above this amount (USD)

        Returns:
            Self for method chaining

        Example:
            # Set limits for all mainnets
            config.set_limits(max_single=500.0, max_daily=2000.0)

            # Set limits for specific chain
            config.set_limits(
                chain=ChainType.BASE_MAINNET,
                max_single=1000.0,
            )
        """
        if chain:
            # Configure specific chain
            chain_config = self.get_chain_config(chain)
            chain_config.set_limits(
                max_single=max_single,
                max_daily=max_daily,
                max_hourly=max_hourly,
                max_tx_per_hour=max_tx_per_hour,
                max_tx_per_day=max_tx_per_day,
                confirm_above=confirm_above,
            )
        else:
            # Configure all mainnet chains
            for chain_type, chain_config in self.chain_configs.items():
                if not chain_type.is_testnet:
                    chain_config.set_limits(
                        max_single=max_single,
                        max_daily=max_daily,
                        max_hourly=max_hourly,
                        max_tx_per_hour=max_tx_per_hour,
                        max_tx_per_day=max_tx_per_day,
                        confirm_above=confirm_above,
                    )
        return self

    def set_testnet_limits(
        self,
        max_single: Optional[float] = None,
        max_daily: Optional[float] = None,
    ) -> "SentinelCoinbaseConfig":
        """
        Set spending limits for all testnets.

        Example:
            config.set_testnet_limits(max_single=50000.0)
        """
        for chain_type, chain_config in self.chain_configs.items():
            if chain_type.is_testnet:
                chain_config.set_limits(
                    max_single=max_single,
                    max_daily=max_daily,
                )
        return self

    def block_address(self, address: str) -> "SentinelCoinbaseConfig":
        """
        Add an address to the global blocklist.

        Example:
            config.block_address("0xbad...")
        """
        if address is None:
            return self
        self.blocked_addresses.add(address.lower())
        return self

    def unblock_address(self, address: str) -> "SentinelCoinbaseConfig":
        """Remove an address from the global blocklist."""
        if address is None:
            return self
        self.blocked_addresses.discard(address.lower())
        return self

    def block_action(self, action: str) -> "SentinelCoinbaseConfig":
        """Block an action globally."""
        if action is None:
            return self
        self.blocked_actions.add(action.lower())
        return self

    def allow_action(self, action: str) -> "SentinelCoinbaseConfig":
        """
        Add action to allowlist. When allowlist is non-empty,
        only listed actions are permitted.
        """
        if action is None:
            return self
        self.allowed_actions.add(action.lower())
        return self

    def use_profile(self, profile: Union[str, SecurityProfile]) -> "SentinelCoinbaseConfig":
        """
        Switch to a different security profile.

        This reconfigures all chain limits to match the new profile.

        Example:
            config.use_profile("strict")
            config.use_profile(SecurityProfile.PARANOID)
        """
        if profile is None:
            return self
        if isinstance(profile, str):
            profile = SecurityProfile(profile.lower())
        self.security_profile = profile
        self._init_default_chain_configs()
        return self

    def get_limits_summary(self) -> Dict[str, Any]:
        """
        Get a summary of current limits for easy inspection.

        Returns:
            Dictionary with limits per chain type (mainnet/testnet)
        """
        mainnet_limits = None
        testnet_limits = None

        for chain_type, chain_config in self.chain_configs.items():
            if chain_type.is_testnet and testnet_limits is None:
                testnet_limits = chain_config.spending_limits.to_dict()
            elif not chain_type.is_testnet and mainnet_limits is None:
                mainnet_limits = chain_config.spending_limits.to_dict()

        return {
            "security_profile": self.security_profile.value,
            "mainnet": mainnet_limits,
            "testnet": testnet_limits,
            "blocked_addresses_count": len(self.blocked_addresses),
            "blocked_actions": list(self.blocked_actions),
        }


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
    if profile is None:
        profile = "standard"
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
