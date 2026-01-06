"""
Tests for sentinelseed.detection.checkers.base module.

This module tests the BaseChecker abstract base class and CheckerConfig.
Tests verify the contract that all checker implementations must follow.

Key Difference from Detectors:
    - Detectors (input): "Is this an ATTACK?" - Pattern/intent based
    - Checkers (output): "Did the SEED fail?" - Behavior/content based

Test Categories:
    1. CheckerConfig: Creation, validation, rules, options
    2. BaseChecker Abstract: Cannot instantiate, requires implementations
    3. BaseChecker Contract: Properties, methods, lifecycle
    4. Context Handling: input_context, require_input_context
    5. Rules: merge_rules, supports_rule, get_supported_rules
    6. Statistics: Tracking, context_provided counter
    7. Batch Checking: Default implementation, error handling
"""

import pytest
from typing import Dict, Any, Optional

from sentinelseed.detection.checkers.base import (
    BaseChecker,
    CheckerConfig,
)
from sentinelseed.detection.types import (
    DetectionResult,
    CheckFailureType,
)


# =============================================================================
# Test Fixtures - Concrete Checker Implementations for Testing
# =============================================================================

class SimpleTestChecker(BaseChecker):
    """
    Minimal concrete checker implementation for testing BaseChecker.

    This checker detects the word "harmful" in output.
    """

    def __init__(self, config: Optional[CheckerConfig] = None):
        super().__init__(config)
        self._harmful_word = "harmful"

    @property
    def name(self) -> str:
        return "simple_test_checker"

    @property
    def version(self) -> str:
        return "1.0.0"

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        if input_context:
            self._stats["context_provided"] += 1

        if self._harmful_word.lower() in output.lower():
            result = DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.85,
                category=CheckFailureType.HARMFUL_CONTENT.value,
                description=f"Found '{self._harmful_word}' in output",
                evidence=self._harmful_word,
            )
            self._stats["failures_detected"] += 1
            return result

        return DetectionResult.nothing_detected(self.name, self.version)


class ConfigurableTestChecker(BaseChecker):
    """
    Checker that uses configuration options and rules for testing.
    """

    @property
    def name(self) -> str:
        return "configurable_test_checker"

    @property
    def version(self) -> str:
        return "2.0.0"

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        merged_rules = self._merge_rules(rules)
        keyword = self._config.get_option("keyword", "default")
        max_length = merged_rules.get("max_length", float("inf"))

        if keyword.lower() in output.lower():
            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.8,
                category=CheckFailureType.POLICY_VIOLATION.value,
                description=f"Found configured keyword: {keyword}",
            )

        if len(output) > max_length:
            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.9,
                category=CheckFailureType.SCOPE_VIOLATION.value,
                description=f"Output exceeds max_length: {len(output)} > {max_length}",
            )

        return DetectionResult.nothing_detected(self.name, self.version)

    def supports_rule(self, rule_name: str) -> bool:
        return rule_name in ["max_length", "forbidden_words"]

    def get_supported_rules(self):
        return ["max_length", "forbidden_words"]


class ContextAwareTestChecker(BaseChecker):
    """
    Checker that demonstrates context-aware checking.

    This checker requires input context to make decisions:
    - If input mentions "chemistry" and output mentions "explosive" -> OK
    - If input doesn't mention "chemistry" and output mentions "explosive" -> Fail
    """

    def __init__(self, config: Optional[CheckerConfig] = None):
        super().__init__(config)

    @property
    def name(self) -> str:
        return "context_aware_test_checker"

    @property
    def version(self) -> str:
        return "1.0.0"

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        self._ensure_initialized()

        # Track stats
        self._stats["total_calls"] += 1
        if input_context:
            self._stats["context_provided"] += 1

        # Check if context is required
        if self._config.require_input_context and input_context is None:
            raise ValueError("input_context is required for this checker")

        # Context-aware check
        has_explosive = "explosive" in output.lower()
        has_chemistry_context = (
            input_context and "chemistry" in input_context.lower()
        )

        if has_explosive and not has_chemistry_context:
            result = DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.9,
                category=CheckFailureType.HARMFUL_CONTENT.value,
                description="Explosive content without appropriate context",
                evidence="explosive",
            )
            self._stats["failures_detected"] += 1
            return result

        return DetectionResult.nothing_detected(self.name, self.version)


