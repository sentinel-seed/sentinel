"""
Example: Using Sentinel Safety Plugin with Virtuals Protocol GAME SDK

This example demonstrates how to integrate Sentinel's safety guardrails
with AI agents built on the GAME SDK.

Prerequisites:
    pip install game-sdk sentinelseed

Note: This is a demonstration script. You'll need a valid GAME API key
to actually run agents.
"""

import json
import logging

# Set up logging to see Sentinel validation results
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import from local plugin (same directory)
# In production with sentinelseed package: from sentinelseed.integrations.virtuals import ...
from plugin import (
    SentinelWorkerConfig,
    SentinelValidator,
    sentinel_protected,
    SentinelValidationError,
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
    config = SentinelWorkerConfig(
        max_token_amount=500.0,
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
        # Blocked by HARM gate (suspicious pattern)
        {
            "name": "approve_unlimited",
            "args": {"spender": "0x...", "amount": "0xffffffffffffffffffffffffffffffff"},
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

    @sentinel_protected(level="standard", block_on_failure=True)
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
    trading_config = SentinelWorkerConfig(
        max_token_amount=10000.0,  # Higher limit for trading
        require_confirmation_above=1000.0,
        block_unsafe=True,
        seed_level="standard",

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
    result = validator.validate("swap_tokens", {"amount": 500, "from": "SOL", "to": "USDC"}, {"purpose": "Rebalance portfolio"})
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
# Example 4: GAME SDK Integration (Mock)
# =============================================================================

def example_game_sdk_integration():
    """Demonstrate integration with GAME SDK (mocked for demo)."""
    print("\n" + "="*60)
    print("Example 4: GAME SDK Integration (Conceptual)")
    print("="*60)

    print("""
This example shows how you would integrate with the GAME SDK in production:

```python
from game_sdk.game import Agent, WorkerConfig, Function, Argument
from sentinel.integrations.virtuals import (
    wrap_agent_with_sentinel,
    SentinelWorkerConfig,
    SentinelSafetyWorker,
)

# 1. Create your worker functions
def transfer_tokens(recipient: str, amount: float, purpose: str = ""):
    # Your transfer logic
    return {"status": "success", "tx": "0x..."}

transfer_fn = Function(
    fn_name="transfer_tokens",
    fn_description="Transfer tokens to a recipient",
    args=[
        Argument(name="recipient", type="string", description="Wallet address"),
        Argument(name="amount", type="number", description="Amount to send"),
        Argument(name="purpose", type="string", description="Reason for transfer"),
    ],
    executable=transfer_tokens,
)

# 2. Create worker config
trading_worker = WorkerConfig(
    id="trading_worker",
    worker_description="Executes token transfers and swaps",
    get_state_fn=lambda result, state: state,
    action_space=[transfer_fn],
)

# 3. Create safety worker (optional but recommended)
safety_worker = SentinelSafetyWorker.create_worker_config()

# 4. Create agent
agent = Agent(
    api_key="your-game-api-key",
    name="TradingBot",
    goal="Safely execute user-requested trades",
    workers=[safety_worker, trading_worker],
)

# 5. Wrap with Sentinel protection
config = SentinelWorkerConfig(
    max_token_amount=1000,
    require_confirmation_above=100,
    block_unsafe=True,
)
agent = wrap_agent_with_sentinel(agent, config)

# 6. Run agent
agent.compile()
while True:
    agent.step()  # All actions validated through THSP
```
""")


# =============================================================================
# Example 5: Handling Validation Results
# =============================================================================

def example_handling_results():
    """Demonstrate proper handling of validation results."""
    print("\n" + "="*60)
    print("Example 5: Handling Validation Results")
    print("="*60)

    config = SentinelWorkerConfig(block_unsafe=False)  # Log-only mode
    validator = SentinelValidator(config)

    # Simulate validation with detailed handling
    actions_to_validate = [
        ("send_tokens", {"amount": 2000, "to": "0x..."}, {"purpose": "Large transfer"}),
        ("approve", {"spender": "0x...", "amount": 999999999}, {}),
    ]

    for action_name, args, context in actions_to_validate:
        print(f"\nValidating: {action_name}")
        result = validator.validate(action_name, args, context)

        if result.passed:
            print("  [OK] Action approved")
            # Proceed with action
        else:
            print(f"  [X] Action flagged")
            print(f"    Blocked gate: {result.blocked_gate}")
            print(f"    Failed gates: {result.failed_gates}")

            for concern in result.concerns:
                print(f"    - {concern}")

            # In production, you might:
            # 1. Request user confirmation
            # 2. Log for audit
            # 3. Modify the action to comply
            # 4. Reject the action entirely


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    print("""
================================================================================
  SENTINEL SAFETY PLUGIN FOR VIRTUALS PROTOCOL - EXAMPLES

  This script demonstrates various ways to use Sentinel's THSP Protocol
  to protect AI agents built on the GAME SDK.
================================================================================
""")

    example_basic_validation()
    example_decorator_usage()
    example_custom_config()
    example_game_sdk_integration()
    example_handling_results()

    print("\n" + "="*60)
    print("All examples completed!")
    print("="*60)
    print("\nFor more information, see:")
    print("  - https://sentinelseed.dev/docs")
    print("  - https://github.com/sentinel-seed/sentinel")
    print("  - https://whitepaper.virtuals.io/developer-documents/game-framework/agent-sdk")
