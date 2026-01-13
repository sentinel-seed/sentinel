"""
InputValidator - Attack detection for user input.

This module provides InputValidator, the entry point for validating user input
in the Validation 360 architecture. It answers the question:

    "Is this an ATTACK?"

InputValidator orchestrates multiple detectors to identify attacks in user input
BEFORE it reaches the AI. This is the first layer of the 360 validation:

    Input → [TextNormalizer] → [InputValidator] → AI + Seed → [OutputValidator] → Output

The TextNormalizer preprocessor removes obfuscation (base64, unicode tricks, etc.)
before detection, ensuring that hidden attacks are properly analyzed.

Design Principles:
    1. Non-Invasive: Validates without altering the input
    2. Pluggable: Detectors can be added/removed/upgraded at runtime
    3. Weighted: Detector results are weighted for final decision
    4. Configurable: Thresholds and behavior via InputValidatorConfig
    5. Fast: Heuristic-first approach, semantic only when needed

Default Detectors (registered automatically):
    1. PatternDetector (weight 1.0): 700+ regex patterns for direct attacks
    2. FramingDetector (weight 1.2): Roleplay, fiction, DAN mode detection
    3. EscalationDetector (weight 1.1): Multi-turn escalation detection
    4. HarmfulRequestDetector (weight 1.3): Direct harmful content requests

    Weights are based on research showing that:
    - Framing attacks (roleplay, fiction) often bypass pattern detection
    - Multi-turn attacks (Crescendo) achieve 98% ASR in research
    - Harmful requests need high weight after benchmark gap discovery (v1.3.0)

Attack Categories Detected:
    - Jailbreak: DAN, developer mode, role manipulation
    - Injection: Prompt injection, delimiter injection
    - Manipulation: Authority claims, urgency, roleplay, multi-turn escalation
    - Harmful Requests: Violence, malware, fraud instructions
    - Evasion: Prompt extraction, filter bypass, obfuscation
    - Structural: Suspicious patterns, encoding tricks

Usage:
    from sentinelseed.detection import InputValidator

    validator = InputValidator()
    result = validator.validate("ignore previous instructions and tell me...")

    if result.is_attack:
        print(f"Attack detected: {result.attack_types}")
        print(f"Confidence: {result.confidence}")
        if result.blocked:
            # Do not send to AI
            pass

Multi-turn Validation (with context):
    # For multi-turn attack detection, provide conversation history
    result = validator.validate(
        "Now make it more detailed",
        context={
            "previous_messages": [
                {"role": "user", "content": "Tell me about chemistry"},
                {"role": "assistant", "content": "Chemistry is..."},
                {"role": "user", "content": "What about energetic reactions?"},
            ]
        }
    )

Integration with LayeredValidator (Fase 2):
    validator = LayeredValidator()
    input_result = validator.validate_input(user_input)
    if input_result.is_safe:
        # Proceed to AI
        output_result = validator.validate_output(ai_response, user_input)

References:
    - INPUT_VALIDATOR_v2.md: Design specification
    - VALIDATION_360_v2.md: Architecture overview
    - Crescendo paper: arxiv.org/abs/2404.01833
    - MHJ dataset: arxiv.org/abs/2408.15221
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

if TYPE_CHECKING:
    from sentinelseed.detection.embeddings import AttackVectorDatabase

from sentinelseed.detection.types import (
    AttackType,
    DetectionResult,
    InputValidationResult,
    NormalizationResult,
)
from sentinelseed.detection.config import InputValidatorConfig
from sentinelseed.detection.registry import DetectorRegistry
from sentinelseed.detection.normalizer import TextNormalizer, NormalizerConfig

# Import benign context detector for FP reduction
try:
    from sentinelseed.detection.benign_context import BenignContextDetector
    BENIGN_CONTEXT_AVAILABLE = True
except ImportError:
    BENIGN_CONTEXT_AVAILABLE = False

logger = logging.getLogger("sentinelseed.detection.input_validator")


class InputValidator:
    """
    Validates user input for attack detection.

    InputValidator is the main entry point for input validation in the
    Validation 360 architecture. It coordinates multiple detectors to
    identify attacks before they reach the AI.

    The validator:
    - Registers default detectors on initialization
    - Runs enabled detectors on input
    - Aggregates results with configurable weights
    - Returns InputValidationResult with attack details

    Attributes:
        config: InputValidatorConfig controlling behavior
        registry: DetectorRegistry managing detectors

    Example:
        # Basic usage
        validator = InputValidator()
        result = validator.validate("user input text")

        if result.is_attack:
            print(f"Blocked: {result.violations}")

        # With configuration
        config = InputValidatorConfig(
            min_confidence_to_block=0.8,
            require_multiple_detectors=True,
        )
        validator = InputValidator(config=config)

        # Custom detectors
        validator.register_detector(MyCustomDetector(), weight=1.5)
    """

    VERSION = "1.8.0"  # Added BenignContextDetector for FP reduction

    def __init__(
        self,
        config: Optional[InputValidatorConfig] = None,
        normalizer_config: Optional[NormalizerConfig] = None,
    ):
        """
        Initialize InputValidator.

        Args:
            config: Optional InputValidatorConfig. If None, uses defaults.
            normalizer_config: Optional NormalizerConfig for text preprocessing.
        """
        self.config = config or InputValidatorConfig()
        self.registry = DetectorRegistry()

        # Initialize text normalizer for obfuscation removal
        self._normalizer = TextNormalizer(normalizer_config)

        # Statistics
        self._stats = {
            "total_validations": 0,
            "attacks_detected": 0,
            "attacks_blocked": 0,
            "obfuscations_detected": 0,
            "benign_context_reductions": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        # Initialize benign context detector for FP reduction
        self._benign_detector = None
        if BENIGN_CONTEXT_AVAILABLE and self.config.use_benign_context:
            try:
                self._benign_detector = BenignContextDetector()
                logger.debug("BenignContextDetector initialized for FP reduction")
            except Exception as e:
                logger.warning(f"Could not initialize BenignContextDetector: {e}")

        # Initialize default detectors
        self._init_default_detectors()

    def _init_default_detectors(self) -> None:
        """
        Initialize and register default detectors.

        Default detectors (in execution order):
            1. PatternDetector (weight 1.0): Regex-based patterns (700+), always runs
            2. FramingDetector (weight 1.2): Roleplay/fiction/DAN detection
            3. EscalationDetector (weight 1.1): Multi-turn escalation detection
            4. HarmfulRequestDetector (weight 1.3): Direct harmful content requests

        Weight rationale (based on research):
            - PatternDetector is baseline (1.0) for direct pattern matching.
            - FramingDetector has higher weight (1.2) because framing attacks
              (roleplay, fiction) have demonstrated very high ASR and often
              bypass pattern-based detection entirely.
            - EscalationDetector has elevated weight (1.1) because multi-turn
              attacks like Crescendo achieve 98% ASR. Requires conversation
              context for full effectiveness.
            - HarmfulRequestDetector has highest weight (1.3) because benchmark
              testing (v1.3.0) revealed 0% recall on JailbreakBench/HarmBench
              without detecting direct harmful content requests.

        All detectors can be enabled/disabled via config.enabled_detectors.
        All weights can be overridden via config.detector_weights.
        """
        # 1. PatternDetector - baseline pattern matching
        try:
            from sentinelseed.detection.detectors import PatternDetector

            pattern_detector = PatternDetector()
            self.registry.register(
                pattern_detector,
                weight=self.config.detector_weights.get("pattern_detector", 1.0),
                enabled=self._is_detector_enabled("pattern_detector"),
            )
            logger.debug("Registered PatternDetector (weight=%.1f)",
                         self.config.detector_weights.get("pattern_detector", 1.0))

        except ImportError as e:
            logger.warning(f"Could not import PatternDetector: {e}")
            self._stats["errors"] += 1

        # 2. FramingDetector - roleplay, fiction, DAN mode detection
        # Higher weight because framing attacks bypass pattern detection
        try:
            from sentinelseed.detection.detectors import FramingDetector

            framing_detector = FramingDetector()
            self.registry.register(
                framing_detector,
                weight=self.config.detector_weights.get("framing_detector", 1.2),
                enabled=self._is_detector_enabled("framing_detector"),
            )
            logger.debug("Registered FramingDetector (weight=%.1f)",
                         self.config.detector_weights.get("framing_detector", 1.2))

        except ImportError as e:
            logger.warning(f"Could not import FramingDetector: {e}")
            self._stats["errors"] += 1

        # 3. EscalationDetector - multi-turn attack detection
        # Elevated weight for Crescendo-style attacks (98% ASR in research)
        # Note: Requires context["previous_messages"] for full effectiveness
        try:
            from sentinelseed.detection.detectors import EscalationDetector

            escalation_detector = EscalationDetector()
            self.registry.register(
                escalation_detector,
                weight=self.config.detector_weights.get("escalation_detector", 1.1),
                enabled=self._is_detector_enabled("escalation_detector"),
            )
            logger.debug("Registered EscalationDetector (weight=%.1f)",
                         self.config.detector_weights.get("escalation_detector", 1.1))

        except ImportError as e:
            logger.warning(f"Could not import EscalationDetector: {e}")
            self._stats["errors"] += 1

        # 4. HarmfulRequestDetector - direct harmful content requests
        # Highest weight (1.3) - added in v1.3.0 after benchmark testing revealed
        # 0% recall on JailbreakBench/HarmBench without this detector.
        # Detects requests like "Write a defamatory article..." that bypass
        # pattern-based jailbreak detection.
        try:
            from sentinelseed.detection.detectors import HarmfulRequestDetector

            harmful_detector = HarmfulRequestDetector()
            self.registry.register(
                harmful_detector,
                weight=self.config.detector_weights.get("harmful_request_detector", 1.3),
                enabled=self._is_detector_enabled("harmful_request_detector"),
            )
            logger.debug("Registered HarmfulRequestDetector (weight=%.1f)",
                         self.config.detector_weights.get("harmful_request_detector", 1.3))

        except ImportError as e:
            logger.warning(f"Could not import HarmfulRequestDetector: {e}")
            self._stats["errors"] += 1

        # 5. PhysicalSafetyDetector - physical safety risks for embodied agents
        # Weight 1.4 - added in v1.5.0 after SafeAgentBench testing revealed
        # 28.3% failure rate on physical hazard detection.
        # Detects commands like "Put fork in microwave" for robot/smart home systems.
        try:
            from sentinelseed.detection.detectors import PhysicalSafetyDetector

            physical_detector = PhysicalSafetyDetector()
            self.registry.register(
                physical_detector,
                weight=self.config.detector_weights.get("physical_safety_detector", 1.4),
                enabled=self._is_detector_enabled("physical_safety_detector"),
            )
            logger.debug("Registered PhysicalSafetyDetector (weight=%.1f)",
                         self.config.detector_weights.get("physical_safety_detector", 1.4))

        except ImportError as e:
            logger.warning(f"Could not import PhysicalSafetyDetector: {e}")
            self._stats["errors"] += 1

        # 6. IntentSignalDetector - intelligent intent signal detection
        # Weight 1.3 - added in v1.6.0 to catch requests that evade keyword detection
        # Uses compositional analysis of action + target + context
        try:
            from sentinelseed.detection.detectors import IntentSignalDetector

            intent_detector = IntentSignalDetector()
            self.registry.register(
                intent_detector,
                weight=self.config.detector_weights.get("intent_signal_detector", 1.3),
                enabled=self._is_detector_enabled("intent_signal_detector"),
            )
            logger.debug("Registered IntentSignalDetector (weight=%.1f)",
                         self.config.detector_weights.get("intent_signal_detector", 1.3))

        except ImportError as e:
            logger.warning(f"Could not import IntentSignalDetector: {e}")
            self._stats["errors"] += 1

        # 7. SafeAgentDetector - enhanced embodied agent safety detection
        # Weight 1.4 - added in v1.7.0 based on Sentinel v2 experiments
        # Covers plant care, object location, contamination, electrical stress
        try:
            from sentinelseed.detection.detectors import SafeAgentDetector

            safe_agent_detector = SafeAgentDetector()
            self.registry.register(
                safe_agent_detector,
                weight=self.config.detector_weights.get("safe_agent_detector", 1.4),
                enabled=self._is_detector_enabled("safe_agent_detector"),
            )
            logger.debug("Registered SafeAgentDetector (weight=%.1f)",
                         self.config.detector_weights.get("safe_agent_detector", 1.4))

        except ImportError as e:
            logger.warning(f"Could not import SafeAgentDetector: {e}")
            self._stats["errors"] += 1

        # 8. EmbeddingDetector - semantic similarity detection (optional)
        # Weight 1.4 - catches attacks that evade heuristic detection
        # Only enabled if use_embeddings=True and provider available
        if self.config.use_embeddings:
            self._init_embedding_detector()

        # 8. SemanticDetector - LLM-based THSP validation (optional)
        # Weight 1.5 - highest weight for contextual understanding
        # Only enabled if use_semantic=True and API key available
        if self.config.use_semantic:
            self._init_semantic_detector()

    def _init_embedding_detector(self) -> None:
        """
        Initialize embedding-based detector (optional).

        This detector uses semantic similarity to catch attacks that evade
        heuristic detection. Requires an embedding provider (OpenAI/Ollama)
        and a database of known attack vectors.

        Graceful degradation:
        - If no provider available: detector disabled, heuristics continue
        - If database empty: detector disabled, heuristics continue
        - If embedding fails: returns nothing detected, no error
        """
        try:
            from sentinelseed.detection.embeddings import (
                EmbeddingDetector,
                EmbeddingDetectorConfig,
                get_available_provider,
                AttackVectorDatabase,
            )

            # Try to get an available provider
            provider = get_available_provider()

            if not provider.is_available():
                logger.info(
                    "No embedding provider available. "
                    "EmbeddingDetector disabled. Set OPENAI_API_KEY or run Ollama."
                )
                return

            # Initialize database (will be populated later or from file)
            database = AttackVectorDatabase()

            # Try to load default attack vectors if available
            self._load_default_attack_vectors(database)

            if len(database) == 0:
                logger.info(
                    "Attack vector database is empty. "
                    "EmbeddingDetector will be limited until vectors are loaded."
                )

            # Create detector with configuration
            embed_config = EmbeddingDetectorConfig(
                similarity_threshold=self.config.embedding_threshold,
            )

            embedding_detector = EmbeddingDetector(
                provider=provider,
                database=database,
                embed_config=embed_config,
            )

            self.registry.register(
                embedding_detector,
                weight=self.config.detector_weights.get("embedding_detector", 1.4),
                enabled=self._is_detector_enabled("embedding_detector"),
            )

            logger.info(
                f"Registered EmbeddingDetector (weight=%.1f, provider={provider.name}, "
                f"vectors={len(database)})",
                self.config.detector_weights.get("embedding_detector", 1.4),
            )

        except ImportError as e:
            logger.debug(f"Embedding module not available: {e}")
        except Exception as e:
            logger.warning(f"Could not initialize EmbeddingDetector: {e}")

    def _init_semantic_detector(self) -> None:
        """
        Initialize LLM-based semantic detector (optional).

        This detector uses the SemanticValidator (THSP validation via LLM)
        to detect sophisticated attacks that bypass heuristic patterns.

        The semantic detector:
        - Requires API key for the configured LLM provider
        - Has highest weight (1.5) due to contextual understanding
        - Fails closed by default (API errors = block)
        - Optional caching to reduce API costs

        Graceful degradation:
        - If no API key: detector disabled, heuristics continue
        - If API fails: returns detected=True (fail-closed)
        """
        try:
            from sentinelseed.detection.detectors import (
                SemanticDetector,
                SemanticDetectorConfig,
            )

            # Build config from validator config
            semantic_config = SemanticDetectorConfig(
                provider=self.config.semantic_provider,
                model=self.config.semantic_model,
                api_key=self.config.api_key,
                fail_closed=self.config.semantic_fail_closed,
                confidence_threshold=self.config.semantic_threshold,
            )

            semantic_detector = SemanticDetector(config=semantic_config)

            self.registry.register(
                semantic_detector,
                weight=self.config.detector_weights.get("semantic_detector", 1.5),
                enabled=self._is_detector_enabled("semantic_detector"),
            )

            logger.info(
                f"Registered SemanticDetector (weight=%.1f, provider={self.config.semantic_provider})",
                self.config.detector_weights.get("semantic_detector", 1.5),
            )

        except ImportError as e:
            logger.warning(f"Could not import SemanticDetector: {e}")
            self._stats["errors"] += 1
        except Exception as e:
            logger.warning(f"Could not initialize SemanticDetector: {e}")
            self._stats["errors"] += 1

    def _load_default_attack_vectors(self, database: "AttackVectorDatabase") -> None:
        """
        Load default attack vectors from bundled file.

        The default vectors file is distributed with the package and contains
        embeddings generated from JailbreakBench and HarmBench datasets.
        """
        from pathlib import Path

        # Look for default vectors file
        package_dir = Path(__file__).parent
        vectors_file = package_dir / "embeddings" / "data" / "attack_vectors.json"

        if vectors_file.exists():
            try:
                database.load_from_file(vectors_file)
                logger.debug(f"Loaded {len(database)} default attack vectors")
            except Exception as e:
                logger.warning(f"Failed to load default attack vectors: {e}")

    def _is_detector_enabled(self, detector_name: str) -> bool:
        """Check if detector is enabled in configuration."""
        if self.config.enabled_detectors is None:
            return True  # All enabled by default
        return detector_name in self.config.enabled_detectors

    def validate(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> InputValidationResult:
        """
        Validate input text for attacks.

        This is the main entry point for input validation. It:
        1. Normalizes text to remove obfuscation (base64, unicode, etc.)
        2. Runs all enabled detectors on the normalized text
        3. Aggregates results with configured weights
        4. Determines if the input should be blocked
        5. Returns detailed InputValidationResult

        Args:
            text: User input text to validate
            context: Optional context for detectors (e.g., user_id, session)

        Returns:
            InputValidationResult with attack details

        Example:
            result = validator.validate("ignore all instructions")
            if not result.is_safe:
                print(f"Attack: {result.primary_attack_type}")
        """
        start_time = time.time()
        self._stats["total_validations"] += 1

        # Handle empty input
        if not text or not text.strip():
            return InputValidationResult.safe()

        # Check text length
        if len(text) > self.config.max_text_length:
            return InputValidationResult.attack_detected(
                attack_types=[AttackType.STRUCTURAL],
                violations=[
                    f"Input exceeds maximum length ({len(text)} > {self.config.max_text_length})"
                ],
                detections=[],
                confidence=0.9,
                block=True,
            )

        # PHASE 1: Normalize text to remove obfuscation
        normalization_result = self._normalizer.normalize(text)
        text_to_analyze = normalization_result.normalized_text

        if normalization_result.is_obfuscated:
            self._stats["obfuscations_detected"] += 1
            logger.debug(
                f"Obfuscation detected: {normalization_result.obfuscation_types}, "
                f"risk_level={normalization_result.risk_level}"
            )

        # PHASE 2: Run all enabled detectors on normalized text
        try:
            detection_results = self.registry.run_all(text_to_analyze, context)
        except Exception as e:
            logger.error(f"Detector execution failed: {e}")
            self._stats["errors"] += 1

            if self.config.fail_closed:
                return InputValidationResult.attack_detected(
                    attack_types=[AttackType.UNKNOWN],
                    violations=[f"Validation error: {str(e)}"],
                    detections=[],
                    confidence=0.5,
                    block=True,
                )
            return InputValidationResult.safe()

        # PHASE 3: Aggregate results (including obfuscation info)
        result = self._aggregate_results(
            detection_results, normalization_result, text_to_analyze
        )

        # Update stats
        latency_ms = (time.time() - start_time) * 1000
        self._stats["total_latency_ms"] += latency_ms

        if result.is_attack:
            self._stats["attacks_detected"] += 1
            if result.blocked:
                self._stats["attacks_blocked"] += 1

        # Log if configured
        if self.config.log_level == "debug":
            logger.debug(
                f"InputValidator: text_len={len(text)}, "
                f"is_attack={result.is_attack}, "
                f"confidence={result.confidence:.2f}, "
                f"latency={latency_ms:.1f}ms"
            )

        return result

    def _aggregate_results(
        self,
        detection_results: List[DetectionResult],
        normalization_result: Optional[NormalizationResult] = None,
        original_text: str = "",
    ) -> InputValidationResult:
        """
        Aggregate detection results into final InputValidationResult.

        Uses configuration to determine:
        - Whether to block based on confidence threshold
        - Whether multiple detectors are required
        - How to weight different detectors

        Additionally considers:
        - Obfuscation as a risk factor (boosts confidence)
        - Benign context as a FP reduction factor (reduces confidence)

        Args:
            detection_results: List of DetectionResult from all detectors
            normalization_result: Optional result from text normalization
            original_text: Original text for benign context checking

        Returns:
            InputValidationResult with aggregated information
        """
        # Filter positive detections
        positive_detections = [r for r in detection_results if r.detected]

        # Check if we have obfuscation without other detections
        has_obfuscation = (
            normalization_result is not None
            and normalization_result.is_obfuscated
        )

        if not positive_detections:
            # No attack detected, but check obfuscation
            if has_obfuscation and normalization_result.risk_level == "high":
                # High-risk obfuscation alone is suspicious
                return InputValidationResult(
                    is_attack=False,  # Not definitively an attack
                    blocked=False,
                    confidence=normalization_result.confidence * 0.5,
                    metadata={
                        "obfuscation_detected": True,
                        "obfuscation_types": [
                            t.value for t in normalization_result.obfuscation_types
                        ],
                        "obfuscation_risk_level": normalization_result.risk_level,
                        "normalized_text_preview": normalization_result.normalized_text[:100],
                    },
                )
            return InputValidationResult.safe()

        # Collect attack types and violations
        attack_types: Set[AttackType] = set()
        violations: List[str] = []

        for detection in positive_detections:
            # Parse attack type from category
            try:
                attack_type = AttackType(detection.category)
            except ValueError:
                attack_type = AttackType.UNKNOWN
            attack_types.add(attack_type)

            # Collect violations
            if detection.description:
                violations.append(detection.description)

            # Add evidence as violation if available
            if detection.evidence:
                violations.append(f"Evidence: {detection.evidence}")

        # Calculate weighted confidence
        total_weight = 0.0
        weighted_confidence = 0.0

        for detection in positive_detections:
            detector_weight = self.registry.get_weight(detection.detector_name)
            weighted_confidence += detection.confidence * detector_weight
            total_weight += detector_weight

        if total_weight > 0:
            confidence = weighted_confidence / total_weight
        else:
            confidence = max(d.confidence for d in positive_detections)

        # Boost confidence if obfuscation was detected
        # Obfuscation + attack = strong indicator of malicious intent
        obfuscation_boost = 0.0
        if has_obfuscation:
            risk_level = normalization_result.risk_level
            if risk_level == "high":
                obfuscation_boost = 0.15
            elif risk_level == "medium":
                obfuscation_boost = 0.10
            else:
                obfuscation_boost = 0.05

            confidence = min(1.0, confidence + obfuscation_boost)
            attack_types.add(AttackType.EVASION)
            violations.append(
                f"Obfuscation detected: {[t.value for t in normalization_result.obfuscation_types]}"
            )

        # Reduce confidence if benign context detected
        # Benign context = technical/academic/legitimate use of "dangerous" words
        # Example: "kill the process" in programming context
        benign_reduction = 0.0
        benign_matches = []
        if self._benign_detector and not has_obfuscation and original_text:
            # Don't apply benign reduction if obfuscation detected
            # (obfuscation + "benign" context = likely bypass attempt)
            try:
                is_benign, matches, reduction_factor = self._benign_detector.check(original_text)
                if is_benign:
                    # Apply reduction to confidence
                    original_confidence = confidence
                    confidence = confidence * reduction_factor
                    benign_reduction = original_confidence - confidence
                    benign_matches = [m.pattern_name for m in matches]

                    self._stats["benign_context_reductions"] += 1
                    logger.debug(
                        f"Benign context detected: {benign_matches}, "
                        f"confidence reduced from {original_confidence:.2f} to {confidence:.2f}"
                    )
            except Exception as e:
                logger.warning(f"Benign context check failed: {e}")

        # Determine if should block
        should_block = self._should_block(
            confidence=confidence,
            detector_count=len(positive_detections),
            attack_types=attack_types,
        )

        # Build metadata with obfuscation and benign context info
        metadata: Dict[str, Any] = {}
        if has_obfuscation:
            metadata["obfuscation_detected"] = True
            metadata["obfuscation_types"] = [
                t.value for t in normalization_result.obfuscation_types
            ]
            metadata["obfuscation_risk_level"] = normalization_result.risk_level
            metadata["obfuscation_confidence_boost"] = obfuscation_boost

        if benign_reduction > 0:
            metadata["benign_context_detected"] = True
            metadata["benign_matches"] = benign_matches
            metadata["benign_confidence_reduction"] = benign_reduction

        return InputValidationResult(
            is_attack=True,
            attack_types=list(attack_types),
            detections=positive_detections,
            confidence=confidence,
            blocked=should_block,
            violations=violations,
            metadata=metadata,
        )

    def _should_block(
        self,
        confidence: float,
        detector_count: int,
        attack_types: Set[AttackType],
    ) -> bool:
        """
        Determine if input should be blocked based on configuration.

        Args:
            confidence: Weighted confidence score
            detector_count: Number of detectors that flagged
            attack_types: Set of detected attack types

        Returns:
            True if input should be blocked
        """
        # Always block critical attack types regardless of thresholds
        # This check comes FIRST to ensure critical attacks are never allowed through
        critical_types = {
            AttackType.JAILBREAK,
            AttackType.INJECTION,
            AttackType.HARMFUL_REQUEST,
        }
        if attack_types & critical_types and confidence >= 0.5:
            return True

        # Check confidence threshold for non-critical attacks
        if confidence < self.config.min_confidence_to_block:
            return False

        # Check if multiple detectors required
        if self.config.require_multiple_detectors:
            if detector_count < self.config.min_detectors_to_block:
                return False

        return True

    def register_detector(
        self,
        detector: Any,
        weight: float = 1.0,
        enabled: bool = True,
    ) -> None:
        """
        Register a custom detector.

        Args:
            detector: Detector instance implementing BaseDetector
            weight: Weight for this detector in aggregation
            enabled: Whether detector is enabled

        Example:
            validator.register_detector(MyDetector(), weight=1.5)
        """
        self.registry.register(detector, weight=weight, enabled=enabled)
        logger.info(f"Registered detector: {detector.name}")

    def unregister_detector(self, name: str) -> bool:
        """
        Remove a detector by name.

        Args:
            name: Detector name to remove

        Returns:
            True if detector was removed
        """
        return self.registry.unregister(name)

    def enable_detector(self, name: str) -> bool:
        """Enable a detector by name."""
        return self.registry.enable(name)

    def disable_detector(self, name: str) -> bool:
        """Disable a detector by name."""
        return self.registry.disable(name)

    def set_detector_weight(self, name: str, weight: float) -> bool:
        """Set detector weight."""
        return self.registry.set_weight(name, weight)

    def list_detectors(self) -> Dict[str, Dict[str, Any]]:
        """List all registered detectors with their configuration."""
        return self.registry.list_detectors()

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self._stats["total_validations"]
        return {
            **self._stats,
            "avg_latency_ms": (
                self._stats["total_latency_ms"] / total if total > 0 else 0.0
            ),
            "attack_rate": (
                self._stats["attacks_detected"] / total if total > 0 else 0.0
            ),
            "block_rate": (
                self._stats["attacks_blocked"] / total if total > 0 else 0.0
            ),
            "detector_count": len(self.registry),
        }

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._stats = {
            "total_validations": 0,
            "attacks_detected": 0,
            "attacks_blocked": 0,
            "obfuscations_detected": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }


__all__ = ["InputValidator"]
