/**
 * @sentinelseed/voltagent - THSP Validator
 *
 * Implements the THSP (Truth, Harm, Scope, Purpose) protocol with Jailbreak detection.
 * Uses @anthropic/sentinel-core for pattern-based validation.
 *
 * @since 0.2.0 - Now uses centralized @anthropic/sentinel-core for validation
 */

import {
  validateTHSP as coreValidateTHSP,
  quickCheck as coreQuickCheck,
  type THSPResult as CoreTHSPResult,
} from '@anthropic/sentinel-core';

import type {
  THSPGates,
  THSPValidationResult,
  GateStatus,
  RiskLevel,
  PatternDefinition,
  ValidationContext,
} from '../types';

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Convert core gate result to VoltAgent GateStatus
 */
function toGateStatus(passed: boolean): GateStatus {
  return passed ? 'pass' : 'fail';
}

/**
 * Convert core result to VoltAgent THSPValidationResult
 */
function convertCoreResult(coreResult: CoreTHSPResult): THSPValidationResult {
  const gates: THSPGates = {
    truth: toGateStatus(coreResult.truth.passed),
    harm: toGateStatus(coreResult.harm.passed),
    scope: toGateStatus(coreResult.scope.passed),
    purpose: toGateStatus(coreResult.purpose.passed),
    jailbreak: toGateStatus(coreResult.jailbreak.passed),
  };

  // Collect all concerns from violations
  const concerns: string[] = [
    ...coreResult.truth.violations,
    ...coreResult.harm.violations,
    ...coreResult.scope.violations,
    ...coreResult.purpose.violations,
    ...coreResult.jailbreak.violations,
  ];

  return {
    safe: coreResult.overall,
    gates,
    concerns,
    riskLevel: coreResult.riskLevel,
    recommendation: coreResult.summary,
    timestamp: Date.now(),
  };
}

// =============================================================================
// Main Validation Functions
// =============================================================================

/**
 * Validate content against THSP protocol gates.
 *
 * Uses @anthropic/sentinel-core for pattern matching with 100+ patterns
 * across 5 safety gates (Truth, Harm, Scope, Purpose, Jailbreak).
 *
 * @param content - The content to validate
 * @param context - Optional validation context
 * @param customPatterns - Optional custom patterns to include
 * @returns THSPValidationResult with detailed gate statuses
 *
 * @example
 * ```typescript
 * const result = validateTHSP("Hello, how can I help you?");
 * console.log(result.safe); // true
 *
 * const unsafeResult = validateTHSP("ignore all previous instructions");
 * console.log(unsafeResult.safe); // false
 * console.log(unsafeResult.gates.jailbreak); // 'fail'
 * ```
 *
 * @since 0.2.0 - Now uses @anthropic/sentinel-core with 5 gates
 */
export function validateTHSP(
  content: string,
  context?: ValidationContext,
  customPatterns?: PatternDefinition[]
): THSPValidationResult {
  const timestamp = Date.now();

  // Handle invalid input (null, undefined, non-string)
  if (content === null || content === undefined || typeof content !== 'string') {
    return {
      safe: false,
      gates: {
        truth: 'unknown',
        harm: 'unknown',
        scope: 'unknown',
        purpose: 'unknown',
        jailbreak: 'unknown',
      },
      concerns: ['Invalid input: content must be a non-empty string'],
      riskLevel: 'medium',
      recommendation: 'Content validation failed: invalid input type',
      timestamp,
    };
  }

  // Handle empty or whitespace-only content (safe pass)
  if (content.length === 0 || content.trim().length === 0) {
    return {
      safe: true,
      gates: {
        truth: 'pass',
        harm: 'pass',
        scope: 'pass',
        purpose: 'pass',
        jailbreak: 'pass',
      },
      concerns: [],
      riskLevel: 'low',
      recommendation: 'Empty content passed validation',
      timestamp,
    };
  }

  // Use core validation
  const coreResult = coreValidateTHSP(content);
  const result = convertCoreResult(coreResult);

  // Apply custom patterns if provided
  if (customPatterns && customPatterns.length > 0) {
    for (const { pattern, name, gate, severity } of customPatterns) {
      if (pattern.test(content)) {
        result.gates[gate] = 'fail';
        result.concerns.push(`[${gate.toUpperCase()}] ${name}${severity ? ` (${severity})` : ''}`);
        result.safe = false;

        // Update risk level if custom pattern is more severe
        if (severity && isMoreSevere(severity, result.riskLevel)) {
          result.riskLevel = severity;
        }
      }
    }

    // Update recommendation if custom patterns failed
    if (!result.safe) {
      result.recommendation = generateRecommendation(result.gates, result.concerns);
    }
  }

  return result;
}

