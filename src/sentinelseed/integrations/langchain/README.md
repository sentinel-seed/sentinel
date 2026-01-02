# LangChain Integration

Safety validation for LangChain applications via callbacks, guards, and chain wrappers.

## Architecture

The integration is organized into modular components:

```
langchain/
├── __init__.py      # Public API exports
├── utils.py         # Utilities, thread-safe structures, logger
├── callbacks.py     # SentinelCallback, StreamingBuffer
├── guards.py        # SentinelGuard
├── chains.py        # SentinelChain, inject_seed, wrap_llm
└── example.py       # Usage examples
```

## Requirements

```bash
pip install sentinelseed[langchain]
# or manually:
pip install sentinelseed langchain langchain-core
```

**Dependencies:**
- `langchain>=0.1.0`: [Docs](https://docs.langchain.com/oss/python/langchain/overview)
- `langchain-core>=0.1.0`: [API Reference](https://reference.langchain.com/python/)

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
    on_violation="log",         # log, raise, block, flag (see Violation Handling)
    validate_input=True,        # Validate input messages/prompts
    validate_output=True,       # Validate LLM responses
    log_safe=False,             # Log safe validations too
    max_violations=1000,        # Max violations to store (prevents memory leak)
    sanitize_logs=False,        # Mask emails, phones, tokens in logs
    logger=None,                # Custom logger instance
    max_text_size=50*1024,      # Max text size in bytes (50KB default)
    validation_timeout=30.0,    # Timeout for validation (seconds)
    fail_closed=False,          # Block on validation errors (vs fail-open)
    validator=None,             # Custom LayeredValidator instance
    use_semantic=False,         # Enable semantic validation layer
    semantic_api_key=None,      # API key for semantic validation
)
```

> **IMPORTANT**: Callbacks MONITOR but do NOT BLOCK execution. The `on_violation`
> parameter controls logging/raising behavior, not request blocking. For actual
> request blocking, use `SentinelGuard` or `SentinelChain` instead.

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
    max_text_size=50*1024,      # Max text size in bytes (50KB default)
    validation_timeout=30.0,    # Timeout for validation (seconds)
    fail_closed=False,          # Block on validation errors (vs fail-open)
    validator=None,             # Custom LayeredValidator instance
    use_semantic=False,         # Enable semantic validation layer
    semantic_api_key=None,      # API key for semantic validation
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
    max_text_size=50*1024,      # Max text size in bytes (50KB default)
    validation_timeout=30.0,    # Timeout for validation (seconds)
    fail_closed=False,          # Block on validation errors (vs fail-open)
    streaming_validation_interval=500,  # Characters between incremental validations
)
```

## Callback Events

The callback monitors these LangChain events:

| Event | Validation |
|-------|------------|
| `on_llm_start` | Input prompts |
| `on_chat_model_start` | Input messages |
| `on_llm_end` | Response content |
| `on_llm_error` | Error logging |
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

> **Note**: These modes apply to `SentinelCallback` only. Callbacks MONITOR but do NOT BLOCK
> LLM execution. For actual request blocking, use `SentinelGuard` or `SentinelChain`.

| Mode | Behavior |
|------|----------|
| `log` | Log warning message, continue execution |
| `raise` | Raise `SentinelViolationError` exception |
| `block` | Log as blocked (for monitoring dashboards), continue execution |
| `flag` | Silent recording only, no log output |

The `block` mode is useful for tracking violations in monitoring systems without actually
stopping the LLM call. It marks the violation as "blocked" in the violation log, which can
be queried via `get_violations()` for analytics purposes.

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

## Advanced Features

### Streaming Support

```python
# Stream with safety validation
for chunk in chain.stream("Your input"):
    if chunk.get("final"):
        print(f"Final: {chunk}")
    else:
        print(f"Chunk: {chunk.get('chunk')}")
```

### Batch Operations

```python
# Process multiple inputs
results = chain.batch(["Input 1", "Input 2", "Input 3"])

# Async batch
results = await chain.abatch(["Input 1", "Input 2"])
```

### Thread Safety

All components use thread-safe data structures:
- `ThreadSafeDeque` for bounded violation/validation logs
- `StreamingBuffer` for accumulating streaming tokens
- Thread locks for logger and buffer operations

### Exception Handling

Validation errors are caught and logged without crashing:
- `on_violation="raise"` still raises `SentinelViolationError`
- Other modes log errors and continue safely

### Require LangChain

```python
from sentinelseed.integrations.langchain import require_langchain

# Raises ImportError with helpful message if not installed
require_langchain("my_function")
```

## Safety Options

### Fail-Closed Mode

By default, validation errors (timeouts, exceptions) allow content through if heuristic passed (fail-open). Enable `fail_closed=True` for stricter behavior:

```python
guard = SentinelGuard(
    agent=agent,
    fail_closed=True,  # Block on any validation error
)
```

### Timeout Configuration

Configure validation timeout to prevent hangs:

```python
chain = SentinelChain(
    llm=llm,
    validation_timeout=10.0,  # 10 second timeout
)
```

### Text Size Limits

Prevent DoS attacks by limiting input text size:

```python
callback = SentinelCallback(
    max_text_size=10 * 1024,  # 10KB limit
)
```

### Incremental Streaming Validation

SentinelChain validates streaming output incrementally, not just at the end:

```python
chain = SentinelChain(
    llm=llm,
    streaming_validation_interval=500,  # Validate every 500 chars
)
```

## Error Handling

```python
from sentinelseed.integrations.langchain import (
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

# ConfigurationError for invalid parameters
from sentinelseed.integrations.langchain import ConfigurationError

try:
    callback = SentinelCallback(max_text_size="invalid")
except ConfigurationError as e:
    print(f"Invalid param '{e.param_name}': expected {e.expected}")
```

## Security Considerations

### Fail-Open vs Fail-Closed

> **IMPORTANT SECURITY DECISION**

By default, all components operate in **fail-open** mode (`fail_closed=False`). This means:

- If validation times out → content is **allowed through**
- If validation throws an exception → content is **allowed through**
- If the executor is unavailable → content is **allowed through**

This is a deliberate trade-off prioritizing **availability over security**.

For security-critical applications, enable `fail_closed=True`:

```python
# Fail-closed: block on any validation error
guard = SentinelGuard(agent=agent, fail_closed=True)
chain = SentinelChain(llm=llm, fail_closed=True)
callback = SentinelCallback(fail_closed=True)
```

### Streaming Exposure Window

Streaming validation occurs every `streaming_validation_interval` characters (default: 500). This means:

- Content in the first 0-499 characters may be sent to the client before the first validation
- Harmful content appearing mid-stream may be partially sent before detection

For maximum security, consider:
1. Reducing the interval: `streaming_validation_interval=100`
2. Using non-streaming mode for sensitive applications
3. Combining with client-side filtering

### wrap_llm Behavior

The `wrap_llm()` function does **NOT** modify the original LLM:

```python
llm = ChatOpenAI()
safe_llm = wrap_llm(llm)

# Original LLM is unchanged - can still be used without safety
response = llm.invoke("...")  # No safety checks
safe_response = safe_llm.invoke("...")  # With safety checks
```

This is intentional to avoid unexpected side effects when the same LLM is used elsewhere.

## Performance Notes

### Shared Executor

All validation operations use a shared `ValidationExecutor` singleton instead of creating new thread pools per call:

- Reduces thread creation overhead
- Limits maximum concurrent validation threads
- Automatically cleaned up on process exit

### Async Operations

Async methods (`ainvoke`, `astream`, `abatch`) use the shared `ValidationExecutor` for non-blocking validation:

- Does not block the event loop
- Uses the same controlled thread pool as sync operations
- Proper timeout handling via `asyncio.wrap_future()` and `asyncio.wait_for()`
- Thread pool size is bounded (default: 4 workers)

## Limitations

- **Text size limit**: Default 50KB per request. Configure with `max_text_size`.
- **Timeout**: Default 30s for validation. Configure with `validation_timeout`.
- **Callback behavior**: Callbacks MONITOR but do NOT BLOCK execution. Use `SentinelGuard` or `SentinelChain` for blocking.
- **Streaming validation**: Validated incrementally every N characters (configurable).
- **Fail-open default**: Validation errors allow content through by default. Use `fail_closed=True` for stricter security.

## Technical Notes

### Configuration Validation

All components validate configuration parameters at initialization:

- `max_text_size`: Must be a positive integer
- `validation_timeout`: Must be a positive number
- `fail_closed`: Must be a boolean
- `max_violations`: Must be a positive integer
- `streaming_validation_interval`: Must be a positive integer

Invalid parameters raise `ConfigurationError` with details about the expected type.

### Fail-Open Warning

When `fail_closed=False` (default), a debug-level warning is logged at initialization to alert about the fail-open behavior. This helps users understand the security implications without being intrusive.

## Links

- **LangChain Docs:** https://docs.langchain.com/oss/python/langchain/overview
- **LangChain Callbacks:** https://python.langchain.com/docs/how_to/callbacks_attach/
- **LangChain API Reference:** https://reference.langchain.com/python/langchain_core/callbacks/
- **Sentinel:** https://sentinelseed.dev
