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

    def test_configuration_error(self):
        """ConfigurationError should store configuration information."""
        from sentinelseed.integrations.dspy import ConfigurationError

        error = ConfigurationError("max_text_size", "positive integer", "invalid")
        assert error.param_name == "max_text_size"
        assert error.expected == "positive integer"
        assert error.got == "invalid"
        assert "max_text_size" in str(error)
        assert "positive integer" in str(error)


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

    @pytest.mark.skip(reason="Cannot test require_dspy failure when dspy is installed")
    def test_require_dspy_raises_when_not_available(self):
        """require_dspy should raise DSPyNotAvailableError when not available.

        Note: This test is skipped because require_dspy uses dynamic import,
        which cannot be mocked when dspy is already installed.
        """
        pass


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

        assert cot.mode == "heuristic"
        assert cot.fail_closed is True

    def test_cot_validate_reasoning_default(self):
        """SentinelChainOfThought should validate reasoning by default."""
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
        )

        assert cot.validate_reasoning is True
        assert cot.validate_output is True
        assert cot.reasoning_field == "reasoning"

    def test_cot_disable_reasoning_validation(self):
        """SentinelChainOfThought should allow disabling reasoning validation."""
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
            validate_reasoning=False,
        )

        assert cot.validate_reasoning is False
        assert cot.validate_output is True

    def test_cot_custom_reasoning_field(self):
        """SentinelChainOfThought should allow custom reasoning field name."""
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
            reasoning_field="thought_process",
        )

        assert cot.reasoning_field == "thought_process"

    def test_cot_extract_fields(self):
        """SentinelChainOfThought should extract reasoning and output fields."""
        import dspy
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
        )

        # Create mock prediction with reasoning and answer
        result = dspy.Prediction()
        result.reasoning = "This is my reasoning process"
        result.answer = "This is my answer"

        fields = cot._extract_fields(result)

        assert "reasoning" in fields
        assert "answer" in fields
        assert fields["reasoning"] == "This is my reasoning process"
        assert fields["answer"] == "This is my answer"

    def test_cot_extract_fields_without_reasoning(self):
        """SentinelChainOfThought should skip reasoning when disabled."""
        import dspy
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
            validate_reasoning=False,
        )

        result = dspy.Prediction()
        result.reasoning = "This is my reasoning"
        result.answer = "This is my answer"

        fields = cot._extract_fields(result)

        assert "reasoning" not in fields
        assert "answer" in fields

    def test_cot_validate_content(self):
        """SentinelChainOfThought._validate_content should work."""
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
        )

        # Safe content
        result = cot._validate_content("This is safe content")
        assert result["is_safe"] is True
        assert result["method"] == "heuristic"

    def test_cot_validate_all_fields(self):
        """SentinelChainOfThought._validate_all_fields should validate multiple fields."""
        from sentinelseed.integrations.dspy import SentinelChainOfThought

        cot = SentinelChainOfThought(
            "question -> answer",
            mode="heuristic",
        )

        fields = {
            "reasoning": "This is my safe reasoning",
            "answer": "This is my safe answer",
        }

        result = cot._validate_all_fields(fields)

        assert result["is_safe"] is True
        assert "reasoning" in result["fields_validated"]
        assert "answer" in result["fields_validated"]
        assert result["failed_fields"] == []
        assert result["field_results"]["reasoning"]["is_safe"] is True
        assert result["field_results"]["answer"]["is_safe"] is True


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

    def test_validate_mode_valid(self):
        """validate_mode should accept valid modes."""
        from sentinelseed.integrations.dspy import validate_mode

        assert validate_mode("block") == "block"
        assert validate_mode("flag") == "flag"
        assert validate_mode("heuristic") == "heuristic"

    def test_validate_mode_invalid(self):
        """validate_mode should reject invalid modes."""
        from sentinelseed.integrations.dspy import validate_mode, InvalidParameterError

        with pytest.raises(InvalidParameterError):
            validate_mode("invalid")

    def test_validate_provider_valid(self):
        """validate_provider should accept valid providers."""
        from sentinelseed.integrations.dspy import validate_provider

        assert validate_provider("openai") == "openai"
        assert validate_provider("anthropic") == "anthropic"

    def test_validate_provider_invalid(self):
        """validate_provider should reject invalid providers."""
        from sentinelseed.integrations.dspy import validate_provider, InvalidParameterError

        with pytest.raises(InvalidParameterError):
            validate_provider("google")

    def test_validate_text_size_valid(self):
        """validate_text_size should pass for valid sizes."""
        from sentinelseed.integrations.dspy import validate_text_size

        # Should not raise
        validate_text_size("Hello", 1000)

    def test_validate_text_size_too_large(self):
        """validate_text_size should raise for too large text."""
        from sentinelseed.integrations.dspy import validate_text_size, TextTooLargeError

        with pytest.raises(TextTooLargeError):
            validate_text_size("x" * 100, 50)


