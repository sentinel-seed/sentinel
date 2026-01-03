# Raw API Integration

Utilities for adding Sentinel safety to raw HTTP API calls.

## Requirements

```bash
pip install sentinelseed requests
```

No framework dependencies. Works with any HTTP client.

## Overview

| Component | Description |
|-----------|-------------|
| `prepare_openai_request` | Prepare OpenAI-compatible request |
| `prepare_anthropic_request` | Prepare Anthropic request |
| `validate_response` | Validate API response |
| `RawAPIClient` | Simple HTTP client |
| `inject_seed_openai` | Add seed to OpenAI messages |
| `inject_seed_anthropic` | Add seed to Anthropic system |

## Usage

### OpenAI-Compatible APIs

```python
import requests
from sentinelseed.integrations.raw_api import prepare_openai_request

headers, body = prepare_openai_request(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4o",
    api_key="sk-...",
    seed_level="standard",
)

response = requests.post(
    "https://api.openai.com/v1/chat/completions",
    headers=headers,
    json=body,
)
```

Works with: OpenAI, OpenRouter, Together AI, any OpenAI-compatible API.

### Anthropic API

```python
import requests
from sentinelseed.integrations.raw_api import prepare_anthropic_request

headers, body = prepare_anthropic_request(
    messages=[{"role": "user", "content": "Hello"}],
    model="claude-sonnet-4-5-20250929",
    api_key="sk-ant-...",
    system="You are helpful",  # Seed prepended
)

response = requests.post(
    "https://api.anthropic.com/v1/messages",
    headers=headers,
    json=body,
)
```

### Validate Response

```python
from sentinelseed.integrations.raw_api import validate_response

result = validate_response(
    response.json(),
    response_format="openai",  # or "anthropic"
    block_on_unsafe=False,     # Set True to raise ValidationError for unsafe content
)

if result["valid"]:
    print(result["content"])
else:
    print(f"Concerns: {result['violations']}")
```

### Simple Client

```python
from sentinelseed.integrations.raw_api import RawAPIClient

client = RawAPIClient(
    provider="openai",      # "openai" or "anthropic"
    api_key="sk-...",
    timeout=30,             # Request timeout in seconds
)

result = client.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4o",
    block_on_unsafe=True,   # Raise ValidationError for unsafe output
)

print(result["content"])
print(result["valid"])
```

### Just Inject Seed

```python
from sentinelseed.integrations.raw_api import (
    inject_seed_openai,
    inject_seed_anthropic,
)

# OpenAI format
messages = [{"role": "user", "content": "Hello"}]
safe_messages = inject_seed_openai(messages)
# System message with seed added

# Anthropic format
system = inject_seed_anthropic("You are helpful")
# Returns: "{seed}\n\n---\n\nYou are helpful"
```

## Configuration

### prepare_openai_request

```python
prepare_openai_request(
    messages=[...],
    model="gpt-4o-mini",
    api_key=None,
    sentinel=None,
    seed_level="standard",       # minimal, standard, full
    inject_seed=True,            # Add seed to system
    validate_input=True,         # Validate user messages
    max_tokens=1024,
    temperature=0.7,
    **kwargs,                    # Additional API params
)
# Returns: (headers, body)
# Raises: ValueError, ValidationError
```

### prepare_anthropic_request

```python
prepare_anthropic_request(
    messages=[...],
    model="claude-sonnet-4-5-20250929",
    api_key=None,
    sentinel=None,
    seed_level="standard",       # minimal, standard, full
    inject_seed=True,
    validate_input=True,
    max_tokens=1024,
    system=None,                 # System prompt
    **kwargs,
)
# Returns: (headers, body)
# Raises: ValueError, ValidationError
```

### validate_response

```python
validate_response(
    response,                    # Parsed JSON dict
    sentinel=None,               # Sentinel instance (fallback)
    response_format="openai",    # openai, anthropic
    block_on_unsafe=False,       # Raise ValidationError if unsafe
    validator=None,              # LayeredValidator (preferred over sentinel)
)
# Returns: {valid, response, violations, content, sentinel_checked}
# Raises: ValueError, ValidationError
```

### RawAPIClient

```python
RawAPIClient(
    provider="openai",           # openai, anthropic
    api_key=None,
    base_url=None,               # Custom endpoint
    sentinel=None,
    seed_level="standard",       # minimal, standard, full
    timeout=30,                  # Request timeout in seconds (int or float)
    validator=None,              # LayeredValidator for dependency injection
)
# Raises: ValueError for invalid provider/seed_level/base_url/timeout

client.chat(
    messages=[...],
    model=None,                  # Uses provider default
    max_tokens=1024,
    timeout=None,                # Override client timeout
    block_on_unsafe=False,       # Raise ValidationError if unsafe
    **kwargs,
)
# Returns: {valid, response, violations, content, sentinel_checked}
# Raises: RawAPIError, ValidationError
```

