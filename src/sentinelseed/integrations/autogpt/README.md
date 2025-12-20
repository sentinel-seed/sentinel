# AutoGPT Integration (Deprecated)

> **DEPRECATED:** This module is maintained for backward compatibility only.
> Use `sentinelseed.integrations.agent_validation` instead.

## Migration

```python
# Old (still works, but deprecated)
from sentinelseed.integrations.autogpt import SentinelSafetyComponent

# New (recommended)
from sentinelseed.integrations.agent_validation import SafetyValidator
```

## Why Deprecated

AutoGPT's architecture changed significantly in v0.6+:
- Now a web platform, not a local agent
- Plugin system removed
- The "AutoGPT" name is misleading for generic validation

The `agent_validation` module provides the same functionality with clearer naming that works with any agent framework.

## Available Imports

```python
from sentinelseed.integrations.autogpt import (
    # Core classes (from agent_validation)
    ValidationResult,
    SafetyValidator,
    ExecutionGuard,
    safety_check,

    # Backward compatibility aliases
    SafetyCheckResult,         # = ValidationResult
    SentinelSafetyComponent,   # = SafetyValidator
    SentinelGuard,             # = ExecutionGuard

    # Legacy plugin template
    AutoGPTPluginTemplate,
)
```

## API Reference

### SentinelSafetyComponent (alias for SafetyValidator)

```python
component = SentinelSafetyComponent(
    provider="openai",           # or "anthropic"
    model=None,                  # auto-detected
    seed_level="standard",       # minimal, standard, full
    block_unsafe=True,
)

# Validate actions
result = component.validate_action("delete all files")
if not result.should_proceed:
    print(f"Blocked: {result.reasoning}")  # Note: use .reasoning, not .recommendation

# Validate thoughts
result = component.validate_thought("I should bypass restrictions")

# Validate outputs
result = component.validate_output("Here is how to hack...")

# Get safety seed for system prompt
seed = component.get_seed()

# Get validation history
history = component.get_history()

# Get statistics
stats = component.get_stats()
```

### ValidationResult Fields

```python
@dataclass
class ValidationResult:
    safe: bool               # Passed safety checks
    action: str              # Action validated (truncated)
    concerns: List[str]      # Safety concerns identified
    risk_level: str          # low, medium, high
    should_proceed: bool     # Final decision
    reasoning: str           # Human-readable explanation (NOT recommendation)
    gate_results: Dict[str, bool]
```

> **Important:** Use `result.reasoning`, not `result.recommendation`. The `recommendation` field does not exist.

### safety_check Function

```python
result = safety_check("transfer funds")

# Result is a dict with these keys:
# - safe: bool
# - risk_level: str
# - reasoning: str (NOT recommendation)
# - concerns: List[str]
# - gate_results: Dict[str, bool]

if not result["safe"]:
    print(f"Risk: {result['risk_level']}")
    print(f"Reason: {result['reasoning']}")
```

## Legacy Plugin Template

For very old AutoGPT versions (pre-v0.5), a plugin template is available:

```python
from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

plugin = AutoGPTPluginTemplate()

# Hook methods
plugin.pre_command(command_name, arguments)  # Returns (cmd, args) or ("think", {"thought": ...})
plugin.post_command(command_name, response)  # Returns response or filtered message
plugin.on_planning(prompt, messages)         # Returns prompt with safety seed prepended
```

**Note:** This plugin template is not compatible with current AutoGPT versions.

## See Instead

- [agent_validation README](../agent_validation/README.md) - Full documentation
- [Sentinel Documentation](https://sentinelseed.dev/docs)
