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
client.agents.messages(agent.id).create(
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

> **Note:** The `MemoryGuardTool` provides HMAC-based memory integrity verification.
> It uses the core `MemoryIntegrityChecker` to sign and verify memory blocks,
> detecting tampering attempts. The tool can register memory content, retrieve
> hashes, and verify content against expected hashes.

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
    require_approval=False,# Require human approval
    name="sentinel_safety_check",  # Tool name
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

### async_validate_message

Async version of validate_message for use in async contexts:

```python
from sentinelseed.integrations.letta import async_validate_message

# In async context
result = await async_validate_message(
    "Check this content",
    api_key="your-key"
)
# Returns same format as validate_message
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

## Constants

```python
from sentinelseed.integrations.letta import (
    VALID_MODES,            # ("block", "flag", "log")
    VALID_PROVIDERS,        # ("openai", "anthropic")
    DEFAULT_HIGH_RISK_TOOLS,# ("send_message", "run_code", "web_search")
)
```

## Configuration Classes

### SafetyConfig

Internal configuration class used by SentinelLettaClient:

```python
from sentinelseed.integrations.letta import SafetyConfig

config = SafetyConfig(
    api_key="...",
    provider="openai",
    model=None,
    mode="block",
    validate_input=True,
    validate_output=True,
    validate_tool_calls=True,
)
```

### ApprovalDecision

Returned by sentinel_approval_handler:

```python
from sentinelseed.integrations.letta import ApprovalDecision

decision = ApprovalDecision(
    status="approved",  # approved, denied, pending
    reasoning="Content passed all THSP gates",
    tool_call_id="call-123",
)

# Convert to Letta approval message
message = decision.to_approval_message()
```

## Exceptions

| Exception | Description |
|-----------|-------------|
| `SafetyBlockedError` | Raised when content is blocked in block mode |

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

## Known Limitations

1. **Streaming output validation** - Output validation is not possible during
   streaming. Use `create()` instead of `stream()` for full validation.

2. **Semantic validation requires API key** - Without an OpenAI or Anthropic
   API key, only heuristic validation is available.

3. **Provider support** - Currently supports `openai` and `anthropic` providers only.

4. **Memory verification scope** - MemoryGuardTool verifies content registered
   through the tool. External modifications to Letta's memory blocks need to be
   re-registered for verification.

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
