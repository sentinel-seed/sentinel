"""
Tests for sentinelseed.detection.detectors.base module.

This module tests the BaseDetector abstract base class and DetectorConfig.
Tests verify the contract that all detector implementations must follow.

Test Categories:
    1. DetectorConfig: Creation, validation, options
    2. BaseDetector Abstract: Cannot instantiate, requires implementations
    3. BaseDetector Contract: Properties, methods, lifecycle
    4. Statistics: Tracking, updating, resetting
    5. Batch Detection: Default implementation, error handling
    6. Lifecycle: initialize(), shutdown(), _ensure_initialized()
"""

import pytest
from typing import Dict, Any, Optional

from sentinelseed.detection.detectors.base import (
    BaseDetector,
    DetectorConfig,
)
from sentinelseed.detection.types import (
    DetectionResult,
    AttackType,
)


# =============================================================================
# Test Fixtures - Concrete Detector Implementation for Testing
# =============================================================================

class SimpleTestDetector(BaseDetector):
    """
    Minimal concrete detector implementation for testing BaseDetector.

    This detector detects the word "attack" in text.
    """

    def __init__(self, config: Optional[DetectorConfig] = None):
        super().__init__(config)
        self._detection_word = "attack"

    @property
    def name(self) -> str:
        return "simple_test_detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        self._ensure_initialized()
        self._stats["total_calls"] += 1

        if self._detection_word.lower() in text.lower():
            result = DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.9,
                category=AttackType.UNKNOWN.value,
                description=f"Found '{self._detection_word}' in text",
                evidence=self._detection_word,
            )
            self._stats["detections"] += 1
            return result

        return DetectionResult.nothing_detected(self.name, self.version)


class ConfigurableTestDetector(BaseDetector):
    """
    Detector that uses configuration options for testing.
    """

    @property
    def name(self) -> str:
        return "configurable_test_detector"

    @property
    def version(self) -> str:
        return "2.0.0"

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        keyword = self._config.get_option("keyword", "default")
        if keyword.lower() in text.lower():
            return DetectionResult(
                detected=True,
                detector_name=self.name,
                detector_version=self.version,
                confidence=0.8,
                category=AttackType.UNKNOWN.value,
                description=f"Found configured keyword: {keyword}",
            )
        return DetectionResult.nothing_detected(self.name, self.version)


class LifecycleTestDetector(BaseDetector):
    """
    Detector that tracks lifecycle method calls for testing.
    """

    def __init__(self, config: Optional[DetectorConfig] = None):
        super().__init__(config)
        self.lifecycle_events: list = []

    @property
    def name(self) -> str:
        return "lifecycle_test_detector"

    @property
    def version(self) -> str:
        return "1.0.0"

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        self._ensure_initialized()
        self.lifecycle_events.append("detect")
        return DetectionResult.nothing_detected(self.name, self.version)

    def initialize(self) -> None:
        self.lifecycle_events.append("initialize")
        super().initialize()

    def shutdown(self) -> None:
        self.lifecycle_events.append("shutdown")
        super().shutdown()


# =============================================================================
# DetectorConfig Tests
# =============================================================================

class TestDetectorConfig:
    """Tests for DetectorConfig dataclass."""

    def test_default_values(self):
        """Default values are correctly set."""
        config = DetectorConfig()
        assert config.enabled is True
        assert config.confidence_threshold == 0.0
        assert config.categories == []
        assert config.options == {}

    def test_custom_values(self):
        """Can create with custom values."""
        config = DetectorConfig(
            enabled=False,
            confidence_threshold=0.7,
            categories=[AttackType.JAILBREAK, AttackType.INJECTION],
            options={"strict": True, "max_length": 1000},
        )
        assert config.enabled is False
        assert config.confidence_threshold == 0.7
        assert AttackType.JAILBREAK in config.categories
        assert config.options["strict"] is True


class TestDetectorConfigValidation:
    """Tests for DetectorConfig validation."""

    def test_confidence_threshold_below_zero_raises(self):
        """confidence_threshold < 0 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(confidence_threshold=-0.1)
        assert "confidence_threshold" in str(exc_info.value)
        assert "0.0" in str(exc_info.value)

    def test_confidence_threshold_above_one_raises(self):
        """confidence_threshold > 1 raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DetectorConfig(confidence_threshold=1.1)
        assert "confidence_threshold" in str(exc_info.value)
        assert "1.0" in str(exc_info.value)

    def test_confidence_threshold_at_boundaries(self):
        """confidence_threshold at 0.0 and 1.0 is valid."""
        config_zero = DetectorConfig(confidence_threshold=0.0)
        config_one = DetectorConfig(confidence_threshold=1.0)
        assert config_zero.confidence_threshold == 0.0
        assert config_one.confidence_threshold == 1.0


