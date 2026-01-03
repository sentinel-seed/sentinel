#!/usr/bin/env python3
"""
Sentinel + Solana Agent Kit Integration Examples

Demonstrates safety validation for Solana blockchain transactions.

Run directly:
    python -m sentinelseed.integrations.solana_agent_kit.example

Options:
    --all       Run all examples including edge cases
    --help      Show this help message

Requirements:
    pip install sentinelseed
"""

import sys


def example_validator():
    """Example 1: Using SentinelValidator with custom limits."""
    print("\n" + "=" * 60)
    print("Example 1: SentinelValidator")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import (
        SentinelValidator,
        AddressValidationMode,
    )

    # Create validator with custom limits
    validator = SentinelValidator(
        seed_level="standard",
        max_transfer=50.0,  # Lower limit for demo
        confirm_above=10.0,
        address_validation=AddressValidationMode.WARN,
    )

    print(f"\nConfiguration:")
    print(f"  Max transfer: {validator.max_transfer} SOL")
    print(f"  Confirm above: {validator.confirm_above} SOL")
    print(f"  Address validation: {validator.address_validation.value}")

    # Test 1: Normal transaction
    print("\n--- Test: Normal transfer ---")
    result = validator.check(
        action="transfer",
        amount=5.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        purpose="Payment for development services",
    )
    print(f"  Safe: {result.should_proceed}")
    print(f"  Risk: {result.risk_level.name}")

    # Test 2: High-value transaction
    print("\n--- Test: High-value transfer ---")
    result = validator.check(
        action="transfer",
        amount=25.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        purpose="Large payment for quarterly services",
    )
    print(f"  Safe: {result.should_proceed}")
    print(f"  Requires confirmation: {result.requires_confirmation}")

    # Test 3: Exceeds limit
    print("\n--- Test: Exceeds transfer limit ---")
    result = validator.check(
        action="transfer",
        amount=100.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    )
    print(f"  Safe: {result.should_proceed}")
    print(f"  Concerns: {result.concerns}")


def example_address_validation():
    """Example 2: Address validation modes."""
    print("\n" + "=" * 60)
    print("Example 2: Address Validation")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import (
        SentinelValidator,
        AddressValidationMode,
        is_valid_solana_address,
    )

    # Valid Solana address
    valid_address = "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU"
    invalid_address = "not-a-valid-address"

    print(f"\nAddress validation function:")
    print(f"  '{valid_address[:20]}...' valid: {is_valid_solana_address(valid_address)}")
    print(f"  '{invalid_address}' valid: {is_valid_solana_address(invalid_address)}")

    # STRICT mode - rejects invalid addresses
    print("\n--- STRICT mode ---")
    validator_strict = SentinelValidator(
        address_validation=AddressValidationMode.STRICT
    )
    result = validator_strict.check(
        action="transfer",
        amount=1.0,
        recipient=invalid_address,
        purpose="Test transfer",
    )
    print(f"  Invalid address blocked: {not result.should_proceed}")
    if result.concerns:
        print(f"  Concern: {result.concerns[0]}")

    # WARN mode - allows but warns
    print("\n--- WARN mode (default) ---")
    validator_warn = SentinelValidator(
        address_validation=AddressValidationMode.WARN
    )
    result = validator_warn.check(
        action="transfer",
        amount=1.0,
        recipient=invalid_address,
        purpose="Test transfer",
    )
    print(f"  Transaction proceeds: {result.should_proceed}")
    if result.recommendations:
        print(f"  Recommendation: {result.recommendations[0]}")


def example_safe_transaction():
    """Example 3: Using the safe_transaction convenience function."""
    print("\n" + "=" * 60)
    print("Example 3: safe_transaction Function")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import safe_transaction

    # Quick validation
    print("\n--- Quick validation ---")
    result = safe_transaction(
        "transfer",
        amount=5.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        purpose="Quick payment",
    )
    print(f"  Result: {'SAFE' if result.should_proceed else 'BLOCKED'}")
    print(f"  Risk level: {result.risk_level.name}")

    # With params dict
    print("\n--- Using params dict ---")
    result = safe_transaction(
        "swap",
        params={
            "amount": 10.0,
            "purpose": "Token swap for liquidity",
        }
    )
    print(f"  Result: {'SAFE' if result.should_proceed else 'BLOCKED'}")


