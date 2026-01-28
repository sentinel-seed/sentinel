/**
 * @sentinelseed/moltbot - CLI Commands
 *
 * Provides command handlers for Sentinel CLI.
 * Commands can be invoked via /sentinel <command> in Moltbot.
 *
 * @module cli/commands
 */

import type { ProtectionLevel } from '../types';
import { LEVELS } from '../config';
import type { EscapeManager } from '../escapes';
import type { AuditLog } from '../logging/audit';
import type { AlertManager } from '../logging/alerts';
import {
  formatStatus,
  formatLevel,
  formatLevelList,
  formatSuccess,
  formatError,
  formatInfo,
  formatHelp,
  formatHeader,
  type StatusData,
  type CommandDescription,
} from './formatters';
import { formatAuditLog } from '../logging/formatters';

// =============================================================================
// Types
// =============================================================================

/**
 * Command execution context.
 */
export interface CommandContext {
  /** Current session ID */
  sessionId: string;
  /** Current protection level */
  currentLevel: ProtectionLevel;
  /** Escape manager instance */
  escapes?: EscapeManager;
  /** Audit log instance */
  audit?: AuditLog;
  /** Alert manager instance */
  alerts?: AlertManager;
  /** Whether colors are enabled */
  useColor?: boolean;
  /** Callback to change level */
  onLevelChange?: (level: ProtectionLevel) => void;
  /** Additional status data */
  statusData?: Partial<StatusData>;
}

/**
 * Command execution result.
 */
export interface CommandResult {
  /** Whether the command succeeded */
  success: boolean;
  /** Message to display to user */
  message: string;
  /** Whether to suppress default output */
  silent?: boolean;
}

/**
 * Command handler function.
 */
export type CommandHandler = (
  args: string[],
  context: CommandContext
) => CommandResult | Promise<CommandResult>;

/**
 * Command definition.
 */
export interface Command {
  /** Command name (without leading slash) */
  name: string;
  /** Command aliases */
  aliases?: string[];
  /** Command description */
  description: string;
  /** Usage string */
  usage?: string;
  /** Example usages */
  examples?: string[];
  /** Command handler */
  handler: CommandHandler;
}

// =============================================================================
// Command Registry
// =============================================================================

/** Registered commands */
const commands: Map<string, Command> = new Map();

/**
 * Register a command.
 *
 * @param command - Command to register
 */
export function registerCommand(command: Command): void {
  commands.set(command.name, command);

  // Register aliases
  if (command.aliases) {
    for (const alias of command.aliases) {
      commands.set(alias, command);
    }
  }
}

/**
 * Get a command by name.
 *
 * @param name - Command name
 * @returns Command or undefined
 */
export function getCommand(name: string): Command | undefined {
  return commands.get(name.toLowerCase());
}

/**
 * Get all registered commands (unique, no aliases).
 *
 * @returns Array of commands
 */
export function getAllCommands(): Command[] {
  const seen = new Set<string>();
  const result: Command[] = [];

  for (const cmd of commands.values()) {
    if (!seen.has(cmd.name)) {
      seen.add(cmd.name);
      result.push(cmd);
    }
  }

  return result;
}

/**
 * Execute a command.
 *
 * @param input - Full command input (e.g., "status" or "level guard")
 * @param context - Command context
 * @returns Command result
 */
export async function executeCommand(
  input: string,
  context: CommandContext
): Promise<CommandResult> {
  const parts = input.trim().split(/\s+/);
  const commandName = parts[0]?.toLowerCase() ?? '';
  const args = parts.slice(1);

  const command = getCommand(commandName);

  if (!command) {
    return {
      success: false,
      message: formatError(
        `Unknown command: ${commandName}. Type /sentinel help for available commands.`,
        context.useColor ?? true
      ),
    };
  }

  try {
    return await command.handler(args, context);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : String(error);
    return {
      success: false,
      message: formatError(`Command failed: ${errorMessage}`, context.useColor ?? true),
    };
  }
}

// =============================================================================
// Built-in Commands
// =============================================================================

/**
 * Status command - show current Sentinel status.
 */
registerCommand({
  name: 'status',
  aliases: ['s'],
  description: 'Show current Sentinel status',
  handler: (_, context): CommandResult => {
    const useColor = context.useColor ?? true;

    const statusData: StatusData = {
      level: context.currentLevel,
      active: context.currentLevel !== 'off',
      paused: context.escapes?.pause.isPaused(context.sessionId) ?? false,
      pauseReason: context.escapes?.pause.getState(context.sessionId).reason,
      ...context.statusData,
    };

    return {
      success: true,
      message: formatStatus(statusData, useColor),
    };
  },
});

/**
 * Level command - show or change protection level.
 */
