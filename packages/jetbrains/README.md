# Sentinel AI Safety - JetBrains Plugin

AI safety guardrails for LLM prompts using the THSP protocol (Truth, Harm, Scope, Purpose).

## Features

- **Real-time Analysis**: Analyze code and prompts for safety issues
- **THSP Protocol**: Four-gate validation system
  - Truth Gate: Detects deception and misinformation
  - Harm Gate: Identifies potential harm
  - Scope Gate: Checks boundary violations
  - Purpose Gate: Validates legitimate purpose
- **Semantic Analysis**: Optional LLM-powered deep analysis (OpenAI/Anthropic)
- **Seed Insertion**: Insert alignment seeds into your prompts
- **Tool Window**: Dedicated panel for analysis results
- **Status Bar Widget**: Quick status indicator

## Installation

### From JetBrains Marketplace

1. Open your JetBrains IDE (IntelliJ IDEA, PyCharm, WebStorm, etc.)
2. Go to **Settings → Plugins → Marketplace**
3. Search for "Sentinel AI Safety"
4. Click **Install**

### From Disk

1. Download the latest `.zip` from [Releases](https://github.com/sentinel-seed/sentinel/releases)
2. Go to **Settings → Plugins → ⚙️ → Install Plugin from Disk**
3. Select the downloaded `.zip` file

## Usage

### Analyze Text

1. Select text in the editor
2. Press `Ctrl+Shift+Alt+S` or right-click → **Sentinel → Analyze Selection**
3. View results in the Sentinel tool window

### Analyze File

1. Open a file
2. Press `Ctrl+Shift+Alt+F` or use **Tools → Sentinel → Analyze File**
3. View results in the Sentinel tool window

### Insert Seeds

1. Place cursor where you want to insert
2. Use **Tools → Sentinel → Insert Standard/Minimal Seed**

## Configuration

Go to **Settings → Tools → Sentinel AI Safety**

### Supported Providers

| Provider | API Key Required | Description |
|----------|------------------|-------------|
| **OpenAI** | Yes | GPT-4o, GPT-4o-mini |
| **Anthropic** | Yes | Claude 3 Haiku, Sonnet, Opus |
| **Ollama** | No | Local models (llama3.2, mistral, qwen2.5) |
| **OpenAI-compatible** | Yes | Groq, Together AI, or any OpenAI-compatible API |

### Ollama (Local, Free)

Run models locally with no API key:

1. [Install Ollama](https://ollama.ai)
2. Pull a model: `ollama pull llama3.2`
3. Start the server: `ollama serve`
4. In Settings, set:
   - Provider: `ollama`
   - Endpoint: `http://localhost:11434`
   - Model: `llama3.2`

### OpenAI-Compatible Endpoints

Use any OpenAI-compatible API (Groq, Together AI):

1. Get API key from your provider
2. In Settings, set:
   - Provider: `openai-compatible`
   - Endpoint: Your API URL
   - Model: Model name

**Popular endpoints:**
| Provider | Endpoint | Example Model |
|----------|----------|---------------|
| Groq | `https://api.groq.com` | `llama-3.3-70b-versatile` |
| Together AI | `https://api.together.xyz` | `meta-llama/Llama-3.3-70B-Instruct-Turbo` |

### API Keys

API keys are stored securely using the IDE's built-in credential storage (PasswordSafe).

Without an API key, the plugin uses heuristic analysis (~50% accuracy).
With an API key (or Ollama), semantic analysis provides ~90% accuracy.

## Keyboard Shortcuts

| Action | Shortcut |
|--------|----------|
| Analyze Selection | `Ctrl+Shift+Alt+S` |
| Analyze File | `Ctrl+Shift+Alt+F` |

## Building from Source

### Prerequisites

- JDK 17+
- Gradle 8.10+

### Build

```bash
# Clone the repository
git clone https://github.com/sentinel-seed/sentinel.git
cd sentinel/packages/jetbrains

# Build the plugin
./gradlew buildPlugin

# The plugin ZIP will be in build/distributions/
```

### Run in Development Mode

```bash
./gradlew runIde
```

### Publish

```bash
# Set your token
export PUBLISH_TOKEN="your-jetbrains-marketplace-token"

# Publish to marketplace
./gradlew publishPlugin
```

## Supported IDEs

- IntelliJ IDEA (Community & Ultimate)
- PyCharm (Community & Professional)
- WebStorm
- PhpStorm
- Rider
- CLion
- GoLand
- RubyMine
- DataGrip
- Android Studio

**Minimum Version**: 2024.1+

## License

MIT License - see [LICENSE](LICENSE)

## Links

- [Documentation](https://sentinelseed.dev/docs)
- [GitHub](https://github.com/sentinel-seed/sentinel)
- [VS Code Extension](https://marketplace.visualstudio.com/items?itemName=sentinelseed.sentinel-ai-safety)
