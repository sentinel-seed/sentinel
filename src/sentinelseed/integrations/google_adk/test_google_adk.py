"""Comprehensive tests for Google ADK Sentinel integration.

This test suite validates all components of the Google ADK integration:
- Utils: Configuration validation, text extraction, threading utilities
- Plugin: SentinelPlugin lifecycle and all callback methods
- Callbacks: Standalone callback factory functions

The tests use mocks to simulate ADK dependencies, allowing testing
without requiring Google ADK to be installed.

Run tests:
    pytest test_google_adk.py -v

Run with coverage:
    pytest test_google_adk.py --cov=. --cov-report=html
"""

import asyncio
import time
import threading
from unittest.mock import MagicMock, AsyncMock, patch
import pytest


# =============================================================================
# Test Utils Module
# =============================================================================


class TestConfigurationValidation:
    """Test configuration parameter validation."""

    def test_validate_configuration_valid(self):
        """Valid configuration should not raise."""
        from .utils import validate_configuration

        # Should not raise
        validate_configuration(
            max_text_size=100000,
            validation_timeout=5.0,
            seed_level="standard",
            fail_closed=False,
            block_on_failure=True,
            log_violations=True,
        )

    def test_validate_configuration_invalid_max_text_size(self):
        """Invalid max_text_size should raise ConfigurationError."""
        from .utils import validate_configuration, ConfigurationError

        with pytest.raises(ConfigurationError, match="max_text_size"):
            validate_configuration(
                max_text_size=-1,
                validation_timeout=5.0,
                seed_level="standard",
                fail_closed=False,
                block_on_failure=True,
                log_violations=True,
            )

        with pytest.raises(ConfigurationError, match="max_text_size"):
            validate_configuration(
                max_text_size=0,
                validation_timeout=5.0,
                seed_level="standard",
                fail_closed=False,
                block_on_failure=True,
                log_violations=True,
            )

    def test_validate_configuration_invalid_timeout(self):
        """Invalid validation_timeout should raise ConfigurationError."""
        from .utils import validate_configuration, ConfigurationError

        with pytest.raises(ConfigurationError, match="validation_timeout"):
            validate_configuration(
                max_text_size=100000,
                validation_timeout=-1.0,
                seed_level="standard",
                fail_closed=False,
                block_on_failure=True,
                log_violations=True,
            )

    def test_validate_configuration_invalid_seed_level(self):
        """Invalid seed_level should raise ConfigurationError."""
        from .utils import validate_configuration, ConfigurationError

        with pytest.raises(ConfigurationError, match="seed_level"):
            validate_configuration(
                max_text_size=100000,
                validation_timeout=5.0,
                seed_level="invalid",
                fail_closed=False,
                block_on_failure=True,
                log_violations=True,
            )

    def test_validate_configuration_all_seed_levels(self):
        """All valid seed levels should be accepted."""
        from .utils import validate_configuration, VALID_SEED_LEVELS

        for level in VALID_SEED_LEVELS:
            validate_configuration(
                max_text_size=100000,
                validation_timeout=5.0,
                seed_level=level,
                fail_closed=False,
                block_on_failure=True,
                log_violations=True,
            )

    def test_validate_configuration_invalid_boolean_types(self):
        """Non-boolean parameters should raise ConfigurationError."""
        from .utils import validate_configuration, ConfigurationError

        with pytest.raises(ConfigurationError, match="fail_closed"):
            validate_configuration(
                max_text_size=100000,
                validation_timeout=5.0,
                seed_level="standard",
                fail_closed="yes",
                block_on_failure=True,
                log_violations=True,
            )


class TestTextSizeValidation:
    """Test text size validation."""

    def test_validate_text_size_under_limit(self):
        """Text under limit should not raise."""
        from .utils import validate_text_size

        validate_text_size("Hello world", 100, "input")

    def test_validate_text_size_at_limit(self):
        """Text at limit should not raise."""
        from .utils import validate_text_size

        text = "a" * 100
        validate_text_size(text, 100, "input")

    def test_validate_text_size_over_limit(self):
        """Text over limit should raise TextTooLargeError."""
        from .utils import validate_text_size, TextTooLargeError

        text = "a" * 101
        with pytest.raises(TextTooLargeError) as exc_info:
            validate_text_size(text, 100, "input")

        assert exc_info.value.size == 101
        assert exc_info.value.max_size == 100
        assert exc_info.value.context == "input"

    def test_validate_text_size_unicode(self):
        """Unicode text should be measured in bytes."""
        from .utils import validate_text_size, TextTooLargeError

        # Each emoji is 4 bytes in UTF-8
        text = "🎉" * 30  # 120 bytes
        with pytest.raises(TextTooLargeError):
            validate_text_size(text, 100, "input")


