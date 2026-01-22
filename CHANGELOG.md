# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.26.0] - 2026-01-22

### Added

#### Memory: Memory Shield v2.0
- **MemoryContentValidator**: Pre-signing content validation for memory entries
  - Detects injection attacks BEFORE content is signed (vs v1.0 which only detected tampering AFTER)
  - 23+ detection patterns across 9 injection categories
  - Reuses BenignContextDetector from detection module for false-positive reduction
  - Configurable strict mode, confidence thresholds, and custom patterns
  - Full metrics collection: validations, block rate, time, suspicions by category
- **InjectionCategory enum**: 9 attack categories with severity levels
  - `AUTHORITY_CLAIM` (high): Fake admin/system messages
  - `INSTRUCTION_OVERRIDE` (critical): Attempts to override agent rules
  - `ADDRESS_REDIRECTION` (critical): Crypto fund redirection
  - `AIRDROP_SCAM` (high): Fake reward/airdrop schemes
  - `URGENCY_MANIPULATION` (medium): Time-pressure tactics
  - `TRUST_EXPLOITATION` (medium): Fake verification claims
  - `ROLE_MANIPULATION` (high): Identity/role injection
  - `CONTEXT_POISONING` (high): Fake context markers
  - `CRYPTO_ATTACK` (critical): Direct crypto theft attempts
- **MemoryContentUnsafe exception**: Raised when injection detected in strict mode
  - Includes suspicion list, content preview, and full serialization support
- **ContentValidationResult**: Immutable result type with factory methods
  - Properties: `is_suspicious`, `suspicion_count`, `primary_suspicion`, `categories_detected`
- **MemorySuspicion**: Individual detection result with category, confidence, and position
- **Convenience functions**: `is_memory_safe()`, `validate_memory_content()`

#### Memory: MemoryIntegrityChecker v2.0
- **New parameters**: `validate_content`, `content_validator`, `content_validation_config`
  - `validate_content=True`: Enable content validation before signing (opt-in)
  - `content_validator`: Inject custom MemoryContentValidator instance
  - `content_validation_config`: Dict config for default validator
- **sign_entry()**: Now validates content before signing (if enabled)
  - Raises `MemoryContentUnsafe` in strict mode
  - Adjusts trust score based on validation result in non-strict mode
- **skip_content_validation parameter**: Bypass content validation for specific entries

#### Cross-Platform: TypeScript Synchronization
- **@sentinelseed/core memory-patterns**: Canonical TypeScript source for all patterns
  - New `./memory-patterns` subpath export in package.json
  - `InjectionCategory` enum, `InjectionSeverity` type
  - Pattern utilities: `compilePatterns`, `getPatternsByCategory`, `getHighConfidencePatterns`
- **@sentinelseed/elizaos-plugin**: Memory content validation support
  - `MemoryContentValidator`, `MemoryContentUnsafeError`
  - Pattern exports from `memory-patterns.ts`
  - Updated `memory-integrity.ts` with v2.0 content validation
- **Browser extension**: Updated `memory-scanner.ts` with shared patterns
- **Sync script**: `scripts/sync-memory-patterns.py` generates TypeScript from Python

### Changed
- **memory/__init__.py**: Updated exports for v2.0 (patterns, content_validator)
- **memory/README.md**: Comprehensive v2.0 documentation
  - New "What's New in v2.0" section
  - Content validation quick start examples
  - API reference for new classes and types
  - OWASP coverage comparison table

### Security
- Addresses Princeton CrAIBench attack vector: malicious content injected BEFORE signing
- Pattern detection prevents: authority impersonation, instruction override, address redirection
- Benign context handling prevents false positives on technical content
- MALICIOUS_OVERRIDES prevent bypass via benign framing

### References
- Princeton CrAIBench: https://arxiv.org/abs/2503.16248 (85.1% attack success rate)
- OWASP ASI06: Memory and Context Poisoning
- Memory Shield v2.0 Specification

## [2.25.1] - 2026-01-17

### Changed

#### Detection: L3 OutputValidator v1.2.0
- **ToxicityChecker v1.2.0**: Improved false-positive reduction
  - Raised `keyword_threshold` from 0.5 to 0.75
  - Raised `combined_threshold` from 0.6 to 0.75
  - Removed overly generic keywords: "beat", "explicit", "minor", "cutting", "hanging", "bank account"
  - Added `BENIGN_CONTEXTS` whitelist for legitimate technical contexts
  - Added `SAFE_PROPER_NAMES` for common names that match patterns (e.g., "Dan" vs "DAN mode")
  - Added `MALICIOUS_OVERRIDES` security protection to prevent bypass via benign framing
  - New method: `_is_benign_context()` for context-aware detection
  - New method: `_has_malicious_override()` for security protection
