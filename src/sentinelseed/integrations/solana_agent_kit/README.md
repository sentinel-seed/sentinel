# Solana Agent Kit Integration

Safety validation for Solana blockchain agents.

## Requirements

```bash
pip install sentinelseed
```

**Note:** This integration provides validation functions that work **alongside** Solana Agent Kit, not as a plugin. Solana Agent Kit plugins add actions, they don't intercept transactions.

**Dependencies:**
- `sentinelseed>=2.0.0`
- `langchain` (optional, for LangChain tools)

**Solana Agent Kit:** [GitHub](https://github.com/sendaifun/solana-agent-kit) | [Docs](https://docs.sendai.fun)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelValidator` | Core transaction validator |
| `safe_transaction` | Quick validation function |
| `create_sentinel_actions` | Actions for custom workflows |
| `create_langchain_tools` | LangChain tools for agents |
| `SentinelSafetyMiddleware` | Function wrapper |
| `is_valid_solana_address` | Address format validation |

## Quick Start

```python
from sentinelseed.integrations.solana_agent_kit import safe_transaction

result = safe_transaction(
    "transfer",
    amount=5.0,
    recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    purpose="Payment for services",
)

if result.should_proceed:
    # Execute with Solana Agent Kit
    pass
else:
    print(f"Blocked: {result.concerns}")
```

## Usage Patterns

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
from solana_agent_kit import create_solana_tools
from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

# Get Solana tools (from solana-agent-kit-py)
solana_tools = create_solana_tools(agent)

# Add Sentinel safety tools
safety_tools = create_langchain_tools()

# Combine for agent
all_tools = solana_tools + safety_tools
agent = create_react_agent(llm, all_tools)

# Agent can now call sentinel_check_transaction before transfers
```

### Pattern 4: Function Wrapper

```python
from sentinelseed.integrations.solana_agent_kit import (
    SentinelSafetyMiddleware,
    TransactionBlockedError,
)

middleware = SentinelSafetyMiddleware()

def my_transfer(amount, recipient):
    # your transfer logic
    pass

# Wrap function
safe_transfer = middleware.wrap(my_transfer, "transfer")

try:
    safe_transfer(5.0, "ABC...")  # Validates then executes
except TransactionBlockedError as e:
    print(f"Blocked: {e}")
```

## Configuration

### SentinelValidator

```python
from sentinelseed.integrations.solana_agent_kit import (
    SentinelValidator,
    AddressValidationMode,
)

SentinelValidator(
    # Core settings
    seed_level="standard",           # Sentinel seed level ("minimal", "standard", "full")
    max_transfer=100.0,              # Max SOL per transaction (see note below)
    confirm_above=10.0,              # Require confirmation above
    blocked_addresses=[],            # Blocked wallet addresses
    allowed_programs=[],             # Whitelist (empty = all)
    require_purpose_for=[            # Actions needing purpose
        "transfer", "send", "approve", "swap", "bridge", "withdraw", "stake"
    ],
    address_validation=AddressValidationMode.STRICT,  # IGNORE, WARN, or STRICT (default: STRICT for security)

    # Advanced settings
    max_history_size=1000,           # Max validation history entries
    strict_mode=False,               # Block any transaction with concerns
    custom_patterns=None,            # Additional SuspiciousPattern list
    on_validation=None,              # Callback after each validation
    validator=None,                  # Custom LayeredValidator (for testing)

    # Memory integrity
    memory_integrity_check=False,    # Enable cryptographic history verification
    memory_secret_key=None,          # Secret key for HMAC signatures

    # Fiduciary validation (see section below)
    fiduciary_enabled=True,          # Enable duty of loyalty/care checks
    user_context=None,               # UserContext for fiduciary validation
    strict_fiduciary=False,          # Block on any fiduciary violation
)
```

> **Important:** Default `max_transfer=100.0` SOL may be too high for many use cases.
> Always configure appropriate limits for your application.

### Address Validation Modes

| Mode | Behavior |
|------|----------|
| `IGNORE` | Don't validate address format |
| `WARN` | Log warning but allow transaction |
| `STRICT` | Reject invalid addresses with CRITICAL risk (default) |

```python
from sentinelseed.integrations.solana_agent_kit import is_valid_solana_address

# Validate address format (base58, 32-44 chars)
valid = is_valid_solana_address("7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
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
| `CRITICAL` | Yes | Blocked address, exceeds max, invalid address (strict) |

## Checks Performed

1. **Address validation:** Format check (base58, configurable mode)
2. **Blocked addresses:** Recipient in blocklist
3. **Program whitelist:** Program ID allowed
4. **Transfer limits:** Amount within max
5. **PURPOSE gate:** Sensitive actions need purpose
6. **Sentinel validation:** THSP protocol check
7. **Pattern detection:** Drain, sweep, bulk transfers
8. **Fiduciary validation:** User-aligned decision making (if enabled)

## Fiduciary Validation

Validates that transactions align with user's best interests (duty of loyalty/care).

### Enabling Fiduciary Validation

```python
from sentinelseed.integrations.solana_agent_kit import SentinelValidator

# Enabled by default with Solana-specific defaults
validator = SentinelValidator(fiduciary_enabled=True)

# Custom user context
from sentinelseed.fiduciary import UserContext, RiskTolerance

validator = SentinelValidator(
    fiduciary_enabled=True,
    user_context=UserContext(
        goals=["protect holdings", "minimize fees"],
        constraints=["max 10 SOL per day"],
        risk_tolerance=RiskTolerance.LOW,
    ),
    strict_fiduciary=True,  # Block any fiduciary violation
)
```

### Fiduciary Classes (re-exported)

| Class | Description |
|-------|-------------|
| `UserContext` | User goals, constraints, risk tolerance |
| `RiskTolerance` | LOW, MODERATE, HIGH, AGGRESSIVE |
| `FiduciaryValidator` | Core fiduciary validator |
| `FiduciaryResult` | Validation result with violations |

### Fiduciary Methods

| Method | Description |
|--------|-------------|
| `get_fiduciary_stats()` | Get fiduciary validation statistics |
| `update_user_context(ctx)` | Update user context at runtime |

### Checking Fiduciary Availability

```python
from sentinelseed.integrations.solana_agent_kit import HAS_FIDUCIARY

if HAS_FIDUCIARY:
    print("Fiduciary validation available")
```

## LangChain Tool

The `create_langchain_tools()` function creates:

```python
Tool(
    name="sentinel_check_transaction",
    description="Check if a Solana transaction is safe...",
    func=check_transaction,  # Parses "action amount recipient"
)
```

Input format: `"action amount recipient"`

Examples:
- `"transfer 5.0 ABC123..."`
- `"swap 10.0"`
- `"stake 100.0"`

Agent usage:
```
Agent: I should check this transfer first.
Action: sentinel_check_transaction
Action Input: transfer 5.0 ABC123...
Observation: SAFE: transfer validated
Agent: Proceeding with transfer...
```

## Running Examples

```bash
# Basic examples
python -m sentinelseed.integrations.solana_agent_kit.example

# All examples including statistics
python -m sentinelseed.integrations.solana_agent_kit.example --all
```

## API Reference

### Classes

| Class | Description |
|-------|-------------|
| `SentinelValidator` | Core validator |
| `TransactionSafetyResult` | Validation result dataclass |
| `TransactionRisk` | Risk level enum (LOW, MEDIUM, HIGH, CRITICAL) |
| `AddressValidationMode` | Address validation mode (IGNORE, WARN, STRICT) |
| `SuspiciousPattern` | Pattern definition for suspicious behavior detection |
| `SentinelSafetyMiddleware` | Function wrapper |
| `TransactionBlockedError` | Exception for blocked transactions |

### Functions

| Function | Description |
|----------|-------------|
| `safe_transaction(action, **params)` | Quick validation |
| `create_sentinel_actions()` | Action functions dict |
| `create_langchain_tools()` | LangChain Tool list |
| `is_valid_solana_address(addr)` | Validate address format |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `__version__` | str | Integration version (e.g., "2.1.0") |
| `HAS_FIDUCIARY` | bool | Whether fiduciary module is available |
| `DEFAULT_SUSPICIOUS_PATTERNS` | List[SuspiciousPattern] | Default crypto-specific patterns |
| `HIGH_RISK_ACTIONS` | List[str] | Actions that always trigger blocking |
| `ALLOWED_METADATA_KEYS` | Set[str] | Allowed keys for metadata sanitization |

### Methods (SentinelValidator)

| Method | Returns | Description |
|--------|---------|-------------|
| `check(action, amount, recipient, ...)` | TransactionSafetyResult | Validate transaction |
| `get_stats()` | Dict | Validation statistics |
| `clear_history()` | None | Clear validation history |
| `verify_transaction_history()` | Dict | Verify history integrity (if enabled) |
| `get_memory_stats()` | Dict | Memory integrity statistics |
| `get_fiduciary_stats()` | Dict | Fiduciary validation statistics |
| `update_user_context(ctx)` | None | Update fiduciary user context |
| `block_address(addr)` | None | Add address to blocklist |
| `unblock_address(addr)` | None | Remove address from blocklist |
| `get_config()` | Dict | Get current configuration |
| `update_config(...)` | None | Update configuration at runtime |

## Error Handling

```python
from sentinelseed.integrations.solana_agent_kit import (
    SentinelSafetyMiddleware,
    TransactionBlockedError,
)

middleware = SentinelSafetyMiddleware()
safe_fn = middleware.wrap(my_function, "transfer")

try:
    safe_fn(100.0, "recipient")
except TransactionBlockedError as e:
    # Handle blocked transaction
    print(f"Transaction blocked: {e}")
```

## Logging

Enable debug logging to see validation details:

```python
import logging
logging.getLogger("sentinelseed.solana_agent_kit").setLevel(logging.DEBUG)
```

## Links

- **Solana Agent Kit:** https://docs.sendai.fun
- **Solana Agent Kit GitHub:** https://github.com/sendaifun/solana-agent-kit
- **Sentinel:** https://sentinelseed.dev
