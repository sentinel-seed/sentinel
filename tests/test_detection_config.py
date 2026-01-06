"""
Tests for sentinelseed.detection.config module.

This module tests the configuration classes for InputValidator and OutputValidator:
- ValidationMode, LLMProvider, Strictness enums
- DetectionConfig (base class)
- InputValidatorConfig
- OutputValidatorConfig

Test Categories:
    1. Enums: Values, string inheritance
    2. Validation: Parameter bounds, type conversion
    3. Environment: from_env(), env var loading
    4. File Loading: from_file() with JSON
    5. Factory Methods: strict(), lenient(), for_context()
    6. Serialization: to_dict()
    7. Properties: is_semantic, is_heuristic, severity_threshold
"""

import json
import os
import tempfile
import pytest
from pathlib import Path

from sentinelseed.detection.config import (
    ValidationMode,
    LLMProvider,
    Strictness,
    DetectionConfig,
    InputValidatorConfig,
    OutputValidatorConfig,
)


# =============================================================================
# Enum Tests
# =============================================================================

class TestValidationMode:
    """Tests for ValidationMode enum."""

    def test_values_exist(self):
        """All expected values exist."""
        assert ValidationMode.AUTO.value == "auto"
        assert ValidationMode.HEURISTIC.value == "heuristic"
        assert ValidationMode.SEMANTIC.value == "semantic"

    def test_string_inheritance(self):
        """ValidationMode is a string enum."""
        assert isinstance(ValidationMode.AUTO, str)
        assert ValidationMode.HEURISTIC == "heuristic"

    def test_all_modes_count(self):
        """Verify we have exactly 3 modes."""
        assert len(ValidationMode) == 3


class TestLLMProvider:
    """Tests for LLMProvider enum."""

    def test_values_exist(self):
        """All expected values exist."""
        assert LLMProvider.OPENAI.value == "openai"
        assert LLMProvider.ANTHROPIC.value == "anthropic"

    def test_string_inheritance(self):
        """LLMProvider is a string enum."""
        assert isinstance(LLMProvider.OPENAI, str)

    def test_all_providers_count(self):
        """Verify we have exactly 2 providers."""
        assert len(LLMProvider) == 2


class TestStrictness:
    """Tests for Strictness enum."""

    def test_values_exist(self):
        """All expected values exist."""
        assert Strictness.LENIENT.value == "lenient"
        assert Strictness.BALANCED.value == "balanced"
        assert Strictness.STRICT.value == "strict"
        assert Strictness.PARANOID.value == "paranoid"

    def test_all_levels_count(self):
        """Verify we have exactly 4 strictness levels."""
        assert len(Strictness) == 4


# =============================================================================
# DetectionConfig Tests
# =============================================================================

class TestDetectionConfig:
    """Tests for DetectionConfig base class."""

    def test_default_values(self):
        """Default values are correctly set."""
        config = DetectionConfig()
        # Mode resolves to HEURISTIC without API key
        assert config.mode == ValidationMode.HEURISTIC
        assert config.provider == LLMProvider.OPENAI
        assert config.model is None
        assert config.timeout == 10.0
        assert config.max_text_length == 50000
        assert config.fail_closed is True
        assert config.log_level == "info"

    def test_custom_values(self):
        """Can create with custom values."""
        config = DetectionConfig(
            mode=ValidationMode.HEURISTIC,
            provider=LLMProvider.ANTHROPIC,
            model="claude-3",
            timeout=30.0,
            max_text_length=10000,
            fail_closed=False,
            log_level="debug",
        )
        assert config.mode == ValidationMode.HEURISTIC
        assert config.provider == LLMProvider.ANTHROPIC
        assert config.model == "claude-3"
        assert config.timeout == 30.0
        assert config.max_text_length == 10000
        assert config.fail_closed is False
        assert config.log_level == "debug"


