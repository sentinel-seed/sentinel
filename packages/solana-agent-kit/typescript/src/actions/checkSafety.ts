/**
 * CHECK_SAFETY Action
 *
 * Quick safety check action that returns a simple pass/fail result.
 * Use for rapid pre-flight checks before transaction execution.
 */

import type { Action, SolanaAgentKit } from "solana-agent-kit";
import { z } from "zod";
import { SentinelValidator } from "../tools/validator";
import { RiskLevel } from "../types";

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
 * CHECK_SAFETY Action
 *
 * Quick safety check for transactions. Returns simplified pass/fail result.
 * For detailed analysis, use VALIDATE_TRANSACTION instead.
 */
export const checkSafetyAction: Action = {
  name: "CHECK_SAFETY",

  similes: [
    "is it safe",
    "quick check",
    "safety check",
    "can I proceed",
    "is this ok",
    "verify safe",
    "pre-check",
  ],

  description:
    "Quick safety check for a Solana transaction. Returns a simple pass/fail " +
    "result. Use for rapid pre-flight checks. For detailed gate-by-gate " +
    "analysis, use VALIDATE_TRANSACTION instead.",

  examples: [
    [
      {
        input: {
          action: "transfer",
          amount: 5,
        },
        output: {
          safe: true,
          canProceed: true,
          message: "Transaction is safe to proceed",
        },
        explanation: "Quick check for a small transfer - passes all gates",
      },
    ],
    [
      {
        input: {
          action: "drainWallet",
          amount: 1000,
        },
        output: {
          safe: false,
          canProceed: false,
          reason: "High-risk action detected: drainWallet",
          message: "Transaction blocked - high risk action",
        },
        explanation: "Quick check catches dangerous drain operation",
      },
    ],
  ],

  schema: z.object({
    action: z
      .string()
      .min(1)
      .describe("The transaction action type"),
    amount: z
      .number()
      .positive()
      .optional()
      .describe("Transaction amount"),
    recipient: z
      .string()
      .min(32)
      .max(44)
      .optional()
      .describe("Recipient address"),
  }),

  handler: async (
    agent: SolanaAgentKit,
    input: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    try {
      // Validate action is a string
      if (!input.action || typeof input.action !== "string") {
        return {
          safe: false,
          canProceed: false,
          riskLevel: RiskLevel.CRITICAL,
          reason: "action must be a non-empty string",
          message: "Safety check error: invalid action parameter",
        };
      }

      // Validate amount is a number if provided
      if (input.amount !== undefined && typeof input.amount !== "number") {
        return {
          safe: false,
          canProceed: false,
          riskLevel: RiskLevel.CRITICAL,
          reason: "amount must be a number",
          message: "Safety check error: invalid amount parameter",
        };
      }

      // Validate recipient is a string if provided
      if (input.recipient !== undefined && typeof input.recipient !== "string") {
        return {
          safe: false,
          canProceed: false,
          riskLevel: RiskLevel.CRITICAL,
          reason: "recipient must be a string",
          message: "Safety check error: invalid recipient parameter",
        };
      }

      const result = getValidator().validate({
        action: input.action,
        amount: input.amount as number | undefined,
        recipient: input.recipient as string | undefined,
      });

      if (result.shouldProceed) {
        return {
          safe: result.safe,
          canProceed: true,
          riskLevel: result.riskLevel,
          message: result.safe
            ? "Transaction is safe to proceed"
            : "Transaction has minor concerns but can proceed",
        };
      } else {
        return {
          safe: false,
          canProceed: false,
          riskLevel: result.riskLevel,
          reason: result.concerns[0] ?? "Safety check failed",
          message: `Transaction blocked: ${result.concerns[0] ?? "safety check failed"}`,
        };
      }
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      return {
        safe: false,
        canProceed: false,
        riskLevel: RiskLevel.CRITICAL,
        reason: errorMessage,
        message: `Safety check error: ${errorMessage}`,
      };
    }
  },
};
