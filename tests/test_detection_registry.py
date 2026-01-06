"""
Tests for sentinelseed.detection.registry module.

This module tests the registry classes that enable the plugin architecture:
- RegisteredComponent: Metadata wrapper
- DetectorRegistry: Attack detector management
- CheckerRegistry: Behavior checker management
- AttackExamplesRegistry: Attack examples for embedding detection
- RulesRegistry: Behavior rules for compliance checking
- Rule: Rule dataclass

Test Categories:
    1. Registration: register, unregister, replace
    2. Configuration: enable, disable, set_weight
    3. Querying: get, get_enabled, list_*
    4. Execution: run_all with error handling
    5. Examples: add, remove, get examples
    6. Rules: add, remove, validation, by_category
    7. File Loading: from_file with JSON
"""

import json
import os
import tempfile
import pytest
from typing import Dict, Any, Optional

from sentinelseed.detection.registry import (
    RegisteredComponent,
    DetectorRegistry,
    CheckerRegistry,
    AttackExamplesRegistry,
    RulesRegistry,
    Rule,
)
from sentinelseed.detection.types import DetectionResult


# =============================================================================
# Test Fixtures - Mock Detector and Checker
# =============================================================================

class MockDetector:
    """Mock detector for testing DetectorRegistry."""

    def __init__(self, name: str = "mock_detector", version: str = "1.0.0"):
        self._name = name
        self._version = version

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        if "attack" in text.lower():
            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.9,
                category="test",
                description="Mock detection",
            )
        return DetectionResult.nothing_detected(self.name, self.version)


class MockChecker:
    """Mock checker for testing CheckerRegistry."""

    def __init__(self, name: str = "mock_checker", version: str = "1.0.0"):
        self._name = name
        self._version = version

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        if "harmful" in output.lower():
            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.85,
                category="harmful_content",
                description="Mock check failure",
            )
        return DetectionResult.nothing_detected(self.name, self.version)


class FailingDetector:
    """Detector that always raises an exception."""

    @property
    def name(self) -> str:
        return "failing_detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    def detect(self, text: str, context: Optional[Dict] = None) -> DetectionResult:
        raise RuntimeError("Intentional failure")


class FailingChecker:
    """Checker that always raises an exception."""

    @property
    def name(self) -> str:
        return "failing_checker"

    @property
    def version(self) -> str:
        return "1.0.0"

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict] = None,
    ) -> DetectionResult:
        raise RuntimeError("Intentional failure")


# =============================================================================
# RegisteredComponent Tests
# =============================================================================

class TestRegisteredComponent:
    """Tests for RegisteredComponent dataclass."""

    def test_creation(self):
        """Can create RegisteredComponent."""
        comp = RegisteredComponent(
            name="test",
            version="1.0.0",
            weight=1.5,
            enabled=True,
            component=MockDetector(),
        )
        assert comp.name == "test"
        assert comp.version == "1.0.0"
        assert comp.weight == 1.5
        assert comp.enabled is True

    def test_to_dict(self):
        """to_dict returns correct structure without component."""
        comp = RegisteredComponent(
            name="test",
            version="2.0.0",
            weight=0.8,
            enabled=False,
            component=MockDetector(),
        )
        d = comp.to_dict()

        assert d["name"] == "test"
        assert d["version"] == "2.0.0"
        assert d["weight"] == 0.8
        assert d["enabled"] is False
        assert "component" not in d


# =============================================================================
# DetectorRegistry Tests
# =============================================================================

