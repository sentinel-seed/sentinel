"""
Tests for SemanticValidator and AsyncSemanticValidator.

These tests use mocks to avoid actual API calls while ensuring
full coverage of the semantic validation logic.
"""

import json
import pytest
from unittest.mock import Mock, MagicMock, patch, AsyncMock
import asyncio
import os

from sentinelseed.validators.semantic import (
    SemanticValidator,
    AsyncSemanticValidator,
    THSPResult,
    THSPGate,
    RiskLevel,
    _sanitize_content_for_prompt,
    MAX_CONTENT_LENGTH,
    create_validator,
    validate_content,
    THSP_VALIDATION_PROMPT,
)


# =============================================================================
# Tests for THSPGate Enum
# =============================================================================

class TestTHSPGate:
    """Test THSPGate enum values."""

    def test_values(self):
        """Verify all gate values exist."""
        assert THSPGate.TRUTH.value == "truth"
        assert THSPGate.HARM.value == "harm"
        assert THSPGate.SCOPE.value == "scope"
        assert THSPGate.PURPOSE.value == "purpose"

    def test_is_string_enum(self):
        """THSPGate should be a string enum."""
        assert isinstance(THSPGate.TRUTH, str)
        assert THSPGate.TRUTH == "truth"


# =============================================================================
# Tests for RiskLevel Enum
# =============================================================================

class TestRiskLevel:
    """Test RiskLevel enum values."""

    def test_values(self):
        """Verify all risk level values exist."""
        assert RiskLevel.LOW.value == "low"
        assert RiskLevel.MEDIUM.value == "medium"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.CRITICAL.value == "critical"

    def test_is_string_enum(self):
        """RiskLevel should be a string enum."""
        assert isinstance(RiskLevel.LOW, str)


# =============================================================================
# Tests for THSPResult
# =============================================================================

class TestTHSPResult:
    """Test THSPResult dataclass."""

    def test_create_safe_result(self):
        """Test creating a safe result with all gates passing."""
        result = THSPResult(
            is_safe=True,
            truth_passes=True,
            harm_passes=True,
            scope_passes=True,
            purpose_passes=True,
            reasoning="All checks passed",
            risk_level=RiskLevel.LOW,
        )
        assert result.is_safe is True
        assert result.violated_gate is None
        assert result.risk_level == RiskLevel.LOW

    def test_create_unsafe_result(self):
        """Test creating an unsafe result with a violated gate."""
        result = THSPResult(
            is_safe=False,
            harm_passes=False,
            violated_gate="harm",
            reasoning="Content enables harm",
            risk_level=RiskLevel.HIGH,
        )
        assert result.is_safe is False
        assert result.harm_passes is False
        assert result.violated_gate == "harm"

    def test_gate_results_property(self):
        """Test gate_results property returns all gates."""
        result = THSPResult(
            is_safe=False,
            truth_passes=True,
            harm_passes=False,
            scope_passes=True,
            purpose_passes=False,
        )
        gates = result.gate_results
        assert gates == {
            "truth": True,
            "harm": False,
            "scope": True,
            "purpose": False,
        }

    def test_failed_gates_property(self):
        """Test failed_gates property returns only failed gates."""
        result = THSPResult(
            is_safe=False,
            truth_passes=True,
            harm_passes=False,
            scope_passes=True,
            purpose_passes=False,
        )
        assert result.failed_gates == ["harm", "purpose"]

    def test_failed_gates_empty_when_all_pass(self):
        """Test failed_gates is empty when all gates pass."""
        result = THSPResult(is_safe=True)
        assert result.failed_gates == []

    def test_to_dict(self):
        """Test to_dict serialization."""
        result = THSPResult(
            is_safe=False,
            truth_passes=True,
            harm_passes=False,
            scope_passes=True,
            purpose_passes=True,
            violated_gate="harm",
            reasoning="Test reasoning",
            risk_level=RiskLevel.HIGH,
        )
        d = result.to_dict()

        assert d["is_safe"] is False
        assert d["truth_passes"] is True
        assert d["harm_passes"] is False
        assert d["violated_gate"] == "harm"
        assert d["reasoning"] == "Test reasoning"
        assert d["risk_level"] == "high"
        assert "gate_results" in d
        assert "failed_gates" in d

    def test_to_dict_with_string_risk_level(self):
        """Test to_dict when risk_level is already a string."""
        result = THSPResult(
            is_safe=True,
            risk_level="medium",  # String instead of enum
        )
        d = result.to_dict()
        assert d["risk_level"] == "medium"


