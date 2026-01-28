/**
 * @sentinelseed/moltbot - CLI Module
 *
 * Provides command-line interface for Sentinel.
 * Users can invoke commands via /sentinel <command> in Moltbot.
 *
 * @module cli
 */

// =============================================================================
// Formatters
// =============================================================================

export {
  // Constants
  BOX,
  LEVEL_DISPLAY,
  // Level formatting
  formatLevel,
  formatLevelFull,
  formatLevelList,
  // Status formatting
  formatStatus,
  type StatusData,
  // Block message formatting
  formatBlockMessage,
  formatEscapeHint,
  // Alert formatting
  formatAlertNotification,
  // Help formatting
  formatHelp,
  type CommandDescription,
  // Utility functions
  formatHeader,
  formatSuccess,
  formatError,
  formatInfo,
  formatWarning,
} from './formatters';

// =============================================================================
// Commands
// =============================================================================

export {
  // Command management
  registerCommand,
  getCommand,
  getAllCommands,
  executeCommand,
  // Types
  type CommandContext,
  type CommandResult,
  type CommandHandler,
  type Command,
} from './commands';
