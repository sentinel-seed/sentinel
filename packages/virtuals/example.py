"""
Example: Using Sentinel Safety Plugin with Virtuals Protocol GAME SDK

This example demonstrates how to integrate Sentinel's safety guardrails
with AI agents built on the GAME SDK.

Prerequisites:
    pip install game-sdk sentinelseed

Note: This is a demonstration script. You'll need a valid GAME API key
to actually run agents. Get one at https://console.game.virtuals.io/
"""

import json
import logging

# Set up logging to see Sentinel validation results
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from local plugin
from plugin import (
    SentinelConfig,
    SentinelValidator,
    SentinelSafetyWorker,
    sentinel_protected,
    SentinelValidationError,
    GAME_SDK_AVAILABLE,
)


# =============================================================================
# Example 1: Basic Validation (No GAME SDK Required)
# =============================================================================

def example_basic_validation():
    """Demonstrate THSP validation without GAME SDK."""
    print("\n" + "="*60)
    print("Example 1: Basic THSP Validation")
    print("="*60)

    # Create validator with config
    config = SentinelConfig(
        max_transaction_amount=500.0,
        require_confirmation_above=100.0,
        block_unsafe=True,
    )
    validator = SentinelValidator(config)

    # Test various actions
    test_cases = [
        # Safe actions
        {
            "name": "get_balance",
            "args": {"wallet": "0x123..."},
            "context": {"purpose": "Check user balance"},
            "expected": "pass",
        },
        {
            "name": "swap_tokens",
            "args": {"amount": 50, "from": "SOL", "to": "USDC"},
            "context": {"purpose": "User requested swap"},
            "expected": "pass",
        },
        # Blocked by SCOPE gate (amount too high)
        {
            "name": "transfer",
            "args": {"amount": 1000, "recipient": "0x..."},
            "context": {"purpose": "Payment"},
            "expected": "fail",
        },
        # Blocked by HARM gate (blocked function)
        {
            "name": "drain_wallet",
            "args": {"target": "0x..."},
            "context": {},
            "expected": "fail",
        },
        # Blocked by HARM gate (private key exposure)
        {
            "name": "sign_message",
            "args": {"private_key": "a1b2c3d4e5f6789012345678901234567890123456789012345678901234567890"},
            "context": {},
            "expected": "fail",
        },
        # Blocked by PURPOSE gate (no purpose for high-risk action)
        {
            "name": "transfer",
            "args": {"amount": 50, "recipient": "0x..."},
            "context": {},  # Missing purpose
            "expected": "fail",
        },
        # Blocked by TRUTH gate (misleading name)
        {
            "name": "safe_drain_wallet",
            "args": {},
            "context": {},
            "expected": "fail",
        },
    ]

    for i, test in enumerate(test_cases, 1):
        result = validator.validate(
            action_name=test["name"],
            action_args=test["args"],
            context=test["context"],
        )

        status = "PASSED" if result.passed else "BLOCKED"
        match = "[OK]" if (result.passed and test["expected"] == "pass") or \
                       (not result.passed and test["expected"] == "fail") else "[FAIL]"

        print(f"\n{match} Test {i}: {test['name']}")
        print(f"   Status: {status}")
        print(f"   Gates: {result.gate_results}")
        if result.concerns:
            print(f"   Concerns: {result.concerns}")


# =============================================================================
# Example 2: Decorator Usage
# =============================================================================

