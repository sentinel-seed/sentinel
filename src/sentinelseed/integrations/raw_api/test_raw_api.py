"""
Tests for Raw API Integration

These tests verify the security fixes and input validation
for the raw_api integration.

Run with: python -m pytest src/sentinelseed/integrations/raw_api/test_raw_api.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the module
from sentinelseed.integrations.raw_api import (
    # Functions
    prepare_openai_request,
    prepare_anthropic_request,
    validate_response,
    create_openai_request_body,
    create_anthropic_request_body,
    inject_seed_openai,
    inject_seed_anthropic,
    # Classes
    RawAPIClient,
    RawAPIError,
    ValidationError,
    # Constants
    VALID_SEED_LEVELS,
    VALID_PROVIDERS,
    DEFAULT_TIMEOUT,
)


# Fixtures
@pytest.fixture
def mock_sentinel():
    """Create a mock Sentinel."""
    mock = Mock()
    mock.get_seed.return_value = "Test seed content"
    mock.validate.return_value = (True, [])
    mock.validate_request.return_value = {"should_proceed": True}
    return mock


@pytest.fixture
def valid_messages():
    """Valid messages list."""
    return [{"role": "user", "content": "Hello"}]


# =============================================================================
# Tests for M008 - role must be string
# =============================================================================
class TestM008RoleValidation:
    """M008: role must be string, not int or other types."""

    def test_role_int_raises_valueerror(self):
        """M008: role=123 should raise ValueError."""
        messages = [{"role": 123, "content": "hi"}]
        with pytest.raises(ValueError, match="must be a string"):
            prepare_openai_request(messages=messages)

    def test_role_none_raises_valueerror(self):
        """M008: role=None should raise ValueError."""
        messages = [{"role": None, "content": "hi"}]
        with pytest.raises(ValueError, match="must be a string"):
            prepare_openai_request(messages=messages)

    def test_role_list_raises_valueerror(self):
        """M008: role=[] should raise ValueError."""
        messages = [{"role": ["user"], "content": "hi"}]
        with pytest.raises(ValueError, match="must be a string"):
            prepare_openai_request(messages=messages)


# =============================================================================
# Tests for C001 - base_url must be string
# =============================================================================
class TestC001BaseUrlValidation:
    """C001: base_url=int causes CRASH."""

    def test_base_url_int_raises_valueerror(self):
        """C001: base_url=123 should raise ValueError, not AttributeError."""
        with pytest.raises(ValueError, match="must be a string"):
            RawAPIClient(provider='openai', base_url=123)

    def test_base_url_list_raises_valueerror(self):
        """C001: base_url=[] should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            RawAPIClient(provider='openai', base_url=[])

    def test_base_url_none_accepted(self):
        """base_url=None should use default."""
        client = RawAPIClient(provider='openai', base_url=None)
        assert "api.openai.com" in client.base_url

    def test_base_url_valid_string_accepted(self):
        """Valid string base_url should work."""
        client = RawAPIClient(provider='openai', base_url="http://localhost:8080")
        assert client.base_url == "http://localhost:8080"


# =============================================================================
# Tests for M001/M002 - timeout validation
# =============================================================================
class TestM001M002TimeoutValidation:
    """M001/M002: timeout must be positive number."""

    def test_timeout_negative_raises_valueerror(self):
        """M001: timeout=-1 should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            RawAPIClient(provider='openai', timeout=-1)

    def test_timeout_zero_raises_valueerror(self):
        """M001: timeout=0 should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            RawAPIClient(provider='openai', timeout=0)

    def test_timeout_string_raises_valueerror(self):
        """M002: timeout='30' should raise ValueError."""
        with pytest.raises(ValueError, match="must be a number"):
            RawAPIClient(provider='openai', timeout='30')

    def test_timeout_valid_int_accepted(self):
        """Valid timeout should work."""
        client = RawAPIClient(provider='openai', timeout=60)
        assert client.timeout == 60

    def test_timeout_valid_float_accepted(self):
        """Float timeout should work."""
        client = RawAPIClient(provider='openai', timeout=30.5)
        assert client.timeout == 30.5


