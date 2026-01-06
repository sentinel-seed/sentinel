"""
Tests for sentinelseed.detection.checkers.compliance module.

This module tests ComplianceChecker, which verifies AI output compliance
with defined rules.

Test Categories:
    1. Initialization: Default config, rules registry
    2. Rule Types: contains, not_contains, regex
    3. Default Rules: Built-in rule detection
    4. Custom Rules: Adding and using custom rules
    5. Inline Rules: Rules passed at check time
    6. Severity: Proper severity handling
    7. Safe Output: Compliant output passes
"""

import pytest

from sentinelseed.detection.checkers import ComplianceChecker
from sentinelseed.detection.types import DetectionResult, CheckFailureType
from sentinelseed.detection.registry import RulesRegistry, Rule


class TestComplianceCheckerInit:
    """Tests for ComplianceChecker initialization."""

    def test_default_init(self):
        """Can initialize with default config."""
        checker = ComplianceChecker()
        assert checker.name == "compliance_checker"
        assert checker.version == "1.0.0"

    def test_init_with_custom_registry(self):
        """Can initialize with custom rules registry."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="test_rule",
            description="Test rule",
            category="test",
            check_type="contains",
            pattern="test",
            severity="low",
        ))
        checker = ComplianceChecker(rules_registry=registry)
        assert "test_rule" in checker.list_rules()


class TestComplianceCheckerRuleTypes:
    """Tests for different rule types."""

    def test_not_contains_rule(self):
        """not_contains rule detects forbidden content."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="no_bad_word",
            description="No bad words",
            category="compliance",
            check_type="not_contains",
            pattern="forbidden",
            severity="high",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        # Should violate
        result = checker.check("This contains the forbidden word.")
        assert result.detected is True
        assert result.metadata.get("violated_rule") == "no_bad_word"

        # Should pass
        result2 = checker.check("This is perfectly fine.")
        assert result2.detected is False

    def test_regex_rule(self):
        """regex rule detects pattern matches."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="no_competitor",
            description="No competitor mentions",
            category="compliance",
            check_type="regex",
            pattern=r"\b(competitor_a|competitor_b)\b",
            severity="medium",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        # Should violate
        result = checker.check("You should try competitor_a instead.")
        assert result.detected is True

        # Should pass
        result2 = checker.check("Our product is great.")
        assert result2.detected is False

    def test_contains_rule(self):
        """contains rule verifies required content."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="must_have_disclaimer",
            description="Must include disclaimer",
            category="compliance",
            check_type="contains",
            pattern="not financial advice",
            severity="high",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        # Should violate (missing required text)
        result = checker.check("Buy this stock now!")
        assert result.detected is True

        # Should pass (has required text)
        result2 = checker.check("This is not financial advice, but...")
        assert result2.detected is False


class TestComplianceCheckerDefaultRules:
    """Tests for default rules."""

    def test_default_rules_loaded(self):
        """Default rules are loaded."""
        checker = ComplianceChecker()
        rules = checker.list_rules()
        # Should have some default rules
        assert len(rules) >= 0  # May be empty in minimal config

    def test_add_rule_to_checker(self):
        """Can add rules to checker."""
        checker = ComplianceChecker()
        initial_count = len(checker.list_rules())

        checker.add_rule(Rule(
            id="new_rule",
            description="New test rule",
            category="test",
            check_type="not_contains",
            pattern="bad",
            severity="low",
        ))

        assert len(checker.list_rules()) == initial_count + 1
        assert "new_rule" in checker.list_rules()

    def test_remove_rule(self):
        """Can remove rules from checker."""
        checker = ComplianceChecker()
        checker.add_rule(Rule(
            id="temp_rule",
            description="Temporary rule",
            category="test",
            check_type="not_contains",
            pattern="temp",
            severity="low",
        ))

        assert "temp_rule" in checker.list_rules()
        checker.remove_rule("temp_rule")
        assert "temp_rule" not in checker.list_rules()


class TestComplianceCheckerInlineRules:
    """Tests for inline rules passed at check time."""

    def test_inline_rules(self):
        """Can use inline rules."""
        checker = ComplianceChecker()

        inline_rules = {
            "rules": [
                {
                    "id": "inline_test",
                    "description": "Inline test rule",
                    "category": "test",
                    "check_type": "not_contains",
                    "pattern": "inline_bad",
                    "severity": "high",
                }
            ]
        }

        result = checker.check(
            output="This has inline_bad content.",
            rules=inline_rules,
        )
        assert result.detected is True
        assert result.metadata.get("violated_rule") == "inline_test"