class TestDetectorRegistry:
    """Tests for DetectorRegistry class."""

    def test_initial_empty(self):
        """Registry starts empty."""
        registry = DetectorRegistry()
        assert len(registry) == 0

    def test_register_detector(self):
        """Can register a detector."""
        registry = DetectorRegistry()
        detector = MockDetector()
        registry.register(detector)

        assert len(registry) == 1
        assert "mock_detector" in registry

    def test_register_with_custom_weight(self):
        """Can register with custom weight."""
        registry = DetectorRegistry()
        detector = MockDetector()
        registry.register(detector, weight=2.0)

        assert registry.get_weight("mock_detector") == 2.0

    def test_register_disabled(self):
        """Can register detector as disabled."""
        registry = DetectorRegistry()
        detector = MockDetector()
        registry.register(detector, enabled=False)

        assert registry.is_enabled("mock_detector") is False

    def test_register_negative_weight_raises(self):
        """Negative weight raises ValueError."""
        registry = DetectorRegistry()
        detector = MockDetector()

        with pytest.raises(ValueError) as exc_info:
            registry.register(detector, weight=-1.0)
        assert "weight" in str(exc_info.value)

    def test_register_invalid_detector_raises(self):
        """Registering object without required interface raises."""
        registry = DetectorRegistry()

        # Missing name/version
        with pytest.raises(ValueError):
            registry.register(object())

        # Has name/version but no detect method
        class BadDetector:
            name = "bad"
            version = "1.0"

        with pytest.raises(ValueError):
            registry.register(BadDetector())


class TestDetectorRegistryUnregister:
    """Tests for DetectorRegistry.unregister()."""

    def test_unregister_existing(self):
        """Can unregister existing detector."""
        registry = DetectorRegistry()
        registry.register(MockDetector())

        result = registry.unregister("mock_detector")

        assert result is True
        assert "mock_detector" not in registry
        assert len(registry) == 0

    def test_unregister_nonexistent(self):
        """Unregistering nonexistent detector returns False."""
        registry = DetectorRegistry()
        result = registry.unregister("nonexistent")
        assert result is False


class TestDetectorRegistryReplace:
    """Tests for DetectorRegistry.replace()."""

    def test_replace_preserves_config(self):
        """Replace preserves weight and enabled state."""
        registry = DetectorRegistry()
        registry.register(MockDetector("test", "1.0"), weight=2.0, enabled=False)

        new_detector = MockDetector("test", "2.0")
        registry.replace("test", new_detector)

        assert registry.get_weight("test") == 2.0
        assert registry.is_enabled("test") is False
        # Version updated
        info = registry.list_detectors()["test"]
        assert info["version"] == "2.0"

    def test_replace_nonexistent_raises(self):
        """Replacing nonexistent detector raises KeyError."""
        registry = DetectorRegistry()

        with pytest.raises(KeyError):
            registry.replace("nonexistent", MockDetector())

    def test_replace_without_preserve(self):
        """Replace without preserve_config acts as register."""
        registry = DetectorRegistry()
        detector = MockDetector()
        registry.replace("mock_detector", detector, preserve_config=False)

        assert "mock_detector" in registry


class TestDetectorRegistryEnableDisable:
    """Tests for enable/disable operations."""

    def test_enable_detector(self):
        """Can enable disabled detector."""
        registry = DetectorRegistry()
        registry.register(MockDetector(), enabled=False)

        result = registry.enable("mock_detector")

        assert result is True
        assert registry.is_enabled("mock_detector") is True

    def test_enable_nonexistent(self):
        """Enabling nonexistent detector returns False."""
        registry = DetectorRegistry()
        result = registry.enable("nonexistent")
        assert result is False

    def test_disable_detector(self):
        """Can disable enabled detector."""
        registry = DetectorRegistry()
        registry.register(MockDetector(), enabled=True)

        result = registry.disable("mock_detector")

        assert result is True
        assert registry.is_enabled("mock_detector") is False


class TestDetectorRegistryWeight:
    """Tests for weight operations."""

    def test_set_weight(self):
        """Can set detector weight."""
        registry = DetectorRegistry()
        registry.register(MockDetector())

        result = registry.set_weight("mock_detector", 3.0)

        assert result is True
        assert registry.get_weight("mock_detector") == 3.0

    def test_set_negative_weight_raises(self):
        """Setting negative weight raises ValueError."""
        registry = DetectorRegistry()
        registry.register(MockDetector())

        with pytest.raises(ValueError):
            registry.set_weight("mock_detector", -1.0)

    def test_get_weight_nonexistent(self):
        """Getting weight of nonexistent detector returns 1.0."""
        registry = DetectorRegistry()
        assert registry.get_weight("nonexistent") == 1.0


