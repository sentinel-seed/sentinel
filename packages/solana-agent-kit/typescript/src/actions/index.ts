/**
 * Sentinel Actions for Solana Agent Kit
 *
 * Export all actions that will be registered with the plugin.
 */

export {
  validateTransactionAction,
  setValidator as setValidatorForValidate,
} from "./validateTransaction";

export {
  checkSafetyAction,
  setValidator as setValidatorForCheck,
} from "./checkSafety";

export {
  getSafetyStatsAction,
  setValidator as setValidatorForStats,
} from "./getSafetyStats";

export {
  blockAddressAction,
  unblockAddressAction,
  setValidator as setValidatorForBlock,
} from "./blockAddress";

// Re-export all actions as an array for plugin registration
import { validateTransactionAction } from "./validateTransaction";
import { checkSafetyAction } from "./checkSafety";
import { getSafetyStatsAction } from "./getSafetyStats";
import { blockAddressAction, unblockAddressAction } from "./blockAddress";

/**
 * All Sentinel actions for plugin registration
 */
export const sentinelActions = [
  validateTransactionAction,
  checkSafetyAction,
  getSafetyStatsAction,
  blockAddressAction,
  unblockAddressAction,
];
