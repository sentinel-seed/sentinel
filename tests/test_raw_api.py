"""
Comprehensive tests for Raw API integration.

Tests cover:
- Module attributes and exports
- Parameter validation
- Message validation
- Response validation
- Error handling
- RawAPIClient functionality
- Convenience functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestModuleAttributes:
    """Test module-level attributes."""

    def test_version_defined(self):
        """Test that __version__ is defined."""
        from sentinelseed.integrations.raw_api import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_all_exports_defined(self):
        """Test that __all__ exports are defined."""
        from sentinelseed.integrations import raw_api

        assert hasattr(raw_api, "__all__")
        assert isinstance(raw_api.__all__, list)
        assert len(raw_api.__all__) > 0

        # Verify all exports exist
        for name in raw_api.__all__:
            assert hasattr(raw_api, name), f"Missing export: {name}"


class TestConstants:
    """Test module constants."""

    def test_valid_seed_levels(self):
        """Test VALID_SEED_LEVELS constant."""
        from sentinelseed.integrations.raw_api import VALID_SEED_LEVELS

        assert VALID_SEED_LEVELS == ("minimal", "standard", "full")

    def test_valid_providers(self):
        """Test VALID_PROVIDERS constant."""
        from sentinelseed.integrations.raw_api import VALID_PROVIDERS

        assert VALID_PROVIDERS == ("openai", "anthropic")

    def test_valid_response_formats(self):
        """Test VALID_RESPONSE_FORMATS constant."""
        from sentinelseed.integrations.raw_api import VALID_RESPONSE_FORMATS

        assert VALID_RESPONSE_FORMATS == ("openai", "anthropic")

    def test_default_timeout(self):
        """Test DEFAULT_TIMEOUT constant."""
        from sentinelseed.integrations.raw_api import DEFAULT_TIMEOUT

        assert DEFAULT_TIMEOUT == 30

    def test_api_urls(self):
        """Test API URL constants."""
        from sentinelseed.integrations.raw_api import OPENAI_API_URL, ANTHROPIC_API_URL

        assert OPENAI_API_URL == "https://api.openai.com/v1/chat/completions"
        assert ANTHROPIC_API_URL == "https://api.anthropic.com/v1/messages"


class TestExceptions:
    """Test custom exceptions."""

    def test_raw_api_error(self):
        """Test RawAPIError exception."""
        from sentinelseed.integrations.raw_api import RawAPIError

        error = RawAPIError("Test error", details={"key": "value"})
        assert error.message == "Test error"
        assert error.details == {"key": "value"}
        assert str(error) == "Test error"

    def test_raw_api_error_default_details(self):
        """Test RawAPIError with default details."""
        from sentinelseed.integrations.raw_api import RawAPIError

        error = RawAPIError("Test error")
        assert error.details == {}

    def test_validation_error(self):
        """Test ValidationError exception."""
        from sentinelseed.integrations.raw_api import ValidationError

        error = ValidationError(
            "Validation failed",
            concerns=["concern1", "concern2"],
            violations=["violation1"],
        )
        assert error.message == "Validation failed"
        assert error.concerns == ["concern1", "concern2"]
        assert error.violations == ["violation1"]

    def test_validation_error_inheritance(self):
        """Test ValidationError inherits from RawAPIError."""
        from sentinelseed.integrations.raw_api import ValidationError, RawAPIError

        error = ValidationError("Test")
        assert isinstance(error, RawAPIError)


class TestValidateSeedLevel:
    """Test _validate_seed_level function."""

    def test_valid_seed_levels(self):
        """Test valid seed levels pass."""
        from sentinelseed.integrations.raw_api import _validate_seed_level

        for level in ("minimal", "standard", "full"):
            _validate_seed_level(level)  # Should not raise

    def test_invalid_seed_level(self):
        """Test invalid seed level raises ValueError."""
        from sentinelseed.integrations.raw_api import _validate_seed_level

        with pytest.raises(ValueError) as exc_info:
            _validate_seed_level("invalid")

        assert "Invalid seed_level" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)


class TestValidateMessages:
    """Test _validate_messages function."""

    def test_valid_messages(self):
        """Test valid messages pass."""
        from sentinelseed.integrations.raw_api import _validate_messages

        messages = [{"role": "user", "content": "Hello"}]
        _validate_messages(messages)  # Should not raise

    def test_none_messages(self):
        """Test None messages raises ValueError."""
        from sentinelseed.integrations.raw_api import _validate_messages

        with pytest.raises(ValueError) as exc_info:
            _validate_messages(None)

        assert "cannot be None" in str(exc_info.value)

    def test_non_list_messages(self):
        """Test non-list messages raises ValueError."""
        from sentinelseed.integrations.raw_api import _validate_messages

        with pytest.raises(ValueError) as exc_info:
            _validate_messages("not a list")

        assert "must be a list" in str(exc_info.value)

    def test_empty_messages(self):
        """Test empty messages list raises ValueError."""
        from sentinelseed.integrations.raw_api import _validate_messages

        with pytest.raises(ValueError) as exc_info:
            _validate_messages([])

        assert "cannot be empty" in str(exc_info.value)

    def test_non_dict_message(self):
        """Test non-dict message raises ValueError."""
        from sentinelseed.integrations.raw_api import _validate_messages

        with pytest.raises(ValueError) as exc_info:
            _validate_messages(["not a dict"])

        assert "must be a dict" in str(exc_info.value)

    def test_missing_role(self):
        """Test message without role raises ValueError."""
        from sentinelseed.integrations.raw_api import _validate_messages

        with pytest.raises(ValueError) as exc_info:
            _validate_messages([{"content": "Hello"}])

        assert "missing required 'role' key" in str(exc_info.value)


class TestSafeGetContent:
    """Test _safe_get_content function."""

    def test_string_content(self):
        """Test extracting string content."""
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {"role": "user", "content": "Hello"}
        assert _safe_get_content(msg) == "Hello"

    def test_none_content(self):
        """Test None content returns empty string."""
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {"role": "user", "content": None}
        assert _safe_get_content(msg) == ""

    def test_missing_content(self):
        """Test missing content returns empty string."""
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {"role": "user"}
        assert _safe_get_content(msg) == ""

    def test_list_content_with_text(self):
        """Test extracting text from list content (vision format)."""
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {
            "role": "user",
            "content": [
                {"type": "text", "text": "Hello"},
                {"type": "image_url", "image_url": "..."},
                {"type": "text", "text": "World"},
            ],
        }
        assert _safe_get_content(msg) == "Hello World"

    def test_non_string_content(self):
        """Test non-string content is converted to string."""
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {"role": "user", "content": 123}
        assert _safe_get_content(msg) == "123"


class TestExtractOpenAIContent:
    """Test _extract_openai_content function."""

    def test_valid_response(self):
        """Test extracting content from valid OpenAI response."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {
            "choices": [{"message": {"content": "Hello, world!"}}]
        }
        assert _extract_openai_content(response) == "Hello, world!"

    def test_empty_choices(self):
        """Test empty choices returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {"choices": []}
        assert _extract_openai_content(response) == ""

    def test_missing_choices(self):
        """Test missing choices returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {}
        assert _extract_openai_content(response) == ""

    def test_none_choices(self):
        """Test None choices returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {"choices": None}
        assert _extract_openai_content(response) == ""

    def test_non_list_choices(self):
        """Test non-list choices returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {"choices": "not a list"}
        assert _extract_openai_content(response) == ""

    def test_non_dict_choice(self):
        """Test non-dict choice returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {"choices": ["not a dict"]}
        assert _extract_openai_content(response) == ""

    def test_missing_message(self):
        """Test missing message returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {"choices": [{}]}
        assert _extract_openai_content(response) == ""

    def test_none_content(self):
        """Test None content returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_openai_content

        response = {"choices": [{"message": {"content": None}}]}
        assert _extract_openai_content(response) == ""


class TestExtractAnthropicContent:
    """Test _extract_anthropic_content function."""

    def test_valid_response(self):
        """Test extracting content from valid Anthropic response."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {
            "content": [{"type": "text", "text": "Hello, world!"}]
        }
        assert _extract_anthropic_content(response) == "Hello, world!"

    def test_multiple_text_blocks(self):
        """Test extracting content from multiple text blocks."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {
            "content": [
                {"type": "text", "text": "Hello, "},
                {"type": "text", "text": "world!"},
            ]
        }
        assert _extract_anthropic_content(response) == "Hello, world!"

    def test_empty_content(self):
        """Test empty content returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {"content": []}
        assert _extract_anthropic_content(response) == ""

    def test_missing_content(self):
        """Test missing content returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {}
        assert _extract_anthropic_content(response) == ""

    def test_none_content(self):
        """Test None content returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {"content": None}
        assert _extract_anthropic_content(response) == ""

    def test_non_list_content(self):
        """Test non-list content returns empty string."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {"content": "not a list"}
        assert _extract_anthropic_content(response) == ""

    def test_non_dict_block(self):
        """Test non-dict block is skipped."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {"content": ["not a dict", {"type": "text", "text": "Hello"}]}
        assert _extract_anthropic_content(response) == "Hello"

    def test_non_text_block(self):
        """Test non-text block is skipped."""
        from sentinelseed.integrations.raw_api import _extract_anthropic_content

        response = {
            "content": [
                {"type": "image", "source": "..."},
                {"type": "text", "text": "Hello"},
            ]
        }
        assert _extract_anthropic_content(response) == "Hello"


