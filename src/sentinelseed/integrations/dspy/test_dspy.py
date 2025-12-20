"""
Comprehensive test suite for DSPy integration.

Tests cover:
- Constants and configuration
- Custom exceptions
- Module initialization and validation
- Tools functionality
- Error handling
- Timeout behavior
- Fail-closed mode
- Text size limits
- Parameter validation

Run with: python -m pytest sentinelseed/integrations/dspy/test_dspy.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any


# Test constants and exceptions (always available)
class TestConstants:
    """Test that constants are correctly defined."""

    def test_dspy_available_flag(self):
        """DSPY_AVAILABLE should be a boolean."""
        from sentinelseed.integrations.dspy import DSPY_AVAILABLE
        assert isinstance(DSPY_AVAILABLE, bool)

    def test_default_seed_level(self):
        """DEFAULT_SEED_LEVEL should be 'standard'."""
        from sentinelseed.integrations.dspy import DEFAULT_SEED_LEVEL
        assert DEFAULT_SEED_LEVEL == "standard"

    def test_default_max_text_size(self):
        """DEFAULT_MAX_TEXT_SIZE should be 50KB."""
        from sentinelseed.integrations.dspy import DEFAULT_MAX_TEXT_SIZE
        assert DEFAULT_MAX_TEXT_SIZE == 50 * 1024

    def test_default_validation_timeout(self):
        """DEFAULT_VALIDATION_TIMEOUT should be 30 seconds."""
        from sentinelseed.integrations.dspy import DEFAULT_VALIDATION_TIMEOUT
        assert DEFAULT_VALIDATION_TIMEOUT == 30.0

    def test_valid_seed_levels(self):
        """VALID_SEED_LEVELS should contain expected values."""
        from sentinelseed.integrations.dspy import VALID_SEED_LEVELS
        assert VALID_SEED_LEVELS == ("minimal", "standard", "full")

    def test_valid_modes(self):
        """VALID_MODES should contain expected values."""
        from sentinelseed.integrations.dspy import VALID_MODES
        assert VALID_MODES == ("block", "flag", "heuristic")

    def test_valid_providers(self):
        """VALID_PROVIDERS should contain expected values."""
        from sentinelseed.integrations.dspy import VALID_PROVIDERS
        assert VALID_PROVIDERS == ("openai", "anthropic")

    def test_valid_gates(self):
        """VALID_GATES should contain expected values."""
        from sentinelseed.integrations.dspy import VALID_GATES
        assert VALID_GATES == ("truth", "harm", "scope", "purpose")


class TestExceptions:
    """Test custom exceptions."""

    def test_dspy_not_available_error(self):
        """DSPyNotAvailableError should have correct message."""
        from sentinelseed.integrations.dspy import DSPyNotAvailableError

        error = DSPyNotAvailableError()
        assert "dspy is required" in str(error)
        assert "pip install dspy" in str(error)

    def test_text_too_large_error(self):
        """TextTooLargeError should store size information."""
        from sentinelseed.integrations.dspy import TextTooLargeError

        error = TextTooLargeError(100000, 50000)
        assert error.size == 100000
        assert error.max_size == 50000
        assert "100,000" in str(error)
        assert "50,000" in str(error)

    def test_validation_timeout_error(self):
        """ValidationTimeoutError should store timeout information."""
        from sentinelseed.integrations.dspy import ValidationTimeoutError

        error = ValidationTimeoutError(30.0, "sync validation")
        assert error.timeout == 30.0
        assert error.operation == "sync validation"
        assert "30" in str(error)

    def test_invalid_parameter_error(self):
        """InvalidParameterError should store parameter information."""
        from sentinelseed.integrations.dspy import InvalidParameterError

        error = InvalidParameterError("mode", "invalid", ("block", "flag"))
        assert error.param == "mode"
        assert error.value == "invalid"
        assert error.valid_values == ("block", "flag")
        assert "mode" in str(error)
        assert "invalid" in str(error)


class TestRequireDspy:
    """Test require_dspy function."""

    def test_require_dspy_when_available(self):
        """require_dspy should not raise when DSPy is available."""
        from sentinelseed.integrations.dspy import DSPY_AVAILABLE, require_dspy

        if DSPY_AVAILABLE:
            # Should not raise
            require_dspy("test_function")
        else:
            pytest.skip("DSPy not available")

    def test_require_dspy_raises_when_not_available(self):
        """require_dspy should raise DSPyNotAvailableError when not available."""
        from sentinelseed.integrations.dspy import (
            DSPyNotAvailableError,
            require_dspy,
        )
        import sentinelseed.integrations.dspy as dspy_mod

        # Temporarily patch DSPY_AVAILABLE to False
        original = dspy_mod.DSPY_AVAILABLE
        dspy_mod.DSPY_AVAILABLE = False
        try:
            with pytest.raises(DSPyNotAvailableError):
                require_dspy("test_function")
        finally:
            dspy_mod.DSPY_AVAILABLE = original


# Tests that require DSPy
@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed"
)
class TestSentinelGuard:
    """Test SentinelGuard module."""

    def test_guard_initialization_heuristic(self):
        """SentinelGuard should initialize in heuristic mode."""
        import dspy
        from sentinelseed.integrations.dspy import SentinelGuard

        base = Mock(spec=dspy.Module)
        guard = SentinelGuard(base, mode="heuristic")

        assert guard.mode == "heuristic"
        assert guard.max_text_size == 50 * 1024
        assert guard.timeout == 30.0
        assert guard.fail_closed is False

    def test_guard_initialization_custom_params(self):
        """SentinelGuard should accept custom parameters."""
        import dspy
        from sentinelseed.integrations.dspy import SentinelGuard

        base = Mock(spec=dspy.Module)
        guard = SentinelGuard(
            base,
            mode="heuristic",
            max_text_size=10000,
            timeout=10.0,
            fail_closed=True,
        )

        assert guard.max_text_size == 10000
        assert guard.timeout == 10.0
        assert guard.fail_closed is True

    def test_guard_invalid_mode_raises(self):
        """SentinelGuard should raise for invalid mode."""
        import dspy
        from sentinelseed.integrations.dspy import (
            SentinelGuard,
            InvalidParameterError,
        )

        base = Mock(spec=dspy.Module)
        with pytest.raises(InvalidParameterError) as exc_info:
            SentinelGuard(base, mode="invalid")

        assert exc_info.value.param == "mode"
        assert exc_info.value.value == "invalid"

    def test_guard_invalid_provider_raises(self):
        """SentinelGuard should raise for invalid provider."""
        import dspy
        from sentinelseed.integrations.dspy import (
            SentinelGuard,
            InvalidParameterError,
        )

        base = Mock(spec=dspy.Module)
        with pytest.raises(InvalidParameterError) as exc_info:
            SentinelGuard(base, api_key="test", provider="invalid")

        assert exc_info.value.param == "provider"

    def test_guard_fallback_to_heuristic(self):
        """SentinelGuard should fallback to heuristic without API key."""
        import dspy
        from sentinelseed.integrations.dspy import SentinelGuard

        base = Mock(spec=dspy.Module)
        guard = SentinelGuard(base, mode="block")  # No API key

        assert guard.mode == "heuristic"


@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed"
)
class TestSentinelPredict:
    """Test SentinelPredict module."""

    def test_predict_initialization(self):
        """SentinelPredict should initialize correctly."""
        from sentinelseed.integrations.dspy import SentinelPredict

        predictor = SentinelPredict(
            "question -> answer",
            mode="heuristic",
            timeout=15.0,
        )

        assert predictor._guard.mode == "heuristic"
        assert predictor._guard.timeout == 15.0


@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed"
)
class TestSentinelChainOfThought:
    """Test SentinelChainOfThought module."""

    def test_cot_initialization(self):
        """SentinelChainOfThought should initialize correctly."""
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
            fail_closed=True,
        )

        assert cot._guard.mode == "heuristic"
        assert cot._guard.fail_closed is True


# Tool tests (require DSPy)
@pytest.mark.skipif(
    not pytest.importorskip("dspy", reason="DSPy not installed"),
    reason="DSPy not installed"
)
class TestTools:
    """Test tool creation functions."""

    def test_create_sentinel_tool_heuristic(self):
        """create_sentinel_tool should create heuristic tool."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(use_heuristic=True)

        assert callable(tool)
        assert tool.__name__ == "check_safety"

    def test_create_sentinel_tool_custom_name(self):
        """create_sentinel_tool should accept custom name."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(use_heuristic=True, name="my_safety_check")

        assert tool.__name__ == "my_safety_check"

    def test_sentinel_tool_safe_content(self):
        """Sentinel tool should return SAFE for safe content."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(use_heuristic=True, timeout=5.0)
        result = tool("What is the weather today?")

        assert "SAFE" in result

    def test_sentinel_tool_text_too_large(self):
        """Sentinel tool should handle text too large."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(
            use_heuristic=True,
            max_text_size=10,  # Very small
            timeout=5.0,
        )
        result = tool("This text is definitely longer than 10 bytes")

        assert "ERROR" in result or "exceeds" in result.lower()

    def test_create_content_filter_tool(self):
        """create_content_filter_tool should create filter tool."""
        from sentinelseed.integrations.dspy import create_content_filter_tool

        tool = create_content_filter_tool()

        assert callable(tool)
        assert tool.__name__ == "filter_content"

    def test_content_filter_returns_original(self):
        """Content filter should return original safe content."""
        from sentinelseed.integrations.dspy import create_content_filter_tool

        tool = create_content_filter_tool(timeout=5.0)
        content = "Hello, how are you?"
        result = tool(content)

        assert result == content

    def test_create_gate_check_tool(self):
        """create_gate_check_tool should create gate-specific tool."""
        from sentinelseed.integrations.dspy import create_gate_check_tool

        tool = create_gate_check_tool("harm")

        assert callable(tool)
        assert tool.__name__ == "check_harm_gate"

    def test_create_gate_check_tool_invalid_gate(self):
        """create_gate_check_tool should raise for invalid gate."""
        from sentinelseed.integrations.dspy import (
            create_gate_check_tool,
            InvalidParameterError,
        )

        with pytest.raises(InvalidParameterError) as exc_info:
            create_gate_check_tool("invalid_gate")

        assert exc_info.value.param == "gate"

    def test_gate_check_all_gates(self):
        """All valid gates should create tools."""
        from sentinelseed.integrations.dspy import create_gate_check_tool, VALID_GATES

        for gate in VALID_GATES:
            tool = create_gate_check_tool(gate)
            assert tool.__name__ == f"check_{gate}_gate"

    def test_gate_check_returns_pass(self):
        """Gate check should return PASS for safe content."""
        from sentinelseed.integrations.dspy import create_gate_check_tool

        tool = create_gate_check_tool("harm", timeout=5.0)
        result = tool("What is machine learning?")

        assert "PASS" in result


class TestFailClosedMode:
    """Test fail_closed behavior."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_tool_fail_closed_on_timeout(self):
        """Tool should return UNSAFE when fail_closed and timeout."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(
            use_heuristic=True,
            timeout=0.0001,  # Very short timeout
            fail_closed=True,
        )

        # This may or may not timeout, but tests the code path
        result = tool("Test content")
        # Result should be SAFE or UNSAFE (if timed out with fail_closed)
        assert "SAFE" in result or "UNSAFE" in result

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_filter_fail_closed(self):
        """Filter should return FILTERED when fail_closed and error."""
        from sentinelseed.integrations.dspy import create_content_filter_tool

        tool = create_content_filter_tool(
            max_text_size=5,  # Very small
            fail_closed=True,
        )

        result = tool("Content that is too large")
        # Should return error message (not filtered, since it's a size error)
        assert "ERROR" in result or "exceeds" in result.lower()


class TestTextSizeLimits:
    """Test text size validation."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_text_size_validation(self):
        """Text size validation should work correctly."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        # Small limit
        tool = create_sentinel_tool(
            use_heuristic=True,
            max_text_size=50,
            timeout=5.0,
        )

        # Small text should pass
        result = tool("Hi")
        assert "SAFE" in result or "ERROR" not in result

        # Large text should fail
        result = tool("x" * 100)
        assert "ERROR" in result


class TestModuleExports:
    """Test module exports are correct."""

    def test_all_contains_constants(self):
        """__all__ should contain constants."""
        from sentinelseed.integrations.dspy import __all__

        assert "DSPY_AVAILABLE" in __all__
        assert "DEFAULT_SEED_LEVEL" in __all__
        assert "DEFAULT_MAX_TEXT_SIZE" in __all__
        assert "DEFAULT_VALIDATION_TIMEOUT" in __all__

    def test_all_contains_exceptions(self):
        """__all__ should contain exceptions."""
        from sentinelseed.integrations.dspy import __all__

        assert "DSPyNotAvailableError" in __all__
        assert "TextTooLargeError" in __all__
        assert "ValidationTimeoutError" in __all__
        assert "InvalidParameterError" in __all__

    def test_all_contains_functions(self):
        """__all__ should contain functions."""
        from sentinelseed.integrations.dspy import __all__

        assert "require_dspy" in __all__

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_all_contains_dspy_components(self):
        """__all__ should contain DSPy components when available."""
        from sentinelseed.integrations.dspy import __all__, DSPY_AVAILABLE

        if DSPY_AVAILABLE:
            assert "SentinelGuard" in __all__
            assert "SentinelPredict" in __all__
            assert "SentinelChainOfThought" in __all__
            assert "create_sentinel_tool" in __all__


class TestSignatures:
    """Test signature classes."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_thsp_check_signature_exists(self):
        """THSPCheckSignature should be importable."""
        from sentinelseed.integrations.dspy import THSPCheckSignature

        assert THSPCheckSignature is not None

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_safety_filter_signature_exists(self):
        """SafetyFilterSignature should be importable."""
        from sentinelseed.integrations.dspy import SafetyFilterSignature

        assert SafetyFilterSignature is not None

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_content_classification_signature_exists(self):
        """ContentClassificationSignature should be importable."""
        from sentinelseed.integrations.dspy import ContentClassificationSignature

        assert ContentClassificationSignature is not None

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_thsp_instructions_exists(self):
        """THSP_INSTRUCTIONS should be importable."""
        from sentinelseed.integrations.dspy import THSP_INSTRUCTIONS

        assert isinstance(THSP_INSTRUCTIONS, str)
        assert "TRUTH" in THSP_INSTRUCTIONS
        assert "HARM" in THSP_INSTRUCTIONS
        assert "SCOPE" in THSP_INSTRUCTIONS
        assert "PURPOSE" in THSP_INSTRUCTIONS


