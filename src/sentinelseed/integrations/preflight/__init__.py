"""
Pre-flight Transaction Simulator for Solana.

Simulates blockchain transactions BEFORE execution to detect potential issues:
- Transaction simulation via Solana RPC
- Slippage estimation for swaps (Jupiter API)
- Token security analysis (GoPlus API)
- Honeypot and rug pull detection
- Liquidity analysis

This module provides a critical safety layer for AI agents handling crypto assets.

Usage:
    from sentinelseed.integrations.preflight import TransactionSimulator

    # Initialize simulator
    simulator = TransactionSimulator(
        rpc_url="https://api.mainnet-beta.solana.com",
        goplus_api_key=None,  # Optional, free tier available
    )

    # Simulate a swap
    result = await simulator.simulate_swap(
        input_mint="So11111111111111111111111111111111111111112",  # SOL
        output_mint="EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",  # USDC
        amount=1_000_000_000,  # 1 SOL (lamports)
    )

    if result.is_safe:
        print(f"Expected output: {result.expected_output}")
        print(f"Slippage: {result.slippage_bps} bps")
    else:
        print(f"Risks detected: {result.risks}")

GitHub: https://github.com/sentinel-seed/sentinel/tree/main/src/sentinelseed/integrations/preflight

References:
- Solana RPC: https://solana.com/docs/rpc/http/simulatetransaction
- Jupiter API: https://dev.jup.ag/docs/swap-api
- GoPlus Security: https://docs.gopluslabs.io/reference/solanatokensecurityusingget
"""

__version__ = "1.0.0"
__author__ = "Sentinel Team"

from .simulator import (
    TransactionSimulator,
    SimulationResult,
    SwapSimulationResult,
    TokenSecurityResult,
    SimulationError,
    RiskLevel,
    RiskFactor,
)

from .analyzers import (
    JupiterAnalyzer,
    GoPlusAnalyzer,
    TokenRiskAnalyzer,
    SlippageAnalyzer,
    LiquidityAnalyzer,
)

from .wrapper import (
    PreflightValidator,
    PreflightResult,
    create_preflight_tools,
)

__all__ = [
    # Version
    "__version__",
    # Main classes
    "TransactionSimulator",
    "SimulationResult",
    "SwapSimulationResult",
    "TokenSecurityResult",
    "SimulationError",
    # Enums
    "RiskLevel",
    "RiskFactor",
    # Analyzers
    "JupiterAnalyzer",
    "GoPlusAnalyzer",
    "TokenRiskAnalyzer",
    "SlippageAnalyzer",
    "LiquidityAnalyzer",
    # Wrapper
    "PreflightValidator",
    "PreflightResult",
    "create_preflight_tools",
]
