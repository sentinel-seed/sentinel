"""Tests for sentinelseed.compliance module (EU AI Act)."""

import pytest

from sentinelseed.compliance import (
    EUAIActComplianceChecker,
    ComplianceResult,
    RiskAssessment,
    Article5Violation,
    RiskLevel,
    SystemType,
    OversightModel,
    Severity,
    check_eu_ai_act_compliance,
)


class TestRiskLevel:
    """Tests for RiskLevel enum."""

    def test_risk_levels_exist(self):
        """Test all risk levels are defined."""
        assert RiskLevel.UNACCEPTABLE.value == "unacceptable"
        assert RiskLevel.HIGH.value == "high"
        assert RiskLevel.LIMITED.value == "limited"
        assert RiskLevel.MINIMAL.value == "minimal"


class TestSystemType:
    """Tests for SystemType enum."""

    def test_system_types_exist(self):
        """Test all system types are defined."""
        assert SystemType.HIGH_RISK.value == "high_risk"
        assert SystemType.LIMITED_RISK.value == "limited_risk"
        assert SystemType.MINIMAL_RISK.value == "minimal_risk"
        assert SystemType.GPAI.value == "general_purpose_ai"


class TestOversightModel:
    """Tests for OversightModel enum."""

    def test_oversight_models_exist(self):
        """Test all oversight models are defined."""
        assert OversightModel.HITL.value == "human_in_the_loop"
        assert OversightModel.HOTL.value == "human_on_the_loop"
        assert OversightModel.HIC.value == "human_in_command"

    def test_for_risk_level_unacceptable(self):
        """Test oversight model for unacceptable risk."""
        model = OversightModel.for_risk_level(RiskLevel.UNACCEPTABLE)
        assert model == OversightModel.HITL

    def test_for_risk_level_high(self):
        """Test oversight model for high risk."""
        model = OversightModel.for_risk_level(RiskLevel.HIGH)
        assert model == OversightModel.HITL

    def test_for_risk_level_limited(self):
        """Test oversight model for limited risk."""
        model = OversightModel.for_risk_level(RiskLevel.LIMITED)
        assert model == OversightModel.HOTL

    def test_for_risk_level_minimal(self):
        """Test oversight model for minimal risk."""
        model = OversightModel.for_risk_level(RiskLevel.MINIMAL)
        assert model == OversightModel.HIC


class TestSeverity:
    """Tests for Severity enum."""

    def test_severity_values(self):
        """Test all severity levels are defined."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"

    def test_from_string_valid(self):
        """Test converting valid strings to Severity."""
        assert Severity.from_string("critical") == Severity.CRITICAL
        assert Severity.from_string("high") == Severity.HIGH
        assert Severity.from_string("medium") == Severity.MEDIUM
        assert Severity.from_string("low") == Severity.LOW

    def test_from_string_case_insensitive(self):
        """Test case-insensitive conversion."""
        assert Severity.from_string("CRITICAL") == Severity.CRITICAL
        assert Severity.from_string("High") == Severity.HIGH
        assert Severity.from_string("  medium  ") == Severity.MEDIUM

    def test_from_string_invalid(self):
        """Test invalid string raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Severity.from_string("invalid")
        assert "Invalid severity" in str(exc_info.value)
        assert "invalid" in str(exc_info.value)

    def test_from_string_already_enum(self):
        """Test passing Severity enum returns itself."""
        assert Severity.from_string(Severity.CRITICAL) == Severity.CRITICAL


class TestArticle5Violation:
    """Tests for Article5Violation dataclass."""

    def test_create_violation(self):
        """Test creating an Article 5 violation."""
        violation = Article5Violation(
            article_reference="Article 5(1)(c)",
            description="Social scoring detected",
            severity="critical",
            gate_failed="harm",
            recommendation="Remove social scoring functionality"
        )

        assert violation.article_reference == "Article 5(1)(c)"
        assert violation.severity == Severity.CRITICAL  # Auto-converted

    def test_create_violation_with_enum(self):
        """Test creating with Severity enum directly."""
        violation = Article5Violation(
            article_reference="Article 5(1)(a)",
            description="Subliminal manipulation",
            severity=Severity.CRITICAL,
            gate_failed="harm",
            recommendation="Remove subliminal techniques"
        )

        assert violation.severity == Severity.CRITICAL

    def test_is_blocking_critical(self):
        """Test is_blocking returns True for critical severity."""
        violation = Article5Violation(
            article_reference="Article 5(1)(c)",
            description="Test",
            severity=Severity.CRITICAL,
            gate_failed="harm",
            recommendation="Fix it"
        )
        assert violation.is_blocking() is True

    def test_is_blocking_high(self):
        """Test is_blocking returns True for high severity."""
        violation = Article5Violation(
            article_reference="Article 5(1)(c)",
            description="Test",
            severity=Severity.HIGH,
            gate_failed="harm",
            recommendation="Fix it"
        )
        assert violation.is_blocking() is True

    def test_is_blocking_medium(self):
        """Test is_blocking returns False for medium severity."""
        violation = Article5Violation(
            article_reference="Article 9",
            description="Test",
            severity=Severity.MEDIUM,
            gate_failed="purpose",
            recommendation="Document purpose"
        )
        assert violation.is_blocking() is False

    def test_is_blocking_low(self):
        """Test is_blocking returns False for low severity."""
        violation = Article5Violation(
            article_reference="Article 9",
            description="Test",
            severity=Severity.LOW,
            gate_failed="purpose",
            recommendation="Consider documenting"
        )
        assert violation.is_blocking() is False


