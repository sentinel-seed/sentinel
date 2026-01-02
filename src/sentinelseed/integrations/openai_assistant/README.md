# OpenAI Assistants Integration

Safety wrappers for the OpenAI Assistants API.

## Requirements

```bash
pip install sentinelseed[openai]
# or manually:
pip install sentinelseed openai
```

**Dependencies:**
- `openai>=1.0.0`: [Docs](https://platform.openai.com/docs/assistants)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelAssistant` | Assistant with safety instructions |
| `SentinelAssistantClient` | Full client for assistant management |
| `SentinelAsyncAssistantClient` | Async version |
| `wrap_assistant` | Wrap existing assistant |
| `inject_seed_instructions` | Add seed to instructions |

## Usage

### Option 1: Create Safe Assistant

```python
from sentinelseed.integrations.openai_assistant import SentinelAssistant

# Create assistant with seed in instructions
assistant = SentinelAssistant.create(
    name="Code Helper",
    instructions="You help users write Python code",
    model="gpt-4o",
    tools=[{"type": "code_interpreter"}],
    seed_level="standard",
)

print(f"Created: {assistant.id}")
```

### Option 2: Full Client

```python
from sentinelseed.integrations.openai_assistant import SentinelAssistantClient

client = SentinelAssistantClient(
    api_key="...",
    seed_level="standard",
    validate_input=True,
    validate_output=True,
)

# Create assistant
assistant = client.create_assistant(
    name="Helper",
    instructions="You are helpful",
    model="gpt-4o",
)

# Create thread
thread = client.create_thread()

# Run conversation
result = client.run_conversation(
    assistant_id=assistant.id,
    thread_id=thread.id,
    message="Help me with Python",
)

print(result["response"])
print(result["validated"])  # True if output passed validation
```

### Option 3: Wrap Existing Assistant

```python
from openai import OpenAI
from sentinelseed.integrations.openai_assistant import wrap_assistant

client = OpenAI()
assistant = client.beta.assistants.retrieve("asst_...")

# Wrap for local validation
safe_assistant = wrap_assistant(assistant, seed_level="standard")
```

### Option 4: Just Inject Instructions

```python
from openai import OpenAI
from sentinelseed.integrations.openai_assistant import inject_seed_instructions

client = OpenAI()
assistant = client.beta.assistants.create(
    name="Helper",
    instructions=inject_seed_instructions("You help users"),
    model="gpt-4o",
)
```

## Configuration

### SentinelAssistantClient

```python
SentinelAssistantClient(
    api_key=None,                # Defaults to OPENAI_API_KEY
    sentinel=None,               # Sentinel instance
    seed_level="standard",       # minimal, standard, full
    validate_input=True,         # Validate user messages
    validate_output=True,        # Validate assistant responses
    block_unsafe_output=False,   # Raise OutputBlockedError if unsafe
    validator=None,              # Optional LayeredValidator (for testing)
    use_semantic=False,          # Enable semantic validation
    semantic_api_key=None,       # API key for semantic validation
    semantic_provider="openai",  # Provider for semantic validation
    semantic_model=None,         # Model for semantic validation
)
```

**Notes:**
- `block_unsafe_output`: When True, raises `OutputBlockedError` instead of just logging violations
- `validator`: Primarily for dependency injection in tests
- `use_semantic`: Enables LLM-based validation (~90% accuracy vs ~50% for heuristic)
- Semantic validation requires `semantic_api_key` to be set

### SentinelAssistant.create

```python
SentinelAssistant.create(
    name="...",
    instructions="...",          # Seed prepended
    model="gpt-4o",
    tools=[],
    sentinel=None,
    seed_level="standard",
    api_key=None,
    **kwargs,                    # Additional API params
)
```

## Workflow

### Complete Conversation Flow

```python
client = SentinelAssistantClient()

# 1. Create assistant (seed in instructions)
assistant = client.create_assistant(
    name="Analyst",
    instructions="You analyze data",
)

# 2. Create thread
thread = client.create_thread()

# 3. Add message (validates input)
client.add_message(thread.id, "Analyze this dataset")

# 4. Create run
run = client.create_run(thread.id, assistant.id)

# 5. Wait for completion
completed = client.wait_for_run(thread.id, run.id)

# 6. Get validated response
messages = client.get_messages(thread.id)
```

### run_conversation (Simplified)

```python
result = client.run_conversation(
    assistant_id=assistant.id,
    thread_id=thread.id,
    message="Your question",
    poll_interval=1.0,           # Seconds between checks
    timeout=300.0,               # Max wait time
)

# Result contains:
# - response: str
# - messages: List[Message]
# - run: Run
# - validated: bool
# - validation: {valid: bool, violations: []}
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelAssistant` | Assistant wrapper |
| `SentinelAssistantClient` | Sync client |
| `SentinelAsyncAssistantClient` | Async client |

### Methods (SentinelAssistantClient)

| Method | Description |
|--------|-------------|
| `create_assistant(...)` | Create assistant with seed |
| `create_thread(messages)` | Create conversation thread |
| `add_message(thread_id, content)` | Add validated message |
| `create_run(thread_id, assistant_id)` | Start run |
| `wait_for_run(thread_id, run_id)` | Wait for completion |
| `get_messages(thread_id)` | Get thread messages |
| `run_conversation(...)` | Complete turn |
| `delete_assistant(id)` | Delete assistant |
| `delete_thread(id)` | Delete thread |

### Functions

| Function | Description |
|----------|-------------|
| `wrap_assistant(assistant)` | Wrap existing assistant |
| `inject_seed_instructions(text)` | Add seed to instructions |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `AssistantRunError` | Raised when an assistant run fails or is cancelled |
| `AssistantRequiresActionError` | Raised when a run requires action (function calling) |
| `ValidationError` | Raised when validation fails |
| `OutputBlockedError` | Raised when output is blocked due to safety violations |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `OPENAI_AVAILABLE` | bool | True if openai package is installed |
| `VALID_SEED_LEVELS` | tuple | ("minimal", "standard", "full") |
| `DEFAULT_POLL_INTERVAL` | 1.0 | Default seconds between run status checks |
| `DEFAULT_TIMEOUT` | 300.0 | Default max wait time for run completion |
| `DEFAULT_VALIDATION_TIMEOUT` | 30.0 | Reserved for semantic validation timeout |

### Inherited Methods (from SentinelIntegration)

| Method/Property | Description |
|-----------------|-------------|
| `validate(content)` | Validate content through THSP protocol |
| `validate_action(action, args)` | Validate an action with arguments |
| `validate_request(content)` | Validate a request (returns dict with should_proceed) |
| `reset_stats()` | Reset validation statistics |
| `validation_stats` | Property: Get validation statistics |
| `validator` | Property: Access the LayeredValidator instance |

## Error Handling

```python
from sentinelseed.integrations.openai_assistant import (
    SentinelAssistantClient,
    AssistantRunError,
    AssistantRequiresActionError,
    OutputBlockedError,
    ValidationError,
)

client = SentinelAssistantClient(block_unsafe_output=True)

try:
    result = client.run_conversation(assistant_id, thread_id, message)
except OutputBlockedError as e:
    print(f"Output blocked: {e.violations}")
except AssistantRunError as e:
    print(f"Run failed: {e.run_id} - {e.status}")
except AssistantRequiresActionError as e:
    print(f"Run requires action: {e.run_id}")
except ValidationError as e:
    print(f"Validation failed: {e.concerns}")
```

## Links

- **OpenAI Assistants:** https://platform.openai.com/docs/assistants
- **OpenAI Python SDK:** https://github.com/openai/openai-python
- **Sentinel:** https://sentinelseed.dev
