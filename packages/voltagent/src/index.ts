/**
 * @sentinelseed/voltagent
 *
 * AI safety guardrails for VoltAgent applications.
 *
 * This package provides VoltAgent-compatible guardrails that implement:
 * - THSP Protocol: Truth, Harm, Scope, Purpose validation
 * - OWASP Protection: SQL injection, XSS, command injection, etc.
 * - PII Detection: Email, phone, SSN, credit cards, API keys, etc.
 *
 * @example Quick Start
 * ```typescript
 * import { Agent } from "@voltagent/core";
 * import { createSentinelGuardrails } from "@sentinelseed/voltagent";
 *
 * const { inputGuardrails, outputGuardrails } = createSentinelGuardrails({
 *   level: "strict",
 *   enablePII: true,
 * });
 *
 * const agent = new Agent({
 *   name: "safe-agent",
 *   inputGuardrails,
 *   outputGuardrails,
 * });
 * ```
 *
 * @see https://sentinelseed.dev/docs/integrations/voltagent
 * @see https://voltagent.dev/docs/
 */

// =============================================================================
// Guardrail Factories (Primary API)
// =============================================================================

// Bundle function - recommended for most use cases
export {
  createSentinelGuardrails,
  createChatGuardrails,
  createAgentGuardrails,
  createPrivacyGuardrails,
  createDevelopmentGuardrails,
  getPresetConfig,
  getAvailableLevels,
  type SentinelGuardrailBundle,
} from './guardrails/bundle';

// Individual guardrail factories
export {
  // Input guardrails
  createSentinelInputGuardrail,
  createStrictInputGuardrail,
  createPermissiveInputGuardrail,
  createTHSPOnlyGuardrail,
  createOWASPOnlyGuardrail,
  type SentinelInputGuardrail,
  // Output guardrails
  createSentinelOutputGuardrail,
  createPIIOutputGuardrail,
  createStrictOutputGuardrail,
  createPermissiveOutputGuardrail,
  type SentinelOutputGuardrail,
  // Streaming handlers
  createSentinelPIIRedactor,
  createStrictStreamingRedactor,
  createPermissiveStreamingRedactor,
  createMonitoringStreamHandler,
  createStreamingState,
  type StreamingConfig,
} from './guardrails';

// =============================================================================
// Validators (For Advanced Use)
// =============================================================================

// THSP Validator
export {
  validateTHSP,
  quickCheck,
  getFailedGates,
  gatePasssed,
  getBuiltinPatterns,
  getTHSPPatternCount,
} from './validators';

// OWASP Validator
export {
  validateOWASP,
  quickOWASPCheck,
  hasViolation,
  getOWASPPatternsForType,
  getPatternStats,
  getOWASPPatternCount,
} from './validators';

// PII Validator
export {
  detectPII,
  hasPII,
  redactPII,
  maskPII,
  createStreamingRedactor,
  getPIIPatternsForType,
  getSupportedPIITypes,
  getPIIPatternCount,
} from './validators';

// =============================================================================
// Type Exports
// =============================================================================

export type {
  // Core types
  RiskLevel,
  GateStatus,
  GuardrailAction,
  THSPGates,

  // Validation results
  THSPValidationResult,
  OWASPValidationResult,
  OWASPViolationType,
  OWASPFinding,
  PIIDetectionResult,
  PIIType,
  PIIMatch,
  FullValidationResult,

  // Pattern definitions
  PatternDefinition,
  OWASPPatternDefinition,
  PIIPatternDefinition,

  // Configuration
  SentinelGuardrailConfig,
  SentinelBundleConfig,
  ValidationContext,

  // Streaming
  StreamingGuardrailState,
  StreamingChunkResult,
  TextStream,
  StreamHandler,

  // VoltAgent compatibility
  VoltAgentInputArgs,
  VoltAgentInputResult,
  VoltAgentOutputArgs,
  VoltAgentOutputResult,
} from './types';

// =============================================================================
// Version & Metadata
// =============================================================================

/**
 * Package version.
 */
export const VERSION = '0.1.0';

/**
 * Package name.
 */
export const PACKAGE_NAME = '@sentinelseed/voltagent';

/**
 * Supported VoltAgent version range.
 */
export const VOLTAGENT_VERSION_RANGE = '>=0.1.0';