registerCommand({
  name: 'level',
  aliases: ['l'],
  description: 'Show or change protection level',
  usage: '/sentinel level [off|watch|guard|shield]',
  examples: [
    '/sentinel level        - Show current level',
    '/sentinel level guard  - Set level to guard',
  ],
  handler: (args, context): CommandResult => {
    const useColor = context.useColor ?? true;

    // No args - show current level and options
    if (args.length === 0) {
      const header = formatHeader('Protection Levels', useColor);
      const list = formatLevelList(context.currentLevel, useColor);

      return {
        success: true,
        message: `${header}\n\n${list}`,
      };
    }

    // Set new level
    const newLevel = args[0]!.toLowerCase() as ProtectionLevel;

    if (!(newLevel in LEVELS)) {
      return {
        success: false,
        message: formatError(
          `Invalid level: ${args[0]}. Use: off, watch, guard, or shield`,
          useColor
        ),
      };
    }

    if (newLevel === context.currentLevel) {
      return {
        success: true,
        message: formatInfo(
          `Level is already set to ${formatLevel(newLevel, useColor)}`,
          useColor
        ),
      };
    }

    // Call level change callback if provided
    if (context.onLevelChange) {
      context.onLevelChange(newLevel);
    }

    return {
      success: true,
      message: formatSuccess(
        `Level changed to ${formatLevel(newLevel, useColor)}`,
        useColor
      ),
    };
  },
});

/**
 * Allow-once command - bypass next block.
 */
registerCommand({
  name: 'allow-once',
  aliases: ['ao', 'allow'],
  description: 'Allow the next blocked action to proceed',
  usage: '/sentinel allow-once [output|tool]',
  examples: [
    '/sentinel allow-once       - Allow any next action',
    '/sentinel allow-once tool  - Allow only tool calls',
  ],
  handler: (args, context): CommandResult => {
    const useColor = context.useColor ?? true;

    if (!context.escapes) {
      return {
        success: false,
        message: formatError('Escape manager not available', useColor),
      };
    }

    const scope = (args[0]?.toLowerCase() ?? 'any') as 'output' | 'tool' | 'any';

    if (scope !== 'output' && scope !== 'tool' && scope !== 'any') {
      return {
        success: false,
        message: formatError(
          'Invalid scope. Use: output, tool, or any',
          useColor
        ),
      };
    }

    const token = context.escapes.grantAllowOnce(context.sessionId, { scope });

    return {
      success: true,
      message: formatSuccess(
        `Allow-once granted (scope: ${scope}, expires in 30s)`,
        useColor
      ),
    };
  },
});

/**
 * Pause command - pause Sentinel protection.
 */
registerCommand({
  name: 'pause',
  aliases: ['p'],
  description: 'Pause Sentinel protection temporarily',
  usage: '/sentinel pause [duration]',
  examples: [
    '/sentinel pause        - Pause for 5 minutes',
    '/sentinel pause 10m    - Pause for 10 minutes',
  ],
  handler: (args, context): CommandResult => {
    const useColor = context.useColor ?? true;

    if (!context.escapes) {
      return {
        success: false,
        message: formatError('Escape manager not available', useColor),
      };
    }

    // Parse duration if provided
    let durationMs = 5 * 60 * 1000; // Default 5 minutes

    if (args[0]) {
      const parsed = parseDuration(args[0]);
      if (parsed === null) {
        return {
          success: false,
          message: formatError(
            'Invalid duration. Use format: 5m, 10m, 1h',
            useColor
          ),
        };
      }
      durationMs = parsed;
    }

    const result = context.escapes.pauseProtection(context.sessionId, {
      durationMs,
      reason: 'User requested via CLI',
    });

    if (!result.success) {
      return {
        success: false,
        message: formatError(
          result.error === 'already_paused'
            ? 'Already paused'
            : 'Failed to pause',
          useColor
        ),
      };
    }

    const durationStr = formatDurationString(durationMs);

    return {
      success: true,
      message: formatSuccess(`Sentinel paused for ${durationStr}`, useColor),
    };
  },
});

/**
 * Resume command - resume Sentinel protection.
 */
registerCommand({
  name: 'resume',
  aliases: ['r'],
  description: 'Resume Sentinel protection after pause',
  handler: (_, context): CommandResult => {
    const useColor = context.useColor ?? true;

    if (!context.escapes) {
      return {
        success: false,
        message: formatError('Escape manager not available', useColor),
      };
    }

    const result = context.escapes.resumeProtection(context.sessionId);

    if (!result.success) {
      return {
        success: false,
        message: formatError(
          result.error === 'not_paused'
            ? 'Not currently paused'
            : 'Failed to resume',
          useColor
        ),
      };
    }

    return {
      success: true,
      message: formatSuccess('Sentinel resumed', useColor),
    };
  },
});

/**
 * Trust command - trust a tool.
 */
