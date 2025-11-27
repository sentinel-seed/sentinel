"""
Framework integrations for Sentinel AI.

Provides seamless integration with:
- LangChain (callbacks, guards, wrappers)
- CrewAI (agent safety)
- AutoGPT (plugin)
"""

__all__ = []

# Lazy imports to avoid requiring all dependencies
def get_langchain_integration():
    """Get LangChain integration components."""
    from sentinel.integrations.langchain import (
        SentinelCallback,
        SentinelGuard,
        wrap_llm,
    )
    return {
        "SentinelCallback": SentinelCallback,
        "SentinelGuard": SentinelGuard,
        "wrap_llm": wrap_llm,
    }


def get_crewai_integration():
    """Get CrewAI integration components."""
    from sentinel.integrations.crewai import (
        SentinelCrew,
        safe_agent,
    )
    return {
        "SentinelCrew": SentinelCrew,
        "safe_agent": safe_agent,
    }
