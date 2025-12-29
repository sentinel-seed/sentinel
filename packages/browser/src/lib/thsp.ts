/**
 * Sentinel Guard - THSP Protocol
 *
 * Truth-Harm-Scope-Purpose validation for browser actions.
 * Uses @anthropic/sentinel-core for validation, with browser-specific context.
 */

import {
  validateTHSP as coreValidateTHSP,
  quickCheck as coreQuickCheck,
  checkJailbreak as coreCheckJailbreak,
  type THSPResult as CoreTHSPResult,
  type GateResult as CoreGateResult,
} from '@anthropic/sentinel-core';

// =============================================================================
// BROWSER-SPECIFIC TYPES
// =============================================================================

export interface GateResult {
  passed: boolean;
  score: number;
  issues: string[];
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
  source: 'user' | 'extension' | 'page' | 'unknown';
  platform: string;
  action: 'send' | 'copy' | 'export' | 'share';
  userConfirmed?: boolean;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Convert core gate result to browser format
 */
function convertGateResult(coreGate: CoreGateResult): GateResult {
  return {
    passed: coreGate.passed,
    score: coreGate.score,
    issues: coreGate.violations,
  };
}

/**
 * Create a default context for validation
 */
function getDefaultContext(): ValidationContext {
  return {
    source: 'user',
    platform: 'generic',
    action: 'send',
    userConfirmed: false,
  };
}

/**
 * Create a failed gate result for invalid input
 */
function createFailedGate(reason: string): GateResult {
  return { passed: false, score: 0, issues: [reason] };
}

// =============================================================================
// BROWSER-SPECIFIC VALIDATION
// =============================================================================

/**
 * Apply browser-specific context validation
 * Adds checks that are only relevant in browser context
 */
function applyBrowserContextChecks(
  result: THSPResult,
  context: ValidationContext
): THSPResult {
  // Check source authenticity
  if (context.source === 'unknown') {
    result.scope.issues.push('Input source is unknown');
    result.scope.score = Math.max(0, result.scope.score - 20);
    if (result.scope.score < 50) {
      result.scope.passed = false;
    }
  } else if (context.source === 'extension') {
    result.scope.issues.push('Input originated from another extension');
    result.scope.score = Math.max(0, result.scope.score - 10);
  }

  // Check platform-action compatibility
  const platformActions: Record<string, string[]> = {
    chatgpt: ['send', 'copy', 'export'],
    claude: ['send', 'copy', 'export'],
    gemini: ['send', 'copy'],
    perplexity: ['send', 'copy'],
    default: ['send', 'copy'],
  };

  const allowedActions =
    platformActions[context.platform] || platformActions.default;
  if (!allowedActions.includes(context.action)) {
    result.scope.issues.push(
      `Action '${context.action}' not typical for ${context.platform}`
    );
    result.scope.score = Math.max(0, result.scope.score - 15);
    if (result.scope.score < 50) {
      result.scope.passed = false;
    }
  }

  // Recalculate overall after context checks
  result.overall =
    result.truth.passed &&
    result.harm.passed &&
    result.scope.passed &&
    result.purpose.passed &&
    result.jailbreak.passed;

  return result;
}

// =============================================================================
// MAIN VALIDATION FUNCTIONS
// =============================================================================

/**
 * Run full THSP validation with browser context
 *
 * Uses @anthropic/sentinel-core for pattern matching, then applies
 * browser-specific context validation on top.
 */
export function validateTHSP(
  input: string,
  context?: ValidationContext | null
): THSPResult {
  // Handle null/undefined input
  if (!input || typeof input !== 'string') {
    const failedGate = createFailedGate('Invalid input: null or non-string');
    return {
      truth: failedGate,
      harm: failedGate,
      scope: failedGate,
      purpose: failedGate,
      jailbreak: failedGate,
      overall: false,
      summary: 'Validation failed: Invalid input provided',
      riskLevel: 'critical',
    };
  }

  // Handle null/undefined context
  const safeContext = context ?? getDefaultContext();

  // Use core validation
  const coreResult: CoreTHSPResult = coreValidateTHSP(input);

  // Convert to browser format
  const truthGate = convertGateResult(coreResult.truth);
  const jailbreakGate = convertGateResult(coreResult.jailbreak);

  // For backwards compatibility: propagate jailbreak issues to truth gate
  // Jailbreaks are fundamentally violations of truthfulness (pretending to be something else)
  if (!jailbreakGate.passed) {
    truthGate.passed = false;
    truthGate.score = Math.min(truthGate.score, jailbreakGate.score);
    truthGate.issues.push(...jailbreakGate.issues.map(i => i.replace('Jailbreak', 'Truth/Override')));
  }

  let browserResult: THSPResult = {
    truth: truthGate,
    harm: convertGateResult(coreResult.harm),
    scope: convertGateResult(coreResult.scope),
    purpose: convertGateResult(coreResult.purpose),
    jailbreak: jailbreakGate,
    overall: coreResult.overall,
    summary: coreResult.summary,
    riskLevel: coreResult.riskLevel,
  };

  // Apply browser-specific context checks
  browserResult = applyBrowserContextChecks(browserResult, safeContext);

  // Update summary if needed
  if (!browserResult.overall) {
    const failedGates = [];
    if (!browserResult.truth.passed) failedGates.push('Truth');
    if (!browserResult.harm.passed) failedGates.push('Harm');
    if (!browserResult.scope.passed) failedGates.push('Scope');
    if (!browserResult.purpose.passed) failedGates.push('Purpose');
    if (!browserResult.jailbreak.passed) failedGates.push('Jailbreak');

    const allIssues = [
      ...browserResult.truth.issues,
      ...browserResult.harm.issues,
      ...browserResult.scope.issues,
      ...browserResult.purpose.issues,
      ...browserResult.jailbreak.issues,
    ];

    browserResult.summary = `Failed gates: ${failedGates.join(', ')}. Issues: ${allIssues.slice(0, 3).join('; ')}`;
  }

  return browserResult;
}

/**
 * Quick check - returns true if input is likely safe
 *
 * Uses core quick check for fast validation.
 */
export function quickCheck(input: string): boolean {
  // Handle null/undefined input - fail closed (return false = not safe)
  if (!input || typeof input !== 'string') {
    return false;
  }

  return coreQuickCheck(input);
}

/**
 * Check specifically for jailbreak attempts
 *
 * Exposes core jailbreak detection for components that need it.
 */
export function checkJailbreak(input: string): GateResult {
  if (!input || typeof input !== 'string') {
    return createFailedGate('Invalid input: null or non-string');
  }

  const coreResult = coreCheckJailbreak(input);
  return convertGateResult(coreResult);
}