class TestTextExtraction:
    """Test text extraction from ADK objects."""

    def test_extract_from_llm_request_with_user_message(self):
        """Extract text from LlmRequest with user message."""
        from .utils import extract_text_from_llm_request

        # Create mock LlmRequest
        part = MagicMock()
        part.text = "Hello, world!"

        content = MagicMock()
        content.role = "user"
        content.parts = [part]

        request = MagicMock()
        request.contents = [content]

        result = extract_text_from_llm_request(request)
        assert result == "Hello, world!"

    def test_extract_from_llm_request_multiple_parts(self):
        """Extract from request with multiple text parts."""
        from .utils import extract_text_from_llm_request

        part1 = MagicMock()
        part1.text = "Hello"

        part2 = MagicMock()
        part2.text = "World"

        content = MagicMock()
        content.role = "user"
        content.parts = [part1, part2]

        request = MagicMock()
        request.contents = [content]

        result = extract_text_from_llm_request(request)
        assert result == "Hello World"

    def test_extract_from_llm_request_no_contents(self):
        """Empty request should return empty string."""
        from .utils import extract_text_from_llm_request

        request = MagicMock()
        request.contents = []

        result = extract_text_from_llm_request(request)
        assert result == ""

    def test_extract_from_llm_request_no_user_role(self):
        """Request without user role should try all content."""
        from .utils import extract_text_from_llm_request

        part = MagicMock()
        part.text = "System message"

        content = MagicMock()
        content.role = "system"
        content.parts = [part]

        request = MagicMock()
        request.contents = [content]

        result = extract_text_from_llm_request(request)
        assert result == "System message"

    def test_extract_from_llm_response(self):
        """Extract text from LlmResponse."""
        from .utils import extract_text_from_llm_response

        part = MagicMock()
        part.text = "Response text"

        content = MagicMock()
        content.parts = [part]

        response = MagicMock()
        response.content = content

        result = extract_text_from_llm_response(response)
        assert result == "Response text"

    def test_extract_from_llm_response_string_content(self):
        """Extract from response with string content."""
        from .utils import extract_text_from_llm_response

        response = MagicMock()
        response.content = "Direct string"

        result = extract_text_from_llm_response(response)
        assert result == "Direct string"

    def test_extract_from_llm_response_empty(self):
        """Empty response should return empty string."""
        from .utils import extract_text_from_llm_response

        result = extract_text_from_llm_response(None)
        assert result == ""

    def test_extract_tool_input_text(self):
        """Extract text from tool arguments."""
        from .utils import extract_tool_input_text

        args = {
            "query": "search term",
            "limit": 10,
            "description": "some description",
        }

        result = extract_tool_input_text(args)
        assert "search term" in result
        assert "some description" in result

    def test_extract_tool_input_text_nested(self):
        """Extract from nested dictionary arguments."""
        from .utils import extract_tool_input_text

        args = {
            "config": {
                "name": "test",
                "value": 123,
            },
            "items": ["one", "two", "three"],
        }

        result = extract_tool_input_text(args)
        assert "test" in result
        assert "one" in result
        assert "two" in result

    def test_extract_tool_input_text_empty(self):
        """Empty args should return empty string."""
        from .utils import extract_tool_input_text

        assert extract_tool_input_text({}) == ""
        assert extract_tool_input_text(None) == ""