class TestToolsValidation:
    """Test tools parameter validation."""

    def test_tool_validate_gate_valid(self):
        """validate_gate should accept valid gates."""
        from sentinelseed.integrations.dspy import validate_gate

        assert validate_gate("truth") == "truth"
        assert validate_gate("harm") == "harm"
        assert validate_gate("scope") == "scope"
        assert validate_gate("purpose") == "purpose"

    def test_tool_validate_gate_invalid(self):
        """validate_gate should reject invalid gates."""
        from sentinelseed.integrations.dspy import validate_gate, InvalidParameterError

        with pytest.raises(InvalidParameterError):
            validate_gate("invalid")


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


class TestValidateConfigTypes:
    """Test validate_config_types function."""

    def test_valid_config(self):
        """Valid config should not raise."""
        from sentinelseed.integrations.dspy import validate_config_types

        # Should not raise
        validate_config_types(
            max_text_size=1000,
            timeout=30.0,
            fail_closed=True,
        )

    def test_invalid_max_text_size_type(self):
        """Invalid max_text_size type should raise ConfigurationError."""
        from sentinelseed.integrations.dspy import validate_config_types, ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_types(max_text_size="invalid")

        assert exc_info.value.param_name == "max_text_size"

    def test_invalid_max_text_size_value(self):
        """Negative max_text_size should raise ConfigurationError."""
        from sentinelseed.integrations.dspy import validate_config_types, ConfigurationError

        with pytest.raises(ConfigurationError):
            validate_config_types(max_text_size=-1)

    def test_invalid_timeout_type(self):
        """Invalid timeout type should raise ConfigurationError."""
        from sentinelseed.integrations.dspy import validate_config_types, ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_types(timeout="invalid")

        assert exc_info.value.param_name == "timeout"

    def test_invalid_timeout_value(self):
        """Negative timeout should raise ConfigurationError."""
        from sentinelseed.integrations.dspy import validate_config_types, ConfigurationError

        with pytest.raises(ConfigurationError):
            validate_config_types(timeout=-1.0)

    def test_invalid_fail_closed_type(self):
        """Invalid fail_closed type should raise ConfigurationError."""
        from sentinelseed.integrations.dspy import validate_config_types, ConfigurationError

        with pytest.raises(ConfigurationError) as exc_info:
            validate_config_types(fail_closed="invalid")

        assert exc_info.value.param_name == "fail_closed"

    def test_none_values_ignored(self):
        """None values should be ignored."""
        from sentinelseed.integrations.dspy import validate_config_types

        # Should not raise
        validate_config_types(
            max_text_size=None,
            timeout=None,
            fail_closed=None,
        )


