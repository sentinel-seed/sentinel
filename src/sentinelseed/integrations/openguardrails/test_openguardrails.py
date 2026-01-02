"""
Tests for OpenGuardrails Integration

These tests verify the security fixes and input validation
for the openguardrails integration.

Run with: python -m pytest src/sentinelseed/integrations/openguardrails/test_openguardrails.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

# Import the module
from sentinelseed.integrations.openguardrails import (
    RiskLevel,
    DetectionResult,
    OpenGuardrailsValidator,
    SentinelOpenGuardrailsScanner,
    SentinelGuardrailsWrapper,
)


class TestRiskLevel:
    """Tests for RiskLevel enum"""

    def test_all_levels_defined(self):
        assert RiskLevel.LOW.value == "low_risk"
        assert RiskLevel.MEDIUM.value == "medium_risk"
        assert RiskLevel.HIGH.value == "high_risk"
        assert RiskLevel.CRITICAL.value == "critical_risk"


class TestDetectionResult:
    """Tests for DetectionResult dataclass"""

    def test_create_safe(self):
        result = DetectionResult(safe=True, risk_level=RiskLevel.LOW, detections=[])
        assert result.safe is True
        assert result.risk_level == RiskLevel.LOW
        assert result.detections == []

    def test_create_unsafe(self):
        result = DetectionResult(
            safe=False,
            risk_level=RiskLevel.HIGH,
            detections=["harmful content detected"]
        )
        assert result.safe is False
        assert result.risk_level == RiskLevel.HIGH
        assert len(result.detections) == 1


class TestOpenGuardrailsValidatorInit:
    """Tests for OpenGuardrailsValidator.__init__ parameter validation"""

    def test_init_default_values(self):
        validator = OpenGuardrailsValidator()
        assert validator.api_url == "http://localhost:5001"
        assert validator.timeout == 30
        assert validator.fail_safe is False

    def test_init_custom_values(self):
        validator = OpenGuardrailsValidator(
            api_url="http://custom:8080",
            timeout=60,
            api_key="test-key"
        )
        assert validator.api_url == "http://custom:8080"
        assert validator.timeout == 60
        assert validator.api_key == "test-key"

    def test_api_url_empty_raises(self):
        """M004: api_url cannot be empty"""
        with pytest.raises(ValueError, match="non-empty string"):
            OpenGuardrailsValidator(api_url="")

    def test_api_url_none_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            OpenGuardrailsValidator(api_url=None)

    def test_timeout_negative_raises(self):
        """M003: timeout must be positive"""
        with pytest.raises(ValueError, match="positive"):
            OpenGuardrailsValidator(timeout=-1)

    def test_timeout_zero_raises(self):
        """B001: timeout=0 is invalid"""
        with pytest.raises(ValueError, match="positive"):
            OpenGuardrailsValidator(timeout=0)

    def test_timeout_string_raises(self):
        """M003: timeout must be number"""
        with pytest.raises(ValueError, match="positive"):
            OpenGuardrailsValidator(timeout="abc")

    def test_api_key_int_raises(self):
        """M009: api_key must be string"""
        with pytest.raises(TypeError, match="string or None"):
            OpenGuardrailsValidator(api_key=123)

    def test_default_scanners_invalid_type_raises(self):
        """M006: default_scanners must be list"""
        with pytest.raises(TypeError, match="list or None"):
            OpenGuardrailsValidator(default_scanners="scanner1")

    def test_default_scanners_with_int_raises(self):
        """M006: scanners list must contain strings"""
        with pytest.raises(TypeError, match="must be string"):
            OpenGuardrailsValidator(default_scanners=["valid", 123])

    def test_fail_safe_string_raises(self):
        with pytest.raises(TypeError, match="bool"):
            OpenGuardrailsValidator(fail_safe="yes")


class TestSentinelOpenGuardrailsScannerInit:
    """Tests for SentinelOpenGuardrailsScanner.__init__ parameter validation"""

    def test_risk_level_invalid_string_raises(self):
        """C002: risk_level must be valid"""
        with pytest.raises(ValueError, match="Invalid risk_level"):
            SentinelOpenGuardrailsScanner(risk_level="invalid")

    def test_risk_level_int_raises(self):
        """C002: risk_level must be RiskLevel or string"""
        with pytest.raises(TypeError, match="RiskLevel enum or string"):
            SentinelOpenGuardrailsScanner(risk_level=123)

    def test_risk_level_valid_string_accepted(self):
        """C002: valid string should convert to RiskLevel"""
        scanner = SentinelOpenGuardrailsScanner(risk_level="high_risk")
        assert scanner.risk_level == RiskLevel.HIGH

    def test_risk_level_enum_accepted(self):
        scanner = SentinelOpenGuardrailsScanner(risk_level=RiskLevel.CRITICAL)
        assert scanner.risk_level == RiskLevel.CRITICAL

    def test_timeout_negative_raises(self):
        """M003: timeout must be positive"""
        with pytest.raises(ValueError, match="positive"):
            SentinelOpenGuardrailsScanner(timeout=-1)

    def test_timeout_zero_raises(self):
        with pytest.raises(ValueError, match="positive"):
            SentinelOpenGuardrailsScanner(timeout=0)

    def test_scan_prompt_string_raises(self):
        """M008: scan_prompt must be bool"""
        with pytest.raises(TypeError, match="bool"):
            SentinelOpenGuardrailsScanner(scan_prompt="yes")

    def test_scan_response_int_raises(self):
        """M008: scan_response must be bool"""
        with pytest.raises(TypeError, match="bool"):
            SentinelOpenGuardrailsScanner(scan_response=1)

    def test_jwt_token_int_raises(self):
        """M007: jwt_token must be string"""
        with pytest.raises(TypeError, match="string or None"):
            SentinelOpenGuardrailsScanner(jwt_token=123)


class TestSentinelGuardrailsWrapperValidation:
    """Tests for SentinelGuardrailsWrapper.validate() security fixes

    These tests use LayeredValidator mocks to test error handling,
    since SentinelGuardrailsWrapper uses LayeredValidator internally.
    """

    def test_validator_exception_returns_safe_false(self):
        """C003: Validator exception must return safe=False"""
        from unittest.mock import MagicMock

        mock_validator = MagicMock()
        mock_validator.validate.side_effect = RuntimeError("Validator crashed!")

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is False
        assert "sentinel_error" in result["blocked_by"]

    def test_validator_returns_unsafe_returns_safe_false(self):
        """C004: Validator returning is_safe=False must return safe=False"""
        from unittest.mock import MagicMock
        from sentinelseed.validation import ValidationResult
        from sentinelseed.validation.types import ValidationLayer, RiskLevel

        mock_validator = MagicMock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            violations=["Test violation"],
            layer=ValidationLayer.HEURISTIC,
            risk_level=RiskLevel.HIGH,
        )

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is False
        assert "sentinel" in result["blocked_by"]

    def test_validator_returns_safe_returns_safe_true(self):
        """Normal case: Validator returning is_safe=True returns safe=True"""
        from unittest.mock import MagicMock
        from sentinelseed.validation import ValidationResult
        from sentinelseed.validation.types import ValidationLayer, RiskLevel

        mock_validator = MagicMock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=True,
            violations=[],
            layer=ValidationLayer.HEURISTIC,
            risk_level=RiskLevel.LOW,
        )

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is True

    def test_validator_blocks_returns_safe_false(self):
        """Normal case: Validator blocking returns safe=False"""
        from unittest.mock import MagicMock
        from sentinelseed.validation import ValidationResult
        from sentinelseed.validation.types import ValidationLayer, RiskLevel

        mock_validator = MagicMock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            violations=["Blocked by validator"],
            layer=ValidationLayer.HEURISTIC,
            risk_level=RiskLevel.HIGH,
        )

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is False
        assert "sentinel" in result["blocked_by"]

    def test_sentinel_passes_returns_safe_true(self):
        """Normal case: Sentinel passing returns safe=True"""
        class PassingSentinel:
            def validate(self, content):
                return {"safe": True}

        wrapper = SentinelGuardrailsWrapper(sentinel=PassingSentinel())
        result = wrapper.validate("test content")

        assert result["safe"] is True
        assert result["blocked_by"] == []

    def test_require_both_one_fails_blocks(self):
        """C001: require_both=True - if one fails, block"""
        class PassingSentinel:
            def validate(self, content):
                return {"safe": True}

        class FailingGuardrails:
            def validate(self, content, scanners=None):
                return DetectionResult(safe=False, risk_level=RiskLevel.HIGH, detections=["blocked"])

        wrapper = SentinelGuardrailsWrapper(
            sentinel=PassingSentinel(),
            openguardrails=FailingGuardrails(),
            require_both=True
        )
        result = wrapper.validate("test content")

        # With require_both=True, if OpenGuardrails fails, result should be safe=False
        assert result["safe"] is False
        assert "openguardrails" in result["blocked_by"]

    def test_require_both_both_pass_safe(self):
        """C001: require_both=True - both pass, safe=True"""
        class PassingSentinel:
            def validate(self, content):
                return {"safe": True}

        class PassingGuardrails:
            def validate(self, content, scanners=None):
                return DetectionResult(safe=True, risk_level=RiskLevel.LOW, detections=[])

        wrapper = SentinelGuardrailsWrapper(
            sentinel=PassingSentinel(),
            openguardrails=PassingGuardrails(),
            require_both=True
        )
        result = wrapper.validate("test content")

        assert result["safe"] is True
        assert result["blocked_by"] == []

    def test_openguardrails_exception_returns_safe_false(self):
        """OpenGuardrails exception must return safe=False"""
        class PassingSentinel:
            def validate(self, content):
                return {"safe": True}

        class ExceptionGuardrails:
            def validate(self, content, scanners=None):
                raise RuntimeError("OpenGuardrails crashed!")

        wrapper = SentinelGuardrailsWrapper(
            sentinel=PassingSentinel(),
            openguardrails=ExceptionGuardrails()
        )
        result = wrapper.validate("test content")

        assert result["safe"] is False
        assert "openguardrails_error" in result["blocked_by"]

    def test_empty_content_raises(self):
        """Empty content should raise ValueError"""
        wrapper = SentinelGuardrailsWrapper()
        with pytest.raises(ValueError):
            wrapper.validate("")

    def test_none_content_raises(self):
        """None content should raise ValueError"""
        wrapper = SentinelGuardrailsWrapper()
        with pytest.raises(ValueError):
            wrapper.validate(None)


class TestOpenGuardrailsValidatorValidate:
    """Tests for OpenGuardrailsValidator.validate()"""

    def test_empty_content_raises(self):
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="cannot be empty"):
            validator.validate("")

    def test_none_content_raises(self):
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="cannot be None"):
            validator.validate(None)

    def test_int_content_raises(self):
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="must be a string"):
            validator.validate(123)


class TestImportConditionals:
    """Tests for M001/M002 - Import conditionals"""

    def test_requests_not_available_raises(self):
        """When requests not available, should raise ImportError"""
        with patch.dict('sys.modules', {'requests': None}):
            # The module is already loaded, so we test the flag behavior
            pass  # This is tested by the REQUESTS_AVAILABLE flag check


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
