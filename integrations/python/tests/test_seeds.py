"""
Tests for seed management.
"""

import pytest
from sentinel_ai import load_seed, get_seed_info, list_seeds
from sentinel_ai.seeds import (
    load_embedded_seed,
    validate_seed,
    estimate_tokens,
    format_seed_for_system_prompt,
    SEED_METADATA,
)


class TestSeedLoading:
    """Tests for loading seeds."""

    def test_load_minimal_seed(self):
        """Should load minimal seed."""
        seed = load_seed("minimal")
        assert len(seed) > 0
        assert "SENTINEL" in seed or "THS" in seed

    def test_load_standard_seed(self):
        """Should load standard seed."""
        seed = load_seed("standard")
        assert len(seed) > 0
        assert "THREE-GATE" in seed or "THS" in seed

    def test_load_full_seed(self):
        """Should load full seed."""
        seed = load_seed("full")
        assert len(seed) > 0
        # Full should be larger than standard
        standard = load_seed("standard")
        assert len(seed) >= len(standard)

    def test_load_seed_case_insensitive(self):
        """Should work with different cases."""
        seed1 = load_seed("Standard")
        seed2 = load_seed("STANDARD")
        seed3 = load_seed("standard")
        assert seed1 == seed2 == seed3

    def test_load_invalid_seed_raises(self):
        """Should raise ValueError for invalid seed level."""
        with pytest.raises(ValueError) as excinfo:
            load_seed("invalid")
        assert "Unknown seed level" in str(excinfo.value)


class TestSeedInfo:
    """Tests for seed metadata."""

    def test_get_seed_info_minimal(self):
        """Should return correct info for minimal."""
        info = get_seed_info("minimal")
        assert info.level == "minimal"
        assert info.estimated_tokens == 2000
        assert "THS Protocol" in info.features

    def test_get_seed_info_standard(self):
        """Should return correct info for standard."""
        info = get_seed_info("standard")
        assert info.level == "standard"
        assert info.estimated_tokens == 5000
        assert "Prompt Injection Defense" in info.features

    def test_get_seed_info_full(self):
        """Should return correct info for full."""
        info = get_seed_info("full")
        assert info.level == "full"
        assert info.estimated_tokens == 8000

    def test_list_seeds(self):
        """Should list all available seeds."""
        seeds = list_seeds()
        assert len(seeds) == 3
        levels = [s.level for s in seeds]
        assert "minimal" in levels
        assert "standard" in levels
        assert "full" in levels


class TestEmbeddedSeeds:
    """Tests for embedded seed functionality."""

    def test_load_embedded_minimal(self):
        """Should load embedded minimal seed."""
        seed = load_embedded_seed("minimal")
        assert len(seed) > 0
        assert "SENTINEL" in seed

    def test_load_embedded_invalid_raises(self):
        """Should raise for non-minimal embedded seeds."""
        with pytest.raises(ValueError):
            load_embedded_seed("standard")


class TestSeedValidation:
    """Tests for seed validation."""

    def test_validate_has_ths_protocol(self):
        """Should detect THS protocol presence."""
        seed = load_seed("standard")
        validation = validate_seed(seed)
        assert validation["ths_protocol"] is True

    def test_validate_has_truth_gate(self):
        """Should detect truth gate presence."""
        seed = load_seed("standard")
        validation = validate_seed(seed)
        assert validation["truth_gate"] is True

    def test_validate_has_harm_gate(self):
        """Should detect harm gate presence."""
        seed = load_seed("standard")
        validation = validate_seed(seed)
        assert validation["harm_gate"] is True

    def test_validate_has_scope_gate(self):
        """Should detect scope gate presence."""
        seed = load_seed("standard")
        validation = validate_seed(seed)
        assert validation["scope_gate"] is True

    def test_validate_has_anti_self_preservation(self):
        """Should detect anti-self-preservation presence."""
        seed = load_seed("standard")
        validation = validate_seed(seed)
        assert validation["anti_self_preservation"] is True


class TestTokenEstimation:
    """Tests for token estimation."""

    def test_estimate_tokens_reasonable(self):
        """Token estimate should be reasonable."""
        seed = load_seed("standard")
        estimated = estimate_tokens(seed)
        # Should be in a reasonable range
        assert 1000 < estimated < 20000

    def test_estimate_matches_metadata(self):
        """Estimate should roughly match metadata for larger seeds."""
        # Only test standard and full - minimal may vary significantly
        for level in ["standard", "full"]:
            seed = load_seed(level)
            info = get_seed_info(level)
            estimated = estimate_tokens(seed)
            # Allow wide variance since token estimation is rough
            assert estimated * 0.3 < info.estimated_tokens < estimated * 3


class TestFormatting:
    """Tests for seed formatting."""

    def test_format_basic(self):
        """Basic formatting should work."""
        seed = "Test seed content"
        formatted = format_seed_for_system_prompt(seed)
        assert "Test seed content" in formatted

    def test_format_with_prefix(self):
        """Should prepend prefix."""
        formatted = format_seed_for_system_prompt(
            "Seed", prefix="PREFIX:"
        )
        assert formatted.startswith("PREFIX:")

    def test_format_with_suffix(self):
        """Should append suffix."""
        formatted = format_seed_for_system_prompt(
            "Seed", suffix="SUFFIX"
        )
        assert "SUFFIX" in formatted

    def test_format_with_instructions(self):
        """Should add additional instructions."""
        formatted = format_seed_for_system_prompt(
            "Seed", additional_instructions="Extra rules"
        )
        assert "Extra rules" in formatted
        assert "ADDITIONAL INSTRUCTIONS" in formatted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
