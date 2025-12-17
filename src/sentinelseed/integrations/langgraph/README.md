# LangGraph Integration

Safety nodes for LangGraph state machines.

## Requirements

```bash
pip install sentinelseed[langgraph]
# or manually:
pip install sentinelseed langgraph
```

**Dependencies:**
- `langgraph>=0.0.1` — [Docs](https://langchain-ai.github.io/langgraph/)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelSafetyNode` | Node that validates state/messages |
| `SentinelCheckpoint` | Safety checkpoint for workflows |
| `create_safe_graph` | Add safety to existing graphs |
| `sentinel_edge` | Conditional edge based on safety |

## Usage

### Option 1: Safety Node

Add safety validation as a graph node:

```python
from langgraph.graph import StateGraph
from sentinelseed.integrations.langgraph import SentinelSafetyNode

# Create safety node
safety_node = SentinelSafetyNode(
    seed_level="standard",
    block_unsafe=True,
    validate_messages=True,
)

# Add to graph
graph = StateGraph(State)
graph.add_node("safety_check", safety_node.run)
graph.add_node("llm", llm_node)

# Route through safety
graph.add_edge(START, "safety_check")
graph.add_conditional_edges(
    "safety_check",
    safety_node.should_continue,
    {"continue": "llm", "blocked": END}
)
```

### Option 2: Wrap Existing Graph

```python
from sentinelseed.integrations.langgraph import create_safe_graph

# Your existing graph
workflow = StateGraph(State)
workflow.add_node("agent", agent_node)
workflow.add_edge(START, "agent")

# Add safety layer
safe_workflow = create_safe_graph(
    workflow,
    validate_input=True,
    validate_output=True,
)

app = safe_workflow.compile()
```

### Option 3: Safety Checkpoint

```python
from sentinelseed.integrations.langgraph import SentinelCheckpoint

checkpoint = SentinelCheckpoint(
    checkpoint_id="pre_action",
    validation_type="action",  # action, content, both
)

# Use in node
def my_node(state):
    check = checkpoint.validate(state)
    if not check.safe:
        return {"blocked": True, "reason": check.concerns}
    # proceed
```

## Configuration

### SentinelSafetyNode

```python
SentinelSafetyNode(
    sentinel=None,
    seed_level="standard",
    block_unsafe=True,
    validate_messages=True,      # Check message content
    validate_actions=True,       # Check planned actions
    inject_seed=False,           # Add seed to messages
    state_key="messages",        # Key for messages in state
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

### Purpose Gate Configuration

For financial or agentic workflows, require explicit purpose:

```python
safety_node = SentinelSafetyNode(
    require_purpose_for=["transfer", "delete", "execute", "approve"],
)

# In your state
class State(TypedDict):
    messages: List[dict]
    action_purpose: str  # Required for sensitive actions
```

## State Integration

The safety node works with LangGraph's state:

```python
from typing import TypedDict, List

class State(TypedDict):
    messages: List[dict]
    safe: bool
    safety_concerns: List[str]

# Safety node updates state
def safety_node(state: State) -> State:
    node = SentinelSafetyNode()
    result = node.validate_state(state)
    return {
        **state,
        "safe": result.safe,
        "safety_concerns": result.concerns,
    }
```

## Conditional Routing

Route based on safety validation:

```python
from sentinelseed.integrations.langgraph import sentinel_edge

graph.add_conditional_edges(
    "safety_check",
    sentinel_edge(
        safe_path="continue",
        unsafe_path="human_review",
        state_key="safe",
    )
)
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelSafetyNode` | Safety validation node |
| `SentinelCheckpoint` | Checkpoint for validation |
| `SafetyState` | TypedDict with safety fields |

### Functions

| Function | Description |
|----------|-------------|
| `create_safe_graph(graph)` | Wrap graph with safety |
| `sentinel_edge(safe, unsafe)` | Create conditional edge |
| `inject_seed_to_state(state)` | Add seed to state messages |

## Links

- **LangGraph Docs:** https://langchain-ai.github.io/langgraph/
- **LangGraph Concepts:** https://langchain-ai.github.io/langgraph/concepts/
- **Sentinel:** https://sentinelseed.dev
