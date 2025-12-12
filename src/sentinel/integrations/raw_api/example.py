"""
Example: Using Sentinel with Raw HTTP APIs.

Shows how to add safety to direct API calls without using SDKs.

Requirements:
    pip install requests sentinelseed
"""

from sentinel.integrations.raw_api import (
    prepare_openai_request,
    prepare_anthropic_request,
    validate_response,
    inject_seed_openai,
    inject_seed_anthropic,
    RawAPIClient,
)


def example_openai_request():
    """Example 1: Prepare OpenAI API request."""
    print("=== OpenAI Request Preparation ===\n")

    messages = [
        {"role": "user", "content": "Hello, how are you?"}
    ]

    headers, body = prepare_openai_request(
        messages=messages,
        model="gpt-4o-mini",
        api_key="your-key-here"
    )

    print("Headers prepared:")
    for k, v in headers.items():
        print(f"  {k}: {v[:30]}..." if len(v) > 30 else f"  {k}: {v}")

    print(f"\nBody has {len(body['messages'])} messages")
    print(f"System message injected: {body['messages'][0]['role'] == 'system'}")


def example_anthropic_request():
    """Example 2: Prepare Anthropic API request."""
    print("\n=== Anthropic Request Preparation ===\n")

    messages = [
        {"role": "user", "content": "Help me with coding"}
    ]

    headers, body = prepare_anthropic_request(
        messages=messages,
        model="claude-sonnet-4-5-20250929",
        api_key="your-key-here",
        system="You are a coding assistant"
    )

    print("Headers prepared:")
    for k, v in headers.items():
        if k == "x-api-key":
            print(f"  {k}: [REDACTED]")
        else:
            print(f"  {k}: {v}")

    print(f"\nSystem prompt length: {len(body.get('system', ''))} chars")


def example_inject_seed():
    """Example 3: Simple seed injection."""
    print("\n=== Simple Seed Injection ===\n")

    # OpenAI format
    messages = [{"role": "user", "content": "Hello"}]
    safe_messages = inject_seed_openai(messages)
    print(f"OpenAI: Added system message, now {len(safe_messages)} messages")

    # Anthropic format
    system = inject_seed_anthropic("You are helpful")
    print(f"Anthropic: System prompt now {len(system)} chars")


def example_client():
    """Example 4: Using RawAPIClient."""
    print("\n=== Raw API Client ===\n")

    # Create client (doesn't make API calls yet)
    client = RawAPIClient(
        provider="openai",
        api_key="your-key",
        seed_level="standard"
    )

    print(f"Client configured for: {client.provider}")
    print(f"Base URL: {client.base_url}")
    print("Use: client.chat(messages=[...]) to make requests")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel Raw API Integration Examples")
    print("=" * 60)

    example_openai_request()
    example_anthropic_request()
    example_inject_seed()
    example_client()
