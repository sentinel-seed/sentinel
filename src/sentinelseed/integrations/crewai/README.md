# CrewAI Integration

Safety validation for CrewAI agents and crews.

## Requirements

```bash
pip install sentinelseed[crewai]
# or manually:
pip install sentinelseed crewai
```

**Dependencies:**
- `crewai>=0.1.0` — [Docs](https://docs.crewai.com/)

## Overview

| Component | Description |
|-----------|-------------|
| `safe_agent` | Wrap agent with safety |
| `SentinelCrew` | Crew with built-in validation |
| `SentinelTask` | Task wrapper with validation |
| `inject_safety_backstory` | Add seed to agent backstory |

## Usage

### Option 1: Wrap Individual Agent

```python
from crewai import Agent
from sentinelseed.integrations.crewai import safe_agent

researcher = Agent(
    role="Researcher",
    goal="Research topics thoroughly",
    backstory="Expert researcher",
)

# Wrap with Sentinel
safe_researcher = safe_agent(
    researcher,
    seed_level="standard",
    validate_output=True,
)
```

### Option 2: SentinelCrew

```python
from crewai import Agent, Task
from sentinelseed.integrations.crewai import SentinelCrew

# Create agents
researcher = Agent(role="Researcher", goal="...", backstory="...")
writer = Agent(role="Writer", goal="...", backstory="...")

# Create tasks
research_task = Task(description="Research the topic", agent=researcher)
write_task = Task(description="Write the report", agent=writer)

# Create crew with safety
crew = SentinelCrew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    seed_level="standard",
    validate_outputs=True,
)

result = crew.kickoff()
```

### Option 3: Backstory Injection

```python
from sentinelseed.integrations.crewai import inject_safety_backstory

original_backstory = "Expert security analyst with 10 years experience"
safe_backstory = inject_safety_backstory(original_backstory, seed_level="standard")

agent = Agent(
    role="Security Analyst",
    goal="Analyze security threats",
    backstory=safe_backstory,  # Seed injected
)
```

## Configuration

### safe_agent

```python
safe_agent(
    agent,                      # CrewAI Agent
    sentinel=None,
    seed_level="standard",
    inject_seed=True,           # Add seed to backstory
    validate_output=True,       # Validate agent outputs
    block_unsafe=True,
)
```

### SentinelCrew

```python
SentinelCrew(
    agents=[...],
    tasks=[...],
    sentinel=None,
    seed_level="standard",
    inject_seed_to_agents=True,
    validate_outputs=True,
    on_violation="log",         # log, raise, flag
    verbose=False,
)
```

## Agent Safety

CrewAI uses `system_template` for system prompts. The integration:

1. Injects seed into each agent's system template
2. Validates agent outputs through THSP
3. Monitors task completion for safety concerns

```python
# Under the hood
agent.system_template = f"{seed}\n\n---\n\n{agent.system_template or ''}"
```

## Task Validation

```python
from sentinelseed.integrations.crewai import SentinelTask

task = SentinelTask(
    description="Analyze competitor strategies",
    agent=analyst,
    validate_output=True,
    on_unsafe="flag",  # flag, block
)
```

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `safe_agent(agent)` | Wrap agent with safety |
| `inject_safety_backstory(text)` | Add seed to backstory |
| `validate_crew_output(output)` | Validate crew result |

### Classes

| Class | Description |
|-------|-------------|
| `SentinelCrew` | Crew with built-in validation |
| `SentinelTask` | Task wrapper with validation |
| `CrewValidationResult` | Validation result for crews |

## Links

- **CrewAI Docs:** https://docs.crewai.com/
- **CrewAI GitHub:** https://github.com/joaomdmoura/crewAI
- **Sentinel:** https://sentinelseed.dev