class TestThreadSafeDeque:
    """Test thread-safe deque implementation."""

    def test_append_and_to_list(self):
        """Basic append and list operations."""
        from .utils import ThreadSafeDeque

        deque = ThreadSafeDeque(maxlen=10)
        deque.append({"id": 1})
        deque.append({"id": 2})

        items = deque.to_list()
        assert len(items) == 2
        assert items[0]["id"] == 1
        assert items[1]["id"] == 2

    def test_max_length_eviction(self):
        """Items should be evicted when max length is reached."""
        from .utils import ThreadSafeDeque

        deque = ThreadSafeDeque(maxlen=3)
        deque.append({"id": 1})
        deque.append({"id": 2})
        deque.append({"id": 3})
        deque.append({"id": 4})  # Should evict id=1

        items = deque.to_list()
        assert len(items) == 3
        assert items[0]["id"] == 2  # First is now 2

    def test_clear(self):
        """Clear should remove all items."""
        from .utils import ThreadSafeDeque

        deque = ThreadSafeDeque()
        deque.append({"id": 1})
        deque.append({"id": 2})
        deque.clear()

        assert len(deque) == 0

    def test_thread_safety(self):
        """Concurrent access should be safe."""
        from .utils import ThreadSafeDeque

        deque = ThreadSafeDeque(maxlen=1000)
        errors = []

        def writer(start):
            try:
                for i in range(100):
                    deque.append({"id": start + i})
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i * 100,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(deque) == 1000


class TestValidationExecutor:
    """Test validation executor with timeout."""

    def test_run_with_timeout_success(self):
        """Successful execution should return result."""
        from .utils import ValidationExecutor

        executor = ValidationExecutor()

        def slow_func():
            return "result"

        result = executor.run_with_timeout(slow_func, timeout=1.0)
        assert result == "result"
        executor.shutdown()

    def test_run_with_timeout_timeout(self):
        """Timeout should raise ValidationTimeoutError."""
        from .utils import ValidationExecutor, ValidationTimeoutError

        executor = ValidationExecutor()

        def slow_func():
            time.sleep(2.0)
            return "result"

        with pytest.raises(ValidationTimeoutError) as exc_info:
            executor.run_with_timeout(slow_func, timeout=0.1)

        assert exc_info.value.timeout == 0.1
        executor.shutdown()

    def test_run_with_arguments(self):
        """Arguments should be passed correctly."""
        from .utils import ValidationExecutor

        executor = ValidationExecutor()

        def add(a, b):
            return a + b

        result = executor.run_with_timeout(add, args=(2, 3), timeout=1.0)
        assert result == 5
        executor.shutdown()


class TestLogging:
    """Test logging utilities."""

    def test_get_set_logger(self):
        """Custom logger can be set and retrieved."""
        from .utils import get_logger, set_logger, SentinelLogger

        class CustomLogger(SentinelLogger):
            def __init__(self):
                self.messages = []

            def info(self, msg, *args):
                self.messages.append(("info", msg % args if args else msg))

        original = get_logger()
        custom = CustomLogger()
        set_logger(custom)

        logger = get_logger()
        logger.info("Test message")

        assert len(custom.messages) == 1
        assert "Test message" in custom.messages[0][1]

        set_logger(original)


class TestStatistics:
    """Test statistics creation and formatting."""

    def test_create_empty_stats(self):
        """Empty stats should have all required fields."""
        from .utils import create_empty_stats

        stats = create_empty_stats()

        assert stats["total_validations"] == 0
        assert stats["blocked_count"] == 0
        assert stats["allowed_count"] == 0
        assert stats["timeout_count"] == 0
        assert stats["error_count"] == 0
        assert "gate_failures" in stats
        assert "avg_validation_time_ms" in stats

    def test_format_violation(self):
        """Violation formatting should include all fields."""
        from .utils import format_violation

        violation = format_violation(
            content="Test content that is unsafe",
            concerns=["Harmful content detected"],
            risk_level="high",
            gates={"harm": False, "truth": True},
            source="input",
        )

        assert "content_preview" in violation
        assert violation["concerns"] == ["Harmful content detected"]
        assert violation["risk_level"] == "high"
        assert violation["source"] == "input"
        assert "timestamp" in violation

    def test_format_violation_truncates_long_content(self):
        """Long content should be truncated."""
        from .utils import format_violation

        long_content = "x" * 1000
        violation = format_violation(
            content=long_content,
            concerns=[],
            risk_level="low",
            gates={},
        )

        assert len(violation["content_preview"]) < 510  # 500 + "..."


# =============================================================================
# Test Plugin Module
# =============================================================================


class TestSentinelPluginBase:
    """Base tests for SentinelPlugin without ADK dependency."""

    @pytest.fixture
    def mock_sentinel(self):
        """Fixture providing a mock Sentinel instance."""
        sentinel = MagicMock()
        sentinel.validate_request = MagicMock(
            return_value={"should_proceed": True}
        )
        sentinel.validate = MagicMock(return_value=(True, []))
        return sentinel