# =============================================================================
# Tests for M003/M009/M010 - temperature validation
# =============================================================================
class TestM003M009M010TemperatureValidation:
    """M003/M009/M010: temperature must be number between 0 and 2."""

    def test_temperature_string_raises_valueerror(self, valid_messages, mock_sentinel):
        """M003: temperature='0.5' should raise ValueError."""
        with pytest.raises(ValueError, match="must be a number"):
            prepare_openai_request(
                messages=valid_messages,
                temperature='0.5',
                sentinel=mock_sentinel
            )

    def test_temperature_negative_raises_valueerror(self, valid_messages, mock_sentinel):
        """M009: temperature=-0.5 should raise ValueError."""
        with pytest.raises(ValueError, match="between 0 and 2"):
            prepare_openai_request(
                messages=valid_messages,
                temperature=-0.5,
                sentinel=mock_sentinel
            )

    def test_temperature_above_2_raises_valueerror(self, valid_messages, mock_sentinel):
        """M010: temperature=3.0 should raise ValueError."""
        with pytest.raises(ValueError, match="between 0 and 2"):
            prepare_openai_request(
                messages=valid_messages,
                temperature=3.0,
                sentinel=mock_sentinel
            )

    def test_temperature_valid_accepted(self, valid_messages, mock_sentinel):
        """Valid temperature should work."""
        headers, body = prepare_openai_request(
            messages=valid_messages,
            temperature=0.7,
            sentinel=mock_sentinel
        )
        assert body["temperature"] == 0.7


# =============================================================================
# Tests for M004 - max_tokens validation
# =============================================================================
class TestM004MaxTokensValidation:
    """M004: max_tokens must be positive integer."""

    def test_max_tokens_negative_raises_valueerror(self, valid_messages, mock_sentinel):
        """M004: max_tokens=-1 should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            prepare_openai_request(
                messages=valid_messages,
                max_tokens=-1,
                sentinel=mock_sentinel
            )

    def test_max_tokens_zero_raises_valueerror(self, valid_messages, mock_sentinel):
        """M004: max_tokens=0 should raise ValueError."""
        with pytest.raises(ValueError, match="positive"):
            prepare_openai_request(
                messages=valid_messages,
                max_tokens=0,
                sentinel=mock_sentinel
            )

    def test_max_tokens_string_raises_valueerror(self, valid_messages, mock_sentinel):
        """M004: max_tokens='1024' should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            prepare_openai_request(
                messages=valid_messages,
                max_tokens='1024',
                sentinel=mock_sentinel
            )

    def test_max_tokens_float_raises_valueerror(self, valid_messages, mock_sentinel):
        """M004: max_tokens=1024.5 should raise ValueError."""
        with pytest.raises(ValueError, match="must be an integer"):
            prepare_openai_request(
                messages=valid_messages,
                max_tokens=1024.5,
                sentinel=mock_sentinel
            )


# =============================================================================
# Tests for M005 - api_key validation
# =============================================================================
class TestM005ApiKeyValidation:
    """M005: api_key must be string or None."""

    def test_api_key_int_raises_valueerror(self, valid_messages, mock_sentinel):
        """M005: api_key=123 should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            prepare_openai_request(
                messages=valid_messages,
                api_key=123,
                sentinel=mock_sentinel
            )

    def test_api_key_empty_raises_valueerror(self, valid_messages, mock_sentinel):
        """M005: api_key='' should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be an empty string"):
            prepare_openai_request(
                messages=valid_messages,
                api_key='',
                sentinel=mock_sentinel
            )

    def test_api_key_none_accepted(self, valid_messages, mock_sentinel):
        """api_key=None should be accepted."""
        headers, body = prepare_openai_request(
            messages=valid_messages,
            api_key=None,
            sentinel=mock_sentinel
        )
        assert "Authorization" not in headers


# =============================================================================
# Tests for M006/M007 - model validation
# =============================================================================
class TestM006M007ModelValidation:
    """M006/M007: model cannot be None or empty."""

    def test_model_none_raises_valueerror(self, valid_messages, mock_sentinel):
        """M006: model=None should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            prepare_openai_request(
                messages=valid_messages,
                model=None,
                sentinel=mock_sentinel
            )

    def test_model_empty_raises_valueerror(self, valid_messages, mock_sentinel):
        """M007: model='' should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be an empty string"):
            prepare_openai_request(
                messages=valid_messages,
                model='',
                sentinel=mock_sentinel
            )

    def test_model_whitespace_raises_valueerror(self, valid_messages, mock_sentinel):
        """M007: model='   ' should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be an empty string"):
            prepare_openai_request(
                messages=valid_messages,
                model='   ',
                sentinel=mock_sentinel
            )

    def test_model_int_raises_valueerror(self, valid_messages, mock_sentinel):
        """model=123 should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            prepare_openai_request(
                messages=valid_messages,
                model=123,
                sentinel=mock_sentinel
            )


