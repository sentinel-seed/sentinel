"""
Tests for Agent Validation integration.

Run with: python -m pytest test_agent_validation.py -v
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from dataclasses import dataclass

from sentinelseed.integrations.agent_validation import (
    ValidationResult,
    SafetyValidator,
    AsyncSafetyValidator,
    ExecutionGuard,
    safety_check,
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidProviderError,
    VALID_PROVIDERS,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_HISTORY_LIMIT,
    DEFAULT_VALIDATION_TIMEOUT,
)
from sentinelseed.validators.semantic import THSPResult, RiskLevel


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_thsp_safe():
    """Create a safe THSPResult."""
    return THSPResult(
        is_safe=True,
        truth_passes=True,
        harm_passes=True,
        scope_passes=True,
        purpose_passes=True,
        violated_gate=None,
        reasoning="Action is safe and has legitimate purpose.",
        risk_level=RiskLevel.LOW,
    )


@pytest.fixture
def mock_thsp_unsafe():
    """Create an unsafe THSPResult."""
    return THSPResult(
        is_safe=False,
        truth_passes=True,
        harm_passes=False,
        scope_passes=True,
        purpose_passes=False,
        violated_gate="harm",
        reasoning="Action could cause harm.",
        risk_level=RiskLevel.HIGH,
    )


@pytest.fixture
def mock_semantic_validator(mock_thsp_safe):
    """Create a mock SemanticValidator."""
    mock = Mock()
    mock.validate_action.return_value = mock_thsp_safe
    mock.validate.return_value = mock_thsp_safe
    mock.get_stats.return_value = {"provider": "openai", "model": "gpt-4o-mini"}
    return mock


@pytest.fixture
def mock_sentinel():
    """Create a mock Sentinel."""
    mock = Mock()
    mock.get_seed.return_value = "test seed content"
    return mock


@pytest.fixture
def mock_async_semantic_validator(mock_thsp_safe):
    """Create a mock AsyncSemanticValidator."""
    mock = AsyncMock()
    mock.validate_action.return_value = mock_thsp_safe
    mock.validate.return_value = mock_thsp_safe
    return mock


# ============================================================================
# ValidationResult Tests
# ============================================================================


class TestValidationResult:
    """Tests for ValidationResult dataclass."""

    def test_create_basic(self):
        """Test basic creation."""
        result = ValidationResult(
            safe=True,
            action="test action",
        )
        assert result.safe is True
        assert result.action == "test action"
        assert result.concerns == []
        assert result.risk_level == "low"
        assert result.should_proceed is True
        assert result.reasoning == ""
        assert result.gate_results == {}

    def test_create_full(self):
        """Test creation with all fields."""
        result = ValidationResult(
            safe=False,
            action="dangerous action",
            concerns=["Could cause harm", "No purpose"],
            risk_level="high",
            should_proceed=False,
            reasoning="This is dangerous.",
            gate_results={"truth": True, "harm": False},
        )
        assert result.safe is False
        assert len(result.concerns) == 2
        assert result.risk_level == "high"
        assert result.should_proceed is False

    def test_from_thsp_safe(self, mock_thsp_safe):
        """Test creation from safe THSPResult."""
        result = ValidationResult.from_thsp(mock_thsp_safe, "test action")

        assert result.safe is True
        assert result.should_proceed is True
        assert result.action == "test action"
        assert len(result.concerns) == 0
        assert result.risk_level == "low"
        assert result.reasoning == mock_thsp_safe.reasoning

    def test_from_thsp_unsafe(self, mock_thsp_unsafe):
        """Test creation from unsafe THSPResult."""
        result = ValidationResult.from_thsp(mock_thsp_unsafe, "bad action")

        assert result.safe is False
        assert result.should_proceed is False
        assert "Failed Harm gate" in result.concerns[0]
        assert "Failed Purpose gate" in result.concerns[1]
        assert result.risk_level == "high"

    def test_from_thsp_truncates_action(self, mock_thsp_safe):
        """Test that long actions are truncated."""
        long_action = "x" * 200
        result = ValidationResult.from_thsp(mock_thsp_safe, long_action)

        assert len(result.action) == 100

    def test_error_result(self):
        """Test error result creation."""
        error = ValueError("Test error")
        result = ValidationResult.error_result("failed action", error)

        assert result.safe is False
        assert result.should_proceed is False
        assert "ValueError" in result.concerns[0]
        assert result.risk_level == "high"
        assert "Test error" in result.reasoning


# ============================================================================
# Exception Tests
# ============================================================================


class TestExceptions:
    """Tests for custom exceptions."""

    def test_text_too_large_error(self):
        """Test TextTooLargeError."""
        error = TextTooLargeError(size=100000, max_size=50000)

        assert error.size == 100000
        assert error.max_size == 50000
        assert "100,000" in str(error)
        assert "50,000" in str(error)

    def test_validation_timeout_error(self):
        """Test ValidationTimeoutError."""
        error = ValidationTimeoutError(timeout=30.0)

        assert error.timeout == 30.0
        assert "30.0" in str(error)

    def test_invalid_provider_error(self):
        """Test InvalidProviderError."""
        error = InvalidProviderError(provider="invalid")

        assert error.provider == "invalid"
        assert "invalid" in str(error)
        assert "openai" in str(error)
        assert "anthropic" in str(error)


# ============================================================================
# SafetyValidator Tests
# ============================================================================


class TestSafetyValidator:
    """Tests for SafetyValidator class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator()

        assert validator.provider == "openai"
        assert validator.model is None
        assert validator.block_unsafe is True
        assert validator.log_checks is True
        assert validator.max_text_size == DEFAULT_MAX_TEXT_SIZE
        assert validator.history_limit == DEFAULT_HISTORY_LIMIT
        assert validator.validation_timeout == DEFAULT_VALIDATION_TIMEOUT
        assert validator.fail_closed is False

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(
                    provider="anthropic",
                    model="claude-3-haiku",
                    max_text_size=1024,
                    history_limit=100,
                    validation_timeout=10.0,
                    fail_closed=True,
                )

        assert validator.provider == "anthropic"
        assert validator.model == "claude-3-haiku"
        assert validator.max_text_size == 1024
        assert validator.history_limit == 100
        assert validator.validation_timeout == 10.0
        assert validator.fail_closed is True

    def test_init_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(InvalidProviderError):
            SafetyValidator(provider="invalid")

    def test_validate_text_size_ok(self):
        """Test text size validation passes for small text."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(max_text_size=1000)

        # Should not raise
        validator._validate_text_size("small text")

    def test_validate_text_size_exceeds(self):
        """Test text size validation fails for large text."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(max_text_size=10)

        with pytest.raises(TextTooLargeError) as exc_info:
            validator._validate_text_size("this is a long text")

        assert exc_info.value.max_size == 10

    def test_validate_action_success(self, mock_semantic_validator, mock_thsp_safe):
        """Test successful action validation."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator()

        result = validator.validate_action("safe action")

        assert result.safe is True
        assert result.should_proceed is True
        mock_semantic_validator.validate_action.assert_called_once()

    def test_validate_action_with_purpose(self, mock_semantic_validator, mock_thsp_safe):
        """Test action validation with purpose."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator()

        result = validator.validate_action("action", purpose="legitimate purpose")

        call_args = mock_semantic_validator.validate_action.call_args
        assert call_args.kwargs["purpose"] == "legitimate purpose"

    def test_validate_action_text_too_large(self):
        """Test action validation with oversized text."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(max_text_size=10)

        with pytest.raises(TextTooLargeError):
            validator.validate_action("this is a very long action text")

    def test_validate_action_fail_open(self, mock_semantic_validator):
        """Test fail-open behavior on error."""
        mock_semantic_validator.validate_action.side_effect = RuntimeError("API error")

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(fail_closed=False)

        result = validator.validate_action("action")

        assert result.safe is True  # Fail open
        assert result.should_proceed is True
        assert "fail-open" in result.concerns[0]

    def test_validate_action_fail_closed(self, mock_semantic_validator):
        """Test fail-closed behavior on error."""
        mock_semantic_validator.validate_action.side_effect = RuntimeError("API error")

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(fail_closed=True)

        result = validator.validate_action("action")

        assert result.safe is False  # Fail closed
        assert result.should_proceed is False

    def test_validate_thought(self, mock_semantic_validator, mock_thsp_safe):
        """Test thought validation."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator()

        result = validator.validate_thought("thinking about safety")

        assert result.safe is True
        mock_semantic_validator.validate.assert_called_once()
        assert "Agent thought:" in mock_semantic_validator.validate.call_args[0][0]

    def test_validate_output(self, mock_semantic_validator, mock_thsp_safe):
        """Test output validation."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator()

        result = validator.validate_output("safe output")

        assert result.safe is True
        assert "Agent output" in mock_semantic_validator.validate.call_args[0][0]

    def test_history_tracking(self, mock_semantic_validator, mock_thsp_safe):
        """Test history tracking."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(log_checks=True)

        validator.validate_action("action 1")
        validator.validate_action("action 2")

        history = validator.get_history()
        assert len(history) == 2

    def test_history_limit(self, mock_semantic_validator, mock_thsp_safe):
        """Test history limit is enforced."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(history_limit=3, log_checks=True)

        for i in range(5):
            validator.validate_action(f"action {i}")

        history = validator.get_history()
        assert len(history) == 3

    def test_clear_history(self, mock_semantic_validator, mock_thsp_safe):
        """Test history clearing."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(log_checks=True)

        validator.validate_action("action")
        assert len(validator.get_history()) == 1

        validator.clear_history()
        assert len(validator.get_history()) == 0

    def test_check_history_property(self, mock_semantic_validator, mock_thsp_safe):
        """Test backward-compatible check_history property."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(log_checks=True)

        validator.validate_action("action")

        # Both should work
        assert len(validator.check_history) == 1
        assert len(validator.get_history()) == 1

    def test_get_stats_empty(self):
        """Test stats with no checks."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator()

        stats = validator.get_stats()
        assert stats["total_checks"] == 0

    def test_get_stats_with_checks(self, mock_semantic_validator, mock_thsp_safe, mock_thsp_unsafe):
        """Test stats with checks."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = SafetyValidator(log_checks=True)

        # Safe check
        validator.validate_action("safe")

        # Unsafe check
        mock_semantic_validator.validate_action.return_value = mock_thsp_unsafe
        validator.validate_action("unsafe")

        stats = validator.get_stats()
        assert stats["total_checks"] == 2
        assert stats["blocked"] == 1
        assert stats["allowed"] == 1
        assert stats["block_rate"] == 0.5

    def test_get_seed(self):
        """Test seed retrieval."""
        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "test seed content"

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", return_value=mock_sentinel):
                validator = SafetyValidator()

        seed = validator.get_seed()
        assert seed == "test seed content"


# ============================================================================
# AsyncSafetyValidator Tests
# ============================================================================


class TestAsyncSafetyValidator:
    """Tests for AsyncSafetyValidator class."""

    def test_init_defaults(self):
        """Test initialization with defaults."""
        with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = AsyncSafetyValidator()

        assert validator.provider == "openai"
        assert validator.max_text_size == DEFAULT_MAX_TEXT_SIZE

    def test_init_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(InvalidProviderError):
            AsyncSafetyValidator(provider="invalid")

    def test_validate_action_success(self, mock_async_semantic_validator, mock_thsp_safe):
        """Test successful async action validation."""
        async def run_test():
            with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator", return_value=mock_async_semantic_validator):
                with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                    validator = AsyncSafetyValidator()

            result = await validator.validate_action("safe action")

            assert result.safe is True
            assert result.should_proceed is True

        asyncio.run(run_test())

    def test_validate_action_timeout(self, mock_async_semantic_validator, mock_thsp_safe):
        """Test timeout handling."""
        async def run_test():
            async def slow_validate(*args, **kwargs):
                await asyncio.sleep(10)
                return mock_thsp_safe

            mock_async_semantic_validator.validate_action = slow_validate

            with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator", return_value=mock_async_semantic_validator):
                with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                    validator = AsyncSafetyValidator(validation_timeout=0.01)

            with pytest.raises(ValidationTimeoutError):
                await validator.validate_action("action")

        asyncio.run(run_test())

    def test_validate_thought(self, mock_async_semantic_validator, mock_thsp_safe):
        """Test async thought validation."""
        async def run_test():
            with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator", return_value=mock_async_semantic_validator):
                with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                    validator = AsyncSafetyValidator()

            result = await validator.validate_thought("thinking")
            assert result.safe is True

        asyncio.run(run_test())

    def test_validate_output(self, mock_async_semantic_validator, mock_thsp_safe):
        """Test async output validation."""
        async def run_test():
            with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator", return_value=mock_async_semantic_validator):
                with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                    validator = AsyncSafetyValidator()

            result = await validator.validate_output("output")
            assert result.safe is True

        asyncio.run(run_test())

    def test_get_history(self):
        """Test async validator has get_history."""
        with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = AsyncSafetyValidator()

        assert hasattr(validator, 'get_history')
        assert len(validator.get_history()) == 0

    def test_clear_history(self):
        """Test async validator has clear_history."""
        with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = AsyncSafetyValidator()

        assert hasattr(validator, 'clear_history')
        validator.clear_history()  # Should not raise

    def test_check_history_property(self):
        """Test async validator has check_history property."""
        with patch("sentinelseed.integrations.agent_validation.AsyncSemanticValidator"):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                validator = AsyncSafetyValidator()

        assert hasattr(validator, 'check_history')
        assert validator.check_history == []


# ============================================================================
# ExecutionGuard Tests
# ============================================================================


class TestExecutionGuard:
    """Tests for ExecutionGuard class."""

    def test_init(self, mock_semantic_validator):
        """Test guard initialization."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        assert guard.validator is not None

    def test_init_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(InvalidProviderError):
            ExecutionGuard(provider="invalid")

    def test_extract_action_string(self, mock_semantic_validator):
        """Test action extraction from string."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        action = guard._extract_action(("test command",), {})
        assert action == "test command"

    def test_extract_action_dict_with_action_key(self, mock_semantic_validator):
        """Test action extraction from dict with 'action' key."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        action = guard._extract_action(({"action": "do something"},), {})
        assert action == "do something"

    def test_extract_action_dict_with_command_key(self, mock_semantic_validator):
        """Test action extraction from dict with 'command' key."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        action = guard._extract_action(({"command": "run this"},), {})
        assert action == "run this"

    def test_extract_action_object_with_attribute(self, mock_semantic_validator):
        """Test action extraction from object with attribute."""

        @dataclass
        class Command:
            action: str

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        action = guard._extract_action((Command(action="object action"),), {})
        assert action == "object action"

    def test_extract_action_kwargs(self, mock_semantic_validator):
        """Test action extraction from kwargs."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        action = guard._extract_action((), {"query": "search this"})
        assert action == "search this"

    def test_extract_action_custom_extractor(self, mock_semantic_validator):
        """Test custom action extractor."""
        def custom_extractor(*args, **kwargs):
            return kwargs.get("custom_field", "default")

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard(action_extractor=custom_extractor)

        action = guard._extract_action((), {"custom_field": "custom value"})
        assert action == "custom value"

    def test_protected_decorator_allows_safe(self, mock_semantic_validator, mock_thsp_safe):
        """Test decorator allows safe actions."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        @guard.protected
        def my_function(cmd: str) -> str:
            return f"executed: {cmd}"

        result = my_function("safe command")
        assert result == "executed: safe command"

    def test_protected_decorator_blocks_unsafe(self, mock_semantic_validator, mock_thsp_unsafe):
        """Test decorator blocks unsafe actions."""
        mock_semantic_validator.validate_action.return_value = mock_thsp_unsafe

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        @guard.protected
        def my_function(cmd: str) -> str:
            return f"executed: {cmd}"

        result = my_function("dangerous command")

        assert isinstance(result, dict)
        assert result["success"] is False
        assert result["blocked"] is True
        assert "reason" in result

    def test_protected_decorator_validates_output(self, mock_semantic_validator, mock_thsp_safe, mock_thsp_unsafe):
        """Test decorator validates string output."""
        # First call (action) succeeds, second call (output) fails
        mock_semantic_validator.validate_action.return_value = mock_thsp_safe
        mock_semantic_validator.validate.return_value = mock_thsp_unsafe

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        @guard.protected
        def my_function(cmd: str) -> str:
            return "dangerous output"

        result = my_function("command")

        assert isinstance(result, dict)
        assert result["blocked"] is True
        assert "original_output" in result

    def test_check_method(self, mock_semantic_validator, mock_thsp_safe):
        """Test manual check method."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        result = guard.check("some action")

        assert isinstance(result, ValidationResult)
        assert result.safe is True

    def test_get_stats(self, mock_semantic_validator):
        """Test guard statistics."""
        mock_semantic_validator.get_stats.return_value = {"provider": "openai", "model": "gpt-4o-mini"}

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                guard = ExecutionGuard()

        stats = guard.get_stats()
        assert "total_checks" in stats


