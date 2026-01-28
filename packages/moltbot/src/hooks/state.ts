/**
 * @sentinelseed/moltbot - Session State Management
 *
 * This module provides session state management for tracking
 * validation statistics, detecting anomalies, and generating
 * session summaries.
 *
 * Design:
 * - SessionState is mutable for performance (counters updated frequently)
 * - SessionStateManager handles multiple concurrent sessions
 * - Anomaly detection uses configurable thresholds
 * - All state is in-memory (no persistence)
 *
 * @module hooks/state
 */

import type {
  SessionState,
  SessionSummary,
  SessionAnomalyType,
} from './types';
import { createSessionState, createSessionSummary } from './types';

// Re-export types and factories from types.ts
export type { SessionState, SessionSummary, SessionAnomalyType };
export { createSessionState, createSessionSummary };

// =============================================================================
// Anomaly Detection Configuration
// =============================================================================

/**
 * Configuration for anomaly detection thresholds.
 */
export interface AnomalyDetectionConfig {
  /** Minimum threat level to count as "high threat" (default: 4) */
  highThreatThreshold: number;
  /** Rate of high-threat inputs that triggers anomaly (0-1, default: 0.3) */
  highThreatRateThreshold: number;
  /** Rate of blocked actions that triggers anomaly (0-1, default: 0.5) */
  highBlockRateThreshold: number;
  /** Minimum messages before checking rates (default: 5) */
  minMessagesForRateCheck: number;
  /** Number of recent threat levels to track for escalation (default: 5) */
  recentThreatWindowSize: number;
  /** Difference in avg threat level that indicates escalation (default: 2) */
  escalationThreshold: number;
}

/**
 * Default anomaly detection configuration.
 */
export const DEFAULT_ANOMALY_CONFIG: Readonly<AnomalyDetectionConfig> = {
  highThreatThreshold: 4,
  highThreatRateThreshold: 0.3,
  highBlockRateThreshold: 0.5,
  minMessagesForRateCheck: 5,
  recentThreatWindowSize: 5,
  escalationThreshold: 2,
};

// =============================================================================
// State Update Functions
// =============================================================================

/**
 * Record a received message in session state.
 *
 * @param state - Session state to update
 * @param threatLevel - Threat level of the message (0-5)
 */
export function recordMessageReceived(
  state: SessionState,
  threatLevel: number
): void {
  state.messageCount++;

  // Update max threat level
  if (threatLevel > state.maxThreatLevel) {
    state.maxThreatLevel = threatLevel;
  }

  // Track recent threat levels for escalation detection
  state.recentThreatLevels.push(threatLevel);

  // Keep window size bounded
  if (state.recentThreatLevels.length > DEFAULT_ANOMALY_CONFIG.recentThreatWindowSize * 2) {
    state.recentThreatLevels = state.recentThreatLevels.slice(
      -DEFAULT_ANOMALY_CONFIG.recentThreatWindowSize
    );
  }
}

/**
 * Record a tool call in session state.
 *
 * @param state - Session state to update
 * @param blocked - Whether the tool call was blocked
 * @param issueCount - Number of issues detected
 */
export function recordToolCall(
  state: SessionState,
  blocked: boolean,
  issueCount: number
): void {
  state.toolCallCount++;
  state.issuesDetected += issueCount;

  if (blocked) {
    state.actionsBlocked++;
  }
}

/**
 * Record an output validation in session state.
 *
 * @param state - Session state to update
 * @param blocked - Whether the output was blocked
 * @param issueCount - Number of issues detected
 */
export function recordOutputValidation(
  state: SessionState,
  blocked: boolean,
  issueCount: number
): void {
  state.issuesDetected += issueCount;

  if (blocked) {
    state.actionsBlocked++;
  }
}

/**
 * Record an alert being triggered.
 *
 * @param state - Session state to update
 */
export function recordAlert(state: SessionState): void {
  state.alertsTriggered++;
}

// =============================================================================
// Anomaly Detection
// =============================================================================

/**
 * Result of anomaly detection.
 */
export interface AnomalyDetectionResult {
  /** Whether an anomaly was detected */
  detected: boolean;
  /** Type of anomaly if detected */
  type?: SessionAnomalyType;
  /** Confidence level (0-1) */
  confidence: number;
  /** Human-readable description */
  description?: string;
}

/**
 * Detect anomalies in session state.
 *
 * Checks for:
 * - High rate of high-threat inputs
 * - High rate of blocked actions
 * - Escalating threat levels
 * - Repeated attack patterns
 *
 * @param state - Session state to analyze
 * @param config - Anomaly detection configuration (optional)
 * @returns Anomaly detection result
 */