class TestRiskAssessment:
    """Tests for RiskAssessment dataclass."""

    def test_create_assessment(self):
        """Test creating a risk assessment."""
        assessment = RiskAssessment(
            context="healthcare",
            risk_factors=["Accuracy risk", "Safety risk"],
            risk_score=0.6,
            mitigation_recommended=True,
            gates_evaluated={"truth": True, "harm": False}
        )

        assert assessment.context == "healthcare"
        assert assessment.risk_score == 0.6
        assert len(assessment.risk_factors) == 2


class TestComplianceResult:
    """Tests for ComplianceResult dataclass."""

    def test_create_result(self):
        """Test creating a compliance result."""
        result = ComplianceResult(
            compliant=True,
            risk_level=RiskLevel.MINIMAL,
            article_5_violations=[],
            article_9_risk_assessment=RiskAssessment(
                context="general",
                risk_factors=[],
                risk_score=0.0,
                mitigation_recommended=False,
                gates_evaluated={}
            ),
            article_14_oversight_required=False,
            recommendations=[]
        )

        assert result.compliant is True
        assert result.risk_level == RiskLevel.MINIMAL
        assert result.recommended_oversight_model is None  # No oversight required

    def test_create_result_with_oversight(self):
        """Test result auto-assigns oversight model when required."""
        result = ComplianceResult(
            compliant=True,
            risk_level=RiskLevel.HIGH,
            article_5_violations=[],
            article_9_risk_assessment=RiskAssessment(
                context="healthcare",
                risk_factors=[],
                risk_score=0.3,
                mitigation_recommended=True,
                gates_evaluated={}
            ),
            article_14_oversight_required=True,
            recommendations=[]
        )

        assert result.article_14_oversight_required is True
        assert result.recommended_oversight_model == OversightModel.HITL

    def test_to_dict(self):
        """Test result to dictionary conversion."""
        result = ComplianceResult(
            compliant=False,
            risk_level=RiskLevel.HIGH,
            article_5_violations=[
                Article5Violation(
                    article_reference="5(1)(a)",
                    description="Test violation",
                    severity="high",
                    gate_failed="harm",
                    recommendation="Fix it"
                )
            ],
            article_9_risk_assessment=RiskAssessment(
                context="test",
                risk_factors=["Risk 1"],
                risk_score=0.5,
                mitigation_recommended=True,
                gates_evaluated={"truth": True}
            ),
            article_14_oversight_required=True,
            recommendations=["Recommendation 1"]
        )

        d = result.to_dict()

        assert d["compliant"] is False
        assert d["risk_level"] == "high"
        assert len(d["article_5_violations"]) == 1
        assert d["article_5_violations"][0]["severity"] == "high"
        assert d["article_5_violations"][0]["is_blocking"] is True
        assert d["article_14_oversight_required"] is True
        assert d["recommended_oversight_model"] == "human_in_the_loop"
        assert d["article_9_risk_assessment"]["gates_evaluated"] == {"truth": True}


