"""
Example usage of Sentinel Coinbase Integration.

This module demonstrates how to use Sentinel's comprehensive
security features with Coinbase AgentKit and x402 payments.

Prerequisites:
    pip install sentinelseed

    # For AgentKit:
    pip install coinbase-agentkit

    # For x402:
    pip install x402 httpx

Run examples:
    python -m sentinelseed.integrations.coinbase.example
"""

from __future__ import annotations


def example_address_validation() -> None:
    """Example 1: EVM Address Validation."""
    print("\n" + "=" * 60)
    print("Example 1: EVM Address Validation")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        validate_address,
        is_valid_evm_address,
        to_checksum_address,
    )

    # Test addresses
    addresses = [
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",  # Valid checksum
        "0x742d35cc6634c0532925a3b844bc454e4438f44e",  # Valid lowercase
        "0x742D35CC6634C0532925A3B844BC454E4438F44E",  # Valid uppercase
        "0xinvalid",                                    # Invalid
        "0x742d35Cc6634C0532925a3b844Bc454e4438f44E",  # Invalid checksum
    ]

    for addr in addresses:
        result = validate_address(addr)
        status = "[OK]" if result.valid else "[FAIL]"
        print(f"\n{status} {addr[:20]}...")
        print(f"   Status: {result.status.value}")
        print(f"   Checksummed: {result.is_checksummed}")
        if result.warnings:
            print(f"   Warnings: {result.warnings}")


def example_transaction_validation() -> None:
    """Example 2: Transaction Validation."""
    print("\n" + "=" * 60)
    print("Example 2: Transaction Validation")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        TransactionValidator,
        ChainType,
        get_default_config,
    )

    # Create validator with strict profile
    config = get_default_config("strict")
    validator = TransactionValidator(config=config)

    # Test transactions
    transactions = [
        {
            "action": "native_transfer",
            "from_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "to_address": "0x1234567890123456789012345678901234567890",
            "amount": 10.0,
            "chain": ChainType.BASE_MAINNET,
            "purpose": "Payment for API services",
        },
        {
            "action": "native_transfer",
            "from_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "to_address": "0x1234567890123456789012345678901234567890",
            "amount": 100.0,  # Exceeds strict limit
            "chain": ChainType.BASE_MAINNET,
        },
        {
            "action": "approve",
            "from_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            "to_address": "0x1234567890123456789012345678901234567890",
            "amount": 0,
            "approval_amount": "115792089237316195423570985008687907853269984665640564039457584007913129639935",  # MAX_UINT256
            "chain": ChainType.BASE_MAINNET,
        },
    ]

    for i, tx in enumerate(transactions, 1):
        result = validator.validate(**tx)
        status = "[OK]" if result.is_approved else "[FAIL]"
        print(f"\nTransaction {i}: {tx['action']} ${tx['amount']}")
        print(f"   {status} Decision: {result.decision.value}")
        print(f"   Risk Level: {result.risk_level.value}")
        if result.concerns:
            print(f"   Concerns: {result.concerns}")
        if result.blocked_reason:
            print(f"   Blocked: {result.blocked_reason}")


def example_defi_risk_assessment() -> None:
    """Example 3: DeFi Risk Assessment."""
    print("\n" + "=" * 60)
    print("Example 3: DeFi Risk Assessment")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        DeFiValidator,
        assess_defi_risk,
    )

    # Test DeFi operations
    operations = [
        {
            "protocol": "compound",
            "action": "supply",
            "amount": 500.0,
        },
        {
            "protocol": "compound",
            "action": "borrow",
            "amount": 1000.0,
            "collateral_ratio": 1.2,  # Low collateral
        },
        {
            "protocol": "wow",
            "action": "create_token",
            "amount": 100.0,
        },
        {
            "protocol": "unknown_protocol",
            "action": "supply",
            "amount": 1000.0,
            "apy": 500.0,  # Suspiciously high APY
        },
    ]

    for op in operations:
        assessment = assess_defi_risk(**op)
        status = "[WARN]" if assessment.is_high_risk else "[OK]"
        print(f"\n{status} {op['protocol']}.{op['action']}(${op['amount']})")
        print(f"   Risk Level: {assessment.risk_level.value}")
        print(f"   Risk Score: {assessment.risk_score:.1f}/100")
        if assessment.risk_factors:
            print(f"   Factors: {assessment.risk_factors[:2]}")
        if assessment.warnings:
            print(f"   Warnings: {assessment.warnings}")


def example_action_provider() -> None:
    """Example 4: AgentKit Action Provider."""
    print("\n" + "=" * 60)
    print("Example 4: AgentKit Action Provider")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        sentinel_action_provider,
    )
    import json

    # Create provider
    provider = sentinel_action_provider(
        security_profile="standard",
        wallet_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
    )

    print(f"\nProvider: {provider.name}")
    print(f"Security Profile: {provider.config.security_profile.value}")

    # Test validate_transaction action
    result = provider.validate_transaction({
        "action": "native_transfer",
        "from_address": "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        "to_address": "0x1234567890123456789012345678901234567890",
        "amount": 25.0,
        "chain": "base-mainnet",
        "purpose": "Payment for services",
    })

    parsed = json.loads(result)
    print(f"\nValidate Transaction Result:")
    print(f"   Decision: {parsed['decision']}")
    print(f"   Approved: {parsed['approved']}")
    print(f"   Risk Level: {parsed['risk_level']}")

    # Test check_action_safety action
    result = provider.check_action_safety({
        "action_name": "native_transfer",
        "purpose": "Regular payment",
    })

    parsed = json.loads(result)
    print(f"\nAction Safety Check:")
    print(f"   Safe: {parsed['safe']}")
    print(f"   Is High Risk: {parsed['is_high_risk']}")

    # Test spending summary
    result = provider.get_spending_summary({})
    parsed = json.loads(result)
    print(f"\nSpending Summary:")
    if parsed.get("success"):
        summary = parsed["summary"]
        print(f"   Daily Spent: ${summary['daily_spent']:.2f}")
        print(f"   Daily Limit: ${summary['daily_limit']:.2f}")


