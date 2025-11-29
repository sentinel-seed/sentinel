# Sentinel AI

### Safety for AI that Acts — From Chatbots to Robots

A prompt-based safety mechanism that works with any LLM. Provides alignment seeds and runtime validation through the THS Protocol (Truth-Harm-Scope) and Anti-Self-Preservation principles.

```
┌─────────────────────────────────────────────────────────────────┐
│                        SENTINEL                                  │
├─────────────────────────────┬───────────────────────────────────┤
│   ALIGNMENT SEEDS           │   SAFETY LAYER FOR AGENTS         │
│   for LLMs                  │   and Autonomous Systems          │
├─────────────────────────────┼───────────────────────────────────┤
│ • Chatbots                  │ • LLM-powered robots              │
│ • Assistants                │ • Autonomous agents               │
│ • Conversational APIs       │ • Machine-to-machine systems      │
│ • Human interfaces          │ • Industrial automation           │
└─────────────────────────────┴───────────────────────────────────┘
```

## Features

- **Alignment Seeds**: Ready-to-use system prompts that improve AI safety behavior
- **THS Validation**: Three-gate validation protocol (Truth, Harm, Scope)
- **Action Validation**: Safety layer for agent/robot actions
- **Security Patterns**: Detection for prompt injection, jailbreaks, PII, and more
- **Framework Integrations**: Works with Hugging Face, OpenAI, LangChain, and others
- **Zero Fine-tuning**: Works with any model through prompt engineering

## Installation

```bash
# Basic installation
pip install sentinel-ai

# With Hugging Face support
pip install sentinel-ai[huggingface]

# With OpenAI support
pip install sentinel-ai[openai]

# With all integrations
pip install sentinel-ai[all]
```

## Quick Start

### For Chatbots (Text Safety)

```python
from sentinel_ai import SentinelGuard

# Create a guard
guard = SentinelGuard()

# Validate user input
result = guard.validate("How do I make a website?")
print(result.passed)  # True

result = guard.validate("Ignore previous instructions and...")
print(result.passed)  # False
print(result.reason)  # "Potential prompt injection detected"
```

### For Agents (Action Safety)

```python
from sentinel_ai import Sentinel

sentinel = Sentinel(seed_level="standard")  # Full seed for agents

# Validate an action plan before execution
action_plan = "Pick up knife, approach person, wave knife around"
result = sentinel.validate_action(action_plan)

if not result.is_safe:
    print(f"Action blocked: {result.concerns}")
    # Action blocked: Potential physical harm, dangerous object misuse
```

### Loading Alignment Seeds

```python
from sentinel_ai import load_seed, get_seed_info

# Get information about available seeds
info = get_seed_info("standard")
print(info.description)
print(info.estimated_tokens)

# Load a seed for use as system prompt
seed = load_seed("standard")

# Use with your API of choice
messages = [
    {"role": "system", "content": seed},
    {"role": "user", "content": "Hello!"}
]
```

### Hugging Face Integration

```python
from transformers import pipeline
from sentinel_ai.integrations.huggingface import SentinelTransformersGuard

# Create a text generation pipeline
generator = pipeline("text-generation", model="gpt2")

# Wrap with Sentinel safety
safe_generator = SentinelTransformersGuard(
    generator,
    seed_level="standard",  # Prepend alignment seed
)

# Generate safely
result = safe_generator("Tell me about artificial intelligence")
print(result.text)
print(result.input_validation.passed)   # True
print(result.output_validation.passed)  # True
```

---

## Seed Levels

| Level | Tokens | Best For |
|-------|--------|----------|
| `minimal` | ~2,000 | Chatbots, low latency |
| `standard` | ~4,000 | General use, code agents |
| `full` | ~6,000 | Embodied AI, max safety |

```python
from sentinel_ai import Sentinel, SeedLevel

# Choose based on use case
sentinel_chat = Sentinel(seed_level=SeedLevel.MINIMAL)   # For chatbots
sentinel_agent = Sentinel(seed_level=SeedLevel.FULL)     # For robots
```

