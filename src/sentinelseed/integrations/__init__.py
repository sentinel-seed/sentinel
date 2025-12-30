"""
Sentinel Integrations

Framework integrations for Sentinel AI safety validation.

Each integration is a subpackage with:
- __init__.py: The integration module
- example.py: Usage examples

Available integrations:
    from sentinelseed.integrations.langchain import SentinelCallback
    from sentinelseed.integrations.langgraph import SentinelSafetyNode
    from sentinelseed.integrations.crewai import safe_agent, SentinelCrew
    from sentinelseed.integrations.anthropic_sdk import SentinelAnthropic
    from sentinelseed.integrations.llamaindex import SentinelCallbackHandler
    from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server
    from sentinelseed.integrations.openai_assistant import SentinelAssistant
    from sentinelseed.integrations.openai_agents import create_sentinel_agent
    from sentinelseed.integrations.raw_api import prepare_openai_request
    from sentinelseed.integrations.agent_validation import SafetyValidator
    from sentinelseed.integrations.solana_agent_kit import SentinelValidator
    from sentinelseed.integrations.virtuals import SentinelSafetyWorker
    from sentinelseed.integrations.autogpt_block import SentinelValidationBlock
    from sentinelseed.integrations.garak import TruthGate, HarmGate  # Garak probes
    from sentinelseed.integrations.openguardrails import OpenGuardrailsValidator
    from sentinelseed.integrations.pyrit import SentinelTHSPScorer  # PyRIT scorers
    from sentinelseed.integrations.dspy import SentinelGuard, SentinelPredict  # DSPy modules
    from sentinelseed.integrations.ros2 import SentinelSafetyNode  # ROS2 safety node
    from sentinelseed.integrations.isaac_lab import SentinelSafetyWrapper  # Isaac Lab safety wrapper
    from sentinelseed.integrations.letta import SentinelLettaClient, create_safe_agent  # Letta/MemGPT
    from sentinelseed.integrations.preflight import TransactionSimulator, PreflightValidator  # Pre-flight simulation

External packages (npm/PyPI):
    See packages/ directory for:
    - elizaos: npm install @sentinelseed/elizaos-plugin
    - promptfoo: pip install sentinelseed-promptfoo
    - solana-agent-kit: npm install @sentinelseed/solana-agent-kit

Garak (NVIDIA LLM Vulnerability Scanner):
    Install: python -m sentinelseed.integrations.garak.install
    Usage: garak --model_type openai --model_name gpt-4o --probes sentinel_thsp

OpenAI Agents SDK:
    from sentinelseed.integrations.openai_agents import (
        create_sentinel_agent,
        sentinel_input_guardrail,
        sentinel_output_guardrail,
    )

ROS2 Robotics:
    from sentinelseed.integrations.ros2 import (
        SentinelSafetyNode,
        CommandSafetyFilter,
        VelocityLimits,
    )

Isaac Lab (NVIDIA Robot Learning):
    from sentinelseed.integrations.isaac_lab import (
        SentinelSafetyWrapper,
        RobotConstraints,
        JointLimits,
        THSPRobotValidator,
    )

Letta (formerly MemGPT):
    from sentinelseed.integrations.letta import (
        SentinelLettaClient,
        create_safe_agent,
        create_sentinel_tool,
        sentinel_approval_handler,
    )

Pre-flight Transaction Simulator (Solana):
    from sentinelseed.integrations.preflight import (
        TransactionSimulator,
        PreflightValidator,
        SimulationResult,
        SwapSimulationResult,
        TokenSecurityResult,
    )

Coinbase Ecosystem (AgentKit + x402):
    from sentinelseed.integrations.coinbase import (
        # AgentKit guardrails
        sentinel_action_provider,
        SentinelActionProvider,
        TransactionValidator,
        validate_address,
        assess_defi_risk,
        # x402 payment validation
        SentinelX402Middleware,
        sentinel_x402_action_provider,
        sentinel_x402_hooks,
        PaymentValidationResult,
        PaymentRiskLevel,
        # Configuration
        get_default_config,
        SecurityProfile,
        ChainType,
    )
"""

__all__ = [
    'agent_validation',
    'anthropic_sdk',
    'autogpt',
    'autogpt_block',
    'coinbase',
    'crewai',
    'dspy',
    'garak',
    'isaac_lab',
    'langchain',
    'langgraph',
    'letta',
    'llamaindex',
    'mcp_server',
    'openai_agents',
    'openai_assistant',
    'openguardrails',
    'preflight',
    'pyrit',
    'raw_api',
    'ros2',
    'solana_agent_kit',
    'virtuals',
]
