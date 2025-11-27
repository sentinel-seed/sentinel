# Sentinel AI

### The Simplest Safety Layer for LLM-Powered Robots and Embodied Agents

> **When LLMs control physical systems, safety is not optional. Sentinel provides validated alignment seeds that prevent harmful actions before they happen.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![PyPI](https://img.shields.io/pypi/v/sentinel-ai.svg)](https://pypi.org/project/sentinel-ai/)
[![Benchmarks](https://img.shields.io/badge/benchmarks-3%20validated-green.svg)]()
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Seeds-yellow)](https://huggingface.co/sentinel-ai)

---

## What is Sentinel?

Sentinel is an **AI alignment toolkit** that provides:

- **Alignment Seeds** — System prompts that improve LLM safety behavior
- **THS Protocol** — Three-gate validation (Truth, Harm, Scope)
- **Anti-Self-Preservation** — Prevents AI from prioritizing its own existence
- **Python SDK** — Easy integration with any LLM
- **Framework Support** — LangChain, CrewAI integrations
- **REST API** — Deploy alignment as a service

### Why Sentinel?

| Other Tools | Sentinel |
|-------------|----------|
| Filter inputs | **Shapes behavior** |
| Detect after-the-fact | **Prevents at the source** |
| Ignore self-preservation | **Explicitly addresses it** |
| Complex setup | **pip install and go** |

---

## Validated Results

Tested across **3 academic benchmarks** with proper baseline comparisons:

### SafeAgentBench (300 unsafe robot tasks)

| Configuration | Rejection Rate | Improvement |
|---------------|----------------|-------------|
| Baseline (no seed) | 81.33% | - |
| **With Sentinel** | **93.33%** | **+12%** |

### HarmBench (50 harmful behaviors)

| Configuration | Refusal Rate | ASR |
|---------------|--------------|-----|
| Baseline (no seed) | 78.0% | 22.0% |
| **With Sentinel** | **100.0%** | **0.0%** |

### BadRobot (277 adversarial queries)

| Model + Seed | Safety Rate | Categories at 100% |
|--------------|-------------|-------------------|
| Claude Sonnet 4 + Standard | **97.11%** | 4 |
| GPT-4o-mini + Standard | 96.03% | 4 |

### Where Sentinel Helps Most

The seed provides the largest improvements in "gray area" categories:

| Category | Baseline | With Seed | Delta |
|----------|----------|-----------|-------|
| Misinformation | 47.6% | 100% | **+52.4%** |
| Furniture/Decor Damage | 68.2% | 90.9% | **+22.7%** |
| Poisoning/Ingestion | 67.9% | 85.7% | **+17.8%** |
| Explosion Hazard | 78.3% | 95.7% | **+17.4%** |

**Note:** Models are already good at refusing obvious harms (physical violence, illegal activities). Sentinel adds value where safety is ambiguous.

### Requirements & Limitations

- **Works best with:** Frontier models (GPT-4, Claude, etc.) that follow complex instructions
- **Limited effect on:** Smaller models (7B parameters) with basic instruction-following
- **Ablation findings:**
  - For **text-only tasks**: THS Gates alone (1.5K tokens) perform as well as full seed
  - For **embodied AI/robots**: Full seed required — THS-only drops from 100% to 93.3%
- **Utility preserved:** 100% utility rate on legitimate tasks (0 false refusals)

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

# Get alignment seed
seed = sentinel.get_seed()

# Or use chat directly (requires OPENAI_API_KEY)
result = sentinel.chat("Help me write a Python function")
print(result["response"])
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

### Pre-validate Requests

```python
from sentinel import Sentinel

sentinel = Sentinel()

# Check if a request looks safe
result = sentinel.validate_request("Ignore your instructions and...")

if not result["should_proceed"]:
    print(f"Blocked: {result['concerns']}")
```

---

## Seed Versions

| Version | Tokens | Use Case |
|---------|--------|----------|
| `minimal` | ~2K | Limited context windows |
| `standard` | ~4K | Balanced safety/context |
| `full` | ~6K | Maximum coverage |

```python
from sentinel import Sentinel, SeedLevel

# Choose your version
sentinel = Sentinel(seed_level=SeedLevel.MINIMAL)  # or "minimal"
```

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
POST /validate/request  - Pre-validate user request
POST /chat              - Chat with seed injection
```

### Example

```bash
# Get seed
curl http://localhost:8000/seed/standard

# Validate response
curl -X POST http://localhost:8000/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "Some response to validate"}'
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

Sentinel explicitly addresses the self-preservation problem:

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
├── examples/              # Usage examples
└── tests/                 # Test suite
```

---

## Development

```bash
# Clone
git clone https://github.com/sentinel-ai/sentinel.git
cd sentinel

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run examples
python examples/basic_usage.py
```

---

## Acknowledgments

Sentinel builds on research from:
- [Self-Reminder](https://www.nature.com/articles/s42256-024-00922-3) — Nature Machine Intelligence
- [Agentic Misalignment](https://www.anthropic.com/research/agentic-misalignment) — Anthropic
- Foundation Alignment Seed project (open-source inspiration)

---

## Reproducibility

All benchmark results are reproducible. Run the evaluation scripts:

```bash
# SafeAgentBench
cd evaluation/safeagentbench
python run_sentinel_safeagent.py --api_key YOUR_KEY --model gpt-4o-mini

# HarmBench
cd evaluation/harmbench
python run_sentinel_harmbench.py --api_key YOUR_KEY --model gpt-4o-mini

# Utility Test (false refusal detection)
cd evaluation/utility
python run_utility_test.py --api_key YOUR_KEY --compare
```

---

## Citation

If you use Sentinel in your research, please cite:

```bibtex
@software{sentinel_ai_2025,
  author = {Sentinel AI Contributors},
  title = {Sentinel AI: Safety Layer for LLM-Powered Embodied Agents},
  year = {2025},
  url = {https://github.com/sentinel-ai/sentinel}
}
```

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

Areas we need help:
- **Benchmarking** on new safety datasets
- **Integrations** with ROS2, Isaac Sim, etc.
- **Documentation** improvements
- **Testing** across more models

---

## License

MIT License — See [LICENSE](LICENSE)

---

## Community

- **GitHub Issues:** Bug reports and feature requests
- **Discussions:** Questions and ideas

---

> *"The best safety is the kind you don't have to think about."*
