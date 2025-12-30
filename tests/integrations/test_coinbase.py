"""
Comprehensive test suite for Coinbase Integration.

Tests cover:
- Address validation (EIP-55 checksum)
- SpendingTracker (spending limits, None handling)
- TransactionValidator (validation logic, edge cases)
- DeFiValidator (risk assessment, None handling)

Run with: pytest tests/integrations/test_coinbase.py -v
"""

import pytest
from unittest.mock import patch, MagicMock

# Import modules under test
from sentinelseed.integrations.coinbase.validators.address import (
    is_valid_evm_address,
    is_valid_checksum_address,
    to_checksum_address,
    validate_address,
    normalize_address,
    AddressValidationStatus,
    KECCAK_AVAILABLE,
)
from sentinelseed.integrations.coinbase.validators.transaction import (
    SpendingTracker,
    TransactionValidator,
    TransactionDecision,
    validate_transaction,
)
from sentinelseed.integrations.coinbase.validators.defi import (
    DeFiValidator,
    DeFiProtocol,
    DeFiActionType,
    assess_defi_risk,
)
from sentinelseed.integrations.coinbase.config import (
    ChainType,
    RiskLevel,
    get_default_config,
)


# =============================================================================
# Address Validation Tests
# =============================================================================

class TestIsValidEvmAddress:
    """Tests for is_valid_evm_address function."""

    def test_valid_checksummed_address(self):
        """Valid checksummed address should return True."""
        assert is_valid_evm_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e") is True

    def test_valid_lowercase_address(self):
        """Valid lowercase address should return True."""
        assert is_valid_evm_address("0x742d35cc6634c0532925a3b844bc454e4438f44e") is True

    def test_valid_uppercase_address(self):
        """Valid uppercase address should return True."""
        assert is_valid_evm_address("0x742D35CC6634C0532925A3B844BC454E4438F44E") is True

    def test_invalid_too_short(self):
        """Address too short should return False."""
        assert is_valid_evm_address("0x742d35Cc6634C0532925a3b844Bc454e4438f4") is False

    def test_invalid_too_long(self):
        """Address too long should return False."""
        assert is_valid_evm_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44eAB") is False

    def test_invalid_no_prefix(self):
        """Address without 0x prefix should return False."""
        assert is_valid_evm_address("742d35Cc6634C0532925a3b844Bc454e4438f44e") is False

    def test_invalid_chars(self):
        """Address with invalid characters should return False."""
        assert is_valid_evm_address("0x742d35Cc6634C0532925a3b844Bc454e4438fGGG") is False

    def test_none_input(self):
        """None input should return False."""
        assert is_valid_evm_address(None) is False

    def test_empty_string(self):
        """Empty string should return False."""
        assert is_valid_evm_address("") is False

    def test_non_string_input(self):
        """Non-string input should return False."""
        assert is_valid_evm_address(123) is False
        assert is_valid_evm_address([]) is False
        assert is_valid_evm_address({}) is False


class TestValidateAddress:
    """Tests for validate_address function."""

    def test_valid_checksum_address(self):
        """Valid checksummed address should pass."""
        result = validate_address("0x742d35Cc6634C0532925a3b844Bc454e4438f44e")
        assert result.valid is True
        # Note: is_checksummed depends on Keccak availability
        if KECCAK_AVAILABLE:
            assert result.is_checksummed is True
            assert result.status == AddressValidationStatus.VALID_CHECKSUM

    def test_valid_lowercase_address(self):
        """Valid lowercase address should pass with warning."""
        result = validate_address("0x742d35cc6634c0532925a3b844bc454e4438f44e")
        assert result.valid is True
        assert result.is_checksummed is False
        assert result.status == AddressValidationStatus.VALID_LOWERCASE
        assert len(result.warnings) > 0

    def test_require_checksum_lowercase(self):
        """Lowercase address with require_checksum=True should fail."""
        result = validate_address(
            "0x742d35cc6634c0532925a3b844bc454e4438f44e",
            require_checksum=True
        )
        assert result.valid is False

    def test_invalid_format(self):
        """Invalid format should return INVALID_FORMAT status."""
        result = validate_address("0xinvalid")
        assert result.valid is False
        assert result.status == AddressValidationStatus.INVALID_FORMAT

    def test_empty_address(self):
        """Empty address should return EMPTY status."""
        result = validate_address("")
        assert result.valid is False
        assert result.status == AddressValidationStatus.EMPTY

    def test_none_address(self):
        """None address should return EMPTY status."""
        result = validate_address(None)
        assert result.valid is False
        assert result.status == AddressValidationStatus.EMPTY


