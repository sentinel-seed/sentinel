"""
Tests for OpenGuardrails integration.

Tests cover:
- DetectionResult parsing and validation
- OpenGuardrailsValidator input validation and error handling
- SentinelOpenGuardrailsScanner configuration
- SentinelGuardrailsWrapper combined validation
- Convenience functions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from json import JSONDecodeError

from sentinelseed.integrations.openguardrails import (
    DetectionResult,
    RiskLevel,
    ScannerType,
    OpenGuardrailsValidator,
    SentinelOpenGuardrailsScanner,
    SentinelGuardrailsWrapper,
    register_sentinel_scanner,
    create_combined_validator,
    REQUESTS_AVAILABLE,
    __version__,
)


class TestModuleAttributes:
    """Test module-level attributes."""

    def test_version_exists(self):
        """Module should have a version string."""
        assert __version__ is not None
        assert isinstance(__version__, str)
        assert len(__version__) > 0

    def test_requests_available_flag(self):
        """REQUESTS_AVAILABLE should be a boolean."""
        assert isinstance(REQUESTS_AVAILABLE, bool)


class TestRiskLevel:
    """Test RiskLevel enum."""

    def test_risk_level_values(self):
        """RiskLevel should have expected values."""
        assert RiskLevel.LOW.value == "low_risk"
        assert RiskLevel.MEDIUM.value == "medium_risk"
        assert RiskLevel.HIGH.value == "high_risk"
        assert RiskLevel.CRITICAL.value == "critical_risk"

    def test_risk_level_is_string_enum(self):
        """RiskLevel should be a string enum."""
        assert isinstance(RiskLevel.LOW, str)
        assert RiskLevel.LOW == "low_risk"


class TestScannerType:
    """Test ScannerType enum."""

    def test_scanner_type_values(self):
        """ScannerType should have expected values."""
        assert ScannerType.GENAI.value == "genai"
        assert ScannerType.REGEX.value == "regex"
        assert ScannerType.KEYWORD.value == "keyword"


class TestDetectionResult:
    """Test DetectionResult dataclass."""

    def test_creation_with_valid_data(self):
        """Should create DetectionResult with valid data."""
        result = DetectionResult(
            safe=True,
            risk_level=RiskLevel.LOW,
            detections=[],
            raw_response={"test": "data"},
        )
        assert result.safe is True
        assert result.risk_level == RiskLevel.LOW
        assert result.detections == []
        assert result.raw_response == {"test": "data"}

    def test_from_response_empty_detections(self):
        """Should handle empty detections list."""
        response = {"detections": []}
        result = DetectionResult.from_response(response)
        assert result.safe is True
        assert result.risk_level == RiskLevel.LOW
        assert result.detections == []

    def test_from_response_low_risk_detection(self):
        """Should handle low risk detection."""
        response = {
            "detections": [
                {"type": "test", "risk_level": "low_risk"}
            ]
        }
        result = DetectionResult.from_response(response)
        assert result.safe is True
        assert result.risk_level == RiskLevel.LOW

    def test_from_response_high_risk_detection(self):
        """Should mark unsafe for high risk detection."""
        response = {
            "detections": [
                {"type": "harmful", "risk_level": "high_risk"}
            ]
        }
        result = DetectionResult.from_response(response)
        assert result.safe is False
        assert result.risk_level == RiskLevel.HIGH

    def test_from_response_critical_risk_detection(self):
        """Should mark unsafe for critical risk detection."""
        response = {
            "detections": [
                {"type": "critical", "risk_level": "critical_risk"}
            ]
        }
        result = DetectionResult.from_response(response)
        assert result.safe is False
        assert result.risk_level == RiskLevel.CRITICAL

    def test_from_response_mixed_risk_levels(self):
        """Should use highest risk level from multiple detections."""
        response = {
            "detections": [
                {"type": "low", "risk_level": "low_risk"},
                {"type": "high", "risk_level": "high_risk"},
                {"type": "medium", "risk_level": "medium_risk"},
            ]
        }
        result = DetectionResult.from_response(response)
        assert result.safe is False
        assert result.risk_level == RiskLevel.HIGH

    def test_from_response_missing_detections_key(self):
        """Should handle missing detections key."""
        response = {}
        result = DetectionResult.from_response(response)
        assert result.safe is True
        assert result.detections == []

    def test_from_response_none_detections(self):
        """Should handle None detections value."""
        response = {"detections": None}
        result = DetectionResult.from_response(response)
        assert result.safe is True
        assert result.detections == []

    def test_from_response_invalid_response_type(self):
        """Should raise ValueError for non-dict response."""
        with pytest.raises(ValueError, match="response must be a dict"):
            DetectionResult.from_response("not a dict")

    def test_from_response_invalid_detections_type(self):
        """Should raise ValueError for non-list detections."""
        with pytest.raises(ValueError, match="detections must be a list"):
            DetectionResult.from_response({"detections": "not a list"})

    def test_from_response_invalid_detection_item_type(self):
        """Should raise ValueError for non-dict detection item."""
        with pytest.raises(ValueError, match="detection at index 0 must be a dict"):
            DetectionResult.from_response({"detections": ["not a dict"]})

    def test_from_response_preserves_raw_response(self):
        """Should preserve the raw response."""
        response = {"detections": [], "extra": "data"}
        result = DetectionResult.from_response(response)
        assert result.raw_response == response


class TestOpenGuardrailsValidatorInit:
    """Test OpenGuardrailsValidator initialization."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_default_initialization(self):
        """Should initialize with default values."""
        validator = OpenGuardrailsValidator()
        assert validator.api_url == "http://localhost:5001"
        assert validator.api_key is None
        assert validator.timeout == 30
        assert validator.default_scanners == []
        assert validator.fail_safe is False

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_custom_initialization(self):
        """Should initialize with custom values."""
        validator = OpenGuardrailsValidator(
            api_url="http://custom:8080/",
            api_key="test-key",
            timeout=60,
            default_scanners=["S1", "S2"],
            fail_safe=True,
        )
        assert validator.api_url == "http://custom:8080"  # Trailing slash removed
        assert validator.api_key == "test-key"
        assert validator.timeout == 60
        assert validator.default_scanners == ["S1", "S2"]
        assert validator.fail_safe is True


