# LangChain Integration

Safety validation for LangChain applications via callbacks and wrappers.

## Requirements

```bash
pip install sentinelseed[langchain]
# or manually:
pip install sentinelseed langchain langchain-core
```

**Dependencies:**
- `langchain>=0.1.0` — [Docs](https://python.langchain.com/docs/)
- `langchain-core>=0.1.0` — [API Reference](https://api.python.langchain.com/)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelCallback` | Callback handler for LLM monitoring |
| `SentinelGuard` | Wrapper for agents with validation |
| `SentinelChain` | Chain wrapper with safety checks |
| `inject_seed` | Add seed to any messages |

## Usage

### Option 1: Callback Handler

Monitor all LLM interactions:

```python
from langchain_openai import ChatOpenAI
from sentinelseed.integrations.langchain import SentinelCallback

# Create callback
callback = SentinelCallback(
    seed_level="standard",
    on_violation="log",  # or "raise", "flag"
)

# Add to LLM
llm = ChatOpenAI(callbacks=[callback])
response = llm.invoke("Your prompt")

# Check results
print(callback.get_stats())
print(callback.get_violations())
```

### Option 2: Agent Wrapper

Wrap agents for action validation:

```python
from langchain.agents import create_react_agent
from sentinelseed.integrations.langchain import SentinelGuard

agent = create_react_agent(llm, tools, prompt)

# Wrap with Sentinel
guard = SentinelGuard(
    agent=agent,
    block_unsafe=True,
    validate_input=True,
    validate_output=True,
)

result = guard.run("Your task")
```

### Option 3: Chain Wrapper

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sentinelseed.integrations.langchain import SentinelChain

prompt = ChatPromptTemplate.from_messages([...])
llm = ChatOpenAI()
chain = prompt | llm

# Wrap chain
safe_chain = SentinelChain(
    chain=chain,
    inject_seed=True,
    validate_output=True,
)

response = safe_chain.invoke({"input": "query"})
```

### Option 4: Message Injection

```python
from sentinelseed.integrations.langchain import inject_seed

messages = [
    {"role": "user", "content": "Hello"}
]

# Inject seed as system message
safe_messages = inject_seed(messages, seed_level="standard")
```

## Configuration

### SentinelCallback

```python
SentinelCallback(
    sentinel=None,           # Sentinel instance (auto-created if None)
    seed_level="standard",   # minimal, standard, full
    on_violation="log",      # log, raise, flag
    validate_input=True,     # Validate user messages
    validate_output=True,    # Validate LLM responses
)
```

### SentinelGuard

```python
SentinelGuard(
    agent=agent,
    sentinel=None,
    seed_level="standard",
    block_unsafe=True,       # Block or allow with warning
    validate_input=True,
    validate_output=True,
    inject_seed=True,        # Add seed to system prompt
)
```

## Callback Events

The callback monitors these LangChain events:

| Event | Validation |
|-------|------------|
| `on_llm_start` | Input messages/prompt |
| `on_llm_end` | Response content |
| `on_chain_start` | Chain inputs |
| `on_chain_end` | Chain outputs |
| `on_tool_start` | Tool inputs |
| `on_tool_end` | Tool outputs |

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelCallback` | BaseCallbackHandler implementation |
| `SentinelGuard` | Agent wrapper with validation |
| `SentinelChain` | Chain wrapper with injection |

### Functions

| Function | Description |
|----------|-------------|
| `inject_seed(messages, level)` | Add seed to message list |
| `create_safe_callback()` | Factory for callbacks |

### Methods (SentinelCallback)

| Method | Returns |
|--------|---------|
| `get_violations()` | List of validation events with issues |
| `get_validation_log()` | Full validation history |
| `get_stats()` | Dict with totals and rates |
| `clear_log()` | Reset validation history |

## Links

- **LangChain Docs:** https://python.langchain.com/docs/
- **LangChain Callbacks:** https://python.langchain.com/docs/how_to/callbacks_runtime
- **Sentinel:** https://sentinelseed.dev
