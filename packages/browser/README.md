# Sentinel Guard

> The Guardian of Your AI Conversations

Browser extension that protects your AI conversations from data harvesting, detects threats, and keeps you safe online.

## Features

### MVP (v0.1.0)

- **Conversation Shield** - Blocks other extensions from reading your AI chats
- **Secret Scanner** - Detects passwords, API keys, and sensitive data before you send them
- **Extension Trust Score** - Rates installed extensions by security risk
- **Real-time Alerts** - Notifications when threats are detected

### Coming Soon

- Bot/Agent detection
- PII protection
- Clipboard guard
- Crypto wallet protection

## Supported Platforms

- ChatGPT (chat.openai.com)
- Claude (claude.ai)
- Gemini (gemini.google.com)
- Perplexity (perplexity.ai)
- DeepSeek
- More coming...

## Installation

### From Chrome Web Store (Coming Soon)

1. Visit the Chrome Web Store
2. Search for "Sentinel Guard"
3. Click "Add to Chrome"

### Development Build

```bash
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
```

## Architecture

```
src/
├── background/     # Service Worker
├── content/        # Content Scripts (injected into pages)
├── popup/          # Extension Popup UI (React)
├── lib/            # Shared libraries (THSP, patterns)
└── types/          # TypeScript types
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
- Detects 30+ types of secrets (API keys, passwords, tokens)
- Warns before submission with options to remove, mask, or proceed

### THSP Protocol

All actions are validated through the Truth-Harm-Scope-Purpose protocol:
- **Truth**: Is this from a legitimate source?
- **Harm**: Could this cause harm?
- **Scope**: Is this within appropriate boundaries?
- **Purpose**: Is there a legitimate reason?

## Privacy

Sentinel Guard is privacy-first:
- **No data collection** - Your conversations never leave your browser
- **No external servers** - All processing happens locally
- **Open source** - Verify the code yourself

## Part of Sentinel Ecosystem

Sentinel Guard is part of the [Sentinel](https://sentinelseed.dev) AI safety ecosystem:

- **VS Code Extension** - Protect your code
- **JetBrains Plugin** - IDE integration
- **Python/npm SDKs** - For applications
- **Browser Extension** - Protect your browsing

## License

MIT License - see [LICENSE](../../LICENSE)

## Links

- Website: https://sentinelseed.dev
- GitHub: https://github.com/sentinel-seed/sentinel
- Twitter: @sentinelseed
