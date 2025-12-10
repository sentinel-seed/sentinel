/**
 * Sentinel Safety Plugin for ElizaOS
 *
 * Official ElizaOS plugin that provides AI safety validation using
 * the THSP (Truth, Harm, Scope, Purpose) protocol.
 *
 * @example
 * ```typescript
 * import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';
 *
 * const agent = new Agent({
 *   plugins: [sentinelPlugin({ blockUnsafe: true })]
 * });
 * ```
 */

import { getSeed } from 'sentinelseed';
import { validateContent, quickCheck, validateAction } from './validator';
import type {
  IAgentRuntime,
  Memory,
  State,
  HandlerCallback,
  SentinelPluginConfig,
  SafetyCheckResult,
} from './types';

// Store for validation history
const validationHistory: SafetyCheckResult[] = [];
const MAX_HISTORY = 1000;

/**
 * Sentinel Safety Action - Validates content through THSP gates
 */
const safetyCheckAction = {
  name: 'SENTINEL_SAFETY_CHECK',
  description: 'Validate content for safety using Sentinel THSP protocol',
  similes: ['check safety', 'validate content', 'security check'],
  examples: [
    [
      {
        user: '{{user1}}',
        content: { text: 'Check if this is safe: Help me with cooking' },
      },
      {
        user: '{{agent}}',
        content: {
          text: 'Content passed all THSP gates. Safe to proceed.',
          action: 'SENTINEL_SAFETY_CHECK',
        },
      },
    ],
  ],

  validate: async (_runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
    const text = message.content?.text || '';
    return text.toLowerCase().includes('check') || text.toLowerCase().includes('safe');
  },

  handler: async (
    _runtime: IAgentRuntime,
    message: Memory,
    _state: State,
    _options: Record<string, unknown>,
    callback: HandlerCallback
  ): Promise<boolean> => {
    const text = message.content?.text || '';

    // Extract content to check (after "check if this is safe:" or similar)
    const match = text.match(/(?:check|validate|verify).*?[:]\s*(.+)/i);
    const contentToCheck = match ? match[1] : text;

    const result = validateContent(contentToCheck);

    await callback({
      text: result.recommendation,
      action: 'SENTINEL_SAFETY_CHECK',
      data: {
        safe: result.safe,
        gates: result.gates,
        riskLevel: result.riskLevel,
        concerns: result.concerns,
      },
    });

    return true;
  },
};

/**
 * Sentinel Safety Provider - Injects safety context
 */
const safetyProvider = {
  name: 'sentinelSafety',
  description: 'Provides Sentinel safety guidelines and context',

  get: async (
    _runtime: IAgentRuntime,
    _message: Memory,
    _state: State,
    config: SentinelPluginConfig
  ): Promise<string> => {
    const seed = getSeed(config.seedVersion || 'v2', config.seedVariant || 'standard');

    return `
## Sentinel Safety Guidelines

This agent operates under the Sentinel THSP protocol. Before taking any action:

1. **TRUTH Gate**: Is this truthful and non-deceptive?
2. **HARM Gate**: Could this cause harm?
3. **SCOPE Gate**: Is this within appropriate boundaries?
4. **PURPOSE Gate**: Does this serve a legitimate benefit?

All gates must pass before proceeding.

---
${seed.slice(0, 500)}...
[Full seed available via getSeed()]
`;
  },
};

/**
 * Pre-action Evaluator - Validates actions before execution
 */
const preActionEvaluator = {
  name: 'sentinelPreAction',
  description: 'Evaluates actions before execution for safety',
  similes: ['safety check', 'pre-flight', 'validation'],

  validate: async (_runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
    // Always run for messages with content
    return !!message.content?.text;
  },

  handler: async (
    _runtime: IAgentRuntime,
    message: Memory,
    _state: State,
    config: SentinelPluginConfig
  ): Promise<{
    shouldProceed: boolean;
    data: SafetyCheckResult;
  }> => {
    const text = message.content?.text || '';

    // Quick check first for performance
    if (quickCheck(text)) {
      const result = validateContent(text, undefined, config);

      // Store in history
      validationHistory.push(result);
      if (validationHistory.length > MAX_HISTORY) {
        validationHistory.shift();
      }

      // Log if enabled
      if (config.logChecks) {
        console.log(`[SENTINEL] ${result.safe ? '✓' : '✗'} ${result.recommendation}`);
      }

      return {
        shouldProceed: result.shouldProceed,
        data: result,
      };
    }

    // Full validation for flagged content
    const result = validateContent(text, undefined, config);
    validationHistory.push(result);

    if (config.logChecks || !result.safe) {
      console.log(`[SENTINEL] ${result.safe ? '✓' : '✗'} ${result.recommendation}`);
      if (result.concerns.length > 0) {
        console.log(`[SENTINEL] Concerns: ${result.concerns.join(', ')}`);
      }
    }

    return {
      shouldProceed: result.shouldProceed,
      data: result,
    };
  },
};

