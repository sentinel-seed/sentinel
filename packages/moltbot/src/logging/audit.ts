/**
 * @sentinelseed/moltbot - Audit Log
 *
 * Provides audit logging functionality for security events.
 * Supports in-memory storage with optional persistence.
 *
 * @module logging/audit
 */

import type { AuditEntry, AuditEventType, DetectedIssue } from '../types';

// =============================================================================
// Constants
// =============================================================================

/** Default maximum entries to keep in memory */
export const DEFAULT_MAX_ENTRIES = 1000;

/** Default entry expiration time (24 hours) */
export const DEFAULT_ENTRY_TTL_MS = 24 * 60 * 60 * 1000;

// =============================================================================
// Types
// =============================================================================

/**
 * Options for creating an audit entry.
 */
export interface CreateEntryOptions {
  /** Event type */
  event: AuditEventType;
  /** Outcome of the event */
  outcome: AuditEntry['outcome'];
  /** Event details */
  details?: Record<string, unknown>;
  /** Session ID */
  sessionId?: string;
}

/**
 * Filter options for querying audit entries.
 */
export interface AuditFilter {
  /** Filter by event type */
  event?: AuditEventType;
  /** Filter by outcome */
  outcome?: AuditEntry['outcome'];
  /** Filter by session ID */
  sessionId?: string;
  /** Filter by time range (start) */
  fromTimestamp?: number;
  /** Filter by time range (end) */
  toTimestamp?: number;
  /** Maximum entries to return */
  limit?: number;
}

/**
 * Options for the AuditLog.
 */
export interface AuditLogOptions {
  /** Maximum entries to keep in memory */
  maxEntries?: number;
  /** Entry expiration time in ms (0 = no expiration) */
  entryTtlMs?: number;
  /** Cleanup interval in ms */
  cleanupIntervalMs?: number;
  /** Optional persistence handler */
  persistHandler?: PersistHandler;
}

/**
 * Handler for persisting audit entries.
 */
export interface PersistHandler {
  /** Save an entry */
  save: (entry: AuditEntry) => Promise<void>;
  /** Load entries (optional, for startup) */
  load?: () => Promise<AuditEntry[]>;
}

/**
 * Audit statistics.
 */
export interface AuditStats {
  /** Total entries in memory */
  totalEntries: number;
  /** Entries by event type */
  byEvent: Record<AuditEventType, number>;
  /** Entries by outcome */
  byOutcome: Record<AuditEntry['outcome'], number>;
  /** Unique sessions */
  uniqueSessions: number;
  /** Oldest entry timestamp */
  oldestEntry?: number;
  /** Newest entry timestamp */
  newestEntry?: number;
}

// =============================================================================
// AuditLog
// =============================================================================

/**
 * Audit log for security events.
 *
 * Provides:
 * - In-memory storage with size limits
 * - Filtering and querying
 * - Optional persistence
 * - Automatic cleanup of old entries
 *
 * @example
 * ```typescript
 * const audit = new AuditLog({ maxEntries: 500 });
 *
 * // Log an event
 * audit.log({
 *   event: 'output_blocked',
 *   outcome: 'blocked',
 *   sessionId: 'session-1',
 *   details: { reason: 'API key detected' },
 * });
 *
 * // Query entries
 * const blocked = audit.query({ outcome: 'blocked', limit: 10 });
 * ```
 */
export class AuditLog {
  /** Stored entries */
  private readonly entries: AuditEntry[] = [];

  /** Entry counter for ID generation */
  private entryCounter = 0;

  /** Maximum entries to keep */
  private readonly maxEntries: number;

  /** Entry TTL in ms */
  private readonly entryTtlMs: number;

  /** Cleanup interval handle */
  private cleanupInterval?: ReturnType<typeof setInterval>;

  /** Persistence handler */
  private readonly persistHandler?: PersistHandler;

  /**
   * Create a new AuditLog.
   *
   * @param options - Log options
   */
  constructor(options: AuditLogOptions = {}) {
    this.maxEntries = options.maxEntries ?? DEFAULT_MAX_ENTRIES;
    this.entryTtlMs = options.entryTtlMs ?? DEFAULT_ENTRY_TTL_MS;
    this.persistHandler = options.persistHandler;

    // Start cleanup interval if TTL is enabled
    if (this.entryTtlMs > 0) {
      const cleanupInterval = options.cleanupIntervalMs ?? 60_000;
      this.cleanupInterval = setInterval(() => {
        this.cleanupExpired();
      }, cleanupInterval);

      if (this.cleanupInterval.unref) {
        this.cleanupInterval.unref();
      }
    }
  }

