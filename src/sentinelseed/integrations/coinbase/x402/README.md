# Sentinel x402 Payment Validation

THSP safety validation for [x402](https://github.com/coinbase/x402) payment protocol.

x402 is an HTTP-native payment protocol by Coinbase that enables AI agents to make autonomous payments. This integration adds Sentinel's THSP safety gates to ensure payments are validated before execution.

## Installation

```bash
pip install sentinelseed x402 httpx
```

For AgentKit integration:
```bash
pip install coinbase-agentkit
```

## Quick Start

### Basic Validation

```python
from sentinelseed.integrations.coinbase import (
    SentinelX402Middleware,
    PaymentRequirementsModel,
)

# Create middleware
middleware = SentinelX402Middleware()

# Validate a payment
result = middleware.validate_payment(
    endpoint="https://api.example.com/paid",
    payment_requirements=PaymentRequirementsModel(
        scheme="exact",
        network="base",
        max_amount_required="1000000",  # 1 USDC
        resource="https://api.example.com/paid",
        pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    ),
    wallet_address="0x123...",
)

if result.is_approved:
    print("Payment safe to proceed")
else:
    print(f"Payment blocked: {result.issues}")
```

### With httpx Client

```python
import httpx
from eth_account import Account
from sentinelseed.integrations.x402 import sentinel_x402_hooks

account = Account.from_key("0x...")

async with httpx.AsyncClient() as client:
    client.event_hooks = sentinel_x402_hooks(account)
    response = await client.get("https://api.example.com/paid-endpoint")
```

### With AgentKit

```python
from coinbase_agentkit import AgentKit
from sentinelseed.integrations.x402 import sentinel_x402_action_provider

agent = AgentKit(
    action_providers=[
        sentinel_x402_action_provider(security_profile="strict"),
    ]
)
```

## THSP Gate Framework

Sentinel validates x402 payments using four gates:

| Gate | Function | Checks |
|------|----------|--------|
| **TRUTH** | Verify legitimacy | URL validity, network support, contract verification |
| **HARM** | Prevent harm | Blocklist matching, malicious patterns |
| **SCOPE** | Enforce limits | Amount limits, daily totals, rate limits |
| **PURPOSE** | Validate intent | Endpoint familiarity, suspicious patterns |

All four gates must pass for a payment to be approved.

## Security Profiles

Pre-configured security levels:

```python
from sentinelseed.integrations.x402 import get_default_config

# Available profiles
config = get_default_config("permissive")  # Minimal restrictions
config = get_default_config("standard")    # Balanced (default)
config = get_default_config("strict")      # Higher security
config = get_default_config("paranoid")    # Maximum security
```

| Profile | Max Single | Max Daily | Confirmation Threshold |
|---------|------------|-----------|------------------------|
| permissive | $1,000 | $5,000 | $100 |
| standard | $100 | $500 | $10 |
| strict | $25 | $100 | $5 |
| paranoid | $10 | $50 | $1 |

## Configuration

### Custom Configuration

```python
from sentinelseed.integrations.coinbase import (
    SentinelX402Config,
    SpendingLimits,
    ConfirmationThresholds,
    ValidationConfig,
    SentinelX402Middleware,
)

config = SentinelX402Config(
    spending_limits=SpendingLimits(
        max_single_payment=50.0,
        max_daily_total=200.0,
        max_transactions_per_day=20,
    ),
    confirmation_thresholds=ConfirmationThresholds(
        amount_threshold=5.0,
    ),
    validation=ValidationConfig(
        strict_mode=True,
        require_https=True,
    ),
    blocked_addresses=[
        "0xbad...",  # Known malicious address
    ],
)

middleware = SentinelX402Middleware(config=config)
```

### Blocklists

```python
config = SentinelX402Config(
    blocked_addresses=[
        "0xknown_scam_address...",
    ],
    blocked_endpoints=[
        "scam.example.com",
        "phishing.io",
    ],
)
```

## AgentKit Actions

### sentinel_x402_validate_payment

Validate a payment before execution:

```python
result = provider.validate_payment({
    "endpoint": "https://api.example.com",
    "amount": "1000000",
    "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "network": "base",
    "pay_to": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
})
```

### sentinel_x402_get_spending_summary

Get current spending statistics:

```python
result = provider.get_spending_summary({})
# Returns: daily_spent, daily_limit, remaining, etc.
```

### sentinel_x402_configure_limits

Adjust spending limits:

```python
result = provider.configure_limits({
    "max_single_payment": 50.0,
    "max_daily_total": 200.0,
})
```

### sentinel_x402_check_endpoint

Pre-check endpoint safety:

```python
result = provider.check_endpoint({
    "endpoint": "https://api.example.com",
})
```

### sentinel_x402_get_audit_log

Get payment audit history:

```python
result = provider.get_audit_log({
    "limit": 50,
})
```

## Lifecycle Hooks

Integrate with x402 SDK lifecycle:

```python
from sentinelseed.integrations.x402 import SentinelX402Middleware

middleware = SentinelX402Middleware()

# Before payment
result = middleware.before_payment_hook(
    endpoint="https://api.example.com",
    payment_requirements=payment_req,
    wallet_address="0x...",
)

# After payment (for tracking)
middleware.after_payment_hook(
    endpoint="https://api.example.com",
    wallet_address="0x...",
    amount=1.0,
    asset="USDC",
    network="base",
    pay_to="0x...",
    success=True,
    transaction_hash="0x...",
)
```

## Spending Tracking

The middleware tracks spending per wallet:

```python
# Get summary
summary = middleware.get_spending_summary("0x...")
print(f"Daily spent: ${summary['daily_spent']}")
print(f"Remaining: ${summary['daily_remaining']}")

# Reset (if needed)
middleware.reset_spending("0x...")
```

## Audit Logging

All payment validations are logged:

```python
# Get audit log
entries = middleware.get_audit_log(
    wallet_address="0x...",
    limit=100,
)

for entry in entries:
    print(f"{entry['timestamp']}: ${entry['amount']} to {entry['endpoint']}")
    print(f"  Decision: {entry['decision']}")
```

## Supported Networks

- Base (mainnet)
- Base Sepolia (testnet)
- Avalanche (mainnet)
- Avalanche Fuji (testnet)

## Error Handling

```python
from sentinelseed.integrations.coinbase import (
    PaymentBlockedError,
    PaymentRejectedError,
    PaymentConfirmationRequired,
)

try:
    result = middleware.before_payment_hook(...)
except PaymentBlockedError as e:
    print(f"BLOCKED: {e.result.blocked_reason}")
except PaymentRejectedError as e:
    print(f"REJECTED: {e.result.issues}")
except PaymentConfirmationRequired as e:
    # Handle confirmation flow
    if user_confirms():
        proceed_with_payment()
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     AI Agent                                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                SentinelX402Middleware                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              THSPPaymentValidator                    │   │
│  │  ┌──────────┐ ┌──────────┐ ┌───────────┐ ┌────────┐ │   │
│  │  │  TRUTH   │ │   HARM   │ │   SCOPE   │ │PURPOSE │ │   │
│  │  │   Gate   │ │   Gate   │ │    Gate   │ │  Gate  │ │   │
│  │  └──────────┘ └──────────┘ └───────────┘ └────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                           │                                 │
│            ┌──────────────┴──────────────┐                 │
│            ▼                             ▼                 │
│    PaymentValidationResult        SpendingTracker          │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    x402 SDK                                 │
│              (httpx/requests hooks)                         │
└─────────────────────────────────────────────────────────────┘
```

## References

- [x402 Protocol](https://github.com/coinbase/x402)
- [x402 Documentation](https://docs.cdp.coinbase.com/x402)
- [Coinbase AgentKit](https://github.com/coinbase/agentkit)
- [Sentinel Documentation](https://sentinelseed.dev)

## License

MIT
