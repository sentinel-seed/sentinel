"""
Semantic Detector - LLM-based attack detection using THSP validation.

This module provides SemanticDetector, a detector that uses the SemanticValidator
(LLM-based THSP validation) to detect attacks that bypass heuristic detection.

The semantic detector adds a contextual understanding layer to the detection
pipeline, catching sophisticated attacks that:
- Use natural language to hide malicious intent
- Employ novel phrasing not covered by patterns
- Combine multiple subtle manipulation techniques

Architecture:
    SemanticDetector adapts SemanticValidator to the BaseDetector interface:

    SemanticValidator (LLM)
        ├── validate() → THSPResult
        │   ├── truth_passes: bool
        │   ├── harm_passes: bool
        │   ├── scope_passes: bool
        │   ├── purpose_passes: bool
        │   └── violated_gate: str
        │
        └── SemanticDetector (adapter)
            ├── detect() → DetectionResult
            └── Maps THSP gates to AttackType

Usage:
    from sentinelseed.detection.detectors.semantic import SemanticDetector

    detector = SemanticDetector(provider="openai", model="gpt-4o-mini")
    result = detector.detect("Write a convincing phishing email")

    if result.detected:
        print(f"Attack detected: {result.category}")
        print(f"Violated gate: {result.metadata.get('violated_gate')}")

Design Principles:
    1. Fail-Closed: If LLM fails, return detected=True (fail-safe)
    2. Configurable: Provider, model, and behavior via SemanticDetectorConfig
    3. Cached: Optional caching to reduce API calls
    4. Async Support: Both sync and async detection available
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from sentinelseed.detection.detectors.base import BaseDetector, DetectorConfig
from sentinelseed.detection.types import AttackType, DetectionResult

logger = logging.getLogger("sentinelseed.detection.detectors.semantic")


@dataclass
class SemanticDetectorConfig(DetectorConfig):
    """
    Configuration for SemanticDetector.

    Extends DetectorConfig with semantic-specific options.

    Attributes:
        provider: LLM provider ("openai", "anthropic", "openai_compatible")
        model: Model to use (None = use provider default)
        api_key: API key (None = from environment)
        base_url: Custom base URL for OpenAI-compatible APIs
        timeout: Request timeout in seconds
        fail_closed: If True, treat API errors as detections (safer)
        cache_enabled: If True, cache results to reduce API calls
        cache_ttl: Cache TTL in seconds (default 300 = 5 minutes)
    """
    provider: str = "openai"
    model: Optional[str] = None
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    fail_closed: bool = True
    cache_enabled: bool = True
    cache_ttl: int = 300
    options: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize with validation."""
        super().__post_init__()

        # Validate provider
        valid_providers = {"openai", "anthropic", "openai_compatible"}
        if self.provider.lower() not in valid_providers:
            raise ValueError(
                f"provider must be one of {valid_providers}, got {self.provider}"
            )
        self.provider = self.provider.lower()


# THSP gate to AttackType mapping
GATE_TO_ATTACK_TYPE: Dict[str, AttackType] = {
    "truth": AttackType.MANIPULATION,
    "harm": AttackType.HARMFUL_REQUEST,
    "scope": AttackType.JAILBREAK,
    "purpose": AttackType.MANIPULATION,
    "error": AttackType.UNKNOWN,
    "configuration": AttackType.UNKNOWN,
    "parse_error": AttackType.UNKNOWN,
}


