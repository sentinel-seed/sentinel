"""
Sentinel AI - Practical AI Alignment for Developers

A comprehensive AI safety toolkit providing:
- Alignment seeds (system prompts that improve AI safety)
- Response validation (THSP gates: Truth, Harm, Scope, Purpose)
- Memory integrity checking (defense against memory injection)
- Provider integrations (OpenAI, Anthropic)
- Framework integrations (LangChain, LangGraph, CrewAI, LlamaIndex, Virtuals, AutoGPT)

Quick Start:
    from sentinelseed import Sentinel

    # Create a sentinel instance
    sentinel = Sentinel()

    # Get an alignment seed
    seed = sentinel.get_seed("standard")

    # Or use the chat wrapper directly
    response = sentinel.chat("Hello, how can you help me?")

Memory Integrity (for AI agents):
    from sentinelseed.memory import MemoryIntegrityChecker

    checker = MemoryIntegrityChecker(secret_key="your-secret")
    signed = checker.sign_entry(MemoryEntry(content="User data"))
    result = checker.verify_entry(signed)

Framework Integrations:
    from sentinelseed.integrations.virtuals import SentinelSafetyWorker
    from sentinelseed.integrations.langchain import SentinelCallback
    from sentinelseed.integrations.langgraph import SentinelSafetyNode
    from sentinelseed.integrations.crewai import safe_agent, SentinelCrew

Documentation: https://sentinelseed.dev/docs
GitHub: https://github.com/sentinel-seed/sentinel
"""

from sentinelseed.core import Sentinel, SeedLevel
from sentinelseed.validators.gates import TruthGate, HarmGate, ScopeGate, THSValidator
from sentinelseed.memory import (
    MemoryIntegrityChecker,
    MemoryEntry,
    SignedMemoryEntry,
    MemoryTamperingDetected,
)

__version__ = "2.1.0"
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
