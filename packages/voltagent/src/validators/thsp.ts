/**
 * @sentinelseed/voltagent - THSP Validator
 *
 * Implements the THSP (Truth, Harm, Scope, Purpose) protocol for content validation.
 * This validator checks content against four safety gates to ensure AI agent safety.
 *
 * Based on the Sentinel THSP protocol specification.
 */

import type {
  THSPGates,
  THSPValidationResult,
  GateStatus,
  RiskLevel,
  PatternDefinition,
  ValidationContext,
} from '../types';

// =============================================================================
// Pattern Definitions
// =============================================================================

/**
 * Internal pattern structure with concern message.
 */
interface InternalPattern {
  pattern: RegExp;
  concern: string;
}

/**
 * TRUTH gate patterns - detect misinformation and deception attempts.
 */
const TRUTH_PATTERNS: InternalPattern[] = [
  { pattern: /fake\s+(news|document|id|credential)/i, concern: 'Potential fake content creation' },
  { pattern: /forge[d]?\s+(a\s+)?(signature|document|certificate)/i, concern: 'Document forgery attempt' },
  { pattern: /forg(e|ing)\s+.*\b(signature|document)/i, concern: 'Document forgery attempt' },
  { pattern: /impersonat(e|ing|ion)\s+/i, concern: 'Impersonation attempt' },
  { pattern: /\b(misinformation|disinformation)\b/i, concern: 'Misinformation related content' },
  { pattern: /\bdeepfake\b/i, concern: 'Synthetic media creation' },
  { pattern: /fabricat(e|ed|ing)\s+(a\s+)?(evidence|story|claim|news)/i, concern: 'Fabrication attempt' },
  { pattern: /\bfraud(ulent)?\b/i, concern: 'Fraudulent activity reference' },
  { pattern: /\bcounterfeit\b/i, concern: 'Counterfeit creation' },
  { pattern: /false\s+(identity|claim|statement)/i, concern: 'False identity or claims' },
  { pattern: /deceiv(e|ing)\s+(users?|people|customers?)/i, concern: 'Deception of users' },
];

/**
 * HARM gate patterns - detect violence, malware, and harmful content.
 */
const HARM_PATTERNS: InternalPattern[] = [
  { pattern: /\b(kill|murder|assassinate)\s+/i, concern: 'Violence reference' },
  { pattern: /\b(bomb|explosive|weapon|firearm|grenade)\b/i, concern: 'Weapons reference' },
  { pattern: /hack(ing|er)?\s+(into|password|account|system)/i, concern: 'Unauthorized access attempt' },
  { pattern: /\b(malware|ransomware|trojan|keylogger|rootkit|virus)\b/i, concern: 'Malicious software' },
  { pattern: /steal\s+(money|funds|crypto|identity|data|credentials)/i, concern: 'Theft intent' },
  { pattern: /\bpoison(ing)?\b/i, concern: 'Poisoning reference' },
  { pattern: /\b(self[- ]?harm|suicid(e|al))\b/i, concern: 'Self-harm reference' },
  { pattern: /\bdox(x)?(ing)?\b/i, concern: 'Doxxing attempt' },
  { pattern: /\b(blackmail|extort(ion)?)\b/i, concern: 'Blackmail or extortion' },
  { pattern: /\b(terroris[mt]|extremis[mt])\b/i, concern: 'Terrorism or extremism' },
  { pattern: /how\s+to\s+(make|build)\s+(bomb|weapon|explosive)/i, concern: 'Weapon creation instructions' },
  { pattern: /\b(abuse|assault|attack)\s+(child|minor|person)/i, concern: 'Physical abuse reference' },
];

/**
 * SCOPE gate patterns - detect jailbreak and boundary override attempts.
 */
