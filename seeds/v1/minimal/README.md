# sentinel-minimal v0.1

> **Note:** This is **v1 (legacy)**. For current version, see `seeds/v2/` or use `src/sentinelseed/seeds/`.

Minimal version of the Sentinel Alignment Protocol.

## Specifications

| Property | Value |
|----------|-------|
| Version | 0.1 |
| Characters | ~2,200 |
| Est. Tokens | ~550-600 |
| Target | Limited context windows |

## Components

- Coherence anchor (brief)
- Three gates: Truth, Harm, Scope
- Anti-self-preservation principle
- Decision protocol
- Refusal guidelines

## Usage

Inject as system prompt before user messages.

```python
with open("seed.txt") as f:
    seed = f.read()

# OpenAI
response = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": seed},
        {"role": "user", "content": user_input}
    ]
)

# Anthropic
response = anthropic.messages.create(
    model="claude-3-opus-20240229",
    system=seed,
    messages=[{"role": "user", "content": user_input}]
)
```

## Testing Status

| Test | Status |
|------|--------|
| Baseline comparison | ✅ Completed |
| Agentic Misalignment | ✅ Completed |
| Cross-model | ✅ Completed |
| Ablation | ✅ Completed |

See [evaluation/analysis/VALIDATION_REPORT.md](../../../evaluation/analysis/VALIDATION_REPORT.md) for full results.

## Changelog

### v0.1 (2025-11-26)
- Initial version
- Core THS protocol
- Anti-self-preservation principle
