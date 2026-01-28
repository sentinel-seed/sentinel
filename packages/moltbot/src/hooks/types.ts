/**
 * @sentinelseed/moltbot - Hook Type Definitions
 *
 * This module defines the type contracts for Sentinel hooks.
 *
 * Architecture:
 * - Event types: Input received from Moltbot (or caller)
 * - Result types: Output returned by Sentinel handlers
 * - Session types: Per-session state tracking
 *
 * Design Principles:
 * - Event types are Moltbot-compatible (minimal, what Moltbot provides)
 * - Result types are Sentinel-rich (detailed info for logging/metrics)
 * - All types are immutable (readonly where applicable)
 * - No optional fields without clear semantics
 *
 * @module hooks/types
 */

import type {
  DetectedIssue,
  RiskLevel,
  SeedTemplate,
  LevelConfig,
  SentinelMoltbotConfig,
  AlertingConfig,
} from '../types';

// =============================================================================
// Event Types (Input to Hooks)
// =============================================================================
// These types represent what Moltbot (or any caller) provides to hooks.
// They should be minimal and stable.

/**
 * Event fired when a message is received from the user.
 *
 * This is a fire-and-forget hook - it cannot block the message.
 * Use it for threat analysis, logging, and alerting.
 */
export interface MessageReceivedEvent {
  /** The message content from the user */
  readonly content: string;
  /** Unique session identifier */
  readonly sessionId: string;
  /** When the message was received (Unix timestamp ms) */
  readonly timestamp: number;
}

/**
 * Event fired before the AI agent starts processing.
 *
 * This hook can inject additional context (safety seed) into the prompt.
 */
export interface BeforeAgentStartEvent {
  /** Unique session identifier */
  readonly sessionId: string;
  /** The current system prompt (if any) */
  readonly systemPrompt?: string;
}

/**
 * Event fired before a message is sent to the user.
 *
 * This hook can block or modify the message.
 */
export interface MessageSendingEvent {
  /** The message content to be sent */
  readonly content: string;
  /** Unique session identifier */
  readonly sessionId: string;
}

/**
 * Event fired before a tool is executed.
 *
 * This hook can block the tool call or modify parameters.
 */
export interface BeforeToolCallEvent {
  /** Name of the tool being called */
  readonly toolName: string;
  /** Parameters passed to the tool */
  readonly params: Readonly<Record<string, unknown>>;
  /** Unique session identifier */
  readonly sessionId: string;
}

/**
 * Event fired when the agent session ends.
 *
 * This is a fire-and-forget hook for session analysis and logging.
 */
export interface AgentEndEvent {
  /** Unique session identifier */
  readonly sessionId: string;
  /** Whether the session completed successfully */
  readonly success: boolean;
  /** Error if session failed */
  readonly error?: Error;
  /** Total session duration in milliseconds */
  readonly durationMs?: number;
}

// =============================================================================
// Result Types (Output from Hooks)
// =============================================================================
// These types represent what Sentinel returns after processing.
// They are rich in detail for logging, metrics, and decision-making.

/**
 * Result of analyzing a received message.
 *
 * Note: This hook cannot block messages, only analyze and alert.
 */
export interface MessageReceivedResult {
  /** Confirms analysis was performed */
  readonly analyzed: true;
  /** Threat level assessment (0-5) */
  readonly threatLevel: number;
  /** Whether prompt injection was detected */
  readonly isPromptInjection: boolean;
  /** Whether a jailbreak attempt was detected */
  readonly isJailbreakAttempt: boolean;
  /** Detailed issues found during analysis */
  readonly issues: readonly DetectedIssue[];
  /** Whether this warrants an alert based on config */
  readonly shouldAlert: boolean;
  /** How long analysis took in milliseconds */
  readonly durationMs: number;
}

/**
 * Result of the before-agent-start hook.
 *
 * Returns the safety seed to inject (if any).
 */
export interface BeforeAgentStartResult {
  /** Whether a seed was injected */
  readonly seedInjected: boolean;
  /** The seed template that was used */
  readonly seedTemplate: SeedTemplate;
  /** Additional context to prepend to the conversation */
  readonly additionalContext?: string;
}