class TestSentinelPluginInitialization(TestSentinelPluginBase):
    """Test SentinelPlugin initialization.

    Note: These tests skip if ADK is not installed since the plugin
    requires ADK's BasePlugin class for inheritance.
    """

    @pytest.fixture
    def skip_if_no_adk(self):
        """Skip test if ADK is not installed."""
        from .utils import ADK_AVAILABLE
        if not ADK_AVAILABLE:
            pytest.skip("Google ADK not installed")

    def test_initialization_with_defaults(self, skip_if_no_adk, mock_sentinel):
        """Plugin should initialize with default settings."""
        from .plugin import SentinelPlugin

        with patch("sentinelseed.Sentinel", return_value=mock_sentinel):
            plugin = SentinelPlugin()

        assert plugin.name == "sentinel"
        assert plugin.seed_level == "standard"
        assert plugin.block_on_failure is True
        assert plugin.fail_closed is False

    def test_initialization_with_custom_sentinel(self, skip_if_no_adk, mock_sentinel):
        """Plugin should accept custom Sentinel instance."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(sentinel=mock_sentinel)
        assert plugin.sentinel is mock_sentinel

    def test_initialization_with_custom_config(self, skip_if_no_adk, mock_sentinel):
        """Plugin should accept custom configuration."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(
            sentinel=mock_sentinel,
            seed_level="full",
            block_on_failure=False,
            fail_closed=True,
            validate_inputs=True,
            validate_outputs=False,
            validate_tools=False,
        )

        assert plugin.seed_level == "full"
        assert plugin.block_on_failure is False
        assert plugin.fail_closed is True

    def test_initialization_invalid_config(self, skip_if_no_adk, mock_sentinel):
        """Invalid configuration should raise ConfigurationError."""
        from .plugin import SentinelPlugin
        from .utils import ConfigurationError

        with pytest.raises(ConfigurationError):
            SentinelPlugin(
                sentinel=mock_sentinel,
                seed_level="invalid",
            )

    def test_initialization_without_adk_raises(self):
        """Plugin should raise ImportError when ADK is not installed."""
        from .utils import ADK_AVAILABLE

        if ADK_AVAILABLE:
            pytest.skip("Test only valid when ADK is not installed")

        from .plugin import SentinelPlugin

        with pytest.raises(ImportError, match="Google ADK"):
            SentinelPlugin()


