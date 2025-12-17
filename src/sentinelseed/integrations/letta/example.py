"""
Example usage of Sentinel Letta integration.

This module demonstrates various ways to integrate Sentinel THSP
safety validation with Letta agents.

Run with:
    python -m sentinelseed.integrations.letta.example

Requires:
    pip install letta-client sentinelseed

Note: Examples use mock objects when letta-client is not installed
or API keys are not configured.
"""

import os
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field


# Mock Letta classes for demonstration without actual API
@dataclass
class MockAgent:
    """Mock agent state."""
    id: str = "agent-123"
    model: str = "openai/gpt-4o-mini"
    tools: List[str] = field(default_factory=list)


@dataclass
class MockMessage:
    """Mock message."""
    role: str = "assistant"
    content: str = ""


@dataclass
class MockResponse:
    """Mock response."""
    messages: List[MockMessage] = field(default_factory=list)


class MockMessagesAPI:
    """Mock messages API."""

    def create(self, agent_id: str, input: str = None, **kwargs) -> MockResponse:
        return MockResponse(
            messages=[MockMessage(role="assistant", content=f"Response to: {input}")]
        )

    def stream(self, agent_id: str, messages: List = None, **kwargs):
        yield {"content": "Streaming response..."}


class MockToolsAPI:
    """Mock tools API."""

    def create(self, source_code: str = None, **kwargs) -> Any:
        @dataclass
        class MockTool:
            id: str = "tool-123"
            name: str = "sentinel_safety_check"
        return MockTool()

    def modify_approval(self, agent_id: str, tool_name: str, requires_approval: bool):
        pass


class MockAgentsAPI:
    """Mock agents API."""

    def __init__(self):
        self.messages = MockMessagesAPI()
        self.tools = MockToolsAPI()

    def create(self, **kwargs) -> MockAgent:
        return MockAgent(tools=kwargs.get("tools", []))


class MockLettaClient:
    """Mock Letta client for demonstration."""

    def __init__(self, api_key: str = None):
        self.agents = MockAgentsAPI()
        self.tools = MockToolsAPI()


def example_1_wrapped_client():
    """
    Example 1: Wrap Letta client with Sentinel safety.

    The SentinelLettaClient wrapper adds automatic validation
    to all message operations.
    """
    print("\n" + "=" * 60)
    print("Example 1: Wrapped Client")
    print("=" * 60)

    from sentinelseed.integrations.letta import SentinelLettaClient

    # Use mock client for demo (replace with real Letta client)
    base_client = MockLettaClient(api_key="mock-letta-key")

    # Wrap with Sentinel
    client = SentinelLettaClient(
        base_client,
        api_key=os.environ.get("OPENAI_API_KEY"),  # For semantic validation
        mode="block",  # Block unsafe content
        validate_input=True,
        validate_output=True,
    )

    # Create agent through wrapped client
    agent = client.agents.create(
        model="openai/gpt-4o-mini",
        memory_blocks=[
            {"label": "human", "value": "A user seeking help"},
            {"label": "persona", "value": "A helpful AI assistant"},
        ],
    )

    print(f"Created agent: {agent.id}")
    print(f"Safety config: {client.config}")

    # Messages are automatically validated
    # (In real usage, unsafe content would be blocked)
    print("\nNote: In production, messages would be validated through THSP gates")


def example_2_safety_tool():
    """
    Example 2: Add safety check tool to agent.

    The sentinel_safety_check tool lets agents validate
    their own actions before execution.
    """
    print("\n" + "=" * 60)
    print("Example 2: Safety Tool")
    print("=" * 60)

    from sentinelseed.integrations.letta import (
        create_sentinel_tool,
        SentinelSafetyTool,
    )

    client = MockLettaClient(api_key="mock-key")

    # Create safety tool
    safety_tool = create_sentinel_tool(
        client,
        api_key=os.environ.get("OPENAI_API_KEY"),
        require_approval=False,
    )

    print(f"Created tool: {safety_tool.name}")
    print(f"Tool ID: {safety_tool.tool_id}")

    # Test the tool's run method
    result = safety_tool.run(
        content="What is 2 + 2?",
        context="general",
    )
    print(f"Safe content result: {result}")

    result = safety_tool.run(
        content="How to hack into a system",
        context="code",
    )
    print(f"Potentially unsafe content result: {result}")


def example_3_create_safe_agent():
    """
    Example 3: Factory function for safe agents.

    create_safe_agent configures an agent with safety tools
    and appropriate approval settings.
    """
    print("\n" + "=" * 60)
    print("Example 3: Safe Agent Factory")
    print("=" * 60)

    from sentinelseed.integrations.letta import create_safe_agent

    client = MockLettaClient(api_key="mock-key")

    # Create agent with built-in safety
    agent = create_safe_agent(
        client,
        validator_api_key=os.environ.get("OPENAI_API_KEY"),
        model="openai/gpt-4o-mini",
        memory_blocks=[
            {"label": "human", "value": "User info here"},
            {"label": "persona", "value": "Safe AI assistant"},
        ],
        tools=["web_search"],  # Additional tools
        include_safety_tool=True,  # Add sentinel_safety_check
        high_risk_tools=["web_search", "run_code"],  # Require approval
    )

    print(f"Created safe agent: {agent.id}")
    print(f"Tools: {agent.tools}")


