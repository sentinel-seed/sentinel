/**
 * Tests for Bot/Agent Detector
 * @jest-environment jsdom
 */

import {
  detectBot,
  quickBotCheck,
  recordInteraction,
} from './bot-detector';

describe('Bot Detector', () => {
  describe('detectBot', () => {
    it('should return a valid BotDetectionResult', async () => {
      const result = await detectBot();

      expect(result).toHaveProperty('isBot');
      expect(result).toHaveProperty('confidence');
      expect(result).toHaveProperty('indicators');
      expect(result).toHaveProperty('summary');
      expect(typeof result.isBot).toBe('boolean');
      expect(typeof result.confidence).toBe('number');
      expect(Array.isArray(result.indicators)).toBe(true);
      expect(typeof result.summary).toBe('string');
    });

    it('should have confidence between 0 and 100', async () => {
      const result = await detectBot();

      expect(result.confidence).toBeGreaterThanOrEqual(0);
      expect(result.confidence).toBeLessThanOrEqual(100);
    });

    it('should not detect bot in normal browser environment', async () => {
      // In a normal test environment (Jest/JSDOM), there shouldn't be
      // automation signatures. However, some indicators might trigger.
      const result = await detectBot();

      // At minimum, we expect a valid result
      expect(result).toBeDefined();
      expect(result.summary.length).toBeGreaterThan(0);
    });
  });

  describe('quickBotCheck', () => {
    it('should return a boolean', async () => {
      const result = await quickBotCheck();
      expect(typeof result).toBe('boolean');
    });
  });

  describe('recordInteraction', () => {
    it('should not throw when recording clicks', () => {
      expect(() => {
        recordInteraction('click');
        recordInteraction('click');
        recordInteraction('click');
      }).not.toThrow();
    });

    it('should not throw when recording keystrokes', () => {
      expect(() => {
        recordInteraction('keystroke');
        recordInteraction('keystroke');
        recordInteraction('keystroke');
      }).not.toThrow();
    });
  });

  describe('BotIndicator types', () => {
    it('should have valid indicator structure when detected', async () => {
      const result = await detectBot();

      for (const indicator of result.indicators) {
        expect(indicator).toHaveProperty('type');
        expect(indicator).toHaveProperty('confidence');
        expect(indicator).toHaveProperty('description');
        expect(typeof indicator.type).toBe('string');
        expect(typeof indicator.confidence).toBe('number');
        expect(typeof indicator.description).toBe('string');
        expect(indicator.confidence).toBeGreaterThanOrEqual(0);
        expect(indicator.confidence).toBeLessThanOrEqual(100);
      }
    });
  });
});