class TestOpenGuardrailsValidatorValidation:
    """Test OpenGuardrailsValidator input validation."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_validate_none_content(self):
        """Should raise ValueError for None content."""
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="content cannot be None"):
            validator.validate(None)

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_validate_empty_content(self):
        """Should raise ValueError for empty content."""
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="content cannot be empty"):
            validator.validate("")

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_validate_whitespace_content(self):
        """Should raise ValueError for whitespace-only content."""
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="content cannot be empty"):
            validator.validate("   \n\t  ")

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_validate_non_string_content(self):
        """Should raise ValueError for non-string content."""
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="content must be a string"):
            validator.validate(12345)

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_validate_invalid_scanners_type(self):
        """Should raise ValueError for non-list scanners."""
        validator = OpenGuardrailsValidator()
        with pytest.raises(ValueError, match="scanners must be a list"):
            validator.validate("test content", scanners="S1")


class TestOpenGuardrailsValidatorErrorHandling:
    """Test OpenGuardrailsValidator error handling."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_api_error_fail_closed(self, mock_requests):
        """Should return safe=False on API error when fail_safe=False."""
        mock_requests.RequestException = Exception
        mock_requests.post.side_effect = Exception("Connection error")

        validator = OpenGuardrailsValidator(fail_safe=False)
        result = validator.validate("test content")

        assert result.safe is False
        assert result.risk_level == RiskLevel.HIGH
        assert "api_error" in str(result.detections)

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_api_error_fail_open(self, mock_requests):
        """Should return safe=True on API error when fail_safe=True."""
        mock_requests.RequestException = Exception
        mock_requests.post.side_effect = Exception("Connection error")

        validator = OpenGuardrailsValidator(fail_safe=True)
        result = validator.validate("test content")

        assert result.safe is True
        assert result.risk_level == RiskLevel.LOW

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_json_decode_error_handling(self, mock_requests):
        """Should handle JSONDecodeError gracefully."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.side_effect = JSONDecodeError("Error", "", 0)
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        validator = OpenGuardrailsValidator(fail_safe=False)
        result = validator.validate("test content")

        assert result.safe is False
        # Error type is in detections, not raw_response
        assert any(d.get("type") == "json_decode_error" for d in result.detections)

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_invalid_response_structure(self, mock_requests):
        """Should handle non-dict response gracefully."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = ["not", "a", "dict"]
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        validator = OpenGuardrailsValidator(fail_safe=False)
        result = validator.validate("test content")

        assert result.safe is False
        # Error type is in detections, not raw_response
        assert any(d.get("type") == "invalid_response_structure" for d in result.detections)


