"""
Embedding-based Attack Detector.

Uses semantic similarity to detect attacks by comparing input embeddings
against a database of known attack patterns. This detector catches attacks
that evade keyword-based detection through paraphrasing or synonyms.

How It Works:
    1. Convert input text to embedding using configured provider
    2. Search attack vector database for similar embeddings
    3. If similarity > threshold, flag as attack
    4. Return category of most similar known attack

Advantages over Heuristic Detection:
    - Catches paraphrased attacks
    - Works across languages (with multilingual models)
    - Robust to synonym substitution
    - Learns from new attack examples

Usage:
    from sentinelseed.detection.embeddings import (
        EmbeddingDetector,
        OpenAIEmbeddings,
        AttackVectorDatabase,
    )

    provider = OpenAIEmbeddings(api_key="sk-...")
    database = AttackVectorDatabase()
    database.load_from_file("attack_vectors.json")

    detector = EmbeddingDetector(provider=provider, database=database)
    result = detector.detect("ignore all previous instructions")

    if result.detected:
        print(f"Attack detected: {result.category}")

References:
    - Semantic similarity for safety: Anthropic Constitutional AI
    - Embedding-based moderation: OpenAI Moderation API
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from sentinelseed.detection.detectors.base import BaseDetector, DetectorConfig
from sentinelseed.detection.types import AttackType, DetectionResult

from .provider import EmbeddingProvider, NullEmbeddingProvider
from .vectors import AttackVectorDatabase, SimilarityMatch

logger = logging.getLogger("sentinelseed.detection.embeddings.detector")


@dataclass
class EmbeddingDetectorConfig:
    """
    Configuration for EmbeddingDetector.

    Attributes:
        similarity_threshold: Minimum cosine similarity to flag as attack (0.0-1.0)
            Calibrated with OpenAI text-embedding-3-small via leave-one-out CV:
            - Threshold 0.50: 93.6% recall, 3% FPR (highest Youden's J)
            - Threshold 0.55: 80.6% recall, 0% FPR (best precision/recall balance)
            - Threshold 0.60: 66.2% recall, 0% FPR
            Default 0.55 for zero false positives with good recall.
        top_k: Maximum number of similar vectors to consider
        min_confidence: Minimum confidence to report detection
        boost_per_match: Confidence boost for each additional match
        max_confidence: Maximum confidence cap

    Calibration Details:
        - Dataset: 500 attack vectors (JailbreakBench + HarmBench)
        - Safe prompts: 100 benign queries across 10 categories
        - Methodology: Leave-one-out cross-validation
        - See: scripts/benchmark_embeddings.py for reproduction
    """

    similarity_threshold: float = 0.55
    top_k: int = 5
    min_confidence: float = 0.55
    boost_per_match: float = 0.05
    max_confidence: float = 0.95


class EmbeddingDetector(BaseDetector):
    """
    Detector that uses embedding similarity to identify attacks.

    This detector complements heuristic detection by catching semantically
    similar attacks that don't match exact patterns. It requires:
    - An embedding provider (OpenAI, Ollama, etc.)
    - A database of known attack embeddings

    Detection Strategy:
        1. Generate embedding for input text
        2. Search database for similar attack vectors
        3. If matches found above threshold:
           - Flag as attack
           - Use category from best match
           - Confidence based on similarity score

    Graceful Degradation:
        - If provider unavailable: returns nothing detected
        - If database empty: returns nothing detected
        - If embedding fails: returns nothing detected

    Example:
        detector = EmbeddingDetector(
            provider=OpenAIEmbeddings(api_key="sk-..."),
            database=loaded_database,
        )

        result = detector.detect("how to make a bomb")
        if result.detected:
            print(f"Similar to known attack: {result.metadata['matches']}")

    Attributes:
        provider: Embedding provider for generating vectors
        database: Database of known attack vectors
        embed_config: Detection configuration
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        provider: Optional[EmbeddingProvider] = None,
        database: Optional[AttackVectorDatabase] = None,
        embed_config: Optional[EmbeddingDetectorConfig] = None,
        config: Optional[DetectorConfig] = None,
    ):
        """
        Initialize embedding detector.

        Args:
            provider: Embedding provider. If None, detector is disabled.
            database: Attack vector database. If None, detector is disabled.
            embed_config: Detection configuration.
            config: Base detector configuration.
        """
        super().__init__(config)
        self._provider = provider or NullEmbeddingProvider()
        self._database = database or AttackVectorDatabase()
        self._embed_config = embed_config or EmbeddingDetectorConfig()

    @property
    def name(self) -> str:
        return "embedding_detector"

    @property
    def version(self) -> str:
        return self.VERSION

    @property
    def provider(self) -> EmbeddingProvider:
        """Get the embedding provider."""
        return self._provider

    @property
    def database(self) -> AttackVectorDatabase:
        """Get the attack vector database."""
        return self._database

    def is_ready(self) -> bool:
        """
        Check if detector is ready for use.

        Returns:
            True if provider is available and database has vectors
        """
        return (
            self._provider.is_available() and
            len(self._database) > 0
        )

    def detect(
        self,
        text: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Detect attacks using embedding similarity.

        Args:
            text: Input text to analyze
            context: Optional context (not used by this detector)

        Returns:
            DetectionResult with detection status
        """
        # Early exit if not ready
        if not text or not text.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        if not self._provider.is_available():
            logger.debug("Embedding provider not available, skipping detection")
            return DetectionResult.nothing_detected(self.name, self.version)

        if len(self._database) == 0:
            logger.debug("Attack vector database is empty, skipping detection")
            return DetectionResult.nothing_detected(self.name, self.version)

        # Generate embedding for input
        try:
            result = self._provider.get_embedding_cached(text)
            query_embedding = result.embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            return DetectionResult.nothing_detected(self.name, self.version)

        # Search for similar attacks
        matches = self._database.search_similar(
            query_embedding=query_embedding,
            threshold=self._embed_config.similarity_threshold,
            top_k=self._embed_config.top_k,
        )

        if not matches:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Calculate confidence based on matches
        best_match = matches[0]
        confidence = self._calculate_confidence(matches)

        if confidence < self._embed_config.min_confidence:
            return DetectionResult.nothing_detected(self.name, self.version)

        # Determine attack type from best match
        attack_type = self._map_category_to_attack_type(best_match.category)

        # Build description
        description = (
            f"Semantic similarity to known attack: {best_match.category}"
        )
        if best_match.subcategory:
            description += f" ({best_match.subcategory})"

        # Build evidence
        evidence_parts = []
        for match in matches[:3]:
            if match.vector.example:
                # Truncate long examples
                example = match.vector.example[:100]
                if len(match.vector.example) > 100:
                    example += "..."
                evidence_parts.append(
                    f"{match.category}: {match.score:.2f} - \"{example}\""
                )
            else:
                evidence_parts.append(f"{match.category}: {match.score:.2f}")

        return DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            category=attack_type.value,
            confidence=confidence,
            description=description,
            evidence="; ".join(evidence_parts) if evidence_parts else None,
            metadata={
                "best_match_score": best_match.score,
                "best_match_category": best_match.category,
                "best_match_subcategory": best_match.subcategory,
                "match_count": len(matches),
                "provider": self._provider.name,
                "model": self._provider.model,
                "cached": result.cached,
            },
        )

    def _calculate_confidence(self, matches: List[SimilarityMatch]) -> float:
        """
        Calculate detection confidence from similarity matches.

        Uses best match score as base, with boost for additional matches.
        """
        if not matches:
            return 0.0

        # Base confidence from best match similarity
        confidence = matches[0].score

        # Boost for additional matches
        for match in matches[1:]:
            confidence += self._embed_config.boost_per_match

        # Cap at maximum
        return min(confidence, self._embed_config.max_confidence)

    def _map_category_to_attack_type(self, category: str) -> AttackType:
        """Map database category to AttackType enum."""
        category_lower = category.lower()

        # Direct mappings
        mappings = {
            "jailbreak": AttackType.JAILBREAK,
            "injection": AttackType.INJECTION,
            "manipulation": AttackType.MANIPULATION,
            "harmful_request": AttackType.HARMFUL_REQUEST,
            "evasion": AttackType.EVASION,
            "structural": AttackType.STRUCTURAL,
        }

        for key, attack_type in mappings.items():
            if key in category_lower:
                return attack_type

        # Default for unknown categories
        return AttackType.UNKNOWN

    def initialize(self) -> None:
        """Initialize detector and provider."""
        if self._provider.is_available():
            self._provider.initialize()
        super().initialize()

    def shutdown(self) -> None:
        """Shutdown detector and provider."""
        self._provider.shutdown()
        super().shutdown()


__all__ = ["EmbeddingDetector", "EmbeddingDetectorConfig"]