def example_action_wrappers() -> None:
    """Example 5: Action Wrappers."""
    print("\n" + "=" * 60)
    print("Example 5: Action Wrappers")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        safe_action,
        create_safe_action_wrapper,
        SentinelActionWrapper,
    )

    # Example: Wrap a function with validation
    @safe_action(action_type="native_transfer")
    def transfer_eth(to: str, amount: float, from_address: str = None):
        """Simulated transfer function."""
        return f"Transferred {amount} ETH to {to[:10]}..."

    # This will validate before executing
    try:
        result = transfer_eth(
            to="0x1234567890123456789012345678901234567890",
            amount=10.0,
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        )
        print(f"\n[OK] Transfer succeeded: {result}")
    except Exception as e:
        print(f"\n[FAIL] Transfer blocked: {e}")

    # Try a blocked transaction (high amount with strict config)
    wrapper = create_safe_action_wrapper(
        security_profile="strict",
        block_on_failure=True,
    )

    @wrapper.wrap_decorator("native_transfer")
    def strict_transfer(to: str, amount: float):
        return f"Strict transfer: {amount} to {to[:10]}..."

    try:
        result = strict_transfer(
            to="0x1234567890123456789012345678901234567890",
            amount=100.0,  # Exceeds strict limit of $25
        )
        print(f"\n[OK] Strict transfer: {result}")
    except Exception as e:
        print(f"\n[FAIL] Strict transfer blocked (expected): {type(e).__name__}")


def example_security_profiles() -> None:
    """Example 6: Security Profiles Comparison."""
    print("\n" + "=" * 60)
    print("Example 6: Security Profiles Comparison")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        get_default_config,
        TransactionValidator,
        ChainType,
    )

    profiles = ["permissive", "standard", "strict", "paranoid"]
    test_amount = 50.0

    print(f"\nTesting ${test_amount} transfer against different profiles:")
    print("-" * 50)

    for profile in profiles:
        config = get_default_config(profile)
        validator = TransactionValidator(config=config)

        result = validator.validate(
            action="native_transfer",
            from_address="0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
            to_address="0x1234567890123456789012345678901234567890",
            amount=test_amount,
            chain=ChainType.BASE_MAINNET,
        )

        chain_config = config.get_chain_config(ChainType.BASE_MAINNET)
        limits = chain_config.spending_limits

        status = "[OK]" if result.is_approved else "[FAIL]"
        print(f"\n{profile.upper()}:")
        print(f"   Max Single: ${limits.max_single_transaction:.2f}")
        print(f"   Max Daily: ${limits.max_daily_total:.2f}")
        print(f"   {status} Decision: {result.decision.value}")


def example_x402_integration() -> None:
    """Example 7: x402 Payment Validation."""
    print("\n" + "=" * 60)
    print("Example 7: x402 Payment Validation")
    print("=" * 60)

    from sentinelseed.integrations.coinbase import (
        SentinelX402Middleware,
        get_x402_config,
    )
    from sentinelseed.integrations.coinbase.x402 import PaymentRequirementsModel

    # Create middleware with standard config
    config = get_x402_config("standard")
    middleware = SentinelX402Middleware(config=config)

    # Test payment
    payment_req = PaymentRequirementsModel(
        scheme="exact",
        network="base",
        max_amount_required="5000000",  # $5 USDC
        resource="https://api.example.com/data",
        description="API access payment",
        mime_type="application/json",
        pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )

    result = middleware.validate_payment(
        endpoint="https://api.example.com/data",
        payment_requirements=payment_req,
        wallet_address="0x1234567890123456789012345678901234567890",
    )

    status = "[OK]" if result.is_approved else "[FAIL]"
    print(f"\nPayment Validation:")
    print(f"   Amount: ${payment_req.get_amount_float():.2f}")
    print(f"   {status} Decision: {result.decision.value}")
    print(f"   Risk Level: {result.risk_level.value}")

    print("\nTHSP Gates:")
    for gate, gate_result in result.gates.items():
        gate_status = "PASS" if gate_result.passed else "FAIL"
        print(f"   {gate.value.upper()}: {gate_status}")


def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("Sentinel Coinbase Integration Examples")
    print("=" * 60)

    # Run examples
    example_address_validation()
    example_transaction_validation()
    example_defi_risk_assessment()
    example_action_provider()
    example_action_wrappers()
    example_security_profiles()

    try:
        example_x402_integration()
    except ImportError as e:
        print(f"\n[WARN] x402 example skipped: {e}")

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