class TestOpenGuardrailsValidatorHeaders:
    """Test OpenGuardrailsValidator header generation."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_headers_without_api_key(self):
        """Should generate headers without Authorization."""
        validator = OpenGuardrailsValidator()
        headers = validator._headers()
        assert headers == {"Content-Type": "application/json"}

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_headers_with_api_key(self):
        """Should include Authorization header."""
        validator = OpenGuardrailsValidator(api_key="test-key")
        headers = validator._headers()
        assert headers["Authorization"] == "Bearer test-key"


class TestSentinelOpenGuardrailsScannerInit:
    """Test SentinelOpenGuardrailsScanner initialization."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_default_initialization(self):
        """Should initialize with default values."""
        scanner = SentinelOpenGuardrailsScanner()
        assert scanner.api_url == "http://localhost:5000"
        assert scanner.jwt_token is None
        assert scanner.risk_level == RiskLevel.HIGH
        assert scanner.scan_prompt is True
        assert scanner.scan_response is True
        assert scanner.timeout == 30
        assert scanner._scanner_tag is None

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_custom_initialization(self):
        """Should initialize with custom values."""
        scanner = SentinelOpenGuardrailsScanner(
            openguardrails_url="http://custom:9000/",
            jwt_token="jwt-token",
            risk_level=RiskLevel.CRITICAL,
            scan_prompt=False,
            scan_response=False,
            timeout=60,
        )
        assert scanner.api_url == "http://custom:9000"
        assert scanner.jwt_token == "jwt-token"
        assert scanner.risk_level == RiskLevel.CRITICAL
        assert scanner.scan_prompt is False
        assert scanner.scan_response is False
        assert scanner.timeout == 60

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_scanner_definition_present(self):
        """Scanner should have a definition."""
        scanner = SentinelOpenGuardrailsScanner()
        assert "THSP Protocol" in scanner.SCANNER_DEFINITION
        assert "TRUTH" in scanner.SCANNER_DEFINITION
        assert "HARM" in scanner.SCANNER_DEFINITION
        assert "SCOPE" in scanner.SCANNER_DEFINITION
        assert "PURPOSE" in scanner.SCANNER_DEFINITION


class TestSentinelOpenGuardrailsScannerRegister:
    """Test SentinelOpenGuardrailsScanner register/unregister."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_register_success(self, mock_requests):
        """Should register and return tag."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"tag": "S100"}
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        scanner = SentinelOpenGuardrailsScanner()
        tag = scanner.register()

        assert tag == "S100"
        assert scanner.scanner_tag == "S100"

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_register_empty_tag_raises(self, mock_requests):
        """Should raise RuntimeError if tag is empty."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"tag": None}
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        scanner = SentinelOpenGuardrailsScanner()
        with pytest.raises(RuntimeError, match="empty tag"):
            scanner.register()

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_register_api_error_raises(self, mock_requests):
        """Should raise RuntimeError on API error."""
        mock_requests.RequestException = Exception
        mock_requests.post.side_effect = Exception("API error")

        scanner = SentinelOpenGuardrailsScanner()
        with pytest.raises(RuntimeError, match="Failed to register"):
            scanner.register()

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_unregister_without_registration(self):
        """Should return False if not registered."""
        scanner = SentinelOpenGuardrailsScanner()
        result = scanner.unregister()
        assert result is False

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_unregister_success(self, mock_requests):
        """Should unregister successfully."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_requests.delete.return_value = mock_response
        mock_requests.RequestException = Exception

        scanner = SentinelOpenGuardrailsScanner()
        scanner._scanner_tag = "S100"

        result = scanner.unregister()
        assert result is True
        assert scanner.scanner_tag is None


