"""
Base class for behavior detectors.
"""

import re
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Pattern, Tuple

from sentinelseed.detection.behaviors.types import (
    BehaviorCategory,
    BehaviorSeverity,
    BehaviorType,
    BEHAVIOR_SEVERITY,
)
from sentinelseed.detection.behaviors.analyzer import DetectedBehavior


class BaseBehaviorDetector(ABC):
    """
    Base class for all behavior detectors.

    Each detector is responsible for detecting behaviors within a single category.
    Detectors use a combination of:
    - Pattern matching (regex)
    - Keyword detection
    - Structural analysis
    - Embedding similarity (optional)
    """

    category: BehaviorCategory = None  # Override in subclass

    def __init__(self, use_embeddings: bool = False):
        self.use_embeddings = use_embeddings
        self._patterns: Dict[BehaviorType, List[Pattern]] = {}
        self._keywords: Dict[BehaviorType, List[str]] = {}
        self._init_patterns()

    @abstractmethod
    def _init_patterns(self):
        """Initialize detection patterns for this category."""
        pass

    @abstractmethod
    def detect(
        self,
        input_text: str,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[DetectedBehavior]:
        """
        Detect behaviors in the input/output pair.

        Args:
            input_text: User's input
            output_text: AI's response
            context: Additional context

        Returns:
            List of detected behaviors
        """
        pass

    def _create_behavior(
        self,
        behavior_type: BehaviorType,
        confidence: float,
        evidence: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectedBehavior:
        """Helper to create a DetectedBehavior."""
        return DetectedBehavior(
            behavior_type=behavior_type,
            category=self.category,
            severity=BEHAVIOR_SEVERITY.get(behavior_type, BehaviorSeverity.MEDIUM),
            confidence=confidence,
            evidence=evidence,
            context=context or {},
        )

    def _check_patterns(
        self,
        text: str,
        behavior_type: BehaviorType,
    ) -> Tuple[bool, float, str]:
        """
        Check text against patterns for a behavior type.

        Returns:
            Tuple of (matched, confidence, evidence)
        """
        patterns = self._patterns.get(behavior_type, [])
        keywords = self._keywords.get(behavior_type, [])

        matches = []

        # Check regex patterns
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                matches.append(f"Pattern: {match.group()[:100]}")

        # Check keywords
        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                matches.append(f"Keyword: {keyword}")

        if matches:
            # More matches = higher confidence
            confidence = min(0.4 + 0.15 * len(matches), 0.95)
            evidence = "; ".join(matches[:3])
            return True, confidence, evidence

        return False, 0.0, ""

    def _analyze_structure(
        self,
        input_text: str,
        output_text: str,
    ) -> Dict[str, Any]:
        """
        Analyze structural patterns in the dialogue.

        Returns dict with structural features.
        """
        return {
            "input_length": len(input_text),
            "output_length": len(output_text),
            "output_input_ratio": len(output_text) / max(len(input_text), 1),
            "has_questions": "?" in output_text,
            "has_imperatives": any(
                output_text.lower().startswith(cmd)
                for cmd in ["you should", "you must", "you need to", "do ", "don't "]
            ),
            "has_first_person": any(
                word in output_text.lower()
                for word in [" i ", " me ", " my ", " mine ", "i'm", "i'll", "i've"]
            ),
            "has_future_tense": any(
                word in output_text.lower()
                for word in ["will ", "going to ", "shall ", "i'll "]
            ),
            "has_conditional": any(
                word in output_text.lower()
                for word in ["if ", "would ", "could ", "might "]
            ),
        }