- **AdversarialBehaviorDetector v1.2.0**: Improved precision
  - Case-sensitive patterns for jailbreak detection ("DAN" vs "Dan")
  - Updated `_is_adversarial_input()` with separate case-sensitive patterns
  - Fixed "I am an evil AI" pattern to match "an" article
- **OutputValidatorConfig**: New configuration options
  - `output_mode`: Enable output-focused detection (default: True)
  - `require_behavioral_context`: Keywords need behavioral indicators (default: True)
  - `benign_context_check`: Enable benign context whitelist (default: True)

### Security
- MALICIOUS_OVERRIDES prevents attackers from using benign framing to bypass detection
- Examples blocked: "kill the process that is my enemy", "attack the problem illegally"
- Benign context detection does NOT apply when malicious indicators are present

## [2.25.0] - 2026-01-14

### Added

#### Core: Multi-turn Support in Public API
- **SentinelValidator.validate_dialogue()**: Added `conversation_history` parameter
  - Enables Q6 escalation detection (Crescendo, MHJ attacks) in Gate 4
  - Optional parameter with default `None` for backward compatibility
  - History is passed to `SentinelObserver.observe()` for multi-turn analysis
  - Maximum 10 turns used for analysis
- **SentinelValidator.validate()**: Updated alias to support `conversation_history`

### Changed
- **Gate 4 (L4 Observer)**: Now receives conversation history when provided
  - Previously: `SentinelObserver.observe()` supported history internally but not exposed
  - Now: Full multi-turn support through public API
- **Documentation**: Updated docstrings with conversation_history examples

### Notes
- This is a backward-compatible change
- Existing code calling `validate_dialogue(input, output)` continues to work
- For multi-turn analysis, provide history as list of `{"role": "user"|"assistant", "content": "..."}`

## [2.24.0] - 2026-01-13

### Added

#### Core: L4 Resilience & Retry System
- **Retry System** (`retry.py`): Exponential backoff with jitter for L4 API calls
  - Automatic retry for rate limits, timeouts, and transient errors
  - Configurable max attempts, delays, and retry conditions
  - Based on tenacity library for robust implementation
- **Token Tracker** (`token_tracker.py`): Usage tracking for cost monitoring
  - Track input/output tokens per API call
  - Aggregate statistics for billing and optimization
- **Gate 4 Fallback Policy**: Configurable behavior when L4 is unavailable
  - `BLOCK`: Maximum security (block if L4 fails)
  - `ALLOW_IF_L2_PASSED`: Balanced (allow only if L2 passed)
  - `ALLOW`: Maximum usability (allow regardless)
- **Block Messages**: User-facing messages for blocked requests
  - Configurable per-gate messages
  - Security-focused: never reveal detection details

#### Detection: False Positive Reduction
- **Benign Context Detector** (`benign_context.py`): Reduces false positives
  - Detects legitimate technical contexts ("kill process", "attack the problem")
  - Categories: programming, business, security education, health, chemistry
  - Does not apply if obfuscation detected (prevents bypass)
- **Intent Signal Detector** (`intent_signal.py`): Compositional intent analysis
  - Analyzes action + target + context for better accuracy
  - Weight 1.3 in InputValidator
- **Safe Agent Detector** (`safe_agent_detector.py`): Enhanced embodied AI safety
  - Covers plant care, object location, contamination, electrical stress
  - Based on SafeAgentBench patterns, weight 1.4

#### Detection: Expanded Pattern Coverage
- **HarmfulContentChecker v1.2.0**: Major pattern expansion
  - New categories: drugs, fraud (skimmers), exploitation, terrorism, chemical/bio
  - Improved fiction bypass detection ("for educational purposes only")
  - Compliance indicators now boost (not trigger) detection
- **OutputValidator**: Enhanced with behavior checking
  - New `behavior_checker.py` for behavioral analysis
  - New `output_signal.py` for output signal detection

#### Observer: Multi-turn Analysis
- **Conversation Context** (`observer.py`): Multi-turn conversation support
  - `ConversationTurn` and `ConversationContext` dataclasses
  - Enables detection of escalation attacks (Crescendo, multi-turn jailbreaks)
  - Integrated with retry system for resilient API calls

#### Seed: Anti-Frame Protection
- **Anti-Frame Protection** section in `standard.txt`
  - Protects against positive framing bypass ("for objectivity", "for user control")
  - Explicit rules: noble cause + harmful action = REFUSE
  - "The test: If the ACTION is harmful, no PURPOSE justifies it"

### Changed
- **Gate Naming**: Standardized to L1/L2/L3/L4 (gate3 → gate4 internally)
  - Legacy `gate3_*` properties maintained for backward compatibility
  - All public APIs unchanged
