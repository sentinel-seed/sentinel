/**
 * Sentinel Tools for Solana Agent Kit
 *
 * These tools provide safety validation functionality that can be
 * registered with the SolanaAgentKit plugin system.
 */

export { SentinelValidator, createValidator } from "./validator";
export {
  validateTransaction,
  checkSafety,
  getSafetyStatus,
  blockAddress,
  unblockAddress,
  clearValidationHistory,
  updateSafetyConfig,
  initializeValidator,
  setSharedValidator,
  isValidatorInitialized,
} from "./functions";
