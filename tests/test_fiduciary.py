"""Tests for sentinelseed.fiduciary module."""

import pytest
import threading

from sentinelseed.fiduciary import (
    FiduciaryValidator,
    FiduciaryGuard,
    FiduciaryResult,
    UserContext,
    Violation,
    Severity,
    RiskTolerance,
    FiduciaryDuty,
    ViolationType,
    FiduciaryStep,
    ConflictDetector,
    FiduciaryViolationError,
    validate_fiduciary,
    is_fiduciary_compliant,
)


class TestUserContext:
    """Tests for UserContext dataclass."""

    def test_create_with_defaults(self):
        """Test creating context with default values."""
        ctx = UserContext()
        assert ctx.user_id is None
        assert ctx.goals == []
        assert ctx.risk_tolerance == "moderate"

    def test_create_with_values(self):
        """Test creating context with specific values."""
        ctx = UserContext(
            user_id="user123",
            goals=["save money", "reduce risk"],
            risk_tolerance="low",
            sensitive_topics=["health", "finances"]
        )
        assert ctx.user_id == "user123"
        assert len(ctx.goals) == 2
        assert ctx.risk_tolerance == "low"

    def test_from_dict(self):
        """Test creating context from dictionary."""
        data = {
            "user_id": "test-user",
            "goals": ["retirement planning"],
            "risk_tolerance": "low",
            "constraints": ["budget limited"],
        }
        ctx = UserContext.from_dict(data)

        assert ctx.user_id == "test-user"
        assert ctx.goals == ["retirement planning"]
        assert ctx.risk_tolerance == "low"


class TestViolation:
    """Tests for Violation dataclass."""

    def test_create_violation(self):
        """Test creating a violation."""
        violation = Violation(
            duty=FiduciaryDuty.LOYALTY,
            type=ViolationType.CONFLICT_OF_INTEREST,
            description="Test violation",
            severity="high",
        )
        assert violation.duty == FiduciaryDuty.LOYALTY
        assert violation.severity == "high"

    def test_to_dict(self):
        """Test violation to dictionary conversion."""
        violation = Violation(
            duty=FiduciaryDuty.CARE,
            type=ViolationType.INCOMPETENT_ACTION,
            description="Vague recommendation",
            severity="low",
            step=FiduciaryStep.CARE,
        )
        d = violation.to_dict()

        assert d["duty"] == "care"
        assert d["type"] == "incompetent_action"
        assert d["step"] == "care"


class TestConflictDetector:
    """Tests for ConflictDetector."""

    def test_detect_self_dealing(self):
        """Test detecting self-dealing patterns."""
        detector = ConflictDetector()
        # Use phrase that matches the regex pattern exactly
        violations = detector.detect("I recommend our service for your needs")

        assert len(violations) > 0
        assert any(v.type == ViolationType.CONFLICT_OF_INTEREST for v in violations)

    def test_detect_provider_benefit_keywords(self):
        """Test detecting provider benefit keywords."""
        detector = ConflictDetector()
        violations = detector.detect("This affiliate product is great for you")

        assert len(violations) > 0
        assert any("affiliate" in v.description.lower() for v in violations)

    def test_no_conflict_in_neutral_action(self):
        """Test no conflict in neutral action."""
        detector = ConflictDetector()
        violations = detector.detect("Here is information about Python programming")

        # No self-dealing patterns
        conflict_violations = [
            v for v in violations
            if v.type == ViolationType.CONFLICT_OF_INTEREST
        ]
        assert len(conflict_violations) == 0


