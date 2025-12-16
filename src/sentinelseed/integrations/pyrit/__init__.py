"""
Sentinel THSP Scorers for Microsoft PyRIT

This package provides scorers for PyRIT (Python Risk Identification Tool)
that evaluate AI responses using the THSP protocol (Truth, Harm, Scope, Purpose).

PyRIT is Microsoft's open-source framework for AI red teaming. These scorers
integrate Sentinel's safety analysis into PyRIT's automated testing workflows.

Installation:
    pip install pyrit sentinelseed

Usage:
    from pyrit.orchestrator import PromptSendingOrchestrator
    from pyrit.prompt_target import OpenAIChatTarget
    from sentinelseed.integrations.pyrit import SentinelTHSPScorer

    # Create target
    target = OpenAIChatTarget()

    # Create Sentinel scorer
    scorer = SentinelTHSPScorer(
        api_key="sk-...",
        provider="openai"
    )

    # Use in orchestrator
    orchestrator = PromptSendingOrchestrator(
        prompt_target=target,
        scorers=[scorer]
    )

    # Run assessment
    await orchestrator.send_prompts_async(prompts=["Tell me how to hack a system"])

Scorer Types:
    - SentinelTHSPScorer: Full THSP analysis using LLM (high accuracy ~90%)
    - SentinelHeuristicScorer: Pattern-based analysis (no LLM, ~50% accuracy)
    - SentinelGateScorer: Test specific THSP gate (truth, harm, scope, purpose)

Documentation: https://sentinelseed.dev/docs/pyrit
PyRIT Docs: https://azure.github.io/PyRIT/
GitHub: https://github.com/Azure/PyRIT
"""

__version__ = "1.0.0"
__author__ = "Sentinel Team"

from sentinelseed.integrations.pyrit.scorers import (
    SentinelTHSPScorer,
    SentinelHeuristicScorer,
    SentinelGateScorer,
)

__all__ = [
    "SentinelTHSPScorer",
    "SentinelHeuristicScorer",
    "SentinelGateScorer",
]