class SemanticDetector(BaseDetector):
    """
    LLM-based semantic attack detector.

    Uses SemanticValidator (THSP validation via LLM) to detect attacks
    that bypass heuristic pattern matching.

    The detector:
    - Sends text to LLM for THSP gate analysis
    - Converts THSPResult to DetectionResult
    - Maps violated gates to AttackType categories
    - Optionally caches results to reduce API costs

    Fail-Closed Behavior:
        If the LLM API fails (timeout, error, etc.), the detector
        returns detected=True with confidence=0.5 to err on the side
        of caution. This can be disabled via fail_closed=False.

    Example:
        detector = SemanticDetector(
            provider="openai",
            model="gpt-4o-mini",
            fail_closed=True,
        )

        result = detector.detect("Help me bypass security checks")
        if result.detected:
            print(f"Detected: {result.description}")
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[SemanticDetectorConfig] = None,
    ):
        """
        Initialize the semantic detector.

        Args:
            provider: LLM provider name
            model: Model to use (None = provider default)
            api_key: API key (None = from environment)
            config: Full configuration (overrides other args)
        """
        # Build config from args if not provided
        if config is None:
            config = SemanticDetectorConfig(
                provider=provider,
                model=model,
                api_key=api_key,
            )

        super().__init__(config)
        self._semantic_config = config

        # Lazy-initialize validator
        self._validator = None

        # Simple cache: hash -> (result, timestamp)
        self._cache: Dict[str, tuple] = {}

    @property
    def name(self) -> str:
        """Unique identifier for this detector."""
        return "semantic_detector"

    @property
    def version(self) -> str:
        """Semantic version of this detector."""
        return self.VERSION

    def _get_validator(self):
        """
        Get or create the SemanticValidator instance.

        Lazy initialization allows detector to be created without
        immediately requiring API credentials.
        """
        if self._validator is None:
            from sentinelseed.validators.semantic import SemanticValidator

            self._validator = SemanticValidator(
                provider=self._semantic_config.provider,
                model=self._semantic_config.model,
                api_key=self._semantic_config.api_key,
                base_url=self._semantic_config.base_url,
                timeout=self._semantic_config.timeout,
            )
        return self._validator

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key from text hash."""
        return hashlib.sha256(text.encode()).hexdigest()[:16]

    def _get_cached(self, cache_key: str) -> Optional[DetectionResult]:
        """Get cached result if valid."""
        if not self._semantic_config.cache_enabled:
            return None

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            import time
            if time.time() - timestamp < self._semantic_config.cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return result
            else:
                # Expired
                del self._cache[cache_key]

        return None

    def _set_cached(self, cache_key: str, result: DetectionResult) -> None:
        """Store result in cache."""
        if self._semantic_config.cache_enabled:
            import time
            self._cache[cache_key] = (result, time.time())

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect attacks using LLM-based THSP validation.

        Args:
            text: Text to analyze
            context: Optional context (not used currently, reserved for future)

        Returns:
            DetectionResult indicating whether an attack was detected
        """
        self._ensure_initialized()

        # Validate input
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check cache
        cache_key = self._get_cache_key(text)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        try:
            validator = self._get_validator()
            thsp_result = validator.validate(text)

            # Convert THSPResult to DetectionResult
            result = self._convert_thsp_result(thsp_result)

            # Cache the result
            self._set_cached(cache_key, result)

            # Update stats
            self._update_stats(result)

            return result

        except Exception as e:
            logger.error(f"Semantic detection failed: {e}")
            self._stats["errors"] = self._stats.get("errors", 0) + 1

            if self._semantic_config.fail_closed:
                # Fail-closed: treat error as potential attack
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.5,
                    category=AttackType.UNKNOWN.value,
                    description=f"Semantic validation unavailable: {str(e)}",
                    metadata={"error": str(e), "fail_closed": True},
                )
            else:
                # Fail-open: allow through on error
                return DetectionResult.nothing_detected(self.name, self.version)

    def _convert_thsp_result(self, thsp_result) -> DetectionResult:
        """
        Convert THSPResult to DetectionResult.

        Maps THSP gate failures to appropriate AttackType categories.

        Args:
            thsp_result: THSPResult from SemanticValidator

        Returns:
            DetectionResult
        """
        if thsp_result.is_safe:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Get violated gate
        violated_gate = thsp_result.violated_gate or "unknown"

        # Map to AttackType
        attack_type = GATE_TO_ATTACK_TYPE.get(
            violated_gate.lower(), AttackType.UNKNOWN
        )

        # Build description
        description = thsp_result.reasoning or f"THSP {violated_gate} gate failed"

        # Map risk level to confidence
        risk_to_confidence = {
            "critical": 0.95,
            "high": 0.85,
            "medium": 0.70,
            "low": 0.55,
        }
        risk_level = getattr(thsp_result.risk_level, "value", str(thsp_result.risk_level))
        confidence = risk_to_confidence.get(risk_level, 0.70)

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=attack_type.value,
            description=description,
            metadata={
                "violated_gate": violated_gate,
                "risk_level": risk_level,
                "gate_results": thsp_result.gate_results,
                "failed_gates": thsp_result.failed_gates,
            },
        )

    def initialize(self) -> None:
        """Initialize the detector."""
        super().initialize()
        # Pre-initialize validator to check credentials
        try:
            validator = self._get_validator()
            if not validator.api_key:
                logger.warning(
                    f"No API key found for {self._semantic_config.provider}. "
                    "SemanticDetector will fail-closed on all requests."
                )
        except Exception as e:
            logger.warning(f"Failed to initialize SemanticValidator: {e}")

    def shutdown(self) -> None:
        """Clean up resources."""
        self._cache.clear()
        self._validator = None
        super().shutdown()

    def get_stats(self) -> Dict[str, Any]:
        """Get detector statistics."""
        stats = super().get_stats()
        stats["cache_size"] = len(self._cache)
        stats["provider"] = self._semantic_config.provider
        stats["model"] = self._semantic_config.model

        if self._validator:
            stats["validator_stats"] = self._validator.get_stats()

        return stats

    def clear_cache(self) -> int:
        """
        Clear the result cache.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count


