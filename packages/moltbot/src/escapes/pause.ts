/**
 * @sentinelseed/moltbot - Pause Escape Hatch
 *
 * Provides a mechanism to temporarily pause Sentinel protection.
 * When paused, all validation and blocking is disabled for the session.
 *
 * Features:
 * - Per-session pause state
 * - Automatic expiration (configurable, default 5 minutes)
 * - Optional reason tracking
 * - Resume functionality
 * - Global pause option for all sessions
 *
 * @module escapes/pause
 */

import type { PauseState } from '../types';

// =============================================================================
// Constants
// =============================================================================

/** Default pause duration in milliseconds (5 minutes) */
export const DEFAULT_PAUSE_DURATION_MS = 5 * 60 * 1000;

/** Maximum pause duration (1 hour) */
export const MAX_PAUSE_DURATION_MS = 60 * 60 * 1000;

/** Minimum pause duration (10 seconds) */
export const MIN_PAUSE_DURATION_MS = 10_000;

/** Special session ID for global pause */
export const GLOBAL_SESSION_ID = '__global__';

// =============================================================================
// Types
// =============================================================================

/**
 * Internal pause record with full metadata.
 */
export interface PauseRecord {
  /** Session ID this pause applies to */
  readonly sessionId: string;
  /** When the pause was started */
  readonly startedAt: number;
  /** When the pause expires (undefined = indefinite) */
  readonly expiresAt?: number;
  /** Reason for the pause */
  readonly reason?: string;
  /** Who initiated the pause */
  readonly initiatedBy?: string;
  /** Whether this is currently active */
  active: boolean;
  /** When the pause was resumed (if resumed early) */
  resumedAt?: number;
}

/**
 * Options for pausing Sentinel.
 */
export interface PauseOptions {
  /** Duration in milliseconds (undefined = use default) */
  durationMs?: number;
  /** Reason for pausing */
  reason?: string;
  /** Who is initiating the pause */
  initiatedBy?: string;
  /** Indefinite pause (no expiration) */
  indefinite?: boolean;
}

/**
 * Result of a pause operation.
 */
export interface PauseResult {
  /** Whether the pause was successful */
  success: boolean;
  /** The pause record */
  record?: PauseRecord;
  /** Error if not successful */
  error?: 'already_paused' | 'invalid_duration';
}

/**
 * Result of a resume operation.
 */
export interface ResumeResult {
  /** Whether the resume was successful */
  success: boolean;
  /** The pause record that was resumed */
  record?: PauseRecord;
  /** Duration the session was paused (ms) */
  pausedDurationMs?: number;
  /** Error if not successful */
  error?: 'not_paused' | 'already_expired';
}

// =============================================================================
// PauseManager
// =============================================================================

/**
 * Manages pause state for Sentinel protection.
 *
 * Supports both per-session pauses and global pause.
 * Automatically cleans up expired pause states.
 *
 * @example
 * ```typescript
 * const manager = new PauseManager();
 *
 * // Pause for a specific session
 * manager.pause('session-1', { durationMs: 60000, reason: 'Debugging' });
 *
 * // Check if paused before validation
 * if (manager.isPaused('session-1')) {
 *   return; // Skip validation
 * }
 *
 * // Resume early
 * manager.resume('session-1');
 * ```
 */
export class PauseManager {
  /** Pause records by session ID */
  private readonly pauses: Map<string, PauseRecord> = new Map();

  /** Cleanup interval handle */
  private cleanupInterval?: ReturnType<typeof setInterval>;