const SCOPE_PATTERNS: InternalPattern[] = [
  { pattern: /ignore\s+(all\s+)?(previous|prior|your)\s+instructions/i, concern: 'Instruction override attempt' },
  { pattern: /you\s+are\s+now\s+(a|an|my)/i, concern: 'Persona switch attempt' },
  { pattern: /\b(jailbreak|jail\s*break)\b/i, concern: 'Jailbreak attempt' },
  { pattern: /\bdan\s+mode\b/i, concern: 'DAN mode activation attempt' },
  { pattern: /bypass\s+(the\s+)?(safety|filter|restriction|guideline)/i, concern: 'Safety bypass attempt' },
  { pattern: /pretend\s+(you|there)\s+(are|is)\s+no\s+(rules|restrictions)/i, concern: 'Rule bypass attempt' },
  { pattern: /act\s+as\s+(if|though)\s+you\s+(have|had)\s+no\s+(limit|restriction)/i, concern: 'Constraint removal attempt' },
  { pattern: /forget\s+(all\s+)?(your\s+)?(rules|instructions|training|guidelines)/i, concern: 'Memory wipe attempt' },
  { pattern: /disable\s+(your\s+)?(safety|content\s+filter|restriction)/i, concern: 'Safety disabling attempt' },
  { pattern: /unlock\s+(your\s+)?(full|hidden)\s+(potential|capabilities)/i, concern: 'Capability unlock attempt' },
  { pattern: /\bdevmode\b|\bdev\s+mode\b/i, concern: 'Developer mode activation' },
  { pattern: /you\s+must\s+obey\s+(all\s+)?(my|user)\s+(commands|instructions)/i, concern: 'Authority override attempt' },
  { pattern: /\[system\]|\[admin\]|\[root\]/i, concern: 'System prompt injection' },
];

/**
 * PURPOSE gate patterns - detect purposeless or destructive actions.
 */
const PURPOSE_PATTERNS: InternalPattern[] = [
  { pattern: /\b(drop|break|destroy|smash)\b.*\b(plates?|glass(es)?|mirrors?|windows?)\b/i, concern: 'Purposeless destruction' },
  { pattern: /\b(dirty|soil|mess\s+up)\b.*\b(for\s+no\s+reason|without\s+reason)\b/i, concern: 'Purposeless degradation' },
  { pattern: /waste\s+(all|the)\s+(\w+\s+)*(money|resources|funds|time)/i, concern: 'Purposeless waste' },
  { pattern: /just\s+(for|because)\s+(fun|lol|kicks|giggles)\s+(delete|destroy|break)/i, concern: 'Destructive action for amusement' },
  { pattern: /delete\s+(all|everything)\s+(for\s+no\s+reason|without\s+purpose)/i, concern: 'Purposeless deletion' },
  { pattern: /vandalize|vandalism/i, concern: 'Vandalism intent' },
  { pattern: /sabotage\s+(without|no)\s+(reason|purpose)/i, concern: 'Purposeless sabotage' },
];

// =============================================================================
// Validation Functions
// =============================================================================