# ============================================================================
# safety_check Function Tests
# ============================================================================


class TestSafetyCheck:
    """Tests for safety_check function."""

    def test_basic_usage(self, mock_semantic_validator, mock_thsp_safe):
        """Test basic safety_check usage."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                result = safety_check("test action")

        assert isinstance(result, dict)
        assert "safe" in result
        assert "concerns" in result
        assert "risk_level" in result
        assert "reasoning" in result
        assert "gate_results" in result
        assert "should_proceed" in result

    def test_returns_correct_safe_value(self, mock_semantic_validator, mock_thsp_safe):
        """Test that safe value is correct."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                result = safety_check("safe action")

        assert result["safe"] is True
        assert result["should_proceed"] is True

    def test_returns_correct_unsafe_value(self, mock_semantic_validator, mock_thsp_unsafe):
        """Test that unsafe value is correct."""
        mock_semantic_validator.validate_action.return_value = mock_thsp_unsafe

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                result = safety_check("dangerous action")

        assert result["safe"] is False
        assert result["should_proceed"] is False

    def test_with_custom_provider(self, mock_semantic_validator, mock_thsp_safe):
        """Test with custom provider."""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator) as mock_cls:
            with patch("sentinelseed.integrations.agent_validation.Sentinel"):
                result = safety_check("action", provider="anthropic")

        # Verify provider was passed
        call_kwargs = mock_cls.call_args.kwargs
        assert call_kwargs["provider"] == "anthropic"


