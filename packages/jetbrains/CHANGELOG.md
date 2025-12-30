# Changelog

All notable changes to the Sentinel AI Safety JetBrains plugin will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2024-12-30

### Added
- **Security Scanning Module**
  - Scan Secrets: Detect 67+ patterns for API keys, passwords, tokens
  - Sanitize Prompts: Identify prompt injection attempts
  - Validate Output: Check for XSS, command injection, leaked secrets
  - SQL Injection Detection: 8 categories of SQL injection patterns

- **Compliance Checking Module**
  - EU AI Act compliance (Articles 5, 6, 52)
  - OWASP LLM Top 10 vulnerability detection
  - CSA AI Controls Matrix validation

- **Metrics Dashboard**
  - Track analysis history and trends
  - Security scan statistics
  - Compliance check metrics
  - Persistent storage using PropertiesComponent

- **Professional Quality Improvements**
  - Comprehensive unit tests (SecurityPatterns, SecurityService, CompliancePatterns, ComplianceService)
  - CI/CD pipeline with GitHub Actions
  - Centralized error handling (ErrorHandler)
  - Structured logging (SentinelLogger)
  - Internationalization support (i18n) - English and Portuguese

- **New Actions**
  - Scan Secrets
  - Sanitize Prompt
  - Validate Output
  - Scan SQL Injection
  - Check OWASP LLM Top 10
  - Check EU AI Act
  - Check CSA AICM
  - Full Compliance Check
  - Show Metrics
  - Clear Metrics

### Changed
- Updated build.gradle.kts with test dependencies (JUnit 5, MockK, AssertJ)
- Improved plugin.xml with new actions and menu structure
- Enhanced README with new features documentation

### Fixed
- MetricsService now properly integrated with all security/compliance actions

## [0.2.1] - 2024-12-15

### Fixed
- CredentialAttributes API compatibility for IntelliJ 2024.1+
- Build configuration for Gradle 8.13

### Changed
- Improved secure storage for API keys using PasswordSafe

## [0.2.0] - 2024-12-01

### Added
- Ollama support for local LLM analysis (no API key required)
- OpenAI-compatible endpoint support (Groq, Together AI)
- Multiple LLM provider selection in settings
- Tool window for analysis results

### Changed
- Improved settings UI with provider-specific options
- Enhanced heuristic analysis patterns

## [0.1.0] - 2024-11-15

### Added
- Initial release
- THSP Protocol implementation (Truth, Harm, Scope, Purpose gates)
- OpenAI and Anthropic integration
- Real-time analysis with editor integration
- Seed insertion actions
- Status bar widget
- Settings panel for API configuration

[0.3.0]: https://github.com/sentinel-seed/sentinel/compare/jetbrains-v0.2.1...jetbrains-v0.3.0
[0.2.1]: https://github.com/sentinel-seed/sentinel/compare/jetbrains-v0.2.0...jetbrains-v0.2.1
[0.2.0]: https://github.com/sentinel-seed/sentinel/compare/jetbrains-v0.1.0...jetbrains-v0.2.0
[0.1.0]: https://github.com/sentinel-seed/sentinel/releases/tag/jetbrains-v0.1.0
