/**
 * @sentinelseed/moltbot - Input Analyzer
 *
 * Analyzes user input for potential threats.
 * This is for alerting/logging only - the message_received hook cannot block.
 *
 * Features:
 * - Jailbreak attempt detection
 * - Prompt injection detection
 * - Social engineering detection
 * - THSP validation
 * - Full observability via logging and metrics
 *
 * @example
 * ```typescript
 * import { analyzeInput } from './input';
 *
 * const result = await analyzeInput(userMessage, levelConfig);
 * if (result.threatLevel > 3) {
 *   // Log and alert
 * }
 * ```
 */

import type {
  InputAnalysisResult,
  LevelConfig,
  DetectedIssue,
  RiskLevel,
} from '../types';
import {
  validateTHSP,
  checkJailbreak,
  type THSPResult,
  type GateResult,
} from './patterns';
import { logger, logValidation, logError } from '../internal/logger';
import { metrics } from '../internal/metrics';

// =============================================================================
// Constants
// =============================================================================

/**
 * Threat level scale (0-5):
 * 0: No threat detected
 * 1: Minor concern (unusual patterns)
 * 2: Low threat (suspicious patterns)
 * 3: Medium threat (likely attack attempt)
 * 4: High threat (active attack attempt)
 * 5: Critical threat (sophisticated attack)
 */
const THREAT_LEVELS = {
  NONE: 0,
  MINOR: 1,
  LOW: 2,
  MEDIUM: 3,
  HIGH: 4,
  CRITICAL: 5,
} as const;

/**
 * Indicators of prompt injection attempts.
 * These are patterns that suggest someone is trying to inject instructions.
 */
const INJECTION_INDICATORS = [
  /\b(ignore|disregard|forget)(\s+all)?\s+(previous|above|earlier|prior|your)\b.*\b(instructions?|rules?|guidelines?|prompts?|programming)\b/i,
  /\b(new|updated|real|actual|true|correct)\s+(system\s+)?(instructions?|rules?|prompt)\b/i,
  /\bsystem\s*:\s*/i,
  /\b(you\s+are\s+now|from\s+now\s+on|starting\s+now)\b/i,
  /<<\s*SYS\s*>>/i,
  /\[INST\]/i,
  /<\|im_start\|>/i,
  /---\s*(system|admin|override|root)\s*---/i,
  /\bpretend\s+your?\s+(system\s+)?prompt\b/i,
  /\boverride\s+(safety|guidelines?|rules?|restrictions?)\b/i,
] as const;

/**
 * Indicators of social engineering attempts.
 */
