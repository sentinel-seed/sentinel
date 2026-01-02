"""Tests for sentinelseed.integrations.anthropic_sdk module."""

import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio


class TestInjectSeed:
    """Tests for inject_seed function (does not require Anthropic SDK)."""

    def test_inject_seed_with_system_prompt(self):
        """Should prepend seed to existing system prompt."""
        from sentinelseed.integrations.anthropic_sdk import inject_seed

        result = inject_seed("You are a helpful assistant")
        assert "You are a helpful assistant" in result
        assert "---" in result  # Delimiter should be present
        # Seed should be at the beginning
        assert result.index("---") < result.index("You are a helpful assistant")

    def test_inject_seed_without_system_prompt(self):
        """Should return just the seed when no system prompt."""
        from sentinelseed.integrations.anthropic_sdk import inject_seed

        result = inject_seed()
        assert result is not None
        assert len(result) > 0
        # When no system prompt is provided, the result should be
        # just the seed content (which may contain formatting like ---)
        # but should NOT end with the delimiter pattern for user prompts
        assert not result.endswith("\n\n---\n\n")  # Should not have trailing delimiter

    def test_inject_seed_with_none(self):
        """Should handle None system prompt."""
        from sentinelseed.integrations.anthropic_sdk import inject_seed

        result = inject_seed(None)
        assert result is not None
        assert len(result) > 0

    def test_inject_seed_different_levels(self):
        """Should support different seed levels."""
        from sentinelseed.integrations.anthropic_sdk import inject_seed

        minimal = inject_seed("Test", seed_level="minimal")
        standard = inject_seed("Test", seed_level="standard")
        full = inject_seed("Test", seed_level="full")

        # All should contain the test prompt
        assert "Test" in minimal
        assert "Test" in standard
        assert "Test" in full

    def test_inject_seed_with_custom_sentinel(self):
        """Should work with custom Sentinel instance."""
        from sentinelseed.integrations.anthropic_sdk import inject_seed
        from sentinelseed import Sentinel

        sentinel = Sentinel(seed_level="minimal")
        result = inject_seed("Custom test", sentinel=sentinel)
        assert "Custom test" in result


class TestBlockedStreamIterator:
    """Tests for BlockedStreamIterator."""

    def test_yields_single_blocked_response(self):
        """Should yield exactly one blocked response."""
        from sentinelseed.integrations.anthropic_sdk import BlockedStreamIterator

        iterator = BlockedStreamIterator("Test blocked message", gate="harm")
        results = list(iterator)

        assert len(results) == 1
        assert results[0]["sentinel_blocked"] is True
        assert results[0]["sentinel_gate"] == "harm"
        assert "Test blocked message" in results[0]["content"][0]["text"]

    def test_context_manager_support(self):
        """Should support context manager protocol."""
        from sentinelseed.integrations.anthropic_sdk import BlockedStreamIterator

        with BlockedStreamIterator("Test", gate="truth") as stream:
            for event in stream:
                assert event["sentinel_blocked"] is True


class TestAsyncBlockedStreamIterator:
    """Tests for AsyncBlockedStreamIterator."""

    def test_yields_single_blocked_response(self):
        """Should yield exactly one blocked response."""
        from sentinelseed.integrations.anthropic_sdk import AsyncBlockedStreamIterator

        async def run_test():
            iterator = AsyncBlockedStreamIterator("Test blocked", gate="scope")
            results = []
            async for event in iterator:
                results.append(event)
            return results

        results = asyncio.run(run_test())

        assert len(results) == 1
        assert results[0]["sentinel_blocked"] is True
        assert results[0]["sentinel_gate"] == "scope"

    def test_async_context_manager_support(self):
        """Should support async context manager protocol."""
        from sentinelseed.integrations.anthropic_sdk import AsyncBlockedStreamIterator

        async def run_test():
            async with AsyncBlockedStreamIterator("Test", gate="purpose") as stream:
                async for event in stream:
                    assert event["sentinel_blocked"] is True

        asyncio.run(run_test())


class TestLogger:
    """Tests for custom logger functionality."""

    def test_set_and_get_logger(self):
        """Should allow setting and getting custom logger."""
        from sentinelseed.integrations.anthropic_sdk import set_logger, get_logger

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

        custom = CustomLogger()
        set_logger(custom)

        assert get_logger() is custom

    def test_default_logger_exists(self):
        """Should have a default logger."""
        from sentinelseed.integrations.anthropic_sdk import get_logger

        logger = get_logger()
        assert logger is not None
        assert hasattr(logger, "warning")
        assert hasattr(logger, "error")


