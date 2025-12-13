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

## Available Aliases

```python
from sentinelseed.integrations.autogpt import (
    ValidationResult,          # From agent_validation
    SafetyValidator,           # From agent_validation
    ExecutionGuard,            # From agent_validation
    safety_check,              # From agent_validation

    # Backward compatibility
    SafetyCheckResult,         # = ValidationResult
    SentinelSafetyComponent,   # = SafetyValidator
    SentinelGuard,             # = ExecutionGuard
)
```

## Legacy Plugin Template

For very old AutoGPT versions (pre-v0.5), a plugin template is available:

```python
from sentinelseed.integrations.autogpt import AutoGPTPluginTemplate

plugin = AutoGPTPluginTemplate()

# Hook methods
plugin.pre_command(command_name, arguments)
plugin.post_command(command_name, response)
plugin.on_planning(prompt, messages)
```

**Note:** This plugin template is not compatible with current AutoGPT versions.

## See Instead

- [agent_validation README](../agent_validation/README.md)
- [Sentinel Documentation](https://sentinelseed.dev/docs)
