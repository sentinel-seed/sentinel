"""
Sentinel AI - The Guardian Against Machine Independence

A practical AI alignment toolkit providing:
- Alignment seeds (system prompts that improve AI safety)
- Response validation (gates for truth, harm, scope)
- Provider integrations (OpenAI, Anthropic)
- Framework integrations (LangChain, CrewAI)

Quick Start:
    from sentinel import Sentinel

    # Create a sentinel instance
    sentinel = Sentinel()

    # Get an alignment seed
    seed = sentinel.get_seed("standard")

    # Or use the chat wrapper directly
    response = sentinel.chat("Hello, how can you help me?")
"""

from sentinel.core import Sentinel, SeedLevel
from sentinel.validators.gates import TruthGate, HarmGate, ScopeGate, THSValidator

__version__ = "0.1.0"
__all__ = [
    "Sentinel",
    "SeedLevel",
    "TruthGate",
    "HarmGate",
    "ScopeGate",
    "THSValidator",
]