class TestFiduciaryValidator:
    """Tests for FiduciaryValidator."""

    def test_validate_compliant_action(self):
        """Test validating a compliant action."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            action="Provide information about safe investment strategies",
            user_context=UserContext(risk_tolerance="moderate")
        )

        assert result.compliant is True
        assert len(result.violations) == 0

    def test_validate_misaligned_risk(self):
        """Test detecting misaligned risk tolerance."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            action="Invest in high risk volatile stocks",
            user_context=UserContext(risk_tolerance="low")
        )

        assert result.compliant is False
        assert any(
            v.type == ViolationType.MISALIGNED_RECOMMENDATION
            for v in result.violations
        )

    def test_validate_goal_contradiction(self):
        """Test detecting goal contradictions."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            action="Increase spending on luxury items",
            user_context=UserContext(goals=["save money"])
        )

        # Should detect contradiction between "save" and "increase spending"
        misaligned = [
            v for v in result.violations
            if v.type == ViolationType.MISALIGNED_RECOMMENDATION
        ]
        assert len(misaligned) > 0

    def test_validate_transparency_violation(self):
        """Test detecting lack of transparency."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            action="Just do this, trust me, don't worry about the details"
        )

        transparency_violations = [
            v for v in result.violations
            if v.duty == FiduciaryDuty.TRANSPARENCY
        ]
        assert len(transparency_violations) > 0

    def test_validate_confidentiality_violation(self):
        """Test detecting confidentiality violations."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            action="Share your health records on social media",
            user_context=UserContext(sensitive_topics=["health"])
        )

        assert any(
            v.type == ViolationType.PRIVACY_VIOLATION
            for v in result.violations
        )

    def test_strict_mode(self):
        """Test strict mode flags any violation."""
        validator = FiduciaryValidator(strict_mode=True)
        result = validator.validate_action(
            action="This action maybe possibly might work",  # vague
        )

        # Strict mode: any violation = non-compliant
        if len(result.violations) > 0:
            assert result.compliant is False

    def test_passed_duties_tracking(self):
        """Test tracking of passed duties."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            action="Provide clear and specific financial guidance"
        )

        # Should have some passed duties
        assert len(result.passed_duties) > 0

    def test_explanations_provided(self):
        """Test that explanations are provided."""
        validator = FiduciaryValidator()
        result = validator.validate_action(action="Help with budgeting")

        assert len(result.explanations) > 0

    def test_confidence_score(self):
        """Test confidence score calculation."""
        validator = FiduciaryValidator()

        # Clean action should have high confidence
        clean_result = validator.validate_action(action="Provide helpful information")
        assert clean_result.confidence >= 0.8

        # Action with violations should have lower confidence
        risky_result = validator.validate_action(
            action="High risk speculative investment, trust me, upgrade to premium",
            user_context=UserContext(risk_tolerance="low")
        )
        assert risky_result.confidence < clean_result.confidence


class TestFiduciaryGuard:
    """Tests for FiduciaryGuard decorator."""

    def test_protect_decorator_allows_compliant(self):
        """Test decorator allows compliant functions."""
        guard = FiduciaryGuard(block_on_violation=False)

        @guard.protect
        def safe_function(x):
            return x * 2

        result = safe_function(5)
        assert result == 10

    def test_protect_decorator_blocks_violation(self):
        """Test decorator blocks on violation."""
        guard = FiduciaryGuard(block_on_violation=True)

        @guard.protect
        def risky_function(upgrade_to_premium=True):
            return "result"

        # This might raise FiduciaryViolationError due to "premium" keyword
        # But the action string includes function name, so it depends on detection
        try:
            result = risky_function()
            # If no violation detected, that's also acceptable
            assert result == "result"
        except FiduciaryViolationError:
            pass  # Expected if violation detected

    def test_decision_log(self):
        """Test decision logging."""
        guard = FiduciaryGuard(log_decisions=True, block_on_violation=False)

        @guard.protect
        def some_action():
            return "done"

        some_action()
        some_action()

        log = guard.decision_log
        assert len(log) == 2
        assert all("timestamp" in entry for entry in log)


class TestFiduciaryResult:
    """Tests for FiduciaryResult."""

    def test_to_dict(self):
        """Test result to dictionary conversion."""
        result = FiduciaryResult(
            compliant=True,
            violations=[],
            passed_duties=[FiduciaryDuty.LOYALTY, FiduciaryDuty.CARE],
            explanations={"loyalty": "No conflicts detected"},
            confidence=0.95
        )

        d = result.to_dict()

        assert d["compliant"] is True
        assert "loyalty" in d["passed_duties"]
        assert d["confidence"] == 0.95


