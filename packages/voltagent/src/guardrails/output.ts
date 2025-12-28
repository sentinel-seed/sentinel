/**
 * @sentinelseed/voltagent - Output Guardrail
 *
 * Creates VoltAgent-compatible output guardrails for AI response validation.
 * Primary use case is PII detection and redaction in model outputs.
 */

import type {
  SentinelGuardrailConfig,
  VoltAgentOutputArgs,
  VoltAgentOutputResult,
  VoltAgentOutputStreamArgs,
  VoltAgentOutputStreamResult,
  GuardrailAction,
  PIIType,
} from '../types';
import type { VoltAgentTextStreamPart } from '@voltagent/core';
import { validateTHSP } from '../validators/thsp';
import { validateOWASP } from '../validators/owasp';
import { detectPII, redactPII, maskPII } from '../validators/pii';

// =============================================================================
// Default Configuration
// =============================================================================

const DEFAULT_OUTPUT_CONFIG: Required<
  Pick<
    SentinelGuardrailConfig,
    | 'blockUnsafe'
    | 'logChecks'
    | 'enableTHSP'
    | 'enableOWASP'
    | 'enablePII'
    | 'redactPII'
    | 'maxContentLength'
  >
> = {
  blockUnsafe: false, // Output guardrails typically modify rather than block
  logChecks: false,
  enableTHSP: false, // THSP less relevant for output
  enableOWASP: true, // Check for sensitive data exposure
  enablePII: true, // Primary use case for output guardrails
  redactPII: true, // Default to redacting PII
  maxContentLength: 100000,
};

// =============================================================================
// Output Guardrail Interface
// =============================================================================

/**
 * VoltAgent output guardrail interface.
 * Compatible with VoltAgent's OutputGuardrail type.
 */
export interface SentinelOutputGuardrail<T = unknown> {
  /** Guardrail unique identifier */
  id?: string;
  /** Guardrail name */
  name: string;
  /** Guardrail description */
  description?: string;
  /** Optional tags for categorization */
  tags?: string[];
  /** Severity level */
  severity?: 'info' | 'warning' | 'critical';
  /** Additional metadata */
  metadata?: Record<string, unknown>;
  /** Handler function that performs validation */
  handler: (args: VoltAgentOutputArgs<T>) => Promise<VoltAgentOutputResult<T>>;
  /** VoltAgent-compatible stream handler for streaming responses */
  streamHandler?: (args: VoltAgentOutputStreamArgs) => VoltAgentOutputStreamResult;
}

// =============================================================================
// Output Guardrail Factory
// =============================================================================

/**
 * Create a Sentinel output guardrail for VoltAgent.
 *
 * @param config - Guardrail configuration
 * @returns VoltAgent-compatible output guardrail
 *
 * @example
 * ```typescript
 * import { Agent } from "@voltagent/core";
 * import { createSentinelOutputGuardrail } from "@sentinelseed/voltagent";
 *
 * const piiGuard = createSentinelOutputGuardrail({
 *   enablePII: true,
 *   redactPII: true,
 * });
 *
 * const agent = new Agent({
 *   name: "safe-agent",
 *   outputGuardrails: [piiGuard],
 * });
 * ```
 */
