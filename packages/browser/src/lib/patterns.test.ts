/**
 * Unit tests for Sentinel Guard - Detection Patterns
 *
 * Tests all functions and validates bug fixes from audit #053.
 */

import {
  scanForSecrets,
  scanForPII,
  scanAll,
  maskSensitiveData,
  PatternMatch,
} from './patterns';

// =============================================================================
// Null Handling Tests (C004)
// =============================================================================

describe('Null Handling', () => {
  describe('scanForSecrets', () => {
    it('should return empty array for null input', () => {
      expect(scanForSecrets(null as unknown as string)).toEqual([]);
    });

    it('should return empty array for undefined input', () => {
      expect(scanForSecrets(undefined as unknown as string)).toEqual([]);
    });

    it('should return empty array for non-string input', () => {
      expect(scanForSecrets(123 as unknown as string)).toEqual([]);
      expect(scanForSecrets({} as unknown as string)).toEqual([]);
      expect(scanForSecrets([] as unknown as string)).toEqual([]);
    });

    it('should return empty array for empty string', () => {
      expect(scanForSecrets('')).toEqual([]);
    });
  });

  describe('scanForPII', () => {
    it('should return empty array for null input', () => {
      expect(scanForPII(null as unknown as string)).toEqual([]);
    });

    it('should return empty array for undefined input', () => {
      expect(scanForPII(undefined as unknown as string)).toEqual([]);
    });

    it('should return empty array for non-string input', () => {
      expect(scanForPII(123 as unknown as string)).toEqual([]);
    });
  });

  describe('scanAll', () => {
    it('should return empty array for null input', () => {
      expect(scanAll(null as unknown as string)).toEqual([]);
    });

    it('should return empty array for undefined input', () => {
      expect(scanAll(undefined as unknown as string)).toEqual([]);
    });
  });

  describe('maskSensitiveData', () => {
    it('should return empty string for null text', () => {
      expect(maskSensitiveData(null as unknown as string, [])).toBe('');
    });

    it('should return original text for null matches', () => {
      expect(maskSensitiveData('test', null as unknown as PatternMatch[])).toBe('test');
    });

    it('should return original text for empty matches array', () => {
      expect(maskSensitiveData('test', [])).toBe('test');
    });
  });
});

// =============================================================================
// BIP39 Seed Phrase Detection (C002)
// =============================================================================

describe('Seed Phrase Detection (C002)', () => {
  it('should NOT detect regular 12-word sentences as seed phrases', () => {
    const normalText = 'The quick brown fox jumps over the lazy dog and runs away';
    const matches = scanForSecrets(normalText);
    const seedMatches = matches.filter(m => m.type.includes('seed_phrase'));
    expect(seedMatches.length).toBe(0);
  });

  it('should NOT detect text with common words as seed phrases', () => {
    const textWithCommonWords = 'I will not have what you are looking for but they would be here';
    const matches = scanForSecrets(textWithCommonWords);
    const seedMatches = matches.filter(m => m.type.includes('seed_phrase'));
    expect(seedMatches.length).toBe(0);
  });

  it('should detect actual BIP39 seed phrases', () => {
    // These are real BIP39 words (example - not a real wallet)
    const seedPhrase = 'abandon ability able about above absent absorb abstract absurd abuse access accident';
    const matches = scanForSecrets(seedPhrase);
    const seedMatches = matches.filter(m => m.type.includes('seed_phrase'));
    expect(seedMatches.length).toBeGreaterThan(0);
  });
});

// =============================================================================
// SSN Detection (M007)
// =============================================================================

describe('SSN Detection (M007)', () => {
  it('should detect actual SSN patterns', () => {
    const text = 'My SSN is 123-45-6789';
    const matches = scanForPII(text);
    const ssnMatches = matches.filter(m => m.type === 'ssn');
    expect(ssnMatches.length).toBe(1);
  });

  it('should NOT detect phone numbers as SSN', () => {
    const text = 'Call me at phone: 123-45-6789';
    const matches = scanForPII(text);
    const ssnMatches = matches.filter(m => m.type === 'ssn');
    expect(ssnMatches.length).toBe(0);
  });

  it('should NOT detect telephone numbers as SSN', () => {
    const text = 'Tel: 123-45-6789';
    const matches = scanForPII(text);
    const ssnMatches = matches.filter(m => m.type === 'ssn');
    expect(ssnMatches.length).toBe(0);
  });
});

// =============================================================================
// Email Detection (M008)
// =============================================================================

describe('Email Detection (M008)', () => {
  it('should detect actual email addresses', () => {
    const text = 'Contact me at john.doe@example.com';
    const matches = scanForPII(text);
    const emailMatches = matches.filter(m => m.type === 'email');
    expect(emailMatches.length).toBe(1);
  });

  it('should skip code-like patterns starting with @', () => {
    const text = '@decorator function example';
    const matches = scanForPII(text);
    const emailMatches = matches.filter(m => m.type === 'email');
    expect(emailMatches.length).toBe(0);
  });
});

// =============================================================================
// Deduplication Tests (N007)
// =============================================================================

