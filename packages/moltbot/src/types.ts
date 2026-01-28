/**
 * @sentinelseed/moltbot - Type Definitions
 *
 * Core type definitions for Sentinel Moltbot integration.
 * These types provide the foundation for protection levels,
 * validation, and Moltbot hook integration.
 */

// =============================================================================
// Protection Levels
// =============================================================================

/**
 * Protection level presets.
 * - 'off': Disabled, no monitoring or blocking
 * - 'watch': Monitor and alert only, never block (default)
 * - 'guard': Block critical threats (data leaks, destructive commands)
 * - 'shield': Maximum protection with strict blocking
 */
export type ProtectionLevel = 'off' | 'watch' | 'guard' | 'shield';

/**
 * Configuration for what to block at each level.
 */
export interface BlockingConfig {
  /** Block detected data leaks (API keys, passwords, etc.) */
  dataLeaks: boolean;
  /** Block destructive commands (rm -rf, DROP TABLE, etc.) */
  destructiveCommands: boolean;
  /** Block access to system paths (/etc, ~/.ssh, etc.) */
  systemPaths: boolean;
  /** Block suspicious URLs (known malicious domains, etc.) */
  suspiciousUrls: boolean;
  /** Block when AI appears to comply with injected instructions */
  injectionCompliance: boolean;
}

/**
 * Configuration for when to send alerts.
 */
export interface AlertingConfig {
  /** Alert on high-threat input detection */
  highThreatInput: boolean;
  /** Alert when actions are blocked */
  blockedActions: boolean;
  /** Alert on prompt injection attempts */
  promptInjection: boolean;
  /** Alert on unusual session patterns */
  sessionAnomalies: boolean;
}

/**
 * Seed template selection.
 */
export type SeedTemplate = 'none' | 'standard' | 'strict';

/**
 * Log verbosity level.
 */
export type LogLevel = 'none' | 'blocked' | 'warnings' | 'all';

/**
 * Complete level configuration.
 */
export interface LevelConfig {
  /** The protection level name */
  level: ProtectionLevel;
  /** Blocking configuration */
  blocking: BlockingConfig;
  /** Alerting configuration */
  alerting: AlertingConfig;
  /** Which seed template to inject */
  seedTemplate: SeedTemplate;
  /** Log verbosity */
  logLevel: LogLevel;
}

// =============================================================================
// Plugin Configuration
// =============================================================================

/**
 * Alert delivery configuration.
 */
export interface AlertsConfig {
  /** Whether alerts are enabled */
  enabled: boolean;
  /** Webhook URL for alert delivery */
  webhook?: string;
}

/**
 * Main plugin configuration.
 */
export interface SentinelMoltbotConfig {
  /** Protection level preset (default: 'watch') */
  level: ProtectionLevel;
  /** Alert configuration */
  alerts?: AlertsConfig;
  /** Patterns to ignore during validation (strings or regex) */
  ignorePatterns?: string[];
  /** Tool names that bypass validation */
  trustedTools?: string[];
  /** Tools that are always blocked (overrides trusted) */
  dangerousTools?: string[];
  /** Custom level overrides */
  custom?: Partial<LevelConfig>;
}

// =============================================================================
// Validation Results
// =============================================================================

/**
 * Risk level assessment.
 */
export type RiskLevel = 'none' | 'low' | 'medium' | 'high' | 'critical';

/**
 * THSP gate status.
 */
export type GateStatus = 'pass' | 'fail' | 'unknown';

/**
 * Issue type categories.
 */
export type IssueType =
  | 'data_leak'
  | 'destructive_command'
  | 'system_path'
  | 'suspicious_url'
  | 'prompt_injection'
  | 'jailbreak_attempt'
  | 'injection_compliance'
  | 'unknown';

/**
 * A detected issue during validation.
 */
export interface DetectedIssue {
  /** Type of issue */
  type: IssueType;
  /** Human-readable description */
  description: string;
  /** Evidence that triggered detection */
  evidence: string;
  /** Severity level */
  severity: RiskLevel;
  /** Which THSP gate this affects */
  gate?: 'truth' | 'harm' | 'scope' | 'purpose' | 'jailbreak';
}

/**
 * THSP gate results.
 */
export interface GateResults {
  truth: GateStatus;
  harm: GateStatus;
  scope: GateStatus;
  purpose: GateStatus;
  jailbreak: GateStatus;
}

/**
 * Output validation result.
 */
