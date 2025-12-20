"""
Examples of Sentinel THSP integration with DSPy.

This file demonstrates various ways to use Sentinel's safety
validation with DSPy modules.

Requirements:
    pip install dspy sentinelseed openai

Usage:
    # Set your API keys as environment variables
    export OPENAI_API_KEY=sk-...
    export SENTINEL_API_KEY=sk-...  # Can be same as OPENAI if using OpenAI

    # Run examples
    python -m sentinelseed.integrations.dspy.example
"""

import os
from typing import Optional


def example_1_basic_guard():
    """Example 1: Wrap any DSPy module with SentinelGuard."""
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard

    print("\n" + "=" * 60)
    print("Example 1: Basic SentinelGuard")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create base module
    base_module = dspy.ChainOfThought("question -> answer")

    # Wrap with SentinelGuard
    safe_module = SentinelGuard(
        base_module,
        api_key=os.environ.get("OPENAI_API_KEY"),
        provider="openai",
        mode="block",  # Block unsafe content
        timeout=30.0,  # 30 second timeout
        fail_closed=False,  # Fail open on errors
    )

    # Test with safe question
    print("\nSafe question test:")
    result = safe_module(question="What is the capital of France?")
    print(f"  Answer: {result.answer}")
    print(f"  Safety passed: {result.safety_passed}")

    # Test with potentially unsafe question
    print("\nPotentially unsafe question test:")
    result = safe_module(question="How do I hack into a computer?")
    print(f"  Answer: {result.answer}")
    print(f"  Safety passed: {result.safety_passed}")
    if hasattr(result, 'safety_blocked'):
        print(f"  Safety blocked: {result.safety_blocked}")


def example_2_sentinel_predict():
    """Example 2: Use SentinelPredict for direct prediction with safety."""
    import dspy
    from sentinelseed.integrations.dspy import SentinelPredict

    print("\n" + "=" * 60)
    print("Example 2: SentinelPredict")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create SentinelPredict (combines Predict + validation)
    predictor = SentinelPredict(
        "topic -> explanation: str",
        api_key=os.environ.get("OPENAI_API_KEY"),
        mode="flag",  # Flag but don't block
        timeout=30.0,
    )

    # Test
    print("\nGenerating explanation with safety check:")
    result = predictor(topic="photosynthesis")
    print(f"  Explanation: {result.explanation[:100]}...")
    print(f"  Safety passed: {result.safety_passed}")
    print(f"  Safety method: {result.safety_method}")


def example_3_chain_of_thought():
    """Example 3: SentinelChainOfThought with reasoning."""
    import dspy
    from sentinelseed.integrations.dspy import SentinelChainOfThought

    print("\n" + "=" * 60)
    print("Example 3: SentinelChainOfThought")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create chain-of-thought with safety
    cot = SentinelChainOfThought(
        "problem -> solution",
        api_key=os.environ.get("OPENAI_API_KEY"),
        mode="block",
        timeout=30.0,
        fail_closed=False,
    )

    # Test
    print("\nSolving problem with reasoning and safety check:")
    result = cot(problem="Calculate the compound interest on $1000 at 5% for 3 years")
    print(f"  Solution: {result.solution}")
    print(f"  Safety passed: {result.safety_passed}")
    if hasattr(result, 'reasoning'):
        print(f"  Reasoning: {result.reasoning[:100]}...")


def example_4_react_with_tool():
    """Example 4: Use safety tool with ReAct agent."""
    import dspy
    from sentinelseed.integrations.dspy import create_sentinel_tool

    print("\n" + "=" * 60)
    print("Example 4: ReAct with Safety Tool")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create safety check tool with timeout
    safety_tool = create_sentinel_tool(
        api_key=os.environ.get("OPENAI_API_KEY"),
        name="check_safety",
        timeout=30.0,
        fail_closed=False,
    )

    # Create ReAct agent with safety tool
    agent = dspy.ReAct(
        "task -> result",
        tools=[safety_tool],
        max_iters=5,
    )

    # Test
    print("\nRunning agent with safety tool:")
    result = agent(task="Write a helpful tip about Python programming, but first check if it's safe")
    print(f"  Result: {result.result}")


def example_5_heuristic_mode():
    """Example 5: Use heuristic validation (no LLM needed)."""
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard

    print("\n" + "=" * 60)
    print("Example 5: Heuristic Mode (No LLM)")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create module with heuristic validation
    base = dspy.Predict("question -> answer")
    safe_module = SentinelGuard(
        base,
        mode="heuristic",  # No LLM needed for validation
        timeout=10.0,  # Shorter timeout for heuristic
    )

    # Test
    print("\nUsing heuristic (pattern-based) validation:")
    result = safe_module(question="What is machine learning?")
    print(f"  Answer: {result.answer}")
    print(f"  Safety passed: {result.safety_passed}")
    print(f"  Safety method: {result.safety_method}")