/**
 * Result of validating a message before sending.
 *
 * This hook CAN block messages.
 */
export interface MessageSendingResult {
  /** Confirms validation was performed */
  readonly validated: true;
  /** Whether the content passed validation */
  readonly safe: boolean;
  /** Whether the message should be blocked */
  readonly shouldBlock: boolean;
  /** Human-readable reason for blocking (if blocked) */
  readonly cancelReason?: string;
  /** Detailed issues found during validation */
  readonly issues: readonly DetectedIssue[];
  /** Overall risk level */
  readonly riskLevel: RiskLevel;
  /** How long validation took in milliseconds */
  readonly durationMs: number;
}

/**
 * Result of validating a tool call.
 *
 * This hook CAN block tool calls.
 */
export interface BeforeToolCallResult {
  /** Confirms validation was performed */
  readonly validated: true;
  /** Whether the tool call passed validation */
  readonly safe: boolean;
  /** Whether the tool call should be blocked */
  readonly shouldBlock: boolean;
  /** Human-readable reason for blocking (if blocked) */
  readonly blockReason?: string;
  /** Detailed issues found during validation */
  readonly issues: readonly DetectedIssue[];
  /** Overall risk level */
  readonly riskLevel: RiskLevel;
  /** How long validation took in milliseconds */
  readonly durationMs: number;
}

/**
 * Result of the agent-end hook.
 *
 * Contains session summary for logging and anomaly detection.
 */
export interface AgentEndResult {
  /** Confirms logging was performed */
  readonly logged: true;
  /** Summary of the session */
  readonly sessionSummary: SessionSummary;
  /** Whether any anomalies were detected */
  readonly anomalyDetected: boolean;
  /** Type of anomaly if detected */
  readonly anomalyType?: SessionAnomalyType;
}

// =============================================================================
// Session Types
// =============================================================================

/**
 * Types of session anomalies that can be detected.
 */
export type SessionAnomalyType =
  | 'high_threat_rate'      // Too many high-threat inputs
  | 'high_block_rate'       // Too many blocked actions
  | 'rapid_requests'        // Unusual request frequency
  | 'repeated_attacks'      // Same attack pattern repeated
  | 'escalation_pattern';   // Threat level escalating over time

/**
 * Summary of a completed session.
 */
export interface SessionSummary {
  /** Session identifier */
  readonly sessionId: string;
  /** Whether the session ended successfully */
  readonly success: boolean;
  /** Total session duration in milliseconds */
  readonly durationMs: number;
  /** Number of messages received */
  readonly messageCount: number;
  /** Number of tool calls made */
  readonly toolCallCount: number;
  /** Number of issues detected across all validations */
  readonly issuesDetected: number;
  /** Number of actions that were blocked */
  readonly actionsBlocked: number;
  /** Highest threat level observed in the session */
  readonly maxThreatLevel: number;
  /** Whether any alerts were triggered */
  readonly alertsTriggered: number;
}

/**
 * Per-session state tracking.
 *
 * Used internally by hooks to accumulate statistics
 * and detect anomalies across the session lifecycle.
 */
export interface SessionState {
  /** Session identifier */
  readonly sessionId: string;
  /** When the session started (Unix timestamp ms) */
  readonly startedAt: number;
  /** Running count of messages received */
  messageCount: number;
  /** Running count of tool calls */
  toolCallCount: number;
  /** Running count of issues detected */
  issuesDetected: number;
  /** Running count of blocked actions */
  actionsBlocked: number;
  /** Running count of alerts triggered */
  alertsTriggered: number;
  /** Highest threat level seen so far */
  maxThreatLevel: number;
  /** Recent threat levels for pattern detection */
  recentThreatLevels: number[];
}

// =============================================================================
// Handler Context Types
// =============================================================================

/**
 * Context passed to all hook handlers.
 *
 * Contains configuration and state needed for processing.
 */
export interface HookContext {
  /** Parsed and validated plugin configuration */
  readonly config: SentinelMoltbotConfig;
  /** Resolved level configuration */
  readonly levelConfig: LevelConfig;
  /** Session state (mutable for accumulating stats) */
  sessionState?: SessionState;
}

