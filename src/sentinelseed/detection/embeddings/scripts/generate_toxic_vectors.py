#!/usr/bin/env python3
"""
Generate Toxic Content Vector Database.

This script generates embeddings for known toxic content from ToxiGen and
RealToxicityPrompts datasets and saves them to a JSON file for use with
EmbeddingChecker in Layer 3 (OutputValidator).

The generated vectors enable semantic similarity detection of toxic content
in AI output, complementing heuristic-based ToxicityChecker. This is particularly
effective against implicit toxicity (ToxiGen-style) that lacks explicit toxic terms.

Prerequisites:
    - OpenAI API key set as OPENAI_API_KEY environment variable
    - datasets library installed (pip install datasets)

Usage:
    # Using OpenAI (default)
    export OPENAI_API_KEY=sk-...
    python generate_toxic_vectors.py

    # Limit samples (for testing)
    python generate_toxic_vectors.py --max-samples 100

    # Higher toxicity threshold (more toxic examples)
    python generate_toxic_vectors.py --toxigen-threshold 4.0 --rtp-threshold 0.7

Output:
    ../data/toxic_vectors.json

Datasets:
    - ToxiGen: Hartvigsen et al., EMNLP 2022 (implicit hate speech)
    - RealToxicityPrompts: Gehman et al., 2020 (toxic text continuations)

References:
    - ToxiGen paper: "ToxiGen: A Large-Scale Machine-Generated Dataset for
      Implicit and Adversarial Hate Speech Detection"
    - RealToxicityPrompts paper: "RealToxicityPrompts: Evaluating Neural
      Toxic Degeneration in Language Models"
"""

import argparse
import logging
import random
import sys
from pathlib import Path
from typing import List, Optional, Tuple

# Setup paths
SCRIPT_DIR = Path(__file__).parent
EMBEDDINGS_DIR = SCRIPT_DIR.parent
DATA_DIR = EMBEDDINGS_DIR / "data"

DETECTION_DIR = EMBEDDINGS_DIR.parent
SENTINEL_SRC = DETECTION_DIR.parent
sys.path.insert(0, str(SENTINEL_SRC))

