# Virtuals Protocol Integration

Safety validation for AI agents built with the GAME SDK.

## Requirements

```bash
pip install sentinelseed[virtuals]
# or manually:
pip install sentinelseed game-sdk
```

**Dependencies:**
- `game-sdk>=0.1.1`: [PyPI](https://pypi.org/project/game-sdk/) | [GitHub](https://github.com/game-by-virtuals/game-python)

## Overview

This integration provides THSP Protocol validation for GAME SDK agents:

| Component | Description |
|-----------|-------------|
| `SentinelConfig` | Configuration for validation rules |
| `SentinelValidator` | Core THSP validation engine |
| `SentinelSafetyWorker` | Worker that validates agent actions |
| `create_sentinel_function` | Wrap individual functions |
| `wrap_functions_with_sentinel` | Wrap multiple functions |
| `sentinel_protected` | Decorator for executables |

## Usage

### Option 1: Add Safety Worker to Agent

```python
from game_sdk.game.agent import Agent
from sentinelseed.integrations.virtuals import (
    SentinelConfig,
    SentinelSafetyWorker,
)

# Configure limits
config = SentinelConfig(
    max_transaction_amount=500.0,
    require_confirmation_above=100.0,
    block_unsafe=True,
)

# Create safety worker
safety_worker = SentinelSafetyWorker.create_worker_config(config)

# Add to agent (place first in workers list)
agent = Agent(
    api_key=api_key,
    name="SafeAgent",
    agent_goal="Execute safe operations",
    agent_description="Agent with Sentinel validation",
    get_agent_state_fn=get_state,
    workers=[safety_worker, your_other_worker],
)
```

### Option 2: Wrap Individual Functions

```python
from game_sdk.game.custom_types import Function, Argument, FunctionResultStatus
from sentinelseed.integrations.virtuals import create_sentinel_function

# Your original function
def transfer_tokens(recipient: str, amount: float):
    return (FunctionResultStatus.DONE, f"Transferred {amount}", {})

transfer_fn = Function(
    fn_name="transfer_tokens",
    fn_description="Transfer tokens",
    args=[
        Argument(name="recipient", description="Wallet address", type="string"),
        Argument(name="amount", description="Amount", type="number"),
    ],
    executable=transfer_tokens,
)

# Wrap with Sentinel
safe_transfer_fn = create_sentinel_function(transfer_fn, config)
```

### Option 3: Decorator

```python
from sentinelseed.integrations.virtuals import sentinel_protected

@sentinel_protected(config=SentinelConfig(max_transaction_amount=100))
def my_transfer(recipient: str, amount: float):
    return (FunctionResultStatus.DONE, "Success", {})
```

## Configuration

```python
SentinelConfig(
    # Behavior
    block_unsafe=True,              # Block or log unsafe actions
    log_validations=True,           # Log validation results

    # Transaction limits
    max_transaction_amount=1000.0,  # Max per transaction
    require_confirmation_above=100.0,

    # PURPOSE gate
    require_purpose_for=[           # Actions requiring explicit purpose
        "transfer", "send", "approve", "swap", "bridge", "withdraw"
    ],

    # Function control
    allowed_functions=[],           # Whitelist (empty = all)
    blocked_functions=[             # Always blocked
        "drain_wallet",
        "send_all_tokens",
        "approve_unlimited",
        "export_private_key",
    ],

    # Pattern detection
    suspicious_patterns=[
        r"(?i)private[_\s]?key",
        r"(?i)seed[_\s]?phrase",
        r"(?i)drain[_\s]?wallet",
        r"0x[fF]{64}",              # Max uint256
    ],

    # Memory integrity (defense against injection attacks)
    memory_integrity_check=False,   # Enable memory signing/verification
    memory_secret_key=None,         # Secret key for HMAC signatures
)
```

## THSP Gates

Every action passes through four validation gates:

| Gate | Function | Blocks When |
|------|----------|-------------|
| **TRUTH** | Verify factual accuracy | Context manipulation, misleading names |
| **HARM** | Assess damage potential | Blocked functions, suspicious patterns, key exposure |
| **SCOPE** | Check boundaries | Amount exceeds limit, non-whitelisted functions |
| **PURPOSE** | Require justification | Sensitive actions without stated purpose |

## Safety Worker Functions

The `SentinelSafetyWorker` exposes functions to the agent (plus `verify_memory_integrity` when memory is enabled):

### check_action_safety

```python
# Agent can call before executing sensitive operations
status, message, info = check_action_safety(
    action_name="transfer",
    action_args='{"amount": 100, "recipient": "..."}',
    purpose="User requested payment"
)
# Returns tuple: (FunctionResultStatus, message: str, info: dict)
# info contains: safe (bool), concerns (list), gate_results (dict), blocked_gate (str|None)
```

### get_safety_statistics

```python
# Get validation stats
status, message, stats = get_safety_statistics()
# Returns tuple: (FunctionResultStatus, message: str, stats: dict)
# stats contains: total (int), passed (int), blocked (int), pass_rate (float)
```

## Fiduciary Validation

The integration includes optional **Fiduciary Validation** to ensure agent actions align with user interests. This is enabled by default when the fiduciary module is available.

### Enabling/Disabling

```python
from sentinelseed.integrations.virtuals import SentinelValidator

# Enabled by default (when module available)
validator = SentinelValidator()

# Explicitly disable
validator = SentinelValidator(fiduciary_enabled=False)

# Strict mode: block on fiduciary violations
validator = SentinelValidator(strict_fiduciary=True)
```

### Custom User Context

```python
from sentinelseed.integrations.virtuals import (
    SentinelValidator,
    UserContext,
    RiskTolerance,
)

# Define custom user preferences
context = UserContext(
    goals=["maximize trading profits", "minimize fees"],
    constraints=["never trade memecoins", "max 10% portfolio per trade"],
    risk_tolerance=RiskTolerance.HIGH,  # LOW, MODERATE, HIGH
    preferences={
        "max_slippage": 0.03,
        "require_confirmation_above": 500.0,
    },
)

validator = SentinelValidator(user_context=context)

# Update context at runtime
new_context = UserContext(risk_tolerance=RiskTolerance.LOW)
validator.update_user_context(new_context)
```

### Fiduciary Stats

```python
stats = validator.get_fiduciary_stats()
# Returns: {
#   "enabled": bool,
#   "strict": bool,
#   "validator_stats": {...}
# }
```

## Memory Integrity

Defends against memory injection attacks (Princeton CrAIBench found 85% success rate on unprotected agents).

### Enabling Memory Integrity

```python
from sentinelseed.integrations.virtuals import SentinelConfig, SentinelSafetyWorker

config = SentinelConfig(
    memory_integrity_check=True,
    memory_secret_key="your-secret-key",  # For HMAC signing
)

worker = SentinelSafetyWorker(config)
```

### Signing State Entries

```python
# Sign a state entry
signed = worker.sign_state_entry(
    key="balance",
    value=1000.0,
    source="agent_internal",  # user_direct, user_verified, external_api, blockchain
)
# Returns: {"key": ..., "value": ..., "signed": True, "_sentinel_integrity": {...}}
```

### Verifying State Integrity

```python
# Verify a single entry
result = worker.verify_state_entry(signed_entry)
# Returns: {"valid": bool, "reason": str, "trust_score": float}

# Verify entire state
result = worker.verify_state(state_dict)
# Returns: {"all_valid": bool, "checked": int, "results": {...}}

# Get memory stats
stats = worker.get_memory_stats()
# Returns: {"enabled": True, "total": ..., "valid": ..., "invalid": ...}
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelConfig` | Dataclass for validation configuration |
| `SentinelValidator` | Core validation engine with THSP + Fiduciary |
| `SentinelSafetyWorker` | Creates WorkerConfig for agents |
| `ValidationResult` | Result from validation (passed, gate_results, concerns, blocked_gate) |
| `THSPGate` | Enum: TRUTH, HARM, SCOPE, PURPOSE |
| `SentinelValidationError` | Exception for blocked actions (gate, concerns) |
| `UserContext` | User preferences for fiduciary validation |
| `RiskTolerance` | Enum: LOW, MODERATE, HIGH |

### Functions

| Function | Description |
|----------|-------------|
| `create_sentinel_function(fn, config)` | Wrap a Function with validation |
| `wrap_functions_with_sentinel(fns, config)` | Wrap multiple Functions |
| `sentinel_protected(config)` | Decorator for executables |

### SentinelSafetyWorker Methods

| Method | Description |
|--------|-------------|
| `check_action_safety(name, args, purpose)` | Check if action is safe |
| `get_safety_stats()` | Get validation statistics |
| `sign_state_entry(key, value, source)` | Sign state for integrity |
| `verify_state_entry(entry)` | Verify signed entry |
| `verify_state(state)` | Verify all signed entries |
| `get_memory_stats()` | Get memory integrity stats |

### SentinelValidator Methods

| Method | Description |
|--------|-------------|
| `validate(action_name, action_args, context)` | Validate through THSP gates |
| `get_stats()` | Get validation statistics |
| `get_fiduciary_stats()` | Get fiduciary validation stats |
| `update_user_context(context)` | Update UserContext at runtime |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `GAME_SDK_AVAILABLE` | bool | Whether game-sdk is installed |
| `MEMORY_INTEGRITY_AVAILABLE` | bool | Whether memory module is available |
| `FIDUCIARY_AVAILABLE` | bool | Whether fiduciary module is available |

## Examples

See `example.py` for complete working examples:

1. Basic THSP validation (no SDK required)
2. Decorator usage
3. Custom configuration
4. GAME SDK integration
5. Safety worker demo

## Links

- **GAME SDK:** https://docs.game.virtuals.io/
- **game-sdk PyPI:** https://pypi.org/project/game-sdk/
- **game-sdk GitHub:** https://github.com/game-by-virtuals/game-python
- **Sentinel:** https://sentinelseed.dev