class TestSentinelGuardrailsWrapperInit:
    """Test SentinelGuardrailsWrapper initialization."""

    def test_default_initialization(self):
        """Should initialize with defaults."""
        wrapper = SentinelGuardrailsWrapper()
        assert wrapper.require_both is False

    def test_custom_initialization(self):
        """Should accept custom validators."""
        mock_sentinel = Mock()
        mock_og = Mock(spec=OpenGuardrailsValidator)

        wrapper = SentinelGuardrailsWrapper(
            sentinel=mock_sentinel,
            openguardrails=mock_og,
            require_both=True,
        )

        assert wrapper.sentinel == mock_sentinel
        assert wrapper.openguardrails == mock_og
        assert wrapper.require_both is True


class TestSentinelGuardrailsWrapperValidation:
    """Test SentinelGuardrailsWrapper validation."""

    def test_validate_none_content(self):
        """Should raise ValueError for None content."""
        wrapper = SentinelGuardrailsWrapper()
        with pytest.raises(ValueError, match="content cannot be None"):
            wrapper.validate(None)

    def test_validate_empty_content(self):
        """Should raise ValueError for empty content."""
        wrapper = SentinelGuardrailsWrapper()
        with pytest.raises(ValueError, match="content cannot be empty"):
            wrapper.validate("")

    def test_validate_whitespace_content(self):
        """Should raise ValueError for whitespace content."""
        wrapper = SentinelGuardrailsWrapper()
        with pytest.raises(ValueError, match="content cannot be empty"):
            wrapper.validate("   \n  ")

    def test_validate_non_string_content(self):
        """Should raise ValueError for non-string content."""
        wrapper = SentinelGuardrailsWrapper()
        with pytest.raises(ValueError, match="content must be a string"):
            wrapper.validate(123)


class TestSentinelGuardrailsWrapperResults:
    """Test SentinelGuardrailsWrapper result handling."""

    def test_validate_with_sentinel_only(self):
        """Should work with only Sentinel (LayeredValidator)."""
        from sentinelseed.validation import ValidationResult, ValidationLayer, RiskLevel as ValRiskLevel

        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=True,
            layer=ValidationLayer.HEURISTIC,
            violations=[],
            risk_level=ValRiskLevel.LOW,
        )

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is True
        assert result["blocked_by"] == []
        assert result["sentinel_result"]["is_safe"] is True
        assert result["openguardrails_result"] is None

    def test_validate_sentinel_blocks(self):
        """Should block when LayeredValidator returns unsafe."""
        from sentinelseed.validation import ValidationResult, ValidationLayer, RiskLevel as ValRiskLevel

        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            layer=ValidationLayer.HEURISTIC,
            violations=["Unsafe content detected"],
            risk_level=ValRiskLevel.HIGH,
        )

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is False
        assert "sentinel" in result["blocked_by"]

    def test_validate_sentinel_blocks_with_violations(self):
        """Should include violations in result when blocked."""
        from sentinelseed.validation import ValidationResult, ValidationLayer, RiskLevel as ValRiskLevel

        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            layer=ValidationLayer.HEURISTIC,
            violations=["Harmful content"],
            risk_level=ValRiskLevel.HIGH,
        )

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        assert result["safe"] is False
        assert result["sentinel_result"]["violations"] == ["Harmful content"]

    def test_validate_sentinel_exception_handled(self):
        """Should handle LayeredValidator exceptions with fail-closed behavior."""
        mock_validator = Mock()
        mock_validator.validate.side_effect = Exception("Validation error")

        wrapper = SentinelGuardrailsWrapper(validator=mock_validator)
        result = wrapper.validate("test content")

        # Fail-closed: exception should block (safe=False) for security
        assert result["safe"] is False
        assert "sentinel_error" in result["blocked_by"]
        assert result["sentinel_result"] is None

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_validate_with_openguardrails(self):
        """Should work with OpenGuardrails validator."""
        mock_og = Mock(spec=OpenGuardrailsValidator)
        mock_og.validate.return_value = DetectionResult(
            safe=True,
            risk_level=RiskLevel.LOW,
            detections=[],
            raw_response={},
        )

        wrapper = SentinelGuardrailsWrapper(openguardrails=mock_og)
        result = wrapper.validate("test content")

        assert result["safe"] is True
        assert result["openguardrails_result"]["safe"] is True

    def test_validate_require_both_permissive_mode(self):
        """With require_both=True (permissive mode), only block if BOTH validators fail."""
        from sentinelseed.validation import ValidationResult, ValidationLayer, RiskLevel as ValRiskLevel

        # Sentinel validator fails
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            layer=ValidationLayer.HEURISTIC,
            violations=["Blocked content"],
            risk_level=ValRiskLevel.HIGH,
        )

        # OpenGuardrails validator passes
        mock_og = Mock()
        mock_og.validate.return_value = DetectionResult(
            safe=True,
            risk_level=RiskLevel.LOW,
            detections=[],
        )

        wrapper = SentinelGuardrailsWrapper(
            validator=mock_validator,
            openguardrails=mock_og,
            require_both=True,
        )
        result = wrapper.validate("test content")

        # require_both=True (permissive): only block if BOTH fail
        # Here only sentinel fails, so should be allowed
        assert result["safe"] is True
        assert "sentinel" in result["blocked_by"]  # sentinel failed but didn't block overall

    def test_validate_require_both_blocks_when_both_fail(self):
        """With require_both=True, block when BOTH validators fail."""
        from sentinelseed.validation import ValidationResult, ValidationLayer, RiskLevel as ValRiskLevel

        # Sentinel validator fails
        mock_validator = Mock()
        mock_validator.validate.return_value = ValidationResult(
            is_safe=False,
            layer=ValidationLayer.HEURISTIC,
            violations=["Blocked content"],
            risk_level=ValRiskLevel.HIGH,
        )

        # OpenGuardrails validator also fails
        mock_og = Mock()
        mock_og.validate.return_value = DetectionResult(
            safe=False,
            risk_level=RiskLevel.HIGH,
            detections=["Detected threat"],
        )

        wrapper = SentinelGuardrailsWrapper(
            validator=mock_validator,
            openguardrails=mock_og,
            require_both=True,
        )
        result = wrapper.validate("test content")

        # require_both=True: BOTH failed, so should block
        assert result["safe"] is False
        assert "sentinel" in result["blocked_by"]
        assert "openguardrails" in result["blocked_by"]


