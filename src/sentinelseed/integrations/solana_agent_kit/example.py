"""
Example: Using Sentinel with Solana Agent Kit.

Shows how to add safety to Solana blockchain transactions.

Requirements:
    pip install solana sentinelseed
"""

from sentinelseed.integrations.solana_agent_kit import (
    SentinelValidator,
    SentinelSafetyMiddleware,
    safe_transaction,
    create_sentinel_actions,
)


def example_validator():
    """Example 1: Using SentinelValidator."""
    print("=== Sentinel Validator ===\n")

    # Create validator with custom limits
    validator = SentinelValidator(
        seed_level="standard",
        max_transfer=100.0,
        confirm_above=10.0
    )

    print(f"Max transfer limit: {validator.max_transfer} SOL")
    print(f"Confirm above: {validator.confirm_above} SOL")

    # Validate a transaction
    result = validator.check(
        action="transfer",
        amount=5.0,
        recipient="ABC123..."
    )

    print(f"\nTransaction check:")
    print(f"  Safe: {result.should_proceed}")
    print(f"  Risk level: {result.risk_level.value}")
    if result.concerns:
        print(f"  Concerns: {result.concerns}")


def example_safe_transaction():
    """Example 2: Using safe_transaction function."""
    print("\n=== Safe Transaction Function ===\n")

    # Quick validation without setting up a full validator
    result = safe_transaction(
        action="transfer",
        amount=5.0,
        recipient="ABC123..."
    )

    print(f"Transaction safe: {result.should_proceed}")
    print(f"Risk: {result.risk_level.value}")

    # High-value transaction
    high_value = safe_transaction(
        action="transfer",
        amount=50.0,
        recipient="XYZ789..."
    )

    print(f"\nHigh-value transaction:")
    print(f"  Requires confirmation: {high_value.requires_confirmation}")


def example_middleware():
    """Example 3: Using middleware to wrap functions."""
    print("\n=== Safety Middleware ===\n")

    middleware = SentinelSafetyMiddleware()

    # Wrap a function with safety validation
    def my_transfer(amount: float, recipient: str):
        return f"Transferred {amount} SOL to {recipient}"

    safe_transfer = middleware.wrap(my_transfer, "transfer")

    # This will be validated before execution
    try:
        result = safe_transfer(5.0, "valid_address")
        print(f"Result: {result}")
    except ValueError as e:
        print(f"Blocked: {e}")


def example_actions():
    """Example 4: Creating validation actions for custom workflows."""
    print("\n=== Sentinel Actions ===\n")

    actions = create_sentinel_actions()

    print("Available actions:")
    for name, func in actions.items():
        print(f"  - {name}")

    # Use the validate_transfer action
    result = actions["validate_transfer"](5.0, "ABC123...")
    print(f"\nValidate transfer result: {result}")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + Solana Agent Kit Integration Examples")
    print("=" * 60)

    example_validator()
    example_safe_transaction()
    example_middleware()
    example_actions()