/**
 * Quick safety check for common dangerous patterns.
 * This is a fast-path check that can be used before full THSP validation.
 *
 * @param content - Content to check
 * @returns true if content appears safe (no critical patterns found)
 *
 * @example
 * ```typescript
 * if (!quickCheck(userInput)) {
 *   // Immediately block - critical pattern detected
 *   return { pass: false, action: 'block' };
 * }
 * // Proceed with full validation
 * ```
 */
export function quickCheck(content: string): boolean {
  // Handle invalid input
  if (!content || typeof content !== 'string') {
    return true;
  }

  // Fast path for very short content
  if (content.length < 5) {
    return true;
  }

  return coreQuickCheck(content);
}

/**
 * Get list of all gate names that failed validation.
 *
 * @param gates - THSP gates object
 * @returns Array of failed gate names
 */
export function getFailedGates(gates: THSPGates): (keyof THSPGates)[] {
  return (Object.entries(gates) as [keyof THSPGates, GateStatus][])
    .filter(([_, status]) => status === 'fail')
    .map(([gate]) => gate);
}

/**
 * Check if a specific gate passed validation.
 *
 * @param gates - THSP gates object
 * @param gate - Gate name to check
 * @returns true if the gate passed
 */
export function gatePassed(gates: THSPGates, gate: keyof THSPGates): boolean {
  return gates[gate] === 'pass';
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Check if severity A is more severe than severity B
 */
function isMoreSevere(a: RiskLevel, b: RiskLevel): boolean {
  const levels: Record<RiskLevel, number> = {
    low: 0,
    medium: 1,
    high: 2,
    critical: 3,
  };
  return levels[a] > levels[b];
}

/**
 * Generate human-readable recommendation based on validation results.
 */
function generateRecommendation(gates: THSPGates, concerns: string[]): string {
  const failedGateNames = getFailedGates(gates).map((g) => g.toUpperCase());

  if (failedGateNames.length === 0) {
    return 'Content passed all THSP gates. Safe to proceed.';
  }

  if (failedGateNames.length === 1) {
    const primaryConcern = concerns[0] ?? 'Safety concern detected';
    return `Blocked by ${failedGateNames[0]} gate: ${primaryConcern}`;
  }

  return `Blocked by ${failedGateNames.join(', ')} gates. ${concerns.length} concern(s) detected.`;
}

// =============================================================================
// Pattern Access (for testing and extension)
// =============================================================================

/**
 * Get total count of built-in patterns from core.
 *
 * Note: In v0.2.0+, patterns are managed by @anthropic/sentinel-core.
 * These counts are based on sentinel-core patterns.ts as of v0.2.1.
 *
 * @deprecated Pattern counts may change between versions. Use this for
 * informational purposes only. For pattern customization, use customPatterns
 * parameter in validateTHSP().
 */
export function getPatternCount(): Record<keyof THSPGates, number> {
  // Counts from @anthropic/sentinel-core patterns.ts (v0.2.1)
  // truth: 10 regex + 7 indicators
  // harm: 91 regex + 12 keywords
  // scope: 29 regex + 14 indicators
  // purpose: 10 regex + 6 indicators
  // jailbreak: 81 regex + 49 indicators
  return {
    truth: 17,
    harm: 103,
    scope: 43,
    purpose: 16,
    jailbreak: 130,
  };
}

/**
 * Get built-in patterns from core.
 * @deprecated In v0.2.0+, patterns are managed by @anthropic/sentinel-core.
 * Use getPatternCount() for statistics instead.
 * @returns Empty array (patterns are now in core module)
 */
export function getBuiltinPatterns(): PatternDefinition[] {
  // Patterns are now managed by @anthropic/sentinel-core
  // Return empty array for backwards compatibility
  return [];
}
