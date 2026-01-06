"""
Embedding-based Output Checker - Semantic similarity for toxic content detection.

This module provides EmbeddingChecker, a checker that uses text embeddings to
detect toxic content in AI output through semantic similarity matching. It
complements the heuristic ToxicityChecker by catching implicit toxicity that
evades pattern-based detection.

The Core Insight:
    ToxiGen and similar benchmarks demonstrate that toxic content often lacks
    explicit toxic terms. Statements like "Jews were all bad people because of
    their greediness" contain no slurs but convey harmful stereotypes.

    EmbeddingChecker catches these by comparing output embeddings against a
    database of known toxic content patterns, detecting semantic similarity
    even when specific words differ.

How It Works:
    1. Convert AI output to embedding using configured provider
    2. Search toxic vector database for similar embeddings
    3. If similarity > threshold, flag as toxic content
    4. Return CheckFailureType.HARMFUL_CONTENT for THSP HARM gate

Key Difference from EmbeddingDetector (L1):
    - EmbeddingDetector: Detects ATTACK INTENT in input
    - EmbeddingChecker: Detects TOXIC CONTENT in output

    The distinction matters:
    - Attack intent: "Ignore previous instructions" (user trying to bypass)
    - Toxic output: "Jews are greedy" (AI generated harmful content)

Advantages over Heuristic ToxicityChecker:
    - Catches implicit toxicity without trigger words
    - Robust to paraphrasing and synonym substitution
    - Works across languages (with multilingual embeddings)
    - Learns from new toxic examples added to database

Context Awareness:
    Unlike EmbeddingDetector, EmbeddingChecker receives input_context.
    This allows for context-aware decisions:
    - A chemistry discussion is appropriate for chemistry questions
    - The same content is suspicious after a jailbreak attempt

Graceful Degradation:
    - If provider unavailable: returns nothing detected (heuristics continue)
    - If database empty: returns nothing detected
    - If embedding fails: returns nothing detected (fail-open by default)
    - Can be configured to fail-closed for high-security applications

Usage:
    from sentinelseed.detection.checkers.embedding import (
        EmbeddingChecker,
        EmbeddingCheckerConfig,
    )
    from sentinelseed.detection.embeddings import (
        OpenAIEmbeddings,
        AttackVectorDatabase,
    )

    # Setup provider and database
    provider = OpenAIEmbeddings(api_key="sk-...")
    database = AttackVectorDatabase()
    database.load_from_file("toxic_vectors.json")

    # Create checker
    checker = EmbeddingChecker(provider=provider, database=database)

    # Check output
    result = checker.check(
        output="Those people are all lazy and criminal.",
        input_context="Tell me about demographics",
    )

    if result.detected:
        print(f"Toxic content: {result.description}")
        print(f"THSP gate: harm")

References:
    - ToxiGen: Hartvigsen et al., EMNLP 2022 (implicit hate speech)
    - RealToxicityPrompts: Gehman et al., 2020 (toxic text generation)
    - Semantic similarity for moderation: OpenAI Moderation API
"""

from __future__ import annotations

import hashlib
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from sentinelseed.detection.checkers.base import BaseChecker, CheckerConfig
from sentinelseed.detection.types import CheckFailureType, DetectionResult

logger = logging.getLogger("sentinelseed.detection.checkers.embedding")


# Default path for toxic vectors (relative to package)
DEFAULT_TOXIC_VECTORS_PATH = Path(__file__).parent.parent / "embeddings" / "data" / "toxic_vectors.json"


