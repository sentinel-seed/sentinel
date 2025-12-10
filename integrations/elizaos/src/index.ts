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
 * const agent = new Agent({
 *   plugins: [
 *     sentinelPlugin({
 *       blockUnsafe: true,
 *       logChecks: true,
 *     })
 *   ]
 * });
 * ```
 *
 * @see https://sentinelseed.dev
 * @see https://docs.elizaos.ai
 */

// Main plugin export
export {
  sentinelPlugin,
  validateContent,
  validateAction,
  quickCheck,
  getValidationHistory,
  getValidationStats,
  clearValidationHistory,
} from './plugin';

// Type exports
export type {
  SentinelPluginConfig,
  SafetyCheckResult,
  THSPGates,
  RiskLevel,
  SeedVersion,
  SeedVariant,
  ValidationContext,
  Memory,
  State,
  IAgentRuntime,
  HandlerCallback,
} from './types';

// Default export
export { sentinelPlugin as default } from './plugin';
