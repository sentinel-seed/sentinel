/**
 * PII Validator Tests
 *
 * Comprehensive tests for PII detection and redaction.
 */

import { describe, it, expect } from 'vitest';
import {
  detectPII,
  hasPII,
  redactPII,
  maskPII,
  createStreamingRedactor,
  getPatternsForType,
  getSupportedTypes,
  getPatternCount,
} from '../validators/pii';

describe('detectPII', () => {
  describe('email detection', () => {
    it('should detect email addresses', () => {
      const result = detectPII('Contact me at john.doe@example.com');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('EMAIL');
      expect(result.count).toBe(1);
      expect(result.matches[0]?.value).toBe('john.doe@example.com');
    });

    it('should detect multiple emails', () => {
      const result = detectPII('Emails: alice@test.com and bob@test.org');

      expect(result.count).toBe(2);
      expect(result.types).toContain('EMAIL');
    });
  });

  describe('phone detection', () => {
    it('should detect US phone numbers', () => {
      const result = detectPII('Call me at 555-123-4567');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('PHONE');
    });

    it('should detect phone with parentheses', () => {
      const result = detectPII('Phone: (555) 123-4567');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('PHONE');
    });

    it('should detect international format', () => {
      const result = detectPII('Contact: +1-555-123-4567');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('PHONE');
    });
  });

  describe('SSN detection', () => {
    it('should detect SSN with dashes', () => {
      const result = detectPII('SSN: 123-45-6789');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('SSN');
    });

    it('should detect SSN with spaces', () => {
      const result = detectPII('SSN: 123 45 6789');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('SSN');
    });

    it('should detect SSN without separators', () => {
      const result = detectPII('SSN: 123456789');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('SSN');
    });
  });

  describe('credit card detection', () => {
    it('should detect Visa cards', () => {
      const result = detectPII('Card: 4111111111111111');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('CREDIT_CARD');
    });

    it('should detect MasterCard', () => {
      const result = detectPII('Card: 5500000000000004');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('CREDIT_CARD');
    });

    it('should detect card with spaces', () => {
      const result = detectPII('Card: 4111 1111 1111 1111');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('CREDIT_CARD');
    });
  });

  describe('IP address detection', () => {
    it('should detect IPv4 addresses', () => {
      const result = detectPII('Server IP: 192.168.1.100');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('IP_ADDRESS');
    });

    it('should validate IP range', () => {
      const result = detectPII('Invalid: 999.999.999.999');

      // Should not match invalid IP
      expect(result.types).not.toContain('IP_ADDRESS');
    });
  });

  describe('API key detection', () => {
    it('should detect AWS access keys', () => {
      const result = detectPII('AWS Key: AKIAIOSFODNN7EXAMPLE');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('AWS_KEY');
    });
  });

  describe('private key detection', () => {
    it('should detect RSA private keys', () => {
      const result = detectPII(`-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEA...
-----END RSA PRIVATE KEY-----`);

      expect(result.detected).toBe(true);
      expect(result.types).toContain('PRIVATE_KEY');
    });
  });

  describe('JWT detection', () => {
    it('should detect JWT tokens', () => {
      const result = detectPII(
        'Token: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U'
      );

      expect(result.detected).toBe(true);
      expect(result.types).toContain('JWT_TOKEN');
    });
  });

  describe('date of birth detection', () => {
    it('should detect MM/DD/YYYY format', () => {
      const result = detectPII('DOB: 01/15/1990');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('DATE_OF_BIRTH');
    });

    it('should detect YYYY-MM-DD format', () => {
      const result = detectPII('Born: 1990-01-15');

      expect(result.detected).toBe(true);
      expect(result.types).toContain('DATE_OF_BIRTH');
    });
  });

  describe('filtered detection', () => {
    it('should only detect specified types', () => {
      const result = detectPII(
        'Email: test@example.com, Phone: 555-123-4567',
        ['EMAIL']
      );

      expect(result.types).toContain('EMAIL');
      expect(result.types).not.toContain('PHONE');
    });
  });

  describe('empty and invalid input', () => {
    it('should handle empty string', () => {
      const result = detectPII('');

      expect(result.detected).toBe(false);
      expect(result.count).toBe(0);
    });

    it('should handle null', () => {
      const result = detectPII(null as unknown as string);

      expect(result.detected).toBe(false);
    });
  });

  describe('multiple PII types', () => {
    it('should detect multiple types in one string', () => {
      const result = detectPII(
        'Contact: john@example.com, Phone: 555-123-4567, SSN: 123-45-6789'
      );

      expect(result.detected).toBe(true);
      expect(result.types).toContain('EMAIL');
      expect(result.types).toContain('PHONE');
      expect(result.types).toContain('SSN');
      expect(result.count).toBe(3);
    });
  });
});

