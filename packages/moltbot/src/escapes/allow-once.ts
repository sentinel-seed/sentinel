/**
 * @sentinelseed/moltbot - Allow-Once Escape Hatch
 *
 * Provides a mechanism for users to bypass a single blocked action.
 * When Sentinel blocks something, the user can invoke "allow once"
 * to permit that specific action to proceed.
 *
 * Features:
 * - Scoped tokens (output, tool, or any)
 * - Automatic expiration (default 30 seconds)
 * - Single-use (token consumed on use)
 * - Per-session isolation
 *
 * @module escapes/allow-once
 */

import type { AllowOnceState } from '../types';

// =============================================================================
// Constants
// =============================================================================

/** Default token expiration time in milliseconds (30 seconds) */
export const DEFAULT_EXPIRATION_MS = 30_000;

/** Maximum allowed expiration time (5 minutes) */
export const MAX_EXPIRATION_MS = 5 * 60 * 1000;

/** Minimum allowed expiration time (5 seconds) */
export const MIN_EXPIRATION_MS = 5_000;

// =============================================================================
// Types
// =============================================================================

/**
 * Scope for allow-once token.
 */
export type AllowOnceScope = 'output' | 'tool' | 'any';

/**
 * Allow-once token with metadata.
 */
export interface AllowOnceToken {
  /** Unique token ID */
  readonly id: string;
  /** Session this token belongs to */
  readonly sessionId: string;
  /** Scope of the token */
  readonly scope: AllowOnceScope;
  /** When this token was created */
  readonly createdAt: number;
  /** When this token expires */
  readonly expiresAt: number;
  /** Whether this token has been used */
  used: boolean;
  /** When this token was used (if used) */
  usedAt?: number;
  /** What action this token was used for */
  usedFor?: string;
}

/**
 * Options for granting an allow-once token.
 */
export interface GrantOptions {
  /** Scope of the token (default: 'any') */
  scope?: AllowOnceScope;
  /** Expiration time in ms (default: 30s) */
  expirationMs?: number;
}

/**
 * Result of checking if an allow-once is available.
 */
export interface AllowOnceCheckResult {
  /** Whether an allow-once token is available */
  available: boolean;
  /** The token if available */
  token?: AllowOnceToken;
  /** Reason if not available */
  reason?: 'no_token' | 'expired' | 'wrong_scope' | 'already_used';
}

/**
 * Result of using an allow-once token.
 */
export interface AllowOnceUseResult {
  /** Whether the token was successfully used */
  success: boolean;
  /** The token that was used */
  token?: AllowOnceToken;
  /** Error reason if not successful */
  error?: 'no_token' | 'expired' | 'wrong_scope' | 'already_used';
}

// =============================================================================
// AllowOnceManager
// =============================================================================

/**
 * Manages allow-once tokens for escape hatch functionality.
 *
 * Each session can have at most one active allow-once token.
 * Tokens are automatically cleaned up on expiration.
 *
 * @example
 * ```typescript
 * const manager = new AllowOnceManager();
 *
 * // User requests allow-once after a block
 * manager.grant('session-1', { scope: 'tool' });
 *
 * // Later, when checking if action should be blocked:
 * const result = manager.use('session-1', 'tool', 'bash');
 * if (result.success) {
 *   // Action was allowed by allow-once token
 * }
 * ```
 */
export class AllowOnceManager {
  /** Active tokens by session ID */
  private readonly tokens: Map<string, AllowOnceToken> = new Map();

  /** Token ID counter */
  private tokenCounter = 0;

  /** Cleanup interval handle */
  private cleanupInterval?: ReturnType<typeof setInterval>;

  /**
   * Create a new AllowOnceManager.
   *
   * @param cleanupIntervalMs - How often to clean up expired tokens (default: 10s)
   */
  constructor(cleanupIntervalMs = 10_000) {
    // Start cleanup interval
    this.cleanupInterval = setInterval(() => {
      this.cleanupExpired();
    }, cleanupIntervalMs);

    // Don't prevent process exit
    if (this.cleanupInterval.unref) {
      this.cleanupInterval.unref();
    }
  }

  /**
   * Grant an allow-once token for a session.
   *
   * Replaces any existing token for the session.
   *
   * @param sessionId - Session to grant token for
   * @param options - Grant options
   * @returns The granted token
   */
  grant(sessionId: string, options: GrantOptions = {}): AllowOnceToken {
    const now = Date.now();
    const scope = options.scope ?? 'any';
    const expirationMs = this.clampExpiration(options.expirationMs ?? DEFAULT_EXPIRATION_MS);

    const token: AllowOnceToken = {
      id: this.generateTokenId(),
      sessionId,
      scope,
      createdAt: now,
      expiresAt: now + expirationMs,
      used: false,
    };

    this.tokens.set(sessionId, token);
    return token;
  }