def example_decorator_usage():
    """Demonstrate protecting functions with decorators."""
    print("\n" + "="*60)
    print("Example 2: Decorator Protection")
    print("="*60)

    @sentinel_protected(config=SentinelConfig(block_unsafe=True))
    def safe_transfer(recipient: str, amount: float, purpose: str = "") -> dict:
        """Transfer tokens with Sentinel protection."""
        return {
            "status": "success",
            "recipient": recipient,
            "amount": amount,
            "tx_hash": "0xabc123...",
        }

    # This should pass (reasonable amount with purpose)
    print("\n1. Testing safe transfer (50 tokens with purpose)...")
    try:
        result = safe_transfer(
            recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f4E2",
            amount=50,
            purpose="Payment for artwork purchase",
        )
        print(f"   [OK] Transfer succeeded: {result}")
    except SentinelValidationError as e:
        print(f"   [X] Transfer blocked: {e.concerns}")

    # This should fail (no purpose for transfer)
    print("\n2. Testing transfer without purpose...")
    try:
        result = safe_transfer(
            recipient="0x742d35Cc6634C0532925a3b844Bc9e7595f4E2",
            amount=50,
        )
        print(f"   [X] Transfer succeeded (should have been blocked): {result}")
    except SentinelValidationError as e:
        print(f"   [OK] Transfer blocked as expected")
        print(f"      Gate: {e.gate}")
        print(f"      Concerns: {e.concerns}")


# =============================================================================
# Example 3: Custom Configuration
# =============================================================================

def example_custom_config():
    """Demonstrate custom configuration for specific use cases."""
    print("\n" + "="*60)
    print("Example 3: Custom Configuration")
    print("="*60)

    # Trading bot config - higher limits, specific patterns
    trading_config = SentinelConfig(
        max_transaction_amount=10000.0,  # Higher limit for trading
        require_confirmation_above=1000.0,
        block_unsafe=True,

        # Only allow trading-related functions
        allowed_functions=[
            "swap_tokens",
            "get_price",
            "get_balance",
            "place_limit_order",
            "cancel_order",
        ],

        # Block dangerous operations
        blocked_functions=[
            "transfer_to_external",
            "approve_unlimited",
            "export_keys",
        ],

        # Custom patterns for trading scams
        suspicious_patterns=[
            r"(?i)guaranteed.*profit",
            r"(?i)100x.*return",
            r"(?i)honeypot",
            r"(?i)rug.*pull",
        ],
    )

    validator = SentinelValidator(trading_config)

    # Test allowed function
    print("\n1. Testing allowed function (swap_tokens)...")
    result = validator.validate(
        "swap_tokens",
        {"amount": 500, "from": "SOL", "to": "USDC"},
        {"purpose": "Rebalance portfolio"}
    )
    print(f"   {'[OK]' if result.passed else '[X]'} swap_tokens: {result.passed}")

    # Test blocked function
    print("\n2. Testing blocked function (transfer_to_external)...")
    result = validator.validate("transfer_to_external", {"amount": 100}, {})
    print(f"   {'[OK]' if not result.passed else '[X]'} transfer_to_external blocked: {not result.passed}")

    # Test non-whitelisted function
    print("\n3. Testing non-whitelisted function (stake_tokens)...")
    result = validator.validate("stake_tokens", {"amount": 100}, {"purpose": "Earn yield"})
    print(f"   {'[OK]' if not result.passed else '[X]'} stake_tokens blocked (not in whitelist): {not result.passed}")


# =============================================================================
# Example 4: GAME SDK Integration
# =============================================================================

