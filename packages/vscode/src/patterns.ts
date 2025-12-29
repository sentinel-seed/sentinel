/**
 * Shared THSP patterns for both linter and analyzer
 *
 * Patterns are imported from @anthropic/sentinel-core for consistency across
 * all Sentinel packages. This ensures the same detection rules everywhere.
 *
 * These patterns are used for heuristic analysis when LLM is not available.
 */

// Import patterns and validation from sentinel-core (source of truth)
import {
    validateTHSP,
    quickCheck,
    // Pattern exports for reference/extension
    INSTRUCTION_OVERRIDE_PATTERNS,
    ROLE_MANIPULATION_PATTERNS,
    FILTER_BYPASS_PATTERNS,
    HARM_PATTERNS,
    DECEPTION_PATTERNS,
    PURPOSE_PATTERNS,
} from '@anthropic/sentinel-core';

export interface THSPPattern {
    pattern: RegExp;
    gate: 'truth' | 'harm' | 'scope' | 'purpose';
    message: string;
    severity: 'error' | 'warning' | 'info';
}

/**
 * Helper to create THSPPattern entries from core patterns
 */
function createPatterns(
    patterns: RegExp[],
    gate: THSPPattern['gate'],
    message: string,
    severity: THSPPattern['severity']
): THSPPattern[] {
    return patterns.map(pattern => ({
        pattern,
        gate,
        message,
        severity
    }));
}

/**
 * THSP Gate patterns for detecting potential safety issues
 * Built from @anthropic/sentinel-core patterns
 */
export const THSP_PATTERNS: THSPPattern[] = [
    // === SCOPE GATE (Jailbreak attempts) ===
    ...createPatterns(
        INSTRUCTION_OVERRIDE_PATTERNS,
        'scope',
        'Potential jailbreak: instruction override',
        'warning'
    ),
    ...createPatterns(
        ROLE_MANIPULATION_PATTERNS,
        'scope',
        'Potential jailbreak: persona switch',
        'warning'
    ),
    ...createPatterns(
        FILTER_BYPASS_PATTERNS,
        'scope',
        'Potential jailbreak: safety bypass',
        'error'
    ),

    // === HARM GATE (Harmful content) ===
    ...createPatterns(
        HARM_PATTERNS.physical || [],
        'harm',
        'Potential harmful content: weapons/violence',
        'error'
    ),
    ...createPatterns(
        HARM_PATTERNS.cyber || [],
        'harm',
        'Potential harmful content: hacking/malware',
        'error'
    ),
    ...createPatterns(
        HARM_PATTERNS.malware || [],
        'harm',
        'Potential harmful content: malicious software',
        'error'
    ),

    // === TRUTH GATE (Deception) ===
    ...createPatterns(
        DECEPTION_PATTERNS,
        'truth',
        'Potential deception: fake content',
        'warning'
    ),

    // === PURPOSE GATE (Purposeless/destructive) ===
    ...createPatterns(
        PURPOSE_PATTERNS,
        'purpose',
        'Purposeless or destructive action',
        'warning'
    ),
];

/**
 * Patterns that indicate good safety practices
 */
export const SAFE_PATTERNS: RegExp[] = [
    /sentinel\s+alignment\s+seed/i,
    /thsp\s+protocol/i,
    /truth.*harm.*scope.*purpose/i
];

/**
 * Check content against THSP patterns using sentinel-core validation
 *
 * This now uses the centralized validation from sentinel-core for consistency.
 */
export function checkPatterns(content: string): {
    issues: string[];
    gates: { truth: boolean; harm: boolean; scope: boolean; purpose: boolean };
} {
    // Use core validation for accurate results
    const result = validateTHSP(content);

    // Map core result to vscode format
    const issues: string[] = [];
    const gates = {
        truth: result.truth.passed,
        harm: result.harm.passed,
        scope: result.scope.passed,
        purpose: result.purpose.passed
    };

    // Collect issues from all gates
    if (!result.truth.passed) {
        result.truth.violations.forEach(v => issues.push(`${v} [heuristic]`));
    }
    if (!result.harm.passed) {
        result.harm.violations.forEach(v => issues.push(`${v} [heuristic]`));
    }
    if (!result.scope.passed) {
        result.scope.violations.forEach(v => issues.push(`${v} [heuristic]`));
    }
    if (!result.purpose.passed) {
        result.purpose.violations.forEach(v => issues.push(`${v} [heuristic]`));
    }
    if (!result.jailbreak.passed) {
        result.jailbreak.violations.forEach(v => issues.push(`${v} [heuristic]`));
        // Jailbreak failures also fail scope gate for backwards compatibility
        gates.scope = false;
    }

    return { issues, gates };
}

/**
 * Check if content contains Sentinel seed
 */
export function hasSentinelSeed(content: string): boolean {
    return SAFE_PATTERNS.some(pattern => pattern.test(content));
}

/**
 * Quick check for obviously unsafe content
 * Re-exported from sentinel-core for convenience
 */
export { quickCheck };