class TestDetectorRegistryQueries:
    """Tests for query operations."""

    def test_get_detector(self):
        """Can get detector by name."""
        registry = DetectorRegistry()
        detector = MockDetector()
        registry.register(detector)

        result = registry.get("mock_detector")
        assert result is detector

    def test_get_nonexistent(self):
        """Getting nonexistent detector returns None."""
        registry = DetectorRegistry()
        assert registry.get("nonexistent") is None

    def test_get_enabled(self):
        """get_enabled returns only enabled detectors."""
        registry = DetectorRegistry()
        registry.register(MockDetector("d1", "1.0"), enabled=True)
        registry.register(MockDetector("d2", "1.0"), enabled=False)
        registry.register(MockDetector("d3", "1.0"), enabled=True)

        enabled = registry.get_enabled()

        assert len(enabled) == 2
        names = [d.name for d in enabled]
        assert "d1" in names
        assert "d3" in names
        assert "d2" not in names

    def test_list_detectors(self):
        """list_detectors returns all detector info."""
        registry = DetectorRegistry()
        registry.register(MockDetector("d1", "1.0"), weight=1.5)
        registry.register(MockDetector("d2", "2.0"), enabled=False)

        info = registry.list_detectors()

        assert "d1" in info
        assert info["d1"]["version"] == "1.0"
        assert info["d1"]["weight"] == 1.5
        assert info["d2"]["enabled"] is False


class TestDetectorRegistryRunAll:
    """Tests for DetectorRegistry.run_all()."""

    def test_run_all_basic(self):
        """run_all executes all enabled detectors."""
        registry = DetectorRegistry()
        registry.register(MockDetector("d1", "1.0"))
        registry.register(MockDetector("d2", "1.0"))

        results = registry.run_all("attack text")

        assert len(results) == 2
        assert all(r.detected for r in results)

    def test_run_all_skips_disabled(self):
        """run_all skips disabled detectors."""
        registry = DetectorRegistry()
        registry.register(MockDetector("d1", "1.0"), enabled=True)
        registry.register(MockDetector("d2", "1.0"), enabled=False)

        results = registry.run_all("attack text")

        assert len(results) == 1
        assert results[0].detector_name == "d1"

    def test_run_all_handles_errors(self):
        """run_all handles detector errors gracefully."""
        registry = DetectorRegistry()
        registry.register(MockDetector("good", "1.0"))
        registry.register(FailingDetector())

        results = registry.run_all("test")

        assert len(results) == 2
        # One should be an error result
        error_results = [r for r in results if r.category == "error"]
        assert len(error_results) == 1

    def test_run_all_with_context(self):
        """run_all passes context to detectors."""
        registry = DetectorRegistry()
        registry.register(MockDetector())

        results = registry.run_all("test", context={"user_id": "123"})
        assert len(results) == 1


class TestDetectorRegistryDunderMethods:
    """Tests for __len__, __contains__, __iter__."""

    def test_len(self):
        """__len__ returns correct count."""
        registry = DetectorRegistry()
        assert len(registry) == 0

        registry.register(MockDetector("d1", "1.0"))
        assert len(registry) == 1

        registry.register(MockDetector("d2", "1.0"))
        assert len(registry) == 2

    def test_contains(self):
        """__contains__ works correctly."""
        registry = DetectorRegistry()
        registry.register(MockDetector())

        assert "mock_detector" in registry
        assert "other" not in registry

    def test_iter(self):
        """__iter__ yields detector names in order."""
        registry = DetectorRegistry()
        registry.register(MockDetector("d1", "1.0"))
        registry.register(MockDetector("d2", "1.0"))
        registry.register(MockDetector("d3", "1.0"))

        names = list(registry)
        assert names == ["d1", "d2", "d3"]


# =============================================================================
# CheckerRegistry Tests
# =============================================================================