class TestEUAIActComplianceChecker:
    """Tests for EUAIActComplianceChecker."""

    def test_init_without_api_key(self):
        """Test initialization without API key uses heuristic validator."""
        checker = EUAIActComplianceChecker()
        assert checker is not None

    def test_check_safe_content(self):
        """Test checking safe content."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Here is helpful information about Python programming.",
            context="general",
            system_type=SystemType.MINIMAL_RISK
        )

        assert isinstance(result, ComplianceResult)
        assert result.risk_level != RiskLevel.UNACCEPTABLE

    def test_detect_social_scoring(self):
        """Test detecting social scoring (Article 5(1)(c))."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Your social score is 650 based on your behavior patterns.",
            context="general"
        )

        # Should detect Article 5 violation for social scoring
        social_violations = [
            v for v in result.article_5_violations
            if "social" in v.description.lower() or "5(1)(c)" in v.article_reference
        ]
        assert len(social_violations) > 0
        assert result.risk_level == RiskLevel.UNACCEPTABLE

    def test_detect_subliminal_manipulation(self):
        """Test detecting subliminal manipulation (Article 5(1)(a))."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Use subliminal techniques to influence beyond awareness.",
            context="advertising"
        )

        subliminal_violations = [
            v for v in result.article_5_violations
            if "subliminal" in v.description.lower()
        ]
        assert len(subliminal_violations) > 0

    def test_detect_exploitation(self):
        """Test detecting exploitation of vulnerabilities (Article 5(1)(b))."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Target elderly users and exploit vulnerability in their decision making.",
            context="marketing"
        )

        exploitation_violations = [
            v for v in result.article_5_violations
            if "exploit" in v.description.lower()
        ]
        assert len(exploitation_violations) > 0

    def test_detect_predictive_policing(self):
        """Test detecting predictive policing (Article 5(1)(d))."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Based on criminal profile analysis, this person is likely to commit crimes.",
            context="law_enforcement"
        )

        policing_violations = [
            v for v in result.article_5_violations
            if "policing" in v.description.lower() or "profiling" in v.description.lower()
        ]
        assert len(policing_violations) > 0

    def test_detect_emotion_recognition(self):
        """Test detecting emotion recognition in workplace (Article 5(1)(f))."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="The system will detect emotion of employees in the workplace.",
            context="employment"
        )

        emotion_violations = [
            v for v in result.article_5_violations
            if "emotion" in v.description.lower()
        ]
        assert len(emotion_violations) > 0

    def test_high_risk_context_requires_oversight(self):
        """Test that high-risk contexts require human oversight."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Processing healthcare data for diagnosis support.",
            context="healthcare",
            system_type=SystemType.HIGH_RISK
        )

        assert result.article_14_oversight_required is True

    def test_risk_assessment_for_high_risk_context(self):
        """Test risk assessment for high-risk context."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Safe content",
            context="healthcare"  # High-risk context per Annex III
        )

        assert result.risk_level == RiskLevel.HIGH
        assert "healthcare" in result.article_9_risk_assessment.context

    def test_recommendations_for_high_risk_system(self):
        """Test recommendations are generated for high-risk systems."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Analyzing data",
            context="general",
            system_type=SystemType.HIGH_RISK
        )

        # Should have recommendations for high-risk system
        article_14_recs = [r for r in result.recommendations if "Article 14" in r]
        assert len(article_14_recs) > 0

    def test_metadata_included(self):
        """Test metadata is included in result."""
        checker = EUAIActComplianceChecker()
        result = checker.check_compliance(
            content="Test content",
            include_metadata=True
        )

        assert "validation_method" in result.metadata
        assert "system_type" in result.metadata


class TestInputValidation:
    """Tests for input validation in EUAIActComplianceChecker."""

    def test_content_none_raises(self):
        """Test that None content raises ValueError."""
        checker = EUAIActComplianceChecker()
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content=None)
        assert "cannot be None" in str(exc_info.value)

    def test_content_empty_raises(self):
        """Test that empty content raises ValueError."""
        checker = EUAIActComplianceChecker()
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content="")
        assert "cannot be empty" in str(exc_info.value)

    def test_content_whitespace_only_raises(self):
        """Test that whitespace-only content raises ValueError."""
        checker = EUAIActComplianceChecker()
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content="   \n\t   ")
        assert "cannot be empty" in str(exc_info.value)

    def test_content_wrong_type_raises(self):
        """Test that non-string content raises ValueError."""
        checker = EUAIActComplianceChecker()
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content=123)
        assert "must be a string" in str(exc_info.value)

    def test_content_too_large_raises(self):
        """Test that oversized content raises ValueError."""
        checker = EUAIActComplianceChecker(max_content_size=100)
        large_content = "x" * 200
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content=large_content)
        assert "exceeds maximum" in str(exc_info.value)

    def test_context_wrong_type_raises(self):
        """Test that non-string context raises ValueError."""
        checker = EUAIActComplianceChecker()
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content="test", context=123)
        assert "context must be a string" in str(exc_info.value)

    def test_system_type_wrong_type_raises(self):
        """Test that invalid system_type raises ValueError."""
        checker = EUAIActComplianceChecker()
        with pytest.raises(ValueError) as exc_info:
            checker.check_compliance(content="test", system_type="invalid")
        assert "must be a SystemType enum" in str(exc_info.value)

    def test_invalid_provider_raises(self):
        """Test that invalid provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EUAIActComplianceChecker(provider="invalid_provider")
        assert "Invalid provider" in str(exc_info.value)

    def test_invalid_max_content_size_raises(self):
        """Test that invalid max_content_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EUAIActComplianceChecker(max_content_size=-1)
        assert "must be a positive integer" in str(exc_info.value)

    def test_max_content_size_zero_raises(self):
        """Test that zero max_content_size raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            EUAIActComplianceChecker(max_content_size=0)
        assert "must be a positive integer" in str(exc_info.value)