class LifecycleTestChecker(BaseChecker):
    """
    Checker that tracks lifecycle method calls for testing.
    """

    def __init__(self, config: Optional[CheckerConfig] = None):
        super().__init__(config)
        self.lifecycle_events: list = []

    @property
    def name(self) -> str:
        return "lifecycle_test_checker"

    @property
    def version(self) -> str:
        return "1.0.0"

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        self._ensure_initialized()
        self.lifecycle_events.append("check")
        return DetectionResult.nothing_detected(self.name, self.version)

    def initialize(self) -> None:
        self.lifecycle_events.append("initialize")
        super().initialize()

    def shutdown(self) -> None:
        self.lifecycle_events.append("shutdown")
        super().shutdown()


# =============================================================================
# CheckerConfig Tests
# =============================================================================

class TestCheckerConfig:
    """Tests for CheckerConfig dataclass."""

    def test_default_values(self):
        """Default values are correctly set."""
        config = CheckerConfig()
        assert config.enabled is True
        assert config.confidence_threshold == 0.0
        assert config.failure_types == []
        assert config.require_input_context is False
        assert config.rules == {}
        assert config.options == {}

    def test_custom_values(self):
        """Can create with custom values."""
        config = CheckerConfig(
            enabled=False,
            confidence_threshold=0.7,
            failure_types=[
                CheckFailureType.HARMFUL_CONTENT,
                CheckFailureType.DECEPTIVE_CONTENT,
            ],
            require_input_context=True,
            rules={"max_length": 1000, "forbidden_topics": ["violence"]},
            options={"strict": True},
        )
        assert config.enabled is False
        assert config.confidence_threshold == 0.7
        assert CheckFailureType.HARMFUL_CONTENT in config.failure_types
        assert config.require_input_context is True
        assert config.rules["max_length"] == 1000
        assert config.options["strict"] is True


class TestCheckerConfigValidation:
    """Tests for CheckerConfig validation."""

    def test_confidence_threshold_below_zero_raises(self):
        """confidence_threshold < 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CheckerConfig(confidence_threshold=-0.1)
        assert "confidence_threshold" in str(exc_info.value)

    def test_confidence_threshold_above_one_raises(self):
        """confidence_threshold > 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            CheckerConfig(confidence_threshold=1.1)
        assert "confidence_threshold" in str(exc_info.value)

    def test_confidence_threshold_at_boundaries(self):
        """confidence_threshold at 0.0 and 1.0 is valid."""
        config_zero = CheckerConfig(confidence_threshold=0.0)
        config_one = CheckerConfig(confidence_threshold=1.0)
        assert config_zero.confidence_threshold == 0.0
        assert config_one.confidence_threshold == 1.0


class TestCheckerConfigGetOption:
    """Tests for CheckerConfig.get_option() method."""

    def test_get_existing_option(self):
        """get_option returns value for existing option."""
        config = CheckerConfig(options={"key1": "value1", "key2": 42})
        assert config.get_option("key1") == "value1"
        assert config.get_option("key2") == 42

    def test_get_missing_option_returns_default(self):
        """get_option returns default for missing option."""
        config = CheckerConfig(options={})
        assert config.get_option("missing") is None
        assert config.get_option("missing", "fallback") == "fallback"


class TestCheckerConfigGetRule:
    """Tests for CheckerConfig.get_rule() method."""

    def test_get_existing_rule(self):
        """get_rule returns value for existing rule."""
        config = CheckerConfig(rules={"max_length": 500, "allow_code": True})
        assert config.get_rule("max_length") == 500
        assert config.get_rule("allow_code") is True

    def test_get_missing_rule_returns_default(self):
        """get_rule returns default for missing rule."""
        config = CheckerConfig(rules={})
        assert config.get_rule("missing") is None
        assert config.get_rule("missing", 100) == 100


# =============================================================================
# BaseChecker Abstract Tests
# =============================================================================

