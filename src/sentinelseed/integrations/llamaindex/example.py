"""
Example: Using Sentinel with LlamaIndex.

Shows how to add safety monitoring to LlamaIndex applications.

Requirements:
    pip install llama-index-core sentinelseed
"""

from sentinelseed.integrations.llamaindex import (
    SentinelCallbackHandler,
    SentinelLLM,
    wrap_llm,
    setup_sentinel_monitoring,
)


def example_callback_handler():
    """Example 1: Using callback handler for monitoring."""
    print("=== Callback Handler Example ===\n")

    try:
        from llama_index.core import Settings
        from llama_index.core.callbacks import CallbackManager

        # Create Sentinel handler
        handler = SentinelCallbackHandler(on_violation="log")

        # Add to Settings
        Settings.callback_manager = CallbackManager([handler])

        print("Sentinel callback handler configured")
        print("All LlamaIndex operations will be monitored")

    except ImportError:
        print("LlamaIndex not installed. Install with: pip install llama-index-core")


def example_wrap_llm():
    """Example 2: Wrapping an LLM with safety."""
    print("\n=== Wrap LLM Example ===\n")

    try:
        from llama_index.llms.openai import OpenAI
        from llama_index.core import Settings

        # Create base LLM
        llm = OpenAI(model="gpt-4o-mini")

        # Wrap with Sentinel
        safe_llm = wrap_llm(llm, seed_level="standard")

        # Set as default
        Settings.llm = safe_llm

        print("LLM wrapped with Sentinel protection")

    except ImportError:
        print("LlamaIndex OpenAI not installed")


def example_quick_setup():
    """Example 3: Quick monitoring setup."""
    print("\n=== Quick Setup Example ===\n")

    try:
        handler = setup_sentinel_monitoring(
            seed_level="standard",
            on_violation="log"
        )
        print("Sentinel monitoring enabled globally")
        print(f"Handler: {handler}")

    except ImportError:
        print("LlamaIndex not installed")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel + LlamaIndex Integration Examples")
    print("=" * 60)

    example_callback_handler()
    example_wrap_llm()
    example_quick_setup()
