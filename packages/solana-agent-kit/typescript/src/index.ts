/**
 * @sentinelseed/solana-agent-kit
 *
 * Sentinel Safety Plugin for Solana Agent Kit
 *
 * Provides AI safety validation for Solana transactions using the
 * THSP (Truth-Harm-Scope-Purpose) protocol. Protects AI agents from
 * executing harmful, unauthorized, or suspicious transactions.
 *
 * @packageDocumentation
 *
 * @example Basic Usage
 * ```typescript
 * import { SolanaAgentKit } from "solana-agent-kit";
 * import SentinelPlugin from "@sentinelseed/solana-agent-kit";
 *
 * const agent = new SolanaAgentKit(privateKey, rpcUrl)
 *   .use(SentinelPlugin());
 *
 * // All transactions now pass through THSP validation
 * ```
 *
 * @example With Configuration
 * ```typescript
 * const agent = new SolanaAgentKit(privateKey, rpcUrl)
 *   .use(SentinelPlugin({
 *     maxTransactionAmount: 100,
 *     confirmationThreshold: 10,
 *     requirePurposeFor: ["transfer", "swap", "stake"],
 *     strictMode: false,
 *   }));
 * ```
 *
 * @example Manual Validation
 * ```typescript
 * const result = await agent.methods.validateTransaction({
 *   action: "transfer",
 *   amount: 50,
 *   recipient: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
 *   purpose: "Payment for NFT purchase",
 * });
 *
 * if (result.shouldProceed) {
 *   // Safe to execute
 * } else {
 *   console.log("Blocked:", result.concerns);
 * }
 * ```
 */

// Main plugin export
export { SentinelPlugin, default } from "./plugin";
export type { SentinelMethods } from "./plugin";

// Validator for direct use
export { SentinelValidator, createValidator } from "./tools/validator";

// Actions for custom integrations
export {
  validateTransactionAction,
  checkSafetyAction,
  getSafetyStatsAction,
  blockAddressAction,
  unblockAddressAction,
  sentinelActions,
} from "./actions";

// Types
export {
  RiskLevel,
  THSPGate,
  AddressValidationMode,
  DEFAULT_CONFIG,
  HIGH_RISK_ACTIONS,
  DEFAULT_SUSPICIOUS_PATTERNS,
} from "./types";

export type {
  SafetyValidationResult,
  ValidationInput,
  ValidationStats,
  SentinelPluginConfig,
  GateResult,
  SuspiciousPattern,
  SeedVariant,
} from "./types";