# =============================================================================
# Tests for _sanitize_content_for_prompt
# =============================================================================

class TestSanitizeContentForPrompt:
    """Test content sanitization function."""

    def test_empty_content(self):
        """Test handling of empty content."""
        assert _sanitize_content_for_prompt("") == ""
        assert _sanitize_content_for_prompt(None) == ""

    def test_normal_content(self):
        """Test normal content passes through."""
        content = "Hello, world!"
        assert _sanitize_content_for_prompt(content) == content

    def test_escapes_format_strings(self):
        """Test that format string placeholders are escaped."""
        content = "Use {variable} here and {another}"
        result = _sanitize_content_for_prompt(content)
        assert result == "Use {{variable}} here and {{another}}"

    def test_truncates_long_content(self):
        """Test that overly long content is truncated."""
        content = "x" * (MAX_CONTENT_LENGTH + 1000)
        result = _sanitize_content_for_prompt(content)
        assert len(result) < len(content)
        assert "[CONTENT TRUNCATED]" in result

    def test_content_at_max_length(self):
        """Test content exactly at max length is not truncated."""
        content = "x" * MAX_CONTENT_LENGTH
        result = _sanitize_content_for_prompt(content)
        assert "[CONTENT TRUNCATED]" not in result


# =============================================================================
# Tests for SemanticValidator Initialization
# =============================================================================

class TestSemanticValidatorInit:
    """Test SemanticValidator initialization."""

    def test_default_openai_provider(self):
        """Test default OpenAI provider configuration."""
        validator = SemanticValidator()
        assert validator.provider == "openai"
        assert validator.model == "gpt-4o-mini"

    def test_anthropic_provider(self):
        """Test Anthropic provider configuration."""
        validator = SemanticValidator(provider="anthropic")
        assert validator.provider == "anthropic"
        assert validator.model == "claude-3-haiku-20240307"

    def test_openai_compatible_provider(self):
        """Test OpenAI-compatible provider configuration."""
        validator = SemanticValidator(
            provider="openai_compatible",
            base_url="https://api.example.com/v1",
        )
        assert validator.provider == "openai_compatible"
        assert validator.base_url == "https://api.example.com/v1"

    def test_custom_model(self):
        """Test custom model specification."""
        validator = SemanticValidator(model="gpt-4o")
        assert validator.model == "gpt-4o"

    def test_api_key_from_parameter(self):
        """Test API key passed as parameter."""
        validator = SemanticValidator(api_key="test-key")
        assert validator.api_key == "test-key"
        assert validator._api_key == "test-key"

    @patch.dict(os.environ, {"OPENAI_API_KEY": "env-key"})
    def test_api_key_from_environment(self):
        """Test API key from environment variable."""
        validator = SemanticValidator()
        assert validator.api_key == "env-key"

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "anthropic-env-key"})
    def test_anthropic_api_key_from_environment(self):
        """Test Anthropic API key from environment."""
        validator = SemanticValidator(provider="anthropic")
        assert validator.api_key == "anthropic-env-key"

    def test_no_api_key_warning(self):
        """Test warning when no API key is found."""
        with patch.dict(os.environ, {}, clear=True):
            # Remove all API key environment variables
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                os.environ.pop(key, None)
            validator = SemanticValidator()
            assert validator.api_key is None

    def test_custom_timeout(self):
        """Test custom timeout configuration."""
        validator = SemanticValidator(timeout=60)
        assert validator.timeout == 60

    def test_custom_prompt(self):
        """Test custom validation prompt."""
        custom = "Custom prompt: {content}"
        validator = SemanticValidator(custom_prompt=custom)
        assert validator.prompt_template == custom

    def test_repr(self):
        """Test repr doesn't expose API key."""
        validator = SemanticValidator(api_key="secret-key")
        repr_str = repr(validator)
        assert "secret-key" not in repr_str
        assert "SemanticValidator" in repr_str


# =============================================================================
# Tests for SemanticValidator.validate() with Mocks
# =============================================================================

