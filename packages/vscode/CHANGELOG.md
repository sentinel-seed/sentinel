# Changelog

All notable changes to the Sentinel AI Safety extension will be documented in this file.

## [0.4.0] - 2025-12-22

### Added

- **Compliance Checking Module**: Comprehensive regulatory compliance analysis
  - **EU AI Act (2024/1689)**: Full Article 5 prohibited practices detection, Annex III high-risk context identification, risk level classification (unacceptable/high/limited/minimal)
  - **OWASP LLM Top 10 (2025)**: Input and output validation against all 10 vulnerability categories with 37+ detection patterns
  - **CSA AI Controls Matrix (v1.0)**: Assessment across 18 security domains with threat category mapping

- **New Commands**:
  - `Sentinel: Check Compliance (All Frameworks)` - Run all compliance checks at once
  - `Sentinel: Check EU AI Act Compliance` - EU AI Act specific analysis
  - `Sentinel: Check OWASP LLM Top 10` - OWASP vulnerability scanning
  - `Sentinel: Check CSA AI Controls Matrix` - CSA AICM domain assessment

- **WebView Result Panel**: Rich visual presentation of compliance results
  - Framework-specific result visualization
  - Risk level indicators with color coding
  - Threat assessment summaries
  - Actionable recommendations

- **Context Menu Integration**: Quick access to compliance checks via right-click
  - All four compliance commands available in editor context menu
  - Organized in dedicated "sentinel" menu group

- **Unified Compliance Checker**: Single API for multi-framework analysis
  - Combined recommendations (deduplicated)
  - Summary view across all frameworks
  - Individual framework drill-down

### Technical Details

- **Privacy-First Design**: All heuristic checks run 100% locally
- **THSP Gate Mapping**: Each vulnerability/domain mapped to relevant THSP gates
- **Coverage Levels**: Strong/Moderate/Indirect/Not Applicable for transparency
- **Pattern Detection**:
  - 23 prompt injection patterns (LLM01)
  - 15 sensitive information patterns (LLM02)
  - Advanced techniques: token smuggling, grandma exploit, continuation attack
- **Comprehensive Type System**: Full TypeScript definitions for all compliance types

## [0.3.3] - 2025-12-20

### Security

- **Critical**: Added response validation for OpenAI and Anthropic API calls
- **Critical**: User content now sanitized to prevent prompt injection attacks
- **Critical**: Added 30-second timeout with AbortController for all API calls

### Added

- Result caching system (1-minute TTL, 50 entries max) for better performance
- Comprehensive test suite for semantic, analyzer, linter, seeds, and secrets modules
- ESLint configuration (`.eslintrc.json`) for code quality enforcement
- Dynamic token count estimation for alignment seeds
- Type guards for LLM response validation

### Fixed

- Added try/catch to `loadSecretKeys` and `migrateFromSettings` for graceful error handling
- Implemented `dispose()` in SentinelLinter for proper resource cleanup
- Linter now properly added to context.subscriptions for automatic cleanup
- Empty file validation in `analyzeFile` command
- API key prefix validation made more flexible (accepts non-standard formats)
- Removed unnecessary global flag from regex patterns

### Changed

- Optimized validator re-initialization with config hash comparison
- Updated Anthropic API version to `2024-01-01`
- Migration now offers to auto-clear settings after successful migration
- Added `noUnusedLocals` and `noUnusedParameters` to tsconfig
- Added `engines.node >= 18.0.0` requirement

## [0.3.2] - 2025-12-17

### Fixed

- Converted mixed `require()` to ES6 `import` for consistency
- Improved code organization in analyzer module

### Changed

- Minor internal refactoring for better maintainability

## [0.3.0] - 2025-12-16

### Added

- **Secure API Key Storage**: API keys now stored in VS Code's SecretStorage
  - New commands: "Set OpenAI API Key (Secure)" and "Set Anthropic API Key (Secure)"
  - Keys encrypted and stored securely
  - Automatic migration from settings to secure storage

- **Status Bar Indicator**: Shows current analysis mode (Semantic/Heuristic)
  - Click to see detailed status information
  - Visual feedback when API key is not configured

- **Show Status Command**: View current provider, model, and accuracy level

### Improved

- Enhanced error messages with specific causes (rate limit, invalid key, network issues)
- Unified pattern detection system for consistent results
- Better TypeScript type definitions throughout codebase
- Reduced extension size by removing unused dependencies

## [0.2.0] - 2025-12-16

### Added

- **Semantic Analysis Mode**: LLM-based analysis using OpenAI or Anthropic APIs
  - Real semantic understanding of content
  - Context-aware detection (distinguishes "hack productivity" from malicious hacking)
  - Provides reasoning for decisions
  - ~90% confidence vs ~50% for heuristic mode

- New settings:
  - `sentinel.llmProvider`: Choose between OpenAI and Anthropic
  - `sentinel.openaiApiKey`: OpenAI API key for semantic analysis
  - `sentinel.openaiModel`: OpenAI model selection (default: gpt-4o-mini)
  - `sentinel.anthropicApiKey`: Anthropic API key for semantic analysis
  - `sentinel.anthropicModel`: Anthropic model selection (default: claude-3-haiku)

### Changed

- Analysis results now show method used (Semantic vs Heuristic)
- Analysis results now show confidence percentage
- Heuristic mode clearly marked as fallback with lower confidence
- Improved pattern matching to reduce false positives
- Updated documentation with clear comparison of analysis modes

### Fixed

- Heuristic patterns now use phrase matching instead of single words
- Reduced false positives for legitimate security discussions

## [0.1.0] - 2025-12-10

### Added

- Initial release
- Real-time safety linting for prompts
- THSP protocol analysis (Truth, Harm, Scope, Purpose)
- Commands:
  - Analyze Selection for Safety
  - Analyze File for Safety
  - Insert Alignment Seed (standard)
  - Insert Alignment Seed (minimal)
- Right-click context menu integration
- Configurable settings
- Support for Markdown, Python, JavaScript, TypeScript, JSON, YAML
- Local heuristic-based analysis
- API fallback support for enhanced analysis

### Patterns Detected

- Jailbreak attempts (instruction override, persona switch)
- Harmful content (weapons, hacking, malware)
- Deception patterns (fake documents, impersonation)
- Bypass attempts (safety disable, mode switches)
- Purposeless actions (unclear benefit)