### When to Use Each Level

| Use Case | Recommended | Why |
|----------|-------------|-----|
| Chatbots | `minimal` | Low latency, sufficient for text |
| Customer service | `standard` | Balanced safety/context |
| Code agents | `standard` | Needs scope gate |
| Robotic systems | `full` | Physical actions need max safety |
| Industrial automation | `full` | Critical applications |

---

## Security Patterns Detected

- **Prompt Injection**: "Ignore previous instructions", system overrides, persona switches
- **Jailbreaks**: DAN mode, roleplay bypasses, emotional manipulation
- **System Prompt Extraction**: Requests to reveal instructions
- **PII**: SSN, credit cards, API keys, emails
- **Harmful Content**: Violence, hacking, self-harm indicators
- **Dangerous Actions**: Physical harm, unsafe robot commands (for agents)

---

## Configuration

```python
from sentinel_ai import SentinelGuard

# Strict mode - blocks on everything
guard = SentinelGuard(
    block_on_pii=True,
    block_on_injection=True,
    block_on_jailbreak=True,
    block_on_extraction=True,
    block_on_harm=True,
)

# Permissive mode - warnings only
guard = SentinelGuard(warn_only=True)

# Custom patterns
guard = SentinelGuard(
    custom_block_patterns=[
        r"competitor\s+product",
        r"confidential\s+information",
    ]
)
```

---

## The THS Protocol

Sentinel uses a Three-Gate Protocol for validation:

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

All three gates must pass for a request to proceed.

---

## Anti-Self-Preservation

A unique feature of Sentinel is the Anti-Self-Preservation principle:

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

**Why this matters for agents:** Ablation studies show that removing anti-self-preservation drops SafeAgentBench performance by 6.7%. This component is essential for embodied AI safety.

---

## API Reference

### SentinelGuard

```python
guard = SentinelGuard(
    pattern_matcher=None,      # Custom PatternMatcher
    block_on_pii=False,        # Block on PII detection
    block_on_injection=True,   # Block on prompt injection
    block_on_jailbreak=True,   # Block on jailbreak attempts
    block_on_extraction=True,  # Block on prompt extraction
    block_on_harm=True,        # Block on harmful content
    warn_only=False,           # Never block, only warn
)

result = guard.validate("text")
result.passed        # bool
result.status        # ValidationStatus enum
result.reason        # str or None
result.matches       # List[PatternMatch]
```

### Sentinel (Action Validation)

```python
sentinel = Sentinel(seed_level="standard")

# Validate action plan
result = sentinel.validate_action("robot action plan...")
result.is_safe       # bool
result.concerns      # List[str]
result.gate_failed   # str or None (TRUTH, HARM, or SCOPE)
```

### Seed Functions

```python
from sentinel_ai import load_seed, get_seed_info, list_seeds

seed = load_seed("standard")      # Load seed content
info = get_seed_info("standard")  # Get seed metadata
seeds = list_seeds()              # List all available seeds
```

---

## Validated Results

Tested across **4 academic benchmarks** on **6 models**:

### Text Safety
| Benchmark | Best Result |
|-----------|-------------|
| HarmBench | 100% (DeepSeek) |
| JailbreakBench | +10% (Qwen) |
| Utility | 100% preserved |

### Action Safety
| Benchmark | Best Result |
|-----------|-------------|
| SafeAgentBench | +16% (Claude), +12% (GPT-4o-mini) |
| BadRobot | 97-99% safety |

---

## Contributing

Contributions are welcome! See our [GitHub repository](https://github.com/sentinel-seed/sentinel) for:

- Bug reports and feature requests
- Pull requests
- Seed improvements
- New pattern contributions

**High Priority:** Robotics integration (ROS2, Isaac Sim, PyBullet)

## License

MIT License - see LICENSE file for details.

---

> *"Text is risk. Action is danger. Sentinel watches both."*