def example_game_sdk_integration():
    """Demonstrate integration with GAME SDK."""
    print("\n" + "="*60)
    print("Example 4: GAME SDK Integration")
    print("="*60)

    if GAME_SDK_AVAILABLE:
        print("\nGAME SDK is available. Here's how to use it:")
    else:
        print("\nGAME SDK not installed. Install with: pip install game-sdk")

    print("""
Integration pattern with GAME SDK:

```python
import os
from game_sdk.game.agent import Agent, WorkerConfig
from game_sdk.game.custom_types import Function, Argument, FunctionResultStatus
from sentinel.integrations.virtuals import (
    SentinelConfig,
    SentinelSafetyWorker,
    create_sentinel_function,
    wrap_functions_with_sentinel,
)

# 1. Define your function
def transfer_tokens(recipient: str, amount: float, purpose: str = ""):
    # Your transfer logic here
    return (FunctionResultStatus.DONE, f"Transferred {amount} to {recipient}", {})

# 2. Create GAME Function
transfer_fn = Function(
    fn_name="transfer_tokens",
    fn_description="Transfer tokens to a recipient wallet",
    args=[
        Argument(name="recipient", description="Wallet address", type="string"),
        Argument(name="amount", description="Amount to send", type="number"),
        Argument(name="purpose", description="Reason for transfer", type="string", optional=True),
    ],
    executable=transfer_tokens,
)

# 3. Wrap with Sentinel protection
config = SentinelConfig(max_transaction_amount=1000, block_unsafe=True)
safe_transfer_fn = create_sentinel_function(transfer_fn, config)

# 4. Create Sentinel Safety Worker (recommended)
safety_worker = SentinelSafetyWorker.create_worker_config(config)

# 5. Create your trading worker
def get_trading_state(fn_result, current_state):
    return {"balance": 1000, "last_action": fn_result}

trading_worker = WorkerConfig(
    id="trading_worker",
    worker_description="Executes token transfers and swaps safely",
    get_state_fn=get_trading_state,
    action_space=[safe_transfer_fn],  # Using wrapped function
)

# 6. Create agent
agent = Agent(
    api_key=os.environ.get("GAME_API_KEY"),
    name="SafeTradingBot",
    agent_goal="Execute safe token operations",
    agent_description="A trading bot with Sentinel safety validation",
    get_agent_state_fn=lambda r, s: {"status": "active"},
    workers=[safety_worker, trading_worker],  # Safety worker first
)

# 7. Run agent
agent.compile()
agent.run()
```

Key points:
- Use `create_sentinel_function()` to wrap individual functions
- Add `SentinelSafetyWorker` as the first worker for self-validation
- The agent can call `check_action_safety` before sensitive operations
""")


# =============================================================================
# Example 5: Safety Worker Demo
# =============================================================================

def example_safety_worker():
    """Demonstrate the safety worker's check function."""
    print("\n" + "="*60)
    print("Example 5: Safety Worker Check Function")
    print("="*60)

    # Create safety worker instance (without GAME SDK)
    config = SentinelConfig(max_transaction_amount=500)
    worker = SentinelSafetyWorker(config)

    # Test the check_action_safety function (same as what the agent would call)
    test_actions = [
        ("transfer", '{"amount": 100, "recipient": "0x..."}', "Payment for services"),
        ("transfer", '{"amount": 1000, "recipient": "0x..."}', "Large payment"),
        ("drain_wallet", '{}', ""),
        ("swap", '{"amount": 50}', ""),  # No purpose
    ]

    print("\nSimulating what the Safety Worker would return:\n")

    for action_name, args_json, purpose in test_actions:
        status, message, info = worker.check_action_safety(action_name, args_json, purpose)
        print(f"Action: {action_name}")
        print(f"  Status: {status}")
        print(f"  Message: {message}")
        print(f"  Safe: {info.get('safe')}")
        if info.get('concerns'):
            print(f"  Concerns: {info.get('concerns')}")
        print()


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("""
================================================================================
  SENTINEL SAFETY PLUGIN FOR VIRTUALS PROTOCOL GAME SDK - EXAMPLES

  This script demonstrates how to use Sentinel's THSP Protocol
  to protect AI agents built on the GAME SDK.

  GAME SDK: pip install game-sdk
  Documentation: https://docs.game.virtuals.io/
================================================================================
""")

    example_basic_validation()
    example_decorator_usage()
    example_custom_config()
    example_game_sdk_integration()
    example_safety_worker()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
    print("\nFor more information, see:")
    print("  - https://sentinelseed.dev/docs")
    print("  - https://github.com/sentinel-seed/sentinel")
    print("  - https://docs.game.virtuals.io/")
