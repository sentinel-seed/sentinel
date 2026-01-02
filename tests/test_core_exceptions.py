"""
Tests for sentinelseed.core.exceptions module.
"""

import pytest
from sentinelseed.core.exceptions import (
    SentinelError,
    ValidationError,
    ConfigurationError,
    IntegrationError,
)


class TestSentinelError:
    """Tests for base SentinelError exception."""

    def test_simple_message(self):
        """Test creating exception with just a message."""
        error = SentinelError("Something went wrong")
        assert str(error) == "Something went wrong"
        assert error.message == "Something went wrong"
        assert error.context == {}

    def test_message_with_context(self):
        """Test creating exception with context dictionary."""
        error = SentinelError(
            "Operation failed",
            context={"operation": "validate", "content_length": 1000}
        )
        assert "Operation failed" in str(error)
        assert "operation=validate" in str(error)
        assert "content_length=1000" in str(error)
        assert error.context == {"operation": "validate", "content_length": 1000}

    def test_is_base_exception(self):
        """Test that SentinelError inherits from Exception."""
        error = SentinelError("test")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        """Test that exception can be raised and caught."""
        with pytest.raises(SentinelError) as exc_info:
            raise SentinelError("Test error")
        assert str(exc_info.value) == "Test error"


class TestValidationError:
    """Tests for ValidationError exception."""

    def test_simple_validation_error(self):
        """Test creating a simple validation error."""
        error = ValidationError("Content failed validation")
        assert "Content failed validation" in str(error)
        assert error.violations == []
        assert error.risk_level is None

    def test_validation_error_with_violations(self):
        """Test validation error with violations list."""
        error = ValidationError(
            "Content blocked",
            violations=["Harm detected", "Jailbreak attempt"]
        )
        assert "Content blocked" in str(error)
        assert "Harm detected" in str(error)
        assert "Jailbreak attempt" in str(error)
        assert error.violations == ["Harm detected", "Jailbreak attempt"]

    def test_validation_error_with_risk_level(self):
        """Test validation error with risk level."""
        error = ValidationError(
            "High risk content",
            risk_level="high",
            violations=["Violence detected"]
        )
        assert error.risk_level == "high"
        assert "risk_level=high" in str(error)

    def test_violations_truncation_in_str(self):
        """Test that many violations are truncated in string representation."""
        error = ValidationError(
            "Multiple issues",
            violations=["Issue 1", "Issue 2", "Issue 3", "Issue 4", "Issue 5"]
        )
        # Should show first 3 and indicate more
        assert "+2 more" in str(error)

    def test_inherits_from_sentinel_error(self):
        """Test that ValidationError inherits from SentinelError."""
        error = ValidationError("test")
        assert isinstance(error, SentinelError)


class TestConfigurationError:
    """Tests for ConfigurationError exception."""

    def test_simple_config_error(self):
        """Test creating a simple configuration error."""
        error = ConfigurationError("Invalid configuration")
        assert str(error) == "Invalid configuration"
        assert error.parameter is None

    def test_config_error_with_parameter(self):
        """Test configuration error with parameter name."""
        error = ConfigurationError(
            "API key required",
            parameter="semantic_api_key"
        )
        assert "API key required" in str(error)
        assert "parameter=semantic_api_key" in str(error)
        assert error.parameter == "semantic_api_key"

    def test_config_error_with_context(self):
        """Test configuration error with additional context."""
        error = ConfigurationError(
            "Invalid timeout",
            parameter="validation_timeout",
            context={"provided_value": -5}
        )
        assert error.parameter == "validation_timeout"
        assert "parameter=validation_timeout" in str(error)
        assert "provided_value=-5" in str(error)

    def test_inherits_from_sentinel_error(self):
        """Test that ConfigurationError inherits from SentinelError."""
        error = ConfigurationError("test")
        assert isinstance(error, SentinelError)


class TestIntegrationError:
    """Tests for IntegrationError exception."""

    def test_simple_integration_error(self):
        """Test creating a simple integration error."""
        error = IntegrationError("Integration failed")
        assert str(error) == "Integration failed"
        assert error.integration is None
        assert error.operation is None

    def test_integration_error_with_integration_name(self):
        """Test integration error with integration name."""
        error = IntegrationError(
            "Failed to initialize",
            integration="langchain"
        )
        assert "Failed to initialize" in str(error)
        assert "integration=langchain" in str(error)
        assert error.integration == "langchain"

    def test_integration_error_with_operation(self):
        """Test integration error with operation name."""
        error = IntegrationError(
            "Callback failed",
            integration="crewai",
            operation="before_task_execution"
        )
        assert error.integration == "crewai"
        assert error.operation == "before_task_execution"
        assert "integration=crewai" in str(error)
        assert "operation=before_task_execution" in str(error)

    def test_integration_error_with_full_context(self):
        """Test integration error with full context."""
        error = IntegrationError(
            "Provider error",
            integration="openai",
            operation="chat_completion",
            context={"status_code": 429, "retry_after": 60}
        )
        assert error.integration == "openai"
        assert error.operation == "chat_completion"
        assert "status_code=429" in str(error)
        assert "retry_after=60" in str(error)

    def test_inherits_from_sentinel_error(self):
        """Test that IntegrationError inherits from SentinelError."""
        error = IntegrationError("test")
        assert isinstance(error, SentinelError)


class TestExceptionHierarchy:
    """Tests for exception hierarchy and catch behavior."""

    def test_catch_all_sentinel_errors(self):
        """Test that all specific errors can be caught as SentinelError."""
        errors = [
            ValidationError("validation failed"),
            ConfigurationError("config invalid"),
            IntegrationError("integration failed"),
        ]

        for error in errors:
            with pytest.raises(SentinelError):
                raise error

    def test_specific_catches_work(self):
        """Test that specific exception types can be caught."""
        with pytest.raises(ValidationError):
            raise ValidationError("test")

        with pytest.raises(ConfigurationError):
            raise ConfigurationError("test")

        with pytest.raises(IntegrationError):
            raise IntegrationError("test")

    def test_validation_error_not_caught_as_config_error(self):
        """Test that specific exceptions don't catch wrong types."""
        with pytest.raises(ValidationError):
            try:
                raise ValidationError("validation issue")
            except ConfigurationError:
                pytest.fail("Should not catch as ConfigurationError")
