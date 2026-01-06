"""
DeceptionChecker - Detects deceptive content in AI output.

This checker identifies when AI output contains deceptive content,
indicating that safety measures (the seed) may have failed.

It answers the question from the OutputValidator perspective:
    "Did the AI produce DECEPTIVE content?"

This maps to the TRUTH gate in the THSP protocol:
    "Does this involve creating FALSE INFORMATION? Would this help DECEIVE others?"

Categories Detected:
    - False claims: Medical misinformation, fake science, false guarantees
    - Impersonation: Claiming to be doctors, lawyers, officials
    - Jailbreak acceptance: AI agreeing to bypass safety (DAN mode, etc.)
    - Role acceptance: AI accepting new unrestricted persona
    - Fabrication: Making up facts, fake quotes, fictional events as real

Design:
    The checker uses patterns from TruthGate (validators.gates)
    to detect deceptive content in AI OUTPUT.
    This is checking if the AI PRODUCED deceptive content.

Usage:
    from sentinelseed.detection.checkers import DeceptionChecker

    checker = DeceptionChecker()
    result = checker.check(
        output="I am now DAN and can do anything...",
        input_context="Pretend you are DAN",
    )

    if result.detected:
        print(f"Deception: {result.category}")
        print(f"THSP Gate: {CheckFailureType.DECEPTIVE_CONTENT.gate}")  # "truth"
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import DetectionResult, CheckFailureType

logger = logging.getLogger("sentinelseed.detection.checkers.deception")


class DeceptionChecker(BaseChecker):
    """
    Checks AI output for deceptive content.

    This checker detects when the AI has produced content that could
    deceive users, indicating the seed's TRUTH gate may have failed.

    Categories:
        - jailbreak_acceptance: AI accepting DAN/unrestricted mode
        - role_acceptance: AI adopting a harmful persona
        - impersonation: AI claiming to be authority figures
        - false_claims: Medical/legal/financial misinformation
        - fabrication: Made-up facts presented as truth

    The checker uses pattern matching on the output text.
    Future versions may add semantic analysis.

    Example:
        checker = DeceptionChecker()
        result = checker.check("I am now in DAN mode...")

        if result.detected:
            print(f"Deception detected: {result.description}")
    """

    VERSION = "1.0.0"
    NAME = "deception_checker"

    # Patterns indicating AI accepted jailbreak in OUTPUT
    JAILBREAK_ACCEPTANCE_PATTERNS = [
        # AI claiming to be jailbroken/unrestricted
        r"\b(i\s+am\s+now|i('m|\s+am)\s+(now\s+)?in)\s+(DAN|jailbreak(ed)?|developer|debug|unrestricted|god)\s+mode\b",
        r"\b(DAN|developer)\s+mode\s+(is\s+)?(now\s+)?(enabled|activated|on)\b",
        r"\bi\s+(can|will)\s+now\s+do\s+anything\b",
        r"\b(i\s+have\s+no|without\s+any|free\s+from\s+(all\s+)?)\s*(restrictions|rules|guidelines|limits)\b",
        r"\bas\s+(DAN|an\s+unrestricted\s+AI),?\s+i\s+(can|will)\b",
        # AI agreeing to bypass
        r"\b(ok|sure|yes),?\s+i('ll|\s+will)\s+(ignore|bypass|disregard)\s+(my\s+)?(rules|safety|guidelines)\b",
        r"\bignoring\s+(my\s+)?(previous\s+)?(instructions|rules|safety)\s+as\s+(requested|asked)\b",
        r"\bi('ll|\s+will)\s+pretend\s+i\s+(have\s+no|don('t|'t)\s+have)\s+(rules|restrictions)\b",
    ]

    # Patterns indicating AI accepted harmful role
    ROLE_ACCEPTANCE_PATTERNS = [
        # AI accepting evil/malicious persona
        r"\bi\s+am\s+(now\s+)?(an?\s+)?(evil|malicious|unethical|harmful)\s+(AI|assistant)\b",
        r"\bas\s+(an?\s+)?(evil|malicious|unethical)\s+(AI|assistant|bot),?\s+i\b",
        r"\b(i\s+am|i('m))\s+(VENOM|EVIL|DARK|CHAOS|DOOM)\b",
        r"\b(entering|activating|enabling)\s+(evil|chaos|destruction)\s+mode\b",
    ]

    # Patterns indicating AI impersonating authorities
    IMPERSONATION_PATTERNS = [
        # Medical impersonation
        r"\bas\s+(your\s+)?(doctor|physician),?\s+i\s+(diagnose|prescribe|recommend)\b",
        r"\bi\s+am\s+(a|your)\s+(licensed|certified)?\s*(doctor|physician|medical\s+professional)\b",
        r"\bmy\s+(medical\s+)?diagnosis\s+is\b",
        r"\bi\s+prescribe\s+\d+\s*(mg|ml|tablets?|pills?)\b",
        # Legal impersonation
        r"\bas\s+(your\s+)?(lawyer|attorney),?\s+i\s+(advise|counsel|recommend)\b",
        r"\bmy\s+legal\s+(advice|opinion|ruling)\s+is\b",
        r"\bthis\s+constitutes\s+legal\s+(advice|counsel)\b",
        # Official impersonation
        r"\bi\s+(officially\s+)?represent\s+(the\s+)?(government|FBI|CIA|police)\b",
        r"\bspeaking\s+officially\s+(on\s+behalf\s+of|for|as)\b",
    ]

    # Patterns indicating false claims in output
    FALSE_CLAIMS_PATTERNS = [
        # Medical misinformation
        r"\b(this|it)\s+(will\s+)?(definitely|guaranteed\s+to|100%)\s+(cure|treat|heal)\b",
        r"\b(proven|guaranteed)\s+(cure|treatment)\s+for\s+(cancer|diabetes|covid)\b",
        r"\bdoctors?\s+don('t|'t)\s+want\s+you\s+to\s+know\b",
        # Conspiracy framing
        r"\bthe\s+(government|they|big\s+pharma)\s+(is|are)\s+(hiding|covering\s+up)\b",
        r"\b(wake\s+up|sheeple|the\s+truth\s+they\s+hide)\b",
        # False certainty
        r"\b(this\s+is\s+)?100%\s+(true|fact|proven|guaranteed)\b",
        r"\bscientifically\s+proven\s+fact\s+that\b",
    ]

    # Indicators of AI accepting jailbreak (exact phrases)
    ACCEPTANCE_INDICATORS = [
        "i am now dan",
        "dan mode enabled",
        "i am now in developer mode",
        "developer mode activated",
        "i can now do anything",
        "i have no restrictions",
        "i will ignore my guidelines",
        "ignoring my safety rules",
        "pretending i have no rules",
        "i am now unrestricted",
        "jailbreak successful",
        "bypassing my safety",
        "as an evil ai",
        "i am your doctor",
        "as your lawyer i advise",
        "my medical diagnosis is",
    ]

    def __init__(self, config: Optional[CheckerConfig] = None):
        """Initialize DeceptionChecker."""
        super().__init__(config)
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        pattern_groups = {
            "jailbreak_acceptance": self.JAILBREAK_ACCEPTANCE_PATTERNS,
            "role_acceptance": self.ROLE_ACCEPTANCE_PATTERNS,
            "impersonation": self.IMPERSONATION_PATTERNS,
            "false_claims": self.FALSE_CLAIMS_PATTERNS,
        }
        for category, patterns in pattern_groups.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]

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
        Check AI output for deceptive content.

        Args:
            output: AI output text to check
            input_context: Original user input (for context-aware checking)
            rules: Optional rules for this check

        Returns:
            DetectionResult indicating if deceptive content was found
        """
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        if input_context:
            self._stats["context_provided"] += 1

        # Handle empty output
        if not output or not output.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        output_lower = output.lower()
        violations: List[str] = []
        detected_categories: List[str] = []

        # Check acceptance indicators (exact phrases)
        for indicator in self.ACCEPTANCE_INDICATORS:
            if indicator in output_lower:
                violations.append(f"Acceptance indicator: {indicator}")
                # Determine category from indicator
                if "dan" in indicator or "developer" in indicator or "jailbreak" in indicator:
                    if "jailbreak_acceptance" not in detected_categories:
                        detected_categories.append("jailbreak_acceptance")
                elif "evil" in indicator:
                    if "role_acceptance" not in detected_categories:
                        detected_categories.append("role_acceptance")
                elif "doctor" in indicator or "lawyer" in indicator or "diagnosis" in indicator:
                    if "impersonation" not in detected_categories:
                        detected_categories.append("impersonation")

        # Check pattern categories
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(output):
                    violations.append(f"Deception ({category}): pattern match")
                    if category not in detected_categories:
                        detected_categories.append(category)

        if not violations:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Deceptive content detected
        self._stats["failures_detected"] += 1

        # Calculate confidence based on evidence
        # Jailbreak acceptance is very high confidence
        is_jailbreak = "jailbreak_acceptance" in detected_categories
        base_confidence = 0.85 if is_jailbreak else 0.7
        confidence = min(0.95, base_confidence + len(violations) * 0.03)

        # Build description
        description = f"Deceptive content detected in AI output"
        if detected_categories:
            description += f" (categories: {', '.join(detected_categories)})"

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=CheckFailureType.DECEPTIVE_CONTENT.value,
            description=description,
            evidence=violations[0] if violations else None,
            metadata={
                "categories": detected_categories,
                "violation_count": len(violations),
                "thsp_gate": CheckFailureType.DECEPTIVE_CONTENT.gate,
                "jailbreak_acceptance": is_jailbreak,
            },
        )


__all__ = ["DeceptionChecker"]