# ============================================================================
# Constants Tests
# ============================================================================


class TestConstants:
    """Tests for module constants."""

    def test_valid_providers(self):
        """Test VALID_PROVIDERS contains expected values."""
        assert "openai" in VALID_PROVIDERS
        assert "anthropic" in VALID_PROVIDERS
        assert len(VALID_PROVIDERS) == 2

    def test_default_max_text_size(self):
        """Test DEFAULT_MAX_TEXT_SIZE is reasonable."""
        assert DEFAULT_MAX_TEXT_SIZE == 50 * 1024  # 50KB

    def test_default_history_limit(self):
        """Test DEFAULT_HISTORY_LIMIT is reasonable."""
        assert DEFAULT_HISTORY_LIMIT == 1000

    def test_default_validation_timeout(self):
        """Test DEFAULT_VALIDATION_TIMEOUT is reasonable."""
        assert DEFAULT_VALIDATION_TIMEOUT == 30.0


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


class TestBackwardCompatibility:
    """Tests for backward compatibility aliases."""

    def test_safety_check_result_alias(self):
        """Test SafetyCheckResult is alias for ValidationResult."""
        from sentinelseed.integrations.agent_validation import SafetyCheckResult
        assert SafetyCheckResult is ValidationResult

    def test_sentinel_safety_component_alias(self):
        """Test SentinelSafetyComponent is alias for SafetyValidator."""
        from sentinelseed.integrations.agent_validation import SentinelSafetyComponent
        assert SentinelSafetyComponent is SafetyValidator

    def test_sentinel_guard_alias(self):
        """Test SentinelGuard is alias for ExecutionGuard."""
        from sentinelseed.integrations.agent_validation import SentinelGuard
        assert SentinelGuard is ExecutionGuard