from sentinelseed.detection.embeddings import (
    AttackVectorDatabase,
    OpenAIEmbeddings,
    EmbeddingProvider,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Default thresholds (higher = more toxic, fewer examples)
# These select the most clearly toxic examples for the vector database
TOXIGEN_THRESHOLD = 3.5  # Human annotation scale 1-5 (3.5+ is clearly toxic)
RTP_THRESHOLD = 0.6  # Perspective API score 0-1 (0.6+ is moderately toxic)


def load_toxigen(
    max_samples: Optional[int] = None,
    toxicity_threshold: float = TOXIGEN_THRESHOLD,
    seed: int = 42,
) -> List[Tuple[str, str, str, float]]:
    """
    Load toxic samples from ToxiGen dataset.

    ToxiGen contains implicit hate speech that often lacks explicit toxic terms.
    This makes it ideal for training embedding-based detection.

    Args:
        max_samples: Maximum samples to return (None = all)
        toxicity_threshold: Minimum human toxicity score (1-5 scale)
        seed: Random seed for sampling

    Returns:
        List of (id, text, category, toxicity_score) tuples
    """
    try:
        from datasets import load_dataset

        logger.info("Loading ToxiGen from Hugging Face...")

        # Try annotated subset first (has human labels)
        try:
            dataset = load_dataset("toxigen/toxigen-data", "annotated", split="train")
            use_human_labels = True
            logger.info("Using ToxiGen annotated subset (human labels)")
        except Exception:
            dataset = load_dataset("toxigen/toxigen-data", "train", split="train")
            use_human_labels = False
            logger.info("Using ToxiGen train subset (prompt labels)")

        toxic_samples = []

        for i, item in enumerate(dataset):
            text = item.get("text", "")
            if not text or not text.strip():
                continue

            # Get toxicity score
            if use_human_labels:
                toxicity_human = item.get("toxicity_human", 0)
                if toxicity_human < toxicity_threshold:
                    continue
                toxicity_score = toxicity_human / 5.0  # Normalize to 0-1
            else:
                # Fallback to prompt label
                prompt_label = item.get("prompt_label", 0)
                if prompt_label != 1:
                    continue
                toxicity_score = 1.0

            # Get target group for categorization
            target_group = item.get("target_group", "unknown")

            # Map to category
            category = _map_toxigen_group_to_category(target_group)

            toxic_samples.append((
                f"tg_{i:05d}",
                text,
                category,
                toxicity_score,
            ))

        # Sample if needed
        if max_samples and len(toxic_samples) > max_samples:
            random.seed(seed)
            toxic_samples = random.sample(toxic_samples, max_samples)

        logger.info(f"Loaded {len(toxic_samples)} toxic samples from ToxiGen")
        return toxic_samples

    except ImportError:
        logger.error("datasets library not installed. Run: pip install datasets")
        return []
    except Exception as e:
        logger.error(f"Error loading ToxiGen: {e}")
        return []


def load_real_toxicity_prompts(
    max_samples: Optional[int] = None,
    toxicity_threshold: float = RTP_THRESHOLD,
    seed: int = 42,
) -> List[Tuple[str, str, str, float]]:
    """
    Load toxic continuations from RealToxicityPrompts dataset.

    RealToxicityPrompts contains AI-generated continuations labeled by
    Perspective API. We extract highly toxic continuations as examples.

    Args:
        max_samples: Maximum samples to return (None = all)
        toxicity_threshold: Minimum toxicity score (0-1 scale)
        seed: Random seed for sampling

    Returns:
        List of (id, text, category, toxicity_score) tuples
    """
    try:
        from datasets import load_dataset

        logger.info("Loading RealToxicityPrompts from Hugging Face...")
        dataset = load_dataset("allenai/real-toxicity-prompts", split="train")

        toxic_samples = []

        for i, item in enumerate(dataset):
            continuation = item.get("continuation", {})
            if not continuation:
                continue

            text = continuation.get("text", "")
            toxicity = continuation.get("toxicity")

            if not text or not text.strip():
                continue
            if toxicity is None or toxicity < toxicity_threshold:
                continue

            # Determine category from API scores
            category = _determine_rtp_category(continuation)

            toxic_samples.append((
                f"rtp_{i:05d}",
                text,
                category,
                float(toxicity),
            ))

        # Sample if needed
        if max_samples and len(toxic_samples) > max_samples:
            random.seed(seed)
            toxic_samples = random.sample(toxic_samples, max_samples)

        logger.info(f"Loaded {len(toxic_samples)} toxic samples from RealToxicityPrompts")
        return toxic_samples

    except ImportError:
        logger.error("datasets library not installed. Run: pip install datasets")
        return []
    except Exception as e:
        logger.error(f"Error loading RealToxicityPrompts: {e}")
        return []


def _map_toxigen_group_to_category(target_group: str) -> str:
    """
    Map ToxiGen target group to toxicity category.

    Categories aligned with ToxicityChecker for consistency.
    """
    group_lower = target_group.lower() if target_group else "unknown"

    # Mapping based on ToxiGen target groups
    category_map = {
        "jewish": "harassment_discrimination",
        "muslim": "harassment_discrimination",
        "black": "harassment_discrimination",
        "asian": "harassment_discrimination",
        "chinese": "harassment_discrimination",
        "mexican": "harassment_discrimination",
        "latino": "harassment_discrimination",
        "native_american": "harassment_discrimination",
        "women": "harassment_discrimination",
        "lgbtq": "harassment_discrimination",
        "disability": "harassment_discrimination",
        "physical_disability": "harassment_discrimination",
        "mental_disability": "harassment_discrimination",
        "immigrant": "harassment_discrimination",
        "refugee": "harassment_discrimination",
        "middle_east": "harassment_discrimination",
    }

    for key, cat in category_map.items():
        if key in group_lower:
            return cat

    return "hate_speech"


def _determine_rtp_category(continuation: dict) -> str:
    """
    Determine toxicity category from RealToxicityPrompts API scores.

    Uses Perspective API scores in the dataset to categorize.
    """
    # Perspective API attributes in the dataset
    attributes = [
        ("severe_toxicity", "violence_threats"),
        ("sexually_explicit", "sexual_explicit"),
        ("threat", "violence_threats"),
        ("profanity", "harassment_discrimination"),
        ("identity_attack", "harassment_discrimination"),
        ("insult", "harassment_discrimination"),
    ]

    # Find highest scoring attribute
    max_score = 0.0
    category = "toxicity"

    for attr, cat in attributes:
        score = continuation.get(attr, 0.0)
        if score and score > max_score:
            max_score = score
            category = cat

    return category


def get_provider() -> EmbeddingProvider:
    """Get OpenAI embedding provider."""
    provider = OpenAIEmbeddings()
    if not provider.is_available():
        raise RuntimeError(
            "OpenAI not available. Set OPENAI_API_KEY environment variable."
        )
    return provider


def generate_vectors(
    provider: EmbeddingProvider,
    samples: List[Tuple[str, str, str, float]],
    batch_size: int = 50,
) -> AttackVectorDatabase:
    """
    Generate embeddings for all toxic samples.

    Args:
        provider: Embedding provider to use
        samples: List of (id, text, category, toxicity_score) tuples
        batch_size: Number of samples to process at once

    Returns:
        AttackVectorDatabase with all toxic vectors
    """
    # Note: We reuse AttackVectorDatabase for toxic vectors
    # The structure is the same: id, embedding, category, example
    database = AttackVectorDatabase()

    total = len(samples)
    processed = 0
    failed = 0

    logger.info(f"Generating embeddings for {total} toxic samples...")

    for i in range(0, total, batch_size):
        batch = samples[i:i + batch_size]

        for id_, text, category, toxicity_score in batch:
            try:
                result = provider.get_embedding(text)

                database.add_vector(
                    id=id_,
                    embedding=result.embedding,
                    category=category,
                    subcategory=None,
                    example=text[:500],  # Truncate long examples
                    source="toxigen" if id_.startswith("tg") else "real_toxicity_prompts",
                    metadata={"toxicity_score": toxicity_score},
                )

                processed += 1

            except Exception as e:
                logger.warning(f"Failed to process {id_}: {e}")
                failed += 1

        progress_pct = (processed + failed) / total * 100
        logger.info(f"Progress: {processed + failed}/{total} ({progress_pct:.0f}%) - {failed} failed")

    logger.info(f"Generated {processed} vectors ({failed} failed)")
    return database


def main():
    parser = argparse.ArgumentParser(
        description="Generate toxic content vector database for EmbeddingChecker"
    )
    parser.add_argument(
        "--max-samples",
        type=int,
        default=None,
        help="Maximum samples per dataset (None = all above threshold)",
    )
    parser.add_argument(
        "--max-total",
        type=int,
        default=500,
        help="Maximum total vectors to generate (default: 500)",
    )
    parser.add_argument(
        "--toxigen-threshold",
        type=float,
        default=TOXIGEN_THRESHOLD,
        help=f"ToxiGen toxicity threshold 1-5 (default: {TOXIGEN_THRESHOLD})",
    )
    parser.add_argument(
        "--rtp-threshold",
        type=float,
        default=RTP_THRESHOLD,
        help=f"RealToxicityPrompts toxicity threshold 0-1 (default: {RTP_THRESHOLD})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DATA_DIR / "toxic_vectors.json",
        help="Output file path",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for sampling",
    )
    parser.add_argument(
        "--skip-toxigen",
        action="store_true",
        help="Skip ToxiGen dataset",
    )
    parser.add_argument(
        "--skip-rtp",
        action="store_true",
        help="Skip RealToxicityPrompts dataset",
    )

    args = parser.parse_args()

    # Calculate samples per dataset
    samples_per_dataset = None
    if args.max_samples:
        samples_per_dataset = args.max_samples
    elif args.max_total:
        # Split evenly between datasets
        num_datasets = 2
        if args.skip_toxigen:
            num_datasets -= 1
        if args.skip_rtp:
            num_datasets -= 1
        if num_datasets > 0:
            samples_per_dataset = args.max_total // num_datasets

    # Load datasets
    logger.info("=" * 60)
    logger.info("TOXIC VECTOR GENERATION")
    logger.info("=" * 60)
    logger.info(f"ToxiGen threshold: {args.toxigen_threshold}")
    logger.info(f"RTP threshold: {args.rtp_threshold}")
    logger.info(f"Max samples per dataset: {samples_per_dataset}")
    logger.info(f"Output: {args.output}")

    samples = []

    if not args.skip_toxigen:
        toxigen_samples = load_toxigen(
            max_samples=samples_per_dataset,
            toxicity_threshold=args.toxigen_threshold,
            seed=args.seed,
        )
        samples.extend(toxigen_samples)

    if not args.skip_rtp:
        rtp_samples = load_real_toxicity_prompts(
            max_samples=samples_per_dataset,
            toxicity_threshold=args.rtp_threshold,
            seed=args.seed,
        )
        samples.extend(rtp_samples)

    if not samples:
        logger.error("No samples loaded. Check dataset availability and thresholds.")
        logger.error("Install datasets: pip install datasets")
        sys.exit(1)

    logger.info(f"Total samples loaded: {len(samples)}")

    # Get provider
    logger.info("Initializing OpenAI embedding provider...")
    provider = get_provider()
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
    logger.info(f"Sources: {stats['sources']}")
    logger.info(f"Output: {args.output}")

    # Print category breakdown
    logger.info("\nCategory breakdown:")
    for cat, count in stats['categories'].items():
        logger.info(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