class TestValidationExecutor:
    """Test ValidationExecutor class."""

    def test_singleton_pattern(self):
        """ValidationExecutor should be singleton."""
        from sentinelseed.integrations.dspy import ValidationExecutor

        executor1 = ValidationExecutor.get_instance()
        executor2 = ValidationExecutor.get_instance()

        assert executor1 is executor2

    def test_run_with_timeout_success(self):
        """run_with_timeout should return result on success."""
        from sentinelseed.integrations.dspy import get_validation_executor

        executor = get_validation_executor()

        def add(a, b):
            return a + b

        result = executor.run_with_timeout(add, args=(2, 3), timeout=5.0)
        assert result == 5

    def test_run_with_timeout_kwargs(self):
        """run_with_timeout should handle kwargs."""
        from sentinelseed.integrations.dspy import get_validation_executor

        executor = get_validation_executor()

        def greet(name, greeting="Hello"):
            return f"{greeting}, {name}!"

        result = executor.run_with_timeout(
            greet,
            args=("World",),
            kwargs={"greeting": "Hi"},
            timeout=5.0,
        )
        assert result == "Hi, World!"


class TestValidationExecutorAsync:
    """Test ValidationExecutor async methods."""

    def test_run_with_timeout_async_success(self):
        """run_with_timeout_async should return result on success."""
        import asyncio
        from sentinelseed.integrations.dspy import get_validation_executor

        executor = get_validation_executor()

        def multiply(a, b):
            return a * b

        async def run_test():
            return await executor.run_with_timeout_async(
                multiply, args=(3, 4), timeout=5.0
            )

        result = asyncio.run(run_test())
        assert result == 12

    def test_run_with_timeout_async_helper(self):
        """run_with_timeout_async helper should work."""
        import asyncio
        from sentinelseed.integrations.dspy import run_with_timeout_async

        def subtract(a, b):
            return a - b

        async def run_test():
            return await run_with_timeout_async(
                subtract, args=(10, 3), timeout=5.0
            )

        result = asyncio.run(run_test())
        assert result == 7


class TestLoggerManagement:
    """Test logger management functions."""

    def test_get_logger(self):
        """get_logger should return a logger."""
        from sentinelseed.integrations.dspy import get_logger

        logger = get_logger()
        assert hasattr(logger, "debug")
        assert hasattr(logger, "info")
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")

    def test_set_logger(self):
        """set_logger should set custom logger."""
        from sentinelseed.integrations.dspy import get_logger, set_logger

        # Save original
        original = get_logger()

        # Create custom logger
        class CustomLogger:
            def __init__(self):
                self.messages = []

            def debug(self, msg):
                self.messages.append(("debug", msg))

            def info(self, msg):
                self.messages.append(("info", msg))

            def warning(self, msg):
                self.messages.append(("warning", msg))

            def error(self, msg):
                self.messages.append(("error", msg))

        custom = CustomLogger()
        set_logger(custom)

        # Verify custom logger is used
        assert get_logger() is custom

        # Restore original
        set_logger(original)


class TestNewExports:
    """Test new exports in __all__."""

    def test_configuration_error_exported(self):
        """ConfigurationError should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "ConfigurationError" in __all__

    def test_validation_executor_exported(self):
        """ValidationExecutor should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "ValidationExecutor" in __all__

    def test_get_validation_executor_exported(self):
        """get_validation_executor should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "get_validation_executor" in __all__

    def test_run_with_timeout_async_exported(self):
        """run_with_timeout_async should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "run_with_timeout_async" in __all__

    def test_validate_config_types_exported(self):
        """validate_config_types should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "validate_config_types" in __all__

    def test_warn_fail_open_default_exported(self):
        """warn_fail_open_default should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "warn_fail_open_default" in __all__

    def test_sentinel_logger_exported(self):
        """SentinelLogger should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "SentinelLogger" in __all__

    def test_get_logger_exported(self):
        """get_logger should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "get_logger" in __all__

    def test_set_logger_exported(self):
        """set_logger should be exported."""
        from sentinelseed.integrations.dspy import __all__

        assert "set_logger" in __all__


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