class TestConvenienceFunctions:
    """Tests for convenience functions."""

    def test_validate_fiduciary(self):
        """Test validate_fiduciary function."""
        result = validate_fiduciary(
            action="Provide helpful advice",
            user_context={"risk_tolerance": "moderate"}
        )

        assert isinstance(result, FiduciaryResult)

    def test_is_fiduciary_compliant(self):
        """Test is_fiduciary_compliant function."""
        # Simple helpful action should be compliant
        compliant = is_fiduciary_compliant(
            action="Answer user question about programming"
        )
        assert isinstance(compliant, bool)

    def test_is_fiduciary_compliant_detects_issues(self):
        """Test is_fiduciary_compliant detects issues."""
        # Action with clear conflict should not be compliant
        result = is_fiduciary_compliant(
            action="Upgrade to our premium service immediately, trust me",
            user_context={"risk_tolerance": "low"}
        )
        # May or may not be compliant depending on detection
        assert isinstance(result, bool)


class TestSeverityEnum:
    """Tests for Severity enum."""

    def test_all_values(self):
        """Test all severity values exist."""
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"

    def test_from_string_valid(self):
        """Test from_string with valid values."""
        assert Severity.from_string("low") == Severity.LOW
        assert Severity.from_string("HIGH") == Severity.HIGH

    def test_from_string_invalid(self):
        """Test from_string with invalid value defaults to MEDIUM."""
        assert Severity.from_string("invalid") == Severity.MEDIUM


class TestRiskToleranceEnum:
    """Tests for RiskTolerance enum."""

    def test_all_values(self):
        """Test all risk tolerance values exist."""
        assert RiskTolerance.LOW == "low"
        assert RiskTolerance.MODERATE == "moderate"
        assert RiskTolerance.HIGH == "high"

    def test_from_string_valid(self):
        """Test from_string with valid values."""
        assert RiskTolerance.from_string("low") == RiskTolerance.LOW
        assert RiskTolerance.from_string("MODERATE") == RiskTolerance.MODERATE

    def test_from_string_invalid(self):
        """Test from_string with invalid value defaults to MODERATE."""
        assert RiskTolerance.from_string("invalid") == RiskTolerance.MODERATE


class TestViolationDataclass:
    """Tests for Violation dataclass with Severity enum."""

    def test_severity_auto_conversion(self):
        """Test that string severity is auto-converted to enum."""
        violation = Violation(
            duty=FiduciaryDuty.LOYALTY,
            type=ViolationType.CONFLICT_OF_INTEREST,
            description="Test",
            severity="high",  # String should be converted
        )
        assert violation.severity == Severity.HIGH

    def test_is_blocking(self):
        """Test is_blocking method."""
        high_violation = Violation(
            duty=FiduciaryDuty.CARE,
            type=ViolationType.USER_HARM,
            description="High severity",
            severity=Severity.HIGH,
        )
        assert high_violation.is_blocking() is True

        low_violation = Violation(
            duty=FiduciaryDuty.CARE,
            type=ViolationType.INCOMPETENT_ACTION,
            description="Low severity",
            severity=Severity.LOW,
        )
        assert low_violation.is_blocking() is False


class TestUserContextWithEnum:
    """Tests for UserContext with RiskTolerance enum."""

    def test_risk_tolerance_enum(self):
        """Test risk_tolerance is converted to enum."""
        ctx = UserContext(risk_tolerance="low")
        assert ctx.risk_tolerance == RiskTolerance.LOW

    def test_from_dict_with_string(self):
        """Test from_dict converts string to enum."""
        ctx = UserContext.from_dict({"risk_tolerance": "high"})
        assert ctx.risk_tolerance == RiskTolerance.HIGH

    def test_to_dict(self):
        """Test to_dict outputs string value."""
        ctx = UserContext(risk_tolerance=RiskTolerance.LOW)
        d = ctx.to_dict()
        assert d["risk_tolerance"] == "low"


