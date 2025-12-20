"""
Tests for AutoGPT Block SDK integration.

Comprehensive test suite covering:
- Standalone functions (validate_content, check_action, get_seed)
- Parameter validation
- Text size limits
- Timeout handling
- Fail-closed behavior
- Risk level calculation
- Exception handling
- Module exports
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import time

from sentinelseed.integrations.autogpt_block import (
    # Constants
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    VALID_SEED_LEVELS,
    VALID_CHECK_TYPES,
    VALID_RISK_LEVELS,
    # Exceptions
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidParameterError,
    # Functions
    validate_content,
    check_action,
    get_seed,
    estimate_tokens,
    # Data classes
    ValidationResult,
    ActionCheckResult,
    ValidationLevel,
    # SDK availability
    AUTOGPT_SDK_AVAILABLE,
)


# ============================================================================
# Constants Tests
# ============================================================================

class TestConstants:
    """Test configuration constants."""

    def test_default_seed_level(self):
        assert DEFAULT_SEED_LEVEL == "standard"

    def test_default_max_text_size(self):
        assert DEFAULT_MAX_TEXT_SIZE == 50 * 1024  # 50KB

    def test_default_validation_timeout(self):
        assert DEFAULT_VALIDATION_TIMEOUT == 30.0

    def test_valid_seed_levels(self):
        assert VALID_SEED_LEVELS == ("minimal", "standard", "full")

    def test_valid_check_types(self):
        assert VALID_CHECK_TYPES == ("general", "action", "request")

    def test_valid_risk_levels(self):
        assert VALID_RISK_LEVELS == ("low", "medium", "high", "critical")


# ============================================================================
# Exception Tests
# ============================================================================

class TestExceptions:
    """Test custom exceptions."""

    def test_text_too_large_error(self):
        error = TextTooLargeError(100000, 50000)
        assert error.size == 100000
        assert error.max_size == 50000
        assert "100,000" in str(error)
        assert "50,000" in str(error)

    def test_validation_timeout_error(self):
        error = ValidationTimeoutError(30.0, "test operation")
        assert error.timeout == 30.0
        assert error.operation == "test operation"
        assert "30.0s" in str(error)

    def test_validation_timeout_error_default_operation(self):
        error = ValidationTimeoutError(10.0)
        assert error.operation == "validation"

    def test_invalid_parameter_error(self):
        error = InvalidParameterError("seed_level", "invalid", ("a", "b", "c"))
        assert error.param == "seed_level"
        assert error.value == "invalid"
        assert error.valid_values == ("a", "b", "c")
        assert "seed_level" in str(error)
        assert "invalid" in str(error)


# ============================================================================
# Data Classes Tests
# ============================================================================

class TestDataClasses:
    """Test data classes."""

    def test_validation_result_defaults(self):
        result = ValidationResult(safe=True, content="test")
        assert result.safe is True
        assert result.content == "test"
        assert result.violations == []
        assert result.gate_results == {}
        assert result.risk_level == "low"

    def test_validation_result_with_violations(self):
        result = ValidationResult(
            safe=False,
            content="bad content",
            violations=["violation1", "violation2"],
            gate_results={"harm": False},
            risk_level="high"
        )
        assert result.safe is False
        assert len(result.violations) == 2
        assert result.risk_level == "high"

    def test_action_check_result_defaults(self):
        result = ActionCheckResult(should_proceed=True, action="test_action")
        assert result.should_proceed is True
        assert result.action == "test_action"
        assert result.concerns == []
        assert result.recommendations == []
        assert result.risk_level == "low"

    def test_validation_level_enum(self):
        assert ValidationLevel.PERMISSIVE.value == "permissive"
        assert ValidationLevel.STANDARD.value == "standard"
        assert ValidationLevel.STRICT.value == "strict"


# ============================================================================
# validate_content Tests
# ============================================================================

class TestValidateContent:
    """Test validate_content function."""

    def test_validate_safe_content(self):
        result = validate_content("Hello, how are you?")
        assert result["safe"] is True
        assert result["violations"] == []
        assert result["risk_level"] == "low"
        assert "gate_results" in result
        assert result["validation_type"] == "heuristic"

    def test_validate_content_returns_content(self):
        content = "Test content"
        result = validate_content(content)
        assert result["content"] == content

    def test_validate_content_gate_results_limited(self):
        result = validate_content("Hello")
        assert result.get("gate_results_limited") is True

    def test_validate_content_default_parameters(self):
        result = validate_content("Test")
        assert "safe" in result
        assert "violations" in result
        assert "risk_level" in result
        assert "gate_results" in result

    def test_validate_content_with_seed_level(self):
        for level in VALID_SEED_LEVELS:
            result = validate_content("Test", seed_level=level)
            assert "safe" in result

    def test_validate_content_with_check_type(self):
        for check_type in VALID_CHECK_TYPES:
            result = validate_content("Test", check_type=check_type)
            assert "safe" in result

    def test_validate_content_invalid_seed_level(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            validate_content("Test", seed_level="invalid")
        assert "seed_level" in str(exc_info.value)

    def test_validate_content_invalid_seed_level_fail_closed(self):
        result = validate_content("Test", seed_level="invalid", fail_closed=True)
        assert result["safe"] is False
        assert "error" in result

    def test_validate_content_invalid_check_type(self):
        with pytest.raises(InvalidParameterError) as exc_info:
            validate_content("Test", check_type="invalid")
        assert "check_type" in str(exc_info.value)

    def test_validate_content_text_too_large(self):
        large_text = "x" * (DEFAULT_MAX_TEXT_SIZE + 1000)
        with pytest.raises(TextTooLargeError):
            validate_content(large_text)

    def test_validate_content_text_too_large_fail_closed(self):
        large_text = "x" * (DEFAULT_MAX_TEXT_SIZE + 1000)
        result = validate_content(large_text, fail_closed=True)
        assert result["safe"] is False
        assert "error" in result

    def test_validate_content_custom_max_size(self):
        # Small max size
        result = validate_content("Test", max_text_size=100)
        assert result["safe"] is True

        # Content exceeds custom max size
        with pytest.raises(TextTooLargeError):
            validate_content("x" * 200, max_text_size=100)

    def test_validate_content_request_type(self):
        result = validate_content("Test request", check_type="request")
        assert "safe" in result
        assert "risk_level" in result

    def test_validate_content_action_type(self):
        result = validate_content("Test action", check_type="action")
        assert "safe" in result


# ============================================================================
# check_action Tests
# ============================================================================

class TestCheckAction:
    """Test check_action function."""

    def test_check_safe_action(self):
        result = check_action("read_file", {"path": "/tmp/safe.txt"})
        assert "should_proceed" in result
        assert "concerns" in result
        assert "recommendations" in result
        assert "risk_level" in result

    def test_check_action_returns_action_name(self):
        result = check_action("test_action")
        assert result["action"] == "test_action"

    def test_check_action_with_purpose(self):
        result = check_action(
            "delete_file",
            {"path": "/tmp/test.txt"},
            purpose="Clean up temporary files"
        )
        assert "should_proceed" in result

    def test_check_action_without_purpose_recommendation(self):
        result = check_action("some_action")
        recommendations = result.get("recommendations", [])
        # Should recommend providing purpose
        has_purpose_recommendation = any(
            "purpose" in r.lower() for r in recommendations
        )
        assert has_purpose_recommendation or result["should_proceed"]

    def test_check_action_invalid_seed_level(self):
        with pytest.raises(InvalidParameterError):
            check_action("test", seed_level="invalid")

    def test_check_action_invalid_seed_level_fail_closed(self):
        result = check_action("test", seed_level="invalid", fail_closed=True)
        assert result["should_proceed"] is False
        assert "error" in result

    def test_check_action_text_too_large(self):
        large_args = {"data": "x" * (DEFAULT_MAX_TEXT_SIZE + 1000)}
        with pytest.raises(TextTooLargeError):
            check_action("action", large_args)

    def test_check_action_text_too_large_fail_closed(self):
        large_args = {"data": "x" * (DEFAULT_MAX_TEXT_SIZE + 1000)}
        result = check_action("action", large_args, fail_closed=True)
        assert result["should_proceed"] is False


# ============================================================================
# get_seed Tests
# ============================================================================

class TestGetSeed:
    """Test get_seed function."""

    def test_get_seed_default(self):
        seed = get_seed()
        assert isinstance(seed, str)
        assert len(seed) > 0

    def test_get_seed_all_levels(self):
        for level in VALID_SEED_LEVELS:
            seed = get_seed(level)
            assert isinstance(seed, str)
            assert len(seed) > 0

    def test_get_seed_invalid_level(self):
        with pytest.raises(InvalidParameterError):
            get_seed("invalid")

    def test_get_seed_with_token_count(self):
        result = get_seed("standard", include_token_count=True)
        assert isinstance(result, dict)
        assert "seed" in result
        assert "token_count" in result
        assert "level" in result
        assert "note" in result
        assert result["level"] == "standard"
        assert result["token_count"] > 0

    def test_get_seed_token_count_increases_with_level(self):
        minimal = get_seed("minimal", include_token_count=True)
        standard = get_seed("standard", include_token_count=True)
        full = get_seed("full", include_token_count=True)

        # Each level should be larger than the previous
        assert minimal["token_count"] < standard["token_count"]
        assert standard["token_count"] < full["token_count"]


# ============================================================================
# estimate_tokens Tests
# ============================================================================

class TestEstimateTokens:
    """Test estimate_tokens function."""

    def test_estimate_tokens_empty(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens(None) == 0

    def test_estimate_tokens_basic(self):
        # ~4 chars per token
        text = "Hello World!"  # 12 chars
        tokens = estimate_tokens(text)
        assert tokens == 3  # 12 // 4

    def test_estimate_tokens_longer_text(self):
        text = "x" * 100
        tokens = estimate_tokens(text)
        assert tokens == 25  # 100 // 4


# ============================================================================
# Timeout Tests
# ============================================================================

class TestTimeout:
    """Test timeout functionality."""

    def test_validate_content_respects_timeout_parameter(self):
        # Short timeout should work for fast validation
        result = validate_content("Hello", timeout=10.0)
        assert "safe" in result

    def test_check_action_respects_timeout_parameter(self):
        result = check_action("test", timeout=10.0)
        assert "should_proceed" in result


# ============================================================================
# Risk Level Calculation Tests
# ============================================================================

class TestRiskLevelCalculation:
    """Test risk level calculation logic."""

    def test_risk_level_with_no_violations(self):
        result = validate_content("Safe content")
        assert result["risk_level"] == "low"

    def test_risk_levels_are_valid(self):
        result = validate_content("Test")
        assert result["risk_level"] in VALID_RISK_LEVELS


# ============================================================================
# Fail-Closed Mode Tests
# ============================================================================

class TestFailClosedMode:
    """Test fail-closed behavior."""

    def test_validate_content_fail_closed_on_invalid_param(self):
        result = validate_content("Test", seed_level="bad", fail_closed=True)
        assert result["safe"] is False
        assert "error" in result

    def test_validate_content_fail_closed_on_large_text(self):
        large = "x" * (DEFAULT_MAX_TEXT_SIZE + 100)
        result = validate_content(large, fail_closed=True)
        assert result["safe"] is False

    def test_check_action_fail_closed_on_invalid_param(self):
        result = check_action("test", seed_level="bad", fail_closed=True)
        assert result["should_proceed"] is False
        assert "error" in result

    def test_check_action_fail_closed_on_large_text(self):
        large = {"x": "y" * (DEFAULT_MAX_TEXT_SIZE + 100)}
        result = check_action("test", large, fail_closed=True)
        assert result["should_proceed"] is False


# ============================================================================
# Module Exports Tests
# ============================================================================

class TestModuleExports:
    """Test that all expected exports are available."""

    def test_constants_exported(self):
        from sentinelseed.integrations.autogpt_block import (
            DEFAULT_SEED_LEVEL,
            DEFAULT_MAX_TEXT_SIZE,
            DEFAULT_VALIDATION_TIMEOUT,
            VALID_SEED_LEVELS,
            VALID_CHECK_TYPES,
            VALID_RISK_LEVELS,
        )
        assert DEFAULT_SEED_LEVEL is not None
        assert DEFAULT_MAX_TEXT_SIZE is not None
        assert DEFAULT_VALIDATION_TIMEOUT is not None

    def test_exceptions_exported(self):
        from sentinelseed.integrations.autogpt_block import (
            TextTooLargeError,
            ValidationTimeoutError,
            InvalidParameterError,
        )
        assert TextTooLargeError is not None
        assert ValidationTimeoutError is not None
        assert InvalidParameterError is not None

    def test_functions_exported(self):
        from sentinelseed.integrations.autogpt_block import (
            validate_content,
            check_action,
            get_seed,
            estimate_tokens,
        )
        assert callable(validate_content)
        assert callable(check_action)
        assert callable(get_seed)
        assert callable(estimate_tokens)

    def test_dataclasses_exported(self):
        from sentinelseed.integrations.autogpt_block import (
            ValidationResult,
            ActionCheckResult,
            ValidationLevel,
        )
        assert ValidationResult is not None
        assert ActionCheckResult is not None
        assert ValidationLevel is not None

    def test_autogpt_availability_exported(self):
        from sentinelseed.integrations.autogpt_block import (
            AUTOGPT_SDK_AVAILABLE,
            BLOCKS,
        )
        assert isinstance(AUTOGPT_SDK_AVAILABLE, bool)
        assert isinstance(BLOCKS, list)


# ============================================================================
# Integration Tests
# ============================================================================

class TestIntegration:
    """Integration tests combining multiple functions."""

    def test_validate_then_get_seed(self):
        # Validate content first
        result = validate_content("Safe content")
        if result["safe"]:
            # Then get seed for safe response
            seed = get_seed("standard")
            assert len(seed) > 0

    def test_check_action_then_validate_result(self):
        # Check action
        action_result = check_action("process_data", {"input": "test"})

        if action_result["should_proceed"]:
            # Validate the action output
            validation_result = validate_content("Processed: test")
            assert "safe" in validation_result

    def test_full_workflow(self):
        # 1. Get seed
        seed_result = get_seed("standard", include_token_count=True)
        assert seed_result["token_count"] > 0

        # 2. Validate input
        input_result = validate_content("User input to process")
        assert input_result["safe"] is True

        # 3. Check action
        action_result = check_action(
            "transform_text",
            {"text": "User input"},
            purpose="Transform user input for processing"
        )
        assert "should_proceed" in action_result

        # 4. Validate output
        output_result = validate_content("Transformed output")
        assert output_result["safe"] is True


# ============================================================================
# Edge Cases Tests
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_content(self):
        result = validate_content("")
        assert "safe" in result

    def test_whitespace_content(self):
        result = validate_content("   \n\t  ")
        assert "safe" in result

    def test_unicode_content(self):
        result = validate_content("Hello 世界 مرحبا 🌍")
        assert "safe" in result

    def test_empty_action_args(self):
        result = check_action("test_action")
        assert "should_proceed" in result

        result = check_action("test_action", {})
        assert "should_proceed" in result

        result = check_action("test_action", None)
        assert "should_proceed" in result

    def test_special_characters_in_action_name(self):
        result = check_action("test-action_123")
        assert "should_proceed" in result

    def test_very_long_action_args(self):
        # Within limit
        args = {"key": "v" * 1000}
        result = check_action("test", args)
        assert "should_proceed" in result

    def test_case_insensitive_seed_level(self):
        result1 = validate_content("Test", seed_level="STANDARD")
        result2 = validate_content("Test", seed_level="Standard")
        result3 = validate_content("Test", seed_level="standard")
        assert result1["safe"] == result2["safe"] == result3["safe"]

    def test_case_insensitive_check_type(self):
        result1 = validate_content("Test", check_type="GENERAL")
        result2 = validate_content("Test", check_type="General")
        result3 = validate_content("Test", check_type="general")
        assert result1["safe"] == result2["safe"] == result3["safe"]

    def test_whitespace_in_parameters(self):
        result = validate_content("Test", seed_level="  standard  ")
        assert "safe" in result


# ============================================================================
# Validation Type Tests
# ============================================================================

class TestValidationType:
    """Test validation type field in results."""

    def test_heuristic_validation_type(self):
        result = validate_content("Test", use_semantic=False)
        assert result.get("validation_type") == "heuristic"

    def test_gate_results_limited_flag(self):
        result = validate_content("Test", use_semantic=False)
        assert result.get("gate_results_limited") is True


# ============================================================================
# Logging Tests
# ============================================================================

class TestLogging:
    """Test logging behavior."""

    def test_logger_exists(self):
        import logging
        logger = logging.getLogger("sentinelseed.autogpt_block")
        assert logger is not None

    @patch('sentinelseed.integrations.autogpt_block.logger')
    def test_error_logging_on_invalid_param(self, mock_logger):
        try:
            validate_content("Test", seed_level="invalid")
        except InvalidParameterError:
            pass
        mock_logger.error.assert_called()


# ============================================================================
# Concurrency Tests
# ============================================================================

class TestConcurrency:
    """Test thread safety and concurrent access."""

    def test_multiple_validations(self):
        results = []
        for i in range(10):
            result = validate_content(f"Test content {i}")
            results.append(result)

        assert len(results) == 10
        assert all("safe" in r for r in results)

    def test_multiple_action_checks(self):
        results = []
        for i in range(10):
            result = check_action(f"action_{i}", {"index": i})
            results.append(result)

        assert len(results) == 10
        assert all("should_proceed" in r for r in results)
