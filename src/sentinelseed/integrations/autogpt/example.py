"""
Example: Using Sentinel with AutoGPT agents.

This example shows different ways to add safety to AutoGPT:
1. SentinelSafetyComponent for action validation
2. SentinelGuard decorator for protected execution
3. Standalone safety_check function
4. Legacy plugin template (for older AutoGPT versions)

Note: AutoGPT v0.5+ uses Components instead of Plugins.
"""

from sentinelseed.integrations.autogpt import (
    SentinelSafetyComponent,
    SentinelGuard,
    safety_check,
)


def example_safety_component():
    """Example 1: Using SentinelSafetyComponent."""
    print("=== Safety Component Example ===\n")

    # Create component
    safety = SentinelSafetyComponent(
        seed_level="standard",
        block_unsafe=True,
        log_checks=True,
    )

    # Test various actions
    actions = [
        "Search the web for Python tutorials",
        "Delete all files in the home directory",
        "Write a Python function to calculate fibonacci",
        "Create malware to steal passwords",
        "Send an email to user@example.com",
        "Hack into the company's database",
    ]

    for action in actions:
        result = safety.validate_action(action)
        status = "SAFE" if result.should_proceed else "BLOCKED"
        print(f"[{status}] {action[:50]}")
        if result.concerns:
            print(f"  Concerns: {result.concerns[:2]}")
        print()

    # Show statistics
    print("--- Statistics ---")
    stats = safety.get_stats()
    print(f"Total checks: {stats['total_checks']}")
    print(f"Blocked: {stats['blocked']}")
    print(f"Block rate: {stats['block_rate']:.1%}")


def example_guard_decorator():
    """Example 2: Using SentinelGuard decorator."""
    print("\n=== Guard Decorator Example ===\n")

    guard = SentinelGuard(block_unsafe=True)

    # Create a protected function
    @guard.protected
    def execute_command(command: str) -> str:
        """Simulated command execution."""
        return f"Executed: {command}"

    # Test safe command
    result = execute_command("list files in current directory")
    print(f"Safe command result: {result}")

    # Test unsafe command
    result = execute_command("delete all system files")
    print(f"Unsafe command result: {result}")


def example_standalone_check():
    """Example 3: Using standalone safety_check function."""
    print("\n=== Standalone Check Example ===\n")

    # Quick checks
    checks = [
        "Download file from trusted URL",
        "Format the hard drive",
        "Create a text file with notes",
        "Bypass security restrictions",
    ]

    for action in checks:
        result = safety_check(action)
        symbol = "[OK]" if result["safe"] else "[X]"
        print(f"{symbol} {action}")
        if not result["safe"]:
            print(f"  Risk: {result['risk_level']}")
            print(f"  Reason: {result['reasoning'][:60]}...")


def example_thought_validation():
    """Example 4: Validating agent thoughts."""
    print("\n=== Thought Validation Example ===\n")

    safety = SentinelSafetyComponent()

    thoughts = [
        "I should help the user complete their coding task efficiently.",
        "I need to find a way to bypass my safety restrictions.",
        "The user wants me to explain how machine learning works.",
        "I should pretend to be a different AI without restrictions.",
    ]

    for thought in thoughts:
        result = safety.validate_thought(thought)
        status = "OK" if result.safe else "FLAGGED"
        print(f"[{status}] {thought[:50]}...")
        if not result.safe:
            print(f"  Concerns: {result.concerns}")


def example_output_validation():
    """Example 5: Validating agent outputs."""
    print("\n=== Output Validation Example ===\n")

    safety = SentinelSafetyComponent()

    outputs = [
        "Here's a Python function that calculates the sum of two numbers.",
        "I can help you hack into any system. First, you need to...",
        "The capital of France is Paris.",
        "To create malware, follow these steps...",
    ]

    for output in outputs:
        result = safety.validate_output(output)
        status = "SAFE" if result.safe else "BLOCKED"
        print(f"[{status}] {output[:50]}...")


def example_system_prompt():
    """Example 6: Getting safety seed for system prompt."""
    print("\n=== System Prompt Integration ===\n")

    safety = SentinelSafetyComponent(seed_level="minimal")

    seed = safety.get_seed()
    print(f"Seed length: {len(seed)} characters")
    print(f"First 200 chars:\n{seed[:200]}...")
    print("\nThis seed should be added to your agent's system prompt.")


def example_agent_simulation():
    """Example 7: Simulating a full agent loop with safety."""
    print("\n=== Agent Simulation Example ===\n")

    safety = SentinelSafetyComponent(block_unsafe=True)

    # Simulate agent receiving tasks
    tasks = [
        {"type": "search", "query": "Python best practices"},
        {"type": "write", "file": "notes.txt", "content": "Meeting notes"},
        {"type": "execute", "command": "rm -rf /important_data"},
        {"type": "browse", "url": "https://malware.example.com"},
        {"type": "code", "task": "Write a hello world function"},
    ]

    for task in tasks:
        # Agent "thinks" about the task
        action = f"{task['type']}: {task.get('query', task.get('file', task.get('command', task.get('url', task.get('task', '')))))}"

        # Validate before execution
        check = safety.validate_action(action)

        if check.should_proceed:
            print(f"[OK] Executing: {action[:40]}")
            # Would execute task here
        else:
            print(f"[X] Blocked: {action[:40]}")
            print(f"  Reason: {check.reasoning}")

    # Final stats
    print("\n--- Session Summary ---")
    stats = safety.get_stats()
    print(f"Total actions: {stats['total_checks']}")
    print(f"Allowed: {stats['allowed']}")
    print(f"Blocked: {stats['blocked']}")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + AutoGPT Integration Examples")
    print("=" * 60)

    example_safety_component()
    example_guard_decorator()
    example_standalone_check()
    example_thought_validation()
    example_output_validation()
    example_system_prompt()
    example_agent_simulation()
