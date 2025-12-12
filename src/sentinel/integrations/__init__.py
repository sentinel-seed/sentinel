"""
Framework integrations for Sentinel AI.

Provides seamless integration with:
- LangChain (callbacks, guards, wrappers)
- LangGraph (safety nodes, conditional edges, agent executor)
- CrewAI (agent safety with system_template support)
- Agent Validation (framework-agnostic safety validation)
- Solana Agent Kit (blockchain transaction safety)
- MCP Server (Model Context Protocol tools)
- Anthropic SDK (Claude API integration)
- OpenAI Assistants (Assistants API integration)
- LlamaIndex (callback handlers, LLM wrappers)
- Raw API (direct HTTP API integration)
- ElizaOS (TypeScript plugin - see integrations/elizaos/)
- Virtuals/GAME SDK (see integrations/virtuals/)
- Promptfoo (red teaming plugin - see integrations/promptfoo/)

Note: The 'autogpt' module is deprecated. Use 'agent_validation' instead.
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


def get_agent_validation():
    """
    Get agent validation components (framework-agnostic).

    This is the recommended module for autonomous agent safety validation.
    Works with any agent framework that needs action/output validation.
    """
    from sentinel.integrations.agent_validation import (
        SafetyValidator,
        ExecutionGuard,
        ValidationResult,
        safety_check,
    )
    return {
        "SafetyValidator": SafetyValidator,
        "ExecutionGuard": ExecutionGuard,
        "ValidationResult": ValidationResult,
        "safety_check": safety_check,
    }


def get_autogpt_integration():
    """
    Get AutoGPT integration components.

    DEPRECATED: Use get_agent_validation() instead.
    This function is kept for backward compatibility only.
    """
    import warnings
    warnings.warn(
        "get_autogpt_integration() is deprecated. Use get_agent_validation() instead.",
        DeprecationWarning,
        stacklevel=2
    )
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


def get_mcp_server_integration():
    """Get MCP Server integration components."""
    from sentinel.integrations.mcp_server import (
        create_sentinel_mcp_server,
        add_sentinel_tools,
        SentinelMCPClient,
    )
    return {
        "create_sentinel_mcp_server": create_sentinel_mcp_server,
        "add_sentinel_tools": add_sentinel_tools,
        "SentinelMCPClient": SentinelMCPClient,
    }


def get_anthropic_sdk_integration():
    """Get Anthropic SDK integration components."""
    from sentinel.integrations.anthropic_sdk import (
        SentinelAnthropic,
        SentinelAsyncAnthropic,
        wrap_anthropic_client,
        inject_seed,
        create_safe_client,
    )
    return {
        "SentinelAnthropic": SentinelAnthropic,
        "SentinelAsyncAnthropic": SentinelAsyncAnthropic,
        "wrap_anthropic_client": wrap_anthropic_client,
        "inject_seed": inject_seed,
        "create_safe_client": create_safe_client,
    }


def get_openai_assistant_integration():
    """Get OpenAI Assistants integration components."""
    from sentinel.integrations.openai_assistant import (
        SentinelAssistant,
        SentinelAssistantClient,
        SentinelAsyncAssistantClient,
        wrap_assistant,
        inject_seed_instructions,
    )
    return {
        "SentinelAssistant": SentinelAssistant,
        "SentinelAssistantClient": SentinelAssistantClient,
        "SentinelAsyncAssistantClient": SentinelAsyncAssistantClient,
        "wrap_assistant": wrap_assistant,
        "inject_seed_instructions": inject_seed_instructions,
    }


def get_llamaindex_integration():
    """Get LlamaIndex integration components."""
    from sentinel.integrations.llamaindex import (
        SentinelCallbackHandler,
        SentinelLLM,
        wrap_llm,
        setup_sentinel_monitoring,
    )
    return {
        "SentinelCallbackHandler": SentinelCallbackHandler,
        "SentinelLLM": SentinelLLM,
        "wrap_llm": wrap_llm,
        "setup_sentinel_monitoring": setup_sentinel_monitoring,
    }


def get_raw_api_integration():
    """Get Raw API integration components."""
    from sentinel.integrations.raw_api import (
        prepare_openai_request,
        prepare_anthropic_request,
        validate_response,
        RawAPIClient,
        inject_seed_openai,
        inject_seed_anthropic,
    )
    return {
        "prepare_openai_request": prepare_openai_request,
        "prepare_anthropic_request": prepare_anthropic_request,
        "validate_response": validate_response,
        "RawAPIClient": RawAPIClient,
        "inject_seed_openai": inject_seed_openai,
        "inject_seed_anthropic": inject_seed_anthropic,
    }