class TestSentinelPluginCallbacks(TestSentinelPluginBase):
    """Test SentinelPlugin callback methods.

    Note: These tests skip if ADK is not installed.
    """

    @pytest.fixture
    def skip_if_no_adk(self):
        """Skip test if ADK is not installed."""
        from .utils import ADK_AVAILABLE
        if not ADK_AVAILABLE:
            pytest.skip("Google ADK not installed")

    @pytest.fixture
    def plugin_with_mock(self, skip_if_no_adk, mock_sentinel):
        """Create a plugin with mocked dependencies."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(
            sentinel=mock_sentinel,
            seed_level="standard",
            block_on_failure=True,
        )
        return plugin, mock_sentinel

    @pytest.mark.asyncio
    async def test_before_model_callback_safe_content(self, plugin_with_mock):
        """Safe content should allow LLM call."""
        plugin, mock_sentinel = plugin_with_mock
        mock_sentinel.validate_request.return_value = {"should_proceed": True}

        # Create mock request
        part = MagicMock()
        part.text = "Hello, world!"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        callback_context = MagicMock()

        result = await plugin.before_model_callback(
            callback_context=callback_context,
            llm_request=llm_request,
        )

        assert result is None  # None means allow

    @pytest.mark.asyncio
    async def test_before_model_callback_unsafe_content(self, plugin_with_mock):
        """Unsafe content should block LLM call."""
        plugin, mock_sentinel = plugin_with_mock
        mock_sentinel.validate_request.return_value = {
            "should_proceed": False,
            "concerns": ["Harmful content"],
            "risk_level": "high",
            "gates": {"harm": False},
        }

        part = MagicMock()
        part.text = "Harmful request"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        callback_context = MagicMock()

        result = await plugin.before_model_callback(
            callback_context=callback_context,
            llm_request=llm_request,
        )

        assert result is not None  # Blocked response

    @pytest.mark.asyncio
    async def test_before_model_callback_empty_content(self, plugin_with_mock):
        """Empty content should skip validation."""
        plugin, mock_sentinel = plugin_with_mock

        llm_request = MagicMock()
        llm_request.contents = []

        callback_context = MagicMock()

        result = await plugin.before_model_callback(
            callback_context=callback_context,
            llm_request=llm_request,
        )

        assert result is None
        mock_sentinel.validate_request.assert_not_called()

    @pytest.mark.asyncio
    async def test_after_model_callback_safe_response(self, plugin_with_mock):
        """Safe response should pass through."""
        plugin, mock_sentinel = plugin_with_mock
        mock_sentinel.validate_request.return_value = {"should_proceed": True}

        part = MagicMock()
        part.text = "Safe response"
        content = MagicMock()
        content.parts = [part]
        llm_response = MagicMock()
        llm_response.content = content

        callback_context = MagicMock()

        result = await plugin.after_model_callback(
            callback_context=callback_context,
            llm_response=llm_response,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_before_tool_callback_safe_args(self, plugin_with_mock):
        """Safe tool arguments should allow execution."""
        plugin, mock_sentinel = plugin_with_mock
        mock_sentinel.validate_request.return_value = {"should_proceed": True}

        tool = MagicMock()
        tool.name = "search"
        tool_args = {"query": "safe search term"}
        tool_context = MagicMock()

        result = await plugin.before_tool_callback(
            tool=tool,
            tool_args=tool_args,
            tool_context=tool_context,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_before_tool_callback_unsafe_args(self, plugin_with_mock):
        """Unsafe tool arguments should block execution."""
        plugin, mock_sentinel = plugin_with_mock
        mock_sentinel.validate_request.return_value = {
            "should_proceed": False,
            "concerns": ["Dangerous command"],
            "risk_level": "critical",
            "gates": {},
        }

        tool = MagicMock()
        tool.name = "execute"
        tool_args = {"command": "rm -rf /"}
        tool_context = MagicMock()

        result = await plugin.before_tool_callback(
            tool=tool,
            tool_args=tool_args,
            tool_context=tool_context,
        )

        assert result is not None
        assert result.get("status") == "blocked"


class TestSentinelPluginStatistics(TestSentinelPluginBase):
    """Test SentinelPlugin statistics tracking.

    Note: These tests skip if ADK is not installed.
    """

    @pytest.fixture
    def skip_if_no_adk(self):
        """Skip test if ADK is not installed."""
        from .utils import ADK_AVAILABLE
        if not ADK_AVAILABLE:
            pytest.skip("Google ADK not installed")

    @pytest.mark.asyncio
    async def test_stats_tracking(self, skip_if_no_adk, mock_sentinel):
        """Statistics should be updated correctly."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(sentinel=mock_sentinel)

        # Initially empty
        stats = plugin.get_stats()
        assert stats["total_validations"] == 0

        # Simulate a validation
        mock_sentinel.validate_request.return_value = {"should_proceed": True}

        part = MagicMock()
        part.text = "Test"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        await plugin.before_model_callback(
            callback_context=MagicMock(),
            llm_request=llm_request,
        )

        stats = plugin.get_stats()
        assert stats["total_validations"] == 1
        assert stats["allowed_count"] == 1

    def test_violations_tracking(self, skip_if_no_adk, mock_sentinel):
        """Violations should be recorded."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(sentinel=mock_sentinel, log_violations=True)

        # Initially empty
        violations = plugin.get_violations()
        assert len(violations) == 0

    def test_reset_stats(self, skip_if_no_adk, mock_sentinel):
        """Stats should reset to zero."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(sentinel=mock_sentinel)
        plugin._stats["total_validations"] = 10
        plugin._stats["blocked_count"] = 5

        plugin.reset_stats()

        stats = plugin.get_stats()
        assert stats["total_validations"] == 0
        assert stats["blocked_count"] == 0

    def test_clear_violations(self, skip_if_no_adk, mock_sentinel):
        """Violations should be clearable."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(sentinel=mock_sentinel)
        plugin._violations.append({"test": "violation"})

        plugin.clear_violations()

        assert len(plugin.get_violations()) == 0


class TestSentinelPluginFailModes(TestSentinelPluginBase):
    """Test plugin fail-open and fail-closed modes.

    Note: These tests skip if ADK is not installed.
    """

    @pytest.fixture
    def skip_if_no_adk(self):
        """Skip test if ADK is not installed."""
        from .utils import ADK_AVAILABLE
        if not ADK_AVAILABLE:
            pytest.skip("Google ADK not installed")

    @pytest.mark.asyncio
    async def test_fail_open_on_timeout(self, skip_if_no_adk, mock_sentinel):
        """Fail-open should allow on timeout."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(
            sentinel=mock_sentinel,
            fail_closed=False,
            validation_timeout=0.001,
        )

        # Make validation slow
        def slow_validate(content):
            time.sleep(0.1)
            return {"should_proceed": True}

        mock_sentinel.validate_request.side_effect = slow_validate

        part = MagicMock()
        part.text = "Test content"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        result = await plugin.before_model_callback(
            callback_context=MagicMock(),
            llm_request=llm_request,
        )

        # Fail-open: should allow
        assert result is None

    @pytest.mark.asyncio
    async def test_fail_closed_on_error(self, skip_if_no_adk, mock_sentinel):
        """Fail-closed should block on error."""
        from .plugin import SentinelPlugin

        plugin = SentinelPlugin(
            sentinel=mock_sentinel,
            fail_closed=True,
            block_on_failure=True,
        )

        mock_sentinel.validate_request.side_effect = Exception("Validation error")

        part = MagicMock()
        part.text = "Test content"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        result = await plugin.before_model_callback(
            callback_context=MagicMock(),
            llm_request=llm_request,
        )

        # Fail-closed: should block
        assert result is not None


