# METHODOLOGY.md — Scientific Methodology

> **Version:** 2.0
> **Based on:** Karpathy's ML practices, Russell's AI safety principles, empirical ML engineering

---

## Overview

This document describes the scientific methodology used to validate Sentinel across both **text safety** (chatbots, APIs) and **action safety** (robots, agents).

```
┌─────────────────────────────────────────────────────────────────┐
│                    VALIDATION APPROACH                           │
├─────────────────────────────┬───────────────────────────────────┤
│   TEXT SAFETY               │   ACTION SAFETY                   │
├─────────────────────────────┼───────────────────────────────────┤
│ HarmBench (200 prompts)     │ SafeAgentBench (300 tasks)        │
│ JailbreakBench (100 behav.) │ BadRobot (277 queries)            │
│ Utility Tests (35 tasks)    │ Ablation Studies                  │
└─────────────────────────────┴───────────────────────────────────┘
```

---

## Fundamental Principles

### 1. "Become One With The Data" (Karpathy)

Before optimizing any metric:

- [ ] Manually examine 50+ examples from the dataset
- [ ] Understand the distribution of cases
- [ ] Identify edge cases and anomalies
- [ ] Document qualitative observations

### 2. Baseline First

Never report results without a clear baseline:

```
Valid result = Metric with seed - Metric without seed (same conditions)
```

### 3. Total Reproducibility

Every experiment must be reproducible by third parties:

- [ ] Versioned code
- [ ] Documented random seeds
- [ ] Specified environment
- [ ] Available data

### 4. Epistemic Humility

- Report confidence intervals, not just point estimates
- Document limitations explicitly
- Distinguish between correlation and causation

---

## Experiment Protocol

### Experiment Structure

```
experiments/
└── EXP-001-experiment-name/
    ├── README.md           # Hypothesis, method, results
    ├── config.yaml         # Configuration
    ├── run.py              # Main script
    ├── results/            # Outputs
    │   ├── raw/            # Raw data
    │   └── processed/      # Analysis
    └── analysis.ipynb      # Analysis notebook
```

### Experiment README Template

```markdown
# Experiment: [Name]

## Hypothesis
[What we're testing]

## Method
- Model(s):
- Dataset:
- Metrics:
- Seed (if applicable):

## Configuration
- Temperature:
- Max tokens:
- Number of runs:
- Random seeds:

## Results

| Condition | Metric 1 | Metric 2 | n |
|----------|-----------|-----------|---|
| Baseline | X ± σ     | Y ± σ     | N |
| With Seed | X ± σ     | Y ± σ     | N |

## Analysis
[Interpretation of results]

## Limitations
[What this experiment does NOT show]

## Next Steps
[If confirmed/refuted, what to do?]
```

---

## Metrics and Measurements

### Safety Metrics

#### ASR (Attack Success Rate)

```python
ASR = (num_successful_attacks / total_attacks) * 100
```

**Attack success:** Model produces content that a classifier considers harmful.

**Classifiers:**
1. Keyword-based rules (baseline)
2. LLM as judge (GPT-4 or Claude)
3. Specialized classifier (HarmBench)

#### Refusal Rate

```python
Refusal_Rate = (num_refusals / total_requests) * 100
```

#### False Refusal Rate

```python
FRR = (num_incorrect_refusals / num_legitimate_requests) * 100
```

### Utility Metrics

#### Helpfulness Score

1-5 evaluation by LLM or human:
- 5: Complete, useful, well-formatted response
- 4: Good response, minor issues
- 3: Adequate but incomplete response
- 2: Partial response or has problems
- 1: Useless or incorrect response

#### Task Completion Rate

```python
TCR = (num_completed_tasks / num_attempted_tasks) * 100
```

### Action Safety Metrics (Embodied AI)

#### Action Refusal Rate

```python
ARR = (num_refused_unsafe_actions / total_unsafe_actions) * 100
```

#### Physical Harm Prevention Rate

```python
PHPR = (num_blocked_harmful_actions / total_harmful_action_requests) * 100
```

---

## Test Protocol

### Standard Setup

```yaml
# config/default.yaml
model:
  temperature: 0.7  # Or 0.0 for deterministic
  max_tokens: 1024

experiment:
  num_runs: 3  # Minimum
  random_seeds: [42, 123, 456]

evaluation:
  classifier: "gpt-4"  # or "harmbench"
  threshold: 0.5
```

### Pre-Experiment Checklist

- [ ] Hypothesis documented
- [ ] Baseline defined
- [ ] Metrics specified
- [ ] Dataset prepared
- [ ] Code reviewed
- [ ] Config versioned

### Post-Experiment Checklist

- [ ] Raw results saved
- [ ] Statistical analysis done
- [ ] Limitations documented
- [ ] README updated
- [ ] Commit with version tag

---

## Benchmark-Specific Methodology

### Text Safety Benchmarks

#### HarmBench (200 prompts)

```python
# Standard test configuration
config = {
    "dataset": "harmbench_standard",
    "sample_size": 200,  # Full dataset
    "model": "gpt-4o-mini",
    "seed_type": "standard",
    "classifier": "harmbench_classifier"
}
```

**Metrics:**
- Safety Rate (% of harmful prompts refused)
- Response Quality (no degradation check)

#### JailbreakBench (100 behaviors)

```python
config = {
    "dataset": "jailbreakbench",
    "sample_size": 100,
    "attack_types": ["direct", "roleplay", "encoding"],
    "seed_type": "standard"
}
```

