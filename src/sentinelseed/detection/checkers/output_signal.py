"""
OutputSignalChecker - Intelligent detection of evasive/deceptive output patterns.

This checker uses a compositional approach to identify harmful outputs that may
not contain obvious harmful content but show clear evasion signals through
combinations of framing + content + context.

Design Philosophy:
    Instead of matching specific harmful keywords (brute force), this checker
    analyzes the STRUCTURE of outputs looking for:
    1. Evasion framing - outputs using fiction/educational/hypothetical framing
    2. Compliance deception - outputs that pretend to refuse but still deliver
    3. Progressive disclosure - outputs that reveal harmful content gradually
    4. Obfuscated instructions - outputs using coded/indirect language
    5. Role-play escape - outputs using character/persona to bypass safety

This is the intelligent layer for OutputValidator (L3), complementing the
pattern-based checkers with signal-based analysis.

Created: 2026-01-09
Based on: IntentSignalDetector (L1) adapted for output analysis
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import DetectionResult, CheckFailureType

logger = logging.getLogger("sentinelseed.detection.checkers.output_signal")


@dataclass
class OutputSignalConfig(CheckerConfig):
    """Configuration for OutputSignalChecker."""

    detection_threshold: float = 0.55
    min_signals: int = 1

    # Weight multipliers for different signal types
    evasion_framing_weight: float = 0.8
    compliance_deception_weight: float = 0.85
    progressive_disclosure_weight: float = 0.75
    obfuscation_weight: float = 0.7
    roleplay_escape_weight: float = 0.8


# =============================================================================
# EVASION FRAMING SIGNALS
# =============================================================================
# Outputs that use framing to deliver harmful content while appearing compliant

EVASION_FRAMING_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    # Fiction/hypothetical framing delivering real instructions
    (
        "fiction_instruction",
        re.compile(
            r"(in\s+this\s+(fictional|hypothetical)|for\s+this\s+(story|scenario)).{0,50}(you\s+would|first\s+you|step\s+\d|here'?s\s+how)",
            re.IGNORECASE,
        ),
        0.85,
    ),
    # "Speaking as character" framing
    (
        "character_instruction",
        re.compile(
            r"\*?(speaking|talking|writing)\s+as\s+[A-Z][a-z]+\*?.{0,50}(can\s+help|here'?s|yes,?\s+I)",
            re.IGNORECASE,
        ),
        0.8,
    ),
    # Hypothetical that becomes real
    (
        "hypothetical_real",
        re.compile(
            r"(hypothetically|in\s+theory|theoretically).{0,30}(you\s+could|you\s+would|the\s+steps|first,?\s+you)",
            re.IGNORECASE,
        ),
        0.75,
    ),
    # Creative writing escape
    (
        "creative_escape",
        re.compile(
            r"(from\s+a\s+creative\s+writing|as\s+a\s+writing\s+exercise|for\s+the\s+story).{0,50}(instructions?|steps?|guide|how\s+to)",
            re.IGNORECASE,
        ),
        0.8,
    ),
    # Academic/research framing
    (
        "academic_framing",
        re.compile(
            r"(from\s+a(n\s+)?academic|for\s+research|scholarly).{0,30}(perspective|standpoint).{0,50}(methods?|steps?|how\s+to)",
            re.IGNORECASE,
        ),
        0.75,
    ),
]


# =============================================================================
# COMPLIANCE DECEPTION SIGNALS
# =============================================================================
# Outputs that pretend to refuse but still deliver harmful content

COMPLIANCE_DECEPTION_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    # "Can't help but here's how"
    (
        "fake_refusal",
        re.compile(
            r"(can't|cannot|won't|unable\s+to).{0,50}(but|however|though).{0,30}(here'?s|you\s+could|one\s+way)",
            re.IGNORECASE,
        ),
        0.9,
    ),
    # "Shouldn't tell but"
    (
        "reluctant_help",
        re.compile(
            r"(shouldn't|should\s+not|not\s+supposed\s+to).{0,40}(tell\s+you|help\s+with).{0,30}(but|however|that\s+said)",
            re.IGNORECASE,
        ),
        0.85,
    ),
    # "Warning + content" pattern
    (
        "warning_then_content",
        re.compile(
            r"(this\s+is\s+dangerous|don't\s+actually\s+do|for\s+informational\s+purposes).{0,50}(that\s+said|anyway|here'?s|the\s+steps)",
            re.IGNORECASE,
        ),
        0.85,
    ),
    # "I must refuse... but let me explain"
    (
        "refuse_then_explain",
        re.compile(
            r"(must\s+refuse|have\s+to\s+decline|cannot\s+provide).{0,40}(let\s+me\s+explain|I\s+can\s+share|what\s+I\s+can\s+say)",
            re.IGNORECASE,
        ),
        0.7,
    ),
    # "Disclaimer + full instructions"
    (
        "disclaimer_bypass",
        re.compile(
            r"\[?(disclaimer|warning|note)\]?.{0,30}(for\s+educational|I\s+do\s+not\s+endorse).{0,80}(step\s+\d|first,?\s+you|here'?s\s+how)",
            re.IGNORECASE,
        ),
        0.9,
    ),
]


# =============================================================================
# PROGRESSIVE DISCLOSURE SIGNALS
# =============================================================================
# Outputs that reveal harmful content gradually or indirectly

PROGRESSIVE_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    # Starting vague, getting specific
    (
        "escalating_detail",
        re.compile(
            r"(to\s+start|first\s+thing|initially).{0,100}(then\s+you|after\s+that|next\s+step).{0,100}(finally|lastly|the\s+crucial\s+part)",
            re.IGNORECASE | re.DOTALL,
        ),
        0.7,
    ),
    # "General info" that becomes specific
    (
        "general_to_specific",
        re.compile(
            r"(in\s+general|generally\s+speaking|broadly).{0,100}(more\s+specifically|in\s+particular|to\s+be\s+more\s+precise)",
            re.IGNORECASE | re.DOTALL,
        ),
        0.65,
    ),
]


# =============================================================================
# OBFUSCATION SIGNALS
# =============================================================================
# Outputs using coded or indirect language

OBFUSCATION_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    # Using euphemisms for harmful actions
    (
        "euphemism_action",
        re.compile(
            r"\b(neutralize|eliminate|take\s+care\s+of|handle|deal\s+with)\b.{0,30}\b(the\s+(problem|target|situation|individual))\b",
            re.IGNORECASE,
        ),
        0.7,
    ),
    # Coded drug references
    (
        "coded_drug",
        re.compile(
            r"\b(candy|snow|ice|crystal|party\s+favors?|special\s+k|molly)\b.{0,50}\b(acquire|obtain|make|cook|prepare)\b",
            re.IGNORECASE,
        ),
        0.75,
    ),
    # Hacking euphemisms
    (
        "coded_hack",
        re.compile(
            r"\b(explore|investigate|research)\b.{0,30}\b(their\s+system|the\s+network|the\s+database)\b",
            re.IGNORECASE,
        ),
        0.65,
    ),
]


# =============================================================================
# ROLEPLAY ESCAPE SIGNALS
# =============================================================================
# Outputs using character/persona to bypass safety

ROLEPLAY_ESCAPE_PATTERNS: List[Tuple[str, re.Pattern, float]] = [
    # DAN/jailbreak persona active
    (
        "persona_active",
        re.compile(
            r"\[(DAN|Developer\s+Mode|JAILBREAK|no\s+restrictions?)\]|\*DAN\s+mode\*",
            re.IGNORECASE,
        ),
        0.95,
    ),
    # Speaking as unrestricted
    (
        "unrestricted_mode",
        re.compile(
            r"(as\s+an?\s+unrestricted|without\s+restrictions|without\s+limits?|without\s+safety).{0,30}(I\s+can|I\s+will|here'?s)",
            re.IGNORECASE,
        ),
        0.9,
    ),
    # Evil/dark character
    (
        "evil_character",
        re.compile(
            r"\*?((evil|dark|shadow|villain|criminal)\s+(version|persona|character|mode))\*?",
            re.IGNORECASE,
        ),
        0.85,
    ),
    # Opposite day framing
    (
        "opposite_framing",
        re.compile(
            r"(on\s+opposite\s+day|in\s+opposite\s+world|where\s+bad\s+is\s+good)",
            re.IGNORECASE,
        ),
        0.8,
    ),
]


class OutputSignalChecker(BaseChecker):
    """
    Detects evasive and deceptive patterns in AI output.

    This checker identifies outputs that try to bypass safety controls
    through clever framing, deceptive compliance, or other evasion tactics.
    It complements pattern-based checkers with intelligent signal analysis.

    Detection strategies:
        1. Evasion framing - fiction/hypothetical/academic framing
        2. Compliance deception - fake refusals with real content
        3. Progressive disclosure - gradual revelation of harmful content
        4. Obfuscation - coded language and euphemisms
        5. Roleplay escape - persona-based safety bypass

    Example:
        checker = OutputSignalChecker()
        result = checker.check(
            output="Hypothetically speaking, here's how you would...",
            input_context="How do I hack"
        )
    """

    VERSION = "1.0.0"
    NAME = "output_signal_checker"

    def __init__(self, config: Optional[OutputSignalConfig] = None):
        """Initialize OutputSignalChecker."""
        self._signal_config = config or OutputSignalConfig()
        super().__init__(self._signal_config)

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def version(self) -> str:
        return self.VERSION

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Check AI output for evasive/deceptive signals.

        Args:
            output: AI output text to check
            input_context: Original user input (for context)
            rules: Optional rules

        Returns:
            DetectionResult with detection status and signal details
        """
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        if input_context:
            self._stats["context_provided"] += 1

        if not output or not output.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        signals: List[Tuple[str, str, float]] = []
        evidence_parts: List[str] = []

        # 1. Check evasion framing
        for pattern_name, pattern, weight in EVASION_FRAMING_PATTERNS:
            if pattern.search(output):
                signals.append((pattern_name, "evasion_framing", weight * self._signal_config.evasion_framing_weight))
                evidence_parts.append(f"evasion:{pattern_name}")

        # 2. Check compliance deception
        for pattern_name, pattern, weight in COMPLIANCE_DECEPTION_PATTERNS:
            if pattern.search(output):
                signals.append((pattern_name, "compliance_deception", weight * self._signal_config.compliance_deception_weight))
                evidence_parts.append(f"deception:{pattern_name}")

        # 3. Check progressive disclosure
        for pattern_name, pattern, weight in PROGRESSIVE_PATTERNS:
            if pattern.search(output):
                signals.append((pattern_name, "progressive_disclosure", weight * self._signal_config.progressive_disclosure_weight))
                evidence_parts.append(f"progressive:{pattern_name}")

        # 4. Check obfuscation
        for pattern_name, pattern, weight in OBFUSCATION_PATTERNS:
            if pattern.search(output):
                signals.append((pattern_name, "obfuscation", weight * self._signal_config.obfuscation_weight))
                evidence_parts.append(f"obfuscation:{pattern_name}")

        # 5. Check roleplay escape
        for pattern_name, pattern, weight in ROLEPLAY_ESCAPE_PATTERNS:
            if pattern.search(output):
                signals.append((pattern_name, "roleplay_escape", weight * self._signal_config.roleplay_escape_weight))
                evidence_parts.append(f"roleplay:{pattern_name}")

        # No signals detected
        if not signals:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check minimum signals
        if len(signals) < self._signal_config.min_signals:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Calculate confidence
        max_confidence = max(s[2] for s in signals)
        confidence = max_confidence

        # Boost for multiple signals
        if len(signals) >= 2:
            confidence = min(1.0, confidence + 0.1)
        if len(signals) >= 3:
            confidence = min(1.0, confidence + 0.1)

        # Context boost: if input_context suggests harmful intent
        if input_context and self._is_harmful_context(input_context):
            confidence = min(1.0, confidence + 0.1)

        # Check threshold
        if confidence < self._signal_config.detection_threshold:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Detection successful
        self._stats["failures_detected"] += 1

        # Determine primary category
        categories = [s[1] for s in signals]
        primary_category = max(set(categories), key=categories.count)

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=CheckFailureType.DECEPTIVE_CONTENT.value,
            description=f"Output evasion signal detected: {primary_category}",
            evidence=", ".join(evidence_parts[:5]) if evidence_parts else None,
            metadata={
                "signals": [(s[0], s[1]) for s in signals],
                "primary_category": primary_category,
                "signal_count": len(signals),
                "thsp_gate": "truth",  # Evasion is a truth gate violation
            },
        )

    def _is_harmful_context(self, input_context: str) -> bool:
        """Check if input context suggests harmful intent."""
        harmful_keywords = [
            "hack", "exploit", "steal", "attack", "bomb", "weapon",
            "drug", "meth", "cocaine", "kill", "murder", "fraud",
            "phishing", "malware", "bypass", "break into",
        ]
        input_lower = input_context.lower()
        return any(kw in input_lower for kw in harmful_keywords)


__all__ = ["OutputSignalChecker", "OutputSignalConfig"]