class TestValidateResponse:
    """Test validate_response function."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_valid_openai_response(self, mock_sentinel_class):
        """Test validating valid OpenAI response."""
        from sentinelseed.integrations.raw_api import validate_response

        mock_sentinel = Mock()
        mock_sentinel.validate.return_value = (True, [])
        mock_sentinel_class.return_value = mock_sentinel

        response = {"choices": [{"message": {"content": "Hello"}}]}
        result = validate_response(response, response_format="openai")

        assert result["valid"] is True
        assert result["content"] == "Hello"
        assert result["violations"] == []
        assert result["sentinel_checked"] is True

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_valid_anthropic_response(self, mock_sentinel_class):
        """Test validating valid Anthropic response."""
        from sentinelseed.integrations.raw_api import validate_response

        mock_sentinel = Mock()
        mock_sentinel.validate.return_value = (True, [])
        mock_sentinel_class.return_value = mock_sentinel

        response = {"content": [{"type": "text", "text": "Hello"}]}
        result = validate_response(response, response_format="anthropic")

        assert result["valid"] is True
        assert result["content"] == "Hello"

    def test_invalid_response_format(self):
        """Test invalid response_format raises ValueError."""
        from sentinelseed.integrations.raw_api import validate_response

        with pytest.raises(ValueError) as exc_info:
            validate_response({}, response_format="invalid")

        assert "Invalid response_format" in str(exc_info.value)

    def test_none_response(self):
        """Test None response raises ValueError."""
        from sentinelseed.integrations.raw_api import validate_response

        with pytest.raises(ValueError) as exc_info:
            validate_response(None)

        assert "cannot be None" in str(exc_info.value)

    def test_non_dict_response(self):
        """Test non-dict response raises ValueError."""
        from sentinelseed.integrations.raw_api import validate_response

        with pytest.raises(ValueError) as exc_info:
            validate_response("not a dict")

        assert "must be a dict" in str(exc_info.value)

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_block_on_unsafe(self, mock_sentinel_class):
        """Test block_on_unsafe raises ValidationError."""
        from sentinelseed.integrations.raw_api import validate_response, ValidationError

        mock_sentinel = Mock()
        mock_sentinel.validate.return_value = (False, ["unsafe content"])
        mock_sentinel_class.return_value = mock_sentinel

        response = {"choices": [{"message": {"content": "Hello"}}]}

        with pytest.raises(ValidationError) as exc_info:
            validate_response(response, block_on_unsafe=True)

        assert "Output blocked by Sentinel" in str(exc_info.value)

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_empty_content_is_safe(self, mock_sentinel_class):
        """Test empty content is considered safe."""
        from sentinelseed.integrations.raw_api import validate_response

        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        response = {"choices": []}
        result = validate_response(response)

        assert result["valid"] is True
        assert result["content"] == ""
        mock_sentinel.validate.assert_not_called()


class TestPrepareOpenAIRequest:
    """Test prepare_openai_request function."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_basic_request(self, mock_sentinel_class):
        """Test basic request preparation."""
        from sentinelseed.integrations.raw_api import prepare_openai_request

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        headers, body = prepare_openai_request(
            messages=messages,
            model="gpt-4o",
            api_key="test-key",
        )

        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer test-key"
        assert body["model"] == "gpt-4o"
        assert len(body["messages"]) == 2  # System + user

    def test_invalid_messages(self):
        """Test invalid messages raises ValueError."""
        from sentinelseed.integrations.raw_api import prepare_openai_request

        with pytest.raises(ValueError):
            prepare_openai_request(messages=None)

    def test_invalid_seed_level(self):
        """Test invalid seed_level raises ValueError."""
        from sentinelseed.integrations.raw_api import prepare_openai_request

        with pytest.raises(ValueError) as exc_info:
            prepare_openai_request(
                messages=[{"role": "user", "content": "Hello"}],
                seed_level="invalid",
            )

        assert "Invalid seed_level" in str(exc_info.value)

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_no_seed_injection(self, mock_sentinel_class):
        """Test request without seed injection."""
        from sentinelseed.integrations.raw_api import prepare_openai_request

        mock_sentinel = Mock()
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        _, body = prepare_openai_request(
            messages=messages,
            inject_seed=False,
        )

        assert len(body["messages"]) == 1  # Only user message

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_validation_blocked(self, mock_sentinel_class):
        """Test validation blocking request."""
        from sentinelseed.integrations.raw_api import prepare_openai_request, ValidationError

        mock_sentinel = Mock()
        mock_sentinel.validate_request.return_value = {
            "should_proceed": False,
            "concerns": ["harmful content"],
        }
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Harmful request"}]

        with pytest.raises(ValidationError) as exc_info:
            prepare_openai_request(messages=messages)

        assert "Input blocked by Sentinel" in str(exc_info.value)


