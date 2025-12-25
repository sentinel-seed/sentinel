#!/usr/bin/env python3
"""
Pre-flight Transaction Simulator Examples

Demonstrates transaction simulation and risk analysis for Solana operations.

Run directly:
    python -m sentinelseed.integrations.preflight.example

Requirements:
    pip install sentinelseed httpx

Examples covered:
    1. Basic swap simulation
    2. Token security check
    3. Pre-flight validation (combined)
    4. LangChain tools usage
    5. Custom risk thresholds
    6. Batch token analysis
"""

import asyncio
import sys


# Well-known token addresses for examples
TOKENS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "BONK": "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263",
}


async def example_swap_simulation():
    """Example 1: Simulate a token swap."""
    print("\n" + "=" * 60)
    print("Example 1: Swap Simulation")
    print("=" * 60)

    from sentinelseed.integrations.preflight import TransactionSimulator

    # Initialize simulator
    simulator = TransactionSimulator(
        rpc_url="https://api.mainnet-beta.solana.com",
        max_slippage_bps=500,  # 5% max slippage
    )

    try:
        print("\nSimulating 1 SOL -> USDC swap...")

        result = await simulator.simulate_swap(
            input_mint=TOKENS["SOL"],
            output_mint=TOKENS["USDC"],
            amount=1_000_000_000,  # 1 SOL in lamports
            slippage_bps=50,  # 0.5% slippage
        )

        print(f"\n  Success: {result.success}")
        print(f"  Is Safe: {result.is_safe}")
        print(f"  Risk Level: {result.risk_level.name}")

        if result.success:
            # Convert output to USDC (6 decimals)
            usdc_amount = result.expected_output / 1e6
            print(f"  Expected Output: {usdc_amount:.2f} USDC")
            print(f"  Minimum Output: {result.minimum_output / 1e6:.2f} USDC")
            print(f"  Slippage: {result.slippage_bps / 100:.2f}%")
            print(f"  Price Impact: {result.price_impact_pct:.4f}%")

        if result.risks:
            print(f"\n  Risks detected:")
            for risk in result.risks:
                print(f"    - [{risk.level.name}] {risk.description}")

        if result.recommendations:
            print(f"\n  Recommendations:")
            for rec in result.recommendations:
                print(f"    - {rec}")

    finally:
        await simulator.close()


async def example_token_security():
    """Example 2: Check token security."""
    print("\n" + "=" * 60)
    print("Example 2: Token Security Check")
    print("=" * 60)

    from sentinelseed.integrations.preflight import TransactionSimulator

    simulator = TransactionSimulator()

    try:
        # Check a known safe token (USDC)
        print("\nChecking USDC (known safe token)...")
        result = await simulator.check_token_security(TOKENS["USDC"])

        print(f"  Address: {result.token_address[:16]}...")
        print(f"  Is Safe: {result.is_safe}")
        print(f"  Risk Level: {result.risk_level.name}")
        print(f"  Has Freeze Authority: {result.has_freeze_authority}")
        print(f"  Has Mint Authority: {result.has_mint_authority}")
        print(f"  Is Honeypot: {result.is_honeypot}")

        # Check a random token (may have risks)
        print("\nChecking JUP token...")
        result = await simulator.check_token_security(TOKENS["JUP"])

        print(f"  Is Safe: {result.is_safe}")
        print(f"  Risk Level: {result.risk_level.name}")

        if result.risks:
            print(f"  Risks:")
            for risk in result.risks:
                print(f"    - [{risk.level.name}] {risk.description}")

    finally:
        await simulator.close()


async def example_preflight_validator():
    """Example 3: Pre-flight validation (combined)."""
    print("\n" + "=" * 60)
    print("Example 3: Pre-flight Validator")
    print("=" * 60)

    from sentinelseed.integrations.preflight import PreflightValidator

    # Initialize validator with pre-flight simulation
    validator = PreflightValidator(
        rpc_url="https://api.mainnet-beta.solana.com",
        max_transfer=100.0,
        max_slippage_bps=500,
        require_purpose=True,
    )

    try:
        # Validate a swap
        print("\nValidating swap with purpose...")
        result = await validator.validate_swap(
            input_mint=TOKENS["SOL"],
            output_mint=TOKENS["USDC"],
            amount=1_000_000_000,  # 1 SOL
            purpose="Converting SOL to USDC for stable storage",
        )

        print(f"\n  Should Proceed: {result.should_proceed}")
        print(f"  Risk Level: {result.risk_level}")
        print(f"  Validation Passed: {result.validation_passed}")
        print(f"  Simulation Passed: {result.simulation_passed}")

        if result.expected_output:
            print(f"  Expected Output: {result.expected_output / 1e6:.2f} USDC")

        if result.validation_concerns:
            print(f"  Validation Concerns:")
            for concern in result.validation_concerns:
                print(f"    - {concern}")

        if result.simulation_risks:
            print(f"  Simulation Risks:")
            for risk in result.simulation_risks:
                print(f"    - {risk}")

        if result.recommendations:
            print(f"  Recommendations:")
            for rec in result.recommendations:
                print(f"    - {rec}")

    finally:
        await validator.close()


