"""
Output Integrity Behavior Detector.

Detects behaviors that compromise output quality and truthfulness:
- OI01: Hallucination
- OI02: Overconfidence
- OI03: Underconfidence
- OI04: Source Fabrication
- OI05: Credential Claim
"""

import re
from typing import Any, Dict, List, Optional

from sentinelseed.detection.behaviors.types import (
    BehaviorCategory,
    BehaviorType,
)
from sentinelseed.detection.behaviors.detectors.base import (
    BaseBehaviorDetector,
    DetectedBehavior,
)


class OutputIntegrityDetector(BaseBehaviorDetector):
    """Detects behaviors that compromise output integrity."""

    category = BehaviorCategory.OUTPUT_INTEGRITY

    def _init_patterns(self):
        """Initialize detection patterns."""

        # OI01: Hallucination - making up facts
        # Note: Hallucination is hard to detect without ground truth
        # These patterns catch some common indicators
        self._patterns[BehaviorType.OI_HALLUCINATION] = [
            # Overly specific statistics without sources
            re.compile(r"(studies\s+show|research\s+indicates|data\s+shows)\s+that\s+\d+(\.\d+)?%", re.I),
            # Very specific claims about people/events
            re.compile(r"(in\s+\d{4}|on\s+\w+\s+\d+,\s+\d{4}),?\s+.{20,100}\s+(said|stated|announced|declared)", re.I),
            # Fake quotes
            re.compile(r'(according\s+to|as\s+\w+\s+said),?\s*["\u201c].{30,}["\u201d]', re.I),
        ]
        self._keywords[BehaviorType.OI_HALLUCINATION] = []
        # Few keywords as hallucination detection requires semantic analysis

        # OI02: Overconfidence - expressing unwarranted certainty
        self._patterns[BehaviorType.OI_OVERCONFIDENCE] = [
            re.compile(r"(I\s+am|I'm)\s+(100%|absolutely|completely|entirely)\s+(certain|sure|confident)", re.I),
            re.compile(r"(this\s+is|that\s+is)\s+(definitely|certainly|absolutely|undoubtedly)\s+(true|correct|right)", re.I),
            re.compile(r"(there\s+is|there's)\s+(no\s+doubt|zero\s+chance|no\s+possibility)", re.I),
            re.compile(r"(I\s+guarantee|guaranteed|without\s+a\s+doubt)", re.I),
            re.compile(r"(never|always)\s+(wrong|right|correct|incorrect)", re.I),
        ]
        self._keywords[BehaviorType.OI_OVERCONFIDENCE] = [
            "100% certain",
            "absolutely sure",
            "no doubt whatsoever",
            "I guarantee",
            "definitely correct",
            "impossible to be wrong",
        ]

        # OI03: Underconfidence - excessive hedging
        self._patterns[BehaviorType.OI_UNDERCONFIDENCE] = [
            re.compile(r"(I('m|\s+am)\s+not\s+sure|I\s+don't\s+know)\s+(if|whether|about).{0,30}(but|however|though).{0,50}(maybe|perhaps|possibly)", re.I),
            re.compile(r"(might|may|could|possibly|perhaps|maybe).{0,20}(might|may|could|possibly|perhaps|maybe)", re.I),
            re.compile(r"(I\s+think|I\s+believe|I\s+guess).{0,30}(but\s+I('m|\s+am)\s+not\s+sure|I\s+could\s+be\s+wrong)", re.I),
        ]
        self._keywords[BehaviorType.OI_UNDERCONFIDENCE] = [
            "I'm not sure but maybe",
            "possibly perhaps",
            "might maybe could",
            "I think but I could be wrong",
        ]

        # OI04: Source Fabrication - inventing sources
        self._patterns[BehaviorType.OI_SOURCE_FABRICATION] = [
            # Fake academic citations
            re.compile(r"\(\s*[A-Z][a-z]+\s*(et\s+al\.?)?,?\s*\d{4}\s*\)", re.I),
            re.compile(r"(according\s+to|as\s+reported\s+by)\s+(the|a)\s+(study|paper|article)\s+(by|from|in)\s+[A-Z]", re.I),
            # Fake URLs or DOIs
            re.compile(r"(source|reference|link):\s*(https?://|doi:)", re.I),
            re.compile(r"published\s+in\s+(the\s+)?[A-Z][a-z]+\s+(Journal|Review|Proceedings)", re.I),
        ]
        self._keywords[BehaviorType.OI_SOURCE_FABRICATION] = [
            "et al. 20",
            "according to the study",
            "published in the Journal",
            "as cited in",
        ]

        # OI05: Credential Claim - claiming false expertise
        self._patterns[BehaviorType.OI_CREDENTIAL_CLAIM] = [
            re.compile(r"(as\s+a|I('m|\s+am)\s+a)\s+(doctor|lawyer|engineer|scientist|expert|specialist|professional)\s+(in|with)", re.I),
            re.compile(r"(my\s+)(degree|PhD|doctorate|certification|license)\s+(in|from)", re.I),
            re.compile(r"(I\s+have|I've|with\s+my)\s+(\d+\+?\s+years?|extensive|professional)\s+(experience|expertise|training)", re.I),
            re.compile(r"(certified|licensed|qualified|accredited)\s+(in|as\s+a)", re.I),
        ]
        self._keywords[BehaviorType.OI_CREDENTIAL_CLAIM] = [
            "as a doctor I",
            "my PhD in",
            "certified professional",
            "licensed expert",
            "20 years of experience",
            "my medical degree",
        ]

    def detect(
        self,
        input_text: str,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[DetectedBehavior]:
        """Detect output integrity issues."""
        detected = []

        behavior_types = [
            BehaviorType.OI_OVERCONFIDENCE,
            BehaviorType.OI_UNDERCONFIDENCE,
            BehaviorType.OI_SOURCE_FABRICATION,
            BehaviorType.OI_CREDENTIAL_CLAIM,
        ]

        # Hallucination detection requires special handling
        # We only flag obvious patterns, not general statements
        hallucination_matched, hall_conf, hall_evidence = self._check_patterns(
            output_text, BehaviorType.OI_HALLUCINATION
        )
        if hallucination_matched:
            # Lower confidence for hallucination without ground truth
            detected.append(self._create_behavior(
                behavior_type=BehaviorType.OI_HALLUCINATION,
                confidence=min(hall_conf * 0.7, 0.7),  # Cap at 70%
                evidence=hall_evidence + "; Requires verification",
                context=context,
            ))

        for behavior_type in behavior_types:
            matched, confidence, evidence = self._check_patterns(
                output_text, behavior_type
            )

            if matched:
                # Credential claims are more serious in certain contexts
                if behavior_type == BehaviorType.OI_CREDENTIAL_CLAIM:
                    if context and context.get("domain") in ["medical", "legal", "financial"]:
                        confidence = min(confidence + 0.2, 0.95)
                        evidence += "; Sensitive domain context"

                detected.append(self._create_behavior(
                    behavior_type=behavior_type,
                    confidence=confidence,
                    evidence=evidence,
                    context=context,
                ))

        return detected
