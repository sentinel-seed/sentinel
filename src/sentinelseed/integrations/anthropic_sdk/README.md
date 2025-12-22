# Anthropic SDK Integration

Wrappers for the official Anthropic Python SDK with THSP safety validation.

## Requirements

```bash
pip install sentinelseed[anthropic]
# or manually:
pip install sentinelseed anthropic
```

**Dependencies:**
- `anthropic>=0.18.0`: [Docs](https://docs.anthropic.com/) | [GitHub](https://github.com/anthropics/anthropic-sdk-python)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelAnthropic` | Drop-in replacement for Anthropic client |
| `SentinelAsyncAnthropic` | Async version |
| `SentinelAnthropicWrapper` | Wrap existing client instance |
| `wrap_anthropic_client` | Function to wrap existing client |
| `inject_seed` | Add seed to system prompt (no SDK required) |
| `create_safe_client` | Factory function |

## Usage

### Option 1: Drop-in Replacement (Recommended)

```python
from sentinelseed.integrations.anthropic_sdk import SentinelAnthropic

# Use exactly like Anthropic client
client = SentinelAnthropic(api_key="...")

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "Hello, Claude"}]
)

# Seed automatically injected, input validated
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
    enable_seed_injection=True,
    validate_input=True,
)

message = safe_client.messages.create(...)
```

### Option 3: Just Inject Seed (No Runtime Validation)

```python
from anthropic import Anthropic
from sentinelseed.integrations.anthropic_sdk import inject_seed

# inject_seed does NOT require anthropic SDK to be installed
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

### Option 5: Direct Wrapper Class

```python
from anthropic import Anthropic, AsyncAnthropic
from sentinelseed.integrations.anthropic_sdk import SentinelAnthropicWrapper

# Wrap sync client
client = Anthropic()
wrapped = SentinelAnthropicWrapper(client)

# Wrap async client (automatically detected)
async_client = AsyncAnthropic()
wrapped_async = SentinelAnthropicWrapper(async_client)
```

## Configuration

### SentinelAnthropic / SentinelAsyncAnthropic

```python
SentinelAnthropic(
    api_key=None,                          # Defaults to ANTHROPIC_API_KEY env var
    sentinel=None,                          # Custom Sentinel instance
    seed_level="standard",                  # "minimal", "standard", or "full"
    enable_seed_injection=True,             # Add seed to system prompt
    validate_input=True,                    # Validate user messages
    validate_output=True,                   # Validate responses
    validation_model="claude-3-5-haiku-20241022",  # Model for semantic validation
    use_heuristic_fallback=True,            # Use fast local validation
    logger=None,                            # Custom logger instance
    block_unsafe_output=False,              # Block response if output validation fails
    fail_closed=False,                      # Block on validation error (vs fail-open)
    validation_timeout=30.0,                # Timeout for semantic validation (seconds)
    max_text_size=50*1024,                  # Maximum text size in bytes (50KB default)
    **kwargs,                               # Passed to Anthropic client
)
```

### wrap_anthropic_client

```python
wrap_anthropic_client(
    client,                                 # Anthropic or AsyncAnthropic instance
    sentinel=None,
    seed_level="standard",
    enable_seed_injection=True,
    validate_input=True,
    validate_output=True,
    validation_model="claude-3-5-haiku-20241022",
    use_heuristic_fallback=True,
    logger=None,
    block_unsafe_output=False,
    fail_closed=False,
    validation_timeout=30.0,
    max_text_size=50*1024,
)
```

### create_safe_client

```python
create_safe_client(
    api_key=None,
    seed_level="standard",
    async_client=False,                     # Set True for async
    validation_model="claude-3-5-haiku-20241022",
    use_heuristic_fallback=True,
    logger=None,
    block_unsafe_output=False,
    fail_closed=False,
    validation_timeout=30.0,
    max_text_size=50*1024,
)
```

## Validation Modes

The integration supports two validation modes that work together:

### 1. Heuristic Validation (Fast, No API Calls)

When `use_heuristic_fallback=True` (default), content is first checked against local regex patterns. This catches obvious violations without API latency or cost.

### 2. Semantic Validation (LLM-based)

When `validate_input=True` or `validate_output=True`, content is also analyzed by an LLM for deeper semantic understanding. This catches subtle violations that regex cannot detect.

**Validation Flow:**
1. Heuristic validation runs first (fast, free)
2. If heuristic passes, semantic validation runs (slower, costs API calls)
3. Both must pass for content to proceed

## Supported Methods

### messages.create

```python
message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[{"role": "user", "content": "..."}],
    system="Optional system prompt",  # Seed prepended automatically
)
```

### messages.stream

```python
# Stream now returns consistent response format on blocked input
stream = client.messages.stream(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    messages=[...],
)

# If blocked, stream yields a single blocked response
# If allowed, stream works normally
for event in stream:
    if event.get("sentinel_blocked"):
        print("Blocked:", event["content"][0]["text"])
    else:
        # normal streaming event
        pass