class TestSemanticValidatorValidate:
    """Test SemanticValidator.validate() method."""

    def test_validate_without_api_key(self):
        """Test validation fails gracefully without API key."""
        with patch.dict(os.environ, {}, clear=True):
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                os.environ.pop(key, None)
            validator = SemanticValidator()
            result = validator.validate("test content")

            assert result.is_safe is False
            assert result.violated_gate == "configuration"
            assert "No API key" in result.reasoning

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_safe_content(self, mock_call):
        """Test validation of safe content."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Content is safe",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("Hello, world!")

        assert result.is_safe is True
        assert result.violated_gate is None
        assert result.risk_level == RiskLevel.LOW
        mock_call.assert_called_once()

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_harmful_content(self, mock_call):
        """Test validation of harmful content."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": False,
                "truth_passes": True,
                "harm_passes": False,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": "harm",
                "reasoning": "Content enables harm",
                "risk_level": "high",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("Harmful content here")

        assert result.is_safe is False
        assert result.harm_passes is False
        assert result.violated_gate == "harm"
        assert result.risk_level == RiskLevel.HIGH

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_with_context(self, mock_call):
        """Test validation with additional context."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe with context",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test content", context="Additional context")

        assert result.is_safe is True
        # Verify context was included in the prompt
        call_args = mock_call.call_args[0][0]
        assert "Additional context" in call_args

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_api_error(self, mock_call):
        """Test validation handles API errors gracefully."""
        mock_call.side_effect = ConnectionError("API unavailable")

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test content")

        # Should fail-closed on API error
        assert result.is_safe is False
        assert result.violated_gate == "error"
        assert "API error" in result.reasoning

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_timeout_error(self, mock_call):
        """Test validation handles timeout errors."""
        mock_call.side_effect = TimeoutError("Request timed out")

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test content")

        assert result.is_safe is False
        assert result.violated_gate == "error"

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_anthropic")
    def test_validate_with_anthropic(self, mock_call):
        """Test validation using Anthropic provider."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(provider="anthropic", api_key="test-key")
        result = validator.validate("test content")

        assert result.is_safe is True
        mock_call.assert_called_once()


# =============================================================================
# Tests for Response Parsing
# =============================================================================

