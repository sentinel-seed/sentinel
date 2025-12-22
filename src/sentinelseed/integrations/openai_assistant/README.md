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
    sentinel=None,
    seed_level="standard",
    validate_input=True,         # Validate user messages
    validate_output=True,        # Validate assistant responses
)
```

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

## Links

- **OpenAI Assistants:** https://platform.openai.com/docs/assistants
- **OpenAI Python SDK:** https://github.com/openai/openai-python
- **Sentinel:** https://sentinelseed.dev