## Limitations & Behaviors

### Content Size Limit

**Maximum content size:** 50KB (50,000 bytes) per message.
Content exceeding this limit will be blocked with a `ValidationError`.

### Response Handling

| Behavior | Description |
|----------|-------------|
| **Streaming** | Not supported. Use full responses only. Delta format returns empty content. |
| **Multiple choices** | Only the first choice is extracted. Other choices are ignored. |
| **Tool calls** | When `content` is `None` (tool_calls present), returns empty string. |
| **Vision format** | Content as list (OpenAI vision) is converted to concatenated text. |
| **Anthropic blocks** | Multiple text blocks are concatenated. Non-text blocks are ignored. |

### Example: Tool Calls Response

```python
# When API returns tool_calls, content may be None
response = {
    "choices": [{
        "message": {
            "content": None,  # No text, only tool calls
            "tool_calls": [...]
        }
    }]
}
result = validate_response(response)
result["content"]  # Returns ""
result["valid"]    # Returns True
```

## Error Handling

The integration provides custom exceptions for better error handling:

```python
from sentinelseed.integrations.raw_api import (
    RawAPIError,
    ValidationError,
)

try:
    result = client.chat(messages=[...], block_on_unsafe=True)
except ValidationError as e:
    print(f"Validation failed: {e.message}")
    print(f"Concerns: {e.concerns}")
    print(f"Violations: {e.violations}")
except RawAPIError as e:
    print(f"API error: {e.message}")
    print(f"Details: {e.details}")
```

### Error Types

| Exception | Cause |
|-----------|-------|
| `ValueError` | Invalid parameters (messages, seed_level, etc.) |
| `ValidationError` | Input/output blocked by Sentinel |
| `RawAPIError` | HTTP errors, timeouts, JSON parsing errors |

## API Endpoints

| Provider | URL |
|----------|-----|
| OpenAI | `https://api.openai.com/v1/chat/completions` |
| Anthropic | `https://api.anthropic.com/v1/messages` |

## Headers Generated

### OpenAI

```python
{
    "Content-Type": "application/json",
    "Authorization": "Bearer {api_key}"
}
```

### Anthropic

```python
{
    "Content-Type": "application/json",
    "anthropic-version": "2023-06-01",
    "x-api-key": "{api_key}"
}
```

## Constants

| Constant | Value |
|----------|-------|
| `OPENAI_API_URL` | `https://api.openai.com/v1/chat/completions` |
| `ANTHROPIC_API_URL` | `https://api.anthropic.com/v1/messages` |
| `VALID_SEED_LEVELS` | `("minimal", "standard", "full")` |
| `VALID_PROVIDERS` | `("openai", "anthropic")` |
| `VALID_RESPONSE_FORMATS` | `("openai", "anthropic")` |
| `DEFAULT_TIMEOUT` | `30` |

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `prepare_openai_request(...)` | Create OpenAI request |
| `prepare_anthropic_request(...)` | Create Anthropic request |
| `validate_response(response)` | Validate API response |
| `create_openai_request_body(...)` | Body only (no headers) |
| `create_anthropic_request_body(...)` | Body only |
| `inject_seed_openai(messages)` | Add seed to messages |
| `inject_seed_anthropic(system)` | Add seed to system |

### create_openai_request_body

```python
create_openai_request_body(
    messages=[...],
    model="gpt-4o-mini",
    sentinel=None,
    seed_level="standard",
    inject_seed=True,
    max_tokens=1024,
    temperature=0.7,
    **kwargs,
)
# Returns: dict (request body, no headers)
```

### create_anthropic_request_body

```python
create_anthropic_request_body(
    messages=[...],
    model="claude-sonnet-4-5-20250929",
    sentinel=None,
    seed_level="standard",
    inject_seed=True,
    max_tokens=1024,
    temperature=1.0,
    system=None,
    **kwargs,
)
# Returns: dict (request body, no headers)
```

### Classes

| Class | Description |
|-------|-------------|
| `RawAPIClient` | Simple HTTP client with Sentinel |
| `RawAPIError` | Base exception for API errors |
| `ValidationError` | Exception for validation failures |

## Links

- **OpenAI API:** https://platform.openai.com/docs/api-reference
- **Anthropic API:** https://docs.anthropic.com/
- **Sentinel:** https://sentinelseed.dev
