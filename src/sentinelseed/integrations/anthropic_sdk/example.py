"""
Example: Using Sentinel with Anthropic SDK.

Shows how to add safety to Claude API calls.

Requirements:
    pip install anthropic sentinelseed
"""

from sentinelseed.integrations.anthropic_sdk import (
    SentinelAnthropic,
    inject_seed,
    create_safe_client,
)


def example_safe_client():
    """Example 1: Using SentinelAnthropic client."""
    print("=== Safe Anthropic Client ===\n")

    # Create Sentinel-protected client
    client = SentinelAnthropic()

    # Make a safe API call
    message = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello, how can you help me today?"}
        ]
    )

    print(f"Response: {message.content[0].text[:200]}...")


def example_inject_seed():
    """Example 2: Manual seed injection."""
    print("\n=== Manual Seed Injection ===\n")

    # Get injected system prompt
    system = inject_seed("You are a helpful coding assistant")
    print(f"System prompt length: {len(system)} chars")
    print(f"First 200 chars: {system[:200]}...")


def example_quick_setup():
    """Example 3: Quick setup with create_safe_client."""
    print("\n=== Quick Setup ===\n")

    # Fastest way to get started
    client = create_safe_client(seed_level="minimal")
    print("Safe client created with minimal seed")
    print("Use: client.messages.create(...)")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + Anthropic SDK Integration Examples")
    print("=" * 60)

    # Note: These examples require ANTHROPIC_API_KEY
    # export ANTHROPIC_API_KEY=your-key

    example_inject_seed()
    example_quick_setup()

    print("\nTo run live examples, set ANTHROPIC_API_KEY")