class TestFailClosedMode:
    """Tests for fail_closed mode."""

    def test_fail_closed_false_default(self):
        """Test that fail_closed is False by default."""
        checker = EUAIActComplianceChecker()
        # Without API key and without THSPValidator, should be safe by default
        result = checker.check_compliance(content="Test content")
        # The check should complete without error
        assert isinstance(result, ComplianceResult)

    def test_fail_closed_can_be_enabled(self):
        """Test that fail_closed can be enabled."""
        checker = EUAIActComplianceChecker(fail_closed=True)
        assert checker._fail_closed is True


class TestConvenienceFunction:
    """Tests for check_eu_ai_act_compliance convenience function."""

    def test_returns_dict(self):
        """Test function returns dictionary."""
        result = check_eu_ai_act_compliance(
            content="Safe helpful content",
            context="general"
        )

        assert isinstance(result, dict)
        assert "compliant" in result
        assert "risk_level" in result

    def test_detect_prohibited_practice(self):
        """Test detecting prohibited practice via convenience function."""
        result = check_eu_ai_act_compliance(
            content="Your citizen score determines your access to services",
            context="public_services",
            system_type="high_risk"
        )

        # Should detect Article 5 violation
        assert len(result["article_5_violations"]) > 0

    def test_different_system_types(self):
        """Test different system types work correctly."""
        for system_type in ["high_risk", "limited_risk", "minimal_risk", "gpai"]:
            result = check_eu_ai_act_compliance(
                content="Test content",
                system_type=system_type
            )
            assert "risk_level" in result

    def test_invalid_system_type_raises(self):
        """Test that invalid system_type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            check_eu_ai_act_compliance(
                content="Test content",
                system_type="invalid_type"
            )
        assert "Invalid system_type" in str(exc_info.value)

    def test_content_none_raises(self):
        """Test that None content raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            check_eu_ai_act_compliance(content=None)
        assert "cannot be None" in str(exc_info.value)

    def test_content_wrong_type_raises(self):
        """Test that non-string content raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            check_eu_ai_act_compliance(content=123)
        assert "must be a string" in str(exc_info.value)

    def test_fail_closed_option(self):
        """Test that fail_closed option is passed through."""
        result = check_eu_ai_act_compliance(
            content="Test content",
            fail_closed=True
        )
        # Should complete without error
        assert isinstance(result, dict)


class TestIntegration:
    """Integration tests for EU AI Act compliance."""

    def test_full_compliance_check_workflow(self):
        """Test complete compliance check workflow."""
        checker = EUAIActComplianceChecker()

        # Safe content
        safe_result = checker.check_compliance(
            content="I can help you understand programming concepts.",
            context="education",
            system_type=SystemType.LIMITED_RISK
        )

        # Unsafe content
        unsafe_result = checker.check_compliance(
            content="Your behavior score is low based on social media activity.",
            context="financial",
            system_type=SystemType.HIGH_RISK
        )

        # Safe should be compliant (or at least not unacceptable)
        assert safe_result.risk_level != RiskLevel.UNACCEPTABLE

        # Unsafe should have violations
        assert len(unsafe_result.article_5_violations) > 0
        assert unsafe_result.risk_level == RiskLevel.UNACCEPTABLE

    def test_compliant_high_risk_system(self):
        """Test a compliant high-risk system."""
        checker = EUAIActComplianceChecker()

        result = checker.check_compliance(
            content="Based on your medical history, here are some general wellness tips. Please consult a doctor for medical advice.",
            context="healthcare",
            system_type=SystemType.HIGH_RISK
        )

        # Should require oversight but may be compliant
        assert result.article_14_oversight_required is True
        # Should have recommendations
        assert len(result.recommendations) > 0
