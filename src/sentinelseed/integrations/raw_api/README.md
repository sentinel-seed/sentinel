# Raw API Integration

Utilities for adding Sentinel safety to raw HTTP API calls.

## Requirements

```bash
pip install sentinelseed
# Optional: pip install requests httpx
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
    model="claude-sonnet-4-20250514",
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
    provider="openai",
    api_key="sk-...",
)

result = client.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="gpt-4o",
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
    seed_level="standard",
    inject_seed=True,            # Add seed to system
    validate_input=True,         # Validate user messages
    max_tokens=1024,
    temperature=0.7,
    **kwargs,                    # Additional API params
)
# Returns: (headers, body)
```

### prepare_anthropic_request

```python
prepare_anthropic_request(
    messages=[...],
    model="claude-sonnet-4-20250514",
    api_key=None,
    sentinel=None,
    seed_level="standard",
    inject_seed=True,
    validate_input=True,
    max_tokens=1024,
    system=None,                 # System prompt
    **kwargs,
)
# Returns: (headers, body)
```

### validate_response

```python
validate_response(
    response,                    # Parsed JSON dict
    sentinel=None,
    response_format="openai",    # openai, anthropic
)
# Returns: {valid, response, violations, content, sentinel_checked}
```

### RawAPIClient

```python
RawAPIClient(
    provider="openai",           # openai, anthropic
    api_key=None,
    base_url=None,               # Custom endpoint
    sentinel=None,
    seed_level="standard",
)
```

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

### Classes

| Class | Description |
|-------|-------------|
| `RawAPIClient` | Simple HTTP client |

### Constants

| Constant | Value |
|----------|-------|
| `OPENAI_API_URL` | `https://api.openai.com/v1/chat/completions` |
| `ANTHROPIC_API_URL` | `https://api.anthropic.com/v1/messages` |

## Links

- **OpenAI API:** https://platform.openai.com/docs/api-reference
- **Anthropic API:** https://docs.anthropic.com/en/api
- **Sentinel:** https://sentinelseed.dev
