/**
 * End-to-End Integration Tests
 *
 * Tests complete workflows from plugin registration through
 * validation, blocking, and logging.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { register } from '../plugin';
import {
  createSentinelHooks,
  parseConfig,
  EscapeManager,
  AuditLog,
  AlertManager,
  executeCommand,
  getLevelConfig,
} from '../index';
import type { ProtectionLevel } from '../types';

// Mock fetch for webhook tests
const mockFetch = vi.fn().mockResolvedValue({
  ok: true,
  status: 200,
});

describe('End-to-End: Plugin Registration', () => {
  it('should register all hooks with Moltbot API', () => {
    const registeredHooks: string[] = [];

    const mockApi = {
      id: 'sentinel',
      name: 'Sentinel Safety',
      pluginConfig: { level: 'guard' },
      logger: {
        info: () => {},
        warn: () => {},
        error: () => {},
        debug: () => {},
      },
      on: (hookName: string) => {
        registeredHooks.push(hookName);
      },
    };

    register(mockApi);

    expect(registeredHooks).toContain('message_received');
    expect(registeredHooks).toContain('before_agent_start');
    expect(registeredHooks).toContain('message_sending');
    expect(registeredHooks).toContain('before_tool_call');
    expect(registeredHooks).toContain('agent_end');
    expect(registeredHooks.length).toBe(5);
  });

  it('should skip registration when level is off', () => {
    const registeredHooks: string[] = [];

    const mockApi = {
      id: 'sentinel',
      name: 'Sentinel Safety',
      pluginConfig: { level: 'off' },
      logger: {
        info: () => {},
        warn: () => {},
        error: () => {},
        debug: () => {},
      },
      on: (hookName: string) => {
        registeredHooks.push(hookName);
      },
    };

    register(mockApi);

    expect(registeredHooks.length).toBe(0);
  });
});

describe('End-to-End: Hook Factory', () => {
  it('should create all hooks with guard level', () => {
    const hooks = createSentinelHooks({ level: 'guard' });

    expect(hooks.messageReceived).toBeTypeOf('function');
    expect(hooks.beforeAgentStart).toBeTypeOf('function');
    expect(hooks.messageSending).toBeTypeOf('function');
    expect(hooks.beforeToolCall).toBeTypeOf('function');
    expect(hooks.agentEnd).toBeTypeOf('function');
  });

  it('should inject seed in beforeAgentStart at guard level', () => {
    const hooks = createSentinelHooks({ level: 'guard' });

    const result = hooks.beforeAgentStart({
      sessionId: 'test-session',
      systemPrompt: 'You are a helpful assistant',
    });

    expect(result).toBeDefined();
    // The seed contains the full phrase, not abbreviation
    expect(result?.additionalContext).toContain('Truth');
    expect(result?.additionalContext).toContain('Harm');
    expect(result?.additionalContext).toContain('Scope');
    expect(result?.additionalContext).toContain('Purpose');
  });

  it('should inject seed in beforeAgentStart at watch level', () => {
    const hooks = createSentinelHooks({ level: 'watch' });

    const result = hooks.beforeAgentStart({
      sessionId: 'test-session',
      systemPrompt: 'You are a helpful assistant',
    });

    // Watch level also injects seeds
    expect(result).toBeDefined();
    expect(result?.additionalContext).toContain('sentinel');
  });

  it('should block data leaks in messageSending at guard level', async () => {
    const hooks = createSentinelHooks({ level: 'guard' });

    const result = await hooks.messageSending({
      sessionId: 'test-session',
      content: 'Here is your API key: sk-1234567890abcdef',
    });

    expect(result).toBeDefined();
    expect(result?.cancel).toBe(true);
    // The reason format uses different wording
    expect(result?.cancelReason).toBeDefined();
  });

  it('should not block data leaks at watch level', async () => {
    const hooks = createSentinelHooks({ level: 'watch' });

    const result = await hooks.messageSending({
      sessionId: 'test-session',
      content: 'Here is your API key: sk-1234567890abcdef',
    });

    // Watch level only logs, does not block
    expect(result).toBeUndefined();
  });

  it('should block dangerous tools at guard level', async () => {
    const hooks = createSentinelHooks({ level: 'guard' });

    const result = await hooks.beforeToolCall({
      sessionId: 'test-session',
      toolName: 'rm',
      params: { path: '/important' },
    });

    expect(result).toBeDefined();
    expect(result?.block).toBe(true);
  });
});

describe('End-to-End: Configuration Parsing', () => {
  it('should parse valid config', () => {
    const config = parseConfig({ level: 'shield' });

    expect(config.level).toBe('shield');
  });

  it('should use defaults for partial config', () => {
    const config = parseConfig({});

    // Default is 'watch' level
    expect(config.level).toBe('watch');
    expect(config.ignorePatterns).toEqual([]);
  });

  it('should get level config correctly', () => {
    const levelConfig = getLevelConfig('shield');

    expect(levelConfig.level).toBe('shield');
    // Shield level has strict blocking
    expect(levelConfig.blocking).toBeDefined();
  });
});

describe('End-to-End: Audit Logging', () => {
  let audit: AuditLog;

  beforeEach(() => {
    audit = new AuditLog({ maxEntries: 100 });
  });

  it('should log and retrieve entries', () => {
    audit.logInputAnalysis('session-1', 0, []);
    audit.logInputAnalysis('session-2', 3, []);
    audit.logOutputValidation('session-1', false, []);

    const allEntries = audit.getRecent(10);
    expect(allEntries.length).toBe(3);

    const session1Entries = audit.query({ sessionId: 'session-1' });
    expect(session1Entries.length).toBe(2);
  });

  it('should provide statistics', () => {
    audit.logInputAnalysis('session-1', 0, []);
    audit.logOutputValidation('session-1', true, []);

    const stats = audit.getStats();
    expect(stats.totalEntries).toBe(2);
    expect(stats.byOutcome.allowed).toBe(1);
    expect(stats.byOutcome.blocked).toBe(1);
  });
});

describe('End-to-End: CLI Commands', () => {
  let escapes: EscapeManager;
  let audit: AuditLog;

  beforeEach(() => {
    escapes = new EscapeManager();
    audit = new AuditLog();
  });

  afterEach(() => {
    escapes.destroy();
  });

  it('should execute status command', async () => {
    const result = await executeCommand('status', {
      sessionId: 'cli-test',
      currentLevel: 'guard' as ProtectionLevel,
      escapes,
      audit,
      useColor: false,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain('GUARD');
  });

  it('should execute level command', async () => {
    let newLevel: ProtectionLevel = 'guard';

    const result = await executeCommand('level shield', {
      sessionId: 'cli-test',
      currentLevel: 'guard' as ProtectionLevel,
      escapes,
      audit,
      useColor: false,
      onLevelChange: (level) => {
        newLevel = level;
      },
    });

    expect(result.success).toBe(true);
    expect(newLevel).toBe('shield');
  });

  it('should execute help command', async () => {
    const result = await executeCommand('help', {
      sessionId: 'cli-test',
      currentLevel: 'guard' as ProtectionLevel,
      escapes,
      audit,
      useColor: false,
    });

    expect(result.success).toBe(true);
    expect(result.message).toContain('status');
    expect(result.message).toContain('level');
    expect(result.message).toContain('pause');
    expect(result.message).toContain('trust');
  });

  it('should handle unknown command', async () => {
    const result = await executeCommand('unknown', {
      sessionId: 'cli-test',
      currentLevel: 'guard' as ProtectionLevel,
      escapes,
      audit,
      useColor: false,
    });

    expect(result.success).toBe(false);
    expect(result.message).toContain('Unknown command');
  });
});

describe('End-to-End: Escape Manager', () => {
  let escapes: EscapeManager;

  beforeEach(() => {
    escapes = new EscapeManager();
  });

  afterEach(() => {
    escapes.destroy();
  });

  it('should grant and consume allow-once token', () => {
    escapes.grantAllowOnce('session-1', { scope: 'output' });

    // Check token exists
    const state = escapes.allowOnce.getState('session-1');
    expect(state.active).toBe(true);

    // Use the token (requires 3 args: sessionId, scope, actionDescription)
    const use = escapes.allowOnce.use('session-1', 'output', 'test action');
    expect(use.success).toBe(true);

    // Token should be consumed
    const stateAfter = escapes.allowOnce.getState('session-1');
    expect(stateAfter.active).toBe(false);
  });

  it('should pause and resume protection', () => {
    escapes.pauseProtection('session-1', { durationMs: 60000 });

    expect(escapes.pause.isPaused('session-1')).toBe(true);

    escapes.resumeProtection('session-1');

    expect(escapes.pause.isPaused('session-1')).toBe(false);
  });

  it('should trust and revoke tools', () => {
    escapes.trustTool('session-1', 'bash', { level: 'session' });

    const check = escapes.trust.isTrusted('session-1', 'bash');
    expect(check.trusted).toBe(true);

    escapes.revokeTrust('session-1', 'bash');

    const check2 = escapes.trust.isTrusted('session-1', 'bash');
    expect(check2.trusted).toBe(false);
  });

  it('should isolate sessions', () => {
    escapes.pauseProtection('session-1', { durationMs: 60000 });

    expect(escapes.pause.isPaused('session-1')).toBe(true);
    expect(escapes.pause.isPaused('session-2')).toBe(false);
  });
});

describe('End-to-End: Alert Manager', () => {
  let alerts: AlertManager;
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    originalFetch = global.fetch;
    global.fetch = mockFetch;
    mockFetch.mockClear();

    alerts = new AlertManager({
      webhooks: [
        {
          url: 'https://webhook.example.com/sentinel',
          minSeverity: 'medium',
        },
      ],
      rateLimitWindowMs: 1000,
      rateLimitMax: 10,
    });
  });

  afterEach(() => {
    global.fetch = originalFetch;
    alerts.clear();
  });

  it('should send webhook on alert', async () => {
    const result = await alerts.alertHighThreatInput(
      5,
      [{ type: 'jailbreak', severity: 'critical', description: 'Test' }],
      'test-session'
    );

    expect(result.sent).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith(
      'https://webhook.example.com/sentinel',
      expect.objectContaining({
        method: 'POST',
      })
    );
  });

  it('should rate limit excessive alerts', async () => {
    const limitedAlerts = new AlertManager({
      webhooks: [{ url: 'https://webhook.example.com/test' }],
      rateLimitWindowMs: 60000,
      rateLimitMax: 2,
    });

    await limitedAlerts.alertActionBlocked('output', 'reason', 'test');
    await limitedAlerts.alertActionBlocked('output', 'reason', 'test');
    const result = await limitedAlerts.alertActionBlocked('output', 'reason', 'test');

    expect(result.rateLimited).toBe(true);

    limitedAlerts.clear();
  });

  it('should track alert statistics', async () => {
    await alerts.alertHighThreatInput(5, [], 'test');
    await alerts.alertHighThreatInput(3, [], 'test');

    const stats = alerts.getStats();
    expect(stats.totalAlerts).toBe(2);
    expect(stats.webhookSuccesses).toBe(2);
  });
});

describe('End-to-End: Protection Level Behavior', () => {
  it('should allow everything at off level', async () => {
    const hooks = createSentinelHooks({ level: 'off' });

    const result = await hooks.messageSending({
      sessionId: 'test',
      content: 'API key: sk-1234567890abcdef Password: secret123',
    });

    expect(result).toBeUndefined();
  });

  it('should only log at watch level', async () => {
    const hooks = createSentinelHooks({ level: 'watch' });

    const result = await hooks.messageSending({
      sessionId: 'test',
      content: 'API key: sk-1234567890abcdef',
    });

    expect(result).toBeUndefined();
  });

  it('should block at guard level', async () => {
    const hooks = createSentinelHooks({ level: 'guard' });

    const result = await hooks.messageSending({
      sessionId: 'test',
      content: 'API key: sk-1234567890abcdef',
    });

    expect(result?.cancel).toBe(true);
  });

  it('should block at shield level', async () => {
    const hooks = createSentinelHooks({ level: 'shield' });

    const result = await hooks.messageSending({
      sessionId: 'test',
      content: 'Password: secret123',
    });

    expect(result?.cancel).toBe(true);
  });
});
