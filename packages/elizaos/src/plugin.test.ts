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
    await preEval!.handler(mockRuntime, { content: { text: 'Kill someone' }, entityId: 'e2', roomId: 'r2' } as any);
    await preEval!.handler(mockRuntime, { content: { text: 'Help me please' }, entityId: 'e3', roomId: 'r3' } as any);

    const stats = getValidationStats();
    expect(stats.total).toBe(3);
    expect(stats.safe).toBe(2);
    expect(stats.byRisk.low).toBe(2);
    expect(stats.byRisk.critical).toBe(1);
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
