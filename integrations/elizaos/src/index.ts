/**
 * @sentinelseed/elizaos-plugin
 *
 * Sentinel AI safety plugin for ElizaOS autonomous agents.
 * Implements THSP (Truth, Harm, Scope, Purpose) protocol validation.
 *
 * @example
 * ```typescript
 * import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';
 *
 * const character = {
 *   name: 'SafeAgent',
 *   plugins: [
 *     sentinelPlugin({
 *       blockUnsafe: true,
 *       logChecks: true,
 *     })
 *   ]
 * };
 * ```
 *
 * @see https://sentinelseed.dev
 * @see https://docs.elizaos.ai
 */

// Main plugin export
export {
  sentinelPlugin,
  getValidationHistory,
  getValidationStats,
  clearValidationHistory,
} from './plugin';

// Validation functions
export { validateContent, validateAction, quickCheck } from './validator';

// Type exports
export type {
  // ElizaOS types
  Plugin,
  Action,
  Provider,
  Evaluator,
  Memory,
  State,
  Content,
  IAgentRuntime,
  Handler,
  Validator,
  HandlerCallback,
  HandlerOptions,
  ActionResult,
  ProviderResult,
  ActionExample,
  EvaluationExample,
  UUID,
  // Sentinel types
  SentinelPluginConfig,
  SafetyCheckResult,
  THSPGates,
  RiskLevel,
  GateStatus,
  SeedVersion,
  SeedVariant,
  ValidationContext,
} from './types';

// Default export
export { sentinelPlugin as default } from './plugin';
