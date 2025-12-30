"""
Coinbase Validators.

EVM-specific validation utilities for Sentinel's Coinbase integration.

This module provides:
- Address validation with EIP-55 checksum support
- Transaction validation with spending limits
- DeFi risk assessment for protocol interactions

Based on:
- EIP-55: Mixed-case checksum address encoding
- Ethereum security best practices
"""

from .address import (
    AddressValidationResult,
    is_valid_evm_address,
    is_valid_checksum_address,
    to_checksum_address,
    validate_address,
)
from .transaction import (
    TransactionValidationResult,
    TransactionValidator,
    validate_transaction,
)
from .defi import (
    DeFiRiskAssessment,
    DeFiValidator,
    assess_defi_risk,
)

__all__ = [
    # Address validation
    "AddressValidationResult",
    "is_valid_evm_address",
    "is_valid_checksum_address",
    "to_checksum_address",
    "validate_address",
    # Transaction validation
    "TransactionValidationResult",
    "TransactionValidator",
    "validate_transaction",
    # DeFi validation
    "DeFiRiskAssessment",
    "DeFiValidator",
    "assess_defi_risk",
]