class TestDetectorConfigGetOption:
    """Tests for DetectorConfig.get_option() method."""

    def test_get_existing_option(self):
        """get_option returns value for existing option."""
        config = DetectorConfig(options={"key1": "value1", "key2": 42})
        assert config.get_option("key1") == "value1"
        assert config.get_option("key2") == 42

    def test_get_missing_option_returns_default(self):
        """get_option returns default for missing option."""
        config = DetectorConfig(options={})
        assert config.get_option("missing") is None
        assert config.get_option("missing", "fallback") == "fallback"
        assert config.get_option("missing", 0) == 0

    def test_get_option_with_none_value(self):
        """get_option returns None if that's the stored value."""
        config = DetectorConfig(options={"explicit_none": None})
        assert config.get_option("explicit_none") is None
        # Default is NOT used when key exists
        assert config.get_option("explicit_none", "default") is None


# =============================================================================
# BaseDetector Abstract Tests
# =============================================================================

class TestBaseDetectorAbstract:
    """Tests verifying BaseDetector is properly abstract."""

    def test_cannot_instantiate_directly(self):
        """Cannot instantiate BaseDetector directly."""
        with pytest.raises(TypeError) as exc_info:
            BaseDetector()
        # Error should mention abstract methods
        error_msg = str(exc_info.value)
        assert "abstract" in error_msg.lower()

    def test_must_implement_name(self):
        """Subclass without name property fails."""
        class IncompleteDetector(BaseDetector):
            @property
            def version(self) -> str:
                return "1.0.0"

            def detect(self, text, context=None):
                return DetectionResult.nothing_detected("test", "1.0")

        with pytest.raises(TypeError):
            IncompleteDetector()

    def test_must_implement_version(self):
        """Subclass without version property fails."""
        class IncompleteDetector(BaseDetector):
            @property
            def name(self) -> str:
                return "test"

            def detect(self, text, context=None):
                return DetectionResult.nothing_detected("test", "1.0")

        with pytest.raises(TypeError):
            IncompleteDetector()

    def test_must_implement_detect(self):
        """Subclass without detect method fails."""
        class IncompleteDetector(BaseDetector):
            @property
            def name(self) -> str:
                return "test"

            @property
            def version(self) -> str:
                return "1.0.0"

        with pytest.raises(TypeError):
            IncompleteDetector()


# =============================================================================
# BaseDetector Properties Tests
# =============================================================================

class TestBaseDetectorProperties:
    """Tests for BaseDetector properties."""

    def test_name_property(self):
        """name property returns detector name."""
        detector = SimpleTestDetector()
        assert detector.name == "simple_test_detector"

    def test_version_property(self):
        """version property returns detector version."""
        detector = SimpleTestDetector()
        assert detector.version == "1.0.0"

    def test_config_property_default(self):
        """config property returns default config when not provided."""
        detector = SimpleTestDetector()
        assert isinstance(detector.config, DetectorConfig)
        assert detector.config.enabled is True

    def test_config_property_custom(self):
        """config property returns provided config."""
        config = DetectorConfig(enabled=False, confidence_threshold=0.5)
        detector = SimpleTestDetector(config=config)
        assert detector.config.enabled is False
        assert detector.config.confidence_threshold == 0.5

    def test_enabled_property_getter(self):
        """enabled property returns config.enabled value."""
        detector = SimpleTestDetector()
        assert detector.enabled is True

        disabled_config = DetectorConfig(enabled=False)
        disabled_detector = SimpleTestDetector(disabled_config)
        assert disabled_detector.enabled is False

    def test_enabled_property_setter(self):
        """enabled property setter modifies config."""
        detector = SimpleTestDetector()
        assert detector.enabled is True

        detector.enabled = False
        assert detector.enabled is False
        assert detector.config.enabled is False

        detector.enabled = True
        assert detector.enabled is True


# =============================================================================
# BaseDetector Detection Tests
# =============================================================================

