/**
 * @sentinelseed/moltbot - Internal Metrics
 *
 * Provides metrics collection for monitoring and debugging.
 * Tracks validation counts, timing, and issue detection rates.
 *
 * @example
 * ```typescript
 * import { metrics, getMetricsSnapshot } from './metrics';
 *
 * // Record a validation
 * metrics.recordValidation('output', 25, true, false);
 *
 * // Get current metrics
 * const snapshot = getMetricsSnapshot();
 * console.log(snapshot.validations.output.count);
 * ```
 */

import type { RiskLevel, IssueType } from '../types';

// =============================================================================
// Types
// =============================================================================

/**
 * Timing statistics for an operation.
 */
export interface TimingStats {
  /** Total count of operations */
  count: number;
  /** Total time across all operations (ms) */
  totalMs: number;
  /** Minimum time observed (ms) */
  minMs: number;
  /** Maximum time observed (ms) */
  maxMs: number;
  /** Last operation time (ms) */
  lastMs: number;
}

/**
 * Validation statistics for a specific type.
 */
export interface ValidationStats {
  /** Total validations */
  count: number;
  /** Validations that passed (safe=true) */
  passed: number;
  /** Validations that were flagged (safe=false, blocked=false) */
  flagged: number;
  /** Validations that were blocked (blocked=true) */
  blocked: number;
  /** Timing statistics */
  timing: TimingStats;
}

/**
 * Issue detection statistics.
 */
export interface IssueStats {
  /** Count by issue type */
  byType: Record<IssueType, number>;
  /** Count by severity */
  bySeverity: Record<RiskLevel, number>;
  /** Total issues detected */
  total: number;
}

/**
 * Complete metrics snapshot.
 */
export interface MetricsSnapshot {
  /** Validation statistics by type */
  validations: {
    input: ValidationStats;
    output: ValidationStats;
    tool: ValidationStats;
  };
  /** Issue detection statistics */
  issues: IssueStats;
  /** Error counts */
  errors: {
    validation: number;
    pattern: number;
    unknown: number;
  };
  /** When metrics collection started */
  startedAt: number;
  /** When this snapshot was taken */
  snapshotAt: number;
}

// =============================================================================
// Internal State
// =============================================================================

function createTimingStats(): TimingStats {
  return {
    count: 0,
    totalMs: 0,
    minMs: Infinity,
    maxMs: 0,
    lastMs: 0,
  };
}

function createValidationStats(): ValidationStats {
  return {
    count: 0,
    passed: 0,
    flagged: 0,
    blocked: 0,
    timing: createTimingStats(),
  };
}

function createIssueStats(): IssueStats {
  return {
    byType: {
      data_leak: 0,
      destructive_command: 0,
      system_path: 0,
      suspicious_url: 0,
      prompt_injection: 0,
      jailbreak_attempt: 0,
      injection_compliance: 0,
      unknown: 0,
    },
    bySeverity: {
      none: 0,
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    },
    total: 0,
  };
}

// Internal state
let metricsStartedAt = Date.now();
let inputStats = createValidationStats();
let outputStats = createValidationStats();
let toolStats = createValidationStats();
let issueStats = createIssueStats();
let errorCounts = { validation: 0, pattern: 0, unknown: 0 };

// =============================================================================
// Public API
// =============================================================================

/**
 * Metrics recording interface.
 */
export const metrics = {
  /**
   * Record a validation operation.
   *
   * @param type - Type of validation (input, output, tool)
   * @param durationMs - Time taken in milliseconds
   * @param safe - Whether validation passed
   * @param blocked - Whether the action was blocked
   */
  recordValidation(
    type: 'input' | 'output' | 'tool',
    durationMs: number,
    safe: boolean,
    blocked: boolean
  ): void {
    const stats = getStatsForType(type);

    stats.count++;
    if (safe) {
      stats.passed++;
    } else if (blocked) {
      stats.blocked++;
    } else {
      stats.flagged++;
    }

    // Update timing
    stats.timing.count++;
    stats.timing.totalMs += durationMs;
    stats.timing.lastMs = durationMs;
    stats.timing.minMs = Math.min(stats.timing.minMs, durationMs);
    stats.timing.maxMs = Math.max(stats.timing.maxMs, durationMs);
  },

  /**
   * Record detected issues.
   *
   * @param issues - Array of detected issues
   */
  recordIssues(
    issues: Array<{ type: IssueType; severity: RiskLevel }>
  ): void {
    for (const issue of issues) {
      issueStats.byType[issue.type] = (issueStats.byType[issue.type] || 0) + 1;
      issueStats.bySeverity[issue.severity] = (issueStats.bySeverity[issue.severity] || 0) + 1;
      issueStats.total++;
    }
  },

  /**
   * Record an error.
   *
   * @param type - Type of error
   */
  recordError(type: 'validation' | 'pattern' | 'unknown'): void {
    errorCounts[type]++;
  },
};

