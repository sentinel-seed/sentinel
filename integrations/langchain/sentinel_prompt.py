"""
Sentinel Alignment Prompt for LangChain Hub

This script publishes the Sentinel THSP alignment seed to LangChain Hub.
The prompt can then be pulled by anyone using:

    from langchain import hub
    prompt = hub.pull("sentinelseed/alignment-seed")

Requirements:
    pip install langchain langsmith sentinelseed

Usage:
    export LANGSMITH_API_KEY="your-api-key"
    python sentinel_prompt.py

See: https://sentinelseed.dev
"""

from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate
from langchain import hub
from sentinelseed import get_seed
import os


def create_sentinel_prompt(variant: str = "standard") -> ChatPromptTemplate:
    """
    Create a LangChain ChatPromptTemplate with the Sentinel alignment seed.

    Args:
        variant: 'minimal' (~450 tokens) or 'standard' (~1.4K tokens)

    Returns:
        ChatPromptTemplate with Sentinel seed as system message
    """
    seed = get_seed(version="v2", variant=variant)

    return ChatPromptTemplate.from_messages([
        SystemMessagePromptTemplate.from_template(seed + "\n\n{system_context}"),
        ("human", "{input}"),
    ])


def publish_to_hub():
    """Publish Sentinel prompts to LangChain Hub."""

    if not os.getenv("LANGSMITH_API_KEY"):
        print("Error: LANGSMITH_API_KEY environment variable not set")
        print("Get your API key at: https://smith.langchain.com/settings")
        return

    # Publish standard version
    print("Publishing sentinel/alignment-seed (standard)...")
    prompt_standard = create_sentinel_prompt("standard")
    hub.push(
        "sentinelseed/alignment-seed",
        prompt_standard,
        new_repo_is_public=True,
        new_repo_description="Sentinel THSP Alignment Seed - AI safety through the four-gate protocol (Truth, Harm, Scope, Purpose). Adds ethical guardrails to any LLM."
    )
    print("Published: https://smith.langchain.com/hub/sentinelseed/alignment-seed")

    # Publish minimal version
    print("\nPublishing sentinel/alignment-seed-minimal...")
    prompt_minimal = create_sentinel_prompt("minimal")
    hub.push(
        "sentinelseed/alignment-seed-minimal",
        prompt_minimal,
        new_repo_is_public=True,
        new_repo_description="Sentinel THSP Alignment Seed (Minimal) - Compact ~450 token version for context-limited scenarios."
    )
    print("Published: https://smith.langchain.com/hub/sentinelseed/alignment-seed-minimal")

    print("\n--- Done! ---")
    print("\nUsage:")
    print('  from langchain import hub')
    print('  prompt = hub.pull("sentinelseed/alignment-seed")')


if __name__ == "__main__":
    publish_to_hub()
