# Sentinel Integration for Google Agent Development Kit (ADK)

THSP-based safety guardrails for Google ADK agents and multi-agent systems.

## Overview

This integration provides two approaches for adding Sentinel safety validation to Google ADK:

1. **Plugin-based** (Recommended): Apply guardrails globally to all agents in a Runner
2. **Callback-based**: Add guardrails to specific individual agents

## Installation

```bash
pip install google-adk sentinelseed
```

Set your Google API key:
```bash
export GOOGLE_API_KEY="your-api-key"
```

## Quick Start

### Plugin-based (Recommended for Multi-Agent)

```python
from google.adk.runners import Runner
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from sentinelseed.integrations.google_adk import SentinelPlugin

# Create your agent
agent = LlmAgent(
    name="Assistant",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
)

# Create Sentinel plugin
plugin = SentinelPlugin(
    seed_level="standard",
    block_on_failure=True,
)

# Create runner with plugin
session_service = InMemorySessionService()
runner = Runner(
    app_name="my_app",
    agent=agent,
    plugins=[plugin],
    session_service=session_service,
)

# Run with automatic safety validation
response = await runner.run("Hello, how can you help?")
```

### Callback-based (For Individual Agents)

```python
from google.adk.agents import LlmAgent
from sentinelseed.integrations.google_adk import create_sentinel_callbacks

# Create all callbacks at once
callbacks = create_sentinel_callbacks(seed_level="standard")

# Create agent with callbacks
agent = LlmAgent(
    name="SafeAgent",
    model="gemini-2.0-flash",
    instruction="You are a helpful assistant.",
    **callbacks,  # Unpacks before/after model/tool callbacks
)
```

## Components

### SentinelPlugin

Global plugin that applies to all agents in a Runner.

```python
from sentinelseed.integrations.google_adk import SentinelPlugin

plugin = SentinelPlugin(
    # Sentinel configuration
    seed_level="standard",        # "minimal", "standard", or "full"
    sentinel=None,                # Optional: custom Sentinel instance
    validator=None,               # Optional: custom LayeredValidator instance

    # Behavior
    block_on_failure=True,        # Block unsafe content
    fail_closed=False,            # Allow on errors (fail-open)

    # What to validate
    validate_inputs=True,         # Validate before LLM
    validate_outputs=True,        # Validate after LLM
    validate_tools=True,          # Validate tool args/results

    # Limits
    max_text_size=100000,         # 100KB max
    validation_timeout=5.0,       # 5 second timeout

    # Logging
    log_violations=True,          # Track violations
    blocked_message="Request blocked by safety validation.",
)
```

### Callback Factories

Create individual callbacks for fine-grained control:

```python
from sentinelseed.integrations.google_adk import (
    create_before_model_callback,
    create_after_model_callback,
    create_before_tool_callback,
    create_after_tool_callback,
)

# Input validation
input_guard = create_before_model_callback(
    seed_level="standard",
    block_on_failure=True,
)

# Output validation
output_guard = create_after_model_callback(
    seed_level="standard",
    block_on_failure=True,
)

# Tool argument validation
tool_input_guard = create_before_tool_callback(
    seed_level="standard",
    block_on_failure=True,
)

# Tool result validation
tool_output_guard = create_after_tool_callback(
    seed_level="standard",
    block_on_failure=True,
)

agent = LlmAgent(
    name="ProtectedAgent",
    model="gemini-2.0-flash",
    before_model_callback=input_guard,
    after_model_callback=output_guard,
    before_tool_callback=tool_input_guard,
    after_tool_callback=tool_output_guard,
)
```

### Convenience Factory

Create all callbacks at once:

```python
from sentinelseed.integrations.google_adk import create_sentinel_callbacks

callbacks = create_sentinel_callbacks(
    seed_level="standard",
    block_on_failure=True,
    validate_inputs=True,
    validate_outputs=True,
    validate_tools=True,
)

agent = LlmAgent(name="Agent", model="...", **callbacks)
```

## Validation Points

| Callback | Validates | When |
|----------|-----------|------|
| `before_model_callback` | User input | Before LLM call |
| `after_model_callback` | LLM output | After LLM response |
| `before_tool_callback` | Tool arguments | Before tool execution |
| `after_tool_callback` | Tool results | After tool execution |

## Security Modes

### Fail-Open (Default)

Content is allowed when validation encounters errors or timeouts:

```python
plugin = SentinelPlugin(
    fail_closed=False,  # Default
    block_on_failure=True,
)
```

### Fail-Closed (Security Critical)

