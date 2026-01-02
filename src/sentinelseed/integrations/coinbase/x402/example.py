"""Example usage of Sentinel x402 payment validation.

This example demonstrates how to integrate Sentinel safety validation
with x402 payment flows.

Prerequisites:
    pip install sentinelseed x402 httpx

For AgentKit integration:
    pip install coinbase-agentkit
"""

from __future__ import annotations

from json import loads


def example_basic_validation() -> None:
    """Basic example: Validate a payment request directly."""
    print("\n" + "=" * 60)
    print("Example 1: Basic Payment Validation")
    print("=" * 60)

    from sentinelseed.integrations.coinbase.x402 import (
        PaymentRequirementsModel,
        SentinelX402Middleware,
        get_default_config,
    )

    # Create middleware with standard config
    middleware = SentinelX402Middleware()

    # Create a sample payment request
    payment_req = PaymentRequirementsModel(
        scheme="exact",
        network="base",
        max_amount_required="1000000",  # 1 USDC (6 decimals)
        resource="https://api.weather.io/data",
        description="Weather API access",
        mime_type="application/json",
        pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",  # USDC on Base
    )

    # Validate the payment
    result = middleware.validate_payment(
        endpoint="https://api.weather.io/data",
        payment_requirements=payment_req,
        wallet_address="0x1234567890123456789012345678901234567890",
    )

    print(f"\nDecision: {result.decision.value}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Approved: {result.is_approved}")
    print(f"Amount: ${payment_req.get_amount_float():.2f}")

    print("\nTHSP Gates:")
    for gate, gate_result in result.gates.items():
        status = "PASS" if gate_result.passed else "FAIL"
        print(f"  {gate.value.upper()}: {status}")
        if gate_result.reason:
            print(f"    Reason: {gate_result.reason}")

    if result.recommendations:
        print("\nRecommendations:")
        for rec in result.recommendations:
            print(f"  - {rec}")


def example_high_amount_payment() -> None:
    """Example: Payment that exceeds limits."""
    print("\n" + "=" * 60)
    print("Example 2: High Amount Payment (Exceeds Limits)")
    print("=" * 60)

    from sentinelseed.integrations.coinbase.x402 import (
        PaymentRequirementsModel,
        SentinelX402Middleware,
        get_default_config,
    )

    # Use strict config with lower limits
    config = get_default_config("strict")
    middleware = SentinelX402Middleware(config=config)

    # High amount payment (50 USDC with limit of 25)
    payment_req = PaymentRequirementsModel(
        scheme="exact",
        network="base",
        max_amount_required="50000000",  # 50 USDC
        resource="https://api.expensive.io/premium",
        description="Premium API access",
        mime_type="application/json",
        pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )

    result = middleware.validate_payment(
        endpoint="https://api.expensive.io/premium",
        payment_requirements=payment_req,
        wallet_address="0x1234567890123456789012345678901234567890",
    )

    print(f"\nDecision: {result.decision.value}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Amount: ${payment_req.get_amount_float():.2f}")
    print(f"Limit: ${config.spending_limits.max_single_payment:.2f}")

    if result.issues:
        print("\nIssues detected:")
        for issue in result.issues:
            print(f"  - {issue}")


def example_blocked_address() -> None:
    """Example: Payment to blocked address."""
    print("\n" + "=" * 60)
    print("Example 3: Payment to Blocked Address")
    print("=" * 60)

    from sentinelseed.integrations.coinbase.x402 import (
        PaymentRequirementsModel,
        SentinelX402Config,
        SentinelX402Middleware,
    )

    # Configure with blocked address
    config = SentinelX402Config(
        blocked_addresses=[
            "0xbad0000000000000000000000000000000000bad",
        ]
    )
    middleware = SentinelX402Middleware(config=config)

    # Payment to blocked address
    payment_req = PaymentRequirementsModel(
        scheme="exact",
        network="base",
        max_amount_required="1000000",
        resource="https://api.scam.io/steal",
        description="Definitely not a scam",
        mime_type="application/json",
        pay_to="0xbad0000000000000000000000000000000000bad",
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )

    result = middleware.validate_payment(
        endpoint="https://api.scam.io/steal",
        payment_requirements=payment_req,
        wallet_address="0x1234567890123456789012345678901234567890",
    )

    print(f"\nDecision: {result.decision.value}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Blocked Reason: {result.blocked_reason}")

    from sentinelseed.integrations.coinbase.x402 import THSPGate
    harm_gate = result.gates.get(THSPGate.HARM)
    if harm_gate:
        print(f"\nHARM Gate: {'PASS' if harm_gate.passed else 'FAIL'}")
        if harm_gate.reason:
            print(f"  Reason: {harm_gate.reason}")


