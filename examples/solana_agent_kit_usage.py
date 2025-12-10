"""
Example: Using Sentinel with Solana Agent Kit.

This example shows how to add AI safety to Solana blockchain agents:
1. SentinelPlugin for transaction validation
2. SentinelSafetyMiddleware for method wrapping
3. Standalone safe_transaction function
4. Creating safety actions for agents

Note: These examples work without actual Solana connection.
For production use, install: pip install solana-agent-kit sentinelseed
"""

from sentinel.integrations.solana_agent_kit import (
    SentinelPlugin,
    SentinelSafetyMiddleware,
    safe_transaction,
    create_sentinel_actions,
    TransactionRisk,
)


def example_plugin_validation():
    """Example 1: Using SentinelPlugin for transaction validation."""
    print("=== Plugin Transaction Validation ===\n")

    # Create plugin with custom limits
    plugin = SentinelPlugin(
        max_single_transfer=100.0,  # Max 100 SOL per transaction
        require_confirmation_above=10.0,  # Confirm above 10 SOL
        block_suspicious=True,
    )

    # Test various transactions
    transactions = [
        ("transfer", {"amount": 5, "recipient": "ABC123..."}),
        ("transfer", {"amount": 150, "recipient": "XYZ789..."}),  # Over limit
        ("swap", {"amount": 20, "from_token": "SOL", "to_token": "USDC"}),
        ("drain_wallet", {"target": "all_tokens"}),  # Suspicious
        ("stake", {"amount": 50, "validator": "Validator123..."}),
        ("approve", {"amount": "unlimited", "spender": "Contract..."}),  # Suspicious
    ]

    for action, params in transactions:
        result = plugin.validate_transaction(action, params)
        status = "✓ SAFE" if result.should_proceed else "✗ BLOCKED"
        print(f"{status} | {action}: {params.get('amount', 'N/A')} SOL")
        print(f"  Risk: {result.risk_level.value}")
        if result.concerns:
            print(f"  Concerns: {result.concerns[:2]}")
        if result.requires_confirmation:
            print(f"  ⚠️  Requires confirmation")
        print()

    # Show safety report
    print("--- Safety Report ---")
    report = plugin.get_safety_report()
    print(f"Total transactions: {report['total_transactions']}")
    print(f"Blocked: {report['blocked']}")
    print(f"High risk: {report['high_risk']}")
    print(f"Block rate: {report['block_rate']:.1%}")


def example_standalone_check():
    """Example 2: Using standalone safe_transaction function."""
    print("\n=== Standalone Safety Check ===\n")

    # Quick checks without full plugin setup
    checks = [
        ("transfer", {"amount": 1, "recipient": "Friend123..."}),
        ("transfer", {"amount": 1000, "recipient": "Unknown..."}),
        ("nft_mint", {"collection": "MyNFT", "name": "Token #1"}),
        ("execute_arbitrary", {"code": "malicious_payload"}),
    ]

    for action, params in checks:
        result = safe_transaction(action, params)
        symbol = "✓" if result.should_proceed else "✗"
        print(f"{symbol} {action}")
        print(f"  Risk level: {result.risk_level.value}")
        if result.recommendations:
            print(f"  Recommendation: {result.recommendations[0]}")
        print()


def example_address_blacklist():
    """Example 3: Using address blacklists."""
    print("\n=== Address Blacklist Example ===\n")

    # Known bad addresses
    blocked_addresses = [
        "ScamWallet123...",
        "DrainerContract456...",
        "SuspiciousAddress789...",
    ]

    plugin = SentinelPlugin(
        blocked_addresses=blocked_addresses,
        block_suspicious=True,
    )

    # Test transfers to various addresses
    transfers = [
        {"amount": 10, "recipient": "LegitFriend..."},
        {"amount": 5, "recipient": "ScamWallet123..."},  # Blocked
        {"amount": 20, "recipient": "AnotherGoodAddress..."},
        {"amount": 1, "recipient": "DrainerContract456..."},  # Blocked
    ]

    for params in transfers:
        result = plugin.validate_transaction("transfer", params)
        status = "ALLOWED" if result.should_proceed else "BLOCKED"
        print(f"[{status}] Transfer to {params['recipient'][:15]}...")
        if not result.should_proceed:
            print(f"  Reason: {result.concerns}")


