/**
 * Escape Hatches Tests
 *
 * Tests for the escape hatch modules:
 * - AllowOnceManager
 * - PauseManager
 * - TrustManager
 * - EscapeManager (unified)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  // AllowOnce
  AllowOnceManager,
  createAllowOnceManager,
  isValidScope,
  formatRemainingTime,
  DEFAULT_EXPIRATION_MS,
  // Pause
  PauseManager,
  createPauseManager,
  formatPauseTime,
  GLOBAL_SESSION_ID,
  // Trust
  TrustManager,
  createTrustManager,
  isValidToolPattern,
  formatTrustDuration,
  GLOBAL_TRUST_SESSION_ID,
  // Unified
  EscapeManager,
  createEscapeManager,
} from '../escapes';

// =============================================================================
// AllowOnceManager Tests
// =============================================================================

describe('AllowOnceManager', () => {
  let manager: AllowOnceManager;

  beforeEach(() => {
    vi.useFakeTimers();
    manager = new AllowOnceManager(1000); // Fast cleanup for tests
  });

  afterEach(() => {
    manager.destroy();
    vi.useRealTimers();
  });

  describe('grant', () => {
    it('should grant a token with default scope', () => {
      const token = manager.grant('session-1');

      expect(token.id).toBeDefined();
      expect(token.sessionId).toBe('session-1');
      expect(token.scope).toBe('any');
      expect(token.used).toBe(false);
      expect(token.expiresAt).toBeGreaterThan(Date.now());
    });

    it('should grant a token with specific scope', () => {
      const token = manager.grant('session-1', { scope: 'tool' });

      expect(token.scope).toBe('tool');
    });

    it('should grant a token with custom expiration', () => {
      const now = Date.now();
      const token = manager.grant('session-1', { expirationMs: 60000 });

      expect(token.expiresAt).toBe(now + 60000);
    });

    it('should clamp expiration to max', () => {
      const now = Date.now();
      const token = manager.grant('session-1', { expirationMs: 10 * 60 * 1000 }); // 10 min

      // Should be clamped to max (5 min)
      expect(token.expiresAt).toBe(now + 5 * 60 * 1000);
    });

    it('should replace existing token for same session', () => {
      const token1 = manager.grant('session-1', { scope: 'output' });
      const token2 = manager.grant('session-1', { scope: 'tool' });

      expect(token2.scope).toBe('tool');
      expect(token2.id).not.toBe(token1.id);
    });
  });

  describe('check', () => {
    it('should return available for valid token', () => {
      manager.grant('session-1');

      const result = manager.check('session-1');

      expect(result.available).toBe(true);
      expect(result.token).toBeDefined();
    });

    it('should return not available when no token', () => {
      const result = manager.check('session-1');

      expect(result.available).toBe(false);
      expect(result.reason).toBe('no_token');
    });

    it('should return expired for expired token', () => {
      manager.grant('session-1', { expirationMs: 5000 });

      // Advance time past expiration but before cleanup runs again
      // Note: cleanup may have already removed expired tokens
      vi.advanceTimersByTime(5001);

      const result = manager.check('session-1');

      expect(result.available).toBe(false);
      // Token may be expired or already cleaned up
      expect(['expired', 'no_token']).toContain(result.reason);
    });

    it('should check scope correctly', () => {
      manager.grant('session-1', { scope: 'output' });

      const toolCheck = manager.check('session-1', 'tool');
      expect(toolCheck.available).toBe(false);
      expect(toolCheck.reason).toBe('wrong_scope');

      const outputCheck = manager.check('session-1', 'output');
      expect(outputCheck.available).toBe(true);
    });

    it('should match any scope to all requests', () => {
      manager.grant('session-1', { scope: 'any' });

      expect(manager.check('session-1', 'tool').available).toBe(true);
      expect(manager.check('session-1', 'output').available).toBe(true);
    });
  });

  describe('use', () => {
    it('should consume token on use', () => {
      manager.grant('session-1', { scope: 'tool' });

      const result = manager.use('session-1', 'tool', 'bash');

      expect(result.success).toBe(true);
      expect(result.token?.used).toBe(true);
      expect(result.token?.usedFor).toBe('bash');
    });

    it('should fail when token already used', () => {
      manager.grant('session-1');
      manager.use('session-1', 'any', 'first use');

      const result = manager.use('session-1', 'any', 'second use');

      expect(result.success).toBe(false);
      expect(result.error).toBe('already_used');
    });

    it('should fail for wrong scope', () => {
      manager.grant('session-1', { scope: 'output' });

      const result = manager.use('session-1', 'tool', 'bash');

      expect(result.success).toBe(false);
      expect(result.error).toBe('wrong_scope');
    });
  });

  describe('revoke', () => {
    it('should revoke existing token', () => {
      manager.grant('session-1');

      const revoked = manager.revoke('session-1');

      expect(revoked).toBe(true);
      expect(manager.check('session-1').available).toBe(false);
    });

    it('should return false when no token', () => {
      const revoked = manager.revoke('session-1');

      expect(revoked).toBe(false);
    });
  });

  describe('getState', () => {
    it('should return inactive when no token', () => {
      const state = manager.getState('session-1');

      expect(state.active).toBe(false);
    });

    it('should return active state for valid token', () => {
      manager.grant('session-1', { scope: 'tool' });

      const state = manager.getState('session-1');

      expect(state.active).toBe(true);
      expect(state.scope).toBe('tool');
      expect(state.expiresAt).toBeDefined();
    });
  });

  describe('getRemainingTime', () => {
    it('should return remaining time', () => {
      manager.grant('session-1', { expirationMs: 10000 });

      const remaining = manager.getRemainingTime('session-1');

      expect(remaining).toBeLessThanOrEqual(10000);
      expect(remaining).toBeGreaterThan(9000);
    });

    it('should return 0 when no token', () => {
      expect(manager.getRemainingTime('session-1')).toBe(0);
    });
  });

  describe('cleanup', () => {
    it('should clean up expired tokens', () => {
      manager.grant('session-1', { expirationMs: 5000 });
      manager.grant('session-2', { expirationMs: 5000 });

      // Advance past expiration
      vi.advanceTimersByTime(6000);
      // Trigger cleanup
      vi.advanceTimersByTime(1000);

      expect(manager.getStats().active).toBe(0);
    });

    it('should clean up used tokens', () => {
      manager.grant('session-1');
      manager.use('session-1', 'any', 'test');

      // Trigger cleanup
      vi.advanceTimersByTime(1000);

      expect(manager.getStats().active).toBe(0);
    });
  });
});

describe('AllowOnce utilities', () => {
  describe('isValidScope', () => {
    it('should validate scopes', () => {
      expect(isValidScope('output')).toBe(true);
      expect(isValidScope('tool')).toBe(true);
      expect(isValidScope('any')).toBe(true);
      expect(isValidScope('invalid')).toBe(false);
      expect(isValidScope(null)).toBe(false);
    });
  });

  describe('formatRemainingTime', () => {
    it('should format seconds', () => {
      expect(formatRemainingTime(5000)).toBe('5s');
      expect(formatRemainingTime(30000)).toBe('30s');
    });

    it('should format minutes', () => {
      expect(formatRemainingTime(60000)).toBe('1m');
      expect(formatRemainingTime(90000)).toBe('1m 30s');
    });

    it('should handle expired', () => {
      expect(formatRemainingTime(0)).toBe('expired');
      expect(formatRemainingTime(-1000)).toBe('expired');
    });
  });

  describe('createAllowOnceManager', () => {
    it('should create manager', () => {
      const manager = createAllowOnceManager();
      expect(manager).toBeInstanceOf(AllowOnceManager);
      manager.destroy();
    });
  });
});

// =============================================================================
// PauseManager Tests
// =============================================================================

describe('PauseManager', () => {
  let manager: PauseManager;

  beforeEach(() => {
    vi.useFakeTimers();
    manager = new PauseManager(1000);
  });

  afterEach(() => {
    manager.destroy();
    vi.useRealTimers();
  });

  describe('pause', () => {
    it('should pause a session', () => {
      const result = manager.pause('session-1');

      expect(result.success).toBe(true);
      expect(result.record?.active).toBe(true);
      expect(manager.isPaused('session-1')).toBe(true);
    });

    it('should pause with duration', () => {
      const now = Date.now();
      const result = manager.pause('session-1', { durationMs: 60000 });

      expect(result.record?.expiresAt).toBe(now + 60000);
    });

    it('should pause indefinitely', () => {
      const result = manager.pause('session-1', { indefinite: true });

      expect(result.record?.expiresAt).toBeUndefined();
    });

    it('should fail when already paused', () => {
      manager.pause('session-1');
      const result = manager.pause('session-1');

      expect(result.success).toBe(false);
      expect(result.error).toBe('already_paused');
    });

    it('should record reason', () => {
      manager.pause('session-1', { reason: 'Debugging' });

      const state = manager.getState('session-1');
      expect(state.reason).toBe('Debugging');
    });
  });

  describe('pauseGlobal', () => {
    it('should pause globally', () => {
      manager.pauseGlobal({ reason: 'Maintenance' });

      expect(manager.isPaused('any-session')).toBe(true);
      expect(manager.isPaused('another-session')).toBe(true);
    });
  });

  describe('resume', () => {
    it('should resume a paused session', () => {
      manager.pause('session-1');

      const result = manager.resume('session-1');

      expect(result.success).toBe(true);
      expect(result.pausedDurationMs).toBeDefined();
      expect(manager.isPaused('session-1')).toBe(false);
    });

    it('should fail when not paused', () => {
      const result = manager.resume('session-1');

      expect(result.success).toBe(false);
      expect(result.error).toBe('not_paused');
    });
  });

  describe('isPaused', () => {
    it('should check session pause', () => {
      expect(manager.isPaused('session-1')).toBe(false);

      manager.pause('session-1');

      expect(manager.isPaused('session-1')).toBe(true);
    });

    it('should check global pause', () => {
      manager.pauseGlobal();

      expect(manager.isPaused('session-1')).toBe(true);
      expect(manager.isPaused('session-2')).toBe(true);
    });

    it('should handle expiration', () => {
      // MIN_PAUSE_DURATION_MS is 10s, so use 15000ms to ensure it's not clamped
      manager.pause('session-1', { durationMs: 15000 });

      expect(manager.isPaused('session-1')).toBe(true);

      // Advance past expiration
      vi.advanceTimersByTime(16000);

      expect(manager.isPaused('session-1')).toBe(false);
    });
  });

  describe('getState', () => {
    it('should return not paused when not paused', () => {
      const state = manager.getState('session-1');

      expect(state.paused).toBe(false);
    });

    it('should return paused state', () => {
      manager.pause('session-1', { reason: 'Testing' });

      const state = manager.getState('session-1');

      expect(state.paused).toBe(true);
      expect(state.reason).toBe('Testing');
    });

    it('should include global pause info', () => {
      manager.pauseGlobal({ reason: 'Global maintenance' });

      const state = manager.getState('session-1');

      expect(state.paused).toBe(true);
      expect(state.reason).toBe('Global maintenance');
    });
  });

  describe('getRemainingTime', () => {
    it('should return remaining time', () => {
      manager.pause('session-1', { durationMs: 60000 });

      const remaining = manager.getRemainingTime('session-1');

      expect(remaining).toBeLessThanOrEqual(60000);
      expect(remaining).toBeGreaterThan(59000);
    });

    it('should return 0 when not paused', () => {
      expect(manager.getRemainingTime('session-1')).toBe(0);
    });
  });
});

describe('Pause utilities', () => {
  describe('formatPauseTime', () => {
    it('should format seconds', () => {
      expect(formatPauseTime(30000)).toBe('30s');
    });

    it('should format minutes', () => {
      expect(formatPauseTime(120000)).toBe('2m');
      expect(formatPauseTime(150000)).toBe('2m 30s');
    });

    it('should format hours', () => {
      expect(formatPauseTime(3600000)).toBe('1h');
      expect(formatPauseTime(3720000)).toBe('1h 2m');
    });

    it('should handle indefinite', () => {
      expect(formatPauseTime(undefined)).toBe('indefinite');
    });

    it('should handle expired', () => {
      expect(formatPauseTime(0)).toBe('expired');
    });
  });

  describe('createPauseManager', () => {
    it('should create manager', () => {
      const manager = createPauseManager();
      expect(manager).toBeInstanceOf(PauseManager);
      manager.destroy();
    });
  });
});

// =============================================================================
// TrustManager Tests
// =============================================================================

describe('TrustManager', () => {
  let manager: TrustManager;

  beforeEach(() => {
    vi.useFakeTimers();
    manager = new TrustManager(1000);
  });

  afterEach(() => {
    manager.destroy();
    vi.useRealTimers();
  });

  describe('trust', () => {
    it('should trust a tool', () => {
      const result = manager.trust('session-1', 'my-tool');

      expect(result.success).toBe(true);
      expect(result.record?.name).toBe('my-tool');
      expect(result.record?.level).toBe('session');
    });

    it('should normalize tool names', () => {
      const result = manager.trust('session-1', '  MY-TOOL  ');

      expect(result.record?.name).toBe('my-tool');
    });

    it('should fail on invalid tool name', () => {
      const result = manager.trust('session-1', '');

      expect(result.success).toBe(false);
      expect(result.error).toBe('invalid_tool_name');
    });

    it('should fail on already trusted', () => {
      manager.trust('session-1', 'my-tool');
      const result = manager.trust('session-1', 'my-tool');

      expect(result.success).toBe(false);
      expect(result.error).toBe('already_trusted');
    });

    it('should set temporary trust with expiration', () => {
      const now = Date.now();
      const result = manager.trust('session-1', 'my-tool', {
        level: 'temporary',
        durationMs: 60000,
      });

      expect(result.record?.level).toBe('temporary');
      expect(result.record?.expiresAt).toBe(now + 60000);
    });

    it('should detect patterns', () => {
      const result = manager.trust('session-1', 'mcp__*');

      expect(result.record?.isPattern).toBe(true);
    });
  });

  describe('trustGlobal', () => {
    it('should trust globally', () => {
      manager.trustGlobal('global-tool');

      expect(manager.isTrusted('session-1', 'global-tool').trusted).toBe(true);
      expect(manager.isTrusted('session-2', 'global-tool').trusted).toBe(true);
    });
  });

  describe('revoke', () => {
    it('should revoke trust', () => {
      manager.trust('session-1', 'my-tool');

      const revoked = manager.revoke('session-1', 'my-tool');

      expect(revoked).toBe(true);
      expect(manager.isTrusted('session-1', 'my-tool').trusted).toBe(false);
    });

    it('should return false when not trusted', () => {
      const revoked = manager.revoke('session-1', 'my-tool');

      expect(revoked).toBe(false);
    });
  });

  describe('revokeAll', () => {
    it('should revoke all trusts for session', () => {
      manager.trust('session-1', 'tool-1');
      manager.trust('session-1', 'tool-2');
      manager.trust('session-1', 'tool-3');

      const count = manager.revokeAll('session-1');

      expect(count).toBe(3);
      expect(manager.getTrustedTools('session-1', false).length).toBe(0);
    });
  });

  describe('isTrusted', () => {
    it('should check exact match', () => {
      manager.trust('session-1', 'my-tool');

      const result = manager.isTrusted('session-1', 'my-tool');

      expect(result.trusted).toBe(true);
      expect(result.matchType).toBe('exact');
    });

    it('should check pattern match', () => {
      manager.trust('session-1', 'mcp__*');

      const result = manager.isTrusted('session-1', 'mcp__browser__navigate');

      expect(result.trusted).toBe(true);
      expect(result.matchType).toBe('pattern');
    });

    it('should check global trust', () => {
      manager.trustGlobal('global-tool');

      const result = manager.isTrusted('session-1', 'global-tool');

      expect(result.trusted).toBe(true);
    });

    it('should return not trusted when not matching', () => {
      const result = manager.isTrusted('session-1', 'unknown-tool');

      expect(result.trusted).toBe(false);
    });

    it('should handle expiration', () => {
      manager.trust('session-1', 'my-tool', {
        level: 'temporary',
        durationMs: 5000,
      });

      expect(manager.isTrusted('session-1', 'my-tool').trusted).toBe(true);

      vi.advanceTimersByTime(6000);

      expect(manager.isTrusted('session-1', 'my-tool').trusted).toBe(false);
    });
  });

  describe('getTrustedTools', () => {
    it('should return all trusted tools', () => {
      manager.trust('session-1', 'tool-1');
      manager.trust('session-1', 'tool-2');
      manager.trustGlobal('global-tool');

      const tools = manager.getTrustedTools('session-1');

      expect(tools.length).toBe(3);
    });

    it('should exclude global when requested', () => {
      manager.trust('session-1', 'tool-1');
      manager.trustGlobal('global-tool');

      const tools = manager.getTrustedTools('session-1', false);

      expect(tools.length).toBe(1);
    });
  });

  describe('pattern matching', () => {
    it('should match wildcards', () => {
      manager.trust('session-1', 'mcp__*');

      expect(manager.isTrusted('session-1', 'mcp__browser').trusted).toBe(true);
      expect(manager.isTrusted('session-1', 'mcp__navigate').trusted).toBe(true);
      expect(manager.isTrusted('session-1', 'other__tool').trusted).toBe(false);
    });

    it('should match prefix wildcards', () => {
      manager.trust('session-1', '*__tool');

      expect(manager.isTrusted('session-1', 'prefix__tool').trusted).toBe(true);
      expect(manager.isTrusted('session-1', 'tool').trusted).toBe(false);
    });

    it('should match middle wildcards', () => {
      manager.trust('session-1', 'prefix__*__suffix');

      expect(manager.isTrusted('session-1', 'prefix__middle__suffix').trusted).toBe(true);
      expect(manager.isTrusted('session-1', 'prefix__a__b__suffix').trusted).toBe(true);
    });
  });
});

describe('Trust utilities', () => {
  describe('isValidToolPattern', () => {
    it('should validate patterns', () => {
      expect(isValidToolPattern('my-tool')).toBe(true);
      expect(isValidToolPattern('mcp__*')).toBe(true);
      expect(isValidToolPattern('*')).toBe(false); // Too broad
      expect(isValidToolPattern('')).toBe(false);
      expect(isValidToolPattern('  ')).toBe(false);
    });
  });

  describe('formatTrustDuration', () => {
    it('should format permanent', () => {
      const record = {
        name: 'tool',
        level: 'permanent' as const,
        sessionId: 's',
        grantedAt: Date.now(),
        isPattern: false,
      };
      expect(formatTrustDuration(record)).toBe('permanent');
    });

    it('should format session', () => {
      const record = {
        name: 'tool',
        level: 'session' as const,
        sessionId: 's',
        grantedAt: Date.now(),
        isPattern: false,
      };
      expect(formatTrustDuration(record)).toBe('session');
    });
  });

  describe('createTrustManager', () => {
    it('should create manager', () => {
      const manager = createTrustManager();
      expect(manager).toBeInstanceOf(TrustManager);
      manager.destroy();
    });
  });
});

// =============================================================================
// EscapeManager Tests
// =============================================================================

describe('EscapeManager', () => {
  let manager: EscapeManager;

  beforeEach(() => {
    vi.useFakeTimers();
    manager = new EscapeManager({
      allowOnceCleanupMs: 1000,
      pauseCleanupMs: 1000,
      trustCleanupMs: 1000,
    });
  });

  afterEach(() => {
    manager.destroy();
    vi.useRealTimers();
  });

  describe('shouldAllowOutput', () => {
    it('should not allow by default', () => {
      const result = manager.shouldAllowOutput('session-1');

      expect(result.allowed).toBe(false);
    });

    it('should allow when paused', () => {
      manager.pauseProtection('session-1');

      const result = manager.shouldAllowOutput('session-1');

      expect(result.allowed).toBe(true);
      expect(result.mechanism).toBe('pause');
    });

    it('should allow with allow-once', () => {
      manager.grantAllowOnce('session-1', { scope: 'output' });

      const result = manager.shouldAllowOutput('session-1');

      expect(result.allowed).toBe(true);
      expect(result.mechanism).toBe('allow_once');
    });

    it('should consume allow-once token', () => {
      manager.grantAllowOnce('session-1', { scope: 'output' });

      manager.shouldAllowOutput('session-1');
      const result = manager.shouldAllowOutput('session-1');

      expect(result.allowed).toBe(false);
    });
  });

  describe('shouldAllowTool', () => {
    it('should not allow by default', () => {
      const result = manager.shouldAllowTool('session-1', 'bash');

      expect(result.allowed).toBe(false);
    });

    it('should allow when paused', () => {
      manager.pauseProtection('session-1');

      const result = manager.shouldAllowTool('session-1', 'bash');

      expect(result.allowed).toBe(true);
      expect(result.mechanism).toBe('pause');
    });

    it('should allow trusted tool', () => {
      manager.trustTool('session-1', 'bash');

      const result = manager.shouldAllowTool('session-1', 'bash');

      expect(result.allowed).toBe(true);
      expect(result.mechanism).toBe('trust');
    });

    it('should allow with allow-once', () => {
      manager.grantAllowOnce('session-1', { scope: 'tool' });

      const result = manager.shouldAllowTool('session-1', 'bash');

      expect(result.allowed).toBe(true);
      expect(result.mechanism).toBe('allow_once');
    });

    it('should check pause before trust', () => {
      manager.pauseProtection('session-1');
      manager.trustTool('session-1', 'bash');

      const result = manager.shouldAllowTool('session-1', 'bash');

      expect(result.mechanism).toBe('pause'); // Pause takes priority
    });
  });

  describe('hasActiveEscape', () => {
    it('should return false by default', () => {
      expect(manager.hasActiveEscape('session-1')).toBe(false);
    });

    it('should detect pause', () => {
      manager.pauseProtection('session-1');

      expect(manager.hasActiveEscape('session-1')).toBe(true);
    });

    it('should detect allow-once', () => {
      manager.grantAllowOnce('session-1');

      expect(manager.hasActiveEscape('session-1')).toBe(true);
    });

    it('should detect trust', () => {
      manager.trustTool('session-1', 'bash');

      expect(manager.hasActiveEscape('session-1')).toBe(true);
    });
  });

  describe('getState', () => {
    it('should return combined state', () => {
      manager.pauseProtection('session-1', { reason: 'Testing' });
      manager.grantAllowOnce('session-1', { scope: 'tool' });
      manager.trustTool('session-1', 'bash');
      manager.trustTool('session-1', 'git');

      const state = manager.getState('session-1');

      expect(state.paused).toBe(true);
      expect(state.pauseReason).toBe('Testing');
      expect(state.allowOnceActive).toBe(true);
      expect(state.allowOnceScope).toBe('tool');
      expect(state.trustedToolsCount).toBe(2);
      expect(state.trustedTools).toContain('bash');
      expect(state.trustedTools).toContain('git');
    });
  });

  describe('getStats', () => {
    it('should return combined stats', () => {
      manager.grantAllowOnce('session-1');
      manager.pauseProtection('session-2');
      manager.trustTool('session-3', 'bash');

      const stats = manager.getStats();

      expect(stats.allowOnce.active).toBe(1);
      expect(stats.pause.active).toBe(1);
      expect(stats.trust.totalTrusts).toBe(1);
    });
  });

  describe('cleanupSession', () => {
    it('should clean up all escape state for session', () => {
      manager.grantAllowOnce('session-1');
      manager.pauseProtection('session-1');
      manager.trustTool('session-1', 'bash');

      manager.cleanupSession('session-1');

      expect(manager.hasActiveEscape('session-1')).toBe(false);
    });
  });

  describe('shortcuts', () => {
    it('should support pause shortcuts', () => {
      const pauseResult = manager.pauseProtection('session-1');
      expect(pauseResult.success).toBe(true);

      const resumeResult = manager.resumeProtection('session-1');
      expect(resumeResult.success).toBe(true);
    });

    it('should support global pause shortcuts', () => {
      manager.pauseGlobal({ reason: 'Test' });
      expect(manager.pause.isPaused('any-session')).toBe(true);

      manager.resumeGlobal();
      expect(manager.pause.isPaused('any-session')).toBe(false);
    });

    it('should support trust shortcuts', () => {
      const trustResult = manager.trustTool('session-1', 'bash');
      expect(trustResult.success).toBe(true);

      const revoked = manager.revokeTrust('session-1', 'bash');
      expect(revoked).toBe(true);
    });

    it('should support global trust shortcuts', () => {
      manager.trustGlobal('global-tool');
      expect(manager.trust.isTrusted('any-session', 'global-tool').trusted).toBe(true);
    });

    it('should support allow-once shortcuts', () => {
      const token = manager.grantAllowOnce('session-1', { scope: 'output' });
      expect(token.scope).toBe('output');

      const revoked = manager.revokeAllowOnce('session-1');
      expect(revoked).toBe(true);
    });
  });

  describe('createEscapeManager', () => {
    it('should create manager with factory', () => {
      const m = createEscapeManager();
      expect(m).toBeInstanceOf(EscapeManager);
      m.destroy();
    });
  });
});

// =============================================================================
// Integration Tests
// =============================================================================

describe('Escape Hatches Integration', () => {
  let manager: EscapeManager;

  beforeEach(() => {
    vi.useFakeTimers();
    manager = new EscapeManager();
  });

  afterEach(() => {
    manager.destroy();
    vi.useRealTimers();
  });

  it('should handle complete session lifecycle', () => {
    const sessionId = 'integration-test';

    // Initially no escapes
    expect(manager.hasActiveEscape(sessionId)).toBe(false);

    // User gets blocked, requests allow-once
    manager.grantAllowOnce(sessionId, { scope: 'tool' });
    expect(manager.hasActiveEscape(sessionId)).toBe(true);

    // Allow-once is consumed
    const toolCheck = manager.shouldAllowTool(sessionId, 'bash');
    expect(toolCheck.allowed).toBe(true);
    expect(toolCheck.mechanism).toBe('allow_once');

    // Second attempt not allowed
    const secondCheck = manager.shouldAllowTool(sessionId, 'bash');
    expect(secondCheck.allowed).toBe(false);

    // User trusts the tool permanently
    manager.trustTool(sessionId, 'bash', { level: 'permanent' });

    // Now always allowed
    const trustedCheck = manager.shouldAllowTool(sessionId, 'bash');
    expect(trustedCheck.allowed).toBe(true);
    expect(trustedCheck.mechanism).toBe('trust');

    // Session ends
    manager.cleanupSession(sessionId);
    expect(manager.hasActiveEscape(sessionId)).toBe(false);
  });

  it('should handle global pause correctly', () => {
    // Pause globally
    manager.pauseGlobal({ reason: 'Maintenance' });

    // All sessions affected
    expect(manager.shouldAllowOutput('session-1').allowed).toBe(true);
    expect(manager.shouldAllowOutput('session-2').allowed).toBe(true);
    expect(manager.shouldAllowTool('session-3', 'bash').allowed).toBe(true);

    // Resume
    manager.resumeGlobal();

    // No longer affected
    expect(manager.shouldAllowOutput('session-1').allowed).toBe(false);
    expect(manager.shouldAllowTool('session-3', 'bash').allowed).toBe(false);
  });

  it('should handle expiration correctly', () => {
    // Set short expirations
    manager.grantAllowOnce('session-1', { expirationMs: 5000 });
    manager.pauseProtection('session-2', { durationMs: 10000 });
    manager.trustTool('session-3', 'bash', { level: 'temporary', durationMs: 15000 });

    // All active
    expect(manager.hasActiveEscape('session-1')).toBe(true);
    expect(manager.hasActiveEscape('session-2')).toBe(true);
    expect(manager.hasActiveEscape('session-3')).toBe(true);

    // Advance past allow-once expiration
    vi.advanceTimersByTime(6000);
    expect(manager.hasActiveEscape('session-1')).toBe(false);
    expect(manager.hasActiveEscape('session-2')).toBe(true);

    // Advance past pause expiration
    vi.advanceTimersByTime(5000);
    expect(manager.hasActiveEscape('session-2')).toBe(false);
    expect(manager.hasActiveEscape('session-3')).toBe(true);

    // Advance past trust expiration
    vi.advanceTimersByTime(5000);
    expect(manager.hasActiveEscape('session-3')).toBe(false);
  });
});
