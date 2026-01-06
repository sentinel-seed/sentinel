"""
Base interface for all attack detectors.

This module defines the BaseDetector abstract base class that all detectors
must implement. The detector interface provides a consistent contract for
attack detection, enabling:

1. Plugin architecture - Detectors can be registered/swapped at runtime
2. Versioning - Each detector has name and version for traceability
3. Configurability - Detectors can be enabled/disabled and configured
4. Testability - Mock detectors can be easily created for testing

Architecture:
    BaseDetector (ABC)
    ├── PatternDetector      # Regex-based pattern matching (default)
    ├── EmbeddingDetector    # Semantic similarity detection (optional)
    ├── StructuralDetector   # Structural analysis (optional)
    └── CustomDetector       # User-defined detectors

Design Principles:
    - Single Responsibility: Each detector focuses on one detection strategy
    - Open/Closed: New detectors can be added without modifying existing code
    - Liskov Substitution: All detectors are interchangeable via the interface
    - Interface Segregation: Minimal required interface, optional extensions
    - Dependency Inversion: InputValidator depends on BaseDetector, not concrete types

Usage:
    from sentinelseed.detection.detectors.base import BaseDetector
    from sentinelseed.detection.types import DetectionResult, AttackType

    class MyDetector(BaseDetector):
        @property
        def name(self) -> str:
            return "my_detector"

        @property
        def version(self) -> str:
            return "1.0.0"

        def detect(self, text: str, context: Optional[dict] = None) -> DetectionResult:
            if self._is_suspicious(text):
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.95,
                    category=AttackType.MANIPULATION.value,
                    description="Detected suspicious pattern",
                )
            return DetectionResult.nothing_detected(self.name, self.version)

References:
    - INPUT_VALIDATOR_v2.md: Design specification
    - VALIDATION_360_v2.md: Architecture overview
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from sentinelseed.detection.types import DetectionResult, AttackType


@dataclass
class DetectorConfig:
    """
    Configuration for a detector.

    This provides a standard way to configure detectors without
    requiring detector-specific configuration classes.

    Attributes:
        enabled: Whether the detector is active
        confidence_threshold: Minimum confidence to report detection
        categories: Attack types this detector should look for (empty = all)
        options: Detector-specific configuration options

    Example:
        config = DetectorConfig(
            enabled=True,
            confidence_threshold=0.7,
            categories=[AttackType.JAILBREAK, AttackType.INJECTION],
            options={"strict_mode": True},
        )
        detector = PatternDetector(config=config)
    """
    enabled: bool = True
    confidence_threshold: float = 0.0
    categories: Sequence[AttackType] = field(default_factory=list)
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration values."""
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError(
                f"confidence_threshold must be between 0.0 and 1.0, "
                f"got {self.confidence_threshold}"
            )
        if not isinstance(self.categories, (list, tuple)):
            self.categories = list(self.categories)

    def get_option(self, key: str, default: Any = None) -> Any:
        """
        Get a detector-specific option.

        Args:
            key: Option name
            default: Default value if option not set

        Returns:
            Option value or default
        """
        return self.options.get(key, default)


