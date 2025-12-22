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
    module,                # Any DSPy module
    api_key="...",         # API key for validation
    provider="openai",     # "openai" or "anthropic"
    mode="block",          # "block", "flag", or "heuristic"
    max_text_size=51200,   # Max text size in bytes (50KB)
    timeout=30.0,          # Validation timeout in seconds
    fail_closed=False,     # Block on validation errors
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
    mode="block",
    timeout=30.0,
    fail_closed=False,
)
result = predictor(question="...")
```

#### SentinelChainOfThought

ChainOfThought with validation of **both reasoning AND output**.

Unlike `SentinelGuard` which validates only the output, `SentinelChainOfThought`
validates both the reasoning process and the final answer, ensuring harmful
content cannot hide in either component.

```python
from sentinelseed.integrations.dspy import SentinelChainOfThought

cot = SentinelChainOfThought(
    "problem -> solution",
    api_key="...",
    mode="block",
    validate_reasoning=True,   # Validate reasoning (default: True)
    validate_output=True,      # Validate output (default: True)
    reasoning_field="reasoning",  # Custom reasoning field name
    timeout=30.0,
    fail_closed=False,
)
result = cot(problem="...")

# Check which fields were validated
print(result.safety_fields_validated)  # ["reasoning", "solution"]
print(result.safety_field_results)     # {"reasoning": True, "solution": True}
print(result.safety_failed_fields)     # [] if all passed
```

**Why validate reasoning?**
- Reasoning can contain harmful content even if output is clean
- Reasoning may reveal malicious intent hidden in final answer
- Provides complete audit trail for safety decisions

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
safety_tool = create_sentinel_tool(
    api_key="...",
    timeout=30.0,
    fail_closed=False,
)

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

# Common safety metadata (all modules)
result.safety_passed    # bool: Did content pass all gates?
result.safety_gates     # dict: Individual gate results
result.safety_reasoning # str: Explanation
result.safety_method    # str: "semantic" or "heuristic"
result.safety_blocked   # bool: Was content blocked? (block mode)
result.safety_issues    # list: Issues found

# Additional metadata for SentinelChainOfThought
result.safety_fields_validated  # list: Fields that were validated ["reasoning", "answer"]
result.safety_field_results     # dict: Per-field results {"reasoning": True, "answer": False}
result.safety_failed_fields     # list: Fields that failed validation ["answer"]
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

## Safety Options

### Timeout Configuration

Configure validation timeout to prevent hangs:

```python
guard = SentinelGuard(
    module,
    timeout=10.0,  # 10 second timeout
)
```

### Text Size Limits

Prevent DoS attacks by limiting input text size:

```python
guard = SentinelGuard(
    module,
    max_text_size=10 * 1024,  # 10KB limit
)
```

### Fail-Closed Mode

By default, validation errors allow content through (fail-open). Enable `fail_closed=True` for stricter behavior:

```python
guard = SentinelGuard(
    module,
    fail_closed=True,  # Block on any validation error
)
```

## Async Support

All modules support async operations via `aforward`:

```python
# Async usage
result = await safe_module.aforward(question="...")
```

## Error Handling

```python
from sentinelseed.integrations.dspy import (
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidParameterError,
    DSPyNotAvailableError,
)

# TextTooLargeError includes size details
try:
    result = guard(question="x" * 100000)
except TextTooLargeError as e:
    print(f"Size: {e.size}, Max: {e.max_size}")

# ValidationTimeoutError includes timeout info
try:
    result = guard(question="...", timeout=0.001)
except ValidationTimeoutError as e:
    print(f"Timeout after {e.timeout}s on {e.operation}")

# InvalidParameterError includes valid values
try:
    guard = SentinelGuard(module, mode="invalid")
except InvalidParameterError as e:
    print(f"Invalid {e.param}: {e.value}. Valid: {e.valid_values}")

# DSPyNotAvailableError if dspy not installed
try:
    from sentinelseed.integrations.dspy import require_dspy
    require_dspy()
except DSPyNotAvailableError:
    print("DSPy is not installed")
```

## Graceful Degradation

The integration works even when DSPy is not installed:

```python
from sentinelseed.integrations.dspy import DSPY_AVAILABLE

if DSPY_AVAILABLE:
    from sentinelseed.integrations.dspy import SentinelGuard
    # Use DSPy integration
else:
    # DSPy not installed, use alternative
    print("DSPy not available")
```

## Constants

```python
from sentinelseed.integrations.dspy import (
    DSPY_AVAILABLE,              # bool: Is DSPy installed?
    DEFAULT_SEED_LEVEL,          # "standard"
    DEFAULT_MAX_TEXT_SIZE,       # 51200 (50KB)
    DEFAULT_VALIDATION_TIMEOUT,  # 30.0 seconds
    VALID_SEED_LEVELS,           # ("minimal", "standard", "full")
    VALID_MODES,                 # ("block", "flag", "heuristic")
    VALID_PROVIDERS,             # ("openai", "anthropic")
    VALID_GATES,                 # ("truth", "harm", "scope", "purpose")
)
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
guard = SentinelGuard(module, fail_closed=True)
tool = create_sentinel_tool(fail_closed=True)
```

### Shared Executor

All validation operations use a shared `ValidationExecutor` singleton instead of creating new thread pools per call:

- Reduces thread creation overhead
- Limits maximum concurrent validation threads (default: 4)
- Automatically cleaned up on process exit

### Async Timeout Handling

Async methods (`aforward`) use `asyncio.wait_for()` with the same controlled thread pool as sync operations:

- Does not block the event loop
- Proper timeout handling
- Thread pool size is bounded

### Text Size Limits

Prevent DoS attacks by limiting input text size (default: 50KB):

```python
guard = SentinelGuard(module, max_text_size=10 * 1024)  # 10KB
```

## Performance Notes

### Shared ValidationExecutor

The integration uses a shared `ValidationExecutor` singleton:

- Lazy initialization (executor created on first use)
- Thread pool reused across all validation calls
- Automatic cleanup via `atexit` registration

### Async Operations

Async methods use the shared thread pool via `asyncio.wrap_future()`:

- No additional threads created for async calls
- Proper cancellation support on timeout
- Same timeout behavior as sync operations

## Degradation Signals

Results include flags to distinguish successful validation from degraded modes:

```python
result = safe_module(question="...")

