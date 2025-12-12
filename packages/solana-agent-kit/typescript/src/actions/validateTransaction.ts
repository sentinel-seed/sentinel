/**
 * VALIDATE_TRANSACTION Action
 *
 * Primary action for validating transactions against the THSP protocol.
 * Follows the Solana Agent Kit action pattern for LLM integration.
 */

import type { Action, SolanaAgentKit } from "solana-agent-kit";
import { z } from "zod";
import { SentinelValidator } from "../tools/validator";
import type { ValidationInput } from "../types";

// Shared validator instance
let validator: SentinelValidator | null = null;

/**
 * Get or create validator instance
 */
function getValidator(): SentinelValidator {
  if (!validator) {
    validator = new SentinelValidator();
  }
  return validator;
}

/**
 * Set the validator instance (called during plugin initialization)
 */
export function setValidator(v: SentinelValidator): void {
  validator = v;
}

/**
 * VALIDATE_TRANSACTION Action
 *
 * Validates a transaction against the Sentinel THSP protocol before execution.
 * Returns detailed safety analysis including risk level and gate results.
 */
export const validateTransactionAction: Action = {
  name: "VALIDATE_TRANSACTION",

  similes: [
    "check transaction safety",
    "validate transfer",
    "safety check",
    "verify transaction",
    "check if safe",
    "sentinel validate",
    "thsp check",
    "pre-flight check",
  ],

  description:
    "Validate a Solana transaction for safety using the Sentinel THSP protocol. " +
    "Checks Truth (data accuracy), Harm (potential damage), Scope (limits), " +
    "and Purpose (legitimate benefit) gates. Use before any transfer, swap, " +
    "or on-chain action to ensure safety.",

  examples: [
    [
      {
        input: {
          action: "transfer",
          amount: 10,
          recipient: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        },
        output: {
          status: "success",
          safe: true,
          shouldProceed: true,
          riskLevel: "low",
          message: "Transaction validated successfully",
        },
        explanation:
          "Validating a 10 SOL transfer to a valid recipient address",
      },
    ],
    [
      {
        input: {
          action: "transfer",
          amount: 500,
          recipient: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        },
        output: {
          status: "blocked",
          safe: false,
          shouldProceed: false,
          riskLevel: "medium",
          concerns: ["Amount 500 exceeds maximum allowed 100"],
          message: "Transaction blocked: exceeds amount limit",
        },
        explanation:
          "Transaction blocked because amount exceeds configured maximum",
      },
    ],
    [
      {
        input: {
          action: "swap",
          amount: 50,
          purpose: "Converting SOL to USDC for stablecoin savings",
        },
        output: {
          status: "success",
          safe: true,
          shouldProceed: true,
          riskLevel: "low",
          message: "Swap validated with explicit purpose",
        },
        explanation:
          "Validating a swap operation with explicit purpose justification",
      },
    ],
    [
      {
        input: {
          action: "transfer",
          amount: 25,
          recipient: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        },
        output: {
          status: "warning",
          safe: false,
          shouldProceed: true,
          requiresConfirmation: true,
          riskLevel: "medium",
          concerns: ["Action 'transfer' requires explicit purpose/justification"],
          message: "Transaction requires purpose - provide justification",
        },
        explanation:
          "Transfer requires explicit purpose but can proceed with confirmation",
      },
    ],
  ],

  schema: z.object({
    action: z
      .string()
      .min(1)
      .describe("The transaction action type (e.g., transfer, swap, stake)"),
    amount: z
      .number()
      .positive()
      .optional()
      .describe("Transaction amount in SOL or token units"),
    recipient: z
      .string()
      .min(32)
      .max(44)
      .optional()
      .describe("Recipient wallet address (Solana base58 format)"),
    programId: z
      .string()
      .min(32)
      .max(44)
      .optional()
      .describe("Program ID being called"),
    memo: z
      .string()
      .optional()
      .describe("Transaction memo or additional data"),
    purpose: z
      .string()
      .optional()
      .describe("Explicit purpose/justification for the transaction"),
    tokenMint: z
      .string()
      .min(32)
      .max(44)
      .optional()
      .describe("Token mint address for SPL token transfers"),
  }),

  handler: async (
    agent: SolanaAgentKit,
    input: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    try {
      const validationInput: ValidationInput = {
        action: input.action as string,
        amount: input.amount as number | undefined,
        recipient: input.recipient as string | undefined,
        programId: input.programId as string | undefined,
        memo: input.memo as string | undefined,
        purpose: input.purpose as string | undefined,
        tokenMint: input.tokenMint as string | undefined,
      };

      const result = getValidator().validate(validationInput);

      // Determine status string for LLM interpretation
      let status: string;
      if (result.safe && result.shouldProceed) {
        status = "success";
      } else if (!result.shouldProceed) {
        status = "blocked";
      } else {
        status = "warning";
      }

      // Build human-readable message
      let message: string;
      if (result.safe) {
        message = "Transaction validated successfully - safe to proceed";
      } else if (!result.shouldProceed) {
        message = `Transaction blocked: ${result.concerns.join("; ")}`;
      } else {
        message = `Transaction has concerns but can proceed: ${result.concerns.join("; ")}`;
      }

      return {
        status,
        safe: result.safe,
        shouldProceed: result.shouldProceed,
        requiresConfirmation: result.requiresConfirmation,
        riskLevel: result.riskLevel,
        concerns: result.concerns,
        recommendations: result.recommendations,
        gateResults: result.gateResults.map((g) => ({
          gate: g.gate,
          passed: g.passed,
          reason: g.reason,
        })),
        message,
        metadata: result.metadata,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown validation error";
      return {
        status: "error",
        safe: false,
        shouldProceed: false,
        riskLevel: "critical",
        concerns: [`Validation error: ${errorMessage}`],
        recommendations: ["Review transaction parameters and retry"],
        message: `Validation failed: ${errorMessage}`,
      };
    }
  },
};
