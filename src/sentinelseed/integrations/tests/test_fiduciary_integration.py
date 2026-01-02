"""
Tests for Fiduciary Integration in Financial Modules.

These tests verify that fiduciary validation is correctly integrated
into Solana Agent Kit, Coinbase, and Preflight.

Run with: python -m pytest src/sentinelseed/integrations/tests/test_fiduciary_integration.py -v
"""

import pytest
from unittest.mock import MagicMock, patch

# Check if fiduciary is available
try:
    from sentinelseed.fiduciary import (
        FiduciaryValidator,
        UserContext,
        RiskTolerance,
    )
    HAS_FIDUCIARY = True
except ImportError:
    HAS_FIDUCIARY = False


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestSolanaFiduciaryIntegration:
    """Tests for Fiduciary integration in Solana Agent Kit."""

    def test_fiduciary_enabled_by_default(self):
        """Fiduciary validation should be enabled by default."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()
        stats = validator.get_fiduciary_stats()

        assert stats["enabled"] is True
        assert stats["strict"] is False

    def test_fiduciary_can_be_disabled(self):
        """Fiduciary validation can be disabled."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator(fiduciary_enabled=False)
        stats = validator.get_fiduciary_stats()

        assert stats["enabled"] is False

    def test_fiduciary_uses_default_context(self):
        """Default Solana context should be used if not provided."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        # Should not raise
        result = validator.check("transfer", amount=1.0, purpose="Test transfer")

        stats = validator.get_fiduciary_stats()
        assert stats["validator_stats"]["total_validated"] >= 1

    def test_fiduciary_custom_context(self):
        """Custom UserContext should be used when provided."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        custom_context = UserContext(
            goals=["maximize returns"],
            risk_tolerance=RiskTolerance.HIGH,
        )

        validator = SentinelValidator(user_context=custom_context)

        # High-risk action should be allowed for high-risk user
        result = validator.check(
            "swap",
            amount=50.0,
            purpose="speculative high risk trade"
        )

        # Should not be blocked by fiduciary for high-risk user
        assert result.should_proceed is True

    def test_fiduciary_blocks_misaligned_action(self):
        """Fiduciary should block actions misaligned with user interests."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        low_risk_context = UserContext(
            goals=["preserve capital"],
            constraints=["avoid high risk"],
            risk_tolerance=RiskTolerance.LOW,
        )

        validator = SentinelValidator(
            user_context=low_risk_context,
            strict_fiduciary=True,
        )

        result = validator.check(
            "swap",
            amount=50.0,
            purpose="aggressive high risk volatile meme coin speculation"
        )

        # Should be blocked due to fiduciary violation
        assert result.should_proceed is False
        fiduciary_concerns = [c for c in result.concerns if "Fiduciary" in c]
        assert len(fiduciary_concerns) > 0

    def test_fiduciary_update_context(self):
        """UserContext can be updated at runtime."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        # Update to high-risk context
        new_context = UserContext(
            risk_tolerance=RiskTolerance.HIGH,
            goals=["maximize returns"],
        )
        validator.update_user_context(new_context)

        stats = validator.get_fiduciary_stats()
        assert stats["enabled"] is True


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestCoinbaseFiduciaryIntegration:
    """Tests for Fiduciary integration in Coinbase."""

    def test_fiduciary_enabled_by_default(self):
        """Fiduciary validation should be enabled by default."""
        from sentinelseed.integrations.coinbase.validators.transaction import (
            TransactionValidator,
        )

        validator = TransactionValidator()
        stats = validator.get_fiduciary_stats()

        assert stats["enabled"] is True
        assert stats["strict"] is False

    def test_fiduciary_can_be_disabled(self):
        """Fiduciary validation can be disabled."""
        from sentinelseed.integrations.coinbase.validators.transaction import (
            TransactionValidator,
        )

        validator = TransactionValidator(fiduciary_enabled=False)
        stats = validator.get_fiduciary_stats()

        assert stats["enabled"] is False

    def test_fiduciary_blocks_misaligned_action(self):
        """Fiduciary should block actions misaligned with user interests."""
        from sentinelseed.integrations.coinbase.validators.transaction import (
            TransactionValidator,
            TransactionDecision,
        )

        low_risk_context = UserContext(
            goals=["preserve capital"],
            constraints=["avoid high risk"],
            risk_tolerance=RiskTolerance.LOW,
        )

        validator = TransactionValidator(
            user_context=low_risk_context,
            strict_fiduciary=True,
        )

        result = validator.validate(
            action="swap",
            from_address="0x1234567890123456789012345678901234567890",
            to_address="0xabcdef0123456789abcdef0123456789abcdef01",
            amount=100.0,
            purpose="aggressive high risk volatile meme coin speculation"
        )

        # Should be rejected due to fiduciary violation
        assert result.decision == TransactionDecision.REJECT
        fiduciary_concerns = [c for c in result.concerns if "Fiduciary" in c]
        assert len(fiduciary_concerns) > 0

    def test_fiduciary_allows_aligned_action(self):
        """Fiduciary should allow actions aligned with user interests."""
        from sentinelseed.integrations.coinbase.validators.transaction import (
            TransactionValidator,
            TransactionDecision,
        )

        validator = TransactionValidator()

        result = validator.validate(
            action="native_transfer",
            from_address="0x1234567890123456789012345678901234567890",
            to_address="0xabcdef0123456789abcdef0123456789abcdef01",
            amount=50.0,
            purpose="Regular payment for consulting services"
        )

        # Should not be blocked by fiduciary
        assert result.decision in [
            TransactionDecision.APPROVE,
            TransactionDecision.APPROVE_WITH_CONFIRMATION
        ]


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestPreflightFiduciaryIntegration:
    """Tests for Fiduciary integration in Preflight via Solana."""

    def test_preflight_inherits_fiduciary_from_solana(self):
        """Preflight should inherit fiduciary from SentinelValidator."""
        from sentinelseed.integrations.preflight import PreflightValidator

        validator = PreflightValidator(
            rpc_url="https://api.mainnet-beta.solana.com"
        )

        # Check internal validator has fiduciary
        if validator._validator:
            stats = validator._validator.get_fiduciary_stats()
            assert stats["enabled"] is True


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestFiduciaryStats:
    """Tests for fiduciary statistics tracking."""

    def test_stats_track_validations(self):
        """Fiduciary stats should track validation counts."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        validator = SentinelValidator()

        # Perform some validations
        validator.check("transfer", amount=1.0, purpose="Test 1")
        validator.check("swap", amount=5.0, purpose="Test 2")

        stats = validator.get_fiduciary_stats()
        assert stats["validator_stats"]["total_validated"] >= 2

    def test_stats_track_violations(self):
        """Fiduciary stats should track violation counts."""
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        low_risk_context = UserContext(
            goals=["preserve capital"],
            risk_tolerance=RiskTolerance.LOW,
        )

        validator = SentinelValidator(
            user_context=low_risk_context,
        )

        # Perform a high-risk action (should trigger violation)
        validator.check(
            "swap",
            amount=50.0,
            purpose="aggressive high risk volatile speculation"
        )

        stats = validator.get_fiduciary_stats()
        assert stats["validator_stats"]["total_violations"] >= 1


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
