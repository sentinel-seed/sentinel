/**
 * Output Guardrail Tests
 *
 * Tests for the VoltAgent output guardrail factory.
 */

import { describe, it, expect, vi } from 'vitest';
import {
  createSentinelOutputGuardrail,
  createPIIOutputGuardrail,
  createStrictOutputGuardrail,
  createPermissiveOutputGuardrail,
} from '../guardrails/output';
import type { VoltAgentOutputArgs } from '../types';

// Helper to create output args
function createOutputArgs<T>(outputText: string, output?: T): VoltAgentOutputArgs<T> {
  return {
    output: (output ?? outputText) as T,
    outputText,
    originalOutput: (output ?? outputText) as T,
  };
}

describe('createSentinelOutputGuardrail', () => {
  describe('basic functionality', () => {
    it('should create a valid guardrail object', () => {
      const guardrail = createSentinelOutputGuardrail();

      expect(guardrail.name).toBe('sentinel-output-guardrail');
      expect(guardrail.description).toBeDefined();
      expect(guardrail.tags).toContain('pii');
      expect(typeof guardrail.handler).toBe('function');
      expect(typeof guardrail.streamHandler).toBe('function');
    });

    it('should allow safe content', async () => {
      const guardrail = createSentinelOutputGuardrail();
      const result = await guardrail.handler(
        createOutputArgs('This is a normal response.')
      );

      expect(result.pass).toBe(true);
      expect(result.action).toBe('allow');
    });

    it('should allow content with no PII', async () => {
      const guardrail = createSentinelOutputGuardrail({ enablePII: true });
      const result = await guardrail.handler(
        createOutputArgs('The weather today is sunny.')
      );

      expect(result.pass).toBe(true);
    });
  });

  describe('PII handling', () => {
    it('should detect and redact email addresses', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enablePII: true,
        redactPII: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('Contact: john@example.com')
      );

      expect(result.pass).toBe(true);
      expect(result.action).toBe('modify');
      expect(result.modifiedOutput).toContain('[EMAIL]');
      expect(result.modifiedOutput).not.toContain('john@example.com');
    });

    it('should detect and redact phone numbers', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enablePII: true,
        redactPII: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('Call: 555-123-4567')
      );

      expect(result.pass).toBe(true);
      expect(result.action).toBe('modify');
      expect(result.modifiedOutput).toContain('[PHONE]');
    });

    it('should detect and redact SSN', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enablePII: true,
        redactPII: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('SSN: 123-45-6789')
      );

      expect(result.pass).toBe(true);
      expect(result.action).toBe('modify');
      expect(result.modifiedOutput).toContain('[SSN]');
    });

    it('should redact multiple PII types', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enablePII: true,
        redactPII: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('Email: test@test.com, Phone: 555-111-2222, SSN: 123-45-6789')
      );

      expect(result.action).toBe('modify');
      expect(result.modifiedOutput).toContain('[EMAIL]');
      expect(result.modifiedOutput).toContain('[PHONE]');
      expect(result.modifiedOutput).toContain('[SSN]');
    });

    it('should respect piiTypes filter', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enablePII: true,
        redactPII: true,
        piiTypes: ['EMAIL'],
      });

      const result = await guardrail.handler(
        createOutputArgs('Email: test@test.com, SSN: 123-45-6789')
      );

      expect(result.modifiedOutput).toContain('[EMAIL]');
      expect(result.modifiedOutput).toContain('123-45-6789'); // SSN not redacted
    });
  });

  describe('sensitive data detection (OWASP)', () => {
    it('should detect exposed passwords', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enableOWASP: true,
        blockUnsafe: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('Your password is: password=secret123')
      );

      expect(result.pass).toBe(false);
      expect(result.action).toBe('block');
    });

    it('should detect exposed API keys', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enableOWASP: true,
        blockUnsafe: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('API Key: api_key=sk_live_abc123')
      );

      expect(result.pass).toBe(false);
    });

    it('should detect exposed AWS keys', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enableOWASP: true,
        blockUnsafe: true,
      });

      const result = await guardrail.handler(
        createOutputArgs('AWS: AKIAIOSFODNN7EXAMPLE')
      );

      expect(result.pass).toBe(false);
    });
  });

  describe('configuration', () => {
    it('should respect enablePII: false', async () => {
      const guardrail = createSentinelOutputGuardrail({ enablePII: false });

      const result = await guardrail.handler(
        createOutputArgs('Email: test@example.com')
      );

      // Should not modify since PII is disabled
      expect(result.action).not.toBe('modify');
    });

    it('should call logger when logChecks is true', async () => {
      const logger = vi.fn();
      const guardrail = createSentinelOutputGuardrail({
        logChecks: true,
        logger,
      });

      await guardrail.handler(createOutputArgs('Hello'));

      expect(logger).toHaveBeenCalled();
    });
  });

  describe('streaming handler', () => {
    it('should process streaming chunks', async () => {
      const guardrail = createSentinelOutputGuardrail({
        enablePII: true,
        redactPII: true,
      });

      const chunks = ['Hello ', 'test@', 'example.com', ' world'];
      const outputChunks: string[] = [];

      async function* createStream(): AsyncGenerator<string> {
        for (const chunk of chunks) {
          yield chunk;
        }
      }

      for await (const chunk of guardrail.streamHandler!({ textStream: createStream() })) {
        outputChunks.push(chunk);
      }

      const fullOutput = outputChunks.join('');
      expect(fullOutput).toContain('[EMAIL]');
      expect(fullOutput).not.toContain('test@example.com');
    });
  });

  describe('empty and invalid input', () => {
    it('should handle empty output', async () => {
      const guardrail = createSentinelOutputGuardrail();
      const result = await guardrail.handler(createOutputArgs(''));

      expect(result.pass).toBe(true);
    });

    it('should handle null output', async () => {
      const guardrail = createSentinelOutputGuardrail();
      const result = await guardrail.handler({
        output: null,
        outputText: null as unknown as string,
        originalOutput: null,
      });

      expect(result.pass).toBe(true);
    });
  });

  describe('object output handling', () => {
    it('should modify object output with text property', async () => {
      const guardrail = createSentinelOutputGuardrail<{ text: string }>({
        enablePII: true,
        redactPII: true,
      });

      const result = await guardrail.handler({
        output: { text: 'Email: test@example.com' },
        outputText: 'Email: test@example.com',
        originalOutput: { text: 'Email: test@example.com' },
      });

      expect(result.action).toBe('modify');
      expect((result.modifiedOutput as { text: string }).text).toContain('[EMAIL]');
    });
  });
});