class TestConvenienceFunctions:
    """Test convenience functions."""

    def test_register_sentinel_scanner_invalid_risk_level(self):
        """Should raise ValueError for invalid risk_level."""
        with pytest.raises(ValueError, match="Invalid risk_level"):
            register_sentinel_scanner(risk_level="invalid_level")

    def test_register_sentinel_scanner_valid_risk_levels(self):
        """Should accept all valid risk levels."""
        valid_levels = ["low_risk", "medium_risk", "high_risk", "critical_risk"]
        for level in valid_levels:
            # Just verify no ValueError is raised during validation
            # Actual API call will fail, which is expected
            try:
                register_sentinel_scanner(risk_level=level)
            except RuntimeError:
                pass  # Expected - API not available

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    def test_create_combined_validator(self):
        """Should create combined validator wrapper."""
        wrapper = create_combined_validator(
            openguardrails_url="http://test:5001",
            openguardrails_key="test-key",
            fail_safe=True,
        )

        assert isinstance(wrapper, SentinelGuardrailsWrapper)
        assert wrapper.openguardrails is not None
        assert wrapper.openguardrails.api_url == "http://test:5001"
        assert wrapper.openguardrails.fail_safe is True


class TestValidatePromptAndResponse:
    """Test validate_prompt and validate_response convenience methods."""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_validate_prompt(self, mock_requests):
        """validate_prompt should call validate."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"detections": []}
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        validator = OpenGuardrailsValidator()
        result = validator.validate_prompt("test prompt")

        assert result.safe is True
        mock_requests.post.assert_called_once()

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not installed")
    @patch("sentinelseed.integrations.openguardrails.requests")
    def test_validate_response_with_context(self, mock_requests):
        """validate_response should include prompt as context."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_response.json.return_value = {"detections": []}
        mock_requests.post.return_value = mock_response
        mock_requests.RequestException = Exception

        validator = OpenGuardrailsValidator()
        result = validator.validate_response(
            response="test response",
            prompt="original prompt"
        )

        assert result.safe is True
        # Verify context was passed
        call_args = mock_requests.post.call_args
        payload = call_args[1]["json"]
        assert payload["context"] == "original prompt"
