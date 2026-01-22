"""
Tests for Memory Integration in Solana Agent Kit SentinelValidator.

These tests verify that the SentinelValidator correctly uses the core
MemoryIntegrityChecker with content validation (v2.0) support.

Run with: python -m pytest src/sentinelseed/integrations/solana_agent_kit/test_memory_integration.py -v
"""

import pytest

# Check if memory module is available
try:
    from sentinelseed.memory import (
        MemoryIntegrityChecker,
        MemorySource,
    )
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False


class TestSentinelValidatorMemoryConfig:
    """Tests for SentinelValidator memory configuration."""

    def test_default_content_validation_enabled(self):
        """Content validation should be enabled by default."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        assert validator.memory_content_validation is True

    def test_can_disable_content_validation(self):
        """Content validation should be disableable."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(memory_content_validation=False)
        assert validator.memory_content_validation is False

    def test_memory_integrity_disabled_by_default(self):
        """Memory integrity check should be disabled by default."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        assert validator.memory_integrity_check is False
        assert validator._memory_checker is None

    def test_memory_config_combined(self):
        """All memory settings should work together."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=False,
            memory_content_validation=True,
        )

        assert validator.memory_integrity_check is False
        assert validator.memory_content_validation is True


class TestSentinelValidatorMemoryStats:
    """Tests for SentinelValidator memory statistics."""

    def test_stats_disabled_when_memory_not_enabled(self):
        """Stats should show disabled when memory not enabled."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(memory_integrity_check=False)
        stats = validator.get_memory_stats()

        assert stats["enabled"] is False
        assert stats["content_validation"] is False

    @pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
    def test_stats_show_content_validation_enabled(self):
        """Stats should show content validation status when memory enabled."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret-key",
            memory_content_validation=True,
        )

        stats = validator.get_memory_stats()
        assert stats["enabled"] is True
        assert stats["content_validation"] is True

    @pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
    def test_stats_show_content_validation_disabled(self):
        """Stats should show content validation disabled when set to False."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret-key",
            memory_content_validation=False,
        )

        stats = validator.get_memory_stats()
        assert stats["enabled"] is True
        assert stats["content_validation"] is False


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestSentinelValidatorContentValidation:
    """Tests for Memory Shield v2.0 content validation in Solana Agent Kit."""

    def test_validator_initializes_with_content_validation(self):
        """Validator should initialize memory checker with content validation."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret",
            memory_content_validation=True,
        )

        assert validator._memory_checker is not None
        assert validator._memory_store is not None

    def test_transaction_recorded_with_content_validation(self):
        """Transactions should be recorded in memory store."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret",
            memory_content_validation=True,
        )

        # Perform a transaction check
        result = validator.check(
            action="transfer",
            amount=1.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Test transfer for unit testing",
        )

        # Entry should be stored
        stats = validator.get_memory_stats()
        assert stats["entries_stored"] >= 1

    def test_verify_transaction_history_passes(self):
        """Verify transaction history should pass for valid entries."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret",
            memory_content_validation=True,
        )

        # Add some transactions
        validator.check(
            action="transfer",
            amount=1.0,
            purpose="Test transfer one",
        )
        validator.check(
            action="swap",
            amount=5.0,
            purpose="Test swap operation",
        )

        # Verify
        result = validator.verify_transaction_history()

        assert result["all_valid"] is True
        assert result["checked"] == 2
        assert result["invalid_count"] == 0

    def test_content_validation_with_benign_transactions(self):
        """Benign transactions should be processed normally."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret",
            memory_content_validation=True,
        )

        # Normal benign transaction
        result = validator.check(
            action="transfer",
            amount=5.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Payment for services rendered",
        )

        # Should proceed normally
        assert result.should_proceed is True

    def test_clear_history_clears_memory_store(self):
        """Clear history should also clear memory store."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret",
            memory_content_validation=True,
        )

        # Add transaction
        validator.check(
            action="transfer",
            amount=1.0,
            purpose="Test for clear",
        )

        assert len(validator.history) == 1
        assert len(validator._memory_store) == 1

        # Clear
        validator.clear_history()

        assert len(validator.history) == 0
        assert len(validator._memory_store) == 0


@pytest.mark.skipif(not HAS_MEMORY, reason="Memory module not available")
class TestSentinelValidatorContentValidationDisabled:
    """Tests for behavior when content validation is disabled."""

    def test_transactions_still_recorded_when_disabled(self):
        """Transactions should still be recorded when content validation disabled."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(
            memory_integrity_check=True,
            memory_secret_key="test-secret",
            memory_content_validation=False,
        )

        validator.check(
            action="transfer",
            amount=1.0,
            purpose="Test with validation disabled",
        )

        stats = validator.get_memory_stats()
        assert stats["enabled"] is True
        assert stats["content_validation"] is False
        assert stats["entries_stored"] == 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
