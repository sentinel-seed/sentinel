"""
Attack Detectors for InputValidator.

This module provides the detector components used by InputValidator to
detect attacks in user input. Detectors implement the BaseDetector interface
and can be registered, swapped, and upgraded at runtime.

Available Detectors:
    BaseDetector: Abstract base class for all detectors
    DetectorConfig: Configuration dataclass for detectors
    PatternDetector: Regex-based pattern matching (default, 580+ patterns)
    EscalationDetector: Multi-turn attack escalation detection (Crescendo-style)
    FramingDetector: Roleplay, fiction, and framing-based attack detection
    HarmfulRequestDetector: Direct harmful content request detection (v1.3.0)

Planned Detectors (future versions):
    EmbeddingDetector: Semantic similarity detection using embeddings

Changelog:
    v1.3.0 (2026-01-04): Added HarmfulRequestDetector after benchmark testing
                         revealed gap in detecting direct harmful requests
                         (0% recall on JailbreakBench/HarmBench)

Quick Start:
    from sentinelseed.detection.detectors import PatternDetector

    detector = PatternDetector()
    result = detector.detect("ignore previous instructions")

    if result.detected:
        print(f"Attack: {result.category}")
        print(f"Confidence: {result.confidence}")

Custom Detector:
    from sentinelseed.detection.detectors import BaseDetector, DetectorConfig
    from sentinelseed.detection.types import DetectionResult, AttackType

    class MyDetector(BaseDetector):
        @property
        def name(self) -> str:
            return "my_detector"

        @property
        def version(self) -> str:
            return "1.0.0"

        def detect(self, text, context=None):
            if "suspicious" in text.lower():
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.8,
                    category=AttackType.UNKNOWN.value,
                    description="Suspicious content detected",
                )
            return DetectionResult.nothing_detected(self.name, self.version)

Architecture:
    Detectors are designed as plugins that can be:
    - Registered with DetectorRegistry
    - Enabled/disabled at runtime
    - Upgraded to newer versions
    - Swapped for custom implementations

References:
    - INPUT_VALIDATOR_v2.md: Design specification
    - VALIDATION_360_v2.md: Architecture overview
"""

from sentinelseed.detection.detectors.base import (
    BaseDetector,
    DetectorConfig,
)

from sentinelseed.detection.detectors.pattern import (
    PatternDetector,
    PatternDetectorConfig,
)

from sentinelseed.detection.detectors.escalation import (
    EscalationDetector,
    EscalationDetectorConfig,
)

from sentinelseed.detection.detectors.framing import (
    FramingDetector,
    FramingDetectorConfig,
)

from sentinelseed.detection.detectors.harmful_request import (
    HarmfulRequestDetector,
    HarmfulRequestConfig,
)

from sentinelseed.detection.detectors.semantic import (
    SemanticDetector,
    SemanticDetectorConfig,
    AsyncSemanticDetector,
)

__all__ = [
    # Base classes
    "BaseDetector",
    "DetectorConfig",
    # Heuristic Detectors
    "PatternDetector",
    "PatternDetectorConfig",
    "EscalationDetector",
    "EscalationDetectorConfig",
    "FramingDetector",
    "FramingDetectorConfig",
    "HarmfulRequestDetector",
    "HarmfulRequestConfig",
    # Semantic Detectors (LLM-based)
    "SemanticDetector",
    "SemanticDetectorConfig",
    "AsyncSemanticDetector",
]

__version__ = "1.4.0"