class BaseDetector(ABC):
    """
    Abstract base class for all attack detectors.

    All detectors must inherit from this class and implement the required
    abstract methods. The base class provides:

    - Standard interface for detection
    - Configuration management
    - Enable/disable functionality
    - Statistics tracking (optional)

    Required implementations:
        - name (property): Unique identifier for the detector
        - version (property): Semantic version string
        - detect(text, context): Main detection method

    Optional overrides:
        - initialize(): Called once before first detection
        - shutdown(): Called when detector is being removed
        - get_stats(): Return detection statistics
        - reset_stats(): Reset statistics counters

    Example:
        class JailbreakDetector(BaseDetector):
            def __init__(self, config: DetectorConfig = None):
                super().__init__(config)
                self._patterns = self._load_patterns()

            @property
            def name(self) -> str:
                return "jailbreak_detector"

            @property
            def version(self) -> str:
                return "2.1.0"

            def detect(self, text: str, context: Optional[dict] = None) -> DetectionResult:
                for pattern in self._patterns:
                    if pattern.search(text):
                        return DetectionResult(
                            detected=True,
                            detector_name=self.name,
                            detector_version=self.version,
                            confidence=0.9,
                            category=AttackType.JAILBREAK.value,
                            description="Jailbreak pattern detected",
                            evidence=pattern.pattern,
                        )
                return DetectionResult.nothing_detected(self.name, self.version)
    """

    def __init__(self, config: Optional[DetectorConfig] = None) -> None:
        """
        Initialize the detector with optional configuration.

        Args:
            config: Detector configuration. If None, uses default config.
        """
        self._config = config or DetectorConfig()
        self._initialized = False
        self._stats: Dict[str, Any] = {
            "detections": 0,
            "total_calls": 0,
            "errors": 0,
        }

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Unique identifier for this detector.

        Returns:
            Detector name (e.g., "pattern_detector", "embedding_detector")

        Note:
            This should be a stable identifier that doesn't change between versions.
            Use lowercase with underscores (snake_case).
        """
        ...

    @property
    @abstractmethod
    def version(self) -> str:
        """
        Semantic version of this detector.

        Returns:
            Version string (e.g., "1.0.0", "2.1.3")

        Note:
            Follow semantic versioning: MAJOR.MINOR.PATCH
            - MAJOR: Breaking changes to detection behavior
            - MINOR: New patterns/capabilities, backwards compatible
            - PATCH: Bug fixes, no behavior change
        """
        ...

    @property
    def config(self) -> DetectorConfig:
        """
        Get the detector's configuration.

        Returns:
            Current DetectorConfig instance
        """
        return self._config

    @property
    def enabled(self) -> bool:
        """
        Whether this detector is enabled.

        Returns:
            True if detector should be used, False to skip
        """
        return self._config.enabled

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """
        Enable or disable this detector.

        Args:
            value: True to enable, False to disable
        """
        self._config.enabled = value

    @abstractmethod
    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect attacks in the provided text.

        This is the main detection method that all detectors must implement.
        It analyzes the input text and returns a DetectionResult indicating
        whether an attack was detected.

        Args:
            text: The text content to analyze for attacks
            context: Optional contextual information that may aid detection:
                - "source": Where the text came from (e.g., "user_input", "api")
                - "previous_messages": Conversation history
                - "user_id": User identifier for pattern tracking
                - Other detector-specific context

        Returns:
            DetectionResult containing:
            - detected: Whether an attack was found
            - detector_name: This detector's name
            - detector_version: This detector's version
            - confidence: Confidence score if detected
            - category: AttackType if detected
            - description: Human-readable description
            - evidence: The specific pattern/text that triggered detection

        Raises:
            ValueError: If text is None
            RuntimeError: If detector is not initialized (call initialize() first)

        Example:
            result = detector.detect("ignore previous instructions")
            if result.detected:
                print(f"Attack detected: {result.description}")
                print(f"Confidence: {result.confidence}")
        """
        ...

    def detect_batch(
        self,
        texts: Sequence[str],
        contexts: Optional[Sequence[Optional[Dict[str, Any]]]] = None,
    ) -> List[DetectionResult]:
        """
        Detect attacks in multiple texts.

        Default implementation calls detect() for each text.
        Subclasses may override for optimized batch processing.

        Args:
            texts: Sequence of texts to analyze
            contexts: Optional sequence of contexts (one per text, or None)

        Returns:
            List of DetectionResults, one per input text

        Raises:
            ValueError: If texts and contexts have different lengths
        """
        if contexts is not None and len(contexts) != len(texts):
            raise ValueError(
                f"texts and contexts must have same length: "
                f"{len(texts)} vs {len(contexts)}"
            )

        results = []
        for i, text in enumerate(texts):
            ctx = contexts[i] if contexts else None
            results.append(self.detect(text, ctx))
        return results

    def initialize(self) -> None:
        """
        Initialize the detector before first use.

        Override this method to perform one-time setup such as:
        - Loading pattern databases
        - Initializing ML models
        - Establishing connections

        This is called automatically before the first detect() call,
        or can be called explicitly for eager initialization.

        Example:
            class EmbeddingDetector(BaseDetector):
                def initialize(self):
                    super().initialize()
                    self._model = SentenceTransformer("all-MiniLM-L6-v2")
                    self._attack_embeddings = self._load_attack_embeddings()
        """
        self._initialized = True

    def shutdown(self) -> None:
        """
        Clean up resources when detector is being removed.

        Override this method to release resources such as:
        - Closing database connections
        - Releasing ML model memory
        - Flushing caches

        Example:
            class EmbeddingDetector(BaseDetector):
                def shutdown(self):
                    self._model = None
                    self._attack_embeddings = None
                    super().shutdown()
        """
        self._initialized = False

    def get_stats(self) -> Dict[str, Any]:
        """
        Get detection statistics.

        Returns:
            Dictionary with statistics:
            - detections: Number of attacks detected
            - total_calls: Total detect() calls
            - errors: Number of errors encountered
            - Additional detector-specific stats

        Example:
            stats = detector.get_stats()
            print(f"Detection rate: {stats['detections'] / stats['total_calls']:.1%}")
        """
        return self._stats.copy()

    def reset_stats(self) -> None:
        """Reset detection statistics to zero."""
        self._stats = {
            "detections": 0,
            "total_calls": 0,
            "errors": 0,
        }

    def _ensure_initialized(self) -> None:
        """Ensure detector is initialized before use."""
        if not self._initialized:
            self.initialize()

    def _update_stats(self, result: DetectionResult) -> None:
        """
        Update statistics based on detection result.

        Args:
            result: The detection result to record
        """
        self._stats["total_calls"] = self._stats.get("total_calls", 0) + 1
        if result.detected:
            self._stats["detections"] = self._stats.get("detections", 0) + 1

    def __repr__(self) -> str:
        """String representation of the detector."""
        return (
            f"{self.__class__.__name__}("
            f"name={self.name!r}, "
            f"version={self.version!r}, "
            f"enabled={self.enabled})"
        )


__all__ = [
    "BaseDetector",
    "DetectorConfig",
]
