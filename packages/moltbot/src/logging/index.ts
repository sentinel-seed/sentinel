/**
 * @sentinelseed/moltbot - Logging Module
 *
 * Provides logging, audit, and alerting functionality.
 *
 * Components:
 * - Formatters: Pretty-print logs, alerts, and audit entries
 * - AuditLog: Track and query security events
 * - AlertManager: Send alerts via webhooks
 *
 * @module logging
 */

// =============================================================================
// Formatters
// =============================================================================

export {
  // Colors
  COLORS,
  RISK_COLORS,
  ALERT_ICONS,
  AUDIT_ICONS,
  // Time formatting
  formatTimestamp,
  formatDuration,
  // Risk level formatting
  formatRiskLevel,
  getRiskBadge,
  // Issue formatting
  formatIssue,
  formatIssueList,
  // Audit formatting
  formatAuditEntry,
  formatAuditLog,
  // Alert formatting
  formatAlert,
  formatAlertForWebhook,
  // Summary formatting
  formatSessionSummary,
  // Utilities
  truncate,
  indent,
  stripColors,
} from './formatters';

// =============================================================================
// Audit Log
// =============================================================================

export {
  // Class
  AuditLog,
  createAuditLog,
  // Constants
  DEFAULT_MAX_ENTRIES,
  DEFAULT_ENTRY_TTL_MS,
  // Types
  type CreateEntryOptions,
  type AuditFilter,
  type AuditLogOptions,
  type PersistHandler,
  type AuditStats,
} from './audit';

// =============================================================================
// Alert Manager
// =============================================================================

export {
  // Class
  AlertManager,
  createAlertManager,
  // Constants
  DEFAULT_RATE_LIMIT_WINDOW_MS,
  DEFAULT_RATE_LIMIT_MAX,
  DEFAULT_WEBHOOK_TIMEOUT_MS,
  DEFAULT_WEBHOOK_RETRIES,
  // Types
  type CreateAlertOptions,
  type WebhookConfig,
  type AlertManagerOptions,
  type SendAlertResult,
  type AlertStats,
} from './alerts';
