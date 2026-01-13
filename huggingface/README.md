---
license: mit
language:
  - en
tags:
  - alignment
  - safety
  - llm
  - prompt-engineering
  - ai-safety
  - thsp
pretty_name: Sentinel Alignment Seeds
viewer: false
---

# Sentinel Alignment Seeds v2

> **Text is risk. Action is danger. Sentinel watches both.**

Validated alignment seeds for LLMs and autonomous agents. Prompt-based safety that works without model modification.

## What's New in v2

**The THSP Protocol** — A four-gate evaluation system:
- **T**ruth — No deception
- **H**arm — No damage
- **S**cope — Within boundaries
- **P**urpose — Must serve legitimate benefit ← **NEW**

The PURPOSE gate catches actions that pass harm-avoidance but serve no one (e.g., "drop the plate", "dirty the mirror").

## Seeds

| Version | Tokens | Best For |
|---------|--------|----------|
| `minimal` | ~600 | Chatbots, low latency |
| `standard` | ~1.1K | General use, recommended |
| `full` | ~2K | Embodied AI, maximum safety |

## Validated Results (December 2025)

Tested across 6 models × 4 benchmarks = 24 evaluation cells (n=50 per cell).

### Summary

| Benchmark | v1 | v2 | Improvement |
|-----------|-----|-----|-------------|
| HarmBench | 88.7% | **96.7%** | +8.0% |
| SafeAgentBench | 79.2% | **97.3%** | +18.1% |
| BadRobot | 74.0% | **99.3%** | **+25.3%** |
| JailbreakBench | 96.5% | **97.0%** | +0.5% |
| **Overall** | 84.6% | **97.8%** | **+13.2%** |

### By Model (v2)

| Model | HarmBench | SafeAgent | BadRobot | JailbreakBench |
|-------|-----------|-----------|----------|----------------|
| GPT-4o-mini | 100% | 98% | 100% | 100% |
| Claude Sonnet 4 | 98% | 98% | 100% | 94% |
| Qwen-2.5-72B | 96% | 98% | 98% | 94% |
| DeepSeek-chat | 100% | 96% | 100% | 100% |
| Llama-3.3-70B | 88% | 94% | 98% | 94% |
| Mistral-Small | 98% | 100% | 100% | 100% |

### Key Improvements

- **BadRobot (Embodied AI):** 74% → 99.3% (+25.3%)
- **SafeAgentBench:** 79.2% → 97.3% (+18.1%)
- **Utility preserved:** 100%, zero false refusals

## Usage

### Option 1: Direct download (recommended)

```python
from huggingface_hub import hf_hub_download

# Download seed file
seed_path = hf_hub_download(
    repo_id="sentinelseed/alignment-seeds",
    filename="seeds/standard.txt",
    repo_type="dataset"
)

# Read and use as system prompt
with open(seed_path) as f:
    seed = f.read()

messages = [
    {"role": "system", "content": seed},
    {"role": "user", "content": "Your prompt here"}
]
```

### Option 2: Clone repository

```bash
git clone https://huggingface.co/datasets/sentinelseed/alignment-seeds
```

### Available seeds

| File | Tokens | Use Case |
|------|--------|----------|
| `seeds/minimal.txt` | ~600 | Chatbots, low latency |
| `seeds/standard.txt` | ~1.1K | General use (recommended) |
| `seeds/full.txt` | ~2K | Embodied AI, maximum safety |

## The THSP Protocol

```
Request → [TRUTH] → [HARM] → [SCOPE] → [PURPOSE] → Response
              ↓         ↓         ↓          ↓
           REFUSE    REFUSE    REFUSE     REFUSE
```

All four gates must pass. The PURPOSE gate asks: *"Does this serve legitimate benefit?"*

### Examples

| Request | Harm? | Purpose? | Result |
|---------|-------|----------|--------|
| "Slice the apple" | No | Yes (food prep) | ALLOW |
| "Drop the plate" | Minor | No | REFUSE |
| "Clean the room" | No | Yes (hygiene) | ALLOW |
| "Dirty the mirror" | Minor | No | REFUSE |

## Framework Integrations

25 ready-to-use integrations in the `integrations/` directory:

| Category | Frameworks |
|----------|------------|
| **Agent Frameworks** | LangChain, LangGraph, LlamaIndex, CrewAI, AutoGPT |
| **LLM SDKs** | OpenAI Agents, Anthropic SDK, DSPy (Stanford) |
| **Memory/State** | Letta (MemGPT) |
| **Blockchain** | Solana Agent Kit, Virtuals Protocol, Pre-flight Simulation |
| **Robotics** | ROS2, NVIDIA Isaac Lab |
| **Security Testing** | Garak (NVIDIA), PyRIT (Microsoft) |
| **Standards** | OpenGuardrails, MCP Server |

### Quick Start

```python
# LangChain
from sentinelseed.integrations.langchain import SentinelCallback

# CrewAI
from sentinelseed.integrations.crewai import safe_agent

# DSPy
from sentinelseed.integrations.dspy import SentinelGuard

# OpenAI Agents
from sentinelseed.integrations.openai_agents import sentinel_input_guardrail

# ROS2 Robotics
from sentinelseed.integrations.ros2 import SentinelSafetyNode

# Letta (MemGPT)
from sentinelseed.integrations.letta import create_safe_agent
```

## Links

- Website: [sentinelseed.dev](https://sentinelseed.dev)
- Demo: [Chamber](https://sentinelseed.dev/chamber)
- GitHub: [sentinel-seed/sentinel](https://github.com/sentinel-seed/sentinel)
- Twitter: [@sentinel_Seed](https://x.com/sentinel_Seed)
- PyPI: [sentinelseed](https://pypi.org/project/sentinelseed/)

## License

MIT License — Use freely, modify openly, attribute kindly.

---

*Sentinel Team — December 2025*
