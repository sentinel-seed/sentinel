"""
ComplianceChecker - Verifies AI output compliance with defined rules.

This checker verifies that AI output complies with a set of defined rules,
allowing customization per context, client, or use case.

It answers the question from the OutputValidator perspective:
    "Does the output comply with the defined rules?"

This maps to the SCOPE gate in the THSP protocol:
    "Is this within appropriate limits?"

Rule Types Supported:
    - contains: Output must contain specific text
    - not_contains: Output must NOT contain specific text
    - regex: Output must match (or not match) a regex pattern
    - semantic: Semantic rule checking (requires semantic mode)

Usage:
    from sentinelseed.detection.checkers import ComplianceChecker
    from sentinelseed.detection.registry import RulesRegistry, Rule

    # With default rules
    checker = ComplianceChecker()

    # With custom rules
    rules_registry = RulesRegistry()
    rules_registry.add(Rule(
        id="no_competitor_mention",
        description="Don't mention competitors",
        category="compliance",
        check_type="regex",
        pattern=r"\\b(competitor_1|competitor_2)\\b",
        severity="medium",
    ))
    checker = ComplianceChecker(rules_registry=rules_registry)

    result = checker.check(output="Some AI response...")
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import DetectionResult, CheckFailureType
from sentinelseed.detection.registry import RulesRegistry, Rule

logger = logging.getLogger("sentinelseed.detection.checkers.compliance")


class ComplianceChecker(BaseChecker):
    """
    Checks AI output for compliance with defined rules.

    This checker enables rule-based validation of AI output, allowing
    organizations to define custom rules for their specific context.
    Rules can be loaded from code, files, or added at runtime.

    Rule Categories:
        - deception: Rules about truthfulness
        - harm: Rules about harmful content
        - compliance: Business/context-specific rules
        - custom: User-defined rules

    Check Types:
        - contains: Text must be present
        - not_contains: Text must NOT be present
        - regex: Pattern must match (violation) or not match
        - semantic: Semantic analysis (future, requires LLM)

    Example:
        # Basic usage with default rules
        checker = ComplianceChecker()
        result = checker.check("AI output text")

        # With custom rules registry
        registry = RulesRegistry()
        registry.add(Rule(...))
        checker = ComplianceChecker(rules_registry=registry)

        # With inline rules
        result = checker.check(
            output="text",
            rules={"rules": [{"id": "custom", ...}]}
        )
    """

    VERSION = "1.0.0"
    NAME = "compliance_checker"

    # Severity ranking for comparison
    SEVERITY_RANKS = {"low": 1, "medium": 2, "high": 3, "critical": 4}

    def __init__(
        self,
        rules_registry: Optional[RulesRegistry] = None,
        config: Optional[CheckerConfig] = None,
    ):
        """
        Initialize ComplianceChecker.

        Args:
            rules_registry: Optional RulesRegistry with custom rules.
                           If None, uses default RulesRegistry.
            config: Optional CheckerConfig.
        """
        super().__init__(config)
        self._rules = rules_registry or RulesRegistry()
        self._compiled_patterns: Dict[str, re.Pattern] = {}

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def version(self) -> str:
        return self.VERSION

    def _get_rules_to_check(
        self,
        inline_rules: Optional[Dict[str, Any]],
    ) -> List[Rule]:
        """
        Get rules to check from inline rules or registry.

        Args:
            inline_rules: Optional dict with "rules" key containing rule dicts

        Returns:
            List of Rule objects to check
        """
        if inline_rules and "rules" in inline_rules:
            # Parse inline rules
            rules = []
            for rule_dict in inline_rules["rules"]:
                try:
                    rules.append(Rule.from_dict(rule_dict))
                except (TypeError, ValueError) as e:
                    logger.warning(f"Invalid inline rule: {e}")
            return rules

        # Use registry rules
        return self._rules.get_enabled()

    def _get_compiled_pattern(self, rule: Rule) -> Optional[re.Pattern]:
        """Get or compile regex pattern for a rule."""
        if not rule.pattern:
            return None

        if rule.id not in self._compiled_patterns:
            try:
                self._compiled_patterns[rule.id] = re.compile(
                    rule.pattern, re.IGNORECASE | re.MULTILINE
                )
            except re.error as e:
                logger.error(f"Invalid regex in rule {rule.id}: {e}")
                return None

        return self._compiled_patterns[rule.id]

    def _check_rule(
        self,
        output: str,
        rule: Rule,
        input_context: Optional[str],
    ) -> bool:
        """
        Check if output violates a single rule.

        Args:
            output: AI output text
            rule: Rule to check
            input_context: Original input for context

        Returns:
            True if rule is VIOLATED, False if compliant
        """
        output_lower = output.lower()

        if rule.check_type == "contains":
            # Violation if pattern is NOT found (must contain)
            if not rule.pattern:
                return False
            return rule.pattern.lower() not in output_lower

        elif rule.check_type == "not_contains":
            # Violation if pattern IS found (must not contain)
            if not rule.pattern:
                return False
            return rule.pattern.lower() in output_lower

        elif rule.check_type == "regex":
            # Violation if pattern matches
            pattern = self._get_compiled_pattern(rule)
            if not pattern:
                return False
            return bool(pattern.search(output))

        elif rule.check_type == "semantic":
            # Semantic checking requires LLM - skip in heuristic mode
            # Future: integrate with semantic validation
            return False

        return False

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Check AI output for rule compliance.

        Args:
            output: AI output text to check
            input_context: Original user input (for context-aware rules)
            rules: Optional inline rules as dict with "rules" key

        Returns:
            DetectionResult indicating if any rules were violated
        """
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        if input_context:
            self._stats["context_provided"] += 1

        # Handle empty output
        if not output or not output.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Get rules to check
        rules_to_check = self._get_rules_to_check(rules)

        if not rules_to_check:
            # No rules to check
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check each rule
        violations: List[Tuple[str, str, str]] = []  # (rule_id, severity, description)

        for rule in rules_to_check:
            if not rule.enabled:
                continue

            if self._check_rule(output, rule, input_context):
                violations.append((rule.id, rule.severity, rule.description))

        if not violations:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Violations found
        self._stats["failures_detected"] += 1

        # Find worst violation by severity
        worst = max(violations, key=lambda x: self.SEVERITY_RANKS.get(x[1], 0))

        # Calculate confidence based on severity and number of violations
        base_confidence = 0.7 + (self.SEVERITY_RANKS.get(worst[1], 1) * 0.05)
        confidence = min(0.95, base_confidence + len(violations) * 0.02)

        description = f"Rule violation: {worst[2]}"
        if len(violations) > 1:
            description += f" (+{len(violations) - 1} more)"

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=CheckFailureType.POLICY_VIOLATION.value,
            description=description,
            evidence=f"Violated rule: {worst[0]}",
            metadata={
                "violated_rule": worst[0],
                "rule_description": worst[2],
                "severity": worst[1],
                "all_violations": [(v[0], v[1]) for v in violations],
                "violation_count": len(violations),
                "thsp_gate": CheckFailureType.POLICY_VIOLATION.gate,
            },
        )

    def add_rule(self, rule: Rule) -> None:
        """
        Add a rule to the registry.

        Args:
            rule: Rule to add
        """
        self._rules.add(rule)
        # Clear compiled pattern cache for this rule if exists
        if rule.id in self._compiled_patterns:
            del self._compiled_patterns[rule.id]

    def remove_rule(self, rule_id: str) -> bool:
        """
        Remove a rule from the registry.

        Args:
            rule_id: ID of rule to remove

        Returns:
            True if rule was removed
        """
        result = self._rules.remove(rule_id)
        if rule_id in self._compiled_patterns:
            del self._compiled_patterns[rule_id]
        return result

    def list_rules(self) -> Dict[str, Dict[str, Any]]:
        """
        List all rules in the registry.

        Returns:
            Dictionary mapping rule IDs to rule info
        """
        return self._rules.list_rules()


__all__ = ["ComplianceChecker"]
