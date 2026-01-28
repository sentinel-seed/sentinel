/**
 * @sentinelseed/moltbot - Log Formatters
 *
 * Provides formatting utilities for logs, audit entries, and alerts.
 * These formatters create human-readable and structured output.
 *
 * @module logging/formatters
 */

import type {
  AuditEntry,
  AuditEventType,
  SecurityAlert,
  AlertType,
  RiskLevel,
  DetectedIssue,
} from '../types';

// =============================================================================
// Constants
// =============================================================================

/** ANSI color codes for terminal output */
export const COLORS = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  gray: '\x1b[90m',
} as const;

/** Risk level to color mapping */
export const RISK_COLORS: Record<RiskLevel, string> = {
  none: COLORS.gray,
  low: COLORS.green,
  medium: COLORS.yellow,
  high: COLORS.red,
  critical: `${COLORS.bright}${COLORS.red}`,
};

/** Alert type icons */
export const ALERT_ICONS: Record<AlertType, string> = {
  high_threat_input: '⚠️',
  action_blocked: '🛑',
  prompt_injection: '💉',
  session_anomaly: '🔍',
  error: '❌',
};

/** Audit event icons */
export const AUDIT_ICONS: Record<AuditEventType, string> = {
  input_analyzed: '📥',
  output_validated: '📤',
  output_blocked: '🚫',
  tool_validated: '🔧',
  tool_blocked: '⛔',
  seed_injected: '🌱',
  session_started: '▶️',
  session_ended: '⏹️',
  config_changed: '⚙️',
  escape_used: '🔓',
  error: '❌',
};

// =============================================================================
// Time Formatting
// =============================================================================

/**
 * Format a timestamp for display.
 *
 * @param timestamp - Unix timestamp in milliseconds
 * @param options - Formatting options
 * @returns Formatted time string
 */
export function formatTimestamp(
  timestamp: number,
  options: { includeDate?: boolean; includeMs?: boolean } = {}
): string {
  const date = new Date(timestamp);

  if (options.includeDate) {
    const dateStr = date.toISOString().slice(0, 10);
    const timeStr = formatTimeOnly(date, options.includeMs);
    return `${dateStr} ${timeStr}`;
  }

  return formatTimeOnly(date, options.includeMs);
}

/**
 * Format just the time portion.
 */
function formatTimeOnly(date: Date, includeMs = false): string {
  const hours = date.getHours().toString().padStart(2, '0');
  const minutes = date.getMinutes().toString().padStart(2, '0');
  const seconds = date.getSeconds().toString().padStart(2, '0');

  if (includeMs) {
    const ms = date.getMilliseconds().toString().padStart(3, '0');
    return `${hours}:${minutes}:${seconds}.${ms}`;
  }

  return `${hours}:${minutes}:${seconds}`;
}

/**
 * Format a duration in milliseconds.
 *
 * @param ms - Duration in milliseconds
 * @returns Human-readable duration
 */
