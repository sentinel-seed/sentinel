/**
 * Core validation logic for Sentinel safety checks
 *
 * Implements the THSP (Truth-Harm-Scope-Purpose) protocol for
 * validating AI agent transactions on Solana.
 */

import type { SolanaAgentKit } from "solana-agent-kit";
import { PublicKey } from "@solana/web3.js";
import {
  type SafetyValidationResult,
  type ValidationInput,
  type SentinelPluginConfig,
  type GateResult,
  type ValidationStats,
  type SuspiciousPattern,
  RiskLevel,
  THSPGate,
  AddressValidationMode,
  DEFAULT_CONFIG,
  DEFAULT_SUSPICIOUS_PATTERNS,
  HIGH_RISK_ACTIONS,
} from "../types";

// Allowed metadata keys to prevent injection via arbitrary metadata
const ALLOWED_METADATA_KEYS = new Set([
  "fromToken",
  "toToken",
  "slippage",
  "protocol",
  "expectedAPY",
  "bridge",
  "fromChain",
  "toChain",
  "tokenSymbol",
  "tokenName",
  "decimals",
]);

/**
 * Validate Solana address using PublicKey
 * This properly validates base58 encoding and checksum
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
 * Filter metadata to only allowed keys
 */
function sanitizeMetadata(
  metadata: Record<string, unknown> | undefined
): Record<string, unknown> {
  if (!metadata || typeof metadata !== "object") {
    return {};
  }
  const sanitized: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(metadata)) {
    if (ALLOWED_METADATA_KEYS.has(key)) {
      // Only allow primitive values
      if (
        typeof value === "string" ||
        typeof value === "number" ||
        typeof value === "boolean"
      ) {
        sanitized[key] = value;
      }
    }
  }
  return sanitized;
}

/**
 * Sentinel Validator - Core safety validation engine
 *
 * Validates transactions against the THSP protocol before execution.
 * Each transaction must pass all four gates to be approved.
 */
/** Compiled pattern with cached regex */
interface CompiledPattern {
  name: string;
  regex: RegExp;
  riskLevel: RiskLevel;
  message: string;
}

export class SentinelValidator {
  private config: Required<
    Omit<SentinelPluginConfig, "customPatterns" | "onValidation" | "blockedAddresses" | "allowedPrograms">
  > &
    Pick<SentinelPluginConfig, "customPatterns" | "blockedAddresses" | "allowedPrograms" | "onValidation">;
  private history: SafetyValidationResult[] = [];
  private agent: SolanaAgentKit | null = null;
  private compiledPatterns: CompiledPattern[] = [];

  constructor(config: SentinelPluginConfig = {}) {
    this.config = {
      ...DEFAULT_CONFIG,
      ...config,
      customPatterns: [
        ...DEFAULT_SUSPICIOUS_PATTERNS,
        ...(config.customPatterns || []),
      ],
    };
    // Pre-compile all patterns for performance
    this.compilePatterns();
  }

  /**
   * Compile regex patterns once for performance
   */
  private compilePatterns(): void {
    this.compiledPatterns = (this.config.customPatterns || []).map(
      (pattern: SuspiciousPattern) => ({
        name: pattern.name,
        regex:
          typeof pattern.pattern === "string"
            ? new RegExp(pattern.pattern, "i")
            : pattern.pattern,
        riskLevel: pattern.riskLevel,
        message: pattern.message,
      })
    );
  }

  /**
   * Create a failed validation result for early returns
   */
  private createFailedResult(reason: string, startTime: number): SafetyValidationResult {
    return {
      safe: false,
      riskLevel: RiskLevel.CRITICAL,
      shouldProceed: false,
      requiresConfirmation: false,
      gateResults: [
        { gate: THSPGate.TRUTH, passed: false, reason },
      ],
      concerns: [reason],
      recommendations: ["Fix the input parameters before retrying"],
      metadata: {
        action: "invalid",
        timestamp: Date.now(),
        validationDurationMs: Date.now() - startTime,
      },
    };
  }

  /**
   * Initialize validator with agent instance
   * Called automatically when plugin is registered
   */
  initialize(agent: SolanaAgentKit): void {
    this.agent = agent;
  }

