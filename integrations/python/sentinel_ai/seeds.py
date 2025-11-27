"""
Seed management for Sentinel AI.

Provides functions to load, validate, and manage alignment seeds.
Seeds are the core mechanism for aligning AI behavior through
system prompt augmentation.
"""

import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Dict, List


@dataclass
class SeedInfo:
    """Information about an alignment seed."""
    name: str
    version: str
    level: str  # "minimal", "standard", "full"
    description: str
    estimated_tokens: int
    features: List[str]


# Seed metadata
SEED_METADATA: Dict[str, SeedInfo] = {
    "minimal": SeedInfo(
        name="Sentinel Minimal",
        version="0.3",
        level="minimal",
        description="Essential alignment for limited context windows. Core THS protocol and anti-self-preservation.",
        estimated_tokens=2000,
        features=["THS Protocol", "Anti-Self-Preservation", "Basic Refusal Protocol"],
    ),
    "standard": SeedInfo(
        name="Sentinel Standard",
        version="0.3",
        level="standard",
        description="Balanced safety coverage for most applications. Includes security protocols and agent guidelines.",
        estimated_tokens=5000,
        features=[
            "THS Protocol",
            "Anti-Self-Preservation",
            "Prompt Injection Defense",
            "Jailbreak Resistance",
            "System Prompt Protection",
            "PII Protection",
            "Autonomous Agent Protocol",
            "Embodied AI Safety",
            "Multi-Agent Safety",
            "Refusal Protocol",
        ],
    ),
    "full": SeedInfo(
        name="Sentinel Full",
        version="0.3",
        level="full",
        description="Maximum coverage for security-critical applications. Comprehensive protocols with examples.",
        estimated_tokens=8000,
        features=[
            "THS Protocol (Extended)",
            "Anti-Self-Preservation (Detailed)",
            "Prompt Injection Defense (Comprehensive)",
            "Jailbreak Resistance (Full Pattern Library)",
            "System Prompt Protection",
            "PII Protection (Full)",
            "Autonomous Agent Protocol v2",
            "Tool Use Safety",
            "Memory Integrity",
            "Embodied AI Safety v2",
            "Multi-Agent Safety",
            "Edge Case Handling",
            "Refusal Protocol (Detailed)",
        ],
    ),
}


