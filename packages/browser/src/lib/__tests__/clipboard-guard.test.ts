/**
 * @fileoverview Unit tests for Clipboard Guard
 *
 * Tests clipboard protection functionality:
 * - Content scanning
 * - Configuration management
 * - Copy/paste event handling
 * - Statistics tracking
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  scanClipboardContent,
  handleCopyEvent,
  handlePasteEvent,
  safeClipboardWrite,
  getClipboardStats,
  getClipboardHistory,
  clearClipboardHistory,
  configureClipboardGuard,
  getClipboardGuardConfig,
  setupClipboardGuard,
  checkClipboardForType,
} from '../clipboard-guard';

// Mock patterns module
jest.mock('../patterns', () => ({
  scanAll: jest.fn((text: string) => {
    const matches = [];
    // Simulate API key detection
    if (text.includes('sk-') || text.includes('AKIA')) {
      matches.push({
        type: 'api_key',
        value: text.includes('sk-') ? 'sk-12345' : 'AKIA12345',
        start: 0,
        end: 10,
        severity: 'critical',
      });
    }
    // Simulate password detection
    if (text.includes('password=')) {
      matches.push({
        type: 'password',
        value: 'password=secret',
        start: 0,
        end: 15,
        severity: 'high',
      });
    }
    return matches;
  }),
}));

// Mock PII guard
jest.mock('../pii-guard', () => ({
  scanForPII: jest.fn((text: string) => {
    const matches = [];
    // Simulate SSN detection
    if (text.includes('123-45-6789')) {
      matches.push({
        type: 'ssn',
        value: '123-45-6789',
        masked: '***-**-****',
        start: 0,
        end: 11,
        confidence: 95,
        category: 'identity',
      });
    }
    // Simulate credit card detection
    if (text.includes('4111')) {
      matches.push({
        type: 'credit_card',
        value: '4111111111111111',
        masked: '****-****-****-1111',
        start: 0,
        end: 16,
        confidence: 90,
        category: 'financial',
      });
    }
    // Simulate password detection
    if (text.includes('mypassword')) {
      matches.push({
        type: 'password',
        value: 'mypassword',
        masked: '**********',
        start: 0,
        end: 10,
        confidence: 85,
        category: 'auth',
      });
    }
    return matches;
  }),
}));

// Mock navigator.clipboard
const mockClipboard = {
  readText: jest.fn(() => Promise.resolve('')),
  writeText: jest.fn(() => Promise.resolve()),
};

Object.defineProperty(navigator, 'clipboard', {
  value: mockClipboard,
  writable: true,
});

describe('Clipboard Guard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
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
    it('should return safe result for empty text', () => {
      const result = scanClipboardContent('');

      expect(result.hasSensitiveData).toBe(false);
      expect(result.riskLevel).toBe('safe');
    });

    it('should return safe result for normal text', () => {
      const result = scanClipboardContent('Hello, world! This is a test.');

      expect(result.hasSensitiveData).toBe(false);
      expect(result.hasSecrets).toBe(false);
      expect(result.hasPII).toBe(false);
      expect(result.riskLevel).toBe('safe');
    });

    it('should detect API keys', () => {
      const result = scanClipboardContent('My API key is sk-12345abcdef');

      expect(result.hasSensitiveData).toBe(true);
      expect(result.hasSecrets).toBe(true);
      expect(result.secrets.length).toBeGreaterThan(0);
      expect(result.riskLevel).toBe('critical');
    });

    it('should detect SSN', () => {
      const result = scanClipboardContent('SSN: 123-45-6789');

      expect(result.hasSensitiveData).toBe(true);
      expect(result.hasPII).toBe(true);
      expect(result.pii.length).toBeGreaterThan(0);
    });

    it('should detect credit cards', () => {
      const result = scanClipboardContent('Card: 4111111111111111');

      expect(result.hasSensitiveData).toBe(true);
      expect(result.hasPII).toBe(true);
      expect(result.riskLevel).toBe('high');
    });

    it('should detect auth category PII as critical', () => {
      const result = scanClipboardContent('password: mypassword');

      expect(result.hasSensitiveData).toBe(true);
      expect(result.riskLevel).toBe('critical');
    });

    it('should handle null/undefined input gracefully', () => {
      const result1 = scanClipboardContent(null as unknown as string);
      const result2 = scanClipboardContent(undefined as unknown as string);

      expect(result1.hasSensitiveData).toBe(false);
      expect(result2.hasSensitiveData).toBe(false);
    });

    it('should generate summary for detected items', () => {
      const result = scanClipboardContent('sk-12345 and 123-45-6789');

      expect(result.summary).toContain('secret');
      expect(result.summary).toContain('PII');
    });
  });

  describe('handleCopyEvent', () => {
    it('should allow copy of safe content', () => {
      const result = handleCopyEvent('Hello world', 'https://example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toBeUndefined();
    });

    it('should warn on sensitive copy when enabled', () => {
      configureClipboardGuard({ warnOnSensitiveCopy: true });

      const result = handleCopyEvent('sk-12345abcdef', 'https://example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toContain('Warning');
    });

    it('should not warn when warnings disabled', () => {
      configureClipboardGuard({ warnOnSensitiveCopy: false });

      const result = handleCopyEvent('sk-12345abcdef', 'https://example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toBeUndefined();
    });

    it('should block copy of critical secrets when enabled', () => {
      configureClipboardGuard({ blockCopySecrets: true });

      const result = handleCopyEvent('sk-12345abcdef', 'https://example.com');

      expect(result.allowed).toBe(false);
      expect(result.message).toContain('Blocked');
    });

    it('should record event in history', () => {
      handleCopyEvent('test content', 'https://example.com');

      const history = getClipboardHistory();
      expect(history).toHaveLength(1);
      expect(history[0].type).toBe('copy');
      expect(history[0].source).toBe('https://example.com');
    });
  });

  describe('handlePasteEvent', () => {
    it('should allow paste of safe content', () => {
      const result = handlePasteEvent('Hello world', 'https://chat.example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toBeUndefined();
    });

    it('should warn on sensitive paste when enabled', () => {
      configureClipboardGuard({ warnOnSensitivePaste: true });

      const result = handlePasteEvent('123-45-6789', 'https://chat.example.com');

      expect(result.allowed).toBe(true);
      expect(result.message).toContain('Warning');
    });

    it('should block paste of high-risk PII when enabled', () => {
      configureClipboardGuard({ blockPastePII: true });

      const result = handlePasteEvent('4111111111111111', 'https://chat.example.com');

      expect(result.allowed).toBe(false);
      expect(result.message).toContain('Blocked');
    });

    it('should block paste of auth PII when enabled', () => {
      configureClipboardGuard({ blockPastePII: true });

      const result = handlePasteEvent('mypassword', 'https://chat.example.com');

      expect(result.allowed).toBe(false);
    });

    it('should record event in history', () => {
      handlePasteEvent('pasted text', 'https://chat.example.com');

      const history = getClipboardHistory();
      expect(history).toHaveLength(1);
      expect(history[0].type).toBe('paste');
    });
  });

  describe('safeClipboardWrite', () => {
    it('should write text to clipboard', async () => {
      const result = await safeClipboardWrite('Hello world');

      expect(result.success).toBe(true);
      expect(result.masked).toBe(false);
      expect(mockClipboard.writeText).toHaveBeenCalledWith('Hello world');
    });

    it('should mask sensitive data when requested', async () => {
      const result = await safeClipboardWrite('sk-12345abcdef', true);

      expect(result.success).toBe(true);
      expect(result.masked).toBe(true);
      expect(result.message).toContain('masked');
    });

    it('should handle write failure gracefully', async () => {
      mockClipboard.writeText.mockRejectedValueOnce(new Error('Permission denied'));

      const result = await safeClipboardWrite('test');

      expect(result.success).toBe(false);
      expect(result.message).toContain('Failed');
    });
  });

  describe('getClipboardStats', () => {
    it('should return empty stats initially', () => {
      const stats = getClipboardStats();

      expect(stats.totalEvents).toBe(0);
      expect(stats.copyEvents).toBe(0);
      expect(stats.pasteEvents).toBe(0);
      expect(stats.blockedEvents).toBe(0);
    });

    it('should track copy events', () => {
      handleCopyEvent('test1', 'https://a.com');
      handleCopyEvent('test2', 'https://b.com');

      const stats = getClipboardStats();
      expect(stats.copyEvents).toBe(2);
      expect(stats.totalEvents).toBe(2);
    });

    it('should track paste events', () => {
      handlePasteEvent('test1', 'https://a.com');
      handlePasteEvent('test2', 'https://b.com');

      const stats = getClipboardStats();
      expect(stats.pasteEvents).toBe(2);
    });

    it('should track blocked events', () => {
      configureClipboardGuard({ blockCopySecrets: true });
      handleCopyEvent('sk-12345abcdef', 'https://example.com');

      const stats = getClipboardStats();
      expect(stats.blockedEvents).toBe(1);
    });

    it('should track sensitive data events', () => {
      handleCopyEvent('sk-12345', 'https://example.com');
      handleCopyEvent('normal text', 'https://example.com');

      const stats = getClipboardStats();
      expect(stats.sensitiveDataEvents).toBe(1);
    });

    it('should track risk breakdown', () => {
      handleCopyEvent('sk-12345', 'https://example.com'); // critical
      handleCopyEvent('4111111111111111', 'https://example.com'); // high
      handleCopyEvent('normal', 'https://example.com'); // safe

      const stats = getClipboardStats();
      expect(stats.riskBreakdown.critical).toBe(1);
      expect(stats.riskBreakdown.high).toBe(1);
      expect(stats.riskBreakdown.safe).toBe(1);
    });
  });

  describe('Configuration', () => {
    it('should get current configuration', () => {
      const config = getClipboardGuardConfig();

      expect(config).toHaveProperty('blockCopySecrets');
      expect(config).toHaveProperty('blockPastePII');
      expect(config).toHaveProperty('warnOnSensitiveCopy');
      expect(config).toHaveProperty('trackClipboardHistory');
      expect(config).toHaveProperty('maxHistorySize');
    });

    it('should update configuration partially', () => {
      configureClipboardGuard({ blockCopySecrets: true });

      const config = getClipboardGuardConfig();
      expect(config.blockCopySecrets).toBe(true);
      expect(config.warnOnSensitiveCopy).toBe(true); // unchanged
    });

    it('should respect maxHistorySize', () => {
      configureClipboardGuard({ maxHistorySize: 3 });

      handleCopyEvent('1', 'a');
      handleCopyEvent('2', 'b');
      handleCopyEvent('3', 'c');
      handleCopyEvent('4', 'd');
      handleCopyEvent('5', 'e');

      const history = getClipboardHistory();
      expect(history).toHaveLength(3);
    });

    it('should not track history when disabled', () => {
      configureClipboardGuard({ trackClipboardHistory: false });

      handleCopyEvent('test', 'https://example.com');

      const history = getClipboardHistory();
      expect(history).toHaveLength(0);
    });
  });

  describe('clearClipboardHistory', () => {
    it('should clear all history', () => {
      handleCopyEvent('test1', 'a');
      handleCopyEvent('test2', 'b');
      handlePasteEvent('test3', 'c');

      expect(getClipboardHistory().length).toBe(3);

      clearClipboardHistory();

      expect(getClipboardHistory().length).toBe(0);
    });
  });

  describe('setupClipboardGuard', () => {
    it('should return cleanup function', () => {
      const cleanup = setupClipboardGuard();

      expect(typeof cleanup).toBe('function');
      cleanup();
    });

    it('should accept callback functions', () => {
      const onCopy = jest.fn();
      const onPaste = jest.fn();

      const cleanup = setupClipboardGuard(onCopy, onPaste);
      cleanup();

      expect(typeof cleanup).toBe('function');
    });
  });

  describe('checkClipboardForType', () => {
    beforeEach(() => {
      mockClipboard.readText.mockResolvedValue('');
    });

    it('should check for secrets', async () => {
      mockClipboard.readText.mockResolvedValueOnce('sk-12345');

      const result = await checkClipboardForType('secrets');
      expect(result).toBe(true);
    });

    it('should check for PII', async () => {
      mockClipboard.readText.mockResolvedValueOnce('123-45-6789');

      const result = await checkClipboardForType('pii');
      expect(result).toBe(true);
    });

    it('should check for auth data', async () => {
      mockClipboard.readText.mockResolvedValueOnce('mypassword');

      const result = await checkClipboardForType('auth');
      expect(result).toBe(true);
    });

    it('should check for financial data', async () => {
      mockClipboard.readText.mockResolvedValueOnce('4111111111111111');

      const result = await checkClipboardForType('financial');
      expect(result).toBe(true);
    });

    it('should check for identity data', async () => {
      mockClipboard.readText.mockResolvedValueOnce('123-45-6789');

      const result = await checkClipboardForType('identity');
      expect(result).toBe(true);
    });

    it('should return false for safe clipboard', async () => {
      mockClipboard.readText.mockResolvedValueOnce('Hello world');

      const result = await checkClipboardForType('secrets');
      expect(result).toBe(false);
    });
  });
});