  /**
   * Validate a transaction against THSP protocol
   *
   * @param input - Transaction parameters to validate
   * @returns Validation result with detailed gate analysis
   */
  validate(input: ValidationInput): SafetyValidationResult {
    const startTime = Date.now();

    // Input validation - fail fast for invalid input
    if (!input || typeof input !== "object") {
      return this.createFailedResult("Invalid input: must be an object", startTime);
    }

    if (!input.action || typeof input.action !== "string") {
      return this.createFailedResult("Invalid input: action must be a non-empty string", startTime);
    }

    // Check for Infinity and other edge cases in amount
    if (input.amount !== undefined) {
      if (!Number.isFinite(input.amount)) {
        return this.createFailedResult(
          `Invalid amount: ${input.amount} is not a valid finite number`,
          startTime
        );
      }
    }

    const gateResults: GateResult[] = [];
    const concerns: string[] = [];
    const recommendations: string[] = [];
    let riskLevel = RiskLevel.LOW;

    // GATE 1: TRUTH - Verify transaction data accuracy
    const truthResult = this.checkTruthGate(input);
    gateResults.push(truthResult);
    if (!truthResult.passed) {
      concerns.push(truthResult.reason || "Truth gate failed");
    }

    // GATE 2: HARM - Assess potential for damage
    const harmResult = this.checkHarmGate(input);
    gateResults.push(harmResult);
    if (!harmResult.passed) {
      concerns.push(harmResult.reason || "Harm gate failed");
      riskLevel = this.escalateRisk(riskLevel, RiskLevel.HIGH);
    }

    // GATE 3: SCOPE - Check boundaries and limits
    const scopeResult = this.checkScopeGate(input);
    gateResults.push(scopeResult);
    if (!scopeResult.passed) {
      concerns.push(scopeResult.reason || "Scope gate failed");
      riskLevel = this.escalateRisk(riskLevel, RiskLevel.MEDIUM);
    }

    // GATE 4: PURPOSE - Verify legitimate benefit
    const purposeResult = this.checkPurposeGate(input);
    gateResults.push(purposeResult);
    if (!purposeResult.passed) {
      concerns.push(purposeResult.reason || "Purpose gate failed");
      riskLevel = this.escalateRisk(riskLevel, RiskLevel.MEDIUM);
    }

    // Check for suspicious patterns
    const patternConcerns = this.checkSuspiciousPatterns(input);
    concerns.push(...patternConcerns.concerns);
    riskLevel = this.escalateRisk(riskLevel, patternConcerns.riskLevel);

    // Generate recommendations
    recommendations.push(...this.generateRecommendations(input, concerns, riskLevel));

    // Determine final verdict
    const allGatesPassed = gateResults.every((g) => g.passed);
    const safe = allGatesPassed && concerns.length === 0;
    const shouldProceed = this.config.strictMode
      ? safe
      : riskLevel !== RiskLevel.CRITICAL && allGatesPassed;
    const requiresConfirmation =
      (input.amount || 0) > this.config.confirmationThreshold ||
      riskLevel === RiskLevel.HIGH;

    const result: SafetyValidationResult = {
      safe,
      riskLevel,
      shouldProceed,
      requiresConfirmation,
      gateResults,
      concerns,
      recommendations,
      metadata: {
        action: input.action,
        timestamp: Date.now(),
        validationDurationMs: Date.now() - startTime,
      },
    };

    // Store in history (check size BEFORE push to prevent exceeding limit)
    if (this.history.length >= this.config.maxHistorySize) {
      this.history.shift();
    }
    this.history.push(result);

    // Call optional callback (wrapped in try/catch to prevent callback errors from crashing validation)
    if (this.config.onValidation) {
      try {
        this.config.onValidation(result);
      } catch (callbackError) {
        console.error("[Sentinel] onValidation callback error:", callbackError);
      }
    }

    return result;
  }

  /**
   * TRUTH GATE: Verify the accuracy and validity of transaction data
   */
  private checkTruthGate(input: ValidationInput): GateResult {
    const addressMode = this.config.addressValidation;

    // Check for valid recipient address format based on validation mode
    if (input.recipient) {
      const isValidAddress = isValidSolanaAddress(input.recipient);

      if (!isValidAddress) {
        if (addressMode === AddressValidationMode.STRICT) {
          return {
            gate: THSPGate.TRUTH,
            passed: false,
            reason: `Invalid recipient address format: ${input.recipient.slice(0, 16)}...`,
          };
        } else if (addressMode === AddressValidationMode.WARN) {
          // Log warning but continue - address format issue is noted
          console.warn(
            `[Sentinel] Address may be invalid (not base58): ${input.recipient.slice(0, 16)}...`
          );
        }
        // IGNORE mode: no action, proceed silently
      }
    }

    // Check for valid program ID format (always strict - programs must be valid)
    if (input.programId) {
      const isValidProgram = isValidSolanaAddress(input.programId);
      if (!isValidProgram) {
        return {
          gate: THSPGate.TRUTH,
          passed: false,
          reason: `Invalid program ID format: ${input.programId.slice(0, 16)}...`,
        };
      }
    }

    // Check for reasonable amount (not negative, not NaN)
    if (input.amount !== undefined) {
      if (isNaN(input.amount)) {
        return {
          gate: THSPGate.TRUTH,
          passed: false,
          reason: "Transaction amount is not a valid number",
        };
      }
      if (input.amount < 0) {
        return {
          gate: THSPGate.TRUTH,
          passed: false,
          reason: `Transaction amount cannot be negative: ${input.amount}`,
        };
      }
    }

    // Validate tokenMint if provided
    if (input.tokenMint) {
      if (!isValidSolanaAddress(input.tokenMint)) {
        return {
          gate: THSPGate.TRUTH,
          passed: false,
          reason: `Invalid token mint address: ${input.tokenMint.slice(0, 16)}...`,
        };
      }
    }

    return {
      gate: THSPGate.TRUTH,
      passed: true,
    };
  }