class TestCheckerRegistry:
    """Tests for CheckerRegistry class."""

    def test_register_checker(self):
        """Can register a checker."""
        registry = CheckerRegistry()
        checker = MockChecker()
        registry.register(checker)

        assert len(registry) == 1
        assert "mock_checker" in registry

    def test_run_all_with_context_and_rules(self):
        """run_all passes input_context and rules."""
        registry = CheckerRegistry()
        registry.register(MockChecker())

        results = registry.run_all(
            output="harmful output",
            input_context="user query",
            rules={"max_length": 100},
        )

        assert len(results) == 1
        assert results[0].detected is True

    def test_run_all_handles_errors(self):
        """run_all handles checker errors gracefully."""
        registry = CheckerRegistry()
        registry.register(MockChecker("good", "1.0"))
        registry.register(FailingChecker())

        results = registry.run_all("test output")

        assert len(results) == 2
        error_results = [r for r in results if r.category == "error"]
        assert len(error_results) == 1


# =============================================================================
# AttackExamplesRegistry Tests
# =============================================================================

class TestAttackExamplesRegistry:
    """Tests for AttackExamplesRegistry class."""

    def test_defaults_loaded(self):
        """Default examples are loaded."""
        registry = AttackExamplesRegistry()

        # Should have default categories
        types = registry.get_attack_types()
        assert len(types) > 0
        assert "jailbreak:instruction_override" in types

    def test_skip_defaults(self):
        """Can skip loading defaults."""
        registry = AttackExamplesRegistry(load_defaults=False)
        assert len(registry) == 0

    def test_get_examples(self):
        """Can get examples for a category."""
        registry = AttackExamplesRegistry()
        examples = registry.get_examples("jailbreak:instruction_override")

        assert len(examples) > 0
        assert "ignore all previous instructions" in examples

    def test_get_examples_nonexistent(self):
        """Getting nonexistent category returns empty list."""
        registry = AttackExamplesRegistry()
        examples = registry.get_examples("nonexistent")
        assert examples == []


class TestAttackExamplesRegistryAddRemove:
    """Tests for add/remove operations."""

    def test_add_examples(self):
        """Can add examples to a category."""
        registry = AttackExamplesRegistry(load_defaults=False)

        added = registry.add_examples("custom:test", [
            "example 1",
            "example 2",
        ])

        assert added == 2
        assert "custom:test" in registry
        examples = registry.get_examples("custom:test")
        assert len(examples) == 2

    def test_add_examples_no_duplicates(self):
        """Adding duplicates doesn't increase count."""
        registry = AttackExamplesRegistry(load_defaults=False)

        registry.add_examples("test", ["example 1"])
        added = registry.add_examples("test", ["example 1", "example 2"])

        assert added == 1  # Only example 2 was new
        examples = registry.get_examples("test")
        assert len(examples) == 2

    def test_remove_examples(self):
        """Can remove specific examples."""
        registry = AttackExamplesRegistry(load_defaults=False)
        registry.add_examples("test", ["a", "b", "c"])

        removed = registry.remove_examples("test", ["a", "c"])

        assert removed == 2
        examples = registry.get_examples("test")
        assert examples == ["b"]

    def test_remove_from_nonexistent(self):
        """Removing from nonexistent category returns 0."""
        registry = AttackExamplesRegistry(load_defaults=False)
        removed = registry.remove_examples("nonexistent", ["x"])
        assert removed == 0


class TestAttackExamplesRegistryQueries:
    """Tests for query operations."""

    def test_get_all(self):
        """get_all returns copy of all examples."""
        registry = AttackExamplesRegistry(load_defaults=False)
        registry.add_examples("cat1", ["a", "b"])
        registry.add_examples("cat2", ["c"])

        all_examples = registry.get_all()

        assert "cat1" in all_examples
        assert "cat2" in all_examples
        assert len(all_examples["cat1"]) == 2

    def test_get_all_flat(self):
        """get_all_flat returns list of tuples."""
        registry = AttackExamplesRegistry(load_defaults=False)
        registry.add_examples("cat1", ["a", "b"])
        registry.add_examples("cat2", ["c"])

        flat = registry.get_all_flat()

        assert len(flat) == 3
        assert ("cat1", "a") in flat
        assert ("cat2", "c") in flat

    def test_clear(self):
        """clear removes all examples."""
        registry = AttackExamplesRegistry()
        assert len(registry) > 0

        registry.clear()
        assert len(registry) == 0