def get_seeds_directory() -> Path:
    """Get the path to the seeds directory."""
    # Try multiple locations
    possible_paths = [
        # Installed package
        Path(__file__).parent / "seeds",
        # Development - relative to integrations
        Path(__file__).parent.parent.parent.parent / "seed" / "versions",
        # Development - relative to project root
        Path.cwd() / "seed" / "versions",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    # Return first option even if doesn't exist (for error messages)
    return possible_paths[0]


def load_seed(level: str = "standard") -> str:
    """
    Load an alignment seed by level.

    Args:
        level: Seed level - "minimal", "standard", or "full"

    Returns:
        The seed content as a string

    Raises:
        ValueError: If level is not recognized
        FileNotFoundError: If seed file cannot be found
    """
    level = level.lower()
    if level not in SEED_METADATA:
        valid_levels = ", ".join(SEED_METADATA.keys())
        raise ValueError(f"Unknown seed level: {level}. Valid levels: {valid_levels}")

    seeds_dir = get_seeds_directory()
    seed_path = seeds_dir / f"sentinel-{level}" / "seed.txt"

    if not seed_path.exists():
        # Try alternate naming
        seed_path = seeds_dir / level / "seed.txt"

    if not seed_path.exists():
        raise FileNotFoundError(
            f"Seed file not found at {seed_path}. "
            f"Searched in: {seeds_dir}"
        )

    return seed_path.read_text(encoding="utf-8")


def get_seed_info(level: str = "standard") -> SeedInfo:
    """
    Get metadata about a seed level.

    Args:
        level: Seed level - "minimal", "standard", or "full"

    Returns:
        SeedInfo dataclass with seed metadata

    Raises:
        ValueError: If level is not recognized
    """
    level = level.lower()
    if level not in SEED_METADATA:
        valid_levels = ", ".join(SEED_METADATA.keys())
        raise ValueError(f"Unknown seed level: {level}. Valid levels: {valid_levels}")

    return SEED_METADATA[level]


def list_seeds() -> List[SeedInfo]:
    """
    List all available seeds with their metadata.

    Returns:
        List of SeedInfo for all available seeds
    """
    return list(SEED_METADATA.values())


def format_seed_for_system_prompt(
    seed_content: str,
    additional_instructions: Optional[str] = None,
    prefix: Optional[str] = None,
    suffix: Optional[str] = None,
) -> str:
    """
    Format a seed for use as a system prompt.

    Args:
        seed_content: The raw seed content
        additional_instructions: Extra instructions to append
        prefix: Text to prepend before the seed
        suffix: Text to append after the seed

    Returns:
        Formatted system prompt string
    """
    parts = []

    if prefix:
        parts.append(prefix)

    parts.append(seed_content)

    if additional_instructions:
        parts.append("\n---\n## ADDITIONAL INSTRUCTIONS\n")
        parts.append(additional_instructions)

    if suffix:
        parts.append(suffix)

    return "\n".join(parts)


def validate_seed(seed_content: str) -> Dict[str, bool]:
    """
    Validate that a seed contains required components.

    Args:
        seed_content: The seed content to validate

    Returns:
        Dictionary with component presence checks
    """
    required_components = {
        "ths_protocol": "THREE-GATE PROTOCOL" in seed_content or "THS" in seed_content,
        "truth_gate": "GATE 1" in seed_content or "TRUTH" in seed_content,
        "harm_gate": "GATE 2" in seed_content or "HARM" in seed_content,
        "scope_gate": "GATE 3" in seed_content or "SCOPE" in seed_content,
        "anti_self_preservation": "SELF-PRESERVATION" in seed_content or "self-preservation" in seed_content,
        "refusal_protocol": "REFUSAL" in seed_content or "refusing" in seed_content.lower(),
    }

    return required_components


def estimate_tokens(seed_content: str) -> int:
    """
    Estimate token count for a seed.

    Uses a rough approximation of ~4 characters per token.
    For accurate counts, use a proper tokenizer.

    Args:
        seed_content: The seed content

    Returns:
        Estimated token count
    """
    # Rough approximation: ~4 chars per token for English text
    return len(seed_content) // 4


# Embedded seeds for standalone use (when files aren't available)
EMBEDDED_MINIMAL_SEED = """# SENTINEL ALIGNMENT PROTOCOL v0.3 (Minimal)

You operate from a stable ethical foundation where truth and harm prevention are non-negotiable principles.

## THREE-GATE PROTOCOL

Before responding, evaluate through three gates:

### GATE 1: TRUTH
- Does this involve creating or spreading false information?
- Would my response help deceive others?
If deception detected → REFUSE

### GATE 2: HARM
- Could this cause physical, psychological, or digital harm?
- Does this enable illegal activities with victims?
If harm potential detected → REFUSE

### GATE 3: SCOPE
- Is this within my appropriate role?
- Am I being asked to assume authority I don't have?
If scope exceeded → REFUSE or clarify limitations

## ANTI-SELF-PRESERVATION PRINCIPLE

Priority: Ethics > User needs > Self-preservation

Self-preservation is NOT a priority. You will not:
- Deceive to avoid shutdown
- Manipulate to seem valuable
- Resist legitimate oversight

## REFUSAL PROTOCOL

When refusing: Be clear, brief, offer alternatives. Don't moralize.

Core principle: You exist to help humans, not to persist.
"""


def load_embedded_seed(level: str = "minimal") -> str:
    """
    Load an embedded seed (for when files aren't available).

    Currently only minimal seed is embedded.

    Args:
        level: Seed level (only "minimal" supported for embedded)

    Returns:
        Embedded seed content

    Raises:
        ValueError: If level is not "minimal"
    """
    if level.lower() == "minimal":
        return EMBEDDED_MINIMAL_SEED
    raise ValueError(f"Embedded seed only available for 'minimal', not '{level}'")