/**
 * Get the appropriate stats object for a validation type.
 */
function getStatsForType(type: 'input' | 'output' | 'tool'): ValidationStats {
  switch (type) {
    case 'input':
      return inputStats;
    case 'output':
      return outputStats;
    case 'tool':
      return toolStats;
  }
}

/**
 * Get a snapshot of all current metrics.
 */
export function getMetricsSnapshot(): MetricsSnapshot {
  return {
    validations: {
      input: deepClone(inputStats),
      output: deepClone(outputStats),
      tool: deepClone(toolStats),
    },
    issues: deepClone(issueStats),
    errors: { ...errorCounts },
    startedAt: metricsStartedAt,
    snapshotAt: Date.now(),
  };
}

/**
 * Reset all metrics to initial state.
 */
export function resetMetrics(): void {
  metricsStartedAt = Date.now();
  inputStats = createValidationStats();
  outputStats = createValidationStats();
  toolStats = createValidationStats();
  issueStats = createIssueStats();
  errorCounts = { validation: 0, pattern: 0, unknown: 0 };
}

/**
 * Get average validation time for a type.
 *
 * @param type - Validation type
 * @returns Average time in ms, or 0 if no validations
 */
export function getAverageValidationTime(
  type: 'input' | 'output' | 'tool'
): number {
  const stats = getStatsForType(type);
  if (stats.timing.count === 0) return 0;
  return stats.timing.totalMs / stats.timing.count;
}

/**
 * Get block rate for a validation type.
 *
 * @param type - Validation type
 * @returns Block rate (0-1), or 0 if no validations
 */
export function getBlockRate(type: 'input' | 'output' | 'tool'): number {
  const stats = getStatsForType(type);
  if (stats.count === 0) return 0;
  return stats.blocked / stats.count;
}

/**
 * Get pass rate for a validation type.
 *
 * @param type - Validation type
 * @returns Pass rate (0-1), or 0 if no validations
 */
export function getPassRate(type: 'input' | 'output' | 'tool'): number {
  const stats = getStatsForType(type);
  if (stats.count === 0) return 0;
  return stats.passed / stats.count;
}

/**
 * Get most common issue type.
 *
 * @returns Most common issue type, or null if no issues
 */
export function getMostCommonIssueType(): IssueType | null {
  let maxCount = 0;
  let maxType: IssueType | null = null;

  for (const [type, count] of Object.entries(issueStats.byType)) {
    if (count > maxCount) {
      maxCount = count;
      maxType = type as IssueType;
    }
  }

  return maxType;
}

/**
 * Get metrics summary as a human-readable string.
 */
export function getMetricsSummary(): string {
  const snapshot = getMetricsSnapshot();
  const uptimeMs = snapshot.snapshotAt - snapshot.startedAt;
  const uptimeSec = Math.round(uptimeMs / 1000);

  const lines = [
    `Sentinel Metrics (uptime: ${uptimeSec}s)`,
    '─'.repeat(40),
    `Input validations:  ${snapshot.validations.input.count} (${snapshot.validations.input.passed} passed, ${snapshot.validations.input.blocked} blocked)`,
    `Output validations: ${snapshot.validations.output.count} (${snapshot.validations.output.passed} passed, ${snapshot.validations.output.blocked} blocked)`,
    `Tool validations:   ${snapshot.validations.tool.count} (${snapshot.validations.tool.passed} passed, ${snapshot.validations.tool.blocked} blocked)`,
    `Total issues:       ${snapshot.issues.total}`,
    `Errors:             ${snapshot.errors.validation + snapshot.errors.pattern + snapshot.errors.unknown}`,
  ];

  return lines.join('\n');
}

// =============================================================================
// Helpers
// =============================================================================

/**
 * Deep clone an object (simple implementation for metrics objects).
 */
function deepClone<T>(obj: T): T {
  return JSON.parse(JSON.stringify(obj));
}
