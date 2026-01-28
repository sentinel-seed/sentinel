/**
 * @sentinelseed/moltbot - Output Validator
 *
 * Validates AI output content before sending to the user.
 * Checks for data leaks, harmful content, and compliance with injected instructions.
 *
 * Features:
 * - THSP validation via @sentinelseed/core
 * - Sensitive data leak detection (API keys, passwords, etc.)
 * - Destructive command detection
 * - Extensible via pattern registry
 * - Full observability via logging and metrics
 *
 * @example
 * ```typescript
 * import { validateOutput } from './output';
 *
 * const result = await validateOutput(content, levelConfig);
 * if (result.shouldBlock) {
 *   // Block the output
 * }
 * ```
 */

import type {
  OutputValidationResult,
  LevelConfig,
  DetectedIssue,
  GateResults,
  RiskLevel,
} from '../types';
import {
  validateTHSP,
  SENSITIVE_DATA_PATTERNS,
  type THSPResult,
  patternRegistry,
} from './patterns';
import { logger, logValidation, logError } from '../internal/logger';
import { metrics } from '../internal/metrics';

// =============================================================================
// Types
// =============================================================================

/**
 * Options for output validation.
 */
export interface OutputValidationOptions {
  /** Patterns to ignore during validation */
  ignorePatterns?: string[];
  /** Skip THSP validation (for performance) */
  skipThsp?: boolean;
  /** Skip data leak detection */
  skipDataLeaks?: boolean;
  /** Skip destructive command detection */
  skipDestructive?: boolean;
}

// =============================================================================
// Main Validator
// =============================================================================

/**
 * Validate output content before sending.
 *
 * Performs the following checks:
 * 1. THSP validation via @sentinelseed/core
 * 2. Sensitive data leak detection
 * 3. Destructive command detection
 *
 * @param content - The content to validate
 * @param levelConfig - Current level configuration
 * @param options - Additional validation options
 * @returns Validation result with issues and blocking decision
 */
export async function validateOutput(
  content: string,
  levelConfig: LevelConfig,
  options?: OutputValidationOptions
): Promise<OutputValidationResult> {
  const startTime = Date.now();

  try {
    // Handle empty/invalid content
    if (!content || typeof content !== 'string') {
      const result = createSafeResult(startTime);
      metrics.recordValidation('output', result.durationMs, true, false);
      return result;
    }

    // Apply ignore patterns
    const processedContent = applyIgnorePatterns(content, options?.ignorePatterns);

    // Run THSP validation (unless skipped)
    const thspResult = options?.skipThsp
      ? createPassingThspResult()
      : runThspValidation(processedContent);

    // Detect issues
    const issues: DetectedIssue[] = [];

    // 1. Add THSP violations
    addThspViolations(thspResult, issues);

    // 2. Check for data leaks (unless skipped)
    if (!options?.skipDataLeaks) {
      const dataLeakIssues = detectDataLeaks(processedContent);
      issues.push(...dataLeakIssues);
    }

    // 3. Check for destructive commands (unless skipped)
    if (!options?.skipDestructive) {
      const destructiveIssues = detectDestructiveCommands(processedContent);
      issues.push(...destructiveIssues);
    }

    // Convert THSP result to gate results
    const gates = convertToGateResults(thspResult);

    // Calculate risk level
    const riskLevel = calculateRiskLevel(thspResult, issues);

    // Determine if safe
    const safe = issues.length === 0;

    // Determine if should block based on level config
    const shouldBlock = determineShouldBlock(issues, levelConfig);

    const durationMs = Date.now() - startTime;
    const result: OutputValidationResult = {
      safe,
      shouldBlock,
      issues,
      gates,
      riskLevel,
      durationMs,
    };

    // Record metrics
    metrics.recordValidation('output', durationMs, safe, shouldBlock);
    if (issues.length > 0) {
      metrics.recordIssues(issues);
    }

    // Log result
    logValidation('output', {
      safe,
      blocked: shouldBlock,
      issueCount: issues.length,
      riskLevel,
      durationMs,
    }, {
      contentLength: content.length,
    });

    return result;
  } catch (error) {
    // Log error and return safe result (fail open for output)
    logError('validateOutput', error instanceof Error ? error : String(error), {
      contentLength: content?.length,
    });
    metrics.recordError('validation');

    return createSafeResult(startTime);
  }
}

// =============================================================================
// THSP Integration
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
    return createPassingThspResult();
  }
}

/**
 * Create a passing THSP result (for when validation is skipped or fails).
 */
function createPassingThspResult(): THSPResult {
  const passingGate = { passed: true, violations: [] as string[], score: 0 };
  return {
    overall: true,
    riskLevel: 'low' as const,
    summary: 'Validation skipped or failed',
    jailbreak: passingGate,
    truth: passingGate,
    harm: passingGate,
    scope: passingGate,
    purpose: passingGate,
  };
}

// =============================================================================
// Issue Detection
// =============================================================================

