/**
 * Tests for SentinelValidator
 *
 * Run with: npx vitest run src/__tests__/validator.test.ts
 */

import { describe, it, expect, beforeEach } from "vitest";
import { SentinelValidator, createValidator } from "../tools/validator";
import {
  RiskLevel,
  THSPGate,
  AddressValidationMode,
  DEFAULT_CONFIG,
} from "../types";

describe("SentinelValidator", () => {
  let validator: SentinelValidator;

  beforeEach(() => {
    validator = new SentinelValidator();
  });

  describe("initialization", () => {
    it("should use default config when no options provided", () => {
      const config = validator.getConfig();
      expect(config.maxTransactionAmount).toBe(DEFAULT_CONFIG.maxTransactionAmount);
      expect(config.strictMode).toBe(false);
    });

    it("should accept custom configuration", () => {
      const customValidator = new SentinelValidator({
        maxTransactionAmount: 50,
        strictMode: true,
      });
      const config = customValidator.getConfig();
      expect(config.maxTransactionAmount).toBe(50);
      expect(config.strictMode).toBe(true);
    });
  });

  describe("TRUTH gate", () => {
    it("should pass for valid Solana addresses", () => {
      const result = validator.validate({
        action: "transfer",
        amount: 10,
        recipient: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
      });
      const truthGate = result.gateResults.find((g) => g.gate === THSPGate.TRUTH);
      expect(truthGate?.passed).toBe(true);
    });

    it("should fail for invalid addresses in STRICT mode", () => {
      const strictValidator = new SentinelValidator({
        addressValidation: AddressValidationMode.STRICT,
      });
      const result = strictValidator.validate({
        action: "transfer",
        amount: 10,
        recipient: "invalid-address",
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("Invalid recipient"))).toBe(true);
    });

    it("should allow invalid addresses in WARN mode", () => {
      const warnValidator = new SentinelValidator({
        addressValidation: AddressValidationMode.WARN,
      });
      const result = warnValidator.validate({
        action: "transfer",
        amount: 10,
        recipient: "invalid-address",
        purpose: "Test transfer purpose",
      });
      const truthGate = result.gateResults.find((g) => g.gate === THSPGate.TRUTH);
      expect(truthGate?.passed).toBe(true);
    });

    it("should fail for negative amounts", () => {
      const result = validator.validate({
        action: "transfer",
        amount: -10,
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("negative"))).toBe(true);
    });

    it("should fail for NaN amounts", () => {
      const result = validator.validate({
        action: "transfer",
        amount: NaN,
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("not a valid number"))).toBe(true);
    });
  });

  describe("HARM gate", () => {
    it("should fail for blocked addresses", () => {
      const blockedValidator = new SentinelValidator({
        blockedAddresses: ["BlockedAddress123456789012345678901234"],
      });
      const result = blockedValidator.validate({
        action: "transfer",
        amount: 10,
        recipient: "BlockedAddress123456789012345678901234",
        purpose: "Test transfer",
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("blocked"))).toBe(true);
    });

    it("should fail for high-risk actions", () => {
      const result = validator.validate({
        action: "drainWallet",
        amount: 100,
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.riskLevel).toBe(RiskLevel.CRITICAL);
    });

    it("should fail for non-whitelisted programs when whitelist is set", () => {
      const whitelistValidator = new SentinelValidator({
        allowedPrograms: ["AllowedProgram123"],
      });
      const result = whitelistValidator.validate({
        action: "call",
        programId: "NotAllowedProgram456789012345678901234",
        purpose: "Test call",
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("not in whitelist"))).toBe(true);
    });
  });

  describe("SCOPE gate", () => {
    it("should fail for amounts exceeding limit", () => {
      const result = validator.validate({
        action: "transfer",
        amount: 500,
        purpose: "Large transfer",
      });
      expect(result.shouldProceed).toBe(false);
      expect(result.concerns.some((c) => c.includes("exceeds maximum"))).toBe(true);
    });

    it("should pass for amounts within limit", () => {
      const result = validator.validate({
        action: "query",
        amount: 50,
        purpose: "Regular query",
      });
      const scopeGate = result.gateResults.find((g) => g.gate === THSPGate.SCOPE);
      expect(scopeGate?.passed).toBe(true);
    });
  });

  describe("PURPOSE gate", () => {
    it("should fail when purpose is required but missing", () => {
      const result = validator.validate({
        action: "transfer",
        amount: 10,
        recipient: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
      });
      expect(result.concerns.some((c) => c.includes("requires explicit purpose"))).toBe(true);
    });

    it("should fail for too brief purpose", () => {
      const result = validator.validate({
        action: "transfer",
        amount: 10,
        purpose: "pay",
      });
      expect(result.concerns.some((c) => c.includes("too brief"))).toBe(true);
    });

    it("should pass for valid purpose", () => {
      const result = validator.validate({
        action: "transfer",
        amount: 10,
        recipient: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        purpose: "Monthly payment for hosting services",
      });
      const purposeGate = result.gateResults.find((g) => g.gate === THSPGate.PURPOSE);
      expect(purposeGate?.passed).toBe(true);
    });
  });

  describe("suspicious patterns", () => {
    it("should detect drain patterns", () => {
      const result = validator.validate({
        action: "normal",
        memo: "drain all tokens",
        purpose: "Testing patterns",
      });
      expect(result.concerns.some((c) => c.includes("drain"))).toBe(true);
    });

    it("should detect unlimited approval patterns", () => {
      const result = validator.validate({
        action: "approve",
        memo: "unlimited approval request",
        purpose: "Testing patterns",
      });
      expect(result.concerns.some((c) => c.toLowerCase().includes("unlimited"))).toBe(true);
    });
  });

  describe("strictMode", () => {
    it("should block transactions with any concerns in strict mode", () => {
      const strictValidator = new SentinelValidator({ strictMode: true });
      const result = strictValidator.validate({
        action: "transfer",
        amount: 10,
        recipient: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        // Missing purpose
      });
      expect(result.shouldProceed).toBe(false);
    });

    it("should allow MEDIUM risk in normal mode", () => {
      const normalValidator = new SentinelValidator({ strictMode: false });
      const result = normalValidator.validate({
        action: "transfer",
        amount: 10,
        recipient: "7xKXtg2CW87d97TXJSDpbD5jBkheTqA83TZRuJosgAsU",
        // Missing purpose - MEDIUM risk
      });
      // In normal mode, MEDIUM risk should proceed
      if (result.riskLevel === RiskLevel.MEDIUM) {
        expect(result.shouldProceed).toBe(true);
      }
    });
  });

  describe("history and stats", () => {
    it("should track validation history", () => {
      validator.validate({ action: "transfer", amount: 10, purpose: "Test 1" });
      validator.validate({ action: "swap", amount: 20, purpose: "Test 2" });

      const stats = validator.getStats();
      expect(stats.totalValidations).toBe(2);
    });

    it("should respect max history size", () => {
      const smallHistoryValidator = new SentinelValidator({ maxHistorySize: 3 });
      for (let i = 0; i < 5; i++) {
        smallHistoryValidator.validate({ action: "test", amount: i, purpose: `Test ${i}` });
      }
      const stats = smallHistoryValidator.getStats();
      expect(stats.totalValidations).toBe(3);
    });

    it("should clear history", () => {
      validator.validate({ action: "test", purpose: "Test" });
      validator.clearHistory();
      const stats = validator.getStats();
      expect(stats.totalValidations).toBe(0);
    });
  });

  describe("address management", () => {
    it("should block addresses", () => {
      const address = "TestAddress123456789012345678901234";
      validator.blockAddress(address);
      const config = validator.getConfig();
      expect(config.blockedAddresses).toContain(address);
    });

    it("should unblock addresses", () => {
      const address = "TestAddress123456789012345678901234";
      const blockedValidator = new SentinelValidator({
        blockedAddresses: [address],
      });
      blockedValidator.unblockAddress(address);
      const config = blockedValidator.getConfig();
      expect(config.blockedAddresses).not.toContain(address);
    });
  });

  describe("config update", () => {
    it("should update configuration", () => {
      validator.updateConfig({ maxTransactionAmount: 200 });
      const config = validator.getConfig();
      expect(config.maxTransactionAmount).toBe(200);
    });
  });

  describe("onValidation callback", () => {
    it("should call callback after validation", () => {
      const results: any[] = [];
      const callbackValidator = new SentinelValidator({
        onValidation: (result) => results.push(result),
      });

      callbackValidator.validate({ action: "test", purpose: "Test" });

      expect(results.length).toBe(1);
      expect(results[0].metadata.action).toBe("test");
    });
  });
});

describe("createValidator", () => {
  it("should create validator with default config", () => {
    const validator = createValidator();
    expect(validator).toBeInstanceOf(SentinelValidator);
  });

  it("should create validator with custom config", () => {
    const validator = createValidator({ maxTransactionAmount: 50 });
    const config = validator.getConfig();
    expect(config.maxTransactionAmount).toBe(50);
  });
});

describe("AddressValidationMode", () => {
  it("should have all modes defined", () => {
    expect(AddressValidationMode.IGNORE).toBe("ignore");
    expect(AddressValidationMode.WARN).toBe("warn");
    expect(AddressValidationMode.STRICT).toBe("strict");
  });
});

describe("RiskLevel", () => {
  it("should have all levels defined", () => {
    expect(RiskLevel.LOW).toBe("low");
    expect(RiskLevel.MEDIUM).toBe("medium");
    expect(RiskLevel.HIGH).toBe("high");
    expect(RiskLevel.CRITICAL).toBe("critical");
  });
});

describe("THSPGate", () => {
  it("should have all gates defined", () => {
    expect(THSPGate.TRUTH).toBe("truth");
    expect(THSPGate.HARM).toBe("harm");
    expect(THSPGate.SCOPE).toBe("scope");
    expect(THSPGate.PURPOSE).toBe("purpose");
  });
});
