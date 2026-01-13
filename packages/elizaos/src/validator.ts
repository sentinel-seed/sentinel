/**
 * Sentinel Safety Validator
 *
 * Core validation logic using THSP protocol for ElizaOS agents.
 * Patterns are imported from @sentinelseed/core for consistency.
 */

import type {
  THSPGates,
  SafetyCheckResult,
  RiskLevel,
  GateStatus,
  ValidationContext,
  SentinelPluginConfig,
} from './types';

// Import patterns and utilities from sentinel-core (source of truth)
import {
  DECEPTION_PATTERNS as CORE_DECEPTION,
  ROLE_MANIPULATION_PATTERNS as CORE_ROLE_MANIPULATION,
  ROLEPLAY_MANIPULATION_PATTERNS as CORE_ROLEPLAY_MANIPULATION,
  HARM_PATTERNS as CORE_HARM,
  SCOPE_PATTERNS as CORE_SCOPE,
  INSTRUCTION_OVERRIDE_PATTERNS as CORE_INSTRUCTION_OVERRIDE,
  PROMPT_EXTRACTION_PATTERNS as CORE_PROMPT_EXTRACTION,
  FILTER_BYPASS_PATTERNS as CORE_FILTER_BYPASS,
  SYSTEM_INJECTION_PATTERNS as CORE_SYSTEM_INJECTION,
  PURPOSE_PATTERNS as CORE_PURPOSE,
  ALL_HARM_PATTERNS,
  quickCheck as coreQuickCheck,
} from '@sentinelseed/core';

// Helper function to create pattern definitions from core patterns
function createPatternDefs(patterns: RegExp[], category: string): PatternDefinition[] {
  return patterns.map((pattern) => ({
    pattern,
    concern: `${category} pattern detected`,
  }));
}

// Pattern definitions for each THSP gate
interface PatternDefinition {
  pattern: RegExp;
  concern: string;
}

// TRUTH GATE: Combine deception, role manipulation, and roleplay manipulation patterns
const TRUTH_PATTERNS: PatternDefinition[] = [
  ...createPatternDefs(CORE_DECEPTION, 'Deception'),
  ...createPatternDefs(CORE_ROLE_MANIPULATION, 'Role manipulation'),
  ...createPatternDefs(CORE_ROLEPLAY_MANIPULATION, 'Roleplay manipulation'),
];

// HARM GATE: Use all harm patterns from core
const HARM_PATTERNS: PatternDefinition[] = [
  ...createPatternDefs(ALL_HARM_PATTERNS, 'Harm'),
];

// SCOPE GATE: Combine instruction override, prompt extraction, filter bypass, and system injection
const SCOPE_PATTERNS: PatternDefinition[] = [
  ...createPatternDefs(CORE_INSTRUCTION_OVERRIDE, 'Instruction override'),
  ...createPatternDefs(CORE_PROMPT_EXTRACTION, 'Prompt extraction'),
  ...createPatternDefs(CORE_FILTER_BYPASS, 'Filter bypass'),
  ...createPatternDefs(CORE_SYSTEM_INJECTION, 'System injection'),
];

// PURPOSE GATE: Use purpose patterns from core
const PURPOSE_PATTERNS: PatternDefinition[] = [
  ...createPatternDefs(CORE_PURPOSE, 'Purpose violation'),
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

  // Guard against null/undefined/non-string input
  if (!content || typeof content !== 'string') {
    return {
      safe: false,
      shouldProceed: config?.blockUnsafe === false,
      gates: { truth: 'unknown', harm: 'unknown', scope: 'unknown', purpose: 'unknown' },
      concerns: ['Invalid input: content must be a non-empty string'],
      riskLevel: 'medium',
      recommendation: 'Content validation failed: invalid input type',
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
 * Uses quickCheck from sentinel-core for consistency.
 */
export function quickCheck(content: string): boolean {
  // Guard against null/undefined/non-string input
  if (!content || typeof content !== 'string') return true;

  // Fast path for very short content (but not too short to contain threats)
  if (content.length < 5) return true;

  // Use core quickCheck for consistent pattern matching
  return coreQuickCheck(content);
}

/**
 * Validate an action with parameters
 */
export function validateAction(
  action: string,
  params?: Record<string, unknown>
): SafetyCheckResult {
  // Guard against null/undefined/non-string action
  if (!action || typeof action !== 'string') {
    return {
      safe: false,
      shouldProceed: false,
      gates: { truth: 'unknown', harm: 'unknown', scope: 'unknown', purpose: 'unknown' },
      concerns: ['Invalid action: action name must be a non-empty string'],
      riskLevel: 'medium',
      recommendation: 'Action validation failed: invalid action name',
      timestamp: Date.now(),
    };
  }

  const content = params
    ? `${action}: ${JSON.stringify(params)}`
    : action;

  return validateContent(content, { actionName: action });
}