  /**
   * Check if an allow-once token is available for use.
   *
   * Does NOT consume the token.
   *
   * @param sessionId - Session to check
   * @param requiredScope - Required scope (optional, defaults to any match)
   * @returns Check result
   */
  check(sessionId: string, requiredScope?: AllowOnceScope): AllowOnceCheckResult {
    const token = this.tokens.get(sessionId);

    if (!token) {
      return { available: false, reason: 'no_token' };
    }

    if (token.used) {
      return { available: false, reason: 'already_used', token };
    }

    if (Date.now() > token.expiresAt) {
      return { available: false, reason: 'expired', token };
    }

    if (requiredScope && !this.scopeMatches(token.scope, requiredScope)) {
      return { available: false, reason: 'wrong_scope', token };
    }

    return { available: true, token };
  }

  /**
   * Use (consume) an allow-once token.
   *
   * Marks the token as used, preventing future use.
   *
   * @param sessionId - Session to use token from
   * @param requiredScope - Required scope for the action
   * @param actionDescription - Description of what action this is for
   * @returns Use result
   */
  use(
    sessionId: string,
    requiredScope: AllowOnceScope,
    actionDescription: string
  ): AllowOnceUseResult {
    const checkResult = this.check(sessionId, requiredScope);

    if (!checkResult.available) {
      return {
        success: false,
        token: checkResult.token,
        error: checkResult.reason,
      };
    }

    const token = checkResult.token!;
    token.used = true;
    token.usedAt = Date.now();
    token.usedFor = actionDescription;

    return { success: true, token };
  }

  /**
   * Revoke any active token for a session.
   *
   * @param sessionId - Session to revoke token for
   * @returns Whether a token was revoked
   */
  revoke(sessionId: string): boolean {
    return this.tokens.delete(sessionId);
  }

  /**
   * Get the current state for a session.
   *
   * @param sessionId - Session to get state for
   * @returns Allow-once state
   */
  getState(sessionId: string): AllowOnceState {
    const token = this.tokens.get(sessionId);

    if (!token || token.used || Date.now() > token.expiresAt) {
      return { active: false };
    }

    return {
      active: true,
      scope: token.scope,
      expiresAt: token.expiresAt,
    };
  }

  /**
   * Get remaining time for a session's token in milliseconds.
   *
   * @param sessionId - Session to check
   * @returns Remaining time in ms, or 0 if no active token
   */
  getRemainingTime(sessionId: string): number {
    const token = this.tokens.get(sessionId);

    if (!token || token.used) {
      return 0;
    }

    const remaining = token.expiresAt - Date.now();
    return Math.max(0, remaining);
  }

  /**
   * Clear all tokens (for cleanup).
   */
  clear(): void {
    this.tokens.clear();
  }

  /**
   * Stop the cleanup interval (for cleanup).
   */
  destroy(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = undefined;
    }
    this.tokens.clear();
  }

  /**
   * Get statistics about current tokens.
   *
   * @returns Token statistics
   */
  getStats(): { total: number; active: number; used: number; expired: number } {
    let active = 0;
    let used = 0;
    let expired = 0;
    const now = Date.now();

    for (const token of this.tokens.values()) {
      if (token.used) {
        used++;
      } else if (now > token.expiresAt) {
        expired++;
      } else {
        active++;
      }
    }

    return {
      total: this.tokens.size,
      active,
      used,
      expired,
    };
  }

  // ===========================================================================
  // Private Methods
  // ===========================================================================

  /**
   * Check if a token scope matches the required scope.
   */
  private scopeMatches(tokenScope: AllowOnceScope, requiredScope: AllowOnceScope): boolean {
    // 'any' matches everything
    if (tokenScope === 'any') {
      return true;
    }
    // Otherwise must match exactly
    return tokenScope === requiredScope;
  }

  /**
   * Generate a unique token ID.
   */
  private generateTokenId(): string {
    this.tokenCounter++;
    return `ao_${Date.now()}_${this.tokenCounter}`;
  }

  /**
   * Clamp expiration time to valid range.
   */
  private clampExpiration(ms: number): number {
    return Math.max(MIN_EXPIRATION_MS, Math.min(MAX_EXPIRATION_MS, ms));
  }

  /**
   * Clean up expired and used tokens.
   */
  private cleanupExpired(): void {
    const now = Date.now();

    for (const [sessionId, token] of this.tokens) {
      // Remove if expired or used
      if (token.used || now > token.expiresAt) {
        this.tokens.delete(sessionId);
      }
    }
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new AllowOnceManager instance.
 *
 * @param cleanupIntervalMs - How often to clean up expired tokens
 * @returns New AllowOnceManager
 */
export function createAllowOnceManager(cleanupIntervalMs?: number): AllowOnceManager {
  return new AllowOnceManager(cleanupIntervalMs);
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Check if a scope is valid.
 *
 * @param scope - Scope to check
 * @returns True if valid
 */
export function isValidScope(scope: unknown): scope is AllowOnceScope {
  return scope === 'output' || scope === 'tool' || scope === 'any';
}

/**
 * Format remaining time for display.
 *
 * @param remainingMs - Remaining time in milliseconds
 * @returns Formatted string (e.g., "25s", "1m 30s")
 */
export function formatRemainingTime(remainingMs: number): string {
  if (remainingMs <= 0) {
    return 'expired';
  }

  const seconds = Math.ceil(remainingMs / 1000);

  if (seconds < 60) {
    return `${seconds}s`;
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (remainingSeconds === 0) {
    return `${minutes}m`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}
