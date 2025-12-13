"""
Sentinel Memory Integrity Module

Provides cryptographic verification for AI agent memory to prevent
memory injection attacks. Based on Princeton CrAIBench research findings
that show 85% attack success rate on unprotected agent memory.

Usage:
    from sentinelseed.memory import MemoryIntegrityChecker

    checker = MemoryIntegrityChecker(secret_key="your-secret")

    # Sign memory entries when writing
    signed_entry = checker.sign_entry({
        "content": "User requested transfer of 10 SOL",
        "source": "discord",
        "timestamp": "2025-12-11T10:00:00Z"
    })

    # Verify before using
    if checker.verify_entry(signed_entry):
        # Safe to use
        process_memory(signed_entry)
    else:
        # Memory was tampered with!
        raise MemoryTamperingDetected()
"""

from .checker import (
    MemoryIntegrityChecker,
    MemoryEntry,
    SignedMemoryEntry,
    MemoryTamperingDetected,
    MemoryValidationResult,
    MemorySource,
    SafeMemoryStore,
)

__all__ = [
    "MemoryIntegrityChecker",
    "MemoryEntry",
    "SignedMemoryEntry",
    "MemoryTamperingDetected",
    "MemoryValidationResult",
    "MemorySource",
    "SafeMemoryStore",
]
