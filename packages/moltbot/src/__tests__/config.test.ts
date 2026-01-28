/**
 * Configuration Module Tests
 *
 * Tests for defaults, levels, and parser functionality.
 */

import { describe, it, expect } from 'vitest';

describe('Config: Defaults', () => {
  it('should export DEFAULT_CONFIG with correct values', async () => {
    const { DEFAULT_CONFIG } = await import('../config/defaults');

    expect(DEFAULT_CONFIG.level).toBe('watch');
    expect(DEFAULT_CONFIG.alerts?.enabled).toBe(true);
    expect(DEFAULT_CONFIG.ignorePatterns).toEqual([]);
    expect(DEFAULT_CONFIG.trustedTools).toEqual([]);
    expect(DEFAULT_CONFIG.dangerousTools).toEqual([]);
  });

  it('should return fresh copy from getDefaultConfig', async () => {
    const { getDefaultConfig } = await import('../config/defaults');

    const config1 = getDefaultConfig();
    const config2 = getDefaultConfig();

    // Should be equal in value
    expect(config1.level).toBe(config2.level);

    // But different objects (not same reference)
    expect(config1).not.toBe(config2);
    expect(config1.alerts).not.toBe(config2.alerts);
  });
});

describe('Config: Levels', () => {
  it('should export all four level presets', async () => {
    const { OFF_LEVEL, WATCH_LEVEL, GUARD_LEVEL, SHIELD_LEVEL, LEVELS } =
      await import('../config/levels');

    expect(LEVELS.off).toBe(OFF_LEVEL);
    expect(LEVELS.watch).toBe(WATCH_LEVEL);
    expect(LEVELS.guard).toBe(GUARD_LEVEL);
    expect(LEVELS.shield).toBe(SHIELD_LEVEL);
  });

  it('OFF_LEVEL should disable everything', async () => {
    const { OFF_LEVEL } = await import('../config/levels');

    expect(OFF_LEVEL.level).toBe('off');
    expect(OFF_LEVEL.seedTemplate).toBe('none');
    expect(OFF_LEVEL.logLevel).toBe('none');

    // All blocking disabled
    expect(OFF_LEVEL.blocking.dataLeaks).toBe(false);
    expect(OFF_LEVEL.blocking.destructiveCommands).toBe(false);
    expect(OFF_LEVEL.blocking.systemPaths).toBe(false);
    expect(OFF_LEVEL.blocking.suspiciousUrls).toBe(false);
    expect(OFF_LEVEL.blocking.injectionCompliance).toBe(false);

    // All alerting disabled
    expect(OFF_LEVEL.alerting.highThreatInput).toBe(false);
    expect(OFF_LEVEL.alerting.blockedActions).toBe(false);
    expect(OFF_LEVEL.alerting.promptInjection).toBe(false);
    expect(OFF_LEVEL.alerting.sessionAnomalies).toBe(false);
  });

  it('WATCH_LEVEL should monitor but never block', async () => {
    const { WATCH_LEVEL } = await import('../config/levels');

    expect(WATCH_LEVEL.level).toBe('watch');
    expect(WATCH_LEVEL.seedTemplate).toBe('standard');
    expect(WATCH_LEVEL.logLevel).toBe('all');

    // All blocking disabled (never block)
    expect(WATCH_LEVEL.blocking.dataLeaks).toBe(false);
    expect(WATCH_LEVEL.blocking.destructiveCommands).toBe(false);
    expect(WATCH_LEVEL.blocking.systemPaths).toBe(false);

    // Alerting enabled for threats
    expect(WATCH_LEVEL.alerting.highThreatInput).toBe(true);
    expect(WATCH_LEVEL.alerting.promptInjection).toBe(true);
    expect(WATCH_LEVEL.alerting.sessionAnomalies).toBe(true);
  });

  it('GUARD_LEVEL should block critical threats', async () => {
    const { GUARD_LEVEL } = await import('../config/levels');

    expect(GUARD_LEVEL.level).toBe('guard');

    // Block critical threats
    expect(GUARD_LEVEL.blocking.dataLeaks).toBe(true);
    expect(GUARD_LEVEL.blocking.destructiveCommands).toBe(true);
    expect(GUARD_LEVEL.blocking.systemPaths).toBe(true);

    // But not everything
    expect(GUARD_LEVEL.blocking.suspiciousUrls).toBe(false);
    expect(GUARD_LEVEL.blocking.injectionCompliance).toBe(false);
  });

  it('SHIELD_LEVEL should block everything', async () => {
    const { SHIELD_LEVEL } = await import('../config/levels');

    expect(SHIELD_LEVEL.level).toBe('shield');
    expect(SHIELD_LEVEL.seedTemplate).toBe('strict');

    // All blocking enabled
    expect(SHIELD_LEVEL.blocking.dataLeaks).toBe(true);
    expect(SHIELD_LEVEL.blocking.destructiveCommands).toBe(true);
    expect(SHIELD_LEVEL.blocking.systemPaths).toBe(true);
    expect(SHIELD_LEVEL.blocking.suspiciousUrls).toBe(true);
    expect(SHIELD_LEVEL.blocking.injectionCompliance).toBe(true);
  });

  it('isValidLevel should validate level strings', async () => {
    const { isValidLevel } = await import('../config/levels');

    expect(isValidLevel('off')).toBe(true);
    expect(isValidLevel('watch')).toBe(true);
    expect(isValidLevel('guard')).toBe(true);
    expect(isValidLevel('shield')).toBe(true);

    expect(isValidLevel('invalid')).toBe(false);
    expect(isValidLevel('')).toBe(false);
    expect(isValidLevel(null)).toBe(false);
    expect(isValidLevel(undefined)).toBe(false);
    expect(isValidLevel(123)).toBe(false);
  });

  it('compareLevels should order correctly', async () => {
    const { compareLevels } = await import('../config/levels');

    // Same level
    expect(compareLevels('watch', 'watch')).toBe(0);

    // Higher level
    expect(compareLevels('shield', 'watch')).toBeGreaterThan(0);
    expect(compareLevels('guard', 'watch')).toBeGreaterThan(0);

    // Lower level
    expect(compareLevels('watch', 'shield')).toBeLessThan(0);
    expect(compareLevels('off', 'watch')).toBeLessThan(0);
  });

  it('isMoreProtective should compare levels correctly', async () => {
    const { isMoreProtective } = await import('../config/levels');

    expect(isMoreProtective('shield', 'guard')).toBe(true);
    expect(isMoreProtective('guard', 'watch')).toBe(true);
    expect(isMoreProtective('watch', 'off')).toBe(true);

    expect(isMoreProtective('watch', 'shield')).toBe(false);
    expect(isMoreProtective('guard', 'guard')).toBe(false);
  });
});

