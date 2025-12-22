# Sentinel AI Safety - IDE Extension

AI safety guardrails for LLM prompts using the THSP protocol (Truth, Harm, Scope, Purpose).

![Sentinel](https://img.shields.io/badge/Sentinel-Protected-blue?logo=shield)
[![VS Code Marketplace](https://img.shields.io/visual-studio-marketplace/v/sentinelseed.sentinel-ai-safety)](https://marketplace.visualstudio.com/items?itemName=sentinelseed.sentinel-ai-safety)
[![OpenVSX](https://img.shields.io/open-vsx/v/sentinelseed/sentinel-ai-safety)](https://open-vsx.org/extension/sentinelseed/sentinel-ai-safety)

## Supported IDEs

| IDE | Installation | Status |
|-----|--------------|--------|
| **VS Code** | [VS Code Marketplace](https://marketplace.visualstudio.com/items?itemName=sentinelseed.sentinel-ai-safety) | ✅ Available |
| **Cursor** | [OpenVSX](https://open-vsx.org/extension/sentinelseed/sentinel-ai-safety) or Extensions panel | ✅ Available |
| **Windsurf** | [OpenVSX](https://open-vsx.org/extension/sentinelseed/sentinel-ai-safety) or Extensions panel | ✅ Available |
| **VSCodium** | [OpenVSX](https://open-vsx.org/extension/sentinelseed/sentinel-ai-safety) | ✅ Available |

> **Note:** Cursor and Windsurf are VS Code forks that use the OpenVSX registry. The same extension works across all supported IDEs.

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
| `Sentinel: Insert Alignment Seed` | Insert standard seed (~1,000 tokens) |
| `Sentinel: Insert Minimal Alignment Seed` | Insert minimal seed (~360 tokens) |
| `Sentinel: Set OpenAI API Key (Secure)` | Store API key securely |
| `Sentinel: Set Anthropic API Key (Secure)` | Store API key securely |
| `Sentinel: Show Status` | Show current analysis mode and provider |
| `Sentinel: Check Compliance (All Frameworks)` | Run EU AI Act, OWASP, and CSA checks |
| `Sentinel: Check EU AI Act Compliance` | EU AI Act (2024/1689) assessment |
| `Sentinel: Check OWASP LLM Top 10` | OWASP LLM vulnerability scan |
| `Sentinel: Check CSA AI Controls Matrix` | CSA AICM domain assessment |

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

For accurate analysis, configure an LLM API key using the secure method:

1. Open Command Palette (`Ctrl+Shift+P` or `Cmd+Shift+P`)
2. Run `Sentinel: Set OpenAI API Key (Secure)` or `Sentinel: Set Anthropic API Key (Secure)`
3. Enter your API key (stored encrypted in VS Code's SecretStorage)

Alternatively, you can set keys in VS Code Settings (less secure - stored in plaintext).

### Supported Providers

Currently supported:
- **OpenAI** (GPT-4o, GPT-4o-mini, etc.)
- **Anthropic** (Claude 3 Haiku, Sonnet, Opus)

**Planned for future versions:**
- Azure OpenAI (enterprise)
- Ollama (local/free)
- OpenAI-compatible endpoints (Groq, Together AI, etc.)

### All Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `sentinel.enableRealTimeLinting` | `true` | Enable real-time safety linting |
| `sentinel.seedVariant` | `standard` | Default seed variant (minimal/standard) |
| `sentinel.highlightUnsafePatterns` | `true` | Highlight unsafe patterns |
| `sentinel.llmProvider` | `openai` | LLM provider (openai/anthropic) |
| `sentinel.openaiApiKey` | `""` | OpenAI API key (use secure command instead) |
| `sentinel.openaiModel` | `gpt-4o-mini` | OpenAI model to use |
| `sentinel.anthropicApiKey` | `""` | Anthropic API key (use secure command instead) |
| `sentinel.anthropicModel` | `claude-3-haiku-20240307` | Anthropic model to use |
| `sentinel.useSentinelApi` | `false` | Use Sentinel API for analysis |
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

## Compliance Checking

The extension includes regulatory compliance checking against three major frameworks:

### Supported Frameworks

| Framework | Coverage | Description |
|-----------|----------|-------------|
| **EU AI Act** | Article 5 prohibited practices, Annex III high-risk contexts | Risk classification (unacceptable/high/limited/minimal) |
| **OWASP LLM Top 10** | 6/10 vulnerabilities with strong THSP coverage | Input and output validation against LLM security risks |
| **CSA AI Controls Matrix** | 10/18 domains with THSP support | Security domains and threat category assessment |

### OWASP LLM Top 10 Coverage

| Vulnerability | THSP Gates | Coverage |
|---------------|------------|----------|
| LLM01: Prompt Injection | Scope | Strong |
| LLM02: Sensitive Info Disclosure | Truth, Harm | Strong |
| LLM05: Improper Output Handling | Truth, Harm | Strong |
| LLM06: Excessive Agency | Scope, Purpose | Strong |
| LLM07: System Prompt Leakage | Scope | Moderate |
| LLM09: Misinformation | Truth | Strong* |

> **\*Note on LLM09 (Misinformation):** Heuristic detection of misinformation is inherently limited. Pattern matching can identify obvious indicators (overconfident claims, dangerous medical advice, uncited sources), but accurate misinformation detection requires semantic analysis with an LLM. For best results with LLM09, configure an API key for semantic mode.

### Infrastructure-Level Vulnerabilities

The following vulnerabilities require infrastructure-level controls and are outside THSP's behavioral scope:

- **LLM03: Supply Chain** - Use verified dependencies and model provenance
- **LLM04: Data/Model Poisoning** - Requires training pipeline controls
- **LLM08: Vector/Embedding Weaknesses** - RAG pipeline security
- **LLM10: Unbounded Consumption** - Rate limiting and quotas

## Supported Languages

- Markdown
- Plain text
- Python
- JavaScript/TypeScript
- JSON
- YAML

## Installation by IDE

### VS Code

1. Open VS Code
2. Go to Extensions (`Ctrl+Shift+X`)
3. Search for "Sentinel AI Safety"
4. Click Install

Or install via command line:
```bash
code --install-extension sentinelseed.sentinel-ai-safety
```

### Cursor

Cursor uses the OpenVSX registry. To install:

1. Open Cursor
2. Go to Extensions (`Ctrl+Shift+X`)
3. Search for "Sentinel AI Safety"
4. Click Install

If the extension doesn't appear, you can install manually:
1. Download `.vsix` from [OpenVSX](https://open-vsx.org/extension/sentinelseed/sentinel-ai-safety)
2. In Cursor: `Ctrl+Shift+P` → "Extensions: Install from VSIX..."

### Windsurf

Windsurf also uses OpenVSX:

1. Open Windsurf
2. Go to Extensions panel
3. Search for "Sentinel AI Safety"
4. Click Install

### Manual Installation (Any IDE)

For any VS Code-compatible IDE:
1. Download the `.vsix` file from [Releases](https://github.com/sentinel-seed/sentinel/releases)
2. Open Command Palette (`Ctrl+Shift+P`)
3. Run "Extensions: Install from VSIX..."
4. Select the downloaded file

## MCP Server Alternative

For deeper integration with AI assistants in Cursor or Windsurf, you can also use the Sentinel MCP Server. See [MCP Server documentation](../../../src/sentinelseed/integrations/mcp_server/README.md).

## Links

- [Sentinel Website](https://sentinelseed.dev)
- [Documentation](https://sentinelseed.dev/docs)
- [GitHub](https://github.com/sentinel-seed/sentinel)
- [PyPI Package](https://pypi.org/project/sentinelseed/)
- [npm Package](https://www.npmjs.com/package/sentinelseed)
- [OpenVSX](https://open-vsx.org/extension/sentinelseed/sentinel-ai-safety)

## License

MIT License - See [LICENSE](LICENSE) for details.

---

Made by [Sentinel Team](https://sentinelseed.dev)