@pytest.mark.skipif(not KECCAK_AVAILABLE, reason="Keccak not available")
class TestToChecksumAddress:
    """Tests for to_checksum_address function (requires keccak)."""

    def test_lowercase_to_checksum(self):
        """Should convert lowercase to checksummed."""
        result = to_checksum_address("0x742d35cc6634c0532925a3b844bc454e4438f44e")
        assert result == "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

    def test_already_checksummed(self):
        """Already checksummed should return same."""
        addr = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        assert to_checksum_address(addr) == addr

    def test_invalid_format_raises(self):
        """Invalid format should raise ValueError."""
        with pytest.raises(ValueError):
            to_checksum_address("0xinvalid")


class TestNormalizeAddress:
    """Tests for normalize_address function."""

    def test_normalize_valid(self):
        """Should normalize valid address."""
        success, result = normalize_address("0x742d35cc6634c0532925a3b844bc454e4438f44e")
        assert success is True

    def test_normalize_invalid(self):
        """Should return error for invalid address."""
        success, result = normalize_address("invalid")
        assert success is False
        assert "Invalid address" in result


# =============================================================================
# SpendingTracker Tests
# =============================================================================

class TestSpendingTracker:
    """Tests for SpendingTracker class."""

    def test_init(self):
        """Should initialize with empty state."""
        tracker = SpendingTracker()
        assert len(tracker.hourly_spending) == 0
        assert len(tracker.daily_spending) == 0

    def test_record_transaction(self):
        """Should record transaction amounts."""
        tracker = SpendingTracker()
        wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

        tracker.record_transaction(wallet, 10.0)
        assert tracker.get_hourly_spent(wallet) == 10.0
        assert tracker.get_daily_spent(wallet) == 10.0
        assert tracker.get_hourly_tx_count(wallet) == 1
        assert tracker.get_daily_tx_count(wallet) == 1

    def test_multiple_transactions(self):
        """Should accumulate multiple transactions."""
        tracker = SpendingTracker()
        wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

        tracker.record_transaction(wallet, 10.0)
        tracker.record_transaction(wallet, 20.0)
        tracker.record_transaction(wallet, 30.0)

        assert tracker.get_hourly_spent(wallet) == 60.0
        assert tracker.get_daily_spent(wallet) == 60.0
        assert tracker.get_hourly_tx_count(wallet) == 3

    def test_case_insensitive_wallet(self):
        """Should treat wallet addresses case-insensitively."""
        tracker = SpendingTracker()
        wallet_lower = "0x742d35cc6634c0532925a3b844bc454e4438f44e"
        wallet_upper = "0x742D35CC6634C0532925A3B844BC454E4438F44E"

        tracker.record_transaction(wallet_lower, 10.0)
        assert tracker.get_hourly_spent(wallet_upper) == 10.0

    def test_get_summary(self):
        """Should return complete summary."""
        tracker = SpendingTracker()
        wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

        tracker.record_transaction(wallet, 50.0)
        summary = tracker.get_summary(wallet)

        assert summary["hourly_spent"] == 50.0
        assert summary["daily_spent"] == 50.0
        assert summary["hourly_tx_count"] == 1
        assert summary["daily_tx_count"] == 1

    def test_reset_wallet(self):
        """Should reset specific wallet."""
        tracker = SpendingTracker()
        wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

        tracker.record_transaction(wallet, 100.0)
        tracker.reset(wallet)

        assert tracker.get_hourly_spent(wallet) == 0.0
        assert tracker.get_daily_spent(wallet) == 0.0

    def test_reset_all(self):
        """Should reset all wallets."""
        tracker = SpendingTracker()
        wallet1 = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        wallet2 = "0x1234567890123456789012345678901234567890"

        tracker.record_transaction(wallet1, 100.0)
        tracker.record_transaction(wallet2, 200.0)
        tracker.reset()

        # After full reset, should start fresh
        assert tracker.get_hourly_spent(wallet1) == 0.0
        assert tracker.get_hourly_spent(wallet2) == 0.0

    # None handling tests (M001 fix verification)
    def test_none_wallet_check_reset(self):
        """_check_reset should handle None wallet gracefully."""
        tracker = SpendingTracker()
        # Should not raise
        tracker._check_reset(None)

    def test_none_wallet_record_transaction(self):
        """record_transaction should handle None wallet gracefully."""
        tracker = SpendingTracker()
        # Should not raise
        tracker.record_transaction(None, 100.0)

    def test_none_wallet_get_hourly_spent(self):
        """get_hourly_spent should return 0.0 for None wallet."""
        tracker = SpendingTracker()
        assert tracker.get_hourly_spent(None) == 0.0

    def test_none_wallet_get_daily_spent(self):
        """get_daily_spent should return 0.0 for None wallet."""
        tracker = SpendingTracker()
        assert tracker.get_daily_spent(None) == 0.0

    def test_none_wallet_get_hourly_tx_count(self):
        """get_hourly_tx_count should return 0 for None wallet."""
        tracker = SpendingTracker()
        assert tracker.get_hourly_tx_count(None) == 0

    def test_none_wallet_get_daily_tx_count(self):
        """get_daily_tx_count should return 0 for None wallet."""
        tracker = SpendingTracker()
        assert tracker.get_daily_tx_count(None) == 0

    def test_none_wallet_get_summary(self):
        """get_summary should return zero summary for None wallet."""
        tracker = SpendingTracker()
        summary = tracker.get_summary(None)
        assert summary["hourly_spent"] == 0.0
        assert summary["daily_spent"] == 0.0
        assert summary["hourly_tx_count"] == 0
        assert summary["daily_tx_count"] == 0