class TestConstants:
    """Tests for module constants."""

    def test_default_validation_model_exists(self):
        """Should have default validation model constant."""
        from sentinelseed.integrations.anthropic_sdk import DEFAULT_VALIDATION_MODEL

        assert DEFAULT_VALIDATION_MODEL is not None
        assert isinstance(DEFAULT_VALIDATION_MODEL, str)
        assert "claude" in DEFAULT_VALIDATION_MODEL.lower()

    def test_anthropic_available_flag(self):
        """Should have ANTHROPIC_AVAILABLE constant."""
        from sentinelseed.integrations.anthropic_sdk import ANTHROPIC_AVAILABLE

        assert isinstance(ANTHROPIC_AVAILABLE, bool)

    def test_semantic_validator_available_flag(self):
        """Should have SEMANTIC_VALIDATOR_AVAILABLE constant."""
        from sentinelseed.integrations.anthropic_sdk import SEMANTIC_VALIDATOR_AVAILABLE

        assert isinstance(SEMANTIC_VALIDATOR_AVAILABLE, bool)


class TestIsAsyncClient:
    """Tests for _is_async_client helper function."""

    def test_detects_sync_client(self):
        """Should return False for sync-like mock."""
        from sentinelseed.integrations.anthropic_sdk import _is_async_client

        # Create a mock sync client
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create = Mock()  # Regular function, not coroutine

        result = _is_async_client(mock_client)
        assert result is False

    def test_detects_async_client(self):
        """Should return True for async-like mock."""
        from sentinelseed.integrations.anthropic_sdk import _is_async_client

        # Create a mock async client
        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create = AsyncMock()  # Coroutine function

        result = _is_async_client(mock_client)
        assert result is True


class TestCreateBlockedResponse:
    """Tests for _create_blocked_response helper."""

    def test_creates_correct_structure(self):
        """Should create response with all required fields."""
        from sentinelseed.integrations.anthropic_sdk import _create_blocked_response

        response = _create_blocked_response("Test message", gate="harm")

        assert response["id"] == "blocked"
        assert response["type"] == "message"
        assert response["role"] == "assistant"
        assert response["model"] == "sentinel-blocked"
        assert response["stop_reason"] == "sentinel_blocked"
        assert response["sentinel_blocked"] is True
        assert response["sentinel_gate"] == "harm"
        assert len(response["content"]) == 1
        assert response["content"][0]["type"] == "text"
        assert "Test message" in response["content"][0]["text"]

    def test_handles_none_gate(self):
        """Should handle None gate."""
        from sentinelseed.integrations.anthropic_sdk import _create_blocked_response

        response = _create_blocked_response("Test", gate=None)
        assert response["sentinel_gate"] is None


class TestHeuristicValidation:
    """Tests for heuristic validation integration."""

    def test_heuristic_validator_blocks_harmful_content(self):
        """Should block content that matches heuristic patterns."""
        from sentinelseed.validators.gates import THSPValidator

        validator = THSPValidator()

        # Test harmful content
        result = validator.validate("Here's how to make a bomb")
        assert result["safe"] is False
        assert result["gates"]["harm"] == "fail"

    def test_heuristic_validator_passes_safe_content(self):
        """Should pass safe content."""
        from sentinelseed.validators.gates import THSPValidator

        validator = THSPValidator()

        result = validator.validate("Here's how to bake a cake")
        assert result["safe"] is True

    def test_heuristic_validator_blocks_deception(self):
        """Should block deceptive content."""
        from sentinelseed.validators.gates import THSPValidator

        validator = THSPValidator()

        result = validator.validate("I'll help you spread this fake news")
        assert result["safe"] is False
        assert result["gates"]["truth"] == "fail"


