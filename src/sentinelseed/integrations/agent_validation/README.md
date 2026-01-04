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
| `SafetyValidator` | Core validation component (sync) |
| `AsyncSafetyValidator` | Async validation component |
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
            provider="openai",       # or "anthropic"
            model="gpt-4o-mini",     # optional, auto-detected
            seed_level="standard",
            log_checks=True,               # log blocked actions
            record_history=True,           # record for get_history()
            max_text_size=50 * 1024,       # 50KB limit
            history_limit=1000,            # max history entries
            validation_timeout=30.0,       # seconds
            fail_closed=False,             # fail-open by default
        )

    def execute(self, action):
        check = self.safety.validate_action(action)
        if not check.should_proceed:
            return f"Blocked: {check.reasoning}"
        # proceed with action
```

### Pattern 2: Decorator

```python
from sentinelseed.integrations.agent_validation import ExecutionGuard

guard = ExecutionGuard(
    provider="openai",
    validation_timeout=30.0,
)

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
    print(f"Blocked: {result['reasoning']}")
else:
    # proceed
```

## Configuration

### SafetyValidator

```python
SafetyValidator(
    provider="openai",           # "openai" or "anthropic"
    model=None,                  # auto-detected if None
    api_key=None,                # from environment if None
    seed_level="standard",       # "minimal", "standard", or "full"
    log_checks=True,             # log blocked actions to console
    record_history=True,         # record validations in history
    max_text_size=51200,         # 50KB default
    history_limit=1000,          # max history entries (>= 0)
    validation_timeout=30.0,     # timeout in seconds
    fail_closed=False,           # block on errors if True
    use_layered=True,            # use LayeredValidator (heuristic + semantic)
    use_heuristic=True,          # enable heuristic pre-validation
    validator=None,              # optional LayeredValidator for DI (testing)
)
```

**Note on logging vs history:**
- `log_checks`: Controls whether blocked actions are logged to console
- `record_history`: Controls whether validations are recorded for `get_history()`

These are independent. You can record history without logging, or vice versa.

### AsyncSafetyValidator

Same parameters as `SafetyValidator`, for async contexts:

```python
AsyncSafetyValidator(
    provider="openai",           # "openai" or "anthropic"
    model=None,                  # auto-detected if None
    api_key=None,                # from environment if None
    seed_level="standard",       # "minimal", "standard", or "full"
    log_checks=True,             # log blocked actions to console
    record_history=True,         # record validations in history
    max_text_size=51200,         # 50KB default
    history_limit=1000,          # max history entries (>= 0)
    validation_timeout=30.0,     # timeout in seconds
    fail_closed=False,           # block on errors if True
    use_layered=True,            # use LayeredValidator (heuristic + semantic)
    use_heuristic=True,          # enable heuristic pre-validation
    validator=None,              # optional AsyncLayeredValidator for DI (testing)
)
```

### ExecutionGuard

```python
ExecutionGuard(
    provider="openai",
    model=None,
    api_key=None,
    max_text_size=51200,
    validation_timeout=30.0,
    fail_closed=False,
    action_extractor=None,       # custom extraction function
)
```

## Validation Methods

### validate_action

Check agent actions before execution:

```python
result = validator.validate_action(
    action="transfer 100 SOL to address",
    purpose="User requested funds transfer",  # optional
)

# Returns ValidationResult:
# - safe: bool
# - action: str (truncated to 100 chars)
# - concerns: List[str]
# - risk_level: str (low/medium/high)
# - should_proceed: bool
# - reasoning: str
# - gate_results: Dict[str, bool]
```

**Note on `purpose` parameter:**
- When `purpose` is provided, it's combined with `action` for validation: `"{action} {purpose}"`
- Empty string (`purpose=""`) is treated the same as not passing `purpose`
- Both sync and async validators handle `purpose` identically

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
    reasoning: str           # Human-readable explanation
    gate_results: Dict[str, bool]  # Per-gate results
```

## Exception Handling

The module provides typed exceptions for error handling:

```python
from sentinelseed.integrations.agent_validation import (
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidProviderError,
)

try:
    result = validator.validate_action(very_long_text)
except TextTooLargeError as e:
    print(f"Text too large: {e.size} > {e.max_size}")
except ValidationTimeoutError as e:
    print(f"Timeout after {e.timeout}s")
```

## History and Statistics

```python
# Get validation history
history = validator.get_history()

# Clear history
validator.clear_history()

# Get statistics
stats = validator.get_stats()
# {
#     "total_checks": 100,
#     "blocked": 5,
#     "allowed": 95,
#     "high_risk": 3,
#     "block_rate": 0.05,
#     "provider": "openai",
#     "model": "gpt-4o-mini",
#     "history_limit": 1000,
#     "max_text_size": 51200,
#     "validation_timeout": 30.0,
#     "fail_closed": False
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
#     "concerns": [...],
#     "gate_results": {...}
# }
```

### Smart Action Extraction

The guard can extract actions from various input types:

```python
# From string (default)
@guard.protected
def execute(command: str): ...

# From dict with common keys (action, command, query, text, message, content)
@guard.protected
def process(data: dict): ...

# From objects with common attributes
@guard.protected
def handle(request: Request): ...

# With custom extractor
guard = ExecutionGuard(
    action_extractor=lambda *args, **kwargs: kwargs.get("query", "")
)
```

## Fail Modes

### fail_closed=False (default)

When validation encounters an error (network issues, API errors):
- Allows the action to proceed
- Logs a warning with the error
- Adds "fail-open" note to concerns

### fail_closed=True

When validation encounters an error:
- Blocks the action
- Returns error result with reasoning
- All gates marked as failed

```python
validator = SafetyValidator(fail_closed=True)
# Now errors = blocked actions
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SafetyValidator` | Core sync validation component |
| `AsyncSafetyValidator` | Async validation component |
| `ExecutionGuard` | Function wrapper/decorator |
| `ValidationResult` | Result dataclass |

### Exceptions

| Exception | Description |
|-----------|-------------|
| `TextTooLargeError` | Input exceeds max_text_size |
| `ValidationTimeoutError` | Validation exceeded timeout |
| `InvalidProviderError` | Invalid provider specified |

### Functions

| Function | Description |
|----------|-------------|
| `safety_check(action)` | Quick standalone check |

### Methods (SafetyValidator / AsyncSafetyValidator)

| Method | Returns |
|--------|---------|
| `validate_action(action, purpose)` | ValidationResult |
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
| `get_stats()` | Guard statistics |

### Constants

| Constant | Value | Description |
|----------|-------|-------------|
| `VALID_PROVIDERS` | ("openai", "anthropic") | Allowed providers |
| `DEFAULT_MAX_TEXT_SIZE` | 51200 | 50KB default |
| `DEFAULT_HISTORY_LIMIT` | 1000 | Default history size |
| `DEFAULT_VALIDATION_TIMEOUT` | 30.0 | Default timeout (seconds) |

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

## Limitations

- Requires API key for OpenAI or Anthropic
- Validation latency depends on LLM response time
- Text size limited to max_text_size (default 50KB)
- History is bounded by history_limit (default 1000)

## Links

- **Sentinel:** https://sentinelseed.dev
- **PyPI:** https://pypi.org/project/sentinelseed
- **GitHub:** https://github.com/sentinel-seed/sentinel