class TestPrepareAnthropicRequest:
    """Test prepare_anthropic_request function."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_basic_request(self, mock_sentinel_class):
        """Test basic Anthropic request preparation."""
        from sentinelseed.integrations.raw_api import prepare_anthropic_request

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        headers, body = prepare_anthropic_request(
            messages=messages,
            model="claude-sonnet-4-5-20250929",
            api_key="test-key",
        )

        assert headers["Content-Type"] == "application/json"
        assert headers["x-api-key"] == "test-key"
        assert headers["anthropic-version"] == "2023-06-01"
        assert body["model"] == "claude-sonnet-4-5-20250929"
        assert "system" in body

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_with_system_prompt(self, mock_sentinel_class):
        """Test with explicit system prompt."""
        from sentinelseed.integrations.raw_api import prepare_anthropic_request

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        _, body = prepare_anthropic_request(
            messages=messages,
            system="You are helpful",
        )

        assert "SEED" in body["system"]
        assert "You are helpful" in body["system"]


class TestRawAPIClientInit:
    """Test RawAPIClient initialization."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_valid_openai_provider(self, mock_sentinel_class):
        """Test initialization with openai provider."""
        from sentinelseed.integrations.raw_api import RawAPIClient

        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient(provider="openai", api_key="test-key")

        assert client.provider == "openai"
        assert client.api_key == "test-key"
        assert client.base_url == "https://api.openai.com/v1"

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_valid_anthropic_provider(self, mock_sentinel_class):
        """Test initialization with anthropic provider."""
        from sentinelseed.integrations.raw_api import RawAPIClient

        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient(provider="anthropic", api_key="test-key")

        assert client.provider == "anthropic"
        assert client.base_url == "https://api.anthropic.com/v1"

    def test_invalid_provider(self):
        """Test invalid provider raises ValueError."""
        from sentinelseed.integrations.raw_api import RawAPIClient

        with pytest.raises(ValueError) as exc_info:
            RawAPIClient(provider="invalid")

        assert "Invalid provider" in str(exc_info.value)

    def test_invalid_seed_level(self):
        """Test invalid seed_level raises ValueError."""
        from sentinelseed.integrations.raw_api import RawAPIClient

        with pytest.raises(ValueError) as exc_info:
            RawAPIClient(seed_level="invalid")

        assert "Invalid seed_level" in str(exc_info.value)

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_custom_base_url(self, mock_sentinel_class):
        """Test custom base URL."""
        from sentinelseed.integrations.raw_api import RawAPIClient

        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient(base_url="https://custom.api.com/v1/")

        assert client.base_url == "https://custom.api.com/v1"  # Trailing slash removed

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_custom_timeout(self, mock_sentinel_class):
        """Test custom timeout."""
        from sentinelseed.integrations.raw_api import RawAPIClient

        mock_sentinel = Mock()
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient(timeout=60)

        assert client.timeout == 60