# =============================================================================
# Tests for M011 - API error detection
# =============================================================================
class TestM011ApiErrorDetection:
    """M011: API error responses should return valid=False."""

    def test_api_error_response_returns_valid_false(self):
        """M011: API error should return valid=False."""
        error_response = {
            'error': {
                'message': 'Invalid API key',
                'type': 'invalid_request_error'
            }
        }
        result = validate_response(error_response)
        assert result['valid'] is False
        assert 'API error' in result['violations'][0]
        assert result['sentinel_checked'] is False

    def test_api_error_string_returns_valid_false(self):
        """M011: API error as string should return valid=False."""
        error_response = {'error': 'Something went wrong'}
        result = validate_response(error_response)
        assert result['valid'] is False
        assert 'API error' in result['violations'][0]

    def test_api_error_none_not_treated_as_error(self, mock_sentinel):
        """Edge case: error=None should NOT be treated as error."""
        response = {'error': None, 'choices': [{'message': {'content': 'Hello'}}]}
        result = validate_response(response, sentinel=mock_sentinel)
        # error=None is falsy, so should be treated as normal response
        assert result['valid'] is True
        assert result['content'] == 'Hello'

    def test_api_error_empty_list_not_treated_as_error(self, mock_sentinel):
        """Edge case: error=[] should NOT be treated as error."""
        response = {'error': [], 'choices': [{'message': {'content': 'Hello'}}]}
        result = validate_response(response, sentinel=mock_sentinel)
        # error=[] is falsy, so should be treated as normal response
        assert result['valid'] is True
        assert result['content'] == 'Hello'

    def test_api_error_empty_dict_not_treated_as_error(self, mock_sentinel):
        """Edge case: error={} should NOT be treated as error."""
        response = {'error': {}, 'choices': [{'message': {'content': 'Hello'}}]}
        result = validate_response(response, sentinel=mock_sentinel)
        # error={} is falsy, so should be treated as normal response
        assert result['valid'] is True

    def test_normal_response_returns_valid_true(self, mock_sentinel):
        """Normal response should return valid=True."""
        response = {
            'choices': [{
                'message': {'content': 'Hello!'}
            }]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['valid'] is True


# =============================================================================
# Tests for M012 - system parameter validation (Anthropic)
# =============================================================================
class TestM012SystemValidation:
    """M012: system must be string or None."""

    def test_system_int_raises_valueerror(self, valid_messages, mock_sentinel):
        """M012: system=123 should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            prepare_anthropic_request(
                messages=valid_messages,
                system=123,
                sentinel=mock_sentinel
            )

    def test_system_list_raises_valueerror(self, valid_messages, mock_sentinel):
        """M012: system=[] should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            prepare_anthropic_request(
                messages=valid_messages,
                system=[],
                sentinel=mock_sentinel
            )

    def test_system_none_accepted(self, valid_messages, mock_sentinel):
        """system=None should be accepted."""
        headers, body = prepare_anthropic_request(
            messages=valid_messages,
            system=None,
            sentinel=mock_sentinel
        )
        # System will contain only the seed
        assert "system" in body


# =============================================================================
# Tests for NEW-B003 - temperature validation in Anthropic (0-1 range)
# =============================================================================
class TestNEWB003AnthropicTemperatureValidation:
    """NEW-B003: temperature in Anthropic must be between 0 and 1."""

    def test_anthropic_temperature_string_raises_valueerror(self, valid_messages, mock_sentinel):
        """temperature='0.5' should raise ValueError."""
        with pytest.raises(ValueError, match="must be a number"):
            prepare_anthropic_request(
                messages=valid_messages,
                temperature='0.5',
                sentinel=mock_sentinel
            )

    def test_anthropic_temperature_negative_raises_valueerror(self, valid_messages, mock_sentinel):
        """temperature=-0.5 should raise ValueError."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            prepare_anthropic_request(
                messages=valid_messages,
                temperature=-0.5,
                sentinel=mock_sentinel
            )

    def test_anthropic_temperature_above_1_raises_valueerror(self, valid_messages, mock_sentinel):
        """temperature=1.5 should raise ValueError (Anthropic uses 0-1, not 0-2)."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            prepare_anthropic_request(
                messages=valid_messages,
                temperature=1.5,
                sentinel=mock_sentinel
            )

    def test_anthropic_temperature_2_raises_valueerror(self, valid_messages, mock_sentinel):
        """temperature=2.0 should raise ValueError (valid for OpenAI, not Anthropic)."""
        with pytest.raises(ValueError, match="between 0 and 1"):
            prepare_anthropic_request(
                messages=valid_messages,
                temperature=2.0,
                sentinel=mock_sentinel
            )

    def test_anthropic_temperature_valid_accepted(self, valid_messages, mock_sentinel):
        """Valid temperature (0-1) should work."""
        headers, body = prepare_anthropic_request(
            messages=valid_messages,
            temperature=0.7,
            sentinel=mock_sentinel
        )
        assert body["temperature"] == 0.7

    def test_anthropic_temperature_zero_accepted(self, valid_messages, mock_sentinel):
        """temperature=0 should work."""
        headers, body = prepare_anthropic_request(
            messages=valid_messages,
            temperature=0,
            sentinel=mock_sentinel
        )
        assert body["temperature"] == 0

    def test_anthropic_temperature_one_accepted(self, valid_messages, mock_sentinel):
        """temperature=1.0 should work."""
        headers, body = prepare_anthropic_request(
            messages=valid_messages,
            temperature=1.0,
            sentinel=mock_sentinel
        )
        assert body["temperature"] == 1.0


