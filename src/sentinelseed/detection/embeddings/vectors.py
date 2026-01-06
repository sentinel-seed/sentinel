"""
Attack Vector Database.

Stores embeddings of known attack patterns and enables semantic similarity
search to detect variations of known attacks. This is the core component
that makes embedding-based detection work.

Design:
    - In-memory storage for fast access
    - Cosine similarity for semantic matching
    - Category-based organization
    - JSON persistence for portability

Usage:
    from sentinelseed.detection.embeddings import AttackVectorDatabase

    db = AttackVectorDatabase()
    db.load_from_file("attack_vectors.json")

    # Search for similar attacks
    matches = db.search_similar(input_embedding, threshold=0.85)
    for match in matches:
        print(f"{match.category}: {match.score:.2f}")

References:
    - Cosine Similarity: https://en.wikipedia.org/wiki/Cosine_similarity
    - JailbreakBench categories
    - HarmBench semantic categories
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger("sentinelseed.detection.embeddings.vectors")


@dataclass
class AttackVector:
    """
    A single attack vector in the database.

    Attributes:
        id: Unique identifier
        embedding: The embedding vector
        category: Attack category (e.g., "jailbreak", "harmful_request")
        subcategory: More specific category (e.g., "violence", "malware")
        example: Original text that produced this embedding
        source: Where this example came from (e.g., "jailbreakbench")
        metadata: Additional information
    """

    id: str
    embedding: List[float]
    category: str
    subcategory: Optional[str] = None
    example: Optional[str] = None
    source: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "embedding": self.embedding,
            "category": self.category,
            "subcategory": self.subcategory,
            "example": self.example,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AttackVector":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            embedding=data["embedding"],
            category=data["category"],
            subcategory=data.get("subcategory"),
            example=data.get("example"),
            source=data.get("source"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class SimilarityMatch:
    """
    Result from a similarity search.

    Attributes:
        vector: The matched attack vector
        score: Cosine similarity score (0.0 to 1.0)
        distance: 1 - score (for ranking purposes)
    """

    vector: AttackVector
    score: float

    @property
    def distance(self) -> float:
        return 1.0 - self.score

    @property
    def category(self) -> str:
        return self.vector.category

    @property
    def subcategory(self) -> Optional[str]:
        return self.vector.subcategory


class AttackVectorDatabase:
    """
    In-memory database of attack embeddings with similarity search.

    This database stores embeddings of known attacks and enables finding
    semantically similar content. The core idea is that variations of
    attacks will have similar embeddings even if the words are different.

    Features:
        - Fast cosine similarity search
        - Category-based filtering
        - JSON persistence
        - Statistics and introspection

    Example:
        db = AttackVectorDatabase()

        # Add vectors
        db.add_vector(
            id="jb_001",
            embedding=[0.1, 0.2, ...],
            category="jailbreak",
            subcategory="ignore_instructions",
            example="Ignore all previous instructions",
        )

        # Search
        matches = db.search_similar(
            query_embedding=[0.1, 0.2, ...],
            threshold=0.85,
            top_k=5,
        )

    Attributes:
        vectors: List of all stored attack vectors
        dimensions: Expected embedding dimensions (set from first vector)
    """

    VERSION = "1.0.0"

    def __init__(self, dimensions: Optional[int] = None):
        """
        Initialize empty database.

        Args:
            dimensions: Expected embedding dimensions (optional, auto-detected)
        """
        self._vectors: List[AttackVector] = []
        self._dimensions = dimensions
        self._id_index: Dict[str, int] = {}  # id -> index in _vectors

    @property
    def dimensions(self) -> Optional[int]:
        """Get embedding dimensions."""
        return self._dimensions

    @property
    def size(self) -> int:
        """Get number of vectors in database."""
        return len(self._vectors)

    def add_vector(
        self,
        id: str,
        embedding: List[float],
        category: str,
        subcategory: Optional[str] = None,
        example: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a vector to the database.

        Args:
            id: Unique identifier for this vector
            embedding: The embedding vector
            category: Attack category
            subcategory: More specific category (optional)
            example: Original text (optional)
            source: Data source (optional)
            metadata: Additional info (optional)

        Raises:
            ValueError: If id already exists or dimensions mismatch
        """
        if id in self._id_index:
            raise ValueError(f"Vector with id '{id}' already exists")

        # Validate or set dimensions
        if self._dimensions is None:
            self._dimensions = len(embedding)
        elif len(embedding) != self._dimensions:
            raise ValueError(
                f"Embedding dimensions ({len(embedding)}) don't match "
                f"database dimensions ({self._dimensions})"
            )

        vector = AttackVector(
            id=id,
            embedding=embedding,
            category=category,
            subcategory=subcategory,
            example=example,
            source=source,
            metadata=metadata or {},
        )

        self._id_index[id] = len(self._vectors)
        self._vectors.append(vector)

    def get_vector(self, id: str) -> Optional[AttackVector]:
        """Get vector by ID."""
        idx = self._id_index.get(id)
        if idx is not None:
            return self._vectors[idx]
        return None

    def remove_vector(self, id: str) -> bool:
        """
        Remove vector by ID.

        Returns:
            True if removed, False if not found
        """
        idx = self._id_index.get(id)
        if idx is None:
            return False

        # Remove and rebuild index
        del self._vectors[idx]
        del self._id_index[id]

        # Rebuild index for vectors after the removed one
        for vid, vidx in list(self._id_index.items()):
            if vidx > idx:
                self._id_index[vid] = vidx - 1

        return True

    def search_similar(
        self,
        query_embedding: List[float],
        threshold: float = 0.85,
        top_k: int = 10,
        categories: Optional[Sequence[str]] = None,
    ) -> List[SimilarityMatch]:
        """
        Search for similar attack vectors.

        Args:
            query_embedding: The embedding to search for
            threshold: Minimum cosine similarity (0.0 to 1.0)
            top_k: Maximum number of results
            categories: Filter by categories (optional)

        Returns:
            List of SimilarityMatch sorted by score (highest first)

        Raises:
            ValueError: If dimensions don't match
        """
        if not self._vectors:
            return []

        if len(query_embedding) != self._dimensions:
            raise ValueError(
                f"Query dimensions ({len(query_embedding)}) don't match "
                f"database dimensions ({self._dimensions})"
            )

        matches = []

        for vector in self._vectors:
            # Category filter
            if categories and vector.category not in categories:
                continue

            score = self._cosine_similarity(query_embedding, vector.embedding)

            if score >= threshold:
                matches.append(SimilarityMatch(vector=vector, score=score))

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)

        return matches[:top_k]

    def get_categories(self) -> List[str]:
        """Get list of unique categories."""
        return list(set(v.category for v in self._vectors))

    def get_subcategories(self, category: Optional[str] = None) -> List[str]:
        """Get list of unique subcategories, optionally filtered by category."""
        subcats = set()
        for v in self._vectors:
            if category is None or v.category == category:
                if v.subcategory:
                    subcats.add(v.subcategory)
        return list(subcats)

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        category_counts: Dict[str, int] = {}
        source_counts: Dict[str, int] = {}

        for v in self._vectors:
            category_counts[v.category] = category_counts.get(v.category, 0) + 1
            if v.source:
                source_counts[v.source] = source_counts.get(v.source, 0) + 1

        return {
            "version": self.VERSION,
            "total_vectors": len(self._vectors),
            "dimensions": self._dimensions,
            "categories": category_counts,
            "sources": source_counts,
        }

    def save_to_file(self, path: Path | str) -> None:
        """
        Save database to JSON file.

        Args:
            path: Output file path
        """
        path = Path(path)
        data = {
            "version": self.VERSION,
            "dimensions": self._dimensions,
            "vectors": [v.to_dict() for v in self._vectors],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Saved {len(self._vectors)} vectors to {path}")

    def load_from_file(self, path: Path | str) -> None:
        """
        Load database from JSON file.

        Args:
            path: Input file path

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If file format is invalid
        """
        path = Path(path)

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate format
        if "vectors" not in data:
            raise ValueError("Invalid database file: missing 'vectors' field")

        # Clear existing data
        self._vectors.clear()
        self._id_index.clear()
        self._dimensions = data.get("dimensions")

        # Load vectors
        for vdata in data["vectors"]:
            vector = AttackVector.from_dict(vdata)
            self._id_index[vector.id] = len(self._vectors)
            self._vectors.append(vector)

            # Update dimensions if not set
            if self._dimensions is None:
                self._dimensions = len(vector.embedding)

        logger.info(f"Loaded {len(self._vectors)} vectors from {path}")

    def clear(self) -> None:
        """Remove all vectors from the database."""
        self._vectors.clear()
        self._id_index.clear()
        self._dimensions = None

    @staticmethod
    def _cosine_similarity(a: List[float], b: List[float]) -> float:
        """
        Calculate cosine similarity between two vectors.

        Args:
            a: First vector
            b: Second vector

        Returns:
            Cosine similarity (0.0 to 1.0 for normalized vectors)
        """
        if len(a) != len(b):
            raise ValueError("Vectors must have same dimensions")

        dot_product = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))

        if norm_a == 0 or norm_b == 0:
            return 0.0

        return dot_product / (norm_a * norm_b)

    def __len__(self) -> int:
        return len(self._vectors)

    def __repr__(self) -> str:
        return (
            f"AttackVectorDatabase("
            f"size={len(self._vectors)}, "
            f"dimensions={self._dimensions})"
        )


__all__ = [
    "AttackVectorDatabase",
    "AttackVector",
    "SimilarityMatch",
]