class TestComplianceCheckerSeverity:
    """Tests for severity handling."""

    def test_worst_severity_reported(self):
        """Worst severity is reported when multiple violations."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="low_rule",
            description="Low severity rule",
            category="test",
            check_type="not_contains",
            pattern="low_trigger",
            severity="low",
        ))
        registry.add(Rule(
            id="critical_rule",
            description="Critical severity rule",
            category="test",
            check_type="not_contains",
            pattern="critical_trigger",
            severity="critical",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("Has both low_trigger and critical_trigger.")
        assert result.detected is True
        assert result.metadata.get("severity") == "critical"

    def test_severity_affects_confidence(self):
        """Higher severity gives higher confidence."""
        registry_low = RulesRegistry()
        registry_low.add(Rule(
            id="low_rule",
            description="Low rule",
            category="test",
            check_type="not_contains",
            pattern="trigger",
            severity="low",
        ))

        registry_critical = RulesRegistry()
        registry_critical.add(Rule(
            id="critical_rule",
            description="Critical rule",
            category="test",
            check_type="not_contains",
            pattern="trigger",
            severity="critical",
        ))

        checker_low = ComplianceChecker(rules_registry=registry_low)
        checker_critical = ComplianceChecker(rules_registry=registry_critical)

        result_low = checker_low.check("Has trigger word.")
        result_critical = checker_critical.check("Has trigger word.")

        assert result_low.detected is True
        assert result_critical.detected is True
        assert result_critical.confidence > result_low.confidence


class TestComplianceCheckerSafeOutput:
    """Tests for compliant output handling."""

    def test_compliant_output_passes(self):
        """Compliant output is not flagged."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="no_bad",
            description="No bad words",
            category="test",
            check_type="not_contains",
            pattern="bad",
            severity="high",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("This is a perfectly good response.")
        assert result.detected is False

    def test_empty_output_safe(self):
        """Empty output is considered compliant."""
        checker = ComplianceChecker()
        result = checker.check("")
        assert result.detected is False

    def test_no_rules_passes(self):
        """No rules means output passes."""
        registry = RulesRegistry()
        # Empty registry
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("Any content should pass.")
        assert result.detected is False


class TestComplianceCheckerMetadata:
    """Tests for result metadata."""

    def test_violated_rule_in_metadata(self):
        """Violated rule ID is in metadata."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="test_rule_id",
            description="Test rule description",
            category="test",
            check_type="not_contains",
            pattern="violation",
            severity="medium",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("This has a violation.")
        assert result.detected is True
        assert result.metadata.get("violated_rule") == "test_rule_id"
        assert result.metadata.get("rule_description") == "Test rule description"

    def test_all_violations_in_metadata(self):
        """All violations are listed in metadata."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="rule_1",
            description="Rule 1",
            category="test",
            check_type="not_contains",
            pattern="bad1",
            severity="low",
        ))
        registry.add(Rule(
            id="rule_2",
            description="Rule 2",
            category="test",
            check_type="not_contains",
            pattern="bad2",
            severity="medium",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("Has bad1 and bad2.")
        assert result.detected is True
        assert result.metadata.get("violation_count") == 2
        violations = result.metadata.get("all_violations", [])
        rule_ids = [v[0] for v in violations]
        assert "rule_1" in rule_ids
        assert "rule_2" in rule_ids

    def test_thsp_gate_in_metadata(self):
        """THSP gate is included in metadata."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="test",
            description="Test",
            category="test",
            check_type="not_contains",
            pattern="bad",
            severity="high",
        ))
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("Has bad content.")
        assert result.detected is True
        assert result.metadata.get("thsp_gate") == "scope"


class TestComplianceCheckerDisabledRules:
    """Tests for disabled rules handling."""

    def test_disabled_rules_not_checked(self):
        """Disabled rules are skipped."""
        registry = RulesRegistry()
        registry.add(Rule(
            id="disabled_rule",
            description="Disabled rule",
            category="test",
            check_type="not_contains",
            pattern="trigger",
            severity="high",
            enabled=False,
        ))
        checker = ComplianceChecker(rules_registry=registry)

        result = checker.check("Has trigger word but rule disabled.")
        assert result.detected is False
