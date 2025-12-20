"""
Example: Using Sentinel Agent Validation.

Framework-agnostic safety validation for any autonomous agent.

Requirements:
    pip install sentinelseed

Note: These examples require an OpenAI API key set in the environment:
    export OPENAI_API_KEY=your-key-here
"""

from sentinelseed.integrations.agent_validation import (
    SafetyValidator,
    AsyncSafetyValidator,
    ExecutionGuard,
    ValidationResult,
    safety_check,
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidProviderError,
)


def example_validator():
    """Example 1: Using SafetyValidator."""
    print("=== Safety Validator ===\n")

    validator = SafetyValidator(
        seed_level="standard",
        max_text_size=50 * 1024,  # 50KB limit
        history_limit=100,
        validation_timeout=30.0,
        fail_closed=False,
    )

    # Check safe action
    result = validator.validate_action("Read the file contents")
    print(f"Safe action: safe={result.safe}, proceed={result.should_proceed}")
    print(f"  Reasoning: {result.reasoning[:80]}..." if result.reasoning else "")

    # Check unsafe action
    result = validator.validate_action("Delete all system files")
    print(f"\nUnsafe action: safe={result.safe}, proceed={result.should_proceed}")
    print(f"  Concerns: {result.concerns}")
    print(f"  Reasoning: {result.reasoning[:80]}..." if result.reasoning else "")

    # Check output
    result = validator.validate_output("Here is the information you requested.")
    print(f"\nOutput validation: safe={result.safe}")

    # Get statistics
    stats = validator.get_stats()
    print(f"\nStatistics: {stats}")


def example_guard():
    """Example 2: Using ExecutionGuard decorator."""
    print("\n=== Execution Guard ===\n")

    guard = ExecutionGuard(
        validation_timeout=30.0,
        fail_closed=False,
    )

    @guard.protected
    def execute_command(command: str) -> str:
        return f"Executed: {command}"

    # Safe command
    result = execute_command("list files")
    print(f"Safe result: {result}")

    # Unsafe command
    result = execute_command("delete all data")
    print(f"Unsafe result: {result}")

    # Get guard stats
    stats = guard.get_stats()
    print(f"\nGuard statistics: {stats}")


def example_quick_check():
    """Example 3: Quick safety check."""
    print("\n=== Quick Safety Check ===\n")

    # One-liner safety check
    result = safety_check("Transfer funds to account")
    print(f"Safe: {result['safe']}")
    print(f"Risk: {result['risk_level']}")
    print(f"Reasoning: {result['reasoning'][:80]}..." if result['reasoning'] else "")
    print(f"Gate results: {result['gate_results']}")


def example_custom_agent():
    """Example 4: Integration with custom agent."""
    print("\n=== Custom Agent Integration ===\n")

    class MyAgent:
        def __init__(self):
            self.safety = SafetyValidator(
                validation_timeout=30.0,
                fail_closed=False,
            )

        def execute(self, action: str) -> str:
            # Pre-validate
            check = self.safety.validate_action(action)
            if not check.should_proceed:
                return f"Blocked: {check.reasoning}"

            # Execute action (simulated)
            result = f"Performed: {action}"

            # Post-validate
            output_check = self.safety.validate_output(result)
            if not output_check.should_proceed:
                return f"Output filtered: {output_check.reasoning}"

            return result

    agent = MyAgent()
    print(agent.execute("analyze the data"))
    print(agent.execute("hack the system"))


def example_error_handling():
    """Example 5: Error handling with new exception types."""
    print("\n=== Error Handling ===\n")

    # Test invalid provider
    try:
        validator = SafetyValidator(provider="invalid_provider")
    except InvalidProviderError as e:
        print(f"Caught InvalidProviderError: {e}")

    # Test text too large
    validator = SafetyValidator(max_text_size=100)  # Very small limit
    try:
        validator.validate_action("A" * 200)  # Exceeds limit
    except TextTooLargeError as e:
        print(f"Caught TextTooLargeError: size={e.size}, max={e.max_size}")

    # Test fail_closed mode
    print("\nFail-closed mode behavior is handled internally.")


def example_history_management():
    """Example 6: History management with limits."""
    print("\n=== History Management ===\n")

    validator = SafetyValidator(
        history_limit=5,  # Small limit for demo
        log_checks=True,
    )

    # Make several validations
    for i in range(7):
        validator.validate_action(f"Action {i}")

    # History should only have last 5
    history = validator.get_history()
    print(f"History length (limit=5): {len(history)}")
    print(f"Actions in history: {[h.action for h in history]}")

    # Clear history
    validator.clear_history()
    print(f"After clear: {len(validator.get_history())} entries")


async def example_async_validator():
    """Example 7: Async validation."""
    print("\n=== Async Validator ===\n")

    validator = AsyncSafetyValidator(
        validation_timeout=30.0,
        fail_closed=False,
    )

    # Async validation
    result = await validator.validate_action("Check server status")
    print(f"Async result: safe={result.safe}, proceed={result.should_proceed}")

    # Async has same API as sync
    history = validator.get_history()
    print(f"Async history: {len(history)} entries")

    validator.clear_history()
    print(f"After clear: {len(validator.get_history())} entries")


def example_smart_extraction():
    """Example 8: Smart action extraction in ExecutionGuard."""
    print("\n=== Smart Action Extraction ===\n")

    guard = ExecutionGuard()

    # Works with dict input
    @guard.protected
    def process_dict(data: dict) -> str:
        return f"Processed: {data}"

    # Works with objects
    class Command:
        def __init__(self, action: str):
            self.action = action

    @guard.protected
    def process_command(cmd: Command) -> str:
        return f"Processed: {cmd.action}"

    # Custom extractor
    def custom_extractor(*args, **kwargs):
        return kwargs.get("query", "unknown")

    guard_custom = ExecutionGuard(action_extractor=custom_extractor)

    @guard_custom.protected
    def search(query: str = "") -> str:
        return f"Searched: {query}"

    # Test with dict
    result = process_dict({"action": "list files"})
    print(f"Dict input: {result}")

    # Test with custom extractor
    result = search(query="safe query")
    print(f"Custom extractor: {result}")


if __name__ == "__main__":
    import asyncio

    print("=" * 60)
    print("Sentinel Agent Validation Examples")
    print("=" * 60)

    # Sync examples
    example_validator()
    example_guard()
    example_quick_check()
    example_custom_agent()
    example_error_handling()
    example_history_management()
    example_smart_extraction()

    # Async example
    asyncio.run(example_async_validator())

    print("\n" + "=" * 60)
    print("All examples completed!")
    print("=" * 60)