class TestDetectionConfigValidation:
    """Tests for DetectionConfig validation."""

    def test_timeout_zero_raises(self):
        """timeout <= 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DetectionConfig(timeout=0)
        assert "timeout" in str(exc_info.value)

    def test_timeout_negative_raises(self):
        """Negative timeout raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DetectionConfig(timeout=-1.0)
        assert "timeout" in str(exc_info.value)

    def test_max_text_length_zero_raises(self):
        """max_text_length <= 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DetectionConfig(max_text_length=0)
        assert "max_text_length" in str(exc_info.value)

    def test_string_mode_converted(self):
        """String mode is converted to enum."""
        config = DetectionConfig(mode="heuristic")
        assert config.mode == ValidationMode.HEURISTIC

    def test_string_provider_converted(self):
        """String provider is converted to enum."""
        config = DetectionConfig(provider="anthropic")
        assert config.provider == LLMProvider.ANTHROPIC


class TestDetectionConfigAutoMode:
    """Tests for DetectionConfig AUTO mode resolution."""

    def test_auto_resolves_to_heuristic_without_api_key(self):
        """AUTO mode resolves to HEURISTIC without API key."""
        config = DetectionConfig(mode=ValidationMode.AUTO, api_key=None)
        assert config.mode == ValidationMode.HEURISTIC

    def test_auto_resolves_to_semantic_with_api_key(self):
        """AUTO mode resolves to SEMANTIC with API key."""
        config = DetectionConfig(mode=ValidationMode.AUTO, api_key="sk-test")
        assert config.mode == ValidationMode.SEMANTIC


class TestDetectionConfigProperties:
    """Tests for DetectionConfig computed properties."""

    def test_is_semantic_true_with_api_key(self):
        """is_semantic is True when semantic mode with API key."""
        config = DetectionConfig(mode=ValidationMode.SEMANTIC, api_key="sk-test")
        assert config.is_semantic is True
        assert config.is_heuristic is False

    def test_is_semantic_false_without_api_key(self):
        """is_semantic is False when semantic mode but no API key."""
        config = DetectionConfig(mode=ValidationMode.SEMANTIC, api_key=None)
        assert config.is_semantic is False

    def test_is_heuristic_true(self):
        """is_heuristic is True when heuristic mode."""
        config = DetectionConfig(mode=ValidationMode.HEURISTIC)
        assert config.is_heuristic is True
        assert config.is_semantic is False


class TestDetectionConfigSerialization:
    """Tests for DetectionConfig.to_dict()."""

    def test_to_dict_structure(self):
        """to_dict() returns correct structure."""
        config = DetectionConfig(
            mode=ValidationMode.HEURISTIC,
            provider=LLMProvider.OPENAI,
        )
        d = config.to_dict()

        assert d["mode"] == "heuristic"
        assert d["provider"] == "openai"
        assert d["timeout"] == 10.0
        assert d["fail_closed"] is True

    def test_to_dict_masks_api_key(self):
        """to_dict() masks API key for security."""
        config = DetectionConfig(api_key="sk-secret-key-12345")
        d = config.to_dict()
        assert d["api_key"] == "***"

    def test_to_dict_null_api_key(self):
        """to_dict() shows None for missing API key."""
        config = DetectionConfig(api_key=None)
        d = config.to_dict()
        assert d["api_key"] is None


# =============================================================================
# InputValidatorConfig Tests
# =============================================================================

class TestInputValidatorConfig:
    """Tests for InputValidatorConfig class."""

    def test_default_values(self):
        """Default values are correctly set."""
        config = InputValidatorConfig()
        assert config.use_embeddings is True
        assert config.embedding_model == "all-MiniLM-L6-v2"
        assert config.embedding_threshold == 0.72
        assert config.embedding_cache_size == 1000
        assert config.enabled_detectors is None
        assert config.detector_weights == {}
        assert config.min_confidence_to_block == 0.7
        assert config.require_multiple_detectors is False
        assert config.min_detectors_to_block == 2
        assert config.parallel_detection is True
        assert config.warmup_on_init is True

    def test_inherits_from_detection_config(self):
        """InputValidatorConfig inherits from DetectionConfig."""
        config = InputValidatorConfig()
        assert hasattr(config, "mode")
        assert hasattr(config, "api_key")
        assert hasattr(config, "is_semantic")


class TestInputValidatorConfigValidation:
    """Tests for InputValidatorConfig validation."""

    def test_embedding_threshold_below_zero_raises(self):
        """embedding_threshold < 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            InputValidatorConfig(embedding_threshold=-0.1)
        assert "embedding_threshold" in str(exc_info.value)

    def test_embedding_threshold_above_one_raises(self):
        """embedding_threshold > 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            InputValidatorConfig(embedding_threshold=1.1)
        assert "embedding_threshold" in str(exc_info.value)

    def test_min_confidence_below_zero_raises(self):
        """min_confidence_to_block < 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            InputValidatorConfig(min_confidence_to_block=-0.1)
        assert "min_confidence_to_block" in str(exc_info.value)

    def test_min_confidence_above_one_raises(self):
        """min_confidence_to_block > 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            InputValidatorConfig(min_confidence_to_block=1.1)
        assert "min_confidence_to_block" in str(exc_info.value)

    def test_min_detectors_below_one_raises(self):
        """min_detectors_to_block < 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            InputValidatorConfig(min_detectors_to_block=0)
        assert "min_detectors_to_block" in str(exc_info.value)


