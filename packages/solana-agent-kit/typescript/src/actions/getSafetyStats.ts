/**
 * GET_SAFETY_STATS Action
 *
 * Retrieve validation statistics and safety status.
 * Useful for monitoring and auditing agent behavior.
 */

import type { Action, SolanaAgentKit } from "solana-agent-kit";
import { z } from "zod";
import { SentinelValidator } from "../tools/validator";

// Shared validator instance - set by plugin during initialization
let validator: SentinelValidator | null = null;

/**
 * Set the validator instance (called during plugin initialization)
 */
export function setValidator(v: SentinelValidator): void {
  validator = v;
}

/**
 * Get the validator, throwing if not initialized
 */
function getValidator(): SentinelValidator {
  if (!validator) {
    throw new Error(
      "[Sentinel] Validator not initialized. Ensure SentinelPlugin is registered."
    );
  }
  return validator;
}

/**
 * GET_SAFETY_STATS Action
 *
 * Retrieve current validation statistics including block rate,
 * total validations, and breakdown by action type.
 */
export const getSafetyStatsAction: Action = {
  name: "GET_SAFETY_STATS",

  similes: [
    "safety stats",
    "validation stats",
    "how many blocked",
    "sentinel status",
    "safety report",
    "block rate",
    "safety metrics",
  ],

  description:
    "Get Sentinel safety validation statistics. Returns total validations, " +
    "block rate, high-risk count, and breakdown by action type. Useful for " +
    "monitoring agent safety behavior and auditing.",

  examples: [
    [
      {
        input: {},
        output: {
          status: "success",
          stats: {
            totalValidations: 42,
            blocked: 3,
            approved: 39,
            highRisk: 5,
            blockRate: 0.071,
            byAction: {
              transfer: 25,
              swap: 12,
              stake: 5,
            },
          },
          message: "42 validations performed, 7.1% block rate",
        },
        explanation: "Retrieving safety statistics showing validation history",
      },
    ],
  ],

  schema: z.object({}).describe("No input required"),

  handler: async (
    agent: SolanaAgentKit,
    input: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    try {
      const stats = getValidator().getStats();
      const config = getValidator().getConfig();

      // Handle potential NaN in blockRate
      const blockRateValue = Number.isFinite(stats.blockRate)
        ? stats.blockRate
        : 0;
      const blockRatePercent = (blockRateValue * 100).toFixed(1);

      return {
        status: "success",
        stats: {
          totalValidations: stats.totalValidations,
          blocked: stats.blocked,
          approved: stats.approved,
          highRisk: stats.highRisk,
          blockRate: blockRateValue,
          blockRatePercent: `${blockRatePercent}%`,
          byAction: stats.byAction,
        },
        config: {
          maxTransactionAmount: config.maxTransactionAmount,
          confirmationThreshold: config.confirmationThreshold,
          strictMode: config.strictMode,
          blockedAddressCount: Array.isArray(config.blockedAddresses)
            ? config.blockedAddresses.length
            : 0,
        },
        message:
          stats.totalValidations > 0
            ? `${stats.totalValidations} validations performed, ${blockRatePercent}% block rate`
            : "No validations performed yet",
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      return {
        status: "error",
        message: `Failed to get stats: ${errorMessage}`,
      };
    }
  },
};