def example_spending_tracking() -> None:
    """Example: Spending tracking across multiple payments."""
    print("\n" + "=" * 60)
    print("Example 4: Spending Tracking")
    print("=" * 60)

    from sentinelseed.integrations.coinbase.x402 import (
        PaymentRequirementsModel,
        SentinelX402Middleware,
        get_default_config,
    )

    config = get_default_config("standard")
    middleware = SentinelX402Middleware(config=config)
    wallet = "0x1234567890123456789012345678901234567890"

    # Simulate multiple payments
    payments = [
        ("api1.example.com", "5000000"),   # $5
        ("api2.example.com", "10000000"),  # $10
        ("api3.example.com", "3000000"),   # $3
    ]

    for i, (endpoint, amount) in enumerate(payments, 1):
        payment_req = PaymentRequirementsModel(
            scheme="exact",
            network="base",
            max_amount_required=amount,
            resource=f"https://{endpoint}/data",
            description=f"API #{i}",
            mime_type="application/json",
            pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
            max_timeout_seconds=300,
            asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        )

        result = middleware.validate_payment(
            endpoint=f"https://{endpoint}/data",
            payment_requirements=payment_req,
            wallet_address=wallet,
        )

        print(f"\nPayment {i}: ${payment_req.get_amount_float():.2f} to {endpoint}")
        print(f"  Decision: {result.decision.value}")

        # Simulate successful payment
        if result.is_approved:
            middleware.after_payment_hook(
                endpoint=f"https://{endpoint}/data",
                wallet_address=wallet,
                amount=payment_req.get_amount_float(),
                asset="USDC",
                network="base",
                pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
                success=True,
                transaction_hash=f"0x{'0' * 64}",
            )

    # Get spending summary
    summary = middleware.get_spending_summary(wallet)
    print("\n--- Spending Summary ---")
    print(f"Daily spent: ${summary['daily_spent']:.2f}")
    print(f"Daily transactions: {summary['daily_transactions']}")
    print(f"Daily limit: ${summary['daily_limit']:.2f}")
    print(f"Remaining: ${summary['daily_remaining']:.2f}")


def example_agentkit_provider() -> None:
    """Example: Using with AgentKit (if available)."""
    print("\n" + "=" * 60)
    print("Example 5: AgentKit Action Provider")
    print("=" * 60)

    from sentinelseed.integrations.coinbase.x402 import (
        SentinelX402ActionProvider,
        sentinel_x402_action_provider,
    )

    # Create provider
    provider = sentinel_x402_action_provider(security_profile="standard")

    # Test validate_payment action
    result = provider.validate_payment({
        "endpoint": "https://api.weather.io/forecast",
        "amount": "2000000",  # 2 USDC
        "asset": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
        "network": "base",
        "pay_to": "0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
        "description": "Weather forecast API",
    })

    parsed = loads(result)
    print(f"\nValidate Payment Result:")
    print(f"  Decision: {parsed['decision']}")
    print(f"  Approved: {parsed['approved']}")
    print(f"  Risk Level: {parsed['risk_level']}")
    print(f"  Amount: ${parsed['amount_usd']:.2f}")

    # Test check_endpoint action
    result = provider.check_endpoint({
        "endpoint": "https://api.weather.io/forecast",
    })

    parsed = loads(result)
    print(f"\nEndpoint Safety Check:")
    print(f"  Endpoint: {parsed['endpoint']}")
    print(f"  Is Safe: {parsed['is_safe']}")
    if parsed.get('warnings'):
        print(f"  Warnings: {parsed['warnings']}")

    # Test get_spending_summary action
    result = provider.get_spending_summary({})

    parsed = loads(result)
    print(f"\nSpending Summary:")
    if parsed['success']:
        summary = parsed['summary']
        print(f"  Daily Spent: ${summary['daily_spent']:.2f}")
        print(f"  Daily Limit: ${summary['daily_limit']:.2f}")


def example_security_profiles() -> None:
    """Example: Different security profiles."""
    print("\n" + "=" * 60)
    print("Example 6: Security Profiles Comparison")
    print("=" * 60)

    from sentinelseed.integrations.coinbase.x402 import (
        PaymentRequirementsModel,
        SentinelX402Middleware,
        get_default_config,
    )

    profiles = ["permissive", "standard", "strict", "paranoid"]

    # Same payment tested against different profiles
    payment_req = PaymentRequirementsModel(
        scheme="exact",
        network="base",
        max_amount_required="15000000",  # $15 USDC
        resource="https://api.example.com/data",
        description="API access",
        mime_type="application/json",
        pay_to="0x742d35Cc6634C0532925a3b844Bc9e7595f2bD71",
        max_timeout_seconds=300,
        asset="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    )

    print(f"\nTesting $15 payment against different profiles:")
    print("-" * 50)

    for profile in profiles:
        config = get_default_config(profile)  # type: ignore
        middleware = SentinelX402Middleware(config=config)

        result = middleware.validate_payment(
            endpoint="https://api.example.com/data",
            payment_requirements=payment_req,
            wallet_address="0x1234567890123456789012345678901234567890",
        )

        print(f"\n{profile.upper()}:")
        print(f"  Max single payment: ${config.spending_limits.max_single_payment:.2f}")
        print(f"  Decision: {result.decision.value}")
        print(f"  Risk Level: {result.risk_level.value}")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel x402 Payment Validation Examples")
    print("=" * 60)

    # Run all examples
    example_basic_validation()
    example_high_amount_payment()
    example_blocked_address()
    example_spending_tracking()
    example_agentkit_provider()
    example_security_profiles()

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
