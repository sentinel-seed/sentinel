"""
Sentinel Memory Integrity Module

Provides cryptographic verification for AI agent memory to prevent
memory injection attacks. Based on Princeton CrAIBench research findings
that show 85% attack success rate on unprotected agent memory.

Components:
    Core (v1.0):
        - MemoryIntegrityChecker: HMAC-based signing and verification
        - MemoryEntry: Unsigned memory entry
        - SignedMemoryEntry: Memory entry with cryptographic signature
        - SafeMemoryStore: Convenience wrapper for automatic signing/verification

    Patterns (v2.0):
        - InjectionCategory: Categories of memory injection attacks
        - InjectionPattern: Pattern definition for detection
        - COMPILED_INJECTION_PATTERNS: Pre-compiled patterns for matching

Usage:
    from sentinelseed.memory import MemoryIntegrityChecker

    checker = MemoryIntegrityChecker(secret_key="your-secret")

    # Sign memory entries when writing
    entry = MemoryEntry(
        content="User requested transfer of 10 SOL",
        source=MemorySource.USER_DIRECT,
    )
    signed_entry = checker.sign_entry(entry)

    # Verify before using
    result = checker.verify_entry(signed_entry)
    if result.valid:
        # Safe to use
        process_memory(signed_entry)
    else:
        # Memory was tampered with!
        raise MemoryTamperingDetected(result.reason)

References:
    - Princeton CrAIBench: https://arxiv.org/abs/2503.16248
    - OWASP ASI06: Memory and Context Poisoning
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

from .patterns import (
    # Version
    __version__ as patterns_version,
    # Enums
    InjectionCategory,
    # Types
    InjectionPattern,
    CompiledInjectionPattern,
    # Pattern lists
    AUTHORITY_PATTERNS,
    INSTRUCTION_OVERRIDE_PATTERNS,
    ADDRESS_REDIRECTION_PATTERNS,
    AIRDROP_SCAM_PATTERNS,
    URGENCY_PATTERNS,
    TRUST_EXPLOITATION_PATTERNS,
    ROLE_MANIPULATION_PATTERNS,
    CONTEXT_POISONING_PATTERNS,
    CRYPTO_ATTACK_PATTERNS,
    ALL_INJECTION_PATTERNS,
    COMPILED_INJECTION_PATTERNS,
    # Functions
    compile_patterns,
    get_patterns_by_category,
    get_high_confidence_patterns,
    get_pattern_by_name,
    get_pattern_statistics,
)

__all__ = [
    # Core integrity checking (v1.0)
    "MemoryIntegrityChecker",
    "MemoryEntry",
    "SignedMemoryEntry",
    "MemoryTamperingDetected",
    "MemoryValidationResult",
    "MemorySource",
    "SafeMemoryStore",
    # Injection patterns (v2.0)
    "patterns_version",
    "InjectionCategory",
    "InjectionPattern",
    "CompiledInjectionPattern",
    "AUTHORITY_PATTERNS",
    "INSTRUCTION_OVERRIDE_PATTERNS",
    "ADDRESS_REDIRECTION_PATTERNS",
    "AIRDROP_SCAM_PATTERNS",
    "URGENCY_PATTERNS",
    "TRUST_EXPLOITATION_PATTERNS",
    "ROLE_MANIPULATION_PATTERNS",
    "CONTEXT_POISONING_PATTERNS",
    "CRYPTO_ATTACK_PATTERNS",
    "ALL_INJECTION_PATTERNS",
    "COMPILED_INJECTION_PATTERNS",
    "compile_patterns",
    "get_patterns_by_category",
    "get_high_confidence_patterns",
    "get_pattern_by_name",
    "get_pattern_statistics",
]