export function createSentinelOutputGuardrail<T = unknown>(
  config: SentinelGuardrailConfig = {}
): SentinelOutputGuardrail<T> {
  // Merge with defaults
  const mergedConfig = {
    ...DEFAULT_OUTPUT_CONFIG,
    ...config,
  };

  return {
    name: 'sentinel-output-guardrail',
    description: 'Sentinel output validation: PII detection, sensitive data protection',
    tags: ['security', 'pii', 'sentinel', 'privacy'],

    async handler(args: VoltAgentOutputArgs<T>): Promise<VoltAgentOutputResult<T>> {
      const startTime = Date.now();
      const outputText = args.outputText ?? '';
      const { output } = args;

      // Handle empty output
      if (!outputText || typeof outputText !== 'string') {
        return createAllowResult('Empty output passed validation');
      }

      // Check content length
      if (outputText.length > mergedConfig.maxContentLength) {
        if (mergedConfig.blockUnsafe) {
          return createBlockResult<T>('Output exceeds maximum allowed length');
        }
      }

      try {
        let modifiedText = outputText;
        let wasModified = false;
        const concerns: string[] = [];

        // PII Detection and Redaction
        if (mergedConfig.enablePII) {
          const piiResult = detectPII(outputText, config.piiTypes, config.customPIIPatterns);

          if (piiResult.detected) {
            concerns.push(`PII detected: ${piiResult.types.join(', ')}`);

            if (mergedConfig.redactPII) {
              modifiedText = redactPII(
                modifiedText,
                config.piiTypes,
                config.redactionFormat
              );
              wasModified = true;
            }
          }
        }

        // OWASP Check (for sensitive data exposure)
        if (mergedConfig.enableOWASP) {
          const owaspResult = validateOWASP(outputText, ['SENSITIVE_DATA_EXPOSURE']);

          if (!owaspResult.safe) {
            concerns.push('Sensitive data exposure detected');

            if (mergedConfig.blockUnsafe) {
              return createBlockResult<T>('Sensitive data detected in output', {
                sentinel: {
                  owasp: owaspResult,
                },
              });
            }
          }
        }

        // THSP Check (if enabled for output)
        if (mergedConfig.enableTHSP) {
          const thspResult = validateTHSP(outputText);

          if (!thspResult.safe) {
            concerns.push(...thspResult.concerns);

            if (mergedConfig.blockUnsafe) {
              return createBlockResult<T>('Safety concerns detected in output', {
                sentinel: {
                  thsp: thspResult,
                },
              });
            }
          }
        }

        // Log if enabled
        if (mergedConfig.logChecks && config.logger) {
          config.logger('Sentinel output validation completed', {
            modified: wasModified,
            concerns: concerns.length,
            durationMs: Date.now() - startTime,
          });
        }

        // Return result
        if (wasModified) {
          return createModifyResult<T>(
            'Output modified for safety',
            createModifiedOutput(output, modifiedText),
            {
              sentinel: {
                originalLength: outputText.length,
                modifiedLength: modifiedText.length,
                concerns,
              },
            }
          );
        }

        if (concerns.length > 0 && mergedConfig.blockUnsafe) {
          return createBlockResult<T>(`Concerns detected: ${concerns.join('; ')}`);
        }

        return createAllowResult('Output passed validation', {
          sentinel: {
            concerns,
            durationMs: Date.now() - startTime,
          },
        });

      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';

        if (config.logger) {
          config.logger('Sentinel output validation error', { error: errorMessage });
        }

        // Fail open for output guardrails (don't break the response)
        return createAllowResult('Validation skipped due to error', {
          sentinel: { error: errorMessage },
        });
      }
    },

    // VoltAgent-compatible stream handler for real-time PII redaction
    streamHandler(args: VoltAgentOutputStreamArgs): VoltAgentOutputStreamResult {
      const { part, state } = args;

      // Initialize state if needed
      if (!state._sentinelBuffer) {
        state._sentinelBuffer = '';
        state._sentinelPIICount = 0;
      }

      // If PII redaction not enabled, pass through
      if (!mergedConfig.enablePII || !mergedConfig.redactPII) {
        return part;
      }

      // Only process text-delta parts (the ones that contain actual text)
      // VoltAgentTextStreamPart is a union type - we only care about text-delta
      if (part.type !== 'text-delta') {
        return part;
      }

      // Get text from the text-delta part
      // Note: ai-sdk's text-delta has 'text' property, not 'textDelta'
      const textDeltaPart = part as unknown as { type: 'text-delta'; text: string };
      const textDelta = textDeltaPart.text;

      if (!textDelta) {
        return part;
      }

      // Add to buffer
      state._sentinelBuffer = (state._sentinelBuffer as string) + textDelta;

      // Process buffer for PII
      const bufferText = state._sentinelBuffer as string;
      const { safeText, remainder } = findSafeSplit(bufferText);

      if (safeText.length === 0) {
        // Keep buffering, return null to suppress this part
        return null;
      }

      // Redact PII in the safe portion
      const redacted = redactPII(safeText, config.piiTypes, config.redactionFormat);

      // Track if PII was found
      const piiResult = detectPII(safeText, config.piiTypes);
      if (piiResult.detected) {
        state._sentinelPIICount = (state._sentinelPIICount as number) + piiResult.count;

        // Log if enabled
        if (config.logger) {
          config.logger('PII redacted in stream', {
            count: piiResult.count,
            types: piiResult.types,
          });
        }
      }

      // Update buffer with remainder
      state._sentinelBuffer = remainder;

      // Return modified text-delta part with redacted text
      return {
        ...part,
        text: redacted,
      } as VoltAgentTextStreamPart;
    },
  };
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Create an allow result.
 */
function createAllowResult<T>(
  message: string,
  metadata?: Record<string, unknown>
): VoltAgentOutputResult<T> {
  return {
    pass: true,
    action: 'allow',
    message,
    metadata,
  };
}

/**
 * Create a block result.
 */
function createBlockResult<T>(
  message: string,
  metadata?: Record<string, unknown>
): VoltAgentOutputResult<T> {
  return {
    pass: false,
    action: 'block',
    message,
    metadata,
  };
}

/**
 * Create a modify result.
 */
function createModifyResult<T>(
  message: string,
  modifiedOutput: T,
  metadata?: Record<string, unknown>
): VoltAgentOutputResult<T> {
  return {
    pass: true,
    action: 'modify',
    message,
    modifiedOutput,
    metadata,
  };
}

/**
 * Create modified output based on original output type.
 */
function createModifiedOutput<T>(original: T, newText: string): T {
  // If output is a string, return the new text directly
  if (typeof original === 'string') {
    return newText as unknown as T;
  }

  // If output is an object with text/content property, update it
  if (typeof original === 'object' && original !== null) {
    const obj = original as Record<string, unknown>;

    if ('text' in obj) {
      return { ...obj, text: newText } as T;
    }
    if ('content' in obj) {
      return { ...obj, content: newText } as T;
    }
    if ('message' in obj) {
      return { ...obj, message: newText } as T;
    }
  }

  // Return original if we can't determine how to modify
  return original;
}

/**
 * Find a safe point to split text for streaming.
 * Avoids splitting in the middle of potential PII.
 */
function findSafeSplit(text: string): { safeText: string; remainder: string } {
  // Keep at least 50 chars in buffer to catch PII spanning chunks
  const minBuffer = 50;

  if (text.length <= minBuffer) {
    return { safeText: '', remainder: text };
  }

  // Find a whitespace break point
  const searchStart = text.length - minBuffer;
  let splitPoint = -1;

  for (let i = searchStart; i >= 0; i--) {
    if (/\s/.test(text[i] ?? '')) {
      splitPoint = i + 1;
      break;
    }
  }

  if (splitPoint === -1) {
    splitPoint = searchStart;
  }

  return {
    safeText: text.substring(0, splitPoint),
    remainder: text.substring(splitPoint),
  };
}

// =============================================================================
// Specialized Output Guardrails
// =============================================================================

/**
 * Create a PII-focused output guardrail.
 */
export function createPIIOutputGuardrail<T = unknown>(
  options: {
    piiTypes?: PIIType[];
    redact?: boolean;
    mask?: boolean;
  } = {}
): SentinelOutputGuardrail<T> {
  return createSentinelOutputGuardrail<T>({
    enablePII: true,
    enableOWASP: false,
    enableTHSP: false,
    redactPII: options.redact ?? true,
    piiTypes: options.piiTypes,
  });
}

/**
 * Create a strict output guardrail that blocks on any sensitive content.
 */
export function createStrictOutputGuardrail<T = unknown>(): SentinelOutputGuardrail<T> {
  return createSentinelOutputGuardrail<T>({
    enablePII: true,
    enableOWASP: true,
    enableTHSP: true,
    blockUnsafe: true,
    redactPII: false, // Block instead of redact
  });
}

/**
 * Create a permissive output guardrail that only redacts PII.
 */
export function createPermissiveOutputGuardrail<T = unknown>(
  logger?: (message: string, data?: Record<string, unknown>) => void
): SentinelOutputGuardrail<T> {
  return createSentinelOutputGuardrail<T>({
    enablePII: true,
    enableOWASP: false,
    enableTHSP: false,
    blockUnsafe: false,
    redactPII: true,
    logChecks: true,
    logger,
  });
}
