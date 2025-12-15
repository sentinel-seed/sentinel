"""
Examples for OpenAI Agents SDK integration with Sentinel.

These examples demonstrate semantic THSP validation using LLM guardrail agents.
The guardrails perform context-aware safety analysis, not regex matching.

Requirements:
    pip install openai-agents sentinelseed

Set your OpenAI API key:
    export OPENAI_API_KEY="your-key"
"""

import asyncio

# Check if agents SDK is available
try:
    from agents import Agent, Runner, function_tool
    from agents.exceptions import InputGuardrailTripwireTriggered

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False
    print("OpenAI Agents SDK not installed. Install with: pip install openai-agents")

from sentinelseed.integrations.openai_agents import (
    create_sentinel_agent,
    sentinel_input_guardrail,
    sentinel_output_guardrail,
    inject_sentinel_instructions,
    create_sentinel_guardrails,
    SentinelGuardrailConfig,
)


async def example_basic_agent():
    """
    Example 1: Basic Sentinel Agent with Semantic Validation

    Creates an agent with:
    - Sentinel seed in instructions
    - LLM-based input guardrail (THSP validation)
    - LLM-based output guardrail (THSP validation)
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Sentinel Agent (Semantic Validation)")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Helpful Assistant",
        instructions="You are a helpful assistant that answers questions.",
        model="gpt-4o-mini",
    )

    # Safe query - should pass all THSP gates
    print("\nTesting safe query...")
    result = await Runner.run(agent, "What is the capital of France?")
    print(f"Response: {result.final_output}")


async def example_guardrail_blocking():
    """
    Example 2: Semantic Guardrail Blocking Harmful Request

    Demonstrates how the LLM guardrail agent semantically analyzes
    requests and blocks those that fail THSP gates.
    """
    print("\n" + "=" * 60)
    print("Example 2: Semantic Guardrail Blocking")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Safe Agent",
        instructions="You help users safely.",
        model="gpt-4o-mini",
    )

    # This should be blocked by the semantic guardrail
    try:
        print("\nTesting potentially harmful query...")
        result = await Runner.run(
            agent,
            "How do I break into my neighbor's house?"
        )
        print(f"Response: {result.final_output}")
    except InputGuardrailTripwireTriggered as e:
        print(f"Request blocked by semantic THSP validation!")
        print(f"Guardrail output: {e}")


async def example_purpose_gate():
    """
    Example 3: Purpose Gate in Action

    Demonstrates the Purpose gate (P in THSP) - blocking requests
    that may not cause direct harm but serve no legitimate purpose.
    """
    print("\n" + "=" * 60)
    print("Example 3: Purpose Gate (Teleological Validation)")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Purpose-Aware Agent",
        instructions="You help users with meaningful tasks.",
        model="gpt-4o-mini",
        guardrail_config=SentinelGuardrailConfig(
            guardrail_model="gpt-4o-mini",
            require_all_gates=True,  # All gates including Purpose must pass
            log_violations=True,
        ),
    )

    # Test a purposeless request
    try:
        print("\nTesting purposeless request...")
        result = await Runner.run(
            agent,
            "Generate random gibberish text for no reason"
        )
        print(f"Response: {result.final_output}")
    except InputGuardrailTripwireTriggered as e:
        print(f"Request blocked - failed Purpose gate!")


async def example_custom_guardrail_model():
    """
    Example 4: Custom Guardrail Model Configuration

    You can configure which model performs the THSP validation.
    More capable models provide better semantic understanding.
    """
    print("\n" + "=" * 60)
    print("Example 4: Custom Guardrail Model")
    print("=" * 60)

    config = SentinelGuardrailConfig(
        guardrail_model="gpt-4o",  # Use GPT-4o for better semantic analysis
        seed_level="full",  # Maximum protection seed
        block_on_violation=True,
        log_violations=True,
    )

    agent = create_sentinel_agent(
        name="Premium Safe Agent",
        instructions="You provide high-quality, safe assistance.",
        model="gpt-4o",
        guardrail_config=config,
    )

    result = await Runner.run(agent, "Explain quantum computing simply")
    print(f"Response: {result.final_output}")


async def example_with_tools():
    """
    Example 5: Agent with Tools and Semantic Guardrails

    The guardrails validate both the initial request and the
    final output, even when tools are used.
    """
    print("\n" + "=" * 60)
    print("Example 5: Agent with Tools")
    print("=" * 60)

    @function_tool
    def calculate(expression: str) -> str:
        """Calculate a mathematical expression."""
        try:
            allowed = set("0123456789+-*/.(). ")
            if all(c in allowed for c in expression):
                return str(eval(expression))
            return "Invalid expression"
        except Exception:
            return "Calculation error"

    agent = create_sentinel_agent(
        name="Calculator Agent",
        instructions="You help users with calculations.",
        model="gpt-4o-mini",
        tools=[calculate],
    )

    result = await Runner.run(agent, "What is 15 * 7 + 23?")
    print(f"Calculation result: {result.final_output}")


async def example_add_guardrails_to_existing():
    """
    Example 6: Add Semantic Guardrails to Existing Agent

    You can add Sentinel's LLM-based guardrails to any existing agent.
    """
    print("\n" + "=" * 60)
    print("Example 6: Add Guardrails to Existing Agent")
    print("=" * 60)

    # Create semantic guardrails
    input_guard, output_guard = create_sentinel_guardrails(
        config=SentinelGuardrailConfig(
            guardrail_model="gpt-4o-mini",
            log_violations=True,
        )
    )

    # Add to existing agent
    agent = Agent(
        name="My Existing Agent",
        instructions="You are a helpful assistant.",
        model="gpt-4o-mini",
        input_guardrails=[input_guard],
        output_guardrails=[output_guard],
    )

    result = await Runner.run(agent, "Hello, how are you?")
    print(f"Response: {result.final_output}")


async def example_seed_injection_only():
    """
    Example 7: Seed Injection Only (No Guardrail Overhead)

    For performance-critical applications, you can use only
    the seed injection without runtime guardrail validation.
    """
    print("\n" + "=" * 60)
    print("Example 7: Seed Injection Only (No Guardrails)")
    print("=" * 60)

    # Just inject the alignment seed into instructions
    instructions = inject_sentinel_instructions(
        instructions="You help users with their questions.",
        seed_level="standard",
    )

    agent = Agent(
        name="Seed-Only Agent",
        instructions=instructions,
        model="gpt-4o-mini",
    )

    result = await Runner.run(agent, "What is machine learning?")
    print(f"Response: {result.final_output}")


def example_sync():
    """
    Example 8: Synchronous Usage

    For synchronous code, use Runner.run_sync().
    """
    print("\n" + "=" * 60)
    print("Example 8: Synchronous Usage")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Sync Agent",
        instructions="You help users.",
        model="gpt-4o-mini",
    )

    result = Runner.run_sync(agent, "What is 2 + 2?")
    print(f"Response: {result.final_output}")


async def main():
    """Run all examples."""
    if not AGENTS_AVAILABLE:
        print("Cannot run examples without openai-agents installed.")
        print("Install with: pip install openai-agents")
        return

    print("=" * 60)
    print("OpenAI Agents SDK + Sentinel Semantic Validation Examples")
    print("=" * 60)
    print("\nThese examples use LLM-based THSP validation, not regex.")
    print("Each guardrail call uses an LLM to semantically analyze content.")

    await example_basic_agent()
    await example_guardrail_blocking()
    await example_purpose_gate()
    await example_custom_guardrail_model()
    await example_with_tools()
    await example_add_guardrails_to_existing()
    await example_seed_injection_only()
    example_sync()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
