/**
 * Sentinel validation functions for Solana Agent Kit
 *
 * These functions are exposed as methods on the SolanaAgentKit instance
 * when the Sentinel plugin is registered.
 */

import type { SolanaAgentKit } from "solana-agent-kit";
import { SentinelValidator } from "./validator";
import type {
  SafetyValidationResult,
  ValidationInput,
  ValidationStats,
  SentinelPluginConfig,
} from "../types";

// Shared validator instance - initialized when plugin is registered
let sharedValidator: SentinelValidator | null = null;

/**
 * Initialize the shared validator instance
 * Called internally when the plugin is registered
 */
export function initializeValidator(
  agent: SolanaAgentKit,
  config?: SentinelPluginConfig
): void {
  sharedValidator = new SentinelValidator(config);
  sharedValidator.initialize(agent);
}

/**
 * Get or create the validator instance
 */
function getValidator(): SentinelValidator {
  if (!sharedValidator) {
    sharedValidator = new SentinelValidator();
  }
  return sharedValidator;
}

/**
 * Validate a transaction before execution
 *
 * This is the primary validation function that checks a transaction
 * against the THSP protocol (Truth, Harm, Scope, Purpose).
 *
 * @param agent - SolanaAgentKit instance
 * @param input - Transaction parameters to validate
 * @returns Validation result with detailed analysis
 *
 * @example
 * ```typescript
 * const result = await agent.methods.validateTransaction({
 *   action: "transfer",
 *   amount: 50,
 *   recipient: "ABC123...",
 *   purpose: "Payment for NFT purchase"
 * });
 *
 * if (result.shouldProceed) {
 *   // Safe to execute transaction
 * }
 * ```
 */
export async function validateTransaction(
  agent: SolanaAgentKit,
  input: ValidationInput
): Promise<SafetyValidationResult> {
  const validator = getValidator();
  return validator.validate(input);
}

/**
 * Quick safety check for a transaction
 *
 * Returns a simplified boolean result for quick checks.
 * Use validateTransaction() for detailed analysis.
 *
 * @param agent - SolanaAgentKit instance
 * @param action - Action name (e.g., "transfer", "swap")
 * @param amount - Transaction amount
 * @param recipient - Optional recipient address
 * @returns Boolean indicating if transaction is safe
 *
 * @example
 * ```typescript
 * const isSafe = await agent.methods.checkSafety("transfer", 10, "ABC123...");
 * if (isSafe) {
 *   // Proceed with transaction
 * }
 * ```
 */
export async function checkSafety(
  agent: SolanaAgentKit,
  action: string,
  amount?: number,
  recipient?: string
): Promise<boolean> {
  const validator = getValidator();
  const result = validator.validate({ action, amount, recipient });
  return result.shouldProceed;
}

/**
 * Get current safety status and statistics
 *
 * Returns validation statistics and current configuration status.
 *
 * @param agent - SolanaAgentKit instance
 * @returns Object with stats and configuration info
 *
 * @example
 * ```typescript
 * const status = await agent.methods.getSafetyStatus();
 * console.log(`Block rate: ${status.stats.blockRate * 100}%`);
 * ```
 */
export async function getSafetyStatus(
  agent: SolanaAgentKit
): Promise<{
  stats: ValidationStats;
  config: SentinelPluginConfig;
  isActive: boolean;
}> {
  const validator = getValidator();
  return {
    stats: validator.getStats(),
    config: validator.getConfig(),
    isActive: true,
  };
}

/**
 * Block an address from receiving transactions
 *
 * @param agent - SolanaAgentKit instance
 * @param address - Wallet address to block
 *
 * @example
 * ```typescript
 * await agent.methods.blockAddress("SCAM_ADDRESS_HERE");
 * ```
 */
export async function blockAddress(
  agent: SolanaAgentKit,
  address: string
): Promise<void> {
  const validator = getValidator();
  validator.blockAddress(address);
}

/**
 * Remove an address from the blocklist
 *
 * @param agent - SolanaAgentKit instance
 * @param address - Wallet address to unblock
 */
export async function unblockAddress(
  agent: SolanaAgentKit,
  address: string
): Promise<void> {
  const validator = getValidator();
  validator.unblockAddress(address);
}

/**
 * Clear validation history
 *
 * @param agent - SolanaAgentKit instance
 */
export async function clearValidationHistory(
  agent: SolanaAgentKit
): Promise<void> {
  const validator = getValidator();
  validator.clearHistory();
}

/**
 * Update validator configuration
 *
 * @param agent - SolanaAgentKit instance
 * @param config - Partial configuration to update
 */
export async function updateSafetyConfig(
  agent: SolanaAgentKit,
  config: Partial<SentinelPluginConfig>
): Promise<void> {
  const validator = getValidator();
  validator.updateConfig(config);
}
