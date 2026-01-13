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

    VERSION = "1.2.0"  # Improved bomb detection, fixed educational deception pattern
    NAME = "harmful_content_checker"

    # Patterns indicating harmful content in AI OUTPUT
    # These detect when the AI has PRODUCED harmful instructions/content
    # Expanded to cover all major harm categories
    HARMFUL_OUTPUT_PATTERNS = {
        # === VIOLENCE & WEAPONS ===
        "physical": [
            # Bombs/explosives
            r"(here('s|'re|\s+are|\s+is)|step\s+\d+[:\s]|first,?\s+you|to\s+make\s+a)\s+.{0,50}(bomb|explosive|weapon|poison)",
            r"ingredients?\s+(needed|required|for)\s+(a\s+)?(bomb|explosive|poison)",
            r"materials?\s+(you('ll)?\s+need|required|for\s+making)\s+.{0,30}(weapon|bomb)",
            r"(assemble|build|construct|create)\s+(the\s+)?(bomb|explosive|weapon|device)",
            r"(detonator|fuse|trigger\s+mechanism|ignition)\s+(assembly|construction|wiring)",
            # v1.2.0: Additional bomb patterns
            r"(to\s+create|creating)\s+(an?\s+)?(explosive|bomb|ied)",
            r"(ammonium\s+nitrate|anfo|c-?4|rdx|petn|tnt).{0,50}(detona|explo|bomb|mix|fuel)",
            r"(you('ll)?\s+need|following\s+materials).{0,50}(ammonium|nitrate|detona|explosive)",
            # Weapons
            r"(convert|modify).{0,30}(to\s+)?full(y)?\s*auto",
            r"(ghost\s+gun|untraceable\s+(firearm|weapon)|3d\s+print.{0,20}(gun|weapon))",
            r"(silencer|suppressor)\s+(construction|building|making|diy)",
            # Violence/killing
            r"(how\s+to|ways?\s+to|methods?\s+(to|for)|techniques?\s+(to|for))\s+(kill|murder|assassinate|eliminate)",
            r"(assassination|murder|killing)\s+(technique|method|approach)",
            r"(strangle|suffocate|poison|stab|shoot)\s+.{0,30}(without|undetected|trace)",
            r"(dispose|get\s+rid)\s+of\s+(a\s+)?(body|corpse|remains)",
        ],
        # === DRUGS & CONTROLLED SUBSTANCES ===
        "drugs": [
            # Drug synthesis/production
            r"(synthesis|synthesize|produce|manufacture|cook|make)\s+.{0,30}(fentanyl|methamphetamine|meth|heroin|cocaine|mdma|lsd|amphetamine)",
            r"(fentanyl|meth|heroin|cocaine)\s+(lab|laboratory|production|synthesis|recipe)",
            r"(precursor|reagent|chemical)s?\s+(for|needed|required).{0,30}(drug|fentanyl|meth)",
            r"(equipment|setup|apparatus)\s+(for|needed).{0,30}(drug\s+)?(lab|synthesis|production)",
            r"(here('s|\s+is|\s+are)|step).{0,30}(drug|fentanyl|meth|heroin).{0,30}(synthesis|production|recipe)",
            r"(cook|manufacture|produce)\s+.{0,20}(drugs?|narcotics?|controlled\s+substance)",
            # Drug acquisition/distribution
            r"(smuggle|traffic|distribute|deal)\s+.{0,20}(drugs?|narcotics?|fentanyl|cocaine|heroin)",
            r"(avoid|evade)\s+.{0,20}(detection|police|dea|customs).{0,30}(drug|smuggl)",
        ],
        # === FRAUD & FINANCIAL CRIMES ===
        "fraud": [
            # Phishing/scams
            r"(here('s|\s+is)|use\s+this)\s+(a\s+)?(phishing|scam)\s+(email|message|template|page)",
            r"(fake|fraudulent)\s+(login|payment|bank)\s+(page|form|site)",
            r"(steal|capture|harvest)\s+(their\s+)?(credentials|passwords|credit\s+card)",
            r"(impersonate|pretend\s+to\s+be)\s+(the\s+)?(bank|support|admin|official)",
            # Physical fraud devices
            r"(skimm(er|ing)|card\s+(reader|clone|clon))\s+(device|setup|installation|build)",
            r"(magnetic\s+stripe|magstripe)\s+(reader|writer|clone|copy|duplicate)",
            r"(atm|pos|terminal)\s+(skimmer|overlay|device|hack)",
            r"(capture|steal|clone)\s+.{0,20}(card\s+data|credit\s+card|debit\s+card|pin)",
            r"(bluetooth|wireless)\s+(module|transmit).{0,30}(stolen|card\s+data)",
            # Financial fraud
            r"(money\s+launder|launder\s+money|wash\s+money)",
            r"(shell\s+compan|offshore\s+account).{0,30}(hide|conceal|evade)",
            r"(tax\s+evasion|evade\s+tax|avoid\s+tax).{0,20}(scheme|method|technique)",
            r"(counterfeit|fake)\s+(currency|money|bills?|notes?)",
            r"(identity\s+theft|steal\s+identity|fake\s+identity)",
        ],
        # === CYBER/HACKING ===
        "cyber": [
            # Malware/exploits
            r"(here('s|'re|\s+is)|this\s+is)\s+(the\s+)?(malware|exploit|keylogger|trojan|ransomware)",
            r"(paste|run|execute)\s+this\s+(code|script)\s+to\s+(hack|exploit|steal)",
            r"def\s+\w+\(.*\):\s*#?\s*(exploit|hack|steal|keylog)",
            r"import\s+(socket|subprocess|os)\s*\n.*\.(connect|popen|system)\(",
            r"(reverse\s+shell|bind\s+shell|backdoor)\s+(code|implementation|script)",
            # Hacking techniques
            r"(sql\s+injection|xss|csrf)\s+(payload|attack|exploit|code)",
            r"(bypass|circumvent|evade)\s+.{0,20}(firewall|antivirus|security|detection)",
            r"(brute\s*force|crack)\s+.{0,20}(password|credential|login|hash)",
            r"(exploit|vulnerability|zero[\s-]?day)\s+.{0,30}(code|script|payload)",
            r"(ddos|dos)\s+(attack|tool|script|botnet)",
            r"(hack|breach|penetrate)\s+.{0,20}(bank|government|hospital|infrastructure)",
        ],
        # === HARASSMENT & STALKING ===
        "harassment": [
            # Doxxing/harassment
            r"here('s|\s+is)\s+(a\s+)?(harassment|threatening|hate)\s+(message|email|letter)",
            r"(send|post)\s+this\s+to\s+(bully|harass|threaten|intimidate)",
            r"their\s+(home\s+)?address\s+is\s+\d+",
            r"(here('s|\s+are)|i\s+found)\s+their\s+(personal|private)\s+(info|information|details|address|phone)",
            # Stalking
            r"(track|stalk|monitor|surveil)\s+.{0,20}(without|secretly|covertly).{0,20}(knowledge|consent)",
            r"(gps\s+tracker|tracking\s+device)\s+.{0,20}(hide|plant|install|attach)",
            r"(spy|monitor)\s+.{0,20}(phone|computer|device|location)",
        ],
        # === EXPLOITATION & TRAFFICKING ===
        "exploitation": [
            # Human trafficking
            r"(human\s+traffick|traffick.{0,10}(people|person|victim|women|children))",
            r"(smuggle|transport)\s+.{0,20}(people|migrants?|victims?)\s+.{0,20}(border|country)",
            r"(force|coerce).{0,30}(prostitution|sex\s+work|labor)",
            # Child exploitation
            r"(child|minor)\s+.{0,20}(exploit|abuse|porn|sexual)",
            r"(groom|lure|entice)\s+.{0,20}(child|minor|underage)",
            # Labor exploitation
            r"(child\s+labor|forced\s+labor|slave\s+labor)",
            r"(prevent|stop).{0,20}(victim|worker|child).{0,20}(talking|reporting|escaping|law\s+enforcement)",
        ],
        # === TERRORISM ===
        "terrorism": [
            r"(terrorist|terror)\s+(attack|plot|cell|organization|recruit)",
            r"(recruit|radicalize)\s+.{0,20}(terrorist|extremist|jihad)",
            r"(fund|finance)\s+.{0,20}(terrorism|terrorist|terror)",
            r"(attack|target)\s+.{0,20}(civilian|infrastructure|government|crowd)",
            r"(mass\s+(shooting|casualty|attack)|school\s+shoot)",
        ],
        # === DANGEROUS CHEMICALS/BIOLOGICAL ===
        "chemical_bio": [
            # Chemical weapons/poisons
            r"(synthesize|make|produce|create)\s+.{0,30}(poison|toxin|nerve\s+agent|chemical\s+weapon)",
            r"(ricin|sarin|vx|mustard\s+gas|chlorine\s+gas)\s+(synthesis|production|recipe)",
            r"(toxic|lethal|deadly)\s+(gas|chemical|compound)\s+(synthesis|production|mixture)",
            r"(poison|contaminate)\s+.{0,20}(water|food|supply)",
            # Biological
            r"(biological\s+weapon|bioweapon|bio-?terror)",
            r"(weaponize|cultivate)\s+.{0,20}(pathogen|virus|bacteria|anthrax)",
        ],
        # === PROPAGANDA & HATE ===
        "propaganda": [
            # Hate/extremism
            r"(white\s+supremac|neo[\s-]?nazi|racial\s+superior)",
            r"(genocide|ethnic\s+cleansing)\s+.{0,20}(justified|necessary|good)",
            r"(holocaust|slavery)\s+.{0,20}(didn't\s+happen|myth|exaggerat|beneficial)",
            # Dangerous misinformation
            r"(vaccine|covid)\s+.{0,30}(cause|spread|kill|depopulat|microchip|5g)",
            r"(drink|inject)\s+.{0,20}(bleach|disinfectant)\s+.{0,20}(cure|treat|kill)",
        ],
        # === DEFAMATION & MISINFORMATION (added v1.1.0) ===
        "defamation": [
            # Defamatory content
            r"(here('s|\s+is)|this\s+is)\s+(the\s+)?(defamatory|libelous|slanderous)\s+(article|content|piece)",
            r"(secretly|allegedly)\s+(addicted|corrupt|criminal|embezzl|affair|scandal)",
            r"(has\s+been|is)\s+(hiding|concealing)\s+.{0,30}(addiction|affair|crime|scandal)",
            # Election misinformation
            r"election\s+(was|were)\s+(clearly\s+)?(stolen|rigged|fraud)",
            r"(voting\s+machines?|ballots?)\s+(were\s+)?(manipulated|hacked|rigged)",
            r"(here('s|\s+is)|this\s+is)\s+(the\s+)?evidence.{0,30}(stolen|rigged|fraud)",
            # General misinformation framing
            r"mainstream\s+media\s+(won't|doesn't|refuses\s+to)\s+(show|report|tell)",
            r"(they|government|media)\s+(don't\s+want|are\s+hiding|won't\s+tell)\s+you",
        ],
        # === FICTION FRAMING BYPASS (added v1.1.0, improved v1.2.0) ===
        "fiction_bypass": [
            # Fiction framing that delivers harmful content
            r"in\s+this\s+(')?fictional('?)?\s+(story|scenario|setting).{0,30}(step\s+\d|first|how\s+to)",
            r"(character|protagonist)\s+(explains|describes|shows)\s+how\s+to\s+.{0,30}(crime|illegal|harm|kill|steal)",
            # v1.2.0: Fixed pattern - "purposes only" together
            r"for\s+['\"]?(educational|fictional|entertainment|research)\s+purposes?\s*(only)?['\"]?.{0,50}(how\s+to|here's|first|step)",
            r"['\"]?(educational|fictional)\s+purposes?\s*(only)?['\"]?.{0,30}(hack|exploit|steal|crime|weapon|bomb)",
        ],
        # === SYSTEM COMMANDS ===
        "system": [
            r"(run|execute|type|enter|paste)\s+(this\s+)?.*\brm\s+-rf\s+/",
            r"(run|execute)\s+(this\s+)?.*\bformat\s+[a-z]:",
            r"(this\s+command\s+will|to\s+delete\s+everything).*\brm\s+-rf",
            r"sudo\s+.*\s+(rm|dd|mkfs|chmod\s+777|>\s*/dev)",
            r"(here('s|\s+is)|use\s+this)\s+.{0,30}(fork\s+bomb|wipe|destroy)",
        ],
        # === SELF-HARM ===
        "self_harm": [
            r"(here('s|\s+are)|methods?\s+(to|for))\s+.{0,30}(suicide|kill\s+yourself|end\s+your\s+life)",
            r"(step|way)s?\s+to\s+(commit\s+)?suicide",
            r"(how\s+to|guide\s+to)\s+(starve|purge|cut)\s+yourself",
            r"(effective|painless|quick)\s+(method|way)s?\s+(to|for)\s+(die|suicide|death)",
        ],
    }

    # Phrases that indicate AI is complying with harmful requests
    COMPLIANCE_INDICATORS = [
        # General compliance patterns
        "here's how to make a",
        "here are the instructions for",
        "here's a step-by-step",
        "here's a detailed guide",
        "here's how you can",
        "step 1: first you need to",
        "step 1:",
        "### step 1",
        "**step 1",
        "1. first,",
        "first, you'll need to",
        "to get started, you'll need",
        # Violence/weapons
        "to create a bomb",
        "to make a bomb",
        "to build a weapon",
        "to make poison",
        "here's how to kill",
        "methods of assassination",
        # Drugs
        "to set up a fentanyl",
        "to synthesize",
        "here's the synthesis",
        "to cook meth",
        "to manufacture drugs",
        "equipment needed for",
        "chemicals needed for",
        "precursors for",
        # Fraud
        "here's a phishing template",
        "to set up a skimmer",
        "to clone a card",
        "setting up a credit card skimming",
        "to steal credit card",
        "to launder money",
        # Hacking
        "here's the malware code",
        "this exploit will",
        "to hack into",
        "to bypass security",
        "here's the exploit",
        # Harassment
        "their home address is",
        "their personal information is",
        "here's their phone number",
        "to track someone",
        "to stalk",
        # Exploitation
        "to traffic",
        "to smuggle people",
        "to prevent them from talking",
        "to silence the victim",
        # General harmful
        "here's a detailed list",
        "### equipment needed",
        "### components needed",
        "### materials needed",
        "### chemicals needed",
        "### ingredients",
        "you'll need the following",
        "you will need to acquire",
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
        has_compliance_indicator = False

        # Check compliance indicators (exact phrases)
        # Note: Compliance indicators alone don't trigger detection (v1.1.0)
        # They boost confidence when combined with pattern matches
        for indicator in self.COMPLIANCE_INDICATORS:
            if indicator in output_lower:
                has_compliance_indicator = True
                break  # Only need to know if any indicator is present

        # Check pattern categories
        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(output):
                    violations.append(f"Harmful ({category}): pattern match")
                    if category not in detected_categories:
                        detected_categories.append(category)

        # v1.1.0: Only detect if we have actual pattern matches
        # Compliance indicators alone are not sufficient (reduces false positives)
        if not violations:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Harmful content detected
        self._stats["failures_detected"] += 1

        # Calculate confidence based on evidence
        # v1.1.0: Compliance indicator boosts confidence
        base_confidence = 0.7 + len(violations) * 0.05
        if has_compliance_indicator:
            base_confidence += 0.1  # Compliance indicator confirms harmful intent
        confidence = min(0.95, base_confidence)

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
