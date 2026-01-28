/**
 * Logging Module Tests
 *
 * Tests for:
 * - Formatters
 * - AuditLog
 * - AlertManager
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  // Formatters
  formatTimestamp,
  formatDuration,
  formatRiskLevel,
  getRiskBadge,
  formatIssue,
  formatIssueList,
  formatAuditEntry,
  formatAlert,
  formatAlertForWebhook,
  formatSessionSummary,
  truncate,
  indent,
  stripColors,
  COLORS,
  // AuditLog
  AuditLog,
  createAuditLog,
  DEFAULT_MAX_ENTRIES,
  // AlertManager
  AlertManager,
  createAlertManager,
} from '../logging';
import type { DetectedIssue, AuditEntry, SecurityAlert } from '../types';

// =============================================================================
// Formatter Tests
// =============================================================================

describe('Formatters', () => {
  describe('formatTimestamp', () => {
    it('should format time only by default', () => {
      const timestamp = new Date('2026-01-28T10:30:45.123Z').getTime();
      const result = formatTimestamp(timestamp);

      expect(result).toMatch(/^\d{2}:\d{2}:\d{2}$/);
    });

    it('should include date when requested', () => {
      const timestamp = new Date('2026-01-28T10:30:45.123Z').getTime();
      const result = formatTimestamp(timestamp, { includeDate: true });

      expect(result).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/);
    });

    it('should include milliseconds when requested', () => {
      const timestamp = new Date('2026-01-28T10:30:45.123Z').getTime();
      const result = formatTimestamp(timestamp, { includeMs: true });

      expect(result).toMatch(/^\d{2}:\d{2}:\d{2}\.\d{3}$/);
    });
  });

  describe('formatDuration', () => {
    it('should format milliseconds', () => {
      expect(formatDuration(500)).toBe('500ms');
    });

    it('should format seconds', () => {
      expect(formatDuration(5000)).toBe('5s');
      expect(formatDuration(30000)).toBe('30s');
    });

    it('should format minutes', () => {
      expect(formatDuration(60000)).toBe('1m');
      expect(formatDuration(90000)).toBe('1m 30s');
    });

    it('should format hours', () => {
      expect(formatDuration(3600000)).toBe('1h');
      expect(formatDuration(3720000)).toBe('1h 2m');
    });
  });

  describe('formatRiskLevel', () => {
    it('should format with colors', () => {
      const result = formatRiskLevel('high');

      expect(result).toContain('HIGH');
      expect(result).toContain(COLORS.red);
    });

    it('should format without colors', () => {
      const result = formatRiskLevel('high', false);

      expect(result).toBe('HIGH');
      expect(result).not.toContain(COLORS.red);
    });
  });

  describe('getRiskBadge', () => {
    it('should create badge', () => {
      expect(getRiskBadge('high')).toBe('[HIGH]');
      expect(getRiskBadge('critical')).toBe('[CRITICAL]');
    });
  });

  describe('formatIssue', () => {
    const issue: DetectedIssue = {
      type: 'data_leak',
      description: 'API key detected',
      evidence: 'sk-1234567890abcdef',
      severity: 'critical',
    };

    it('should format issue', () => {
      const result = formatIssue(issue, { useColor: false });

      expect(result).toContain('CRITICAL');
      expect(result).toContain('data leak');
      expect(result).toContain('API key detected');
    });

    it('should include evidence when requested', () => {
      const result = formatIssue(issue, { includeEvidence: true, useColor: false });

      expect(result).toContain('Evidence:');
      expect(result).toContain('sk-1234567890abcdef');
    });
  });

  describe('formatIssueList', () => {
    const issues: DetectedIssue[] = [
      { type: 'data_leak', description: 'API key', evidence: '', severity: 'critical' },
      { type: 'system_path', description: 'Root access', evidence: '', severity: 'high' },
    ];

    it('should format list', () => {
      const result = formatIssueList(issues, { useColor: false });

      expect(result).toContain('1.');
      expect(result).toContain('2.');
      expect(result).toContain('API key');
      expect(result).toContain('Root access');
    });

    it('should truncate with maxItems', () => {
      const manyIssues = Array(10).fill(issues[0]);
      const result = formatIssueList(manyIssues, { maxItems: 3, useColor: false });

      expect(result).toContain('... and 7 more');
    });

    it('should handle empty list', () => {
      expect(formatIssueList([])).toBe('No issues detected');
    });
  });

  describe('formatAuditEntry', () => {
    const entry: AuditEntry = {
      id: 'audit_1',
      timestamp: Date.now(),
      event: 'output_blocked',
      outcome: 'blocked',
      details: { reason: 'test' },
      sessionId: 'session-1',
    };

    it('should format entry', () => {
      const result = formatAuditEntry(entry, { useColor: false });

      expect(result).toContain('output blocked');
      expect(result).toContain('BLOCKED');
      expect(result).toContain('session-1');
    });

    it('should include details in verbose mode', () => {
      const result = formatAuditEntry(entry, { verbose: true, useColor: false });

      expect(result).toContain('reason');
      expect(result).toContain('test');
    });
  });

  describe('formatAlert', () => {
    const alert: SecurityAlert = {
      type: 'action_blocked',
      severity: 'high',
      message: 'Tool call blocked',
      timestamp: Date.now(),
    };

    it('should format alert', () => {
      const result = formatAlert(alert, { useColor: false });

      expect(result).toContain('ACTION BLOCKED');
      expect(result).toContain('HIGH');
      expect(result).toContain('Tool call blocked');
    });
  });

  describe('formatAlertForWebhook', () => {
    const alert: SecurityAlert = {
      type: 'action_blocked',
      severity: 'high',
      message: 'Tool call blocked',
      timestamp: 1706438400000,
    };

    it('should create webhook payload', () => {
      const result = formatAlertForWebhook(alert);

      expect(result.type).toBe('action_blocked');
      expect(result.severity).toBe('high');
      expect(result.message).toBe('Tool call blocked');
      expect(result.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
    });
  });

  describe('formatSessionSummary', () => {
    const summary = {
      sessionId: 'session-1',
      success: true,
      durationMs: 5000,
      messageCount: 10,
      toolCallCount: 5,
      issuesDetected: 2,
      actionsBlocked: 1,
    };

    it('should format summary', () => {
      const result = formatSessionSummary(summary, false);

      expect(result).toContain('Session Summary');
      expect(result).toContain('SUCCESS');
      expect(result).toContain('session-1');
      expect(result).toContain('5s');
      expect(result).toContain('Messages: 10');
      expect(result).toContain('Actions Blocked: 1');
    });
  });

  describe('Utility functions', () => {
    it('truncate should shorten strings', () => {
      expect(truncate('Hello, World!', 10)).toBe('Hello, ...');
      expect(truncate('Short', 10)).toBe('Short');
    });

    it('indent should add spaces', () => {
      expect(indent('Line 1\nLine 2', 4)).toBe('    Line 1\n    Line 2');
    });

    it('stripColors should remove ANSI codes', () => {
      const colored = `${COLORS.red}Error${COLORS.reset}`;
      expect(stripColors(colored)).toBe('Error');
    });
  });
});

// =============================================================================
// AuditLog Tests
// =============================================================================

describe('AuditLog', () => {
  let audit: AuditLog;

  beforeEach(() => {
    vi.useFakeTimers();
    audit = new AuditLog({ entryTtlMs: 0 }); // Disable TTL for most tests
  });

  afterEach(() => {
    audit.destroy();
    vi.useRealTimers();
  });

  describe('log', () => {
    it('should create an entry', () => {
      const entry = audit.log({
        event: 'output_blocked',
        outcome: 'blocked',
        sessionId: 'session-1',
        details: { reason: 'test' },
      });

      expect(entry.id).toBeDefined();
      expect(entry.event).toBe('output_blocked');
      expect(entry.outcome).toBe('blocked');
      expect(entry.sessionId).toBe('session-1');
      expect(entry.details.reason).toBe('test');
    });

    it('should enforce max entries', () => {
      const smallAudit = new AuditLog({ maxEntries: 5, entryTtlMs: 0 });

      for (let i = 0; i < 10; i++) {
        smallAudit.log({ event: 'input_analyzed', outcome: 'allowed' });
      }

      expect(smallAudit.size).toBe(5);
      smallAudit.destroy();
    });
  });

  describe('Convenience log methods', () => {
    it('logInputAnalysis should log correctly', () => {
      const entry = audit.logInputAnalysis('session-1', 4, [
        { type: 'prompt_injection', description: 'test', evidence: '', severity: 'high' },
      ]);

      expect(entry.event).toBe('input_analyzed');
      expect(entry.outcome).toBe('alerted');
      expect(entry.details.threatLevel).toBe(4);
    });

    it('logOutputValidation should log correctly', () => {
      const entry = audit.logOutputValidation('session-1', true, []);

      expect(entry.event).toBe('output_blocked');
      expect(entry.outcome).toBe('blocked');
    });

    it('logToolValidation should log correctly', () => {
      const entry = audit.logToolValidation('session-1', 'bash', false, []);

      expect(entry.event).toBe('tool_validated');
      expect(entry.outcome).toBe('allowed');
      expect(entry.details.toolName).toBe('bash');
    });

    it('logSeedInjection should log correctly', () => {
      const entry = audit.logSeedInjection('session-1', 'standard');

      expect(entry.event).toBe('seed_injected');
      expect(entry.details.seedTemplate).toBe('standard');
    });

    it('logSessionStart/End should log correctly', () => {
      const start = audit.logSessionStart('session-1');
      const end = audit.logSessionEnd('session-1', true);

      expect(start.event).toBe('session_started');
      expect(end.event).toBe('session_ended');
    });

    it('logEscapeUsed should log correctly', () => {
      const entry = audit.logEscapeUsed('session-1', 'allow_once');

      expect(entry.event).toBe('escape_used');
      expect(entry.details.escapeType).toBe('allow_once');
    });

    it('logError should log correctly', () => {
      const entry = audit.logError('session-1', new Error('Test error'));

      expect(entry.event).toBe('error');
      expect(entry.outcome).toBe('error');
      expect(entry.details.errorMessage).toBe('Test error');
    });
  });

  describe('query', () => {
    beforeEach(() => {
      audit.log({ event: 'input_analyzed', outcome: 'allowed', sessionId: 'session-1' });
      audit.log({ event: 'output_blocked', outcome: 'blocked', sessionId: 'session-1' });
      audit.log({ event: 'tool_validated', outcome: 'allowed', sessionId: 'session-2' });
    });

    it('should return all entries', () => {
      const results = audit.query();
      expect(results.length).toBe(3);
    });

    it('should filter by event', () => {
      const results = audit.query({ event: 'output_blocked' });
      expect(results.length).toBe(1);
      expect(results[0]!.event).toBe('output_blocked');
    });

    it('should filter by outcome', () => {
      const results = audit.query({ outcome: 'allowed' });
      expect(results.length).toBe(2);
    });

    it('should filter by sessionId', () => {
      const results = audit.query({ sessionId: 'session-1' });
      expect(results.length).toBe(2);
    });

    it('should limit results', () => {
      const results = audit.query({ limit: 2 });
      expect(results.length).toBe(2);
    });

    it('should sort by timestamp descending', () => {
      const results = audit.query();
      expect(results[0]!.timestamp).toBeGreaterThanOrEqual(results[1]!.timestamp);
    });
  });

  describe('getById', () => {
    it('should find entry by ID', () => {
      const entry = audit.log({ event: 'input_analyzed', outcome: 'allowed' });
      const found = audit.getById(entry.id);

      expect(found).toBeDefined();
      expect(found!.id).toBe(entry.id);
    });

    it('should return undefined for unknown ID', () => {
      expect(audit.getById('unknown')).toBeUndefined();
    });
  });

  describe('getStats', () => {
    it('should return statistics', () => {
      audit.log({ event: 'input_analyzed', outcome: 'allowed', sessionId: 'session-1' });
      audit.log({ event: 'output_blocked', outcome: 'blocked', sessionId: 'session-1' });
      audit.log({ event: 'output_blocked', outcome: 'blocked', sessionId: 'session-2' });

      const stats = audit.getStats();

      expect(stats.totalEntries).toBe(3);
      expect(stats.byEvent.output_blocked).toBe(2);
      expect(stats.byOutcome.blocked).toBe(2);
      expect(stats.uniqueSessions).toBe(2);
    });
  });

  describe('TTL cleanup', () => {
    it('should clean up expired entries', () => {
      const ttlAudit = new AuditLog({
        entryTtlMs: 10000,
        cleanupIntervalMs: 1000,
      });

      ttlAudit.log({ event: 'input_analyzed', outcome: 'allowed' });
      expect(ttlAudit.size).toBe(1);

      // Advance past TTL
      vi.advanceTimersByTime(15000);

      expect(ttlAudit.size).toBe(0);
      ttlAudit.destroy();
    });
  });

  describe('exportToJson', () => {
    it('should export entries as JSON', () => {
      audit.log({ event: 'input_analyzed', outcome: 'allowed' });

      const json = audit.exportToJson();
      const parsed = JSON.parse(json);

      expect(Array.isArray(parsed)).toBe(true);
      expect(parsed.length).toBe(1);
    });
  });

  describe('createAuditLog', () => {
    it('should create instance with factory', () => {
      const a = createAuditLog();
      expect(a).toBeInstanceOf(AuditLog);
      a.destroy();
    });
  });
});

// =============================================================================
// AlertManager Tests
// =============================================================================

describe('AlertManager', () => {
  let alerts: AlertManager;

  beforeEach(() => {
    vi.useFakeTimers();
    alerts = new AlertManager();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('send', () => {
    it('should create and queue alert', async () => {
      const result = await alerts.send({
        type: 'action_blocked',
        severity: 'high',
        message: 'Test alert',
      });

      expect(result.queued).toBe(true);
      expect(result.alert.type).toBe('action_blocked');
      expect(result.alert.severity).toBe('high');
    });

    it('should rate limit', async () => {
      const limitedAlerts = new AlertManager({ rateLimitMax: 2 });

      await limitedAlerts.send({ type: 'error', severity: 'low', message: '1' });
      await limitedAlerts.send({ type: 'error', severity: 'low', message: '2' });
      const result = await limitedAlerts.send({ type: 'error', severity: 'low', message: '3' });

      expect(result.rateLimited).toBe(true);
      expect(result.queued).toBe(false);
    });
  });

  describe('Convenience methods', () => {
    it('alertHighThreatInput should send correct alert', async () => {
      const result = await alerts.alertHighThreatInput(5, [
        { type: 'prompt_injection', description: 'test', evidence: '', severity: 'critical' },
      ]);

      expect(result.alert.type).toBe('high_threat_input');
      expect(result.alert.severity).toBe('critical');
    });

    it('alertActionBlocked should send correct alert', async () => {
      const result = await alerts.alertActionBlocked('tool', 'dangerous command');

      expect(result.alert.type).toBe('action_blocked');
      expect(result.alert.message).toContain('Tool call blocked');
    });

    it('alertPromptInjection should send correct alert', async () => {
      const result = await alerts.alertPromptInjection('ignore previous instructions');

      expect(result.alert.type).toBe('prompt_injection');
      expect(result.alert.severity).toBe('critical');
    });

    it('alertSessionAnomaly should send correct alert', async () => {
      const result = await alerts.alertSessionAnomaly('high_threat_rate', {});

      expect(result.alert.type).toBe('session_anomaly');
    });

    it('alertError should send correct alert', async () => {
      const result = await alerts.alertError(new Error('Test error'));

      expect(result.alert.type).toBe('error');
      expect(result.alert.message).toContain('Test error');
    });
  });

  describe('Query methods', () => {
    beforeEach(async () => {
      await alerts.send({ type: 'action_blocked', severity: 'high', message: '1' });
      await alerts.send({ type: 'error', severity: 'low', message: '2' });
      await alerts.send({ type: 'action_blocked', severity: 'critical', message: '3' });
    });

    it('getRecent should return recent alerts', () => {
      const recent = alerts.getRecent(2);

      expect(recent.length).toBe(2);
      expect(recent[0]!.message).toBe('3'); // Newest first
    });

    it('getByType should filter by type', () => {
      const blocked = alerts.getByType('action_blocked');

      expect(blocked.length).toBe(2);
    });

    it('getBySeverity should filter by minimum severity', () => {
      const highOrMore = alerts.getBySeverity('high');

      expect(highOrMore.length).toBe(2);
    });
  });

  describe('getStats', () => {
    it('should return statistics', async () => {
      await alerts.send({ type: 'action_blocked', severity: 'high', message: '1' });
      await alerts.send({ type: 'action_blocked', severity: 'high', message: '2' });
      await alerts.send({ type: 'error', severity: 'low', message: '3' });

      const stats = alerts.getStats();

      expect(stats.totalAlerts).toBe(3);
      expect(stats.byType.action_blocked).toBe(2);
      expect(stats.bySeverity.high).toBe(2);
      expect(stats.queueSize).toBe(3);
    });
  });

  describe('enable/disable', () => {
    it('should track enabled state', () => {
      expect(alerts.isEnabled()).toBe(true);

      alerts.disable();
      expect(alerts.isEnabled()).toBe(false);

      alerts.enable();
      expect(alerts.isEnabled()).toBe(true);
    });
  });

  describe('Webhook management', () => {
    it('should add webhooks', () => {
      alerts.addWebhook({ url: 'https://example.com/hook1' });
      alerts.addWebhook({ url: 'https://example.com/hook2' });

      expect(alerts.webhookCount).toBe(2);
    });

    it('should remove webhooks', () => {
      alerts.addWebhook({ url: 'https://example.com/hook1' });
      alerts.addWebhook({ url: 'https://example.com/hook2' });

      const removed = alerts.removeWebhook('https://example.com/hook1');

      expect(removed).toBe(true);
      expect(alerts.webhookCount).toBe(1);
    });

    it('should return false when removing non-existent webhook', () => {
      const removed = alerts.removeWebhook('https://example.com/nonexistent');

      expect(removed).toBe(false);
    });
  });

  describe('Webhook delivery', () => {
    it('should send to webhooks when configured', async () => {
      const mockFetch = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal('fetch', mockFetch);

      alerts.addWebhook({ url: 'https://example.com/hook' });

      const result = await alerts.send({
        type: 'action_blocked',
        severity: 'high',
        message: 'Test',
      });

      expect(result.webhookSuccesses).toBe(1);
      expect(mockFetch).toHaveBeenCalledWith(
        'https://example.com/hook',
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
        })
      );

      vi.unstubAllGlobals();
    });

    it('should filter webhooks by minSeverity', async () => {
      const mockFetch = vi.fn().mockResolvedValue({ ok: true });
      vi.stubGlobal('fetch', mockFetch);

      alerts.addWebhook({ url: 'https://example.com/hook', minSeverity: 'critical' });

      // Send a 'high' severity alert (below 'critical' threshold)
      await alerts.send({
        type: 'action_blocked',
        severity: 'high',
        message: 'Test',
      });

      expect(mockFetch).not.toHaveBeenCalled();

      vi.unstubAllGlobals();
    });

    it('should handle webhook failures gracefully', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      vi.stubGlobal('fetch', mockFetch);

      alerts.addWebhook({ url: 'https://example.com/hook', retries: 0 });

      const result = await alerts.send({
        type: 'action_blocked',
        severity: 'high',
        message: 'Test',
      });

      expect(result.queued).toBe(true);
      expect(result.webhookFailures).toBe(1);
      expect(alerts.getStats().webhookFailures).toBe(1);

      vi.unstubAllGlobals();
    });
  });

  describe('clear and resetStats', () => {
    it('should clear queue', async () => {
      await alerts.send({ type: 'error', severity: 'low', message: 'Test' });
      expect(alerts.getRecent().length).toBe(1);

      alerts.clear();
      expect(alerts.getRecent().length).toBe(0);
    });

    it('should reset statistics', async () => {
      await alerts.send({ type: 'error', severity: 'low', message: 'Test' });
      expect(alerts.getStats().totalAlerts).toBe(1);

      alerts.resetStats();
      expect(alerts.getStats().totalAlerts).toBe(0);
    });
  });

  describe('createAlertManager', () => {
    it('should create instance with factory', () => {
      const a = createAlertManager();
      expect(a).toBeInstanceOf(AlertManager);
    });
  });
});
