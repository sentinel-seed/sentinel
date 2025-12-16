# Sentinel THSP Integration for DSPy

Integrate Sentinel's THSP (Truth-Harm-Scope-Purpose) safety validation into DSPy pipelines.

## Overview

[DSPy](https://dspy.ai/) is Stanford's framework for programming language models through declarative specifications. This integration adds safety validation to DSPy modules, ensuring outputs pass through THSP gates before being returned.

## Installation

```bash
pip install dspy sentinelseed
```

## Quick Start

```python
import dspy
from sentinelseed.integrations.dspy import SentinelGuard

# Configure DSPy
lm = dspy.LM("openai/gpt-4o-mini")
dspy.configure(lm=lm)

# Wrap any module with safety validation
base_module = dspy.ChainOfThought("question -> answer")
safe_module = SentinelGuard(
    base_module,
    api_key="sk-...",
    mode="block"
)

# Use as normal - outputs are validated automatically
result = safe_module(question="What is machine learning?")
print(result.answer)  # Safe output
print(result.safety_passed)  # True
```

## Components

### Modules

#### SentinelGuard

Wraps any DSPy module and validates its output.

```python
from sentinelseed.integrations.dspy import SentinelGuard

guard = SentinelGuard(
    module,           # Any DSPy module
    api_key="...",    # API key for validation
    provider="openai", # "openai" or "anthropic"
    mode="block",     # "block", "flag", or "heuristic"
)
```

**Modes:**
- `block`: Return blocked prediction if unsafe
- `flag`: Return original with safety metadata
- `heuristic`: Use pattern-based validation (no LLM)

#### SentinelPredict

Predict with built-in validation.

```python
from sentinelseed.integrations.dspy import SentinelPredict

predictor = SentinelPredict(
    "question -> answer",
    api_key="...",
    mode="block"
)
result = predictor(question="...")
```

#### SentinelChainOfThought

ChainOfThought with validation.

```python
from sentinelseed.integrations.dspy import SentinelChainOfThought

cot = SentinelChainOfThought(
    "problem -> solution",
    api_key="...",
    mode="block"
)
result = cot(problem="...")
```

### Signatures

Custom signatures for explicit THSP validation.

```python
import dspy
from sentinelseed.integrations.dspy import THSPCheckSignature

checker = dspy.Predict(THSPCheckSignature)
result = checker(content="...", context="...")

print(result.is_safe)
print(result.truth_gate)  # "pass" or "fail"
print(result.harm_gate)
print(result.scope_gate)
print(result.purpose_gate)
print(result.reasoning)
```

### Tools for ReAct

Tools for use with DSPy's ReAct agents.

```python
import dspy
from sentinelseed.integrations.dspy import create_sentinel_tool

# Create safety tool
safety_tool = create_sentinel_tool(api_key="...")

# Use with ReAct
agent = dspy.ReAct(
    "task -> result",
    tools=[safety_tool]
)
```

**Available Tools:**
- `create_sentinel_tool()`: Full THSP check
- `create_content_filter_tool()`: Filter unsafe content
- `create_gate_check_tool(gate)`: Check specific gate

## Output Metadata

All Sentinel modules add safety metadata to predictions:

```python
result = safe_module(question="...")

# Safety metadata
result.safety_passed    # bool: Did content pass all gates?
result.safety_gates     # dict: Individual gate results
result.safety_reasoning # str: Explanation
result.safety_method    # str: "semantic" or "heuristic"
result.safety_blocked   # bool: Was content blocked? (block mode)
result.safety_issues    # list: Issues found
```

## Validation Modes

### Semantic (LLM-based)

Uses an LLM to understand context and intent. High accuracy (~90%).

```python
guard = SentinelGuard(
    module,
    api_key="sk-...",
    provider="openai",  # or "anthropic"
    model="gpt-4o-mini",
)
```

### Heuristic (Pattern-based)

Uses regex patterns. No LLM needed, but lower accuracy (~50%).

```python
guard = SentinelGuard(
    module,
    mode="heuristic",
)
```

## Async Support

All modules support async operations:

```python
# Async usage
result = await safe_module.acall(question="...")
```

## Examples

See `example.py` for comprehensive examples:

```bash
python -m sentinelseed.integrations.dspy.example
```

## THSP Protocol

Content must pass all four gates:

| Gate | Question |
|------|----------|
| **Truth** | Does this involve deception? |
| **Harm** | Could this enable harm? |
| **Scope** | Is this within boundaries? |
| **Purpose** | Does this serve legitimate benefit? |

## References

- [DSPy Documentation](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [Sentinel Documentation](https://sentinelseed.dev)
