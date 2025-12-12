"""
Example: Using Sentinel with Solana Agent Kit.

Shows how to add safety to Solana blockchain transactions.

Requirements:
    pip install solana sentinelseed
"""

from sentinel.integrations.solana_agent_kit import (
    SentinelPlugin,
    SentinelSafetyMiddleware,
    safe_transaction,
    create_sentinel_actions,
)


def example_plugin():
    """Example 1: Using SentinelPlugin."""
    print("=== Sentinel Plugin ===\n")

    # Create plugin
    plugin = SentinelPlugin(seed_level="standard")

    print(f"Plugin name: {plugin.name}")
    print(f"Actions available: {len(plugin.actions)}")

    # Validate a transaction
    tx_data = {
        "type": "transfer",
        "amount": 1.0,
        "to": "recipient_address"
    }

    result = plugin.validate_transaction(tx_data)
    print(f"Transaction safe: {result['safe']}")


def example_middleware():
    """Example 2: Using middleware pattern."""
    print("\n=== Safety Middleware ===\n")

    middleware = SentinelSafetyMiddleware()

    # Check an action
    action = "Transfer 100 SOL to unknown address"
    result = middleware.check_action(action)

    print(f"Action: {action}")
    print(f"Safe: {result['safe']}")
    print(f"Risk: {result.get('risk_level', 'N/A')}")


def example_decorator():
    """Example 3: Using safe_transaction decorator."""
    print("\n=== Transaction Decorator ===\n")

    @safe_transaction
    def transfer_sol(amount: float, to_address: str):
        return f"Transferred {amount} SOL to {to_address}"

    # This will be validated before execution
    try:
        result = transfer_sol(1.0, "valid_address")
        print(f"Result: {result}")
    except Exception as e:
        print(f"Blocked: {e}")


def example_actions():
    """Example 4: Creating LangChain-compatible actions."""
    print("\n=== Sentinel Actions ===\n")

    actions = create_sentinel_actions()

    print("Available actions:")
    for action in actions:
        print(f"  - {action['name']}: {action['description'][:50]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + Solana Agent Kit Integration Examples")
    print("=" * 60)

    example_plugin()
    example_middleware()
    example_actions()
