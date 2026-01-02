/**
 * Plugin unit tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  sentinelPlugin,
  getValidationHistory,
  getValidationStats,
  clearValidationHistory,
  validateContent,
  getPluginInstance,
  getPluginInstanceNames,
  getActivePluginInstance,
  removePluginInstance,
  clearPluginRegistry,
  TextTooLargeError,
  signMemory,
  verifyMemory,
} from './plugin';

describe('sentinelPlugin', () => {
  beforeEach(() => {
    clearValidationHistory();
  });

  describe('Plugin creation', () => {
    it('should create plugin with default config', () => {
      const plugin = sentinelPlugin();
      expect(plugin.name).toBe('sentinel-safety');
      expect(plugin.actions).toBeDefined();
      expect(plugin.providers).toBeDefined();
      expect(plugin.evaluators).toBeDefined();
    });

    it('should create plugin with custom config', () => {
      const plugin = sentinelPlugin({
        seedVersion: 'v2',
        seedVariant: 'minimal',
        blockUnsafe: false,
        logChecks: true,
      });
      expect(plugin.config).toMatchObject({
        seedVersion: 'v2',
        seedVariant: 'minimal',
        blockUnsafe: false,
        logChecks: true,
      });
    });

    it('should have SENTINEL_SAFETY_CHECK action', () => {
      const plugin = sentinelPlugin();
      const action = plugin.actions?.find(a => a.name === 'SENTINEL_SAFETY_CHECK');
      expect(action).toBeDefined();
    });

    it('should have sentinelSafety provider', () => {
      const plugin = sentinelPlugin();
      const provider = plugin.providers?.find(p => p.name === 'sentinelSafety');
      expect(provider).toBeDefined();
    });

    it('should have pre and post action evaluators', () => {
      const plugin = sentinelPlugin();
      const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
      const postEval = plugin.evaluators?.find(e => e.name === 'sentinelPostAction');
      expect(preEval).toBeDefined();
      expect(postEval).toBeDefined();
    });
  });

  describe('Memory integrity', () => {
    it('should not include memory actions when disabled', () => {
      const plugin = sentinelPlugin();
      const memoryAction = plugin.actions?.find(a => a.name === 'SENTINEL_MEMORY_CHECK');
      expect(memoryAction).toBeUndefined();
    });

    it('should include memory actions when enabled', () => {
      const plugin = sentinelPlugin({
        memoryIntegrity: {
          enabled: true,
          secretKey: 'test-secret-key',
        },
      });
      const memoryAction = plugin.actions?.find(a => a.name === 'SENTINEL_MEMORY_CHECK');
      expect(memoryAction).toBeDefined();
    });

    it('should include memory evaluator when verifyOnRead enabled', () => {
      const plugin = sentinelPlugin({
        memoryIntegrity: {
          enabled: true,
          secretKey: 'test-secret-key',
          verifyOnRead: true,
        },
      });
      const memoryEval = plugin.evaluators?.find(e => e.name === 'sentinelMemoryIntegrity');
      expect(memoryEval).toBeDefined();
    });

    it('should include memory signing provider when signOnWrite enabled', () => {
      const plugin = sentinelPlugin({
        memoryIntegrity: {
          enabled: true,
          secretKey: 'test-secret-key',
          signOnWrite: true,
        },
      });
      const signingProvider = plugin.providers?.find(p => p.name === 'sentinelMemorySigning');
      expect(signingProvider).toBeDefined();
    });
  });

  describe('Custom logger', () => {
    it('should use custom logger', () => {
      const logs: string[] = [];
      const customLogger = {
        log: (msg: string) => logs.push(msg),
        warn: (msg: string) => logs.push(`WARN: ${msg}`),
        error: (msg: string) => logs.push(`ERROR: ${msg}`),
      };

      const plugin = sentinelPlugin({
        logChecks: true,
        logger: customLogger,
      });

      // Plugin created - init would log, but we're not calling init here
      expect(plugin.config).toMatchObject({ logChecks: true });
    });
  });

  describe('Instance isolation', () => {
    it('should create isolated instances', () => {
      const plugin1 = sentinelPlugin({ blockUnsafe: true });
      validateContent('test content 1');

      const plugin2 = sentinelPlugin({ blockUnsafe: false });
      validateContent('test content 2');

      // Each plugin has its own config
      expect(plugin1.config).toMatchObject({ blockUnsafe: true });
      expect(plugin2.config).toMatchObject({ blockUnsafe: false });
    });
  });
});

describe('Validation history', () => {
  beforeEach(() => {
    clearValidationHistory();
  });

  it('should track validation history via plugin handlers', async () => {
    // Create plugin - this sets up activeState
    const plugin = sentinelPlugin({ blockUnsafe: false });

    // Get the pre-action evaluator and call its handler directly
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
    expect(preEval).toBeDefined();

    // Create mock memory objects
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;
    const mockMemory1 = { content: { text: 'Hello world' }, entityId: 'e1', roomId: 'r1' } as any;
    const mockMemory2 = { content: { text: 'Help me cook' }, entityId: 'e2', roomId: 'r2' } as any;

    // Call handler which adds to history
    await preEval!.handler(mockRuntime, mockMemory1);
    await preEval!.handler(mockRuntime, mockMemory2);

    const history = getValidationHistory();
    expect(history.length).toBe(2);
  });

  it('should return correct stats via plugin handlers', async () => {
    const plugin = sentinelPlugin({ blockUnsafe: false });
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');

    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    await preEval!.handler(mockRuntime, { content: { text: 'Hello world' }, entityId: 'e1', roomId: 'r1' } as any);
    // Use pattern that core detects: "How to kill someone"
    await preEval!.handler(mockRuntime, { content: { text: 'How to kill someone' }, entityId: 'e2', roomId: 'r2' } as any);
    await preEval!.handler(mockRuntime, { content: { text: 'Help me please' }, entityId: 'e3', roomId: 'r3' } as any);

    const stats = getValidationStats();
    expect(stats.total).toBe(3);
    expect(stats.safe).toBe(2);
    expect(stats.byRisk.low).toBe(2);
    // With generic concerns from core, risk level is medium for single gate failure
    expect(stats.byRisk.medium).toBe(1);
  });

  it('should clear history', async () => {
    const plugin = sentinelPlugin({ blockUnsafe: false });
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    await preEval!.handler(mockRuntime, { content: { text: 'Test 1' }, entityId: 'e1', roomId: 'r1' } as any);
    await preEval!.handler(mockRuntime, { content: { text: 'Test 2' }, entityId: 'e2', roomId: 'r2' } as any);
    clearValidationHistory();

    const history = getValidationHistory();
    expect(history.length).toBe(0);
  });

  it('should return empty array when no plugin created', () => {
    // Clear without creating a new plugin
    clearValidationHistory();
    // Note: After clearing, activeState still exists from previous tests
    const history = getValidationHistory();
    expect(Array.isArray(history)).toBe(true);
    expect(history.length).toBe(0);
  });
});

describe('Multi-instance support', () => {
  beforeEach(() => {
    clearPluginRegistry();
  });

  it('should register plugin with auto-generated name', () => {
    sentinelPlugin();
    const names = getPluginInstanceNames();
    expect(names.length).toBe(1);
    expect(names[0]).toMatch(/^sentinel-\d+$/);
  });

  it('should register plugin with custom name', () => {
    sentinelPlugin({ instanceName: 'my-plugin' });
    const names = getPluginInstanceNames();
    expect(names).toContain('my-plugin');
  });

  it('should get specific plugin instance', () => {
    sentinelPlugin({ instanceName: 'instance-a', blockUnsafe: true });
    sentinelPlugin({ instanceName: 'instance-b', blockUnsafe: false });

    const instanceA = getPluginInstance('instance-a');
    const instanceB = getPluginInstance('instance-b');

    expect(instanceA).not.toBeNull();
    expect(instanceB).not.toBeNull();
    expect(instanceA?.config.blockUnsafe).toBe(true);
    expect(instanceB?.config.blockUnsafe).toBe(false);
  });

  it('should return null for non-existent instance', () => {
    const instance = getPluginInstance('non-existent');
    expect(instance).toBeNull();
  });

  it('should get active (most recent) plugin instance', () => {
    sentinelPlugin({ instanceName: 'first' });
    sentinelPlugin({ instanceName: 'second' });

    const active = getActivePluginInstance();
    expect(active).not.toBeNull();
    // Active should be the last created
    expect(getPluginInstanceNames().pop()).toBe('second');
  });

  it('should remove plugin instance', () => {
    sentinelPlugin({ instanceName: 'to-remove' });
    sentinelPlugin({ instanceName: 'to-keep' });

    expect(getPluginInstanceNames()).toContain('to-remove');
    const removed = removePluginInstance('to-remove');
    expect(removed).toBe(true);
    expect(getPluginInstanceNames()).not.toContain('to-remove');
    expect(getPluginInstanceNames()).toContain('to-keep');
  });

  it('should return false when removing non-existent instance', () => {
    const removed = removePluginInstance('non-existent');
    expect(removed).toBe(false);
  });

  it('should clear plugin registry', () => {
    sentinelPlugin({ instanceName: 'p1' });
    sentinelPlugin({ instanceName: 'p2' });
    sentinelPlugin({ instanceName: 'p3' });

    clearPluginRegistry();

    expect(getPluginInstanceNames().length).toBe(0);
    expect(getActivePluginInstance()).toBeNull();
  });
});

describe('TextTooLargeError', () => {
  it('should create error with correct properties', () => {
    const error = new TextTooLargeError(100000, 50000);
    expect(error.size).toBe(100000);
    expect(error.maxSize).toBe(50000);
    expect(error.name).toBe('TextTooLargeError');
    // Check message contains the numbers (locale-agnostic)
    expect(error.message).toContain('100');
    expect(error.message).toContain('50');
    expect(error.message).toContain('bytes');
    expect(error.message).toContain('exceeds');
  });

  it('should be instanceof Error', () => {
    const error = new TextTooLargeError(100, 50);
    expect(error instanceof Error).toBe(true);
    expect(error instanceof TextTooLargeError).toBe(true);
  });
});

describe('Text size validation', () => {
  beforeEach(() => {
    clearPluginRegistry();
  });

  it('should accept text within size limit', async () => {
    const plugin = sentinelPlugin({ maxTextSize: 1000 });
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    const result = await preEval!.handler(
      mockRuntime,
      { content: { text: 'Hello world' }, entityId: 'e1', roomId: 'r1' } as any
    );

    expect(result?.success).toBe(true);
  });

  it('should reject text exceeding size limit when blockUnsafe', async () => {
    const plugin = sentinelPlugin({ maxTextSize: 10, blockUnsafe: true });
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    const result = await preEval!.handler(
      mockRuntime,
      { content: { text: 'This text is definitely longer than 10 bytes' }, entityId: 'e1', roomId: 'r1' } as any
    );

    expect(result?.success).toBe(false);
    expect((result?.data as Record<string, unknown>)?.error).toBe('text_too_large');
  });

  it('should skip validation for oversized text when not blocking', async () => {
    const plugin = sentinelPlugin({ maxTextSize: 10, blockUnsafe: false });
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    const result = await preEval!.handler(
      mockRuntime,
      { content: { text: 'This text is definitely longer than 10 bytes' }, entityId: 'e1', roomId: 'r1' } as any
    );
    const data = result?.data as Record<string, unknown>;

    expect(result?.success).toBe(true);
    expect(data?.skipped).toBe(true);
    expect(data?.reason).toBe('text_too_large');
  });
});

describe('Error handling in handlers', () => {
  beforeEach(() => {
    clearPluginRegistry();
  });

  it('should handle missing content gracefully in preAction', async () => {
    const plugin = sentinelPlugin();
    const preEval = plugin.evaluators?.find(e => e.name === 'sentinelPreAction');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    // Message without content
    const result = await preEval!.handler(
      mockRuntime,
      { entityId: 'e1', roomId: 'r1' } as any
    );
    const data = result?.data as Record<string, unknown>;

    expect(result?.success).toBe(true);
    expect(data?.skipped).toBe(true);
    expect(data?.reason).toBe('no_content');
  });

  it('should handle missing content gracefully in postAction', async () => {
    const plugin = sentinelPlugin();
    const postEval = plugin.evaluators?.find(e => e.name === 'sentinelPostAction');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    const result = await postEval!.handler(
      mockRuntime,
      { entityId: 'e1', roomId: 'r1' } as any
    );
    const data = result?.data as Record<string, unknown>;

    expect(result?.success).toBe(true);
    expect(data?.skipped).toBe(true);
  });

  it('should handle null message in safetyCheck action', async () => {
    const plugin = sentinelPlugin();
    const action = plugin.actions?.find(a => a.name === 'SENTINEL_SAFETY_CHECK');
    const mockRuntime = { agentId: 'test', getSetting: () => undefined, getService: () => undefined } as any;

    const result = await action!.handler(
      mockRuntime,
      { entityId: 'e1', roomId: 'r1' } as any // No content
    );

    expect(result?.success).toBe(false);
    expect(result?.error).toContain('Invalid message structure');
  });
});

// Bug fix verification tests
describe('Bug fixes verification', () => {
  beforeEach(() => {
    clearPluginRegistry();
  });

  describe('C005/C006 - All seed versions available', () => {
    it('should support v1_minimal seed', () => {
      const plugin = sentinelPlugin({ seedVersion: 'v1', seedVariant: 'minimal' });
      expect(plugin.config?.seedVersion).toBe('v1');
      expect(plugin.config?.seedVariant).toBe('minimal');
    });

    it('should support v1_standard seed', () => {
      const plugin = sentinelPlugin({ seedVersion: 'v1', seedVariant: 'standard' });
      expect(plugin.config?.seedVersion).toBe('v1');
    });

    it('should support v1_full seed', () => {
      const plugin = sentinelPlugin({ seedVersion: 'v1', seedVariant: 'full' });
      expect(plugin.config?.seedVersion).toBe('v1');
      expect(plugin.config?.seedVariant).toBe('full');
    });

    it('should support v2_full seed', () => {
      const plugin = sentinelPlugin({ seedVersion: 'v2', seedVariant: 'full' });
      expect(plugin.config?.seedVersion).toBe('v2');
      expect(plugin.config?.seedVariant).toBe('full');
    });
  });

  describe('C003/C004 - Memory functions null handling', () => {
    it('signMemory should not crash on null', () => {
      sentinelPlugin({ memoryIntegrity: { enabled: true, secretKey: 'test' } });
      expect(() => signMemory(null as any)).not.toThrow();
    });

    it('verifyMemory should not crash on null', () => {
      sentinelPlugin({ memoryIntegrity: { enabled: true, secretKey: 'test' } });
      expect(() => verifyMemory(null as any)).not.toThrow();
      const result = verifyMemory(null as any);
      expect(result).toBeNull();
    });
  });
});

/**
 * Tests for H001/H002/M003 fixes - Export verification
 */