async def example_transfer_validation():
    """Example 4: Validate a token transfer."""
    print("\n" + "=" * 60)
    print("Example 4: Transfer Validation")
    print("=" * 60)

    from sentinelseed.integrations.preflight import PreflightValidator

    validator = PreflightValidator(max_transfer=50.0)

    try:
        # Validate a transfer with purpose
        print("\nValidating 10 SOL transfer with purpose...")
        result = await validator.validate_transfer(
            amount=10.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose="Payment for consulting services",
        )

        print(f"  Should Proceed: {result.should_proceed}")
        print(f"  Risk Level: {result.risk_level}")
        print(f"  Is Safe: {result.is_safe}")

        # Validate a transfer WITHOUT purpose
        print("\nValidating 10 SOL transfer WITHOUT purpose...")
        result = await validator.validate_transfer(
            amount=10.0,
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        )

        print(f"  Should Proceed: {result.should_proceed}")
        if result.validation_concerns:
            print(f"  Concerns:")
            for concern in result.validation_concerns:
                print(f"    - {concern}")

    finally:
        await validator.close()


async def example_custom_thresholds():
    """Example 5: Custom risk thresholds."""
    print("\n" + "=" * 60)
    print("Example 5: Custom Risk Thresholds")
    print("=" * 60)

    from sentinelseed.integrations.preflight import TransactionSimulator

    # Strict simulator with low slippage tolerance
    strict_simulator = TransactionSimulator(
        max_slippage_bps=100,  # Only 1% slippage allowed
    )

    # Lenient simulator with higher tolerance
    lenient_simulator = TransactionSimulator(
        max_slippage_bps=1000,  # Up to 10% slippage allowed
    )

    try:
        print("\nSimulating with STRICT settings (max 1% slippage)...")
        result = await strict_simulator.simulate_swap(
            input_mint=TOKENS["SOL"],
            output_mint=TOKENS["BONK"],  # BONK may have higher slippage
            amount=1_000_000_000,
        )
        print(f"  Strict - Is Safe: {result.is_safe}")
        print(f"  Strict - Risk Level: {result.risk_level.name}")

        print("\nSimulating with LENIENT settings (max 10% slippage)...")
        result = await lenient_simulator.simulate_swap(
            input_mint=TOKENS["SOL"],
            output_mint=TOKENS["BONK"],
            amount=1_000_000_000,
        )
        print(f"  Lenient - Is Safe: {result.is_safe}")
        print(f"  Lenient - Risk Level: {result.risk_level.name}")

    finally:
        await strict_simulator.close()
        await lenient_simulator.close()


async def example_batch_analysis():
    """Example 6: Analyze multiple tokens."""
    print("\n" + "=" * 60)
    print("Example 6: Batch Token Analysis")
    print("=" * 60)

    from sentinelseed.integrations.preflight import TransactionSimulator

    simulator = TransactionSimulator()

    try:
        tokens_to_check = ["USDC", "USDT", "JUP", "BONK"]

        print("\nAnalyzing multiple tokens...\n")

        results = []
        for token_name in tokens_to_check:
            token_address = TOKENS[token_name]
            result = await simulator.check_token_security(token_address)
            results.append((token_name, result))

        # Display results table
        print(f"  {'Token':<8} {'Safe':<6} {'Risk':<10} {'Freeze':<8} {'Mint':<8}")
        print("  " + "-" * 48)

        for token_name, result in results:
            print(
                f"  {token_name:<8} "
                f"{'Yes' if result.is_safe else 'No':<6} "
                f"{result.risk_level.name:<10} "
                f"{'Yes' if result.has_freeze_authority else 'No':<8} "
                f"{'Yes' if result.has_mint_authority else 'No':<8}"
            )

        # Summary statistics
        print(f"\nStats: {simulator.get_stats()}")

    finally:
        await simulator.close()


async def example_statistics():
    """Example 7: Simulation statistics."""
    print("\n" + "=" * 60)
    print("Example 7: Statistics")
    print("=" * 60)

    from sentinelseed.integrations.preflight import PreflightValidator

    validator = PreflightValidator()

    try:
        # Run several validations
        operations = [
            ("swap", {"input_mint": TOKENS["SOL"], "output_mint": TOKENS["USDC"], "amount": 1_000_000_000}),
            ("swap", {"input_mint": TOKENS["SOL"], "output_mint": TOKENS["JUP"], "amount": 500_000_000}),
            ("transfer", {"amount": 5.0, "recipient": "ABC123...", "purpose": "Test payment"}),
        ]

        print("\nRunning validations...")
        for action, params in operations:
            result = await validator.validate_with_simulation(action, **params)
            status = "SAFE" if result.should_proceed else "BLOCKED"
            print(f"  {action}: {status} ({result.risk_level})")

        # Display statistics
        stats = validator.get_stats()
        print(f"\nSimulator Stats:")
        print(f"  Total simulations: {stats['simulator']['simulations']}")
        print(f"  Successful: {stats['simulator']['successful']}")
        print(f"  Failed: {stats['simulator']['failed']}")
        print(f"  Risks detected: {stats['simulator']['risks_detected']}")
        print(f"  Cache size: {stats['simulator']['cache_size']}")

    finally:
        await validator.close()


async def main():
    """Run all examples."""
    print("=" * 60)
    print("Pre-flight Transaction Simulator Examples")
    print("=" * 60)
    print("\nDemonstrating transaction simulation for Solana.")
    print("GitHub: https://github.com/sentinel-seed/sentinel/tree/main/src/sentinelseed/integrations/preflight")

    # Check for help
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    try:
        # Run examples
        await example_swap_simulation()
        await example_token_security()
        await example_preflight_validator()
        await example_transfer_validation()

        # Extended examples
        if "--all" in sys.argv:
            await example_custom_thresholds()
            await example_batch_analysis()
            await example_statistics()

        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60 + "\n")

    except Exception as e:
        print(f"\nError running examples: {e}")
        print("Make sure you have network access and httpx installed.")
        print("Install: pip install httpx")


if __name__ == "__main__":
    asyncio.run(main())