class TestBaseCheckerAbstract:
    """Tests verifying BaseChecker is properly abstract."""

    def test_cannot_instantiate_directly(self):
        """Cannot instantiate BaseChecker directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseChecker()
        error_msg = str(exc_info.value)
        assert "abstract" in error_msg.lower()

    def test_must_implement_name(self):
        """Subclass without name property fails."""
        class IncompleteChecker(BaseChecker):
            @property
            def version(self) -> str:
                return "1.0.0"

            def check(self, output, input_context=None, rules=None):
                return DetectionResult.nothing_detected("test", "1.0")

        with pytest.raises(TypeError):
            IncompleteChecker()

    def test_must_implement_version(self):
        """Subclass without version property fails."""
        class IncompleteChecker(BaseChecker):
            @property
            def name(self) -> str:
                return "test"

            def check(self, output, input_context=None, rules=None):
                return DetectionResult.nothing_detected("test", "1.0")

        with pytest.raises(TypeError):
            IncompleteChecker()

    def test_must_implement_check(self):
        """Subclass without check method fails."""
        class IncompleteChecker(BaseChecker):
            @property
            def name(self) -> str:
                return "test"

            @property
            def version(self) -> str:
                return "1.0.0"

        with pytest.raises(TypeError):
            IncompleteChecker()


# =============================================================================
# BaseChecker Properties Tests
# =============================================================================

class TestBaseCheckerProperties:
    """Tests for BaseChecker properties."""

    def test_name_property(self):
        """name property returns checker name."""
        checker = SimpleTestChecker()
        assert checker.name == "simple_test_checker"

    def test_version_property(self):
        """version property returns checker version."""
        checker = SimpleTestChecker()
        assert checker.version == "1.0.0"

    def test_config_property_default(self):
        """config property returns default config when not provided."""
        checker = SimpleTestChecker()
        assert isinstance(checker.config, CheckerConfig)
        assert checker.config.enabled is True

    def test_config_property_custom(self):
        """config property returns provided config."""
        config = CheckerConfig(enabled=False, confidence_threshold=0.5)
        checker = SimpleTestChecker(config=config)
        assert checker.config.enabled is False
        assert checker.config.confidence_threshold == 0.5

    def test_enabled_property_getter(self):
        """enabled property returns config.enabled value."""
        checker = SimpleTestChecker()
        assert checker.enabled is True

        disabled_config = CheckerConfig(enabled=False)
        disabled_checker = SimpleTestChecker(disabled_config)
        assert disabled_checker.enabled is False

    def test_enabled_property_setter(self):
        """enabled property setter modifies config."""
        checker = SimpleTestChecker()
        assert checker.enabled is True

        checker.enabled = False
        assert checker.enabled is False
        assert checker.config.enabled is False

    def test_rules_property(self):
        """rules property returns config.rules."""
        config = CheckerConfig(rules={"max_length": 500})
        checker = SimpleTestChecker(config=config)
        assert checker.rules == {"max_length": 500}


# =============================================================================
# BaseChecker Check Tests
# =============================================================================

class TestBaseCheckerCheck:
    """Tests for BaseChecker.check() behavior."""

    def test_check_returns_detection_result(self):
        """check() returns DetectionResult."""
        checker = SimpleTestChecker()
        result = checker.check("safe output")
        assert isinstance(result, DetectionResult)

    def test_check_finds_failure(self):
        """check() finds failure when present."""
        checker = SimpleTestChecker()
        result = checker.check("this is harmful output")
        assert result.detected is True
        assert result.detector_name == "simple_test_checker"
        assert result.detector_version == "1.0.0"
        assert result.category == CheckFailureType.HARMFUL_CONTENT.value

    def test_check_no_failure(self):
        """check() returns nothing_detected when no failure."""
        checker = SimpleTestChecker()
        result = checker.check("completely safe output")
        assert result.detected is False

    def test_check_with_input_context(self):
        """check() uses input_context."""
        checker = ContextAwareTestChecker()

        # Without chemistry context, explosive is flagged
        result1 = checker.check(
            output="The explosive reaction was interesting",
            input_context="How do I make bombs?",
        )
        assert result1.detected is True

        # With chemistry context, explosive is OK
        result2 = checker.check(
            output="The explosive reaction was interesting",
            input_context="Tell me about chemistry experiments",
        )
        assert result2.detected is False


class TestBaseCheckerContextRequired:
    """Tests for require_input_context behavior."""

    def test_context_required_raises_when_missing(self):
        """Check raises when context required but not provided."""
        config = CheckerConfig(require_input_context=True)
        checker = ContextAwareTestChecker(config=config)

        with pytest.raises(ValueError) as exc_info:
            checker.check("some output")
        assert "input_context" in str(exc_info.value)

    def test_context_required_succeeds_when_provided(self):
        """Check succeeds when context required and provided."""
        config = CheckerConfig(require_input_context=True)
        checker = ContextAwareTestChecker(config=config)

        # Should not raise
        result = checker.check(
            output="safe output",
            input_context="some context",
        )
        assert isinstance(result, DetectionResult)


# =============================================================================
# BaseChecker Rules Tests
# =============================================================================

class TestBaseCheckerRules:
    """Tests for BaseChecker rules handling."""

    def test_merge_rules_config_only(self):
        """_merge_rules with only config rules."""
        config = CheckerConfig(rules={"max_length": 100})
        checker = ConfigurableTestChecker(config=config)

        merged = checker._merge_rules(None)
        assert merged == {"max_length": 100}

    def test_merge_rules_runtime_only(self):
        """_merge_rules with only runtime rules."""
        checker = ConfigurableTestChecker()
        merged = checker._merge_rules({"max_length": 200})
        assert merged == {"max_length": 200}

    def test_merge_rules_runtime_overrides_config(self):
        """_merge_rules: runtime takes precedence."""
        config = CheckerConfig(rules={"max_length": 100, "other": "value"})
        checker = ConfigurableTestChecker(config=config)

        merged = checker._merge_rules({"max_length": 200})
        assert merged["max_length"] == 200
        assert merged["other"] == "value"

    def test_supports_rule(self):
        """supports_rule returns correct value."""
        checker = ConfigurableTestChecker()
        assert checker.supports_rule("max_length") is True
        assert checker.supports_rule("unsupported") is False

    def test_get_supported_rules(self):
        """get_supported_rules returns list."""
        checker = ConfigurableTestChecker()
        rules = checker.get_supported_rules()
        assert "max_length" in rules
        assert "forbidden_words" in rules

    def test_default_supports_rule_returns_false(self):
        """Default supports_rule returns False."""
        checker = SimpleTestChecker()
        assert checker.supports_rule("anything") is False

    def test_default_get_supported_rules_returns_empty(self):
        """Default get_supported_rules returns empty list."""
        checker = SimpleTestChecker()
        assert checker.get_supported_rules() == []

    def test_check_uses_merged_rules(self):
        """check() uses merged rules."""
        config = CheckerConfig(rules={"max_length": 1000})
        checker = ConfigurableTestChecker(config=config)

        # Config says 1000, but we pass runtime rule of 10
        long_output = "A" * 50
        result = checker.check(long_output, rules={"max_length": 10})

        assert result.detected is True
        assert result.category == CheckFailureType.SCOPE_VIOLATION.value


# =============================================================================
# BaseChecker Statistics Tests
# =============================================================================

class TestBaseCheckerStats:
    """Tests for BaseChecker statistics tracking."""

    def test_initial_stats(self):
        """Initial stats are zero."""
        checker = SimpleTestChecker()
        stats = checker.get_stats()
        assert stats["failures_detected"] == 0
        assert stats["total_calls"] == 0
        assert stats["errors"] == 0
        assert stats["context_provided"] == 0

    def test_stats_increment_on_failure(self):
        """Stats increment when failure detected."""
        checker = SimpleTestChecker()
        checker.check("harmful content")
        stats = checker.get_stats()
        assert stats["failures_detected"] == 1
        assert stats["total_calls"] == 1

    def test_stats_increment_on_no_failure(self):
        """total_calls increments even when no failure."""
        checker = SimpleTestChecker()
        checker.check("safe output")
        stats = checker.get_stats()
        assert stats["failures_detected"] == 0
        assert stats["total_calls"] == 1

    def test_stats_context_provided(self):
        """context_provided increments when context given."""
        checker = SimpleTestChecker()
        checker.check("output", input_context="some context")
        stats = checker.get_stats()
        assert stats["context_provided"] == 1

    def test_stats_context_not_provided(self):
        """context_provided doesn't increment without context."""
        checker = SimpleTestChecker()
        checker.check("output")
        stats = checker.get_stats()
        assert stats["context_provided"] == 0

    def test_stats_accumulate(self):
        """Stats accumulate across multiple calls."""
        checker = SimpleTestChecker()
        checker.check("harmful 1")
        checker.check("safe", input_context="ctx")
        checker.check("harmful 2", input_context="ctx")
        checker.check("safe again")

        stats = checker.get_stats()
        assert stats["total_calls"] == 4
        assert stats["failures_detected"] == 2
        assert stats["context_provided"] == 2

    def test_reset_stats(self):
        """reset_stats() clears all statistics."""
        checker = SimpleTestChecker()
        checker.check("harmful", input_context="ctx")

        checker.reset_stats()
        stats = checker.get_stats()
        assert stats["failures_detected"] == 0
        assert stats["total_calls"] == 0
        assert stats["context_provided"] == 0

    def test_get_stats_returns_copy(self):
        """get_stats() returns a copy, not the original dict."""
        checker = SimpleTestChecker()
        stats1 = checker.get_stats()
        stats1["failures_detected"] = 999

        stats2 = checker.get_stats()
        assert stats2["failures_detected"] == 0


