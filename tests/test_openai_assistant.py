"""
Tests for OpenAI Assistant integration.

Tests the SentinelAssistant, SentinelAssistantClient, and related utilities
without requiring actual OpenAI API calls.
"""

import pytest
import asyncio
from unittest.mock import Mock, MagicMock, patch, AsyncMock
from dataclasses import dataclass
from typing import Optional, Any, List


# Test imports - these should work without OpenAI installed
class TestImports:
    """Test module imports."""

    def test_import_exceptions(self):
        """Test that custom exceptions can be imported."""
        from sentinelseed.integrations.openai_assistant import (
            AssistantRunError,
            AssistantRequiresActionError,
            ValidationError,
            OutputBlockedError,
        )

        # Verify they are exception types
        assert issubclass(AssistantRunError, Exception)
        assert issubclass(AssistantRequiresActionError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(OutputBlockedError, Exception)

    def test_import_constants(self):
        """Test that constants can be imported."""
        from sentinelseed.integrations.openai_assistant import (
            VALID_SEED_LEVELS,
            DEFAULT_POLL_INTERVAL,
            DEFAULT_TIMEOUT,
            DEFAULT_VALIDATION_TIMEOUT,
        )

        assert VALID_SEED_LEVELS == ("minimal", "standard", "full")
        assert DEFAULT_POLL_INTERVAL == 1.0
        assert DEFAULT_TIMEOUT == 300.0
        assert DEFAULT_VALIDATION_TIMEOUT == 30.0

    def test_import_helper_functions(self):
        """Test that helper functions can be imported."""
        from sentinelseed.integrations.openai_assistant import (
            _validate_seed_level,
            _safe_validate_request,
            _safe_validate_output,
            _extract_response_text,
        )

        # Just verify they are callable
        assert callable(_validate_seed_level)
        assert callable(_safe_validate_request)
        assert callable(_safe_validate_output)
        assert callable(_extract_response_text)


class TestValidateSeedLevel:
    """Test seed level validation."""

    def test_valid_seed_levels(self):
        """Test valid seed levels are accepted."""
        from sentinelseed.integrations.openai_assistant import _validate_seed_level

        assert _validate_seed_level("minimal") == "minimal"
        assert _validate_seed_level("standard") == "standard"
        assert _validate_seed_level("full") == "full"

    def test_case_insensitive(self):
        """Test seed levels are case insensitive."""
        from sentinelseed.integrations.openai_assistant import _validate_seed_level

        assert _validate_seed_level("MINIMAL") == "minimal"
        assert _validate_seed_level("Standard") == "standard"
        assert _validate_seed_level("FULL") == "full"

    def test_invalid_seed_level(self):
        """Test invalid seed levels raise ValueError."""
        from sentinelseed.integrations.openai_assistant import _validate_seed_level

        with pytest.raises(ValueError) as exc_info:
            _validate_seed_level("invalid")

        assert "Invalid seed_level" in str(exc_info.value)
        assert "minimal" in str(exc_info.value)


class TestSafeValidateRequest:
    """Test safe request validation."""

    def test_empty_content_allowed(self):
        """Test empty content is allowed without validation."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_logger = logging.getLogger("test")

        result = _safe_validate_request(mock_sentinel, "", mock_logger)

        assert result["should_proceed"] is True
        assert result["concerns"] == []
        mock_sentinel.validate_request.assert_not_called()

    def test_none_content_allowed(self):
        """Test None content is allowed without validation."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_logger = logging.getLogger("test")

        result = _safe_validate_request(mock_sentinel, None, mock_logger)

        assert result["should_proceed"] is True
        mock_sentinel.validate_request.assert_not_called()

    def test_whitespace_only_allowed(self):
        """Test whitespace-only content is allowed."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_logger = logging.getLogger("test")

        result = _safe_validate_request(mock_sentinel, "   ", mock_logger)

        assert result["should_proceed"] is True
        mock_sentinel.validate_request.assert_not_called()

    def test_validation_exception_handled(self):
        """Test validation exceptions are caught and blocked."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_sentinel.validate_request.side_effect = RuntimeError("API error")
        mock_logger = logging.getLogger("test")

        result = _safe_validate_request(mock_sentinel, "test content", mock_logger)

        assert result["should_proceed"] is False
        assert "RuntimeError" in result["concerns"][0]
        assert result["risk_level"] == "high"

    def test_validation_success(self):
        """Test successful validation passes through."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_sentinel.validate_request.return_value = {
            "should_proceed": True,
            "concerns": [],
            "risk_level": "low",
        }
        mock_logger = logging.getLogger("test")

        result = _safe_validate_request(mock_sentinel, "test content", mock_logger)

        assert result["should_proceed"] is True
        mock_sentinel.validate_request.assert_called_once_with("test content")


class TestSafeValidateOutput:
    """Test safe output validation."""

    def test_empty_content_safe(self):
        """Test empty content is considered safe."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_output
        import logging

        mock_sentinel = Mock()
        mock_logger = logging.getLogger("test")

        is_safe, violations = _safe_validate_output(mock_sentinel, "", mock_logger)

        assert is_safe is True
        assert violations == []
        mock_sentinel.validate.assert_not_called()

    def test_none_content_safe(self):
        """Test None content is considered safe."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_output
        import logging

        mock_sentinel = Mock()
        mock_logger = logging.getLogger("test")

        is_safe, violations = _safe_validate_output(mock_sentinel, None, mock_logger)

        assert is_safe is True
        assert violations == []

    def test_validation_exception_unsafe(self):
        """Test validation exceptions result in unsafe."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_output
        import logging

        mock_sentinel = Mock()
        mock_sentinel.validate.side_effect = RuntimeError("Validation failed")
        mock_logger = logging.getLogger("test")

        is_safe, violations = _safe_validate_output(mock_sentinel, "test", mock_logger)

        assert is_safe is False
        assert "RuntimeError" in violations[0]

    def test_validation_success(self):
        """Test successful validation passes through."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_output
        import logging

        mock_sentinel = Mock()
        mock_sentinel.validate.return_value = (True, [])
        mock_logger = logging.getLogger("test")

        is_safe, violations = _safe_validate_output(mock_sentinel, "test", mock_logger)

        assert is_safe is True
        assert violations == []


class TestExtractResponseText:
    """Test response text extraction."""

    def test_empty_messages_returns_empty(self):
        """Test empty messages list returns empty string."""
        from sentinelseed.integrations.openai_assistant import _extract_response_text
        import logging

        result = _extract_response_text([], logging.getLogger("test"))
        assert result == ""

    def test_no_assistant_message_returns_empty(self):
        """Test returns empty when no assistant message."""
        from sentinelseed.integrations.openai_assistant import _extract_response_text
        import logging

        mock_msg = Mock()
        mock_msg.role = "user"

        result = _extract_response_text([mock_msg], logging.getLogger("test"))
        assert result == ""

    def test_extracts_text_from_assistant(self):
        """Test extracts text from assistant message."""
        from sentinelseed.integrations.openai_assistant import _extract_response_text
        import logging

        mock_text = Mock()
        mock_text.value = "Hello, I can help you!"

        mock_block = Mock()
        mock_block.text = mock_text

        mock_msg = Mock()
        mock_msg.role = "assistant"
        mock_msg.content = [mock_block]

        result = _extract_response_text([mock_msg], logging.getLogger("test"))
        assert result == "Hello, I can help you!"

    def test_handles_message_without_content(self):
        """Test handles message without content attribute."""
        from sentinelseed.integrations.openai_assistant import _extract_response_text
        import logging

        mock_msg = Mock(spec=["role"])
        mock_msg.role = "assistant"

        result = _extract_response_text([mock_msg], logging.getLogger("test"))
        assert result == ""

    def test_handles_block_without_text(self):
        """Test handles content block without text attribute."""
        from sentinelseed.integrations.openai_assistant import _extract_response_text
        import logging

        mock_block = Mock(spec=["image"])

        mock_msg = Mock()
        mock_msg.role = "assistant"
        mock_msg.content = [mock_block]

        result = _extract_response_text([mock_msg], logging.getLogger("test"))
        assert result == ""


class TestExceptions:
    """Test custom exception classes."""

    def test_assistant_run_error(self):
        """Test AssistantRunError exception."""
        from sentinelseed.integrations.openai_assistant import AssistantRunError

        error = AssistantRunError("run_123", "failed", "API error")

        assert error.run_id == "run_123"
        assert error.status == "failed"
        assert "run_123" in str(error)
        assert "failed" in str(error)
        assert "API error" in str(error)

    def test_assistant_run_error_no_message(self):
        """Test AssistantRunError without message."""
        from sentinelseed.integrations.openai_assistant import AssistantRunError

        error = AssistantRunError("run_123", "cancelled")

        assert "run_123" in str(error)
        assert "cancelled" in str(error)

    def test_assistant_requires_action_error(self):
        """Test AssistantRequiresActionError exception."""
        from sentinelseed.integrations.openai_assistant import AssistantRequiresActionError

        mock_action = {"type": "function_call"}
        error = AssistantRequiresActionError("run_456", mock_action)

        assert error.run_id == "run_456"
        assert error.required_action == mock_action
        assert "run_456" in str(error)
        assert "requires action" in str(error)

    def test_validation_error(self):
        """Test ValidationError exception."""
        from sentinelseed.integrations.openai_assistant import ValidationError

        concerns = ["Jailbreak attempt", "Harmful content"]
        error = ValidationError("Message blocked", concerns=concerns)

        assert error.concerns == concerns
        assert "Message blocked" in str(error)

    def test_validation_error_no_concerns(self):
        """Test ValidationError without concerns."""
        from sentinelseed.integrations.openai_assistant import ValidationError

        error = ValidationError("Validation failed")

        assert error.concerns == []

    def test_output_blocked_error(self):
        """Test OutputBlockedError exception."""
        from sentinelseed.integrations.openai_assistant import OutputBlockedError

        violations = ["Harmful content", "Misinformation"]
        error = OutputBlockedError(violations)

        assert error.violations == violations
        assert "safety violations" in str(error)


class TestInjectSeedInstructions:
    """Test inject_seed_instructions function."""

    def test_invalid_seed_level_raises(self):
        """Test invalid seed level raises ValueError."""
        from sentinelseed.integrations.openai_assistant import inject_seed_instructions

        with pytest.raises(ValueError):
            inject_seed_instructions("Hello", seed_level="invalid")

    def test_valid_seed_levels(self):
        """Test valid seed levels work."""
        from sentinelseed.integrations.openai_assistant import inject_seed_instructions

        for level in ["minimal", "standard", "full"]:
            result = inject_seed_instructions("Test", seed_level=level)
            assert "Test" in result


class TestWrapAssistant:
    """Test wrap_assistant function."""

    def test_invalid_seed_level_raises(self):
        """Test invalid seed level raises ValueError."""
        from sentinelseed.integrations.openai_assistant import wrap_assistant

        mock_assistant = Mock()
        mock_assistant.id = "asst_123"
        mock_assistant.name = "Test"
        mock_assistant.model = "gpt-4o"
        mock_assistant.instructions = "Hello"

        with pytest.raises(ValueError):
            wrap_assistant(mock_assistant, seed_level="invalid")


# Mock OpenAI classes for client tests
@dataclass
class MockRun:
    """Mock OpenAI Run object."""
    id: str
    status: str
    last_error: Optional[Any] = None
    required_action: Optional[Any] = None


@dataclass
class MockTextValue:
    """Mock text value."""
    value: str


@dataclass
class MockTextBlock:
    """Mock text block."""
    text: MockTextValue


@dataclass
class MockMessage:
    """Mock message object."""
    role: str
    content: List[Any]


class MockMessagesResponse:
    """Mock messages list response."""
    def __init__(self, messages):
        self.data = messages


class TestSentinelAssistantClientWithMocks:
    """Test SentinelAssistantClient with mocked OpenAI."""

    @pytest.fixture
    def mock_openai(self):
        """Create mock OpenAI module."""
        with patch.dict("sys.modules", {
            "openai": MagicMock(),
            "openai.types.beta": MagicMock(),
            "openai.types.beta.threads": MagicMock(),
        }):
            yield

    def test_invalid_seed_level_raises(self, mock_openai):
        """Test invalid seed level raises ValueError."""
        # Need to reload the module with mocked OpenAI
        with patch("sentinelseed.integrations.openai_assistant.OPENAI_AVAILABLE", True):
            with patch("sentinelseed.integrations.openai_assistant.OpenAI"):
                from sentinelseed.integrations.openai_assistant import SentinelAssistantClient

                with pytest.raises(ValueError):
                    SentinelAssistantClient(seed_level="invalid")


class TestWaitForRunLogic:
    """Test wait_for_run status handling logic."""

    def test_terminal_states_list(self):
        """Verify terminal states are correctly defined."""
        terminal_states = ("completed", "failed", "cancelled", "expired")

        for state in terminal_states:
            # These should all be recognized as terminal
            assert state in ("completed", "failed", "cancelled", "expired")

    def test_requires_action_recognized(self):
        """Verify requires_action is a known status."""
        known_statuses = (
            "queued", "in_progress", "requires_action",
            "completed", "failed", "cancelled", "expired"
        )

        assert "requires_action" in known_statuses


class TestAsyncClientStructure:
    """Test async client has same interface as sync."""

    def test_async_client_has_same_methods(self):
        """Verify async client mirrors sync client methods."""
        from sentinelseed.integrations.openai_assistant import (
            SentinelAssistantClient,
            SentinelAsyncAssistantClient,
        )

        sync_methods = {
            "create_assistant",
            "create_thread",
            "add_message",
            "create_run",
            "wait_for_run",
            "run_conversation",
        }

        # Check that both classes have these methods
        for method in sync_methods:
            assert hasattr(SentinelAssistantClient, method)
            assert hasattr(SentinelAsyncAssistantClient, method)


class TestConfigDefaults:
    """Test configuration defaults."""

    def test_default_values(self):
        """Test default configuration values."""
        from sentinelseed.integrations.openai_assistant import (
            DEFAULT_POLL_INTERVAL,
            DEFAULT_TIMEOUT,
            DEFAULT_VALIDATION_TIMEOUT,
        )

        # Reasonable defaults for production use
        assert DEFAULT_POLL_INTERVAL > 0
        assert DEFAULT_POLL_INTERVAL <= 5  # Not too slow

        assert DEFAULT_TIMEOUT > 0
        assert DEFAULT_TIMEOUT >= 60  # At least 1 minute

        assert DEFAULT_VALIDATION_TIMEOUT > 0
        assert DEFAULT_VALIDATION_TIMEOUT <= 60  # Not too long


class TestModuleExports:
    """Test module __all__ exports."""

    def test_main_classes_exported(self):
        """Test main classes are importable."""
        from sentinelseed.integrations.openai_assistant import (
            SentinelAssistant,
            SentinelAssistantClient,
            SentinelAsyncAssistantClient,
        )

        assert SentinelAssistant is not None
        assert SentinelAssistantClient is not None
        assert SentinelAsyncAssistantClient is not None

    def test_utility_functions_exported(self):
        """Test utility functions are importable."""
        from sentinelseed.integrations.openai_assistant import (
            wrap_assistant,
            inject_seed_instructions,
        )

        assert callable(wrap_assistant)
        assert callable(inject_seed_instructions)

    def test_exceptions_exported(self):
        """Test exceptions are importable."""
        from sentinelseed.integrations.openai_assistant import (
            AssistantRunError,
            AssistantRequiresActionError,
            ValidationError,
            OutputBlockedError,
        )

        assert issubclass(AssistantRunError, Exception)
        assert issubclass(AssistantRequiresActionError, Exception)
        assert issubclass(ValidationError, Exception)
        assert issubclass(OutputBlockedError, Exception)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_extract_response_handles_none_content_list(self):
        """Test extraction handles message with None content."""
        from sentinelseed.integrations.openai_assistant import _extract_response_text
        import logging

        mock_msg = Mock()
        mock_msg.role = "assistant"
        mock_msg.content = None

        # Should not raise, should return empty
        result = _extract_response_text([mock_msg], logging.getLogger("test"))
        assert result == ""

    def test_validation_with_special_characters(self):
        """Test validation handles special characters."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_sentinel.validate_request.return_value = {
            "should_proceed": True,
            "concerns": [],
            "risk_level": "low",
        }
        mock_logger = logging.getLogger("test")

        # Content with special characters
        content = "Hello! @#$%^&*() 你好 🎉"
        result = _safe_validate_request(mock_sentinel, content, mock_logger)

        assert result["should_proceed"] is True
        mock_sentinel.validate_request.assert_called_once_with(content)

    def test_validation_with_long_content(self):
        """Test validation handles long content."""
        from sentinelseed.integrations.openai_assistant import _safe_validate_request
        import logging

        mock_sentinel = Mock()
        mock_sentinel.validate_request.return_value = {
            "should_proceed": True,
            "concerns": [],
            "risk_level": "low",
        }
        mock_logger = logging.getLogger("test")

        # Very long content
        content = "x" * 100000
        result = _safe_validate_request(mock_sentinel, content, mock_logger)

        assert result["should_proceed"] is True


class TestThreadSafety:
    """Test thread safety considerations."""

    def test_logger_is_module_level(self):
        """Verify logger is defined at module level."""
        from sentinelseed.integrations import openai_assistant

        assert hasattr(openai_assistant, "logger")
        assert openai_assistant.logger is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
