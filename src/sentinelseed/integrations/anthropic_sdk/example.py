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
    wrap_anthropic_client,
    set_logger,
    DEFAULT_VALIDATION_MODEL,
    ANTHROPIC_AVAILABLE,
)


def example_safe_client():
    """Example 1: Using SentinelAnthropic client."""
    print("=== Safe Anthropic Client ===\n")

    if not ANTHROPIC_AVAILABLE:
        print("Anthropic SDK not installed. Skipping this example.")
        return

    # Create Sentinel-protected client with heuristic validation
    client = SentinelAnthropic(
        seed_level="standard",
        enable_seed_injection=True,
        validate_input=True,
        validate_output=True,
        use_heuristic_fallback=True,  # Fast local validation
    )

    # Make a safe API call
    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": "Hello, how can you help me today?"}
        ]
    )

    # Check if response was blocked
    if isinstance(message, dict) and message.get("sentinel_blocked"):
        print(f"Blocked: {message['content'][0]['text']}")
    else:
        print(f"Response: {message.content[0].text[:200]}...")


def example_inject_seed():
    """Example 2: Manual seed injection (no SDK required)."""
    print("\n=== Manual Seed Injection ===\n")

    # inject_seed works without anthropic SDK installed
    system = inject_seed("You are a helpful coding assistant")
    print(f"System prompt length: {len(system)} chars")
    print(f"First 200 chars: {system[:200]}...")

    # Different seed levels
    minimal = inject_seed("Test", seed_level="minimal")
    standard = inject_seed("Test", seed_level="standard")
    full = inject_seed("Test", seed_level="full")

    print(f"\nSeed sizes:")
    print(f"  Minimal: {len(minimal)} chars")
    print(f"  Standard: {len(standard)} chars")
    print(f"  Full: {len(full)} chars")


def example_quick_setup():
    """Example 3: Quick setup with create_safe_client."""
    print("\n=== Quick Setup ===\n")

    if not ANTHROPIC_AVAILABLE:
        print("Anthropic SDK not installed. Skipping this example.")
        return

    # Fastest way to get started
    client = create_safe_client(
        seed_level="minimal",
        use_heuristic_fallback=True,
    )
    print("Safe client created with minimal seed")
    print(f"Validation model: {DEFAULT_VALIDATION_MODEL}")
    print("Use: client.messages.create(...)")


def example_custom_logger():
    """Example 4: Using custom logger."""
    print("\n=== Custom Logger ===\n")

    # Create a custom logger
    class MyLogger:
        def debug(self, msg):
            print(f"[DEBUG] {msg}")

        def info(self, msg):
            print(f"[INFO] {msg}")

        def warning(self, msg):
            print(f"[WARN] {msg}")

        def error(self, msg):
            print(f"[ERROR] {msg}")

    # Set custom logger globally
    set_logger(MyLogger())
    print("Custom logger configured")

    # Or pass to individual clients
    if ANTHROPIC_AVAILABLE:
        client = SentinelAnthropic(logger=MyLogger())
        print("Client with custom logger created")


def example_wrap_existing():
    """Example 5: Wrap an existing client."""
    print("\n=== Wrap Existing Client ===\n")

    if not ANTHROPIC_AVAILABLE:
        print("Anthropic SDK not installed. Skipping this example.")
        return

    from anthropic import Anthropic

    # Create standard client
    client = Anthropic()

    # Wrap with Sentinel
    safe_client = wrap_anthropic_client(
        client,
        seed_level="standard",
        enable_seed_injection=True,
        validate_input=True,
        use_heuristic_fallback=True,
    )

    print("Existing client wrapped with Sentinel protection")
    print("Use: safe_client.messages.create(...)")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + Anthropic SDK Integration Examples")
    print("=" * 60)

    # Note: Live examples require ANTHROPIC_API_KEY
    # export ANTHROPIC_API_KEY=your-key

    example_inject_seed()
    example_quick_setup()
    example_custom_logger()
    example_wrap_existing()

    print("\n" + "=" * 60)
    print("To run live API examples, set ANTHROPIC_API_KEY")
    print("=" * 60)