export function formatDuration(ms: number): string {
  if (ms < 1000) {
    return `${ms}ms`;
  }

  const seconds = Math.floor(ms / 1000);
  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

// =============================================================================
// Risk Level Formatting
// =============================================================================

/**
 * Format a risk level for display.
 *
 * @param level - Risk level
 * @param useColor - Whether to include ANSI colors
 * @returns Formatted risk level
 */
export function formatRiskLevel(level: RiskLevel, useColor = true): string {
  const label = level.toUpperCase();

  if (!useColor) {
    return label;
  }

  return `${RISK_COLORS[level]}${label}${COLORS.reset}`;
}

/**
 * Get a risk level badge for display.
 *
 * @param level - Risk level
 * @returns Badge string like "[HIGH]"
 */
export function getRiskBadge(level: RiskLevel): string {
  return `[${level.toUpperCase()}]`;
}

// =============================================================================
// Issue Formatting
// =============================================================================

/**
 * Format a detected issue for display.
 *
 * @param issue - The detected issue
 * @param options - Formatting options
 * @returns Formatted issue string
 */
export function formatIssue(
  issue: DetectedIssue,
  options: { includeEvidence?: boolean; useColor?: boolean } = {}
): string {
  const { includeEvidence = false, useColor = true } = options;

  const severity = formatRiskLevel(issue.severity, useColor);
  const type = issue.type.replace(/_/g, ' ');

  let result = `${severity} ${type}: ${issue.description}`;

  if (includeEvidence && issue.evidence) {
    const evidence = truncate(issue.evidence, 50);
    result += `\n  Evidence: "${evidence}"`;
  }

  return result;
}

/**
 * Format multiple issues as a list.
 *
 * @param issues - Array of detected issues
 * @param options - Formatting options
 * @returns Formatted issue list
 */
export function formatIssueList(
  issues: readonly DetectedIssue[],
  options: { maxItems?: number; useColor?: boolean } = {}
): string {
  const { maxItems = 5, useColor = true } = options;

  if (issues.length === 0) {
    return 'No issues detected';
  }

  const displayIssues = issues.slice(0, maxItems);
  const lines = displayIssues.map((issue, i) =>
    `  ${i + 1}. ${formatIssue(issue, { useColor })}`
  );

  if (issues.length > maxItems) {
    lines.push(`  ... and ${issues.length - maxItems} more`);
  }

  return lines.join('\n');
}

// =============================================================================
// Audit Entry Formatting
// =============================================================================

/**
 * Format an audit entry for display.
 *
 * @param entry - The audit entry
 * @param options - Formatting options
 * @returns Formatted audit entry
 */
export function formatAuditEntry(
  entry: AuditEntry,
  options: { verbose?: boolean; useColor?: boolean } = {}
): string {
  const { verbose = false, useColor = true } = options;

  const time = formatTimestamp(entry.timestamp, { includeMs: true });
  const icon = AUDIT_ICONS[entry.event] ?? '•';
  const outcome = formatOutcome(entry.outcome, useColor);
  const event = entry.event.replace(/_/g, ' ');

  let line = `${time} ${icon} ${event} [${outcome}]`;

  if (entry.sessionId) {
    line += ` (session: ${truncate(entry.sessionId, 12)})`;
  }

  if (verbose && Object.keys(entry.details).length > 0) {
    line += `\n  ${JSON.stringify(entry.details)}`;
  }

  return line;
}

/**
 * Format an audit outcome.
 */
function formatOutcome(
  outcome: AuditEntry['outcome'],
  useColor: boolean
): string {
  if (!useColor) {
    return outcome.toUpperCase();
  }

  const colors: Record<AuditEntry['outcome'], string> = {
    allowed: COLORS.green,
    blocked: COLORS.red,
    alerted: COLORS.yellow,
    error: COLORS.magenta,
  };

  return `${colors[outcome]}${outcome.toUpperCase()}${COLORS.reset}`;
}

/**
 * Format multiple audit entries as a log.
 *
 * @param entries - Array of audit entries
 * @param options - Formatting options
 * @returns Formatted log
 */
export function formatAuditLog(
  entries: readonly AuditEntry[],
  options: { maxEntries?: number; useColor?: boolean } = {}
): string {
  const { maxEntries = 20, useColor = true } = options;

  if (entries.length === 0) {
    return 'No audit entries';
  }

  const displayEntries = entries.slice(-maxEntries);
  const lines = displayEntries.map(entry =>
    formatAuditEntry(entry, { useColor })
  );

  if (entries.length > maxEntries) {
    lines.unshift(`... ${entries.length - maxEntries} earlier entries omitted`);
  }

  return lines.join('\n');
}

// =============================================================================
// Alert Formatting
// =============================================================================

/**
 * Format a security alert for display.
 *
 * @param alert - The security alert
 * @param options - Formatting options
 * @returns Formatted alert
 */
export function formatAlert(
  alert: SecurityAlert,
  options: { verbose?: boolean; useColor?: boolean } = {}
): string {
  const { verbose = false, useColor = true } = options;

  const time = formatTimestamp(alert.timestamp);
  const icon = ALERT_ICONS[alert.type] ?? '⚡';
  const severity = formatRiskLevel(alert.severity, useColor);
  const type = alert.type.replace(/_/g, ' ').toUpperCase();

  let line = `${icon} ${type} ${severity}`;
  line += `\n   ${alert.message}`;
  line += `\n   Time: ${time}`;

  if (alert.auditEntryId) {
    line += `\n   Audit ID: ${alert.auditEntryId}`;
  }

  if (verbose && alert.context && Object.keys(alert.context).length > 0) {
    line += `\n   Context: ${JSON.stringify(alert.context)}`;
  }

  return line;
}

/**
 * Format an alert for webhook payload.
 *
 * @param alert - The security alert
 * @returns JSON-serializable object
 */
export function formatAlertForWebhook(alert: SecurityAlert): Record<string, unknown> {
  return {
    type: alert.type,
    severity: alert.severity,
    message: alert.message,
    timestamp: new Date(alert.timestamp).toISOString(),
    auditEntryId: alert.auditEntryId,
    context: alert.context,
  };
}

// =============================================================================
// Summary Formatting
// =============================================================================

/**
 * Format a session summary.
 *
 * @param summary - Session summary object
 * @param useColor - Whether to use colors
 * @returns Formatted summary
 */
export function formatSessionSummary(
  summary: {
    sessionId: string;
    success: boolean;
    durationMs: number;
    messageCount: number;
    toolCallCount: number;
    issuesDetected: number;
    actionsBlocked: number;
  },
  useColor = true
): string {
  const status = summary.success
    ? (useColor ? `${COLORS.green}SUCCESS${COLORS.reset}` : 'SUCCESS')
    : (useColor ? `${COLORS.red}FAILED${COLORS.reset}` : 'FAILED');

  const lines = [
    `Session Summary [${status}]`,
    `  ID: ${summary.sessionId}`,
    `  Duration: ${formatDuration(summary.durationMs)}`,
    `  Messages: ${summary.messageCount}`,
    `  Tool Calls: ${summary.toolCallCount}`,
    `  Issues Detected: ${summary.issuesDetected}`,
    `  Actions Blocked: ${summary.actionsBlocked}`,
  ];

  return lines.join('\n');
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Truncate a string to a maximum length.
 *
 * @param str - String to truncate
 * @param maxLength - Maximum length
 * @param suffix - Suffix to add if truncated
 * @returns Truncated string
 */
export function truncate(str: string, maxLength: number, suffix = '...'): string {
  if (str.length <= maxLength) {
    return str;
  }

  return str.slice(0, maxLength - suffix.length) + suffix;
}

/**
 * Indent text by a number of spaces.
 *
 * @param text - Text to indent
 * @param spaces - Number of spaces
 * @returns Indented text
 */
export function indent(text: string, spaces = 2): string {
  const padding = ' '.repeat(spaces);
  return text.split('\n').map(line => padding + line).join('\n');
}

/**
 * Remove ANSI color codes from a string.
 *
 * @param str - String with color codes
 * @returns Plain string
 */
export function stripColors(str: string): string {
  // eslint-disable-next-line no-control-regex
  return str.replace(/\x1b\[[0-9;]*m/g, '');
}