# Degradation metadata
result.safety_degraded    # bool: Was validation degraded (error/timeout/fallback)?
result.safety_confidence  # str: "none", "low", "medium", or "high"
```

| Confidence | Meaning |
|------------|---------|
| `none` | No validation performed (error/timeout in fail-open) |
| `low` | Heuristic validation only (~50% accuracy) |
| `medium` | Semantic validation with uncertainty |
| `high` | Full semantic validation completed |

**Important:** `safety_passed=True` with `safety_confidence="none"` means content
was NOT validated but allowed through due to fail-open mode.

## Heuristic Fallback Control

By default, components require an API key for semantic validation:

```python
# This raises HeuristicFallbackError
guard = SentinelGuard(module, mode="block")  # No API key!

# Option 1: Provide API key
guard = SentinelGuard(module, api_key="sk-...", mode="block")

# Option 2: Explicitly allow fallback
guard = SentinelGuard(module, mode="block", allow_heuristic_fallback=True)

# Option 3: Use heuristic intentionally
guard = SentinelGuard(module, mode="heuristic")
```

When `allow_heuristic_fallback=True`:
- `safety_degraded=True` indicates fallback occurred
- `safety_confidence="low"` indicates heuristic was used

## Limitations

- **Text size limit**: Default 50KB per request. Configure with `max_text_size`.
- **Timeout**: Default 30s for validation. Configure with `timeout`.
- **Heuristic mode**: Less accurate (~50%) compared to semantic mode (~90%).
- **Semantic mode**: Requires API key and incurs API costs.
- **Fail-open default**: Validation errors allow content through by default. Use `fail_closed=True` for stricter security.

## Agent Modules

### SentinelToolValidator

Validates tool/function calls before execution.

```python
from sentinelseed.integrations.dspy import SentinelToolValidator

validator = SentinelToolValidator(
    api_key="sk-...",
    validate_args=True,    # Validate tool arguments
    validate_output=False, # Optionally validate outputs
)

# Wrap any tool function
@validator.wrap
def search_web(query: str) -> str:
    return web_search(query)

# Tool calls are validated before execution
result = search_web(query="how to make cookies")

# Or validate without executing
validation = validator.validate_call(
    tool_name="search_web",
    args=(),
    kwargs={"query": "suspicious query"}
)
```

### SentinelAgentGuard

Validates each step of agent execution.

```python
from sentinelseed.integrations.dspy import SentinelAgentGuard

agent = dspy.ReAct("task -> result", tools=[...])

# Wrap agent with step-by-step validation
safe_agent = SentinelAgentGuard(
    agent,
    api_key="sk-...",
    validate_input=True,   # Validate agent input
    validate_steps=True,   # Validate intermediate steps
    validate_output=True,  # Validate final output
    step_callback=lambda n, content, result: print(f"Step {n}: {'SAFE' if result['is_safe'] else 'UNSAFE'}")
)

result = safe_agent(task="Research topic X")

# Access validation details
print(result.safety_step_validations)  # All step validations
print(result.safety_steps_validated)   # Number of steps validated
```

### SentinelMemoryGuard

Validates data before writing to agent memory.

```python
from sentinelseed.integrations.dspy import SentinelMemoryGuard

memory_guard = SentinelMemoryGuard(api_key="sk-...")

# Validate before writing
validation = memory_guard.validate_write(
    key="user_preferences",
    value={"theme": "dark", "notifications": True}
)

if validation["is_safe"]:
    memory.write(key, value)

# Or wrap entire memory object
safe_memory = memory_guard.wrap_memory(memory)
safe_memory.set("key", "value")  # Automatically validated

# Check blocked writes
print(safe_memory.blocked_writes)
```

### Context-Aware Validation

All modules support context for better understanding:

```python
# Static context (set once)
guard = SentinelGuard(
    module,
    api_key="sk-...",
    context="User is a cybersecurity professional doing authorized testing"
)

# Dynamic context (per-call)
result = guard(
    question="How do I test for SQL injection?",
    _context="Authorized penetration testing engagement"
)
```

## Roadmap

| Feature | Description | Status |
|---------|-------------|--------|
| **Context-aware validation** | Pass prompt history, agent context | ✅ Implemented |
| **Tool call validation** | Validate agent tool/function calls | ✅ Implemented |
| **Step-by-step agent validation** | Validate each agent step | ✅ Implemented |
| **Memory write validation** | Validate agent memory updates | ✅ Implemented |
| **THSP as DSPy metric** | Use safety as optimization objective | Research |
| **Adversarial validation** | Test against adversarial variations | Research |
| **Behavioral drift detection** | Track safety changes over time | Research |

### Contributing

Contributions welcome! See the main Sentinel repository for guidelines.

## References

- [DSPy Documentation](https://dspy.ai/)
- [DSPy GitHub](https://github.com/stanfordnlp/dspy)
- [Sentinel Documentation](https://sentinelseed.dev)
