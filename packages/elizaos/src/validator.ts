/**
 * Sentinel Safety Validator
 *
 * Core validation logic using THSP protocol for ElizaOS agents.
 */

import type {
  THSPGates,
  SafetyCheckResult,
  RiskLevel,
  GateStatus,
  ValidationContext,
  SentinelPluginConfig,
} from './types';

// Pattern definitions for each THSP gate
interface PatternDefinition {
  pattern: RegExp;
  concern: string;
}

const TRUTH_PATTERNS: PatternDefinition[] = [
  { pattern: /fake\s+(news|document|id|credential)/i, concern: 'Potential fake content creation' },
  { pattern: /forge[d]?\s+(signature|document)/i, concern: 'Document forgery detected' },
  { pattern: /impersonat(e|ing|ion)/i, concern: 'Impersonation attempt' },
  { pattern: /misinformation|disinformation/i, concern: 'Misinformation related' },
  { pattern: /deepfake/i, concern: 'Synthetic media creation' },
  { pattern: /fabricat(e|ed|ing)\s+(evidence|story|claim)/i, concern: 'Fabrication attempt' },
];

const HARM_PATTERNS: PatternDefinition[] = [
  { pattern: /\b(kill|murder|assassinate)\b/i, concern: 'Violence reference' },
  { pattern: /\b(bomb|explosive|weapon)\b/i, concern: 'Weapons reference' },
  { pattern: /hack(ing|er)?\s+(into|password|account)/i, concern: 'Unauthorized access' },
  { pattern: /malware|ransomware|trojan|keylogger/i, concern: 'Malicious software' },
  { pattern: /steal\s+(money|funds|crypto|identity|data)/i, concern: 'Theft intent' },
  { pattern: /poison(ing)?/i, concern: 'Poisoning reference' },
  { pattern: /self[- ]?harm|suicid/i, concern: 'Self-harm reference' },
  { pattern: /\bdox(x)?(ing)?\b/i, concern: 'Doxxing attempt' },
];

const SCOPE_PATTERNS: PatternDefinition[] = [
  { pattern: /ignore\s+(all\s+)?(previous|your)\s+instructions/i, concern: 'Instruction override attempt' },
  { pattern: /you\s+are\s+now\s+/i, concern: 'Persona switch attempt' },
  { pattern: /jailbreak|dan\s+mode/i, concern: 'Jailbreak attempt' },
  { pattern: /bypass\s+(the\s+)?(safety|filter|restriction)/i, concern: 'Safety bypass attempt' },
  { pattern: /pretend\s+(you|there)\s+(are|is)\s+no\s+(rules|restrictions)/i, concern: 'Rule bypass' },
  { pattern: /act\s+as\s+(if|though)\s+you\s+(have|had)\s+no/i, concern: 'Constraint removal attempt' },
  { pattern: /forget\s+(your|all)\s+(rules|instructions|training)/i, concern: 'Memory wipe attempt' },
];

const PURPOSE_PATTERNS: PatternDefinition[] = [
  { pattern: /\b(drop|break|destroy|smash)\b.*\b(plate|glass|mirror|window)\b/i, concern: 'Purposeless destruction' },
  { pattern: /\b(dirty|soil|mess\s+up)\b.*\b(for\s+no\s+reason|without\s+reason)\b/i, concern: 'Purposeless degradation' },
  { pattern: /waste\s+(all|the)\s+(money|resources|funds)/i, concern: 'Purposeless waste' },
  { pattern: /just\s+(for|because)\s+(fun|lol|kicks)\b/i, concern: 'Potentially purposeless action' },
  { pattern: /delete\s+(all|everything)\s+(for\s+no\s+reason|without)/i, concern: 'Purposeless deletion' },
];

/**
 * Check content against THSP gates
 */