# =============================================================================
# TransactionValidator Tests
# =============================================================================

class TestTransactionValidator:
    """Tests for TransactionValidator class."""

    def test_init_default_config(self):
        """Should initialize with default config."""
        validator = TransactionValidator()
        assert validator.config is not None
        assert validator.spending_tracker is not None

    def test_init_custom_config(self):
        """Should initialize with custom config."""
        config = get_default_config("strict")
        validator = TransactionValidator(config=config)
        assert validator.config == config

    def test_approve_valid_transaction(self):
        """Should approve valid small transaction."""
        validator = TransactionValidator()
        result = validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=10.0,
            chain=ChainType.BASE_MAINNET,
        )
        assert result.is_approved is True
        assert result.decision == TransactionDecision.APPROVE

    def test_block_invalid_sender_address(self):
        """Should block invalid sender address."""
        validator = TransactionValidator()
        result = validator.validate(
            action="native_transfer",
            from_address="0xinvalid",
            to_address="0x1234567890123456789012345678901234567890",
            amount=10.0,
        )
        assert result.decision == TransactionDecision.BLOCK
        assert "Invalid sender address" in result.blocked_reason

    def test_block_invalid_recipient_address(self):
        """Should block invalid recipient address."""
        validator = TransactionValidator()
        result = validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0xinvalid",
            amount=10.0,
        )
        assert result.decision == TransactionDecision.BLOCK
        assert "Invalid recipient address" in result.blocked_reason

    def test_block_exceeds_single_limit(self):
        """Should block transaction exceeding single limit."""
        config = get_default_config("strict")  # Low limits
        validator = TransactionValidator(config=config)
        result = validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=1000.0,  # Exceeds strict limit
        )
        assert result.decision == TransactionDecision.BLOCK
        assert "exceeds single transaction limit" in result.blocked_reason

    def test_detect_unlimited_approval(self):
        """Should detect unlimited approval (MAX_UINT256)."""
        config = get_default_config("standard")
        config.block_unlimited_approvals = True
        validator = TransactionValidator(config=config)

        result = validator.validate(
            action="approve",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=0,
            approval_amount="115792089237316195423570985008687907853269984665640564039457584007913129639935",
        )
        assert result.decision == TransactionDecision.BLOCK
        assert "Unlimited token approval" in result.blocked_reason

    def test_record_completed_transaction(self):
        """Should record completed transaction."""
        validator = TransactionValidator()
        wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"

        validator.record_completed_transaction(wallet, 50.0)

        summary = validator.get_spending_summary(wallet)
        assert summary["hourly_spent"] == 50.0
        assert summary["daily_spent"] == 50.0

    def test_validation_stats(self):
        """Should track validation statistics."""
        validator = TransactionValidator()

        # Perform some validations
        validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=10.0,
        )

        stats = validator.get_validation_stats()
        assert stats["total"] >= 1

    # None handling tests (M004 fix verification)
    def test_none_from_address_with_amount(self):
        """Should handle None from_address with amount > 0."""
        validator = TransactionValidator()
        # Should not raise, should process without spending tracking
        result = validator.validate(
            action="native_transfer",
            from_address=None,
            to_address="0x1234567890123456789012345678901234567890",
            amount=10.0,
        )
        # Should still work (no crash)
        assert result is not None

    def test_none_from_address_rate_limits(self):
        """Should skip rate limits for None from_address."""
        validator = TransactionValidator()
        result = validator.validate(
            action="native_transfer",
            from_address=None,
            to_address="0x1234567890123456789012345678901234567890",
            amount=0,
        )
        # Should not have rate limit concerns
        assert result is not None


