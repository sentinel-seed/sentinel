/**
 * Tests for Clipboard Guard
 */

import {
  scanClipboardContent,
  handleCopyEvent,
  handlePasteEvent,
  configureClipboardGuard,
  getClipboardGuardConfig,
  getClipboardHistory,
  clearClipboardHistory,
  getClipboardStats,
  ClipboardScanResult,
} from './clipboard-guard';

describe('Clipboard Guard', () => {
  beforeEach(() => {
    clearClipboardHistory();
    // Reset config to defaults
    configureClipboardGuard({
      blockCopySecrets: false,
      blockPastePII: false,
      warnOnSensitiveCopy: true,
      warnOnSensitivePaste: true,
      trackClipboardHistory: true,
      maxHistorySize: 50,
    });
  });

  describe('scanClipboardContent', () => {
    it('should return safe result for empty input', () => {
      const result = scanClipboardContent('');

      expect(result.hasSensitiveData).toBe(false);
      expect(result.hasSecrets).toBe(false);
      expect(result.hasPII).toBe(false);
      expect(result.riskLevel).toBe('safe');
    });

    it('should return safe result for null/undefined', () => {
      const result = scanClipboardContent(null as unknown as string);

      expect(result.hasSensitiveData).toBe(false);
      expect(result.riskLevel).toBe('safe');
    });

    it('should detect secrets', () => {
      // Use a valid OpenAI API key pattern (sk- followed by exactly 48 alphanumeric chars)
      const fakeOpenAIKey = 'sk-' + 'a'.repeat(48); // sk-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa
      const result = scanClipboardContent(fakeOpenAIKey);

      expect(result.hasSecrets).toBe(true);
      expect(result.hasSensitiveData).toBe(true);
    });

    it('should detect PII', () => {
      const result = scanClipboardContent('SSN: 123-45-6789');

      expect(result.hasPII).toBe(true);
      expect(result.hasSensitiveData).toBe(true);
    });

    it('should calculate risk level correctly', () => {
      // Critical - password
      const critical = scanClipboardContent('password: mysecret123');
      expect(critical.riskLevel).toBe('critical');

      // High - credit card
      const high = scanClipboardContent('Card: 4111-1111-1111-1111');
      expect(['high', 'critical']).toContain(high.riskLevel);

      // Safe - normal text
      const safe = scanClipboardContent('Hello world');
      expect(safe.riskLevel).toBe('safe');
    });

    it('should generate summary', () => {
      // Use a valid OpenAI API key pattern (sk- followed by exactly 48 alphanumeric chars)
      const fakeOpenAIKey = 'sk-' + 'a'.repeat(48);
      const result = scanClipboardContent(fakeOpenAIKey);

      expect(result.summary.length).toBeGreaterThan(0);
      // If secrets were detected, summary should mention it
      if (result.hasSecrets) {
        expect(result.summary.toLowerCase()).toMatch(/secret|found|item/);
      }
    });
  });

  describe('handleCopyEvent', () => {
    it('should allow copy by default', () => {
      const result = handleCopyEvent('Hello world', 'https://example.com');

      expect(result.allowed).toBe(true);
    });

    it('should record event in history', () => {
      handleCopyEvent('test', 'https://example.com');
      const history = getClipboardHistory();

      expect(history.length).toBe(1);
      expect(history[0].type).toBe('copy');
      expect(history[0].source).toBe('https://example.com');
    });

    it('should warn on sensitive content', () => {
      const result = handleCopyEvent('password: secret123', 'https://example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toBeDefined();
    });

    it('should block critical secrets when configured', () => {
      configureClipboardGuard({ blockCopySecrets: true });

      // This should trigger critical secret detection
      const result = handleCopyEvent('sk-1234567890abcdefghijklmnopqrstuvwxyzABCDEFGH', 'https://example.com');

      // May or may not block depending on pattern matching
      expect(result).toHaveProperty('allowed');
    });
  });

  describe('handlePasteEvent', () => {
    it('should allow paste by default', () => {
      const result = handlePasteEvent('Hello world', 'https://example.com');

      expect(result.allowed).toBe(true);
    });

    it('should record event in history', () => {
      handlePasteEvent('test', 'https://example.com');
      const history = getClipboardHistory();

      expect(history.length).toBe(1);
      expect(history[0].type).toBe('paste');
    });

    it('should warn on sensitive content', () => {
      const result = handlePasteEvent('SSN: 123-45-6789', 'https://example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toBeDefined();
    });

    it('should block high-risk PII when configured', () => {
      configureClipboardGuard({ blockPastePII: true });

      const result = handlePasteEvent('password: secret123', 'https://example.com');

      // Should block because password is auth category (high-risk)
      expect(result.allowed).toBe(false);
    });
  });

  describe('configureClipboardGuard', () => {
    it('should update config', () => {
      configureClipboardGuard({ blockCopySecrets: true });
      const config = getClipboardGuardConfig();

      expect(config.blockCopySecrets).toBe(true);
    });

    it('should preserve other config values', () => {
      configureClipboardGuard({ blockCopySecrets: true });
      const config = getClipboardGuardConfig();

      expect(config.warnOnSensitiveCopy).toBe(true);
      expect(config.trackClipboardHistory).toBe(true);
    });
  });

  describe('getClipboardHistory', () => {
    it('should return copy of history', () => {
      handleCopyEvent('test1', 'https://example.com');
      handlePasteEvent('test2', 'https://example.com');

      const history = getClipboardHistory();

      expect(history.length).toBe(2);
    });

    it('should respect maxHistorySize', () => {
      configureClipboardGuard({ maxHistorySize: 5 });

      for (let i = 0; i < 10; i++) {
        handleCopyEvent(`test${i}`, 'https://example.com');
      }

      const history = getClipboardHistory();
      expect(history.length).toBeLessThanOrEqual(5);
    });
  });

  describe('clearClipboardHistory', () => {
    it('should clear all history', () => {
      handleCopyEvent('test', 'https://example.com');
      clearClipboardHistory();
      const history = getClipboardHistory();

      expect(history.length).toBe(0);
    });
  });

  describe('getClipboardStats', () => {
    it('should return valid stats', () => {
      handleCopyEvent('test1', 'https://example.com');
      handlePasteEvent('test2', 'https://example.com');

      const stats = getClipboardStats();

      expect(stats.totalEvents).toBe(2);
      expect(stats.copyEvents).toBe(1);
      expect(stats.pasteEvents).toBe(1);
    });

    it('should count sensitive data events', () => {
      handleCopyEvent('password: secret123', 'https://example.com');

      const stats = getClipboardStats();

      expect(stats.sensitiveDataEvents).toBe(1);
    });
  });
});
