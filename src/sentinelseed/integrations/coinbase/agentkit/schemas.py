"""
Pydantic Schemas for Sentinel AgentKit Actions.

These schemas provide input validation for all Sentinel
security actions in the AgentKit integration.

Following Coinbase AgentKit patterns from:
- https://github.com/coinbase/agentkit/tree/master/python/coinbase-agentkit
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class SecurityProfileEnum(str, Enum):
    """Security profile options."""

    PERMISSIVE = "permissive"
    STANDARD = "standard"
    STRICT = "strict"
    PARANOID = "paranoid"


class ChainEnum(str, Enum):
    """Supported blockchain networks."""

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


class ValidateTransactionSchema(BaseModel):
    """
    Schema for validating a transaction before execution.

    Use this action to check if a transaction is safe to execute.
    Always validate before native_transfer, transfer, approve, etc.
    """

    action: str = Field(
        ...,
        description="The action type being validated (e.g., 'native_transfer', 'transfer', 'approve')",
    )
    from_address: str = Field(
        ...,
        description="The sender wallet address (0x...)",
    )
    to_address: Optional[str] = Field(
        None,
        description="The recipient address (0x...) if applicable",
    )
    amount: float = Field(
        0.0,
        description="Transaction amount in USD equivalent",
        ge=0,
    )
    chain: ChainEnum = Field(
        ChainEnum.BASE_MAINNET,
        description="The blockchain network",
    )
    token_address: Optional[str] = Field(
        None,
        description="Token contract address for ERC20/ERC721 operations",
    )
    approval_amount: Optional[str] = Field(
        None,
        description="Approval amount for approve actions (to detect unlimited approvals)",
    )
    purpose: Optional[str] = Field(
        None,
        description="Stated purpose/reason for the transaction",
    )

    @field_validator("from_address", "to_address", "token_address")
    @classmethod
    def validate_address_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate Ethereum address format."""
        if v is None:
            return None
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format. Must be 0x followed by 40 hex characters.")
        return v


class ValidateAddressSchema(BaseModel):
    """
    Schema for validating an Ethereum address.

    Checks format, checksum validity, and blocked status.
    """

    address: str = Field(
        ...,
        description="The Ethereum address to validate (0x...)",
    )
    require_checksum: bool = Field(
        False,
        description="If true, require valid EIP-55 checksum",
    )

    @field_validator("address")
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        """Basic format validation."""
        v = v.strip()
        if not v.startswith("0x"):
            raise ValueError("Address must start with 0x")
        return v


class CheckActionSafetySchema(BaseModel):
    """
    Schema for checking if an action is safe to execute.

    Use before any AgentKit action to verify safety.
    """

    action_name: str = Field(
        ...,
        description="Name of the AgentKit action to check",
    )
    action_args: Optional[Dict[str, Any]] = Field(
        None,
        description="Arguments that will be passed to the action",
    )
    purpose: Optional[str] = Field(
        None,
        description="Stated purpose for the action",
    )


class GetSpendingSummarySchema(BaseModel):
    """
    Schema for getting spending summary for a wallet.

    Returns current spending stats and remaining limits.
    """

    wallet_address: Optional[str] = Field(
        None,
        description="Wallet address to check. If not provided, uses current wallet.",
    )

    @field_validator("wallet_address")
    @classmethod
    def validate_address_format(cls, v: Optional[str]) -> Optional[str]:
        """Validate address format if provided."""
        if v is None:
            return None
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v


class AssessDeFiRiskSchema(BaseModel):
    """
    Schema for assessing DeFi operation risk.

    Use before DeFi operations (supply, borrow, trade, etc.)
    """

    protocol: str = Field(
        ...,
        description="DeFi protocol name (compound, aave, morpho, superfluid, wow)",
    )
    action: str = Field(
        ...,
        description="DeFi action type (supply, borrow, withdraw, trade, etc.)",
    )
    amount: float = Field(
        0.0,
        description="Operation amount in USD",
        ge=0,
    )
    collateral_ratio: Optional[float] = Field(
        None,
        description="Current collateral ratio (for borrow operations)",
        gt=0,
    )
    apy: Optional[float] = Field(
        None,
        description="Expected APY percentage",
    )
    token_address: Optional[str] = Field(
        None,
        description="Token contract address",
    )


class ConfigureGuardrailsSchema(BaseModel):
    """
    Schema for configuring security guardrails.

    Allows runtime adjustment of security parameters.
    """

    security_profile: Optional[SecurityProfileEnum] = Field(
        None,
        description="Security profile to apply",
    )
    max_single_transaction: Optional[float] = Field(
        None,
        description="Maximum single transaction amount in USD",
        gt=0,
    )
    max_daily_total: Optional[float] = Field(
        None,
        description="Maximum daily spending total in USD",
        gt=0,
    )
    max_hourly_total: Optional[float] = Field(
        None,
        description="Maximum hourly spending total in USD",
        gt=0,
    )
    block_unlimited_approvals: Optional[bool] = Field(
        None,
        description="Whether to block unlimited token approvals",
    )
    require_purpose: Optional[bool] = Field(
        None,
        description="Whether to require purpose for high-risk actions",
    )


class BlockAddressSchema(BaseModel):
    """
    Schema for blocking an address.
    """

    address: str = Field(
        ...,
        description="Address to block (0x...)",
    )
    reason: Optional[str] = Field(
        None,
        description="Reason for blocking",
    )

    @field_validator("address")
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        """Validate address format."""
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v


class UnblockAddressSchema(BaseModel):
    """
    Schema for unblocking an address.
    """

    address: str = Field(
        ...,
        description="Address to unblock (0x...)",
    )

    @field_validator("address")
    @classmethod
    def validate_address_format(cls, v: str) -> str:
        """Validate address format."""
        v = v.strip()
        if not v.startswith("0x") or len(v) != 42:
            raise ValueError("Invalid Ethereum address format")
        return v


class GetValidationHistorySchema(BaseModel):
    """
    Schema for getting validation history.
    """

    limit: int = Field(
        50,
        description="Maximum number of entries to return",
        ge=1,
        le=1000,
    )
    include_approved: bool = Field(
        True,
        description="Include approved transactions",
    )
    include_rejected: bool = Field(
        True,
        description="Include rejected transactions",
    )


__all__ = [
    "SecurityProfileEnum",
    "ChainEnum",
    "ValidateTransactionSchema",
    "ValidateAddressSchema",
    "CheckActionSafetySchema",
    "GetSpendingSummarySchema",
    "AssessDeFiRiskSchema",
    "ConfigureGuardrailsSchema",
    "BlockAddressSchema",
    "UnblockAddressSchema",
    "GetValidationHistorySchema",
]
