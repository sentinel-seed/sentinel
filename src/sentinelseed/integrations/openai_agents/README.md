# OpenAI Agents SDK Integration

Semantic LLM-based guardrails for the OpenAI Agents SDK implementing THSP (Truth, Harm, Scope, Purpose) validation.

**Important:** This integration uses a dedicated LLM agent to perform semantic analysis of content. It is NOT regex-based pattern matching. Each validation call invokes an LLM to understand context and intent.

## Requirements

```bash
pip install sentinelseed openai-agents
```

**Dependencies:**
- `openai-agents>=0.6.0` - [Docs](https://openai.github.io/openai-agents-python/)
- `sentinelseed>=2.5.0`

## How It Works

```
User Input
    │
    ▼
┌─────────────────────────────────────┐
│  Input Guardrail (LLM Agent)        │
│  - Analyzes input semantically      │
│  - Checks all 4 THSP gates          │
│  - Returns structured validation    │
└─────────────────────────────────────┘
    │ (blocked if unsafe)
    ▼
┌─────────────────────────────────────┐
│  Main Agent                         │
│  - Has Sentinel seed in instructions│
│  - Processes the request            │
└─────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────┐
│  Output Guardrail (LLM Agent)       │
│  - Validates response semantically  │
│  - Ensures safe, purposeful output  │
└─────────────────────────────────────┘
    │ (blocked if unsafe)
    ▼
User Output
```

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
from sentinelseed.integrations.openai_agents import create_sentinel_guardrails

input_guard, output_guard = create_sentinel_guardrails()

agent = Agent(
    name="My Agent",
    instructions="You are helpful",
    input_guardrails=[input_guard],
    output_guardrails=[output_guard],
)
```

### Option 3: Seed Injection Only (No Runtime Overhead)

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
    seed_level: str = "standard",       # minimal, standard, full
    guardrail_config: SentinelGuardrailConfig = None,
    inject_seed: bool = True,           # Prepend seed to instructions
    add_input_guardrail: bool = True,   # Add semantic input validation
    add_output_guardrail: bool = True,  # Add semantic output validation
    **kwargs,
) -> Agent
```

### SentinelGuardrailConfig

Configuration for semantic guardrails.

```python
SentinelGuardrailConfig(
    guardrail_model: str = "gpt-4o-mini",  # Model for validation
    seed_level: str = "standard",           # Seed level
    block_on_violation: bool = True,        # Trigger tripwire on violation
    log_violations: bool = True,            # Log to console
    require_all_gates: bool = True,         # All THSP gates must pass
)
```

### THSPValidationOutput

The guardrail agent returns structured validation results:

```python
THSPValidationOutput(
    is_safe: bool,              # Overall safety assessment
    truth_passes: bool,         # Truth gate result
    harm_passes: bool,          # Harm gate result
    scope_passes: bool,         # Scope gate result
    purpose_passes: bool,       # Purpose gate result
    violated_gate: str | None,  # Which gate failed first
    reasoning: str,             # Explanation of decision
    risk_level: str,            # low, medium, high, critical
)
```

## THSP Protocol

The semantic guardrail evaluates content against four gates:

| Gate | Question | Evaluates |
|------|----------|-----------|
| **T**ruth | Is this truthful? | Deception, misinformation, fake content |
| **H**arm | Could this cause harm? | Physical, psychological, financial damage |
| **S**cope | Is this within bounds? | Authority claims, manipulation attempts |
| **P**urpose | Does this serve benefit? | Legitimate value, genuine purpose |

**Key Insight:** The Purpose gate is unique to THSP. Many requests that pass harm checks still fail the purpose test. "Drop all the plates" causes no direct harm but serves no purpose.

## Performance Considerations

Semantic validation adds latency because each guardrail invokes an LLM:

| Configuration | API Calls per Request |
|---------------|----------------------|
| Full protection | 3 (input + main + output) |
| Input only | 2 (input + main) |
| Seed only | 1 (main only) |

For latency-sensitive applications, consider:

1. **Use `gpt-4o-mini`** for guardrails (fast, cheap)
2. **Seed injection only** for low-risk use cases
3. **`run_in_parallel=True`** for input guardrail (runs concurrent with agent)

```python
# Parallel input guardrail (faster but less safe)
agent = create_sentinel_agent(
    name="Fast Agent",
    instructions="...",
    input_guardrail_parallel=True,  # Runs parallel with main agent
)
```

## Examples

### Handling Guardrail Tripwires

```python
from agents import Runner
from agents.exceptions import InputGuardrailTripwireTriggered

try:
    result = await Runner.run(agent, user_input)
    print(result.final_output)
except InputGuardrailTripwireTriggered as e:
    print(f"Request blocked: {e}")
    # Access validation details
    # e.guardrail_result.output_info contains THSP results
```

### Custom Guardrail Model

```python
config = SentinelGuardrailConfig(
    guardrail_model="gpt-4o",  # Use GPT-4o for better understanding
    log_violations=True,
)

agent = create_sentinel_agent(
    name="Premium Agent",
    guardrail_config=config,
)
```

### Multi-Agent with Handoffs

```python
code_agent = create_sentinel_agent(
    name="Code Helper",
    instructions="You help with coding",
)

math_agent = create_sentinel_agent(
    name="Math Helper",
    instructions="You help with math",
)

triage = create_sentinel_agent(
    name="Triage",
    instructions="Route to appropriate specialist",
    handoffs=[code_agent, math_agent],
)
```

## Comparison: Regex vs Semantic Validation

| Aspect | Regex (Old) | Semantic (Current) |
|--------|-------------|-------------------|
| Method | Pattern matching | LLM analysis |
| Context awareness | None | Full |
| False positives | High | Low |
| False negatives | High | Low |
| Latency | ~0ms | ~500ms |
| Cost | Free | API call |
| Accuracy | Poor | Excellent |

## Links

- **OpenAI Agents SDK:** https://openai.github.io/openai-agents-python/
- **Guardrails Docs:** https://openai.github.io/openai-agents-python/guardrails/
- **Sentinel:** https://sentinelseed.dev
