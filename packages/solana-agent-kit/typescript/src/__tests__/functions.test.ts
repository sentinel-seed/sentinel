/**
 * Tests for Sentinel functions (methods exposed to SolanaAgentKit)
 *
 * Run with: npx vitest run src/__tests__/functions.test.ts
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import {
  validateTransaction,
  checkSafety,
  getSafetyStatus,
  blockAddress,
  unblockAddress,
  clearValidationHistory,
  updateSafetyConfig,
  setSharedValidator,
  isValidatorInitialized,
} from "../tools/functions";
import { SentinelValidator } from "../tools/validator";
import { RiskLevel } from "../types";

// Valid Solana addresses for testing
const VALID_ADDRESS = "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM";
const VALID_ADDRESS_2 = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263";
const VALID_PURPOSE = "This is a valid purpose with more than twenty characters";

// Mock SolanaAgentKit instance
const mockAgent = {} as any;

describe("Sentinel Functions", () => {
  let validator: SentinelValidator;

  beforeEach(() => {
    // Create and set a fresh validator for each test
    validator = new SentinelValidator({
      requirePurposeFor: ["transfer", "swap", "stake"],
    });
    setSharedValidator(validator);
  });

  describe("isValidatorInitialized", () => {
    it("should return true when validator is set", () => {
      expect(isValidatorInitialized()).toBe(true);
    });
  });

  describe("validateTransaction", () => {
    it("should validate a valid transaction", () => {
      const result = validateTransaction(mockAgent, {
        action: "transfer",
        amount: 10,
        recipient: VALID_ADDRESS,
        purpose: VALID_PURPOSE,
      });

      expect(result.shouldProceed).toBe(true);
      expect(result.safe).toBe(true);
    });

    it("should reject transaction without purpose when required", () => {
      const result = validateTransaction(mockAgent, {
        action: "transfer",
        amount: 10,
        recipient: VALID_ADDRESS,
      });

      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("purpose"))).toBe(true);
    });
  });

  describe("checkSafety", () => {
    it("should return true for safe transactions", () => {
      const isSafe = checkSafety(
        mockAgent,
        "query", // query doesn't require purpose
        10,
        VALID_ADDRESS
      );

      expect(isSafe).toBe(true);
    });

    it("should return false when purpose is missing for transfer", () => {
      // Transfer requires purpose, so without it should fail
      const isSafe = checkSafety(mockAgent, "transfer", 10, VALID_ADDRESS);

      expect(isSafe).toBe(false);
    });

    it("should return true when purpose is provided for transfer", () => {
      const isSafe = checkSafety(
        mockAgent,
        "transfer",
        10,
        VALID_ADDRESS,
        VALID_PURPOSE
      );

      expect(isSafe).toBe(true);
    });

    it("should accept purpose as 4th parameter", () => {
      const isSafe = checkSafety(
        mockAgent,
        "swap",
        25,
        undefined,
        "Swapping tokens for portfolio rebalancing purposes"
      );

      expect(isSafe).toBe(true);
    });
  });

  describe("blockAddress", () => {
    it("should block a valid address", () => {
      blockAddress(mockAgent, VALID_ADDRESS_2);
      const config = validator.getConfig();
      expect(config.blockedAddresses).toContain(VALID_ADDRESS_2);
    });

    it("should throw error for invalid address", () => {
      expect(() => {
        blockAddress(mockAgent, "invalid-address");
      }).toThrow("[Sentinel] Invalid address format");
    });

    it("should throw error for empty address", () => {
      expect(() => {
        blockAddress(mockAgent, "");
      }).toThrow("[Sentinel] Invalid address format");
    });
  });

  describe("unblockAddress", () => {
    it("should unblock a valid address", () => {
      // First block it
      blockAddress(mockAgent, VALID_ADDRESS_2);
      expect(validator.getConfig().blockedAddresses).toContain(VALID_ADDRESS_2);

      // Then unblock
      unblockAddress(mockAgent, VALID_ADDRESS_2);
      expect(validator.getConfig().blockedAddresses).not.toContain(VALID_ADDRESS_2);
    });

    it("should throw error for invalid address", () => {
      expect(() => {
        unblockAddress(mockAgent, "not-a-valid-address");
      }).toThrow("[Sentinel] Invalid address format");
    });
  });

  describe("getSafetyStatus", () => {
    it("should return stats and config", () => {
      const status = getSafetyStatus(mockAgent);

      expect(status.isActive).toBe(true);
      expect(status.stats).toBeDefined();
      expect(status.config).toBeDefined();
      expect(status.stats.totalValidations).toBe(0);
    });

    it("should reflect validation history", () => {
      // Perform some validations
      validateTransaction(mockAgent, { action: "query", purpose: VALID_PURPOSE });
      validateTransaction(mockAgent, { action: "test", purpose: VALID_PURPOSE });

      const status = getSafetyStatus(mockAgent);
      expect(status.stats.totalValidations).toBe(2);
    });
  });

  describe("clearValidationHistory", () => {
    it("should clear history", () => {
      // Add some validations
      validateTransaction(mockAgent, { action: "test", purpose: VALID_PURPOSE });
      expect(validator.getStats().totalValidations).toBe(1);

      // Clear history
      clearValidationHistory(mockAgent);
      expect(validator.getStats().totalValidations).toBe(0);
    });
  });

  describe("updateSafetyConfig", () => {
    it("should update configuration", () => {
      updateSafetyConfig(mockAgent, { maxTransactionAmount: 200 });
      const config = validator.getConfig();
      expect(config.maxTransactionAmount).toBe(200);
    });

    it("should update strictMode", () => {
      updateSafetyConfig(mockAgent, { strictMode: true });
      const config = validator.getConfig();
      expect(config.strictMode).toBe(true);
    });
  });
});
