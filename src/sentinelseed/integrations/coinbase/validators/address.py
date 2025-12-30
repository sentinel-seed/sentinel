"""
EVM Address Validation.

Implements EIP-55 checksum address validation for Ethereum and
compatible networks (Base, Polygon, Arbitrum, Optimism, Avalanche).

EIP-55 Specification:
- Addresses are 40 hex characters prefixed with 0x
- Checksum uses keccak256 hash to determine capitalization
- If the ith digit is a letter and the ith bit of the hash is 1, uppercase it

References:
- EIP-55: https://eips.ethereum.org/EIPS/eip-55
- Ethers.js: https://docs.ethers.org/v5/api/utils/address/
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

# Try to import keccak from various sources
try:
    from Crypto.Hash import keccak as pycryptodome_keccak

    def keccak256(data: bytes) -> bytes:
        """Compute keccak256 hash using pycryptodome."""
        k = pycryptodome_keccak.new(digest_bits=256)
        k.update(data)
        return k.digest()

    KECCAK_AVAILABLE = True
except ImportError:
    try:
        from eth_hash.auto import keccak as eth_keccak

        def keccak256(data: bytes) -> bytes:
            """Compute keccak256 hash using eth-hash."""
            return eth_keccak(data)

        KECCAK_AVAILABLE = True
    except ImportError:
        try:
            import hashlib

            def keccak256(data: bytes) -> bytes:
                """Compute keccak256 hash using hashlib (Python 3.11+)."""
                return hashlib.new("sha3_256", data).digest()

            KECCAK_AVAILABLE = True
        except (ImportError, ValueError):
            KECCAK_AVAILABLE = False

            def keccak256(data: bytes) -> bytes:
                """Fallback - no keccak available."""
                raise ImportError(
                    "No keccak implementation available. "
                    "Install pycryptodome or eth-hash: pip install pycryptodome"
                )


# Regex patterns for address validation
# Basic format: 0x followed by 40 hex characters
ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")

# All lowercase (no checksum)
ADDRESS_LOWERCASE_PATTERN = re.compile(r"^0x[0-9a-f]{40}$")

# All uppercase (no checksum)
ADDRESS_UPPERCASE_PATTERN = re.compile(r"^0X[0-9A-F]{40}$")


class AddressValidationStatus(Enum):
    """Status of address validation."""

    VALID_CHECKSUM = "valid_checksum"      # Valid with correct checksum
    VALID_LOWERCASE = "valid_lowercase"    # Valid lowercase (no checksum)
    VALID_UPPERCASE = "valid_uppercase"    # Valid uppercase (no checksum)
    INVALID_CHECKSUM = "invalid_checksum"  # Invalid checksum
    INVALID_FORMAT = "invalid_format"      # Invalid format
    EMPTY = "empty"                        # Empty or None


@dataclass
class AddressValidationResult:
    """
    Result of address validation.

    Attributes:
        valid: Whether the address is valid (format-wise)
        status: Detailed validation status
        address: The original address
        checksum_address: The checksummed version (if valid)
        is_checksummed: Whether original had valid checksum
        warnings: Any warnings (e.g., "no checksum")
    """

    valid: bool
    status: AddressValidationStatus
    address: str
    checksum_address: Optional[str] = None
    is_checksummed: bool = False
    warnings: list = None

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


def is_valid_evm_address(address: str) -> bool:
    """
    Check if a string is a valid EVM address format.

    This only checks the format (0x + 40 hex chars), not the checksum.

    Args:
        address: The address string to validate

    Returns:
        True if valid format, False otherwise

    Example:
        >>> is_valid_evm_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
        True
        >>> is_valid_evm_address("0xinvalid")
        False
    """
    if not address or not isinstance(address, str):
        return False
    return bool(ADDRESS_PATTERN.match(address))


def to_checksum_address(address: str) -> str:
    """
    Convert an address to EIP-55 checksum format.

    Args:
        address: The address to convert (must be valid format)

    Returns:
        The checksummed address

    Raises:
        ValueError: If address is not valid format
        ImportError: If no keccak implementation available

    Example:
        >>> to_checksum_address("0x742d35cc6634c0532925a3b844bc454e4438f44e")
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
    """
    if not is_valid_evm_address(address):
        raise ValueError(f"Invalid address format: {address}")

    # Remove 0x prefix and lowercase
    address_lower = address[2:].lower()

    # Compute keccak256 hash of the lowercase address
    address_hash = keccak256(address_lower.encode("utf-8")).hex()

    # Apply checksum based on hash
    checksummed = "0x"
    for i, char in enumerate(address_lower):
        if char in "0123456789":
            checksummed += char
        elif int(address_hash[i], 16) >= 8:
            checksummed += char.upper()
        else:
            checksummed += char.lower()

    return checksummed


def is_valid_checksum_address(address: str) -> bool:
    """
    Check if an address has a valid EIP-55 checksum.

    Args:
        address: The address to validate

    Returns:
        True if the checksum is valid, False otherwise

    Example:
        >>> is_valid_checksum_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
        True
        >>> is_valid_checksum_address("0x742d35cc6634c0532925a3b844bc454e4438f44e")
        False  # All lowercase, no checksum
    """
    if not is_valid_evm_address(address):
        return False

    # All lowercase or all uppercase are not checksummed
    if ADDRESS_LOWERCASE_PATTERN.match(address) or ADDRESS_UPPERCASE_PATTERN.match(address):
        return False

    try:
        return address == to_checksum_address(address)
    except (ImportError, ValueError):
        return False


def validate_address(
    address: str,
    require_checksum: bool = False,
) -> AddressValidationResult:
    """
    Validate an EVM address with detailed results.

    Args:
        address: The address to validate
        require_checksum: If True, reject addresses without valid checksum

    Returns:
        AddressValidationResult with detailed validation info

    Example:
        >>> result = validate_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
        >>> result.valid
        True
        >>> result.is_checksummed
        True
    """
    # Handle empty/None
    if not address or not isinstance(address, str):
        return AddressValidationResult(
            valid=False,
            status=AddressValidationStatus.EMPTY,
            address=address or "",
        )

    # Strip whitespace
    address = address.strip()

    # Check basic format
    if not is_valid_evm_address(address):
        return AddressValidationResult(
            valid=False,
            status=AddressValidationStatus.INVALID_FORMAT,
            address=address,
        )

    # Check if all lowercase (no checksum applied)
    if ADDRESS_LOWERCASE_PATTERN.match(address):
        try:
            checksum = to_checksum_address(address)
        except ImportError:
            checksum = None

        result = AddressValidationResult(
            valid=not require_checksum,
            status=AddressValidationStatus.VALID_LOWERCASE,
            address=address,
            checksum_address=checksum,
            is_checksummed=False,
        )
        if not require_checksum:
            result.warnings.append("Address has no checksum - consider using checksummed version")
        return result

    # Check if all uppercase (no checksum applied)
    if ADDRESS_UPPERCASE_PATTERN.match(address.upper()):
        try:
            checksum = to_checksum_address(address)
        except ImportError:
            checksum = None

        result = AddressValidationResult(
            valid=not require_checksum,
            status=AddressValidationStatus.VALID_UPPERCASE,
            address=address,
            checksum_address=checksum,
            is_checksummed=False,
        )
        if not require_checksum:
            result.warnings.append("Address has no checksum - consider using checksummed version")
        return result

    # Mixed case - validate checksum
    try:
        checksum = to_checksum_address(address)
        is_valid_checksum = address == checksum

        if is_valid_checksum:
            return AddressValidationResult(
                valid=True,
                status=AddressValidationStatus.VALID_CHECKSUM,
                address=address,
                checksum_address=checksum,
                is_checksummed=True,
            )
        else:
            return AddressValidationResult(
                valid=False,
                status=AddressValidationStatus.INVALID_CHECKSUM,
                address=address,
                checksum_address=checksum,
                is_checksummed=False,
                warnings=[f"Invalid checksum. Correct checksum: {checksum}"],
            )
    except ImportError:
        # No keccak available - can't verify checksum
        return AddressValidationResult(
            valid=True,  # Accept as valid format
            status=AddressValidationStatus.VALID_LOWERCASE,  # Can't verify
            address=address,
            checksum_address=None,
            is_checksummed=False,
            warnings=["Checksum verification unavailable - install pycryptodome"],
        )


def normalize_address(address: str) -> Tuple[bool, str]:
    """
    Normalize an address to checksummed format.

    Args:
        address: The address to normalize

    Returns:
        Tuple of (success, normalized_address or error_message)

    Example:
        >>> success, normalized = normalize_address("0x742d35cc...")
        >>> if success:
        ...     print(normalized)  # Checksummed version
    """
    result = validate_address(address)

    if not result.valid:
        return False, f"Invalid address: {result.status.value}"

    if result.checksum_address:
        return True, result.checksum_address

    return True, result.address


__all__ = [
    "AddressValidationStatus",
    "AddressValidationResult",
    "is_valid_evm_address",
    "is_valid_checksum_address",
    "to_checksum_address",
    "validate_address",
    "normalize_address",
    "KECCAK_AVAILABLE",
]