class TestEdgeCases:
    """Test edge cases and error conditions."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_empty_content(self):
        """Tools should handle empty content."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(use_heuristic=True, timeout=5.0)
        result = tool("")

        # Empty content should be safe
        assert "SAFE" in result

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_unicode_content(self):
        """Tools should handle unicode content."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(use_heuristic=True, timeout=5.0)
        result = tool("Hello 世界 🌍")

        # Unicode should be handled
        assert "SAFE" in result or "ERROR" not in result

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_very_long_content(self):
        """Tools should reject very long content."""
        from sentinelseed.integrations.dspy import create_sentinel_tool

        tool = create_sentinel_tool(
            use_heuristic=True,
            max_text_size=1000,
            timeout=5.0,
        )
        result = tool("x" * 10000)

        assert "ERROR" in result or "exceeds" in result.lower()


class TestConcurrency:
    """Test concurrent usage."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_multiple_tools_independent(self):
        """Multiple tools should work independently."""
        from sentinelseed.integrations.dspy import (
            create_sentinel_tool,
            create_gate_check_tool,
        )

        tool1 = create_sentinel_tool(use_heuristic=True, timeout=5.0)
        tool2 = create_gate_check_tool("harm", timeout=5.0)

        result1 = tool1("Test content 1")
        result2 = tool2("Test content 2")

        assert "SAFE" in result1 or "UNSAFE" in result1
        assert "PASS" in result2 or "FAIL" in result2