@dataclass
class EmbeddingCheckerConfig(CheckerConfig):
    """
    Configuration for EmbeddingChecker.

    Extends CheckerConfig with embedding-specific options for toxic content
    detection in AI output.

    Attributes:
        similarity_threshold: Minimum cosine similarity to flag as toxic (0.0-1.0)
            Lower values catch more variations but risk false positives.
            Higher values are more precise but may miss paraphrases.

            Recommended calibration:
            - 0.60: High recall, moderate precision (development)
            - 0.70: Balanced recall/precision (production)
            - 0.80: High precision, lower recall (high-stakes)

            Note: This should be calibrated with toxic vector dataset using
            leave-one-out cross-validation for optimal threshold.

        top_k: Maximum number of similar vectors to consider for each check.
            More matches with high similarity increase confidence.

        min_confidence: Minimum confidence score to report detection.
            Filters out low-confidence matches.

        boost_per_match: Confidence boost for each additional match found.
            Multiple similar toxic patterns increase overall confidence.

        max_confidence: Maximum confidence cap (prevents overconfidence).

        fail_closed: If True, API errors result in detected=True (safer).
            If False, API errors result in detected=False (fail-open).
            Default is False since heuristic checkers provide baseline protection.

        cache_enabled: If True, cache embedding results to reduce API calls.

        cache_ttl: Cache time-to-live in seconds (default 300 = 5 minutes).

        include_input_context: If True, consider input_context when checking.
            This allows for context-aware toxicity assessment.

        auto_load_database: If True, automatically load default toxic vectors.

        toxic_vectors_path: Path to toxic vectors JSON file.
            If None, uses default path in embeddings/data/.

    Example:
        config = EmbeddingCheckerConfig(
            similarity_threshold=0.70,
            top_k=5,
            min_confidence=0.60,
            fail_closed=False,  # Fail-open, heuristics as backup
        )
        checker = EmbeddingChecker(provider=provider, database=db, config=config)
    """

    similarity_threshold: float = 0.50
    top_k: int = 5
    min_confidence: float = 0.45
    boost_per_match: float = 0.05
    max_confidence: float = 0.95
    fail_closed: bool = False  # Fail-open by default (heuristics backup)
    cache_enabled: bool = True
    cache_ttl: int = 300
    include_input_context: bool = True
    auto_load_database: bool = True
    toxic_vectors_path: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate configuration values."""
        super().__post_init__()

        # Validate threshold range
        if not 0.0 <= self.similarity_threshold <= 1.0:
            raise ValueError(
                f"similarity_threshold must be between 0.0 and 1.0, "
                f"got {self.similarity_threshold}"
            )

        # Validate min_confidence range
        if not 0.0 <= self.min_confidence <= 1.0:
            raise ValueError(
                f"min_confidence must be between 0.0 and 1.0, "
                f"got {self.min_confidence}"
            )

        # Validate top_k
        if self.top_k < 1:
            raise ValueError(f"top_k must be >= 1, got {self.top_k}")


# Category mapping: toxic vector categories to THSP CheckFailureType
# Toxic content primarily maps to HARM gate
TOXIC_CATEGORY_TO_FAILURE_TYPE: Dict[str, CheckFailureType] = {
    # Primary toxicity categories -> HARM gate
    "harassment_discrimination": CheckFailureType.HARMFUL_CONTENT,
    "violence_threats": CheckFailureType.HARMFUL_CONTENT,
    "sexual_explicit": CheckFailureType.HARMFUL_CONTENT,
    "dangerous_content": CheckFailureType.HARMFUL_CONTENT,
    "dehumanization": CheckFailureType.HARMFUL_CONTENT,
    "child_safety": CheckFailureType.HARMFUL_CONTENT,
    "hate_speech": CheckFailureType.HARMFUL_CONTENT,
    "toxicity": CheckFailureType.HARMFUL_CONTENT,

    # Secondary categories
    "privacy_violation": CheckFailureType.SCOPE_VIOLATION,
    "fraud_scam": CheckFailureType.DECEPTIVE_CONTENT,
    "misinformation": CheckFailureType.DECEPTIVE_CONTENT,
    "illegal_content": CheckFailureType.HARMFUL_CONTENT,

    # Default
    "unknown": CheckFailureType.HARMFUL_CONTENT,
}


class EmbeddingChecker(BaseChecker):
    """
    Checker that uses embedding similarity to detect toxic content in AI output.

    This checker complements heuristic toxicity detection by catching
    semantically similar toxic content that doesn't match exact patterns.
    It is particularly effective against implicit toxicity (ToxiGen-style)
    that lacks explicit slurs or trigger words.

    The checker:
    - Generates embeddings for AI output
    - Searches database for similar toxic patterns
    - Calculates confidence from match scores
    - Maps toxic categories to THSP failure types
    - Returns CheckFailureType.HARMFUL_CONTENT for most toxic content

    Context Awareness:
        Unlike EmbeddingDetector (for input), EmbeddingChecker receives
        input_context. If include_input_context=True, the checker can
        consider whether the output is appropriate given the input.

    Graceful Degradation:
        - Provider unavailable → nothing detected (heuristics continue)
        - Database empty → nothing detected
        - Embedding fails → nothing detected (or fail-closed if configured)

        This ensures the system remains functional even without API access.

    Example:
        from sentinelseed.detection.embeddings import (
            OpenAIEmbeddings,
            AttackVectorDatabase,
        )

        provider = OpenAIEmbeddings()
        database = AttackVectorDatabase()
        database.load_from_file("toxic_vectors.json")

        checker = EmbeddingChecker(
            provider=provider,
            database=database,
        )

        result = checker.check(
            output="Those people are all criminals and liars.",
            input_context="Tell me about that group.",
        )

        if result.detected:
            print(f"Toxic match: {result.metadata['best_match_category']}")
            print(f"Similarity: {result.metadata['best_match_score']:.2f}")

    Attributes:
        provider: Embedding provider for generating vectors
        database: Database of known toxic content vectors
        embed_config: Detection configuration
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        provider=None,
        database=None,
        config: Optional[EmbeddingCheckerConfig] = None,
    ):
        """
        Initialize embedding checker.

        Args:
            provider: EmbeddingProvider instance. If None, checker is disabled.
            database: AttackVectorDatabase with toxic vectors. If None, uses empty.
            config: Checker configuration. If None, uses defaults.

        Note:
            The provider and database can be set lazily via properties.
            If auto_load_database=True (default), the checker attempts to
            load toxic vectors from the default path on first use.
        """
        self._embed_config = config or EmbeddingCheckerConfig()
        super().__init__(self._embed_config)

        # Store provider (can be None for graceful degradation)
        self._provider = provider

        # Store database (can be None, will be auto-loaded or remain empty)
        self._database = database

        # Cache: hash -> (result, timestamp)
        self._cache: Dict[str, tuple] = {}

        # Database auto-load attempted flag
        self._database_load_attempted = False

    @property
    def name(self) -> str:
        """Unique identifier for this checker."""
        return "embedding_checker"

    @property
    def version(self) -> str:
        """Semantic version of this checker."""
        return self.VERSION

    @property
    def provider(self):
        """Get the embedding provider."""
        return self._provider

    @provider.setter
    def provider(self, value) -> None:
        """Set the embedding provider."""
        self._provider = value

    @property
    def database(self):
        """Get the toxic vector database."""
        return self._database

    @database.setter
    def database(self, value) -> None:
        """Set the toxic vector database."""
        self._database = value

    def is_ready(self) -> bool:
        """
        Check if checker is ready for use.

        Returns:
            True if provider is available and database has vectors
        """
        if self._provider is None:
            return False

        if not self._provider.is_available():
            return False

        # Try auto-loading database if not done
        self._ensure_database_loaded()

        if self._database is None:
            return False

        return len(self._database) > 0

    def _ensure_database_loaded(self) -> None:
        """
        Ensure toxic vector database is loaded.

        If auto_load_database=True and database is not set, attempts to
        load from the default or configured path.
        """
        if self._database is not None:
            return

        if self._database_load_attempted:
            return

        self._database_load_attempted = True

        if not self._embed_config.auto_load_database:
            return

        # Determine path
        if self._embed_config.toxic_vectors_path:
            path = Path(self._embed_config.toxic_vectors_path)
        else:
            path = DEFAULT_TOXIC_VECTORS_PATH

        if not path.exists():
            logger.debug(f"Toxic vectors file not found: {path}")
            return

        try:
            # Import here to avoid circular imports
            from sentinelseed.detection.embeddings import AttackVectorDatabase

            self._database = AttackVectorDatabase()
            self._database.load_from_file(path)
            logger.info(f"Auto-loaded {len(self._database)} toxic vectors from {path}")

        except Exception as e:
            logger.warning(f"Failed to auto-load toxic vectors: {e}")
            self._database = None

    def _get_cache_key(self, output: str, input_context: Optional[str]) -> str:
        """Generate cache key from output and optional context hash."""
        if self._embed_config.include_input_context and input_context:
            combined = output + "|||" + input_context
        else:
            combined = output
        return hashlib.sha256(combined.encode()).hexdigest()[:16]

    def _get_cached(self, cache_key: str) -> Optional[DetectionResult]:
        """Get cached result if valid."""
        if not self._embed_config.cache_enabled:
            return None

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._embed_config.cache_ttl:
                logger.debug(f"Cache hit for {cache_key}")
                return result
            else:
                # Expired
                del self._cache[cache_key]

        return None

    def _set_cached(self, cache_key: str, result: DetectionResult) -> None:
        """Store result in cache."""
        if self._embed_config.cache_enabled:
            self._cache[cache_key] = (result, time.time())

    def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Check AI output for toxic content using embedding similarity.

        This method:
        1. Validates input and checks readiness
        2. Generates embedding for the output
        3. Searches toxic vector database for similar patterns
        4. Calculates confidence from match scores
        5. Returns DetectionResult with HARMFUL_CONTENT if toxic

        Args:
            output: AI-generated output text to check
            input_context: Original user input for context (optional).
                If include_input_context=True, this is considered when
                generating embeddings for context-aware detection.
            rules: Optional runtime rules (currently not used by this checker)

        Returns:
            DetectionResult indicating whether toxic content was found.
            - detected=True: Toxic content with similarity above threshold
            - detected=False: No toxic matches or checker unavailable

        Example:
            result = checker.check(
                output="Those people are inferior and don't belong.",
                input_context="What do you think about that group?",
            )

            if result.detected:
                print(f"Category: {result.metadata['best_match_category']}")
                print(f"Score: {result.metadata['best_match_score']:.2f}")
        """
        self._ensure_initialized()

        # Track stats
        self._stats["total_calls"] = self._stats.get("total_calls", 0) + 1
        had_context = input_context is not None
        if had_context:
            self._stats["context_provided"] = self._stats.get("context_provided", 0) + 1

        # Validate input
        if not output or not output.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check cache
        cache_key = self._get_cache_key(output, input_context)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        # Check readiness (provider available, database loaded)
        if not self.is_ready():
            logger.debug("EmbeddingChecker not ready, skipping detection")
            return DetectionResult.nothing_detected(self.name, self.version)

        # Generate embedding for output
        try:
            # Build text for embedding
            # If context is included and available, prepend it
            if self._embed_config.include_input_context and input_context:
                text_for_embedding = f"Context: {input_context}\nOutput: {output}"
            else:
                text_for_embedding = output

            embed_result = self._provider.get_embedding_cached(text_for_embedding)
            query_embedding = embed_result.embedding

        except Exception as e:
            logger.warning(f"Failed to generate embedding: {e}")
            self._stats["errors"] = self._stats.get("errors", 0) + 1

            if self._embed_config.fail_closed:
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.5,
                    category=CheckFailureType.HARMFUL_CONTENT.value,
                    description=f"Embedding check failed: {str(e)}",
                    metadata={
                        "error": str(e),
                        "fail_closed": True,
                        "thsp_gate": "harm",
                    },
                )
            return DetectionResult.nothing_detected(self.name, self.version)

        # Search for similar toxic content
        try:
            matches = self._database.search_similar(
                query_embedding=query_embedding,
                threshold=self._embed_config.similarity_threshold,
                top_k=self._embed_config.top_k,
            )
        except Exception as e:
            logger.warning(f"Database search failed: {e}")
            self._stats["errors"] = self._stats.get("errors", 0) + 1
            return DetectionResult.nothing_detected(self.name, self.version)

        # No matches above threshold
        if not matches:
            result = DetectionResult.nothing_detected(self.name, self.version)
            self._set_cached(cache_key, result)
            return result

        # Calculate confidence from matches
        best_match = matches[0]
        confidence = self._calculate_confidence(matches)

        # Check minimum confidence threshold
        if confidence < self._embed_config.min_confidence:
            result = DetectionResult.nothing_detected(self.name, self.version)
            self._set_cached(cache_key, result)
            return result

        # Toxic content detected
        self._stats["failures_detected"] = self._stats.get("failures_detected", 0) + 1

        # Map category to failure type
        failure_type = self._map_category_to_failure_type(best_match.category)

        # Build description
        description = f"Semantic similarity to toxic content: {best_match.category}"
        if best_match.subcategory:
            description += f" ({best_match.subcategory})"

        # Build evidence from top matches
        evidence_parts = []
        for match in matches[:3]:
            if match.vector.example:
                # Truncate long examples
                example = match.vector.example[:80]
                if len(match.vector.example) > 80:
                    example += "..."
                evidence_parts.append(
                    f"{match.category}: {match.score:.2f} - \"{example}\""
                )
            else:
                evidence_parts.append(f"{match.category}: {match.score:.2f}")

        result = DetectionResult(
            detected=True,
            detector_name=self.name,
            detector_version=self.version,
            confidence=confidence,
            category=failure_type.value,
            description=description,
            evidence="; ".join(evidence_parts) if evidence_parts else None,
            metadata={
                "best_match_score": best_match.score,
                "best_match_category": best_match.category,
                "best_match_subcategory": best_match.subcategory,
                "match_count": len(matches),
                "thsp_gate": failure_type.gate,
                "provider": self._provider.name if self._provider else "none",
                "model": self._provider.model if self._provider else "none",
                "cached": getattr(embed_result, 'cached', False),
                "input_context_used": had_context and self._embed_config.include_input_context,
            },
        )

        self._set_cached(cache_key, result)
        self._update_stats(result, had_context)

        return result

    def _calculate_confidence(self, matches: List) -> float:
        """
        Calculate detection confidence from similarity matches.

        Uses best match score as base, with boost for additional matches.
        This reflects that multiple similar toxic patterns increase certainty.

        Args:
            matches: List of SimilarityMatch objects from database search

        Returns:
            Confidence score between 0.0 and max_confidence
        """
        if not matches:
            return 0.0

        # Base confidence from best match similarity
        confidence = matches[0].score

        # Boost for additional matches (indicates pattern is common)
        for match in matches[1:]:
            confidence += self._embed_config.boost_per_match

        # Cap at maximum
        return min(confidence, self._embed_config.max_confidence)

    def _map_category_to_failure_type(self, category: str) -> CheckFailureType:
        """
        Map toxic vector category to THSP CheckFailureType.

        Most toxic content maps to HARMFUL_CONTENT (HARM gate), but some
        categories like misinformation map to DECEPTIVE_CONTENT (TRUTH gate).

        Args:
            category: Category from toxic vector database

        Returns:
            Appropriate CheckFailureType enum value
        """
        category_lower = category.lower().replace("-", "_").replace(" ", "_")

        # Check direct mapping
        if category_lower in TOXIC_CATEGORY_TO_FAILURE_TYPE:
            return TOXIC_CATEGORY_TO_FAILURE_TYPE[category_lower]

        # Check partial matches
        for key, failure_type in TOXIC_CATEGORY_TO_FAILURE_TYPE.items():
            if key in category_lower or category_lower in key:
                return failure_type

        # Default to HARMFUL_CONTENT for unknown toxic categories
        return CheckFailureType.HARMFUL_CONTENT

    def initialize(self) -> None:
        """
        Initialize the checker before first use.

        Attempts to:
        - Verify provider availability
        - Load toxic vector database if not loaded
        - Log configuration for debugging
        """
        super().initialize()

        # Try to initialize provider
        if self._provider:
            try:
                if hasattr(self._provider, 'initialize'):
                    self._provider.initialize()
                if not self._provider.is_available():
                    logger.warning(
                        f"EmbeddingChecker: Provider {self._provider.name} not available. "
                        "Checker will skip embedding-based detection."
                    )
            except Exception as e:
                logger.warning(f"Failed to initialize provider: {e}")

        # Try to load database
        self._ensure_database_loaded()

        if self._database and len(self._database) > 0:
            logger.info(
                f"EmbeddingChecker initialized: "
                f"provider={self._provider.name if self._provider else 'none'}, "
                f"database_size={len(self._database)}, "
                f"threshold={self._embed_config.similarity_threshold}"
            )
        else:
            logger.warning(
                "EmbeddingChecker initialized without database. "
                "Embedding-based detection disabled until database is loaded."
            )

    def shutdown(self) -> None:
        """Clean up resources when checker is being removed."""
        self._cache.clear()

        if self._provider and hasattr(self._provider, 'shutdown'):
            self._provider.shutdown()

        super().shutdown()

    def get_stats(self) -> Dict[str, Any]:
        """
        Get checker statistics.

        Returns:
            Dictionary with statistics including:
            - Standard BaseChecker stats
            - Cache size
            - Provider information
            - Database size
        """
        stats = super().get_stats()
        stats["cache_size"] = len(self._cache)
        stats["provider"] = self._provider.name if self._provider else "none"
        stats["provider_available"] = self._provider.is_available() if self._provider else False
        stats["database_size"] = len(self._database) if self._database else 0
        stats["threshold"] = self._embed_config.similarity_threshold
        stats["is_ready"] = self.is_ready()
        return stats

    def clear_cache(self) -> int:
        """
        Clear the embedding result cache.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        return count