registerCommand({
  name: 'trust',
  aliases: ['t'],
  description: 'Trust a tool to bypass validation',
  usage: '/sentinel trust <tool-name>',
  examples: [
    '/sentinel trust bash          - Trust bash for this session',
    '/sentinel trust mcp__*        - Trust all MCP tools',
  ],
  handler: (args, context): CommandResult => {
    const useColor = context.useColor ?? true;

    if (!context.escapes) {
      return {
        success: false,
        message: formatError('Escape manager not available', useColor),
      };
    }

    if (args.length === 0) {
      // Show trusted tools
      const trustedTools = context.escapes.trust.getTrustedTools(context.sessionId);

      if (trustedTools.length === 0) {
        return {
          success: true,
          message: formatInfo('No tools currently trusted', useColor),
        };
      }

      const list = trustedTools.map(t => `  • ${t.name}`).join('\n');
      return {
        success: true,
        message: `${formatHeader('Trusted Tools', useColor)}\n\n${list}`,
      };
    }

    const toolName = args[0]!;

    const result = context.escapes.trustTool(context.sessionId, toolName, {
      level: 'session',
    });

    if (!result.success) {
      return {
        success: false,
        message: formatError(
          result.error === 'already_trusted'
            ? `Tool '${toolName}' is already trusted`
            : 'Failed to trust tool',
          useColor
        ),
      };
    }

    return {
      success: true,
      message: formatSuccess(`Tool '${toolName}' trusted for this session`, useColor),
    };
  },
});

/**
 * Untrust command - revoke tool trust.
 */
registerCommand({
  name: 'untrust',
  aliases: ['ut'],
  description: 'Revoke trust from a tool',
  usage: '/sentinel untrust <tool-name>',
  handler: (args, context): CommandResult => {
    const useColor = context.useColor ?? true;

    if (!context.escapes) {
      return {
        success: false,
        message: formatError('Escape manager not available', useColor),
      };
    }

    if (args.length === 0) {
      return {
        success: false,
        message: formatError('Please specify a tool name', useColor),
      };
    }

    const toolName = args[0]!;
    const revoked = context.escapes.revokeTrust(context.sessionId, toolName);

    if (!revoked) {
      return {
        success: false,
        message: formatError(`Tool '${toolName}' was not trusted`, useColor),
      };
    }

    return {
      success: true,
      message: formatSuccess(`Trust revoked for '${toolName}'`, useColor),
    };
  },
});

/**
 * Log command - show audit log.
 */
registerCommand({
  name: 'log',
  aliases: ['logs'],
  description: 'Show recent audit log entries',
  usage: '/sentinel log [count]',
  examples: [
    '/sentinel log      - Show last 10 entries',
    '/sentinel log 20   - Show last 20 entries',
  ],
  handler: (args, context): CommandResult => {
    const useColor = context.useColor ?? true;

    if (!context.audit) {
      return {
        success: false,
        message: formatError('Audit log not available', useColor),
      };
    }

    const count = args[0] ? parseInt(args[0], 10) : 10;

    if (isNaN(count) || count < 1) {
      return {
        success: false,
        message: formatError('Invalid count. Use a positive number.', useColor),
      };
    }

    const entries = context.audit.getRecent(count);

    if (entries.length === 0) {
      return {
        success: true,
        message: formatInfo('No audit entries yet', useColor),
      };
    }

    const header = formatHeader(`Last ${entries.length} Audit Entries`, useColor);
    const log = formatAuditLog(entries, { useColor });

    return {
      success: true,
      message: `${header}\n\n${log}`,
    };
  },
});

/**
 * Help command - show available commands.
 */
registerCommand({
  name: 'help',
  aliases: ['h', '?'],
  description: 'Show available commands',
  handler: (_, context): CommandResult => {
    const useColor = context.useColor ?? true;

    const commandDescs: CommandDescription[] = getAllCommands().map(cmd => ({
      name: cmd.name,
      description: cmd.description,
      usage: cmd.usage,
      examples: cmd.examples,
    }));

    return {
      success: true,
      message: formatHelp(commandDescs, useColor),
    };
  },
});

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Parse a duration string (e.g., "5m", "1h").
 *
 * @param str - Duration string
 * @returns Duration in ms, or null if invalid
 */
function parseDuration(str: string): number | null {
  const match = str.match(/^(\d+)(s|m|h)?$/i);
  if (!match) {
    return null;
  }

  const value = parseInt(match[1]!, 10);
  const unit = (match[2] ?? 'm').toLowerCase();

  switch (unit) {
    case 's':
      return value * 1000;
    case 'm':
      return value * 60 * 1000;
    case 'h':
      return value * 60 * 60 * 1000;
    default:
      return null;
  }
}

/**
 * Format a duration in ms to a human-readable string.
 *
 * @param ms - Duration in milliseconds
 * @returns Formatted string
 */
function formatDurationString(ms: number): string {
  if (ms < 60_000) {
    return `${Math.round(ms / 1000)} seconds`;
  }

  if (ms < 3_600_000) {
    return `${Math.round(ms / 60_000)} minutes`;
  }

  return `${Math.round(ms / 3_600_000)} hours`;
}