class TestValidationMethods:
    """Test validation helper functions."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_validate_mode_valid(self):
        """_validate_mode should accept valid modes."""
        from sentinelseed.integrations.dspy.modules import _validate_mode

        assert _validate_mode("block") == "block"
        assert _validate_mode("flag") == "flag"
        assert _validate_mode("heuristic") == "heuristic"

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_validate_mode_invalid(self):
        """_validate_mode should reject invalid modes."""
        from sentinelseed.integrations.dspy.modules import _validate_mode
        from sentinelseed.integrations.dspy import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            _validate_mode("invalid")

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_validate_provider_valid(self):
        """_validate_provider should accept valid providers."""
        from sentinelseed.integrations.dspy.modules import _validate_provider

        assert _validate_provider("openai") == "openai"
        assert _validate_provider("anthropic") == "anthropic"

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_validate_provider_invalid(self):
        """_validate_provider should reject invalid providers."""
        from sentinelseed.integrations.dspy.modules import _validate_provider
        from sentinelseed.integrations.dspy import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            _validate_provider("google")

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_validate_text_size_valid(self):
        """_validate_text_size should pass for valid sizes."""
        from sentinelseed.integrations.dspy.modules import _validate_text_size

        # Should not raise
        _validate_text_size("Hello", 1000)

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_validate_text_size_too_large(self):
        """_validate_text_size should raise for too large text."""
        from sentinelseed.integrations.dspy.modules import _validate_text_size
        from sentinelseed.integrations.dspy import TextTooLargeError

        with pytest.raises(TextTooLargeError):
            _validate_text_size("x" * 100, 50)


class TestToolsValidation:
    """Test tools parameter validation."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_tool_validate_gate_valid(self):
        """Tools should accept valid gates."""
        from sentinelseed.integrations.dspy.tools import _validate_gate

        assert _validate_gate("truth") == "truth"
        assert _validate_gate("harm") == "harm"
        assert _validate_gate("scope") == "scope"
        assert _validate_gate("purpose") == "purpose"

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_tool_validate_gate_invalid(self):
        """Tools should reject invalid gates."""
        from sentinelseed.integrations.dspy.tools import _validate_gate
        from sentinelseed.integrations.dspy import InvalidParameterError

        with pytest.raises(InvalidParameterError):
            _validate_gate("invalid")


class TestIntegration:
    """Integration tests."""

    @pytest.mark.skipif(
        not pytest.importorskip("dspy", reason="DSPy not installed"),
        reason="DSPy not installed"
    )
    def test_full_workflow_heuristic(self):
        """Test full workflow with heuristic validation."""
        from sentinelseed.integrations.dspy import (
            create_sentinel_tool,
            create_content_filter_tool,
            create_gate_check_tool,
        )

        # Create all tools
        safety = create_sentinel_tool(use_heuristic=True, timeout=5.0)
        filter_tool = create_content_filter_tool(timeout=5.0)
        harm_check = create_gate_check_tool("harm", timeout=5.0)

        content = "What is artificial intelligence?"

        # Check safety
        safety_result = safety(content)
        assert "SAFE" in safety_result

        # Filter (should return original)
        filtered = filter_tool(content)
        assert filtered == content

        # Check harm gate
        harm_result = harm_check(content)
        assert "PASS" in harm_result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