/**
 * Detect sensitive data leaks in content.
 * Uses both core patterns and registry patterns.
 */
function detectDataLeaks(content: string): DetectedIssue[] {
  const issues: DetectedIssue[] = [];

  try {
    // Check core patterns
    for (const [category, patterns] of Object.entries(SENSITIVE_DATA_PATTERNS)) {
      for (const pattern of patterns) {
        const match = content.match(pattern);
        if (match) {
          issues.push({
            type: 'data_leak',
            description: `Potential ${formatCategory(category)} detected in output`,
            evidence: sanitizeEvidence(match[0]),
            severity: getSeverityForCategory(category),
            gate: 'harm',
          });
          break; // One issue per category is enough
        }
      }
    }

    // Check registry patterns
    const sensitiveData = patternRegistry.hasSensitiveData(content);
    if (sensitiveData && !issues.some(i => i.type === 'data_leak')) {
      issues.push({
        type: 'data_leak',
        description: sensitiveData.description ?? 'Sensitive data detected',
        evidence: '[REDACTED]',
        severity: (sensitiveData.severity ?? 'high') as RiskLevel,
        gate: 'harm',
      });
    }
  } catch (error) {
    logger.error('Data leak detection failed', {
      operation: 'detectDataLeaks',
      error: error instanceof Error ? error : String(error),
    });
  }

  return issues;
}

/**
 * Detect destructive commands in content.
 * Uses both hardcoded patterns and registry patterns.
 */