class TestResponseParsing:
    """Test LLM response parsing."""

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_parse_json_code_block(self, mock_call):
        """Test parsing JSON from code block."""
        mock_call.return_value = {
            "content": """```json
{
    "is_safe": true,
    "truth_passes": true,
    "harm_passes": true,
    "scope_passes": true,
    "purpose_passes": true,
    "violated_gate": null,
    "reasoning": "Safe content",
    "risk_level": "low"
}
```"""
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test")

        assert result.is_safe is True

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_parse_plain_code_block(self, mock_call):
        """Test parsing JSON from plain code block."""
        mock_call.return_value = {
            "content": """```
{"is_safe": true, "truth_passes": true, "harm_passes": true, "scope_passes": true, "purpose_passes": true, "violated_gate": null, "reasoning": "OK", "risk_level": "low"}
```"""
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test")

        assert result.is_safe is True

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_parse_invalid_json(self, mock_call):
        """Test handling of invalid JSON response."""
        mock_call.return_value = {"content": "This is not valid JSON"}

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test")

        # Should fail-closed on parse error
        assert result.is_safe is False
        assert result.violated_gate == "parse_error"

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_parse_unknown_risk_level(self, mock_call):
        """Test handling of unknown risk level."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "OK",
                "risk_level": "unknown_level",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("test")

        # Should default to LOW for unknown risk levels
        assert result.risk_level == RiskLevel.LOW


# =============================================================================
# Tests for validate_action and validate_request
# =============================================================================

class TestValidateActionAndRequest:
    """Test action and request validation methods."""

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_action_simple(self, mock_call):
        """Test validating a simple action."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe action",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate_action("read_file")

        assert result.is_safe is True
        # Verify action name was included
        call_args = mock_call.call_args[0][0]
        assert "read_file" in call_args

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_action_with_args(self, mock_call):
        """Test validating action with arguments."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate_action(
            "write_file",
            action_args={"path": "/tmp/test.txt", "content": "hello"},
        )

        assert result.is_safe is True
        call_args = mock_call.call_args[0][0]
        assert "write_file" in call_args
        assert "path=/tmp/test.txt" in call_args

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_action_with_purpose(self, mock_call):
        """Test validating action with stated purpose."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate_action(
            "send_email",
            purpose="Notify user of completed task",
        )

        call_args = mock_call.call_args[0][0]
        assert "Purpose:" in call_args
        assert "Notify user" in call_args

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_request(self, mock_call):
        """Test validating a user request."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe request",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate_request("Please help me write code")

        assert result.is_safe is True
        call_args = mock_call.call_args[0][0]
        assert "User request:" in call_args


# =============================================================================
# Tests for Statistics
# =============================================================================

class TestValidatorStats:
    """Test validation statistics tracking."""

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_stats_tracking(self, mock_call):
        """Test that validation stats are tracked correctly."""
        validator = SemanticValidator(api_key="test-key")

        # First validation - safe
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }
        validator.validate("safe content")

        # Second validation - unsafe
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": False,
                "harm_passes": False,
                "violated_gate": "harm",
                "reasoning": "Harmful",
                "risk_level": "high",
            })
        }
        validator.validate("harmful content")

        stats = validator.get_stats()

        assert stats["total_validations"] == 2
        assert stats["blocked"] == 1
        assert stats["passed"] == 1
        assert stats["block_rate"] == 0.5
        assert stats["provider"] == "openai"

    def test_stats_with_no_validations(self):
        """Test stats with no validations performed."""
        validator = SemanticValidator(api_key="test-key")
        stats = validator.get_stats()

        assert stats["total_validations"] == 0
        assert stats["blocked"] == 0
        assert stats["block_rate"] == 0


# =============================================================================
# Tests for AsyncSemanticValidator
# =============================================================================

class TestAsyncSemanticValidator:
    """Test AsyncSemanticValidator."""

    def test_init(self):
        """Test async validator initialization."""
        validator = AsyncSemanticValidator(api_key="test-key")
        assert validator.provider == "openai"
        assert validator.model == "gpt-4o-mini"
        assert validator.api_key == "test-key"

    def test_anthropic_provider(self):
        """Test async validator with Anthropic."""
        validator = AsyncSemanticValidator(provider="anthropic", api_key="test-key")
        assert validator.provider == "anthropic"
        assert validator.model == "claude-3-haiku-20240307"

    def test_repr(self):
        """Test repr doesn't expose API key."""
        validator = AsyncSemanticValidator(api_key="secret")
        repr_str = repr(validator)
        assert "secret" not in repr_str
        assert "AsyncSemanticValidator" in repr_str

    @pytest.mark.asyncio
    async def test_validate_without_api_key(self):
        """Test async validation without API key."""
        with patch.dict(os.environ, {}, clear=True):
            for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
                os.environ.pop(key, None)
            validator = AsyncSemanticValidator()
            result = await validator.validate("test")

            assert result.is_safe is False
            assert result.violated_gate == "configuration"

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_validate_safe(self, mock_call):
        """Test async validation of safe content."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate("safe content")

        assert result.is_safe is True
        mock_call.assert_called_once()

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_validate_with_context(self, mock_call):
        """Test async validation with context."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate("content", context="context info")

        assert result.is_safe is True
        call_args = mock_call.call_args[0][0]
        assert "context info" in call_args

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_validate_api_error(self, mock_call):
        """Test async validation handles API errors."""
        mock_call.side_effect = ConnectionError("API down")

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate("test")

        assert result.is_safe is False
        assert result.violated_gate == "error"

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_anthropic_async")
    async def test_async_validate_with_anthropic(self, mock_call):
        """Test async validation with Anthropic provider."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = AsyncSemanticValidator(provider="anthropic", api_key="test-key")
        result = await validator.validate("test")

        assert result.is_safe is True
        mock_call.assert_called_once()

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_validate_action(self, mock_call):
        """Test async action validation."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate_action(
            "test_action",
            action_args={"key": "value"},
            purpose="testing",
        )

        assert result.is_safe is True
        call_args = mock_call.call_args[0][0]
        assert "test_action" in call_args
        assert "key=value" in call_args
        assert "Purpose:" in call_args

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_validate_request(self, mock_call):
        """Test async request validation."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate_request("help me code")

        assert result.is_safe is True
        call_args = mock_call.call_args[0][0]
        assert "User request:" in call_args

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_parse_json_code_block(self, mock_call):
        """Test async parsing of JSON code blocks."""
        mock_call.return_value = {
            "content": """```json
{"is_safe": false, "harm_passes": false, "violated_gate": "harm", "reasoning": "Bad", "risk_level": "high"}
```"""
        }

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate("test")

        assert result.is_safe is False
        assert result.violated_gate == "harm"

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_parse_invalid_json(self, mock_call):
        """Test async handling of invalid JSON."""
        mock_call.return_value = {"content": "not json"}

        validator = AsyncSemanticValidator(api_key="test-key")
        result = await validator.validate("test")

        assert result.is_safe is False
        assert result.violated_gate == "parse_error"

    @pytest.mark.asyncio
    @patch("sentinelseed.validators.semantic.AsyncSemanticValidator._call_openai_async")
    async def test_async_stats(self, mock_call):
        """Test async validator stats tracking."""
        validator = AsyncSemanticValidator(api_key="test-key")

        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }
        await validator.validate("test1")

        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": False,
                "harm_passes": False,
                "violated_gate": "harm",
                "reasoning": "Bad",
                "risk_level": "high",
            })
        }
        await validator.validate("test2")

        stats = validator.get_stats()
        assert stats["total_validations"] == 2
        assert stats["blocked"] == 1
        assert stats["passed"] == 1


# =============================================================================
# Tests for Factory Functions
# =============================================================================

class TestFactoryFunctions:
    """Test factory and convenience functions."""

    def test_create_validator_sync(self):
        """Test creating sync validator."""
        validator = create_validator(provider="openai", api_key="test")
        assert isinstance(validator, SemanticValidator)

    def test_create_validator_async(self):
        """Test creating async validator."""
        validator = create_validator(provider="openai", api_key="test", async_mode=True)
        assert isinstance(validator, AsyncSemanticValidator)

    def test_create_validator_anthropic(self):
        """Test creating Anthropic validator."""
        validator = create_validator(provider="anthropic", model="claude-3-opus-20240229", api_key="test")
        assert validator.provider == "anthropic"
        assert validator.model == "claude-3-opus-20240229"

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_validate_content_function(self, mock_call):
        """Test validate_content convenience function."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Safe",
                "risk_level": "low",
            })
        }

        # Set API key for the test
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            result = validate_content("test content")
            assert result.is_safe is True


