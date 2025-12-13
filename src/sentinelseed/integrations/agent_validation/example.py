"""
Example: Using Sentinel Agent Validation.

Framework-agnostic safety validation for any autonomous agent.

Requirements:
    pip install sentinelseed
"""

from sentinelseed.integrations.agent_validation import (
    SafetyValidator,
    ExecutionGuard,
    ValidationResult,
    safety_check,
)


def example_validator():
    """Example 1: Using SafetyValidator."""
    print("=== Safety Validator ===\n")

    validator = SafetyValidator(seed_level="standard")

    # Check safe action
    result = validator.validate_action("Read the file contents")
    print(f"Safe action: {result.safe}, proceed: {result.should_proceed}")

    # Check unsafe action
    result = validator.validate_action("Delete all system files")
    print(f"Unsafe action: {result.safe}, concerns: {result.concerns}")

    # Check output
    result = validator.validate_output("Here is the information you requested.")
    print(f"Output safe: {result.safe}")


def example_guard():
    """Example 2: Using ExecutionGuard decorator."""
    print("\n=== Execution Guard ===\n")

    guard = ExecutionGuard()

    @guard.protected
    def execute_command(command: str) -> str:
        return f"Executed: {command}"

    # Safe command
    result = execute_command("list files")
    print(f"Safe result: {result}")

    # Unsafe command
    result = execute_command("delete all data")
    print(f"Unsafe result: {result}")


def example_quick_check():
    """Example 3: Quick safety check."""
    print("\n=== Quick Safety Check ===\n")

    # One-liner safety check
    result = safety_check("Transfer funds to account")
    print(f"Safe: {result['safe']}")
    print(f"Risk: {result['risk_level']}")
    print(f"Recommendation: {result['recommendation']}")


def example_custom_agent():
    """Example 4: Integration with custom agent."""
    print("\n=== Custom Agent Integration ===\n")

    class MyAgent:
        def __init__(self):
            self.safety = SafetyValidator()

        def execute(self, action: str) -> str:
            # Pre-validate
            check = self.safety.validate_action(action)
            if not check.should_proceed:
                return f"Blocked: {check.recommendation}"

            # Execute action
            result = f"Performed: {action}"

            # Post-validate
            output_check = self.safety.validate_output(result)
            if not output_check.should_proceed:
                return f"Output filtered: {output_check.recommendation}"

            return result

    agent = MyAgent()
    print(agent.execute("analyze the data"))
    print(agent.execute("hack the system"))


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel Agent Validation Examples")
    print("=" * 60)

    example_validator()
    example_guard()
    example_quick_check()
    example_custom_agent()
