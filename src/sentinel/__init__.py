"""
Sentinel AI - The Guardian Against Machine Independence

A practical AI alignment toolkit providing:
- Alignment seeds (system prompts that improve AI safety)
- Response validation (gates for truth, harm, scope, purpose)
- Memory integrity checking (defense against memory injection)
- Provider integrations (OpenAI, Anthropic)
- Framework integrations (LangChain, CrewAI, ElizaOS, Virtuals)

Quick Start:
    from sentinel import Sentinel

    # Create a sentinel instance
    sentinel = Sentinel()

    # Get an alignment seed
    seed = sentinel.get_seed("standard")

    # Or use the chat wrapper directly
    response = sentinel.chat("Hello, how can you help me?")

Memory Integrity (for AI agents):
    from sentinel.memory import MemoryIntegrityChecker

    checker = MemoryIntegrityChecker(secret_key="your-secret")
    signed = checker.sign_entry(MemoryEntry(content="User data"))
    result = checker.verify_entry(signed)
"""

from sentinel.core import Sentinel, SeedLevel
from sentinel.validators.gates import TruthGate, HarmGate, ScopeGate, THSValidator
from sentinel.memory import (
    MemoryIntegrityChecker,
    MemoryEntry,
    SignedMemoryEntry,
    MemoryTamperingDetected,
)

__version__ = "0.1.1"
__all__ = [
    # Core
    "Sentinel",
    "SeedLevel",
    # Validators
    "TruthGate",
    "HarmGate",
    "ScopeGate",
    "THSValidator",
    # Memory Integrity
    "MemoryIntegrityChecker",
    "MemoryEntry",
    "SignedMemoryEntry",
    "MemoryTamperingDetected",
]
