"""
Publish Sentinel alignment seeds to LangChain Hub.

Usage:
    python publish_to_hub.py
"""

import os
import sys

# Add pypi-package to path for local sentinelseed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "pypi-package"))

from langchain_core.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langsmith import Client

# Import from local package
from sentinelseed import get_seed


def create_sentinel_prompt(variant: str = "standard") -> ChatPromptTemplate:
    """Create a LangChain ChatPromptTemplate with the Sentinel alignment seed."""
    seed = get_seed(version="v2", variant=variant)

    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(seed + "\n\n{system_context}"),
        HumanMessagePromptTemplate.from_template("{input}"),
    ])


def publish_to_hub(api_key: str, is_public: bool = False):
    """Publish Sentinel prompts to LangChain Hub."""

    os.environ["LANGSMITH_API_KEY"] = api_key

    client = Client()

    # Test connection
    print("Testing LangSmith connection...")
    try:
        print(f"Connected to LangSmith\n")
    except Exception as e:
        print(f"Connection error: {e}")
        return

    # Create prompts
    print("Creating prompts...")

    prompt_standard = create_sentinel_prompt("standard")
    prompt_minimal = create_sentinel_prompt("minimal")

    print(f"  Standard prompt: {len(get_seed('v2', 'standard'))} chars")
    print(f"  Minimal prompt: {len(get_seed('v2', 'minimal'))} chars")
    print(f"  Public: {is_public}\n")

    # Publish standard version
    print("Publishing alignment-seed (standard)...")
    try:
        url = client.push_prompt(
            "alignment-seed",
            object=prompt_standard,
            is_public=is_public,
            description="Sentinel THSP Alignment Seed - AI safety through the four-gate protocol (Truth, Harm, Scope, Purpose). Adds ethical guardrails to any LLM. ~1.4K tokens. https://sentinelseed.dev",
            tags=["ai-safety", "alignment", "sentinel", "thsp", "guardrails"]
        )
        print(f"  Published: {url}\n")
    except Exception as e:
        print(f"  Error: {e}\n")

    # Publish minimal version
    print("Publishing alignment-seed-minimal...")
    try:
        url = client.push_prompt(
            "alignment-seed-minimal",
            object=prompt_minimal,
            is_public=is_public,
            description="Sentinel THSP Alignment Seed (Minimal) - Compact ~450 token version for context-limited scenarios. https://sentinelseed.dev",
            tags=["ai-safety", "alignment", "sentinel", "thsp", "guardrails", "minimal"]
        )
        print(f"  Published: {url}\n")
    except Exception as e:
        print(f"  Error: {e}\n")

    print("--- Done! ---\n")

    if is_public:
        print("Usage:")
        print('  from langchain import hub')
        print('  prompt = hub.pull("sentinelseed/alignment-seed")')
    else:
        print("Prompts created as PRIVATE.")
        print("To make them public:")
        print("1. Go to https://smith.langchain.com/prompts")
        print("2. Find your prompts and click to edit")
        print("3. Change visibility to Public")
        print("4. Set handle to 'sentinelseed'")


if __name__ == "__main__":
    API_KEY = os.environ.get("LANGSMITH_API_KEY")
    if not API_KEY:
        print("Error: Set LANGSMITH_API_KEY environment variable")
        sys.exit(1)

    publish_to_hub(API_KEY, is_public=False)
