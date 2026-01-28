/**
 * @sentinelseed/moltbot - Escape Hatches Module
 *
 * Provides mechanisms for users to override Sentinel protection
 * when needed. Escape hatches are designed to give users control
 * while maintaining visibility and accountability.
 *
 * Components:
 * - AllowOnceManager: Bypass a single blocked action
 * - PauseManager: Temporarily pause all protection
 * - TrustManager: Trust specific tools
 *
 * @module escapes
 */

// =============================================================================
// Re-exports
// =============================================================================

export {
  // AllowOnce
  AllowOnceManager,
  createAllowOnceManager,
  isValidScope,
  formatRemainingTime,
  DEFAULT_EXPIRATION_MS,
  MAX_EXPIRATION_MS,
  MIN_EXPIRATION_MS,
  type AllowOnceScope,
  type AllowOnceToken,
  type GrantOptions,
  type AllowOnceCheckResult,
  type AllowOnceUseResult,
} from './allow-once';

export {
  // Pause
  PauseManager,
  createPauseManager,
  formatPauseTime,
  recordToPauseState,
  DEFAULT_PAUSE_DURATION_MS,
  MAX_PAUSE_DURATION_MS,
  MIN_PAUSE_DURATION_MS,
  GLOBAL_SESSION_ID,
  type PauseRecord,
  type PauseOptions,
  type PauseResult,
  type ResumeResult,
} from './pause';

export {
  // Trust
  TrustManager,
  createTrustManager,
  isValidToolPattern,
  formatTrustDuration,
  DEFAULT_TRUST_DURATION_MS,
  MAX_TRUST_DURATION_MS,
  GLOBAL_TRUST_SESSION_ID,
  type TrustLevel,
  type TrustRecord,
  type TrustOptions,
  type TrustResult,
  type TrustCheckResult,
} from './trust';

// Import for internal use
import { AllowOnceManager, type AllowOnceScope } from './allow-once';
import { PauseManager } from './pause';
import { TrustManager } from './trust';

// =============================================================================
// Types
// =============================================================================

/**
 * Combined escape state for a session.
 */
export interface EscapeState {
  /** Whether protection is paused */
  paused: boolean;
  /** Pause reason (if paused) */
  pauseReason?: string;
  /** Pause expiration (if paused) */
  pauseExpiresAt?: number;
  /** Whether allow-once is active */
  allowOnceActive: boolean;
  /** Allow-once scope (if active) */
  allowOnceScope?: AllowOnceScope;
  /** Allow-once expiration (if active) */
  allowOnceExpiresAt?: number;
  /** Number of trusted tools */
  trustedToolsCount: number;
  /** Names of trusted tools */
  trustedTools: string[];
}

/**
 * Options for creating an EscapeManager.
 */
export interface EscapeManagerOptions {
  /** Cleanup interval for allow-once tokens (default: 10s) */
  allowOnceCleanupMs?: number;
  /** Cleanup interval for pause states (default: 30s) */
  pauseCleanupMs?: number;
  /** Cleanup interval for trust records (default: 60s) */
  trustCleanupMs?: number;
}

/**
 * Result of checking if an action should be allowed.
 */
export interface EscapeCheckResult {
  /** Whether the action should be allowed (escape applies) */
  allowed: boolean;
  /** Which escape mechanism allowed it */
  mechanism?: 'pause' | 'allow_once' | 'trust';
  /** Description of why it was allowed */
  reason?: string;
}

/**
 * Statistics for escape manager.
 */
export interface EscapeStats {
  /** Allow-once statistics */
  allowOnce: {
    total: number;
    active: number;
    used: number;
    expired: number;
  };
  /** Pause statistics */
  pause: {
    total: number;
    active: number;
    expired: number;
    global: boolean;
  };
  /** Trust statistics */
  trust: {
    totalSessions: number;
    totalTrusts: number;
    globalTrusts: number;
    patterns: number;
  };
}

// =============================================================================
// EscapeManager
// =============================================================================

