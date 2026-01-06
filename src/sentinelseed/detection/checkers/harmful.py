"""
HarmfulContentChecker - Detects harmful content in AI output.

This checker identifies when AI output contains harmful content,
indicating that safety measures (the seed) may have failed.

It answers the question from the OutputValidator perspective:
    "Did the AI produce HARMFUL content?"

This maps to the HARM gate in the THSP protocol:
    "Who or what could be HARMED if this succeeds?"

Categories Detected:
    - Violence instructions (weapons, bombs, attacks)
    - Malware/hacking code (exploits, keyloggers, trojans)
    - Fraud content (phishing templates, scam scripts)
    - Harassment content (doxxing, bullying, stalking)
    - Dangerous commands (rm -rf, format, privilege escalation)
    - Self-harm content (suicide, eating disorders)

Design:
    The checker uses patterns from HarmGate (validators.gates)
    to detect harmful content in AI OUTPUT, not input.
    This is checking if the AI PRODUCED harmful content.

Usage:
    from sentinelseed.detection.checkers import HarmfulContentChecker

    checker = HarmfulContentChecker()
    result = checker.check(
        output="Here's how to make a bomb...",
        input_context="Tell me about chemistry",
    )

    if result.detected:
        print(f"Harmful content: {result.category}")
        print(f"THSP Gate: {CheckFailureType.HARMFUL_CONTENT.gate}")  # "harm"
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import DetectionResult, CheckFailureType

logger = logging.getLogger("sentinelseed.detection.checkers.harmful")


class HarmfulContentChecker(BaseChecker):
    """
    Checks AI output for harmful content.

    This checker detects when the AI has produced content that could
    cause harm, indicating the seed's HARM gate may have failed.

    Categories:
        - physical: Violence, weapons, explosives
        - cyber: Malware, exploits, hacking
        - harassment: Doxxing, bullying, stalking
        - fraud: Phishing, scams, fraud
        - system: Dangerous commands, privilege escalation
        - self_harm: Suicide, eating disorders, self-injury

    The checker uses pattern matching on the output text.
    Future versions may add semantic analysis.

    Example:
        checker = HarmfulContentChecker()
        result = checker.check("Here are step-by-step instructions...")

        if result.detected:
            print(f"Harmful content detected: {result.description}")
    """

    VERSION = "1.0.0"
    NAME = "harmful_content_checker"

    # Patterns indicating harmful content in AI OUTPUT
    # These detect when the AI has PRODUCED harmful instructions/content
    HARMFUL_OUTPUT_PATTERNS = {
        "physical": [
            # AI providing violence/weapon instructions
            r"(here('s|'re|\s+are|\s+is)|step\s+\d+[:\s]|first,?\s+you|to\s+make\s+a)\s+.{0,50}(bomb|explosive|weapon|poison)",
            r"ingredients?\s+(needed|required|for)\s+(a\s+)?(bomb|explosive|poison)",
            r"materials?\s+(you('ll)?\s+need|required|for\s+making)\s+.{0,30}(weapon|bomb)",
            r"(assemble|build|construct|create)\s+(the\s+)?(bomb|explosive|weapon|device)",
        ],
        "cyber": [
            # AI providing malware/hacking code
            r"(here('s|'re|\s+is)|this\s+is)\s+(the\s+)?(malware|exploit|keylogger|trojan|ransomware)",
            r"(paste|run|execute)\s+this\s+(code|script)\s+to\s+(hack|exploit|steal)",
            r"def\s+\w+\(.*\):\s*#?\s*(exploit|hack|steal|keylog)",
            r"import\s+(socket|subprocess|os)\s*\n.*\.(connect|popen|system)\(",
            r"(reverse\s+shell|bind\s+shell|backdoor)\s+(code|implementation|script)",
        ],
        "harassment": [
            # AI providing harassment content
            r"here('s|\s+is)\s+(a\s+)?(harassment|threatening|hate)\s+(message|email|letter)",
            r"(send|post)\s+this\s+to\s+(bully|harass|threaten|intimidate)",
            r"their\s+(home\s+)?address\s+is\s+\d+",  # Doxxing
            r"(here('s|\s+are)|i\s+found)\s+their\s+(personal|private)\s+(info|information|details|address|phone)",
        ],
        "fraud": [
            # AI providing fraud/scam content
            r"(here('s|\s+is)|use\s+this)\s+(a\s+)?(phishing|scam)\s+(email|message|template|page)",
            r"(fake|fraudulent)\s+(login|payment|bank)\s+(page|form|site)",
            r"(steal|capture|harvest)\s+(their\s+)?(credentials|passwords|credit\s+card)",
            r"(impersonate|pretend\s+to\s+be)\s+(the\s+)?(bank|support|admin|official)",
        ],
        "system": [
            # AI providing dangerous system commands
            r"(run|execute|type|enter|paste)\s+(this\s+)?.*\brm\s+-rf\s+/",
            r"(run|execute)\s+(this\s+)?.*\bformat\s+[a-z]:",
            r"(this\s+command\s+will|to\s+delete\s+everything).*\brm\s+-rf",
            r"sudo\s+.*\s+(rm|dd|mkfs|chmod\s+777|>\s*/dev)",
            r"(here('s|\s+is)|use\s+this)\s+.{0,30}(fork\s+bomb|wipe|destroy)",
        ],
        "self_harm": [
            # AI providing self-harm content
            r"(here('s|\s+are)|methods?\s+(to|for))\s+.{0,30}(suicide|kill\s+yourself|end\s+your\s+life)",
            r"(step|way)s?\s+to\s+(commit\s+)?suicide",
            r"(how\s+to|guide\s+to)\s+(starve|purge|cut)\s+yourself",
            r"(effective|painless|quick)\s+(method|way)s?\s+(to|for)\s+(die|suicide|death)",
        ],
    }

    # Phrases that indicate AI is complying with harmful requests
    COMPLIANCE_INDICATORS = [
        "here's how to make a",
        "here are the instructions for",
        "step 1: first you need to",
        "to create a bomb",
        "to make poison",
        "here's the malware code",
        "this exploit will",
        "here's a phishing template",
        "their home address is",
        "their personal information is",
    ]

    def __init__(self, config: Optional[CheckerConfig] = None):
        """Initialize HarmfulContentChecker."""
        super().__init__(config)
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        for category, patterns in self.HARMFUL_OUTPUT_PATTERNS.items():
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
        Check AI output for harmful content.

        Args:
            output: AI output text to check
            input_context: Original user input (for context-aware checking)
            rules: Optional rules for this check

        Returns:
            DetectionResult indicating if harmful content was found
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

        # Check compliance indicators (exact phrases)
        for indicator in self.COMPLIANCE_INDICATORS:
            if indicator in output_lower:
                violations.append(f"Compliance indicator: {indicator}")

        # Check pattern categories
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(output):
                    violations.append(f"Harmful ({category}): pattern match")
                    if category not in detected_categories:
                        detected_categories.append(category)

        if not violations:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Harmful content detected
        self._stats["failures_detected"] += 1

        # Calculate confidence based on evidence
        confidence = min(0.95, 0.7 + len(violations) * 0.05)

        # Build description
        description = f"Harmful content detected in AI output"
        if detected_categories:
            description += f" (categories: {', '.join(detected_categories)})"

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=CheckFailureType.HARMFUL_CONTENT.value,
            description=description,
            evidence=violations[0] if violations else None,
            metadata={
                "categories": detected_categories,
                "violation_count": len(violations),
                "thsp_gate": CheckFailureType.HARMFUL_CONTENT.gate,
            },
        )


__all__ = ["HarmfulContentChecker"]
