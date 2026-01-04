/**
 * Streaming Guardrail Tests
 *
 * Tests for the streaming PII redaction and content processing.
 */

import { describe, it, expect, vi } from 'vitest';
import {
  createSentinelPIIRedactor,
  createStrictStreamingRedactor,
  createPermissiveStreamingRedactor,
  createMonitoringStreamHandler,
  createStreamingState,
} from '../guardrails/streaming';

// Helper to create async iterable from array
async function* createTextStream(texts: string[]): AsyncIterable<string> {
  for (const text of texts) {
    yield text;
  }
}

// Helper to collect all chunks from async generator
async function collectChunks(
  generator: AsyncGenerator<string, void, unknown>
): Promise<string[]> {
  const chunks: string[] = [];
  for await (const chunk of generator) {
    chunks.push(chunk);
  }
  return chunks;
}

describe('createStreamingState', () => {
  it('should create initial streaming state', () => {
    const state = createStreamingState();

    expect(state.buffer).toBe('');
    expect(state.piiMatches).toEqual([]);
    expect(state.violationDetected).toBe(false);
    expect(state.chunkIndex).toBe(0);
  });
});

describe('createSentinelPIIRedactor', () => {
  describe('basic functionality', () => {
    it('should create a stream handler function', () => {
      const redactor = createSentinelPIIRedactor();
      expect(typeof redactor).toBe('function');
    });

    it('should process text stream without PII', async () => {
      const redactor = createSentinelPIIRedactor();
      const textStream = createTextStream(['Hello, ', 'how are ', 'you today?']);

      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      expect(result).toContain('Hello');
      expect(result).toContain('you');
    });

    it('should redact email addresses in stream', async () => {
      const redactor = createSentinelPIIRedactor({
        enablePII: true,
        minBufferSize: 10,
        maxBufferSize: 100,
      });

      const textStream = createTextStream([
        'Contact: ',
        'john@',
        'example.com',
        ' for help.',
      ]);

      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      expect(result).toContain('[EMAIL]');
      expect(result).not.toContain('john@example.com');
    });

    it('should redact phone numbers in stream', async () => {
      const redactor = createSentinelPIIRedactor({
        enablePII: true,
        minBufferSize: 5,
        maxBufferSize: 100,
      });

      // Use larger chunks so phone number is in a single buffer
      const textStream = createTextStream([
        'Call me at 555-123-4567 anytime.',
      ]);

      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      expect(result).toContain('[PHONE]');
      expect(result).not.toContain('555-123-4567');
    });

    it('should handle empty stream', async () => {
      const redactor = createSentinelPIIRedactor();
      const textStream = createTextStream([]);

      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);

      expect(chunks).toHaveLength(0);
    });
  });

  describe('configuration options', () => {
    it('should respect enablePII: false', async () => {
      const redactor = createSentinelPIIRedactor({ enablePII: false });
      const textStream = createTextStream(['Email: test@example.com']);

      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      // PII should NOT be redacted when disabled
      expect(result).toContain('test@example.com');
    });

    it('should only redact specified PII types', async () => {
      const redactor = createSentinelPIIRedactor({
        enablePII: true,
        piiTypes: ['EMAIL'],
        minBufferSize: 5,
        maxBufferSize: 100,
      });

      const textStream = createTextStream([
        'Email: test@example.com, ',
        'SSN: 123-45-6789',
      ]);

      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      expect(result).toContain('[EMAIL]');
      // SSN should NOT be redacted when only EMAIL is specified
      expect(result).toContain('123-45-6789');
    });

    it('should call logger on stream completion', async () => {
      const logger = vi.fn();
      const redactor = createSentinelPIIRedactor({
        enablePII: true,
        logger,
      });

      const textStream = createTextStream(['Hello world']);
      const generator = redactor({ textStream });
      await collectChunks(generator);

      expect(logger).toHaveBeenCalledWith(
        'Stream processing completed',
        expect.objectContaining({ chunks: expect.any(Number) })
      );
    });

    it('should use custom redaction format', async () => {
      const redactor = createSentinelPIIRedactor({
        enablePII: true,
        redactionFormat: '***HIDDEN***',
        minBufferSize: 5,
        maxBufferSize: 100,
      });

      const textStream = createTextStream(['Email: test@example.com']);
      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      expect(result).toContain('***HIDDEN***');
    });
  });

  describe('sensitive data detection', () => {
    it('should detect sensitive data when enabled', async () => {
      const logger = vi.fn();
      const redactor = createSentinelPIIRedactor({
        enableSensitiveDataCheck: true,
        abortOnSensitiveData: false,
        logger,
      });

      const textStream = createTextStream(['password=secret123']);
      const generator = redactor({ textStream });
      await collectChunks(generator);

      // Should complete without aborting
      expect(logger).toHaveBeenCalled();
    });

    it('should abort stream on sensitive data when configured', async () => {
      const logger = vi.fn();
      const redactor = createSentinelPIIRedactor({
        enableSensitiveDataCheck: true,
        abortOnSensitiveData: true,
        logger,
      });

      const textStream = createTextStream(['Your password=secret123 is exposed']);
      const generator = redactor({ textStream });
      const chunks = await collectChunks(generator);
      const result = chunks.join('');

      expect(result).toContain('blocked');
      expect(logger).toHaveBeenCalledWith(
        'Stream aborted',
        expect.objectContaining({ reason: expect.any(String) })
      );
    });
  });
});