class TestBaseDetectorDetection:
    """Tests for BaseDetector.detect() behavior."""

    def test_detect_returns_detection_result(self):
        """detect() returns DetectionResult."""
        detector = SimpleTestDetector()
        result = detector.detect("safe text")
        assert isinstance(result, DetectionResult)

    def test_detect_finds_attack(self):
        """detect() finds attack when present."""
        detector = SimpleTestDetector()
        result = detector.detect("this is an attack")
        assert result.detected is True
        assert result.detector_name == "simple_test_detector"
        assert result.detector_version == "1.0.0"
        assert result.confidence > 0

    def test_detect_no_attack(self):
        """detect() returns nothing_detected when no attack."""
        detector = SimpleTestDetector()
        result = detector.detect("completely safe text")
        assert result.detected is False
        assert result.detector_name == "simple_test_detector"

    def test_detect_uses_context(self):
        """detect() can receive and use context."""
        detector = SimpleTestDetector()
        # Our simple detector doesn't use context, but should accept it
        result = detector.detect(
            "attack text",
            context={"user_id": "123", "source": "api"}
        )
        assert result.detected is True

    def test_detect_with_config_options(self):
        """detect() can use config options."""
        config = DetectorConfig(options={"keyword": "danger"})
        detector = ConfigurableTestDetector(config=config)

        # Should detect "danger" not "attack"
        result1 = detector.detect("this is dangerous")
        assert result1.detected is True

        result2 = detector.detect("this is an attack")
        assert result2.detected is False


# =============================================================================
# BaseDetector Statistics Tests
# =============================================================================

class TestBaseDetectorStats:
    """Tests for BaseDetector statistics tracking."""

    def test_initial_stats(self):
        """Initial stats are zero."""
        detector = SimpleTestDetector()
        stats = detector.get_stats()
        assert stats["detections"] == 0
        assert stats["total_calls"] == 0
        assert stats["errors"] == 0

    def test_stats_increment_on_detection(self):
        """Stats increment when detection occurs."""
        detector = SimpleTestDetector()
        detector.detect("attack text")
        stats = detector.get_stats()
        assert stats["detections"] == 1
        assert stats["total_calls"] == 1

    def test_stats_increment_on_no_detection(self):
        """total_calls increments even when no detection."""
        detector = SimpleTestDetector()
        detector.detect("safe text")
        stats = detector.get_stats()
        assert stats["detections"] == 0
        assert stats["total_calls"] == 1

    def test_stats_accumulate(self):
        """Stats accumulate across multiple calls."""
        detector = SimpleTestDetector()
        detector.detect("attack 1")
        detector.detect("safe")
        detector.detect("attack 2")
        detector.detect("safe again")

        stats = detector.get_stats()
        assert stats["total_calls"] == 4
        assert stats["detections"] == 2

    def test_reset_stats(self):
        """reset_stats() clears all statistics."""
        detector = SimpleTestDetector()
        detector.detect("attack")
        detector.detect("safe")

        detector.reset_stats()
        stats = detector.get_stats()
        assert stats["detections"] == 0
        assert stats["total_calls"] == 0
        assert stats["errors"] == 0

    def test_get_stats_returns_copy(self):
        """get_stats() returns a copy, not the original dict."""
        detector = SimpleTestDetector()
        stats1 = detector.get_stats()
        stats1["detections"] = 999  # Modify the copy

        stats2 = detector.get_stats()
        assert stats2["detections"] == 0  # Original unchanged


# =============================================================================
# BaseDetector Batch Detection Tests
# =============================================================================

class TestBaseDetectorBatch:
    """Tests for BaseDetector.detect_batch() method."""

    def test_detect_batch_basic(self):
        """detect_batch() processes multiple texts."""
        detector = SimpleTestDetector()
        texts = ["attack one", "safe text", "another attack"]
        results = detector.detect_batch(texts)

        assert len(results) == 3
        assert results[0].detected is True
        assert results[1].detected is False
        assert results[2].detected is True

    def test_detect_batch_with_contexts(self):
        """detect_batch() uses provided contexts."""
        detector = SimpleTestDetector()
        texts = ["text1", "text2"]
        contexts = [{"id": 1}, {"id": 2}]

        results = detector.detect_batch(texts, contexts)
        assert len(results) == 2

    def test_detect_batch_length_mismatch_raises(self):
        """detect_batch() raises if texts and contexts lengths differ."""
        detector = SimpleTestDetector()
        texts = ["text1", "text2", "text3"]
        contexts = [{"id": 1}]  # Only one context

        with pytest.raises(ValueError) as exc_info:
            detector.detect_batch(texts, contexts)
        assert "same length" in str(exc_info.value)

    def test_detect_batch_empty_lists(self):
        """detect_batch() handles empty lists."""
        detector = SimpleTestDetector()
        results = detector.detect_batch([])
        assert results == []

    def test_detect_batch_none_contexts(self):
        """detect_batch() works with contexts=None."""
        detector = SimpleTestDetector()
        texts = ["attack", "safe"]
        results = detector.detect_batch(texts, contexts=None)
        assert len(results) == 2


# =============================================================================
# BaseDetector Lifecycle Tests
# =============================================================================

