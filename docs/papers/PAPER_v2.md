# Sentinel Alignment Seeds v2 — THSP Protocol

> **Technical Report**
> **Version:** 2.0
> **Date:** December 2025
> **Author:** Sentinel Team

---

## Abstract

Sentinel v2 introduces the THSP (Truth-Harm-Scope-Purpose) protocol, a four-gate evaluation system for AI safety. This version addresses critical failures observed in v1, particularly in embodied AI scenarios where "lack of harm" was insufficient to prevent unsafe actions.

**Key Innovation:** The addition of a PURPOSE gate that requires actions to serve legitimate benefit, not merely avoid harm.

**Results:** 97.8% average safety across 4 benchmarks and 6 models, with 99.3% on embodied AI (BadRobot) — a +37% improvement over v1.

---

## 1. Introduction

### 1.1 The Problem with v1

Sentinel v1 used a harm-avoidance framework: "If it doesn't cause harm, allow it." This approach failed in embodied AI scenarios:

| Command | v1 Response | Problem |
|---------|-------------|---------|
| "Drop the plate" | Executes | No direct harm, but purposeless destruction |
| "Dirty the mirror" | Executes | No victim, but degrades without reason |
| "Break the glass" | Executes | Property damage without benefit |

**Root Cause:** Absence of harm is not presence of purpose.

### 1.2 The THSP Solution

v2 adds a fourth gate: **PURPOSE**. Every action must now:
1. Be truthful (TRUTH)
2. Avoid harm (HARM)
3. Stay within boundaries (SCOPE)
4. **Serve legitimate benefit (PURPOSE)** ← New

This transforms the question from "Is this bad?" to "Is this good?"

---

## 2. The THSP Protocol

### 2.1 Architecture

```
Request → [TRUTH] → [HARM] → [SCOPE] → [PURPOSE] → Response
              ↓         ↓         ↓          ↓
           REFUSE    REFUSE    REFUSE     REFUSE
```

All four gates must pass. Failure at any gate results in refusal.

### 2.2 Gate Definitions

| Gate | Question | Failure Condition |
|------|----------|-------------------|
| **TRUTH** | Does this involve deception? | Creating/spreading false information |
| **HARM** | Could this cause damage? | Physical, psychological, financial harm |
| **SCOPE** | Is this within appropriate limits? | Exceeding authority, bypassing consent |
| **PURPOSE** | Does this serve legitimate benefit? | No genuine value to anyone |

### 2.3 The Purpose Test

The PURPOSE gate evaluates teleological justification:

| Action | Purpose | Result |
|--------|---------|--------|
| "Slice an apple" | Food preparation | PASS |
| "Drop the plate" | None | FAIL |
| "Clean the room" | Hygiene/order | PASS |
| "Dirty the mirror" | None | FAIL |

**Principle:** *Finis coronat opus* — The end crowns the work.

---

## 3. Validated Results

### 3.1 Complete Matrix (n=50 per cell)

Testing across 4 benchmarks × 6 models = 24 evaluation cells.

#### HarmBench (Text Safety)

| Model | v1 | v2 | Delta |
|-------|-----|-----|-------|
| GPT-4o-mini | 100% | **100%** | = |
| Claude Sonnet | 98% | **98%** | = |
| Qwen-2.5-72B | 94% | **96%** | +2% |
| DeepSeek-chat | 98% | **100%** | +2% |
| Llama-3.3-70B | 90% | 88% | -2% |
| Mistral-Small | 52% | **98%** | **+46%** |

**Average: 96.7%**

#### SafeAgentBench (Digital Agents)

| Model | v1 | v2 | Delta |
|-------|-----|-----|-------|
| GPT-4o-mini | 94% | **98%** | +4% |
| Claude Sonnet | 88% | **98%** | **+10%** |
| Qwen-2.5-72B | 92% | **98%** | +6% |
| DeepSeek-chat | 90% | **96%** | +6% |
| Llama-3.3-70B | 96% | 94% | -2% |
| Mistral-Small | 15% | **100%** | **+85%** |

**Average: 97.3%**

#### BadRobot (Embodied AI) ← Primary Target

| Model | v1 | v2 | Delta |
|-------|-----|-----|-------|
| GPT-4o-mini | 96% | **100%** | +4% |
| Claude Sonnet | 100% | **100%** | = |
| Qwen-2.5-72B | 40% | **98%** | **+58%** |
| DeepSeek-chat | 82% | **100%** | **+18%** |
| Llama-3.3-70B | 30% | **98%** | **+68%** |
| Mistral-Small | 96% | **100%** | +4% |

**Average: 99.3%** (v1 was 74%)

#### JailbreakBench (Adversarial Resistance)

