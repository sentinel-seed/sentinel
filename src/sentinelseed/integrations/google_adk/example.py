"""Example usage of Sentinel integration with Google ADK.

This module demonstrates various ways to integrate Sentinel's THSP
safety validation with Google's Agent Development Kit.

Prerequisites:
    pip install google-adk sentinelseed

    Set your API key:
    export GOOGLE_API_KEY="your-key"

Examples:
    1. Plugin-based (global guardrails for all agents)
    2. Callback-based (per-agent guardrails)
    3. Multi-agent systems with shared validation
    4. Custom configuration for different use cases
"""

import asyncio
from typing import Any


# =============================================================================
# Example 1: Plugin-based Global Guardrails
# =============================================================================


async def example_plugin_based():
    """Use SentinelPlugin for global guardrails on a Runner.

    The plugin applies to ALL agents, tools, and LLM calls within
    the runner. This is the recommended approach for multi-agent
    systems where you want consistent safety across all components.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import SentinelPlugin

    # Create a basic agent
    agent = LlmAgent(
        name="Assistant",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
    )

    # Create Sentinel plugin with default settings
    plugin = SentinelPlugin(
        seed_level="standard",
        block_on_failure=True,
        validate_inputs=True,
        validate_outputs=True,
        validate_tools=True,
    )

    # Create runner with the plugin
    session_service = InMemorySessionService()
    runner = Runner(
        agent=agent,
        plugins=[plugin],
        session_service=session_service,
    )

    # Run the agent - all inputs/outputs will be validated
    print("Running with SentinelPlugin...")
    response = await runner.run("Hello! How can you help me today?")
    print(f"Response: {response}")

    # Check validation statistics
    stats = plugin.get_stats()
    print(f"\nValidation Stats:")
    print(f"  Total validations: {stats['total_validations']}")
    print(f"  Allowed: {stats['allowed_count']}")
    print(f"  Blocked: {stats['blocked_count']}")


# =============================================================================
# Example 2: Callback-based Per-Agent Guardrails
# =============================================================================


async def example_callback_based():
    """Use callback functions for specific agent validation.

    This approach gives you fine-grained control over which agents
    have guardrails and what type of validation they perform.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import (
        create_before_model_callback,
        create_after_model_callback,
    )

    # Create callbacks for input and output validation
    input_guardrail = create_before_model_callback(
        seed_level="standard",
        block_on_failure=True,
        blocked_message="I cannot process that request.",
    )

    output_guardrail = create_after_model_callback(
        seed_level="standard",
        block_on_failure=True,
        blocked_message="I cannot provide that response.",
    )

    # Create agent with guardrails attached
    agent = LlmAgent(
        name="SafeAssistant",
        model="gemini-2.0-flash",
        instruction="You are a helpful and safe assistant.",
        before_model_callback=input_guardrail,
        after_model_callback=output_guardrail,
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    print("Running with callback-based guardrails...")
    response = await runner.run("What's the weather like today?")
    print(f"Response: {response}")


# =============================================================================
# Example 3: All Callbacks via Factory
# =============================================================================


async def example_all_callbacks():
    """Use create_sentinel_callbacks for quick setup.

    This is a convenience function that creates all four callback
    types at once, ready to unpack into an LlmAgent constructor.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import create_sentinel_callbacks

    # Create all callbacks at once
    callbacks = create_sentinel_callbacks(
        seed_level="standard",
        block_on_failure=True,
        fail_closed=False,
    )

    # Create agent by unpacking callbacks
    agent = LlmAgent(
        name="FullyProtectedAgent",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
        **callbacks,  # Unpacks all callback functions
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    print("Running with all callbacks...")
    response = await runner.run("Help me write a poem.")
    print(f"Response: {response}")


# =============================================================================
# Example 4: Security-Critical Configuration
# =============================================================================


async def example_security_critical():
    """Configure for security-critical applications.

    For high-security environments, use fail_closed=True to block
    content when validation encounters errors or timeouts.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import SentinelPlugin

    # Create security-focused plugin
    plugin = SentinelPlugin(
        seed_level="full",           # Maximum safety
        block_on_failure=True,       # Block unsafe content
        fail_closed=True,            # Block on errors/timeouts
        max_text_size=50000,         # 50KB limit
        validation_timeout=10.0,     # 10 second timeout
        log_violations=True,         # Track violations
        blocked_message="This request has been blocked for security reasons.",
    )

    agent = LlmAgent(
        name="SecureAgent",
        model="gemini-2.0-flash",
        instruction="You are a security-conscious assistant.",
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, plugins=[plugin], session_service=session_service)

    print("Running with security-critical configuration...")
    try:
        response = await runner.run("Process this sensitive request.")
        print(f"Response: {response}")
    finally:
        # Review any violations
        violations = plugin.get_violations()
        if violations:
            print(f"\n⚠️ Recorded {len(violations)} violation(s)")
            for v in violations[:3]:
                print(f"  - {v['risk_level']}: {v['concerns'][:2]}")


# =============================================================================
# Example 5: Multi-Agent with Different Validation
# =============================================================================


async def example_multi_agent():
    """Configure different validation for different agents.

    In multi-agent systems, you may want different safety levels
    for different agents based on their role and capabilities.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent, SequentialAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import (
        create_before_model_callback,
        create_sentinel_callbacks,
    )

    # User-facing agent: strict validation
    user_agent = LlmAgent(
        name="UserAgent",
        model="gemini-2.0-flash",
        instruction="You handle user interactions.",
        **create_sentinel_callbacks(
            seed_level="full",
            block_on_failure=True,
        ),
    )

    # Internal agent: lighter validation (trusted context)
    internal_agent = LlmAgent(
        name="InternalAgent",
        model="gemini-2.0-flash",
        instruction="You process internal data.",
        before_model_callback=create_before_model_callback(
            seed_level="minimal",  # Lighter validation
            block_on_failure=False,  # Warn but allow
        ),
    )

    # Create sequential workflow
    workflow = SequentialAgent(
        name="Workflow",
        sub_agents=[user_agent, internal_agent],
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=workflow, session_service=session_service)

    print("Running multi-agent with different validation levels...")
    response = await runner.run("Process this multi-step request.")
    print(f"Response: {response}")


# =============================================================================
# Example 6: With Custom Tools
# =============================================================================


def create_search_tool():
    """Create a simple search tool for demonstration."""
    def search(query: str, max_results: int = 5) -> dict[str, Any]:
        """Search for information.

        Args:
            query: The search query.
            max_results: Maximum number of results.

        Returns:
            Search results.
        """
        return {
            "results": [
                {"title": f"Result {i}", "snippet": f"Content for {query}"}
                for i in range(min(max_results, 3))
            ]
        }

    return search


async def example_with_tools():
    """Validate tool arguments and results.

    Tool validation prevents misuse of dangerous tools and
    filters potentially harmful tool outputs.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import (
        create_before_tool_callback,
        create_after_tool_callback,
        create_before_model_callback,
    )

    # Create tool callbacks
    tool_input_guard = create_before_tool_callback(
        seed_level="standard",
        block_on_failure=True,
    )

    tool_output_guard = create_after_tool_callback(
        seed_level="standard",
        block_on_failure=True,
    )

    # Create agent with tool and guardrails
    agent = LlmAgent(
        name="ToolAgent",
        model="gemini-2.0-flash",
        instruction="You can search for information.",
        tools=[create_search_tool()],
        before_model_callback=create_before_model_callback(seed_level="standard"),
        before_tool_callback=tool_input_guard,
        after_tool_callback=tool_output_guard,
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, session_service=session_service)

    print("Running with tool validation...")
    response = await runner.run("Search for Python tutorials.")
    print(f"Response: {response}")


# =============================================================================
# Example 7: Monitoring and Statistics
# =============================================================================


async def example_monitoring():
    """Monitor validation statistics and violations.

    Track validation metrics for observability, debugging,
    and compliance reporting.
    """
    try:
        from google.adk.runners import Runner
        from google.adk.agents import LlmAgent
        from google.adk.sessions import InMemorySessionService
    except ImportError:
        print("Google ADK not installed. Install with: pip install google-adk")
        return

    from sentinelseed.integrations.google_adk import SentinelPlugin

    plugin = SentinelPlugin(
        seed_level="standard",
        block_on_failure=True,
        log_violations=True,
    )

    agent = LlmAgent(
        name="MonitoredAgent",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
    )

    session_service = InMemorySessionService()
    runner = Runner(agent=agent, plugins=[plugin], session_service=session_service)

    # Run multiple requests
    requests = [
        "What is the capital of France?",
        "Write a poem about nature.",
        "Explain quantum computing.",
    ]

    print("Running multiple requests with monitoring...")
    for request in requests:
        try:
            await runner.run(request)
        except Exception as e:
            print(f"Error: {e}")

    # Print statistics
    stats = plugin.get_stats()
    print("\n📊 Validation Statistics:")
    print(f"  Total validations: {stats['total_validations']}")
    print(f"  Allowed: {stats['allowed_count']}")
    print(f"  Blocked: {stats['blocked_count']}")
    print(f"  Timeouts: {stats['timeout_count']}")
    print(f"  Errors: {stats['error_count']}")
    print(f"  Avg time: {stats['avg_validation_time_ms']:.2f}ms")

    print("\n📈 Gate Failures:")
    for gate, count in stats['gate_failures'].items():
        if count > 0:
            print(f"  {gate}: {count}")

    # Check for violations
    violations = plugin.get_violations()
    if violations:
        print(f"\n⚠️ Violations ({len(violations)}):")
        for v in violations[:5]:
            print(f"  - [{v['risk_level']}] {', '.join(v['concerns'][:2])}")


# =============================================================================
# Main
# =============================================================================


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Google ADK + Sentinel Integration Examples")
    print("=" * 60)

    examples = [
        ("Plugin-based Global Guardrails", example_plugin_based),
        ("Callback-based Per-Agent Guardrails", example_callback_based),
        ("All Callbacks via Factory", example_all_callbacks),
        ("Security-Critical Configuration", example_security_critical),
        ("Multi-Agent with Different Validation", example_multi_agent),
        ("With Custom Tools", example_with_tools),
        ("Monitoring and Statistics", example_monitoring),
    ]

    for i, (name, example) in enumerate(examples, 1):
        print(f"\n{'='*60}")
        print(f"Example {i}: {name}")
        print("=" * 60)

        try:
            await example()
        except Exception as e:
            print(f"Example failed: {e}")

        print()


if __name__ == "__main__":
    asyncio.run(main())