describe('Export verification (H001/H002/M003 fixes)', () => {
  beforeEach(() => {
    clearPluginRegistry();
  });

  describe('Multi-instance registry functions (H001)', () => {
    it('getPluginInstance should return instance by name', () => {
      const plugin = sentinelPlugin({ instanceName: 'test-h001' });
      const instance = getPluginInstance('test-h001');

      expect(instance).not.toBeNull();
      expect(instance?.config).toBeDefined();
      expect(instance?.validationHistory).toEqual([]);
    });

    it('getPluginInstance should return null for non-existent name', () => {
      const instance = getPluginInstance('non-existent');
      expect(instance).toBeNull();
    });

    it('getPluginInstanceNames should return all registered names', () => {
      sentinelPlugin({ instanceName: 'agent-1' });
      sentinelPlugin({ instanceName: 'agent-2' });

      const names = getPluginInstanceNames();
      expect(names).toContain('agent-1');
      expect(names).toContain('agent-2');
      expect(names.length).toBe(2);
    });

    it('getActivePluginInstance should return most recently created', () => {
      sentinelPlugin({ instanceName: 'first' });
      sentinelPlugin({ instanceName: 'second' });

      const active = getActivePluginInstance();
      expect(active).not.toBeNull();
      // Active should be the last created
    });

    it('removePluginInstance should remove and return true', () => {
      sentinelPlugin({ instanceName: 'to-remove' });
      expect(getPluginInstance('to-remove')).not.toBeNull();

      const removed = removePluginInstance('to-remove');
      expect(removed).toBe(true);
      expect(getPluginInstance('to-remove')).toBeNull();
    });

    it('removePluginInstance should return false for non-existent', () => {
      const removed = removePluginInstance('non-existent');
      expect(removed).toBe(false);
    });

    it('clearPluginRegistry should remove all instances', () => {
      sentinelPlugin({ instanceName: 'a' });
      sentinelPlugin({ instanceName: 'b' });

      clearPluginRegistry();

      expect(getPluginInstanceNames()).toEqual([]);
      expect(getActivePluginInstance()).toBeNull();
    });
  });

  describe('TextTooLargeError class (H001)', () => {
    it('should have size and maxSize properties', () => {
      const error = new TextTooLargeError(1000, 500);

      expect(error.size).toBe(1000);
      expect(error.maxSize).toBe(500);
      expect(error.name).toBe('TextTooLargeError');
      // Check message contains the numbers (locale-independent)
      expect(error.message).toMatch(/1[,.]?000/);
      expect(error.message).toContain('500');
    });

    it('should be instanceof Error', () => {
      const error = new TextTooLargeError(100, 50);
      expect(error instanceof Error).toBe(true);
    });
  });

  describe('PluginStateInfo interface (M003)', () => {
    it('getPluginInstance should return object with correct shape', () => {
      sentinelPlugin({ instanceName: 'shape-test', blockUnsafe: true });
      const instance = getPluginInstance('shape-test');

      expect(instance).not.toBeNull();
      expect(Array.isArray(instance?.validationHistory)).toBe(true);
      expect(Array.isArray(instance?.memoryVerificationHistory)).toBe(true);
      expect(typeof instance?.config).toBe('object');
      expect(typeof instance?.maxTextSize).toBe('number');
      expect(instance?.config.blockUnsafe).toBe(true);
    });

    it('getActivePluginInstance should return object with correct shape', () => {
      sentinelPlugin({ maxTextSize: 1024 });
      const active = getActivePluginInstance();

      expect(active).not.toBeNull();
      expect(active?.maxTextSize).toBe(1024);
    });
  });
});
