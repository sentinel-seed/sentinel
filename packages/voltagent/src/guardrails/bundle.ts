/**
 * @sentinelseed/voltagent - Bundle Function
 *
 * Provides preset configurations for common use cases.
 * Simplifies setup by bundling input and output guardrails together.
 */

import type { SentinelBundleConfig, SentinelGuardrailConfig } from '../types';
import { createSentinelInputGuardrail, type SentinelInputGuardrail } from './input';
import { createSentinelOutputGuardrail, type SentinelOutputGuardrail } from './output';

// =============================================================================
// Bundle Result Type
// =============================================================================

/**
 * Result of createSentinelGuardrails bundle function.
 */
export interface SentinelGuardrailBundle<T = unknown> {
  /** Array of input guardrails (for VoltAgent inputGuardrails property) */
  inputGuardrails: SentinelInputGuardrail[];
  /** Array of output guardrails (for VoltAgent outputGuardrails property) */
  outputGuardrails: SentinelOutputGuardrail<T>[];
  /** The resolved configuration used */
  config: SentinelGuardrailConfig;
}

// =============================================================================
// Preset Configurations
// =============================================================================

/**
 * Preset configurations for different security levels.
 */
const PRESET_CONFIGS: Record<'permissive' | 'standard' | 'strict', SentinelGuardrailConfig> = {
  permissive: {
    blockUnsafe: false,
    enableTHSP: true,
    enableOWASP: false,
    enablePII: false,
    logChecks: true,
  },
  standard: {
    blockUnsafe: true,
    enableTHSP: true,
    enableOWASP: true,
    enablePII: false,
    minBlockLevel: 'medium',
  },
  strict: {
    blockUnsafe: true,
    enableTHSP: true,
    enableOWASP: true,
    enablePII: true,
    minBlockLevel: 'low',
    redactPII: true,
  },
};

// =============================================================================
// Bundle Factory
// =============================================================================

/**
 * Create a complete set of Sentinel guardrails for VoltAgent.
 *
 * This is the recommended way to add Sentinel protection to a VoltAgent agent.
 * It provides preset configurations for common use cases and handles both
 * input and output guardrails.
 *
 * @param bundleConfig - Bundle configuration
 * @returns Object with inputGuardrails and outputGuardrails arrays
 *
 * @example
 * ```typescript
 * import { Agent } from "@voltagent/core";
 * import { createSentinelGuardrails } from "@sentinelseed/voltagent";
 *
 * // Simple usage with preset
 * const { inputGuardrails, outputGuardrails } = createSentinelGuardrails({
 *   level: "strict",
 * });
 *
 * const agent = new Agent({
 *   name: "safe-agent",
 *   inputGuardrails,
 *   outputGuardrails,
 * });
 * ```
 *
 * @example
 * ```typescript
 * // With PII protection enabled
 * const guardrails = createSentinelGuardrails({
 *   level: "standard",
 *   enablePII: true,
 * });
 *
 * const agent = new Agent({
 *   ...guardrails,
 * });
 * ```
 *
 * @example
 * ```typescript
 * // Custom configuration
 * const guardrails = createSentinelGuardrails({
 *   custom: {
 *     enableTHSP: true,
 *     enableOWASP: true,
 *     enablePII: true,
 *     blockUnsafe: true,
 *     redactPII: true,
 *     piiTypes: ['EMAIL', 'PHONE', 'SSN'],
 *   },
 * });
 * ```
 */
export function createSentinelGuardrails<T = unknown>(
  bundleConfig: SentinelBundleConfig = {}
): SentinelGuardrailBundle<T> {
  // Resolve configuration
  const baseConfig = PRESET_CONFIGS[bundleConfig.level ?? 'standard'];
  const config: SentinelGuardrailConfig = {
    ...baseConfig,
    // Override PII if specified
    ...(bundleConfig.enablePII !== undefined && {
      enablePII: bundleConfig.enablePII,
      redactPII: bundleConfig.enablePII,
    }),
    // Apply custom overrides
    ...bundleConfig.custom,
  };

  // Create input guardrail
  const inputGuardrail = createSentinelInputGuardrail(config);

  // Create output guardrail with PII focus
  const outputConfig: SentinelGuardrailConfig = {
    ...config,
    // Output guardrails typically don't need THSP
    enableTHSP: false,
    // But always check for sensitive data
    enableOWASP: true,
    // PII is the main concern for output
    enablePII: bundleConfig.enablePII ?? config.enablePII ?? false,
    redactPII: bundleConfig.enablePII ?? config.redactPII ?? false,
    // Output guardrails typically modify rather than block
    blockUnsafe: false,
  };

  const outputGuardrail = createSentinelOutputGuardrail<T>(outputConfig);

  return {
    inputGuardrails: [inputGuardrail],
    outputGuardrails: [outputGuardrail],
    config,
  };
}

// =============================================================================
// Specialized Bundle Functions
// =============================================================================

/**
 * Create guardrails optimized for chat applications.
 * Focuses on jailbreak prevention and safe content generation.
 */
export function createChatGuardrails<T = unknown>(): SentinelGuardrailBundle<T> {
  return createSentinelGuardrails<T>({
    level: 'standard',
    enablePII: true,
    custom: {
      // Focus on scope (jailbreak) and harm
      minBlockLevel: 'medium',
    },
  });
}

/**
 * Create guardrails optimized for agent applications.
 * Focuses on preventing dangerous tool calls and OWASP violations.
 */
export function createAgentGuardrails<T = unknown>(): SentinelGuardrailBundle<T> {
  return createSentinelGuardrails<T>({
    level: 'strict',
    enablePII: true,
    custom: {
      // Agents need stricter OWASP checks
      owaspChecks: [
        'SQL_INJECTION',
        'COMMAND_INJECTION',
        'PATH_TRAVERSAL',
        'SSRF',
        'PROMPT_INJECTION',
      ],
    },
  });
}

/**
 * Create guardrails for privacy-sensitive applications.
 * Focuses on PII detection and redaction.
 */
export function createPrivacyGuardrails<T = unknown>(): SentinelGuardrailBundle<T> {
  return createSentinelGuardrails<T>({
    level: 'standard',
    enablePII: true,
    custom: {
      // Enable all PII types
      piiTypes: [
        'EMAIL',
        'PHONE',
        'SSN',
        'CREDIT_CARD',
        'IP_ADDRESS',
        'DATE_OF_BIRTH',
        'API_KEY',
        'AWS_KEY',
        'PRIVATE_KEY',
        'JWT_TOKEN',
      ],
      redactPII: true,
    },
  });
}

/**
 * Create minimal guardrails for development/testing.
 * Only logs issues, doesn't block content.
 */
export function createDevelopmentGuardrails<T = unknown>(
  logger?: (message: string, data?: Record<string, unknown>) => void
): SentinelGuardrailBundle<T> {
  return createSentinelGuardrails<T>({
    level: 'permissive',
    custom: {
      blockUnsafe: false,
      logChecks: true,
      logger: logger ?? console.log,
    },
  });
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Get the preset configuration for a security level.
 */
export function getPresetConfig(
  level: 'permissive' | 'standard' | 'strict'
): SentinelGuardrailConfig {
  return { ...PRESET_CONFIGS[level] };
}

/**
 * Get available security levels.
 */
export function getAvailableLevels(): Array<'permissive' | 'standard' | 'strict'> {
  return ['permissive', 'standard', 'strict'];
}