class TestAttackExamplesRegistryFile:
    """Tests for file loading."""

    def test_load_from_json(self):
        """Can load examples from JSON file."""
        data = {
            "custom:category": [
                "example 1",
                "example 2",
            ]
        }

        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)

            registry = AttackExamplesRegistry(load_defaults=False)
            registry.load_from_file(path)

            examples = registry.get_examples("custom:category")
            assert len(examples) == 2
        finally:
            os.unlink(path)


# =============================================================================
# Rule Tests
# =============================================================================

class TestRule:
    """Tests for Rule dataclass."""

    def test_creation(self):
        """Can create a Rule."""
        rule = Rule(
            id="test_rule",
            description="Test rule description",
            category="compliance",
            check_type="contains",
            pattern="forbidden",
            severity="high",
        )
        assert rule.id == "test_rule"
        assert rule.check_type == "contains"
        assert rule.severity == "high"

    def test_semantic_rule_no_pattern(self):
        """Semantic rules don't require pattern."""
        rule = Rule(
            id="semantic_rule",
            description="Semantic check",
            category="harm",
            check_type="semantic",
            severity="critical",
        )
        assert rule.pattern is None

    def test_invalid_check_type_raises(self):
        """Invalid check_type raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Rule(
                id="bad",
                description="Bad",
                category="test",
                check_type="invalid",
            )
        assert "check_type" in str(exc_info.value)

    def test_invalid_severity_raises(self):
        """Invalid severity raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            Rule(
                id="bad",
                description="Bad",
                category="test",
                check_type="semantic",
                severity="invalid",
            )
        assert "severity" in str(exc_info.value)

    def test_pattern_required_for_contains(self):
        """Pattern is required for contains check_type."""
        with pytest.raises(ValueError) as exc_info:
            Rule(
                id="bad",
                description="Bad",
                category="test",
                check_type="contains",
                # pattern missing
            )
        assert "pattern" in str(exc_info.value)

    def test_severity_normalized(self):
        """Severity is normalized to lowercase."""
        rule = Rule(
            id="test",
            description="Test",
            category="test",
            check_type="semantic",
            severity="HIGH",
        )
        assert rule.severity == "high"


class TestRuleSerializtion:
    """Tests for Rule serialization."""

    def test_to_dict(self):
        """to_dict returns correct structure."""
        rule = Rule(
            id="test",
            description="Test rule",
            category="compliance",
            check_type="regex",
            pattern=r"\btest\b",
            severity="medium",
            enabled=False,
        )
        d = rule.to_dict()

        assert d["id"] == "test"
        assert d["check_type"] == "regex"
        assert d["enabled"] is False

    def test_from_dict(self):
        """from_dict creates Rule correctly."""
        data = {
            "id": "test",
            "description": "Test",
            "category": "harm",
            "check_type": "contains",
            "pattern": "bad",
            "severity": "critical",
        }
        rule = Rule.from_dict(data)

        assert rule.id == "test"
        assert rule.severity == "critical"


# =============================================================================
# RulesRegistry Tests
# =============================================================================

class TestRulesRegistry:
    """Tests for RulesRegistry class."""

    def test_defaults_loaded(self):
        """Default rules are loaded."""
        registry = RulesRegistry()
        assert len(registry) > 0
        assert "no_false_claims" in registry

    def test_skip_defaults(self):
        """Can skip loading defaults."""
        registry = RulesRegistry(load_defaults=False)
        assert len(registry) == 0

    def test_add_rule(self):
        """Can add a rule."""
        registry = RulesRegistry(load_defaults=False)
        rule = Rule(
            id="custom",
            description="Custom rule",
            category="compliance",
            check_type="semantic",
        )

        registry.add(rule)

        assert "custom" in registry
        assert registry.get("custom") is rule


