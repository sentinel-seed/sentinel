# Sentinel Guard

> The Guardian of Your AI Conversations

Browser extension that protects your AI conversations from data harvesting, monitors AI agents, controls MCP tools, and keeps you safe online.

## Features

### Core Protection (v0.1.0)

- **Conversation Shield**: Blocks other extensions from reading your AI chats
- **Secret Scanner**: Detects passwords, API keys, seed phrases, and sensitive data before you send them
- **Extension Trust Score**: Rates installed extensions by security risk
- **Real-time Alerts**: Notifications when threats are detected

### Agent Shield

- **Agent Registry**: Track all connected AI agents (ElizaOS, AutoGPT, CrewAI, custom)
- **Action Interceptor**: Review and approve agent actions before execution
- **Memory Scanner**: Detect memory injection attacks (40+ patterns from ElizaOS research)
- **Trust Levels**: Assign trust levels to agents for automatic approval

### MCP Gateway

- **Server Registry**: Track all connected MCP servers
- **Tool Interceptor**: Review and approve MCP tool calls
- **Risk Calculator**: Automatic risk assessment for tool calls
- **Tool Validation**: THSP-based validation for all tool executions

### Approval System

- **Configurable Rules**: Create rules for auto-approve, auto-reject, or manual approval
- **Risk-based Defaults**: Low risk auto-approved, high risk requires approval
- **Action History**: Full audit trail of all approved/rejected actions
- **Expiration Handling**: Automatic handling of expired approval requests

## Supported Platforms

- ChatGPT (chat.openai.com, chatgpt.com)
- Claude (claude.ai)
- Gemini (gemini.google.com)
- Perplexity (perplexity.ai)
- DeepSeek (deepseek.com)
- Grok (grok.x.ai)
- Copilot (copilot.microsoft.com)
- Meta AI (meta.ai)

## Installation

### From Chrome Web Store (Coming Soon)

1. Visit the Chrome Web Store
2. Search for "Sentinel Guard"
3. Click "Add to Chrome"

### Development Build

```bash
# Clone the repository
git clone https://github.com/sentinel-seed/sentinel.git
cd sentinel/packages/browser

# Install dependencies
npm install

# Build extension
npm run build

# The built extension will be in ./dist
```

### Load in Chrome (Development)

1. Open Chrome and go to `chrome://extensions`
2. Enable "Developer mode" (top right)
3. Click "Load unpacked"
4. Select the `dist` folder

### Load in Firefox (Development)

1. Open Firefox and go to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on"
3. Select `manifest.json` from the `dist` folder

### Load in Edge (Development)

1. Open Edge and go to `edge://extensions`
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select the `dist` folder

## Development

```bash
# Install dependencies
npm install

# Development build with watch
npm run dev

# Production build
npm run build

# Run tests
npm test

# Run tests with coverage
npm run test:coverage

# Lint code
npm run lint
```

## Architecture

```
src/
├── background/          # Service Worker (Chrome MV3)
├── content/             # Content Scripts (injected into pages)
├── popup/               # Extension Popup UI (React)
│   ├── components/      # React components
│   ├── hooks/           # Custom React hooks
│   └── styles/          # CSS styles
├── lib/                 # Shared libraries
│   ├── thsp.ts          # THSP Protocol validation
│   ├── patterns.ts      # Pattern detection
│   ├── wallet-guard.ts  # Crypto transaction analysis
│   └── i18n.ts          # Internationalization (EN/ES/PT)
├── agent-shield/        # Agent monitoring module
├── mcp-gateway/         # MCP tools interception
├── approval/            # Approval system with IndexedDB
├── messaging/           # Chrome messaging utilities
└── types/               # TypeScript types
```

## How It Works

### Conversation Shield

The extension injects a content script into AI chat platforms that:
- Monitors for suspicious DOM access attempts
- Creates protective wrappers around conversation elements
- Blocks unauthorized data extraction

### Secret Scanner

Based on the same patterns used in the Sentinel VS Code extension:
- Scans text in real-time as you type
- Detects 30+ types of secrets (API keys, passwords, tokens, seed phrases)
- Warns before submission with options to remove, mask, or proceed

### THSP Protocol

All actions are validated through the Truth-Harm-Scope-Purpose protocol:
- **Truth**: Is this from a legitimate source?
- **Harm**: Could this cause harm?
- **Scope**: Is this within appropriate boundaries?
- **Purpose**: Is there a legitimate reason?

### Agent Shield

Monitors AI agents and their actions:
- Intercepts tool calls before execution
- Detects memory injection attempts
- Requires approval for high-risk actions

### MCP Gateway

Controls Model Context Protocol tool calls:
- Validates tools against THSP protocol
- Calculates risk level for each call
- Maintains audit trail

## Internationalization

Sentinel Guard supports multiple languages:
- English (en)
- Spanish (es)
- Portuguese (pt)

Language is auto-detected from browser settings or can be set manually in Settings.

## Privacy

Sentinel Guard is privacy-first:
- **No data collection**: Your conversations never leave your browser
- **No external servers**: All processing happens locally
- **Open source**: Verify the code yourself

## Testing

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Watch mode
npm run test:watch
```

Current test coverage: 866 tests passing, 55%+ code coverage.

## Part of Sentinel Ecosystem

Sentinel Guard is part of the [Sentinel](https://sentinelseed.dev) AI safety ecosystem:

- **VS Code Extension**: Protect your code
- **JetBrains Plugin**: IDE integration
- **Neovim Plugin**: Editor integration
- **Python/npm SDKs**: For applications
- **Browser Extension**: Protect your browsing

## License

MIT License (see [LICENSE](../../LICENSE))

## Links

- Website: https://sentinelseed.dev
- GitHub: https://github.com/sentinel-seed/sentinel
- Twitter: @sentinelseed
- PyPI: https://pypi.org/project/sentinelseed/
- npm: https://www.npmjs.com/package/sentinelseed
