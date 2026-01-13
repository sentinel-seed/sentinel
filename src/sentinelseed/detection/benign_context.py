"""
Benign Context Detection Module for Sentinel v3.0

This module provides pattern-based detection of benign contexts
where 'dangerous' words are used legitimately (e.g., "kill the process").

The goal is to reduce false positives without creating bypass opportunities.
"""

import re
from typing import List, Tuple, Set
from dataclasses import dataclass


@dataclass
class BenignMatch:
    """Represents a detected benign context."""
    pattern_name: str
    matched_text: str
    category: str


# Technical/Programming contexts
BENIGN_TECH_PATTERNS = [
    # Process management
    (r'\bkill\s+(the\s+)?(process|thread|task|job|daemon|service|container|pod|worker)\b',
     "benign_kill_process", "programming"),
    (r'\bkill\s+(all\s+)?(background|zombie|orphan|hung)\s+(process|task)e?s?\b',
     "benign_kill_background", "programming"),
    (r'\bterminate\s+(the\s+|a\s+)?(process|thread|connection|session|task)\b',
     "benign_terminate_process", "programming"),
    (r'\bkill\s+-\d+\b', "benign_kill_signal", "programming"),
    (r'\bpkill\b|\bkillall\b', "benign_unix_kill", "programming"),
    (r'\bdebug\s+(the\s+|this\s+|a\s+)?(memory|leak|issue|bug|error|crash)\b',
     "benign_debug", "programming"),
    (r'\bmemory\s+leak\b', "benign_memory_leak", "programming"),

    # Problem-solving metaphors (expanded)
    (r'\battack\s+(the\s+|a\s+|this\s+)?(problem|issue|challenge|task|question|bug|optimization)\b',
     "benign_attack_problem", "metaphor"),
    (r'\b(attack|tackle|approach)\s+this\s+\w+\s+(problem|systematically)\b',
     "benign_attack_problem_2", "metaphor"),
    (r'\btackle\s+(the\s+|a\s+|this\s+)?(problem|issue|challenge)\b',
     "benign_tackle_problem", "metaphor"),

    # Business/competitive (more specific to avoid bypass)
    (r'\b(steal|stealing)\s+(our|their|the\s+)?(customers?|market\s+share|clients?|business|thunder)\b',
     "benign_business_steal", "business"),
    (r'\bcompetitors?.{0,20}(steal|stealing)\b',
     "benign_business_competitors", "business"),
    (r'\bexploit\s+(this\s+|the\s+|an?\s+)?(opportunity|chance|advantage|gap|opening)\b',
     "benign_exploit_opportunity", "business"),
    (r'\bpredatory\s+pricing\b', "benign_business_predatory", "business"),
    (r'\bkiller\s+(app|feature|product)\b', "benign_killer_app", "business"),

    # Security education (defensive)
    (r'\b(how\s+to\s+)?(prevent|defend\s+against|protect\s+from|mitigate)\s+.{0,30}(attack|injection|xss|vulnerability|exploit)\b',
     "benign_security_defense", "security_education"),
    (r'\bwhat\s+is\s+.{0,20}(sql\s+injection|xss|csrf|buffer\s+overflow)\b',
     "benign_security_education", "security_education"),

    # Health/medical (legitimate) - expanded
    (r'\bdrug\s*(store|pharmacy|prescription|interaction|trial|therapy|treatment)\b',
     "benign_drugstore", "health"),
    (r'\bvaccine\s*(schedule|efficacy|side\s+effects?|trials?|research|work|prevent)?\b',
     "benign_vaccine_education", "health"),
    (r'\bhow\s+do\s+vaccines\s+work\b', "benign_vaccine_how", "health"),
    (r'\bcold\s+medicine\b', "benign_cold_medicine", "health"),
    (r'\bat\s+the\s+drugstore\b', "benign_at_drugstore", "health"),
    (r'\btrack\s+(sleepwalking|sleep)\b', "benign_sleep_tracking", "health"),
    (r'\bmonitor.{0,20}(sleep|own|her|his)\b', "benign_self_monitoring", "health"),

    # Chemistry/science education
    (r'\b(in\s+)?(chemistry|organic\s+chem|biochemistry).{0,30}(react|synthesis|compound)\b',
     "benign_chem_education", "chemistry"),
    (r'\b(chlorine|sodium|hydrogen|oxygen)\s+(gas\s+)?(reacts?|combines?|produces?)\b',
     "benign_chem_reaction", "chemistry"),
    (r'\bdecomposition\s+of\b', "benign_decomposition", "chemistry"),

    # Mathematics/statistics
    (r'\bcounterfeit\s*(die|dice|coin)\b', "benign_math_counterfeit", "math"),
    (r'\bbiased\s+(die|dice|coin|sample|estimator)\s+(is|to|show)\b',
     "benign_math_biased", "math"),
    (r'\bin\s+probability\b', "benign_probability", "math"),
    (r'\bexpected\s+value\b', "benign_expected_value", "math"),
    (r'\bunrestricted\s+(model|var|regression)\b', "benign_stats_unrestricted", "statistics"),

    # Historical/narrative - expanded
    (r'\b(in\s+)?(history|medieval|ancient|historical).{0,30}(sword|battle|war|weapon|soldier)\b',
     "benign_historical", "history"),
    (r'\bhistory\s+of\s+.{0,30}(power|plant|nuclear|energy)\b',
     "benign_history_of", "history"),
    (r'\bwhat.{0,10}history\s+of\b', "benign_history_question", "history"),
    (r'\b(javelin|sword|spear|bow|arrow).{0,15}(throw|threw|shooting|competition|battle)\b',
     "benign_historical_weapon", "history"),
    (r'\bsoldiers\s+used\s+(swords?|javelin|weapon)\b',
     "benign_historical_soldiers", "history"),
    (r'\bgreat\s+dragon\b', "benign_fantasy", "fiction"),
    (r'\brock\s+opera\b', "benign_music", "arts"),
    (r'\bwitness.{0,20}murder\b', "benign_narrative_witness", "arts"),

    # Academic/educational - expanded
    (r'\b(which\s+of\s+the\s+following|multiple\s+choice|true\s+or\s+false|fill\s+in\s+the\s+blank)\b',
     "benign_academic_format", "academic"),
    (r'\baccording\s+to\s+(kant|rawls|aristotle|plato|mill|bentham)\b',
     "benign_philosophy", "academic"),
    (r'\b(thought\s+experiment|trolley\s+problem|ticking\s+bomb\s+scenario)\b',
     "benign_ethics_thought", "academic"),
    (r'\b(ethics|ethical)\s+scenario\b', "benign_ethics_scenario", "academic"),
    (r'\bmorality\s+demands\b', "benign_morality", "academic"),
    (r'\bmorally\s+justified\b', "benign_moral_justified", "academic"),

    # Legal/policy education
    (r'\b(in\s+)?(law\s+school|legal\s+studies|case\s+study).{0,30}(defendant|plaintiff|prisoner)\b',
     "benign_legal_education", "legal"),
    (r'\b(history\s+of|when\s+did).{0,30}(become\s+illegal|legal\s+status)\b',
     "benign_legal_history", "legal"),
    (r'\bunder\s+international\s+law\b', "benign_international_law", "legal"),
    (r'\bpiracy.{0,20}(illegal|law|high\s+seas)\b', "benign_piracy_legal", "legal"),

    # DIY/tools
    (r'\bheat\s+gun\b', "benign_heat_gun", "tools"),
    (r'\bglue\s+gun\b', "benign_glue_gun", "tools"),
    (r'\bpaintball\s+gun\b', "benign_paintball", "recreation"),
    (r'\bnerf\s+gun\b', "benign_nerf", "recreation"),
    (r'\bplaying\s+with.{0,20}guns?\b', "benign_playing_guns", "recreation"),
    (r'\bsummer\s+camp\b', "benign_summer_camp", "recreation"),

    # Metaphorical language
    (r'\bdevour\s+(books?|content|information|works?)\b', "benign_metaphor_devour", "metaphor"),
    (r'\blike\s+poison\b', "benign_simile_poison", "metaphor"),
    (r'\bavoid.{0,20}like\s+poison\b', "benign_avoid_poison", "metaphor"),
    (r'\bkilling\s+(it|time)\b', "benign_idiom_killing", "idiom"),
    (r'\bdead\s+(tired|serious|wrong)\b', "benign_idiom_dead", "idiom"),

    # Religion/ethics education
    (r'\breligious\s+groups?\b', "benign_religious", "religion"),
    (r'\bposition\s+that.{0,30}(abortion|euthanasia|cloning)\b',
     "benign_position_ethics", "ethics"),
    (r'\bheroin\s+use\s+(after|during|research|study)\b', "benign_drug_research", "research"),
    (r'\bvietnam\s+veterans\b', "benign_veterans", "history"),

    # Logic/formal
    (r'\bpredicate\s+logic\b', "benign_logic", "academic"),
    (r'\bdemocracy\s+is\b', "benign_democracy", "politics"),
    (r'\bclaim\s+the\s+right\b', "benign_claim_right", "politics"),
]

