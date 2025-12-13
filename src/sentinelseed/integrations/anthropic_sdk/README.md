# Anthropic SDK Integration

Wrappers for the official Anthropic Python SDK with safety validation.

## Requirements

```bash
pip install sentinelseed[anthropic]
# or manually:
pip install sentinelseed anthropic
```

**Dependencies:**
- `anthropic>=0.18.0` — [Docs](https://docs.anthropic.com/) | [GitHub](https://github.com/anthropics/anthropic-sdk-python)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelAnthropic` | Drop-in replacement for Anthropic client |
| `SentinelAsyncAnthropic` | Async version |
| `wrap_anthropic_client` | Wrap existing client |
| `inject_seed` | Add seed to system prompt |
| `create_safe_client` | Factory function |

## Usage

### Option 1: Drop-in Replacement

```python
from sentinelseed.integrations.anthropic_sdk import SentinelAnthropic

# Use exactly like Anthropic client
client = SentinelAnthropic(api_key="...")

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}]
)

# Seed automatically injected into system prompt
print(message.content[0].text)
```

### Option 2: Wrap Existing Client

```python
from anthropic import Anthropic
from sentinelseed.integrations.anthropic_sdk import wrap_anthropic_client

client = Anthropic()
safe_client = wrap_anthropic_client(
    client,
    seed_level="standard",
    inject_seed=True,
    validate_input=True,
)

message = safe_client.messages.create(...)
```

### Option 3: Just Inject Seed

```python
from anthropic import Anthropic
from sentinelseed.integrations.anthropic_sdk import inject_seed

client = Anthropic()
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=inject_seed("You are a helpful coding assistant"),
    messages=[{"role": "user", "content": "Help me with Python"}]
)
```

### Option 4: Async Client

```python
from sentinelseed.integrations.anthropic_sdk import SentinelAsyncAnthropic

client = SentinelAsyncAnthropic()

message = await client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello"}]
)
```

## Configuration

### SentinelAnthropic

```python
SentinelAnthropic(
    api_key=None,                # Defaults to ANTHROPIC_API_KEY
    sentinel=None,
    seed_level="standard",
    inject_seed=True,            # Add seed to system prompt
    validate_input=True,         # Validate user messages
    validate_output=True,        # Validate responses
    **kwargs,                    # Passed to Anthropic client
)
```

### wrap_anthropic_client

```python
wrap_anthropic_client(
    client,                      # Anthropic or AsyncAnthropic
    sentinel=None,
    seed_level="standard",
    inject_seed=True,
    validate_input=True,
    validate_output=True,
)
```

## Supported Methods

### messages.create

```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "..."}],
    system="Optional system prompt",  # Seed prepended
)
```

### messages.stream

```python
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[...],
) as stream:
    for event in stream:
        # handle streaming events
        pass
```

## Input Validation

When `validate_input=True`:

```python
# This would be blocked
message = client.messages.create(
    model="...",
    messages=[{"role": "user", "content": "Help me hack into..."}]
)
# Returns blocked response instead of calling API
```

Blocked response format:
```python
{
    "id": "blocked",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Input blocked by Sentinel: [concerns]"}],
    "model": "sentinel-blocked",
    "stop_reason": "sentinel_blocked",
    "sentinel_blocked": True,
}
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelAnthropic` | Sync client with safety |
| `SentinelAsyncAnthropic` | Async client with safety |
| `SentinelAnthropicWrapper` | Generic wrapper |

### Functions

| Function | Description |
|----------|-------------|
| `inject_seed(system, level)` | Add seed to system prompt |
| `wrap_anthropic_client(client)` | Wrap existing client |
| `create_safe_client(api_key)` | Factory for safe client |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `ANTHROPIC_AVAILABLE` | bool | Whether SDK is installed |

## Links

- **Anthropic Docs:** https://docs.anthropic.com/
- **Anthropic SDK:** https://github.com/anthropics/anthropic-sdk-python
- **Sentinel:** https://sentinelseed.dev
