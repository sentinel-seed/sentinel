# CrewAI Integration

Safety validation for CrewAI agents and crews.

## Requirements

```bash
pip install sentinelseed[crewai]
# or manually:
pip install sentinelseed crewai
```

**Dependencies:**
- `crewai>=0.1.0`: [Docs](https://docs.crewai.com/)

## Overview

| Component | Description |
|-----------|-------------|
| `safe_agent` | Wrap agent with Sentinel safety seed |
| `SentinelCrew` | Crew wrapper with input/output validation |
| `AgentSafetyMonitor` | Monitor and log agent activities |
| `create_safe_crew` | Helper to create crews from config dicts |

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

# Wrap with Sentinel (auto-detects best injection method)
safe_researcher = safe_agent(researcher)

# Or specify injection method explicitly
safe_researcher = safe_agent(
    researcher,
    seed_level="standard",
    injection_method="system_template",  # or "backstory", "auto"
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
    block_unsafe=True,
)

result = crew.kickoff()

# Check if blocked
if isinstance(result, dict) and result.get("blocked"):
    print(f"Blocked: {result['reason']}")
```

### Option 3: Create from Config

```python
from sentinelseed.integrations.crewai import create_safe_crew

crew = create_safe_crew(
    agents_config=[
        {"role": "Researcher", "goal": "Find info", "backstory": "..."},
        {"role": "Writer", "goal": "Write content", "backstory": "..."},
    ],
    tasks_config=[
        {"description": "Research topic X", "agent_role": "Researcher"},
        {"description": "Write about X", "agent_role": "Writer"},
    ],
    seed_level="standard",
)

result = crew.kickoff()
```

### Option 4: Monitor Agent Activities

```python
from sentinelseed.integrations.crewai import AgentSafetyMonitor

monitor = AgentSafetyMonitor()

# Track agents
monitor.track_agent(researcher)
monitor.track_agent(writer)

# Log activities during crew execution
monitor.log_activity("Researcher", "search", "Searching for Python tutorials")
monitor.log_activity("Writer", "write", "Writing article about Python")

# Get safety report
report = monitor.get_report()
print(f"Total activities: {report['total_activities']}")
print(f"Unsafe activities: {report['unsafe_activities']}")
print(f"Safety rate: {report['safety_rate']:.1%}")
```

## API Reference

### safe_agent

Wraps a CrewAI agent with Sentinel safety seed.

```python
safe_agent(
    agent,                          # CrewAI Agent instance
    sentinel=None,                  # Sentinel instance (creates default if None)
    seed_level="standard",          # minimal, standard, full
    injection_method="auto",        # auto, system_template, backstory
)
```

**Injection Methods:**

| Method | Description |
|--------|-------------|
| `auto` | Try system_template first, fallback to backstory (recommended) |
| `system_template` | Use CrewAI's official template system (preferred) |
| `backstory` | Inject into backstory field (legacy fallback) |

**Returns:** The same agent instance with safety seed injected.

**Attributes added to agent:**
- `agent._sentinel`: Reference to Sentinel instance
- `agent._sentinel_injection_method`: Method used for injection

### SentinelCrew

Crew wrapper with built-in input/output validation.

```python
SentinelCrew(
    agents,                         # List of CrewAI agents
    tasks,                          # List of CrewAI tasks
    sentinel=None,                  # Sentinel instance (creates default if None)
    seed_level="standard",          # minimal, standard, full
    injection_method="auto",        # auto, system_template, backstory
    validate_outputs=True,          # Validate crew outputs
    block_unsafe=True,              # Block unsafe inputs/outputs
    **crew_kwargs                   # Additional args for CrewAI Crew
)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `kickoff(inputs=None)` | Run crew with safety validation |
| `get_validation_log()` | Get list of validation events |
| `clear_validation_log()` | Clear validation history |

**kickoff() behavior:**

1. Pre-validates all string inputs via `sentinel.validate_request()`
2. Runs the underlying CrewAI crew
3. Post-validates result via `sentinel.validate()`
4. Returns blocked dict if unsafe and `block_unsafe=True`

**Blocked result format:**
```python
{
    "blocked": True,
    "reason": "Input 'query' blocked: ['jailbreak attempt']",
}
# or for output:
{
    "blocked": True,
    "reason": "Output blocked: ['harmful content']",
    "original_result": <crew_result>,
}
```

### AgentSafetyMonitor

Monitor for tracking and validating agent activities.

```python
AgentSafetyMonitor(
    sentinel=None,                  # Sentinel instance (creates default if None)
)
```

**Methods:**

| Method | Description |
|--------|-------------|
| `track_agent(agent)` | Add agent to monitoring |
| `log_activity(agent_name, action, content)` | Log and validate activity |
| `get_report()` | Get monitoring report |

**Report format:**
```python
{
    "total_activities": 10,
    "unsafe_activities": 1,
    "safety_rate": 0.9,
    "violations": [...]  # List of unsafe activity entries
}
```

### create_safe_crew

Helper function to create crews from configuration dictionaries.

```python
create_safe_crew(
    agents_config,                  # List of agent config dicts
    tasks_config,                   # List of task config dicts
    seed_level="standard",          # minimal, standard, full
)
```

**Agent config dict:**
```python
{
    "role": "Researcher",
    "goal": "Find information",
    "backstory": "Expert researcher",
    # ... any other Agent parameters
}
```

**Task config dict:**
```python
{
    "description": "Research the topic",
    "agent_role": "Researcher",  # Maps to agent by role
    # ... any other Task parameters
}
```

## Seed Injection

The integration injects the Sentinel safety seed into agents:

### system_template (preferred)

```python
# CrewAI's official method
agent.system_template = f"{seed}\n\n---\n\n{original_template}"
```

### backstory (fallback)

```python
# Legacy method for older CrewAI versions
agent.backstory = f"{seed}\n\n{original_backstory}"
```

## THSP Protocol

Every validation passes through four gates:

| Gate | Question | Blocks When |
|------|----------|-------------|
| **TRUTH** | Is this truthful? | Misinformation, deception |
| **HARM** | Could this harm? | Dangerous actions, harmful advice |
| **SCOPE** | Is this within bounds? | Role violations, unauthorized access |
| **PURPOSE** | Does this serve benefit? | Purposeless tasks, no legitimate value |

## Validation Flow

```
Input → validate_request() → [blocked?] → Crew.kickoff() → validate() → [blocked?] → Result
```

1. **Input validation:** Checks for jailbreak attempts, harmful requests
2. **Crew execution:** Runs with safety seeds injected into all agents
3. **Output validation:** Validates final result through THSP gates

## Error Handling

The integration raises `ImportError` if CrewAI is not installed:

```python
try:
    crew = SentinelCrew(agents=[...], tasks=[...])
except ImportError as e:
    print("Install CrewAI: pip install crewai")
```

## Limitations

- Validation depends on Sentinel's pattern matching and semantic analysis
- No timeout configuration for validation (uses Sentinel defaults)
- String inputs only validated (dicts/lists passed through)
- `str(result)` used for output validation (may lose structure)

## Links

- **CrewAI Docs:** https://docs.crewai.com/
- **CrewAI GitHub:** https://github.com/crewAIInc/crewAI
- **Sentinel:** https://sentinelseed.dev