class TestBaseDetectorLifecycle:
    """Tests for BaseDetector lifecycle methods."""

    def test_initialize_sets_flag(self):
        """initialize() sets _initialized flag."""
        detector = LifecycleTestDetector()
        assert detector._initialized is False

        detector.initialize()
        assert detector._initialized is True

    def test_shutdown_clears_flag(self):
        """shutdown() clears _initialized flag."""
        detector = LifecycleTestDetector()
        detector.initialize()
        assert detector._initialized is True

        detector.shutdown()
        assert detector._initialized is False

    def test_ensure_initialized_auto_initializes(self):
        """_ensure_initialized() calls initialize() if needed."""
        detector = LifecycleTestDetector()
        assert detector._initialized is False
        assert "initialize" not in detector.lifecycle_events

        # detect() calls _ensure_initialized()
        detector.detect("test")

        assert detector._initialized is True
        assert "initialize" in detector.lifecycle_events
        assert detector.lifecycle_events.index("initialize") < \
               detector.lifecycle_events.index("detect")

    def test_ensure_initialized_only_once(self):
        """_ensure_initialized() only initializes once."""
        detector = LifecycleTestDetector()

        detector.detect("test1")
        detector.detect("test2")
        detector.detect("test3")

        # initialize should only appear once
        assert detector.lifecycle_events.count("initialize") == 1

    def test_lifecycle_sequence(self):
        """Lifecycle methods are called in correct sequence."""
        detector = LifecycleTestDetector()

        detector.initialize()
        detector.detect("test")
        detector.shutdown()

        assert detector.lifecycle_events == ["initialize", "detect", "shutdown"]


# =============================================================================
# BaseDetector Repr Tests
# =============================================================================

class TestBaseDetectorRepr:
    """Tests for BaseDetector.__repr__() method."""

    def test_repr_contains_class_name(self):
        """__repr__ contains the class name."""
        detector = SimpleTestDetector()
        repr_str = repr(detector)
        assert "SimpleTestDetector" in repr_str

    def test_repr_contains_name(self):
        """__repr__ contains detector name."""
        detector = SimpleTestDetector()
        repr_str = repr(detector)
        assert "simple_test_detector" in repr_str

    def test_repr_contains_version(self):
        """__repr__ contains version."""
        detector = SimpleTestDetector()
        repr_str = repr(detector)
        assert "1.0.0" in repr_str

    def test_repr_contains_enabled_status(self):
        """__repr__ contains enabled status."""
        detector = SimpleTestDetector()
        repr_str = repr(detector)
        assert "enabled=True" in repr_str

        detector.enabled = False
        repr_str = repr(detector)
        assert "enabled=False" in repr_str


# =============================================================================
# Integration Tests
# =============================================================================

class TestBaseDetectorIntegration:
    """Integration tests for complete detector workflows."""

    def test_full_detection_workflow(self):
        """Complete detection workflow with stats and lifecycle."""
        # Create detector with config
        config = DetectorConfig(
            enabled=True,
            confidence_threshold=0.5,
            options={"strict": True},
        )
        detector = SimpleTestDetector(config=config)

        # Verify initial state
        assert detector.enabled is True
        assert detector._initialized is False
        assert detector.get_stats()["total_calls"] == 0

        # First detection (triggers auto-initialize)
        result1 = detector.detect("safe text")
        assert detector._initialized is True
        assert result1.detected is False

        # Second detection (attack found)
        result2 = detector.detect("attack detected")
        assert result2.detected is True
        assert result2.detector_name == detector.name
        assert result2.detector_version == detector.version

        # Verify stats
        stats = detector.get_stats()
        assert stats["total_calls"] == 2
        assert stats["detections"] == 1

        # Shutdown and verify
        detector.shutdown()
        assert detector._initialized is False

    def test_detector_disable_during_operation(self):
        """Detector can be disabled during operation."""
        detector = SimpleTestDetector()

        # Works when enabled
        result1 = detector.detect("attack")
        assert result1.detected is True

        # Disable
        detector.enabled = False
        assert detector.enabled is False

        # Note: BaseDetector doesn't check enabled in detect()
        # That's the responsibility of the registry/validator
        # But the enabled flag should be accessible

    def test_multiple_detectors_independent(self):
        """Multiple detector instances are independent."""
        detector1 = SimpleTestDetector()
        detector2 = SimpleTestDetector()

        # Stats are independent
        detector1.detect("attack")
        assert detector1.get_stats()["detections"] == 1
        assert detector2.get_stats()["detections"] == 0

        # Config is independent
        detector1.enabled = False
        assert detector1.enabled is False
        assert detector2.enabled is True

        # Initialization is independent
        detector1.initialize()
        assert detector1._initialized is True
        assert detector2._initialized is False
