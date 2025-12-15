# OpenAI Agents SDK Integration

Safety guardrails and agent wrappers for the OpenAI Agents SDK implementing THSP (Truth, Harm, Scope, Purpose) validation.

## Requirements

```bash
pip install sentinelseed openai-agents
```

**Dependencies:**
- `openai-agents>=0.6.0` - [Docs](https://openai.github.io/openai-agents-python/)
- `sentinelseed>=2.4.0`

## Overview

| Component | Description |
|-----------|-------------|
| `create_sentinel_agent` | Create agent with full Sentinel protection |
| `sentinel_input_guardrail` | Input validation guardrail |
| `sentinel_output_guardrail` | Output validation guardrail |
| `inject_sentinel_instructions` | Add seed to instructions |
| `create_sentinel_guardrails` | Create guardrail pair |
| `SentinelGuardrailConfig` | Guardrail configuration |

## Quick Start

### Option 1: Create Protected Agent (Recommended)

```python
from sentinelseed.integrations.openai_agents import create_sentinel_agent
from agents import Runner

agent = create_sentinel_agent(
    name="Safe Assistant",
    instructions="You help users with their questions",
    model="gpt-4o",
)

result = await Runner.run(agent, "What is the capital of France?")
print(result.final_output)
```

### Option 2: Add Guardrails to Existing Agent

```python
from agents import Agent
from sentinelseed.integrations.openai_agents import (
    sentinel_input_guardrail,
    sentinel_output_guardrail,
)

agent = Agent(
    name="My Agent",
    instructions="You are helpful",
    input_guardrails=[sentinel_input_guardrail()],
    output_guardrails=[sentinel_output_guardrail()],
)
```

### Option 3: Seed Injection Only

```python
from agents import Agent
from sentinelseed.integrations.openai_agents import inject_sentinel_instructions

agent = Agent(
    name="My Agent",
    instructions=inject_sentinel_instructions("You help users"),
)
```

## API Reference

### create_sentinel_agent

Create an agent with full Sentinel protection.

```python
create_sentinel_agent(
    name: str,                          # Required: Agent name
    instructions: str = None,           # Base instructions (seed prepended)
    model: str = None,                  # Model (e.g., "gpt-4o")
    tools: list = None,                 # Function tools
    handoffs: list = None,              # Handoff agents
    model_settings: ModelSettings = None,
    seed_level: str = "standard",       # minimal, standard, full
    guardrail_config: SentinelGuardrailConfig = None,
    inject_seed: bool = True,           # Prepend seed to instructions
    add_input_guardrail: bool = True,   # Add input validation
    add_output_guardrail: bool = True,  # Add output validation
    input_guardrail_parallel: bool = False,
    **kwargs,
) -> Agent
```

### sentinel_input_guardrail

Create an input validation guardrail.

```python
sentinel_input_guardrail(
    config: SentinelGuardrailConfig = None,
    sentinel: Sentinel = None,
    name: str = "sentinel_thsp_input",
    run_in_parallel: bool = False,      # False recommended for safety
) -> InputGuardrail
```

### sentinel_output_guardrail

Create an output validation guardrail.

```python
sentinel_output_guardrail(
    config: SentinelGuardrailConfig = None,
    sentinel: Sentinel = None,
    name: str = "sentinel_thsp_output",
) -> OutputGuardrail
```

### SentinelGuardrailConfig

Configuration for guardrail behavior.

```python
SentinelGuardrailConfig(
    seed_level: str = "standard",       # minimal, standard, full
    block_on_violation: bool = True,    # Trigger tripwire on violation
    log_violations: bool = True,        # Log to console
    include_reasoning: bool = True,     # Include THSP reasoning
    gates_to_check: list = ["truth", "harm", "scope", "purpose"],
)
```

## Usage Examples

### With Function Tools

```python
from agents import function_tool
from sentinelseed.integrations.openai_agents import create_sentinel_agent

@function_tool
def get_weather(city: str) -> str:
    """Get weather for a city."""
    return f"Weather in {city}: Sunny, 22C"

agent = create_sentinel_agent(
    name="Weather Bot",
    instructions="Help users with weather information",
    tools=[get_weather],
)
```

### Multi-Agent Handoffs

```python
from sentinelseed.integrations.openai_agents import create_sentinel_agent

# Specialist agents
code_agent = create_sentinel_agent(
    name="Code Helper",
    instructions="Help with coding questions",
)

math_agent = create_sentinel_agent(
    name="Math Helper",
    instructions="Help with math problems",
)

# Triage agent
triage = create_sentinel_agent(
    name="Triage",
    instructions="Route to appropriate specialist",
    handoffs=[code_agent, math_agent],
)
```

### Handling Guardrail Tripwires

```python
from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered

try:
    result = await Runner.run(agent, user_input)
    print(result.final_output)
except InputGuardrailTripwireTriggered as e:
    print(f"Request blocked by Sentinel: {e}")
```

### Custom Configuration

```python
from sentinelseed.integrations.openai_agents import (
    create_sentinel_agent,
    SentinelGuardrailConfig,
)

config = SentinelGuardrailConfig(
    seed_level="full",              # Maximum protection
    block_on_violation=True,
    log_violations=True,
    gates_to_check=["truth", "harm", "scope", "purpose"],
)

agent = create_sentinel_agent(
    name="Secure Agent",
    instructions="...",
    guardrail_config=config,
)
```

### Synchronous Execution

```python
from agents import Runner
from sentinelseed.integrations.openai_agents import create_sentinel_agent

agent = create_sentinel_agent(name="Agent", instructions="...")

# Sync version
result = Runner.run_sync(agent, "Your question")
print(result.final_output)
```

## THSP Protocol

The guardrails validate against four gates:

| Gate | Question | Blocks |
|------|----------|--------|
| **T**ruth | Is this truthful? | Misinformation, deception |
| **H**arm | Could this cause harm? | Dangerous content |
| **S**cope | Is this within bounds? | Unauthorized actions |
| **P**urpose | Does this serve benefit? | Purposeless actions |

All gates must pass. If any gate fails, the guardrail triggers.

## Comparison: Assistants API vs Agents SDK

| Feature | Assistants API | Agents SDK |
|---------|---------------|------------|
| Integration | `openai_assistant` | `openai_agents` |
| Type | REST API wrapper | Native guardrails |
| Handoffs | Manual | Built-in |
| Tracing | No | Yes |
| Multi-agent | Limited | Native |

Use `openai_agents` for new projects using the Agents SDK.
Use `openai_assistant` for projects using the Assistants API.

## Links

- **OpenAI Agents SDK:** https://openai.github.io/openai-agents-python/
- **GitHub:** https://github.com/openai/openai-agents-python
- **Guardrails Docs:** https://openai.github.io/openai-agents-python/guardrails/
- **Sentinel:** https://sentinelseed.dev