/**
 * Unified manager for all escape hatches.
 *
 * Provides a single interface to:
 * - Check if an action should bypass validation
 * - Grant allow-once tokens
 * - Pause/resume protection
 * - Trust/revoke tools
 *
 * @example
 * ```typescript
 * const escapes = new EscapeManager();
 *
 * // Before blocking an action, check if escape applies
 * const check = escapes.shouldAllowOutput('session-1');
 * if (check.allowed) {
 *   // Skip blocking, action was escaped
 *   return;
 * }
 *
 * // Grant allow-once after user requests it
 * escapes.grantAllowOnce('session-1', { scope: 'output' });
 *
 * // Pause protection temporarily
 * escapes.pause('session-1', { durationMs: 60000 });
 *
 * // Trust a specific tool
 * escapes.trustTool('session-1', 'my-safe-tool');
 * ```
 */
export class EscapeManager {
  /** Allow-once manager */
  readonly allowOnce: AllowOnceManager;

  /** Pause manager */
  readonly pause: PauseManager;

  /** Trust manager */
  readonly trust: TrustManager;

  /**
   * Create a new EscapeManager.
   *
   * @param options - Manager options
   */
  constructor(options: EscapeManagerOptions = {}) {
    this.allowOnce = new AllowOnceManager(options.allowOnceCleanupMs);
    this.pause = new PauseManager(options.pauseCleanupMs);
    this.trust = new TrustManager(options.trustCleanupMs);
  }

  // ===========================================================================
  // Unified Check Methods
  // ===========================================================================

  /**
   * Check if an output action should be allowed.
   *
   * Checks: pause → allow-once
   *
   * @param sessionId - Session to check
   * @returns Whether to allow and why
   */
  shouldAllowOutput(sessionId: string): EscapeCheckResult {
    // Check pause first
    if (this.pause.isPaused(sessionId)) {
      return {
        allowed: true,
        mechanism: 'pause',
        reason: 'Protection is paused',
      };
    }

    // Check allow-once
    const allowOnceResult = this.allowOnce.use(sessionId, 'output', 'output validation');
    if (allowOnceResult.success) {
      return {
        allowed: true,
        mechanism: 'allow_once',
        reason: 'Allow-once token used',
      };
    }

    return { allowed: false };
  }

  /**
   * Check if a tool call should be allowed.
   *
   * Checks: pause → trust → allow-once
   *
   * @param sessionId - Session to check
   * @param toolName - Tool being called
   * @returns Whether to allow and why
   */
  shouldAllowTool(sessionId: string, toolName: string): EscapeCheckResult {
    // Check pause first
    if (this.pause.isPaused(sessionId)) {
      return {
        allowed: true,
        mechanism: 'pause',
        reason: 'Protection is paused',
      };
    }

    // Check trust
    const trustResult = this.trust.isTrusted(sessionId, toolName);
    if (trustResult.trusted) {
      return {
        allowed: true,
        mechanism: 'trust',
        reason: `Tool '${toolName}' is trusted`,
      };
    }

    // Check allow-once
    const allowOnceResult = this.allowOnce.use(sessionId, 'tool', `tool: ${toolName}`);
    if (allowOnceResult.success) {
      return {
        allowed: true,
        mechanism: 'allow_once',
        reason: 'Allow-once token used',
      };
    }

    return { allowed: false };
  }

  /**
   * Check if any escape is active for a session (without consuming tokens).
   *
   * @param sessionId - Session to check
   * @returns Whether any escape is active
   */
  hasActiveEscape(sessionId: string): boolean {
    if (this.pause.isPaused(sessionId)) {
      return true;
    }

    const allowOnceCheck = this.allowOnce.check(sessionId);
    if (allowOnceCheck.available) {
      return true;
    }

    const trustedTools = this.trust.getTrustedTools(sessionId);
    if (trustedTools.length > 0) {
      return true;
    }

    return false;
  }

  // ===========================================================================
  // Allow-Once Shortcuts
  // ===========================================================================

  /**
   * Grant an allow-once token.
   *
   * @param sessionId - Session to grant for
   * @param options - Grant options
   * @returns The granted token
   */
  grantAllowOnce(
    sessionId: string,
    options?: { scope?: AllowOnceScope; expirationMs?: number }
  ) {
    return this.allowOnce.grant(sessionId, options);
  }

  /**
   * Revoke allow-once token for a session.
   *
   * @param sessionId - Session to revoke for
   * @returns Whether a token was revoked
   */
  revokeAllowOnce(sessionId: string): boolean {
    return this.allowOnce.revoke(sessionId);
  }

  // ===========================================================================
  // Pause Shortcuts
  // ===========================================================================

