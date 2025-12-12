/**
 * Sentinel Safety Plugin for Solana Agent Kit
 *
 * This plugin provides AI safety validation for Solana transactions
 * using the THSP (Truth-Harm-Scope-Purpose) protocol.
 *
 * @example
 * ```typescript
 * import { SolanaAgentKit } from "solana-agent-kit";
 * import SentinelPlugin from "@sentinelseed/solana-agent-kit";
 *
 * const agent = new SolanaAgentKit(privateKey, rpcUrl)
 *   .use(SentinelPlugin({
 *     maxTransactionAmount: 100,
 *     requirePurposeFor: ["transfer", "swap"],
 *   }));
 *
 * // Validate before transactions
 * const result = await agent.methods.validateTransaction({
 *   action: "transfer",
 *   amount: 50,
 *   recipient: "...",
 *   purpose: "Payment for services",
 * });
 * ```
 */

import type { Plugin, SolanaAgentKit } from "solana-agent-kit";
import { SentinelValidator } from "./tools/validator";
import {
  validateTransaction,
  checkSafety,
  getSafetyStatus,
  blockAddress,
  unblockAddress,
  clearValidationHistory,
  updateSafetyConfig,
} from "./tools/functions";
import {
  sentinelActions,
  setValidatorForValidate,
  setValidatorForCheck,
  setValidatorForStats,
  setValidatorForBlock,
} from "./actions";
import type { SentinelPluginConfig } from "./types";

/**
 * Sentinel Plugin Methods
 *
 * These methods are added to agent.methods when the plugin is registered.
 */
export interface SentinelMethods {
  validateTransaction: typeof validateTransaction;
  checkSafety: typeof checkSafety;
  getSafetyStatus: typeof getSafetyStatus;
  blockAddress: typeof blockAddress;
  unblockAddress: typeof unblockAddress;
  clearValidationHistory: typeof clearValidationHistory;
  updateSafetyConfig: typeof updateSafetyConfig;
}

/**
 * Create the Sentinel safety plugin
 *
 * @param config - Plugin configuration options
 * @returns Plugin instance ready for registration with SolanaAgentKit
 *
 * @example
 * ```typescript
 * const agent = new SolanaAgentKit(privateKey, rpcUrl)
 *   .use(SentinelPlugin({
 *     maxTransactionAmount: 100,
 *     strictMode: false,
 *   }));
 * ```
 */
export function SentinelPlugin(config: SentinelPluginConfig = {}): Plugin {
  // Create validator instance with config
  const validator = new SentinelValidator(config);

  return {
    name: "sentinel",

    methods: {
      validateTransaction,
      checkSafety,
      getSafetyStatus,
      blockAddress,
      unblockAddress,
      clearValidationHistory,
      updateSafetyConfig,
    },

    actions: sentinelActions,

    initialize(agent: SolanaAgentKit): void {
      // Initialize validator with agent instance
      validator.initialize(agent);

      // Share validator instance with all actions
      setValidatorForValidate(validator);
      setValidatorForCheck(validator);
      setValidatorForStats(validator);
      setValidatorForBlock(validator);
    },
  } satisfies Plugin;
}

/**
 * Default export for convenient import
 *
 * @example
 * ```typescript
 * import SentinelPlugin from "@sentinelseed/solana-agent-kit";
 * ```
 */
export default SentinelPlugin;