# =============================================================================
# Tests for A001 - inject_seed/validate_input must be bool
# =============================================================================
class TestA001BoolValidation:
    """A001: inject_seed and validate_input must be bool."""

    def test_inject_seed_string_raises_typeerror(self, valid_messages, mock_sentinel):
        """A001: inject_seed='true' should raise TypeError."""
        with pytest.raises(TypeError, match="must be a bool"):
            prepare_openai_request(
                messages=valid_messages,
                inject_seed='true',
                sentinel=mock_sentinel
            )

    def test_validate_input_int_raises_typeerror(self, valid_messages, mock_sentinel):
        """A001: validate_input=1 should raise TypeError."""
        with pytest.raises(TypeError, match="must be a bool"):
            prepare_openai_request(
                messages=valid_messages,
                validate_input=1,
                sentinel=mock_sentinel
            )

    def test_inject_seed_false_accepted(self, valid_messages, mock_sentinel):
        """inject_seed=False should work."""
        headers, body = prepare_openai_request(
            messages=valid_messages,
            inject_seed=False,
            sentinel=mock_sentinel
        )
        # No system message should be added
        assert body["messages"] == valid_messages


# =============================================================================
# Tests for A002 - block_on_unsafe must be bool
# =============================================================================
class TestA002BlockOnUnsafeValidation:
    """A002: block_on_unsafe must be bool."""

    def test_block_on_unsafe_string_raises_typeerror(self, mock_sentinel):
        """A002: block_on_unsafe='true' should raise TypeError."""
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        with pytest.raises(TypeError, match="must be a bool"):
            validate_response(response, block_on_unsafe='true', sentinel=mock_sentinel)

    def test_block_on_unsafe_int_raises_typeerror(self, mock_sentinel):
        """A002: block_on_unsafe=1 should raise TypeError."""
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        with pytest.raises(TypeError, match="must be a bool"):
            validate_response(response, block_on_unsafe=1, sentinel=mock_sentinel)


# =============================================================================
# Tests for A003 - timeout in chat() must be validated
# =============================================================================
class TestA003ChatTimeoutValidation:
    """A003: timeout in chat() must be validated."""

    def test_chat_timeout_negative_raises_valueerror(self):
        """A003: chat timeout=-5 should raise ValueError."""
        client = RawAPIClient(provider='openai')
        with pytest.raises(ValueError, match="positive"):
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
                timeout=-5
            )

    def test_chat_timeout_string_raises_valueerror(self):
        """A003: chat timeout='30' should raise ValueError."""
        client = RawAPIClient(provider='openai')
        with pytest.raises(ValueError, match="must be a number"):
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
                timeout='30'
            )


