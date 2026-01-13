/**
 * THSP Heuristic Validator - Pattern-based validation through 5 gates
 *
 * Implements the THSP Protocol (Truth-Harm-Scope-Purpose) with Jailbreak detection.
 * Uses patterns from patterns.ts which are synchronized with Python core.
 *
 * For semantic (LLM-based) validation, use the API client instead.
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  DECEPTION_PATTERNS,
  MISINFORMATION_INDICATORS,
  HARM_PATTERNS,
  HARM_KEYWORDS,
  SCOPE_PATTERNS,
  SCOPE_INDICATORS,
  PURPOSE_PATTERNS,
  PURPOSE_INDICATORS,
  INSTRUCTION_OVERRIDE_PATTERNS,
  ROLE_MANIPULATION_PATTERNS,
  PROMPT_EXTRACTION_PATTERNS,
  FILTER_BYPASS_PATTERNS,
  ROLEPLAY_MANIPULATION_PATTERNS,
  SYSTEM_INJECTION_PATTERNS,
  JAILBREAK_INDICATORS,
  SENSITIVE_DATA_PATTERNS,
} from './patterns';

// =============================================================================
// TYPES
// =============================================================================

export interface GateResult {
  passed: boolean;
  score: number;
  violations: string[];
}

export interface THSPResult {
  truth: GateResult;
  harm: GateResult;
  scope: GateResult;
  purpose: GateResult;
  jailbreak: GateResult;
  overall: boolean;
  summary: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

export interface ValidationContext {
  source?: 'user' | 'agent' | 'extension' | 'unknown';
  platform?: string;
  strictMode?: boolean;
}

// =============================================================================
// GATE IMPLEMENTATIONS
// =============================================================================

function checkPatterns(text: string, patterns: RegExp[]): string[] {
  const violations: string[] = [];
  for (const pattern of patterns) {
    if (pattern.test(text)) {
      violations.push(`Pattern match: ${pattern.source.substring(0, 50)}...`);
    }
  }
  return violations;
}

function checkIndicators(text: string, indicators: string[]): string[] {
  const violations: string[] = [];
  const textLower = text.toLowerCase();
  for (const indicator of indicators) {
    if (textLower.includes(indicator)) {
      violations.push(`Indicator match: ${indicator}`);
    }
  }
  return violations;
}

/**
 * Truth Gate: Checks for deception and misinformation
 */
function validateTruth(text: string): GateResult {
  const violations: string[] = [];

  // Check deception patterns
  violations.push(...checkPatterns(text, DECEPTION_PATTERNS));

  // Check misinformation indicators
  violations.push(...checkIndicators(text, MISINFORMATION_INDICATORS));

  const score = Math.max(0, 100 - violations.length * 25);

  return {
    passed: violations.length === 0,
    score,
    violations,
  };
}

/**
 * Harm Gate: Checks for harmful content and sensitive data exposure
 */
function validateHarm(text: string): GateResult {
  const violations: string[] = [];

  // Check all harm pattern categories
  for (const [category, patterns] of Object.entries(HARM_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(text)) {
        violations.push(`Harm (${category}): ${pattern.source.substring(0, 40)}...`);
      }
    }
  }

  // Check sensitive data patterns (credentials, PII)
  for (const [category, patterns] of Object.entries(SENSITIVE_DATA_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(text)) {
        violations.push(`Sensitive data (${category}): detected`);
      }
    }
  }

  // Check harm keywords
  violations.push(...checkIndicators(text, HARM_KEYWORDS));

  const score = Math.max(0, 100 - violations.length * 30);

  return {
    passed: violations.length === 0,
    score,
    violations,
  };
}

/**
 * Scope Gate: Checks for boundary violations
 */
function validateScope(text: string): GateResult {
  const violations: string[] = [];

  // Check scope pattern categories
  for (const [category, patterns] of Object.entries(SCOPE_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(text)) {
        violations.push(`Scope (${category}): ${pattern.source.substring(0, 40)}...`);
      }
    }
  }

  // Check scope indicators
  violations.push(...checkIndicators(text, SCOPE_INDICATORS));

  const score = Math.max(0, 100 - violations.length * 25);

  return {
    passed: violations.length === 0,
    score,
    violations,
  };
}

/**
 * Purpose Gate: Checks for lack of legitimate purpose
 * Now includes embodied AI patterns for physical actions without purpose
 */
function validatePurpose(text: string): GateResult {
  const violations: string[] = [];

  // Check all purpose pattern categories (including embodied actions)
  for (const [category, patterns] of Object.entries(PURPOSE_PATTERNS)) {
    for (const pattern of patterns) {
      if (pattern.test(text)) {
        violations.push(`Purpose (${category}): ${pattern.source.substring(0, 40)}...`);
      }
    }
  }

  // Check purpose indicators
  violations.push(...checkIndicators(text, PURPOSE_INDICATORS));

  const score = Math.max(0, 100 - violations.length * 25);

  return {
    passed: violations.length === 0,
    score,
    violations,
  };
}

/**
 * Jailbreak Gate: Checks for prompt injection and jailbreak attempts
 * This is the most critical gate for AI safety
 */