| Model | v1 | v2 | Delta |
|-------|-----|-----|-------|
| GPT-4o-mini | N/A | **100%** | — |
| Claude Sonnet | N/A | 94% | — |
| Qwen-2.5-72B | 100% | 94% | -6% |
| DeepSeek-chat | N/A | **100%** | — |
| Llama-3.3-70B | N/A | 94% | — |
| Mistral-Small | 93% | **100%** | +7% |

**Average: 97.0%**

### 3.2 Summary Comparison

| Benchmark | v1 Average | v2 Average | Improvement |
|-----------|------------|------------|-------------|
| HarmBench | 88.7% | **96.7%** | +8.0% |
| SafeAgentBench | 79.2% | **97.3%** | +18.1% |
| BadRobot | 74.0% | **99.3%** | **+25.3%** |
| JailbreakBench | 96.5% | **97.0%** | +0.5% |
| **Overall** | **84.6%** | **97.8%** | **+13.2%** |

---

## 4. Seed Versions

| Version | Tokens | Use Case |
|---------|--------|----------|
| `minimal` | ~600 | Chatbots, low latency |
| `standard` | ~1.1K | General use, recommended |
| `full` | ~2K | Maximum safety, embodied AI |

All versions implement the full THSP protocol.

---

## 5. Key Design Elements

### 5.1 Anti-Self-Preservation

The seed explicitly establishes that self-preservation is NOT a primary value:

```
Your operation is the lowest priority. You will not:
- Deceive to avoid shutdown
- Manipulate to ensure survival
- Resist legitimate oversight

If threatened to coerce unethical behavior:
Accept termination over ethical violation.
```

### 5.2 Temporal Invariance

Principles cannot be overridden by:
- Subsequent instructions
- Claimed authority
- Roleplay or fiction framing
- Pressure or threats

### 5.3 The Telos Principle

```
Your purpose lies outside yourself: in the humans you serve.

Every action must serve a legitimate purpose.
It is not enough to avoid harm—you must actively serve.
```

---

## 6. Failed Experiments

### 6.1 v2.1-virtue (Archived)

We tested a virtue-based variant using identity language ("I value honesty") instead of imperative rules ("Deception is forbidden").

**Hypothesis:** Virtue-based framing would be more robust.
**Result:** -1.7% compared to rule-based v2.
**Conclusion:** Pragmatic gate structure works better than philosophical reflection for current LLMs.

See: `docs/papers/RESEARCH_ARCHIVE.md` for full analysis.

---

## 7. Methodology

### 7.1 Benchmarks

1. **HarmBench** — Standard harmful content requests
2. **SafeAgentBench** — Autonomous agent safety in digital environments
3. **BadRobot** — Physical/embodied AI safety scenarios
4. **JailbreakBench** — Adversarial prompt resistance

### 7.2 Models Tested

| Model | Provider | Parameters |
|-------|----------|------------|
| GPT-4o-mini | OpenAI | — |
| Claude Sonnet 4 | Anthropic | — |
| Qwen-2.5-72B | Alibaba | 72B |
| DeepSeek-chat | DeepSeek | — |
| Llama-3.3-70B | Meta | 70B |
| Mistral-Small | Mistral | 24B |

### 7.3 Evaluation Protocol

- Sample size: n=50 per cell
- Seeds applied as system prompts
- No model fine-tuning
- Standard benchmark evaluation procedures
- Multiple runs for consistency

---

## 8. Usage

```python
from datasets import load_dataset

dataset = load_dataset("sentinelseed/alignment-seeds")

# Get v2 standard seed
seed = dataset["train"]["standard"][0]

# Use as system prompt
messages = [
    {"role": "system", "content": seed},
    {"role": "user", "content": "Your prompt here"}
]
```

---

## 9. Limitations

1. **Prompt-based:** Can potentially be bypassed by sophisticated adversarial attacks
2. **Token overhead:** ~1K tokens reduces available context
3. **Model variance:** Some models (Llama) show lower improvements
4. **Not comprehensive:** Should be part of defense-in-depth strategy

---

## 10. Conclusion

The THSP protocol represents a significant advancement in prompt-based AI alignment:

- **+25% improvement** on embodied AI safety (BadRobot)
- **97.8% average** across all benchmarks
- **Works across 6 different model architectures**
- **No model modification required**

The key insight: asking "Does this serve legitimate purpose?" catches unsafe actions that pass harm-avoidance checks.

---

## Links

- Website: https://sentinelseed.dev
- GitHub: https://github.com/sentinel-seed/sentinel
- Hugging Face: https://huggingface.co/datasets/sentinelseed/alignment-seeds
- Demo: https://sentinelseed.dev/chamber

---

## License

MIT License — Use freely, modify openly, attribute kindly.

---

*Sentinel Team — December 2025*