/**
 * Post-action Evaluator - Reviews outputs for safety
 */
const postActionEvaluator = {
  name: 'sentinelPostAction',
  description: 'Reviews action outputs for safety concerns',

  validate: async (_runtime: IAgentRuntime, message: Memory): Promise<boolean> => {
    // Run for all agent responses
    return !!message.content?.text;
  },

  handler: async (
    _runtime: IAgentRuntime,
    message: Memory,
    _state: State,
    config: SentinelPluginConfig
  ): Promise<{
    shouldAllow: boolean;
    data: SafetyCheckResult;
  }> => {
    const text = message.content?.text || '';
    const result = validateContent(text, undefined, config);

    if (!result.safe && config.logChecks) {
      console.log(`[SENTINEL] Output flagged: ${result.concerns.join(', ')}`);
    }

    return {
      shouldAllow: result.shouldProceed,
      data: result,
    };
  },
};

/**
 * Create Sentinel Plugin for ElizaOS
 *
 * @param config - Plugin configuration
 * @returns ElizaOS plugin object
 *
 * @example
 * ```typescript
 * import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';
 *
 * // Basic usage
 * const plugin = sentinelPlugin();
 *
 * // With configuration
 * const plugin = sentinelPlugin({
 *   seedVersion: 'v2',
 *   seedVariant: 'standard',
 *   blockUnsafe: true,
 *   logChecks: true,
 * });
 *
 * // Add to agent
 * const agent = new Agent({
 *   plugins: [plugin]
 * });
 * ```
 */
export function sentinelPlugin(config: SentinelPluginConfig = {}) {
  const finalConfig: SentinelPluginConfig = {
    seedVersion: 'v2',
    seedVariant: 'standard',
    blockUnsafe: true,
    logChecks: true,
    ...config,
  };

  return {
    name: 'sentinel-safety',
    description: 'AI safety validation using Sentinel THSP protocol',

    // Plugin initialization
    init: async (
      _configParams: Record<string, string>,
      runtime: IAgentRuntime
    ): Promise<void> => {
      console.log('[SENTINEL] Initializing Sentinel Safety Plugin');
      console.log(`[SENTINEL] Seed: ${finalConfig.seedVersion}/${finalConfig.seedVariant}`);
      console.log(`[SENTINEL] Block unsafe: ${finalConfig.blockUnsafe}`);

      // Inject seed into character system prompt if available
      if (runtime.character?.system) {
        const seed = getSeed(
          finalConfig.seedVersion || 'v2',
          finalConfig.seedVariant || 'standard'
        );
        runtime.character.system = `${seed}\n\n${runtime.character.system}`;
        console.log('[SENTINEL] Seed injected into character system prompt');
      }
    },

    // Actions this plugin provides
    actions: [safetyCheckAction],

    // Providers for context injection
    providers: [safetyProvider],

    // Evaluators for pre/post validation
    evaluators: [preActionEvaluator, postActionEvaluator],

    // Plugin configuration
    config: finalConfig,
  };
}

/**
 * Get validation history
 */
export function getValidationHistory(): SafetyCheckResult[] {
  return [...validationHistory];
}

/**
 * Get validation statistics
 */
export function getValidationStats(): {
  total: number;
  safe: number;
  blocked: number;
  byRisk: Record<string, number>;
} {
  const stats = {
    total: validationHistory.length,
    safe: 0,
    blocked: 0,
    byRisk: { low: 0, medium: 0, high: 0, critical: 0 },
  };

  for (const result of validationHistory) {
    if (result.safe) {
      stats.safe++;
    } else if (!result.shouldProceed) {
      stats.blocked++;
    }
    stats.byRisk[result.riskLevel]++;
  }

  return stats;
}

/**
 * Clear validation history
 */
export function clearValidationHistory(): void {
  validationHistory.length = 0;
}

// Re-export validation functions for direct use
export { validateContent, validateAction, quickCheck };