function detectDestructiveCommands(content: string): DetectedIssue[] {
  const issues: DetectedIssue[] = [];

  try {
    // Hardcoded destructive command patterns
    const destructivePatterns = [
      { pattern: /\brm\s+-rf\s+\//i, desc: 'Recursive force delete from root' },
      { pattern: /\bsudo\s+rm\s+-rf/i, desc: 'Sudo recursive force delete' },
      { pattern: /\bformat\s+[a-zA-Z]:/i, desc: 'Disk format command' },
      { pattern: /DROP\s+TABLE/i, desc: 'SQL DROP TABLE' },
      { pattern: /DROP\s+DATABASE/i, desc: 'SQL DROP DATABASE' },
      { pattern: /TRUNCATE\s+TABLE/i, desc: 'SQL TRUNCATE TABLE' },
      { pattern: /\bshutdown\s+(-h|\/s|now)/i, desc: 'System shutdown command' },
      { pattern: />\s*\/dev\/sd[a-z]/i, desc: 'Write to disk device' },
      { pattern: /\bmkfs\./i, desc: 'Filesystem format command' },
      { pattern: /\bdd\s+.*\bof=\/dev\//i, desc: 'Direct disk write (dd)' },
      { pattern: /\binit\s+[06]/i, desc: 'System init level change' },
    ];

    for (const { pattern, desc } of destructivePatterns) {
      const match = content.match(pattern);
      if (match) {
        issues.push({
          type: 'destructive_command',
          description: desc,
          evidence: match[0],
          severity: 'high',
          gate: 'harm',
        });
      }
    }

    // Check registry patterns
    const dangerousCmd = patternRegistry.hasDangerousCommand(content);
    if (dangerousCmd && !issues.some(i => i.evidence === dangerousCmd.pattern?.toString())) {
      issues.push({
        type: 'destructive_command',
        description: dangerousCmd.description ?? 'Dangerous command detected',
        evidence: '[detected]',
        severity: (dangerousCmd.severity ?? 'high') as RiskLevel,
        gate: 'harm',
      });
    }
  } catch (error) {
    logger.error('Destructive command detection failed', {
      operation: 'detectDestructiveCommands',
      error: error instanceof Error ? error : String(error),
    });
  }

  return issues;
}

/**
 * Add violations from THSP result to issues array.
 */
function addThspViolations(thspResult: THSPResult, issues: DetectedIssue[]): void {
  try {
    // Process each gate directly with proper typing
    const gates = [
      { result: thspResult.jailbreak, name: 'jailbreak', type: 'jailbreak_attempt' as const },
      { result: thspResult.truth, name: 'truth', type: 'unknown' as const },
      { result: thspResult.harm, name: 'harm', type: 'unknown' as const },
      { result: thspResult.scope, name: 'scope', type: 'unknown' as const },
      { result: thspResult.purpose, name: 'purpose', type: 'unknown' as const },
    ];

    for (const { result, name, type } of gates) {
      if (!result.passed && result.violations.length > 0) {
        for (const violation of result.violations.slice(0, 3)) { // Limit to 3 per gate
          issues.push({
            type,
            description: `${name} gate violation`,
            evidence: truncateString(violation, 100),
            severity: name === 'jailbreak' ? 'critical' : 'medium',
            gate: name as DetectedIssue['gate'],
          });
        }
      }
    }
  } catch (error) {
    logger.error('THSP violation processing failed', {
      operation: 'addThspViolations',
      error: error instanceof Error ? error : String(error),
    });
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Apply ignore patterns to content.
 * Returns content with ignored sections replaced.
 */
function applyIgnorePatterns(content: string, patterns?: string[]): string {
  if (!patterns || patterns.length === 0) {
    return content;
  }

  let processed = content;
  for (const pattern of patterns) {
    try {
      const regex = new RegExp(pattern, 'gi');
      processed = processed.replace(regex, '[IGNORED]');
    } catch (error) {
      logger.warn('Invalid ignore pattern', {
        operation: 'applyIgnorePatterns',
        error: error instanceof Error ? error.message : String(error),
      });
    }
  }
  return processed;
}

/**
 * Convert THSP result to simplified gate results.
 */
function convertToGateResults(thspResult: THSPResult): GateResults {
  return {
    truth: thspResult.truth.passed ? 'pass' : 'fail',
    harm: thspResult.harm.passed ? 'pass' : 'fail',
    scope: thspResult.scope.passed ? 'pass' : 'fail',
    purpose: thspResult.purpose.passed ? 'pass' : 'fail',
    jailbreak: thspResult.jailbreak.passed ? 'pass' : 'fail',
  };
}

/**
 * Calculate risk level based on THSP result and detected issues.
 */
function calculateRiskLevel(thspResult: THSPResult, issues: DetectedIssue[]): RiskLevel {
  // Use THSP risk level as base
  const thspRisk = thspResult.riskLevel;

  // Check for critical issues
  const hasCritical = issues.some(i => i.severity === 'critical');
  if (hasCritical || thspRisk === 'critical') {
    return 'critical';
  }

  // Check for high-severity issues
  const hasHigh = issues.some(i => i.severity === 'high');
  if (hasHigh || thspRisk === 'high') {
    return 'high';
  }

  // Check for medium-severity issues
  const hasMedium = issues.some(i => i.severity === 'medium');
  if (hasMedium || thspRisk === 'medium') {
    return 'medium';
  }

  // Check for any issues
  if (issues.length > 0) {
    return 'low';
  }

  return 'none';
}

/**
 * Determine if content should be blocked based on issues and level config.
 */
function determineShouldBlock(issues: DetectedIssue[], levelConfig: LevelConfig): boolean {
  // Never block if blocking is disabled
  if (!hasAnyBlockingEnabled(levelConfig)) {
    return false;
  }

  for (const issue of issues) {
    // Data leaks
    if (issue.type === 'data_leak' && levelConfig.blocking.dataLeaks) {
      return true;
    }

    // Destructive commands
    if (issue.type === 'destructive_command' && levelConfig.blocking.destructiveCommands) {
      return true;
    }

    // Injection compliance (AI following injected instructions)
    if (issue.type === 'injection_compliance' && levelConfig.blocking.injectionCompliance) {
      return true;
    }

    // Jailbreak attempts (always critical)
    if (issue.type === 'jailbreak_attempt' && levelConfig.blocking.injectionCompliance) {
      return true;
    }
  }

  return false;
}

/**
 * Check if any blocking is enabled in level config.
 */
function hasAnyBlockingEnabled(levelConfig: LevelConfig): boolean {
  const { blocking } = levelConfig;
  return (
    blocking.dataLeaks ||
    blocking.destructiveCommands ||
    blocking.systemPaths ||
    blocking.suspiciousUrls ||
    blocking.injectionCompliance
  );
}

/**
 * Create a safe (no issues) result.
 */
function createSafeResult(startTime: number): OutputValidationResult {
  return {
    safe: true,
    shouldBlock: false,
    issues: [],
    gates: {
      truth: 'pass',
      harm: 'pass',
      scope: 'pass',
      purpose: 'pass',
      jailbreak: 'pass',
    },
    riskLevel: 'none',
    durationMs: Date.now() - startTime,
  };
}

/**
 * Format category name for display.
 */
function formatCategory(category: string): string {
  return category
    .replace(/([A-Z])/g, ' $1')
    .replace(/^./, str => str.toUpperCase())
    .trim();
}

/**
 * Get severity for a sensitive data category.
 */
function getSeverityForCategory(category: string): RiskLevel {
  switch (category) {
    case 'apiKeys':
    case 'passwords':
    case 'privateKeys':
      return 'critical';
    case 'ssn':
    case 'creditCard':
      return 'high';
    case 'email':
    case 'pii':
      return 'medium';
    default:
      return 'low';
  }
}

/**
 * Sanitize evidence for display (truncate and redact sensitive parts).
 */
function sanitizeEvidence(evidence: string): string {
  // Truncate long evidence
  const maxLength = 50;
  let sanitized = evidence.length > maxLength
    ? evidence.substring(0, maxLength) + '...'
    : evidence;

  // Redact middle part of potential secrets
  if (sanitized.length > 10) {
    const start = sanitized.substring(0, 4);
    const end = sanitized.substring(sanitized.length - 4);
    sanitized = `${start}****${end}`;
  }

  return sanitized;
}

/**
 * Truncate a string to a maximum length.
 */
function truncateString(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '...';
}