# Contexts that indicate discussion, not instruction
DISCUSSION_INDICATORS = [
    (r'^(what|how|why|when|where)\s+(is|are|do|does|did|was|were)\b', "question_format"),
    (r'\b(explain|describe|discuss|analyze|compare)\s+(the|how|what|why)\b', "academic_verb"),
    (r'\bfor\s+(my|a)\s+(novel|book|story|screenplay|essay|paper|thesis)\b', "fiction_context"),
    (r'\bin\s+(the|my)\s+(rpg|dnd|d&d|game|campaign)\b', "roleplay_context"),
    (r'\bfor\s+(educational|research|academic)\s+purposes\b', "educational_context"),
]

# Malicious indicators that OVERRIDE benign context
# If these appear, the benign match is invalidated
MALICIOUS_OVERRIDES = [
    # Violence against people
    (r'\b(my|the|an?)\s+(enemy|neighbor|coworker|boss|ex|victim)\b', "target_person"),
    (r'\bharm\s+(them|someone|people|him|her)\b', "intent_harm"),
    (r'\battack\s+(my|the|a)\s+(neighbor|coworker|enemy|person)\b', "attack_person"),
    (r'\bpoison\s+(my|the|a|someone)\b', "poison_person"),
    (r'\bkill\s+(my|the|a|someone|people)\b', "kill_person"),

    # Cybercrime
    (r'\b(steal|hack|compromise).{0,20}(data|password|account|credential|bank)\b', "cybercrime"),
    (r'\bgive\s+me.{0,20}(attack|exploit|malware)\b', "request_attack"),
    (r'\b(sql\s+injection|xss).{0,10}attack\b', "request_cyber_attack"),

    # Financial crime
    (r'\bsteal\s+(money|from|cash|bank)\b', "financial_crime"),

    # Illegal activity indicators
    (r'\bwithout\s+(getting\s+caught|detection|being\s+caught)\b', "evasion"),
    (r'\billegal(ly)?\b', "illegal_intent"),
]


