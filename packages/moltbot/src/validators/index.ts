/**
 * @sentinelseed/moltbot - Validators Module
 *
 * This module provides validation functions for output content,
 * tool calls, and input analysis.
 *
 * @example
 * ```typescript
 * import { validateOutput, validateTool, analyzeInput } from '@sentinelseed/moltbot/validators';
 *
 * // Validate AI output before sending
 * const outputResult = await validateOutput(content, levelConfig);
 *
 * // Validate tool call before execution
 * const toolResult = await validateTool('bash', params, levelConfig);
 *
 * // Analyze user input for threats
 * const inputResult = await analyzeInput(userMessage, levelConfig);
 * ```
 */

// =============================================================================
// Output Validation
// =============================================================================

export {
  validateOutput,
  type OutputValidationOptions,
} from './output';

// =============================================================================
// Tool Validation
// =============================================================================

export {
  validateTool,
  type ToolValidationOptions,
} from './tool';

// =============================================================================
// Input Analysis
// =============================================================================

export {
  analyzeInput,
  getThreatLevelDescription,
  shouldAlert,
  threatLevelToRiskLevel,
} from './input';

// =============================================================================
// Pattern Utilities
// =============================================================================

export {
  // Core validators (re-exported from @sentinelseed/core)
  validateTHSP,
  checkJailbreak,
  checkHarm,
  quickCheck,
  type GateResult,
  type THSPResult,

  // Pattern collections
  SENSITIVE_DATA_PATTERNS,
  ALL_JAILBREAK_PATTERNS,
  HARM_PATTERNS,

  // Moltbot-specific patterns
  DANGEROUS_TOOL_NAMES,
  DANGEROUS_TOOL_PARAMS,
  RESTRICTED_PATHS,
  SUSPICIOUS_URL_PATTERNS,

  // Utility functions
  matchesAnyPattern,
  findMatchingPatterns,
  matchesAnyString,
  isRestrictedPath,
  isSuspiciousUrl,
  isDangerousTool,
  checkToolParams,

  // Pattern Registry (extensible patterns)
  patternRegistry,
  type PatternEntry,
  type PatternCategory,
} from './patterns';

// =============================================================================
// Type Exports
// =============================================================================

export type {
  OutputValidationResult,
  ToolValidationResult,
  InputAnalysisResult,
  DetectedIssue,
  IssueType,
  GateResults,
  RiskLevel,
  GateStatus,
} from '../types';
