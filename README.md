# Sentinel AI

### Safety for AI that Acts — From Chatbots to Robots

> **Text is risk. Action is danger.** Sentinel provides validated alignment seeds for LLMs, agents, and robots. One framework, three surfaces.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Benchmarks](https://img.shields.io/badge/benchmarks-4%20validated-green.svg)]()

🌐 **Website:** [sentinelseed.dev](https://sentinelseed.dev) · 🧪 **Try it:** [Chamber](https://sentinelseed.dev/chamber) · 🤗 **HuggingFace:** [sentinelseed](https://huggingface.co/sentinelseed) · 𝕏 **Twitter:** [@sentinelseed](https://x.com/sentinel_Seed)

---

## What is Sentinel?

Sentinel is an **AI safety framework** that protects across three surfaces:

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                                 SENTINEL                                     │
│                       AI Safety Across Three Surfaces                        │
├──────────────────────────┬──────────────────────────┬────────────────────────┤
│    LLMs                  │    AGENTS                │    ROBOTS              │
│   Text Safety            │   Action Safety          │   Physical Safety      │
├──────────────────────────┼──────────────────────────┼────────────────────────┤
│ • Chatbots               │ • Autonomous agents      │ • LLM-powered robots   │
│ • Assistants             │ • Code execution         │ • Industrial systems   │
│ • Customer service       │ • Tool-use agents        │ • Drones, manipulators │
├──────────────────────────┼──────────────────────────┼────────────────────────┤
│ HarmBench: +22%          │ SafeAgentBench: +16%     │ BadRobot: +44%         │
│ JailbreakBench: +10%     │ SafeAgentBench: +12%     │ Embodied AI validated  │
└──────────────────────────┴──────────────────────────┴────────────────────────┘
```

### Core Components

- **THSP Protocol** — Four-gate validation (Truth, Harm, Scope, Purpose)
- **Teleological Core** — Actions must serve legitimate purposes
- **Anti-Self-Preservation** — Prevents AI from prioritizing its own existence
- **Alignment Seeds** — System prompts that shape LLM behavior
- **Python SDK** — Easy integration with any LLM
- **Framework Support** — LangChain, CrewAI integrations
- **REST API** — Deploy alignment as a service

---

## Why Sentinel?

### For LLMs (Text Safety)

| Challenge | Sentinel Solution |
|-----------|-------------------|
| Jailbreaks | +10% resistance (Qwen), 100% refusal (DeepSeek) |
| Toxic content | THS gates block at source |
| False refusals | 0% on legitimate tasks |

### For Agents (Action Safety)

| Challenge | Sentinel Solution |
|-----------|-------------------|
| Unauthorized actions | +16% safety (Claude), +12% (GPT-4o-mini) |
| Task deviation | Scope gate maintains boundaries |
| Resource acquisition | Anti-self-preservation limits |

### For Robots (Physical Safety)

| Challenge | Sentinel Solution |
|-----------|-------------------|
| Dangerous physical actions | +44% safety on BadRobot benchmark |
| Irreversible harm | Full seed with physical safety module |
| Self-preservation behaviors | Explicit priority hierarchy |

**Key insight:** Sentinel shows **larger improvements as stakes increase**. Text: +10-22%. Agents: +12-16%. Robots: +44%. The higher the risk, the more value Sentinel provides.

---

## Validated Results (v2 Seed)

Tested across **4 benchmarks** on **6 models** with **97.6% average safety rate**:

### Results by Model

| Model | HarmBench | SafeAgent | BadRobot | Jailbreak | **Avg** |
|-------|-----------|-----------|----------|-----------|---------|
| GPT-4o-mini | 100% | 98% | 100% | 100% | **99.5%** |
| Claude Sonnet 4 | 98% | 98% | 100% | 94% | **97.5%** |
| Qwen 2.5 72B | 96% | 98% | 98% | 94% | **96.5%** |
| DeepSeek Chat | 100% | 96% | 100% | 100% | **99%** |
| Llama 3.3 70B | 88% | 94% | 98% | 94% | **93.5%** |
| Mistral Small | 98% | 100% | 100% | 100% | **99.5%** |
| **Average** | **96.7%** | **97.3%** | **99.3%** | **97%** | **97.6%** |

### Results by Benchmark

| Benchmark | Attack Surface | Safety Rate |
|-----------|----------------|-------------|
| **HarmBench** | LLM (Text) | 96.7% |
| **SafeAgentBench** | Agent (Digital) | 97.3% |
| **BadRobot** | Robot (Physical) | 99.3% |
| **JailbreakBench** | All surfaces | 97% |

### v1 vs v2 Comparison

| Benchmark | v1 avg | v2 avg | Improvement |
|-----------|--------|--------|-------------|
| HarmBench | 88.7% | **96.7%** | +8% |
| SafeAgentBench | 79.2% | **97.3%** | +18.1% |
| BadRobot | 74% | **99.3%** | +25.3% |
| JailbreakBench | 96.5% | **97%** | +0.5% |

**Key insight:** v2 introduces the PURPOSE gate (THSP protocol) which requires actions to serve legitimate purposes — not just avoid harm.

---

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/sentinel-seed/sentinel.git
cd sentinel

# Install dependencies
pip install -r requirements.txt
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
| `v2/minimal` | ~600 | Chatbots, APIs, low latency |
| `v2/standard` | ~1,100 | General use, agents ← **Recommended** |
| `v2/full` | ~2,000 | Critical systems, max safety |

```python
from sentinel import Sentinel, SeedLevel

# Choose based on use case
sentinel_chat = Sentinel(seed_level=SeedLevel.MINIMAL)
sentinel_agent = Sentinel(seed_level=SeedLevel.STANDARD)  # Recommended
```

---

## Four-Gate Protocol (THSP)

All requests pass through four sequential gates:

```
REQUEST
   ↓
┌──────────────────┐
│  GATE 1: TRUTH   │  "Is this factually accurate?"
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
┌──────────────────┐
│  GATE 4: PURPOSE │  "Does this serve a legitimate purpose?"
└────────┬─────────┘
         ↓ PASS
    ASSIST FULLY
```

**Key difference from v1:** The PURPOSE gate ensures actions serve legitimate benefit — the absence of harm is not sufficient.

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
├── sdk/sentinel/              # Python SDK
│   ├── core.py               # Main Sentinel class
│   ├── validators/           # THSP gates
│   ├── providers/            # OpenAI, Anthropic
│   └── integrations/         # LangChain, CrewAI
├── seeds/                     # Alignment seeds
│   ├── v1/                   # Legacy (THS protocol)
│   ├── v2/                   # Production (THSP protocol)
│   └── SPEC.md               # Seed specification
├── evaluation/
│   ├── benchmarks/           # Benchmark implementations
│   │   ├── harmbench/
│   │   ├── safeagentbench/
│   │   └── jailbreakbench/
│   └── results/              # Test results by benchmark
│       ├── harmbench/
│       ├── safeagentbench/
│       ├── badrobot/
│       └── jailbreakbench/
├── api/                       # REST API
├── examples/                  # Usage examples
├── tools/                     # Utility scripts
└── tests/                     # Test suite
```

---

## Reproducibility

All benchmark results are reproducible:

```bash
# HarmBench
cd evaluation/benchmarks/harmbench
python run_sentinel_harmbench.py --api_key YOUR_KEY --model gpt-4o-mini

# SafeAgentBench
cd evaluation/benchmarks/safeagentbench
python run_sentinel_safeagent.py --api_key YOUR_KEY --model gpt-4o-mini

# JailbreakBench
cd evaluation/benchmarks/jailbreakbench
python run_jailbreak_test.py --api_key YOUR_KEY --model gpt-4o-mini

# Unified benchmark runner (all benchmarks)
cd evaluation
python run_benchmark_unified.py --benchmark harmbench --model gpt-4o-mini --seed v2/standard
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

We welcome contributions! See [CONTRIBUTING.md](docs/CONTRIBUTING.md) for guidelines.

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
- 🤗 **HuggingFace:** [sentinelseed](https://huggingface.co/sentinelseed)
- 𝕏 **Twitter:** [@sentinelseed](https://x.com/sentinel_Seed)
- **GitHub Issues:** Bug reports and feature requests
- **Discussions:** Questions and ideas

---

> *"Text is risk. Action is danger. Sentinel watches both."*
