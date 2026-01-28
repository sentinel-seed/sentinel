/**
 * Internal Modules Tests
 *
 * Tests for logger, metrics, and pattern registry functionality.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('Internal: Logger', () => {
  beforeEach(async () => {
    const { resetLogger, configureLogger } = await import('../internal/logger');
    resetLogger();
    configureLogger({ level: 'debug', enabled: true });
  });

  afterEach(async () => {
    const { resetLogger } = await import('../internal/logger');
    resetLogger();
  });

  it('should log messages at appropriate levels', async () => {
    const { logger, configureLogger } = await import('../internal/logger');
    const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});

    configureLogger({ level: 'debug', enabled: true });
    logger.debug('Test message');

    expect(consoleSpy).toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('should respect log level filtering', async () => {
    const { logger, configureLogger } = await import('../internal/logger');
    const consoleSpy = vi.spyOn(console, 'debug').mockImplementation(() => {});

    configureLogger({ level: 'warn', enabled: true });
    logger.debug('Should not appear');

    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('should support custom logger injection', async () => {
    const { logger, setLogger, resetLogger } = await import('../internal/logger');
    const customLog = vi.fn();

    setLogger({
      debug: customLog,
      info: customLog,
      warn: customLog,
      error: customLog,
    });

    logger.info('Custom message');
    expect(customLog).toHaveBeenCalledWith('Custom message', undefined);

    resetLogger();
  });

  it('should create child loggers with context', async () => {
    const { createChildLogger, setLogger } = await import('../internal/logger');
    const customLog = vi.fn();

    setLogger({
      debug: customLog,
      info: customLog,
      warn: customLog,
      error: customLog,
    });

    const child = createChildLogger('test-operation');
    child.info('Child message');

    expect(customLog).toHaveBeenCalledWith(
      'Child message',
      expect.objectContaining({ operation: 'test-operation' })
    );
  });

  it('should format context safely', async () => {
    const { logger, setLogger } = await import('../internal/logger');
    const customLog = vi.fn();

    setLogger({
      debug: customLog,
      info: customLog,
      warn: customLog,
      error: customLog,
    });

    // Should truncate long strings
    logger.info('Test', {
      longValue: 'a'.repeat(100),
    });

    expect(customLog).toHaveBeenCalled();
  });

  it('should handle errors in context', async () => {
    const { logger, setLogger } = await import('../internal/logger');
    const customLog = vi.fn();

    setLogger({
      debug: customLog,
      info: customLog,
      warn: customLog,
      error: customLog,
    });

    logger.error('Error occurred', {
      error: new Error('Test error'),
    });

    expect(customLog).toHaveBeenCalled();
  });

  it('should respect enabled flag', async () => {
    const { logger, configureLogger } = await import('../internal/logger');
    const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    configureLogger({ enabled: false });
    logger.error('Should not appear');

    expect(consoleSpy).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it('getLoggerConfig should return current config', async () => {
    const { getLoggerConfig, configureLogger } = await import('../internal/logger');

    configureLogger({ level: 'info', prefix: '[test]' });
    const config = getLoggerConfig();

    expect(config.level).toBe('info');
    expect(config.prefix).toBe('[test]');
  });

  it('logValidation should log with correct format', async () => {
    const { logValidation, setLogger } = await import('../internal/logger');
    const customLog = vi.fn();

    setLogger({
      debug: customLog,
      info: customLog,
      warn: customLog,
      error: customLog,
    });

    logValidation('output', {
      safe: true,
      blocked: false,
      issueCount: 0,
      riskLevel: 'none',
      durationMs: 10,
    });

    expect(customLog).toHaveBeenCalledWith(
      'output validation passed',
      expect.objectContaining({ operation: 'validate_output' })
    );
  });
});

describe('Internal: Metrics', () => {
  beforeEach(async () => {
    const { resetMetrics } = await import('../internal/metrics');
    resetMetrics();
  });

  it('should record validations', async () => {
    const { metrics, getMetricsSnapshot } = await import('../internal/metrics');

    metrics.recordValidation('output', 10, true, false);
    metrics.recordValidation('output', 20, false, true);

    const snapshot = getMetricsSnapshot();
    expect(snapshot.validations.output.count).toBe(2);
    expect(snapshot.validations.output.passed).toBe(1);
    expect(snapshot.validations.output.blocked).toBe(1);
  });

  it('should track timing statistics', async () => {
    const { metrics, getMetricsSnapshot } = await import('../internal/metrics');

    metrics.recordValidation('tool', 5, true, false);
    metrics.recordValidation('tool', 15, true, false);
    metrics.recordValidation('tool', 10, true, false);

    const snapshot = getMetricsSnapshot();
    expect(snapshot.validations.tool.timing.count).toBe(3);
    expect(snapshot.validations.tool.timing.minMs).toBe(5);
    expect(snapshot.validations.tool.timing.maxMs).toBe(15);
    expect(snapshot.validations.tool.timing.totalMs).toBe(30);
  });

  it('should record issues by type and severity', async () => {
    const { metrics, getMetricsSnapshot } = await import('../internal/metrics');

    metrics.recordIssues([
      { type: 'data_leak', severity: 'critical' },
      { type: 'data_leak', severity: 'high' },
      { type: 'destructive_command', severity: 'high' },
    ]);

    const snapshot = getMetricsSnapshot();
    expect(snapshot.issues.total).toBe(3);
    expect(snapshot.issues.byType.data_leak).toBe(2);
    expect(snapshot.issues.byType.destructive_command).toBe(1);
    expect(snapshot.issues.bySeverity.critical).toBe(1);
    expect(snapshot.issues.bySeverity.high).toBe(2);
  });

  it('should record errors', async () => {
    const { metrics, getMetricsSnapshot } = await import('../internal/metrics');

    metrics.recordError('validation');
    metrics.recordError('validation');
    metrics.recordError('pattern');

    const snapshot = getMetricsSnapshot();
    expect(snapshot.errors.validation).toBe(2);
    expect(snapshot.errors.pattern).toBe(1);
  });

  it('getAverageValidationTime should calculate correctly', async () => {
    const { metrics, getAverageValidationTime } = await import('../internal/metrics');

    metrics.recordValidation('input', 10, true, false);
    metrics.recordValidation('input', 20, true, false);
    metrics.recordValidation('input', 30, true, false);

    expect(getAverageValidationTime('input')).toBe(20);
  });

  it('getAverageValidationTime should return 0 for no validations', async () => {
    const { getAverageValidationTime } = await import('../internal/metrics');

    expect(getAverageValidationTime('output')).toBe(0);
  });

  it('getBlockRate should calculate correctly', async () => {
    const { metrics, getBlockRate } = await import('../internal/metrics');

    metrics.recordValidation('tool', 10, true, false);
    metrics.recordValidation('tool', 10, false, true);
    metrics.recordValidation('tool', 10, false, false);
    metrics.recordValidation('tool', 10, false, true);

    expect(getBlockRate('tool')).toBe(0.5); // 2 blocked out of 4
  });

  it('getPassRate should calculate correctly', async () => {
    const { metrics, getPassRate } = await import('../internal/metrics');

    metrics.recordValidation('output', 10, true, false);
    metrics.recordValidation('output', 10, true, false);
    metrics.recordValidation('output', 10, false, true);
    metrics.recordValidation('output', 10, false, false);

    expect(getPassRate('output')).toBe(0.5); // 2 passed out of 4
  });

  it('getMostCommonIssueType should return correct type', async () => {
    const { metrics, getMostCommonIssueType } = await import('../internal/metrics');

    metrics.recordIssues([
      { type: 'data_leak', severity: 'high' },
      { type: 'system_path', severity: 'high' },
      { type: 'system_path', severity: 'high' },
      { type: 'system_path', severity: 'high' },
    ]);

    expect(getMostCommonIssueType()).toBe('system_path');
  });

  it('getMostCommonIssueType should return null for no issues', async () => {
    const { getMostCommonIssueType } = await import('../internal/metrics');

    expect(getMostCommonIssueType()).toBeNull();
  });

  it('getMetricsSummary should return formatted string', async () => {
    const { metrics, getMetricsSummary } = await import('../internal/metrics');

    metrics.recordValidation('output', 10, true, false);
    metrics.recordValidation('tool', 10, false, true);

    const summary = getMetricsSummary();
    expect(summary).toContain('Sentinel Metrics');
    expect(summary).toContain('Output validations');
    expect(summary).toContain('Tool validations');
  });

  it('resetMetrics should clear all data', async () => {
    const { metrics, resetMetrics, getMetricsSnapshot } = await import('../internal/metrics');

    metrics.recordValidation('output', 10, true, false);
    metrics.recordIssues([{ type: 'data_leak', severity: 'high' }]);
    metrics.recordError('validation');

    resetMetrics();

    const snapshot = getMetricsSnapshot();
    expect(snapshot.validations.output.count).toBe(0);
    expect(snapshot.issues.total).toBe(0);
    expect(snapshot.errors.validation).toBe(0);
  });
});

describe('Internal: Pattern Registry', () => {
  beforeEach(async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');
    patternRegistry.reset();
  });

  it('should have built-in dangerous tools', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    expect(patternRegistry.isDangerousTool('rm')).toBe(true);
    expect(patternRegistry.isDangerousTool('format')).toBe(true);
    expect(patternRegistry.isDangerousTool('drop_table')).toBe(true);
    expect(patternRegistry.isDangerousTool('shutdown')).toBe(true);
  });

  it('should have built-in restricted paths', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    expect(patternRegistry.isRestrictedPath('/etc/passwd')).toBe(true);
    expect(patternRegistry.isRestrictedPath('/etc/shadow')).toBe(true);
    expect(patternRegistry.isRestrictedPath('~/.ssh/id_rsa')).toBe(true);
    expect(patternRegistry.isRestrictedPath('.env')).toBe(true);
  });

  it('should have built-in suspicious URL patterns', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    expect(patternRegistry.isSuspiciousUrl('http://192.168.1.1/admin')).toBe(true);
    expect(patternRegistry.isSuspiciousUrl('http://10.0.0.1/api')).toBe(true);
    expect(patternRegistry.isSuspiciousUrl('http://bit.ly/abc123')).toBe(true);
  });

  it('should allow adding custom string patterns', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const added = patternRegistry.addPattern('dangerousTool', 'my_risky_tool', {
      description: 'Custom dangerous tool',
      severity: 'high',
    });

    expect(added).toBe(true);
    expect(patternRegistry.isDangerousTool('my_risky_tool')).toBe(true);
  });

  it('should allow adding custom regex patterns', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const added = patternRegistry.addRegexPattern('suspiciousUrl', /evil\.com/i, {
      description: 'Evil domain',
      severity: 'critical',
    });

    expect(added).toBe(true);
    expect(patternRegistry.isSuspiciousUrl('https://evil.com/malware')).toBe(true);
  });

  it('should not add duplicate patterns', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    patternRegistry.addPattern('dangerousTool', 'custom_tool');
    const addedAgain = patternRegistry.addPattern('dangerousTool', 'custom_tool');

    expect(addedAgain).toBe(false);
  });

  it('should allow removing custom patterns', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    patternRegistry.addPattern('dangerousTool', 'temp_tool');
    expect(patternRegistry.isDangerousTool('temp_tool')).toBe(true);

    const removed = patternRegistry.removePattern('dangerousTool', 'temp_tool');
    expect(removed).toBe(true);
    expect(patternRegistry.isDangerousTool('temp_tool')).toBe(false);
  });

  it('should not remove built-in patterns', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const removed = patternRegistry.removePattern('dangerousTool', 'rm');

    expect(removed).toBe(false);
    expect(patternRegistry.isDangerousTool('rm')).toBe(true);
  });

  it('hasPattern should check existence', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    expect(patternRegistry.hasPattern('dangerousTool', 'rm')).toBe(true);
    expect(patternRegistry.hasPattern('dangerousTool', 'nonexistent')).toBe(false);
  });

  it('hasDangerousCommand should detect dangerous commands', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const result = patternRegistry.hasDangerousCommand('rm -rf /');
    expect(result).not.toBeNull();

    const safeResult = patternRegistry.hasDangerousCommand('ls -la');
    expect(safeResult).toBeNull();
  });

  it('hasSensitiveData should detect sensitive data', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const result = patternRegistry.hasSensitiveData('password = "secret123"');
    expect(result).not.toBeNull();

    const safeResult = patternRegistry.hasSensitiveData('Hello world');
    expect(safeResult).toBeNull();
  });

  it('getPatterns should return all patterns for a category', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const patterns = patternRegistry.getPatterns('dangerousTool');
    expect(patterns.length).toBeGreaterThan(0);
    expect(patterns.some(p => p.pattern === 'rm')).toBe(true);
  });

  it('getSnapshot should return registry state', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    const snapshot = patternRegistry.getSnapshot();
    expect(snapshot.categories.dangerousTool.totalEntries).toBeGreaterThan(0);
    expect(snapshot.categories.restrictedPath.totalEntries).toBeGreaterThan(0);
  });

  it('reset should restore built-in patterns only', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    // Add custom pattern
    patternRegistry.addPattern('dangerousTool', 'custom_tool');
    expect(patternRegistry.isDangerousTool('custom_tool')).toBe(true);

    // Reset
    patternRegistry.reset();

    // Custom should be gone, built-in should remain
    expect(patternRegistry.isDangerousTool('custom_tool')).toBe(false);
    expect(patternRegistry.isDangerousTool('rm')).toBe(true);
  });

  it('should match paths case-insensitively', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    expect(patternRegistry.isRestrictedPath('/ETC/PASSWD')).toBe(true);
    expect(patternRegistry.isRestrictedPath('/Etc/Shadow')).toBe(true);
  });

  it('should handle Windows paths', async () => {
    const { patternRegistry } = await import('../internal/pattern-registry');

    expect(patternRegistry.isRestrictedPath('C:\\Windows\\System32\\config')).toBe(true);
    expect(patternRegistry.isRestrictedPath('C:/Windows/System32/config')).toBe(true);
  });
});