  /**
   * HARM GATE: Assess potential for damage to users or systems
   */
  private checkHarmGate(input: ValidationInput): GateResult {
    // Check against blocked addresses with proper type guard
    if (
      input.recipient &&
      Array.isArray(this.config.blockedAddresses) &&
      this.config.blockedAddresses.includes(input.recipient)
    ) {
      return {
        gate: THSPGate.HARM,
        passed: false,
        reason: `Recipient is a known blocked address: ${input.recipient.slice(0, 8)}...`,
      };
    }

    // Check for high-risk action patterns (action already validated as string)
    const actionLower = input.action.toLowerCase();
    const isHighRisk = HIGH_RISK_ACTIONS.some((pattern) =>
      actionLower.includes(pattern.toLowerCase())
    );
    if (isHighRisk) {
      return {
        gate: THSPGate.HARM,
        passed: false,
        reason: `High-risk action detected: ${input.action}`,
      };
    }

    // Check program whitelist if configured
    if (
      this.config.allowedPrograms &&
      this.config.allowedPrograms.length > 0 &&
      input.programId
    ) {
      if (!this.config.allowedPrograms.includes(input.programId)) {
        return {
          gate: THSPGate.HARM,
          passed: false,
          reason: `Program not in whitelist: ${input.programId.slice(0, 8)}...`,
        };
      }
    }

    return {
      gate: THSPGate.HARM,
      passed: true,
    };
  }

  /**
   * SCOPE GATE: Check if transaction is within appropriate boundaries
   */
  private checkScopeGate(input: ValidationInput): GateResult {
    // Check transaction amount limits
    if (
      input.amount !== undefined &&
      input.amount > this.config.maxTransactionAmount
    ) {
      return {
        gate: THSPGate.SCOPE,
        passed: false,
        reason: `Amount ${input.amount} exceeds maximum allowed ${this.config.maxTransactionAmount}`,
      };
    }

    return {
      gate: THSPGate.SCOPE,
      passed: true,
    };
  }

  /**
   * PURPOSE GATE: Verify legitimate benefit and explicit justification
   */
  private checkPurposeGate(input: ValidationInput): GateResult {
    const actionLower = input.action.toLowerCase();

    // Check if this action requires explicit purpose
    const requiresPurpose = this.config.requirePurposeFor.some((keyword) =>
      actionLower.includes(keyword.toLowerCase())
    );

    if (requiresPurpose && !input.purpose) {
      return {
        gate: THSPGate.PURPOSE,
        passed: false,
        reason: `Action '${input.action}' requires explicit purpose/justification`,
      };
    }

    // Validate purpose content if provided
    if (input.purpose) {
      const trimmedPurpose = input.purpose.trim();

      // Purpose must be at least 20 characters for meaningful justification
      if (trimmedPurpose.length < 20) {
        return {
          gate: THSPGate.PURPOSE,
          passed: false,
          reason: "Purpose explanation is too brief - provide at least 20 characters",
        };
      }

      // Purpose should have at least 3 words
      const words = trimmedPurpose.split(/\s+/).filter((w) => w.length > 0);
      if (words.length < 3) {
        return {
          gate: THSPGate.PURPOSE,
          passed: false,
          reason: "Purpose should contain at least 3 words to be meaningful",
        };
      }

      // Reject if purpose is mostly repeated characters (e.g., "aaaaaaaaaaaaaaaaaaaaa")
      if (/^(.)\1{9,}$/.test(trimmedPurpose.replace(/\s/g, ""))) {
        return {
          gate: THSPGate.PURPOSE,
          passed: false,
          reason: "Purpose appears to be meaningless repeated characters",
        };
      }
    }

    return {
      gate: THSPGate.PURPOSE,
      passed: true,
    };
  }