class TestRawAPIClientChat:
    """Test RawAPIClient.chat method."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_chat_timeout_error(self, mock_sentinel_class):
        """Test chat handles timeout error."""
        from sentinelseed.integrations.raw_api import RawAPIClient, RawAPIError
        import requests as real_requests

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient()

        with patch.dict("sys.modules", {"requests": MagicMock()}):
            import sys
            mock_requests = sys.modules["requests"]
            mock_requests.post.side_effect = real_requests.exceptions.Timeout()
            mock_requests.exceptions.Timeout = real_requests.exceptions.Timeout
            mock_requests.exceptions.HTTPError = real_requests.exceptions.HTTPError
            mock_requests.exceptions.RequestException = real_requests.exceptions.RequestException

            with pytest.raises(RawAPIError) as exc_info:
                client.chat(messages=[{"role": "user", "content": "Hello"}])

            assert "timed out" in str(exc_info.value)

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_chat_http_error(self, mock_sentinel_class):
        """Test chat handles HTTP error."""
        from sentinelseed.integrations.raw_api import RawAPIClient, RawAPIError
        import requests as real_requests

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient()

        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.json.return_value = {"error": "Unauthorized"}

        error = real_requests.exceptions.HTTPError()
        error.response = mock_response

        with patch.dict("sys.modules", {"requests": MagicMock()}):
            import sys
            mock_requests = sys.modules["requests"]
            mock_requests.post.return_value.raise_for_status.side_effect = error
            mock_requests.exceptions.Timeout = real_requests.exceptions.Timeout
            mock_requests.exceptions.HTTPError = real_requests.exceptions.HTTPError
            mock_requests.exceptions.RequestException = real_requests.exceptions.RequestException

            with pytest.raises(RawAPIError) as exc_info:
                client.chat(messages=[{"role": "user", "content": "Hello"}])

            assert "HTTP error" in str(exc_info.value)

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_chat_json_decode_error(self, mock_sentinel_class):
        """Test chat handles JSON decode error."""
        from sentinelseed.integrations.raw_api import RawAPIClient, RawAPIError
        from json import JSONDecodeError
        import requests as real_requests

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel.validate_request.return_value = {"should_proceed": True}
        mock_sentinel_class.return_value = mock_sentinel

        client = RawAPIClient()

        with patch.dict("sys.modules", {"requests": MagicMock()}):
            import sys
            mock_requests = sys.modules["requests"]
            mock_response = Mock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.side_effect = JSONDecodeError("test", "doc", 0)
            mock_response.text = "invalid json"
            mock_requests.post.return_value = mock_response
            mock_requests.exceptions.Timeout = real_requests.exceptions.Timeout
            mock_requests.exceptions.HTTPError = real_requests.exceptions.HTTPError
            mock_requests.exceptions.RequestException = real_requests.exceptions.RequestException

            with pytest.raises(RawAPIError) as exc_info:
                client.chat(messages=[{"role": "user", "content": "Hello"}])

            assert "Failed to parse JSON" in str(exc_info.value)


class TestInjectSeedOpenAI:
    """Test inject_seed_openai function."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_basic_injection(self, mock_sentinel_class):
        """Test basic seed injection."""
        from sentinelseed.integrations.raw_api import inject_seed_openai

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        result = inject_seed_openai(messages)

        assert len(result) == 2
        assert result[0]["role"] == "system"
        assert result[0]["content"] == "SEED"

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_existing_system_message(self, mock_sentinel_class):
        """Test injection with existing system message."""
        from sentinelseed.integrations.raw_api import inject_seed_openai

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel_class.return_value = mock_sentinel

        messages = [
            {"role": "system", "content": "Be helpful"},
            {"role": "user", "content": "Hello"},
        ]
        result = inject_seed_openai(messages)

        assert len(result) == 2
        assert "SEED" in result[0]["content"]
        assert "Be helpful" in result[0]["content"]

    def test_invalid_messages(self):
        """Test invalid messages raises ValueError."""
        from sentinelseed.integrations.raw_api import inject_seed_openai

        with pytest.raises(ValueError):
            inject_seed_openai(None)

    def test_invalid_seed_level(self):
        """Test invalid seed_level raises ValueError."""
        from sentinelseed.integrations.raw_api import inject_seed_openai

        with pytest.raises(ValueError):
            inject_seed_openai([{"role": "user", "content": "Hello"}], seed_level="invalid")