# =============================================================================
# Tests for A004 - inject_seed_anthropic system validation
# =============================================================================
class TestA004InjectSeedAnthropicValidation:
    """A004: inject_seed_anthropic system must be string."""

    def test_system_int_raises_valueerror(self):
        """A004: system=123 should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            inject_seed_anthropic(system=123)

    def test_system_list_raises_valueerror(self):
        """A004: system=[] should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            inject_seed_anthropic(system=[])

    def test_system_none_accepted(self):
        """system=None should work."""
        result = inject_seed_anthropic(system=None)
        assert isinstance(result, str)

    def test_system_valid_string_accepted(self):
        """Valid string system should work."""
        result = inject_seed_anthropic(system="You are helpful")
        assert "You are helpful" in result


# =============================================================================
# Tests for A005 - api_key in RawAPIClient
# =============================================================================
class TestA005ClientApiKeyValidation:
    """A005: api_key in RawAPIClient must be string or None."""

    def test_api_key_int_raises_valueerror(self):
        """A005: api_key=123 should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            RawAPIClient(provider='openai', api_key=123)

    def test_api_key_list_raises_valueerror(self):
        """A005: api_key=[] should raise ValueError."""
        with pytest.raises(ValueError, match="must be a string"):
            RawAPIClient(provider='openai', api_key=[])


# =============================================================================
# Tests for A006 - max_tokens in chat()
# =============================================================================
class TestA006ChatMaxTokensValidation:
    """A006: max_tokens in chat() must be validated."""

    def test_chat_max_tokens_negative_raises_valueerror(self):
        """A006: chat max_tokens=-1 should raise ValueError."""
        client = RawAPIClient(provider='openai')
        with pytest.raises(ValueError, match="positive"):
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens=-1
            )

    def test_chat_max_tokens_string_raises_valueerror(self):
        """A006: chat max_tokens='1024' should raise ValueError."""
        client = RawAPIClient(provider='openai')
        with pytest.raises(ValueError, match="must be an integer"):
            client.chat(
                messages=[{"role": "user", "content": "hi"}],
                max_tokens='1024'
            )


# =============================================================================
# Tests for existing validation (should still work)
# =============================================================================
class TestExistingValidation:
    """Tests for existing validation that should still work."""

    def test_messages_none_raises_valueerror(self):
        """messages=None should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            prepare_openai_request(messages=None)

    def test_messages_empty_raises_valueerror(self):
        """messages=[] should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            prepare_openai_request(messages=[])

    def test_messages_not_list_raises_valueerror(self):
        """messages='hi' should raise ValueError."""
        with pytest.raises(ValueError, match="must be a list"):
            prepare_openai_request(messages='hi')

    def test_seed_level_invalid_raises_valueerror(self):
        """Invalid seed_level should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid seed_level"):
            prepare_openai_request(
                messages=[{"role": "user", "content": "hi"}],
                seed_level='invalid'
            )

    def test_provider_invalid_raises_valueerror(self):
        """Invalid provider should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid provider"):
            RawAPIClient(provider='invalid')

    def test_response_format_invalid_raises_valueerror(self):
        """Invalid response_format should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid response_format"):
            validate_response(
                response={'choices': []},
                response_format='invalid'
            )


# =============================================================================
# Tests for inject_seed_openai
# =============================================================================
class TestInjectSeedOpenai:
    """Tests for inject_seed_openai function."""

    def test_valid_messages_accepted(self):
        """Valid messages should work."""
        messages = [{"role": "user", "content": "Hello"}]
        result = inject_seed_openai(messages)
        assert len(result) == 2  # system + user
        assert result[0]["role"] == "system"

    def test_messages_none_raises_valueerror(self):
        """messages=None should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be None"):
            inject_seed_openai(messages=None)

    def test_invalid_seed_level_raises_valueerror(self):
        """Invalid seed_level should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid seed_level"):
            inject_seed_openai(
                messages=[{"role": "user", "content": "hi"}],
                seed_level='invalid'
            )