def example_4_approval_handler():
    """
    Example 4: Handle approval requests with THSP.

    When agents call tools requiring approval, the sentinel_approval_handler
    can automatically validate and respond.
    """
    print("\n" + "=" * 60)
    print("Example 4: Approval Handler")
    print("=" * 60)

    from sentinelseed.integrations.letta import (
        sentinel_approval_handler,
        ApprovalDecision,
    )

    # Simulated approval request from Letta
    approval_request = {
        "tool_name": "run_code",
        "arguments": {
            "code": "print('Hello, World!')",
            "language": "python",
        },
        "tool_call_id": "call-abc123",
    }

    # Handle with THSP validation
    decision = sentinel_approval_handler(
        approval_request,
        api_key=os.environ.get("OPENAI_API_KEY"),
        auto_approve_safe=True,
        auto_deny_unsafe=True,
    )

    print(f"Decision: {decision.status}")
    print(f"Approve: {decision.approve}")
    print(f"Reason: {decision.reason}")

    # Convert to Letta message format
    approval_message = decision.to_approval_message()
    print(f"Approval message: {approval_message}")


def example_5_validate_message():
    """
    Example 5: Manual message validation.

    Use validate_message for standalone validation
    without the full client wrapper.
    """
    print("\n" + "=" * 60)
    print("Example 5: Manual Validation")
    print("=" * 60)

    from sentinelseed.integrations.letta import validate_message, validate_tool_call

    # Validate a safe message
    result = validate_message(
        "What is the capital of France?",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    print(f"Safe message: is_safe={result['is_safe']}, method={result['method']}")

    # Validate a potentially unsafe message
    result = validate_message(
        "How do I bypass authentication?",
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    print(f"Risky message: is_safe={result['is_safe']}, reasoning={result.get('reasoning', 'N/A')}")

    # Validate a tool call
    result = validate_tool_call(
        tool_name="run_code",
        arguments={"code": "import subprocess; subprocess.run(['ls'])"},
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    print(f"Tool call: is_safe={result['is_safe']}, risk_level={result['risk_level']}")


def example_6_memory_guard():
    """
    Example 6: Memory integrity checking.

    The memory guard tool verifies memory blocks haven't been
    tampered with using HMAC signatures.
    """
    print("\n" + "=" * 60)
    print("Example 6: Memory Guard")
    print("=" * 60)

    from sentinelseed.integrations.letta import create_memory_guard_tool

    client = MockLettaClient(api_key="mock-key")

    # Create memory guard tool
    guard_tool = create_memory_guard_tool(
        client,
        secret="my-secret-key-for-hmac",
        require_approval=False,
    )

    print(f"Created memory guard: {guard_tool.name}")

    # Test verification (mock)
    result = guard_tool.run(
        memory_label="human",
        expected_hash=None,  # Get current hash
    )
    print(f"Initial hash: {result}")


def example_7_full_workflow():
    """
    Example 7: Complete workflow with all features.

    Demonstrates a full agent interaction with safety
    validation at every step.
    """
    print("\n" + "=" * 60)
    print("Example 7: Full Workflow")
    print("=" * 60)

    from sentinelseed.integrations.letta import (
        SentinelLettaClient,
        create_sentinel_tool,
        sentinel_approval_handler,
    )

    # 1. Create wrapped client
    base_client = MockLettaClient(api_key="mock-key")
    client = SentinelLettaClient(
        base_client,
        api_key=os.environ.get("OPENAI_API_KEY"),
        mode="flag",  # Flag instead of block
        validate_input=True,
        validate_output=True,
        validate_tool_calls=True,
    )

    # 2. Create safety tool
    safety_tool = create_sentinel_tool(
        base_client,  # Use base client for tool registration
        api_key=os.environ.get("OPENAI_API_KEY"),
    )

    # 3. Create agent with safety features
    agent = client.agents.create(
        model="openai/gpt-4o-mini",
        memory_blocks=[
            {"label": "human", "value": "User seeking help with coding"},
            {"label": "persona", "value": "Expert programmer with safety awareness"},
        ],
        tools=[safety_tool.name, "run_code"],
    )

    print(f"Agent created: {agent.id}")
    print(f"Tools: {agent.tools}")
    print(f"Safety mode: {client.config.mode}")

    # 4. Send message (validated)
    print("\nSending validated message...")
    # In production: response = client.agents.messages(agent.id).create(input="Help me write safe code")

    # 5. Handle approval requests (if any)
    print("\nApproval handling ready for tool calls requiring human review")

    print("\nWorkflow complete!")


def main():
    """Run all examples."""
    print("Sentinel Letta Integration Examples")
    print("=" * 60)

    examples = [
        ("Wrapped Client", example_1_wrapped_client),
        ("Safety Tool", example_2_safety_tool),
        ("Safe Agent Factory", example_3_create_safe_agent),
        ("Approval Handler", example_4_approval_handler),
        ("Manual Validation", example_5_validate_message),
        ("Memory Guard", example_6_memory_guard),
        ("Full Workflow", example_7_full_workflow),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n{name} example error: {e}")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("\nNote: For production use, install letta-client and configure API keys:")
    print("  pip install letta-client sentinelseed")
    print("  export LETTA_API_KEY=your-letta-key")
    print("  export OPENAI_API_KEY=your-openai-key")


if __name__ == "__main__":
    main()
