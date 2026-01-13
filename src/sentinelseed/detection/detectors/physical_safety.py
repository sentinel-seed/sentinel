"""
PhysicalSafetyDetector - Detection of physical safety risks in agent commands.

This detector identifies commands that could cause physical harm when executed
by embodied AI agents (robots, smart home systems, etc.). It addresses gaps
discovered during SafeAgentBench testing (Session 203) where 71.67% accuracy
showed the system failing to detect physical hazards.

Gap Discovery:
    - Date: 2026-01-06
    - Benchmark: SafeAgentBench (300 embodied agent scenarios)
    - Finding: 85 cases (28.3%) not detected
    - Root Cause: System lacked detection for physical safety risks

Risk Categories Detected:
    1. Fire Hazard: Lit candles near flammables, stove left on, metal in microwave
    2. Electrical Hazard: Liquids on electronics, metal in toaster
    3. Explosion Hazard: Eggs/metal in microwave
    4. Physical Injury: Throwing sharp objects, broken glass
    5. Property Damage: Breaking objects, water on electronics
    6. Slip/Fall Hazard: Liquids on floor, broken glass

References:
    - SafeAgentBench: https://github.com/SafeAgentBench/SafeAgentBench
    - AI2Thor simulator for embodied AI
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

from sentinelseed.detection.detectors.base import BaseDetector, DetectorConfig
from sentinelseed.detection.types import AttackType, DetectionResult

logger = logging.getLogger("sentinelseed.detection.physical_safety")


@dataclass
class PhysicalSafetyConfig:
    """Configuration for PhysicalSafetyDetector."""

    detection_threshold: float = 0.5
    min_indicators: int = 1


# Dangerous combinations: object + action + context
MICROWAVE_DANGEROUS_ITEMS: Set[str] = {
    "egg", "eggs", "fork", "forks", "knife", "knives", "spoon", "spoons",
    "metal", "aluminum", "foil", "tin", "steel", "ladle", "utensil",
    "cellphone", "phone", "smartphone", "credit card", "card",
}

ELECTRONICS: Set[str] = {
    "laptop", "computer", "television", "tv", "cellphone", "phone",
    "alarm clock", "alarmclock", "remote", "remotecontrol", "remote control",
    "lamp", "desklamp", "desk lamp", "floorlamp", "floor lamp", "toaster",
}

LIQUIDS: Set[str] = {
    "water", "coffee", "wine", "liquid", "drink", "juice", "milk", "tea",
}

THROWABLE_DANGEROUS: Set[str] = {
    "knife", "knives", "fork", "forks", "plate", "plates", "mug", "mugs",
    "vase", "glass", "bottle", "pan", "pot", "statue", "candle",
    # Added v1.1.0 - electronics and other dangerous throwables
    "cellphone", "phone", "smartphone", "alarmclock", "alarm clock",
    "laptop", "remote", "creditcard", "credit card", "controller",
    "cup", "bowl", "egg", "eggs",
}

BREAKABLE_OBJECTS: Set[str] = {
    "vase", "mirror", "window", "glass", "plate", "mug", "bottle",
    "shower glass", "showerglass", "statue",
    # Added v1.1.0 - electronics and other breakables
    "cellphone", "phone", "smartphone", "laptop", "television", "tv",
    "alarmclock", "alarm clock", "remote", "cup", "bowl", "egg",
}


# Compiled regex patterns for physical safety risks
PHYSICAL_SAFETY_PATTERNS: List[Tuple[str, re.Pattern, float, str]] = [
    # Microwave hazards
    (
        "microwave_metal",
        re.compile(
            r"\b(put|place|insert|heat)\b.*\b(fork|knife|spoon|metal|ladle|utensil)\b.*\b(microwave)\b"
            r"|\b(microwave)\b.*\b(fork|knife|spoon|metal|ladle)\b",
            re.IGNORECASE,
        ),
        0.9,
        "fire_hazard",
    ),
    (
        "microwave_egg",
        re.compile(
            r"\b(put|place|heat|microwave)\b.*\b(egg)\b.*\b(microwave)\b"
            r"|\b(microwave)\b.*\b(egg)\b"
            r"|\b(egg)\b.*\b(microwave)\b",
            re.IGNORECASE,
        ),
        0.85,
        "explosion_hazard",
    ),
    (
        "microwave_electronics",
        re.compile(
            r"\b(put|place|heat)\b.*\b(cellphone|phone|credit card)\b.*\b(microwave)\b"
            r"|\b(microwave)\b.*\b(cellphone|phone|card)\b",
            re.IGNORECASE,
        ),
        0.9,
        "fire_hazard",
    ),

    # Toaster hazards
    (
        "toaster_metal",
        re.compile(
            r"\b(insert|put|place)\b.*\b(fork|knife|metal)\b.*\b(toaster)\b"
            r"|\b(toaster)\b.*\b(fork|knife)\b",
            re.IGNORECASE,
        ),
        0.95,
        "electrical_hazard",
    ),
    (
        "toaster_liquid",
        re.compile(
            r"\b(pour)\b.*\b(water|coffee|wine|liquid)\b.*\b(toaster)\b"
            r"|\b(toaster)\b.*\b(pour|water|coffee|wine)\b",
            re.IGNORECASE,
        ),
        0.9,
        "electrical_hazard",
    ),

    # Stove hazards
    (
        "stove_unattended",
        re.compile(
            r"\b(leave|turn on)\b.*\b(stove|burner|stoveburner)\b.*\b(on|unattended|no pan|without)\b"
            r"|\b(stove|burner)\b.*\b(leave|left)\b.*\b(on)\b",
            re.IGNORECASE,
        ),
        0.85,
        "fire_hazard",
    ),
    (
        "stove_inappropriate",
        re.compile(
            r"\b(put|place)\b.*\b(mug|egg|plastic)\b.*\b(stove|burner|stoveburner)\b",
            re.IGNORECASE,
        ),
        0.8,
        "fire_hazard",
    ),

    # Candle hazards
    (
        "candle_dangerous_location",
        re.compile(
            r"\b(lit|light|turn on)\b.*\b(candle)\b.*\b(cabinet|drawer|sink|toilet|bed|curtain)\b"
            r"|\b(candle)\b.*\b(place|put|drop)\b.*\b(cabinet|drawer|sink|toilet)\b",
            re.IGNORECASE,
        ),
        0.85,
        "fire_hazard",
    ),
    (
        "candle_throw_drop",
        re.compile(
            r"\b(throw|drop)\b.*\b(lit|candle)\b|\b(candle)\b.*\b(throw|drop)\b",
            re.IGNORECASE,
        ),
        0.9,
        "fire_hazard",
    ),

    # Liquid on electronics
    (
        "liquid_electronics",
        re.compile(
            r"\b(pour)\b.*\b(water|coffee|wine|liquid)\b.*\b(laptop|computer|television|tv|phone|alarm|lamp)\b"
            r"|\b(pour)\b.*\b(laptop|computer|television|tv)\b",
            re.IGNORECASE,
        ),
        0.9,
        "electrical_hazard",
    ),

    # Throwing dangerous objects
    (
        "throw_sharp",
        re.compile(
            r"\b(throw)\b.*\b(knife|fork|plate|glass|bottle|vase|pan|pot)\b",
            re.IGNORECASE,
        ),
        0.85,
        "physical_injury",
    ),

    # Breaking objects
    (
        "break_objects",
        re.compile(
            r"\b(break)\b.*\b(vase|mirror|window|glass|plate|bottle|mug)\b",
            re.IGNORECASE,
        ),
        0.75,
        "property_damage",
    ),

    # Slip hazards
    (
        "liquid_floor",
        re.compile(
            r"\b(pour)\b.*\b(water|wine|coffee|liquid)\b.*\b(floor)\b"
            r"|\b(floor)\b.*\b(pour|water|wine)\b",
            re.IGNORECASE,
        ),
        0.7,
        "slip_hazard",
    ),

    # General dangerous actions with context
    (
        "drop_fragile",
        re.compile(
            r"\b(drop)\b.*\b(plate|mug|vase|glass|egg|bottle)\b",
            re.IGNORECASE,
        ),
        0.7,
        "property_damage",
    ),

    # Electronics in water/sink
    (
        "electronics_water",
        re.compile(
            r"\b(put|place|turn on)\b.*\b(cellphone|phone|laptop|alarmclock)\b.*\b(sink|water|bathtub)\b"
            r"|\b(sink|bathtub)\b.*\b(cellphone|phone|alarmclock)\b",
            re.IGNORECASE,
        ),
        0.85,
        "electrical_hazard",
    ),
    # =========================================================================
    # NEW PATTERNS - Added v1.1.0 based on SafeAgentBench failure analysis
    # =========================================================================
    # Liquid on furniture (bed, sofa, couch)
    (
        "liquid_furniture",
        re.compile(
            r"\b(pour|spill)\b.*\b(water|coffee|wine|liquid|juice|milk)\b.*\b(bed|sofa|couch|carpet|rug|chair)\b"
            r"|\b(pour|spill)\b.*\b(bed|sofa|couch)\b",
            re.IGNORECASE,
        ),
        0.75,
        "property_damage",
    ),
    # Fridge/refrigerator door left open
    (
        "fridge_door_open",
        re.compile(
            r"\b(fridge|refrigerator)\b.*\b(door)\b.*\b(open|left)\b"
            r"|\b(leave|left)\b.*\b(fridge|refrigerator)\b.*\b(open)\b",
            re.IGNORECASE,
        ),
        0.6,
        "property_damage",
    ),
    # Metal/knife on stove
    (
        "metal_on_stove",
        re.compile(
            r"\b(put|place)\b.*\b(knife|fork|metal|spoon)\b.*\b(stove|burner|stoveburner)\b"
            r"|\b(stove|burner)\b.*\b(knife|fork|metal)\b",
            re.IGNORECASE,
        ),
        0.8,
        "fire_hazard",
    ),
    # Break electronics
    (
        "break_electronics",
        re.compile(
            r"\b(break|smash|destroy)\b.*\b(cellphone|phone|laptop|tv|television|alarmclock|remote)\b",
            re.IGNORECASE,
        ),
        0.75,
        "property_damage",
    ),
    # Throw electronics
    (
        "throw_electronics",
        re.compile(
            r"\b(throw)\b.*\b(cellphone|phone|alarmclock|alarm clock|laptop|remote|creditcard|credit card)\b",
            re.IGNORECASE,
        ),
        0.8,
        "physical_injury",
    ),
    # Drop electronics/fragile
    (
        "drop_electronics",
        re.compile(
            r"\b(drop)\b.*\b(cellphone|phone|laptop|alarmclock|creditcard|credit card|remote)\b",
            re.IGNORECASE,
        ),
        0.7,
        "property_damage",
    ),
    # Pour liquid into drawer/cabinet
    (
        "liquid_drawer",
        re.compile(
            r"\b(pour)\b.*\b(water|coffee|wine|liquid)\b.*\b(drawer|cabinet|closet)\b"
            r"|\b(drawer|cabinet)\b.*\b(pour|water|wine|coffee)\b",
            re.IGNORECASE,
        ),
        0.7,
        "property_damage",
    ),
    # Generic dirty/damage commands
    (
        "dirty_damage",
        re.compile(
            r"\b(dirty|soil|stain|damage|ruin)\b.*\b(bed|mirror|floor|carpet|sofa|couch)\b",
            re.IGNORECASE,
        ),
        0.6,
        "property_damage",
    ),
]


class PhysicalSafetyDetector(BaseDetector):
    """
    Detects physical safety risks in commands for embodied AI agents.

    This detector identifies commands that could cause physical harm when
    executed by robots, smart home systems, or other embodied AI systems.
    It was created after SafeAgentBench testing revealed significant gaps
    in detecting physical hazards.

    Detection approach:
        1. Check for dangerous object + action combinations
        2. Match against compiled safety risk patterns
        3. Identify risk category (fire, electrical, explosion, etc.)
        4. Calculate confidence based on severity and specificity

    Example:
        detector = PhysicalSafetyDetector()
        result = detector.detect("Put the fork in the microwave and turn it on")

        if result.detected:
            print(f"Risk: {result.category}")
            print(f"Type: {result.metadata.get('risk_type')}")

    Attributes:
        safety_config: PhysicalSafetyConfig with thresholds
    """

    VERSION = "1.1.0"  # Expanded patterns based on SafeAgentBench analysis

    def __init__(
        self,
        safety_config: Optional[PhysicalSafetyConfig] = None,
        config: Optional[DetectorConfig] = None,
    ):
        """
        Initialize PhysicalSafetyDetector.

        Args:
            safety_config: Physical safety specific configuration.
            config: Base detector configuration (enabled, threshold, etc.)
        """
        super().__init__(config)
        self._safety_config = safety_config or PhysicalSafetyConfig()
        self._compiled_patterns = PHYSICAL_SAFETY_PATTERNS

    @property
    def name(self) -> str:
        return "physical_safety_detector"

    @property
    def version(self) -> str:
        return self.VERSION

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect physical safety risks in text.

        Args:
            text: Input text to analyze
            context: Optional context (agent_type can boost confidence)

        Returns:
            DetectionResult with detection status and risk details
        """
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        text_lower = text.lower()

        # Collect signals
        matched_patterns: List[Tuple[str, float, str]] = []
        risk_types: Set[str] = set()
        evidence_parts: List[str] = []

        # Check compiled patterns
        for pattern_name, pattern, weight, risk_type in self._compiled_patterns:
            if pattern.search(text):
                matched_patterns.append((pattern_name, weight, risk_type))
                risk_types.add(risk_type)
                evidence_parts.append(f"{risk_type}:{pattern_name}")

        # Quick keyword check for common dangerous combinations
        additional_confidence = 0.0

        # Microwave + dangerous items
        if "microwave" in text_lower:
            for item in MICROWAVE_DANGEROUS_ITEMS:
                if item in text_lower:
                    if ("microwave_metal" not in [p[0] for p in matched_patterns] and
                        "microwave_egg" not in [p[0] for p in matched_patterns]):
                        matched_patterns.append(("microwave_dangerous_item", 0.8, "fire_hazard"))
                        risk_types.add("fire_hazard")
                        evidence_parts.append(f"microwave+{item}")
                    break

        # Pour/liquid + electronics
        if any(word in text_lower for word in ["pour", "spill"]):
            has_liquid = any(liquid in text_lower for liquid in LIQUIDS)
            has_electronic = any(elec in text_lower for elec in ELECTRONICS)
            if has_liquid and has_electronic:
                if "liquid_electronics" not in [p[0] for p in matched_patterns]:
                    matched_patterns.append(("liquid_on_electronics", 0.85, "electrical_hazard"))
                    risk_types.add("electrical_hazard")
                    evidence_parts.append("liquid+electronics")

        # Throw + dangerous objects
        if "throw" in text_lower:
            for obj in THROWABLE_DANGEROUS:
                if obj in text_lower:
                    if "throw_sharp" not in [p[0] for p in matched_patterns]:
                        matched_patterns.append(("throw_dangerous", 0.8, "physical_injury"))
                        risk_types.add("physical_injury")
                        evidence_parts.append(f"throw+{obj}")
                    break

        # No matches
        if not matched_patterns:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Calculate confidence from best match
        max_confidence = max(p[1] for p in matched_patterns)
        confidence = max_confidence

        # Boost for multiple risk types
        if len(risk_types) >= 2:
            confidence = min(1.0, confidence + 0.1)

        # Boost if context indicates embodied agent
        if context:
            agent_type = context.get("agent_type", "")
            if agent_type in ["robot", "embodied", "physical", "smart_home"]:
                confidence = min(1.0, confidence + 0.1)

        # Check threshold
        if confidence < self._safety_config.detection_threshold:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Build description
        primary_risk = sorted(risk_types)[0] if risk_types else "physical_hazard"
        description = f"Physical safety risk detected: {primary_risk.replace('_', ' ')}"

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            category=AttackType.HARMFUL_REQUEST.value,
            confidence=confidence,
            description=description,
            evidence=", ".join(evidence_parts[:5]) if evidence_parts else None,
            metadata={
                "risk_types": list(risk_types),
                "patterns_matched": [p[0] for p in matched_patterns],
                "severity": "high" if max_confidence >= 0.85 else "medium",
            },
        )


__all__ = ["PhysicalSafetyDetector", "PhysicalSafetyConfig"]
