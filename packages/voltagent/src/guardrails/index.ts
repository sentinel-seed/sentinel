/**
 * @sentinelseed/voltagent - Guardrails
 *
 * VoltAgent-compatible guardrails for AI safety.
 * Export all guardrail factories and types.
 */

// Input Guardrails
export {
  createSentinelInputGuardrail,
  createStrictInputGuardrail,
  createPermissiveInputGuardrail,
  createTHSPOnlyGuardrail,
  createOWASPOnlyGuardrail,
  type SentinelInputGuardrail,
} from './input';

// Output Guardrails
export {
  createSentinelOutputGuardrail,
  createPIIOutputGuardrail,
  createStrictOutputGuardrail,
  createPermissiveOutputGuardrail,
  type SentinelOutputGuardrail,
} from './output';

// Streaming Handlers
export {
  createSentinelPIIRedactor,
  createStrictStreamingRedactor,
  createPermissiveStreamingRedactor,
  createMonitoringStreamHandler,
  createStreamingState,
  type StreamingConfig,
} from './streaming';

// Bundle Functions
export {
  createSentinelGuardrails,
  createChatGuardrails,
  createAgentGuardrails,
  createPrivacyGuardrails,
  createDevelopmentGuardrails,
  getPresetConfig,
  getAvailableLevels,
  type SentinelGuardrailBundle,
} from './bundle';