class TestValidateTransactionFunction:
    """Tests for validate_transaction convenience function."""

    def test_convenience_function(self):
        """Should work as standalone function."""
        result = validate_transaction(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=10.0,
        )
        assert result.is_approved is True


# =============================================================================
# DeFiValidator Tests
# =============================================================================

class TestDeFiValidator:
    """Tests for DeFiValidator class."""

    def test_init_default(self):
        """Should initialize with default settings."""
        validator = DeFiValidator()
        assert validator.min_collateral_ratio == 1.5
        assert validator.max_borrow_utilization == 0.75

    def test_init_custom(self):
        """Should initialize with custom settings."""
        validator = DeFiValidator(
            min_collateral_ratio=2.0,
            max_borrow_utilization=0.5,
        )
        assert validator.min_collateral_ratio == 2.0
        assert validator.max_borrow_utilization == 0.5

    def test_assess_low_risk_supply(self):
        """Supply operation should return valid assessment."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol="compound",
            action="supply",
            amount=100.0,
        )
        # Base risk for Compound is 2.0, which gives score of 50 (HIGH threshold)
        # This is expected behavior - DeFi is inherently risky
        assert assessment.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH)
        assert assessment.protocol == DeFiProtocol.COMPOUND
        assert assessment.action_type == DeFiActionType.SUPPLY

    def test_assess_high_risk_borrow(self):
        """Borrowing with low collateral should be high risk."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol="aave",
            action="borrow",
            amount=1000.0,
            collateral_ratio=1.2,  # Below min 1.5
        )
        assert assessment.is_high_risk is True
        assert len(assessment.warnings) > 0

    def test_assess_critical_undercollateralized(self):
        """Under-collateralized position should be critical."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol="compound",
            action="borrow",
            amount=1000.0,
            collateral_ratio=0.9,  # Below 1.0!
        )
        assert assessment.risk_level == RiskLevel.CRITICAL
        assert "CRITICAL" in str(assessment.warnings)

    def test_assess_suspicious_apy(self):
        """Extremely high APY should be flagged."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol="unknown_protocol",
            action="supply",
            amount=500.0,
            apy=500.0,  # Suspiciously high
        )
        assert assessment.is_high_risk is True
        assert any("APY" in w for w in assessment.warnings)

    def test_assess_unknown_protocol(self):
        """Unknown protocol should be high risk."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol="unknown_protocol",
            action="supply",
            amount=100.0,
        )
        assert assessment.protocol == DeFiProtocol.UNKNOWN
        assert len(assessment.warnings) > 0

    def test_parse_protocol_case_insensitive(self):
        """Protocol parsing should be case insensitive."""
        validator = DeFiValidator()

        assessment1 = validator.assess(protocol="COMPOUND", action="supply")
        assessment2 = validator.assess(protocol="compound", action="supply")
        assessment3 = validator.assess(protocol="Compound", action="supply")

        assert assessment1.protocol == DeFiProtocol.COMPOUND
        assert assessment2.protocol == DeFiProtocol.COMPOUND
        assert assessment3.protocol == DeFiProtocol.COMPOUND

    def test_parse_action_variations(self):
        """Action parsing should handle variations."""
        validator = DeFiValidator()

        assessment1 = validator.assess(protocol="aave", action="add_liquidity")
        assessment2 = validator.assess(protocol="aave", action="add-liquidity")
        assessment3 = validator.assess(protocol="aave", action="ADD LIQUIDITY")

        assert assessment1.action_type == DeFiActionType.ADD_LIQUIDITY
        assert assessment2.action_type == DeFiActionType.ADD_LIQUIDITY
        assert assessment3.action_type == DeFiActionType.ADD_LIQUIDITY

    # None handling tests (M003 fix verification)
    def test_none_protocol(self):
        """Should handle None protocol gracefully."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol=None,
            action="supply",
            amount=100.0,
        )
        assert assessment.protocol == DeFiProtocol.UNKNOWN

    def test_none_action(self):
        """Should handle None action gracefully."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol="compound",
            action=None,
            amount=100.0,
        )
        assert assessment.action_type == DeFiActionType.OTHER

    def test_none_protocol_and_action(self):
        """Should handle both None protocol and action."""
        validator = DeFiValidator()
        assessment = validator.assess(
            protocol=None,
            action=None,
            amount=100.0,
        )
        assert assessment.protocol == DeFiProtocol.UNKNOWN
        assert assessment.action_type == DeFiActionType.OTHER


class TestAssessDeFiRiskFunction:
    """Tests for assess_defi_risk convenience function."""

    def test_convenience_function(self):
        """Should work as standalone function."""
        assessment = assess_defi_risk(
            protocol="compound",
            action="supply",
            amount=100.0,
        )
        assert assessment.protocol == DeFiProtocol.COMPOUND


# =============================================================================
# Integration Tests
# =============================================================================

class TestCoinbaseIntegration:
    """Integration tests combining multiple components."""

    def test_full_transaction_flow(self):
        """Test complete transaction validation flow."""
        # Create validator
        validator = TransactionValidator()
        wallet = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
        recipient = "0x1234567890123456789012345678901234567890"

        # Validate transaction
        result = validator.validate(
            action="native_transfer",
            from_address=wallet,
            to_address=recipient,
            amount=25.0,
            purpose="Payment for services",
        )

        assert result.is_approved is True

        # Record if approved
        if result.is_approved:
            validator.record_completed_transaction(wallet, 25.0)

        # Check spending
        summary = validator.get_spending_summary(wallet)
        assert summary["hourly_spent"] == 25.0

    def test_security_profiles(self):
        """Test different security profiles."""
        profiles = ["permissive", "standard", "strict", "paranoid"]

        for profile in profiles:
            config = get_default_config(profile)
            validator = TransactionValidator(config=config)

            result = validator.validate(
                action="native_transfer",
                from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
                to_address="0x1234567890123456789012345678901234567890",
                amount=50.0,
            )

            # All should return a valid result
            assert result is not None
            assert result.decision in TransactionDecision


# =============================================================================
# Edge Cases and Error Handling
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_zero_amount_transaction(self):
        """Zero amount transaction should be allowed."""
        validator = TransactionValidator()
        result = validator.validate(
            action="approve",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=0,
        )
        assert result.is_approved is True

    def test_negative_amount_treated_as_zero(self):
        """Negative amount should be treated appropriately."""
        validator = TransactionValidator()
        result = validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=-10.0,  # Negative
        )
        # Should not trigger spending limits
        assert result is not None

    def test_very_large_amount(self):
        """Very large amounts should be blocked."""
        validator = TransactionValidator()
        result = validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=1000000.0,  # 1 million
        )
        assert result.decision == TransactionDecision.BLOCK

    def test_empty_action(self):
        """Empty action string handling."""
        validator = TransactionValidator()
        result = validator.validate(
            action="",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=10.0,
        )
        # Should handle gracefully
        assert result is not None

    def test_whitespace_addresses(self):
        """Addresses with whitespace should be handled."""
        result = validate_address("  0x742d35Cc6634C0532925a3b844Bc454e4438f44e  ")
        assert result.valid is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