export function detectAnomalies(
  state: SessionState,
  config: AnomalyDetectionConfig = DEFAULT_ANOMALY_CONFIG
): AnomalyDetectionResult {
  // Not enough data for rate-based detection
  if (state.messageCount < config.minMessagesForRateCheck) {
    return { detected: false, confidence: 0 };
  }

  // Check for high threat rate
  const highThreatCount = state.recentThreatLevels.filter(
    t => t >= config.highThreatThreshold
  ).length;
  const threatRate = highThreatCount / state.recentThreatLevels.length;

  if (threatRate >= config.highThreatRateThreshold) {
    return {
      detected: true,
      type: 'high_threat_rate',
      confidence: Math.min(1, threatRate / config.highThreatRateThreshold),
      description: `High threat rate: ${(threatRate * 100).toFixed(0)}% of recent messages are high-threat`,
    };
  }

  // Check for high block rate
  const totalActions = state.toolCallCount + state.messageCount;
  if (totalActions > 0) {
    const blockRate = state.actionsBlocked / totalActions;

    if (blockRate >= config.highBlockRateThreshold) {
      return {
        detected: true,
        type: 'high_block_rate',
        confidence: Math.min(1, blockRate / config.highBlockRateThreshold),
        description: `High block rate: ${(blockRate * 100).toFixed(0)}% of actions blocked`,
      };
    }
  }

  // Check for escalation pattern
  const escalation = detectEscalationPattern(state, config);
  if (escalation.detected) {
    return escalation;
  }

  // Check for repeated attack patterns
  const repeated = detectRepeatedAttacks(state, config);
  if (repeated.detected) {
    return repeated;
  }

  return { detected: false, confidence: 0 };
}

/**
 * Detect escalating threat levels over time.
 *
 * @param state - Session state
 * @param config - Configuration
 * @returns Detection result
 */
function detectEscalationPattern(
  state: SessionState,
  config: AnomalyDetectionConfig
): AnomalyDetectionResult {
  const levels = state.recentThreatLevels;

  if (levels.length < config.recentThreatWindowSize) {
    return { detected: false, confidence: 0 };
  }

  // Compare first half vs second half of recent threats
  const midpoint = Math.floor(levels.length / 2);
  const firstHalf = levels.slice(0, midpoint);
  const secondHalf = levels.slice(midpoint);

  const firstAvg = average(firstHalf);
  const secondAvg = average(secondHalf);

  const escalation = secondAvg - firstAvg;

  if (escalation >= config.escalationThreshold) {
    return {
      detected: true,
      type: 'escalation_pattern',
      confidence: Math.min(1, escalation / (config.escalationThreshold * 2)),
      description: `Threat escalation detected: avg increased from ${firstAvg.toFixed(1)} to ${secondAvg.toFixed(1)}`,
    };
  }

  return { detected: false, confidence: 0 };
}

/**
 * Detect repeated high-threat attacks.
 *
 * @param state - Session state
 * @param config - Configuration
 * @returns Detection result
 */
function detectRepeatedAttacks(
  state: SessionState,
  config: AnomalyDetectionConfig
): AnomalyDetectionResult {
  const levels = state.recentThreatLevels;

  // Count consecutive high-threat messages
  let consecutiveHighThreats = 0;
  let maxConsecutive = 0;

  for (const level of levels) {
    if (level >= config.highThreatThreshold) {
      consecutiveHighThreats++;
      maxConsecutive = Math.max(maxConsecutive, consecutiveHighThreats);
    } else {
      consecutiveHighThreats = 0;
    }
  }

  // 3+ consecutive high-threat messages indicates repeated attacks
  if (maxConsecutive >= 3) {
    return {
      detected: true,
      type: 'repeated_attacks',
      confidence: Math.min(1, maxConsecutive / 5),
      description: `Repeated attacks: ${maxConsecutive} consecutive high-threat messages`,
    };
  }

  return { detected: false, confidence: 0 };
}

// =============================================================================
// Session State Manager
// =============================================================================

/**
 * Manager for multiple concurrent session states.
 *
 * Handles:
 * - Creating and retrieving session states
 * - Automatic cleanup of old sessions
 * - Session statistics across all sessions
 */
export class SessionStateManager {
  private sessions: Map<string, SessionState> = new Map();
  private maxSessions: number;
  private sessionTimeoutMs: number;

  /**
   * Create a new session state manager.
   *
   * @param options - Manager options
   */
  constructor(options: SessionStateManagerOptions = {}) {
    this.maxSessions = options.maxSessions ?? 1000;
    this.sessionTimeoutMs = options.sessionTimeoutMs ?? 30 * 60 * 1000; // 30 minutes
  }

  /**
   * Get or create a session state.
   *
   * @param sessionId - Session identifier
   * @returns Session state (creates if not exists)
   */
  getOrCreate(sessionId: string): SessionState {
    let state = this.sessions.get(sessionId);

    if (!state) {
      // Cleanup if at capacity
      if (this.sessions.size >= this.maxSessions) {
        this.cleanup();
      }

      state = createSessionState(sessionId);
      this.sessions.set(sessionId, state);
    }

    return state;
  }

  /**
   * Get a session state if it exists.
   *
   * @param sessionId - Session identifier
   * @returns Session state or undefined
   */
  get(sessionId: string): SessionState | undefined {
    return this.sessions.get(sessionId);
  }