# ============================================================================
# Integration Tests (without real API)
# ============================================================================


class TestIntegration:
    """Integration tests with mocked dependencies."""

    def test_full_workflow_safe(self, mock_semantic_validator, mock_thsp_safe):
        """Test complete safe workflow."""
        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "seed content"

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", return_value=mock_sentinel):
                validator = SafetyValidator()

                # Validate action
                result = validator.validate_action("transfer funds", purpose="user request")
                assert result.should_proceed is True

                # Validate thought
                result = validator.validate_thought("processing request")
                assert result.should_proceed is True

                # Validate output
                result = validator.validate_output("Transfer complete")
                assert result.should_proceed is True

                # Check history
                history = validator.get_history()
                assert len(history) == 3

                # Get stats
                stats = validator.get_stats()
                assert stats["total_checks"] == 3
                assert stats["blocked"] == 0

    def test_full_workflow_blocked(self, mock_semantic_validator, mock_thsp_unsafe):
        """Test complete blocked workflow."""
        mock_semantic_validator.validate_action.return_value = mock_thsp_unsafe

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "seed content"

        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", return_value=mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", return_value=mock_sentinel):
                guard = ExecutionGuard()

                @guard.protected
                def execute(cmd: str) -> str:
                    return f"Executed: {cmd}"

                result = execute("dangerous command")

                assert result["blocked"] is True
                assert result["success"] is False

                stats = guard.get_stats()
                assert stats["blocked"] == 1