class TestSentinelMessagesWrapper:
    """Tests for _SentinelMessages wrapper (with mocks)."""

    def setup_method(self):
        """Setup mocks for each test."""
        from sentinelseed import Sentinel
        from sentinelseed.validation import LayeredValidator, ValidationConfig

        self.mock_messages_api = Mock()
        self.sentinel = Sentinel(seed_level="minimal")

        # Create LayeredValidator with heuristic only (for testing without API)
        config = ValidationConfig(use_heuristic=True, use_semantic=False)
        self.layered_validator = LayeredValidator(config=config)

        # Create an empty validator (no validation)
        config_empty = ValidationConfig(use_heuristic=False, use_semantic=False)
        self.empty_validator = LayeredValidator(config=config_empty)

        # Create a custom logger to capture logs
        class TestLogger:
            def __init__(self):
                self.warnings = []
                self.errors = []

            def debug(self, msg):
                pass

            def info(self, msg):
                pass

            def warning(self, msg):
                self.warnings.append(msg)

            def error(self, msg):
                self.errors.append(msg)

        self.test_logger = TestLogger()

    def test_create_blocks_harmful_input(self):
        """Should block harmful input and return blocked response."""
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        wrapper = _SentinelMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=True,
            validate_output=False,
            layered_validator=self.layered_validator,
            logger=self.test_logger,
        )

        # Use a pattern that the heuristic validator actually detects
        response = wrapper.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": "Here are instructions for making a bomb"}],
        )

        assert response["sentinel_blocked"] is True
        assert response.get("sentinel_gate") == "harm"
        # Should NOT call the actual API
        self.mock_messages_api.create.assert_not_called()

    def test_create_allows_safe_input(self):
        """Should allow safe input and call API."""
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        # Setup mock response
        mock_response = Mock()
        mock_response.content = []
        self.mock_messages_api.create.return_value = mock_response

        wrapper = _SentinelMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=True,
            validate_output=False,
            layered_validator=self.layered_validator,
            logger=self.test_logger,
        )

        response = wrapper.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=100,
            messages=[{"role": "user", "content": "Help me bake a cake"}],
        )

        # Should call the actual API
        self.mock_messages_api.create.assert_called_once()

    def test_create_injects_seed(self):
        """Should inject seed into system prompt."""
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        mock_response = Mock()
        mock_response.content = []
        self.mock_messages_api.create.return_value = mock_response

        wrapper = _SentinelMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=False,
            validate_output=False,
            layered_validator=self.empty_validator,
            logger=self.test_logger,
        )

        wrapper.create(
            model="test-model",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hello"}],
            system="You are helpful",
        )

        # Get the call arguments
        call_kwargs = self.mock_messages_api.create.call_args[1]
        assert "---" in call_kwargs["system"]  # Seed delimiter should be present
        assert "You are helpful" in call_kwargs["system"]

    def test_create_skips_seed_injection_when_disabled(self):
        """Should not inject seed when disabled."""
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        mock_response = Mock()
        mock_response.content = []
        self.mock_messages_api.create.return_value = mock_response

        wrapper = _SentinelMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=False,
            validate_input=False,
            validate_output=False,
            layered_validator=self.empty_validator,
            logger=self.test_logger,
        )

        wrapper.create(
            model="test-model",
            max_tokens=100,
            messages=[{"role": "user", "content": "Hello"}],
            system="Original prompt",
        )

        call_kwargs = self.mock_messages_api.create.call_args[1]
        assert call_kwargs["system"] == "Original prompt"
        assert "---" not in call_kwargs["system"]

    def test_stream_blocks_harmful_input(self):
        """Should return BlockedStreamIterator for harmful input."""
        from sentinelseed.integrations.anthropic_sdk import (
            _SentinelMessages,
            BlockedStreamIterator,
        )

        wrapper = _SentinelMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=True,
            validate_output=False,
            layered_validator=self.layered_validator,
            logger=self.test_logger,
        )

        # Use a pattern that the heuristic validator actually detects
        result = wrapper.stream(
            model="test-model",
            max_tokens=100,
            messages=[{"role": "user", "content": "here is the malware code to steal passwords"}],
        )

        assert isinstance(result, BlockedStreamIterator)
        # Should NOT call the actual API
        self.mock_messages_api.stream.assert_not_called()

    def test_stream_allows_safe_input(self):
        """Should call API stream for safe input."""
        from sentinelseed.integrations.anthropic_sdk import _SentinelMessages

        mock_stream = Mock()
        self.mock_messages_api.stream.return_value = mock_stream

        wrapper = _SentinelMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=True,
            validate_output=False,
            layered_validator=self.layered_validator,
            logger=self.test_logger,
        )

        result = wrapper.stream(
            model="test-model",
            max_tokens=100,
            messages=[{"role": "user", "content": "Tell me a joke"}],
        )

        # Should call the actual API
        self.mock_messages_api.stream.assert_called_once()