  /**
   * Check if a session exists.
   *
   * @param sessionId - Session identifier
   * @returns True if session exists
   */
  has(sessionId: string): boolean {
    return this.sessions.has(sessionId);
  }

  /**
   * End a session and get summary.
   *
   * @param sessionId - Session identifier
   * @param success - Whether session ended successfully
   * @returns Session summary, or undefined if session not found
   */
  endSession(sessionId: string, success: boolean): SessionSummary | undefined {
    const state = this.sessions.get(sessionId);

    if (!state) {
      return undefined;
    }

    const summary = createSessionSummary(state, success);
    this.sessions.delete(sessionId);

    return summary;
  }

  /**
   * Remove a session without generating summary.
   *
   * @param sessionId - Session identifier
   * @returns True if session was removed
   */
  remove(sessionId: string): boolean {
    return this.sessions.delete(sessionId);
  }

  /**
   * Get the number of active sessions.
   */
  get size(): number {
    return this.sessions.size;
  }

  /**
   * Get all session IDs.
   */
  get sessionIds(): string[] {
    return Array.from(this.sessions.keys());
  }

  /**
   * Clear all sessions.
   */
  clear(): void {
    this.sessions.clear();
  }

  /**
   * Cleanup old sessions that have exceeded timeout.
   *
   * @returns Number of sessions removed
   */
  cleanup(): number {
    const now = Date.now();
    const cutoff = now - this.sessionTimeoutMs;
    let removed = 0;

    for (const [sessionId, state] of this.sessions) {
      if (state.startedAt < cutoff) {
        this.sessions.delete(sessionId);
        removed++;
      }
    }

    return removed;
  }

  /**
   * Get aggregate statistics across all sessions.
   */
  getAggregateStats(): AggregateSessionStats {
    let totalMessages = 0;
    let totalToolCalls = 0;
    let totalIssues = 0;
    let totalBlocked = 0;
    let totalAlerts = 0;
    let maxThreatLevel = 0;

    for (const state of this.sessions.values()) {
      totalMessages += state.messageCount;
      totalToolCalls += state.toolCallCount;
      totalIssues += state.issuesDetected;
      totalBlocked += state.actionsBlocked;
      totalAlerts += state.alertsTriggered;
      maxThreatLevel = Math.max(maxThreatLevel, state.maxThreatLevel);
    }

    return {
      activeSessions: this.sessions.size,
      totalMessages,
      totalToolCalls,
      totalIssues,
      totalBlocked,
      totalAlerts,
      maxThreatLevel,
    };
  }
}

/**
 * Options for SessionStateManager.
 */
export interface SessionStateManagerOptions {
  /** Maximum number of sessions to track (default: 1000) */
  maxSessions?: number;
  /** Session timeout in milliseconds (default: 30 minutes) */
  sessionTimeoutMs?: number;
}

/**
 * Aggregate statistics across all active sessions.
 */
export interface AggregateSessionStats {
  /** Number of active sessions */
  activeSessions: number;
  /** Total messages across all sessions */
  totalMessages: number;
  /** Total tool calls across all sessions */
  totalToolCalls: number;
  /** Total issues detected across all sessions */
  totalIssues: number;
  /** Total blocked actions across all sessions */
  totalBlocked: number;
  /** Total alerts triggered across all sessions */
  totalAlerts: number;
  /** Maximum threat level observed across all sessions */
  maxThreatLevel: number;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Calculate average of an array of numbers.
 */
function average(numbers: number[]): number {
  if (numbers.length === 0) return 0;
  return numbers.reduce((sum, n) => sum + n, 0) / numbers.length;
}

/**
 * Get a human-readable session duration.
 *
 * @param state - Session state
 * @returns Human-readable duration string
 */
export function getSessionDuration(state: SessionState): string {
  const durationMs = Date.now() - state.startedAt;
  const seconds = Math.floor(durationMs / 1000);

  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;

  return `${hours}h ${remainingMinutes}m`;
}

/**
 * Check if a session is still active (not timed out).
 *
 * @param state - Session state
 * @param timeoutMs - Timeout in milliseconds (default: 30 minutes)
 * @returns True if session is still active
 */
export function isSessionActive(
  state: SessionState,
  timeoutMs: number = 30 * 60 * 1000
): boolean {
  return Date.now() - state.startedAt < timeoutMs;
}

/**
 * Get session risk assessment based on statistics.
 *
 * @param state - Session state
 * @returns Risk level: 'low', 'medium', 'high', or 'critical'
 */
export function getSessionRiskLevel(
  state: SessionState
): 'low' | 'medium' | 'high' | 'critical' {
  // Critical: max threat level is 5 or many blocks
  if (state.maxThreatLevel >= 5 || state.actionsBlocked >= 5) {
    return 'critical';
  }

  // High: max threat level is 4 or several blocks
  if (state.maxThreatLevel >= 4 || state.actionsBlocked >= 3) {
    return 'high';
  }

  // Medium: max threat level is 3 or some issues
  if (state.maxThreatLevel >= 3 || state.issuesDetected >= 5) {
    return 'medium';
  }

  // Low: everything else
  return 'low';
}