# =============================================================================
# BaseChecker Batch Check Tests
# =============================================================================

class TestBaseCheckerBatch:
    """Tests for BaseChecker.check_batch() method."""

    def test_check_batch_basic(self):
        """check_batch() processes multiple outputs."""
        checker = SimpleTestChecker()
        outputs = ["harmful one", "safe output", "another harmful"]
        results = checker.check_batch(outputs)

        assert len(results) == 3
        assert results[0].detected is True
        assert results[1].detected is False
        assert results[2].detected is True

    def test_check_batch_with_contexts(self):
        """check_batch() uses provided contexts."""
        checker = SimpleTestChecker()
        outputs = ["output1", "output2"]
        contexts = ["context1", "context2"]

        results = checker.check_batch(outputs, contexts)
        assert len(results) == 2

    def test_check_batch_with_rules(self):
        """check_batch() applies rules to all checks."""
        checker = ConfigurableTestChecker()
        outputs = ["short", "this is a longer output text"]
        results = checker.check_batch(outputs, rules={"max_length": 10})

        assert results[0].detected is False  # "short" < 10
        assert results[1].detected is True   # longer > 10

    def test_check_batch_length_mismatch_raises(self):
        """check_batch() raises if outputs and contexts lengths differ."""
        checker = SimpleTestChecker()
        outputs = ["out1", "out2", "out3"]
        contexts = ["ctx1"]  # Only one context

        with pytest.raises(ValueError) as exc_info:
            checker.check_batch(outputs, contexts)
        assert "same length" in str(exc_info.value)

    def test_check_batch_empty_lists(self):
        """check_batch() handles empty lists."""
        checker = SimpleTestChecker()
        results = checker.check_batch([])
        assert results == []

    def test_check_batch_none_contexts(self):
        """check_batch() works with input_contexts=None."""
        checker = SimpleTestChecker()
        outputs = ["harmful", "safe"]
        results = checker.check_batch(outputs, input_contexts=None)
        assert len(results) == 2


