# Solana Agent Kit Integration

Safety validation for Solana blockchain agents.

## Requirements

```bash
pip install sentinelseed
```

**Note:** This integration provides validation functions that work **alongside** Solana Agent Kit, not as a plugin. Solana Agent Kit plugins add actions, they don't intercept transactions.

**Solana Agent Kit:** [GitHub](https://github.com/sendaifun/solana-agent-kit) | [Docs](https://kit.sendai.fun/)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelValidator` | Core transaction validator |
| `safe_transaction` | Quick validation function |
| `create_sentinel_actions` | Actions for custom workflows |
| `create_langchain_tools` | LangChain tools for agents |
| `SentinelSafetyMiddleware` | Function wrapper |

## Usage

### Pattern 1: Explicit Validation

```python
from solana_agent_kit import SolanaAgentKit
from sentinelseed.integrations.solana_agent_kit import SentinelValidator

# Initialize both
agent = SolanaAgentKit(wallet, rpc_url, config)
validator = SentinelValidator(max_transfer=10.0)

# Validate before executing
result = validator.check(
    action="transfer",
    amount=5.0,
    recipient="ABC123...",
    purpose="Payment for services",
)

if result.should_proceed:
    agent.transfer(recipient, amount)
else:
    print(f"Blocked: {result.concerns}")
```

### Pattern 2: Quick Check

```python
from sentinelseed.integrations.solana_agent_kit import safe_transaction

result = safe_transaction(
    "transfer",
    amount=50.0,
    recipient="ABC...",
    purpose="User requested payment",
)

if result.should_proceed:
    # execute with your Solana Agent Kit
    pass
```

### Pattern 3: LangChain Tools

```python
from langchain.agents import create_react_agent
from solana_agent_kit import createSolanaTools
from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

# Get Solana tools
solana_tools = createSolanaTools(agent)

# Add Sentinel safety tools
safety_tools = create_langchain_tools()

# Combine for agent
all_tools = solana_tools + safety_tools
agent = create_react_agent(llm, all_tools)

# Agent can now call sentinel_check_transaction before transfers
```

### Pattern 4: Function Wrapper

```python
from sentinelseed.integrations.solana_agent_kit import SentinelSafetyMiddleware

middleware = SentinelSafetyMiddleware()

def my_transfer(amount, recipient):
    # your transfer logic
    pass

# Wrap function
safe_transfer = middleware.wrap(my_transfer, "transfer")

# Now validates before executing
safe_transfer(5.0, "ABC...")  # Validates then executes
```

## Configuration

### SentinelValidator

```python
SentinelValidator(
    seed_level="standard",
    max_transfer=100.0,          # Max SOL per transaction
    confirm_above=10.0,          # Require confirmation above
    blocked_addresses=[],        # Blocked wallet addresses
    allowed_programs=[],         # Whitelist (empty = all)
    require_purpose_for=[        # Actions needing purpose
        "transfer", "send", "approve", "swap", "bridge", "withdraw", "stake"
    ],
    memory_integrity_check=False,
    memory_secret_key=None,
)
```

## Validation Result

```python
@dataclass
class TransactionSafetyResult:
    safe: bool                   # Passed all checks
    risk_level: TransactionRisk  # LOW, MEDIUM, HIGH, CRITICAL
    transaction_type: str        # Action name
    concerns: List[str]          # Safety concerns
    recommendations: List[str]   # Suggested actions
    should_proceed: bool         # Final decision
    requires_confirmation: bool  # High-value flag
```

## Risk Levels

| Level | Blocks | Example |
|-------|--------|---------|
| `LOW` | No | Normal transactions |
| `MEDIUM` | No | Missing purpose, suspicious patterns |
| `HIGH` | Yes | Non-whitelisted program, Sentinel concerns |
| `CRITICAL` | Yes | Blocked address, exceeds max |

## Checks Performed

1. **Blocked addresses** — Recipient in blocklist
2. **Program whitelist** — Program ID allowed
3. **Transfer limits** — Amount within max
4. **PURPOSE gate** — Sensitive actions need purpose
5. **Sentinel validation** — THSP protocol check
6. **Pattern detection** — Drain, sweep, bulk transfers

## LangChain Tool

The `create_langchain_tools()` function creates:

```python
Tool(
    name="sentinel_check_transaction",
    description="Check if a Solana transaction is safe...",
    func=check_transaction,  # Parses "action amount recipient"
)
```

Agent usage:
```
Agent: I should check this transfer first.
Action: sentinel_check_transaction
Action Input: transfer 5.0 ABC123...
Observation: SAFE: transfer validated
Agent: Proceeding with transfer...
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelValidator` | Core validator |
| `TransactionSafetyResult` | Validation result |
| `TransactionRisk` | Risk level enum |
| `SentinelSafetyMiddleware` | Function wrapper |
| `TransactionBlockedError` | Exception for blocked |

### Functions

| Function | Description |
|----------|-------------|
| `safe_transaction(action, **params)` | Quick validation |
| `create_sentinel_actions()` | Action functions dict |
| `create_langchain_tools()` | LangChain Tool list |

### Methods (SentinelValidator)

| Method | Returns |
|--------|---------|
| `check(action, amount, recipient, ...)` | TransactionSafetyResult |
| `get_stats()` | Dict with totals |
| `clear_history()` | None |

## Links

- **Solana Agent Kit:** https://kit.sendai.fun/
- **Solana Agent Kit GitHub:** https://github.com/sendaifun/solana-agent-kit
- **Sentinel:** https://sentinelseed.dev
