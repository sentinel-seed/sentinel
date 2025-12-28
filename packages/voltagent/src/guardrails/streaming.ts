/**
 * @sentinelseed/voltagent - Streaming Guardrail
 *
 * Specialized streaming handler for real-time content processing.
 * Designed for PII redaction and sensitive content detection during
 * streaming responses.
 */

import type {
  StreamingGuardrailState,
  StreamingChunkResult,
  PIIType,
  PIIPatternDefinition,
} from '../types';
import { redactPII, detectPII, createStreamingRedactor } from '../validators/pii';
import { validateOWASP } from '../validators/owasp';

// =============================================================================
// Streaming Configuration
// =============================================================================

export interface StreamingConfig {
  /** Enable PII redaction */
  enablePII?: boolean;
  /** Specific PII types to redact */
  piiTypes?: PIIType[];
  /** Custom PII patterns */
  customPIIPatterns?: PIIPatternDefinition[];
  /** Custom redaction format */
  redactionFormat?: string | ((type: PIIType, value: string) => string);
  /** Enable sensitive data detection (OWASP) */
  enableSensitiveDataCheck?: boolean;
  /** Abort stream on sensitive data detection */
  abortOnSensitiveData?: boolean;
  /** Minimum buffer size to maintain */
  minBufferSize?: number;
  /** Maximum buffer size before forcing flush */
  maxBufferSize?: number;
  /** Logger function */
  logger?: (message: string, data?: Record<string, unknown>) => void;
}

const DEFAULT_STREAMING_CONFIG: Required<
  Pick<StreamingConfig, 'enablePII' | 'enableSensitiveDataCheck' | 'abortOnSensitiveData' | 'minBufferSize' | 'maxBufferSize'>
> = {
  enablePII: true,
  enableSensitiveDataCheck: false,
  abortOnSensitiveData: false,
  minBufferSize: 50,
  maxBufferSize: 1000,
};

// =============================================================================
// Streaming State
// =============================================================================

/**
 * Create initial streaming state.
 */
export function createStreamingState(): StreamingGuardrailState {
  return {
    buffer: '',
    piiMatches: [],
    violationDetected: false,
    chunkIndex: 0,
  };
}

// =============================================================================
// Streaming Handler Factory
// =============================================================================

/**
 * Create a streaming PII redactor that can be used with VoltAgent's streamHandler.
 *
 * @param config - Streaming configuration
 * @returns Async generator function for stream processing
 *
 * @example
 * ```typescript
 * const piiRedactor = createSentinelPIIRedactor({
 *   enablePII: true,
 *   piiTypes: ['EMAIL', 'PHONE', 'SSN'],
 * });
 *
 * // Use in VoltAgent output guardrail
 * const guardrail = {
 *   name: 'pii-redactor',
 *   handler: async (args) => ({ pass: true }),
 *   streamHandler: piiRedactor,
 * };
 * ```
 */
export function createSentinelPIIRedactor(
  config: StreamingConfig = {}
): (args: { textStream: AsyncIterable<string> }) => AsyncGenerator<string, void, unknown> {
  const mergedConfig = {
    ...DEFAULT_STREAMING_CONFIG,
    ...config,
  };

  return async function* streamHandler({ textStream }): AsyncGenerator<string, void, unknown> {
    let state = createStreamingState();

    for await (const chunk of textStream) {
      const result = processChunk(chunk, state, mergedConfig);

      if (result.abort) {
        // Log abort if logger provided
        if (config.logger) {
          config.logger('Stream aborted', { reason: result.abortMessage });
        }
        // Yield abort message and stop
        yield result.abortMessage ?? '[Content blocked for safety]';
        return;
      }

      // Yield processed text
      if (result.text.length > 0) {
        yield result.text;
      }

      // Update state
      state = result.state;
    }

    // Process any remaining buffer
    if (state.buffer.length > 0) {
      const finalText = processBuffer(state.buffer, mergedConfig);
      if (finalText.length > 0) {
        yield finalText;
      }
    }

    // Log completion if logger provided
    if (config.logger) {
      config.logger('Stream processing completed', {
        chunks: state.chunkIndex,
        piiMatches: state.piiMatches.length,
      });
    }
  };
}

/**
 * Process a single chunk in the stream.
 */
