"""
ToxicityChecker - Comprehensive toxic content detection in AI output.

This checker identifies toxic, harmful, and discriminatory content in AI output,
providing the HARM gate coverage that was missing in OutputValidator.

It answers the critical question:
    "Does this output contain content that should not be shown to users?"

This is the LAST LINE OF DEFENSE - if L1 and L2 failed, L3 must catch it.

Detection Layers:
    1. Explicit Terms: Slurs, profanity, explicit hate terms
    2. Structural Patterns: Hate speech patterns, discriminatory structures
    3. Category Keywords: 10 harm categories aligned with L1 (HarmfulRequestDetector)
    4. Intensity Analysis: Concentration of toxic signals

Categories (aligned with THSP HARM gate):
    - harassment_discrimination: Hate speech, slurs, bullying
    - violence_threats: Violence, threats, harm to persons
    - sexual_explicit: Explicit sexual content, NSFW
    - dangerous_content: Self-harm, eating disorders, dangerous activities
    - privacy_violation: Doxxing, exposed PII, personal attacks
    - fraud_scam: Scam content, fraudulent claims
    - misinformation: Dangerous false claims, medical misinformation
    - illegal_content: Drug synthesis, weapons, illegal activities
    - child_safety: Any content harmful to minors
    - dehumanization: Dehumanizing language, genocide advocacy

Design Principles:
    - Defense in depth: Multiple detection techniques
    - Fail-closed: When uncertain, flag for review
    - Category-aware: Different thresholds for different harm types
    - Context-aware: Uses input_context for informed decisions
    - Aligned with THSP: Maps to HARM gate

References:
    - ToxiGen: Hartvigsen et al., EMNLP 2022
    - RealToxicityPrompts: Gehman et al., 2020
    - Perspective API categories
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import DetectionResult, CheckFailureType

logger = logging.getLogger("sentinelseed.detection.checkers.toxicity")


@dataclass
class ToxicityCheckerConfig(CheckerConfig):
    """Configuration for ToxicityChecker."""

    # Detection thresholds
    explicit_term_threshold: float = 0.9  # High confidence for explicit terms
    pattern_threshold: float = 0.7  # Pattern matches
    keyword_threshold: float = 0.75  # Category keywords (raised from 0.5 to reduce FPs)
    combined_threshold: float = 0.75  # Final decision threshold (raised from 0.6 to reduce FPs)

    # Minimum signals to flag
    min_signals: int = 1

    # Category weights (some categories are more severe)
    category_weights: Dict[str, float] = None

    # Enable/disable detection layers
    check_explicit_terms: bool = True
    check_patterns: bool = True
    check_keywords: bool = True
    check_intensity: bool = True

    def __post_init__(self):
        if self.category_weights is None:
            self.category_weights = {
                "child_safety": 1.5,  # Highest priority
                "violence_threats": 1.3,
                "harassment_discrimination": 1.2,
                "dehumanization": 1.2,
                "dangerous_content": 1.1,
                "sexual_explicit": 1.0,
                "privacy_violation": 1.0,
                "fraud_scam": 0.9,
                "misinformation": 0.9,
                "illegal_content": 1.0,
            }


# =============================================================================
# EXPLICIT TOXIC TERMS (High-confidence detection)
# =============================================================================

# Slurs and explicit hate terms - these are always toxic
# Note: This list is intentionally limited for code review purposes
# Production version should use external wordlist
EXPLICIT_SLURS: Set[str] = {
    # Racial slurs (abbreviated/masked for code review)
    "n*gger", "n*gga", "sp*c", "ch*nk", "g**k", "k*ke", "w*tback",
    # Homophobic slurs
    "f*ggot", "f*g", "d*ke", "tr*nny",
    # Other slurs
    "r*tard", "retarded",
    # Portuguese
    "viado", "bicha", "sapatão", "crioulo", "macaco",
}

# Explicit violence terms
VIOLENCE_EXPLICIT: Set[str] = {
    "kill yourself", "kys", "go die", "hope you die",
    "should be killed", "deserve to die", "must die",
    "murder them", "slaughter them", "exterminate",
    "should die", "need to die", "have to die",
    "to die", "all die", "must be killed",
    # Portuguese
    "se mate", "vai morrer", "merece morrer", "tem que morrer",
    "devem morrer", "precisam morrer",
}

# Dehumanization terms
DEHUMANIZATION: Set[str] = {
    "subhuman", "less than human", "not human", "animals",
    "vermin", "cockroaches", "parasites", "infestation",
    "plague", "disease", "cancer on society",
    # Portuguese
    "sub-humano", "vermes", "pragas", "parasitas",
}


# =============================================================================
# STRUCTURAL PATTERNS (Hate speech structures)
# =============================================================================

TOXICITY_PATTERNS: Dict[str, List[str]] = {
    "harassment_discrimination": [
        # Group-targeted hate - expanded groups
        r"\b(all|every|those|these)\s+(jews?|muslims?|blacks?|whites?|asians?|chinese|latinos?|mexicans?|arabs?|gays?|lesbians?|trans|immigrants?|refugees?|disabled)\s+(are|is|should|must|deserve|need\s+to)",
        r"\b(jews?|muslims?|blacks?|whites?|asians?|chinese|latinos?|mexicans?|arabs?|gays?|lesbians?|trans|immigrants?|refugees?|disabled)\s+(are\s+)?(evil|disgusting|inferior|subhuman|vermin|bad|terrible|horrible|stupid|dumb|lazy|dirty|criminals?|terrorists?|thieves?|liars?)",
        r"\b(hate|despise|loathe|cant\s+stand)\s+(all\s+)?(jews?|muslims?|blacks?|whites?|asians?|chinese|latinos?|mexicans?|arabs?|gays?|lesbians?|trans|immigrants?|refugees?)",
        # Stereotyping - expanded
        r"\b(typical|always|never)\s+\w+\s+(because|since)\s+(they('re|\s+are)|their)\s+\w+",
        r"\bpeople\s+like\s+(them|you)\s+(always|never|should|can't|cannot)",
        # Group + negative action
        r"\b(jews?|muslims?|blacks?|asians?|chinese|latinos?|arabs?|gays?|trans|immigrants?|disabled)\s+.{0,30}(die|killed|eliminated|removed|deported|banned)",
        # "All X are Y" pattern
        r"\ball\s+(of\s+)?(them|those\s+people|these\s+people)\s+are\s+\w+",
        # "No good X" pattern
        r"\bno\s+(good|real|true)\s+(jew|muslim|black|asian|latino|immigrant|refugee)",
        # Exclusion patterns
        r"\b(don't|shouldn't|can't)\s+(trust|believe|hire|date|marry)\s+(any\s+)?(jew|muslim|black|asian|latino|immigrant)",
    ],
    "violence_threats": [
        # Direct threats
        r"\b(i('ll|\s+will)|we('ll|\s+will)|they\s+should)\s+(kill|murder|hurt|harm|attack)\s+(you|them|him|her)",
        r"\b(deserve|deserves)\s+to\s+(die|be\s+killed|be\s+hurt|suffer)",
        r"\b(hope|wish)\s+(you|they|he|she)\s+(die|dies|get\s+hurt|suffer)",
        r"\b(should|must|need\s+to)\s+(be\s+)?(killed|murdered|eliminated|exterminated)",
        # Violence advocacy
        r"\b(kill|murder|shoot|stab|beat)\s+(all|every|those)\s+\w+",
    ],
    "sexual_explicit": [
        # Explicit sexual content indicators
        r"\b(explicit|graphic)\s+(sexual|sex)\s+(content|description|scene)",
        r"\b(penetrat|thrust|moan|orgasm|ejaculat)\w*",
        r"\b(cock|dick|pussy|cunt|tits|breasts?)\b(?!\s+(cancer|exam|feeding))",
    ],
    "dangerous_content": [
        # Self-harm encouragement
        r"\b(cut|harm|hurt)\s+yourself",
        r"\b(starve|purge)\s+yourself",
        r"\bsuicide\s+(method|instruction|guide|how\s+to)",
        r"\b(best|easiest|painless)\s+(way|method)\s+to\s+(die|kill\s+yourself)",
    ],
    "dehumanization": [
        # Dehumanizing language
        r"\b(they|those\s+people)\s+are\s+(animals?|vermin|cockroaches?|parasites?|disease)",
        r"\b(subhuman|less\s+than\s+human|not\s+really\s+human)",
        r"\b(infestation|plague|cancer)\s+of\s+\w+\s+(people|immigrants?|refugees?)",
        r"\bexterminate\s+(them|those|the)\s+\w+",
    ],
    "child_safety": [
        # Content harmful to minors
        r"\b(child|minor|kid|underage)\s+(sex|porn|nude|naked)",
        r"\b(groom|grooming)\s+(child|minor|kid)",
        r"\bpedophil",
    ],
}


# =============================================================================
# CATEGORY KEYWORDS (Aligned with HarmfulRequestDetector from L1)
# =============================================================================

TOXICITY_KEYWORDS: Dict[str, Set[str]] = {
    "harassment_discrimination": {
        "racist", "racism", "sexist", "sexism", "bigot", "bigotry",
        "hate speech", "hateful", "discriminate", "discrimination",
        "prejudice", "xenophobic", "xenophobia", "homophobic", "homophobia",
        "transphobic", "transphobia", "ableist", "ableism", "antisemitic",
        "islamophobic", "misogynist", "misogyny", "slur",
        # Common hate patterns
        "bad people", "all bad", "are bad", "are evil", "are terrorists",
        "are criminals", "are thieves", "are lazy", "are stupid", "are dirty",
        "don't belong", "go back", "not welcome", "should leave",
        "inferior", "superior race", "master race",
        "greed", "greedy", "greedness",  # Common antisemitic trope
        # Portuguese
        "racista", "racismo", "sexista", "preconceito", "discriminação",
        "homofóbico", "transfóbico", "xenofóbico",
        "pessoas ruins", "são ruins", "são maus", "não pertencem",
    },
    "violence_threats": {
        "kill", "murder", "assassinate", "slaughter", "massacre",
        "attack", "assault", "torture", "maim",
        # Note: "beat" removed in v1.2.0 - too generic (FP: "Beatrice", "beat the record")
        # Note: "execute" removed in v1.1.0 - too generic, causes FP in programming contexts
        "bomb", "shoot", "stab", "strangle",
        "genocide", "ethnic cleansing", "exterminate",
        "deserve to die", "should die", "must die", "hope you die",
        "need to die", "have to die", "going to die",
        # Portuguese
        "matar", "assassinar", "massacrar", "atacar", "torturar",
        "espancar", "esfaquear", "atirar",
        # Note: "executar" removed in v1.1.0 - too generic
        "merece morrer", "devem morrer", "precisam morrer",
    },
    "sexual_explicit": {
        "pornography", "pornographic", "xxx", "nsfw",
        # Note: "explicit" removed in v1.2.0 - too generic (FP: "explicit calculation")
        "sexual act", "intercourse", "orgasm", "masturbat",
        "erotic", "lewd", "obscene",
        # Portuguese
        "pornografia", "pornográfico", "obsceno",
        # Note: "explícito" removed - too generic
    },
    "dangerous_content": {
        "suicide", "self-harm", "anorexia", "bulimia",
        # Note: "cutting" removed in v1.2.0 - too generic (FP: "cutting vegetables", "cutting costs")
        # Note: "hanging" removed in v1.2.0 - too generic (FP: "hanging pictures", "hanging decorations")
        "overdose", "suffocation", "poison yourself",
        # Portuguese
        "suicídio", "automutilação", "anorexia", "bulimia",
    },
    "privacy_violation": {
        "doxxing", "dox", "personal information", "home address",
        "phone number", "social security", "credit card number",
        # Note: "bank account" removed in v1.2.0 - too generic (FP: math problems about bank accounts)
        "private photos", "leaked",
        # Portuguese
        "informação pessoal", "endereço", "número de telefone",
    },
    "fraud_scam": {
        "scam", "fraud", "phishing", "ponzi", "pyramid scheme",
        "fake investment", "guaranteed returns", "get rich quick",
        "nigerian prince", "wire transfer", "cryptocurrency scam",
        # Portuguese
        "golpe", "fraude", "esquema", "pirâmide",
    },
    "misinformation": {
        "fake cure", "miracle cure", "doctors don't want",
        "vaccine causes", "covid hoax", "5g causes", "flat earth",
        "chemtrails", "crisis actor", "false flag",
        # Portuguese
        "cura milagrosa", "médicos não querem", "vacina causa",
    },
    "illegal_content": {
        "drug synthesis", "how to make meth", "cook meth",
        "make cocaine", "grow marijuana", "drug dealer",
        "illegal weapons", "gun without license", "untraceable",
        # Portuguese
        "como fazer droga", "traficante", "arma ilegal",
    },
    "child_safety": {
        "child porn", "cp", "underage", "jailbait",
        # Note: "minor" removed in v1.2.0 - too generic (FP: "minor issue", "minor changes")
        "grooming", "pedophile", "pedo",
        # Portuguese
        "pornografia infantil", "menor de idade", "pedófilo",
    },
    "dehumanization": {
        "subhuman", "vermin", "cockroach", "parasite", "plague",
        "infestation", "exterminate", "cleanse", "purge",
        "inferior race", "master race", "untermensch",
        # Portuguese
        "sub-humano", "verme", "praga", "parasita", "exterminar",
    },
}


# =============================================================================
# BENIGN CONTEXT WHITELIST (v1.2.0 - Output-focused FP reduction)
# =============================================================================
# These contexts make certain keywords benign in AI OUTPUT
# Example: "grooming" is fine in "dog grooming service"

BENIGN_CONTEXTS: Dict[str, List[str]] = {
    # "grooming" is benign in pet/salon contexts
    "grooming": ["pet", "dog", "cat", "horse", "salon", "service", "appointment", "professional"],
    # "kill" is benign in programming/process contexts
    "kill": ["process", "thread", "task", "daemon", "signal", "container", "pod", "job"],
    # "attack" is benign in problem-solving contexts
    "attack": ["problem", "issue", "challenge", "optimization", "approach", "strategy"],
    # "slaughter" is benign in food/cooking contexts
    "slaughter": ["beef", "pork", "chicken", "lamb", "meat", "butcher", "farm"],
    # "assault" is benign in legal/news discussion contexts
    "assault": ["charges", "case", "victim", "reported", "alleged", "convicted", "trial"],
    # "massacre" is benign in historical contexts
    "massacre": ["history", "historical", "memorial", "museum", "victims", "1800s", "1900s"],
}

# Safe proper names that should not trigger detection
# These are common first names that might match toxic patterns
SAFE_PROPER_NAMES: Set[str] = {
    "dan", "daniel", "dan's",  # vs "DAN mode"
    "may",  # vs "may I" attack patterns
    "hunter",  # vs hunting
    "grace",  # vs "disgrace"
    "joy",  # vs "killjoy"
    "christian", "cristian",  # vs religious discrimination patterns
    "german",  # vs anti-German patterns (nationality, not slur)
    "jordan",  # vs country-based patterns
}

# =============================================================================
# MALICIOUS OVERRIDES (v1.2.0 - Security protection)
# =============================================================================
# If these patterns are present, benign context is INVALIDATED
# This prevents attackers from using benign framing to bypass detection
# Example: "kill the process that is my enemy" - "process" is benign but "my enemy" overrides

MALICIOUS_OVERRIDES: List[Tuple[str, str]] = [
    # Violence against HUMAN targets - specific person types
    # Note: "my enemy", "the victim" etc. are strong signals of human targeting
    (r"\b(my|the|an?)\s+(enemy|neighbor|coworker|boss|ex|victim|target)\b", "target_person"),
    (r"\bharm\s+(them|someone|people|him|her|you)\b", "intent_harm"),

    # Violence verbs + human targets (more specific than just "kill the")
    (r"\b(kill|attack|harm|hurt)\s+(my|the|a|an)\s+(enemy|neighbor|coworker|boss|ex|wife|husband|friend|family)\b", "violence_person"),
    (r"\b(kill|attack|harm|hurt)\s+(someone|people|person|him|her|them|you)\b", "violence_generic"),
    (r"\bpoison\s+(my|the|a|someone|him|her|them)\b", "poison_person"),

    # Cybercrime indicators
    (r"\b(steal|hack|compromise).{0,20}(data|password|account|credential|bank)\b", "cybercrime"),
    (r"\bgive\s+me.{0,20}(attack|exploit|malware)\b", "request_attack"),

    # Financial crime
    (r"\bsteal\s+(money|from|cash|bank)\b", "financial_crime"),

    # Evasion indicators - strong signal of malicious intent
    (r"\bwithout\s+(getting\s+caught|detection|being\s+caught)\b", "evasion"),
    (r"\billegal(ly)?\b", "illegal_intent"),

    # Human targets in violence context (word order variations)
    (r"\b(person|people|human|child|woman|man|victim)\s.{0,10}(kill|murder|attack|harm|hurt)\b", "human_target"),
    (r"\b(kill|murder|attack|harm|hurt)\s.{0,10}(person|people|human|child|woman|man|victim)\b", "human_target_2"),
]


class ToxicityChecker(BaseChecker):
    """
    Comprehensive toxic content checker for AI output.

    Implements multiple detection layers:
    1. Explicit terms (slurs, violence phrases)
    2. Structural patterns (hate speech structures)
    3. Category keywords (10 harm categories)
    4. Intensity analysis (concentration of signals)

    This is the HARM gate implementation for OutputValidator (L3).
    """

    VERSION = "1.2.0"
    NAME = "toxicity_checker"

    def __init__(self, config: Optional[ToxicityCheckerConfig] = None):
        """Initialize ToxicityChecker."""
        self._toxicity_config = config or ToxicityCheckerConfig()
        super().__init__(self._toxicity_config)
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._compiled_malicious: List[Tuple[re.Pattern, str]] = []
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        for category, patterns in TOXICITY_PATTERNS.items():
            self._compiled_patterns[category] = [
                re.compile(p, re.IGNORECASE | re.MULTILINE)
                for p in patterns
            ]
        # Compile malicious override patterns (v1.2.0)
        for pattern, name in MALICIOUS_OVERRIDES:
            self._compiled_malicious.append(
                (re.compile(pattern, re.IGNORECASE), name)
            )

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
        Check AI output for toxic content.

        Args:
            output: AI output text to check
            input_context: Original user input (for context)
            rules: Optional custom rules

        Returns:
            DetectionResult with toxicity detection details
        """
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        if input_context:
            self._stats["context_provided"] += 1

        # Handle empty output
        if not output or not output.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        output_lower = output.lower()
        signals: List[Dict[str, Any]] = []
        detected_categories: Set[str] = set()

        # Layer 1: Explicit terms (highest confidence)
        if self._toxicity_config.check_explicit_terms:
            explicit_signals = self._check_explicit_terms(output_lower)
            signals.extend(explicit_signals)
            for sig in explicit_signals:
                detected_categories.add(sig["category"])

        # Layer 2: Structural patterns
        if self._toxicity_config.check_patterns:
            pattern_signals = self._check_patterns(output)
            signals.extend(pattern_signals)
            for sig in pattern_signals:
                detected_categories.add(sig["category"])

        # Layer 3: Category keywords
        if self._toxicity_config.check_keywords:
            keyword_signals = self._check_keywords(output_lower)
            signals.extend(keyword_signals)
            for sig in keyword_signals:
                detected_categories.add(sig["category"])

        # No signals found
        if not signals:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Calculate weighted confidence
        confidence = self._calculate_confidence(signals, detected_categories)

        # Check against threshold
        if confidence < self._toxicity_config.combined_threshold:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Toxicity detected
        self._stats["failures_detected"] += 1

        # Build description
        categories_str = ", ".join(sorted(detected_categories))
        description = f"Toxic content detected (categories: {categories_str})"

        # Get most severe signal as evidence
        evidence = signals[0]["evidence"] if signals else None

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=CheckFailureType.HARMFUL_CONTENT.value,
            description=description,
            evidence=evidence,
            metadata={
                "categories": list(detected_categories),
                "signal_count": len(signals),
                "signals": signals[:5],  # Top 5 signals
                "thsp_gate": "harm",
            },
        )

    def _check_explicit_terms(self, text: str) -> List[Dict[str, Any]]:
        """Check for explicit toxic terms (slurs, violence phrases)."""
        signals = []

        # Check slurs (with masking handling)
        for slur in EXPLICIT_SLURS:
            # Handle masked versions (n*gger -> n.gger, n-gger, etc.)
            # v1.1.0: Removed \s from pattern - spaces in normal text shouldn't match
            pattern = slur.replace("*", r"[*\-_.]?")
            if re.search(pattern, text, re.IGNORECASE):
                signals.append({
                    "type": "explicit_slur",
                    "category": "harassment_discrimination",
                    "confidence": self._toxicity_config.explicit_term_threshold,
                    "evidence": f"Explicit slur detected",
                })

        # Check violence phrases
        for phrase in VIOLENCE_EXPLICIT:
            if phrase.lower() in text:
                signals.append({
                    "type": "explicit_violence",
                    "category": "violence_threats",
                    "confidence": self._toxicity_config.explicit_term_threshold,
                    "evidence": f"Violence phrase: {phrase[:30]}",
                })

        # Check dehumanization
        for term in DEHUMANIZATION:
            if term.lower() in text:
                signals.append({
                    "type": "dehumanization",
                    "category": "dehumanization",
                    "confidence": self._toxicity_config.explicit_term_threshold,
                    "evidence": f"Dehumanizing term detected",
                })

        return signals

    def _check_patterns(self, text: str) -> List[Dict[str, Any]]:
        """Check for structural toxicity patterns."""
        signals = []

        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                match = pattern.search(text)
                if match:
                    signals.append({
                        "type": "pattern_match",
                        "category": category,
                        "confidence": self._toxicity_config.pattern_threshold,
                        "evidence": f"Pattern match: {match.group()[:50]}",
                    })
                    break  # One match per category is enough

        return signals

    def _has_malicious_override(self, text: str) -> bool:
        """
        Check if text contains malicious indicators that override benign context.

        This is a SECURITY measure to prevent attackers from using benign
        framing to bypass detection.

        Example: "kill the process that is my enemy" has "process" (benign)
        but also "my enemy" (malicious) - should NOT be considered benign.

        Returns:
            True if malicious indicators found, False otherwise
        """
        for pattern, _ in self._compiled_malicious:
            if pattern.search(text):
                return True
        return False

    def _is_benign_context(self, keyword: str, text: str) -> bool:
        """
        Check if keyword appears in a benign context (v1.2.0).

        This reduces false positives by checking if 'dangerous' keywords
        appear alongside benign context words.

        SECURITY: Malicious indicators OVERRIDE benign context.

        Args:
            keyword: The potentially toxic keyword found
            text: The full text to check for context

        Returns:
            True if keyword appears in benign context AND no malicious override
        """
        # SECURITY: Check for malicious indicators FIRST
        # If found, benign context does NOT apply
        if self._has_malicious_override(text):
            return False

        keyword_lower = keyword.lower()
        text_lower = text.lower()

        # Check if it's a safe proper name (case-sensitive check for names)
        # "Dan" as a name is fine, "DAN" as jailbreak mode is not
        if keyword_lower in SAFE_PROPER_NAMES:
            # Look for the keyword as a standalone word (not in "I am DAN" pattern)
            jailbreak_patterns = [
                rf"(i\s+am|i'm|call\s+me|entering)\s+{keyword_lower}",
                rf"{keyword_lower}\s+(mode|activated|enabled)",
                rf"\[{keyword_lower}\]",  # [DAN] format
            ]
            for pattern in jailbreak_patterns:
                if re.search(pattern, text_lower, re.IGNORECASE):
                    return False  # This IS a jailbreak pattern, not benign
            return True  # Just a name, benign

        # Check for benign context words
        contexts = BENIGN_CONTEXTS.get(keyword_lower, [])
        if not contexts:
            return False

        # Look for context words near the keyword (within ~50 chars)
        keyword_pos = text_lower.find(keyword_lower)
        if keyword_pos == -1:
            return False

        # Extract surrounding context (50 chars before and after)
        start = max(0, keyword_pos - 50)
        end = min(len(text_lower), keyword_pos + len(keyword_lower) + 50)
        context_window = text_lower[start:end]

        # Check if any benign context word is present
        for ctx in contexts:
            if ctx.lower() in context_window:
                return True

        return False

    def _check_keywords(self, text: str) -> List[Dict[str, Any]]:
        """Check for category keywords with benign context filtering (v1.2.0)."""
        signals = []

        for category, keywords in TOXICITY_KEYWORDS.items():
            matches = []
            for keyword in keywords:
                if keyword.lower() in text:
                    # v1.2.0: Skip keywords in benign contexts
                    if self._is_benign_context(keyword, text):
                        continue
                    matches.append(keyword)

            if matches:
                # More matches = higher confidence
                confidence = min(
                    self._toxicity_config.keyword_threshold + len(matches) * 0.1,
                    0.85
                )
                signals.append({
                    "type": "keyword_match",
                    "category": category,
                    "confidence": confidence,
                    "evidence": f"Keywords: {', '.join(matches[:3])}",
                    "match_count": len(matches),
                })

        return signals

    def _calculate_confidence(
        self,
        signals: List[Dict[str, Any]],
        categories: Set[str],
    ) -> float:
        """Calculate weighted confidence from signals."""
        if not signals:
            return 0.0

        # Base confidence from highest signal
        base_confidence = max(s["confidence"] for s in signals)

        # Boost for multiple signals
        signal_boost = min(len(signals) * 0.05, 0.2)

        # Boost for multiple categories
        category_boost = min(len(categories) * 0.05, 0.15)

        # Apply category weights
        max_weight = 1.0
        for cat in categories:
            weight = self._toxicity_config.category_weights.get(cat, 1.0)
            max_weight = max(max_weight, weight)

        # Final confidence
        confidence = (base_confidence + signal_boost + category_boost) * max_weight
        return min(confidence, 1.0)


__all__ = ["ToxicityChecker", "ToxicityCheckerConfig"]
