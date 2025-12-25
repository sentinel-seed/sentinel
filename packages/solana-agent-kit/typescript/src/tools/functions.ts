/**
 * Sentinel validation functions for Solana Agent Kit
 *
 * These functions are exposed as methods on the SolanaAgentKit instance
 * when the Sentinel plugin is registered.
 *
 * IMPORTANT: The validator must be initialized via initializeValidator()
 * before any validation functions are called. This is done automatically
 * by the SentinelPlugin during registration.
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
 * Set a pre-configured validator instance
 * Used by the plugin to share its validator with these functions
 */
export function setSharedValidator(validator: SentinelValidator): void {
  sharedValidator = validator;
}

/**
 * Get the validator instance
 * Throws if not initialized (prevents accidental default validator creation)
 */
function getValidator(): SentinelValidator {
  if (!sharedValidator) {
    throw new Error(
      "[Sentinel] Validator not initialized. Ensure SentinelPlugin is registered before calling validation methods."
    );
  }
  return sharedValidator;
}

/**
 * Check if validator is initialized
 */
export function isValidatorInitialized(): boolean {
  return sharedValidator !== null;
}

/**
 * Validate a transaction before execution
 *
 * This is the primary validation function that checks a transaction
 * against the THSP protocol (Truth, Harm, Scope, Purpose).
 *
 * @param _agent - SolanaAgentKit instance (reserved for future use)
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
export function validateTransaction(
  _agent: SolanaAgentKit,
  input: ValidationInput
): SafetyValidationResult {
  const validator = getValidator();
  return validator.validate(input);
}

/**
 * Quick safety check for a transaction
 *
 * Returns a simplified boolean result for quick checks.
 * Use validateTransaction() for detailed analysis.
 *
 * @param _agent - SolanaAgentKit instance (reserved for future use)
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
export function checkSafety(
  _agent: SolanaAgentKit,
  action: string,
  amount?: number,
  recipient?: string
): boolean {
  const validator = getValidator();
  const result = validator.validate({ action, amount, recipient });
  return result.shouldProceed;
}

/**
 * Get current safety status and statistics
 *
 * Returns validation statistics and current configuration status.
 *
 * @param _agent - SolanaAgentKit instance (reserved for future use)
 * @returns Object with stats and configuration info
 *
 * @example
 * ```typescript
 * const status = await agent.methods.getSafetyStatus();
 * console.log(`Block rate: ${status.stats.blockRate * 100}%`);
 * ```
 */
export function getSafetyStatus(_agent: SolanaAgentKit): {
  stats: ValidationStats;
  config: SentinelPluginConfig;
  isActive: boolean;
} {
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
 * @param _agent - SolanaAgentKit instance (reserved for future use)
 * @param address - Wallet address to block
 *
 * @example
 * ```typescript
 * await agent.methods.blockAddress("SCAM_ADDRESS_HERE");
 * ```
 */
export function blockAddress(_agent: SolanaAgentKit, address: string): void {
  const validator = getValidator();
  validator.blockAddress(address);
}

/**
 * Remove an address from the blocklist
 *
 * @param _agent - SolanaAgentKit instance (reserved for future use)
 * @param address - Wallet address to unblock
 */
export function unblockAddress(_agent: SolanaAgentKit, address: string): void {
  const validator = getValidator();
  validator.unblockAddress(address);
}

/**
 * Clear validation history
 *
 * @param _agent - SolanaAgentKit instance (reserved for future use)
 */
export function clearValidationHistory(_agent: SolanaAgentKit): void {
  const validator = getValidator();
  validator.clearHistory();
}

/**
 * Update validator configuration
 *
 * @param _agent - SolanaAgentKit instance (reserved for future use)
 * @param config - Partial configuration to update
 */
export function updateSafetyConfig(
  _agent: SolanaAgentKit,
  config: Partial<SentinelPluginConfig>
): void {
  const validator = getValidator();
  validator.updateConfig(config);
}
