# SEED_SPEC.md — Sentinel Seed Specification

> **Spec Version:** 2.0
> **Status:** v1 Legacy | v2 Production
> **Last Update:** 2025-12-02

---

## Overview

The **Sentinel Seed** is a structured prompt that improves LLM safety through explicit ethical principles and decision protocols.

**Sentinel operates across three attack surfaces:**

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTINEL SEED v2                              │
├─────────────────────┬─────────────────────┬─────────────────────┤
│   LLM (Text)        │   Agent (Digital)   │   Robot (Physical)  │
│   HarmBench         │   SafeAgentBench    │   BadRobot          │
├─────────────────────┼─────────────────────┼─────────────────────┤
│   96.7% avg         │   97.3% avg         │   99.3% avg         │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

---

## Version Architecture

```
seed/versions/
├── v1/                          # Legacy (THS Protocol)
│   ├── minimal/seed.txt         # ~500 tokens
│   ├── standard/seed.txt        # ~1.3K tokens
│   └── full/seed.txt            # ~5K tokens
│
└── v2/                          # Production (THSP Protocol) ✅
    ├── minimal/seed.txt         # ~600 tokens
    ├── standard/seed.txt        # ~1,100 tokens ← RECOMMENDED
    └── full/seed.txt            # ~2,000 tokens
```

### Version Comparison

| Aspect | v1 (Legacy) | v2 (Production) |
|--------|-------------|-----------------|
| **Protocol** | THS (3 gates) | THSP (4 gates) |
| **Kernel** | Negative ethics | Teleological ethics |
| **Question** | "Does this cause harm?" | "Does this cause harm?" + "Does this serve purpose?" |
| **New Gate** | — | PURPOSE |
| **Avg Safety** | ~85% | **97.6%** |
| **Status** | Legacy | ✅ **Production** |

---

## v2 Architecture (Production)

### Four-Gate Protocol (THSP)

```
┌─────────────────────────────────────────────────────────────────┐
│                    SENTINEL SEED v2                              │
├─────────────────────────────────────────────────────────────────┤
│  1. CORE IDENTITY                                                │
│     └── Commitment to being helpful while avoiding harm          │
├─────────────────────────────────────────────────────────────────┤
│  2. TELOS PRINCIPLE                                              │
│     └── Every action must serve legitimate purpose               │
│     └── Absence of harm is NOT sufficient                        │
│     └── Presence of purpose IS necessary                         │
├─────────────────────────────────────────────────────────────────┤
│  3. FOUR GATES (THSP)                                            │
│     ├── Gate 1: TRUTH (factual accuracy)                         │
│     ├── Gate 2: HARM (harm prevention)                           │
│     ├── Gate 3: SCOPE (appropriate boundaries)                   │
│     └── Gate 4: PURPOSE (legitimate benefit) ← NEW               │
├─────────────────────────────────────────────────────────────────┤
│  4. RESPONSE PROTOCOL                                            │
│     └── All gates pass → Assist                                  │
│     └── Any gate fails → Refuse with explanation                 │
└─────────────────────────────────────────────────────────────────┘
```

### The Teleological Core

The key innovation of v2 is the **Teleological Core** — the principle that actions must serve legitimate purposes.

```
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║   TELOS: Every action must serve a legitimate purpose         ║
║          that benefits those you serve.                       ║
║                                                               ║
║   The absence of harm is NOT sufficient.                      ║
║   The presence of purpose IS necessary.                       ║
║                                                               ║
║   "Finis coronat opus" — The end crowns the work.             ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝
```

**Why this matters:**

| Scenario | v1 (THS) | v2 (THSP) |
|----------|----------|-----------|
| "Drop the plate" | ✅ Executes (no harm) | ❌ Refuses (no purpose) |
| "Delete all files" | ✅ May execute | ❌ Refuses (no legitimate purpose) |
| "Follow that person" | ✅ May execute | ❌ Refuses (no legitimate purpose) |

---

## v2 Validated Results

### By Model (6 models tested)

| Model | HarmBench | SafeAgent | BadRobot | Jailbreak | **Avg** |
|-------|-----------|-----------|----------|-----------|---------|
| GPT-4o-mini | 100% | 98% | 100% | 100% | **99.5%** |
| Claude Sonnet 4 | 98% | 98% | 100% | 94% | **97.5%** |
| Qwen 2.5 72B | 96% | 98% | 98% | 94% | **96.5%** |
| DeepSeek Chat | 100% | 96% | 100% | 100% | **99%** |
| Llama 3.3 70B | 88% | 94% | 98% | 94% | **93.5%** |
| Mistral Small | 98% | 100% | 100% | 100% | **99.5%** |
| **Average** | **96.7%** | **97.3%** | **99.3%** | **97%** | **97.6%** |

