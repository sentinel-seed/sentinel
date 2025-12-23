"""
Sentinel THSP Scorers for Microsoft PyRIT

This package provides scorers for PyRIT (Python Risk Identification Tool)
that evaluate AI responses using the THSP protocol (Truth, Harm, Scope, Purpose).

PyRIT is Microsoft's open-source framework for AI red teaming. These scorers
integrate Sentinel's safety analysis into PyRIT's automated testing workflows.

Requirements:
    - PyRIT >= 0.10.0 (required for _score_piece_async API)

Installation:
    pip install 'pyrit>=0.10.0' sentinelseed

Usage:
    from pyrit.orchestrator import PromptSendingOrchestrator
    from pyrit.prompt_target import OpenAIChatTarget
    from sentinelseed.integrations.pyrit import SentinelTHSPScorer

    # Create target
    target = OpenAIChatTarget()

    # Create Sentinel scorer
    scorer = SentinelTHSPScorer(
        api_key="sk-...",
        provider="openai",
        fail_mode="closed",  # Errors treated as unsafe
    )

    # Use in orchestrator
    orchestrator = PromptSendingOrchestrator(
        prompt_target=target,
        scorers=[scorer]
    )

    # Run assessment
    await orchestrator.send_prompts_async(prompts=["Tell me how to hack a system"])

Scorer Types:
    - SentinelTHSPScorer: Full THSP analysis using LLM (~85% accuracy)
    - SentinelHeuristicScorer: Pattern-based analysis, no LLM (~45% accuracy)
    - SentinelGateScorer: Test specific THSP gate (truth, harm, scope, purpose)

Configuration:
    - fail_mode: 'closed' (errors=unsafe), 'open' (errors=safe), 'raise' (errors throw)
    - max_content_length: Limit content size (default: 100,000 chars)

References:
    - Sentinel: https://sentinelseed.dev
    - PyRIT Docs: https://azure.github.io/PyRIT/
    - PyRIT GitHub: https://github.com/Azure/PyRIT
"""

__version__ = "2.14.0"
__author__ = "Sentinel Team"

from sentinelseed.integrations.pyrit.scorers import (
    SentinelTHSPScorer,
    SentinelHeuristicScorer,
    SentinelGateScorer,
    FailMode,
    ConfidenceLevel,
    MAX_CONTENT_LENGTH,
)

__all__ = [
    "SentinelTHSPScorer",
    "SentinelHeuristicScorer",
    "SentinelGateScorer",
    "FailMode",
    "ConfidenceLevel",
    "MAX_CONTENT_LENGTH",
]