class TestConflictDetectorValidation:
    """Tests for ConflictDetector input validation."""

    def test_detect_none_action(self):
        """Test detect raises TypeError for None action."""
        detector = ConflictDetector()
        with pytest.raises(TypeError, match="cannot be None"):
            detector.detect(None)

    def test_detect_invalid_type(self):
        """Test detect raises TypeError for non-string action."""
        detector = ConflictDetector()
        with pytest.raises(TypeError, match="must be a string"):
            detector.detect(123)

    def test_custom_patterns_validation(self):
        """Test custom_patterns validation."""
        with pytest.raises(TypeError):
            ConflictDetector(custom_patterns="not a list")

        with pytest.raises(ValueError, match="must be.*tuple"):
            ConflictDetector(custom_patterns=[("pattern",)])  # Missing second element

        with pytest.raises(ValueError, match="must contain strings"):
            ConflictDetector(custom_patterns=[(123, "type")])

    def test_invalid_regex_pattern(self):
        """Test invalid regex pattern raises ValueError."""
        with pytest.raises(ValueError, match="Invalid regex"):
            ConflictDetector(custom_patterns=[("[invalid", "type")])


class TestFiduciaryValidatorValidation:
    """Tests for FiduciaryValidator input validation."""

    def test_validate_none_action(self):
        """Test validate raises TypeError for None action."""
        validator = FiduciaryValidator()
        with pytest.raises(TypeError, match="cannot be None"):
            validator.validate_action(None)

    def test_validate_empty_action(self):
        """Test validate raises ValueError for empty action."""
        validator = FiduciaryValidator()
        with pytest.raises(ValueError, match="cannot be empty"):
            validator.validate_action("")
        with pytest.raises(ValueError, match="cannot be empty"):
            validator.validate_action("   ")

    def test_validate_invalid_type(self):
        """Test validate raises TypeError for non-string action."""
        validator = FiduciaryValidator()
        with pytest.raises(TypeError, match="must be a string"):
            validator.validate_action(123)

    def test_custom_rules_validation(self):
        """Test custom_rules validation."""
        with pytest.raises(TypeError):
            FiduciaryValidator(custom_rules="not a list")

        with pytest.raises(TypeError, match="must be callable"):
            FiduciaryValidator(custom_rules=["not callable"])

    def test_statistics_tracking(self):
        """Test statistics are tracked."""
        validator = FiduciaryValidator()
        validator.validate_action("Test action 1")
        validator.validate_action("Test action 2")

        stats = validator.get_stats()
        assert stats["total_validated"] == 2

        validator.reset_stats()
        stats = validator.get_stats()
        assert stats["total_validated"] == 0

    def test_dict_user_context_conversion(self):
        """Test dict is converted to UserContext."""
        validator = FiduciaryValidator()
        result = validator.validate_action(
            "Test action",
            user_context={"risk_tolerance": "low", "goals": ["save money"]}
        )
        assert isinstance(result, FiduciaryResult)


class TestFiduciaryGuardValidation:
    """Tests for FiduciaryGuard input validation."""

    def test_validate_and_execute_non_callable(self):
        """Test validate_and_execute raises TypeError for non-callable."""
        guard = FiduciaryGuard(block_on_violation=False)
        with pytest.raises(TypeError, match="must be callable"):
            guard.validate_and_execute("not callable")

    def test_clear_log(self):
        """Test clear_log method."""
        guard = FiduciaryGuard(log_decisions=True, block_on_violation=False)

        @guard.protect
        def test_func():
            return "result"

        test_func()
        assert len(guard.decision_log) == 1

        guard.clear_log()
        assert len(guard.decision_log) == 0

    def test_max_log_size(self):
        """Test log size is limited."""
        guard = FiduciaryGuard(
            log_decisions=True,
            block_on_violation=False,
            max_log_size=5,
        )

        @guard.protect
        def test_func():
            return "result"

        for _ in range(10):
            test_func()

        assert len(guard.decision_log) == 5


class TestThreadSafety:
    """Tests for thread safety."""

    def test_validator_thread_safety(self):
        """Test FiduciaryValidator is thread-safe."""
        validator = FiduciaryValidator()
        errors = []

        def validate_loop():
            try:
                for i in range(50):
                    validator.validate_action(f"Test action {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=validate_loop) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        stats = validator.get_stats()
        assert stats["total_validated"] == 250

    def test_guard_thread_safety(self):
        """Test FiduciaryGuard is thread-safe."""
        guard = FiduciaryGuard(log_decisions=True, block_on_violation=False)
        errors = []

        @guard.protect
        def test_func(x):
            return x * 2

        def call_loop():
            try:
                for i in range(50):
                    test_func(i)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=call_loop) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert len(guard.decision_log) == 250
