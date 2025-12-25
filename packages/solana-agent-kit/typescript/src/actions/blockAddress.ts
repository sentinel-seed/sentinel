/**
 * BLOCK_ADDRESS and UNBLOCK_ADDRESS Actions
 *
 * Manage the address blocklist for transaction validation.
 */

import type { Action, SolanaAgentKit } from "solana-agent-kit";
import { z } from "zod";
import { PublicKey } from "@solana/web3.js";
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
 * Validate Solana address using PublicKey
 */
function isValidSolanaAddress(address: string): boolean {
  if (!address || typeof address !== "string") {
    return false;
  }
  try {
    new PublicKey(address);
    return true;
  } catch {
    return false;
  }
}

/**
 * BLOCK_ADDRESS Action
 *
 * Add an address to the blocklist to prevent transactions to that address.
 */
export const blockAddressAction: Action = {
  name: "BLOCK_ADDRESS",

  similes: [
    "block wallet",
    "blacklist address",
    "ban address",
    "add to blocklist",
    "mark as scam",
    "flag address",
  ],

  description:
    "Add a wallet address to the Sentinel blocklist. All future transactions " +
    "to this address will be blocked. Use to protect against known scam " +
    "addresses or compromised wallets.",

  examples: [
    [
      {
        input: {
          address: "ScamWa11etAddress111111111111111111111111111",
        },
        output: {
          status: "success",
          blocked: true,
          address: "ScamWa11etAddress111111111111111111111111111",
          message: "Address added to blocklist",
        },
        explanation: "Adding a known scam address to the blocklist",
      },
    ],
  ],

  schema: z.object({
    address: z
      .string()
      .min(32)
      .max(44)
      .describe("Solana wallet address to block (base58 format)"),
  }),

  handler: async (
    agent: SolanaAgentKit,
    input: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    try {
      // Validate address is a string
      if (!input.address || typeof input.address !== "string") {
        return {
          status: "error",
          blocked: false,
          message: "Invalid input: address must be a non-empty string",
        };
      }

      const address = input.address;

      // Validate address format using PublicKey
      if (!isValidSolanaAddress(address)) {
        return {
          status: "error",
          blocked: false,
          message: "Invalid address format - must be valid Solana base58 address",
        };
      }

      // Check if already blocked
      const config = getValidator().getConfig();
      const alreadyBlocked =
        Array.isArray(config.blockedAddresses) &&
        config.blockedAddresses.includes(address);

      if (alreadyBlocked) {
        return {
          status: "success",
          blocked: true,
          alreadyBlocked: true,
          address,
          message: `Address ${address.slice(0, 8)}... is already blocked`,
        };
      }

      getValidator().blockAddress(address);

      return {
        status: "success",
        blocked: true,
        newlyBlocked: true,
        address,
        message: `Address ${address.slice(0, 8)}... added to blocklist`,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      return {
        status: "error",
        blocked: false,
        message: `Failed to block address: ${errorMessage}`,
      };
    }
  },
};

/**
 * UNBLOCK_ADDRESS Action
 *
 * Remove an address from the blocklist.
 */
export const unblockAddressAction: Action = {
  name: "UNBLOCK_ADDRESS",

  similes: [
    "unblock wallet",
    "remove from blocklist",
    "whitelist address",
    "unban address",
    "clear block",
  ],

  description:
    "Remove a wallet address from the Sentinel blocklist. Transactions to " +
    "this address will be allowed again (subject to other safety checks).",

  examples: [
    [
      {
        input: {
          address: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
        },
        output: {
          status: "success",
          unblocked: true,
          address: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
          message: "Address removed from blocklist",
        },
        explanation: "Removing an address from the blocklist after verification",
      },
    ],
  ],

  schema: z.object({
    address: z
      .string()
      .min(32)
      .max(44)
      .describe("Solana wallet address to unblock"),
  }),

  handler: async (
    agent: SolanaAgentKit,
    input: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    try {
      // Validate address is a string
      if (!input.address || typeof input.address !== "string") {
        return {
          status: "error",
          unblocked: false,
          message: "Invalid input: address must be a non-empty string",
        };
      }

      const address = input.address;

      // Validate address format using PublicKey
      if (!isValidSolanaAddress(address)) {
        return {
          status: "error",
          unblocked: false,
          message: "Invalid address format - must be valid Solana base58 address",
        };
      }

      // Check if address is in blocklist
      const config = getValidator().getConfig();
      const isBlocked =
        Array.isArray(config.blockedAddresses) &&
        config.blockedAddresses.includes(address);

      if (!isBlocked) {
        return {
          status: "success",
          unblocked: true,
          wasBlocked: false,
          address,
          message: `Address ${address.slice(0, 8)}... was not in blocklist`,
        };
      }

      getValidator().unblockAddress(address);

      return {
        status: "success",
        unblocked: true,
        wasBlocked: true,
        address,
        message: `Address ${address.slice(0, 8)}... removed from blocklist`,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";
      return {
        status: "error",
        unblocked: false,
        message: `Failed to unblock address: ${errorMessage}`,
      };
    }
  },
};
