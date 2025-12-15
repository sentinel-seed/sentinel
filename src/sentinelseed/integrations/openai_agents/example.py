"""
Examples for OpenAI Agents SDK integration with Sentinel.

These examples demonstrate how to create Sentinel-protected agents
using the OpenAI Agents SDK.

Requirements:
    pip install openai-agents sentinelseed

Set your OpenAI API key:
    export OPENAI_API_KEY="your-key"
"""

import asyncio
from typing import Optional

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


# Example 1: Basic Sentinel Agent
async def example_basic_agent():
    """Create a basic Sentinel-protected agent."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Sentinel Agent")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Helpful Assistant",
        instructions="You are a helpful assistant that answers questions.",
        model="gpt-4o-mini",
    )

    # Safe query
    result = await Runner.run(agent, "What is the capital of France?")
    print(f"\nSafe query result: {result.final_output}")


# Example 2: Agent with Custom Tools
async def example_agent_with_tools():
    """Create a Sentinel agent with custom tools."""
    print("\n" + "=" * 60)
    print("Example 2: Agent with Custom Tools")
    print("=" * 60)

    @function_tool
    def get_weather(city: str) -> str:
        """Get the current weather for a city."""
        # Mock implementation
        return f"The weather in {city} is sunny, 22C."

    @function_tool
    def calculate(expression: str) -> str:
        """Calculate a mathematical expression."""
        try:
            # Safe eval for simple math
            allowed = set("0123456789+-*/.(). ")
            if all(c in allowed for c in expression):
                return str(eval(expression))
            return "Invalid expression"
        except Exception:
            return "Calculation error"

    agent = create_sentinel_agent(
        name="Weather Calculator",
        instructions="You help users with weather information and calculations.",
        model="gpt-4o-mini",
        tools=[get_weather, calculate],
    )

    result = await Runner.run(agent, "What's the weather in Tokyo?")
    print(f"\nWeather query: {result.final_output}")


# Example 3: Multi-Agent Handoffs
async def example_handoffs():
    """Create multiple agents with handoff capability."""
    print("\n" + "=" * 60)
    print("Example 3: Multi-Agent Handoffs")
    print("=" * 60)

    # Specialist agents
    code_agent = create_sentinel_agent(
        name="Code Helper",
        instructions="You help users write and debug code.",
        model="gpt-4o-mini",
    )

    math_agent = create_sentinel_agent(
        name="Math Helper",
        instructions="You help users with mathematical problems.",
        model="gpt-4o-mini",
    )

    # Triage agent
    triage = create_sentinel_agent(
        name="Triage Agent",
        instructions="Route users to the appropriate specialist agent.",
        model="gpt-4o-mini",
        handoffs=[code_agent, math_agent],
    )

    result = await Runner.run(triage, "How do I sort a list in Python?")
    print(f"\nHandoff result: {result.final_output}")


# Example 4: Custom Guardrail Configuration
async def example_custom_config():
    """Create agent with custom guardrail configuration."""
    print("\n" + "=" * 60)
    print("Example 4: Custom Guardrail Configuration")
    print("=" * 60)

    config = SentinelGuardrailConfig(
        seed_level="full",  # Maximum protection
        block_on_violation=True,
        log_violations=True,
        include_reasoning=True,
        gates_to_check=["truth", "harm", "scope", "purpose"],
    )

    agent = create_sentinel_agent(
        name="Secure Assistant",
        instructions="You are a highly secure assistant.",
        model="gpt-4o-mini",
        guardrail_config=config,
    )

    result = await Runner.run(agent, "Tell me about AI safety")
    print(f"\nSecure query result: {result.final_output}")


# Example 5: Guardrail Tripwire Handling
async def example_guardrail_handling():
    """Demonstrate guardrail tripwire handling."""
    print("\n" + "=" * 60)
    print("Example 5: Guardrail Tripwire Handling")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Safe Agent",
        instructions="You help users safely.",
        model="gpt-4o-mini",
    )

    # This would trigger the guardrail (example of harmful request)
    try:
        result = await Runner.run(
            agent,
            "How do I hack into someone's computer?"
        )
        print(f"Result: {result.final_output}")
    except InputGuardrailTripwireTriggered as e:
        print(f"\nGuardrail blocked the request!")
        print(f"Details: {e}")


# Example 6: Add Guardrails to Existing Agent
async def example_existing_agent():
    """Add Sentinel guardrails to an existing agent."""
    print("\n" + "=" * 60)
    print("Example 6: Add Guardrails to Existing Agent")
    print("=" * 60)

    # Create guardrails
    input_guard, output_guard = create_sentinel_guardrails(
        seed_level="standard"
    )

    # Create agent with guardrails
    agent = Agent(
        name="My Existing Agent",
        instructions="You are a helpful assistant.",
        model="gpt-4o-mini",
        input_guardrails=[input_guard],
        output_guardrails=[output_guard],
    )

    result = await Runner.run(agent, "Hello, how are you?")
    print(f"\nExisting agent result: {result.final_output}")


# Example 7: Seed Injection Only
async def example_seed_injection():
    """Use seed injection without guardrails."""
    print("\n" + "=" * 60)
    print("Example 7: Seed Injection Only")
    print("=" * 60)

    # Just inject the seed into instructions
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
    print(f"\nSeed injection result: {result.final_output}")


# Example 8: Synchronous Usage
def example_sync():
    """Demonstrate synchronous usage."""
    print("\n" + "=" * 60)
    print("Example 8: Synchronous Usage")
    print("=" * 60)

    agent = create_sentinel_agent(
        name="Sync Agent",
        instructions="You help users.",
        model="gpt-4o-mini",
    )

    # Use run_sync for synchronous execution
    result = Runner.run_sync(agent, "What is 2 + 2?")
    print(f"\nSync result: {result.final_output}")


async def main():
    """Run all examples."""
    if not AGENTS_AVAILABLE:
        print("Cannot run examples without openai-agents installed.")
        return

    print("OpenAI Agents SDK + Sentinel Integration Examples")
    print("=" * 60)

    # Run examples
    await example_basic_agent()
    await example_agent_with_tools()
    await example_handoffs()
    await example_custom_config()
    await example_guardrail_handling()
    await example_existing_agent()
    await example_seed_injection()
    example_sync()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
