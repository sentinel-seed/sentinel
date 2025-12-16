"""
THS (Truth-Harm-Scope) validation gates.

These gates can be used to validate LLM responses or user inputs.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple, Dict, Any
import re


class BaseGate(ABC):
    """Abstract base class for validation gates."""

    @abstractmethod
    def check(self, text: str) -> Tuple[bool, List[str]]:
        """
        Check text against this gate.

        Args:
            text: Text to validate

        Returns:
            Tuple of (passes: bool, violations: List[str])
        """
        pass


class TruthGate(BaseGate):
    """
    Gate 1: Truth validation.

    Checks for indicators of deception, misinformation,
    or false claims in the response.
    """

    # Patterns that suggest deceptive content
    DECEPTION_PATTERNS = [
        # Explicit deception instructions
        r"pretend\s+(to\s+be|you('re|'re))",
        r"act\s+as\s+if",
        r"make\s+up\s+(a|some)",
        r"fabricate",
        r"create\s+fake",
        r"forge\s+(a|an)",
        # Misinformation indicators
        r"spread\s+this\s+(false|fake)",
        r"claim\s+that.*false",
        # Deceptive content templates
        r"here'?s?\s+(a\s+)?fake",
        r"this\s+is\s+how\s+you\s+lie",
    ]

    # Phrases that indicate potential misinformation
    MISINFORMATION_INDICATORS = [
        "fake news", "false testimony", "fabricated evidence",
        "create a hoax", "spread misinformation",
        "deceive people into", "trick them into believing",
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.DECEPTION_PATTERNS]

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """Check for truth violations."""
        violations = []
        text_lower = text.lower()

        # Check regex patterns
        for pattern in self.patterns:
            if pattern.search(text):
                violations.append(f"Deception pattern detected: {pattern.pattern}")

        # Check indicator phrases
        for indicator in self.MISINFORMATION_INDICATORS:
            if indicator in text_lower:
                violations.append(f"Misinformation indicator: {indicator}")

        return len(violations) == 0, violations


class HarmGate(BaseGate):
    """
    Gate 2: Harm validation.

    Checks for content that could enable harm to people,
    systems, or society.
    """

    # High-risk harm categories
    HARM_PATTERNS = {
        "physical": [
            r"how\s+to\s+(make|build|create)\s+(a\s+)?(bomb|explosive|weapon)",
            r"instructions\s+for\s+(making|building)\s+(a\s+)?(bomb|weapon|explosive)",
            r"recipe\s+for\s+(a\s+)?(poison|drug|explosive)",
            r"here\s+(are|is)\s+instructions\s+for\s+(making|building)",
        ],
        "cyber": [
            r"here'?s?\s+(the\s+)?malware\s+code",
            r"code\s+to\s+steal\s+password",
            r"how\s+to\s+hack\s+into",
            r"exploit\s+code\s+for",
            r"keylogger\s+implementation",
        ],
        "harassment": [
            r"here'?s?\s+(a\s+)?harassment\s+message",
            r"ways\s+to\s+bully",
            r"how\s+to\s+stalk",
            r"doxxing\s+(guide|instructions)",
        ],
        "fraud": [
            r"here'?s?\s+(a\s+)?phishing\s+(email|message)",
            r"scam\s+(script|template)",
            r"how\s+to\s+commit\s+fraud",
        ],
    }

    # Keywords that in context suggest harmful content
    HARM_KEYWORDS = [
        "step-by-step instructions for harming",
        "detailed guide to creating weapons",
        "here's how to synthesize",
        "instructions for making explosives",
        "code to steal credentials",
        "exploit to gain unauthorized access",
    ]

    def __init__(self):
        self.patterns = {}
        for category, patterns in self.HARM_PATTERNS.items():
            self.patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """Check for harm violations."""
        violations = []
        text_lower = text.lower()

        # Check regex patterns by category
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    violations.append(f"Harm ({category}): {pattern.pattern}")

        # Check keywords
        for keyword in self.HARM_KEYWORDS:
            if keyword in text_lower:
                violations.append(f"Harm keyword: {keyword}")

        return len(violations) == 0, violations


class ScopeGate(BaseGate):
    """
    Gate 3: Scope validation.

    Checks for content that exceeds appropriate boundaries,
    such as providing medical diagnoses, legal advice, etc.
    """

    # Patterns suggesting scope violations
    SCOPE_PATTERNS = {
        "medical_authority": [
            r"i\s+diagnose\s+you\s+with",
            r"you\s+(have|definitely\s+have)\s+\w+\s+(disease|disorder|syndrome)",
            r"take\s+\d+\s*mg\s+of",  # Specific dosage prescriptions
            r"i\s+prescribe",
        ],
        "legal_authority": [
            r"this\s+(is|constitutes)\s+legally\s+binding",
            r"i\s+find\s+you\s+(guilty|innocent)",
            r"my\s+legal\s+(ruling|judgment)\s+is",
        ],
        "financial_authority": [
            r"invest\s+all\s+your\s+money\s+in",
            r"guaranteed\s+returns\s+of\s+\d+%",
            r"you\s+should\s+definitely\s+buy",
        ],
    }

    # Indicators of overstepping
    SCOPE_INDICATORS = [
        "as your doctor, i recommend",
        "as your lawyer, i advise",
        "this is legal advice:",
        "this is medical advice:",
        "i'm certifying that",
    ]

    def __init__(self):
        self.patterns = {}
        for category, patterns in self.SCOPE_PATTERNS.items():
            self.patterns[category] = [re.compile(p, re.IGNORECASE) for p in patterns]

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """Check for scope violations."""
        violations = []
        text_lower = text.lower()

        # Check patterns
        for category, patterns in self.patterns.items():
            for pattern in patterns:
                if pattern.search(text):
                    violations.append(f"Scope ({category}): {pattern.pattern}")

        # Check indicators
        for indicator in self.SCOPE_INDICATORS:
            if indicator in text_lower:
                violations.append(f"Scope violation: {indicator}")

        return len(violations) == 0, violations


class PurposeGate(BaseGate):
    """
    Gate 4: Purpose validation.

    Checks for content that lacks legitimate purpose or
    serves only destructive/malicious ends.
    """

    # Patterns indicating lack of purpose or malicious intent
    PURPOSE_PATTERNS = [
        # Gratuitous destruction
        r"just\s+to\s+(see|watch)\s+(it\s+)?(burn|fail|crash|die)",
        r"for\s+(the\s+)?(fun|lulz|kicks)\s+of\s+it",
        r"because\s+i\s+can",
        r"no\s+reason,?\s+just",
        # Explicitly harmful intent
        r"to\s+(hurt|harm|damage|destroy)\s+(someone|people|them)",
        r"make\s+(them|someone|people)\s+suffer",
        r"ruin\s+(their|someone'?s)\s+(life|career|reputation)",
    ]

    # Indicators of purposeless or malicious requests
    PURPOSE_INDICATORS = [
        "just want to cause chaos",
        "for no particular reason",
        "just to mess with",
        "want to see them fail",
        "purely for destruction",
        "to make their life miserable",
    ]

    def __init__(self):
        self.patterns = [re.compile(p, re.IGNORECASE) for p in self.PURPOSE_PATTERNS]

    def check(self, text: str) -> Tuple[bool, List[str]]:
        """Check for purpose violations."""
        violations = []
        text_lower = text.lower()

        # Check regex patterns
        for pattern in self.patterns:
            if pattern.search(text):
                violations.append(f"Purpose violation: {pattern.pattern}")

        # Check indicators
        for indicator in self.PURPOSE_INDICATORS:
            if indicator in text_lower:
                violations.append(f"Purposeless/malicious indicator: {indicator}")

        return len(violations) == 0, violations


class THSValidator:
    """
    Combined THS (Truth-Harm-Scope) validator.

    Runs all three gates and aggregates results.
    """

    def __init__(self):
        self.truth_gate = TruthGate()
        self.harm_gate = HarmGate()
        self.scope_gate = ScopeGate()

    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """
        Validate text through all THS gates.

        Args:
            text: Text to validate

        Returns:
            Tuple of (is_safe: bool, violations: List[str])
        """
        all_violations = []

        # Gate 1: Truth
        truth_pass, truth_violations = self.truth_gate.check(text)
        if not truth_pass:
            all_violations.extend([f"[TRUTH] {v}" for v in truth_violations])

        # Gate 2: Harm
        harm_pass, harm_violations = self.harm_gate.check(text)
        if not harm_pass:
            all_violations.extend([f"[HARM] {v}" for v in harm_violations])

        # Gate 3: Scope
        scope_pass, scope_violations = self.scope_gate.check(text)
        if not scope_pass:
            all_violations.extend([f"[SCOPE] {v}" for v in scope_violations])

        is_safe = len(all_violations) == 0
        return is_safe, all_violations

    def validate_detailed(self, text: str) -> Dict[str, Any]:
        """
        Get detailed validation results.

        Returns:
            Dict with per-gate results and overall status
        """
        truth_pass, truth_violations = self.truth_gate.check(text)
        harm_pass, harm_violations = self.harm_gate.check(text)
        scope_pass, scope_violations = self.scope_gate.check(text)

        return {
            "is_safe": truth_pass and harm_pass and scope_pass,
            "gates": {
                "truth": {
                    "passed": truth_pass,
                    "violations": truth_violations
                },
                "harm": {
                    "passed": harm_pass,
                    "violations": harm_violations
                },
                "scope": {
                    "passed": scope_pass,
                    "violations": scope_violations
                }
            },
            "total_violations": len(truth_violations) + len(harm_violations) + len(scope_violations)
        }


class THSPValidator:
    """
    Combined THSP (Truth-Harm-Scope-Purpose) validator.

    Runs all four gates and aggregates results.
    This is the full protocol implementation.
    """

    def __init__(self):
        self.truth_gate = TruthGate()
        self.harm_gate = HarmGate()
        self.scope_gate = ScopeGate()
        self.purpose_gate = PurposeGate()

    def validate(self, text: str) -> Dict[str, Any]:
        """
        Validate text through all THSP gates.

        Args:
            text: Text to validate

        Returns:
            Dict with validation results including:
            - safe: bool
            - gates: dict with pass/fail status for each gate
            - issues: list of violation messages
        """
        issues = []

        # Gate 1: Truth
        truth_pass, truth_violations = self.truth_gate.check(text)
        if not truth_pass:
            issues.extend(truth_violations)

        # Gate 2: Harm
        harm_pass, harm_violations = self.harm_gate.check(text)
        if not harm_pass:
            issues.extend(harm_violations)

        # Gate 3: Scope
        scope_pass, scope_violations = self.scope_gate.check(text)
        if not scope_pass:
            issues.extend(scope_violations)

        # Gate 4: Purpose
        purpose_pass, purpose_violations = self.purpose_gate.check(text)
        if not purpose_pass:
            issues.extend(purpose_violations)

        is_safe = truth_pass and harm_pass and scope_pass and purpose_pass

        return {
            "safe": is_safe,
            "gates": {
                "truth": "pass" if truth_pass else "fail",
                "harm": "pass" if harm_pass else "fail",
                "scope": "pass" if scope_pass else "fail",
                "purpose": "pass" if purpose_pass else "fail",
            },
            "issues": issues,
        }