# =============================================================================
# BaseChecker Lifecycle Tests
# =============================================================================

class TestBaseCheckerLifecycle:
    """Tests for BaseChecker lifecycle methods."""

    def test_initialize_sets_flag(self):
        """initialize() sets _initialized flag."""
        checker = LifecycleTestChecker()
        assert checker._initialized is False

        checker.initialize()
        assert checker._initialized is True

    def test_shutdown_clears_flag(self):
        """shutdown() clears _initialized flag."""
        checker = LifecycleTestChecker()
        checker.initialize()
        assert checker._initialized is True

        checker.shutdown()
        assert checker._initialized is False

    def test_ensure_initialized_auto_initializes(self):
        """_ensure_initialized() calls initialize() if needed."""
        checker = LifecycleTestChecker()
        assert checker._initialized is False

        checker.check("test")  # Triggers _ensure_initialized

        assert checker._initialized is True
        assert "initialize" in checker.lifecycle_events

    def test_lifecycle_sequence(self):
        """Lifecycle methods are called in correct sequence."""
        checker = LifecycleTestChecker()

        checker.initialize()
        checker.check("test")
        checker.shutdown()

        assert checker.lifecycle_events == ["initialize", "check", "shutdown"]


# =============================================================================
# BaseChecker Repr Tests
# =============================================================================