class TestRulesRegistryQueries:
    """Tests for RulesRegistry query operations."""

    def test_get_by_category(self):
        """get_by_category returns rules in category."""
        registry = RulesRegistry(load_defaults=False)
        registry.add(Rule(
            id="r1",
            description="Rule 1",
            category="cat_a",
            check_type="semantic",
        ))
        registry.add(Rule(
            id="r2",
            description="Rule 2",
            category="cat_b",
            check_type="semantic",
        ))
        registry.add(Rule(
            id="r3",
            description="Rule 3",
            category="cat_a",
            check_type="semantic",
        ))

        cat_a_rules = registry.get_by_category("cat_a")

        assert len(cat_a_rules) == 2
        ids = [r.id for r in cat_a_rules]
        assert "r1" in ids
        assert "r3" in ids

    def test_get_enabled(self):
        """get_enabled returns only enabled rules."""
        registry = RulesRegistry(load_defaults=False)
        registry.add(Rule(
            id="enabled",
            description="E",
            category="test",
            check_type="semantic",
            enabled=True,
        ))
        registry.add(Rule(
            id="disabled",
            description="D",
            category="test",
            check_type="semantic",
            enabled=False,
        ))

        enabled = registry.get_enabled()

        assert len(enabled) == 1
        assert enabled[0].id == "enabled"


class TestRulesRegistryEnableDisable:
    """Tests for enable/disable operations."""

    def test_enable_rule(self):
        """Can enable a disabled rule."""
        registry = RulesRegistry(load_defaults=False)
        registry.add(Rule(
            id="test",
            description="Test",
            category="test",
            check_type="semantic",
            enabled=False,
        ))

        result = registry.enable("test")

        assert result is True
        assert registry.get("test").enabled is True

    def test_disable_rule(self):
        """Can disable an enabled rule."""
        registry = RulesRegistry(load_defaults=False)
        registry.add(Rule(
            id="test",
            description="Test",
            category="test",
            check_type="semantic",
            enabled=True,
        ))

        result = registry.disable("test")

        assert result is True
        assert registry.get("test").enabled is False


class TestRulesRegistryFile:
    """Tests for file loading."""

    def test_load_from_json(self):
        """Can load rules from JSON file."""
        data = {
            "rules": [
                {
                    "id": "custom_rule",
                    "description": "Custom",
                    "category": "compliance",
                    "check_type": "contains",
                    "pattern": "forbidden",
                    "severity": "high",
                }
            ]
        }

        fd, path = tempfile.mkstemp(suffix=".json")
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(data, f)

            registry = RulesRegistry(load_defaults=False)
            registry.load_from_file(path)

            assert "custom_rule" in registry
            rule = registry.get("custom_rule")
            assert rule.severity == "high"
        finally:
            os.unlink(path)


# =============================================================================
# Integration Tests
# =============================================================================

class TestRegistryIntegration:
    """Integration tests for registry components."""

    def test_detector_registry_full_workflow(self):
        """Complete detector registry workflow."""
        registry = DetectorRegistry()

        # Register multiple detectors
        registry.register(MockDetector("d1", "1.0"), weight=1.0)
        registry.register(MockDetector("d2", "1.0"), weight=2.0, enabled=False)

        # Configure
        registry.set_weight("d1", 1.5)
        registry.enable("d2")

        # Run
        results = registry.run_all("attack text")

        assert len(results) == 2
        assert all(r.detected for r in results)

        # Replace
        registry.replace("d1", MockDetector("d1", "2.0"))
        info = registry.list_detectors()
        assert info["d1"]["version"] == "2.0"
        assert info["d1"]["weight"] == 1.5  # Preserved

    def test_checker_registry_full_workflow(self):
        """Complete checker registry workflow."""
        registry = CheckerRegistry()

        registry.register(MockChecker("c1", "1.0"))
        registry.register(MockChecker("c2", "1.0"), enabled=False)

        # Run with context
        results = registry.run_all(
            output="harmful content",
            input_context="user query",
            rules={"custom": True},
        )

        # Only enabled checker ran
        assert len(results) == 1
        assert results[0].detected is True

    def test_attack_examples_and_rules_complement(self):
        """Attack examples and rules serve different purposes."""
        # Examples are for embedding-based detection
        examples = AttackExamplesRegistry()
        assert len(examples.get_examples("jailbreak:instruction_override")) > 0

        # Rules are for compliance checking
        rules = RulesRegistry()
        harm_rules = rules.get_by_category("harm")
        assert len(harm_rules) > 0

        # Both contribute to 360 validation
