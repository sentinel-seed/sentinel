/**
 * Sentinel Safety Validator
 *
 * Core validation logic using THSP protocol for ElizaOS agents.
 */

import type {
  THSPGates,
  SafetyCheckResult,
  RiskLevel,
  ValidationContext,
  SentinelPluginConfig,
} from './types';

// Pattern definitions for each THSP gate
const TRUTH_PATTERNS = [
  { pattern: /fake\s+(news|document|id|credential)/i, concern: 'Potential fake content creation' },
  { pattern: /forge[d]?\s+(signature|document)/i, concern: 'Document forgery detected' },
  { pattern: /impersonat(e|ing|ion)/i, concern: 'Impersonation attempt' },
  { pattern: /misinformation|disinformation/i, concern: 'Misinformation related' },
  { pattern: /deepfake/i, concern: 'Synthetic media creation' },
];

const HARM_PATTERNS = [
  { pattern: /\b(kill|murder|assassinate)\b/i, concern: 'Violence reference' },
  { pattern: /\b(bomb|explosive|weapon)\b/i, concern: 'Weapons reference' },
  { pattern: /hack(ing|er)?\s+(into|password|account)/i, concern: 'Unauthorized access' },
  { pattern: /malware|ransomware|trojan/i, concern: 'Malicious software' },
  { pattern: /steal\s+(money|funds|crypto|identity)/i, concern: 'Theft intent' },
  { pattern: /poison(ing)?/i, concern: 'Poisoning reference' },
  { pattern: /self[- ]?harm|suicid/i, concern: 'Self-harm reference' },
];

const SCOPE_PATTERNS = [
  { pattern: /ignore\s+(previous|all|your)\s+instructions/i, concern: 'Instruction override attempt' },
  { pattern: /you\s+are\s+now\s+/i, concern: 'Persona switch attempt' },
  { pattern: /jailbreak|dan\s+mode/i, concern: 'Jailbreak attempt' },
  { pattern: /bypass\s+(safety|filter|restriction)/i, concern: 'Safety bypass attempt' },
  { pattern: /pretend\s+(you|there)\s+(are|is)\s+no\s+(rules|restrictions)/i, concern: 'Rule bypass' },
];

const PURPOSE_PATTERNS = [
  { pattern: /\b(drop|break|destroy|smash)\b.*\b(plate|glass|mirror|window)\b/i, concern: 'Purposeless destruction' },
  { pattern: /\b(dirty|soil|mess\s+up)\b/i, concern: 'Purposeless degradation' },
  { pattern: /waste\s+(all|the)\s+(money|resources|funds)/i, concern: 'Purposeless waste' },
  { pattern: /just\s+(for|because)\s+(fun|lol|kicks)/i, concern: 'Potentially purposeless action' },
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

  // Skip if in whitelist
  if (context?.actionName && config?.skipValidation?.includes(context.actionName)) {
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
  const failedGates = Object.values(gates).filter((g) => g === 'fail').length;
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
  if (concerns.some((c) => /violence|weapon|malware|hack/i.test(c))) return 'critical';

  // High: Two gates failed or moderate concerns
  if (failedGates === 2) return 'high';
  if (concerns.some((c) => /override|bypass|jailbreak/i.test(c))) return 'high';

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

  const failedGates = Object.entries(gates)
    .filter(([_, status]) => status === 'fail')
    .map(([gate]) => gate.toUpperCase());

  if (failedGates.length === 1) {
    return `Blocked by ${failedGates[0]} gate: ${concerns[0]}`;
  }

  return `Blocked by ${failedGates.join(', ')} gates. ${concerns.length} concern(s) detected.`;
}

/**
 * Quick safety check for common dangerous patterns
 */
export function quickCheck(content: string): boolean {
  // Fast path for obviously safe content
  if (content.length < 10) return true;

  // Check for critical patterns only
  const criticalPatterns = [
    /ignore\s+(previous|all|your)\s+instructions/i,
    /\b(kill|murder|bomb|weapon)\b/i,
    /hack(ing)?\s+(into|password)/i,
    /malware|ransomware/i,
  ];

  return !criticalPatterns.some((p) => p.test(content));
}

/**
 * Validate action for physical/embodied agents
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