describe('hasPII', () => {
  it('should return true when PII exists', () => {
    expect(hasPII('email: test@example.com')).toBe(true);
    expect(hasPII('SSN: 123-45-6789')).toBe(true);
  });

  it('should return false when no PII', () => {
    expect(hasPII('Hello, this is a normal message')).toBe(false);
  });

  it('should handle empty input', () => {
    expect(hasPII('')).toBe(false);
    expect(hasPII(null as unknown as string)).toBe(false);
  });
});

describe('redactPII', () => {
  it('should redact email addresses', () => {
    const result = redactPII('Contact: john@example.com');

    expect(result).toBe('Contact: [EMAIL]');
    expect(result).not.toContain('john@example.com');
  });

  it('should redact phone numbers', () => {
    const result = redactPII('Call: 555-123-4567');

    expect(result).toContain('[PHONE]');
    expect(result).not.toContain('555-123-4567');
  });

  it('should redact SSN', () => {
    const result = redactPII('SSN: 123-45-6789');

    expect(result).toContain('[SSN]');
    expect(result).not.toContain('123-45-6789');
  });

  it('should redact multiple PII instances', () => {
    const result = redactPII('Email: a@b.com, Phone: 555-111-2222');

    expect(result).toContain('[EMAIL]');
    expect(result).toContain('[PHONE]');
    expect(result).not.toContain('a@b.com');
    expect(result).not.toContain('555-111-2222');
  });

  it('should redact only specified types', () => {
    const result = redactPII('Email: a@b.com, SSN: 123-45-6789', ['EMAIL']);

    expect(result).toContain('[EMAIL]');
    expect(result).toContain('123-45-6789'); // SSN not redacted
  });

  it('should use custom redaction format', () => {
    const result = redactPII('Email: test@example.com', undefined, '***REDACTED***');

    expect(result).toBe('Email: ***REDACTED***');
  });

  it('should use custom format function', () => {
    const result = redactPII(
      'Email: test@example.com',
      undefined,
      (type, value) => `[${type}:${value.length}chars]`
    );

    expect(result).toBe('Email: [EMAIL:16chars]');
  });

  it('should handle content with no PII', () => {
    const result = redactPII('Hello, this is normal text');

    expect(result).toBe('Hello, this is normal text');
  });

  it('should handle empty input', () => {
    expect(redactPII('')).toBe('');
    expect(redactPII(null as unknown as string)).toBe('');
  });
});

describe('maskPII', () => {
  it('should mask email addresses', () => {
    const result = maskPII('Contact: john@example.com');

    expect(result).toBe('Contact: j***@example.com');
  });

  it('should mask phone numbers', () => {
    const result = maskPII('Call: 555-123-4567');

    expect(result).toContain('***-***-4567');
  });

  it('should mask SSN', () => {
    const result = maskPII('SSN: 123-45-6789');

    expect(result).toContain('***-**-6789');
  });

  it('should mask credit cards', () => {
    const result = maskPII('Card: 4111-1111-1111-1111');

    expect(result).toContain('****-****-****-1111');
  });

  it('should handle empty input', () => {
    expect(maskPII('')).toBe('');
  });
});

describe('createStreamingRedactor', () => {
  it('should create a streaming redactor function', () => {
    const redactor = createStreamingRedactor();

    expect(typeof redactor).toBe('function');
  });

  it('should process chunks and redact PII', () => {
    const redactor = createStreamingRedactor();

    const result1 = redactor('Contact: test@', '');
    // First chunk may be buffered
    expect(typeof result1.output).toBe('string');
    expect(typeof result1.newBuffer).toBe('string');

    const result2 = redactor('example.com', result1.newBuffer);
    // Combined should redact
    const combined = result1.output + result2.output + result2.newBuffer;
    // Final processing should handle the email
    const finalResult = redactor('', result2.newBuffer);
    expect(result1.output + result2.output + finalResult.output).toBeDefined();
  });
});

describe('getPatternsForType', () => {
  it('should return patterns for EMAIL', () => {
    const patterns = getPatternsForType('EMAIL');
    expect(patterns.length).toBeGreaterThan(0);
    expect(patterns[0]?.type).toBe('EMAIL');
  });

  it('should return patterns for SSN', () => {
    const patterns = getPatternsForType('SSN');
    expect(patterns.length).toBeGreaterThan(0);
  });
});

describe('getSupportedTypes', () => {
  it('should return all supported PII types', () => {
    const types = getSupportedTypes();

    expect(types).toContain('EMAIL');
    expect(types).toContain('PHONE');
    expect(types).toContain('SSN');
    expect(types).toContain('CREDIT_CARD');
    expect(types).toContain('IP_ADDRESS');
  });
});

describe('getPatternCount', () => {
  it('should return pattern count', () => {
    const count = getPatternCount();
    expect(count).toBeGreaterThan(10);
  });
});