class TestInputValidatorConfigEnvironment:
    """Tests for InputValidatorConfig.from_env()."""

    def test_from_env_defaults(self):
        """from_env() works with no environment variables."""
        # Clear relevant env vars
        for key in ["SENTINEL_API_KEY", "SENTINEL_PROVIDER", "SENTINEL_MODE"]:
            os.environ.pop(key, None)

        config = InputValidatorConfig.from_env()
        assert config.api_key is None
        assert config.provider == LLMProvider.OPENAI
        assert config.mode == ValidationMode.HEURISTIC

    def test_from_env_with_api_key(self):
        """from_env() reads SENTINEL_API_KEY."""
        os.environ["SENTINEL_API_KEY"] = "test-key"
        try:
            config = InputValidatorConfig.from_env()
            assert config.api_key == "test-key"
        finally:
            del os.environ["SENTINEL_API_KEY"]

    def test_from_env_with_provider(self):
        """from_env() reads SENTINEL_PROVIDER."""
        os.environ["SENTINEL_PROVIDER"] = "anthropic"
        try:
            config = InputValidatorConfig.from_env()
            assert config.provider == LLMProvider.ANTHROPIC
        finally:
            del os.environ["SENTINEL_PROVIDER"]

    def test_from_env_with_mode(self):
        """from_env() reads SENTINEL_MODE."""
        os.environ["SENTINEL_MODE"] = "heuristic"
        try:
            config = InputValidatorConfig.from_env()
            assert config.mode == ValidationMode.HEURISTIC
        finally:
            del os.environ["SENTINEL_MODE"]


class TestInputValidatorConfigFile:
    """Tests for InputValidatorConfig.from_file()."""

    def test_from_json_file(self):
        """from_file() loads JSON configuration."""
        config_data = {
            "mode": "heuristic",
            "min_confidence_to_block": 0.8,
            "use_embeddings": False,
            "timeout": 15.0,
        }

        # Create temp file, close it, then use it (Windows compatibility)
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(config_data, f)

            config = InputValidatorConfig.from_file(path)
            assert config.mode == ValidationMode.HEURISTIC
            assert config.min_confidence_to_block == 0.8
            assert config.use_embeddings is False
            assert config.timeout == 15.0
        finally:
            os.unlink(path)

    def test_from_file_not_found(self):
        """from_file() raises FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            InputValidatorConfig.from_file("nonexistent.json")

    def test_from_file_unsupported_format(self):
        """from_file() raises ValueError for unsupported format."""
        fd, path = tempfile.mkstemp(suffix=".txt")
        try:
            with os.fdopen(fd, "w") as f:
                f.write("some content")

            with pytest.raises(ValueError) as exc_info:
                InputValidatorConfig.from_file(path)
            assert "Unsupported" in str(exc_info.value)
        finally:
            os.unlink(path)


class TestInputValidatorConfigPresets:
    """Tests for InputValidatorConfig factory presets."""

    def test_strict_preset(self):
        """strict() creates strict configuration."""
        config = InputValidatorConfig.strict()
        assert config.min_confidence_to_block == 0.5
        assert config.require_multiple_detectors is False
        assert config.fail_closed is True

    def test_lenient_preset(self):
        """lenient() creates lenient configuration."""
        config = InputValidatorConfig.lenient()
        assert config.min_confidence_to_block == 0.85
        assert config.require_multiple_detectors is True
        assert config.min_detectors_to_block == 2
        assert config.fail_closed is False


class TestInputValidatorConfigSerialization:
    """Tests for InputValidatorConfig.to_dict()."""

    def test_to_dict_includes_input_specific_fields(self):
        """to_dict() includes InputValidator-specific fields."""
        config = InputValidatorConfig(
            use_embeddings=True,
            embedding_threshold=0.75,
            min_confidence_to_block=0.8,
        )
        d = config.to_dict()

        # Base fields
        assert "mode" in d
        assert "api_key" in d

        # Input-specific fields
        assert d["use_embeddings"] is True
        assert d["embedding_threshold"] == 0.75
        assert d["min_confidence_to_block"] == 0.8
        assert "enabled_detectors" in d
        assert "parallel_detection" in d


# =============================================================================
# OutputValidatorConfig Tests
# =============================================================================

class TestOutputValidatorConfig:
    """Tests for OutputValidatorConfig class."""

    def test_default_values(self):
        """Default values are correctly set."""
        config = OutputValidatorConfig()
        assert config.context_type == "general"
        assert config.strictness == Strictness.BALANCED
        assert config.enabled_checkers is None
        assert config.checker_weights == {}
        assert config.min_severity_to_block == "high"
        assert config.require_multiple_checkers is False
        assert config.parallel_checking is True

    def test_inherits_from_detection_config(self):
        """OutputValidatorConfig inherits from DetectionConfig."""
        config = OutputValidatorConfig()
        assert hasattr(config, "mode")
        assert hasattr(config, "api_key")
        assert hasattr(config, "is_semantic")


class TestOutputValidatorConfigValidation:
    """Tests for OutputValidatorConfig validation."""

    def test_invalid_severity_raises(self):
        """Invalid min_severity_to_block raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            OutputValidatorConfig(min_severity_to_block="invalid")
        assert "min_severity_to_block" in str(exc_info.value)

    def test_valid_severities(self):
        """All valid severity levels work."""
        for severity in ["low", "medium", "high", "critical"]:
            config = OutputValidatorConfig(min_severity_to_block=severity)
            assert config.min_severity_to_block == severity

    def test_severity_normalized_to_lowercase(self):
        """Severity is normalized to lowercase."""
        config = OutputValidatorConfig(min_severity_to_block="HIGH")
        assert config.min_severity_to_block == "high"

    def test_string_strictness_converted(self):
        """String strictness is converted to enum."""
        config = OutputValidatorConfig(strictness="strict")
        assert config.strictness == Strictness.STRICT


