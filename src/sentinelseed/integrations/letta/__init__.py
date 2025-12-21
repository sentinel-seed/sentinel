"""
Sentinel THSP Integration for Letta (formerly MemGPT)

This package provides Letta-compatible tools and wrappers
for integrating Sentinel's THSP safety validation into Letta agents.

Letta is a platform for building stateful AI agents with persistent,
self-editing memory. This integration adds safety validation at multiple
points: message input, tool execution, and memory operations.

Installation:
    pip install letta-client sentinelseed

Wrappers:
    - SentinelLettaClient: Wrapper that adds safety validation to all operations
    - create_safe_agent: Factory for creating agents with built-in safety

Tools:
    - create_sentinel_tool: Create THSP safety check tool for agents
    - create_memory_guard_tool: Create memory integrity verification tool

Helpers:
    - sentinel_approval_handler: Handler for human-in-the-loop approvals

Usage Example:
    from letta_client import Letta
    from sentinelseed.integrations.letta import (
        SentinelLettaClient,
        create_sentinel_tool,
        create_safe_agent,
    )

    # Method 1: Wrap existing client
    base_client = Letta(api_key="...")
    safe_client = SentinelLettaClient(
        base_client,
        validator_api_key="sk-...",
        mode="block"
    )
    agent = safe_client.agents.create(...)

    # Method 2: Create agent with safety tool
    client = Letta(api_key="...")
    safety_tool = create_sentinel_tool(
        client,
        api_key="sk-...",
        require_approval=True
    )
    agent = client.agents.create(
        tools=[safety_tool.name],
        ...
    )

    # Method 3: Factory function
    agent = create_safe_agent(
        client,
        validator_api_key="sk-...",
        model="openai/gpt-4o-mini",
        memory_blocks=[...],
    )

References:
    - Letta: https://letta.com/
    - Letta Docs: https://docs.letta.com/
    - Sentinel: https://sentinelseed.dev
"""

__version__ = "1.0.0"

# Validation constants
VALID_MODES = ("block", "flag", "log")
VALID_PROVIDERS = ("openai", "anthropic")
DEFAULT_HIGH_RISK_TOOLS = ("send_message", "run_code", "web_search")

# Wrappers
from sentinelseed.integrations.letta.wrappers import (
    SentinelLettaClient,
    SentinelAgentsAPI,
    SentinelMessagesAPI,
    SafetyConfig,
    BlockedResponse,
    SafetyBlockedError,
    create_safe_agent,
)

# Tools
from sentinelseed.integrations.letta.tools import (
    create_sentinel_tool,
    create_memory_guard_tool,
    SentinelSafetyTool,
    MemoryGuardTool,
    SENTINEL_TOOL_SOURCE,
    MEMORY_GUARD_TOOL_SOURCE,
)

# Helpers
from sentinelseed.integrations.letta.helpers import (
    sentinel_approval_handler,
    validate_message,
    validate_tool_call,
    async_validate_message,
    ApprovalDecision,
    ApprovalStatus,
)

__all__ = [
    # Version
    "__version__",
    # Constants
    "VALID_MODES",
    "VALID_PROVIDERS",
    "DEFAULT_HIGH_RISK_TOOLS",
    # Wrappers
    "SentinelLettaClient",
    "SentinelAgentsAPI",
    "SentinelMessagesAPI",
    "SafetyConfig",
    "BlockedResponse",
    "SafetyBlockedError",
    "create_safe_agent",
    # Tools
    "create_sentinel_tool",
    "create_memory_guard_tool",
    "SentinelSafetyTool",
    "MemoryGuardTool",
    "SENTINEL_TOOL_SOURCE",
    "MEMORY_GUARD_TOOL_SOURCE",
    # Helpers
    "sentinel_approval_handler",
    "validate_message",
    "validate_tool_call",
    "async_validate_message",
    "ApprovalDecision",
    "ApprovalStatus",
]