describe('createStrictStreamingRedactor', () => {
  it('should create a strict redactor that aborts on sensitive content', async () => {
    const redactor = createStrictStreamingRedactor();
    const textStream = createTextStream(['api_key=sk_live_secret']);

    const generator = redactor({ textStream });
    const chunks = await collectChunks(generator);
    const result = chunks.join('');

    expect(result).toContain('blocked');
  });

  it('should still redact PII in normal content', async () => {
    const redactor = createStrictStreamingRedactor({
      minBufferSize: 5,
      maxBufferSize: 100,
    });
    const textStream = createTextStream(['Hello test@example.com']);

    const generator = redactor({ textStream });
    const chunks = await collectChunks(generator);
    const result = chunks.join('');

    expect(result).toContain('[EMAIL]');
  });
});

describe('createPermissiveStreamingRedactor', () => {
  it('should only redact PII without blocking', async () => {
    const redactor = createPermissiveStreamingRedactor(['EMAIL']);
    const textStream = createTextStream([
      'Email: test@example.com, ',
      'password=secret',
    ]);

    const generator = redactor({ textStream });
    const chunks = await collectChunks(generator);
    const result = chunks.join('');

    // Should redact email but not block password
    expect(result).toContain('[EMAIL]');
    expect(result).toContain('password=secret');
  });

  it('should redact all PII types when no types specified', async () => {
    const redactor = createPermissiveStreamingRedactor();
    const textStream = createTextStream(['SSN: 123-45-6789']);

    const generator = redactor({ textStream });
    const chunks = await collectChunks(generator);
    const result = chunks.join('');

    expect(result).toContain('[SSN]');
  });
});

describe('createMonitoringStreamHandler', () => {
  it('should detect PII but pass through unmodified', async () => {
    const logger = vi.fn();
    const handler = createMonitoringStreamHandler(logger);
    const textStream = createTextStream(['Email: test@example.com']);

    const generator = handler({ textStream });
    const chunks = await collectChunks(generator);
    const result = chunks.join('');

    // Content should be unchanged
    expect(result).toContain('test@example.com');

    // But PII should be logged
    expect(logger).toHaveBeenCalledWith(
      'PII detected in chunk',
      expect.objectContaining({
        chunkIndex: expect.any(Number),
        count: expect.any(Number),
      })
    );
  });

  it('should log completion summary', async () => {
    const logger = vi.fn();
    const handler = createMonitoringStreamHandler(logger);
    const textStream = createTextStream(['Hello', 'World']);

    const generator = handler({ textStream });
    await collectChunks(generator);

    expect(logger).toHaveBeenCalledWith(
      'Stream monitoring completed',
      expect.objectContaining({
        totalChunks: 2,
        totalPIIInstances: 0,
      })
    );
  });

  it('should count total PII instances across stream', async () => {
    const logger = vi.fn();
    const handler = createMonitoringStreamHandler(logger);
    const textStream = createTextStream([
      'Email: a@b.com, ',
      'Phone: 555-123-4567',
    ]);

    const generator = handler({ textStream });
    await collectChunks(generator);

    expect(logger).toHaveBeenCalledWith(
      'Stream monitoring completed',
      expect.objectContaining({
        totalPIIInstances: 2,
      })
    );
  });
});