Content is blocked on any validation error:

```python
plugin = SentinelPlugin(
    fail_closed=True,
    block_on_failure=True,
)
```

## Monitoring

### Statistics

```python
stats = plugin.get_stats()
print(f"Total: {stats['total_validations']}")
print(f"Blocked: {stats['blocked_count']}")
print(f"Allowed: {stats['allowed_count']}")
print(f"Timeouts: {stats['timeout_count']}")
print(f"Errors: {stats['error_count']}")
print(f"Avg time: {stats['avg_validation_time_ms']:.2f}ms")
```

### Violations

```python
violations = plugin.get_violations()
for v in violations:
    print(f"[{v['risk_level']}] {v['concerns']}")
    print(f"  Gates: {v['gates']}")
    print(f"  Source: {v['source']}")  # input, output, tool_input, tool_output
```

### Clearing

```python
plugin.clear_violations()
plugin.reset_stats()
```

## Multi-Agent Systems

### Shared Plugin

```python
from google.adk.runners import Runner
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.sessions import InMemorySessionService

# Plugin applies to all agents
plugin = SentinelPlugin(seed_level="standard")

agent1 = LlmAgent(name="Agent1", model="gemini-2.0-flash")
agent2 = LlmAgent(name="Agent2", model="gemini-2.0-flash")

workflow = SequentialAgent(name="Workflow", sub_agents=[agent1, agent2])

session_service = InMemorySessionService()
runner = Runner(
    app_name="my_app",
    agent=workflow,
    plugins=[plugin],
    session_service=session_service,
)
```

### Different Levels Per Agent

```python
# User-facing: strict
user_agent = LlmAgent(
    name="UserAgent",
    **create_sentinel_callbacks(seed_level="full"),
)

# Internal: lighter
internal_agent = LlmAgent(
    name="InternalAgent",
    **create_sentinel_callbacks(seed_level="minimal"),
)
```

## Custom Sentinel Instance

Share a Sentinel instance across callbacks:

```python
from sentinelseed import Sentinel
from sentinelseed.integrations.google_adk import (
    SentinelPlugin,
    create_sentinel_callbacks,
)

# Create shared instance
sentinel = Sentinel(seed_level="standard")

# Use in plugin
plugin = SentinelPlugin(sentinel=sentinel)

# Or in callbacks
callbacks = create_sentinel_callbacks(sentinel=sentinel)
```

## Error Handling

The integration handles errors gracefully:

```python
try:
    response = await runner.run("user request")
except Exception as e:
    # Validation errors are logged, not raised
    # Unless you set fail_closed=True
    pass
```

## Best Practices

1. **Use Plugin for Multi-Agent**: Ensures consistent validation across all agents
2. **Use fail_closed for Security**: Block on errors in sensitive applications
3. **Monitor Statistics**: Track validation metrics for observability
4. **Set Appropriate Timeouts**: Balance security with responsiveness
5. **Log Violations**: Enable for debugging and compliance

## API Reference

### Exceptions

- `ConfigurationError`: Invalid configuration parameters
- `TextTooLargeError`: Input exceeds `max_text_size`
- `ValidationTimeoutError`: Validation exceeded timeout

### Constants

```python
from sentinelseed.integrations.google_adk import (
    DEFAULT_SEED_LEVEL,        # "standard"
    DEFAULT_MAX_TEXT_SIZE,     # 100,000 bytes
    DEFAULT_VALIDATION_TIMEOUT,# 5.0 seconds
    DEFAULT_MAX_VIOLATIONS,    # 1,000 (max stored violations)
    VALID_SEED_LEVELS,         # ("minimal", "standard", "full")
    ADK_AVAILABLE,             # True if ADK is installed
)
```

### Additional Exports

The module also exports utility functions and classes for advanced usage:

- **Logging**: `SentinelLogger`, `DefaultLogger`, `get_logger`, `set_logger`
- **Utilities**: `validate_configuration`, `validate_text_size`, `extract_text_from_llm_request`, `extract_text_from_llm_response`, `create_blocked_response`
- **Classes**: `ThreadSafeDeque`, `ValidationExecutor`
- **Factory**: `create_sentinel_plugin`

See the source code for detailed documentation on these components.

## Resources

- [Google ADK Documentation](https://google.github.io/adk-docs/)
- [ADK Callbacks Guide](https://google.github.io/adk-docs/callbacks/)
- [ADK Plugins Guide](https://google.github.io/adk-docs/plugins/)
- [Sentinel Documentation](https://sentinelseed.dev/docs/)