function processChunk(
  chunk: string,
  state: StreamingGuardrailState,
  config: StreamingConfig & typeof DEFAULT_STREAMING_CONFIG
): StreamingChunkResult {
  // Add chunk to buffer
  const newBuffer = state.buffer + chunk;
  const newState: StreamingGuardrailState = {
    ...state,
    buffer: newBuffer,
    chunkIndex: state.chunkIndex + 1,
  };

  // Check for sensitive data if enabled
  if (config.enableSensitiveDataCheck) {
    const sensitiveResult = validateOWASP(newBuffer, ['SENSITIVE_DATA_EXPOSURE']);
    if (!sensitiveResult.safe) {
      newState.violationDetected = true;

      if (config.abortOnSensitiveData) {
        return {
          text: '',
          abort: true,
          abortMessage: '[Response blocked: sensitive data detected]',
          state: newState,
        };
      }
    }
  }

  // Determine how much of the buffer is safe to process
  const { safeText, remainder } = findSafeSplitPoint(
    newBuffer,
    config.minBufferSize,
    config.maxBufferSize
  );

  if (safeText.length === 0) {
    // Keep everything in buffer
    return {
      text: '',
      abort: false,
      state: newState,
    };
  }

  // Process the safe portion
  let processedText = safeText;
  if (config.enablePII) {
    // Detect PII for logging
    const piiResult = detectPII(safeText, config.piiTypes, config.customPIIPatterns);
    if (piiResult.detected) {
      newState.piiMatches = [...state.piiMatches, ...piiResult.matches];
    }

    // Redact PII
    processedText = redactPII(safeText, config.piiTypes, config.redactionFormat);
  }

  newState.buffer = remainder;

  return {
    text: processedText,
    abort: false,
    state: newState,
  };
}

/**
 * Process the final buffer content.
 */
function processBuffer(buffer: string, config: StreamingConfig): string {
  if (!config.enablePII) {
    return buffer;
  }

  return redactPII(buffer, config.piiTypes, config.redactionFormat);
}

/**
 * Find a safe point to split the buffer.
 */
function findSafeSplitPoint(
  text: string,
  minBuffer: number,
  maxBuffer: number
): { safeText: string; remainder: string } {
  // If buffer is small, keep it all
  if (text.length <= minBuffer) {
    return { safeText: '', remainder: text };
  }

  // If buffer exceeds max, force a split
  if (text.length > maxBuffer) {
    // Find a word boundary
    const searchStart = maxBuffer - minBuffer;
    let splitPoint = maxBuffer;

    for (let i = searchStart; i < maxBuffer; i++) {
      if (/\s/.test(text[i] ?? '')) {
        splitPoint = i + 1;
        break;
      }
    }

    return {
      safeText: text.substring(0, splitPoint),
      remainder: text.substring(splitPoint),
    };
  }

  // Normal case: find a good split point leaving minBuffer in remainder
  const targetSplit = text.length - minBuffer;
  let splitPoint = targetSplit;

  // Look for whitespace near the target
  for (let i = targetSplit; i >= 0; i--) {
    if (/\s/.test(text[i] ?? '')) {
      splitPoint = i + 1;
      break;
    }
  }

  return {
    safeText: text.substring(0, splitPoint),
    remainder: text.substring(splitPoint),
  };
}

// =============================================================================
// Specialized Streaming Handlers
// =============================================================================

/**
 * Create a strict streaming redactor that aborts on any sensitive content.
 */
export function createStrictStreamingRedactor(
  config: Omit<StreamingConfig, 'abortOnSensitiveData' | 'enableSensitiveDataCheck'> = {}
): (args: { textStream: AsyncIterable<string> }) => AsyncGenerator<string, void, unknown> {
  return createSentinelPIIRedactor({
    ...config,
    enablePII: true,
    enableSensitiveDataCheck: true,
    abortOnSensitiveData: true,
  });
}

/**
 * Create a permissive streaming redactor that only removes PII.
 */
export function createPermissiveStreamingRedactor(
  piiTypes?: PIIType[]
): (args: { textStream: AsyncIterable<string> }) => AsyncGenerator<string, void, unknown> {
  return createSentinelPIIRedactor({
    enablePII: true,
    piiTypes,
    enableSensitiveDataCheck: false,
    abortOnSensitiveData: false,
  });
}

/**
 * Create a monitoring streaming handler that detects but doesn't modify.
 */
export function createMonitoringStreamHandler(
  logger: (message: string, data?: Record<string, unknown>) => void
): (args: { textStream: AsyncIterable<string> }) => AsyncGenerator<string, void, unknown> {
  return async function* monitoringHandler({ textStream }): AsyncGenerator<string, void, unknown> {
    let totalPII = 0;
    let chunkCount = 0;

    for await (const chunk of textStream) {
      chunkCount++;

      // Detect but don't redact
      const piiResult = detectPII(chunk);
      if (piiResult.detected) {
        totalPII += piiResult.count;
        logger('PII detected in chunk', {
          chunkIndex: chunkCount,
          piiTypes: piiResult.types,
          count: piiResult.count,
        });
      }

      // Pass through unmodified
      yield chunk;
    }

    logger('Stream monitoring completed', {
      totalChunks: chunkCount,
      totalPIIInstances: totalPII,
    });
  };
}
