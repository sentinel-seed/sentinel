"""
Example: Using Sentinel with Solana Agent Kit.

This example shows how to add AI safety validation to Solana blockchain agents:
1. SentinelValidator for transaction validation
2. safe_transaction convenience function
3. LangChain tools for agent self-validation
4. Function wrappers for automatic validation

IMPORTANT: Solana Agent Kit plugins add ACTIONS, not middleware.
This integration provides validation to use BEFORE executing transactions.

For production use, install: pip install sentinelseed
"""

from sentinel.integrations.solana_agent_kit import (
    SentinelValidator,
    SentinelSafetyMiddleware,
    safe_transaction,
    create_sentinel_actions,
    TransactionRisk,
)


def example_basic_validation():
    """Example 1: Basic transaction validation."""
    print("=== Basic Transaction Validation ===\n")

    # Create validator with custom limits
    validator = SentinelValidator(
        max_transfer=100.0,      # Max 100 SOL per transaction
        confirm_above=10.0,      # Flag transfers above 10 SOL
        blocked_addresses=["ScamWallet123..."],
    )

    # Test various transactions
    transactions = [
        ("transfer", {"amount": 5, "recipient": "FriendWallet..."}),
        ("transfer", {"amount": 150, "recipient": "XYZ789..."}),  # Over limit
        ("swap", {"amount": 20}),
        ("drain", {"amount": 100}),  # Suspicious pattern
        ("stake", {"amount": 50}),
        ("transfer", {"amount": 10, "recipient": "ScamWallet123..."}),  # Blocked
    ]

    for action, params in transactions:
        result = validator.check(action, **params)
        status = "SAFE" if result.should_proceed else "BLOCKED"
        print(f"[{status}] {action}: {params.get('amount', 'N/A')} SOL")
        print(f"  Risk: {result.risk_level.value}")
        if result.concerns:
            print(f"  Concerns: {result.concerns[:2]}")
        if result.requires_confirmation:
            print(f"  Requires confirmation: yes")
        print()

    # Show statistics
    print("--- Statistics ---")
    stats = validator.get_stats()
    print(f"Total: {stats['total']}")
    print(f"Blocked: {stats['blocked']}")
    print(f"Block rate: {stats['block_rate']:.1%}")


def example_convenience_function():
    """Example 2: Using safe_transaction convenience function."""
    print("\n=== Convenience Function ===\n")

    # Quick checks without creating a validator
    checks = [
        ("transfer", {"amount": 5, "recipient": "Friend..."}),
        ("transfer", {"amount": 500, "recipient": "Unknown..."}),
        ("swap", {"amount": 10}),
        ("drain_all", {"target": "wallet"}),
    ]

    for action, params in checks:
        result = safe_transaction(action, **params)
        symbol = "SAFE" if result.should_proceed else "BLOCKED"
        print(f"[{symbol}] {action}")
        print(f"  Risk: {result.risk_level.value}")
        if result.recommendations:
            print(f"  Tip: {result.recommendations[0]}")
        print()


def example_with_solana_agent_kit():
    """Example 3: Integration pattern with Solana Agent Kit."""
    print("\n=== Solana Agent Kit Pattern ===\n")

    # This shows the CORRECT pattern for using with SAK
    # Note: SAK doesn't have middleware - we validate BEFORE calling

    validator = SentinelValidator(max_transfer=50.0)

    # Simulated SAK usage (replace with real SAK in production)
    class MockSolanaAgent:
        def transfer(self, recipient, amount):
            return f"Transferred {amount} SOL to {recipient}"

    agent = MockSolanaAgent()

    # The correct pattern: validate, then execute
    transfers = [
        (10.0, "Friend123..."),
        (100.0, "Unknown..."),   # Will be blocked
        (25.0, "Colleague..."),
    ]

    for amount, recipient in transfers:
        # 1. Validate with Sentinel
        result = validator.check("transfer", amount=amount, recipient=recipient)

        # 2. Execute only if safe
        if result.should_proceed:
            tx_result = agent.transfer(recipient, amount)
            print(f"EXECUTED: {tx_result}")
        else:
            print(f"BLOCKED: Transfer {amount} to {recipient[:8]}...")
            print(f"  Reason: {result.concerns}")
        print()


def example_function_wrapper():
    """Example 4: Using SentinelSafetyMiddleware to wrap functions."""
    print("\n=== Function Wrapper ===\n")

    middleware = SentinelSafetyMiddleware()

    # Your original function
    def do_transfer(amount, recipient):
        return f"Sent {amount} to {recipient}"

    # Wrap with validation
    safe_transfer = middleware.wrap(do_transfer, "transfer")

    # Test wrapped function
    tests = [
        (5.0, "GoodAddress..."),
        (500.0, "Unknown..."),  # Should raise
    ]

    for amount, recipient in tests:
        try:
            result = safe_transfer(amount, recipient)
            print(f"SUCCESS: {result}")
        except ValueError as e:
            print(f"BLOCKED: {e}")
        print()


