"""
Tests for sentinelseed.validation.config module.
"""

import os
import pytest
from sentinelseed.validation.config import (
    ValidationConfig,
    DEFAULT_CONFIG,
    STRICT_CONFIG,
)


class TestValidationConfigDefaults:
    """Tests for default ValidationConfig values."""

    def test_default_values(self):
        """Test that default config has expected values."""
        config = ValidationConfig()

        assert config.use_heuristic is True
        assert config.use_semantic is False
        assert config.semantic_provider == "openai"
        assert config.semantic_model is None
        assert config.semantic_api_key is None
        assert config.semantic_base_url is None
        assert config.validation_timeout == 30.0
        assert config.fail_closed is False
        assert config.skip_semantic_if_heuristic_blocks is True
        assert config.max_text_size == 50_000
        assert config.log_validations is True
        assert config.log_level == "info"

    def test_default_model_openai(self):
        """Test default model for OpenAI provider."""
        config = ValidationConfig(semantic_provider="openai")
        assert config.default_model == "gpt-4o-mini"
        assert config.effective_model == "gpt-4o-mini"

    def test_default_model_anthropic(self):
        """Test default model for Anthropic provider."""
        config = ValidationConfig(semantic_provider="anthropic")
        assert config.default_model == "claude-3-haiku-20240307"
        assert config.effective_model == "claude-3-haiku-20240307"

    def test_custom_model_overrides_default(self):
        """Test that custom model overrides default."""
        config = ValidationConfig(
            semantic_provider="openai",
            semantic_model="gpt-4o"
        )
        assert config.effective_model == "gpt-4o"
        assert config.default_model == "gpt-4o-mini"


