/**
 * Memory integrity unit tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import {
  MemoryIntegrityChecker,
  createMemoryIntegrityChecker,
  hasIntegrityMetadata,
  getMemorySource,
  getSignedTimestamp,
  type MemorySource,
} from './memory-integrity';
import type { Memory, UUID } from './types';

// Helper to create test memory
function createTestMemory(text: string): Memory {
  return {
    entityId: 'test-entity-123' as UUID,
    roomId: 'test-room-456' as UUID,
    content: { text },
  };
}

describe('MemoryIntegrityChecker', () => {
  let checker: MemoryIntegrityChecker;

  beforeEach(() => {
    checker = new MemoryIntegrityChecker({ secretKey: 'test-secret-key-12345' });
  });

  describe('signMemory', () => {
    it('should sign a memory with integrity metadata', () => {
      const memory = createTestMemory('Hello world');
      const signed = checker.signMemory(memory, 'user_direct');
      const metadata = signed.content?.metadata as Record<string, unknown>;

      expect(metadata).toBeDefined();
      expect(metadata?.sentinel_integrity_hash).toBeDefined();
      expect(metadata?.sentinel_signed_at).toBeDefined();
      expect(metadata?.sentinel_source).toBe('user_direct');
      expect(metadata?.sentinel_integrity_version).toBe('1.0');
    });

    it('should preserve original memory content', () => {
      const memory = createTestMemory('Original content');
      const signed = checker.signMemory(memory, 'user_direct');

      expect(signed.content?.text).toBe('Original content');
      expect(signed.entityId).toBe(memory.entityId);
      expect(signed.roomId).toBe(memory.roomId);
    });

    it('should use unknown source by default', () => {
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory);
      const metadata = signed.content?.metadata as Record<string, unknown>;

      expect(metadata?.sentinel_source).toBe('unknown');
    });
  });

  describe('verifyMemory', () => {
    it('should verify valid signed memory', () => {
      const memory = createTestMemory('Test content');
      const signed = checker.signMemory(memory, 'user_direct');
      const result = checker.verifyMemory(signed);

      expect(result.valid).toBe(true);
      expect(result.source).toBe('user_direct');
      expect(result.trustScore).toBe(0.9); // user_direct score
    });

    it('should fail for unsigned memory', () => {
      const memory = createTestMemory('Unsigned content');
      const result = checker.verifyMemory(memory);

      expect(result.valid).toBe(false);
      expect(result.reason).toContain('Missing integrity metadata');
    });

    it('should fail for tampered memory', () => {
      const memory = createTestMemory('Original content');
      const signed = checker.signMemory(memory, 'user_direct');

      // Tamper with the content
      signed.content!.text = 'Tampered content';

      const result = checker.verifyMemory(signed);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('tampered');
    });

    it('should fail for wrong version', () => {
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory, 'user_direct');

      // Change version
      (signed.content!.metadata as any).sentinel_integrity_version = '2.0';

      const result = checker.verifyMemory(signed);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('Version mismatch');
    });
  });

  describe('Trust scores', () => {
    const sources: Array<{ source: MemorySource; expectedScore: number }> = [
      { source: 'user_verified', expectedScore: 1.0 },
      { source: 'user_direct', expectedScore: 0.9 },
      { source: 'blockchain', expectedScore: 0.85 },
      { source: 'agent_internal', expectedScore: 0.8 },
      { source: 'external_api', expectedScore: 0.7 },
      { source: 'social_media', expectedScore: 0.5 },
      { source: 'unknown', expectedScore: 0.3 },
    ];

    sources.forEach(({ source, expectedScore }) => {
      it(`should assign ${expectedScore} trust score for ${source}`, () => {
        const memory = createTestMemory('Test');
        const signed = checker.signMemory(memory, source);
        const result = checker.verifyMemory(signed);

        expect(result.trustScore).toBe(expectedScore);
      });
    });
  });

  describe('verifyBatch', () => {
    it('should verify multiple memories', () => {
      const memories = [
        checker.signMemory(createTestMemory('Memory 1'), 'user_direct'),
        checker.signMemory(createTestMemory('Memory 2'), 'agent_internal'),
        createTestMemory('Unsigned memory'),
      ];

      const results = checker.verifyBatch(memories);

      expect(results.length).toBe(3);
      expect(results[0].valid).toBe(true);
      expect(results[1].valid).toBe(true);
      expect(results[2].valid).toBe(false);
    });
  });

  describe('filterValid', () => {
    it('should filter out invalid memories', () => {
      const memories = [
        checker.signMemory(createTestMemory('Valid 1'), 'user_direct'),
        createTestMemory('Invalid'),
        checker.signMemory(createTestMemory('Valid 2'), 'agent_internal'),
      ];

      const valid = checker.filterValid(memories);

      expect(valid.length).toBe(2);
      expect(valid[0].content?.text).toBe('Valid 1');
      expect(valid[1].content?.text).toBe('Valid 2');
    });
  });

  describe('meetsThreshold', () => {
    it('should return true when trust score meets threshold', () => {
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory, 'user_direct'); // 0.9 score

      expect(checker.meetsThreshold(signed, 0.5)).toBe(true);
      expect(checker.meetsThreshold(signed, 0.9)).toBe(true);
    });

    it('should return false when trust score below threshold', () => {
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory, 'unknown'); // 0.3 score

      expect(checker.meetsThreshold(signed, 0.5)).toBe(false);
    });

    it('should return false for invalid memory', () => {
      const memory = createTestMemory('Unsigned');
      expect(checker.meetsThreshold(memory, 0.1)).toBe(false);
    });
  });

  describe('Different secret keys', () => {
    it('should fail verification with different secret key', () => {
      const checker1 = new MemoryIntegrityChecker({ secretKey: 'key-1' });
      const checker2 = new MemoryIntegrityChecker({ secretKey: 'key-2' });

      const memory = createTestMemory('Test');
      const signed = checker1.signMemory(memory, 'user_direct');

      const result = checker2.verifyMemory(signed);
      expect(result.valid).toBe(false);
    });
  });

  describe('Algorithm options', () => {
    it('should work with sha384 algorithm', () => {
      const checker384 = new MemoryIntegrityChecker({
        secretKey: 'test-key',
        algorithm: 'sha384',
      });

      const memory = createTestMemory('Test');
      const signed = checker384.signMemory(memory, 'user_direct');
      const result = checker384.verifyMemory(signed);

      expect(result.valid).toBe(true);
    });

    it('should work with sha512 algorithm', () => {
      const checker512 = new MemoryIntegrityChecker({
        secretKey: 'test-key',
        algorithm: 'sha512',
      });

      const memory = createTestMemory('Test');
      const signed = checker512.signMemory(memory, 'user_direct');
      const result = checker512.verifyMemory(signed);

      expect(result.valid).toBe(true);
    });
  });
});

describe('createMemoryIntegrityChecker', () => {
  it('should create checker with provided key', () => {
    const checker = createMemoryIntegrityChecker('my-secret');
    const memory = createTestMemory('Test');
    const signed = checker.signMemory(memory, 'user_direct');
    const result = checker.verifyMemory(signed);

    expect(result.valid).toBe(true);
  });

  it('should create checker with auto-generated key', () => {
    const checker = createMemoryIntegrityChecker();
    const memory = createTestMemory('Test');
    const signed = checker.signMemory(memory, 'user_direct');
    const result = checker.verifyMemory(signed);

    expect(result.valid).toBe(true);
  });
});

// Bug fix verification tests
describe('Bug fixes verification', () => {
  describe('M003/M004 - MemoryIntegrityChecker null handling', () => {
    let checker: MemoryIntegrityChecker;

    beforeEach(() => {
      checker = new MemoryIntegrityChecker({ secretKey: 'test-key' });
    });

    it('signMemory should throw on null input', () => {
      expect(() => checker.signMemory(null as any)).toThrow('Memory cannot be null or undefined');
    });

    it('signMemory should throw on undefined input', () => {
      expect(() => checker.signMemory(undefined as any)).toThrow('Memory cannot be null or undefined');
    });

    it('verifyMemory should return valid=false for null', () => {
      const result = checker.verifyMemory(null as any);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('null or undefined');
    });

    it('verifyMemory should return valid=false for undefined', () => {
      const result = checker.verifyMemory(undefined as any);
      expect(result.valid).toBe(false);
      expect(result.reason).toContain('null or undefined');
    });
  });

  describe('Helper functions null handling', () => {
    it('hasIntegrityMetadata should return false for null', () => {
      expect(hasIntegrityMetadata(null as any)).toBe(false);
    });

    it('hasIntegrityMetadata should return false for undefined', () => {
      expect(hasIntegrityMetadata(undefined as any)).toBe(false);
    });

    it('getMemorySource should return unknown for null', () => {
      expect(getMemorySource(null as any)).toBe('unknown');
    });

    it('getMemorySource should return unknown for undefined', () => {
      expect(getMemorySource(undefined as any)).toBe('unknown');
    });

    it('getSignedTimestamp should return undefined for null', () => {
      expect(getSignedTimestamp(null as any)).toBeUndefined();
    });

    it('getSignedTimestamp should return undefined for undefined', () => {
      expect(getSignedTimestamp(undefined as any)).toBeUndefined();
    });
  });
});

describe('Helper functions', () => {
  let checker: MemoryIntegrityChecker;

  beforeEach(() => {
    checker = createMemoryIntegrityChecker('test-key');
  });

  describe('hasIntegrityMetadata', () => {
    it('should return true for signed memory', () => {
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory, 'user_direct');

      expect(hasIntegrityMetadata(signed)).toBe(true);
    });

    it('should return false for unsigned memory', () => {
      const memory = createTestMemory('Test');
      expect(hasIntegrityMetadata(memory)).toBe(false);
    });
  });

  describe('getMemorySource', () => {
    it('should return source from signed memory', () => {
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory, 'blockchain');

      expect(getMemorySource(signed)).toBe('blockchain');
    });

    it('should return unknown for unsigned memory', () => {
      const memory = createTestMemory('Test');
      expect(getMemorySource(memory)).toBe('unknown');
    });
  });

  describe('getSignedTimestamp', () => {
    it('should return timestamp from signed memory', () => {
      const before = Date.now();
      const memory = createTestMemory('Test');
      const signed = checker.signMemory(memory, 'user_direct');
      const after = Date.now();

      const timestamp = getSignedTimestamp(signed);
      expect(timestamp).toBeGreaterThanOrEqual(before);
      expect(timestamp).toBeLessThanOrEqual(after);
    });

    it('should return undefined for unsigned memory', () => {
      const memory = createTestMemory('Test');
      expect(getSignedTimestamp(memory)).toBeUndefined();
    });
  });
});
