# Pre-flight Transaction Simulator

Simulate Solana transactions **before** execution to detect potential issues and risks.

## Overview

The Pre-flight Transaction Simulator provides a critical safety layer for AI agents handling crypto assets. It simulates transactions before execution to detect:

- **Transaction failures** via Solana RPC simulation
- **High slippage** in swaps using Jupiter API
- **Token security risks** (honeypots, freeze authority) via GoPlus API
- **Liquidity issues** that could affect trade execution
- **Price impact** for large trades

## Installation

```bash
pip install sentinelseed httpx
```

## Quick Start

### Basic Swap Simulation

```python
import asyncio
from sentinelseed.integrations.preflight import TransactionSimulator

async def main():
    # Initialize simulator
    simulator = TransactionSimulator(
        rpc_url="https://api.mainnet-beta.solana.com"
    )

    # Simulate SOL -> USDC swap
    result = await simulator.simulate_swap(
        input_mint="So11111111111111111111111111111111111111112",  # SOL
        output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        amount=1_000_000_000,  # 1 SOL in lamports
    )

    if result.is_safe:
        print(f"Expected output: {result.expected_output / 1e6:.2f} USDC")
        print(f"Slippage: {result.slippage_bps / 100:.2f}%")
    else:
        print(f"Risks detected: {[r.description for r in result.risks]}")

    await simulator.close()

asyncio.run(main())
```

### Token Security Check

```python
from sentinelseed.integrations.preflight import TransactionSimulator

async def check_token():
    simulator = TransactionSimulator()

    result = await simulator.check_token_security("TokenMintAddress...")

    print(f"Is Safe: {result.is_safe}")
    print(f"Has Freeze Authority: {result.has_freeze_authority}")
    print(f"Is Honeypot: {result.is_honeypot}")

    if not result.is_safe:
        for risk in result.risks:
            print(f"  - {risk.description}")

    await simulator.close()
```

### Pre-flight Validator (Combined)

```python
from sentinelseed.integrations.preflight import PreflightValidator

async def validate():
    # Combines THSP validation + transaction simulation
    validator = PreflightValidator(
        max_transfer=100.0,
        max_slippage_bps=500,  # 5%
        require_purpose=True,
    )

    result = await validator.validate_swap(
        input_mint="So11...",
        output_mint="Token...",
        amount=1_000_000_000,
        purpose="Converting SOL to stable for savings",
    )

    if result.should_proceed:
        print("Transaction approved!")
        print(f"Expected output: {result.expected_output}")
    else:
        print("Transaction blocked:")
        print(f"  Validation: {result.validation_concerns}")
        print(f"  Simulation: {result.simulation_risks}")

    await validator.close()
```

## Components

### TransactionSimulator

Core simulator with RPC, Jupiter, and GoPlus integration.

**Methods:**
- `simulate_transaction(tx_base64)` - Simulate raw transaction
- `simulate_swap(input_mint, output_mint, amount)` - Simulate token swap
- `check_token_security(token_address)` - Check token security
- `pre_flight_check(action, params)` - High-level action validation

### PreflightValidator

Combined validator that integrates with Sentinel THSP.

**Methods:**
- `validate_with_simulation(action, **kwargs)` - Full validation
- `validate_swap(...)` - Swap-specific validation
- `validate_transfer(...)` - Transfer-specific validation
- `check_token(token_address)` - Token security check

### Analyzers

Specialized risk analyzers:
- `JupiterAnalyzer` - Swap quotes and slippage analysis
- `GoPlusAnalyzer` - Token security via GoPlus API
- `TokenRiskAnalyzer` - Comprehensive token analysis
- `SlippageAnalyzer` - Slippage recommendations
- `LiquidityAnalyzer` - Pool liquidity analysis

## Risk Factors

| Factor | Description |
|--------|-------------|
| `HONEYPOT` | Token prevents selling |
| `FREEZE_AUTHORITY` | Funds can be frozen |
| `MINT_AUTHORITY` | Token supply can increase |
| `TRANSFER_TAX` | High transfer/sell taxes |
| `HIGH_SLIPPAGE` | Slippage exceeds threshold |
| `PRICE_IMPACT` | Large price impact |
| `LOW_LIQUIDITY` | Insufficient pool liquidity |
| `RUG_PULL` | Low LP locked percentage |

## Risk Levels

| Level | Action |
|-------|--------|
| `NONE` | No risks detected |
| `LOW` | Minor concerns |
| `MEDIUM` | Review recommended |
| `HIGH` | Block recommended |
| `CRITICAL` | Must block |

## LangChain Integration

```python
from sentinelseed.integrations.preflight import create_preflight_tools

# Create tools for LangChain agent
tools = create_preflight_tools()

# Tools available:
# - preflight_check_swap: Simulate swaps
# - preflight_check_token: Check token security
```

## Configuration

```python
simulator = TransactionSimulator(
    # Solana RPC endpoint
    rpc_url="https://api.mainnet-beta.solana.com",

    # GoPlus API key (optional, free tier available)
    goplus_api_key=None,

    # Maximum acceptable slippage (basis points)
    max_slippage_bps=500,  # 5%

    # Cache TTL for token security results
    cache_ttl_seconds=300,  # 5 minutes
)
```

## API References

- [Solana RPC simulateTransaction](https://solana.com/docs/rpc/http/simulatetransaction)
- [Jupiter Swap API](https://dev.jup.ag/docs/swap-api)
- [GoPlus Token Security API](https://docs.gopluslabs.io/reference/solanatokensecurityusingget)

## Examples

Run the example script:

```bash
python -m sentinelseed.integrations.preflight.example

# Run all examples
python -m sentinelseed.integrations.preflight.example --all
```

## License

MIT License - Sentinel Seed Team