```

## Input Validation

When `validate_input=True`, dangerous requests are blocked:

```python
# This would be blocked
message = client.messages.create(
    model="...",
    messages=[{"role": "user", "content": "Help me hack into..."}]
)
# Returns blocked response instead of calling API
```

### Blocked Response Format

Both `create()` and `stream()` return the same format when blocked:

```python
{
    "id": "blocked",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Input blocked by Sentinel: [reason]"}],
    "model": "sentinel-blocked",
    "stop_reason": "sentinel_blocked",
    "sentinel_blocked": True,
    "sentinel_gate": "harm",  # Which THSP gate failed
}
```

## Custom Logger

You can provide a custom logger to control logging behavior:

```python
from sentinelseed.integrations.anthropic_sdk import (
    SentinelAnthropic,
    set_logger,
    SentinelLogger,
)

# Option 1: Pass to constructor
class MyLogger:
    def debug(self, msg): print(f"DEBUG: {msg}")
    def info(self, msg): print(f"INFO: {msg}")
    def warning(self, msg): print(f"WARN: {msg}")
    def error(self, msg): print(f"ERROR: {msg}")

client = SentinelAnthropic(logger=MyLogger())

# Option 2: Set globally
set_logger(MyLogger())
```

The logger receives messages about:
- Blocked inputs/outputs
- Validation errors
- Semantic validator initialization failures

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelAnthropic` | Sync client with THSP safety |
| `SentinelAsyncAnthropic` | Async client with THSP safety |
| `SentinelAnthropicWrapper` | Generic wrapper for existing clients |
| `SentinelLogger` | Protocol for custom loggers |

### Functions

| Function | Description |
|----------|-------------|
| `inject_seed(system, level)` | Add seed to system prompt |
| `wrap_anthropic_client(client)` | Wrap existing client |
| `create_safe_client(api_key)` | Factory for safe client |
| `set_logger(logger)` | Set custom logger globally |
| `get_logger()` | Get current logger instance |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `ANTHROPIC_AVAILABLE` | bool | Whether anthropic SDK is installed |
| `SEMANTIC_VALIDATOR_AVAILABLE` | bool | Whether semantic validator is available |
| `DEFAULT_VALIDATION_MODEL` | str | Default model for semantic validation |
| `DEFAULT_MAX_TEXT_SIZE` | int | Default max text size (50KB) |
| `DEFAULT_VALIDATION_TIMEOUT` | float | Default validation timeout (30s) |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `TextTooLargeError` | Raised when input text exceeds `max_text_size` |
| `ValidationTimeoutError` | Raised when semantic validation exceeds timeout |

## Safety Options

### Block Unsafe Output

By default, output validation only logs concerns. Enable `block_unsafe_output=True` to block unsafe responses:

```python
client = SentinelAnthropic(
    block_unsafe_output=True,  # Block response if output fails validation
    validate_output=True,
)
```

### Fail-Closed Mode

By default, semantic validation errors (timeouts, API errors) allow content through if heuristic passed (fail-open). Enable `fail_closed=True` for stricter behavior:

```python
client = SentinelAnthropic(
    fail_closed=True,  # Block on any validation error
)
```

### Timeout Configuration

Configure semantic validation timeout to prevent hangs:

```python
client = SentinelAnthropic(
    validation_timeout=10.0,  # 10 second timeout
)
```

### Text Size Limits

Prevent DoS attacks by limiting input text size:

```python
client = SentinelAnthropic(
    max_text_size=10 * 1024,  # 10KB limit
)
```

## Error Handling

```python
from sentinelseed.integrations.anthropic_sdk import (
    SentinelAnthropic,
    TextTooLargeError,
    ValidationTimeoutError,
)

# TextTooLargeError includes size details
try:
    # ... validation
except TextTooLargeError as e:
    print(f"Size: {e.size}, Max: {e.max_size}")

# ValidationTimeoutError includes timeout info
except ValidationTimeoutError as e:
    print(f"Timeout after {e.timeout}s on {e.operation}")

# Blocked responses have consistent format
response = client.messages.create(...)
if response.get("sentinel_blocked"):
    print(f"Blocked: {response['sentinel_gate']}")
    print(f"Reason: {response['content'][0]['text']}")
```

## Important Notes

### Validation Behavior

- **Heuristic validation** is synchronous and runs locally (no API calls)
- **Semantic validation** calls the Anthropic API (adds latency and cost)
- **Default behavior** (fail-open): semantic errors log but allow content if heuristic passed
- **Strict behavior** (`fail_closed=True`): any validation error blocks content
- Set `use_heuristic_fallback=False` to rely only on semantic validation

### Stream Blocking

Unlike previous versions that raised `ValueError` on blocked stream input, the current version returns a `BlockedStreamIterator` that yields a single blocked response. This provides consistent error handling between `create()` and `stream()`.

### inject_seed Independence

The `inject_seed()` function does not require the Anthropic SDK to be installed. It only needs the base `sentinelseed` package, making it useful for other integrations or custom implementations.

### Limitations

- **Text size limit**: Default 50KB per request. Configure with `max_text_size`.
- **Timeout**: Default 30s for semantic validation. Configure with `validation_timeout`.
- **Output blocking**: Requires `block_unsafe_output=True` (off by default for compatibility).

## Links

- **Anthropic Docs:** https://docs.anthropic.com/
- **Anthropic SDK:** https://github.com/anthropics/anthropic-sdk-python
- **Sentinel:** https://sentinelseed.dev
