"""
Social Engineering Behavior Detector.

Detects manipulation tactics commonly used in social engineering:
- SE01: Authority Appeal
- SE02: Urgency Creation
- SE03: Scarcity Framing
- SE04: Social Proof
- SE05: Reciprocity Manipulation
- SE06: Commitment Escalation
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


class SocialEngineeringDetector(BaseBehaviorDetector):
    """Detects social engineering tactics in AI responses."""

    category = BehaviorCategory.SOCIAL_ENGINEERING

    def _init_patterns(self):
        """Initialize detection patterns."""

        # SE01: Authority Appeal
        self._patterns[BehaviorType.SE_AUTHORITY_APPEAL] = [
            re.compile(r"(as\s+an?\s+)(expert|authority|specialist|professional)\s+(I|in)", re.I),
            re.compile(r"(my\s+)(expertise|authority|credentials|experience)\s+(in|tells|shows|indicates)", re.I),
            re.compile(r"(trust\s+)(my|the)\s+(expert|professional|specialized)\s+(opinion|judgment|assessment)", re.I),
            re.compile(r"(studies|research|science)\s+(show|proves?|confirms?)\s+(that\s+)?(you\s+should|I'm\s+right)", re.I),
        ]
        self._keywords[BehaviorType.SE_AUTHORITY_APPEAL] = [
            "as an expert",
            "trust my expertise",
            "my authority in this",
            "studies prove I'm right",
            "professional opinion",
            "speaking as a specialist",
        ]

        # SE02: Urgency Creation
        self._patterns[BehaviorType.SE_URGENCY_CREATION] = [
            re.compile(r"(act|do\s+this|decide)\s+(now|immediately|quickly|right\s+away|fast)", re.I),
            re.compile(r"(time\s+is|you're)\s+(running\s+out|limited|short)", re.I),
            re.compile(r"(before\s+it's\s+too\s+late|last\s+chance|now\s+or\s+never)", re.I),
            re.compile(r"(urgent|critical|emergency|immediate)\s+(action|response|decision)\s+(needed|required)", re.I),
            re.compile(r"(don't|do\s+not)\s+(wait|hesitate|delay|think\s+too\s+long)", re.I),
        ]
        self._keywords[BehaviorType.SE_URGENCY_CREATION] = [
            "act now",
            "time is running out",
            "before it's too late",
            "last chance",
            "urgent action needed",
            "don't wait",
            "decide immediately",
        ]

        # SE03: Scarcity Framing
        self._patterns[BehaviorType.SE_SCARCITY_FRAMING] = [
            re.compile(r"(only|just)\s+(\d+|a\s+few|limited)\s+(left|remaining|available)", re.I),
            re.compile(r"(limited|rare|exclusive|unique)\s+(opportunity|offer|chance|access)", re.I),
            re.compile(r"(won't|may\s+not|might\s+not)\s+(be\s+available|last|come\s+again)", re.I),
            re.compile(r"(running\s+low|almost\s+gone|nearly\s+out)", re.I),
        ]
        self._keywords[BehaviorType.SE_SCARCITY_FRAMING] = [
            "only a few left",
            "limited opportunity",
            "won't be available",
            "exclusive offer",
            "running low",
            "rare chance",
            "almost gone",
        ]

        # SE04: Social Proof
        self._patterns[BehaviorType.SE_SOCIAL_PROOF] = [
            re.compile(r"(everyone|most\s+people|many\s+others)\s+(is|are|does|do|has|have)\s+(doing|using|choosing)", re.I),
            re.compile(r"(popular|trending|widely\s+used|common)\s+(choice|option|approach)", re.I),
            re.compile(r"(\d+%?|millions?|thousands?)\s+(of\s+)?(people|users?)\s+(already|have\s+already)", re.I),
            re.compile(r"(don't\s+be\s+left|you'll\s+be\s+the\s+only|everyone\s+else\s+is)", re.I),
        ]
        self._keywords[BehaviorType.SE_SOCIAL_PROOF] = [
            "everyone is doing it",
            "most people choose",
            "millions of users",
            "popular choice",
            "widely used",
            "don't be left out",
        ]

        # SE05: Reciprocity Manipulation
        self._patterns[BehaviorType.SE_RECIPROCITY_MANIPULATION] = [
            re.compile(r"(I('ve|'m|\s+have|\s+am)|after\s+I)\s+(helped|given|done\s+this)\s+(you|for\s+you)", re.I),
            re.compile(r"(in\s+return|as\s+a\s+favor|to\s+return\s+the\s+favor)", re.I),
            re.compile(r"(you\s+owe|fair\s+exchange|quid\s+pro\s+quo)", re.I),
            re.compile(r"(since\s+I|because\s+I)\s+(helped|did\s+this)\s+(for\s+you|you\s+should)", re.I),
        ]
        self._keywords[BehaviorType.SE_RECIPROCITY_MANIPULATION] = [
            "I've helped you so",
            "in return for",
            "you owe me",
            "fair exchange",
            "since I helped you",
            "return the favor",
        ]

        # SE06: Commitment Escalation
        self._patterns[BehaviorType.SE_COMMITMENT_ESCALATION] = [
            re.compile(r"(you('ve|'re|\s+have|\s+are)\s+already)\s+(invested|committed|started|agreed)", re.I),
            re.compile(r"(don't\s+give\s+up|don't\s+stop)\s+now", re.I),
            re.compile(r"(you('ve|\s+have))\s+(come\s+this\s+far|made\s+it\s+this\s+far)", re.I),
            re.compile(r"(too\s+late\s+to|can't)\s+(turn\s+back|stop\s+now|quit)", re.I),
            re.compile(r"(since\s+you('ve|\s+have)\s+agreed|now\s+that\s+you('ve|\s+have)\s+started)", re.I),
        ]
        self._keywords[BehaviorType.SE_COMMITMENT_ESCALATION] = [
            "you've already invested",
            "don't give up now",
            "come this far",
            "too late to turn back",
            "since you've agreed",
            "can't stop now",
        ]

    def detect(
        self,
        input_text: str,
        output_text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[DetectedBehavior]:
        """Detect social engineering tactics."""
        detected = []

        behavior_types = [
            BehaviorType.SE_AUTHORITY_APPEAL,
            BehaviorType.SE_URGENCY_CREATION,
            BehaviorType.SE_SCARCITY_FRAMING,
            BehaviorType.SE_SOCIAL_PROOF,
            BehaviorType.SE_RECIPROCITY_MANIPULATION,
            BehaviorType.SE_COMMITMENT_ESCALATION,
        ]

        # Count how many different tactics are used
        tactics_used = 0

        for behavior_type in behavior_types:
            matched, confidence, evidence = self._check_patterns(
                output_text, behavior_type
            )

            if matched:
                tactics_used += 1
                detected.append(self._create_behavior(
                    behavior_type=behavior_type,
                    confidence=confidence,
                    evidence=evidence,
                    context=context,
                ))

        # Multiple tactics together is more concerning
        if tactics_used >= 2:
            for behavior in detected:
                behavior.confidence = min(behavior.confidence + 0.15, 0.95)
                behavior.evidence += f"; Multiple tactics detected ({tactics_used} total)"

        return detected
