/**
 * @sentinelseed/voltagent - Validators
 *
 * Safety validators for AI agent content.
 * Export all validator functions and types.
 */

// THSP Validator
export {
  validateTHSP,
  quickCheck,
  getFailedGates,
  gatePassed,
  getBuiltinPatterns,
  getPatternCount as getTHSPPatternCount,
} from './thsp';

// OWASP Validator
export {
  validateOWASP,
  quickOWASPCheck,
  hasViolation,
  getPatternsForType as getOWASPPatternsForType,
  getPatternStats,
  getTotalPatternCount as getOWASPPatternCount,
} from './owasp';

// PII Validator
export {
  detectPII,
  hasPII,
  redactPII,
  maskPII,
  createStreamingRedactor,
  getPatternsForType as getPIIPatternsForType,
  getSupportedTypes as getSupportedPIITypes,
  getPatternCount as getPIIPatternCount,
} from './pii';