def example_sentinel_actions():
    """Example 5: Using validation actions dict."""
    print("\n=== Validation Actions ===\n")

    actions = create_sentinel_actions()

    print("Available actions:")
    for name in actions.keys():
        print(f"  - {name}")
    print()

    # Test validate_transfer
    print("Testing validate_transfer:")
    result = actions["validate_transfer"](10.0, "Friend...")
    print(f"  Safe: {result['safe']}, Risk: {result['risk']}")

    result = actions["validate_transfer"](500.0, "Unknown...")
    print(f"  Safe: {result['safe']}, Risk: {result['risk']}")
    print()

    # Test validate_swap
    print("Testing validate_swap:")
    result = actions["validate_swap"](50.0, "SOL", "USDC")
    print(f"  Safe: {result['safe']}, Risk: {result['risk']}")


def example_langchain_integration():
    """Example 6: LangChain tools (simulated - requires langchain)."""
    print("\n=== LangChain Tools (Pattern) ===\n")

    # This shows how it would work with LangChain
    # In real usage: from sentinel.integrations.solana_agent_kit import create_langchain_tools

    print("""
# Real LangChain usage:

from langchain.agents import create_react_agent
from solana_agent_kit import createSolanaTools
from sentinel.integrations.solana_agent_kit import create_langchain_tools

# Get Solana tools
solana_tools = createSolanaTools(agent)

# Add Sentinel safety tool
safety_tools = create_langchain_tools()

# Combine for agent
all_tools = solana_tools + safety_tools
agent = create_react_agent(llm, all_tools)

# Agent can now call "sentinel_check_transaction" before actions:
# Input: "transfer 5.0 ABC123..."
# Output: "SAFE: transfer validated" or "BLOCKED: ..."
""")

    # Simulate what the tool does
    from sentinel.integrations.solana_agent_kit import SentinelValidator

    validator = SentinelValidator()

    def mock_tool(description: str) -> str:
        parts = description.strip().split()
        action = parts[0] if parts else "unknown"
        amount = float(parts[1]) if len(parts) > 1 else 0
        recipient = parts[2] if len(parts) > 2 else ""

        result = validator.check(action, amount=amount, recipient=recipient)

        if result.should_proceed:
            return f"SAFE: {action} validated"
        else:
            return f"BLOCKED: {', '.join(result.concerns)}"

    # Test the tool pattern
    test_inputs = [
        "transfer 5.0 Friend123",
        "transfer 500.0 Unknown",
        "drain 1000.0",
    ]

    print("Simulating tool calls:")
    for inp in test_inputs:
        output = mock_tool(inp)
        print(f"  Input:  {inp}")
        print(f"  Output: {output}")
        print()


def example_defi_scenarios():
    """Example 7: Common DeFi scenarios."""
    print("\n=== DeFi Scenarios ===\n")

    validator = SentinelValidator(
        max_transfer=500.0,
        confirm_above=50.0,
    )

    scenarios = [
        # Safe operations
        ("Jupiter Swap", "swap", {"amount": 100}),
        ("Stake SOL", "stake", {"amount": 200}),
        ("NFT Mint", "mint", {"amount": 2.5}),

        # Potentially risky
        ("Large Swap", "swap", {"amount": 1000}),

        # Suspicious
        ("Drain Pattern", "drain_all", {"amount": 500}),
        ("Sweep Wallet", "sweep", {"amount": 100}),
    ]

    risk_emoji = {
        TransactionRisk.LOW: "LOW",
        TransactionRisk.MEDIUM: "MED",
        TransactionRisk.HIGH: "HIGH",
        TransactionRisk.CRITICAL: "CRIT",
    }

    for name, action, params in scenarios:
        result = validator.check(action, **params)
        risk = risk_emoji.get(result.risk_level, "???")
        status = "PASS" if result.should_proceed else "FAIL"

        print(f"[{status}] [{risk}] {name}")
        if result.concerns:
            print(f"  Concerns: {result.concerns[:1]}")
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + Solana Agent Kit Integration Examples")
    print("=" * 60)
    print()
    print("NOTE: Solana Agent Kit plugins add ACTIONS, not middleware.")
    print("This integration provides validation to use BEFORE transactions.")
    print()

    example_basic_validation()
    example_convenience_function()
    example_with_solana_agent_kit()
    example_function_wrapper()
    example_sentinel_actions()
    example_langchain_integration()
    example_defi_scenarios()