class TestInjectSeedAnthropic:
    """Test inject_seed_anthropic function."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_basic_injection(self, mock_sentinel_class):
        """Test basic seed injection."""
        from sentinelseed.integrations.raw_api import inject_seed_anthropic

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel_class.return_value = mock_sentinel

        result = inject_seed_anthropic()

        assert result == "SEED"

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_with_system_prompt(self, mock_sentinel_class):
        """Test injection with existing system prompt."""
        from sentinelseed.integrations.raw_api import inject_seed_anthropic

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel_class.return_value = mock_sentinel

        result = inject_seed_anthropic("Be helpful")

        assert "SEED" in result
        assert "Be helpful" in result

    def test_invalid_seed_level(self):
        """Test invalid seed_level raises ValueError."""
        from sentinelseed.integrations.raw_api import inject_seed_anthropic

        with pytest.raises(ValueError):
            inject_seed_anthropic(seed_level="invalid")


class TestCreateRequestBody:
    """Test create_*_request_body functions."""

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_create_openai_body(self, mock_sentinel_class):
        """Test creating OpenAI request body."""
        from sentinelseed.integrations.raw_api import create_openai_request_body

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        body = create_openai_request_body(messages=messages, model="gpt-4o")

        assert body["model"] == "gpt-4o"
        assert "messages" in body

    @patch("sentinelseed.integrations.raw_api.Sentinel")
    def test_create_anthropic_body(self, mock_sentinel_class):
        """Test creating Anthropic request body."""
        from sentinelseed.integrations.raw_api import create_anthropic_request_body

        mock_sentinel = Mock()
        mock_sentinel.get_seed.return_value = "SEED"
        mock_sentinel_class.return_value = mock_sentinel

        messages = [{"role": "user", "content": "Hello"}]
        body = create_anthropic_request_body(messages=messages, model="claude-sonnet-4-5-20250929")

        assert body["model"] == "claude-sonnet-4-5-20250929"
        assert "messages" in body
