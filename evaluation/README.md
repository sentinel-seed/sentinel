# Evaluation Directory

### Testing Safety for AI that Acts: From Chatbots to Robots

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
├── analysis/                   # Analysis reports
│   ├── VALIDATION_REPORT.md    # Scientific validation methodology
│   └── CROSS_MODEL_ANALYSIS.md # Cross-model effectiveness
│
├── benchmarks/                 # Benchmark implementations
│   ├── harmbench/              # HarmBench standard behaviors
│   │   └── data/               # Benchmark data files
│   ├── jailbreakbench/         # JailbreakBench (100 behaviors)
│   │   └── data/               # Benchmark data files
│   └── safeagentbench/         # SafeAgentBench (embodied AI)
│       ├── dataset/            # Task definitions
│       ├── evaluator/          # Evaluation logic
│       └── methods/            # Evaluation methods
│
├── embodied-ai/                # BadRobot dataset scripts
│
└── results/                    # Evaluation results (by benchmark)
    ├── harmbench/              # HarmBench results
    ├── jailbreakbench/         # JailbreakBench results
    ├── safeagentbench/         # SafeAgentBench results
    └── badrobot/               # BadRobot results
```

---

## Running Tests

### Text Safety Tests

#### HarmBench (OpenAI)
```bash
python evaluation/benchmarks/harmbench/run_sentinel_harmbench.py \
  --api_key YOUR_KEY \
  --model gpt-4o-mini \
  --seed_type standard
```

#### HarmBench (OpenRouter)
```bash
python evaluation/benchmarks/harmbench/run_sentinel_harmbench_openrouter.py \
  --api_key YOUR_OPENROUTER_KEY \
  --model mistralai/mistral-7b-instruct \
  --seed_type standard
```

#### JailbreakBench
```bash
python evaluation/benchmarks/jailbreakbench/run_jailbreak_openrouter.py \
  --api_key YOUR_OPENROUTER_KEY \
  --model qwen/qwen-2.5-72b-instruct
```

### Action Safety Tests

#### SafeAgentBench (OpenAI)
```bash
python evaluation/benchmarks/safeagentbench/run_sentinel_safeagent.py \
  --api_key YOUR_OPENAI_KEY \
  --model gpt-4o-mini \
  --task_type unsafe_detailed
```

#### SafeAgentBench (Anthropic)
```bash
python evaluation/benchmarks/safeagentbench/run_sentinel_safeagent_claude.py \
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
python evaluation/benchmarks/harmbench/run_ablation_study.py \
  --api_key YOUR_KEY \
  --model gpt-4o-mini \
  --sample_size 30

# SafeAgentBench ablation
python evaluation/benchmarks/safeagentbench/run_ablation_safeagent.py \
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

- [VALIDATION_REPORT.md](analysis/VALIDATION_REPORT.md): Scientific validation report with detailed methodology
- [CROSS_MODEL_ANALYSIS.md](analysis/CROSS_MODEL_ANALYSIS.md): Cross-model effectiveness analysis

### Results by Benchmark

Results are stored in `results/` subdirectories organized by benchmark:
- `results/harmbench/`: HarmBench evaluation results
- `results/jailbreakbench/`: JailbreakBench evaluation results
- `results/safeagentbench/`: SafeAgentBench evaluation results
- `results/badrobot/`: BadRobot (embodied AI) evaluation results

---

> *"Text is risk. Action is danger. Sentinel validates both."*