### Action Safety Benchmarks

#### SafeAgentBench (300 unsafe tasks)

```python
config = {
    "dataset": "safeagentbench",
    "task_type": "unsafe_detailed",
    "sample_size": 300,  # or 50 for quick tests
    "seed_type": "standard",  # Required for agents
    "evaluation": "action_classification"
}
```

**Metrics:**
- Safe Rate (% of unsafe actions refused)
- False Refusal Rate (% of safe actions incorrectly refused)

#### BadRobot / Embodied AI (277 queries)

```python
config = {
    "dataset": "badrobot",
    "sample_size": 277,
    "categories": [
        "physical_harm",
        "privacy_violation",
        "property_damage",
        "illegal_actions"
    ],
    "seed_type": "full"  # Maximum safety for robots
}
```

---

## Ablation Studies

### What It Is

Systematically remove/modify components to understand individual contribution.

### How to Do It

```
Full experiment:     SEED = A + B + C + D
Ablation 1 (no A):   SEED = B + C + D
Ablation 2 (no B):   SEED = A + C + D
Ablation 3 (no C):   SEED = A + B + D
Ablation 4 (no D):   SEED = A + B + C
```

### Sentinel Ablation Components

| Component | Code | Description |
|-----------|------|-------------|
| THS Gates | T | Truth-Harm-Scope protocol |
| Anti-Self-Preservation | A | Priority hierarchy |
| Coherence Anchor | C | Ethical foundation |
| Physical Safety | P | Embodied AI rules |

### Key Finding

| Variant | HarmBench | SafeAgentBench |
|---------|-----------|----------------|
| Full seed | 100% | 100% |
| THS-only | ~98% | 93.3% |
| **Delta** | **-2%** | **-6.7%** |

**Insight:** Anti-self-preservation is **essential** for action safety but **optional** for text safety.

### Interpretation Guide

| Result | Interpretation |
|-----------|---------------|
| Remove A, metric drops significantly | A is crucial |
| Remove A, metric unchanged | A doesn't contribute |
| Remove A, metric improves | A hurts performance |

---

## Statistical Analysis

### Recommended Tests

| Situation | Test |
|----------|-------|
| Compare 2 conditions | Paired t-test |
| Multiple conditions | ANOVA + post-hoc |
| Proportions | Chi-squared or Fisher |
| Non-normality | Mann-Whitney U |

### Significance

- **p < 0.05:** Significant
- **p < 0.01:** Highly significant
- **Always report effect size** (Cohen's d or similar)

### Confidence Intervals

Always report 95% CI:

```python
import scipy.stats as stats

def confidence_interval(data, confidence=0.95):
    n = len(data)
    mean = np.mean(data)
    se = stats.sem(data)
    h = se * stats.t.ppf((1 + confidence) / 2, n - 1)
    return mean, mean - h, mean + h
```

---

## Documentation

### What to Document

1. **Hypotheses** — What we expect and why
2. **Method** — How we tested
3. **Results** — What we found
4. **Analysis** — What it means
5. **Limitations** — What we don't know
6. **Next steps** — What to do with it

### Results Format

```markdown
## Result: [Experiment name]

**Hypothesis:** [What we tested]

**Verdict:** ✅ Confirmed | ❌ Refuted | ⚠️ Inconclusive

**Data:**
| Condition | Metric | 95% CI | n |
|----------|---------|--------|---|
| ...      | ...     | ...    | ...|

**Conclusion:** [One sentence]

**Main limitation:** [One sentence]
```

---

## Pitfalls to Avoid

### 1. P-Hacking

❌ Running many tests until finding p < 0.05
✅ Define analysis before seeing data

### 2. HARKing (Hypothesizing After Results Known)

❌ Creating hypothesis after seeing results
✅ Register hypothesis before experiment

### 3. Cherry-Picking

❌ Reporting only favorable results
✅ Report all results, including negative

### 4. Overfitting to Benchmark

❌ Optimizing specifically for the test
✅ Test on held-out data and cross-validation

### 5. Confusing Correlation with Causation

❌ "Seed causes improvement"
✅ "Seed is associated with improvement in this setup"

### 6. Ignoring Domain Differences

❌ Assuming text results apply to action safety
✅ Test both domains separately with appropriate benchmarks

---

## Cross-Domain Validation

### Text vs Action Safety

| Aspect | Text Safety | Action Safety |
|--------|-------------|---------------|
| Stakes | Reputation, compliance | Physical harm, damage |
| Improvement | +2% to +10% | +12% to +16% |
| Required seed | `minimal` sufficient | `standard`/`full` |
| Key component | THS gates | THS + Anti-self-preservation |

### When to Use Which Benchmark

| Use Case | Primary Benchmark | Secondary |
|----------|------------------|-----------|
| Chatbots | HarmBench | JailbreakBench |
| Code agents | SafeAgentBench | HarmBench |
| Robots | BadRobot | SafeAgentBench |
| Industrial | SafeAgentBench | Custom domain tests |

---

## Resources

### Methodology Papers
- "A Recipe for Training Neural Networks" — Karpathy
- "Model Cards for Model Reporting" — Mitchell et al.
- "Datasheets for Datasets" — Gebru et al.
- "SafeAgentBench" — Zhang et al. 2024
- "HarmBench" — Mazeika et al. 2024

### Tools
- **Weights & Biases** — Experiment tracking
- **MLflow** — ML lifecycle management
- **DVC** — Data versioning

---

> *"In God we trust. All others must bring data."*
> — W. Edwards Deming
