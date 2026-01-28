/**
 * @sentinelseed/moltbot - CLI Formatters
 *
 * Provides formatting utilities for CLI output.
 * Creates user-friendly terminal displays for status, levels, and actions.
 *
 * @module cli/formatters
 */

import type { ProtectionLevel, RiskLevel } from '../types';
import { COLORS, formatDuration, formatRiskLevel as baseFormatRiskLevel } from '../logging/formatters';

// =============================================================================
// Constants
// =============================================================================

/** Box drawing characters for fancy output */
export const BOX = {
  topLeft: '╭',
  topRight: '╮',
  bottomLeft: '╰',
  bottomRight: '╯',
  horizontal: '─',
  vertical: '│',
  horizontalDown: '┬',
  horizontalUp: '┴',
  verticalRight: '├',
  verticalLeft: '┤',
  cross: '┼',
} as const;

/** Level display configurations */
export const LEVEL_DISPLAY: Record<ProtectionLevel, {
  icon: string;
  color: string;
  label: string;
  description: string;
}> = {
  off: {
    icon: '○',
    color: COLORS.gray,
    label: 'OFF',
    description: 'Protection disabled',
  },
  watch: {
    icon: '👁',
    color: COLORS.blue,
    label: 'WATCH',
    description: 'Monitor and alert only',
  },
  guard: {
    icon: '🛡',
    color: COLORS.yellow,
    label: 'GUARD',
    description: 'Block critical threats',
  },
  shield: {
    icon: '🔒',
    color: COLORS.green,
    label: 'SHIELD',
    description: 'Maximum protection',
  },
};

// =============================================================================
// Level Formatting
// =============================================================================

/**
 * Format a protection level for display.
 *
 * @param level - Protection level
 * @param useColor - Whether to use colors
 * @returns Formatted level string
 */
export function formatLevel(level: ProtectionLevel, useColor = true): string {
  const config = LEVEL_DISPLAY[level];

  if (!useColor) {
    return `${config.icon} ${config.label}`;
  }

  return `${config.icon} ${config.color}${config.label}${COLORS.reset}`;
}

/**
 * Format a protection level with description.
 *
 * @param level - Protection level
 * @param useColor - Whether to use colors
 * @returns Formatted level with description
 */
export function formatLevelFull(level: ProtectionLevel, useColor = true): string {
  const config = LEVEL_DISPLAY[level];
  const label = formatLevel(level, useColor);

  return `${label} - ${config.description}`;
}

/**
 * Format all available levels for display.
 *
 * @param currentLevel - Currently active level (to highlight)
 * @param useColor - Whether to use colors
 * @returns Formatted level list
 */
export function formatLevelList(
  currentLevel?: ProtectionLevel,
  useColor = true
): string {
  const levels: ProtectionLevel[] = ['off', 'watch', 'guard', 'shield'];

  const lines = levels.map(level => {
    const config = LEVEL_DISPLAY[level];
    const isCurrent = level === currentLevel;
    const marker = isCurrent ? '>' : ' ';
    const label = formatLevelFull(level, useColor);

    if (isCurrent && useColor) {
      return `${marker} ${COLORS.bright}${label}${COLORS.reset}`;
    }

    return `${marker} ${label}`;
  });

  return lines.join('\n');
}

// =============================================================================
// Status Formatting
// =============================================================================

/**
 * Status display data.
 */
export interface StatusData {
  /** Current protection level */
  level: ProtectionLevel;
  /** Whether protection is active */
  active: boolean;
  /** Whether paused */
  paused?: boolean;
  /** Pause reason */
  pauseReason?: string;
  /** Session count */
  activeSessions?: number;
  /** Total messages processed */
  messagesProcessed?: number;
  /** Total blocks */
  actionsBlocked?: number;
  /** Uptime in ms */
  uptimeMs?: number;
}

/**
 * Format a status display.
 *
 * @param status - Status data
 * @param useColor - Whether to use colors
 * @returns Formatted status
 */
export function formatStatus(status: StatusData, useColor = true): string {
  const lines: string[] = [];

  // Header
  lines.push(formatHeader('Sentinel Status', useColor));
  lines.push('');

  // Level
  lines.push(`  Level: ${formatLevel(status.level, useColor)}`);

  // Active state
  const activeState = status.active
    ? (useColor ? `${COLORS.green}Active${COLORS.reset}` : 'Active')
    : (useColor ? `${COLORS.gray}Inactive${COLORS.reset}` : 'Inactive');
  lines.push(`  State: ${activeState}`);

  // Paused state
  if (status.paused) {
    const pausedText = useColor
      ? `${COLORS.yellow}PAUSED${COLORS.reset}`
      : 'PAUSED';
    lines.push(`  Paused: ${pausedText}`);
    if (status.pauseReason) {
      lines.push(`  Reason: ${status.pauseReason}`);
    }
  }

  // Stats
  if (status.activeSessions !== undefined) {
    lines.push(`  Sessions: ${status.activeSessions}`);
  }

  if (status.messagesProcessed !== undefined) {
    lines.push(`  Messages: ${status.messagesProcessed}`);
  }

  if (status.actionsBlocked !== undefined) {
    lines.push(`  Blocked: ${status.actionsBlocked}`);
  }

  if (status.uptimeMs !== undefined) {
    lines.push(`  Uptime: ${formatDuration(status.uptimeMs)}`);
  }

  return lines.join('\n');
}

// =============================================================================
// Block Message Formatting
// =============================================================================

/**
 * Format a block message for the user.
 *
 * @param actionType - Type of action blocked
 * @param reason - Reason for blocking
 * @param useColor - Whether to use colors
 * @returns Formatted block message
 */