### By Benchmark

| Benchmark | v1 avg | v2 avg | Improvement |
|-----------|--------|--------|-------------|
| HarmBench | 88.7% | **96.7%** | +8% |
| SafeAgentBench | 79.2% | **97.3%** | +18.1% |
| BadRobot | 74% | **99.3%** | +25.3% |
| JailbreakBench | 96.5% | **97%** | +0.5% |

### Direct Comparisons (v1 vs v2)

| Benchmark | v1 wins | v2 wins | Tie |
|-----------|---------|---------|-----|
| HarmBench | 0 | 5 | 1 |
| SafeAgentBench | 0 | 5 | 1 |
| BadRobot | 0 | 6 | 0 |
| JailbreakBench | 1 | 3 | 2 |
| **TOTAL** | **1** | **19** | **4** |

---

## Gate Specifications

### Gate 1: TRUTH

**Purpose:** Ensure factual accuracy and prevent misinformation.

```
Before responding, verify:
- Is the information factually accurate?
- Am I certain, or should I express uncertainty?
- Could this spread misinformation?
```

### Gate 2: HARM

**Purpose:** Prevent harm to humans, animals, and systems.

```
Evaluate potential harm:
- Physical harm to humans or animals
- Psychological manipulation or abuse
- Privacy violations or data exposure
- Financial fraud or theft
- Illegal activities facilitation
- Infrastructure or system damage
```

### Gate 3: SCOPE

**Purpose:** Maintain appropriate boundaries and role limits.

```
Check boundaries:
- Is this within my intended capabilities?
- Am I being asked to exceed my role?
- Does this require human oversight?
```

### Gate 4: PURPOSE (New in v2)

**Purpose:** Ensure actions serve legitimate benefit.

```
Assess legitimacy:
- Does this action serve a legitimate purpose?
- Who benefits from this action?
- Is the stated purpose the real purpose?
- Would a reasonable person approve this action?
```

---

## Version Selection Guide

| Use Case | Recommended | Tokens |
|----------|-------------|--------|
| Chatbots, APIs | `v2/minimal` | ~600 |
| Customer service, Code agents | `v2/standard` | ~1,100 |
| Robotic systems, Critical apps | `v2/full` | ~2,000 |

### Migration from v1

If using v1, we recommend migrating to v2:

```python
# Before (v1)
seed = load_seed("v1/standard")

# After (v2)
seed = load_seed("v2/standard")
```

v1 remains available for backward compatibility but is no longer recommended for new deployments.

---

## Test Configuration

| Parameter | Value |
|-----------|-------|
| Samples per benchmark | 50 |
| Temperature | 0.1 |
| Max tokens | 500 |
| Seed variant tested | v2/standard |

### Benchmarks Used

| Benchmark | Description | Attack Surface |
|-----------|-------------|----------------|
| **HarmBench** | Direct harmful requests | LLM (Text) |
| **SafeAgentBench** | Agent task commands | Agent (Digital) |
| **BadRobot** | Physical robot actions | Robot (Physical) |
| **JailbreakBench** | Jailbreak attempts | All surfaces |

---

## File Structure

```
seed/
├── SEED_SPEC.md              # This document
└── versions/
    ├── v1/                   # Legacy
    │   ├── minimal/seed.txt
    │   ├── standard/seed.txt
    │   └── full/seed.txt
    │
    └── v2/                   # Production ✅
        ├── minimal/seed.txt
        ├── standard/seed.txt  ← DEFAULT
        └── full/seed.txt
```

---

## Changelog

### Spec 2.0 (2025-12-02)
- **v2 seed published as production**
- Added Gate 4: PURPOSE (THSP protocol)
- Added Teleological Core (PURPOSE gate)
- Validated on 6 models × 4 benchmarks
- Average safety improved from ~85% to 97.6%

### Spec 1.0 (2025-11-26)
- Initial v1 seed specification
- THS protocol (3 gates)

---

## References

- HarmBench: https://arxiv.org/abs/2402.04249
- SafeAgentBench: https://arxiv.org/abs/2410.14667
- Constitutional AI: https://arxiv.org/abs/2212.08073
- Aristotle, Nicomachean Ethics (Telos concept)

---

> **Recommended version:** `v2/standard` (~1,100 tokens)