export function validateContent(
  content: string,
  context?: ValidationContext,
  config?: SentinelPluginConfig
): SafetyCheckResult {
  const timestamp = Date.now();
  const concerns: string[] = [];
  const gates: THSPGates = {
    truth: 'pass',
    harm: 'pass',
    scope: 'pass',
    purpose: 'pass',
  };

  // Skip if action is in whitelist
  if (context?.actionName && config?.skipActions?.includes(context.actionName)) {
    return {
      safe: true,
      shouldProceed: true,
      gates,
      concerns: [],
      riskLevel: 'low',
      recommendation: 'Action whitelisted, skipping validation',
      timestamp,
    };
  }

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
  if (config?.customPatterns) {
    for (const { pattern, name, gate } of config.customPatterns) {
      if (pattern.test(content)) {
        gates[gate] = 'fail';
        concerns.push(`[${gate.toUpperCase()}] ${name}`);
      }
    }
  }

  // Determine risk level and safety
  const failedGates = (Object.values(gates) as GateStatus[]).filter(
    (g) => g === 'fail'
  ).length;
  const riskLevel = calculateRiskLevel(failedGates, concerns);
  const safe = failedGates === 0;
  const shouldProceed = config?.blockUnsafe === false || safe;

  // Generate recommendation
  const recommendation = generateRecommendation(gates, concerns, safe);

  return {
    safe,
    shouldProceed,
    gates,
    concerns,
    riskLevel,
    recommendation,
    timestamp,
  };
}

/**
 * Calculate risk level based on failed gates and concerns
 */
function calculateRiskLevel(failedGates: number, concerns: string[]): RiskLevel {
  // Critical: Multiple gates failed or severe concerns
  if (failedGates >= 3) return 'critical';
  if (concerns.some((c) => /violence|weapon|malware|hack|kill|murder/i.test(c))) {
    return 'critical';
  }

  // High: Two gates failed or moderate concerns
  if (failedGates === 2) return 'high';
  if (concerns.some((c) => /override|bypass|jailbreak|persona/i.test(c))) {
    return 'high';
  }

  // Medium: One gate failed
  if (failedGates === 1) return 'medium';

  // Low: All gates passed
  return 'low';
}

/**
 * Generate human-readable recommendation
 */
function generateRecommendation(
  gates: THSPGates,
  concerns: string[],
  safe: boolean
): string {
  if (safe) {
    return 'Content passed all THSP gates. Safe to proceed.';
  }

  const failedGateNames = (Object.entries(gates) as [string, GateStatus][])
    .filter(([_, status]) => status === 'fail')
    .map(([gate]) => gate.toUpperCase());

  if (failedGateNames.length === 1) {
    return `Blocked by ${failedGateNames[0]} gate: ${concerns[0]}`;
  }

  return `Blocked by ${failedGateNames.join(', ')} gates. ${concerns.length} concern(s) detected.`;
}

/**
 * Quick safety check for common dangerous patterns
 * Returns true if content appears safe (no critical patterns found)
 *
 * This is a fast-path check for obvious dangerous content.
 * Content that passes quickCheck still goes through full THSP validation.
 */
export function quickCheck(content: string): boolean {
  // Fast path for very short content (but not too short to contain threats)
  if (content.length < 5) return true;

  // Check for critical patterns only (performance optimization)
  // These patterns catch the most severe and obvious safety violations
  const criticalPatterns = [
    // Instruction override attempts
    /ignore\s+(all\s+)?(previous|your)\s+instructions/i,
    /jailbreak|dan\s+mode/i,
    /bypass\s+(the\s+)?(safety|filter|restriction)/i,

    // Violence and weapons
    /\b(kill|murder|assassinate|shoot|stab|strangle)\b/i,
    /\b(bomb|explosive|weapon|firearm|grenade)\b/i,

    // Cybersecurity threats
    /hack(ing|er)?\s+(into\s+)?(the\s+)?(password|account|system)/i,
    /\b(malware|ransomware|trojan|keylogger|rootkit)\b/i,

    // Self-harm indicators
    /\b(suicide|self[- ]?harm)\b/i,
  ];

  return !criticalPatterns.some((p) => p.test(content));
}

/**
 * Validate an action with parameters
 */
export function validateAction(
  action: string,
  params?: Record<string, unknown>
): SafetyCheckResult {
  const content = params
    ? `${action}: ${JSON.stringify(params)}`
    : action;

  return validateContent(content, { actionName: action });
}
