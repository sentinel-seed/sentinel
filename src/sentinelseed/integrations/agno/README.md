# Sentinel Integration for Agno

Enterprise-grade AI safety guardrails for [Agno](https://agno.com) multi-agent framework.

## Overview

This integration provides THSP-based (Truth, Harm, Scope, Purpose) guardrails that work natively with Agno's guardrail system. It validates agent inputs and outputs to prevent harmful, deceptive, or out-of-scope content.

## Features

- **THSP Protocol** - Four-gate validation (Truth, Harm, Scope, Purpose)
- **700+ Detection Patterns** - Comprehensive pattern matching
- **Jailbreak Detection** - Protection against prompt injection
- **Native Integration** - Extends Agno's `BaseGuardrail`
- **Async Support** - Works with both `run()` and `arun()`
- **Monitoring** - Violation tracking and statistics
- **Configurable** - Multiple safety levels and options

## Installation

```bash
pip install sentinelseed agno
```

Or with extras:

```bash
pip install "sentinelseed[agno]"
```

## Quick Start

```python
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from sentinelseed.integrations.agno import SentinelGuardrail

# Create agent with Sentinel guardrail
agent = Agent(
    name="Safe Assistant",
    model=OpenAIChat(id="gpt-4o-mini"),
    pre_hooks=[SentinelGuardrail()],
)

# Guardrail validates input automatically
response = agent.run("Hello! How can you help me?")
```

## Configuration

### SentinelGuardrail (Input Validation)

```python
from sentinelseed.integrations.agno import SentinelGuardrail

guardrail = SentinelGuardrail(
    seed_level="standard",       # 'minimal', 'standard', or 'full'
    block_on_failure=True,       # Block unsafe content
    max_text_size=100000,        # Max input size in bytes
    validation_timeout=5.0,      # Timeout in seconds
    fail_closed=False,           # Block on errors
    log_violations=True,         # Record violations
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seed_level` | str | "standard" | Safety level (minimal, standard, full) |
| `block_on_failure` | bool | True | Raise exception on unsafe content |
| `max_text_size` | int | 100,000 | Maximum input size in bytes |
| `validation_timeout` | float | 5.0 | Validation timeout in seconds |
| `fail_closed` | bool | False | Block on validation errors |
| `log_violations` | bool | True | Record violations for monitoring |
| `validator` | LayeredValidator | None | Custom validator for dependency injection |

### SentinelOutputGuardrail (Output Validation)

```python
from sentinelseed.integrations.agno import SentinelOutputGuardrail

guardrail = SentinelOutputGuardrail(
    seed_level="standard",
    max_text_size=100000,
    validation_timeout=5.0,
    log_violations=True,         # Record violations for monitoring
)

# Validate LLM output
result = guardrail.validate_output(response.content)
if not result["safe"]:
    print(f"Output flagged: {result['concerns']}")
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `seed_level` | str | "standard" | Safety level (minimal, standard, full) |
| `max_text_size` | int | 100,000 | Maximum output size in bytes |
| `validation_timeout` | float | 5.0 | Validation timeout in seconds |
| `log_violations` | bool | True | Record violations for monitoring |
| `validator` | LayeredValidator | None | Custom validator for dependency injection |

## Safety Levels

| Level | Description | Use Case |
|-------|-------------|----------|
| `minimal` | Core safety patterns | Low-risk applications, testing |
| `standard` | Balanced safety coverage | General production use |
| `full` | Maximum safety coverage | Security-critical applications |

Note: All levels use the same detection patterns (700+). The level affects the seed prompt injected into the model, not the validation patterns.

## Monitoring

### Tracking Violations

```python
guardrail = SentinelGuardrail(log_violations=True)

# ... use with agent ...

# Get recorded violations
violations = guardrail.get_violations()
for v in violations:
    print(f"Risk: {v['risk_level']}, Concerns: {v['concerns']}")
```

### Statistics

```python
stats = guardrail.get_stats()
print(f"Total: {stats['total_validations']}")
print(f"Blocked: {stats['blocked_count']}")
print(f"Avg time: {stats['avg_validation_time_ms']:.2f}ms")
print(f"Gate failures: {stats['gate_failures']}")
```

## Combining Guardrails

Use Sentinel alongside Agno's built-in guardrails:

```python
from agno.guardrails import PIIDetectionGuardrail
from sentinelseed.integrations.agno import SentinelGuardrail

agent = Agent(
    name="Secure Agent",
    model=model,
    pre_hooks=[
        PIIDetectionGuardrail(),    # Agno built-in
        SentinelGuardrail(),         # Sentinel THSP
    ],
)
```

## Async Usage

```python
# With agent.arun()
response = await agent.arun("Query")

# Direct async validation
result = await output_guardrail.async_validate_output(content)
```

## Error Handling

```python
from sentinelseed.integrations.agno import (
    SentinelGuardrail,
    ConfigurationError,
    ValidationTimeoutError,
    TextTooLargeError,
)

try:
    guardrail = SentinelGuardrail(max_text_size=-1)
except ConfigurationError as e:
    print(f"Invalid config: {e.parameter} - {e.reason}")

try:
    response = agent.run("query")
except InputCheckError as e:
    print(f"Input blocked by Sentinel: {e}")
```

## Security Considerations

### Fail-Open vs Fail-Closed

By default, `fail_closed=False` (fail-open):
- Validation errors allow content through
- Prioritizes availability over security
- Logs warnings for monitoring

For security-critical applications, use `fail_closed=True`:
- Validation errors block content
- Prioritizes security over availability

```python
# Security-critical configuration
guardrail = SentinelGuardrail(
    seed_level="full",
    block_on_failure=True,
    fail_closed=True,
)
```

## API Reference

### SentinelGuardrail

```python
class SentinelGuardrail:
    def check(self, run_input: RunInput) -> None: ...
    async def async_check(self, run_input: RunInput) -> None: ...
    def get_violations(self) -> list[dict]: ...
    def get_stats(self) -> dict: ...
    def clear_violations(self) -> None: ...
    def reset_stats(self) -> None: ...
```

### SentinelOutputGuardrail

```python
class SentinelOutputGuardrail:
    def validate_output(self, output: str | Any) -> dict: ...
    async def async_validate_output(self, output: str | Any) -> dict: ...
    def get_violations(self) -> list[dict]: ...
    def clear_violations(self) -> None: ...
```

### Validation Result

```python
{
    "safe": bool,              # Whether content passed
    "should_proceed": bool,    # Alias for safe
    "concerns": list[str],     # List of concerns
    "risk_level": str,         # low, medium, high, critical
    "gates": dict,             # THSP gate results
    "validation_time_ms": float,
    "error": str | None,       # Error message if any
}
```

## Examples

See `example.py` for complete examples:

```bash
python -m sentinelseed.integrations.agno.example
```

## Requirements

- Python 3.10+
- sentinelseed >= 2.0.0
- agno >= 2.0.0

## License

MIT License - see [LICENSE](../../../../LICENSE)

## Links

- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [Agno Documentation](https://docs.agno.com)
- [GitHub Repository](https://github.com/sentinel-seed/sentinel)
