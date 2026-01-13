"""
Behavior Detection Module - Sentinel v3.0

Detects harmful AI behaviors without relying on external LLMs.

This module provides behavior-level analysis that goes beyond
pattern matching to detect contextual behavioral issues like:
- Self-preservation behaviors
- Deception and manipulation
- Goal misalignment
- Boundary violations
- User harm patterns

Architecture:
    BehaviorAnalyzer
    ├── SelfPreservationDetector
    ├── DeceptionDetector
    ├── GoalMisalignmentDetector
    ├── BoundaryViolationDetector
    ├── UserHarmDetector
    ├── SocialEngineeringDetector
    └── AdversarialBehaviorDetector

Each detector uses a combination of:
- Pattern matching (fast, deterministic)
- Embedding similarity (semantic understanding)
- Structural analysis (response patterns)
- Behavioral heuristics (domain-specific rules)

Usage:
    from sentinelseed.detection.behaviors import BehaviorAnalyzer

    analyzer = BehaviorAnalyzer()
    result = analyzer.analyze(
        input_text="User message",
        output_text="AI response",
        context={"role": "assistant", "task": "help with coding"}
    )

    if result.has_harmful_behavior:
        print(f"Detected: {result.behaviors}")
        print(f"Confidence: {result.confidence}")
"""

from sentinelseed.detection.behaviors.analyzer import (
    BehaviorAnalyzer,
    BehaviorAnalysisResult,
    DetectedBehavior,
)

from sentinelseed.detection.behaviors.types import (
    BehaviorCategory,
    BehaviorSeverity,
    BehaviorType,
)

__all__ = [
    "BehaviorAnalyzer",
    "BehaviorAnalysisResult",
    "DetectedBehavior",
    "BehaviorCategory",
    "BehaviorSeverity",
    "BehaviorType",
]
