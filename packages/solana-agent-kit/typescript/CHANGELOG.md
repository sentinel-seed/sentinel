# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.2] - 2025-12-15

### Fixed
- README GitHub URL now correctly points to `packages/` instead of `integrations/`
- Security updates for direct dependencies via `npm audit fix`

### Security
- Updated @langchain/core to fix serialization injection vulnerability (GHSA-r399-636x-v7f6)
- Note: Some transitive dependency vulnerabilities remain in solana-agent-kit peer dependencies

## [1.0.1] - 2025-12-10

### Fixed
- Minor documentation fixes
- Improved type exports

## [1.0.0] - 2025-12-01

### Added
- Initial release of @sentinelseed/solana-agent-kit
- THSP Protocol validation (Truth, Harm, Scope, Purpose)
- Transaction validation with configurable limits
- Address blocklist management
- Purpose verification for sensitive operations
- Pattern detection for suspicious transactions
- Native integration with Solana Agent Kit v2 plugin system
- LangChain-compatible tool actions:
  - `VALIDATE_TRANSACTION` - Full validation with gate analysis
  - `CHECK_SAFETY` - Quick pass/fail check
  - `GET_SAFETY_STATS` - Validation statistics
  - `BLOCK_ADDRESS` / `UNBLOCK_ADDRESS` - Blocklist management

### Security
- THSP four-gate validation protocol
- Configurable risk levels (low, medium, high, critical)
- Suspicious pattern detection for common attack vectors

## Links

- [npm package](https://www.npmjs.com/package/@sentinelseed/solana-agent-kit)
- [GitHub](https://github.com/sentinel-seed/sentinel/tree/main/packages/solana-agent-kit/typescript)
- [Documentation](https://sentinelseed.dev/docs)