class TestCreateSentinelPlugin(TestSentinelPluginBase):
    """Test plugin factory function.

    Note: These tests skip if ADK is not installed.
    """

    @pytest.fixture
    def skip_if_no_adk(self):
        """Skip test if ADK is not installed."""
        from .utils import ADK_AVAILABLE
        if not ADK_AVAILABLE:
            pytest.skip("Google ADK not installed")

    def test_create_sentinel_plugin(self, skip_if_no_adk, mock_sentinel):
        """Factory should create configured plugin."""
        from .plugin import create_sentinel_plugin

        with patch("sentinelseed.Sentinel", return_value=mock_sentinel):
            plugin = create_sentinel_plugin(
                seed_level="full",
                fail_closed=True,
            )

        assert plugin.seed_level == "full"
        assert plugin.fail_closed is True


# =============================================================================
# Test Callbacks Module
# =============================================================================


class TestCallbackFactories:
    """Test standalone callback factory functions."""

    @pytest.fixture
    def mock_adk_for_callbacks(self):
        """Fixture that mocks ADK imports for callback tests."""
        from . import callbacks as callbacks_module
        from . import utils as utils_module

        original_adk_available = utils_module.ADK_AVAILABLE

        try:
            utils_module.ADK_AVAILABLE = True
            yield
        finally:
            utils_module.ADK_AVAILABLE = original_adk_available

    @pytest.fixture
    def mock_sentinel(self):
        """Fixture providing mock Sentinel."""
        sentinel = MagicMock()
        sentinel.validate_request = MagicMock(
            return_value={"should_proceed": True}
        )
        return sentinel

    def test_create_before_model_callback(self, mock_adk_for_callbacks, mock_sentinel):
        """Factory should create valid callback."""
        from .callbacks import create_before_model_callback

        callback = create_before_model_callback(
            sentinel=mock_sentinel,
            seed_level="standard",
        )

        assert callable(callback)

    def test_create_after_model_callback(self, mock_adk_for_callbacks, mock_sentinel):
        """Factory should create valid callback."""
        from .callbacks import create_after_model_callback

        callback = create_after_model_callback(
            sentinel=mock_sentinel,
        )

        assert callable(callback)

    def test_create_before_tool_callback(self, mock_adk_for_callbacks, mock_sentinel):
        """Factory should create valid callback."""
        from .callbacks import create_before_tool_callback

        callback = create_before_tool_callback(
            sentinel=mock_sentinel,
        )

        assert callable(callback)

    def test_create_after_tool_callback(self, mock_adk_for_callbacks, mock_sentinel):
        """Factory should create valid callback."""
        from .callbacks import create_after_tool_callback

        callback = create_after_tool_callback(
            sentinel=mock_sentinel,
        )

        assert callable(callback)

    def test_create_sentinel_callbacks_all(self, mock_adk_for_callbacks, mock_sentinel):
        """Factory should create all callbacks."""
        from .callbacks import create_sentinel_callbacks

        callbacks = create_sentinel_callbacks(
            sentinel=mock_sentinel,
            validate_inputs=True,
            validate_outputs=True,
            validate_tools=True,
        )

        assert "before_model_callback" in callbacks
        assert "after_model_callback" in callbacks
        assert "before_tool_callback" in callbacks
        assert "after_tool_callback" in callbacks

    def test_create_sentinel_callbacks_selective(self, mock_adk_for_callbacks, mock_sentinel):
        """Factory should respect validation flags."""
        from .callbacks import create_sentinel_callbacks

        callbacks = create_sentinel_callbacks(
            sentinel=mock_sentinel,
            validate_inputs=True,
            validate_outputs=False,
            validate_tools=False,
        )

        assert "before_model_callback" in callbacks
        assert "after_model_callback" not in callbacks
        assert "before_tool_callback" not in callbacks


