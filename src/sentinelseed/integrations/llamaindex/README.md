# LlamaIndex Integration

Safety callbacks and LLM wrappers for LlamaIndex applications.

## Requirements

```bash
pip install sentinelseed[llamaindex]
# or manually:
pip install sentinelseed llama-index-core
```

**Dependencies:**
- `llama-index-core>=0.10.0`: [Docs](https://developers.llamaindex.ai/)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelCallbackHandler` | Callback for monitoring operations |
| `SentinelLLM` | LLM wrapper with seed injection |
| `wrap_llm` | Convenience function for wrapping |
| `setup_sentinel_monitoring` | Global setup helper |

## Usage

### Option 1: Global Callback Handler

```python
from llama_index.core import Settings
from llama_index.core.callbacks import CallbackManager
from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

# Create handler
handler = SentinelCallbackHandler(
    seed_level="standard",
    on_violation="log",  # log, raise, flag
)

# Set globally
Settings.callback_manager = CallbackManager([handler])

# All LlamaIndex operations are now monitored
index = VectorStoreIndex.from_documents(documents)
response = index.as_query_engine().query("Your question")

# Check validation stats
print(handler.get_stats())
```

### Option 2: Wrap LLM

```python
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings
from sentinelseed.integrations.llamaindex import wrap_llm

# Wrap LLM with Sentinel
Settings.llm = wrap_llm(
    OpenAI(model="gpt-4o"),
    seed_level="standard",
    inject_seed=True,
)

# All LLM calls have seed injected
```

### Option 3: SentinelLLM Directly

```python
from llama_index.llms.openai import OpenAI
from sentinelseed.integrations.llamaindex import SentinelLLM

base_llm = OpenAI(model="gpt-4o")

sentinel_llm = SentinelLLM(
    llm=base_llm,
    seed_level="standard",
    inject_seed=True,
    validate_input=True,
    validate_output=True,
)

# Use directly
response = sentinel_llm.chat(messages)
response = sentinel_llm.complete(prompt)
```

### Option 4: Quick Setup

```python
from sentinelseed.integrations.llamaindex import setup_sentinel_monitoring

# One-line setup
handler = setup_sentinel_monitoring(
    seed_level="standard",
    on_violation="log",
)

# All LlamaIndex operations monitored
```

## Callback Events

The handler monitors these LlamaIndex events:

| Event Type | Validation |
|------------|------------|
| `LLM` | Template, messages, responses |
| `QUERY` | Query string content |
| `SYNTHESIZE` | Synthesis results |

## Configuration

### SentinelCallbackHandler

```python
SentinelCallbackHandler(
    sentinel=None,               # Sentinel instance
    seed_level="standard",       # minimal, standard, full
    on_violation="log",          # log, raise, flag
    event_starts_to_ignore=[],   # Event types to skip on start
    event_ends_to_ignore=[],     # Event types to skip on end
    validator=None,              # Optional LayeredValidator (for testing)
)
```

**Note:** The `validator` parameter is optional and primarily used for dependency injection in tests. In normal usage, a LayeredValidator is created automatically.

### SentinelLLM

```python
SentinelLLM(
    llm=base_llm,                # LlamaIndex LLM to wrap
    sentinel=None,               # Sentinel instance
    seed_level="standard",       # minimal, standard, full
    inject_seed=True,            # Add seed to system messages
    validate_input=True,         # Validate inputs
    validate_output=True,        # Validate outputs
    validator=None,              # Optional LayeredValidator (for testing)
)
```

**Note:** The `validator` parameter is optional and primarily used for dependency injection in tests.

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelCallbackHandler` | BaseCallbackHandler implementation |
| `SentinelLLM` | LLM wrapper with safety |
| `SentinelValidationEvent` | Validation event record |

### Functions

| Function | Description |
|----------|-------------|
| `wrap_llm(llm)` | Wrap LLM with Sentinel |
| `setup_sentinel_monitoring()` | Configure global monitoring |

### Methods (SentinelCallbackHandler)

| Method | Returns |
|--------|---------|
| `get_violations()` | List of unsafe events |
| `get_validation_log()` | All validation events |
| `get_stats()` | Validation statistics |
| `clear_log()` | Reset history |

### Methods (SentinelLLM)

| Method | Description |
|--------|-------------|
| `chat(messages)` | Chat with validation |
| `achat(messages)` | Async chat |
| `complete(prompt)` | Completion with validation |
| `acomplete(prompt)` | Async completion |
| `stream_chat(messages)` | Streaming chat |
| `stream_complete(prompt)` | Streaming completion |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `LLAMAINDEX_AVAILABLE` | bool | True if llama-index-core is installed |
| `SEMANTIC_AVAILABLE` | bool | True if semantic validation is available |
| `VALID_VIOLATION_MODES` | frozenset | Valid values for on_violation: {"log", "raise", "flag"} |

## Error Handling

```python
from sentinelseed.integrations.llamaindex import SentinelCallbackHandler

# Invalid on_violation raises ValueError
try:
    handler = SentinelCallbackHandler(on_violation="invalid")
except ValueError as e:
    print(e)  # "Invalid on_violation 'invalid'. Must be one of: ['flag', 'log', 'raise']"

# Check availability before using
from sentinelseed.integrations.llamaindex import LLAMAINDEX_AVAILABLE

if LLAMAINDEX_AVAILABLE:
    handler = SentinelCallbackHandler()
else:
    print("llama-index-core not installed")
```

## Links

- **LlamaIndex Docs:** https://developers.llamaindex.ai/
- **Sentinel:** https://sentinelseed.dev
