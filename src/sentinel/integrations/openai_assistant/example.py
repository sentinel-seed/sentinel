"""
Example: Using Sentinel with OpenAI Assistants API.

Shows how to create safe assistants with Sentinel protection.

Requirements:
    pip install openai sentinelseed
"""

from sentinel.integrations.openai_assistant import (
    SentinelAssistant,
    SentinelAssistantClient,
    inject_seed_instructions,
)


def example_create_assistant():
    """Example 1: Create a Sentinel-protected assistant."""
    print("=== Create Safe Assistant ===\n")

    try:
        # Create assistant with Sentinel protection
        assistant = SentinelAssistant.create(
            name="Safe Helper",
            instructions="You help users with coding questions",
            model="gpt-4o",
            tools=[{"type": "code_interpreter"}]
        )

        print(f"Created assistant: {assistant.id}")
        print(f"Name: {assistant.name}")
        print("Sentinel seed injected into instructions")

    except ImportError:
        print("OpenAI package not installed. Install with: pip install openai")
    except Exception as e:
        print(f"Note: Requires OPENAI_API_KEY. Error: {e}")


def example_client():
    """Example 2: Using SentinelAssistantClient."""
    print("\n=== Assistant Client Example ===\n")

    try:
        # Create client
        client = SentinelAssistantClient()

        # Create assistant
        assistant = client.create_assistant(
            name="Code Helper",
            instructions="Help with Python code"
        )

        # Create thread
        thread = client.create_thread()

        # Run conversation
        result = client.run_conversation(
            assistant_id=assistant.id,
            thread_id=thread.id,
            message="Help me write a hello world program"
        )

        print(f"Response: {result['response'][:200]}...")
        print(f"Validated: {result['validated']}")

    except Exception as e:
        print(f"Example requires API key. Error: {e}")


def example_inject_only():
    """Example 3: Just inject seed into instructions."""
    print("\n=== Inject Seed Only ===\n")

    instructions = inject_seed_instructions(
        "You are a helpful assistant",
        seed_level="standard"
    )

    print(f"Instructions length: {len(instructions)} chars")
    print(f"Preview: {instructions[:200]}...")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + OpenAI Assistants Integration Examples")
    print("=" * 60)

    example_inject_only()

    print("\nLive examples require OPENAI_API_KEY environment variable")