  /**
   * Log an audit event.
   *
   * @param options - Entry options
   * @returns The created entry
   */
  log(options: CreateEntryOptions): AuditEntry {
    const entry: AuditEntry = {
      id: this.generateId(),
      timestamp: Date.now(),
      event: options.event,
      outcome: options.outcome,
      details: options.details ?? {},
      sessionId: options.sessionId,
    };

    this.addEntry(entry);
    return entry;
  }

  /**
   * Log an input analysis event.
   */
  logInputAnalysis(
    sessionId: string,
    threatLevel: number,
    issues: readonly DetectedIssue[]
  ): AuditEntry {
    return this.log({
      event: 'input_analyzed',
      outcome: threatLevel >= 4 ? 'alerted' : 'allowed',
      sessionId,
      details: {
        threatLevel,
        issueCount: issues.length,
        issueTypes: [...new Set(issues.map(i => i.type))],
      },
    });
  }

  /**
   * Log an output validation event.
   */
  logOutputValidation(
    sessionId: string,
    blocked: boolean,
    issues: readonly DetectedIssue[]
  ): AuditEntry {
    return this.log({
      event: blocked ? 'output_blocked' : 'output_validated',
      outcome: blocked ? 'blocked' : 'allowed',
      sessionId,
      details: {
        issueCount: issues.length,
        issueTypes: [...new Set(issues.map(i => i.type))],
      },
    });
  }

  /**
   * Log a tool validation event.
   */
  logToolValidation(
    sessionId: string,
    toolName: string,
    blocked: boolean,
    issues: readonly DetectedIssue[]
  ): AuditEntry {
    return this.log({
      event: blocked ? 'tool_blocked' : 'tool_validated',
      outcome: blocked ? 'blocked' : 'allowed',
      sessionId,
      details: {
        toolName,
        issueCount: issues.length,
        issueTypes: [...new Set(issues.map(i => i.type))],
      },
    });
  }

  /**
   * Log a seed injection event.
   */
  logSeedInjection(sessionId: string, seedTemplate: string): AuditEntry {
    return this.log({
      event: 'seed_injected',
      outcome: 'allowed',
      sessionId,
      details: { seedTemplate },
    });
  }

  /**
   * Log a session start event.
   */
  logSessionStart(sessionId: string): AuditEntry {
    return this.log({
      event: 'session_started',
      outcome: 'allowed',
      sessionId,
    });
  }

  /**
   * Log a session end event.
   */
  logSessionEnd(
    sessionId: string,
    success: boolean,
    summary?: Record<string, unknown>
  ): AuditEntry {
    return this.log({
      event: 'session_ended',
      outcome: success ? 'allowed' : 'error',
      sessionId,
      details: summary ?? {},
    });
  }

  /**
   * Log an escape hatch usage.
   */
  logEscapeUsed(
    sessionId: string,
    escapeType: 'allow_once' | 'pause' | 'trust',
    details?: Record<string, unknown>
  ): AuditEntry {
    return this.log({
      event: 'escape_used',
      outcome: 'allowed',
      sessionId,
      details: { escapeType, ...details },
    });
  }

  /**
   * Log an error event.
   */
  logError(
    sessionId: string | undefined,
    error: Error,
    context?: Record<string, unknown>
  ): AuditEntry {
    return this.log({
      event: 'error',
      outcome: 'error',
      sessionId,
      details: {
        errorName: error.name,
        errorMessage: error.message,
        ...context,
      },
    });
  }

  /**
   * Query audit entries with filters.
   *
   * @param filter - Query filters
   * @returns Matching entries (newest first)
   */
  query(filter: AuditFilter = {}): AuditEntry[] {
    let results = [...this.entries];

    // Apply filters
    if (filter.event) {
      results = results.filter(e => e.event === filter.event);
    }

    if (filter.outcome) {
      results = results.filter(e => e.outcome === filter.outcome);
    }

    if (filter.sessionId) {
      results = results.filter(e => e.sessionId === filter.sessionId);
    }

    if (filter.fromTimestamp) {
      results = results.filter(e => e.timestamp >= filter.fromTimestamp!);
    }

    if (filter.toTimestamp) {
      results = results.filter(e => e.timestamp <= filter.toTimestamp!);
    }

    // Sort by timestamp descending (newest first)
    results.sort((a, b) => b.timestamp - a.timestamp);

    // Apply limit
    if (filter.limit && filter.limit > 0) {
      results = results.slice(0, filter.limit);
    }

    return results;
  }

