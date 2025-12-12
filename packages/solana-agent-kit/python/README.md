# Sentinel + Solana Agent Kit (Python)

Python validation layer for Solana Agent Kit workflows.

## Installation

```bash
pip install sentinelseed
```

## Usage

```python
from sentinel.integrations.solana_agent_kit import (
    SentinelValidator,
    safe_transaction,
    TransactionRisk,
)

# Create validator with custom limits
validator = SentinelValidator(
    max_transfer=100.0,      # Max 100 SOL per transaction
    confirm_above=10.0,      # Flag transfers above 10 SOL
    blocked_addresses=["ScamWallet123..."],
)

# Validate before executing
result = validator.check("transfer", amount=50, recipient="...")

if result.should_proceed:
    # Safe to execute transaction
    pass
else:
    print(f"Blocked: {result.concerns}")
```

## Pattern with Solana Agent Kit

```python
# 1. Validate with Sentinel
result = validator.check("transfer", amount=amount, recipient=recipient)

# 2. Execute only if safe
if result.should_proceed:
    tx_result = agent.transfer(recipient, amount)
else:
    print(f"Blocked: {result.concerns}")
```

## See Also

- [example.py](./example.py) - Full usage examples
- [TypeScript Plugin](../typescript/) - Native SAK v2 plugin
- [sentinelseed on PyPI](https://pypi.org/project/sentinelseed/)
