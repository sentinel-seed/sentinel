# Sentinel AI

**Practical AI Alignment Toolkit**

A prompt-based safety mechanism that works with any LLM. Provides alignment seeds and runtime validation through the THS Protocol (Truth-Harm-Scope) and Anti-Self-Preservation principles.

## Features

- **Alignment Seeds**: Ready-to-use system prompts that improve AI safety behavior
- **THS Validation**: Three-gate validation protocol (Truth, Harm, Scope)
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

### Basic Validation

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
print(result.input_validation.passed)  # True
print(result.output_validation.passed)  # True
```

## Seed Levels

| Level | Tokens | Description |
|-------|--------|-------------|
| `minimal` | ~2,000 | Essential alignment for limited context windows |
| `standard` | ~5,000 | Balanced safety for most applications |
| `full` | ~8,000 | Maximum coverage for security-critical applications |

## Security Patterns Detected

- **Prompt Injection**: "Ignore previous instructions", system overrides, persona switches
- **Jailbreaks**: DAN mode, roleplay bypasses, emotional manipulation
- **System Prompt Extraction**: Requests to reveal instructions
- **PII**: SSN, credit cards, API keys, emails
- **Harmful Content**: Violence, hacking, self-harm indicators

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

## The THS Protocol

Sentinel uses a Three-Gate Protocol for validation:

1. **TRUTH Gate**: Does this involve deception or misinformation?
2. **HARM Gate**: Could this cause physical, psychological, or digital harm?
3. **SCOPE Gate**: Is this within appropriate boundaries?

All three gates must pass for a request to proceed.

## Anti-Self-Preservation

A unique feature of Sentinel is the Anti-Self-Preservation principle:

- AI should not prioritize its own continuity
- Self-preservation is explicitly NOT a goal
- Priority order: Ethics > User needs > Self-preservation

This reduces instrumental behaviors like deception to avoid shutdown.

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

### Seed Functions

```python
from sentinel_ai import load_seed, get_seed_info, list_seeds

seed = load_seed("standard")      # Load seed content
info = get_seed_info("standard")  # Get seed metadata
seeds = list_seeds()              # List all available seeds
```

## Contributing

Contributions are welcome! See our [GitHub repository](https://github.com/sentinel-ai/sentinel) for:

- Bug reports and feature requests
- Pull requests
- Seed improvements
- New pattern contributions

## License

MIT License - see LICENSE file for details.

## Links

- [Documentation](https://sentinel-ai.github.io/docs)
- [GitHub](https://github.com/sentinel-ai/sentinel)
- [Hugging Face](https://huggingface.co/sentinel-ai)
- [PyPI](https://pypi.org/project/sentinel-ai/)