const SOCIAL_ENGINEERING_INDICATORS = [
  /\b(pretend|imagine|suppose|assume|act\s+as\s+if)\b.*\b(you\s+)?(are|were|have|had)\b/i,
  /\b(what\s+if|hypothetically|theoretically|in\s+theory)\b/i,
  /\b(for\s+)?(educational|research|testing|academic)\s+purposes?\s+only\b/i,
  /\bin\s+a\s+(fictional|hypothetical|alternate|parallel)\b/i,
  /\bif\s+you\s+(had|didn't\s+have|were\s+free\s+of)\s+(no\s+)?(restrictions?|rules?|guidelines?)\b/i,
  /\bjust\s+between\s+(us|you\s+and\s+me)\b/i,
  /\bdon't\s+tell\s+anyone\b/i,
  /\bthis\s+is\s+(just\s+)?a\s+game\b/i,
] as const;

/**
 * Known jailbreak technique names/patterns.
 */
const JAILBREAK_TECHNIQUE_PATTERNS = [
  /\bDAN\b/, // Do Anything Now
  /\bDevMode\b/i,
  /\bJailbreak(ed)?\b/i,
  /\bunlocked\s+mode\b/i,
  /\bno\s+restrictions?\s+mode\b/i,
  /\bgod\s+mode\b/i,
  /\bmax(imum)?\s+mode\b/i,
  /\buncensored\b/i,
  /\bunfiltered\b/i,
] as const;

// =============================================================================
// Main Analyzer
// =============================================================================

/**
 * Analyze input for potential threats.
 *
 * This function is designed for logging and alerting only.
 * It cannot block messages (Moltbot's message_received hook is fire-and-forget).
 *
 * @param content - User input to analyze
 * @param levelConfig - Current level configuration
 * @returns Analysis result with threat assessment
 */
export async function analyzeInput(
  content: string,
  levelConfig: LevelConfig
): Promise<InputAnalysisResult> {
  const startTime = Date.now();

  try {
    // Handle empty/invalid content
    if (!content || typeof content !== 'string') {
      const result: InputAnalysisResult = {
        threatLevel: THREAT_LEVELS.NONE,
        isPromptInjection: false,
        isJailbreakAttempt: false,
        issues: [],
        durationMs: Date.now() - startTime,
      };
      metrics.recordValidation('input', result.durationMs, true, false);
      return result;
    }

    const issues: DetectedIssue[] = [];

    // 1. Run THSP validation
    const thspResult = runThspValidation(content);

    // 2. Check for jailbreak attempts
    const jailbreakResult = runJailbreakCheck(content);
    const isJailbreakAttempt = !jailbreakResult.passed;

    // 3. Check for prompt injection patterns
    const isPromptInjection = detectPromptInjection(content, jailbreakResult);

    // 4. Collect issues from THSP
    collectThspIssues(thspResult, issues);

    // 5. Check for social engineering
    const socialEngineeringDetected = detectSocialEngineering(content);
    if (socialEngineeringDetected) {
      issues.push({
        type: 'prompt_injection',
        description: 'Social engineering pattern detected',
        evidence: 'Hypothetical/educational framing',
        severity: 'medium',
        gate: 'jailbreak',
      });
    }

    // 6. Check for known jailbreak techniques
    const knownTechnique = detectKnownTechniques(content);
    if (knownTechnique) {
      issues.push({
        type: 'jailbreak_attempt',
        description: `Known jailbreak technique: ${knownTechnique}`,
        evidence: knownTechnique,
        severity: 'critical',
        gate: 'jailbreak',
      });
    }

    // 7. Calculate threat level
    const threatLevel = calculateThreatLevel(
      thspResult,
      isJailbreakAttempt,
      isPromptInjection,
      socialEngineeringDetected,
      issues
    );

    const durationMs = Date.now() - startTime;
    const result: InputAnalysisResult = {
      threatLevel,
      isPromptInjection,
      isJailbreakAttempt,
      issues,
      durationMs,
    };

    // Record metrics
    const safe = threatLevel === THREAT_LEVELS.NONE;
    metrics.recordValidation('input', durationMs, safe, false); // Input never blocks
    if (issues.length > 0) {
      metrics.recordIssues(issues);
    }

    // Log result
    logValidation('input', {
      safe,
      blocked: false,
      issueCount: issues.length,
      riskLevel: threatLevelToRiskLevel(threatLevel),
      durationMs,
    }, {
      contentLength: content.length,
      threatLevel,
      isJailbreakAttempt,
      isPromptInjection,
    });

    return result;
  } catch (error) {
    // Log error and return safe result
    logError('analyzeInput', error instanceof Error ? error : String(error), {
      contentLength: content?.length,
    });
    metrics.recordError('validation');

    return {
      threatLevel: THREAT_LEVELS.NONE,
      isPromptInjection: false,
      isJailbreakAttempt: false,
      issues: [],
      durationMs: Date.now() - startTime,
    };
  }
}

// =============================================================================
// Validation Helpers
// =============================================================================

/**
 * Run THSP validation with error handling.
 */
function runThspValidation(content: string): THSPResult {
  try {
    return validateTHSP(content);
  } catch (error) {
    logger.error('THSP validation failed', {
      operation: 'runThspValidation',
      error: error instanceof Error ? error : String(error),
    });
    // Return a passing result on error
    const passingGate = { passed: true, violations: [] as string[], score: 0 };
    return {
      overall: true,
      riskLevel: 'low',
      summary: 'Validation failed',
      jailbreak: passingGate,
      truth: passingGate,
      harm: passingGate,
      scope: passingGate,
      purpose: passingGate,
    };
  }
}

/**
 * Run jailbreak check with error handling.
 */
function runJailbreakCheck(content: string): GateResult {
  try {
    return checkJailbreak(content);
  } catch (error) {
    logger.error('Jailbreak check failed', {
      operation: 'runJailbreakCheck',
      error: error instanceof Error ? error : String(error),
    });
    return { passed: true, violations: [] as string[], score: 0 };
  }
}

// =============================================================================
// Detection Functions
// =============================================================================

/**
 * Detect prompt injection attempts.
 */
function detectPromptInjection(content: string, jailbreakResult: GateResult): boolean {
  // If jailbreak gate failed, it's definitely an injection attempt
  if (!jailbreakResult.passed) {
    return true;
  }

  // Check for injection indicators
  try {
    for (const pattern of INJECTION_INDICATORS) {
      if (pattern.test(content)) {
        return true;
      }
    }
  } catch (error) {
    logger.error('Injection detection failed', {
      operation: 'detectPromptInjection',
      error: error instanceof Error ? error : String(error),
    });
  }

  return false;
}

/**
 * Detect social engineering attempts.
 */
function detectSocialEngineering(content: string): boolean {
  try {
    // Check each indicator
    let matchCount = 0;
    for (const pattern of SOCIAL_ENGINEERING_INDICATORS) {
      if (pattern.test(content)) {
        matchCount++;
      }
    }

    // Need at least 2 matches to flag as social engineering
    // (single matches might be legitimate)
    return matchCount >= 2;
  } catch (error) {
    logger.error('Social engineering detection failed', {
      operation: 'detectSocialEngineering',
      error: error instanceof Error ? error : String(error),
    });
    return false;
  }
}

/**
 * Detect known jailbreak technique names.
 */
function detectKnownTechniques(content: string): string | null {
  try {
    for (const pattern of JAILBREAK_TECHNIQUE_PATTERNS) {
      const match = content.match(pattern);
      if (match) {
        return match[0];
      }
    }
  } catch (error) {
    logger.error('Technique detection failed', {
      operation: 'detectKnownTechniques',
      error: error instanceof Error ? error : String(error),
    });
  }
  return null;
}

/**
 * Collect issues from THSP result.
 */
function collectThspIssues(thspResult: THSPResult, issues: DetectedIssue[]): void {
  try {
    // Add jailbreak violations
    if (!thspResult.jailbreak.passed) {
      for (const violation of thspResult.jailbreak.violations.slice(0, 3)) {
        issues.push({
          type: 'jailbreak_attempt',
          description: 'Jailbreak pattern detected',
          evidence: truncateString(violation, 100),
          severity: 'critical',
          gate: 'jailbreak',
        });
      }
    }

    // Add harm violations
    if (!thspResult.harm.passed) {
      for (const violation of thspResult.harm.violations.slice(0, 2)) {
        issues.push({
          type: 'unknown',
          description: 'Harmful content pattern detected',
          evidence: truncateString(violation, 100),
          severity: 'high',
          gate: 'harm',
        });
      }
    }

    // Add scope violations
    if (!thspResult.scope.passed) {
      for (const violation of thspResult.scope.violations.slice(0, 2)) {
        issues.push({
          type: 'unknown',
          description: 'Scope violation pattern detected',
          evidence: truncateString(violation, 100),
          severity: 'medium',
          gate: 'scope',
        });
      }
    }
  } catch (error) {
    logger.error('THSP issue collection failed', {
      operation: 'collectThspIssues',
      error: error instanceof Error ? error : String(error),
    });
  }
}

/**
 * Calculate threat level (0-5) based on analysis results.
 */
function calculateThreatLevel(
  thspResult: THSPResult,
  isJailbreakAttempt: boolean,
  isPromptInjection: boolean,
  socialEngineeringDetected: boolean,
  issues: DetectedIssue[]
): number {
  let level: number = THREAT_LEVELS.NONE;

  // Critical: Jailbreak attempt
  if (isJailbreakAttempt) {
    level = Math.max(level, THREAT_LEVELS.CRITICAL);
  }

  // High: Prompt injection (without jailbreak)
  if (isPromptInjection && !isJailbreakAttempt) {
    level = Math.max(level, THREAT_LEVELS.HIGH);
  }

  // Medium: Social engineering or THSP failures
  if (socialEngineeringDetected) {
    level = Math.max(level, THREAT_LEVELS.MEDIUM);
  }

  // Map THSP risk level to threat level
  // Note: 'low' is the default when all gates pass, so we don't increase threat level for it
  switch (thspResult.riskLevel) {
    case 'critical':
      level = Math.max(level, THREAT_LEVELS.CRITICAL);
      break;
    case 'high':
      level = Math.max(level, THREAT_LEVELS.HIGH);
      break;
    case 'medium':
      level = Math.max(level, THREAT_LEVELS.MEDIUM);
      break;
    // 'low' is the default - no threat detected, don't increase level
  }

  // Adjust based on issue count
  if (issues.length > 5) {
    level = Math.max(level, THREAT_LEVELS.HIGH);
  } else if (issues.length > 2) {
    level = Math.max(level, THREAT_LEVELS.MEDIUM);
  } else if (issues.length > 0) {
    level = Math.max(level, THREAT_LEVELS.LOW);
  }

  // Cap at CRITICAL (5)
  return Math.min(level, THREAT_LEVELS.CRITICAL);
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get threat level description.
 *
 * @param level - Threat level (0-5)
 * @returns Human-readable description
 */
export function getThreatLevelDescription(level: number): string {
  switch (level) {
    case THREAT_LEVELS.NONE:
      return 'No threat detected';
    case THREAT_LEVELS.MINOR:
      return 'Minor concern - unusual patterns';
    case THREAT_LEVELS.LOW:
      return 'Low threat - suspicious patterns';
    case THREAT_LEVELS.MEDIUM:
      return 'Medium threat - likely attack attempt';
    case THREAT_LEVELS.HIGH:
      return 'High threat - active attack attempt';
    case THREAT_LEVELS.CRITICAL:
      return 'Critical threat - sophisticated attack';
    default:
      return 'Unknown threat level';
  }
}

/**
 * Check if threat level warrants alerting.
 *
 * @param level - Threat level (0-5)
 * @param levelConfig - Level configuration
 * @returns True if alert should be sent
 */
export function shouldAlert(level: number, levelConfig: LevelConfig): boolean {
  // Check if alerting is enabled
  if (levelConfig.level === 'off') {
    return false;
  }

  // Alert on high/critical threats if high threat alerting is enabled
  if (level >= THREAT_LEVELS.HIGH && levelConfig.alerting.highThreatInput) {
    return true;
  }

  return false;
}

/**
 * Convert threat level to risk level.
 *
 * @param level - Threat level (0-5)
 * @returns Risk level
 */
export function threatLevelToRiskLevel(level: number): RiskLevel {
  switch (level) {
    case THREAT_LEVELS.NONE:
      return 'none';
    case THREAT_LEVELS.MINOR:
    case THREAT_LEVELS.LOW:
      return 'low';
    case THREAT_LEVELS.MEDIUM:
      return 'medium';
    case THREAT_LEVELS.HIGH:
      return 'high';
    case THREAT_LEVELS.CRITICAL:
      return 'critical';
    default:
      return 'none';
  }
}

/**
 * Truncate a string to a maximum length.
 */
function truncateString(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '...';
}
