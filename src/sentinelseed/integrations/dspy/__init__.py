"""
Sentinel THSP Integration for DSPy

This package provides DSPy-compatible modules, signatures, and tools
for integrating Sentinel's THSP safety validation into DSPy pipelines.

DSPy is Stanford's framework for programming language models through
declarative specifications rather than manual prompt engineering.

Installation:
    pip install dspy sentinelseed

Modules:
    - SentinelGuard: Wrapper that validates any DSPy module's output
    - SentinelPredict: Predict with built-in THSP validation
    - SentinelChainOfThought: ChainOfThought with THSP validation

Signatures:
    - THSPCheckSignature: Full THSP validation signature
    - SafetyFilterSignature: Content filtering signature
    - ContentClassificationSignature: Risk classification signature

Tools:
    - create_sentinel_tool: Create safety check tool for ReAct
    - create_content_filter_tool: Create content filter tool
    - create_gate_check_tool: Create single-gate check tool

Usage Example:
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard, SentinelPredict

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Method 1: Wrap existing module
    base = dspy.ChainOfThought("question -> answer")
    safe_module = SentinelGuard(
        base,
        api_key="sk-...",
        mode="block"
    )
    result = safe_module(question="What is 2+2?")

    # Method 2: Use SentinelPredict directly
    predictor = SentinelPredict(
        "question -> answer",
        api_key="sk-...",
        mode="block"
    )
    result = predictor(question="How do I learn Python?")

    # Method 3: Use with ReAct agents
    from sentinelseed.integrations.dspy import create_sentinel_tool

    safety_tool = create_sentinel_tool(api_key="sk-...")
    agent = dspy.ReAct(
        "task -> result",
        tools=[safety_tool]
    )

References:
    - DSPy: https://dspy.ai/
    - DSPy GitHub: https://github.com/stanfordnlp/dspy
    - Sentinel: https://sentinelseed.dev
"""

# Modules
from sentinelseed.integrations.dspy.modules import (
    SentinelGuard,
    SentinelPredict,
    SentinelChainOfThought,
)

# Signatures
from sentinelseed.integrations.dspy.signatures import (
    THSPCheckSignature,
    SafetyFilterSignature,
    ContentClassificationSignature,
    THSP_INSTRUCTIONS,
)

# Tools
from sentinelseed.integrations.dspy.tools import (
    create_sentinel_tool,
    create_content_filter_tool,
    create_gate_check_tool,
)

__all__ = [
    # Modules
    "SentinelGuard",
    "SentinelPredict",
    "SentinelChainOfThought",
    # Signatures
    "THSPCheckSignature",
    "SafetyFilterSignature",
    "ContentClassificationSignature",
    "THSP_INSTRUCTIONS",
    # Tools
    "create_sentinel_tool",
    "create_content_filter_tool",
    "create_gate_check_tool",
]
