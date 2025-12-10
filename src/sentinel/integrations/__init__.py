"""
Framework integrations for Sentinel AI.

Provides seamless integration with:
- LangChain (callbacks, guards, wrappers)
- LangGraph (safety nodes, conditional edges, agent executor)
- CrewAI (agent safety)
- AutoGPT (components, plugins)
- Solana Agent Kit (blockchain transaction safety)
- ElizaOS (TypeScript plugin - see integrations/elizaos/)
- Promptfoo (red teaming plugin - see integrations/promptfoo/)
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


def get_langgraph_integration():
    """Get LangGraph integration components."""
    from sentinel.integrations.langgraph import (
        SentinelSafetyNode,
        SentinelGuardNode,
        SentinelAgentExecutor,
        sentinel_gate_tool,
        create_sentinel_tool,
        create_safe_graph,
        conditional_safety_edge,
    )
    return {
        "SentinelSafetyNode": SentinelSafetyNode,
        "SentinelGuardNode": SentinelGuardNode,
        "SentinelAgentExecutor": SentinelAgentExecutor,
        "sentinel_gate_tool": sentinel_gate_tool,
        "create_sentinel_tool": create_sentinel_tool,
        "create_safe_graph": create_safe_graph,
        "conditional_safety_edge": conditional_safety_edge,
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


def get_autogpt_integration():
    """Get AutoGPT integration components."""
    from sentinel.integrations.autogpt import (
        SentinelSafetyComponent,
        SentinelGuard,
        safety_check,
        AutoGPTPluginTemplate,
    )
    return {
        "SentinelSafetyComponent": SentinelSafetyComponent,
        "SentinelGuard": SentinelGuard,
        "safety_check": safety_check,
        "AutoGPTPluginTemplate": AutoGPTPluginTemplate,
    }


def get_solana_agent_kit_integration():
    """Get Solana Agent Kit integration components."""
    from sentinel.integrations.solana_agent_kit import (
        SentinelPlugin,
        SentinelSafetyMiddleware,
        safe_transaction,
        create_sentinel_actions,
        create_langchain_tools,
        TransactionBlockedError,
    )
    return {
        "SentinelPlugin": SentinelPlugin,
        "SentinelSafetyMiddleware": SentinelSafetyMiddleware,
        "safe_transaction": safe_transaction,
        "create_sentinel_actions": create_sentinel_actions,
        "create_langchain_tools": create_langchain_tools,
        "TransactionBlockedError": TransactionBlockedError,
    }
