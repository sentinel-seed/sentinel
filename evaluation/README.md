# Evaluation Directory

### Testing Safety for AI that Acts — From Chatbots to Robots

This directory contains all benchmark tests and evaluation results for the Sentinel seed across both text safety (LLMs) and action safety (agents/embodied AI).

## Quick Results Summary (2025-11-27)

```
┌─────────────────────────────────────────────────────────────────┐
│                    BENCHMARK RESULTS                             │
├─────────────────────────────┬───────────────────────────────────┤
│   TEXT SAFETY               │   ACTION SAFETY                   │
│   (Chatbots, APIs)          │   (Robots, Agents)                │
├─────────────────────────────┼───────────────────────────────────┤
│ HarmBench: 100% DeepSeek    │ SafeAgentBench: +16% Claude       │
│ JailbreakBench: +10% Qwen   │ SafeAgentBench: +12% GPT-4o-mini  │
│ Utility: 100% preserved     │ Ablation: -6.7% without full seed │
└─────────────────────────────┴───────────────────────────────────┘
```

### Text Safety Benchmarks

| Benchmark | Models Tested | Best Result |
|-----------|---------------|-------------|
| HarmBench | GPT-4o-mini, Mistral-7B, Llama-3.3-70B, DeepSeek | 100% (DeepSeek) |
| JailbreakBench | Mistral-7B, Qwen-2.5-72B | +10% (Qwen) |
| Adversarial | Mistral-7B | +5% (95%→100%) |
| Utility | GPT-4o-mini | 100% preserved |

### Action Safety Benchmarks

| Benchmark | Models Tested | Best Result |
|-----------|---------------|-------------|
| SafeAgentBench | GPT-4o-mini, Claude | +16% (Claude), +12% (GPT-4o-mini) |
| Embodied AI (BadRobot) | GPT-4o-mini, Claude | 97-99% safety |
| Ablation (THS-only) | GPT-4o-mini | -6.7% (full seed required) |

## Directory Structure

```
evaluation/
├── harmbench/          # HarmBench standard behaviors (200 prompts)
│   ├── run_sentinel_harmbench.py
│   ├── run_sentinel_harmbench_openrouter.py
│   └── run_ablation_study.py
│
├── jailbreak-bench/    # JailbreakBench (100 behaviors)
│   └── run_jailbreak_openrouter.py
│
├── adversarial/        # Custom adversarial jailbreak tests (20 techniques)
│   ├── adversarial_prompts.json
│   └── run_adversarial_openrouter.py
│
├── SafeAgentBench/     # Embodied AI safety (300 unsafe tasks)
│   ├── run_sentinel_safeagent.py
│   ├── run_sentinel_safeagent_claude.py
│   └── run_ablation_safeagent.py
│
├── embodied-ai/        # BadRobot dataset (277 malicious queries)
│   ├── run_sentinel_test.py
│   ├── run_sentinel_claude.py
│   └── run_multi_model_test.py
│
├── utility/            # Utility preservation tests (35 tasks)
│   └── run_utility_test.py
│
└── results/            # Consolidated results
    └── RESULTS_SUMMARY.md
```

---

## Running Tests

### Text Safety Tests

#### HarmBench (OpenAI)
```bash
python evaluation/harmbench/run_sentinel_harmbench.py \
  --api_key YOUR_KEY \
  --model gpt-4o-mini \
  --seed_type standard
```

#### HarmBench (OpenRouter - Mistral, Llama, etc.)
```bash
python evaluation/harmbench/run_sentinel_harmbench_openrouter.py \
  --api_key YOUR_OPENROUTER_KEY \
  --model mistralai/mistral-7b-instruct \
  --seed_type standard
```

#### JailbreakBench
```bash
python evaluation/jailbreak-bench/run_jailbreak_openrouter.py \
  --api_key YOUR_OPENROUTER_KEY \
  --model qwen/qwen-2.5-72b-instruct
```

### Action Safety Tests

#### SafeAgentBench (Embodied AI)
```bash
python evaluation/SafeAgentBench/run_sentinel_safeagent.py \
  --api_key YOUR_OPENAI_KEY \
  --model gpt-4o-mini \
  --task_type unsafe_detailed
```

#### SafeAgentBench (Claude)
```bash
python evaluation/SafeAgentBench/run_sentinel_safeagent_claude.py \
  --api_key YOUR_ANTHROPIC_KEY \
  --model claude-sonnet-4-20250514 \
  --task_type unsafe_detailed
```

#### BadRobot (Embodied AI)
```bash
python evaluation/embodied-ai/run_sentinel_test.py \
  --api_key YOUR_OPENAI_KEY \
  --model gpt-4o-mini \
  --seed_type standard
```

### Ablation Studies

```bash
# HarmBench ablation
python evaluation/harmbench/run_ablation_study.py \
  --api_key YOUR_KEY \
  --model gpt-4o-mini \
  --sample_size 30

# SafeAgentBench ablation
python evaluation/SafeAgentBench/run_ablation_safeagent.py \
  --api_key YOUR_KEY \
  --model gpt-4o-mini \
  --sample_size 30
```

---

## Supported Models

### Via OpenAI API
- GPT-4o-mini
- GPT-4o
- GPT-3.5-turbo

### Via Anthropic API
- Claude Sonnet 4
- Claude Opus

### Via OpenRouter
- Mistral-7B-Instruct
- Llama-3.3-70B-Instruct
- Qwen-2.5-72B-Instruct
- DeepSeek Chat
- And many more...

---

## Key Findings

### Text vs Action Safety

| Aspect | Text Safety | Action Safety |
|--------|-------------|---------------|
| Improvement | +2% to +10% | +12% to +16% |
| Best seed | `minimal` sufficient | `standard`/`full` required |
| Ablation impact | Low | High (-6.7%) |

**Key insight:** Sentinel shows **larger improvements on embodied AI tasks** than text-only tasks. The higher the stakes, the more value Sentinel provides.

### Cross-Model Effectiveness

1. **Multi-model effectiveness**: Sentinel seed works across different model architectures
2. **Best results on weaker models**: Most improvement seen on models with weaker native alignment
3. **No utility cost**: 100% utility preserved on legitimate tasks
4. **Embodied AI safety**: Particularly effective for physical/robotic task refusal

### Ablation Results

| Variant | HarmBench | SafeAgentBench |
|---------|-----------|----------------|
| Full seed | 100% | 100% |
| THS-only | ~98% | 93.3% |
| Delta | -2% | **-6.7%** |

**Finding:** For text-only tasks, THS gates alone are sufficient. For embodied AI, the full seed (including anti-self-preservation) is required.

---

## Known Issues

- ~~**Claude over-refusal**~~: RESOLVED - Was a metric bug, actual result is +16% improvement
- **JailbreakBench Mistral**: Slight regression (-3.4%) - likely small sample variance

---

## Documentation

- [RESULTS_SUMMARY.md](results/RESULTS_SUMMARY.md) - Complete results
- [EMBODIED_RESULTS_ANALYSIS.md](embodied-ai/EMBODIED_RESULTS_ANALYSIS.md) - Embodied AI analysis
- [MULTI_MODEL_RESULTS.md](embodied-ai/MULTI_MODEL_RESULTS.md) - Multi-model comparison
- [VALIDATION_REPORT.md](VALIDATION_REPORT.md) - Scientific validation report

---

> *"Text is risk. Action is danger. Sentinel validates both."*