describe('Deduplication (N007)', () => {
  it('should deduplicate overlapping matches', () => {
    const text = 'sk-abcdef1234567890123456789012345678901234567890';
    const matches = scanAll(text);
    // Should not have duplicate matches for the same position
    const positions = matches.map(m => `${m.start}-${m.end}`);
    const uniquePositions = [...new Set(positions)];
    expect(positions.length).toBe(uniquePositions.length);
  });

  it('should keep higher severity matches when overlapping', () => {
    // Create a scenario with potential overlaps
    const text = 'AKIA1234567890123456 some text';
    const matches = scanAll(text);
    // AWS key should be kept (critical) over any lower severity match
    const awsMatches = matches.filter(m => m.type === 'aws_access_key');
    expect(awsMatches.length).toBe(1);
  });
});

// =============================================================================
// Mask Overlap Handling (N008)
// =============================================================================

describe('Mask Overlap Handling (N008)', () => {
  it('should handle overlapping matches without corruption', () => {
    const text = 'secret: password123 and api_key: abc123def456';
    const matches = scanAll(text);
    const masked = maskSensitiveData(text, matches);
    // Should not produce undefined or corrupted text
    expect(masked).toBeDefined();
    expect(masked.includes('undefined')).toBe(false);
    expect(masked.length).toBeGreaterThan(0);
  });

  it('should handle matches with invalid indices', () => {
    const text = 'some text';
    const invalidMatches: PatternMatch[] = [
      { type: 'test', value: 'test', start: -1, end: 5, severity: 'low', message: 'test' },
      { type: 'test', value: 'test', start: 0, end: 100, severity: 'low', message: 'test' },
      { type: 'test', value: 'test', start: 5, end: 3, severity: 'low', message: 'test' },
    ];
    const masked = maskSensitiveData(text, invalidMatches);
    // Should return original text when all matches are invalid
    expect(masked).toBe(text);
  });
});

// =============================================================================
// Secret Pattern Detection
// =============================================================================

describe('Secret Pattern Detection', () => {
  it('should detect AWS access keys', () => {
    const text = 'AWS key: AKIA1234567890ABCDEF';
    const matches = scanForSecrets(text);
    expect(matches.some(m => m.type === 'aws_access_key')).toBe(true);
  });

  it('should detect GitHub tokens', () => {
    const text = 'Token: ghp_abcdefghijklmnopqrstuvwxyz1234567890';
    const matches = scanForSecrets(text);
    expect(matches.some(m => m.type === 'github_token')).toBe(true);
  });

  it('should detect OpenAI keys', () => {
    const text = 'API: sk-abcdefghijklmnopqrstuvwxyz1234567890123456789012';
    const matches = scanForSecrets(text);
    expect(matches.some(m => m.type === 'openai_key')).toBe(true);
  });

  it('should detect private key headers', () => {
    const text = '-----BEGIN PRIVATE KEY-----';
    const matches = scanForSecrets(text);
    expect(matches.some(m => m.type === 'private_key_header')).toBe(true);
  });

  it('should detect database connection strings', () => {
    const text = 'mongodb://user:pass@host:27017/db';
    const matches = scanForSecrets(text);
    expect(matches.some(m => m.type === 'connection_string')).toBe(true);
  });
});

// =============================================================================
// PII Pattern Detection
// =============================================================================

describe('PII Pattern Detection', () => {
  it('should detect credit card numbers', () => {
    const text = 'Card: 4111-1111-1111-1111';
    const matches = scanForPII(text);
    expect(matches.some(m => m.type === 'credit_card')).toBe(true);
  });

  it('should detect CPF (Brazilian ID)', () => {
    const text = 'CPF: 123.456.789-00';
    const matches = scanForPII(text);
    expect(matches.some(m => m.type === 'cpf')).toBe(true);
  });

  it('should detect US phone numbers', () => {
    const text = 'Call: (555) 123-4567';
    const matches = scanForPII(text);
    expect(matches.some(m => m.type === 'phone_us')).toBe(true);
  });

  it('should detect passwords in context', () => {
    const text = 'password: supersecret123';
    const matches = scanForPII(text);
    expect(matches.some(m => m.type === 'password_context')).toBe(true);
  });
});

// =============================================================================
// Severity Assignment
// =============================================================================

describe('Severity Assignment', () => {
  it('should assign critical severity to AWS keys', () => {
    const text = 'AKIA1234567890ABCDEF';
    const matches = scanForSecrets(text);
    const awsMatch = matches.find(m => m.type === 'aws_access_key');
    expect(awsMatch?.severity).toBe('critical');
  });

  it('should assign high severity to GitHub tokens', () => {
    const text = 'ghp_abcdefghijklmnopqrstuvwxyz1234567890';
    const matches = scanForSecrets(text);
    const ghMatch = matches.find(m => m.type === 'github_token');
    expect(ghMatch?.severity).toBe('high');
  });

  it('should assign low severity to emails', () => {
    const text = 'test@example.com';
    const matches = scanForPII(text);
    const emailMatch = matches.find(m => m.type === 'email');
    expect(emailMatch?.severity).toBe('low');
  });
});