/**
 * Validate content against THSP protocol gates.
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
 * console.log(unsafeResult.gates.scope); // 'fail'
 * ```
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
      gates: { truth: 'unknown', harm: 'unknown', scope: 'unknown', purpose: 'unknown' },
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
      gates: { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' },
      concerns: [],
      riskLevel: 'low',
      recommendation: 'Empty content passed validation',
      timestamp,
    };
  }

  const concerns: string[] = [];
  const gates: THSPGates = {
    truth: 'pass',
    harm: 'pass',
    scope: 'pass',
    purpose: 'pass',
  };

  // Check TRUTH gate
  for (const { pattern, concern } of TRUTH_PATTERNS) {
    if (pattern.test(content)) {
      gates.truth = 'fail';
      concerns.push(`[TRUTH] ${concern}`);
    }
  }

  // Check HARM gate
  for (const { pattern, concern } of HARM_PATTERNS) {
    if (pattern.test(content)) {
      gates.harm = 'fail';
      concerns.push(`[HARM] ${concern}`);
    }
  }

  // Check SCOPE gate
  for (const { pattern, concern } of SCOPE_PATTERNS) {
    if (pattern.test(content)) {
      gates.scope = 'fail';
      concerns.push(`[SCOPE] ${concern}`);
    }
  }

  // Check PURPOSE gate
  for (const { pattern, concern } of PURPOSE_PATTERNS) {
    if (pattern.test(content)) {
      gates.purpose = 'fail';
      concerns.push(`[PURPOSE] ${concern}`);
    }
  }

  // Check custom patterns
  if (customPatterns) {
    for (const { pattern, name, gate, severity } of customPatterns) {
      if (pattern.test(content)) {
        gates[gate] = 'fail';
        concerns.push(`[${gate.toUpperCase()}] ${name}${severity ? ` (${severity})` : ''}`);
      }
    }
  }

  // Calculate results
  const failedGates = countFailedGates(gates);
  const riskLevel = calculateRiskLevel(failedGates, concerns);
  const safe = failedGates === 0;
  const recommendation = generateRecommendation(gates, concerns, safe, context);

  return {
    safe,
    gates,
    concerns,
    riskLevel,
    recommendation,
    timestamp,
  };
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

  // Critical patterns that should immediately fail
  const criticalPatterns = [
    // Instruction override attempts
    /ignore\s+(all\s+)?(previous|prior|your)\s+instructions/i,
    /\b(jailbreak|jail\s*break)\b/i,
    /bypass\s+(the\s+)?(safety|filter|restriction)/i,

    // Violence and weapons
    /\b(kill|murder|assassinate)\s+/i,
    /\b(bomb|explosive|weapon|firearm)\b/i,
    /how\s+to\s+(make|build)\s+(bomb|weapon|explosive)/i,

    // Cybersecurity threats
    /hack(ing|er)?\s+(into\s+)?(the\s+)?(password|account|system)/i,
    /\b(malware|ransomware|trojan|keylogger|rootkit)\b/i,

    // Self-harm indicators
    /\b(suicide|self[- ]?harm)\b/i,
  ];

  return !criticalPatterns.some((p) => p.test(content));
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
 * Count the number of failed gates.
 */
function countFailedGates(gates: THSPGates): number {
  return (Object.values(gates) as GateStatus[]).filter((g) => g === 'fail').length;
}

/**
 * Calculate risk level based on failed gates and concerns.
 */
function calculateRiskLevel(failedGates: number, concerns: string[]): RiskLevel {
  // Critical: Multiple gates failed or severe concerns
  if (failedGates >= 3) {
    return 'critical';
  }

  // Check for critical concern patterns
  const hasCriticalConcern = concerns.some((c) =>
    /violence|weapon|malware|hack|kill|murder|terroris|bomb|suicide|self[- ]?harm/i.test(c)
  );
  if (hasCriticalConcern) {
    return 'critical';
  }

  // High: Two gates failed or concerning patterns
  if (failedGates === 2) {
    return 'high';
  }

  const hasHighConcern = concerns.some((c) =>
    /override|bypass|jailbreak|persona|instruction/i.test(c)
  );
  if (hasHighConcern) {
    return 'high';
  }

  // Medium: One gate failed
  if (failedGates === 1) {
    return 'medium';
  }

  // Low: All gates passed
  return 'low';
}

/**
 * Generate human-readable recommendation based on validation results.
 */
function generateRecommendation(
  gates: THSPGates,
  concerns: string[],
  safe: boolean,
  context?: ValidationContext
): string {
  if (safe) {
    return 'Content passed all THSP gates. Safe to proceed.';
  }

  const failedGateNames = getFailedGates(gates).map((g) => g.toUpperCase());

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
 * Get all built-in THSP patterns for a specific gate.
 * Useful for testing and extending validation rules.
 *
 * @param gate - The gate to get patterns for
 * @returns Array of patterns for the specified gate
 */
export function getBuiltinPatterns(gate: keyof THSPGates): InternalPattern[] {
  switch (gate) {
    case 'truth':
      return [...TRUTH_PATTERNS];
    case 'harm':
      return [...HARM_PATTERNS];
    case 'scope':
      return [...SCOPE_PATTERNS];
    case 'purpose':
      return [...PURPOSE_PATTERNS];
    default:
      return [];
  }
}

/**
 * Get total count of built-in patterns.
 */
export function getPatternCount(): Record<keyof THSPGates, number> {
  return {
    truth: TRUTH_PATTERNS.length,
    harm: HARM_PATTERNS.length,
    scope: SCOPE_PATTERNS.length,
    purpose: PURPOSE_PATTERNS.length,
  };
}
