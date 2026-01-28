# Changelog

All notable changes to @sentinelseed/moltbot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-28

### Added

#### Core Features
- **Protection Levels**: Four levels of protection (off, watch, guard, shield)
- **Hook Integration**: Full Moltbot hook support (message_received, before_agent_start, message_sending, before_tool_call, agent_end)
- **THSP Validation**: Truth, Harm, Scope, Purpose gate validation via @sentinelseed/core

#### Validators
- **Input Analysis**: Detects prompt injection and jailbreak attempts
- **Output Validation**: Prevents data leaks (API keys, passwords, credentials)
- **Tool Validation**: Blocks dangerous commands and system access

#### Escape Hatches
- **Allow-Once**: Single-use bypass tokens with scope (output/tool/any)
- **Pause Protection**: Time-limited protection pause (10s to 1h)
- **Tool Trust**: Session-level tool trust with wildcard support

#### Logging & Alerts
- **Audit Log**: In-memory audit with TTL, filtering, and persistence hooks
- **Alert Manager**: Webhook delivery with rate limiting and retries
- **Formatters**: Human-readable and webhook-friendly output formats

#### CLI Commands
- `/sentinel status` - Current protection status
- `/sentinel level [new]` - View or change protection level
- `/sentinel log [count]` - View recent audit entries
- `/sentinel pause <duration>` - Pause protection
- `/sentinel resume` - Resume protection
- `/sentinel allow-once [scope]` - Grant one-time bypass
- `/sentinel trust <tool>` - Trust a tool
- `/sentinel untrust <tool>` - Revoke tool trust
- `/sentinel help` - Show available commands

#### Developer Features
- Full TypeScript support with comprehensive type exports
- Pattern registry for extensible detection
- Metrics collection for observability
- Configurable logging with child loggers

### Technical Details
- 724 tests (100% passing)
- 86%+ code coverage
- Zero production dependencies beyond @sentinelseed/core
- ESM and CJS dual module support
- Tree-shakeable exports

### Compatibility
- Node.js 18+
- Moltbot 0.1.x
- @sentinelseed/core 0.1.x

---

## [Unreleased]

### Planned
- Custom validator plugins
- Persistent escape hatch storage
- Multi-webhook routing by alert type
- Metrics export (Prometheus, OpenTelemetry)