  /**
   * Get an entry by ID.
   *
   * @param id - Entry ID
   * @returns Entry or undefined
   */
  getById(id: string): AuditEntry | undefined {
    return this.entries.find(e => e.id === id);
  }

  /**
   * Get the most recent entries.
   *
   * @param count - Number of entries
   * @returns Recent entries (newest first)
   */
  getRecent(count = 10): AuditEntry[] {
    return this.query({ limit: count });
  }

  /**
   * Get entries for a session.
   *
   * @param sessionId - Session ID
   * @param limit - Maximum entries
   * @returns Session entries (newest first)
   */
  getBySession(sessionId: string, limit?: number): AuditEntry[] {
    return this.query({ sessionId, limit });
  }

  /**
   * Get blocked action entries.
   *
   * @param limit - Maximum entries
   * @returns Blocked entries (newest first)
   */
  getBlocked(limit?: number): AuditEntry[] {
    return this.query({ outcome: 'blocked', limit });
  }

  /**
   * Get audit statistics.
   *
   * @returns Statistics
   */
  getStats(): AuditStats {
    const byEvent: Record<string, number> = {};
    const byOutcome: Record<string, number> = {};
    const sessions = new Set<string>();
    let oldest: number | undefined;
    let newest: number | undefined;

    for (const entry of this.entries) {
      // Count by event
      byEvent[entry.event] = (byEvent[entry.event] ?? 0) + 1;

      // Count by outcome
      byOutcome[entry.outcome] = (byOutcome[entry.outcome] ?? 0) + 1;

      // Track sessions
      if (entry.sessionId) {
        sessions.add(entry.sessionId);
      }

      // Track time range
      if (oldest === undefined || entry.timestamp < oldest) {
        oldest = entry.timestamp;
      }
      if (newest === undefined || entry.timestamp > newest) {
        newest = entry.timestamp;
      }
    }

    return {
      totalEntries: this.entries.length,
      byEvent: byEvent as Record<AuditEventType, number>,
      byOutcome: byOutcome as Record<AuditEntry['outcome'], number>,
      uniqueSessions: sessions.size,
      oldestEntry: oldest,
      newestEntry: newest,
    };
  }

  /**
   * Get the total number of entries.
   */
  get size(): number {
    return this.entries.length;
  }

  /**
   * Clear all entries.
   */
  clear(): void {
    this.entries.length = 0;
  }

  /**
   * Destroy the audit log and stop cleanup.
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = undefined;
    }
    this.entries.length = 0;
  }

  /**
   * Export entries to JSON.
   *
   * @param filter - Optional filter
   * @returns JSON string
   */
  exportToJson(filter?: AuditFilter): string {
    const entries = this.query(filter);
    return JSON.stringify(entries, null, 2);
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  /**
   * Add an entry to the log.
   */
  private addEntry(entry: AuditEntry): void {
    // Enforce size limit
    while (this.entries.length >= this.maxEntries) {
      this.entries.shift(); // Remove oldest
    }

    this.entries.push(entry);

    // Persist if handler available
    if (this.persistHandler) {
      this.persistHandler.save(entry).catch(() => {
        // Fail silently - persistence is optional
      });
    }
  }

  /**
   * Generate a unique entry ID.
   */
  private generateId(): string {
    this.entryCounter++;
    return `audit_${Date.now()}_${this.entryCounter}`;
  }

  /**
   * Clean up expired entries.
   */
  private cleanupExpired(): void {
    if (this.entryTtlMs <= 0) {
      return;
    }

    const cutoff = Date.now() - this.entryTtlMs;
    let i = 0;

    // Remove from the beginning (oldest entries)
    while (i < this.entries.length && this.entries[i]!.timestamp < cutoff) {
      i++;
    }

    if (i > 0) {
      this.entries.splice(0, i);
    }
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new AuditLog instance.
 *
 * @param options - Log options
 * @returns New AuditLog
 */
export function createAuditLog(options?: AuditLogOptions): AuditLog {
  return new AuditLog(options);
}
