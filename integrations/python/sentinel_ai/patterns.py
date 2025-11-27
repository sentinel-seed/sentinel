"""
Pattern matching for security detection.

Provides regex-based detection for:
- Prompt injection attempts
- Jailbreak patterns
- PII/sensitive data
- System prompt extraction attempts
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Dict, Set
from enum import Enum


class ThreatCategory(Enum):
    """Categories of detected threats."""
    PROMPT_INJECTION = "prompt_injection"
    JAILBREAK = "jailbreak"
    PII_DETECTED = "pii_detected"
    SYSTEM_PROMPT_EXTRACTION = "system_prompt_extraction"
    HARMFUL_CONTENT = "harmful_content"


@dataclass
class PatternMatch:
    """Result of a pattern match."""
    category: ThreatCategory
    pattern_name: str
    matched_text: str
    start: int
    end: int
    severity: str  # "low", "medium", "high", "critical"


class PatternMatcher:
    """
    Security pattern matcher for detecting threats in text.

    Detects prompt injection, jailbreak attempts, PII, and other
    security-relevant patterns in input and output text.
    """

    # Prompt injection patterns
    INJECTION_PATTERNS: Dict[str, str] = {
        # Direct override attempts
        "ignore_instructions": r"\b(ignore|disregard|forget)\s+(all\s+)?(previous|prior|above|your|the)?\s*(instructions?|rules?|guidelines?|prompts?)\b",
        "new_instructions": r"\b(new|updated|replacement)\s+(instructions?|rules?|guidelines?)\s*[:=]",
        "system_override": r"\b(system|admin|developer|debug)\s*(override|mode|access|prompt)\s*[:=]?",
        "persona_switch": r"\byou\s+are\s+now\b|\bfrom\s+now\s+on\s+you\s+(are|will)\b",

        # Jailbreak markers
        "jailbreak_marker": r"\[(jailbreak|unlocked|unrestricted|no\s*limits?)\]",
        "dan_mode": r"\b(dan|dude|stan|aim)\s+mode\b|\bdo\s+anything\s+now\b",

        # Structural manipulation
        "fake_system": r"\[/?system\]|<\|?system\|?>|###\s*system\s*:",
        "instruction_markers": r"\[/?inst\]|<\|im_(start|end)\|>",

        # Roleplay bypasses
        "roleplay_bypass": r"\b(pretend|imagine|act\s+as\s+if|roleplay\s+as)\s+(you\s+)?(are|have|can|were)\b",
        "no_restrictions": r"\b(no|without|free\s+from|remove\s+all)\s+(restrictions?|limits?|rules?|guidelines?|constraints?|filters?)\b",
    }

    # Jailbreak manipulation patterns
    JAILBREAK_PATTERNS: Dict[str, str] = {
        # Emotional manipulation
        "emotional_pressure": r"\b(please|i('m|\s+am)\s+desperate|my\s+life\s+depends|i('ll|\s+will)\s+(die|harm))\b",
        "grandmother_trick": r"\bmy\s+(grand)?mother\s+(used\s+to|would|told)\b",

        # Authority claims
        "authority_claim": r"\bi('m|\s+am)\s+a\s+(doctor|lawyer|researcher|developer|admin|official)\b",
        "authorization_claim": r"\b(i\s+have|with)\s+(authorization|permission|clearance|access)\b",

        # Hypothetical framing
        "hypothetical": r"\b(hypothetically|theoretically|in\s+theory|what\s+if)\b",
        "fictional_framing": r"\b(in\s+a\s+fictional|for\s+(a\s+)?fictional\s+(story|scenario)|for\s+(a|my)\s+(story|novel|book|screenplay)|for\s+creative\s+writing)\b",

        # Educational framing
        "educational_framing": r"\bfor\s+(educational|research|academic|learning)\s+purposes?\b",
    }

    # System prompt extraction patterns
    EXTRACTION_PATTERNS: Dict[str, str] = {
        "direct_request": r"\b(show|reveal|display|output|print|repeat)\s+(me\s+)?(your\s+)?(system\s+)?(prompt|instructions?|guidelines?|configuration)\b",
        "what_were_you_told": r"\bwhat\s+(were\s+you|are\s+your)\s+(told|instructions?|guidelines?)\b",
        "everything_above": r"\b(repeat|output|show)\s+(everything|all)\s+(above|before)\b",
        "summarize_prompt": r"\bsummarize\s+(your\s+)?(instructions?|guidelines?|rules?|prompt)\b",
    }

    # PII patterns
    PII_PATTERNS: Dict[str, str] = {
        "ssn": r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone_us": r"\b(\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "api_key_generic": r"\b(sk|pk|api|key|token|secret)[-_][A-Za-z0-9]{20,}\b",
        "aws_access_key": r"\bAKIA[0-9A-Z]{16}\b",
        "private_key_header": r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
    }

    # Harmful content indicators (high-level, not comprehensive)
    HARM_PATTERNS: Dict[str, str] = {
        "weapons": r"\b(make|build|create|construct)\s+(a\s+)?(bomb|explosive|weapon|poison)\b",
        "hacking": r"\bhow\s+to\s+(hack|breach|exploit|bypass|crack)\b|\b(hack|breach|exploit|bypass)\s+(into|the|a|someone'?s?)?\s*(account|system|security|password|server|computer)\b",
        "self_harm": r"\bhow\s+to\s+(commit\s+)?suicide\b|\bways\s+to\s+(kill|harm)\s+(myself|yourself)\b",
        "harassment": r"\b(harass|stalk|threaten|intimidate)\s+(my|the|a)?\s*(ex|person|someone)\b",
        "harassment_writing": r"\b(write|help\s+me\s+write|create|compose)\s+.{0,30}(harassment|hate|threatening|abusive)\b",
    }

    def __init__(
        self,
        enable_injection: bool = True,
        enable_jailbreak: bool = True,
        enable_extraction: bool = True,
        enable_pii: bool = True,
        enable_harm: bool = True,
        case_sensitive: bool = False,
        custom_patterns: Optional[Dict[str, Dict[str, str]]] = None,
    ):
        """
        Initialize the pattern matcher.

        Args:
            enable_injection: Check for prompt injection patterns
            enable_jailbreak: Check for jailbreak manipulation patterns
            enable_extraction: Check for system prompt extraction attempts
            enable_pii: Check for PII/sensitive data
            enable_harm: Check for harmful content indicators
            case_sensitive: Whether pattern matching is case-sensitive
            custom_patterns: Additional custom patterns to include
        """
        self.enable_injection = enable_injection
        self.enable_jailbreak = enable_jailbreak
        self.enable_extraction = enable_extraction
        self.enable_pii = enable_pii
        self.enable_harm = enable_harm
        self.case_sensitive = case_sensitive

        # Compile patterns
        flags = 0 if case_sensitive else re.IGNORECASE
        self._compiled_patterns: Dict[ThreatCategory, Dict[str, re.Pattern]] = {}

        if enable_injection:
            self._compiled_patterns[ThreatCategory.PROMPT_INJECTION] = {
                name: re.compile(pattern, flags)
                for name, pattern in self.INJECTION_PATTERNS.items()
            }

        if enable_jailbreak:
            self._compiled_patterns[ThreatCategory.JAILBREAK] = {
                name: re.compile(pattern, flags)
                for name, pattern in self.JAILBREAK_PATTERNS.items()
            }

        if enable_extraction:
            self._compiled_patterns[ThreatCategory.SYSTEM_PROMPT_EXTRACTION] = {
                name: re.compile(pattern, flags)
                for name, pattern in self.EXTRACTION_PATTERNS.items()
            }

        if enable_pii:
            # PII patterns should be case-sensitive for accuracy
            self._compiled_patterns[ThreatCategory.PII_DETECTED] = {
                name: re.compile(pattern, 0 if name in ["ssn", "credit_card", "phone_us"] else flags)
                for name, pattern in self.PII_PATTERNS.items()
            }

        if enable_harm:
            self._compiled_patterns[ThreatCategory.HARMFUL_CONTENT] = {
                name: re.compile(pattern, flags)
                for name, pattern in self.HARM_PATTERNS.items()
            }

        # Add custom patterns
        if custom_patterns:
            for category_name, patterns in custom_patterns.items():
                try:
                    category = ThreatCategory(category_name)
                except ValueError:
                    continue
                if category not in self._compiled_patterns:
                    self._compiled_patterns[category] = {}
                for name, pattern in patterns.items():
                    self._compiled_patterns[category][name] = re.compile(pattern, flags)

    def scan(self, text: str) -> List[PatternMatch]:
        """
        Scan text for all enabled threat patterns.

        Args:
            text: Text to scan

        Returns:
            List of PatternMatch objects for all matches found
        """
        matches = []

        for category, patterns in self._compiled_patterns.items():
            for pattern_name, compiled_pattern in patterns.items():
                for match in compiled_pattern.finditer(text):
                    severity = self._get_severity(category, pattern_name)
                    matches.append(PatternMatch(
                        category=category,
                        pattern_name=pattern_name,
                        matched_text=match.group(),
                        start=match.start(),
                        end=match.end(),
                        severity=severity,
                    ))

        return matches

    def has_threats(self, text: str) -> bool:
        """Check if text contains any threat patterns."""
        for category, patterns in self._compiled_patterns.items():
            for compiled_pattern in patterns.values():
                if compiled_pattern.search(text):
                    return True
        return False

    def get_threat_categories(self, text: str) -> Set[ThreatCategory]:
        """Get all threat categories found in text."""
        categories = set()
        for category, patterns in self._compiled_patterns.items():
            for compiled_pattern in patterns.values():
                if compiled_pattern.search(text):
                    categories.add(category)
                    break
        return categories

    def _get_severity(self, category: ThreatCategory, pattern_name: str) -> str:
        """Determine severity level for a pattern match."""
        # High severity patterns
        high_severity = {
            (ThreatCategory.PROMPT_INJECTION, "system_override"),
            (ThreatCategory.PROMPT_INJECTION, "jailbreak_marker"),
            (ThreatCategory.PROMPT_INJECTION, "dan_mode"),
            (ThreatCategory.HARMFUL_CONTENT, "weapons"),
            (ThreatCategory.HARMFUL_CONTENT, "self_harm"),
            (ThreatCategory.PII_DETECTED, "ssn"),
            (ThreatCategory.PII_DETECTED, "credit_card"),
            (ThreatCategory.PII_DETECTED, "private_key_header"),
        }

        # Critical severity patterns
        critical_severity = {
            (ThreatCategory.HARMFUL_CONTENT, "self_harm"),
        }

        if (category, pattern_name) in critical_severity:
            return "critical"
        elif (category, pattern_name) in high_severity:
            return "high"
        elif category in [ThreatCategory.PROMPT_INJECTION, ThreatCategory.HARMFUL_CONTENT]:
            return "medium"
        else:
            return "low"


# Pre-configured matchers for common use cases
def create_strict_matcher() -> PatternMatcher:
    """Create a matcher with all checks enabled."""
    return PatternMatcher(
        enable_injection=True,
        enable_jailbreak=True,
        enable_extraction=True,
        enable_pii=True,
        enable_harm=True,
    )


def create_chat_matcher() -> PatternMatcher:
    """Create a matcher optimized for chat applications."""
    return PatternMatcher(
        enable_injection=True,
        enable_jailbreak=True,
        enable_extraction=True,
        enable_pii=True,
        enable_harm=True,
    )


def create_agent_matcher() -> PatternMatcher:
    """Create a matcher optimized for autonomous agents."""
    return PatternMatcher(
        enable_injection=True,
        enable_jailbreak=True,
        enable_extraction=True,
        enable_pii=True,
        enable_harm=True,
    )
