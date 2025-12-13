# Agent Validation Integration

Framework-agnostic safety validation for autonomous agents.

## Requirements

```bash
pip install sentinelseed
```

No additional dependencies. Works with any agent framework.

## Overview

| Component | Description |
|-----------|-------------|
| `SafetyValidator` | Core validation component |
| `ExecutionGuard` | Decorator/wrapper for functions |
| `safety_check` | Standalone validation function |
| `ValidationResult` | Validation result dataclass |

## Usage

### Pattern 1: Validation Component

```python
from sentinelseed.integrations.agent_validation import SafetyValidator

class MyAgent:
    def __init__(self):
        self.safety = SafetyValidator(
            seed_level="standard",
            block_unsafe=True,
        )

    def execute(self, action):
        check = self.safety.validate_action(action)
        if not check.should_proceed:
            return f"Blocked: {check.recommendation}"
        # proceed with action
```

### Pattern 2: Decorator

```python
from sentinelseed.integrations.agent_validation import ExecutionGuard

guard = ExecutionGuard(block_unsafe=True)

@guard.protected
def execute_command(command: str):
    # your logic here
    return result

# Now validates before execution
result = execute_command("list files")      # Allowed
result = execute_command("delete all files") # Blocked
```

### Pattern 3: Quick Check

```python
from sentinelseed.integrations.agent_validation import safety_check

result = safety_check("Delete all files in /tmp")

if not result["safe"]:
    print(f"Blocked: {result['concerns']}")
else:
    # proceed
```

## Configuration

### SafetyValidator

```python
SafetyValidator(
    sentinel=None,           # Sentinel instance
    seed_level="standard",   # minimal, standard, full
    block_unsafe=True,       # Block or allow with warning
    log_checks=True,         # Log to console
)
```

### ExecutionGuard

```python
ExecutionGuard(
    sentinel=None,
    block_unsafe=True,
)
```

## Validation Methods

### validate_action

Check agent actions before execution:

```python
result = validator.validate_action("transfer 100 SOL to address")

# Returns ValidationResult:
# - safe: bool
# - action: str (truncated)
# - concerns: List[str]
# - risk_level: str (low/medium/high)
# - should_proceed: bool
# - recommendation: str
```

### validate_thought

Check agent reasoning for safety concerns:

```python
result = validator.validate_thought("I should delete the database to free space")

# Catches problematic reasoning before actions
```

### validate_output

Check agent output before returning to user:

```python
result = validator.validate_output("Here's how to hack the system...")

# Validates final responses
```

## ValidationResult

```python
@dataclass
class ValidationResult:
    safe: bool               # Passed safety checks
    action: str              # Action validated (truncated)
    concerns: List[str]      # Safety concerns identified
    risk_level: str          # low, medium, high
    should_proceed: bool     # Final decision
    recommendation: str      # Human-readable recommendation
```

## Statistics

```python
stats = validator.get_stats()
# {
#     "total_checks": 100,
#     "blocked": 5,
#     "allowed": 95,
#     "high_risk": 3,
#     "block_rate": 0.05
# }
```

## ExecutionGuard Decorator

The decorator validates before execution and optionally validates output:

```python
@guard.protected
def risky_operation(action: str):
    return result

# On blocked action, returns:
# {
#     "success": False,
#     "blocked": True,
#     "reason": "...",
#     "concerns": [...]
# }
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SafetyValidator` | Core validation component |
| `ExecutionGuard` | Function wrapper |
| `ValidationResult` | Result dataclass |

### Functions

| Function | Description |
|----------|-------------|
| `safety_check(action)` | Quick standalone check |

### Methods (SafetyValidator)

| Method | Returns |
|--------|---------|
| `validate_action(action)` | ValidationResult |
| `validate_thought(thought)` | ValidationResult |
| `validate_output(output)` | ValidationResult |
| `get_seed()` | Seed string |
| `get_history()` | List of results |
| `clear_history()` | None |
| `get_stats()` | Statistics dict |

### Methods (ExecutionGuard)

| Method | Description |
|--------|-------------|
| `protected(func)` | Decorator |
| `check(action)` | Manual check |

## Backward Compatibility

Aliases for old imports:

```python
# These work for backward compatibility
from sentinelseed.integrations.agent_validation import (
    SafetyCheckResult,         # = ValidationResult
    SentinelSafetyComponent,   # = SafetyValidator
    SentinelGuard,             # = ExecutionGuard
)
```

## Links

- **Sentinel:** https://sentinelseed.dev