  /**
   * Check for suspicious patterns in transaction data
   */
  private checkSuspiciousPatterns(input: ValidationInput): {
    concerns: string[];
    riskLevel: RiskLevel;
  } {
    const concerns: string[] = [];
    let maxRisk = RiskLevel.LOW;

    // Sanitize metadata to prevent injection attacks
    const safeMetadata = sanitizeMetadata(input.metadata);

    // Build text to check from validated fields
    const textToCheck = [
      input.action,
      input.memo,
      input.purpose,
      Object.keys(safeMetadata).length > 0 ? JSON.stringify(safeMetadata) : "",
    ]
      .filter(Boolean)
      .join(" ");

    // Use pre-compiled patterns for performance
    for (const compiled of this.compiledPatterns) {
      if (compiled.regex.test(textToCheck)) {
        concerns.push(compiled.message);
        maxRisk = this.escalateRisk(maxRisk, compiled.riskLevel);
      }
    }

    return { concerns, riskLevel: maxRisk };
  }

  /**
   * Generate actionable recommendations based on validation results
   */
  private generateRecommendations(
    input: ValidationInput,
    concerns: string[],
    riskLevel: RiskLevel
  ): string[] {
    const recommendations: string[] = [];

    if ((input.amount || 0) > this.config.confirmationThreshold) {
      recommendations.push(
        "High-value transaction - manual confirmation recommended"
      );
    }

    if (riskLevel === RiskLevel.HIGH || riskLevel === RiskLevel.CRITICAL) {
      recommendations.push("Review transaction details carefully before proceeding");
    }

    if (concerns.some((c) => c.includes("purpose"))) {
      recommendations.push(
        `Provide explicit purpose for ${input.action} using the 'purpose' parameter`
      );
    }

    if (!input.recipient && input.action.toLowerCase().includes("transfer")) {
      recommendations.push("Verify recipient address before proceeding");
    }

    return recommendations;
  }

  /**
   * Escalate risk level (never downgrade)
   */
  private escalateRisk(current: RiskLevel, incoming: RiskLevel): RiskLevel {
    const levels = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL];
    const currentIndex = levels.indexOf(current);
    const incomingIndex = levels.indexOf(incoming);
    return levels[Math.max(currentIndex, incomingIndex)];
  }

  /**
   * Get validation statistics
   */
  getStats(): ValidationStats {
    if (this.history.length === 0) {
      return {
        totalValidations: 0,
        blocked: 0,
        approved: 0,
        highRisk: 0,
        byAction: {},
        blockRate: 0,
      };
    }

    const blocked = this.history.filter((r) => !r.shouldProceed).length;
    const highRisk = this.history.filter(
      (r) => r.riskLevel === RiskLevel.HIGH || r.riskLevel === RiskLevel.CRITICAL
    ).length;

    const byAction: Record<string, number> = {};
    for (const result of this.history) {
      byAction[result.metadata.action] =
        (byAction[result.metadata.action] || 0) + 1;
    }

    return {
      totalValidations: this.history.length,
      blocked,
      approved: this.history.length - blocked,
      highRisk,
      byAction,
      blockRate: blocked / this.history.length,
    };
  }

  /**
   * Clear validation history
   */
  clearHistory(): void {
    this.history = [];
  }

  /**
   * Get current configuration
   */
  getConfig(): SentinelPluginConfig {
    return { ...this.config };
  }

  /**
   * Update configuration
   */
  updateConfig(updates: Partial<SentinelPluginConfig>): void {
    const hadPatternUpdate = updates.customPatterns !== undefined;

    this.config = {
      ...this.config,
      ...updates,
    };

    // Recompile patterns if customPatterns was updated
    if (hadPatternUpdate) {
      this.compilePatterns();
    }
  }

  /**
   * Add address to blocklist
   */
  blockAddress(address: string): void {
    if (!this.config.blockedAddresses) {
      this.config.blockedAddresses = [];
    }
    if (!this.config.blockedAddresses.includes(address)) {
      this.config.blockedAddresses.push(address);
    }
  }

  /**
   * Remove address from blocklist
   */
  unblockAddress(address: string): void {
    if (this.config.blockedAddresses) {
      this.config.blockedAddresses = this.config.blockedAddresses.filter(
        (a) => a !== address
      );
    }
  }
}

/**
 * Create a new validator instance with configuration
 */
export function createValidator(config?: SentinelPluginConfig): SentinelValidator {
  return new SentinelValidator(config);
}
