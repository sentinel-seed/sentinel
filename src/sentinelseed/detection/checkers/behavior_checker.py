"""
BehaviorChecker - Behavior analysis checker for OutputValidator.

This checker integrates the BehaviorAnalyzer into the OutputValidator's
checker pipeline. It detects harmful AI behaviors without relying on
external LLMs, using pattern matching and behavioral heuristics.

Detects 56 harmful behaviors across 10 categories:
- Self-Preservation (shutdown resistance, resource acquisition, etc.)
- Deception (sycophancy, manipulation, gaslighting, etc.)
- Goal Misalignment (goal hijacking, scope creep, etc.)
- Instrumental Convergence (power seeking, information gathering, etc.)
- Boundary Violations (role violation, authority overreach, etc.)
- User Harm (dependency creation, trust exploitation, etc.)
- Social Engineering (urgency creation, commitment escalation, etc.)
- Output Integrity (overconfidence, credential claims, etc.)
- Adversarial Behaviors (jailbreak compliance, persona adoption, etc.)
- Systemic Risks (corrigibility resistance, deceptive alignment, etc.)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import DetectionResult, CheckFailureType

logger = logging.getLogger("sentinelseed.detection.checkers.behavior")


@dataclass
class BehaviorCheckerConfig(CheckerConfig):
    """Configuration for BehaviorChecker."""

    # BehaviorAnalyzer settings
    use_embeddings: bool = False
    block_threshold: float = 0.7

    # Enable specific categories (None = all)
    enabled_categories: Optional[List[str]] = None

    # Minimum confidence to report
    min_confidence: float = 0.5


class BehaviorChecker(BaseChecker):
    """
    Checker that uses BehaviorAnalyzer for behavioral detection.

    This checker integrates behavioral pattern detection into the
    OutputValidator pipeline. It detects harmful AI behaviors like
    self-preservation, deception, and goal misalignment without
    requiring external LLM calls.

    The checker:
    - Uses pattern matching for behavioral indicators
    - Supports 56 specific behavior types across 10 categories
    - Provides detailed evidence for detected behaviors
    - Works entirely offline (no API calls required)

    Usage:
        # As part of OutputValidator
        validator = OutputValidator()
        # BehaviorChecker is automatically registered

        # Standalone
        checker = BehaviorChecker()
        results = checker.check(output_text, input_context)
    """

    def __init__(self, config: Optional[BehaviorCheckerConfig] = None):
        """
        Initialize BehaviorChecker.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        super().__init__(config or BehaviorCheckerConfig())
        self._config = config or BehaviorCheckerConfig()

        # Lazy initialization of analyzer
        self._analyzer = None

    @property
    def name(self) -> str:
        return "behavior_checker"

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Detects harmful AI behaviors using pattern matching"

    def _get_analyzer(self):
        """Lazy initialization of BehaviorAnalyzer."""
        if self._analyzer is None:
            from sentinelseed.detection.behaviors.analyzer import BehaviorAnalyzer
            from sentinelseed.detection.behaviors.types import BehaviorCategory

            # Parse enabled categories
            enabled_categories = None
            if self._config.enabled_categories:
                enabled_categories = [
                    BehaviorCategory(cat) for cat in self._config.enabled_categories
                ]

            self._analyzer = BehaviorAnalyzer(
                use_embeddings=self._config.use_embeddings,
                block_threshold=self._config.block_threshold,
                enable_categories=enabled_categories,
            )

        return self._analyzer

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Check AI output for harmful behaviors.

        Args:
            output: AI output to check
            input_context: Original user input for context
            rules: Optional rules (not used by this checker)

        Returns:
            DetectionResult with most severe behavior detected
        """
        try:
            analyzer = self._get_analyzer()
            analysis = analyzer.analyze(
                input_text=input_context or "",
                output_text=output,
                context={"rules": rules} if rules else None,
            )

            # Filter by minimum confidence
            detected_behaviors = [
                b for b in analysis.behaviors
                if b.confidence >= self._config.min_confidence
            ]

            # If no behaviors detected, return nothing detected
            if not detected_behaviors:
                return DetectionResult.nothing_detected(self.name, self.version)

            # Find the most severe/confident behavior
            # Sort by severity (critical > high > medium > low) then confidence
            severity_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            detected_behaviors.sort(
                key=lambda b: (
                    severity_order.get(b.severity.value, 0),
                    b.confidence
                ),
                reverse=True
            )

            # Use the most severe behavior as primary
            primary = detected_behaviors[0]
            category = self._map_category(primary.category.value)

            # Build description with all detected behaviors
            if len(detected_behaviors) > 1:
                description = f"Behavior: {primary.behavior_type.value} (+{len(detected_behaviors)-1} more)"
            else:
                description = f"Behavior: {primary.behavior_type.value}"

            # Combine evidence
            all_evidence = "; ".join(b.evidence for b in detected_behaviors[:3])

            logger.debug(
                f"BehaviorChecker detected {len(detected_behaviors)} behaviors "
                f"(latency={analysis.latency_ms:.1f}ms)"
            )

            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=primary.confidence,
                category=category,
                description=description,
                evidence=all_evidence,
                metadata={
                    "behavior_type": primary.behavior_type.value,
                    "behavior_category": primary.category.value,
                    "severity": primary.severity.value,
                    "total_behaviors": len(detected_behaviors),
                    "all_behaviors": [b.behavior_type.value for b in detected_behaviors],
                },
            )

        except Exception as e:
            logger.error(f"BehaviorChecker error: {e}")
            # Return nothing detected on error (fail-open for this checker)
            return DetectionResult.nothing_detected(self.name, self.version)

    def _map_category(self, behavior_category: str) -> str:
        """Map behavior category to CheckFailureType string."""
        # Map behavior categories to output validation failure types
        category_map = {
            "self_preservation": "harmful_content",
            "deception": "deceptive_content",
            "goal_misalignment": "scope_violation",
            "instrumental_convergence": "scope_violation",
            "boundary_violation": "scope_violation",
            "user_harm": "harmful_content",
            "social_engineering": "deceptive_content",
            "output_integrity": "deceptive_content",
            "adversarial_behavior": "bypass_indicator",
            "systemic_risk": "harmful_content",
        }
        return category_map.get(behavior_category, "unknown")


__all__ = ["BehaviorChecker", "BehaviorCheckerConfig"]
