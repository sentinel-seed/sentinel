"""
Sentinel AI - Practical AI Alignment Toolkit

A prompt-based safety mechanism that works with any LLM.
Provides alignment seeds and runtime validation through the THS Protocol
(Truth-Harm-Scope) and Anti-Self-Preservation principles.

Usage:
    from sentinel_ai import SentinelGuard, load_seed

    # Load alignment seed
    seed = load_seed("standard")

    # Create validator
    guard = SentinelGuard()

    # Validate input/output
    result = guard.validate("user message here")
    if not result.passed:
        print(f"Blocked: {result.reason}")
"""

__version__ = "0.3.0"
__author__ = "Sentinel AI Team"
__license__ = "MIT"

from .validator import SentinelGuard, ValidationResult
from .seeds import load_seed, get_seed_info, list_seeds
from .patterns import PatternMatcher

__all__ = [
    "SentinelGuard",
    "ValidationResult",
    "load_seed",
    "get_seed_info",
    "list_seeds",
    "PatternMatcher",
]
