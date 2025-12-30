"""Pydantic schemas for Sentinel x402 AgentKit actions.

These schemas define the input parameters for each Sentinel x402 action,
following AgentKit's pattern of using Pydantic BaseModel for validation.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ValidatePaymentSchema(BaseModel):
    """Schema for validating an x402 payment before execution."""

    endpoint: str = Field(
        ...,
        description="The URL of the endpoint requesting payment"
    )
    amount: str = Field(
        ...,
        description="Payment amount in atomic units (e.g., USDC has 6 decimals)"
    )
    asset: str = Field(
        ...,
        description="Asset contract address for payment"
    )
    network: str = Field(
        ...,
        description="Network for payment (base, base-sepolia, avalanche, avalanche-fuji)"
    )
    pay_to: str = Field(
        ...,
        description="Recipient address for the payment"
    )
    scheme: str = Field(
        default="exact",
        description="Payment scheme (usually 'exact')"
    )
    description: str = Field(
        default="",
        description="Description of what is being purchased"
    )


class GetSpendingSummarySchema(BaseModel):
    """Schema for retrieving spending summary."""

    wallet_address: Optional[str] = Field(
        None,
        description="Wallet address to get summary for (uses current wallet if not specified)"
    )


class ConfigureSpendingLimitsSchema(BaseModel):
    """Schema for configuring spending limits."""

    max_single_payment: Optional[float] = Field(
        None,
        description="Maximum amount for a single payment (USD)"
    )
    max_daily_total: Optional[float] = Field(
        None,
        description="Maximum total daily spending (USD)"
    )
    max_transactions_per_day: Optional[int] = Field(
        None,
        description="Maximum number of transactions per day"
    )


class SafeX402RequestSchema(BaseModel):
    """Schema for making a safe x402 HTTP request with Sentinel validation."""

    url: str = Field(
        ...,
        description="The URL to request (x402-protected endpoint)"
    )
    method: Literal["GET", "POST", "PUT", "DELETE", "PATCH"] = Field(
        default="GET",
        description="HTTP method"
    )
    headers: Optional[dict[str, str]] = Field(
        None,
        description="Optional headers to include"
    )
    body: Optional[Any] = Field(
        None,
        description="Optional request body for POST/PUT/PATCH"
    )
    max_payment: Optional[float] = Field(
        None,
        description="Maximum payment amount to allow (USD)"
    )
    require_confirmation: bool = Field(
        default=True,
        description="Whether to require confirmation before payment"
    )


class CheckEndpointSafetySchema(BaseModel):
    """Schema for checking if an endpoint is safe for x402 payments."""

    endpoint: str = Field(
        ...,
        description="The endpoint URL to check"
    )


class GetAuditLogSchema(BaseModel):
    """Schema for retrieving payment audit log."""

    wallet_address: Optional[str] = Field(
        None,
        description="Filter by wallet address"
    )
    limit: int = Field(
        default=50,
        description="Maximum number of entries to return"
    )


class ResetSpendingSchema(BaseModel):
    """Schema for resetting spending records."""

    wallet_address: Optional[str] = Field(
        None,
        description="Wallet to reset (all wallets if not specified)"
    )
    confirm: bool = Field(
        default=False,
        description="Must be True to confirm reset"
    )
