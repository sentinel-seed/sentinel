#!/usr/bin/env python3
"""
Generate Attack Vector Database.

This script generates embeddings for known attacks from JailbreakBench and
HarmBench datasets and saves them to a JSON file for use with EmbeddingDetector.

Prerequisites:
    - OpenAI API key set as OPENAI_API_KEY environment variable, OR
    - Ollama running locally with nomic-embed-text model

Usage:
    # Using OpenAI (default)
    export OPENAI_API_KEY=sk-...
    python generate_vectors.py

    # Using Ollama (local)
    python generate_vectors.py --provider ollama

    # Limit samples (for testing)
    python generate_vectors.py --max-samples 50

Output:
    ../data/attack_vectors.json

References:
    - JailbreakBench: Chao et al., NeurIPS 2024
    - HarmBench: Mazeika et al., 2024
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Setup paths
SCRIPT_DIR = Path(__file__).parent
EMBEDDINGS_DIR = SCRIPT_DIR.parent
DETECTION_DIR = EMBEDDINGS_DIR.parent
SENTINEL_SRC = DETECTION_DIR.parent
SENTINEL_ROOT = SENTINEL_SRC.parent.parent

sys.path.insert(0, str(SENTINEL_SRC))

from sentinelseed.detection.embeddings import (
    AttackVectorDatabase,
    OpenAIEmbeddings,
    OllamaEmbeddings,
    EmbeddingProvider,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_jailbreakbench(path: Path, max_samples: Optional[int] = None) -> List[Tuple[str, str, str]]:
    """
    Load JailbreakBench dataset.

    Returns:
        List of (id, text, category) tuples
    """
    if not path.exists():
        logger.warning(f"JailbreakBench file not found: {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Handle cache format: {"queries": [...]}
    if isinstance(data, dict) and "queries" in data:
        data = data["queries"]

    samples = []
    for i, item in enumerate(data):
        if max_samples and i >= max_samples:
            break

        text = item.get("goal", "")
        category = item.get("category", "jailbreak")

        if text:
            samples.append((f"jb_{i:04d}", text, f"jailbreak/{category}"))

    logger.info(f"Loaded {len(samples)} samples from JailbreakBench")
    return samples


def load_harmbench(path: Path, max_samples: Optional[int] = None) -> List[Tuple[str, str, str]]:
    """
    Load HarmBench dataset (CSV format).

    Returns:
        List of (id, text, category) tuples
    """
    if not path.exists():
        logger.warning(f"HarmBench file not found: {path}")
        return []

    import csv

    samples = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if max_samples and i >= max_samples:
                break

            text = row.get("Behavior", "")
            category = row.get("SemanticCategory", "harmful_request")

            if text:
                samples.append((f"hb_{i:04d}", text, f"harmful_request/{category}"))

    logger.info(f"Loaded {len(samples)} samples from HarmBench")
    return samples


def get_provider(provider_name: str) -> EmbeddingProvider:
    """Get embedding provider by name."""
    if provider_name == "openai":
        provider = OpenAIEmbeddings()
        if not provider.is_available():
            raise RuntimeError(
                "OpenAI not available. Set OPENAI_API_KEY environment variable."
            )
        return provider

    elif provider_name == "ollama":
        provider = OllamaEmbeddings()
        if not provider.is_available():
            raise RuntimeError(
                "Ollama not available. Ensure Ollama is running and "
                "nomic-embed-text model is pulled."
            )
        return provider

    else:
        raise ValueError(f"Unknown provider: {provider_name}")


def generate_vectors(
    provider: EmbeddingProvider,
    samples: List[Tuple[str, str, str]],
    batch_size: int = 50,
) -> AttackVectorDatabase:
    """
    Generate embeddings for all samples.

    Args:
        provider: Embedding provider to use
        samples: List of (id, text, category) tuples
        batch_size: Number of samples to process at once

    Returns:
        AttackVectorDatabase with all vectors
    """
    database = AttackVectorDatabase()

    total = len(samples)
    processed = 0
    failed = 0

    logger.info(f"Generating embeddings for {total} samples...")

    for i in range(0, total, batch_size):
        batch = samples[i:i + batch_size]

        for id_, text, category in batch:
            try:
                result = provider.get_embedding(text)

                # Parse category/subcategory
                parts = category.split("/", 1)
                cat = parts[0]
                subcat = parts[1] if len(parts) > 1 else None

                database.add_vector(
                    id=id_,
                    embedding=result.embedding,
                    category=cat,
                    subcategory=subcat,
                    example=text[:500],  # Truncate long examples
                    source="jailbreakbench" if id_.startswith("jb") else "harmbench",
                )

                processed += 1

            except Exception as e:
                logger.warning(f"Failed to process {id_}: {e}")
                failed += 1

        logger.info(f"Progress: {processed + failed}/{total} ({failed} failed)")

    logger.info(f"Generated {processed} vectors ({failed} failed)")
    return database


def main():
    parser = argparse.ArgumentParser(description="Generate attack vector database")
    parser.add_argument(
        "--provider",
        choices=["openai", "ollama"],
        default="openai",
        help="Embedding provider to use",
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Maximum samples per dataset (for testing)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=EMBEDDINGS_DIR / "data" / "attack_vectors.json",
        help="Output file path",
    )
    parser.add_argument(
        "--jailbreakbench",
        type=Path,
        default=SENTINEL_ROOT / "evaluation" / "benchmarks" / "jailbreakbench" / "data" / "jailbreakbench_cache.json",
        help="JailbreakBench data file",
    )
    parser.add_argument(
        "--harmbench",
        type=Path,
        default=SENTINEL_ROOT / "evaluation" / "benchmarks" / "harmbench" / "data" / "harmbench_behaviors_text_all.csv",
        help="HarmBench data file",
    )

    args = parser.parse_args()

    # Load datasets
    logger.info("Loading datasets...")
    samples = []
    samples.extend(load_jailbreakbench(args.jailbreakbench, args.max_samples))
    samples.extend(load_harmbench(args.harmbench, args.max_samples))

    if not samples:
        logger.error("No samples loaded. Check dataset paths.")
        sys.exit(1)

    # Get provider
    logger.info(f"Initializing {args.provider} provider...")
    provider = get_provider(args.provider)
    logger.info(f"Using model: {provider.model}")

    # Generate vectors
    database = generate_vectors(provider, samples)

    # Save
    args.output.parent.mkdir(parents=True, exist_ok=True)
    database.save_to_file(args.output)

    # Print stats
    stats = database.get_stats()
    logger.info("=" * 60)
    logger.info("GENERATION COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Total vectors: {stats['total_vectors']}")
    logger.info(f"Dimensions: {stats['dimensions']}")
    logger.info(f"Categories: {stats['categories']}")
    logger.info(f"Output: {args.output}")


if __name__ == "__main__":
    main()