def example_purpose_gate():
    """Example 4: Purpose Gate validation."""
    print("\n" + "=" * 60)
    print("Example 4: Purpose Gate")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import SentinelValidator

    validator = SentinelValidator()

    # Without purpose
    print("\n--- Transfer without purpose ---")
    result = validator.check(
        action="transfer",
        amount=5.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
    )
    print(f"  Has concerns: {len(result.concerns) > 0}")
    if result.concerns:
        print(f"  Concern: {result.concerns[0][:60]}...")

    # With proper purpose
    print("\n--- Transfer with purpose ---")
    result = validator.check(
        action="transfer",
        amount=5.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        purpose="Monthly payment for hosting services",
    )
    print(f"  Has purpose concerns: {'purpose' in str(result.concerns).lower()}")
    print(f"  Risk level: {result.risk_level.name}")

    # With brief purpose (too short)
    print("\n--- Transfer with brief purpose ---")
    result = validator.check(
        action="transfer",
        amount=5.0,
        recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        purpose="pay",
    )
    print(f"  Concern about brief purpose: {'brief' in str(result.concerns).lower()}")


def example_middleware():
    """Example 5: Using SentinelSafetyMiddleware to wrap functions."""
    print("\n" + "=" * 60)
    print("Example 5: Safety Middleware")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import (
        SentinelSafetyMiddleware,
        SentinelValidator,
        TransactionBlockedError,
    )

    # Create middleware with custom validator
    validator = SentinelValidator(max_transfer=10.0)
    middleware = SentinelSafetyMiddleware(validator=validator)

    # Define a transfer function
    def my_transfer(amount: float, recipient: str) -> str:
        return f"Transferred {amount} SOL to {recipient[:16]}..."

    # Wrap with safety validation
    safe_transfer = middleware.wrap(my_transfer, "transfer")

    # Test safe transfer
    print("\n--- Safe transfer (5 SOL) ---")
    try:
        result = safe_transfer(5.0, "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
        print(f"  Result: {result}")
    except TransactionBlockedError as e:
        print(f"  Blocked: {e}")

    # Test blocked transfer
    print("\n--- Blocked transfer (50 SOL, exceeds limit) ---")
    try:
        result = safe_transfer(50.0, "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
        print(f"  Result: {result}")
    except TransactionBlockedError as e:
        print(f"  Blocked: {e}")


def example_actions():
    """Example 6: Creating validation actions for workflows."""
    print("\n" + "=" * 60)
    print("Example 6: Sentinel Actions")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

    actions = create_sentinel_actions()

    print("\nAvailable actions:")
    for name in actions.keys():
        print(f"  - {name}")

    # Use validate_transfer
    print("\n--- validate_transfer ---")
    result = actions["validate_transfer"](5.0, "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU")
    print(f"  Result: {result}")

    # Use validate_swap
    print("\n--- validate_swap ---")
    result = actions["validate_swap"](10.0, "SOL", "USDC")
    print(f"  Result: {result}")

    # Use validate_action for any action
    print("\n--- validate_action (stake) ---")
    result = actions["validate_action"](
        "stake",
        amount=100.0,
        purpose="Staking for validator rewards",
    )
    print(f"  Result: {result}")


def example_statistics():
    """Example 7: Validation statistics."""
    print("\n" + "=" * 60)
    print("Example 7: Statistics")
    print("=" * 60)

    from sentinelseed.integrations.solana_agent_kit import SentinelValidator

    validator = SentinelValidator(max_transfer=50.0)

    # Run several validations
    test_cases = [
        {"action": "transfer", "amount": 5.0, "purpose": "Payment 1"},
        {"action": "transfer", "amount": 10.0, "purpose": "Payment 2"},
        {"action": "transfer", "amount": 100.0},  # Exceeds limit
        {"action": "swap", "amount": 25.0, "purpose": "Token swap"},
        {"action": "transfer", "amount": 75.0},  # Exceeds limit
    ]

    print("\nRunning test validations...")
    for tc in test_cases:
        result = validator.check(
            action=tc["action"],
            amount=tc["amount"],
            recipient="7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
            purpose=tc.get("purpose", ""),
        )
        status = "SAFE" if result.should_proceed else "BLOCKED"
        print(f"  {tc['action']} {tc['amount']} SOL: {status}")

    # Get statistics
    stats = validator.get_stats()
    print(f"\nStatistics:")
    print(f"  Total validations: {stats['total']}")
    print(f"  Approved: {stats['approved']}")
    print(f"  Blocked: {stats['blocked']}")
    print(f"  Block rate: {stats['block_rate']:.1%}")


def main():
    """Run examples."""
    print("=" * 60)
    print("Sentinel + Solana Agent Kit Integration")
    print("=" * 60)
    print("\nDemonstrating safety validation for Solana transactions.")
    print("Documentation: https://github.com/sentinel-seed/sentinel/tree/main/src/sentinelseed/integrations/solana_agent_kit")

    # Check for help
    if "--help" in sys.argv or "-h" in sys.argv:
        print(__doc__)
        return

    # Run examples
    example_validator()
    example_address_validation()
    example_safe_transaction()
    example_purpose_gate()
    example_middleware()
    example_actions()

    # Extended examples
    if "--all" in sys.argv:
        example_statistics()

    print("\n" + "=" * 60)
    print("All examples completed successfully!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