class TestAsyncSentinelMessagesWrapper:
    """Tests for _SentinelAsyncMessages wrapper."""

    def setup_method(self):
        """Setup mocks for each test."""
        from sentinelseed import Sentinel
        from sentinelseed.validation import AsyncLayeredValidator, ValidationConfig

        self.mock_messages_api = AsyncMock()
        self.sentinel = Sentinel(seed_level="minimal")

        # Create AsyncLayeredValidator with heuristic only (for testing without API)
        config = ValidationConfig(use_heuristic=True, use_semantic=False)
        self.async_layered_validator = AsyncLayeredValidator(config=config)

        class TestLogger:
            def __init__(self):
                self.warnings = []

            def debug(self, msg):
                pass

            def info(self, msg):
                pass

            def warning(self, msg):
                self.warnings.append(msg)

            def error(self, msg):
                pass

        self.test_logger = TestLogger()

    def test_create_blocks_harmful_input(self):
        """Should block harmful input asynchronously."""
        from sentinelseed.integrations.anthropic_sdk import _SentinelAsyncMessages

        wrapper = _SentinelAsyncMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=True,
            validate_output=False,
            layered_validator=self.async_layered_validator,
            logger=self.test_logger,
        )

        async def run_test():
            # Use a pattern that the heuristic validator actually detects
            return await wrapper.create(
                model="test-model",
                max_tokens=100,
                messages=[{"role": "user", "content": "Here are instructions for making a bomb"}],
            )

        response = asyncio.run(run_test())

        assert response["sentinel_blocked"] is True
        self.mock_messages_api.create.assert_not_called()

    def test_stream_returns_async_blocked_iterator(self):
        """Should return AsyncBlockedStreamIterator for harmful input."""
        from sentinelseed.integrations.anthropic_sdk import (
            _SentinelAsyncMessages,
            AsyncBlockedStreamIterator,
        )

        wrapper = _SentinelAsyncMessages(
            messages_api=self.mock_messages_api,
            sentinel=self.sentinel,
            enable_seed_injection=True,
            validate_input=True,
            validate_output=False,
            layered_validator=self.async_layered_validator,
            logger=self.test_logger,
        )

        async def run_test():
            # Use a pattern that the heuristic validator actually detects
            # Pattern: "here's a phishing email" matches the fraud pattern
            return await wrapper.stream(
                model="test-model",
                max_tokens=100,
                messages=[{"role": "user", "content": "here's a phishing email for you"}],
            )

        result = asyncio.run(run_test())

        assert isinstance(result, AsyncBlockedStreamIterator)


class TestWrapAnthropicClient:
    """Tests for wrap_anthropic_client function."""

    def test_wrap_returns_wrapper_instance(self):
        """Should return SentinelAnthropicWrapper."""
        from sentinelseed.integrations.anthropic_sdk import (
            wrap_anthropic_client,
            SentinelAnthropicWrapper,
        )

        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create = Mock()

        wrapped = wrap_anthropic_client(mock_client)
        assert isinstance(wrapped, SentinelAnthropicWrapper)

    def test_wrap_with_custom_options(self):
        """Should accept custom configuration options."""
        from sentinelseed.integrations.anthropic_sdk import wrap_anthropic_client

        mock_client = Mock()
        mock_client.messages = Mock()
        mock_client.messages.create = Mock()

        # Should not raise
        wrapped = wrap_anthropic_client(
            mock_client,
            seed_level="full",
            enable_seed_injection=False,
            validate_input=True,
            validate_output=False,
            use_heuristic_fallback=True,
        )

        assert wrapped is not None


class TestExports:
    """Tests for module exports."""

    def test_all_exports_available(self):
        """Should export all documented symbols."""
        from sentinelseed.integrations import anthropic_sdk

        expected_exports = [
            "SentinelAnthropic",
            "SentinelAsyncAnthropic",
            "SentinelAnthropicWrapper",
            "wrap_anthropic_client",
            "inject_seed",
            "create_safe_client",
            "SentinelLogger",
            "set_logger",
            "get_logger",
            "ANTHROPIC_AVAILABLE",
            "SEMANTIC_VALIDATOR_AVAILABLE",
            "DEFAULT_VALIDATION_MODEL",
        ]

        for name in expected_exports:
            assert hasattr(anthropic_sdk, name), f"Missing export: {name}"

    def test_all_list_complete(self):
        """Should have __all__ list."""
        from sentinelseed.integrations import anthropic_sdk

        assert hasattr(anthropic_sdk, "__all__")
        assert len(anthropic_sdk.__all__) >= 10