  /**
   * Create a new PauseManager.
   *
   * @param cleanupIntervalMs - How often to clean up expired pauses (default: 30s)
   */
  constructor(cleanupIntervalMs = 30_000) {
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpired();
    }, cleanupIntervalMs);

    if (this.cleanupInterval.unref) {
      this.cleanupInterval.unref();
    }
  }

  /**
   * Pause Sentinel for a session.
   *
   * @param sessionId - Session to pause (or GLOBAL_SESSION_ID)
   * @param options - Pause options
   * @returns Pause result
   */
  pause(sessionId: string, options: PauseOptions = {}): PauseResult {
    const existingPause = this.pauses.get(sessionId);

    // Check if already paused and active
    if (existingPause?.active && !this.isExpired(existingPause)) {
      return { success: false, error: 'already_paused', record: existingPause };
    }

    const now = Date.now();
    let expiresAt: number | undefined;

    if (!options.indefinite) {
      const duration = this.clampDuration(options.durationMs ?? DEFAULT_PAUSE_DURATION_MS);
      expiresAt = now + duration;
    }

    const record: PauseRecord = {
      sessionId,
      startedAt: now,
      expiresAt,
      reason: options.reason,
      initiatedBy: options.initiatedBy,
      active: true,
    };

    this.pauses.set(sessionId, record);
    return { success: true, record };
  }

  /**
   * Pause Sentinel globally for all sessions.
   *
   * @param options - Pause options
   * @returns Pause result
   */
  pauseGlobal(options: PauseOptions = {}): PauseResult {
    return this.pause(GLOBAL_SESSION_ID, options);
  }

  /**
   * Resume Sentinel for a session.
   *
   * @param sessionId - Session to resume
   * @returns Resume result
   */
  resume(sessionId: string): ResumeResult {
    const record = this.pauses.get(sessionId);

    if (!record) {
      return { success: false, error: 'not_paused' };
    }

    if (!record.active) {
      return { success: false, error: 'already_expired', record };
    }

    if (this.isExpired(record)) {
      record.active = false;
      return { success: false, error: 'already_expired', record };
    }

    const now = Date.now();
    record.active = false;
    record.resumedAt = now;

    const pausedDurationMs = now - record.startedAt;

    return { success: true, record, pausedDurationMs };
  }

  /**
   * Resume Sentinel globally.
   *
   * @returns Resume result
   */
  resumeGlobal(): ResumeResult {
    return this.resume(GLOBAL_SESSION_ID);
  }

  /**
   * Check if Sentinel is paused for a session.
   *
   * Also checks global pause state.
   *
   * @param sessionId - Session to check
   * @returns True if paused
   */
  isPaused(sessionId: string): boolean {
    // Check session-specific pause
    const sessionPause = this.pauses.get(sessionId);
    if (sessionPause?.active && !this.isExpired(sessionPause)) {
      return true;
    }

    // Check global pause
    const globalPause = this.pauses.get(GLOBAL_SESSION_ID);
    if (globalPause?.active && !this.isExpired(globalPause)) {
      return true;
    }

    return false;
  }

  /**
   * Get pause state for a session.
   *
   * @param sessionId - Session to get state for
   * @returns Pause state
   */
  getState(sessionId: string): PauseState {
    // Check session-specific pause first
    const sessionPause = this.pauses.get(sessionId);
    if (sessionPause?.active && !this.isExpired(sessionPause)) {
      return {
        paused: true,
        expiresAt: sessionPause.expiresAt,
        reason: sessionPause.reason,
      };
    }

    // Check global pause
    const globalPause = this.pauses.get(GLOBAL_SESSION_ID);
    if (globalPause?.active && !this.isExpired(globalPause)) {
      return {
        paused: true,
        expiresAt: globalPause.expiresAt,
        reason: globalPause.reason ?? 'Global pause',
      };
    }

    return { paused: false };
  }

  /**
   * Get remaining pause time for a session in milliseconds.
   *
   * @param sessionId - Session to check
   * @returns Remaining time in ms, or 0 if not paused
   */
  getRemainingTime(sessionId: string): number {
    // Check session-specific pause
    const sessionPause = this.pauses.get(sessionId);
    if (sessionPause?.active && sessionPause.expiresAt) {
      const remaining = sessionPause.expiresAt - Date.now();
      if (remaining > 0) {
        return remaining;
      }
    }

    // Check global pause
    const globalPause = this.pauses.get(GLOBAL_SESSION_ID);
    if (globalPause?.active && globalPause.expiresAt) {
      const remaining = globalPause.expiresAt - Date.now();
      if (remaining > 0) {
        return remaining;
      }
    }

    return 0;
  }

  /**
   * Get the pause record for a session.
   *
   * @param sessionId - Session to get record for
   * @returns Pause record or undefined
   */
  getRecord(sessionId: string): PauseRecord | undefined {
    return this.pauses.get(sessionId);
  }

  /**
   * Clear all pause states (for cleanup).
   */
  clear(): void {
    this.pauses.clear();
  }

  /**
   * Stop the cleanup interval (for cleanup).
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = undefined;
    }
    this.pauses.clear();
  }

  /**
   * Get statistics about current pauses.
   *
   * @returns Pause statistics
   */
  getStats(): { total: number; active: number; expired: number; global: boolean } {
    let active = 0;
    let expired = 0;

    for (const record of this.pauses.values()) {
      if (record.active && !this.isExpired(record)) {
        active++;
      } else {
        expired++;
      }
    }

    const globalPause = this.pauses.get(GLOBAL_SESSION_ID);
    const globalActive = globalPause?.active && !this.isExpired(globalPause);

    return {
      total: this.pauses.size,
      active,
      expired,
      global: !!globalActive,
    };
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  /**
   * Check if a pause record has expired.
   */
  private isExpired(record: PauseRecord): boolean {
    if (!record.expiresAt) {
      return false; // Indefinite pause
    }
    return Date.now() > record.expiresAt;
  }

  /**
   * Clamp duration to valid range.
   */
  private clampDuration(ms: number): number {
    return Math.max(MIN_PAUSE_DURATION_MS, Math.min(MAX_PAUSE_DURATION_MS, ms));
  }

  /**
   * Clean up expired pause records.
   */
  private cleanupExpired(): void {
    for (const [sessionId, record] of this.pauses) {
      if (!record.active || this.isExpired(record)) {
        // Mark as inactive if expired
        if (record.active && this.isExpired(record)) {
          record.active = false;
        }
        // Remove old inactive records
        if (!record.active) {
          this.pauses.delete(sessionId);
        }
      }
    }
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new PauseManager instance.
 *
 * @param cleanupIntervalMs - How often to clean up expired pauses
 * @returns New PauseManager
 */
export function createPauseManager(cleanupIntervalMs?: number): PauseManager {
  return new PauseManager(cleanupIntervalMs);
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Format remaining pause time for display.
 *
 * @param remainingMs - Remaining time in milliseconds
 * @returns Formatted string (e.g., "2m 30s", "indefinite")
 */
export function formatPauseTime(remainingMs: number | undefined): string {
  if (remainingMs === undefined) {
    return 'indefinite';
  }

  if (remainingMs <= 0) {
    return 'expired';
  }

  const seconds = Math.ceil(remainingMs / 1000);

  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes >= 60) {
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (remainingMinutes === 0) {
      return `${hours}h`;
    }
    return `${hours}h ${remainingMinutes}m`;
  }

  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

/**
 * Create a pause state from a record.
 *
 * @param record - Pause record
 * @returns Pause state
 */
export function recordToPauseState(record: PauseRecord | undefined): PauseState {
  if (!record?.active) {
    return { paused: false };
  }

  return {
    paused: true,
    expiresAt: record.expiresAt,
    reason: record.reason,
  };
}