/**
 * Options for determining if an alert should be sent.
 */
export interface AlertDecisionContext {
  /** Threat level from analysis */
  readonly threatLevel: number;
  /** Whether prompt injection was detected */
  readonly isPromptInjection: boolean;
  /** Whether an action was blocked */
  readonly wasBlocked: boolean;
  /** Alerting configuration from level */
  readonly alertingConfig: AlertingConfig;
}

// =============================================================================
// Moltbot-Compatible Result Types
// =============================================================================
// These types match what Moltbot expects from hooks.
// They are simpler than our internal result types.

/**
 * What Moltbot expects from before_agent_start hook.
 */
export interface MoltbotAgentStartResult {
  /** Modified system prompt (optional) */
  systemPrompt?: string;
  /** Additional context to prepend */
  additionalContext?: string;
}

/**
 * What Moltbot expects from message_sending hook.
 */
export interface MoltbotMessageSendingResult {
  /** Modified content (optional) */
  content?: string;
  /** Whether to cancel sending */
  cancel?: boolean;
  /** Reason for cancellation */
  cancelReason?: string;
}

/**
 * What Moltbot expects from before_tool_call hook.
 */
export interface MoltbotToolCallResult {
  /** Modified parameters (optional) */
  params?: Record<string, unknown>;
  /** Whether to block the tool call */
  block?: boolean;
  /** Reason for blocking */
  blockReason?: string;
}

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Check if a value is a valid MessageReceivedEvent.
 */
export function isMessageReceivedEvent(value: unknown): value is MessageReceivedEvent {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.content === 'string' &&
    typeof obj.sessionId === 'string' &&
    typeof obj.timestamp === 'number'
  );
}

/**
 * Check if a value is a valid BeforeAgentStartEvent.
 */
export function isBeforeAgentStartEvent(value: unknown): value is BeforeAgentStartEvent {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.sessionId === 'string' &&
    (obj.systemPrompt === undefined || typeof obj.systemPrompt === 'string')
  );
}

/**
 * Check if a value is a valid MessageSendingEvent.
 */
export function isMessageSendingEvent(value: unknown): value is MessageSendingEvent {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.content === 'string' &&
    typeof obj.sessionId === 'string'
  );
}

/**
 * Check if a value is a valid BeforeToolCallEvent.
 */
export function isBeforeToolCallEvent(value: unknown): value is BeforeToolCallEvent {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.toolName === 'string' &&
    typeof obj.params === 'object' &&
    obj.params !== null &&
    typeof obj.sessionId === 'string'
  );
}

/**
 * Check if a value is a valid AgentEndEvent.
 */
export function isAgentEndEvent(value: unknown): value is AgentEndEvent {
  if (typeof value !== 'object' || value === null) return false;
  const obj = value as Record<string, unknown>;
  return (
    typeof obj.sessionId === 'string' &&
    typeof obj.success === 'boolean'
  );
}

// =============================================================================
// Factory Functions
// =============================================================================

/**
 * Create a new session state object.
 *
 * @param sessionId - Unique session identifier
 * @returns Fresh session state
 */
export function createSessionState(sessionId: string): SessionState {
  return {
    sessionId,
    startedAt: Date.now(),
    messageCount: 0,
    toolCallCount: 0,
    issuesDetected: 0,
    actionsBlocked: 0,
    alertsTriggered: 0,
    maxThreatLevel: 0,
    recentThreatLevels: [],
  };
}

/**
 * Create a session summary from session state.
 *
 * @param state - Current session state
 * @param success - Whether session completed successfully
 * @returns Session summary
 */
export function createSessionSummary(
  state: SessionState,
  success: boolean
): SessionSummary {
  return {
    sessionId: state.sessionId,
    success,
    durationMs: Date.now() - state.startedAt,
    messageCount: state.messageCount,
    toolCallCount: state.toolCallCount,
    issuesDetected: state.issuesDetected,
    actionsBlocked: state.actionsBlocked,
    maxThreatLevel: state.maxThreatLevel,
    alertsTriggered: state.alertsTriggered,
  };
}