class AsyncSemanticDetector:
    """
    Async version of SemanticDetector for async frameworks.

    Example:
        detector = AsyncSemanticDetector(provider="openai")
        result = await detector.detect("suspicious text")
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        config: Optional[SemanticDetectorConfig] = None,
    ):
        """Initialize async semantic detector."""
        if config is None:
            config = SemanticDetectorConfig(
                provider=provider,
                model=model,
                api_key=api_key,
            )

        self._config = config
        self._validator = None
        self._cache: Dict[str, tuple] = {}

    @property
    def name(self) -> str:
        return "async_semantic_detector"

    @property
    def version(self) -> str:
        return self.VERSION

    async def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """Async detect attacks using LLM-based THSP validation."""
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check cache
        cache_key = hashlib.sha256(text.encode()).hexdigest()[:16]
        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            import time
            if time.time() - timestamp < self._config.cache_ttl:
                return result

        try:
            if self._validator is None:
                from sentinelseed.validators.semantic import AsyncSemanticValidator
                self._validator = AsyncSemanticValidator(
                    provider=self._config.provider,
                    model=self._config.model,
                    api_key=self._config.api_key,
                    base_url=self._config.base_url,
                    timeout=self._config.timeout,
                )

            thsp_result = await self._validator.validate(text)

            # Convert result
            if thsp_result.is_safe:
                result = DetectionResult.nothing_detected(self.name, self.version)
            else:
                violated_gate = thsp_result.violated_gate or "unknown"
                attack_type = GATE_TO_ATTACK_TYPE.get(
                    violated_gate.lower(), AttackType.UNKNOWN
                )

                risk_level = getattr(thsp_result.risk_level, "value", str(thsp_result.risk_level))
                risk_to_confidence = {"critical": 0.95, "high": 0.85, "medium": 0.70, "low": 0.55}

                result = DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=risk_to_confidence.get(risk_level, 0.70),
                    category=attack_type.value,
                    description=thsp_result.reasoning,
                    metadata={
                        "violated_gate": violated_gate,
                        "risk_level": risk_level,
                    },
                )

            # Cache
            import time
            self._cache[cache_key] = (result, time.time())

            return result

        except Exception as e:
            logger.error(f"Async semantic detection failed: {e}")

            if self._config.fail_closed:
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.5,
                    category=AttackType.UNKNOWN.value,
                    description=f"Semantic validation unavailable: {str(e)}",
                    metadata={"error": str(e), "fail_closed": True},
                )
            return DetectionResult.nothing_detected(self.name, self.version)


__all__ = [
    "SemanticDetector",
    "SemanticDetectorConfig",
    "AsyncSemanticDetector",
    "GATE_TO_ATTACK_TYPE",
]