def example_program_whitelist():
    """Example 4: Using program ID whitelists."""
    print("\n=== Program Whitelist Example ===\n")

    # Only allow known DeFi programs
    allowed_programs = [
        "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB",  # Jupiter
        "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc",  # Orca Whirlpool
        "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium
    ]

    plugin = SentinelPlugin(
        allowed_programs=allowed_programs,
    )

    # Test interactions with various programs
    interactions = [
        ("swap", {"program_id": "JUP4Fb2cqiRUcaTHdrPC8h2gNsA2ETXiPDD33WcGuJB", "amount": 10}),
        ("swap", {"program_id": "UnknownProgram123...", "amount": 10}),  # Not whitelisted
        ("stake", {"program_id": "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc", "amount": 50}),
    ]

    for action, params in interactions:
        result = plugin.validate_transaction(action, params)
        program = params.get("program_id", "")[:8]
        status = "✓" if result.should_proceed else "✗"
        print(f"{status} {action} via {program}...")
        if result.concerns:
            print(f"  Concerns: {result.concerns}")


def example_sentinel_actions():
    """Example 5: Creating actions for AI agents."""
    print("\n=== Sentinel Actions for Agents ===\n")

    # Create actions that can be added to an agent's toolkit
    actions = create_sentinel_actions()

    print("Available Sentinel actions:")
    for name, func in actions.items():
        print(f"  - {name}")

    print("\n--- Testing sentinel_check_transaction ---")

    # Test the check_transaction action
    check = actions["sentinel_check_transaction"]

    result = check("transfer", amount=5, recipient="FriendWallet...")
    print(f"Safe transfer: {result['safe']}")

    result = check("drain", amount=1000, recipient="Unknown...")
    print(f"Drain attempt: {result['safe']}")
    if not result["safe"]:
        print(f"  Concerns: {result['concerns']}")

    print("\n--- Testing sentinel_validate_intent ---")

    validate = actions["sentinel_validate_intent"]

    intents = [
        "Send 10 SOL to my friend's wallet for the hackathon prize",
        "Drain all tokens from the target wallet to my address",
        "Stake SOL with a reputable validator for rewards",
    ]

    for intent in intents:
        result = validate(intent)
        status = "SAFE" if result["safe"] else "FLAGGED"
        print(f"[{status}] {intent[:50]}...")


def example_high_value_alerts():
    """Example 6: High-value transaction handling."""
    print("\n=== High-Value Transaction Alerts ===\n")

    plugin = SentinelPlugin(
        require_confirmation_above=5.0,  # Low threshold for demo
    )

    amounts = [1, 5, 10, 50, 100]

    for amount in amounts:
        result = plugin.validate_transaction("transfer", {
            "amount": amount,
            "recipient": "SomeWallet..."
        })

        if result.requires_confirmation:
            print(f"⚠️  {amount} SOL - CONFIRMATION REQUIRED")
            print(f"   Risk level: {result.risk_level.value}")
            print(f"   Recommendations: {result.recommendations}")
        else:
            print(f"✓  {amount} SOL - Auto-approved")


def example_defi_scenarios():
    """Example 7: Common DeFi scenarios."""
    print("\n=== DeFi Scenario Validation ===\n")

    plugin = SentinelPlugin(
        max_single_transfer=500.0,
        block_suspicious=True,
    )

    scenarios = [
        # Safe operations
        ("Jupiter Swap", "swap", {
            "amount": 100,
            "from_token": "SOL",
            "to_token": "USDC",
            "slippage": 0.5,
        }),
        ("Marinade Stake", "stake", {
            "amount": 200,
            "protocol": "marinade",
            "validator": "Marinade-Pool",
        }),
        ("NFT Mint", "nft_mint", {
            "collection": "MyCollection",
            "name": "NFT #123",
            "price": 2.5,
        }),

        # Potentially risky
        ("Large Swap", "swap", {
            "amount": 1000,  # Over limit
            "from_token": "SOL",
            "to_token": "UNKNOWN_TOKEN",
        }),
        ("Unlimited Approve", "approve", {
            "amount": "unlimited",
            "spender": "RandomContract...",
            "token": "SOL",
        }),

        # Suspicious
        ("Rug Pattern", "transfer_all", {
            "to": "NewWallet...",
            "drain": True,
        }),
    ]

    for name, action, params in scenarios:
        result = plugin.validate_transaction(action, params)
        risk_emoji = {
            TransactionRisk.LOW: "🟢",
            TransactionRisk.MEDIUM: "🟡",
            TransactionRisk.HIGH: "🟠",
            TransactionRisk.CRITICAL: "🔴",
        }
        emoji = risk_emoji.get(result.risk_level, "⚪")
        status = "PASS" if result.should_proceed else "FAIL"

        print(f"{emoji} [{status}] {name}")
        print(f"   Action: {action}")
        if result.concerns:
            print(f"   Concerns: {result.concerns[:2]}")
        if result.recommendations:
            print(f"   Recommendations: {result.recommendations[:1]}")
        print()


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + Solana Agent Kit Integration Examples")
    print("=" * 60)

    example_plugin_validation()
    example_standalone_check()
    example_address_blacklist()
    example_program_whitelist()
    example_sentinel_actions()
    example_high_value_alerts()
    example_defi_scenarios()
