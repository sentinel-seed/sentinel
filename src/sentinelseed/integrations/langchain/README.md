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
| `SentinelChain` | Chain/LLM wrapper with safety checks |
| `inject_seed` | Add seed to any message list |
| `wrap_llm` | Wrap LLM with safety features |
| `create_safe_callback` | Factory for callbacks |

## Usage

### Option 1: Callback Handler

Monitor all LLM interactions:

```python
from langchain_openai import ChatOpenAI
from sentinelseed.integrations.langchain import SentinelCallback

# Create callback with validation options
callback = SentinelCallback(
    seed_level="standard",       # minimal, standard, full
    on_violation="log",          # log, raise, block, flag
    validate_input=True,         # Validate user messages
    validate_output=True,        # Validate LLM responses
    max_violations=1000,         # Limit stored violations
    sanitize_logs=True,          # Mask sensitive data in logs
)

# Add to LLM
llm = ChatOpenAI(callbacks=[callback])
response = llm.invoke("Your prompt")

# Check results
print(callback.get_stats())
print(callback.get_violations())
print(callback.get_validation_log())
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
    seed_level="standard",
    block_unsafe=True,
    validate_input=True,
    validate_output=True,
    inject_seed=False,
)

result = guard.invoke({"input": "Your task"})
# or legacy: guard.run("Your task")
```

### Option 3: Chain Wrapper

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from sentinelseed.integrations.langchain import SentinelChain

# Option A: Wrap an LLM directly
chain = SentinelChain(
    llm=ChatOpenAI(),
    seed_level="standard",
    inject_seed=True,
    validate_input=True,
    validate_output=True,
)
result = chain.invoke("Help me with something")

# Option B: Wrap a full chain/runnable
prompt = ChatPromptTemplate.from_messages([...])
llm = ChatOpenAI()
full_chain = prompt | llm

safe_chain = SentinelChain(
    chain=full_chain,
    validate_input=True,
    validate_output=True,
)
result = safe_chain.invoke({"input": "query"})
```

### Option 4: Message Injection

```python
from sentinelseed.integrations.langchain import inject_seed

messages = [
    {"role": "user", "content": "Hello"}
]

# Inject seed as system message
safe_messages = inject_seed(messages, seed_level="standard")
# Returns list with seed prepended to (or added as) system message
```

### Option 5: LLM Wrapper

```python
from langchain_openai import ChatOpenAI
from sentinelseed.integrations.langchain import wrap_llm

llm = ChatOpenAI()

# Wrap with Sentinel protection
safe_llm = wrap_llm(
    llm,
    seed_level="standard",
    inject_seed=True,         # Inject seed into prompts
    add_callback=True,        # Add monitoring callback
    validate_input=True,
    validate_output=True,
    on_violation="log",
)

response = safe_llm.invoke([{"role": "user", "content": "Hello"}])
```

## Configuration

### SentinelCallback

```python
SentinelCallback(
    sentinel=None,              # Sentinel instance (auto-created if None)
    seed_level="standard",      # minimal, standard, full
    on_violation="log",         # log, raise, block, flag
    validate_input=True,        # Validate input messages/prompts
    validate_output=True,       # Validate LLM responses
    log_safe=False,             # Log safe validations too
    max_violations=1000,        # Max violations to store (prevents memory leak)
    sanitize_logs=False,        # Mask emails, phones, tokens in logs
    logger=None,                # Custom logger instance
)
```

### SentinelGuard

```python
SentinelGuard(
    agent=agent,                # LangChain agent/chain to wrap
    sentinel=None,              # Sentinel instance
    seed_level="standard",      # Seed level for validation
    block_unsafe=True,          # Block or allow with warning
    validate_input=True,        # Validate inputs
    validate_output=True,       # Validate outputs
    inject_seed=False,          # Inject seed (for internal processing)
    logger=None,                # Custom logger instance
)
```

### SentinelChain

```python
SentinelChain(
    llm=None,                   # LangChain LLM (use this OR chain)
    chain=None,                 # LangChain chain/runnable (use this OR llm)
    sentinel=None,              # Sentinel instance
    seed_level="standard",      # Seed level
    inject_seed=True,           # Inject seed into system message
    validate_input=True,        # Validate inputs
    validate_output=True,       # Validate outputs
    logger=None,                # Custom logger instance
)
```

## Callback Events

The callback monitors these LangChain events:

| Event | Validation |
|-------|------------|
| `on_llm_start` | Input prompts |
| `on_chat_model_start` | Input messages |
| `on_llm_end` | Response content |
| `on_llm_new_token` | Streaming tokens |
| `on_chain_start` | Chain inputs |
| `on_chain_end` | Chain outputs |
| `on_tool_start` | Tool inputs |
| `on_tool_end` | Tool outputs |
| `on_agent_action` | Agent actions |

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelCallback` | BaseCallbackHandler implementation for monitoring |
| `SentinelGuard` | Agent/chain wrapper with validation |
| `SentinelChain` | Chain wrapper with seed injection |
| `SentinelViolationError` | Exception raised when on_violation="raise" |

### Functions

| Function | Description |
|----------|-------------|
| `inject_seed(messages, seed_level)` | Add seed to message list |
| `wrap_llm(llm, ...)` | Wrap LLM with safety features |
| `create_safe_callback(...)` | Factory for SentinelCallback |
| `set_logger(logger)` | Set custom logger globally |

### Methods (SentinelCallback)

| Method | Returns |
|--------|---------|
| `get_violations()` | List of violation events |
| `get_validation_log()` | Full validation history (safe and unsafe) |
| `get_stats()` | Dict with totals, rates, breakdowns |
| `clear_violations()` | Reset violation log |
| `clear_log()` | Reset all logs |

## Custom Logger

```python
import logging
from sentinelseed.integrations.langchain import set_logger, SentinelCallback

# Option 1: Use standard logging
logging.basicConfig(level=logging.DEBUG)
set_logger(logging.getLogger("my_app.sentinel"))

# Option 2: Custom logger class
class MyLogger:
    def debug(self, msg): print(f"[DEBUG] {msg}")
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

callback = SentinelCallback(logger=MyLogger())
```

## Violation Handling

| Mode | Behavior |
|------|----------|
| `log` | Log warning, continue execution |
| `raise` | Raise `SentinelViolationError` |
| `block` | Log as blocked, continue execution |
| `flag` | Silent recording, no log output |

## Response Format

### SentinelChain.invoke()

```python
# Safe response
{"output": "...", "blocked": False, "violations": None}

# Blocked at input
{"output": None, "blocked": True, "blocked_at": "input", "reason": [...]}

# Blocked at output
{"output": "...", "blocked": True, "blocked_at": "output", "violations": [...]}
```

### SentinelGuard.invoke()

```python
# Safe response
{"output": "...", "sentinel_blocked": False}

# Blocked response
{
    "output": "Request blocked by Sentinel: [...]",
    "sentinel_blocked": True,
    "sentinel_reason": [...]
}
```

## Links

- **LangChain Docs:** https://python.langchain.com/docs/
- **LangChain Callbacks:** https://python.langchain.com/docs/how_to/callbacks_runtime
- **Sentinel:** https://sentinelseed.dev
