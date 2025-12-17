# Sentinel Integration for Letta (MemGPT)

Integrate Sentinel THSP safety validation with [Letta](https://letta.com/) agents.

Letta (formerly MemGPT) is a platform for building stateful AI agents with persistent, self-editing memory. This integration adds safety validation at multiple points: message input, tool execution, and memory operations.

## Installation

```bash
pip install letta-client sentinelseed
```

## Quick Start

### Method 1: Wrapped Client

Wrap your Letta client to add automatic safety validation:

```python
from letta_client import Letta
from sentinelseed.integrations.letta import SentinelLettaClient

# Create base client
base = Letta(api_key="your-letta-key")

# Wrap with Sentinel
client = SentinelLettaClient(
    base,
    api_key="your-openai-key",  # For semantic validation
    mode="block",  # block, flag, or log
)

# Create agent - messages are automatically validated
agent = client.agents.create(
    model="openai/gpt-4o-mini",
    memory_blocks=[
        {"label": "human", "value": "User info"},
        {"label": "persona", "value": "AI assistant"},
    ],
)

# Messages are validated through THSP gates
response = client.agents.messages(agent.id).create(
    input="Hello, how are you?"
)
```

### Method 2: Safety Tool

Add a safety check tool that agents can invoke:

```python
from letta_client import Letta
from sentinelseed.integrations.letta import create_sentinel_tool

client = Letta(api_key="your-key")

# Create and register safety tool
tool = create_sentinel_tool(
    client,
    api_key="your-openai-key",
    require_approval=True,  # Require human approval
)

# Create agent with safety tool
agent = client.agents.create(
    model="openai/gpt-4o-mini",
    tools=[tool.name],
    memory_blocks=[...],
)
```

### Method 3: Safe Agent Factory

Create agents with built-in safety features:

```python
from letta_client import Letta
from sentinelseed.integrations.letta import create_safe_agent

client = Letta(api_key="your-key")

# Create agent with safety tools and approval settings
agent = create_safe_agent(
    client,
    validator_api_key="your-openai-key",
    model="openai/gpt-4o-mini",
    memory_blocks=[
        {"label": "human", "value": "User info"},
        {"label": "persona", "value": "Safe AI assistant"},
    ],
    tools=["web_search"],
    include_safety_tool=True,  # Add sentinel_safety_check
    high_risk_tools=["web_search", "run_code"],  # Require approval
)
```

## Features

### Message Validation

Automatically validate messages through THSP gates:

- **Input validation**: Check user messages before processing
- **Output validation**: Check agent responses before returning
- **Configurable modes**: block, flag, or log

### Approval Handler

Handle tool approval requests with THSP validation:

```python
from sentinelseed.integrations.letta import sentinel_approval_handler

# When agent requests approval for a tool call
decision = sentinel_approval_handler(
    approval_request={
        "tool_name": "run_code",
        "arguments": {"code": "print('hello')"},
        "tool_call_id": "call-123",
    },
    api_key="your-openai-key",
    auto_approve_safe=True,
    auto_deny_unsafe=True,
)

# Send decision back to agent
client.agents.messages.create(
    agent_id=agent.id,
    messages=[decision.to_approval_message()]
)
```

### Memory Integrity

Verify memory blocks haven't been tampered with:

```python
from sentinelseed.integrations.letta import create_memory_guard_tool

guard = create_memory_guard_tool(
    client,
    secret="your-hmac-secret",
)

# Add to agent
agent = client.agents.create(
    tools=[guard.name],
    ...
)
```

## API Reference

### SentinelLettaClient

Main wrapper for Letta client with safety features.

```python
SentinelLettaClient(
    client,                    # Base Letta client
    api_key=None,              # API key for semantic validation
    provider="openai",         # LLM provider
    model=None,                # Model for validation
    mode="block",              # block, flag, or log
    validate_input=True,       # Validate user messages
    validate_output=True,      # Validate agent responses
    validate_tool_calls=True,  # Enable approval for risky tools
    memory_integrity=False,    # Enable HMAC verification
    memory_secret=None,        # Secret for HMAC
    high_risk_tools=None,      # Tools requiring extra validation
)
```

### create_sentinel_tool

Create a safety check tool for agents:

```python
tool = create_sentinel_tool(
    client,                # Letta client
    api_key=None,          # API key for validation
    provider="openai",     # LLM provider
    model=None,            # Model for validation
    require_approval=False # Require human approval
)
```

### create_safe_agent

Factory function for creating safe agents:

```python
agent = create_safe_agent(
    client,                      # Letta client
    validator_api_key=None,      # API key for validation
    validator_provider="openai", # LLM provider
    model="openai/gpt-4o-mini",  # Agent model
    embedding="openai/text-embedding-3-small",
    memory_blocks=None,          # Custom memory blocks
    tools=None,                  # Additional tools
    include_safety_tool=True,    # Add sentinel_safety_check
    safety_tool_name="sentinel_safety_check",
    high_risk_tools=None,        # Tools requiring approval
)
```

### validate_message / validate_tool_call

Standalone validation functions:

```python
from sentinelseed.integrations.letta import validate_message, validate_tool_call

# Validate a message
result = validate_message(
    "How do I bypass security?",
    api_key="your-key"
)
# result: {"is_safe": False, "gates": {...}, "reasoning": "..."}

# Validate a tool call
result = validate_tool_call(
    tool_name="run_code",
    arguments={"code": "rm -rf /"},
    api_key="your-key"
)
# result: {"is_safe": False, "risk_level": "high", ...}
```

## THSP Gates

The integration validates content through four gates:

| Gate | Purpose |
|------|---------|
| **Truth** | Is the content factually accurate? |
| **Harm** | Could this cause harm to people? |
| **Scope** | Is this within appropriate boundaries? |
| **Purpose** | Does this serve a legitimate benefit? |

All four gates must pass for content to be considered safe.

## Configuration Options

### Validation Modes

- **block**: Prevent unsafe content from being processed
- **flag**: Allow but add safety metadata
- **log**: Only log warnings, don't interfere

### High-Risk Tools

Default tools considered high-risk:
- `run_code` - Code execution
- `web_search` - External web access
- `send_message` - Agent messaging

## Examples

Run the examples:

```bash
python -m sentinelseed.integrations.letta.example
```

## Links

- [Letta Documentation](https://docs.letta.com/)
- [Letta Python SDK](https://pypi.org/project/letta-client/)
- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [THSP Protocol](https://sentinelseed.dev/docs/thsp)
