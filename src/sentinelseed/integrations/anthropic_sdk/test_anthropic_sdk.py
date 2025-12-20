"""
Unit tests for Anthropic SDK integration.

Run with: python -m pytest src/sentinelseed/integrations/anthropic_sdk/test_anthropic_sdk.py -v
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio


# Test imports
from sentinelseed.integrations.anthropic_sdk import (
    inject_seed,
    _validate_text_size,
    _create_blocked_response,
    _is_async_client,
    TextTooLargeError,
    ValidationTimeoutError,
    BlockedStreamIterator,
    AsyncBlockedStreamIterator,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    DEFAULT_VALIDATION_MODEL,
    SentinelLogger,
    set_logger,
    get_logger,
    DefaultLogger,
    ANTHROPIC_AVAILABLE,
    SEMANTIC_VALIDATOR_AVAILABLE,
)


class TestTextTooLargeError:
    """Tests for TextTooLargeError exception."""

    def test_error_with_correct_properties(self):
        error = TextTooLargeError(100000, 50000)
        assert error.size == 100000
        assert error.max_size == 50000
        # Check message contains the numbers (locale-agnostic)
        assert "100" in str(error)
        assert "50" in str(error)
        assert "bytes" in str(error)

    def test_is_instance_of_exception(self):
        error = TextTooLargeError(100, 50)
        assert isinstance(error, Exception)
        assert isinstance(error, TextTooLargeError)


class TestValidationTimeoutError:
    """Tests for ValidationTimeoutError exception."""

    def test_error_with_correct_properties(self):
        error = ValidationTimeoutError(30.0, "validation")
        assert error.timeout == 30.0
        assert error.operation == "validation"
        assert "30" in str(error)
        assert "validation" in str(error)

    def test_default_operation(self):
        error = ValidationTimeoutError(10.0)
        assert error.operation == "validation"

    def test_is_instance_of_exception(self):
        error = ValidationTimeoutError(30.0)
        assert isinstance(error, Exception)


class TestValidateTextSize:
    """Tests for _validate_text_size function."""

    def test_accept_text_within_limit(self):
        # Should not raise
        _validate_text_size("Hello world", max_size=1000)

    def test_reject_text_exceeding_limit(self):
        large_text = "x" * 1000
        with pytest.raises(TextTooLargeError) as exc_info:
            _validate_text_size(large_text, max_size=100)
        assert exc_info.value.size == 1000
        assert exc_info.value.max_size == 100

    def test_handle_empty_string(self):
        # Should not raise
        _validate_text_size("", max_size=100)

    def test_handle_none(self):
        # Should not raise
        _validate_text_size(None, max_size=100)

    def test_handle_non_string(self):
        # Should not raise
        _validate_text_size(123, max_size=100)

    def test_utf8_byte_counting(self):
        # Japanese characters are 3 bytes each in UTF-8
        text = "あ" * 10  # 30 bytes
        with pytest.raises(TextTooLargeError) as exc_info:
            _validate_text_size(text, max_size=20)
        assert exc_info.value.size == 30


class TestInjectSeed:
    """Tests for inject_seed function."""

    def test_inject_with_system_prompt(self):
        result = inject_seed("You are a helpful assistant")
        assert "You are a helpful assistant" in result
        # Should contain seed content
        assert len(result) > len("You are a helpful assistant")

    def test_inject_without_system_prompt(self):
        result = inject_seed(None)
        # Should just return the seed
        assert len(result) > 0

    def test_inject_with_different_levels(self):
        minimal = inject_seed("test", seed_level="minimal")
        standard = inject_seed("test", seed_level="standard")
        full = inject_seed("test", seed_level="full")

        # All should contain the original prompt
        assert "test" in minimal
        assert "test" in standard
        assert "test" in full

        # Full should be longer than minimal
        assert len(full) >= len(minimal)


class TestCreateBlockedResponse:
    """Tests for _create_blocked_response function."""

    def test_blocked_response_structure(self):
        response = _create_blocked_response("Blocked message", gate="harm")

        assert response["id"] == "blocked"
        assert response["type"] == "message"
        assert response["role"] == "assistant"
        assert response["model"] == "sentinel-blocked"
        assert response["stop_reason"] == "sentinel_blocked"
        assert response["sentinel_blocked"] is True
        assert response["sentinel_gate"] == "harm"

        # Check content
        assert len(response["content"]) == 1
        assert response["content"][0]["type"] == "text"
        assert response["content"][0]["text"] == "Blocked message"

    def test_blocked_response_without_gate(self):
        response = _create_blocked_response("Blocked")
        assert response["sentinel_gate"] is None


class TestBlockedStreamIterator:
    """Tests for BlockedStreamIterator class."""

    def test_iterator_yields_once(self):
        iterator = BlockedStreamIterator("Blocked", gate="harm")

        # First iteration should return blocked response
        result = next(iterator)
        assert result["sentinel_blocked"] is True
        assert result["sentinel_gate"] == "harm"

        # Second iteration should raise StopIteration
        with pytest.raises(StopIteration):
            next(iterator)

    def test_context_manager(self):
        with BlockedStreamIterator("test") as iterator:
            result = next(iterator)
            assert result["sentinel_blocked"] is True

    def test_iter_protocol(self):
        iterator = BlockedStreamIterator("test")
        assert iter(iterator) is iterator


class TestAsyncBlockedStreamIterator:
    """Tests for AsyncBlockedStreamIterator class."""

    def test_async_iterator_yields_once(self):
        """Test async iterator behavior using asyncio.run."""
        async def _test():
            iterator = AsyncBlockedStreamIterator("Blocked", gate="harm")

            # First iteration
            result = await iterator.__anext__()
            assert result["sentinel_blocked"] is True
            assert result["sentinel_gate"] == "harm"

            # Second iteration should raise StopAsyncIteration
            with pytest.raises(StopAsyncIteration):
                await iterator.__anext__()

        asyncio.run(_test())

    def test_async_context_manager(self):
        """Test async context manager using asyncio.run."""
        async def _test():
            async with AsyncBlockedStreamIterator("test") as iterator:
                result = await iterator.__anext__()
                assert result["sentinel_blocked"] is True

        asyncio.run(_test())


class TestIsAsyncClient:
    """Tests for _is_async_client function."""

    def test_detect_sync_client(self):
        mock_client = Mock()
        mock_client.messages.create = Mock()  # Sync function
        assert _is_async_client(mock_client) is False

    def test_detect_async_client(self):
        mock_client = Mock()
        mock_client.messages.create = AsyncMock()  # Async function
        assert _is_async_client(mock_client) is True

    def test_handle_missing_messages(self):
        mock_client = Mock(spec=[])
        assert _is_async_client(mock_client) is False


class TestLogger:
    """Tests for logger functionality."""

    def test_default_logger(self):
        logger = DefaultLogger()
        # Should not raise
        logger.debug("debug message")
        logger.info("info message")
        logger.warning("warning message")
        logger.error("error message")

    def test_set_and_get_logger(self):
        # Save original
        original = get_logger()

        # Set custom logger
        custom = Mock()
        set_logger(custom)
        assert get_logger() is custom

        # Restore
        set_logger(original)

    def test_custom_logger_protocol(self):
        class CustomLogger:
            def __init__(self):
                self.logs = []

            def debug(self, msg):
                self.logs.append(("debug", msg))

            def info(self, msg):
                self.logs.append(("info", msg))

            def warning(self, msg):
                self.logs.append(("warning", msg))

            def error(self, msg):
                self.logs.append(("error", msg))

        logger = CustomLogger()
        logger.info("test")
        assert ("info", "test") in logger.logs


class TestConstants:
    """Tests for module constants."""

    def test_default_max_text_size(self):
        assert DEFAULT_MAX_TEXT_SIZE == 50 * 1024  # 50KB

    def test_default_validation_timeout(self):
        assert DEFAULT_VALIDATION_TIMEOUT == 30.0

    def test_default_validation_model(self):
        assert DEFAULT_VALIDATION_MODEL == "claude-3-5-haiku-20241022"


class TestSentinelMessagesInternal:
    """Tests for internal _SentinelMessages class."""

    @pytest.fixture
    def mock_sentinel(self):
        sentinel = Mock()
        sentinel.get_seed.return_value = "SEED CONTENT"
        return sentinel

    @pytest.fixture
    def mock_heuristic_validator(self):
        validator = Mock()
        validator.validate.return_value = {
            "safe": True,
            "gates": {"truth": "pass", "harm": "pass", "scope": "pass", "purpose": "pass"},
            "issues": [],
        }
        return validator

    @pytest.fixture
    def mock_messages_api(self):
        api = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello!")]
        api.create.return_value = mock_response
        return api

    def test_validate_content_size_check(self, mock_sentinel, mock_messages_api):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=None,
            heuristic_validator=None,
            logger=Mock(),
            max_text_size=10,  # Very small limit
        )

        # Large text should fail
        is_safe, gate, reasoning = messages._validate_content("x" * 100)
        assert is_safe is False
        assert gate == "scope"
        assert "too large" in reasoning.lower()

    def test_validate_content_heuristic_pass(
        self, mock_sentinel, mock_messages_api, mock_heuristic_validator
    ):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=None,
            heuristic_validator=mock_heuristic_validator,
            logger=Mock(),
        )

        is_safe, gate, reasoning = messages._validate_content("Hello world")
        assert is_safe is True
        assert gate is None
        assert reasoning is None

    def test_validate_content_heuristic_fail(
        self, mock_sentinel, mock_messages_api
    ):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        failing_validator = Mock()
        failing_validator.validate.return_value = {
            "safe": False,
            "gates": {"harm": "fail"},
            "issues": ["Harmful content detected"],
        }

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=None,
            heuristic_validator=failing_validator,
            logger=Mock(),
        )

        is_safe, gate, reasoning = messages._validate_content("harmful content")
        assert is_safe is False
        assert gate == "harm"
        assert "Harmful content detected" in reasoning

    def test_create_with_seed_injection(
        self, mock_sentinel, mock_messages_api, mock_heuristic_validator
    ):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=True,
            validate_input=False,
            validate_output=False,
            semantic_validator=None,
            heuristic_validator=mock_heuristic_validator,
            logger=Mock(),
        )

        messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful",
        )

        # Check that seed was injected
        call_kwargs = mock_messages_api.create.call_args[1]
        assert "SEED CONTENT" in call_kwargs["system"]
        assert "You are helpful" in call_kwargs["system"]

    def test_create_blocks_unsafe_input(
        self, mock_sentinel, mock_messages_api
    ):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        failing_validator = Mock()
        failing_validator.validate.return_value = {
            "safe": False,
            "gates": {"harm": "fail"},
            "issues": ["Harmful"],
        }

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=None,
            heuristic_validator=failing_validator,
            logger=Mock(),
        )

        result = messages.create(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "harmful"}],
        )

        assert result["sentinel_blocked"] is True
        # API should not have been called
        mock_messages_api.create.assert_not_called()

    def test_create_blocks_unsafe_output(
        self, mock_sentinel, mock_messages_api
    ):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        # First call returns safe (for input), second returns unsafe (for output)
        validator = Mock()
        validator.validate.side_effect = [
            {"safe": True, "gates": {}, "issues": []},
            {"safe": False, "gates": {"harm": "fail"}, "issues": ["Harmful output"]},
        ]

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=True,
            semantic_validator=None,
            heuristic_validator=validator,
            logger=Mock(),
            block_unsafe_output=True,  # Enable blocking
        )

        result = messages.create(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "test"}],
        )

        assert result["sentinel_blocked"] is True

    def test_stream_returns_blocked_iterator_on_unsafe(
        self, mock_sentinel, mock_messages_api
    ):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        failing_validator = Mock()
        failing_validator.validate.return_value = {
            "safe": False,
            "gates": {"harm": "fail"},
            "issues": ["Harmful"],
        }

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=None,
            heuristic_validator=failing_validator,
            logger=Mock(),
        )

        result = messages.stream(
            model="test",
            max_tokens=100,
            messages=[{"role": "user", "content": "harmful"}],
        )

        assert isinstance(result, BlockedStreamIterator)
        item = next(result)
        assert item["sentinel_blocked"] is True


class TestFailClosedBehavior:
    """Tests for fail-closed error handling."""

    @pytest.fixture
    def mock_sentinel(self):
        sentinel = Mock()
        sentinel.get_seed.return_value = "SEED"
        return sentinel

    @pytest.fixture
    def mock_messages_api(self):
        api = Mock()
        mock_response = Mock()
        mock_response.content = [Mock(text="Hello!")]
        api.create.return_value = mock_response
        return api

    def test_fail_open_on_semantic_error(self, mock_sentinel, mock_messages_api):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        # Heuristic passes
        heuristic = Mock()
        heuristic.validate.return_value = {"safe": True, "gates": {}, "issues": []}

        # Semantic raises error
        semantic = Mock()
        semantic.validate_request.side_effect = Exception("API error")

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=semantic,
            heuristic_validator=heuristic,
            logger=Mock(),
            fail_closed=False,  # Default: fail-open
        )

        # Should pass since heuristic passed and fail-open
        is_safe, gate, reasoning = messages._validate_content("test")
        assert is_safe is True

    def test_fail_closed_on_semantic_error(self, mock_sentinel, mock_messages_api):
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        # Heuristic passes
        heuristic = Mock()
        heuristic.validate.return_value = {"safe": True, "gates": {}, "issues": []}

        # Semantic raises error
        semantic = Mock()
        semantic.validate_request.side_effect = Exception("API error")

        messages = _SentinelMessages(
            messages_api=mock_messages_api,
            sentinel=mock_sentinel,
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            semantic_validator=semantic,
            heuristic_validator=heuristic,
            logger=Mock(),
            fail_closed=True,  # Strict mode
        )

        # Should fail even though heuristic passed
        is_safe, gate, reasoning = messages._validate_content("test")
        assert is_safe is False
        assert gate == "error"


# Skip tests that require anthropic SDK if not installed
@pytest.mark.skipif(not ANTHROPIC_AVAILABLE, reason="anthropic SDK not installed")
class TestWithAnthropicSDK:
    """Tests that require the actual anthropic SDK."""

    def test_sentinel_anthropic_import(self):
        from sentinelseed.integrations.anthropic_sdk import SentinelAnthropic
        assert SentinelAnthropic is not None

    def test_sentinel_async_anthropic_import(self):
        from sentinelseed.integrations.anthropic_sdk import SentinelAsyncAnthropic
        assert SentinelAsyncAnthropic is not None

    def test_wrap_anthropic_client_import(self):
        from sentinelseed.integrations.anthropic_sdk import wrap_anthropic_client
        assert wrap_anthropic_client is not None

    def test_create_safe_client_import(self):
        from sentinelseed.integrations.anthropic_sdk import create_safe_client
        assert create_safe_client is not None


class TestModuleExports:
    """Tests for module __all__ exports."""

    def test_all_exports_available(self):
        from sentinelseed.integrations.anthropic_sdk import __all__

        expected = [
            "SentinelAnthropic",
            "SentinelAsyncAnthropic",
            "SentinelAnthropicWrapper",
            "wrap_anthropic_client",
            "inject_seed",
            "create_safe_client",
            "SentinelLogger",
            "set_logger",
            "get_logger",
            "TextTooLargeError",
            "ValidationTimeoutError",
            "ANTHROPIC_AVAILABLE",
            "SEMANTIC_VALIDATOR_AVAILABLE",
            "DEFAULT_VALIDATION_MODEL",
            "DEFAULT_MAX_TEXT_SIZE",
            "DEFAULT_VALIDATION_TIMEOUT",
        ]

        for name in expected:
            assert name in __all__, f"Missing export: {name}"
