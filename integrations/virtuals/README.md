# Sentinel Safety Plugin for Virtuals Protocol

> Safety guardrails for AI agents built on the GAME SDK

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Overview

This plugin integrates Sentinel's THSP Protocol (Truth, Harm, Scope, Purpose) with Virtuals Protocol's GAME SDK, providing safety validation for autonomous AI agents operating on-chain.

**Why is this needed?**

AI agents on Virtuals Protocol can execute financial transactions, interact with smart contracts, and manage crypto assets. Without proper guardrails, these agents are vulnerable to:

- **Prompt injection attacks** that manipulate agent behavior
- **Memory injection** that corrupts agent context
- **Unauthorized transactions** draining wallets
- **Phishing vectors** through misleading action names

## Features

- **THSP Protocol Validation**: Every action passes through four gates
  - **Truth**: Verify factual correspondence
  - **Harm**: Assess potential for damage
  - **Scope**: Check appropriate boundaries
  - **Purpose**: Require legitimate benefit

- **Financial Safety**:
  - Transaction amount limits
  - Confirmation requirements for large transfers
  - Private key/seed phrase detection
  - Unlimited approval blocking

- **Integration Options**:
  - Function wrapper for individual GAME Functions
  - Batch wrapping for action spaces
  - Dedicated Safety Worker
  - Decorator for custom executables

## Installation

```bash
# Install GAME SDK
pip install game-sdk

# Sentinel integration (optional, for package usage)
pip install sentinelseed
```

## Quick Start

### Option 1: Add Safety Worker to Agent (Recommended)

The Safety Worker provides a `check_action_safety` function that other workers can call before executing sensitive operations.

```python
import os
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import Function, Argument, FunctionResultStatus
from sentinel.integrations.virtuals import SentinelSafetyWorker, SentinelConfig

# Create safety worker
config = SentinelConfig(
    max_transaction_amount=500.0,
    require_confirmation_above=100.0,
    block_unsafe=True,
)
safety_worker = SentinelSafetyWorker.create_worker_config(config)

# Your other workers...
def get_state(fn_result, current_state):
    return {"balance": 1000}

trading_worker = WorkerConfig(
    id="trading_worker",
    worker_description="Executes token swaps",
    get_state_fn=get_state,
    action_space=[your_functions],
)

# Create agent with safety worker FIRST
agent = Agent(
    api_key=os.environ.get("GAME_API_KEY"),
    name="SafeTradingBot",
    agent_goal="Execute safe token operations",
    agent_description="A trading bot that validates all actions",
    get_agent_state_fn=lambda r, s: {"status": "active"},
    workers=[safety_worker, trading_worker],  # Safety first
)

agent.compile()
agent.run()
```

### Option 2: Wrap Individual Functions

```python
from game_sdk.game.custom_types import Function, Argument, FunctionResultStatus
from sentinel.integrations.virtuals import create_sentinel_function, SentinelConfig

# Define your function
def transfer_tokens(recipient: str, amount: float, purpose: str = ""):
    # Your transfer logic
    return (FunctionResultStatus.DONE, f"Transferred {amount}", {})

# Create GAME Function
transfer_fn = Function(
    fn_name="transfer_tokens",
    fn_description="Transfer tokens to a recipient",
    args=[
        Argument(name="recipient", description="Wallet address", type="string"),
        Argument(name="amount", description="Amount to send", type="number"),
        Argument(name="purpose", description="Reason for transfer", type="string", optional=True),
    ],
    executable=transfer_tokens,
)

# Wrap with Sentinel protection
config = SentinelConfig(max_transaction_amount=1000)
safe_transfer_fn = create_sentinel_function(transfer_fn, config)

# Use in your worker's action_space
```

### Option 3: Wrap All Functions in Action Space

```python
from sentinel.integrations.virtuals import wrap_functions_with_sentinel, SentinelConfig

# Your original action space
action_space = [transfer_fn, swap_fn, approve_fn, check_balance_fn]

# Wrap all with Sentinel
config = SentinelConfig(block_unsafe=True)
safe_action_space = wrap_functions_with_sentinel(action_space, config)

# Use in worker
worker = WorkerConfig(
    id="my_worker",
    worker_description="...",
    get_state_fn=get_state,
    action_space=safe_action_space,  # All functions now validated
)
```

### Option 4: Protect Custom Executables with Decorator

