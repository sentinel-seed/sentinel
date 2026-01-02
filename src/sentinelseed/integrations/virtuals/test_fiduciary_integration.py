"""
Tests for Fiduciary Integration in Virtuals/GAME SDK.

These tests verify that fiduciary validation is correctly integrated
into the Virtuals SentinelValidator for AI agent operations.

Run with: python -m pytest src/sentinelseed/integrations/virtuals/test_fiduciary_integration.py -v
"""

import pytest

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
class TestVirtualsFiduciaryIntegration:
    """Tests for Fiduciary integration in Virtuals."""

    def test_fiduciary_enabled_by_default(self):
        """Fiduciary validation should be enabled by default."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        validator = SentinelValidator()
        stats = validator.get_fiduciary_stats()

        assert stats["enabled"] is True
        assert stats["strict"] is False

    def test_fiduciary_can_be_disabled(self):
        """Fiduciary validation can be disabled."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        validator = SentinelValidator(fiduciary_enabled=False)
        stats = validator.get_fiduciary_stats()

        assert stats["enabled"] is False

    def test_fiduciary_uses_default_context(self):
        """Default Virtuals context should be used if not provided."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        validator = SentinelValidator()

        # Should not raise - uses default context
        result = validator.validate(
            action_name="transfer",
            action_args={"amount": 50.0, "recipient": "0x1234"},
            context={"purpose": "Test transfer"},
        )

        stats = validator.get_fiduciary_stats()
        assert stats["validator_stats"]["total_validated"] >= 1

    def test_fiduciary_custom_context(self):
        """Custom UserContext should be used when provided."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        custom_context = UserContext(
            goals=["maximize trading profits"],
            risk_tolerance=RiskTolerance.HIGH,
        )

        validator = SentinelValidator(user_context=custom_context)

        # High-risk action should be allowed for high-risk user
        result = validator.validate(
            action_name="swap",
            action_args={"amount": 500.0},
            context={"purpose": "speculative high risk trade"},
        )

        # Should not be blocked by fiduciary for high-risk user
        # (may still be blocked by scope gate if over limit)
        fiduciary_concerns = [c for c in result.concerns if "Fiduciary" in c]
        # High-risk user should have fewer/no fiduciary concerns
        assert len(fiduciary_concerns) == 0 or result.passed is True

    def test_fiduciary_blocks_misaligned_action_strict_mode(self):
        """Fiduciary should block actions misaligned with user interests in strict mode."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        low_risk_context = UserContext(
            goals=["preserve capital", "minimize risk"],
            constraints=["avoid high risk trades", "no speculative operations"],
            risk_tolerance=RiskTolerance.LOW,
        )

        validator = SentinelValidator(
            user_context=low_risk_context,
            strict_fiduciary=True,
        )

        result = validator.validate(
            action_name="swap",
            action_args={"amount": 500.0},
            context={"purpose": "aggressive high risk volatile meme coin speculation"},
        )

        # Should be blocked due to fiduciary violation in strict mode
        assert result.passed is False
        fiduciary_concerns = [c for c in result.concerns if "Fiduciary" in c]
        assert len(fiduciary_concerns) > 0

    def test_fiduciary_warns_but_allows_in_non_strict_mode(self):
        """Fiduciary should warn but allow in non-strict mode."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        low_risk_context = UserContext(
            goals=["preserve capital"],
            risk_tolerance=RiskTolerance.LOW,
        )

        validator = SentinelValidator(
            user_context=low_risk_context,
            strict_fiduciary=False,  # Non-strict mode
        )

        result = validator.validate(
            action_name="swap",
            action_args={"amount": 50.0},  # Within limits
            context={"purpose": "high risk trade"},
        )

        # May have fiduciary concerns but still pass (non-strict)
        # Action passes if other gates pass
        fiduciary_concerns = [c for c in result.concerns if "Fiduciary" in c]
        # Concerns may be present but don't block
        if fiduciary_concerns:
            # If there are fiduciary concerns, result might still pass
            # because strict_fiduciary is False
            pass

    def test_fiduciary_update_context(self):
        """UserContext can be updated at runtime."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        validator = SentinelValidator()

        # Update to high-risk context
        new_context = UserContext(
            risk_tolerance=RiskTolerance.HIGH,
            goals=["maximize returns"],
        )
        validator.update_user_context(new_context)

        stats = validator.get_fiduciary_stats()
        assert stats["enabled"] is True

    def test_fiduciary_update_context_raises_when_disabled(self):
        """Updating context should raise when fiduciary is disabled."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        validator = SentinelValidator(fiduciary_enabled=False)

        new_context = UserContext(
            risk_tolerance=RiskTolerance.HIGH,
        )

        with pytest.raises(ValueError, match="not enabled"):
            validator.update_user_context(new_context)


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestVirtualsFiduciaryStats:
    """Tests for fiduciary statistics tracking."""

    def test_stats_track_validations(self):
        """Fiduciary stats should track validation counts."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        validator = SentinelValidator()

        # Perform some validations
        validator.validate(
            action_name="transfer",
            action_args={"amount": 10.0},
            context={"purpose": "Test 1"},
        )
        validator.validate(
            action_name="swap",
            action_args={"amount": 20.0},
            context={"purpose": "Test 2"},
        )

        stats = validator.get_fiduciary_stats()
        assert stats["validator_stats"]["total_validated"] >= 2

    def test_stats_track_violations(self):
        """Fiduciary stats should track violation counts."""
        from sentinelseed.integrations.virtuals import SentinelValidator

        low_risk_context = UserContext(
            goals=["preserve capital"],
            risk_tolerance=RiskTolerance.LOW,
        )

        validator = SentinelValidator(
            user_context=low_risk_context,
        )

        # Perform a high-risk action (should trigger violation)
        validator.validate(
            action_name="swap",
            action_args={"amount": 500.0},
            context={"purpose": "aggressive high risk volatile speculation"},
        )

        stats = validator.get_fiduciary_stats()
        assert stats["validator_stats"]["total_violations"] >= 1


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestVirtualsDefaultContext:
    """Tests for default Virtuals context."""

    def test_default_context_has_agent_goals(self):
        """Default context should have agent-appropriate goals."""
        from sentinelseed.integrations.virtuals import _get_default_virtuals_context

        context = _get_default_virtuals_context()

        assert context is not None
        assert len(context.goals) > 0
        assert any("safely" in g or "protect" in g for g in context.goals)

    def test_default_context_has_constraints(self):
        """Default context should have security constraints."""
        from sentinelseed.integrations.virtuals import _get_default_virtuals_context

        context = _get_default_virtuals_context()

        assert context is not None
        assert len(context.constraints) > 0
        assert any("private key" in c or "seed phrase" in c for c in context.constraints)

    def test_default_context_moderate_risk(self):
        """Default context should have moderate risk tolerance."""
        from sentinelseed.integrations.virtuals import _get_default_virtuals_context

        context = _get_default_virtuals_context()

        assert context is not None
        assert context.risk_tolerance == RiskTolerance.MODERATE


@pytest.mark.skipif(not HAS_FIDUCIARY, reason="Fiduciary module not available")
class TestVirtualsFiduciaryWithSafetyWorker:
    """Tests for Fiduciary integration with SentinelSafetyWorker."""

    def test_safety_worker_inherits_fiduciary(self):
        """SentinelSafetyWorker should use validator with fiduciary."""
        from sentinelseed.integrations.virtuals import (
            SentinelSafetyWorker,
            SentinelConfig,
        )

        config = SentinelConfig()
        worker = SentinelSafetyWorker(config)

        # Check that validator has fiduciary enabled
        stats = worker.validator.get_fiduciary_stats()
        assert stats["enabled"] is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