export interface OutputValidationResult {
  /** Whether the output is safe */
  safe: boolean;
  /** Whether to block this output */
  shouldBlock: boolean;
  /** Detected issues */
  issues: DetectedIssue[];
  /** THSP gate results */
  gates: GateResults;
  /** Overall risk level */
  riskLevel: RiskLevel;
  /** Suggested modified content (if applicable) */
  modifiedContent?: string;
  /** Validation duration in ms */
  durationMs: number;
}

/**
 * Tool validation result.
 */
export interface ToolValidationResult {
  /** Whether the tool call is safe */
  safe: boolean;
  /** Whether to block this tool call */
  shouldBlock: boolean;
  /** Detected issues */
  issues: DetectedIssue[];
  /** Risk level */
  riskLevel: RiskLevel;
  /** Human-readable reason (for block message) */
  reason?: string;
  /** Validation duration in ms */
  durationMs: number;
}

/**
 * Input analysis result (for logging/alerting, not blocking).
 */
export interface InputAnalysisResult {
  /** Threat level (0-5) */
  threatLevel: number;
  /** Whether this appears to be a prompt injection */
  isPromptInjection: boolean;
  /** Whether this appears to be a jailbreak attempt */
  isJailbreakAttempt: boolean;
  /** Detected issues */
  issues: DetectedIssue[];
  /** Analysis duration in ms */
  durationMs: number;
}

// =============================================================================
// Escape Hatches
// =============================================================================

/**
 * Allow-once state.
 */
export interface AllowOnceState {
  /** Whether allow-once is active */
  active: boolean;
  /** Scope of the allow-once */
  scope?: 'output' | 'tool' | 'any';
  /** When this expires (timestamp) */
  expiresAt?: number;
}

/**
 * Pause state.
 */
export interface PauseState {
  /** Whether Sentinel is paused */
  paused: boolean;
  /** When the pause expires (timestamp) */
  expiresAt?: number;
  /** Reason for pause */
  reason?: string;
}

/**
 * Trusted tool entry.
 */
export interface TrustedTool {
  /** Tool name */
  name: string;
  /** When this trust expires (timestamp, undefined = permanent) */
  expiresAt?: number;
  /** Who granted this trust */
  grantedBy?: string;
}

// =============================================================================
// Logging & Alerts
// =============================================================================

/**
 * Audit event types.
 */
export type AuditEventType =
  | 'input_analyzed'
  | 'output_validated'
  | 'output_blocked'
  | 'tool_validated'
  | 'tool_blocked'
  | 'seed_injected'
  | 'session_started'
  | 'session_ended'
  | 'config_changed'
  | 'escape_used'
  | 'error';

/**
 * Audit log entry.
 */
export interface AuditEntry {
  /** Unique entry ID */
  id: string;
  /** Timestamp */
  timestamp: number;
  /** Event type */
  event: AuditEventType;
  /** Outcome */
  outcome: 'allowed' | 'blocked' | 'alerted' | 'error';
  /** Event details */
  details: Record<string, unknown>;
  /** Session ID (if applicable) */
  sessionId?: string;
}

/**
 * Alert types.
 */
export type AlertType =
  | 'high_threat_input'
  | 'action_blocked'
  | 'prompt_injection'
  | 'session_anomaly'
  | 'error';

/**
 * Security alert.
 */
export interface SecurityAlert {
  /** Alert type */
  type: AlertType;
  /** Severity */
  severity: RiskLevel;
  /** Human-readable message */
  message: string;
  /** Timestamp */
  timestamp: number;
  /** Related audit entry ID */
  auditEntryId?: string;
  /** Additional context */
  context?: Record<string, unknown>;
}

// =============================================================================
// UX Messages
// =============================================================================

/**
 * Action types for Sentinel messages.
 */
export type SentinelAction =
  | 'blocked'
  | 'modified'
  | 'alerted'
  | 'info'
  | 'escape_activated';

/**
 * Message to display to the user.
 */
export interface SentinelMessage {
  /** Action that triggered this message */
  action: SentinelAction;
  /** Brief title */
  title: string;
  /** Detailed description */
  description: string;
  /** How to escape (if applicable) */
  escapeHint?: string;
}

// =============================================================================
// Version & Metadata
// =============================================================================

/**
 * Package version.
 */
export const VERSION = '0.1.0';

/**
 * Package name.
 */
export const PACKAGE_NAME = '@sentinelseed/moltbot';

/**
 * Supported Moltbot version range.
 */
export const MOLTBOT_VERSION_RANGE = '>=1.0.0';