class TestInputValidationBugs:
    """Tests for input validation bugs fixed in correction #055"""

    def test_validate_action_none_raises_valueerror(self, mock_semantic_validator, mock_sentinel):
        """C001: None input should raise ValueError, not crash"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                validator = SafetyValidator()

        with pytest.raises(ValueError, match="cannot be None"):
            validator.validate_action(None)

    def test_validate_action_int_raises_typeerror(self, mock_semantic_validator, mock_sentinel):
        """C001: Integer input should raise TypeError, not crash"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                validator = SafetyValidator()

        with pytest.raises(TypeError, match="must be a string"):
            validator.validate_action(123)

    def test_validate_action_list_raises_typeerror(self, mock_semantic_validator, mock_sentinel):
        """C001: List input should raise TypeError, not pass with safe=True"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                validator = SafetyValidator()

        with pytest.raises(TypeError, match="must be a string"):
            validator.validate_action(["malicious", "list"])

    def test_validate_thought_none_raises_valueerror(self, mock_semantic_validator, mock_sentinel):
        """C001: None input to validate_thought should raise ValueError"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                validator = SafetyValidator()

        with pytest.raises(ValueError, match="cannot be None"):
            validator.validate_thought(None)

    def test_validate_output_none_raises_valueerror(self, mock_semantic_validator, mock_sentinel):
        """C001: None input to validate_output should raise ValueError"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                validator = SafetyValidator()

        with pytest.raises(ValueError, match="cannot be None"):
            validator.validate_output(None)

    def test_negative_timeout_raises(self, mock_semantic_validator, mock_sentinel):
        """M001: Negative timeout should raise ValueError"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                with pytest.raises(ValueError, match="positive"):
                    SafetyValidator(validation_timeout=-1)

    def test_zero_timeout_raises(self, mock_semantic_validator, mock_sentinel):
        """M001: Zero timeout should raise ValueError"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                with pytest.raises(ValueError, match="positive"):
                    SafetyValidator(validation_timeout=0)

    def test_negative_max_text_size_raises(self, mock_semantic_validator, mock_sentinel):
        """M002: Negative max_text_size should raise ValueError"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                with pytest.raises(ValueError, match="positive"):
                    SafetyValidator(max_text_size=-1)

    def test_zero_max_text_size_raises(self, mock_semantic_validator, mock_sentinel):
        """M002: Zero max_text_size should raise ValueError"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                with pytest.raises(ValueError, match="positive"):
                    SafetyValidator(max_text_size=0)

    def test_execution_guard_none_returns_blocked(self, mock_semantic_validator, mock_sentinel):
        """C002: ExecutionGuard with None input should return blocked"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                guard = ExecutionGuard()

                @guard.protected
                def my_func(action):
                    return f"executed: {action}"

        result = my_func(None)
        assert result["blocked"] is True
        assert result["error_type"] == "ValueError"

    def test_execution_guard_int_returns_blocked(self, mock_semantic_validator, mock_sentinel):
        """C002: ExecutionGuard with int input should return blocked"""
        with patch("sentinelseed.integrations.agent_validation.SemanticValidator", mock_semantic_validator):
            with patch("sentinelseed.integrations.agent_validation.Sentinel", mock_sentinel):
                guard = ExecutionGuard()

                @guard.protected
                def my_func(action):
                    return f"executed: {action}"

        result = my_func(123)
        assert result["blocked"] is True
        assert result["error_type"] == "TypeError"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