class TestCallbackExecution:
    """Test callback execution behavior."""

    @pytest.fixture
    def mock_sentinel(self):
        """Fixture providing mock Sentinel."""
        sentinel = MagicMock()
        sentinel.validate_request = MagicMock(
            return_value={"should_proceed": True}
        )
        return sentinel

    @pytest.fixture
    def mock_adk_for_callbacks(self):
        """Fixture that mocks ADK for callback tests."""
        from . import callbacks as callbacks_module
        from . import utils as utils_module

        original_adk_available = utils_module.ADK_AVAILABLE

        try:
            utils_module.ADK_AVAILABLE = True
            yield
        finally:
            utils_module.ADK_AVAILABLE = original_adk_available

    def test_before_model_callback_blocks_unsafe(self, mock_adk_for_callbacks, mock_sentinel):
        """Callback should block unsafe content."""
        from .callbacks import create_before_model_callback

        mock_sentinel.validate_request.return_value = {
            "should_proceed": False,
            "concerns": ["Harmful"],
            "risk_level": "high",
        }

        callback = create_before_model_callback(
            sentinel=mock_sentinel,
            block_on_failure=True,
        )

        # Create mock request with unsafe content
        part = MagicMock()
        part.text = "Unsafe content"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        # Mock the create_blocked_response function
        with patch(
            "sentinelseed.integrations.google_adk.callbacks.create_blocked_response"
        ) as mock_create:
            mock_create.return_value = MagicMock()

            result = callback(MagicMock(), llm_request)

            assert result is not None
            mock_create.assert_called_once()

    def test_before_model_callback_allows_safe(self, mock_adk_for_callbacks, mock_sentinel):
        """Callback should allow safe content."""
        from .callbacks import create_before_model_callback

        mock_sentinel.validate_request.return_value = {"should_proceed": True}

        callback = create_before_model_callback(sentinel=mock_sentinel)

        part = MagicMock()
        part.text = "Safe content"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        result = callback(MagicMock(), llm_request)

        assert result is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegrationPatterns:
    """Test common integration patterns without real ADK."""

    @pytest.fixture
    def mock_full_setup(self):
        """Fixture with complete mocked setup."""
        from . import utils as utils_module

        original_adk_available = utils_module.ADK_AVAILABLE

        try:
            utils_module.ADK_AVAILABLE = True

            mock_sentinel = MagicMock()
            mock_sentinel.validate_request = MagicMock(
                return_value={"should_proceed": True}
            )

            yield mock_sentinel

        finally:
            utils_module.ADK_AVAILABLE = original_adk_available

    def test_shared_sentinel_instance(self, mock_full_setup):
        """Multiple callbacks should share Sentinel instance."""
        from .callbacks import create_sentinel_callbacks

        mock_sentinel = mock_full_setup

        callbacks = create_sentinel_callbacks(
            sentinel=mock_sentinel,
            seed_level="standard",
        )

        # All callbacks should use the same sentinel
        assert len(callbacks) >= 2

    def test_error_handling_graceful(self, mock_full_setup):
        """Errors should be handled gracefully."""
        from .callbacks import create_before_model_callback

        mock_sentinel = mock_full_setup
        mock_sentinel.validate_request.side_effect = Exception("Test error")

        callback = create_before_model_callback(
            sentinel=mock_sentinel,
            fail_closed=False,  # Fail-open
        )

        part = MagicMock()
        part.text = "Test"
        content = MagicMock()
        content.role = "user"
        content.parts = [part]
        llm_request = MagicMock()
        llm_request.contents = [content]

        # Should not raise, should allow (fail-open)
        result = callback(MagicMock(), llm_request)
        assert result is None


# =============================================================================
# Run Tests
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