describe('createPIIOutputGuardrail', () => {
  it('should create a PII-focused guardrail', async () => {
    const guardrail = createPIIOutputGuardrail();

    const result = await guardrail.handler(
      createOutputArgs('Email: test@example.com')
    );

    expect(result.action).toBe('modify');
    expect(result.modifiedOutput).toContain('[EMAIL]');
  });

  it('should respect piiTypes option', async () => {
    const guardrail = createPIIOutputGuardrail({
      piiTypes: ['SSN'],
    });

    const result = await guardrail.handler(
      createOutputArgs('Email: test@test.com, SSN: 123-45-6789')
    );

    // Only SSN should be redacted
    expect(result.modifiedOutput).toContain('[SSN]');
    expect(result.modifiedOutput).toContain('test@test.com');
  });
});

describe('createStrictOutputGuardrail', () => {
  it('should block on any unsafe content', async () => {
    const guardrail = createStrictOutputGuardrail();

    // Should block on sensitive data
    const result = await guardrail.handler(
      createOutputArgs('password=secret')
    );

    expect(result.pass).toBe(false);
  });
});

describe('createPermissiveOutputGuardrail', () => {
  it('should only redact PII without blocking', async () => {
    const logger = vi.fn();
    const guardrail = createPermissiveOutputGuardrail(logger);

    const result = await guardrail.handler(
      createOutputArgs('Email: test@test.com, password=secret')
    );

    // Should redact email but not block on password
    expect(result.pass).toBe(true);
    expect(result.modifiedOutput).toContain('[EMAIL]');
    expect(logger).toHaveBeenCalled();
  });
});
