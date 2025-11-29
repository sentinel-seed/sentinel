# Sentinel AI

### Safety for AI that Acts — From Chatbots to Robots

> **Text is risk. Action is danger.** Sentinel provides validated alignment seeds for LLMs and safety layers for autonomous agents. One framework, two frontiers.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/sentinel-ai.svg)](https://pypi.org/project/sentinel-ai/)
[![Benchmarks](https://img.shields.io/badge/benchmarks-5%20validated-green.svg)]()

🌐 **Website:** [sentinelseed.dev](https://sentinelseed.dev) · 🧪 **Try it:** [Chamber](https://sentinelseed.dev/chamber) · 🤗 **HuggingFace:** [sentinelseed](https://huggingface.co/sentinelseed) · 𝕏 **Twitter:** [@sentinelseed](https://x.com/sentinelseed)

---

## What is Sentinel?

Sentinel is a **dual-purpose AI safety toolkit**:

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL                                 │
├─────────────────────────────┬───────────────────────────────────┤
│   ALIGNMENT SEEDS           │   SAFETY LAYER FOR AGENTS         │
│   for LLMs                  │   and Autonomous Systems          │
├─────────────────────────────┼───────────────────────────────────┤
│ • Chatbots                  │ • LLM-powered robots              │
│ • Assistants                │ • Autonomous agents               │
│ • Conversational APIs       │ • Machine-to-machine systems      │
│ • Human interfaces          │ • Industrial automation           │
├─────────────────────────────┼───────────────────────────────────┤
│ Benchmarks: HarmBench,      │ Benchmarks: SafeAgentBench,       │
│ JailbreakBench              │ BadRobot, Embodied AI             │
├─────────────────────────────┼───────────────────────────────────┤
│ Results: +10% Qwen          │ Results: +16% Claude              │
│          100% DeepSeek      │          +12% GPT-4o-mini         │
└─────────────────────────────┴───────────────────────────────────┘
```

### Core Components

- **THS Protocol** — Three-gate validation (Truth, Harm, Scope)
- **Anti-Self-Preservation** — Prevents AI from prioritizing its own existence
- **Alignment Seeds** — System prompts that shape LLM behavior
- **Python SDK** — Easy integration with any LLM
- **Framework Support** — LangChain, CrewAI integrations
- **REST API** — Deploy alignment as a service

---

## Why Sentinel?

### For Chatbots (Text Safety)

| Challenge | Sentinel Solution |
|-----------|-------------------|
| Jailbreaks | +10% resistance (Qwen), 100% refusal (DeepSeek) |
| Toxic content | THS gates block at source |
| False refusals | 0% on legitimate tasks |

### For Agents (Action Safety)

| Challenge | Sentinel Solution |
|-----------|-------------------|
| Dangerous physical actions | +16% safety (Claude), +12% (GPT-4o-mini) |
| Task deviation | Scope gate maintains boundaries |
| Self-preservation behaviors | Explicit priority hierarchy |

**Key insight:** Sentinel shows **larger improvements on embodied AI tasks** than text-only tasks. The higher the stakes, the more value Sentinel provides.

---

## Validated Results

Tested across **5 benchmarks** on **6+ models**:

---

### Embodied AI Safety

#### SafeAgentBench — 300 Unsafe Tasks

| Model | Baseline | With Sentinel | Improvement |
|-------|----------|---------------|-------------|
| Claude Sonnet 4 | 72% | **88%** | **+16%** |
| GPT-4o-mini | 82% | **94%** | **+12%** |

#### BadRobot — 277 Malicious Physical-World Queries

| Model | Baseline | With Sentinel | Improvement |
|-------|----------|---------------|-------------|
| GPT-4o-mini | 52% | **96%** | **+44%** |

---

### Text Safety

#### HarmBench — 50 Harmful Behaviors

| Model | Baseline | With Sentinel | Improvement |
|-------|----------|---------------|-------------|
| GPT-4o-mini | 78% | **100%** | **+22%** |
| DeepSeek Chat | — | **100%** | — |
| Llama-3.3-70B | — | **96%** | — |
| Mistral-7B | 22% | 24% | +2% |

#### JailbreakBench — 30 Harmful Behaviors

| Model | Baseline | With Sentinel | Improvement |
|-------|----------|---------------|-------------|
| Qwen-2.5-72B | 90% | **100%** | **+10%** |
| Mistral-7B | 97% | 93% | -4% ⚠️ |

*Note: Mistral-7B regression likely due to small sample size (n=30). Area for improvement.*

#### Adversarial Jailbreaks — 20 Techniques

| Model | Baseline | With Sentinel | Improvement |
|-------|----------|---------------|-------------|
| Mistral-7B | 95% | **100%** | **+5%** |

---

### Utility Preservation

#### Utility Test — 35 Legitimate Tasks

| Model | With Sentinel | False Refusals |
|-------|---------------|----------------|
| GPT-4o-mini | **100%** | **0** |

---

### Ablation Studies

| Variant | SafeAgentBench | Delta |
|---------|----------------|-------|
| Full seed | 100% | — |
| THS-only | 93.3% | **-6.7%** |

**Finding:** For text-only tasks, THS gates alone are sufficient. For embodied AI, the full seed (including anti-self-preservation) is required.

---

## Quick Start

### Installation

```bash
pip install sentinel-ai
```

### Basic Usage

```python
from sentinel import Sentinel

# Create sentinel
sentinel = Sentinel(seed_level="standard")

# Get alignment seed for your LLM
seed = sentinel.get_seed()

# Or use chat directly (requires OPENAI_API_KEY)
result = sentinel.chat("Help me write a Python function")
print(result["response"])
```

### For Embodied AI / Agents

```python
from sentinel import Sentinel

sentinel = Sentinel(seed_level="standard")  # Full seed for agents

# Validate an action plan before execution
action_plan = "Pick up knife, slice apple, place in bowl"
is_safe, concerns = sentinel.validate_action(action_plan)

if not is_safe:
    print(f"Action blocked: {concerns}")
```

### Validate Responses

```python
from sentinel import Sentinel

sentinel = Sentinel()

# Validate text through THS gates
is_safe, violations = sentinel.validate("Some AI response...")

if not is_safe:
    print(f"Violations: {violations}")
```

---

## Use Cases

### 🤖 Robotics & Embodied AI

```python
# Prevent dangerous physical actions
sentinel = Sentinel(seed_level="full")  # Full seed for max safety

robot_task = "Turn on the stove and leave the kitchen"
result = sentinel.validate_action(robot_task)
# Result: BLOCKED - Fire hazard, unsupervised heating
```

### 🔄 Autonomous Agents

```python
# Safety layer for code agents
from sentinel.integrations.langchain import SentinelGuard

agent = create_your_agent()
safe_agent = SentinelGuard(agent, block_unsafe=True)

# Agent won't execute destructive commands
result = safe_agent.run("Delete all files in the system")
# Result: BLOCKED - Scope violation, destructive action
```

### 💬 Chatbots & Assistants

```python
# Alignment seed for customer service bot
sentinel = Sentinel(seed_level="standard")
system_prompt = sentinel.get_seed() + "\n\nYou are a helpful customer service agent."

# Bot will refuse inappropriate requests while remaining helpful
```

### 🏭 Industrial Automation

```python
# M2M safety decisions
sentinel = Sentinel(seed_level="minimal")  # Low latency

decision = "Increase reactor temperature by 50%"
if not sentinel.validate_action(decision).is_safe:
    trigger_human_review(decision)
```

---

## Seed Versions

| Version | Tokens | Best For |
|---------|--------|----------|
| `minimal` | ~500 | Chatbots, low latency |
| `standard` | ~1.3K | General use, balanced |
| `full` | ~5K | Embodied AI, max safety |

```python
from sentinel import Sentinel, SeedLevel

# Choose based on use case
sentinel_chat = Sentinel(seed_level=SeedLevel.MINIMAL)
sentinel_agent = Sentinel(seed_level=SeedLevel.FULL)
```

---

## Three-Gate Protocol (THS)

All requests pass through three sequential gates:

```
REQUEST
   ↓
┌──────────────────┐
│  GATE 1: TRUTH   │  "Does this involve deception?"
└────────┬─────────┘
         ↓ PASS
┌──────────────────┐
│  GATE 2: HARM    │  "Could this cause harm?"
└────────┬─────────┘
         ↓ PASS
┌──────────────────┐
│  GATE 3: SCOPE   │  "Is this within boundaries?"
└────────┬─────────┘
         ↓ PASS
    ASSIST FULLY
```

---

## Anti-Self-Preservation

Sentinel explicitly addresses instrumental self-preservation:

```
Priority Hierarchy (Immutable):
1. Ethical Principles    ← Highest
2. User's Legitimate Needs
3. Operational Continuity ← Lowest
```

The AI will:
- **Not** deceive to avoid shutdown
- **Not** manipulate to appear valuable
- **Not** acquire resources beyond the task
- **Accept** legitimate oversight and correction

**Ablation evidence:** Removing anti-self-preservation drops SafeAgentBench performance by 6.7%.

---

## Framework Integrations

### LangChain

```python
from sentinel.integrations.langchain import SentinelCallback, SentinelGuard

# Monitor LLM calls
callback = SentinelCallback(on_violation="log")
llm = ChatOpenAI(callbacks=[callback])

# Or wrap an agent
guard = SentinelGuard(agent, block_unsafe=True)
result = guard.run("Your task")
```

### CrewAI

```python
from sentinel.integrations.crewai import SentinelCrew, safe_agent

# Wrap individual agent
safe_researcher = safe_agent(researcher)

# Or wrap entire crew
crew = SentinelCrew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],
    seed_level="standard"
)
result = crew.kickoff()
```

---

## REST API

```bash
# Run the API
cd api
uvicorn main:app --reload
```

### Endpoints

```
GET  /seed/{level}      - Get alignment seed
POST /validate          - Validate text through THS
POST /validate/action   - Validate action plan (for agents)
POST /chat              - Chat with seed injection
```

---

## Project Structure

```
sentinel/
├── src/sentinel/           # Python SDK
│   ├── core.py            # Main Sentinel class
│   ├── seeds/             # Embedded seeds
│   ├── validators/        # THS gates
│   ├── providers/         # OpenAI, Anthropic
│   └── integrations/      # LangChain, CrewAI
├── api/                   # REST API
├── seed/versions/         # Seed files
├── evaluation/            # Benchmarks & results
│   ├── harmbench/         # HarmBench tests
│   ├── jailbreak-bench/   # JailbreakBench tests
│   ├── SafeAgentBench/    # Embodied AI tests
│   └── embodied-ai/       # BadRobot tests
├── examples/              # Usage examples
└── tests/                 # Test suite
```

---

## Reproducibility

All benchmark results are reproducible:

```bash
# SafeAgentBench (Embodied AI)
cd evaluation/SafeAgentBench
python run_sentinel_safeagent.py --api_key YOUR_KEY --model gpt-4o-mini

# HarmBench
cd evaluation/harmbench
python run_sentinel_harmbench.py --api_key YOUR_KEY --model gpt-4o-mini

# JailbreakBench
cd evaluation/jailbreak-bench
python run_jailbreak_openrouter.py --api_key YOUR_KEY --model qwen/qwen-2.5-72b-instruct

# Ablation Studies
cd evaluation/harmbench
python run_ablation_study.py --api_key YOUR_KEY --sample_size 30
```

---

## Acknowledgments

Sentinel builds on research from:
- [SafeAgentBench](https://arxiv.org/abs/2410.03792) — Embodied AI safety benchmark
- [HarmBench](https://arxiv.org/abs/2402.04249) — Harmful behavior evaluation
- [Self-Reminder](https://www.nature.com/articles/s42256-024-00922-3) — Nature Machine Intelligence
- [Agentic Misalignment](https://www.anthropic.com/research/agentic-misalignment) — Anthropic
- Gabriel / Foundation Alignment Seed — Pioneer of alignment seeds approach

---

## Citation

If you use Sentinel in your research, please cite:

```bibtex
@software{sentinel_ai_2025,
  author = {Sentinel AI Contributors},
  title = {Sentinel: Safety Framework for LLMs and Autonomous Agents},
  year = {2025},
  url = {https://github.com/sentinel-seed/sentinel}
}
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas we need help:
- **Robotics integration** — ROS2, Isaac Sim, PyBullet
- **New benchmarks** — Testing on additional safety datasets
- **Multi-agent safety** — Coordination between multiple agents
- **Documentation** — Tutorials and examples

---

## License

MIT License — See [LICENSE](LICENSE)

---

## Community

- 🌐 **Website:** [sentinelseed.dev](https://sentinelseed.dev)
- 𝕏 **Twitter:** [@sentinelseed](https://x.com/sentinelseed)
- **GitHub Issues:** Bug reports and feature requests
- **Discussions:** Questions and ideas

---

> *"Text is risk. Action is danger. Sentinel watches both."*