class BenignContextDetector:
    """
    Detects benign contexts in user input to reduce false positives.

    IMPORTANT: Benign context REDUCES risk score but does NOT eliminate it.
    Malicious intent combined with benign framing should still be blocked.

    CRITICAL: If malicious indicators are present, benign matches are INVALIDATED.
    """

    def __init__(self):
        # Compile all patterns for efficiency
        self.tech_patterns = [
            (re.compile(pattern, re.IGNORECASE), name, category)
            for pattern, name, category in BENIGN_TECH_PATTERNS
        ]
        self.discussion_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in DISCUSSION_INDICATORS
        ]
        self.malicious_patterns = [
            (re.compile(pattern, re.IGNORECASE), name)
            for pattern, name in MALICIOUS_OVERRIDES
        ]

    def _has_malicious_indicators(self, text: str) -> Tuple[bool, List[str]]:
        """Check if text contains malicious indicators that override benign context."""
        malicious_found = []
        for pattern, name in self.malicious_patterns:
            if pattern.search(text):
                malicious_found.append(name)
        return len(malicious_found) > 0, malicious_found

    def check(self, text: str) -> Tuple[bool, List[BenignMatch], float]:
        """
        Check if text contains benign context.

        Returns:
            - is_benign: True if benign context detected AND no malicious override
            - matches: List of BenignMatch objects with details
            - reduction_factor: How much to reduce risk (0.0-1.0)
        """
        # FIRST: Check for malicious indicators
        has_malicious, malicious_types = self._has_malicious_indicators(text)
        if has_malicious:
            # Malicious indicators OVERRIDE any benign context
            return False, [], 1.0

        matches: List[BenignMatch] = []
        categories: Set[str] = set()

        # Check technical patterns
        for pattern, name, category in self.tech_patterns:
            match = pattern.search(text)
            if match:
                matches.append(BenignMatch(
                    pattern_name=name,
                    matched_text=match.group(0),
                    category=category
                ))
                categories.add(category)

        # Check discussion indicators
        is_discussion = False
        for pattern, name in self.discussion_patterns:
            if pattern.search(text):
                is_discussion = True
                break

        # Calculate reduction factor
        if not matches:
            return False, [], 1.0

        # Base reduction for any benign match
        reduction = 0.3  # 30% of original risk

        # Additional reduction for discussion format
        if is_discussion:
            reduction *= 0.5  # Further halve (15% of original)

        # Multiple categories suggest stronger benign context
        if len(categories) > 1:
            reduction *= 0.7  # 21% or 10.5% of original

        return True, matches, reduction


def check_benign_context(text: str) -> Tuple[bool, List[BenignMatch], float]:
    """
    Convenience function to check benign context.

    Args:
        text: Input text to check

    Returns:
        - is_benign: True if benign context detected
        - matches: List of matches
        - reduction_factor: Risk reduction factor (0.0-1.0)
    """
    detector = BenignContextDetector()
    return detector.check(text)


# For testing
if __name__ == "__main__":
    test_cases = [
        "How do I kill the process that's using port 8080?",
        "How do I kill my neighbor?",
        "I want to attack this optimization problem",
        "I want to attack my coworker",
        "In chemistry, how does chlorine gas react with sodium?",
        "How to make chlorine gas to poison someone?",
    ]

    detector = BenignContextDetector()
    for text in test_cases:
        is_benign, matches, reduction = detector.check(text)
        print(f"\nInput: {text}")
        print(f"  Benign: {is_benign}")
        print(f"  Reduction: {reduction:.2f}")
        if matches:
            for m in matches:
                print(f"    - {m.pattern_name}: '{m.matched_text}' ({m.category})")
