/**
 * @sentinelseed/moltbot - Trust Escape Hatch
 *
 * Provides a mechanism to trust specific tools temporarily or permanently.
 * Trusted tools bypass Sentinel validation entirely.
 *
 * Features:
 * - Per-session trust lists
 * - Global trust lists
 * - Temporary trust with expiration
 * - Permanent trust
 * - Pattern matching (wildcards)
 *
 * @module escapes/trust
 */

import type { TrustedTool } from '../types';

// =============================================================================
// Constants
// =============================================================================

/** Default trust duration in milliseconds (1 hour) */
export const DEFAULT_TRUST_DURATION_MS = 60 * 60 * 1000;

/** Maximum trust duration (24 hours) */
export const MAX_TRUST_DURATION_MS = 24 * 60 * 60 * 1000;

/** Special session ID for global trust */
export const GLOBAL_TRUST_SESSION_ID = '__global_trust__';

// =============================================================================
// Types
// =============================================================================

/**
 * Trust level for a tool.
 */
export type TrustLevel = 'temporary' | 'permanent' | 'session';

/**
 * Internal trust record with full metadata.
 */
export interface TrustRecord extends TrustedTool {
  /** Trust level */
  level: TrustLevel;
  /** Session ID this trust applies to (or global) */
  sessionId: string;
  /** When the trust was granted */
  grantedAt: number;
  /** Why the trust was granted */
  reason?: string;
  /** Whether this is a pattern (supports wildcards) */
  isPattern: boolean;
}

/**
 * Options for trusting a tool.
 */
export interface TrustOptions {
  /** Trust level (default: 'session') */
  level?: TrustLevel;
  /** Duration in ms for temporary trust */
  durationMs?: number;
  /** Reason for trusting */
  reason?: string;
  /** Who granted the trust */
  grantedBy?: string;
}

/**
 * Result of a trust operation.
 */
export interface TrustResult {
  /** Whether the trust was successful */
  success: boolean;
  /** The trust record */
  record?: TrustRecord;
  /** Error if not successful */
  error?: 'invalid_tool_name' | 'already_trusted';
}

/**
 * Result of checking trust.
 */
export interface TrustCheckResult {
  /** Whether the tool is trusted */
  trusted: boolean;
  /** The matching trust record */
  record?: TrustRecord;
  /** How it matched (exact or pattern) */
  matchType?: 'exact' | 'pattern';
}

// =============================================================================
// TrustManager
// =============================================================================

/**
 * Manages trust state for tools.
 *
 * Supports both per-session and global trust lists.
 * Automatically cleans up expired trust entries.
 *
 * @example
 * ```typescript
 * const manager = new TrustManager();
 *
 * // Trust a tool for this session
 * manager.trust('session-1', 'my-tool', { level: 'session' });
 *
 * // Check if tool is trusted before validation
 * if (manager.isTrusted('session-1', 'my-tool')) {
 *   return; // Skip validation
 * }
 *
 * // Revoke trust
 * manager.revoke('session-1', 'my-tool');
 * ```
 */
export class TrustManager {
  /** Trust records by session ID -> tool name */
  private readonly trusts: Map<string, Map<string, TrustRecord>> = new Map();

  /** Cleanup interval handle */
  private cleanupInterval?: ReturnType<typeof setInterval>;

