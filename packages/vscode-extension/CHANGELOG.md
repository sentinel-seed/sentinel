# Changelog

All notable changes to the Sentinel AI Safety extension will be documented in this file.

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