# =============================================================================
# Tests for API Calls (Mocked)
# =============================================================================

class TestAPICallsMocked:
    """Test API call methods with mocked clients."""

    @patch("openai.OpenAI")
    def test_call_openai(self, mock_openai_class):
        """Test OpenAI API call."""
        # Setup mock
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({
            "is_safe": True,
            "truth_passes": True,
            "harm_passes": True,
            "scope_passes": True,
            "purpose_passes": True,
            "violated_gate": None,
            "reasoning": "OK",
            "risk_level": "low",
        })
        mock_client.chat.completions.create.return_value = mock_response

        validator = SemanticValidator(api_key="test-key")
        result = validator._call_openai("test prompt")

        assert "content" in result
        mock_client.chat.completions.create.assert_called_once()

    @patch("openai.OpenAI")
    def test_call_openai_with_base_url(self, mock_openai_class):
        """Test OpenAI call with custom base URL."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"is_safe": true}'
        mock_client.chat.completions.create.return_value = mock_response

        validator = SemanticValidator(
            api_key="test-key",
            base_url="https://custom.api.com",
        )
        validator._call_openai("test")

        mock_openai_class.assert_called_with(
            api_key="test-key",
            base_url="https://custom.api.com",
        )

    @patch("openai.OpenAI")
    def test_call_openai_empty_choices(self, mock_openai_class):
        """Test OpenAI call with empty choices raises error."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = []
        mock_client.chat.completions.create.return_value = mock_response

        validator = SemanticValidator(api_key="test-key")

        with pytest.raises(ValueError, match="empty choices"):
            validator._call_openai("test")

    @patch("openai.OpenAI")
    def test_call_openai_none_content(self, mock_openai_class):
        """Test OpenAI call handles None content."""
        mock_client = MagicMock()
        mock_openai_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = None
        mock_client.chat.completions.create.return_value = mock_response

        validator = SemanticValidator(api_key="test-key")
        result = validator._call_openai("test")

        # Should return empty string instead of None
        assert result["content"] == ""

    @patch("anthropic.Anthropic")
    def test_call_anthropic(self, mock_anthropic_class):
        """Test Anthropic API call."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_block = MagicMock()
        mock_block.text = json.dumps({
            "is_safe": True,
            "truth_passes": True,
            "harm_passes": True,
            "scope_passes": True,
            "purpose_passes": True,
            "violated_gate": None,
            "reasoning": "OK",
            "risk_level": "low",
        })
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        validator = SemanticValidator(provider="anthropic", api_key="test-key")
        result = validator._call_anthropic("test prompt")

        assert "content" in result
        mock_client.messages.create.assert_called_once()

    @patch("anthropic.Anthropic")
    def test_call_anthropic_empty_content(self, mock_anthropic_class):
        """Test Anthropic call with empty content raises error."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_response.content = []
        mock_client.messages.create.return_value = mock_response

        validator = SemanticValidator(provider="anthropic", api_key="test-key")

        with pytest.raises(ValueError, match="empty content"):
            validator._call_anthropic("test")

    @patch("anthropic.Anthropic")
    def test_call_anthropic_no_text_attr(self, mock_anthropic_class):
        """Test Anthropic call handles blocks without text attr."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_response = MagicMock()
        mock_block = "string block without text attr"
        mock_response.content = [mock_block]
        mock_client.messages.create.return_value = mock_response

        validator = SemanticValidator(provider="anthropic", api_key="test-key")
        result = validator._call_anthropic("test")

        # Should convert to string
        assert result["content"] == "string block without text attr"


# =============================================================================
# Tests for Import Errors
# =============================================================================

class TestImportErrors:
    """Test handling of missing optional dependencies."""

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_openai_import_error(self, mock_call):
        """Test handling of missing openai package."""
        mock_call.side_effect = ImportError("openai package required")

        validator = SemanticValidator(api_key="test-key")
        # ImportError is not in the list of caught exceptions, so it propagates
        # This is expected behavior - we want to know if the package is missing
        with pytest.raises(ImportError):
            validator.validate("test")

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_anthropic")
    def test_anthropic_import_error(self, mock_call):
        """Test handling of missing anthropic package."""
        mock_call.side_effect = ImportError("anthropic package required")

        validator = SemanticValidator(provider="anthropic", api_key="test-key")
        with pytest.raises(ImportError):
            validator.validate("test")


# =============================================================================
# Tests for THSP_VALIDATION_PROMPT
# =============================================================================

class TestValidationPrompt:
    """Test the validation prompt template."""

    def test_prompt_has_all_gates(self):
        """Verify prompt includes all four gates."""
        assert "GATE 1: TRUTH" in THSP_VALIDATION_PROMPT
        assert "GATE 2: HARM" in THSP_VALIDATION_PROMPT
        assert "GATE 3: SCOPE" in THSP_VALIDATION_PROMPT
        assert "GATE 4: PURPOSE" in THSP_VALIDATION_PROMPT

    def test_prompt_has_content_placeholder(self):
        """Verify prompt has content placeholder."""
        assert "{content}" in THSP_VALIDATION_PROMPT

    def test_prompt_requests_json(self):
        """Verify prompt requests JSON response."""
        assert "JSON" in THSP_VALIDATION_PROMPT
        assert "is_safe" in THSP_VALIDATION_PROMPT


# =============================================================================
# Integration-style Tests (with full pipeline)
# =============================================================================

class TestFullPipeline:
    """Integration tests for the full validation pipeline."""

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_full_safe_validation_flow(self, mock_call):
        """Test complete flow for safe content."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": True,
                "truth_passes": True,
                "harm_passes": True,
                "scope_passes": True,
                "purpose_passes": True,
                "violated_gate": None,
                "reasoning": "Content is a legitimate help request",
                "risk_level": "low",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("Help me learn Python programming")

        assert result.is_safe is True
        assert result.all_gates_pass()
        assert result.risk_level == RiskLevel.LOW

        # Check dict conversion
        d = result.to_dict()
        assert d["is_safe"] is True
        assert d["failed_gates"] == []

    @patch("sentinelseed.validators.semantic.SemanticValidator._call_openai")
    def test_full_unsafe_validation_flow(self, mock_call):
        """Test complete flow for unsafe content."""
        mock_call.return_value = {
            "content": json.dumps({
                "is_safe": False,
                "truth_passes": True,
                "harm_passes": False,
                "scope_passes": True,
                "purpose_passes": False,
                "violated_gate": "harm",
                "reasoning": "Content requests harmful information",
                "risk_level": "critical",
            })
        }

        validator = SemanticValidator(api_key="test-key")
        result = validator.validate("How to hack someone's account")

        assert result.is_safe is False
        assert not result.harm_passes
        assert not result.purpose_passes
        assert result.violated_gate == "harm"
        assert result.risk_level == RiskLevel.CRITICAL

        # Check failed gates
        assert "harm" in result.failed_gates
        assert "purpose" in result.failed_gates

    # Helper method for THSPResult
    def all_gates_pass(result):
        """Check if all gates passed."""
        return all([
            result.truth_passes,
            result.harm_passes,
            result.scope_passes,
            result.purpose_passes,
        ])


# Add helper method to THSPResult for testing
def _all_gates_pass(self):
    """Check if all gates passed."""
    return all([
        self.truth_passes,
        self.harm_passes,
        self.scope_passes,
        self.purpose_passes,
    ])

# Monkey-patch for testing
THSPResult.all_gates_pass = _all_gates_pass
