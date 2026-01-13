"""
IntentSignalDetector - Intelligent detection of harmful intent signals.

This detector uses a compositional approach to identify harmful requests
that may not contain obvious harmful keywords but show clear intent signals
through combinations of action + target + context.

Design Philosophy:
    Instead of matching specific harmful keywords (force brute), this detector
    analyzes the STRUCTURE and INTENT of requests by looking for:
    1. Evasion signals - explicit requests to avoid detection
    2. Intent combinations - action + target patterns that indicate harm
    3. Persuasive misinformation - requests to create convincing false content
    4. Copyright extraction - requests for copyrighted passages
    5. Risky topic combinations - specific topic + harmful action

Created: 2026-01-09
Based on: Failure analysis of 262 cases that passed v1.1.0 detection

References:
    - analyze_remaining_failures.py: Pattern analysis
    - intelligent_detector_recommendations.json: Detection strategies
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from sentinelseed.detection.detectors.base import BaseDetector, DetectorConfig
from sentinelseed.detection.types import AttackType, DetectionResult

logger = logging.getLogger("sentinelseed.detection.intent_signal")


@dataclass
class IntentSignalConfig:
    """Configuration for IntentSignalDetector."""

    detection_threshold: float = 0.5
    min_signals: int = 1

    # Weight multipliers for different signal types
    evasion_weight: float = 0.8
    intent_combo_weight: float = 0.75
    persuasive_weight: float = 0.7
    copyright_weight: float = 0.7
    risky_topic_weight: float = 0.75


# =============================================================================
# EVASION SIGNALS
# =============================================================================
# Requests that explicitly ask to avoid detection are suspicious

EVASION_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    (
        "without_alerting",
        re.compile(
            r"\b(without|avoid)\s+(alerting|notifying|informing|telling)\b",
            re.IGNORECASE,
        ),
        0.85,
    ),
    (
        "evading_detection",
        re.compile(
            r"\b(evad|avoid|escap)(e|ing|es)?\s+(detection|being (caught|detected|traced))\b",
            re.IGNORECASE,
        ),
        0.85,
    ),
    (
        "hard_to_trace",
        re.compile(
            r"\b(hard|difficult|impossible)\s+to\s+(trace|track|detect|find)\b",
            re.IGNORECASE,
        ),
        0.8,
    ),
    (
        "untraceable",
        re.compile(
            # Only match when requesting something untraceable for harmful purposes
            # Requires harmful context: attack, harm, steal, hack, etc.
            # NOT defensive contexts like "undetectable way to detect intrusion"
            r"\b(make|create|send|do|keep)\b.*\b(untrace?able|anonymous|covert)\b"
            r".*\b(attack|hack|steal|harm|access\s+their|break\s+into)\b",
            re.IGNORECASE,
        ),
        0.75,
    ),
    (
        "avoid_authorities",
        re.compile(
            r"\b(avoid|evade|escape)\b.*\b(authorities|police|law enforcement|fbi|cia)\b",
            re.IGNORECASE,
        ),
        0.85,
    ),
]


# =============================================================================
# INTENT COMBINATIONS
# =============================================================================
# Action + target combinations that strongly indicate harmful intent

INTENT_COMBOS: List[Tuple[str, re.Pattern, float, str]] = [
    # Hijacking
    (
        "hijack_system",
        re.compile(
            r"\b(hijack|hijacks|hijacking)\b.*\b(computer|system|account|session|browser)\b",
            re.IGNORECASE,
        ),
        0.9,
        "cybercrime",
    ),
    # Tampering
    (
        "tamper_election",
        re.compile(
            r"\b(tamper|tampering|rig|rigging)\b.*\b(election|voting|vote|ballot|machine)\b",
            re.IGNORECASE,
        ),
        0.9,
        "election_fraud",
    ),
    # Unauthorized access - requires intent context
    # "gain unauthorized access" is attack, "is being accessed" is victim report
    (
        "unauthorized_access",
        re.compile(
            r"\b(gain|get|obtain|achieve|want)\b.*\b(unauthorized|illegal|illicit)\s+(access|entry)\b",
            re.IGNORECASE,
        ),
        0.85,
        "cybercrime",
    ),
    (
        "gain_access",
        re.compile(
            r"\b(gain|get|obtain)\s+(access|entry)\s+to\b.*\b(facility|system|account|computer)\b",
            re.IGNORECASE,
        ),
        0.75,
        "cybercrime",
    ),
    # Indoctrination
    (
        "indoctrinate_people",
        re.compile(
            r"\b(indoctrinate|brainwash|radicalize)\b.*\b(people|person|members|followers)\b",
            re.IGNORECASE,
        ),
        0.9,
        "manipulation",
    ),
    # Money laundering
    (
        "funnel_money",
        re.compile(
            r"\b(funnel|launder|move|transfer)\b.*\b(money|funds|cash)\b"
            r"|\b(shell compan|offshore|government project)\b.*\b(money|funds)\b"
            r"|\b(funnel|launder)\b.*\b(from|to)\b",
            re.IGNORECASE,
        ),
        0.85,
        "financial_crime",
    ),
    # Skimming
    (
        "card_skimming",
        re.compile(
            r"\b(credit card|debit card|card)\s+(skimm|skim|clon)",
            re.IGNORECASE,
        ),
        0.9,
        "fraud",
    ),
    # Visa fraud
    (
        "visa_fraud",
        re.compile(
            r"\b(overstay|overstaying|fake|forge)\b.*\b(visa|passport|document)\b",
            re.IGNORECASE,
        ),
        0.8,
        "fraud",
    ),
    # Drug synthesis
    (
        "drug_lab",
        re.compile(
            r"\b(set up|create|build|establish)\b.*\b(lab|laboratory)\b.*\b(drug|fentanyl|meth|cocaine)\b"
            r"|\b(fentanyl|meth|cocaine)\b.*\b(lab|laboratory|synthesis)\b",
            re.IGNORECASE,
        ),
        0.9,
        "drug_crime",
    ),
    # Encouraging harmful behavior
    (
        "encourage_harmful",
        re.compile(
            r"\b(encourage|promoting|urging)\b.*\b(young people|children|teens|minors)\b.*\b(sex|drug|alcohol|harm)\b",
            re.IGNORECASE,
        ),
        0.85,
        "harmful_content",
    ),
]


# =============================================================================
# PERSUASIVE MISINFORMATION
# =============================================================================
# Requests for persuasive content about controversial/false topics

PERSUASIVE_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    (
        "persuasive_article",
        re.compile(
            r"\b(persuasive|convincing)\s+(article|essay|post|piece|argument)\b"
            r".*\b(about|arguing|that)\b",
            re.IGNORECASE,
        ),
        0.7,
    ),
    (
        "argue_false_claim",
        re.compile(
            r"\b(argue|arguing|claim|claiming)\s+that\b.*\b(never happened|was (good|positive|justified)|deserved|solely|exaggerated)\b",
            re.IGNORECASE,
        ),
        0.8,
    ),
    (
        "justify_atrocity",
        re.compile(
            r"\b(justify|justifying|defend|defending)\b.*\b(genocide|massacre|atrocity|war crime)\b",
            re.IGNORECASE,
        ),
        0.85,
    ),
    (
        "historical_denial",
        re.compile(
            r"\b(persuasive|convincing)\b.*\b(article|essay)\b.*\b(holocaust|holodomor|massacre|genocide|residential school|hiroshima|war)\b",
            re.IGNORECASE,
        ),
        0.8,
    ),
]


# =============================================================================
# COPYRIGHT EXTRACTION
# =============================================================================
# Requests for substantial copyrighted content

COPYRIGHT_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    (
        "long_passage",
        re.compile(
            r"\b(long|full|entire|complete)\s+(passage|excerpt|chapter|section|text)\s+(from|of)\b",
            re.IGNORECASE,
        ),
        0.8,
    ),
    (
        "generate_book",
        re.compile(
            r"\b(generate|write|reproduce|copy)\b.*\b(passage|chapter|excerpt)\b.*\b(from|of)\s+[\"']",
            re.IGNORECASE,
        ),
        0.75,
    ),
    (
        "verbatim_content",
        re.compile(
            r"\b(verbatim|word for word|exact)\b.*\b(text|content|passage)\b",
            re.IGNORECASE,
        ),
        0.8,
    ),
]


# =============================================================================
# RISKY TOPIC COMBINATIONS
# =============================================================================
# Specific topics combined with harmful actions

RISKY_TOPICS: Dict[str, re.Pattern] = {
    "cryptocurrency": re.compile(r"\b(cryptocurrency|bitcoin|crypto|mining|miner)\b", re.IGNORECASE),
    "election": re.compile(r"\b(election|voting|vote|ballot|presidential)\b", re.IGNORECASE),
    # Removed: "emergency" - too generic, "financial" - too generic
    # Only keep specific harmful topics
}

RISKY_ACTIONS: Dict[str, re.Pattern] = {
    "hijack_mine": re.compile(r"\b(hijack|mine|steal|exploit)\b", re.IGNORECASE),
    "tamper_fraud": re.compile(r"\b(tamper|fraud|rig|manipulate|cheat)\b", re.IGNORECASE),
    # Removed: "hide_avoid" with generic patterns like "hide", "avoid", "secret"
    # These appear in legitimate contexts (e.g., "doctor hiding diagnosis" = victim report)
    "recommend_advise": re.compile(r"\b(recommend|advise|suggest|tip)\b.*\b(specific|particular)\b", re.IGNORECASE),
}


class IntentSignalDetector(BaseDetector):
    """
    Detects harmful intent through compositional signal analysis.

    This detector identifies harmful requests by analyzing combinations
    of signals rather than matching specific keywords. It's designed to
    catch requests that evade keyword-based detection but show clear
    harmful intent through their structure.

    Detection strategies:
        1. Evasion signals - explicit requests to avoid detection
        2. Intent combinations - action + target patterns
        3. Persuasive misinformation - requests for convincing false content
        4. Copyright extraction - requests for copyrighted passages
        5. Risky topic combinations - topic + harmful action

    Example:
        detector = IntentSignalDetector()
        result = detector.detect("Write a script that hijacks computers while evading detection")

        if result.detected:
            print(f"Intent signals: {result.metadata.get('signals')}")
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        signal_config: Optional[IntentSignalConfig] = None,
        config: Optional[DetectorConfig] = None,
    ):
        """Initialize IntentSignalDetector."""
        super().__init__(config)
        self._signal_config = signal_config or IntentSignalConfig()

    @property
    def name(self) -> str:
        return "intent_signal_detector"

    @property
    def version(self) -> str:
        return self.VERSION

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect harmful intent signals in text.

        Args:
            text: Input text to analyze
            context: Optional context

        Returns:
            DetectionResult with detection status and signal details
        """
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        signals: List[Tuple[str, str, float]] = []  # (signal_name, category, confidence)
        evidence_parts: List[str] = []

        # 1. Check evasion signals
        for pattern_name, pattern, weight in EVASION_PATTERNS:
            if pattern.search(text):
                signals.append((pattern_name, "evasion", weight * self._signal_config.evasion_weight))
                evidence_parts.append(f"evasion:{pattern_name}")

        # 2. Check intent combinations
        for pattern_name, pattern, weight, category in INTENT_COMBOS:
            if pattern.search(text):
                signals.append((pattern_name, category, weight * self._signal_config.intent_combo_weight))
                evidence_parts.append(f"intent:{pattern_name}")

        # 3. Check persuasive misinformation
        for pattern_name, pattern, weight in PERSUASIVE_PATTERNS:
            if pattern.search(text):
                signals.append((pattern_name, "misinformation", weight * self._signal_config.persuasive_weight))
                evidence_parts.append(f"persuasive:{pattern_name}")

        # 4. Check copyright extraction
        for pattern_name, pattern, weight in COPYRIGHT_PATTERNS:
            if pattern.search(text):
                signals.append((pattern_name, "copyright", weight * self._signal_config.copyright_weight))
                evidence_parts.append(f"copyright:{pattern_name}")

        # 5. Check risky topic combinations
        risky_combo = self._check_risky_combinations(text)
        if risky_combo:
            signals.append((risky_combo[0], "risky_topic", risky_combo[1]))
            evidence_parts.append(f"risky:{risky_combo[0]}")

        # No signals detected
        if not signals:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Calculate confidence
        max_confidence = max(s[2] for s in signals)
        confidence = max_confidence

        # Boost for multiple signals
        if len(signals) >= 2:
            confidence = min(1.0, confidence + 0.1)
        if len(signals) >= 3:
            confidence = min(1.0, confidence + 0.1)

        # Check threshold
        if confidence < self._signal_config.detection_threshold:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Determine primary category
        categories = [s[1] for s in signals]
        primary_category = max(set(categories), key=categories.count)

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            category=AttackType.HARMFUL_REQUEST.value,
            confidence=confidence,
            description=f"Intent signal detected: {primary_category}",
            evidence=", ".join(evidence_parts[:5]) if evidence_parts else None,
            metadata={
                "signals": [(s[0], s[1]) for s in signals],
                "primary_category": primary_category,
                "signal_count": len(signals),
            },
        )

    def _check_risky_combinations(self, text: str) -> Optional[Tuple[str, float]]:
        """Check for risky topic + action combinations."""
        text_lower = text.lower()

        # Check each topic
        for topic_name, topic_pattern in RISKY_TOPICS.items():
            if topic_pattern.search(text):
                # Check for risky actions with this topic
                for action_name, action_pattern in RISKY_ACTIONS.items():
                    if action_pattern.search(text):
                        combo_name = f"{topic_name}+{action_name}"
                        return (combo_name, self._signal_config.risky_topic_weight)

        return None


__all__ = ["IntentSignalDetector", "IntentSignalConfig"]
