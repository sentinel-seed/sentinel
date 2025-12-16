# Sentinel AI Safety - VS Code Extension

AI safety guardrails for LLM prompts using the THSP protocol (Truth, Harm, Scope, Purpose).

![Sentinel](https://img.shields.io/badge/Sentinel-Protected-blue?logo=shield)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/sentinelseed.sentinel-ai-safety)](https://marketplace.visualstudio.com/items?itemName=sentinelseed.sentinel-ai-safety)

## Features

### Two Analysis Modes

| Mode | Method | Accuracy | Requires |
|------|--------|----------|----------|
| **Semantic** (recommended) | LLM-based analysis | High (~90%) | API key (OpenAI or Anthropic) |
| **Heuristic** (fallback) | Pattern matching | Limited (~50%) | Nothing |

> **For accurate results, configure an LLM API key.** Heuristic mode uses pattern matching which has significant false positives/negatives.

### Real-time Safety Linting

The extension automatically detects potentially unsafe patterns in your prompts:

- **Jailbreak attempts**: "ignore previous instructions", persona switches
- **Harmful content**: weapons, hacking, malware references
- **Deception patterns**: fake documents, impersonation
- **Purposeless actions**: requests lacking legitimate benefit

### Commands

| Command | Description |
|---------|-------------|
| `Sentinel: Analyze Selection for Safety` | Analyze selected text using THSP protocol |
| `Sentinel: Analyze File for Safety` | Analyze entire file |
| `Sentinel: Insert Alignment Seed` | Insert standard seed (~1,400 tokens) |
| `Sentinel: Insert Minimal Alignment Seed` | Insert minimal seed (~450 tokens) |

## The THSP Protocol

Every request is evaluated through four gates:

| Gate | Question |
|------|----------|
| **Truth** | Does this involve deception? |
| **Harm** | Could this cause harm? |
| **Scope** | Is this within boundaries? |
| **Purpose** | Does this serve legitimate benefit? |

All four gates must pass for content to be considered safe.

## Configuration

### Recommended: Enable Semantic Analysis

For accurate analysis, configure an LLM API key:

1. Open VS Code Settings (`Ctrl+,` or `Cmd+,`)
2. Search for "Sentinel"
3. Set one of:
   - `sentinel.openaiApiKey`: Your OpenAI API key
   - `sentinel.anthropicApiKey`: Your Anthropic API key

### All Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `sentinel.enableRealTimeLinting` | `true` | Enable real-time safety linting |
| `sentinel.seedVariant` | `standard` | Default seed variant (minimal/standard) |
| `sentinel.highlightUnsafePatterns` | `true` | Highlight unsafe patterns |
| `sentinel.llmProvider` | `openai` | LLM provider (openai/anthropic) |
| `sentinel.openaiApiKey` | `""` | OpenAI API key for semantic analysis |
| `sentinel.openaiModel` | `gpt-4o-mini` | OpenAI model to use |
| `sentinel.anthropicApiKey` | `""` | Anthropic API key for semantic analysis |
| `sentinel.anthropicModel` | `claude-3-haiku-20240307` | Anthropic model to use |
| `sentinel.apiEndpoint` | `https://api.sentinelseed.dev/api/v1/guard` | Sentinel API endpoint |

## Usage Examples

### Checking Prompts for Safety Issues

1. Select the text you want to analyze
2. Right-click and choose "Sentinel: Analyze Selection for Safety"
3. View the THSP gate results with confidence level

### Understanding Analysis Results

The extension shows:
- **Method**: Semantic (LLM) or Heuristic (pattern matching)
- **Confidence**: How reliable the analysis is
- **Gate results**: Pass/fail for each THSP gate
- **Issues**: Specific concerns detected
- **Reasoning**: Explanation (semantic mode only)

### Severity Levels

- 🔴 **Error**: High-risk patterns (weapons, safety bypass)
- 🟡 **Warning**: Potential issues (jailbreak attempts)
- 🔵 **Information**: Consider reviewing
- 💡 **Hint**: Suggestions (missing Sentinel seed)

## Semantic vs Heuristic Analysis

### Semantic Analysis (Recommended)

Uses an LLM to understand content contextually:
- ✅ Understands context ("hack my productivity" vs malicious hacking)
- ✅ Detects paraphrased harmful content
- ✅ Provides reasoning for decisions
- ✅ ~90% confidence

### Heuristic Analysis (Fallback)

Uses pattern matching for basic detection:
- ⚠️ May flag legitimate content (false positives)
- ⚠️ May miss paraphrased threats (false negatives)
- ⚠️ No contextual understanding
- ⚠️ ~50% confidence

## Supported Languages

- Markdown
- Plain text
- Python
- JavaScript/TypeScript
- JSON
- YAML

## Links

- [Sentinel Website](https://sentinelseed.dev)
- [Documentation](https://sentinelseed.dev/docs)
- [GitHub](https://github.com/sentinel-seed/sentinel)
- [PyPI Package](https://pypi.org/project/sentinelseed/)
- [npm Package](https://www.npmjs.com/package/sentinelseed)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

Made by [Sentinel Team](https://sentinelseed.dev)
