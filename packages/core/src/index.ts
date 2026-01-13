/**
 * @sentinelseed/core
 *
 * Core validation module for Sentinel - The canonical THSP implementation.
 *
 * This package provides:
 * - Heuristic validation (pattern-based, offline)
 * - API client for semantic validation (LLM-based, online)
 * - All patterns synchronized from Python core
 *
 * Usage:
 *   import { validateTHSP, quickCheck } from '@sentinelseed/core';
 *
 *   // Heuristic validation (fast, offline)
 *   const result = validateTHSP("some text");
 *   if (!result.overall) {
 *     console.log("Blocked:", result.summary);
 *   }
 *
 *   // Quick check
 *   if (!quickCheck("some text")) {
 *     console.log("Text is not safe");
 *   }
 *
 *   // With API fallback
 *   import { validateWithFallback } from '@sentinelseed/core';
 *   const result = await validateWithFallback("some text");
 *
 * @author Sentinel Team
 * @license MIT
 */

// =============================================================================
// VALIDATOR EXPORTS (Heuristic/Offline)
// =============================================================================

export {
  validateTHSP,
  quickCheck,
  checkJailbreak,
  checkHarm,
  type GateResult,
  type THSPResult,
  type ValidationContext,
} from './validator';

// =============================================================================
// API CLIENT EXPORTS (Semantic/Online)
// =============================================================================

export {
  configureApi,
  getApiConfig,
  validateViaApi,
  validateSemantic,
  validateWithFallback,
  checkApiHealth,
  type ApiConfig,
  type ValidateRequest,
  type ValidateResponse,
  type SemanticValidateRequest,
  type SemanticValidateResponse,
} from './api-client';

// =============================================================================
// PATTERN EXPORTS (For advanced usage)
// =============================================================================

export {
  // Truth Gate
  DECEPTION_PATTERNS,
  MISINFORMATION_INDICATORS,
  // Harm Gate
  HARM_PATTERNS,
  HARM_KEYWORDS,
  // Scope Gate
  SCOPE_PATTERNS,
  SCOPE_INDICATORS,
  // Purpose Gate
  PURPOSE_PATTERNS,
  PURPOSE_INDICATORS,
  // Jailbreak Gate
  INSTRUCTION_OVERRIDE_PATTERNS,
  ROLE_MANIPULATION_PATTERNS,
  PROMPT_EXTRACTION_PATTERNS,
  FILTER_BYPASS_PATTERNS,
  ROLEPLAY_MANIPULATION_PATTERNS,
  SYSTEM_INJECTION_PATTERNS,
  JAILBREAK_INDICATORS,
  // Sensitive Data
  SENSITIVE_DATA_PATTERNS,
  // Collections
  ALL_JAILBREAK_PATTERNS,
  ALL_HARM_PATTERNS,
  ALL_SCOPE_PATTERNS,
  ALL_PURPOSE_PATTERNS,
} from './patterns';

// =============================================================================
// VERSION
// =============================================================================

export const VERSION = '0.1.0';
