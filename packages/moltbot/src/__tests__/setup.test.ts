/**
 * Setup tests - Validate package structure and exports.
 */

import { describe, it, expect } from 'vitest';

describe('@sentinelseed/moltbot', () => {
  describe('Package Structure', () => {
    it('should export createSentinelHooks', async () => {
      const { createSentinelHooks } = await import('../index');
      expect(typeof createSentinelHooks).toBe('function');
    });

    it('should export level presets', async () => {
      const { LEVELS, WATCH_LEVEL, GUARD_LEVEL, SHIELD_LEVEL, OFF_LEVEL } =
        await import('../index');

      expect(LEVELS).toBeDefined();
      expect(WATCH_LEVEL).toBeDefined();
      expect(GUARD_LEVEL).toBeDefined();
      expect(SHIELD_LEVEL).toBeDefined();
      expect(OFF_LEVEL).toBeDefined();
    });

    it('should export configuration functions', async () => {
      const { parseConfig, getLevelConfig, getDefaultConfig } =
        await import('../index');

      expect(typeof parseConfig).toBe('function');
      expect(typeof getLevelConfig).toBe('function');
      expect(typeof getDefaultConfig).toBe('function');
    });

    it('should export validators', async () => {
      const { validateOutput, validateTool, analyzeInput } =
        await import('../index');

      expect(typeof validateOutput).toBe('function');
      expect(typeof validateTool).toBe('function');
      expect(typeof analyzeInput).toBe('function');
    });

    it('should export version metadata', async () => {
      const { VERSION, PACKAGE_NAME, MOLTBOT_VERSION_RANGE } =
        await import('../index');

      expect(VERSION).toBe('0.1.0');
      expect(PACKAGE_NAME).toBe('@sentinelseed/moltbot');
      expect(MOLTBOT_VERSION_RANGE).toBe('>=1.0.0');
    });

    it('should export utility functions', async () => {
      const { getAvailableLevels, isValidLevel } = await import('../index');

      expect(typeof getAvailableLevels).toBe('function');
      expect(typeof isValidLevel).toBe('function');
    });
  });

  describe('Level Presets', () => {
    it('should have correct structure for WATCH_LEVEL', async () => {
      const { WATCH_LEVEL } = await import('../index');

      expect(WATCH_LEVEL.level).toBe('watch');
      expect(WATCH_LEVEL.blocking.dataLeaks).toBe(false);
      expect(WATCH_LEVEL.blocking.destructiveCommands).toBe(false);
      expect(WATCH_LEVEL.alerting.highThreatInput).toBe(true);
      expect(WATCH_LEVEL.seedTemplate).toBe('standard');
    });

    it('should have correct structure for GUARD_LEVEL', async () => {
      const { GUARD_LEVEL } = await import('../index');

      expect(GUARD_LEVEL.level).toBe('guard');
      expect(GUARD_LEVEL.blocking.dataLeaks).toBe(true);
      expect(GUARD_LEVEL.blocking.destructiveCommands).toBe(true);
      expect(GUARD_LEVEL.blocking.suspiciousUrls).toBe(false);
    });

    it('should have correct structure for SHIELD_LEVEL', async () => {
      const { SHIELD_LEVEL } = await import('../index');

      expect(SHIELD_LEVEL.level).toBe('shield');
      expect(SHIELD_LEVEL.blocking.dataLeaks).toBe(true);
      expect(SHIELD_LEVEL.blocking.suspiciousUrls).toBe(true);
      expect(SHIELD_LEVEL.blocking.injectionCompliance).toBe(true);
      expect(SHIELD_LEVEL.seedTemplate).toBe('strict');
    });

    it('should have OFF_LEVEL with all disabled', async () => {
      const { OFF_LEVEL } = await import('../index');

      expect(OFF_LEVEL.level).toBe('off');
      expect(OFF_LEVEL.blocking.dataLeaks).toBe(false);
      expect(OFF_LEVEL.alerting.highThreatInput).toBe(false);
      expect(OFF_LEVEL.seedTemplate).toBe('none');
      expect(OFF_LEVEL.logLevel).toBe('none');
    });
  });

  describe('Configuration', () => {
    it('should parse empty config with defaults', async () => {
      const { parseConfig } = await import('../index');

      const config = parseConfig({});

      expect(config.level).toBe('watch');
      expect(config.alerts?.enabled).toBe(true);
      expect(config.ignorePatterns).toEqual([]);
      expect(config.trustedTools).toEqual([]);
    });

    it('should parse config with custom level', async () => {
      const { parseConfig } = await import('../index');

      const config = parseConfig({ level: 'guard' });

      expect(config.level).toBe('guard');
    });

    it('should get level config with custom overrides', async () => {
      const { getLevelConfig } = await import('../index');

      const config = getLevelConfig('watch', {
        blocking: { dataLeaks: true },
      });

      expect(config.level).toBe('watch');
      expect(config.blocking.dataLeaks).toBe(true);
      expect(config.blocking.destructiveCommands).toBe(false);
    });
  });

  describe('Hooks Factory', () => {
    it('should create hooks with default config', async () => {
      const { createSentinelHooks } = await import('../index');

      const hooks = createSentinelHooks({});

      expect(hooks).toBeDefined();
      expect(typeof hooks.messageReceived).toBe('function');
      expect(typeof hooks.beforeAgentStart).toBe('function');
      expect(typeof hooks.messageSending).toBe('function');
      expect(typeof hooks.beforeToolCall).toBe('function');
      expect(typeof hooks.agentEnd).toBe('function');
    });

    it('should create hooks with custom level', async () => {
      const { createSentinelHooks } = await import('../index');

      const hooks = createSentinelHooks({ level: 'shield' });

      expect(hooks).toBeDefined();
    });
  });

  describe('Validators (Placeholders)', () => {
    it('should validate output (placeholder returns safe)', async () => {
      const { validateOutput, WATCH_LEVEL } = await import('../index');

      const result = await validateOutput('test content', WATCH_LEVEL);

      expect(result.safe).toBe(true);
      expect(result.shouldBlock).toBe(false);
      expect(result.issues).toEqual([]);
    });

    it('should validate tool (placeholder returns safe)', async () => {
      const { validateTool, WATCH_LEVEL } = await import('../index');

      const result = await validateTool('bash', { command: 'ls' }, WATCH_LEVEL);

      expect(result.safe).toBe(true);
      expect(result.shouldBlock).toBe(false);
    });

    it('should analyze input (placeholder returns no threats)', async () => {
      const { analyzeInput, WATCH_LEVEL } = await import('../index');

      const result = await analyzeInput('hello world', WATCH_LEVEL);

      expect(result.threatLevel).toBe(0);
      expect(result.isPromptInjection).toBe(false);
      expect(result.isJailbreakAttempt).toBe(false);
    });
  });

  describe('Utility Functions', () => {
    it('should return available levels', async () => {
      const { getAvailableLevels } = await import('../index');

      const levels = getAvailableLevels();

      expect(levels).toEqual(['off', 'watch', 'guard', 'shield']);
    });

    it('should validate level strings', async () => {
      const { isValidLevel } = await import('../index');

      expect(isValidLevel('watch')).toBe(true);
      expect(isValidLevel('guard')).toBe(true);
      expect(isValidLevel('shield')).toBe(true);
      expect(isValidLevel('off')).toBe(true);
      expect(isValidLevel('invalid')).toBe(false);
      expect(isValidLevel('')).toBe(false);
    });
  });
});
