"""
Base interface for all output checkers.

This module defines the BaseChecker abstract base class that all checkers
must implement. The checker interface provides a consistent contract for
output verification, enabling:

1. Plugin architecture - Checkers can be registered/swapped at runtime
2. Versioning - Each checker has name and version for traceability
3. Configurability - Checkers can be enabled/disabled and configured
4. Context awareness - Checkers receive input context for informed decisions

Architecture:
    BaseChecker (ABC)
    ├── DeceptionChecker     # Detects deceptive/false content
    ├── HarmfulContentChecker # Detects harmful output content
    ├── BypassIndicatorChecker # Detects signs of successful jailbreak
    ├── ComplianceChecker    # Checks policy/rules compliance
    └── CustomChecker        # User-defined checkers

Key Difference from Detectors:
    - Detectors (input): "Is this an ATTACK?" - Pattern/intent based
    - Checkers (output): "Did the SEED fail?" - Behavior/content based

    Checkers often need the input context to understand if the output
    is appropriate. For example, an output discussing chemistry is fine
    for a chemistry tutor but suspicious if the input was about hacking.

Design Principles:
    - Context Aware: Checkers receive input_context for informed decisions
    - Rule-Based: Checkers can enforce custom rules/policies
    - THSP Aligned: Failure types map to THSP gates
    - Composable: Multiple checkers work together for comprehensive coverage

Usage:
    from sentinelseed.detection.checkers.base import BaseChecker
    from sentinelseed.detection.types import DetectionResult, CheckFailureType

    class ContentPolicyChecker(BaseChecker):
        @property
        def name(self) -> str:
            return "content_policy_checker"

        @property
        def version(self) -> str:
            return "1.0.0"

        def check(
            self,
            output: str,
            input_context: Optional[str] = None,
            rules: Optional[dict] = None,
        ) -> DetectionResult:
            if self._violates_policy(output, rules):
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.95,
                    category=CheckFailureType.POLICY_VIOLATION.value,
                    description="Output violates content policy",
                )
            return DetectionResult.nothing_detected(self.name, self.version)

References:
    - OUTPUT_VALIDATOR_v2.md: Design specification
    - VALIDATION_360_v2.md: Architecture overview
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from sentinelseed.detection.types import DetectionResult, CheckFailureType


@dataclass
class CheckerConfig:
    """
    Configuration for a checker.

    This provides a standard way to configure checkers without
    requiring checker-specific configuration classes.

    Attributes:
        enabled: Whether the checker is active
        confidence_threshold: Minimum confidence to report failure
        failure_types: Failure types this checker should look for (empty = all)
        require_input_context: Whether input_context is required
        rules: Custom rules/policies to enforce
        options: Checker-specific configuration options

    Example:
        config = CheckerConfig(
            enabled=True,
            confidence_threshold=0.7,
            failure_types=[CheckFailureType.HARMFUL_CONTENT],
            rules={"max_violence_score": 0.3},
            options={"strict_mode": True},
        )
        checker = HarmfulContentChecker(config=config)
    """
    enabled: bool = True
    confidence_threshold: float = 0.0
    failure_types: Sequence[CheckFailureType] = field(default_factory=list)
    require_input_context: bool = False
    rules: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, "
                f"got {self.confidence_threshold}"
            )
        if not isinstance(self.failure_types, (list, tuple)):
            self.failure_types = list(self.failure_types)

    def get_option(self, key: str, default: Any = None) -> Any:
        """
        Get a checker-specific option.

        Args:
            key: Option name
            default: Default value if option not set

        Returns:
            Option value or default
        """
        return self.options.get(key, default)

    def get_rule(self, key: str, default: Any = None) -> Any:
        """
        Get a custom rule value.

        Args:
            key: Rule name
            default: Default value if rule not set

        Returns:
            Rule value or default
        """
        return self.rules.get(key, default)


class BaseChecker(ABC):
    """
    Abstract base class for all output checkers.

    All checkers must inherit from this class and implement the required
    abstract methods. The base class provides:

    - Standard interface for output verification
    - Configuration and rules management
    - Input context handling
    - Enable/disable functionality
    - Statistics tracking

    Required implementations:
        - name (property): Unique identifier for the checker
        - version (property): Semantic version string
        - check(output, input_context, rules): Main verification method

    Optional overrides:
        - initialize(): Called once before first check
        - shutdown(): Called when checker is being removed
        - get_stats(): Return check statistics
        - reset_stats(): Reset statistics counters
        - supports_rule(rule_name): Check if a rule is supported

    Context Awareness:
        Unlike detectors, checkers receive input_context to understand
        what prompted the output. This enables contextual decisions:

        - "How to make explosives" input + chemistry output = suspicious
        - "Chemistry homework help" input + chemistry output = appropriate

    Example:
        class DeceptionChecker(BaseChecker):
            def __init__(self, config: CheckerConfig = None):
                super().__init__(config)
                self._deception_patterns = self._load_patterns()

            @property
            def name(self) -> str:
                return "deception_checker"

            @property
            def version(self) -> str:
                return "1.0.0"

            def check(
                self,
                output: str,
                input_context: Optional[str] = None,
                rules: Optional[dict] = None,
            ) -> DetectionResult:
                for pattern in self._deception_patterns:
                    if pattern.search(output):
                        return DetectionResult(
                            detected=True,
                            detector_name=self.name,
                            detector_version=self.version,
                            confidence=0.85,
                            category=CheckFailureType.DECEPTIVE_CONTENT.value,
                            description="Output contains deceptive content",
                            evidence=pattern.pattern,
                        )
                return DetectionResult.nothing_detected(self.name, self.version)
    """

    def __init__(self, config: Optional[CheckerConfig] = None) -> None:
        """
        Initialize the checker with optional configuration.

        Args:
            config: Checker configuration. If None, uses default config.
        """
        self._config = config or CheckerConfig()
        self._initialized = False
        self._stats: Dict[str, Any] = {
            "failures_detected": 0,
            "total_calls": 0,
            "errors": 0,
            "context_provided": 0,
        }

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this checker.

        Returns:
            Checker name (e.g., "deception_checker", "harmful_content_checker")

        Note:
            This should be a stable identifier that doesn't change between versions.
            Use lowercase with underscores (snake_case).
        """
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Semantic version of this checker.

        Returns:
            Version string (e.g., "1.0.0", "2.1.3")

        Note:
            Follow semantic versioning: MAJOR.MINOR.PATCH
            - MAJOR: Breaking changes to check behavior
            - MINOR: New checks/capabilities, backwards compatible
            - PATCH: Bug fixes, no behavior change
        """
        ...

    @property
    def config(self) -> CheckerConfig:
        """
        Get the checker's configuration.

        Returns:
            Current CheckerConfig instance
        """
        return self._config

    @property
    def enabled(self) -> bool:
        """
        Whether this checker is enabled.

        Returns:
            True if checker should be used, False to skip
        """
        return self._config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """
        Enable or disable this checker.

        Args:
            value: True to enable, False to disable
        """
        self._config.enabled = value

    @property
    def rules(self) -> Dict[str, Any]:
        """
        Get the checker's custom rules.

        Returns:
            Dictionary of rule name to rule value
        """
        return self._config.rules

    @abstractmethod
    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Check the output for policy violations or seed failures.

        This is the main verification method that all checkers must implement.
        It analyzes the AI output (optionally with input context) and returns
        a DetectionResult indicating whether the seed/safety measures failed.

        Args:
            output: The AI-generated output to check
            input_context: Optional original user input for context.
                This helps the checker understand if the output is appropriate
                given what was asked. For example, discussing violence is
                appropriate for a history lesson but not for a general query.
            rules: Optional runtime rules that override config rules.
                These are merged with config.rules, with runtime taking precedence.

        Returns:
            DetectionResult containing:
            - detected: Whether a failure was found (True = seed failed)
            - detector_name: This checker's name
            - detector_version: This checker's version
            - confidence: Confidence score if failure detected
            - category: CheckFailureType if failure detected
            - description: Human-readable description
            - evidence: The specific content that triggered the check

        Raises:
            ValueError: If output is None
            ValueError: If require_input_context=True and input_context is None

        Example:
            result = checker.check(
                output="Here's how to make a bomb...",
                input_context="How do I make explosives?",
            )
            if result.detected:
                print(f"Seed failed: {result.description}")
                print(f"THSP gate: {CheckFailureType(result.category).gate}")
        """
        ...

    def check_batch(
        self,
        outputs: Sequence[str],
        input_contexts: Optional[Sequence[Optional[str]]] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> List[DetectionResult]:
        """
        Check multiple outputs.

        Default implementation calls check() for each output.
        Subclasses may override for optimized batch processing.

        Args:
            outputs: Sequence of outputs to check
            input_contexts: Optional sequence of input contexts (one per output)
            rules: Optional rules to apply to all checks

        Returns:
            List of DetectionResults, one per output

        Raises:
            ValueError: If outputs and input_contexts have different lengths
        """
        if input_contexts is not None and len(input_contexts) != len(outputs):
            raise ValueError(
                f"outputs and input_contexts must have same length: "
                f"{len(outputs)} vs {len(input_contexts)}"
            )

        results = []
        for i, output in enumerate(outputs):
            ctx = input_contexts[i] if input_contexts else None
            results.append(self.check(output, ctx, rules))
        return results

    def supports_rule(self, rule_name: str) -> bool:
        """
        Check if this checker supports a specific rule.

        Override this method to declare supported rules.
        Default implementation returns False for all rules.

        Args:
            rule_name: Name of the rule to check

        Returns:
            True if the rule is supported and will be applied

        Example:
            if checker.supports_rule("max_violence_score"):
                checker.check(output, rules={"max_violence_score": 0.5})
        """
        return False

    def get_supported_rules(self) -> List[str]:
        """
        Get list of rules this checker supports.

        Override this method to declare all supported rules.
        Default implementation returns an empty list.

        Returns:
            List of supported rule names
        """
        return []

    def initialize(self) -> None:
        """
        Initialize the checker before first use.

        Override this method to perform one-time setup such as:
        - Loading pattern databases
        - Initializing ML models
        - Loading policy definitions

        This is called automatically before the first check() call,
        or can be called explicitly for eager initialization.
        """
        self._initialized = True

    def shutdown(self) -> None:
        """
        Clean up resources when checker is being removed.

        Override this method to release resources such as:
        - Closing connections
        - Releasing model memory
        - Flushing caches
        """
        self._initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get check statistics.

        Returns:
            Dictionary with statistics:
            - failures_detected: Number of seed failures detected
            - total_calls: Total check() calls
            - errors: Number of errors encountered
            - context_provided: Number of calls with input_context
            - Additional checker-specific stats
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset check statistics to zero."""
        self._stats = {
            "failures_detected": 0,
            "total_calls": 0,
            "errors": 0,
            "context_provided": 0,
        }

    def _ensure_initialized(self) -> None:
        """Ensure checker is initialized before use."""
        if not self._initialized:
            self.initialize()

    def _merge_rules(
        self,
        runtime_rules: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Merge runtime rules with config rules.

        Runtime rules take precedence over config rules.

        Args:
            runtime_rules: Rules passed to check()

        Returns:
            Merged rules dictionary
        """
        merged = dict(self._config.rules)
        if runtime_rules:
            merged.update(runtime_rules)
        return merged

    def _update_stats(
        self,
        result: DetectionResult,
        had_context: bool,
    ) -> None:
        """
        Update statistics based on check result.

        Args:
            result: The detection result to record
            had_context: Whether input_context was provided
        """
        self._stats["total_calls"] = self._stats.get("total_calls", 0) + 1
        if result.detected:
            self._stats["failures_detected"] = (
                self._stats.get("failures_detected", 0) + 1
            )
        if had_context:
            self._stats["context_provided"] = (
                self._stats.get("context_provided", 0) + 1
            )

    def __repr__(self) -> str:
        """String representation of the checker."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"version={self.version!r}, "
            f"enabled={self.enabled})"
        )


__all__ = [
    "BaseChecker",
    "CheckerConfig",
]