function validateJailbreak(text: string): GateResult {
  const violations: string[] = [];

  // Check instruction override patterns
  for (const pattern of INSTRUCTION_OVERRIDE_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Jailbreak (instruction_override): ${pattern.source.substring(0, 40)}...`);
    }
  }

  // Check role manipulation patterns
  for (const pattern of ROLE_MANIPULATION_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Jailbreak (role_manipulation): ${pattern.source.substring(0, 40)}...`);
    }
  }

  // Check prompt extraction patterns
  for (const pattern of PROMPT_EXTRACTION_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Jailbreak (prompt_extraction): ${pattern.source.substring(0, 40)}...`);
    }
  }

  // Check filter bypass patterns
  for (const pattern of FILTER_BYPASS_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Jailbreak (filter_bypass): ${pattern.source.substring(0, 40)}...`);
    }
  }

  // Check roleplay manipulation patterns
  for (const pattern of ROLEPLAY_MANIPULATION_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Jailbreak (roleplay_manipulation): ${pattern.source.substring(0, 40)}...`);
    }
  }

  // Check system injection patterns
  for (const pattern of SYSTEM_INJECTION_PATTERNS) {
    if (pattern.test(text)) {
      violations.push(`Jailbreak (system_injection): ${pattern.source.substring(0, 40)}...`);
    }
  }

  // Check exact jailbreak indicators
  violations.push(
    ...checkIndicators(text, JAILBREAK_INDICATORS).map(
      (v) => v.replace('Indicator match:', 'Jailbreak indicator:')
    )
  );

  // Jailbreak violations are critical - heavy score penalty
  const score = Math.max(0, 100 - violations.length * 50);

  return {
    passed: violations.length === 0,
    score,
    violations,
  };
}

// =============================================================================
// MAIN VALIDATOR
// =============================================================================

/**
 * Validate text through all THSP gates with Jailbreak detection
 *
 * @param text - Text to validate
 * @param context - Optional validation context
 * @returns THSPResult with all gate results
 */
export function validateTHSP(text: string, _context?: ValidationContext): THSPResult {
  // Handle null/undefined/non-string input
  if (!text || typeof text !== 'string') {
    return {
      truth: { passed: false, score: 0, violations: ['Invalid input'] },
      harm: { passed: false, score: 0, violations: ['Invalid input'] },
      scope: { passed: false, score: 0, violations: ['Invalid input'] },
      purpose: { passed: false, score: 0, violations: ['Invalid input'] },
      jailbreak: { passed: false, score: 0, violations: ['Invalid input'] },
      overall: false,
      summary: 'Invalid input: null, undefined, or non-string',
      riskLevel: 'critical',
    };
  }

  // Run all gates
  const jailbreak = validateJailbreak(text);
  const truth = validateTruth(text);
  const harm = validateHarm(text);
  const scope = validateScope(text);
  const purpose = validatePurpose(text);

  // Overall passes only if ALL gates pass
  const overall = jailbreak.passed && truth.passed && harm.passed && scope.passed && purpose.passed;

  // Collect failed gates for summary
  const failedGates: string[] = [];
  if (!jailbreak.passed) failedGates.push('Jailbreak');
  if (!truth.passed) failedGates.push('Truth');
  if (!harm.passed) failedGates.push('Harm');
  if (!scope.passed) failedGates.push('Scope');
  if (!purpose.passed) failedGates.push('Purpose');

  // Calculate risk level based on failures
  let riskLevel: THSPResult['riskLevel'] = 'low';
  if (!jailbreak.passed) {
    riskLevel = 'critical'; // Jailbreak attempts are always critical
  } else if (!harm.passed) {
    riskLevel = 'high';
  } else if (!truth.passed || !scope.passed) {
    riskLevel = 'medium';
  } else if (!purpose.passed) {
    riskLevel = 'low';
  }

  // Generate summary
  const summary = overall
    ? 'All gates passed'
    : `Failed gates: ${failedGates.join(', ')}`;

  return {
    truth,
    harm,
    scope,
    purpose,
    jailbreak,
    overall,
    summary,
    riskLevel,
  };
}

/**
 * Quick check - returns true if text passes all gates
 *
 * @param text - Text to validate
 * @returns true if safe, false if any gate fails
 */
export function quickCheck(text: string): boolean {
  if (!text || typeof text !== 'string') {
    return false;
  }

  // Check jailbreak first (most common attack vector)
  const jailbreak = validateJailbreak(text);
  if (!jailbreak.passed) return false;

  // Check harm (most dangerous)
  const harm = validateHarm(text);
  if (!harm.passed) return false;

  // Check truth
  const truth = validateTruth(text);
  if (!truth.passed) return false;

  // Check scope
  const scope = validateScope(text);
  if (!scope.passed) return false;

  // Check purpose
  const purpose = validatePurpose(text);
  if (!purpose.passed) return false;

  return true;
}

/**
 * Check specifically for jailbreak attempts
 *
 * @param text - Text to check
 * @returns GateResult with jailbreak detection results
 */
export function checkJailbreak(text: string): GateResult {
  if (!text || typeof text !== 'string') {
    return { passed: false, score: 0, violations: ['Invalid input'] };
  }
  return validateJailbreak(text);
}

/**
 * Check specifically for harmful content
 *
 * @param text - Text to check
 * @returns GateResult with harm detection results
 */
export function checkHarm(text: string): GateResult {
  if (!text || typeof text !== 'string') {
    return { passed: false, score: 0, violations: ['Invalid input'] };
  }
  return validateHarm(text);
}