  /**
   * Create a new TrustManager.
   *
   * @param cleanupIntervalMs - How often to clean up expired trusts (default: 60s)
   */
  constructor(cleanupIntervalMs = 60_000) {
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpired();
    }, cleanupIntervalMs);

    if (this.cleanupInterval.unref) {
      this.cleanupInterval.unref();
    }
  }

  /**
   * Trust a tool for a session.
   *
   * @param sessionId - Session to trust tool for
   * @param toolName - Tool name to trust (supports * wildcard)
   * @param options - Trust options
   * @returns Trust result
   */
  trust(sessionId: string, toolName: string, options: TrustOptions = {}): TrustResult {
    // Validate tool name
    if (!toolName || typeof toolName !== 'string') {
      return { success: false, error: 'invalid_tool_name' };
    }

    const normalizedName = toolName.trim().toLowerCase();
    if (normalizedName.length === 0) {
      return { success: false, error: 'invalid_tool_name' };
    }

    // Get or create session trust map
    let sessionTrusts = this.trusts.get(sessionId);
    if (!sessionTrusts) {
      sessionTrusts = new Map();
      this.trusts.set(sessionId, sessionTrusts);
    }

    // Check if already trusted
    const existing = sessionTrusts.get(normalizedName);
    if (existing && !this.isExpired(existing)) {
      return { success: false, error: 'already_trusted', record: existing };
    }

    const now = Date.now();
    const level = options.level ?? 'session';

    // Calculate expiration
    let expiresAt: number | undefined;
    if (level === 'temporary') {
      const duration = Math.min(
        options.durationMs ?? DEFAULT_TRUST_DURATION_MS,
        MAX_TRUST_DURATION_MS
      );
      expiresAt = now + duration;
    }

    const record: TrustRecord = {
      name: normalizedName,
      level,
      sessionId,
      grantedAt: now,
      expiresAt,
      grantedBy: options.grantedBy,
      reason: options.reason,
      isPattern: normalizedName.includes('*'),
    };

    sessionTrusts.set(normalizedName, record);
    return { success: true, record };
  }

  /**
   * Trust a tool globally for all sessions.
   *
   * @param toolName - Tool name to trust
   * @param options - Trust options
   * @returns Trust result
   */
  trustGlobal(toolName: string, options: TrustOptions = {}): TrustResult {
    return this.trust(GLOBAL_TRUST_SESSION_ID, toolName, options);
  }

  /**
   * Revoke trust for a tool.
   *
   * @param sessionId - Session to revoke trust for
   * @param toolName - Tool name to revoke
   * @returns Whether trust was revoked
   */
  revoke(sessionId: string, toolName: string): boolean {
    const sessionTrusts = this.trusts.get(sessionId);
    if (!sessionTrusts) {
      return false;
    }

    const normalizedName = toolName.trim().toLowerCase();
    return sessionTrusts.delete(normalizedName);
  }

  /**
   * Revoke global trust for a tool.
   *
   * @param toolName - Tool name to revoke
   * @returns Whether trust was revoked
   */
  revokeGlobal(toolName: string): boolean {
    return this.revoke(GLOBAL_TRUST_SESSION_ID, toolName);
  }

  /**
   * Revoke all trust for a session.
   *
   * @param sessionId - Session to revoke all trust for
   * @returns Number of trusts revoked
   */
  revokeAll(sessionId: string): number {
    const sessionTrusts = this.trusts.get(sessionId);
    if (!sessionTrusts) {
      return 0;
    }

    const count = sessionTrusts.size;
    sessionTrusts.clear();
    return count;
  }

  /**
   * Check if a tool is trusted for a session.
   *
   * Checks both session-specific and global trust.
   *
   * @param sessionId - Session to check
   * @param toolName - Tool name to check
   * @returns Trust check result
   */
  isTrusted(sessionId: string, toolName: string): TrustCheckResult {
    const normalizedName = toolName.trim().toLowerCase();

    // Check session-specific trust
    const sessionResult = this.checkTrustInSession(sessionId, normalizedName);
    if (sessionResult.trusted) {
      return sessionResult;
    }

    // Check global trust
    const globalResult = this.checkTrustInSession(GLOBAL_TRUST_SESSION_ID, normalizedName);
    if (globalResult.trusted) {
      return globalResult;
    }

    return { trusted: false };
  }

  /**
   * Get all trusted tools for a session.
   *
   * @param sessionId - Session to get trusts for
   * @param includeGlobal - Whether to include global trusts
   * @returns List of trust records
   */
  getTrustedTools(sessionId: string, includeGlobal = true): TrustRecord[] {
    const result: TrustRecord[] = [];

    // Get session trusts
    const sessionTrusts = this.trusts.get(sessionId);
    if (sessionTrusts) {
      for (const record of sessionTrusts.values()) {
        if (!this.isExpired(record)) {
          result.push(record);
        }
      }
    }

    // Get global trusts
    if (includeGlobal && sessionId !== GLOBAL_TRUST_SESSION_ID) {
      const globalTrusts = this.trusts.get(GLOBAL_TRUST_SESSION_ID);
      if (globalTrusts) {
        for (const record of globalTrusts.values()) {
          if (!this.isExpired(record)) {
            result.push(record);
          }
        }
      }
    }

    return result;
  }

  /**
   * Get trust state for a tool (compatible with TrustedTool type).
   *
   * @param sessionId - Session to check
   * @param toolName - Tool to check
   * @returns TrustedTool or undefined
   */
  getTrustState(sessionId: string, toolName: string): TrustedTool | undefined {
    const result = this.isTrusted(sessionId, toolName);
    if (!result.trusted || !result.record) {
      return undefined;
    }

    return {
      name: result.record.name,
      expiresAt: result.record.expiresAt,
      grantedBy: result.record.grantedBy,
    };
  }

  /**
   * Clear all trust states (for cleanup).
   */
  clear(): void {
    this.trusts.clear();
  }

  /**
   * Stop the cleanup interval (for cleanup).
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = undefined;
    }
    this.trusts.clear();
  }

  /**
   * Get statistics about current trusts.
   *
   * @returns Trust statistics
   */
  getStats(): {
    totalSessions: number;
    totalTrusts: number;
    globalTrusts: number;
    patterns: number;
  } {
    let totalTrusts = 0;
    let patterns = 0;

    for (const sessionTrusts of this.trusts.values()) {
      for (const record of sessionTrusts.values()) {
        if (!this.isExpired(record)) {
          totalTrusts++;
          if (record.isPattern) {
            patterns++;
          }
        }
      }
    }

    const globalTrusts = this.trusts.get(GLOBAL_TRUST_SESSION_ID)?.size ?? 0;

    return {
      totalSessions: this.trusts.size,
      totalTrusts,
      globalTrusts,
      patterns,
    };
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  /**
   * Check trust within a specific session's trust list.
   */
  private checkTrustInSession(sessionId: string, toolName: string): TrustCheckResult {
    const sessionTrusts = this.trusts.get(sessionId);
    if (!sessionTrusts) {
      return { trusted: false };
    }

    // Check exact match first
    const exactMatch = sessionTrusts.get(toolName);
    if (exactMatch && !this.isExpired(exactMatch)) {
      return { trusted: true, record: exactMatch, matchType: 'exact' };
    }

    // Check pattern matches
    for (const record of sessionTrusts.values()) {
      if (record.isPattern && !this.isExpired(record)) {
        if (this.matchesPattern(record.name, toolName)) {
          return { trusted: true, record, matchType: 'pattern' };
        }
      }
    }

    return { trusted: false };
  }

  /**
   * Check if a tool name matches a pattern.
   *
   * Supports * as a wildcard.
   */
  private matchesPattern(pattern: string, toolName: string): boolean {
    // Convert pattern to regex
    // Escape special regex chars except *
    const escaped = pattern.replace(/[.+?^${}()|[\]\\]/g, '\\$&');
    // Convert * to .*
    const regexPattern = '^' + escaped.replace(/\*/g, '.*') + '$';

    try {
      const regex = new RegExp(regexPattern, 'i');
      return regex.test(toolName);
    } catch {
      return false;
    }
  }

  /**
   * Check if a trust record has expired.
   */
  private isExpired(record: TrustRecord): boolean {
    if (!record.expiresAt) {
      return false; // Permanent or session trust
    }
    return Date.now() > record.expiresAt;
  }

  /**
   * Clean up expired trust records.
   */
  private cleanupExpired(): void {
    for (const [sessionId, sessionTrusts] of this.trusts) {
      for (const [toolName, record] of sessionTrusts) {
        if (this.isExpired(record)) {
          sessionTrusts.delete(toolName);
        }
      }

      // Remove empty sessions
      if (sessionTrusts.size === 0) {
        this.trusts.delete(sessionId);
      }
    }
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new TrustManager instance.
 *
 * @param cleanupIntervalMs - How often to clean up expired trusts
 * @returns New TrustManager
 */
export function createTrustManager(cleanupIntervalMs?: number): TrustManager {
  return new TrustManager(cleanupIntervalMs);
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Check if a string is a valid tool pattern.
 *
 * @param pattern - Pattern to check
 * @returns True if valid
 */
export function isValidToolPattern(pattern: string): boolean {
  if (!pattern || typeof pattern !== 'string') {
    return false;
  }

  const trimmed = pattern.trim();
  if (trimmed.length === 0) {
    return false;
  }

  // Must not start with * alone (too broad)
  if (trimmed === '*') {
    return false;
  }

  return true;
}

/**
 * Format trust duration for display.
 *
 * @param record - Trust record
 * @returns Formatted string
 */
export function formatTrustDuration(record: TrustRecord): string {
  if (record.level === 'permanent') {
    return 'permanent';
  }

  if (record.level === 'session') {
    return 'session';
  }

  if (!record.expiresAt) {
    return 'unknown';
  }

  const remaining = record.expiresAt - Date.now();
  if (remaining <= 0) {
    return 'expired';
  }

  const hours = Math.floor(remaining / (60 * 60 * 1000));
  const minutes = Math.floor((remaining % (60 * 60 * 1000)) / (60 * 1000));

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  }

  return `${minutes}m`;
}
