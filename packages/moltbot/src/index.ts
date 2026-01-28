/**
 * @sentinelseed/moltbot
 *
 * AI safety guardrails for Moltbot applications.
 *
 * This package provides Moltbot-compatible hooks that implement:
 * - Protection Levels: watch, guard, shield for different security needs
 * - Output Validation: Prevent data leaks before they leave
 * - Tool Validation: Block dangerous commands and system access
 * - Input Analysis: Detect prompt injection and jailbreak attempts
 * - Seed Injection: Add safety context to improve AI behavior
 *
 * @example Quick Start
 * ```typescript
 * // In your Moltbot config:
 * {
 *   "plugins": {
 *     "sentinel": {
 *       "level": "watch"  // or "guard", "shield"
 *     }
 *   }
 * }
 * ```
 *
 * @example Programmatic Usage
 * ```typescript
 * import { createSentinelHooks } from '@sentinelseed/moltbot';
 *
 * const hooks = createSentinelHooks({
 *   level: 'guard',
 *   alerts: {
 *     enabled: true,
 *     webhook: 'https://your-webhook.com/sentinel'
 *   }
 * });
 * ```
 *
 * @see https://github.com/sentinel-seed/sentinel/tree/main/packages/moltbot
 * @see https://github.com/moltbot/moltbot
 */

// =============================================================================
// Hook Factory (Primary API)
// =============================================================================

export { createSentinelHooks } from './hooks';

// =============================================================================
// Configuration
// =============================================================================

export {
  // Level presets
  OFF_LEVEL,
  WATCH_LEVEL,
  GUARD_LEVEL,
  SHIELD_LEVEL,
  LEVELS,
  // Configuration functions
  getDefaultConfig,
  parseConfig,
  getLevelConfig,
  // Default config
  DEFAULT_CONFIG,
} from './config';

// =============================================================================
// Validators (For Advanced Use)
// =============================================================================

export {
  validateOutput,
  validateTool,
  analyzeInput,
} from './validators';

// =============================================================================
// Type Exports
// =============================================================================

export type {
  // Protection levels
  ProtectionLevel,
  LevelConfig,
  BlockingConfig,
  AlertingConfig,
  SeedTemplate,
  LogLevel,

  // Plugin configuration
  SentinelMoltbotConfig,
  AlertsConfig,

  // Validation results
  RiskLevel,
  GateStatus,
  IssueType,
  DetectedIssue,
  GateResults,
  OutputValidationResult,
  ToolValidationResult,
  InputAnalysisResult,

  // Escape hatches
  AllowOnceState,
  PauseState,
  TrustedTool,

  // Logging & alerts
  AuditEventType,
  AuditEntry,
  AlertType,
  SecurityAlert,

  // UX
  SentinelAction,
  SentinelMessage,
} from './types';

// Hook types
export type {
  SentinelHooks,
  MessageReceivedEvent,
  BeforeAgentStartEvent,
  BeforeAgentStartResult,
  MessageSendingEvent,
  MessageSendingResult,
  BeforeToolCallEvent,
  BeforeToolCallResult,
  AgentEndEvent,
} from './hooks';

// =============================================================================
// Escape Hatches
// =============================================================================

export {
  // Managers
  EscapeManager,
  createEscapeManager,
  AllowOnceManager,
  createAllowOnceManager,
  PauseManager,
  createPauseManager,
  TrustManager,
  createTrustManager,
  // Utilities
  isValidScope,
  formatRemainingTime,
  formatPauseTime,
  isValidToolPattern,
  formatTrustDuration,
  // Constants
  DEFAULT_EXPIRATION_MS,
  DEFAULT_PAUSE_DURATION_MS,
  DEFAULT_TRUST_DURATION_MS,
  GLOBAL_SESSION_ID,
  GLOBAL_TRUST_SESSION_ID,
  // Types
  type AllowOnceScope,
  type AllowOnceToken,
  type GrantOptions,
  type AllowOnceCheckResult,
  type AllowOnceUseResult,
  type PauseRecord,
  type PauseOptions,
  type PauseResult,
  type ResumeResult,
  type TrustLevel,
  type TrustRecord,
  type TrustOptions,
  type TrustResult,
  type TrustCheckResult,
  type EscapeState,
  type EscapeManagerOptions,
  type EscapeCheckResult,
  type EscapeStats,
} from './escapes';

// =============================================================================
// Logging & Alerts
// =============================================================================

export {
  // Formatters
  formatTimestamp,
  formatDuration,
  formatRiskLevel,
  getRiskBadge,
  formatIssue,
  formatIssueList,
  formatAuditEntry,
  formatAuditLog,
  formatAlert,
  formatAlertForWebhook,
  formatSessionSummary,
  truncate,
  indent,
  stripColors,
  COLORS,
  RISK_COLORS,
  ALERT_ICONS,
  AUDIT_ICONS,
  // AuditLog
  AuditLog,
  createAuditLog,
  DEFAULT_MAX_ENTRIES,
  DEFAULT_ENTRY_TTL_MS,
  // AlertManager
  AlertManager,
  createAlertManager,
  DEFAULT_RATE_LIMIT_WINDOW_MS,
  DEFAULT_RATE_LIMIT_MAX,
  DEFAULT_WEBHOOK_TIMEOUT_MS,
  DEFAULT_WEBHOOK_RETRIES,
  // Types
  type CreateEntryOptions,
  type AuditFilter,
  type AuditLogOptions,
  type PersistHandler,
  type AuditStats,
  type CreateAlertOptions,
  type WebhookConfig,
  type AlertManagerOptions,
  type SendAlertResult,
  type AlertStats,
} from './logging';

// =============================================================================
// CLI (User Interface)
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
  // Command management
  registerCommand,
  getCommand,
  getAllCommands,
  executeCommand,
  // Command types
  type CommandContext,
  type CommandResult,
  type CommandHandler,
  type Command,
} from './cli';

// =============================================================================
// Internal Utilities (Advanced)
// =============================================================================

export {
  // Logger
  logger,
  setLogger,
  configureLogger,
  resetLogger,
  createChildLogger,
  type LogLevel as InternalLogLevel,
  type LogContext,
  type Logger,
  type LoggerConfig,
  // Metrics
  metrics,
  getMetricsSnapshot,
  resetMetrics,
  getAverageValidationTime,
  getBlockRate,
  getPassRate,
  getMostCommonIssueType,
  getMetricsSummary,
  type MetricsSnapshot,
  // Pattern Registry
  patternRegistry,
  type PatternCategory,
  type PatternEntry,
  type RegistrySnapshot,
} from './internal';

// =============================================================================
// Version & Metadata
// =============================================================================

import { VERSION, PACKAGE_NAME, MOLTBOT_VERSION_RANGE } from './types';

export { VERSION, PACKAGE_NAME, MOLTBOT_VERSION_RANGE };

/**
 * Get available protection levels.
 */
export function getAvailableLevels(): string[] {
  return ['off', 'watch', 'guard', 'shield'];
}

/**
 * Check if a level is valid.
 */
export function isValidLevel(level: string): level is ProtectionLevel {
  return ['off', 'watch', 'guard', 'shield'].includes(level);
}

// Re-import for type inference
import type { ProtectionLevel } from './types';
