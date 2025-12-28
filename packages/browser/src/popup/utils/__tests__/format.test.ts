/**
 * @fileoverview Unit tests for formatting utilities
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  formatTime,
  formatDate,
  formatRelativeTime,
  formatTimeRemaining,
  formatUSD,
  formatPercentage,
  truncate,
  truncateEndpoint,
  formatCompactNumber,
} from '../format';

describe('format utilities', () => {
  describe('formatTime', () => {
    it('should format timestamp to time string', () => {
      // Create a fixed date for consistent testing
      const date = new Date('2025-12-28T14:30:00');
      const result = formatTime(date.getTime());
      expect(result).toMatch(/\d{1,2}:\d{2}/);
    });
  });

  describe('formatDate', () => {
    it('should format timestamp to date string', () => {
      const date = new Date('2025-12-28');
      const result = formatDate(date.getTime());
      // Date can be 27 or 28 depending on timezone
      expect(result).toMatch(/2[78]/);
      // Month can be Dec, dez, 12 depending on locale
      expect(result).toMatch(/Dec|dez|12/i);
      expect(result).toContain('2025');
    });
  });

  describe('formatRelativeTime', () => {
    it('should return "Just now" for recent timestamps', () => {
      const result = formatRelativeTime(Date.now() - 30000); // 30 seconds ago
      expect(result).toBe('Just now');
    });

    it('should return minutes ago', () => {
      const result = formatRelativeTime(Date.now() - 5 * 60 * 1000); // 5 minutes ago
      expect(result).toBe('5m ago');
    });

    it('should return hours ago', () => {
      const result = formatRelativeTime(Date.now() - 3 * 60 * 60 * 1000); // 3 hours ago
      expect(result).toBe('3h ago');
    });

    it('should return days ago', () => {
      const result = formatRelativeTime(Date.now() - 2 * 24 * 60 * 60 * 1000); // 2 days ago
      expect(result).toBe('2d ago');
    });
  });

  describe('formatTimeRemaining', () => {
    it('should return "Expired" for past timestamps', () => {
      const result = formatTimeRemaining(Date.now() - 1000);
      expect(result).toBe('Expired');
    });

    it('should format seconds remaining', () => {
      const result = formatTimeRemaining(Date.now() + 45000); // 45 seconds
      expect(result).toMatch(/\d+s/);
    });

    it('should format minutes and seconds remaining', () => {
      const result = formatTimeRemaining(Date.now() + 90000); // 1.5 minutes
      expect(result).toMatch(/1m \d+s/);
    });
  });

  describe('formatUSD', () => {
    it('should format number as USD', () => {
      const result = formatUSD(1234.56);
      expect(result).toBe('$1,234.56');
    });

    it('should respect decimal places', () => {
      const result = formatUSD(100, 0);
      expect(result).toBe('$100');
    });

    it('should handle zero', () => {
      const result = formatUSD(0);
      expect(result).toBe('$0.00');
    });

    it('should handle large numbers', () => {
      const result = formatUSD(1000000);
      expect(result).toBe('$1,000,000.00');
    });
  });

  describe('formatPercentage', () => {
    it('should format decimal as percentage', () => {
      expect(formatPercentage(0.85)).toBe('85%');
      expect(formatPercentage(0.5)).toBe('50%');
      expect(formatPercentage(1)).toBe('100%');
    });

    it('should round to nearest integer', () => {
      expect(formatPercentage(0.333)).toBe('33%');
      expect(formatPercentage(0.666)).toBe('67%');
    });

    it('should handle zero', () => {
      expect(formatPercentage(0)).toBe('0%');
    });
  });

  describe('truncate', () => {
    it('should not truncate short text', () => {
      const result = truncate('Hello', 10);
      expect(result).toBe('Hello');
    });

    it('should truncate long text with ellipsis', () => {
      const result = truncate('This is a very long text', 10);
      expect(result).toBe('This is a ...');
    });

    it('should handle exact length', () => {
      const result = truncate('12345', 5);
      expect(result).toBe('12345');
    });
  });

  describe('truncateEndpoint', () => {
    it('should truncate long endpoints', () => {
      const endpoint = 'http://localhost:8080/api/v1/agents/connect';
      const result = truncateEndpoint(endpoint, 20);
      expect(result).toBe('http://localhost:808...');
    });

    it('should not truncate short endpoints', () => {
      const endpoint = 'http://localhost';
      const result = truncateEndpoint(endpoint);
      expect(result).toBe('http://localhost');
    });
  });

  describe('formatCompactNumber', () => {
    it('should format thousands', () => {
      const result = formatCompactNumber(1500);
      expect(result).toMatch(/1\.?5?K/);
    });

    it('should format millions', () => {
      const result = formatCompactNumber(1500000);
      expect(result).toMatch(/1\.?5?M/);
    });

    it('should not compact small numbers', () => {
      const result = formatCompactNumber(100);
      expect(result).toBe('100');
    });
  });
});
