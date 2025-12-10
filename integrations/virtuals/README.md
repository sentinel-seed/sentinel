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
  - Decorator for individual functions
  - Agent-wide wrapping
  - Standalone safety worker

## Installation

```bash
# Install GAME SDK
pip install game-sdk

# Sentinel is included via system prompt or sentinelseed package
pip install sentinelseed
```

## Quick Start

### Option 1: Wrap an Existing Agent

```python
from game_sdk.game import Agent, WorkerConfig
from sentinel.integrations.virtuals import wrap_agent_with_sentinel, SentinelWorkerConfig

# Create your agent as usual
agent = Agent(
    api_key="your-game-api-key",
    name="TradingBot",
    goal="Execute safe token swaps for the user",
    workers=[your_workers],
)

# Wrap with Sentinel protection
config = SentinelWorkerConfig(
    max_token_amount=500.0,        # Max tokens per transaction
    require_confirmation_above=50.0,  # Require confirmation above 50 tokens
    block_unsafe=True,              # Block (vs just log) unsafe actions
)

agent = wrap_agent_with_sentinel(agent, config)

# Agent now validates all actions through THSP Protocol
agent.compile()
agent.run()
```

### Option 2: Protect Individual Functions

```python
from sentinel.integrations.virtuals import sentinel_protected

@sentinel_protected(level="standard", block_on_failure=True)
def transfer_tokens(recipient: str, amount: float, purpose: str = "") -> dict:
    """Transfer tokens to a recipient."""
    # Your transfer logic here
    return {"status": "success", "amount": amount}

# Function will raise SentinelValidationError if validation fails
result = transfer_tokens(
    recipient="0x...",
    amount=100,
    purpose="Payment for services rendered"
)
```

### Option 3: Add Safety Worker to Agent

```python
from sentinel.integrations.virtuals import SentinelSafetyWorker

# Create safety worker config
safety_worker = SentinelSafetyWorker.create_worker_config()

# Add to your agent's workers
agent = Agent(
    api_key="your-key",
    name="SafeBot",
    goal="Execute operations safely",
    workers=[safety_worker, your_other_workers],
)

# The safety worker provides check_action_safety function
# Other workers can call it before sensitive operations
```

### Option 4: Create Safe Agent (All-in-One)

```python
from sentinel.integrations.virtuals import create_safe_agent, SentinelWorkerConfig

agent = create_safe_agent(
    api_key="your-game-api-key",
    name="TradingBot",
    goal="Execute safe token swaps",
    workers=[swap_worker, analysis_worker],
    sentinel_config=SentinelWorkerConfig(
        max_token_amount=100,
        seed_level="standard",
    ),
)

# Agent has safety worker + all functions wrapped
agent.compile()
agent.run()
```

## Configuration

```python
from sentinel.integrations.virtuals import SentinelWorkerConfig

config = SentinelWorkerConfig(
    # Behavior
    block_unsafe=True,           # Block unsafe actions (vs just logging)
    log_all_validations=True,    # Log every validation result
    seed_level="standard",       # minimal, standard, or full

    # Financial limits
    max_token_amount=1000.0,     # Maximum tokens in single transaction
    require_confirmation_above=100.0,  # Require _confirmed=True above this

    # Pattern detection (added to defaults)
    suspicious_patterns=[
        r"(?i)private[_\s]?key",
        r"(?i)seed[_\s]?phrase",
        # ... your custom patterns
    ],

    # Whitelist (empty = allow all)
    allowed_functions=["swap", "transfer", "approve"],

    # Blacklist (always checked)
    blocked_functions=[
        "drain_wallet",
        "send_all_tokens",
        "export_private_key",
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
from sentinel.integrations.virtuals import (
    SentinelValidationError,
    sentinel_protected,
)

@sentinel_protected(block_on_failure=True)
def risky_action(amount: float):
    ...

try:
    risky_action(amount=10000)  # Exceeds limit
except SentinelValidationError as e:
    print(f"Blocked by gate: {e.gate}")
    print(f"Concerns: {e.concerns}")
    # Handle gracefully
```

## Validation History

```python
from sentinel.integrations.virtuals import SentinelSafetyWorker

safety = SentinelSafetyWorker()

# After some validations...
history = safety.get_validation_history()
# [{"action": "transfer", "result": True, "concerns": []}, ...]

stats = safety.get_safety_stats()
# {"total": 10, "passed": 8, "blocked": 2, "pass_rate": 0.8}
```

## Best Practices

1. **Always wrap production agents** with `wrap_agent_with_sentinel()`

2. **Set appropriate limits** for your use case:
   ```python
   config = SentinelWorkerConfig(
       max_token_amount=your_max,
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
   config = SentinelWorkerConfig(
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
- [GAME SDK Documentation](https://whitepaper.virtuals.io/developer-documents/game-framework/agent-sdk)
- [Virtuals Protocol](https://virtuals.io)

## License

MIT License - See [LICENSE](../../../LICENSE)

---

**Sentinel** — Practical AI Alignment for Developers

[Website](https://sentinelseed.dev) • [GitHub](https://github.com/sentinel-seed/sentinel) • [Twitter](https://x.com/Sentinel_Seed)