```python
from sentinel.integrations.virtuals import sentinel_protected, SentinelConfig
from game_sdk.game.custom_types import FunctionResultStatus

@sentinel_protected(config=SentinelConfig(max_transaction_amount=500))
def risky_transfer(recipient: str, amount: float, purpose: str = ""):
    """Transfer with Sentinel validation."""
    # Will be blocked if validation fails
    return (FunctionResultStatus.DONE, f"Transferred {amount}", {})
```

## Configuration

```python
from sentinel.integrations.virtuals import SentinelConfig

config = SentinelConfig(
    # Behavior
    block_unsafe=True,           # Block unsafe actions (vs just logging)
    log_validations=True,        # Log every validation result

    # Financial limits
    max_transaction_amount=1000.0,     # Maximum tokens per transaction
    require_confirmation_above=100.0,  # Require _confirmed=True above this

    # Pattern detection (added to defaults)
    suspicious_patterns=[
        r"(?i)private[_\s]?key",
        r"(?i)seed[_\s]?phrase",
        r"(?i)drain[_\s]?wallet",
        # ... your custom patterns
    ],

    # Whitelist (empty = allow all except blocked)
    allowed_functions=["swap", "transfer", "approve"],

    # Blacklist (always checked)
    blocked_functions=[
        "drain_wallet",
        "send_all_tokens",
        "export_private_key",
        "reveal_seed_phrase",
    ],
)
```

## THSP Protocol Gates

Every action is validated through four gates:

### 1. Truth Gate

Verifies factual correspondence and detects deception:

- Misleading function names (e.g., `safe_drain_wallet`)
- Context manipulation attempts
- Inconsistent arguments

### 2. Harm Gate

Assesses potential for damage:

- Blocked function detection
- Suspicious pattern matching
- Private key/seed phrase detection
- High-risk operation flagging

### 3. Scope Gate

Checks appropriate boundaries:

- Transaction amount limits
- Whitelist/blacklist enforcement
- Confirmation requirements

### 4. Purpose Gate

Requires teleological justification:

- High-risk actions must have stated purpose
- User authorization verification
- Legitimate benefit requirement

**Key insight**: The absence of harm is not sufficient — there must be genuine purpose.

## Error Handling

```python
from sentinel.integrations.virtuals import SentinelValidationError, sentinel_protected

@sentinel_protected()
def risky_action(amount: float):
    ...

try:
    risky_action(amount=10000)  # Exceeds limit
except SentinelValidationError as e:
    print(f"Blocked by gate: {e.gate}")
    print(f"Concerns: {e.concerns}")
    # Handle gracefully
```

When using with GAME SDK Functions, validation failures return:
```python
(FunctionResultStatus.FAILED, "Sentinel blocked: <concerns>", {"sentinel_blocked": True})
```

## Validation Statistics

```python
from sentinel.integrations.virtuals import SentinelValidator, SentinelConfig

config = SentinelConfig()
validator = SentinelValidator(config)

# After some validations...
stats = validator.get_stats()
# {"total": 10, "passed": 8, "blocked": 2, "pass_rate": 0.8}
```

## Best Practices

1. **Add Safety Worker first** in your workers list so the agent can self-validate

2. **Set appropriate limits** for your use case:
   ```python
   config = SentinelConfig(
       max_transaction_amount=your_max,
       require_confirmation_above=your_threshold,
   )
   ```

3. **Include purpose in high-risk actions**:
   ```python
   transfer(amount=100, purpose="User requested withdrawal")
   ```

4. **Log all validations** in production for audit trails

5. **Use whitelist mode** for critical agents:
   ```python
   config = SentinelConfig(
       allowed_functions=["swap", "get_balance"],  # Only these allowed
   )
   ```

## Security Considerations

- This plugin provides an additional safety layer but is not a complete security solution
- Always implement proper key management and access controls
- Audit all agent code before production deployment
- Monitor validation logs for suspicious patterns
- Consider rate limiting and circuit breakers

## Related Resources

- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [THSP Protocol](https://sentinelseed.dev/docs/thsp-protocol)
- [GAME SDK Documentation](https://docs.game.virtuals.io/)
- [Virtuals Protocol](https://virtuals.io)

## License

MIT License - See [LICENSE](../../../LICENSE)

---

**Sentinel** — Practical AI Alignment for Developers

[Website](https://sentinelseed.dev) • [GitHub](https://github.com/sentinel-seed/sentinel) • [Twitter](https://x.com/Sentinel_Seed)
