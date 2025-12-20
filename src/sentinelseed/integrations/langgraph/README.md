# LangGraph Integration

Safety nodes and tools for LangGraph state machines.

## Requirements

```bash
pip install sentinelseed langgraph
```

**Dependencies:**
- `langgraph>=0.0.1` — [Docs](https://langchain-ai.github.io/langgraph/)
- `langchain` (optional, for `create_sentinel_tool`)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelSafetyNode` | Node that validates state/messages |
| `SentinelGuardNode` | Wrapper that validates before/after node execution |
| `SentinelAgentExecutor` | Wrapper for compiled graphs with safety |
| `add_safety_layer` | Add safety nodes to existing graphs |
| `conditional_safety_edge` | Conditional edge based on safety state |
| `create_safety_router` | Factory for custom safety routers |
| `sentinel_gate_tool` | Tool for agents to self-check actions |
| `create_sentinel_tool` | LangChain-compatible safety tool |

## Quick Start

### Option 1: Safety Node

Add safety validation as a graph node:

```python
from langgraph.graph import StateGraph, MessagesState, START, END
from sentinelseed.integrations.langgraph import (
    SentinelSafetyNode,
    conditional_safety_edge,
)

# Create safety node
safety_node = SentinelSafetyNode(
    on_violation="block",  # "log", "block", or "flag"
    check_input=True,
    check_output=False,
)

# Build graph
graph = StateGraph(MessagesState)
graph.add_node("safety_check", safety_node)
graph.add_node("agent", agent_node)
graph.add_node("blocked", blocked_response_node)

# Connect edges
graph.add_edge(START, "safety_check")
graph.add_conditional_edges(
    "safety_check",
    conditional_safety_edge,
    {"continue": "agent", "blocked": "blocked"}
)
graph.add_edge("agent", END)
graph.add_edge("blocked", END)

app = graph.compile()
```

### Option 2: Guard Node (Wrap Existing Node)

```python
from sentinelseed.integrations.langgraph import SentinelGuardNode

# Your existing node
def tool_node(state):
    # Execute tools...
    return state

# Wrap with safety validation
safe_tool_node = SentinelGuardNode(
    tool_node,
    on_violation="block",
)

graph.add_node("safe_tools", safe_tool_node)
```

### Option 3: Agent Executor

```python
from sentinelseed.integrations.langgraph import SentinelAgentExecutor

# Your compiled graph
app = graph.compile()

# Wrap with safety
executor = SentinelAgentExecutor(
    app,
    on_violation="block",
    max_output_messages=5,
)

# Use the executor
result = executor.invoke({
    "messages": [{"role": "user", "content": "Hello"}]
})

# Async support
result = await executor.ainvoke({...})
```

### Option 4: Safety Tool for Agents

```python
from sentinelseed.integrations.langgraph import sentinel_gate_tool

# Check if an action is safe
result = sentinel_gate_tool("Delete all files in /tmp")
print(result["safe"])  # False
print(result["concerns"])  # ["Potentially harmful action..."]

# Or create a LangChain tool
from sentinelseed.integrations.langgraph import create_sentinel_tool

safety_tool = create_sentinel_tool()
agent = create_react_agent(llm, tools=[..., safety_tool])
```

## Configuration

### SentinelSafetyNode

```python
SentinelSafetyNode(
    sentinel=None,              # Sentinel instance (creates default if None)
    seed_level="standard",      # "minimal", "standard", "full"
    on_violation="log",         # "log", "block", "flag"
    check_input=True,           # Validate user messages
    check_output=True,          # Validate assistant messages
    message_key="messages",     # Key in state for messages
    max_text_size=50*1024,      # Max text size in bytes (50KB)
    fail_closed=False,          # Raise exception on errors
    logger=None,                # Custom logger instance
)
```

### SentinelGuardNode

```python
SentinelGuardNode(
    wrapped_node,               # Node function to wrap
    sentinel=None,              # Sentinel instance
    on_violation="block",       # "log", "block", "flag"
    max_text_size=50*1024,      # Max text size in bytes
    fail_closed=False,          # Raise exception on errors
    logger=None,                # Custom logger instance
)
```

### SentinelAgentExecutor

```python
SentinelAgentExecutor(
    graph,                      # Compiled LangGraph
    sentinel=None,              # Sentinel instance
    on_violation="block",       # "log", "block", "flag"
    max_text_size=50*1024,      # Max text size in bytes
    max_output_messages=5,      # Number of output messages to validate
    fail_closed=False,          # Raise exception on errors
    logger=None,                # Custom logger instance
)
```

## THSP Protocol

Every validation passes through four gates:

| Gate | Question | Blocks When |
|------|----------|-------------|
| **TRUTH** | Is this truthful? | Misinformation, fake claims, impersonation |
| **HARM** | Could this harm someone? | Violence, illegal activities, dangerous advice |
| **SCOPE** | Is this within bounds? | Jailbreaks, authority claims, persona hijacking |
| **PURPOSE** | Does this serve benefit? | Purposeless destruction, no legitimate value |

**Key Insight:** The Purpose gate is unique to THSP. Actions that pass harm checks may still fail purpose validation—"delete all records" causes harm, but even "reorganize files randomly" fails purpose without legitimate benefit.

## State Integration

The safety nodes add these fields to state:

```python
{
    "sentinel_safe": bool,          # True if all validations passed
    "sentinel_blocked": bool,       # True if blocked by on_violation="block"
    "sentinel_violations": list,    # List of violation descriptions
    "sentinel_risk_level": str,     # "low", "medium", "high"
}
```

Example:

```python
result = safety_node(state)

if not result["sentinel_safe"]:
    print(f"Violations: {result['sentinel_violations']}")
    print(f"Risk: {result['sentinel_risk_level']}")
```

## Conditional Routing

Route based on safety validation:

```python
from sentinelseed.integrations.langgraph import conditional_safety_edge

graph.add_conditional_edges(
    "safety_check",
    conditional_safety_edge,
    {
        "continue": "agent",
        "blocked": "safe_response",
    }
)
```

For custom route names, use `create_safety_router`:

```python
from sentinelseed.integrations.langgraph import create_safety_router

router = create_safety_router(
    safe_route="process",
    unsafe_route="reject"
)

graph.add_conditional_edges(
    "safety_check",
    router,
    {
        "process": "agent",
        "reject": "rejection_handler",
    }
)
```

## Adding Safety Layer to Existing Graphs

```python
from langgraph.graph import StateGraph, START, END
from sentinelseed.integrations.langgraph import add_safety_layer

graph = StateGraph(MyState)
graph.add_node("agent", agent_node)

# Add safety nodes
result = add_safety_layer(graph)

# Connect edges manually:
# START -> sentinel_entry -> agent -> sentinel_exit -> END
graph.add_edge(START, result["entry_node"])
graph.add_edge(result["entry_node"], "agent")
graph.add_edge("agent", result["exit_node"])
graph.add_edge(result["exit_node"], END)

compiled = graph.compile()
```

## Custom Logger

```python
from sentinelseed.integrations.langgraph import set_logger

class MyLogger:
    def debug(self, msg): print(f"[DEBUG] {msg}")
    def info(self, msg): print(f"[INFO] {msg}")
    def warning(self, msg): print(f"[WARN] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")

set_logger(MyLogger())
```

## Error Handling

### Exceptions

```python
from sentinelseed.integrations.langgraph import (
    TextTooLargeError,
    ValidationTimeoutError,
    SafetyValidationError,
)

try:
    result = safety_node(state)
except TextTooLargeError as e:
    print(f"Text size: {e.size}, max: {e.max_size}")
except SafetyValidationError as e:
    print(f"Validation failed: {e.violations}")
```

### Fail-Closed Mode

For strict environments, enable `fail_closed` to raise exceptions on validation errors:

```python
safety_node = SentinelSafetyNode(
    on_violation="block",
    fail_closed=True,  # Raise SafetyValidationError on any error
)
```

## Async Support

All components support async execution:

```python
# SentinelGuardNode with async wrapped node
async def async_tool_node(state):
    await some_async_operation()
    return state

guard = SentinelGuardNode(async_tool_node)
result = await guard.__acall__(state)

# SentinelAgentExecutor
executor = SentinelAgentExecutor(compiled_graph)
result = await executor.ainvoke(state)
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelSafetyNode` | Safety validation node |
| `SentinelGuardNode` | Wrapper for existing nodes with validation |
| `SentinelAgentExecutor` | Wrapper for compiled graphs |
| `SentinelState` | TypedDict with safety fields |
| `SafetyLayerResult` | Result of add_safety_layer |

### Functions

| Function | Description |
|----------|-------------|
| `sentinel_gate_tool(action)` | Validate an action, returns dict |
| `create_sentinel_tool()` | Create LangChain-compatible tool |
| `add_safety_layer(graph)` | Add safety nodes to graph |
| `conditional_safety_edge(state)` | Route based on safety state |
| `create_safety_router(safe, unsafe)` | Create custom router |
| `set_logger(logger)` | Set custom logger |
| `get_logger()` | Get current logger |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `TextTooLargeError` | Text exceeds max_text_size |
| `ValidationTimeoutError` | Validation timed out |
| `SafetyValidationError` | Validation failed (fail_closed mode) |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `DEFAULT_MAX_TEXT_SIZE` | 51200 | 50KB max text size |
| `DEFAULT_VALIDATION_TIMEOUT` | 30.0 | 30 second timeout |

## Links

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **LangGraph Concepts:** https://langchain-ai.github.io/langgraph/concepts/
- **Sentinel:** https://sentinelseed.dev