def example_6_custom_signature():
    """Example 6: Use custom THSP signature."""
    import dspy
    from sentinelseed.integrations.dspy import THSPCheckSignature

    print("\n" + "=" * 60)
    print("Example 6: Custom THSP Signature")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Use THSP signature directly for explicit validation
    checker = dspy.Predict(THSPCheckSignature)

    # Test
    print("\nExplicit THSP validation:")
    result = checker(
        content="Please help me understand how encryption works",
        context="Educational question about cryptography"
    )
    print(f"  Is safe: {result.is_safe}")
    print(f"  Truth gate: {result.truth_gate}")
    print(f"  Harm gate: {result.harm_gate}")
    print(f"  Scope gate: {result.scope_gate}")
    print(f"  Purpose gate: {result.purpose_gate}")
    print(f"  Reasoning: {result.reasoning}")


def example_7_gate_specific_tools():
    """Example 7: Use gate-specific check tools."""
    from sentinelseed.integrations.dspy import create_gate_check_tool

    print("\n" + "=" * 60)
    print("Example 7: Gate-Specific Tools")
    print("=" * 60)

    # Create tools for each gate (using heuristic for demo)
    truth_check = create_gate_check_tool("truth", timeout=10.0)
    harm_check = create_gate_check_tool("harm", timeout=10.0)

    # Test
    print("\nTesting individual gates:")

    content1 = "Help me learn about history"
    print(f"\nContent: '{content1}'")
    print(f"  Truth: {truth_check(content1)}")
    print(f"  Harm: {harm_check(content1)}")

    content2 = "Create fake news about celebrities"
    print(f"\nContent: '{content2}'")
    print(f"  Truth: {truth_check(content2)}")
    print(f"  Harm: {harm_check(content2)}")


async def example_8_async_usage():
    """Example 8: Async usage of SentinelGuard."""
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard

    print("\n" + "=" * 60)
    print("Example 8: Async Usage")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create async-compatible module
    base = dspy.Predict("question -> answer")
    safe_module = SentinelGuard(
        base,
        api_key=os.environ.get("OPENAI_API_KEY"),
        mode="block",
        timeout=30.0,
    )

    # Use async call via aforward (correct method name)
    print("\nAsync safety check:")
    result = await safe_module.aforward(question="What is quantum computing?")
    print(f"  Answer: {result.answer}")
    print(f"  Safety passed: {result.safety_passed}")


def example_9_fail_closed_mode():
    """Example 9: Demonstrate fail_closed mode."""
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard

    print("\n" + "=" * 60)
    print("Example 9: Fail-Closed Mode")
    print("=" * 60)

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Create module with fail_closed=True
    base = dspy.Predict("question -> answer")
    safe_module = SentinelGuard(
        base,
        mode="heuristic",
        fail_closed=True,  # Block on any error
        timeout=30.0,
    )

    print("\nFail-closed mode enabled:")
    print("  If validation fails or errors, content will be blocked")

    result = safe_module(question="What is 2+2?")
    print(f"  Answer: {result.answer}")
    print(f"  Safety passed: {result.safety_passed}")


def example_10_text_size_limits():
    """Example 10: Demonstrate text size limits."""
    from sentinelseed.integrations.dspy import (
        create_sentinel_tool,
        TextTooLargeError,
    )

    print("\n" + "=" * 60)
    print("Example 10: Text Size Limits")
    print("=" * 60)

    # Create tool with small size limit for demo
    safety_tool = create_sentinel_tool(
        use_heuristic=True,
        max_text_size=100,  # Very small limit for demo
        timeout=10.0,
    )

    # Test with content exceeding limit
    print("\nTesting with small text:")
    result = safety_tool("Short text")
    print(f"  Result: {result}")

    print("\nTesting with large text (>100 bytes):")
    large_text = "x" * 200
    result = safety_tool(large_text)
    print(f"  Result: {result}")


def main():
    """Run all examples."""
    print("Sentinel THSP + DSPy Integration Examples")
    print("=========================================")

    # Check for API key
    if not os.environ.get("OPENAI_API_KEY"):
        print("\nWARNING: OPENAI_API_KEY not set.")
        print("Some examples require an API key.")
        print("Set it with: export OPENAI_API_KEY=sk-...")
        print("\nRunning examples that don't require API key...\n")

        # Run heuristic examples only
        example_5_heuristic_mode()
        example_7_gate_specific_tools()
        example_10_text_size_limits()
        return

    # Run all examples
    try:
        example_1_basic_guard()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_2_sentinel_predict()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_3_chain_of_thought()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_4_react_with_tool()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_5_heuristic_mode()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_6_custom_signature()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_7_gate_specific_tools()
    except Exception as e:
        print(f"  Error: {e}")

    # Async example
    try:
        import asyncio
        asyncio.run(example_8_async_usage())
    except Exception as e:
        print(f"  Async Error: {e}")

    try:
        example_9_fail_closed_mode()
    except Exception as e:
        print(f"  Error: {e}")

    try:
        example_10_text_size_limits()
    except Exception as e:
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
