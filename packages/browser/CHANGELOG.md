# Changelog

All notable changes to Sentinel Guard will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-12-28

### Added

#### Core Protection
- Conversation Shield: Blocks other extensions from reading AI chats
- Secret Scanner: Detects 30+ types of secrets (API keys, passwords, tokens, seed phrases)
- Extension Trust Score: Rates installed extensions by security risk
- Real-time Alerts: Notifications when threats are detected
- THSP Protocol validation for all content

#### Agent Shield
- Agent Registry: Track connected AI agents (ElizaOS, AutoGPT, CrewAI, custom)
- Action Interceptor: Review and approve agent actions before execution
- Memory Scanner: 40+ patterns to detect memory injection attacks
- Trust Level management for agents

#### MCP Gateway
- Server Registry: Track connected MCP servers
- Tool Interceptor: Review and approve MCP tool calls
- Risk Calculator: Automatic risk assessment
- Tool Validator: THSP-based validation

#### Approval System
- Configurable approval rules (auto-approve, auto-reject, require approval)
- Risk-based default actions
- Action history with full audit trail
- IndexedDB persistence for offline support
- Expiration handling for pending approvals

#### UI/UX
- React-based popup with tabbed navigation
- Dashboard with real-time statistics
- Agents tab for monitoring connected agents
- MCP tab for server and tool management
- Rules tab for approval rule configuration
- History tab for action audit trail
- Settings tab with all configuration options
- Toast notifications
- Modal dialogs for approvals
- Skeleton loaders for async content
- Error boundaries for graceful error handling

#### Accessibility
- Screen reader support (ARIA labels, live regions)
- Keyboard navigation (roving tabindex, skip links)
- Reduced motion support (prefers-reduced-motion)
- High contrast mode support
- Focus management and visible focus indicators
- Semantic HTML structure

#### Internationalization
- English (en) support
- Spanish (es) support
- Portuguese (pt) support
- Auto-detection from browser settings

#### Platform Support
- ChatGPT (chat.openai.com, chatgpt.com)
- Claude (claude.ai)
- Gemini (gemini.google.com)
- Perplexity (perplexity.ai)
- DeepSeek (deepseek.com)
- Grok (grok.x.ai)
- Copilot (copilot.microsoft.com)
- Meta AI (meta.ai)

#### Testing
- 504 tests passing
- 50%+ code coverage
- Unit tests for all major components
- Integration tests for approval flow
- Accessibility tests for UI components

### Security
- XSS prevention (no innerHTML with user data)
- Input validation for all user inputs
- Secure messaging between popup and background
- No external data transmission

## [Unreleased]

### Planned
- Chrome Web Store publication
- Firefox Add-ons publication
- Edge Add-ons publication
- Bot/Agent detection for web pages
- PII protection features
- Clipboard guard enhancements
- Crypto wallet protection