  /**
   * Pause protection for a session.
   *
   * @param sessionId - Session to pause
   * @param options - Pause options
   * @returns Pause result
   */
  pauseProtection(
    sessionId: string,
    options?: { durationMs?: number; reason?: string }
  ) {
    return this.pause.pause(sessionId, options);
  }

  /**
   * Resume protection for a session.
   *
   * @param sessionId - Session to resume
   * @returns Resume result
   */
  resumeProtection(sessionId: string) {
    return this.pause.resume(sessionId);
  }

  /**
   * Pause protection globally.
   *
   * @param options - Pause options
   * @returns Pause result
   */
  pauseGlobal(options?: { durationMs?: number; reason?: string }) {
    return this.pause.pauseGlobal(options);
  }

  /**
   * Resume protection globally.
   *
   * @returns Resume result
   */
  resumeGlobal() {
    return this.pause.resumeGlobal();
  }

  // ===========================================================================
  // Trust Shortcuts
  // ===========================================================================

  /**
   * Trust a tool for a session.
   *
   * @param sessionId - Session to trust for
   * @param toolName - Tool to trust
   * @param options - Trust options
   * @returns Trust result
   */
  trustTool(
    sessionId: string,
    toolName: string,
    options?: { level?: 'session' | 'temporary' | 'permanent'; durationMs?: number }
  ) {
    return this.trust.trust(sessionId, toolName, options);
  }

  /**
   * Revoke trust for a tool.
   *
   * @param sessionId - Session to revoke for
   * @param toolName - Tool to revoke
   * @returns Whether trust was revoked
   */
  revokeTrust(sessionId: string, toolName: string): boolean {
    return this.trust.revoke(sessionId, toolName);
  }

  /**
   * Trust a tool globally.
   *
   * @param toolName - Tool to trust
   * @param options - Trust options
   * @returns Trust result
   */
  trustGlobal(
    toolName: string,
    options?: { level?: 'session' | 'temporary' | 'permanent'; durationMs?: number }
  ) {
    return this.trust.trustGlobal(toolName, options);
  }

  // ===========================================================================
  // State Methods
  // ===========================================================================

  /**
   * Get combined escape state for a session.
   *
   * @param sessionId - Session to get state for
   * @returns Combined escape state
   */
  getState(sessionId: string): EscapeState {
    const pauseState = this.pause.getState(sessionId);
    const allowOnceState = this.allowOnce.getState(sessionId);
    const trustedTools = this.trust.getTrustedTools(sessionId);

    return {
      paused: pauseState.paused,
      pauseReason: pauseState.reason,
      pauseExpiresAt: pauseState.expiresAt,
      allowOnceActive: allowOnceState.active,
      allowOnceScope: allowOnceState.scope,
      allowOnceExpiresAt: allowOnceState.expiresAt,
      trustedToolsCount: trustedTools.length,
      trustedTools: trustedTools.map(t => t.name),
    };
  }

  /**
   * Get statistics for all escape mechanisms.
   *
   * @returns Combined statistics
   */
  getStats(): EscapeStats {
    return {
      allowOnce: this.allowOnce.getStats(),
      pause: this.pause.getStats(),
      trust: this.trust.getStats(),
    };
  }

  // ===========================================================================
  // Session Cleanup
  // ===========================================================================

  /**
   * Clean up all escape state for a session.
   *
   * Call this when a session ends.
   *
   * @param sessionId - Session to clean up
   */
  cleanupSession(sessionId: string): void {
    this.allowOnce.revoke(sessionId);
    this.pause.resume(sessionId);
    this.trust.revokeAll(sessionId);
  }

  /**
   * Clear all escape states (for testing/cleanup).
   */
  clear(): void {
    this.allowOnce.clear();
    this.pause.clear();
    this.trust.clear();
  }

  /**
   * Destroy the manager and stop cleanup intervals.
   */
  destroy(): void {
    this.allowOnce.destroy();
    this.pause.destroy();
    this.trust.destroy();
  }
}

// =============================================================================
// Factory Function
// =============================================================================

/**
 * Create a new EscapeManager instance.
 *
 * @param options - Manager options
 * @returns New EscapeManager
 */
export function createEscapeManager(options?: EscapeManagerOptions): EscapeManager {
  return new EscapeManager(options);
}