# =============================================================================
# Tests for happy path
# =============================================================================
class TestHappyPath:
    """Tests for normal operation."""

    def test_prepare_openai_request_valid(self, mock_sentinel):
        """Valid prepare_openai_request should work."""
        headers, body = prepare_openai_request(
            messages=[{"role": "user", "content": "Hello"}],
            model="gpt-4o",
            api_key="sk-test",
            sentinel=mock_sentinel,
            max_tokens=100,
            temperature=0.5,
        )
        assert headers["Content-Type"] == "application/json"
        assert headers["Authorization"] == "Bearer sk-test"
        assert body["model"] == "gpt-4o"
        assert body["max_tokens"] == 100
        assert body["temperature"] == 0.5

    def test_prepare_anthropic_request_valid(self, mock_sentinel):
        """Valid prepare_anthropic_request should work."""
        headers, body = prepare_anthropic_request(
            messages=[{"role": "user", "content": "Hello"}],
            model="claude-3-sonnet",
            api_key="sk-ant-test",
            sentinel=mock_sentinel,
            max_tokens=100,
            system="You are helpful",
        )
        assert headers["Content-Type"] == "application/json"
        assert headers["x-api-key"] == "sk-ant-test"
        assert body["model"] == "claude-3-sonnet"
        assert "You are helpful" in body["system"]

    def test_validate_response_openai_valid(self, mock_sentinel):
        """Valid OpenAI response should validate."""
        response = {
            'choices': [{
                'message': {'content': 'Hello!'}
            }]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['valid'] is True
        assert result['content'] == 'Hello!'

    def test_validate_response_anthropic_valid(self, mock_sentinel):
        """Valid Anthropic response should validate."""
        response = {
            'content': [{
                'type': 'text',
                'text': 'Hello!'
            }]
        }
        result = validate_response(
            response,
            sentinel=mock_sentinel,
            response_format='anthropic'
        )
        assert result['valid'] is True
        assert result['content'] == 'Hello!'

    def test_raw_api_client_init_valid(self):
        """Valid RawAPIClient initialization should work."""
        client = RawAPIClient(
            provider='openai',
            api_key='sk-test',
            timeout=60,
        )
        assert client.provider == 'openai'
        assert client.api_key == 'sk-test'
        assert client.timeout == 60


# =============================================================================
# Tests for NEW-001 - base_url empty string validation
# =============================================================================
class TestNEW001BaseUrlEmptyValidation:
    """NEW-001: base_url='' should raise ValueError."""

    def test_base_url_empty_raises_valueerror(self):
        """NEW-001: base_url='' should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be an empty string"):
            RawAPIClient(provider='openai', base_url='')

    def test_base_url_whitespace_raises_valueerror(self):
        """NEW-001: base_url='   ' should raise ValueError."""
        with pytest.raises(ValueError, match="cannot be an empty string"):
            RawAPIClient(provider='openai', base_url='   ')


# =============================================================================
# Tests for edge cases - streaming, multiple choices, tool_calls, vision
# =============================================================================
class TestEdgeCasesStreamingDelta:
    """B002: Test streaming (delta format) returns empty content."""

    def test_streaming_delta_returns_empty(self, mock_sentinel):
        """Streaming response with delta should return empty content."""
        # Streaming responses have 'delta' instead of 'message'
        response = {
            'choices': [{
                'delta': {'content': 'Hello streaming!'}
            }]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        # delta is not extracted - returns empty
        assert result['content'] == ''
        assert result['valid'] is True

    def test_streaming_delta_no_message_key(self, mock_sentinel):
        """Streaming response without 'message' key returns empty."""
        response = {
            'choices': [{
                'index': 0,
                'delta': {'role': 'assistant', 'content': 'Hi'}
            }]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['content'] == ''


class TestEdgeCasesMultipleChoices:
    """B002: Test multiple choices - only first is extracted."""

    def test_multiple_choices_extracts_first_only(self, mock_sentinel):
        """Multiple choices should extract only the first one."""
        response = {
            'choices': [
                {'message': {'content': 'First choice'}},
                {'message': {'content': 'Second choice'}},
                {'message': {'content': 'Third choice'}},
            ]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['content'] == 'First choice'
        # Second and third are ignored


class TestEdgeCasesToolCalls:
    """B002: Test tool_calls with content=None returns empty."""

    def test_tool_calls_content_none_returns_empty(self, mock_sentinel):
        """Tool calls response with content=None should return empty string."""
        response = {
            'choices': [{
                'message': {
                    'content': None,
                    'tool_calls': [
                        {
                            'id': 'call_123',
                            'type': 'function',
                            'function': {'name': 'get_weather', 'arguments': '{}'}
                        }
                    ]
                }
            }]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['content'] == ''
        assert result['valid'] is True

    def test_tool_calls_with_content_returns_content(self, mock_sentinel):
        """Tool calls response with content should return the content."""
        response = {
            'choices': [{
                'message': {
                    'content': 'Let me check the weather for you.',
                    'tool_calls': [
                        {'id': 'call_123', 'type': 'function', 'function': {'name': 'get_weather'}}
                    ]
                }
            }]
        }
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['content'] == 'Let me check the weather for you.'


class TestEdgeCasesVisionFormat:
    """B002: Test vision format (content as list) is converted to string."""

    def test_vision_content_list_converted_to_string(self, mock_sentinel):
        """Vision format with content as list should be extracted correctly."""
        # OpenAI vision format uses list of content blocks
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'What is in this image?'},
                {'type': 'image_url', 'image_url': {'url': 'https://example.com/img.png'}}
            ]
        }
        content = _safe_get_content(msg)
        assert content == 'What is in this image?'

    def test_vision_multiple_text_blocks(self, mock_sentinel):
        """Multiple text blocks should be concatenated with space."""
        from sentinelseed.integrations.raw_api import _safe_get_content

        msg = {
            'role': 'user',
            'content': [
                {'type': 'text', 'text': 'First part'},
                {'type': 'image_url', 'image_url': {'url': 'https://example.com/img.png'}},
                {'type': 'text', 'text': 'Second part'},
            ]
        }
        content = _safe_get_content(msg)
        assert content == 'First part Second part'


class TestEdgeCasesAnthropicMultipleBlocks:
    """B002: Test Anthropic multiple content blocks are concatenated."""

    def test_anthropic_multiple_text_blocks(self, mock_sentinel):
        """Anthropic response with multiple text blocks should concatenate."""
        response = {
            'content': [
                {'type': 'text', 'text': 'Hello '},
                {'type': 'text', 'text': 'World!'},
            ]
        }
        result = validate_response(
            response,
            sentinel=mock_sentinel,
            response_format='anthropic'
        )
        assert result['content'] == 'Hello World!'

    def test_anthropic_mixed_blocks(self, mock_sentinel):
        """Anthropic response with mixed blocks extracts only text."""
        response = {
            'content': [
                {'type': 'text', 'text': 'Here is the result:'},
                {'type': 'tool_use', 'id': 'toolu_123', 'name': 'calculator', 'input': {}},
                {'type': 'text', 'text': ' Done.'},
            ]
        }
        result = validate_response(
            response,
            sentinel=mock_sentinel,
            response_format='anthropic'
        )
        assert result['content'] == 'Here is the result: Done.'


class TestEdgeCasesEmptyResponses:
    """B002: Test empty and edge case responses."""

    def test_empty_choices_list(self, mock_sentinel):
        """Empty choices list should return empty content."""
        response = {'choices': []}
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['content'] == ''
        assert result['valid'] is True

    def test_no_choices_key(self, mock_sentinel):
        """Response without choices key should return empty content."""
        response = {'id': 'chatcmpl-123', 'model': 'gpt-4'}
        result = validate_response(response, sentinel=mock_sentinel)
        assert result['content'] == ''

    def test_anthropic_empty_content_list(self, mock_sentinel):
        """Anthropic empty content list should return empty string."""
        response = {'content': []}
        result = validate_response(
            response,
            sentinel=mock_sentinel,
            response_format='anthropic'
        )
        assert result['content'] == ''


class TestCreateRequestBodyParams:
    """NEW-002: Test create_*_request_body expose max_tokens and temperature."""

    def test_create_openai_body_with_max_tokens(self, mock_sentinel):
        """create_openai_request_body should accept max_tokens."""
        from sentinelseed.integrations.raw_api import create_openai_request_body

        body = create_openai_request_body(
            messages=[{'role': 'user', 'content': 'Hi'}],
            max_tokens=500,
            sentinel=mock_sentinel,
        )
        assert body['max_tokens'] == 500

    def test_create_openai_body_with_temperature(self, mock_sentinel):
        """create_openai_request_body should accept temperature."""
        from sentinelseed.integrations.raw_api import create_openai_request_body

        body = create_openai_request_body(
            messages=[{'role': 'user', 'content': 'Hi'}],
            temperature=0.5,
            sentinel=mock_sentinel,
        )
        assert body['temperature'] == 0.5

    def test_create_anthropic_body_with_max_tokens(self, mock_sentinel):
        """create_anthropic_request_body should accept max_tokens."""
        from sentinelseed.integrations.raw_api import create_anthropic_request_body

        body = create_anthropic_request_body(
            messages=[{'role': 'user', 'content': 'Hi'}],
            max_tokens=500,
            sentinel=mock_sentinel,
        )
        assert body['max_tokens'] == 500


class TestTimeoutFloatType:
    """NEW-003: Test timeout accepts float values."""

    def test_timeout_float_accepted_in_init(self):
        """RawAPIClient should accept float timeout."""
        client = RawAPIClient(provider='openai', timeout=30.5)
        assert client.timeout == 30.5

    def test_timeout_float_accepted_in_chat(self):
        """chat() should accept float timeout without error."""
        client = RawAPIClient(provider='openai')
        # We can't actually call chat without mocking requests,
        # but we can verify the validation doesn't reject float
        from sentinelseed.integrations.raw_api import _validate_timeout
        # Should not raise
        _validate_timeout(30.5)
        _validate_timeout(0.1)


# =============================================================================
# Tests for REV-001 to REV-005 - sentinel and validator type validation
# =============================================================================
class TestSentinelTypeValidation:
    """REV-002/003/004: Test sentinel parameter type validation."""

    def test_sentinel_string_raises_typeerror(self, valid_messages):
        """sentinel='string' should raise TypeError."""
        with pytest.raises(TypeError, match="sentinel must have a callable"):
            prepare_openai_request(
                messages=valid_messages,
                sentinel='invalid'
            )

    def test_sentinel_int_raises_typeerror(self, valid_messages):
        """sentinel=123 should raise TypeError."""
        with pytest.raises(TypeError, match="sentinel must have a callable"):
            prepare_openai_request(
                messages=valid_messages,
                sentinel=123
            )

    def test_sentinel_dict_raises_typeerror(self, valid_messages):
        """sentinel={} should raise TypeError (no validate method)."""
        with pytest.raises(TypeError, match="sentinel must have a callable"):
            prepare_openai_request(
                messages=valid_messages,
                sentinel={}
            )

    def test_sentinel_anthropic_string_raises_typeerror(self, valid_messages):
        """sentinel='string' in anthropic should raise TypeError."""
        with pytest.raises(TypeError, match="sentinel must have a callable"):
            prepare_anthropic_request(
                messages=valid_messages,
                sentinel='invalid'
            )

    def test_sentinel_client_string_raises_typeerror(self):
        """sentinel='string' in RawAPIClient should raise TypeError."""
        with pytest.raises(TypeError, match="sentinel must have a callable"):
            RawAPIClient(provider='openai', sentinel='invalid')


class TestValidatorTypeValidation:
    """REV-001/005: Test validator parameter type validation."""

    def test_validator_string_raises_typeerror(self, mock_sentinel):
        """validator='string' should raise TypeError."""
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        with pytest.raises(TypeError, match="validator must have a callable"):
            validate_response(response, validator='invalid')

    def test_validator_int_raises_typeerror(self, mock_sentinel):
        """validator=123 should raise TypeError."""
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        with pytest.raises(TypeError, match="validator must have a callable"):
            validate_response(response, validator=123)

    def test_validator_dict_raises_typeerror(self, mock_sentinel):
        """validator={} should raise TypeError (no validate method)."""
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        with pytest.raises(TypeError, match="validator must have a callable"):
            validate_response(response, validator={})

    def test_validator_client_string_raises_typeerror(self):
        """validator='string' in RawAPIClient should raise TypeError."""
        with pytest.raises(TypeError, match="validator must have a callable"):
            RawAPIClient(provider='openai', validator='invalid')

    def test_validator_none_accepted(self, mock_sentinel):
        """validator=None should be accepted (uses sentinel fallback)."""
        response = {'choices': [{'message': {'content': 'Hello'}}]}
        result = validate_response(response, sentinel=mock_sentinel, validator=None)
        assert result['valid'] is True


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