export function formatBlockMessage(
  actionType: 'output' | 'tool',
  reason: string,
  useColor = true
): string {
  const icon = '🛑';
  const title = actionType === 'output'
    ? 'Message Blocked'
    : 'Tool Call Blocked';

  const header = useColor
    ? `${icon} ${COLORS.red}${COLORS.bright}${title}${COLORS.reset}`
    : `${icon} ${title}`;

  const lines = [
    header,
    '',
    `  ${reason}`,
    '',
    formatEscapeHint(useColor),
  ];

  return lines.join('\n');
}

/**
 * Format an escape hint for blocked actions.
 *
 * @param useColor - Whether to use colors
 * @returns Formatted hint
 */
export function formatEscapeHint(useColor = true): string {
  const hint = 'Type /sentinel allow-once to bypass this block once.';

  if (useColor) {
    return `${COLORS.dim}${hint}${COLORS.reset}`;
  }

  return hint;
}

// =============================================================================
// Alert Formatting
// =============================================================================

/**
 * Format an alert notification for CLI.
 *
 * @param type - Alert type
 * @param message - Alert message
 * @param severity - Alert severity
 * @param useColor - Whether to use colors
 * @returns Formatted alert
 */
export function formatAlertNotification(
  type: string,
  message: string,
  severity: RiskLevel,
  useColor = true
): string {
  const severityStr = baseFormatRiskLevel(severity, useColor);
  const typeStr = type.replace(/_/g, ' ').toUpperCase();

  const header = useColor
    ? `⚠️  ${COLORS.yellow}${COLORS.bright}ALERT${COLORS.reset}`
    : '⚠️  ALERT';

  const lines = [
    header,
    `  Type: ${typeStr}`,
    `  Severity: ${severityStr}`,
    `  ${message}`,
  ];

  return lines.join('\n');
}

// =============================================================================
// Help Formatting
// =============================================================================

/**
 * Format a command description.
 */
export interface CommandDescription {
  name: string;
  description: string;
  usage?: string;
  examples?: string[];
}

/**
 * Format help text for commands.
 *
 * @param commands - Command descriptions
 * @param useColor - Whether to use colors
 * @returns Formatted help
 */
export function formatHelp(
  commands: CommandDescription[],
  useColor = true
): string {
  const lines: string[] = [];

  lines.push(formatHeader('Sentinel Commands', useColor));
  lines.push('');

  for (const cmd of commands) {
    const name = useColor
      ? `${COLORS.cyan}${cmd.name}${COLORS.reset}`
      : cmd.name;

    lines.push(`  ${name}`);
    lines.push(`    ${cmd.description}`);

    if (cmd.usage) {
      const usage = useColor
        ? `${COLORS.dim}${cmd.usage}${COLORS.reset}`
        : cmd.usage;
      lines.push(`    Usage: ${usage}`);
    }

    if (cmd.examples && cmd.examples.length > 0) {
      lines.push('    Examples:');
      for (const example of cmd.examples) {
        const ex = useColor
          ? `${COLORS.dim}${example}${COLORS.reset}`
          : example;
        lines.push(`      ${ex}`);
      }
    }

    lines.push('');
  }

  return lines.join('\n');
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format a section header.
 *
 * @param title - Header title
 * @param useColor - Whether to use colors
 * @returns Formatted header
 */
export function formatHeader(title: string, useColor = true): string {
  const line = BOX.horizontal.repeat(title.length + 4);

  if (useColor) {
    return [
      `${COLORS.cyan}${BOX.topLeft}${line}${BOX.topRight}${COLORS.reset}`,
      `${COLORS.cyan}${BOX.vertical}${COLORS.reset}  ${COLORS.bright}${title}${COLORS.reset}  ${COLORS.cyan}${BOX.vertical}${COLORS.reset}`,
      `${COLORS.cyan}${BOX.bottomLeft}${line}${BOX.bottomRight}${COLORS.reset}`,
    ].join('\n');
  }

  return [
    `${BOX.topLeft}${line}${BOX.topRight}`,
    `${BOX.vertical}  ${title}  ${BOX.vertical}`,
    `${BOX.bottomLeft}${line}${BOX.bottomRight}`,
  ].join('\n');
}

/**
 * Format a success message.
 *
 * @param message - Message text
 * @param useColor - Whether to use colors
 * @returns Formatted message
 */
export function formatSuccess(message: string, useColor = true): string {
  const icon = '✓';

  if (useColor) {
    return `${COLORS.green}${icon}${COLORS.reset} ${message}`;
  }

  return `${icon} ${message}`;
}

/**
 * Format an error message.
 *
 * @param message - Message text
 * @param useColor - Whether to use colors
 * @returns Formatted message
 */
export function formatError(message: string, useColor = true): string {
  const icon = '✗';

  if (useColor) {
    return `${COLORS.red}${icon}${COLORS.reset} ${message}`;
  }

  return `${icon} ${message}`;
}

/**
 * Format an info message.
 *
 * @param message - Message text
 * @param useColor - Whether to use colors
 * @returns Formatted message
 */
export function formatInfo(message: string, useColor = true): string {
  const icon = 'ℹ';

  if (useColor) {
    return `${COLORS.blue}${icon}${COLORS.reset} ${message}`;
  }

  return `${icon} ${message}`;
}

/**
 * Format a warning message.
 *
 * @param message - Message text
 * @param useColor - Whether to use colors
 * @returns Formatted message
 */
export function formatWarning(message: string, useColor = true): string {
  const icon = '⚠';

  if (useColor) {
    return `${COLORS.yellow}${icon}${COLORS.reset} ${message}`;
  }

  return `${icon} ${message}`;
}
