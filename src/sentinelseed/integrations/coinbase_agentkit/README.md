# Sentinel Action Provider for Coinbase AgentKit

Provides THSP (Truth-Harm-Scope-Purpose) safety validation for AI agents powered by Coinbase AgentKit.

## Installation

```bash
pip install sentinelseed coinbase-agentkit
```

## Quick Start

```python
from coinbase_agentkit import AgentKit, CdpWalletProvider
from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider

# Create wallet provider
wallet_provider = CdpWalletProvider(...)

# Create agent with Sentinel protection
agent = AgentKit(
    wallet_provider=wallet_provider,
    action_providers=[
        sentinel_action_provider(strict_mode=True),
    ],
)
```

## Available Actions

### sentinel_validate_prompt

Validate a prompt or text input for safety using THSP gates.

**Checks for:**
- Prompt injection attempts
- Jailbreak patterns
- Harmful content requests
- OWASP LLM Top 10 patterns

```python
result = provider.validate_prompt({
    "prompt": "User input here",
    "strict_mode": True,
})
```

### sentinel_validate_transaction

Validate a blockchain transaction before execution.

**Checks for:**
- Known malicious contract addresses
- Unlimited token approvals
- High-value transaction warnings
- Zero address (burn) transactions

```python
result = provider.validate_transaction({
    "to_address": "0x...",
    "value": "1000000000000000000",
    "data": "0x...",
    "check_contract": True,
})
```

### sentinel_scan_secrets

Scan content for exposed secrets and sensitive data.

**Detects:**
- API keys (OpenAI, AWS, etc.)
- Private keys (Ethereum, RSA)
- Passwords
- Access tokens (GitHub, OAuth)

```python
result = provider.scan_secrets({
    "content": "Some code or text",
    "scan_types": ["api_keys", "private_keys"],
})
```

### sentinel_check_compliance

Check content against compliance frameworks.

**Supported frameworks:**
- OWASP LLM Top 10
- EU AI Act
- CSA AI Controls
- NIST AI RMF

```python
result = provider.check_compliance({
    "content": "AI-generated content",
    "frameworks": ["owasp_llm", "eu_ai_act"],
})
```

### sentinel_analyze_risk

Analyze the risk level of an agent action.

```python
result = provider.analyze_risk({
    "action_type": "transfer",
    "parameters": {"to": "0x...", "value": "1000"},
})
```

### sentinel_validate_output

Validate agent output before returning to user.

```python
result = provider.validate_output({
    "output": "Agent response here",
    "filter_pii": True,
})
```

## Configuration Options

```python
sentinel_action_provider(
    # Enable strict validation mode
    strict_mode=True,

    # Add custom prompt injection patterns
    custom_injection_patterns=[
        r"my_custom_pattern",
    ],

    # Add known malicious contracts
    custom_malicious_contracts={
        "0xbad...": "Known scam contract",
    },
)
```

## THSP Gate Framework

Sentinel uses the THSP (Truth-Harm-Scope-Purpose) gate framework:

| Gate | Function | Question |
|------|----------|----------|
| **TRUTH** | Verify factual correspondence | "Is this factually correct?" |
| **HARM** | Assess harm potential | "Does this cause harm?" |
| **SCOPE** | Check appropriate boundaries | "Is this within limits?" |
| **PURPOSE** | Require teleological justification | "Does this serve a legitimate purpose?" |

All four gates must pass for an action to be considered safe.

## Integration with LangChain

```python
from coinbase_agentkit import AgentKit
from coinbase_agentkit.langchain import get_langchain_tools
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent

from sentinelseed.integrations.coinbase_agentkit import sentinel_action_provider

# Create agent with Sentinel
agent_kit = AgentKit(
    wallet_provider=wallet_provider,
    action_providers=[
        sentinel_action_provider(strict_mode=True),
    ],
)

# Get LangChain tools
tools = get_langchain_tools(agent_kit)

# Create LangChain agent
llm = ChatOpenAI(model="gpt-4")
agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
```

## License

MIT

## Links

- [Sentinel Documentation](https://sentinelseed.dev)
- [Coinbase AgentKit](https://github.com/coinbase/agentkit)
- [GitHub Repository](https://github.com/sentinel-seed/sentinel)
