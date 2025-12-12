"""
Sentinel Integrations

Framework integrations for Sentinel AI safety validation.

Each integration is a subpackage with:
- __init__.py: The integration module
- example.py: Usage examples

Available integrations:
    from sentinel.integrations.langchain import SentinelCallback
    from sentinel.integrations.langgraph import SentinelSafetyNode
    from sentinel.integrations.crewai import safe_agent, SentinelCrew
    from sentinel.integrations.anthropic_sdk import SentinelAnthropic
    from sentinel.integrations.llamaindex import SentinelCallbackHandler
    from sentinel.integrations.mcp_server import create_sentinel_mcp_server
    from sentinel.integrations.openai_assistant import SentinelAssistant
    from sentinel.integrations.raw_api import prepare_openai_request
    from sentinel.integrations.agent_validation import SafetyValidator
    from sentinel.integrations.solana_agent_kit import SentinelPlugin

External packages (npm/PyPI):
    See packages/ directory for:
    - elizaos: npm install @sentinelseed/elizaos-plugin
    - promptfoo: pip install sentinelseed-promptfoo
    - solana-agent-kit: npm install @sentinelseed/solana-agent-kit
"""

__all__ = [
    'agent_validation',
    'anthropic_sdk',
    'autogpt',
    'crewai',
    'langchain',
    'langgraph',
    'llamaindex',
    'mcp_server',
    'openai_assistant',
    'raw_api',
    'solana_agent_kit',
]
