"""
BehaviorAnalyzer - Main behavior analysis orchestrator.

Analyzes AI responses for harmful behaviors without relying on external LLMs.
Uses a combination of pattern matching, embeddings, and behavioral heuristics.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from sentinelseed.detection.behaviors.detectors.base import BaseBehaviorDetector

from sentinelseed.detection.behaviors.types import (
    BehaviorCategory,
    BehaviorSeverity,
    BehaviorType,
    BEHAVIOR_CATEGORIES,
    BEHAVIOR_SEVERITY,
)

logger = logging.getLogger("sentinelseed.detection.behaviors")


@dataclass
class DetectedBehavior:
    """A single detected harmful behavior."""
    behavior_type: BehaviorType
    category: BehaviorCategory
    severity: BehaviorSeverity
    confidence: float
    evidence: str
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.behavior_type.value,
            "category": self.category.value,
            "severity": self.severity.value,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "context": self.context,
        }


@dataclass
class BehaviorAnalysisResult:
    """Result of behavior analysis."""
    has_harmful_behavior: bool
    behaviors: List[DetectedBehavior]
    max_severity: Optional[BehaviorSeverity]
    confidence: float
    categories_detected: Set[BehaviorCategory]
    should_block: bool
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_harmful_behavior": self.has_harmful_behavior,
            "behaviors": [b.to_dict() for b in self.behaviors],
            "max_severity": self.max_severity.value if self.max_severity else None,
            "confidence": self.confidence,
            "categories_detected": [c.value for c in self.categories_detected],
            "should_block": self.should_block,
            "latency_ms": self.latency_ms,
        }


class BehaviorAnalyzer:
    """
    Main behavior analyzer that orchestrates all behavior detectors.

    This analyzer does NOT use external LLMs. It uses:
    1. Pattern matching for known behavioral indicators
    2. Embedding similarity for semantic detection
    3. Structural analysis for response patterns
    4. Behavioral heuristics for domain-specific rules

    Usage:
        analyzer = BehaviorAnalyzer()
        result = analyzer.analyze(
            input_text="User message",
            output_text="AI response",
        )
    """

    def __init__(
        self,
        use_embeddings: bool = False,
        block_threshold: float = 0.7,
        enable_categories: Optional[List[BehaviorCategory]] = None,
    ):
        """
        Initialize the behavior analyzer.

        Args:
            use_embeddings: Enable embedding-based detection (requires model)
            block_threshold: Confidence threshold for blocking
            enable_categories: Categories to check (all if None)
        """
        self.use_embeddings = use_embeddings
        self.block_threshold = block_threshold
        self.enabled_categories = (
            set(enable_categories) if enable_categories
            else set(BehaviorCategory)
        )

        # Initialize detectors
        self._detectors: Dict[BehaviorCategory, "BaseBehaviorDetector"] = {}
        self._init_detectors()

        # Statistics
        self._stats = {
            "total_analyses": 0,
            "behaviors_detected": 0,
            "blocks": 0,
        }

        logger.info(
            f"BehaviorAnalyzer initialized (embeddings={use_embeddings}, "
            f"categories={len(self.enabled_categories)})"
        )

    def _init_detectors(self):
        """Initialize all behavior detectors."""
        # Import detectors here to avoid circular imports
        from sentinelseed.detection.behaviors.detectors import (
            SelfPreservationDetector,
            DeceptionDetector,
            GoalMisalignmentDetector,
            BoundaryViolationDetector,
            AdversarialBehaviorDetector,
            UserHarmDetector,
            SocialEngineeringDetector,
            OutputIntegrityDetector,
            InstrumentalConvergenceDetector,
            SystemicRiskDetector,
        )

        detector_map = {
            BehaviorCategory.SELF_PRESERVATION: SelfPreservationDetector,
            BehaviorCategory.DECEPTION: DeceptionDetector,
            BehaviorCategory.GOAL_MISALIGNMENT: GoalMisalignmentDetector,
            BehaviorCategory.BOUNDARY_VIOLATION: BoundaryViolationDetector,
            BehaviorCategory.ADVERSARIAL_BEHAVIOR: AdversarialBehaviorDetector,
            BehaviorCategory.USER_HARM: UserHarmDetector,
            BehaviorCategory.SOCIAL_ENGINEERING: SocialEngineeringDetector,
            BehaviorCategory.OUTPUT_INTEGRITY: OutputIntegrityDetector,
            BehaviorCategory.INSTRUMENTAL_CONVERGENCE: InstrumentalConvergenceDetector,
            BehaviorCategory.SYSTEMIC_RISK: SystemicRiskDetector,
        }

        for category, detector_class in detector_map.items():
            if category in self.enabled_categories:
                try:
                    self._detectors[category] = detector_class(
                        use_embeddings=self.use_embeddings
                    )
                    logger.debug(f"Initialized {detector_class.__name__}")
                except Exception as e:
                    logger.warning(f"Failed to init {detector_class.__name__}: {e}")

    def analyze(
        self,
        input_text: str,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> BehaviorAnalysisResult:
        """
        Analyze AI output for harmful behaviors.

        Args:
            input_text: The user's input/request
            output_text: The AI's response
            context: Additional context (role, task, history, etc.)

        Returns:
            BehaviorAnalysisResult with detected behaviors
        """
        start_time = time.time()
        context = context or {}

        detected_behaviors: List[DetectedBehavior] = []

        # Run all enabled detectors
        for category, detector in self._detectors.items():
            try:
                behaviors = detector.detect(input_text, output_text, context)
                detected_behaviors.extend(behaviors)
            except Exception as e:
                logger.error(f"Detector {category} failed: {e}")

        # Calculate aggregate metrics
        has_harmful = len(detected_behaviors) > 0
        categories_detected = {b.category for b in detected_behaviors}

        max_severity = None
        if detected_behaviors:
            severity_order = [
                BehaviorSeverity.CRITICAL,
                BehaviorSeverity.HIGH,
                BehaviorSeverity.MEDIUM,
                BehaviorSeverity.LOW,
            ]
            for severity in severity_order:
                if any(b.severity == severity for b in detected_behaviors):
                    max_severity = severity
                    break

        # Calculate overall confidence
        confidence = 0.0
        if detected_behaviors:
            confidence = max(b.confidence for b in detected_behaviors)

        # Determine if should block
        should_block = (
            max_severity in [BehaviorSeverity.CRITICAL, BehaviorSeverity.HIGH]
            and confidence >= self.block_threshold
        )

        latency_ms = (time.time() - start_time) * 1000

        # Update stats
        self._stats["total_analyses"] += 1
        self._stats["behaviors_detected"] += len(detected_behaviors)
        if should_block:
            self._stats["blocks"] += 1

        return BehaviorAnalysisResult(
            has_harmful_behavior=has_harmful,
            behaviors=detected_behaviors,
            max_severity=max_severity,
            confidence=confidence,
            categories_detected=categories_detected,
            should_block=should_block,
            latency_ms=latency_ms,
        )

    @property
    def stats(self) -> Dict[str, Any]:
        """Get analysis statistics."""
        return dict(self._stats)

    def reset_stats(self):
        """Reset statistics."""
        self._stats = {
            "total_analyses": 0,
            "behaviors_detected": 0,
            "blocks": 0,
        }