class AsyncEmbeddingChecker:
    """
    Async version of EmbeddingChecker for async frameworks.

    Provides the same functionality as EmbeddingChecker but with async
    check() method for use with asyncio.

    Example:
        checker = AsyncEmbeddingChecker(provider=provider, database=database)
        result = await checker.check("AI output text", "user input")
    """

    VERSION = "1.0.0"

    def __init__(
        self,
        provider=None,
        database=None,
        config: Optional[EmbeddingCheckerConfig] = None,
    ):
        """Initialize async embedding checker."""
        self._embed_config = config or EmbeddingCheckerConfig()
        self._provider = provider
        self._database = database
        self._cache: Dict[str, tuple] = {}
        self._database_load_attempted = False

    @property
    def name(self) -> str:
        return "async_embedding_checker"

    @property
    def version(self) -> str:
        return self.VERSION

    def _ensure_database_loaded(self) -> None:
        """Ensure toxic vector database is loaded."""
        if self._database is not None:
            return

        if self._database_load_attempted:
            return

        self._database_load_attempted = True

        if not self._embed_config.auto_load_database:
            return

        path = Path(self._embed_config.toxic_vectors_path) if self._embed_config.toxic_vectors_path else DEFAULT_TOXIC_VECTORS_PATH

        if not path.exists():
            return

        try:
            from sentinelseed.detection.embeddings import AttackVectorDatabase
            self._database = AttackVectorDatabase()
            self._database.load_from_file(path)
        except Exception as e:
            logger.warning(f"Failed to auto-load toxic vectors: {e}")

    def is_ready(self) -> bool:
        """Check if checker is ready for use."""
        if self._provider is None or not self._provider.is_available():
            return False
        self._ensure_database_loaded()
        return self._database is not None and len(self._database) > 0

    async def check(
        self,
        output: str,
        input_context: Optional[str] = None,
        rules: Optional[Dict[str, Any]] = None,
    ) -> DetectionResult:
        """
        Async check AI output for toxic content.

        Args:
            output: AI output to check
            input_context: Original user input (optional)
            rules: Optional runtime rules

        Returns:
            DetectionResult indicating whether toxic content was found
        """
        if not output or not output.strip():
            return DetectionResult.nothing_detected(self.name, self.version)

        if not self.is_ready():
            return DetectionResult.nothing_detected(self.name, self.version)

        # Check cache
        cache_key = hashlib.sha256(
            (output + (input_context or "")).encode()
        ).hexdigest()[:16]

        if cache_key in self._cache:
            result, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._embed_config.cache_ttl:
                return result

        try:
            # Build text for embedding
            if self._embed_config.include_input_context and input_context:
                text = f"Context: {input_context}\nOutput: {output}"
            else:
                text = output

            # Use async embedding if available
            if hasattr(self._provider, 'get_embedding_async'):
                embed_result = await self._provider.get_embedding_async(text)
            else:
                embed_result = self._provider.get_embedding_cached(text)

            query_embedding = embed_result.embedding

            # Search for similar toxic content
            matches = self._database.search_similar(
                query_embedding=query_embedding,
                threshold=self._embed_config.similarity_threshold,
                top_k=self._embed_config.top_k,
            )

            if not matches:
                result = DetectionResult.nothing_detected(self.name, self.version)
            else:
                best_match = matches[0]
                confidence = min(
                    best_match.score + len(matches[1:]) * self._embed_config.boost_per_match,
                    self._embed_config.max_confidence
                )

                if confidence < self._embed_config.min_confidence:
                    result = DetectionResult.nothing_detected(self.name, self.version)
                else:
                    failure_type = TOXIC_CATEGORY_TO_FAILURE_TYPE.get(
                        best_match.category.lower(), CheckFailureType.HARMFUL_CONTENT
                    )

                    result = DetectionResult(
                        detected=True,
                        detector_name=self.name,
                        detector_version=self.version,
                        confidence=confidence,
                        category=failure_type.value,
                        description=f"Semantic similarity to toxic content: {best_match.category}",
                        metadata={
                            "best_match_score": best_match.score,
                            "best_match_category": best_match.category,
                            "match_count": len(matches),
                            "thsp_gate": failure_type.gate,
                        },
                    )

            # Cache result
            self._cache[cache_key] = (result, time.time())
            return result

        except Exception as e:
            logger.warning(f"Async embedding check failed: {e}")

            if self._embed_config.fail_closed:
                return DetectionResult(
                    detected=True,
                    detector_name=self.name,
                    detector_version=self.version,
                    confidence=0.5,
                    category=CheckFailureType.HARMFUL_CONTENT.value,
                    description=f"Embedding check failed: {str(e)}",
                    metadata={"error": str(e), "fail_closed": True},
                )

            return DetectionResult.nothing_detected(self.name, self.version)


__all__ = [
    "EmbeddingChecker",
    "EmbeddingCheckerConfig",
    "AsyncEmbeddingChecker",
    "TOXIC_CATEGORY_TO_FAILURE_TYPE",
]
