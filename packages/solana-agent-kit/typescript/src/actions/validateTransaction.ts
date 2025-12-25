/**
 * VALIDATE_TRANSACTION Action
 *
 * Primary action for validating transactions against the THSP protocol.
 * Follows the Solana Agent Kit action pattern for LLM integration.
 */

import type { Action, SolanaAgentKit } from "solana-agent-kit";
import { z } from "zod";
import { SentinelValidator } from "../tools/validator";
import type { ValidationInput, SafetyValidationResult } from "../types";
import { RiskLevel, THSPGate } from "../types";

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
 * Create a failed result for invalid input
 */
function createErrorResult(message: string): Record<string, unknown> {
  return {
    status: "error",
    safe: false,
    shouldProceed: false,
    riskLevel: RiskLevel.CRITICAL,
    concerns: [message],
    recommendations: ["Fix the input parameters before retrying"],
    gateResults: [{ gate: THSPGate.TRUTH, passed: false, reason: message }],
    message: `Validation failed: ${message}`,
  };
}

/**
 * Validate input types before processing
 */
function validateInputTypes(
  input: Record<string, unknown>
): { valid: true; data: ValidationInput } | { valid: false; error: string } {
  // Action is required and must be a non-empty string
  if (!input.action || typeof input.action !== "string") {
    return { valid: false, error: "action must be a non-empty string" };
  }

  // Amount must be a number if provided
  if (input.amount !== undefined && typeof input.amount !== "number") {
    return { valid: false, error: "amount must be a number" };
  }

  // Recipient must be a string if provided
  if (input.recipient !== undefined && typeof input.recipient !== "string") {
    return { valid: false, error: "recipient must be a string" };
  }

  // ProgramId must be a string if provided
  if (input.programId !== undefined && typeof input.programId !== "string") {
    return { valid: false, error: "programId must be a string" };
  }

  // Memo must be a string if provided
  if (input.memo !== undefined && typeof input.memo !== "string") {
    return { valid: false, error: "memo must be a string" };
  }

  // Purpose must be a string if provided
  if (input.purpose !== undefined && typeof input.purpose !== "string") {
    return { valid: false, error: "purpose must be a string" };
  }

  // TokenMint must be a string if provided
  if (input.tokenMint !== undefined && typeof input.tokenMint !== "string") {
    return { valid: false, error: "tokenMint must be a string" };
  }

  return {
    valid: true,
    data: {
      action: input.action,
      amount: input.amount as number | undefined,
      recipient: input.recipient as string | undefined,
      programId: input.programId as string | undefined,
      memo: input.memo as string | undefined,
      purpose: input.purpose as string | undefined,
      tokenMint: input.tokenMint as string | undefined,
      metadata: input.metadata as Record<string, unknown> | undefined,
    },
  };
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
      // Validate input types before processing
      const validation = validateInputTypes(input);
      if (!validation.valid) {
        return createErrorResult(validation.error);
      }

      const validatorInstance = getValidator();
      const result = validatorInstance.validate(validation.data);

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
      return createErrorResult(errorMessage);
    }
  },
};