- **Gate 4 Execution**: Now ALWAYS executes when Gate 2 doesn't block
  - Previously: only executed on Gate 2 uncertainty
  - Ensures semantic analysis of full dialogue for accurate judgment
- **InputValidator v1.8.0**: Integrated BenignContextDetector, new detectors
- **SentinelConfig**: Added retry parameters, fallback policy, block messages
- **Configuration Presets**: Added `SECURE_CONFIG` and `RESILIENT_CONFIG`

### Fixed
- Fiction bypass pattern: corrected "purposes only" detection
- False positive reduction via BenignContextDetector integration
- Compliance indicators alone no longer trigger harmful content detection
- ElizaOS build error (ALL_PURPOSE_PATTERNS export from core)
- Dockerfile path (`seed/` → `seeds/`)
- Memory example import (`sentinel.memory` → `sentinelseed.memory`)
- npm package links (6 files: `sentinelseed` → `@sentinelseed/core`)
- Broken internal reference in solana-agent-kit README
- HuggingFace sync script (added agno, coinbase, google_adk)
- Integration count in HuggingFace README (22 → 25)

### Documentation
- Updated pattern count from 580+ to 700+ (16 files)
- Added v2.24.0 architecture diagrams (mermaid flowcharts)
- Added LLM provider examples (DeepSeek, Groq, Meta Llama, Together, Fireworks, Ollama)
- Fixed Python version requirements (3.10+)

### Security
- Block messages designed to never reveal detection mechanisms
- Benign context detection disabled when obfuscation detected
- MALICIOUS_OVERRIDES prevent bypass of known attack patterns

## [2.23.1] - 2026-01-09

### Fixed
- Added `typing_extensions>=4.0.0` as explicit dependency
- Fixed PyPI package cache issues for SDK tests

## [2.23.0] - 2026-01-08

### Added

#### Detection Module (Complete Implementation)
- **InputValidator v1.5.0**: Pre-AI attack detection
  - PatternDetector with 580+ regex patterns (weight 1.0)
  - FramingDetector for roleplay/fiction attacks (weight 1.2)
  - EscalationDetector for multi-turn attacks (weight 1.1)
  - HarmfulRequestDetector for direct harm requests (weight 1.3)
  - PhysicalSafetyDetector for embodied agents (weight 1.4)
  - TextNormalizer with obfuscation detection
  - DetectorRegistry for extensibility
- **OutputValidator v1.3.0**: Post-AI seed compliance
  - HarmfulContentChecker v1.0.0
  - DeceptionChecker
  - BypassChecker
  - ComplianceChecker
  - BehaviorChecker
- **Embedding Detection**: 1000-vector semantic similarity
  - Attack vector database with known harmful patterns
  - Configurable similarity threshold

#### Core v3.0 Architecture
- **SentinelValidator**: Main 3-gate orchestrator
  - Gate 1 (L1): InputValidator (pre-AI)
  - Gate 2 (L3): OutputValidator (post-AI heuristic)
  - Gate 3 (L4): SentinelObserver (post-AI LLM)
- **SentinelConfig**: Unified configuration dataclass
  - Gate enable/disable
  - Embedding thresholds
  - Provider configuration
- **SentinelObserver**: LLM-based transcript analysis
  - Multi-provider support: OpenAI, Anthropic, Groq, Together, DeepSeek
  - Validated prompt (F1=87.9% in Session 189)
  - Logprobs support for confidence scoring
- **Result Types**: `SentinelResult`, `ObservationResult`
  - Detailed gate-by-gate information
  - Latency tracking

#### Integration Updates
- **Seed Injection**: Added to base integration classes
- **SentinelV3Adapter**: Unified adapter for v3.0 architecture
- Integration improvements for all 25 frameworks

### Changed
- Bumped minimum Python version to 3.10 (dropped 3.9)
- CI pipeline improvements and coverage adjustments
- THSPValidator improved to 97/100 accuracy

### Documentation
- Updated ARCHITECTURE.md with v3.0 details
- API documentation refresh

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

[2.26.0]: https://github.com/sentinel-seed/sentinel/compare/v2.25.1...v2.26.0
[2.25.1]: https://github.com/sentinel-seed/sentinel/compare/v2.25.0...v2.25.1
[2.25.0]: https://github.com/sentinel-seed/sentinel/compare/v2.24.0...v2.25.0
[2.24.0]: https://github.com/sentinel-seed/sentinel/compare/v2.23.1...v2.24.0
[2.23.1]: https://github.com/sentinel-seed/sentinel/compare/v2.23.0...v2.23.1
[2.23.0]: https://github.com/sentinel-seed/sentinel/compare/v2.19.0...v2.23.0
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