class TestValidationConfigValidation:
    """Tests for config validation in __post_init__."""

    def test_provider_normalized_to_lowercase(self):
        """Test that provider is normalized to lowercase."""
        config = ValidationConfig(semantic_provider="OPENAI")
        assert config.semantic_provider == "openai"

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ValidationConfig(semantic_provider="invalid")
        assert "Invalid semantic_provider" in str(exc_info.value)

    def test_valid_providers_accepted(self):
        """Test that all valid providers are accepted."""
        for provider in ("openai", "anthropic", "openai_compatible"):
            config = ValidationConfig(semantic_provider=provider)
            assert config.semantic_provider == provider

    def test_negative_timeout_raises(self):
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ValidationConfig(validation_timeout=-1)
        assert "must be positive" in str(exc_info.value)

    def test_zero_timeout_raises(self):
        """Test that zero timeout raises ValueError."""
        with pytest.raises(ValueError):
            ValidationConfig(validation_timeout=0)

    def test_very_long_timeout_warns(self):
        """Test that very long timeout triggers warning."""
        with pytest.warns(UserWarning) as record:
            ValidationConfig(validation_timeout=150)
        assert len(record) == 1
        assert "very long" in str(record[0].message).lower()

    def test_negative_max_text_size_raises(self):
        """Test that negative max_text_size raises ValueError."""
        with pytest.raises(ValueError):
            ValidationConfig(max_text_size=-1)

    def test_invalid_log_level_raises(self):
        """Test that invalid log level raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            ValidationConfig(log_level="invalid")
        assert "Invalid log_level" in str(exc_info.value)

    def test_valid_log_levels_accepted(self):
        """Test that all valid log levels are accepted."""
        for level in ("debug", "info", "warning", "error"):
            config = ValidationConfig(log_level=level)
            assert config.log_level == level


class TestValidationConfigProperties:
    """Tests for config computed properties."""

    def test_semantic_enabled_requires_key(self):
        """Test that semantic_enabled requires API key."""
        config = ValidationConfig(use_semantic=True, semantic_api_key=None)
        assert config.semantic_enabled is False

        config = ValidationConfig(use_semantic=True, semantic_api_key="sk-xxx")
        assert config.semantic_enabled is True

    def test_heuristic_only_property(self):
        """Test heuristic_only computed property."""
        # Heuristic only when semantic not enabled
        config = ValidationConfig(use_heuristic=True, use_semantic=False)
        assert config.heuristic_only is True

        # Not heuristic only when semantic is enabled
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=True,
            semantic_api_key="sk-xxx"
        )
        assert config.heuristic_only is False


class TestValidationConfigMethods:
    """Tests for config methods."""

    def test_with_semantic_creates_new_config(self):
        """Test that with_semantic creates a new config."""
        original = ValidationConfig()
        new_config = original.with_semantic(api_key="sk-xxx")

        assert new_config is not original
        assert new_config.use_semantic is True
        assert new_config.semantic_api_key == "sk-xxx"
        assert original.use_semantic is False

    def test_with_semantic_preserves_other_settings(self):
        """Test that with_semantic preserves other settings."""
        original = ValidationConfig(
            fail_closed=True,
            max_text_size=100_000,
            log_level="debug"
        )
        new_config = original.with_semantic(api_key="sk-xxx")

        assert new_config.fail_closed is True
        assert new_config.max_text_size == 100_000
        assert new_config.log_level == "debug"

    def test_to_dict_excludes_api_key(self):
        """Test that to_dict does not include API key."""
        config = ValidationConfig(
            use_semantic=True,
            semantic_api_key="sk-secret-key"
        )
        result = config.to_dict()

        # API key should never be in the dict for security
        assert "semantic_api_key" not in result
        assert result["use_semantic"] is True
        # semantic_enabled should be True because we provided a key
        assert result["semantic_enabled"] is True

    def test_to_dict_includes_derived_properties(self):
        """Test that to_dict includes derived properties."""
        config = ValidationConfig()
        result = config.to_dict()

        assert "semantic_enabled" in result
        assert "heuristic_only" in result

    def test_from_dict_creates_config(self):
        """Test that from_dict creates a valid config."""
        data = {
            "use_heuristic": True,
            "use_semantic": True,
            "semantic_provider": "anthropic",
            "semantic_model": "claude-3-opus-20240229",
            "fail_closed": True,
        }
        config = ValidationConfig.from_dict(data)

        assert config.use_heuristic is True
        assert config.use_semantic is True
        assert config.semantic_provider == "anthropic"
        assert config.semantic_model == "claude-3-opus-20240229"
        assert config.fail_closed is True

    def test_from_dict_ignores_unknown_keys(self):
        """Test that from_dict ignores unknown keys."""
        data = {
            "use_heuristic": True,
            "unknown_key": "ignored",
            "another_unknown": 123,
        }
        config = ValidationConfig.from_dict(data)
        assert config.use_heuristic is True


class TestValidationConfigFromEnv:
    """Tests for from_env class method."""

    def test_from_env_uses_defaults(self):
        """Test that from_env uses defaults when vars not set."""
        # Clear any existing vars
        for key in ["SENTINEL_USE_SEMANTIC", "SENTINEL_FAIL_CLOSED"]:
            os.environ.pop(key, None)

        config = ValidationConfig.from_env()
        assert config.use_heuristic is True
        assert config.use_semantic is False
        assert config.fail_closed is False

    def test_from_env_reads_bool_values(self):
        """Test that from_env reads boolean values correctly."""
        os.environ["SENTINEL_USE_SEMANTIC"] = "true"
        os.environ["SENTINEL_FAIL_CLOSED"] = "1"

        try:
            config = ValidationConfig.from_env()
            assert config.use_semantic is True
            assert config.fail_closed is True
        finally:
            os.environ.pop("SENTINEL_USE_SEMANTIC", None)
            os.environ.pop("SENTINEL_FAIL_CLOSED", None)

    def test_from_env_reads_false_values(self):
        """Test that from_env reads false boolean values."""
        os.environ["SENTINEL_USE_HEURISTIC"] = "false"

        try:
            config = ValidationConfig.from_env()
            assert config.use_heuristic is False
        finally:
            os.environ.pop("SENTINEL_USE_HEURISTIC", None)

    def test_from_env_reads_float_values(self):
        """Test that from_env reads float values."""
        os.environ["SENTINEL_VALIDATION_TIMEOUT"] = "45.5"

        try:
            config = ValidationConfig.from_env()
            assert config.validation_timeout == 45.5
        finally:
            os.environ.pop("SENTINEL_VALIDATION_TIMEOUT", None)

    def test_from_env_reads_int_values(self):
        """Test that from_env reads integer values."""
        os.environ["SENTINEL_MAX_TEXT_SIZE"] = "100000"

        try:
            config = ValidationConfig.from_env()
            assert config.max_text_size == 100000
        finally:
            os.environ.pop("SENTINEL_MAX_TEXT_SIZE", None)

    def test_from_env_invalid_float_uses_default(self):
        """Test that invalid float values use default."""
        os.environ["SENTINEL_VALIDATION_TIMEOUT"] = "not-a-number"

        try:
            config = ValidationConfig.from_env()
            assert config.validation_timeout == 30.0  # default
        finally:
            os.environ.pop("SENTINEL_VALIDATION_TIMEOUT", None)

    def test_from_env_custom_prefix(self):
        """Test that from_env supports custom prefix."""
        os.environ["MYAPP_USE_SEMANTIC"] = "true"

        try:
            config = ValidationConfig.from_env(prefix="MYAPP_")
            assert config.use_semantic is True
        finally:
            os.environ.pop("MYAPP_USE_SEMANTIC", None)


class TestPresetConfigs:
    """Tests for preset configuration objects."""

    def test_default_config(self):
        """Test DEFAULT_CONFIG preset."""
        assert DEFAULT_CONFIG.use_heuristic is True
        assert DEFAULT_CONFIG.use_semantic is False
        assert DEFAULT_CONFIG.fail_closed is False

    def test_strict_config(self):
        """Test STRICT_CONFIG preset."""
        assert STRICT_CONFIG.fail_closed is True
        assert STRICT_CONFIG.validation_timeout == 10.0


class TestGetApiKeyFromEnv:
    """Tests for get_api_key_from_env method."""

    def test_returns_explicit_key_first(self):
        """Test that explicit key takes precedence."""
        config = ValidationConfig(semantic_api_key="explicit-key")
        assert config.get_api_key_from_env() == "explicit-key"

    def test_returns_openai_key_from_env(self):
        """Test that OpenAI key is read from env."""
        os.environ["OPENAI_API_KEY"] = "env-openai-key"

        try:
            config = ValidationConfig(semantic_provider="openai")
            assert config.get_api_key_from_env() == "env-openai-key"
        finally:
            os.environ.pop("OPENAI_API_KEY", None)

    def test_returns_anthropic_key_from_env(self):
        """Test that Anthropic key is read from env."""
        os.environ["ANTHROPIC_API_KEY"] = "env-anthropic-key"

        try:
            config = ValidationConfig(semantic_provider="anthropic")
            assert config.get_api_key_from_env() == "env-anthropic-key"
        finally:
            os.environ.pop("ANTHROPIC_API_KEY", None)

    def test_returns_none_when_no_key(self):
        """Test that None is returned when no key available."""
        # Ensure no env vars are set
        for key in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY"]:
            os.environ.pop(key, None)

        config = ValidationConfig()
        assert config.get_api_key_from_env() is None
