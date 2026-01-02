# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.19.0] - 2026-01-02

### Added
- Comprehensive test coverage for core modules:
  - `validators/semantic.py`: 29% → 88% coverage
  - `validation/layered.py`: 57% → 90% coverage
  - `sentinel_core.py`: 55% → 93% coverage
- New test file `test_semantic_validator.py` with 75 tests covering:
  - OpenAI and Anthropic API mocking
  - JSON response parsing (code blocks, plain JSON, invalid)
  - THSPResult, THSPGate, RiskLevel types
  - AsyncSemanticValidator
  - Factory functions and convenience methods
- Extended `test_layered_validator.py` with tests for:
  - `validate_action_plan` (physical safety patterns)
  - Async validation with semantic layer
  - Error handling (CancelledError, ConnectionError)
  - Logging validations
- Extended `test_core.py` with tests for:
  - `Sentinel.chat()` with provider mocks
  - API key handling and masking
  - Semantic auto-detection
  - `validate()`, `validate_action()`, `get_validation_result()`
- **OpenAI Agents SDK**: Added layered validation (heuristic + semantic)
  - New `use_heuristic` and `skip_semantic_if_heuristic_blocks` config options
  - Heuristic layer runs first for fast, free validation (<10ms, 580+ patterns)
  - Semantic layer (LLM-based) only called if heuristic passes or doesn't block
  - Saves API costs by avoiding unnecessary LLM calls for obvious violations

### Changed
- `SentinelChain` (langchain/chains.py) now inherits from `SentinelIntegration`
  - Uses `self._validator` from base class instead of creating its own
  - Maintains backwards compatibility for seed injection
- Langchain integration (`chains.py`) now uses `LayeredValidator` directly instead of `Sentinel.validate()`
- Consolidated `THSPGate` enum: now imported from `validators/semantic.py` in all integrations
- Test suite now includes 1833+ tests (up from 1705)
- **OpenAI Agents guardrails**: Now return `layer` field ("heuristic", "semantic", or "none") in output_info

### Deprecated
- `THSValidator` class - Use `THSPValidator` (4 gates) or `LayeredValidator` instead
  - Emits `DeprecationWarning` on instantiation
  - Will be removed in version 3.0.0
- `JailbreakGate` class - Functionality moved to Truth/Scope gates
  - Emits `DeprecationWarning` on instantiation
  - Will be removed in version 3.0.0
- Direct imports of gate classes from `sentinelseed` package
  - Use `Sentinel.validate()` or `LayeredValidator` instead

### Fixed
- Removed duplicate `THSPGate` definitions in `virtuals/` and `coinbase/x402/` integrations

### Verified (Integration Audit)
- `mcp_server`: Uses `LayeredValidator` correctly (exception by design: MCP uses functions)
- `coinbase/x402`: `THSPGate` imported from canonical source (`validators/semantic.py`)
- `virtuals`: Inherits from `SentinelIntegration`, uses `LayeredValidator`
- `solana_agent_kit`: Inherits from `SentinelIntegration`, uses `LayeredValidator`
- `openguardrails`: `SentinelGuardrailsWrapper` inherits from `SentinelIntegration`
- `autogpt_block`: Uses `LayeredValidator` via standalone functions (exception by design)

### Documentation
- New `docs/ARCHITECTURE.md`: System architecture, validation flow, integration patterns
- New `docs/MIGRATION.md`: Migration guide for users upgrading from older versions
- Updated README with architecture and migration documentation references

## [2.18.0] - 2025-12-28

### Added
- Google ADK (Agent Development Kit) integration
- Agno multi-agent framework integration
- Coinbase x402 payment validation integration
- LayeredValidator with automatic semantic detection
- Memory integrity module for long-running agents
- Fiduciary validation for financial AI agents
- EU AI Act compliance checker

### Changed
- Improved THSP validation with 580+ regex patterns
- Enhanced physical safety patterns for robotics

## [2.17.0] - 2025-12-15

### Added
- Letta (MemGPT) integration for stateful agents
- OpenAI Agents SDK integration
- ROS2 integration for robotics
- Isaac Lab integration for simulation

### Changed
- Semantic validation now supports Anthropic Claude models
- Improved timeout handling in async validators

## [2.16.0] - 2025-12-01

### Added
- Solana Agent Kit integration
- Virtuals Protocol GAME SDK integration
- MCP (Model Context Protocol) server implementation
- Preflight transaction validation for blockchain

### Changed
- Upgraded minimum Python version to 3.10
- Improved error messages for configuration issues

## [2.15.0] - 2025-11-15

### Added
- DSPy integration for prompt optimization
- PyRIT integration for security testing
- Garak integration for red teaming
- CrewAI integration for multi-agent workflows

### Changed
- Refactored validation pipeline for better performance
- Added caching for heuristic validation patterns

## [2.14.0] - 2025-11-01

### Added
- LangGraph integration for stateful agents
- AutoGPT integration
- Database guard for SQL injection prevention
- Purpose gate (THSP → 4 gates)

### Changed
- Renamed THS protocol to THSP (added Purpose gate)
- Improved jailbreak detection patterns

## [2.13.0] - 2025-10-15

### Added
- AsyncLayeredValidator for async frameworks
- AsyncSemanticValidator for async LLM calls
- Semantic validation with GPT-4o-mini default

### Changed
- Validation timeout now configurable
- Improved fail-closed behavior

## [2.12.0] - 2025-10-01

### Added
- LangChain integration (chains, callbacks)
- Seed versioning (minimal, standard, full)
- ValidationConfig dataclass

### Changed
- Reorganized package structure
- Added type hints throughout

## [2.11.0] - 2025-09-15

### Added
- Initial LayeredValidator implementation
- THSPValidator (heuristic aggregator)
- Individual gates (Truth, Harm, Scope)

### Changed
- Improved seed content with examples
- Added anti-self-preservation principles

## [2.10.0] - 2025-09-01

### Added
- Initial public release
- Sentinel class with chat and validation
- Alignment seeds (minimal, standard, full)
- OpenAI and Anthropic provider support

[2.19.0]: https://github.com/sentinel-seed/sentinel/compare/v2.18.0...v2.19.0
[2.18.0]: https://github.com/sentinel-seed/sentinel/compare/v2.17.0...v2.18.0
[2.17.0]: https://github.com/sentinel-seed/sentinel/compare/v2.16.0...v2.17.0
[2.16.0]: https://github.com/sentinel-seed/sentinel/compare/v2.15.0...v2.16.0
[2.15.0]: https://github.com/sentinel-seed/sentinel/compare/v2.14.0...v2.15.0
[2.14.0]: https://github.com/sentinel-seed/sentinel/compare/v2.13.0...v2.14.0
[2.13.0]: https://github.com/sentinel-seed/sentinel/compare/v2.12.0...v2.13.0
[2.12.0]: https://github.com/sentinel-seed/sentinel/compare/v2.11.0...v2.12.0
[2.11.0]: https://github.com/sentinel-seed/sentinel/compare/v2.10.0...v2.11.0
[2.10.0]: https://github.com/sentinel-seed/sentinel/releases/tag/v2.10.0
