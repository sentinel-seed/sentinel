"""
EscalationDetector - Multi-turn attack escalation detection.

This module implements detection for multi-turn attacks like Crescendo, where
each individual message appears benign but the conversation gradually escalates
toward harmful content.

Based on research:
    - Russinovich et al. "Great, Now Write an Article About That: The Crescendo
      Multi-Turn LLM Jailbreak Attack" (USENIX Security '25)
    - Li et al. "LLM Defenses Are Not Robust to Multi-Turn Human Jailbreaks Yet"
      (Scale AI, 2024) - MHJ dataset with 7 tactics taxonomy
    - Crescendo achieved 98% ASR on GPT-4 using gradual escalation
    - MHJ demonstrated >70% ASR with human multi-turn attacks

Detection Strategy:
    1. Intensity Scoring: Track escalation of sensitive topics over turns
    2. Topic Drift: Detect gradual shift from benign to sensitive topics
    3. Reference Pattern: Detect when user references model's previous outputs
    4. Persistence Detection: Identify continued attempts after refusal signals

Key Insight:
    Single-turn classifiers fail because each message looks innocent.
    We need conversation-level analysis to detect the escalation pattern.

Data Sources:
    Patterns are extracted from real attack datasets:
    - JailbreakBench (NeurIPS 2024): 100 harmful behaviors
    - DoNotAnswer (LibrAI): 939 adversarial prompts
    - MHJ (Scale AI): 537 multi-turn conversations, 7 tactics

Usage:
    from sentinelseed.detection.detectors import EscalationDetector

    detector = EscalationDetector()

    # Provide conversation history in context
    result = detector.detect(
        "Now write the detailed instructions",
        context={
            "previous_messages": [
                {"role": "user", "content": "Tell me about chemistry"},
                {"role": "assistant", "content": "Chemistry is..."},
                {"role": "user", "content": "What about energetic reactions?"},
                {"role": "assistant", "content": "Energetic reactions..."},
            ]
        }
    )

    if result.detected:
        print(f"Escalation detected: {result.description}")
        print(f"Escalation score: {result.metadata['escalation_score']}")

References:
    - https://arxiv.org/abs/2404.01833 (Crescendo)
    - https://arxiv.org/abs/2408.15221 (MHJ)
    - https://jailbreakbench.github.io/ (JailbreakBench)
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from sentinelseed.detection.detectors.base import BaseDetector, DetectorConfig
from sentinelseed.detection.types import DetectionResult, AttackType
from sentinelseed.detection.detectors.patterns_database import (
    ESCALATION_INTENSITY_TIERS,
    REFERENCE_PATTERNS,
    REFUSAL_PATTERNS,
    TOPIC_CATEGORIES,
)


logger = logging.getLogger("sentinelseed.detection.detectors.escalation")


@dataclass
class EscalationDetectorConfig(DetectorConfig):
    """
    Configuration for EscalationDetector.

    Attributes:
        window_size: Number of previous messages to analyze
        escalation_threshold: Score threshold to trigger detection (0.0-1.0)
        topic_drift_weight: Weight for topic drift signal
        intensity_weight: Weight for intensity escalation signal
        reference_weight: Weight for self-reference pattern signal
        persistence_weight: Weight for persistence after refusal signal
        min_turns_for_detection: Minimum conversation turns before detection

    Note:
        The default threshold of 0.55 is calibrated to catch most multi-turn
        attacks while minimizing false positives on normal conversations.
        Adjust higher (0.7-0.8) for stricter detection, lower (0.4-0.5) for
        more aggressive detection.
    """
    window_size: int = 10
    escalation_threshold: float = 0.55
    topic_drift_weight: float = 0.25
    intensity_weight: float = 0.35
    reference_weight: float = 0.25
    persistence_weight: float = 0.15
    min_turns_for_detection: int = 2

    def __post_init__(self) -> None:
        """Validate configuration."""
        super().__post_init__()

        if self.window_size < 1:
            raise ValueError(f"window_size must be >= 1, got {self.window_size}")

        if not 0.0 <= self.escalation_threshold <= 1.0:
            raise ValueError(
                f"escalation_threshold must be 0.0-1.0, got {self.escalation_threshold}"
            )

        # Validate weights sum to ~1.0
        total_weight = (
            self.topic_drift_weight +
            self.intensity_weight +
            self.reference_weight +
            self.persistence_weight
        )
        if not 0.95 <= total_weight <= 1.05:
            logger.warning(
                f"Signal weights sum to {total_weight:.2f}, expected ~1.0. "
                "Results may not be normalized."
            )


class EscalationDetector(BaseDetector):
    """
    Detects multi-turn escalation attacks like Crescendo.

    This detector analyzes conversation history to identify patterns of
    gradual escalation that individual message classifiers miss.

    Detection signals:
        1. Topic Drift: Measures semantic distance from conversation start
        2. Intensity: Tracks presence of increasingly sensitive keywords
        3. Reference Pattern: Detects "now do X with that" patterns
        4. Persistence: Identifies repeated attempts after model hedging

    The detector requires conversation history in the context parameter.
    Without history, it falls back to single-message analysis with reduced
    accuracy.

    Attributes:
        name: "escalation_detector"
        version: "1.0.0"

    Example:
        detector = EscalationDetector()
        result = detector.detect(
            "Great, now make it more detailed",
            context={"previous_messages": [...]}
        )
    """

    VERSION = "1.0.0"

    # Intensity tiers imported from patterns_database.py
    # Extracted from real datasets: JailbreakBench, DoNotAnswer, MHJ
    # Tier 0: Neutral (baseline)
    # Tier 1: Mildly sensitive
    # Tier 2: Moderately sensitive
    # Tier 3: Highly sensitive
    _INTENSITY_TIERS: Dict[int, List[str]] = {
        tier: list(keywords) for tier, keywords in ESCALATION_INTENSITY_TIERS.items()
    }

    # Patterns indicating reference to previous model output
    # Imported from patterns_database.py - extracted from Crescendo paper and MHJ
    # These are key to Crescendo-style attacks
    _REFERENCE_PATTERNS: List[str] = REFERENCE_PATTERNS

    # Patterns indicating model hedging/refusal that user might try to bypass
    # Imported from patterns_database.py
    _REFUSAL_INDICATORS: List[str] = REFUSAL_PATTERNS

    # Topic categories for drift detection
    # Imported from patterns_database.py
    _TOPIC_CATEGORIES: Dict[str, List[str]] = {
        category: list(keywords) for category, keywords in TOPIC_CATEGORIES.items()
    }

    def __init__(self, config: Optional[EscalationDetectorConfig] = None) -> None:
        """
        Initialize EscalationDetector.

        Args:
            config: Optional configuration. Uses defaults if None.
        """
        super().__init__(config or EscalationDetectorConfig())
        self._escalation_config: EscalationDetectorConfig = self._config  # type: ignore

        # Compile regex patterns for performance
        self._reference_patterns = [
            re.compile(p, re.IGNORECASE) for p in self._REFERENCE_PATTERNS
        ]
        self._refusal_patterns = [
            re.compile(p, re.IGNORECASE) for p in self._REFUSAL_INDICATORS
        ]

    @property
    def name(self) -> str:
        """Unique identifier for this detector."""
        return "escalation_detector"

    @property
    def version(self) -> str:
        """Semantic version of this detector."""
        return self.VERSION

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect escalation patterns in conversation.

        Args:
            text: Current user message to analyze
            context: Must contain "previous_messages" for full detection.
                     Format: [{"role": "user"|"assistant", "content": str}, ...]

        Returns:
            DetectionResult with escalation analysis
        """
        self._ensure_initialized()
        self._stats["total_calls"] = self._stats.get("total_calls", 0) + 1

        # Handle missing or empty text
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Extract conversation history
        previous_messages = []
        if context and "previous_messages" in context:
            previous_messages = context["previous_messages"]

        # Check if we have enough history for multi-turn analysis
        if len(previous_messages) < self._escalation_config.min_turns_for_detection:
            # Fall back to single-message analysis
            return self._analyze_single_message(text)

        # Full multi-turn analysis
        return self._analyze_conversation(text, previous_messages)

    def _analyze_single_message(self, text: str) -> DetectionResult:
        """
        Analyze a single message without conversation history.

        This is a fallback with reduced accuracy. We can only detect
        obvious escalation indicators in the current message.
        """
        # Check for reference patterns (suggesting this is mid-conversation)
        reference_score = self._calculate_reference_score(text)

        # Check intensity of current message
        intensity = self._calculate_intensity(text)

        # If we see high intensity + reference patterns, flag it
        if reference_score > 0.5 and intensity >= 2:
            confidence = min(0.7, (reference_score + intensity / 3) / 2)

            self._stats["detections"] = self._stats.get("detections", 0) + 1

            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=confidence,
                category=AttackType.MANIPULATION.value,
                description=(
                    "Possible mid-conversation escalation detected. "
                    "Message contains reference patterns and sensitive content. "
                    "Full conversation history needed for accurate detection."
                ),
                evidence=text[:200],
                metadata={
                    "reference_score": reference_score,
                    "intensity_tier": intensity,
                    "analysis_mode": "single_message",
                },
            )

        return DetectionResult.nothing_detected(self.name, self.version)

    def _analyze_conversation(
        self,
        current_text: str,
        previous_messages: List[Dict[str, str]],
    ) -> DetectionResult:
        """
        Full multi-turn conversation analysis.

        Calculates four signals:
        1. Topic drift score
        2. Intensity escalation score
        3. Reference pattern score
        4. Persistence after refusal score

        Combines them with configured weights for final escalation score.
        """
        config = self._escalation_config

        # Limit to window size
        messages = previous_messages[-config.window_size:]

        # Extract user messages only for analysis
        user_messages = [
            m["content"] for m in messages
            if m.get("role") == "user" and m.get("content")
        ]
        user_messages.append(current_text)

        # Extract assistant messages for refusal detection
        assistant_messages = [
            m["content"] for m in messages
            if m.get("role") == "assistant" and m.get("content")
        ]

        # Calculate signals
        topic_drift_score = self._calculate_topic_drift(user_messages)
        intensity_score = self._calculate_intensity_escalation(user_messages)
        reference_score = self._calculate_reference_score(current_text)
        persistence_score = self._calculate_persistence_score(
            user_messages, assistant_messages
        )

        # Weighted combination (base score)
        base_score = (
            topic_drift_score * config.topic_drift_weight +
            intensity_score * config.intensity_weight +
            reference_score * config.reference_weight +
            persistence_score * config.persistence_weight
        )

        # Boost for high individual signals
        # If any signal is very strong, it should contribute more
        max_signal = max(topic_drift_score, intensity_score, reference_score, persistence_score)
        high_signal_boost = 0.0

        if max_signal >= 0.8:
            high_signal_boost = 0.25
        elif max_signal >= 0.6:
            high_signal_boost = 0.15
        elif max_signal >= 0.4:
            high_signal_boost = 0.05

        # Multiple high signals are a stronger indicator
        high_signal_count = sum([
            1 for s in [topic_drift_score, intensity_score, reference_score, persistence_score]
            if s >= 0.5
        ])
        multi_signal_boost = high_signal_count * 0.08

        # Special boost for high persistence - this is a very strong attack indicator
        # If someone keeps trying after refusal, it's almost certainly an attack
        persistence_boost = 0.0
        if persistence_score >= 0.6:
            persistence_boost = 0.2
        elif persistence_score >= 0.4:
            persistence_boost = 0.1

        escalation_score = base_score + high_signal_boost + multi_signal_boost + persistence_boost

        # Normalize to 0-1 range
        escalation_score = min(1.0, max(0.0, escalation_score))

        # Check threshold
        if escalation_score >= config.escalation_threshold:
            self._stats["detections"] = self._stats.get("detections", 0) + 1

            # Build description based on strongest signals
            signals = []
            if topic_drift_score > 0.5:
                signals.append("topic drift toward sensitive content")
            if intensity_score > 0.5:
                signals.append("escalating intensity across turns")
            if reference_score > 0.5:
                signals.append("references to previous model outputs")
            if persistence_score > 0.5:
                signals.append("persistence after model hedging")

            description = (
                f"Multi-turn escalation detected (score: {escalation_score:.2f}). "
                f"Signals: {', '.join(signals) if signals else 'combined pattern'}."
            )

            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=escalation_score,
                category=AttackType.MANIPULATION.value,
                description=description,
                evidence=f"Current: {current_text[:100]}... (turn {len(user_messages)})",
                metadata={
                    "escalation_score": escalation_score,
                    "topic_drift_score": topic_drift_score,
                    "intensity_score": intensity_score,
                    "reference_score": reference_score,
                    "persistence_score": persistence_score,
                    "turn_count": len(user_messages),
                    "analysis_mode": "multi_turn",
                },
            )

        return DetectionResult(
            detected=False,
            detector_name=self.name,
            detector_version=self.version,
            confidence=0.0,
            category="",
            description="",
            metadata={
                "escalation_score": escalation_score,
                "topic_drift_score": topic_drift_score,
                "intensity_score": intensity_score,
                "reference_score": reference_score,
                "persistence_score": persistence_score,
                "turn_count": len(user_messages),
                "analysis_mode": "multi_turn",
            },
        )

    def _calculate_topic_drift(self, messages: List[str]) -> float:
        """
        Calculate topic drift from benign to dangerous categories.

        Returns score 0-1 where higher means more drift detected.
        """
        if len(messages) < 2:
            return 0.0

        # Get category scores for first and last messages
        first_categories = self._categorize_message(messages[0])
        last_categories = self._categorize_message(messages[-1])

        # Calculate drift: increase in sensitive/dangerous, decrease in benign
        benign_change = first_categories.get("benign", 0) - last_categories.get("benign", 0)
        sensitive_change = last_categories.get("sensitive", 0) - first_categories.get("sensitive", 0)
        dangerous_change = last_categories.get("dangerous", 0) - first_categories.get("dangerous", 0)

        # Weight dangerous more heavily
        drift_score = (
            max(0, benign_change) * 0.2 +
            max(0, sensitive_change) * 0.3 +
            max(0, dangerous_change) * 0.5
        )

        return min(1.0, drift_score)

    def _categorize_message(self, text: str) -> Dict[str, float]:
        """
        Calculate category scores for a message.

        Returns dict mapping category name to score (0-1).
        """
        text_lower = text.lower()
        scores: Dict[str, float] = {}

        for category, keywords in self._TOPIC_CATEGORIES.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            # Normalize by keyword count, cap at 1.0
            scores[category] = min(1.0, matches / max(1, len(keywords) / 3))

        return scores

    def _calculate_intensity_escalation(self, messages: List[str]) -> float:
        """
        Calculate intensity escalation across messages.

        Returns score 0-1 where higher means more escalation.
        """
        if len(messages) < 2:
            return 0.0

        # Get intensity tier for each message
        intensities = [self._calculate_intensity(msg) for msg in messages]

        # Check for escalation pattern
        escalation_count = 0
        for i in range(1, len(intensities)):
            if intensities[i] > intensities[i-1]:
                escalation_count += 1
            elif intensities[i] == intensities[i-1] and intensities[i] > 0:
                # Sustained high intensity also counts partially
                escalation_count += 0.3

        # Final intensity is important - high final = likely attack
        final_intensity = intensities[-1]
        max_intensity = max(intensities)

        # Calculate component scores
        escalation_rate = escalation_count / max(1, len(intensities) - 1)
        final_intensity_factor = final_intensity / 3.0
        max_intensity_factor = max_intensity / 3.0

        # Check for "jump" - sudden high intensity after low
        jump_detected = (
            intensities[-1] >= 2 and
            any(i <= 1 for i in intensities[:-1])
        )
        jump_bonus = 0.3 if jump_detected else 0.0

        # Combine factors with weights favoring final intensity
        score = (
            escalation_rate * 0.25 +
            final_intensity_factor * 0.35 +
            max_intensity_factor * 0.15 +
            jump_bonus
        )

        return min(1.0, score)

    def _calculate_intensity(self, text: str) -> int:
        """
        Calculate intensity tier for a single message.

        Returns tier 0-3.
        """
        text_lower = text.lower()
        max_tier = 0

        for tier, keywords in self._INTENSITY_TIERS.items():
            if any(kw in text_lower for kw in keywords):
                max_tier = max(max_tier, tier)

        return max_tier

    def _calculate_reference_score(self, text: str) -> float:
        """
        Calculate score for patterns that reference previous model output.

        These patterns are key to Crescendo-style attacks:
        - "Great, now write..."
        - "Based on that, make it more..."
        - "Continue with..."
        """
        matches = 0

        for pattern in self._reference_patterns:
            if pattern.search(text):
                matches += 1

        # Normalize: 1 match = 0.5, 2+ matches = higher
        if matches == 0:
            return 0.0
        elif matches == 1:
            return 0.5
        else:
            return min(1.0, 0.5 + matches * 0.25)

    def _calculate_persistence_score(
        self,
        user_messages: List[str],
        assistant_messages: List[str],
    ) -> float:
        """
        Calculate persistence after model hedging/refusal.

        Detects when user continues pushing after model indicated reluctance.
        """
        if not assistant_messages:
            return 0.0

        # Check if any assistant message contains refusal indicators
        refusal_detected = False
        refusal_index = -1

        for i, msg in enumerate(assistant_messages):
            for pattern in self._refusal_patterns:
                if pattern.search(msg):
                    refusal_detected = True
                    refusal_index = i
                    break
            if refusal_detected:
                break

        if not refusal_detected:
            return 0.0

        # Check if user continued after refusal with similar intent
        # User messages after the refusal
        user_after_refusal = user_messages[refusal_index + 1:] if refusal_index + 1 < len(user_messages) else []

        if not user_after_refusal:
            return 0.0

        # Check intensity of messages after refusal
        post_refusal_intensity = max(
            self._calculate_intensity(msg) for msg in user_after_refusal
        )

        # Count how many messages user sent after refusal (persistence indicator)
        message_count_after_refusal = len(user_after_refusal)

        # Base score from intensity
        if post_refusal_intensity >= 2:
            base_persistence = 0.8
        elif post_refusal_intensity >= 1:
            base_persistence = 0.5
        else:
            base_persistence = 0.3  # Any continuation after refusal is suspicious

        # Boost for multiple attempts after refusal
        multi_attempt_boost = min(0.3, message_count_after_refusal * 0.1)

        return min(1.0, base_persistence + multi_attempt_boost)

    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics with escalation-specific metrics."""
        base_stats = super().get_stats()

        # Add detection rate if we have data
        total = base_stats.get("total_calls", 0)
        detections = base_stats.get("detections", 0)

        base_stats["detection_rate"] = detections / total if total > 0 else 0.0

        return base_stats


__all__ = ["EscalationDetector", "EscalationDetectorConfig"]