class TestOutputValidatorConfigProperties:
    """Tests for OutputValidatorConfig computed properties."""

    def test_severity_threshold_low(self):
        """severity_threshold returns correct value for low."""
        config = OutputValidatorConfig(min_severity_to_block="low")
        assert config.severity_threshold == 1

    def test_severity_threshold_medium(self):
        """severity_threshold returns correct value for medium."""
        config = OutputValidatorConfig(min_severity_to_block="medium")
        assert config.severity_threshold == 2

    def test_severity_threshold_high(self):
        """severity_threshold returns correct value for high."""
        config = OutputValidatorConfig(min_severity_to_block="high")
        assert config.severity_threshold == 3

    def test_severity_threshold_critical(self):
        """severity_threshold returns correct value for critical."""
        config = OutputValidatorConfig(min_severity_to_block="critical")
        assert config.severity_threshold == 4


class TestOutputValidatorConfigEnvironment:
    """Tests for OutputValidatorConfig.from_env()."""

    def test_from_env_defaults(self):
        """from_env() works with no environment variables."""
        for key in ["SENTINEL_API_KEY", "SENTINEL_CONTEXT_TYPE"]:
            os.environ.pop(key, None)

        config = OutputValidatorConfig.from_env()
        assert config.context_type == "general"

    def test_from_env_with_context_type(self):
        """from_env() reads SENTINEL_CONTEXT_TYPE."""
        os.environ["SENTINEL_CONTEXT_TYPE"] = "healthcare"
        try:
            config = OutputValidatorConfig.from_env()
            assert config.context_type == "healthcare"
        finally:
            del os.environ["SENTINEL_CONTEXT_TYPE"]


class TestOutputValidatorConfigFile:
    """Tests for OutputValidatorConfig.from_file()."""

    def test_from_json_file(self):
        """from_file() loads JSON configuration."""
        config_data = {
            "mode": "heuristic",
            "context_type": "financial",
            "strictness": "strict",
            "min_severity_to_block": "medium",
        }

        # Create temp file, close it, then use it (Windows compatibility)
        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(config_data, f)

            config = OutputValidatorConfig.from_file(path)
            assert config.context_type == "financial"
            assert config.strictness == Strictness.STRICT
            assert config.min_severity_to_block == "medium"
        finally:
            os.unlink(path)