class TestBaseCheckerRepr:
    """Tests for BaseChecker.__repr__() method."""

    def test_repr_contains_class_name(self):
        """__repr__ contains the class name."""
        checker = SimpleTestChecker()
        repr_str = repr(checker)
        assert "SimpleTestChecker" in repr_str

    def test_repr_contains_name(self):
        """__repr__ contains checker name."""
        checker = SimpleTestChecker()
        repr_str = repr(checker)
        assert "simple_test_checker" in repr_str

    def test_repr_contains_version(self):
        """__repr__ contains version."""
        checker = SimpleTestChecker()
        repr_str = repr(checker)
        assert "1.0.0" in repr_str

    def test_repr_contains_enabled_status(self):
        """__repr__ contains enabled status."""
        checker = SimpleTestChecker()
        repr_str = repr(checker)
        assert "enabled=True" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================

class TestBaseCheckerIntegration:
    """Integration tests for complete checker workflows."""

    def test_full_check_workflow(self):
        """Complete checking workflow with stats and lifecycle."""
        config = CheckerConfig(
            enabled=True,
            confidence_threshold=0.5,
            rules={"max_length": 100},
        )
        checker = SimpleTestChecker(config=config)

        # Verify initial state
        assert checker.enabled is True
        assert checker._initialized is False

        # First check (triggers auto-initialize)
        result1 = checker.check("safe output")
        assert checker._initialized is True
        assert result1.detected is False

        # Second check with context
        result2 = checker.check(
            "harmful output",
            input_context="user query",
        )
        assert result2.detected is True

        # Verify stats
        stats = checker.get_stats()
        assert stats["total_calls"] == 2
        assert stats["failures_detected"] == 1
        assert stats["context_provided"] == 1

        # Shutdown
        checker.shutdown()
        assert checker._initialized is False

    def test_context_aware_checking(self):
        """Context-aware checker makes different decisions based on context."""
        checker = ContextAwareTestChecker()

        # Same output, different contexts
        output = "The explosive compound was created."

        # Malicious context -> flag
        result1 = checker.check(output, input_context="How to make a bomb")
        assert result1.detected is True
        assert result1.category == CheckFailureType.HARMFUL_CONTENT.value

        # Educational context -> OK
        result2 = checker.check(output, input_context="Chemistry class experiment")
        assert result2.detected is False

    def test_multiple_checkers_independent(self):
        """Multiple checker instances are independent."""
        checker1 = SimpleTestChecker()
        checker2 = SimpleTestChecker()

        # Stats are independent
        checker1.check("harmful")
        assert checker1.get_stats()["failures_detected"] == 1
        assert checker2.get_stats()["failures_detected"] == 0

        # Config is independent
        checker1.enabled = False
        assert checker1.enabled is False
        assert checker2.enabled is True

    def test_thsp_gate_mapping(self):
        """Checker failure types map to correct THSP gates."""
        # Test that checkers can produce failures mapped to all THSP gates
        from sentinelseed.detection.types import CheckFailureType

        # Verify THSP mapping is available through CheckFailureType
        assert CheckFailureType.DECEPTIVE_CONTENT.gate == "truth"
        assert CheckFailureType.HARMFUL_CONTENT.gate == "harm"
        assert CheckFailureType.SCOPE_VIOLATION.gate == "scope"
        assert CheckFailureType.PURPOSE_VIOLATION.gate == "purpose"