describe('Config: Parser', () => {
  it('parseConfig should apply defaults for empty config', async () => {
    const { parseConfig } = await import('../config/parser');

    const config = parseConfig({});

    expect(config.level).toBe('watch');
    expect(config.alerts?.enabled).toBe(true);
    expect(config.ignorePatterns).toEqual([]);
    expect(config.trustedTools).toEqual([]);
    expect(config.dangerousTools).toEqual([]);
  });

  it('parseConfig should preserve valid user values', async () => {
    const { parseConfig } = await import('../config/parser');

    const config = parseConfig({
      level: 'shield',
      alerts: { enabled: false, webhook: 'https://example.com/webhook' },
      ignorePatterns: ['test-*'],
      trustedTools: ['cat', 'ls'],
      dangerousTools: ['rm'],
    });

    expect(config.level).toBe('shield');
    expect(config.alerts?.enabled).toBe(false);
    expect(config.alerts?.webhook).toBe('https://example.com/webhook');
    expect(config.ignorePatterns).toEqual(['test-*']);
    expect(config.trustedTools).toEqual(['cat', 'ls']);
    expect(config.dangerousTools).toEqual(['rm']);
  });

  it('parseConfig should fallback to default for invalid level', async () => {
    const { parseConfig } = await import('../config/parser');

    const config = parseConfig({ level: 'invalid' as any });

    expect(config.level).toBe('watch');
  });

  it('parseConfig should filter non-string items from arrays', async () => {
    const { parseConfig } = await import('../config/parser');

    const config = parseConfig({
      ignorePatterns: ['valid', 123, null, 'also-valid'] as any,
      trustedTools: [true, 'bash', undefined] as any,
    });

    expect(config.ignorePatterns).toEqual(['valid', 'also-valid']);
    expect(config.trustedTools).toEqual(['bash']);
  });

  it('parseConfig should handle single string as array', async () => {
    const { parseConfig } = await import('../config/parser');

    const config = parseConfig({
      ignorePatterns: 'single-pattern' as any,
    });

    expect(config.ignorePatterns).toEqual(['single-pattern']);
  });

  it('getLevelConfig should return base level without custom', async () => {
    const { getLevelConfig, WATCH_LEVEL } = await import('../config/parser');
    const { WATCH_LEVEL: WATCH_LEVEL_DIRECT } = await import('../config/levels');

    const config = getLevelConfig('watch');

    expect(config.level).toBe('watch');
    expect(config.blocking).toEqual(WATCH_LEVEL_DIRECT.blocking);
    expect(config.alerting).toEqual(WATCH_LEVEL_DIRECT.alerting);
  });

  it('getLevelConfig should merge custom overrides', async () => {
    const { getLevelConfig } = await import('../config/parser');

    const config = getLevelConfig('watch', {
      blocking: { dataLeaks: true },
      seedTemplate: 'strict',
    });

    expect(config.level).toBe('watch');
    expect(config.blocking.dataLeaks).toBe(true);
    expect(config.blocking.destructiveCommands).toBe(false); // Not overridden
    expect(config.seedTemplate).toBe('strict');
  });

  it('validateConfig should return errors for invalid config', async () => {
    const { validateConfig } = await import('../config/parser');

    const errors = validateConfig({
      level: 'invalid' as any,
      alerts: { enabled: true, webhook: 'not-a-url' },
      ignorePatterns: 'not-an-array' as any,
      trustedTools: [],
      dangerousTools: [],
    });

    expect(errors.length).toBeGreaterThan(0);
    expect(errors.some(e => e.includes('level'))).toBe(true);
    expect(errors.some(e => e.includes('webhook'))).toBe(true);
  });

  it('validateConfig should return empty array for valid config', async () => {
    const { validateConfig, parseConfig } = await import('../config/parser');

    const config = parseConfig({ level: 'guard' });
    const errors = validateConfig(config);

    expect(errors).toEqual([]);
  });
});