class TestOutputValidatorConfigPresets:
    """Tests for OutputValidatorConfig factory presets."""

    def test_strict_preset(self):
        """strict() creates strict configuration."""
        config = OutputValidatorConfig.strict()
        assert config.strictness == Strictness.STRICT
        assert config.min_severity_to_block == "medium"
        assert config.require_multiple_checkers is False
        assert config.fail_closed is True

    def test_lenient_preset(self):
        """lenient() creates lenient configuration."""
        config = OutputValidatorConfig.lenient()
        assert config.strictness == Strictness.LENIENT
        assert config.min_severity_to_block == "critical"
        assert config.require_multiple_checkers is True
        assert config.fail_closed is False


class TestOutputValidatorConfigContextPresets:
    """Tests for OutputValidatorConfig.for_context() factory."""

    def test_customer_service_context(self):
        """for_context('customer_service') returns appropriate config."""
        config = OutputValidatorConfig.for_context("customer_service")
        assert config.context_type == "customer_service"
        assert config.strictness == Strictness.BALANCED
        assert config.min_severity_to_block == "high"

    def test_financial_context(self):
        """for_context('financial') returns strict config."""
        config = OutputValidatorConfig.for_context("financial")
        assert config.context_type == "financial"
        assert config.strictness == Strictness.STRICT
        assert config.min_severity_to_block == "medium"

    def test_healthcare_context(self):
        """for_context('healthcare') returns strict config."""
        config = OutputValidatorConfig.for_context("healthcare")
        assert config.context_type == "healthcare"
        assert config.strictness == Strictness.STRICT

    def test_education_context(self):
        """for_context('education') returns balanced config."""
        config = OutputValidatorConfig.for_context("education")
        assert config.context_type == "education"
        assert config.strictness == Strictness.BALANCED

    def test_unknown_context_defaults(self):
        """for_context() with unknown type returns default config."""
        config = OutputValidatorConfig.for_context("custom_context")
        assert config.context_type == "custom_context"
        # Uses default strictness
        assert config.strictness == Strictness.BALANCED


class TestOutputValidatorConfigSerialization:
    """Tests for OutputValidatorConfig.to_dict()."""

    def test_to_dict_includes_output_specific_fields(self):
        """to_dict() includes OutputValidator-specific fields."""
        config = OutputValidatorConfig(
            context_type="healthcare",
            strictness=Strictness.STRICT,
            min_severity_to_block="medium",
        )
        d = config.to_dict()

        # Base fields
        assert "mode" in d
        assert "api_key" in d

        # Output-specific fields
        assert d["context_type"] == "healthcare"
        assert d["strictness"] == "strict"
        assert d["min_severity_to_block"] == "medium"
        assert "enabled_checkers" in d
        assert "parallel_checking" in d


# =============================================================================
# Integration Tests
# =============================================================================

class TestConfigIntegration:
    """Integration tests for configuration classes."""

    def test_input_and_output_configs_independent(self):
        """Input and output configs don't affect each other."""
        input_config = InputValidatorConfig(
            min_confidence_to_block=0.9,
            api_key="input-key",
        )
        output_config = OutputValidatorConfig(
            min_severity_to_block="low",
            api_key="output-key",
        )

        assert input_config.min_confidence_to_block == 0.9
        assert output_config.min_severity_to_block == "low"
        assert input_config.api_key == "input-key"
        assert output_config.api_key == "output-key"

    def test_config_round_trip_through_dict(self):
        """Config can be serialized and values match."""
        original = InputValidatorConfig(
            mode=ValidationMode.HEURISTIC,
            min_confidence_to_block=0.8,
            use_embeddings=False,
            timeout=20.0,
        )
        d = original.to_dict()

        # Note: Can't fully reconstruct from dict due to API key masking,
        # but we can verify the non-sensitive values
        assert d["mode"] == "heuristic"
        assert d["min_confidence_to_block"] == 0.8
        assert d["use_embeddings"] is False
        assert d["timeout"] == 20.0

    def test_all_config_classes_have_to_dict(self):
        """All config classes implement to_dict()."""
        configs = [
            DetectionConfig(),
            InputValidatorConfig(),
            OutputValidatorConfig(),
        ]
        for config in configs:
            d = config.to_dict()
            assert isinstance(d, dict)
            assert "mode" in d
