/**
 * Type definitions for Sentinel Solana Agent Kit Plugin
 *
 * These types define the safety validation system that integrates
 * with Solana Agent Kit to protect AI agent transactions.
 */

/**
 * Risk levels for transaction assessment
 */
export enum RiskLevel {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical",
}

/**
 * Address validation modes - how to handle invalid Solana addresses
 *
 * IGNORE: Don't validate address format (not recommended)
 * WARN: Log warning but allow transaction to proceed
 * STRICT: Reject transactions with invalid address format (default)
 */
export enum AddressValidationMode {
  IGNORE = "ignore",
  WARN = "warn",
  STRICT = "strict",
}

/**
 * THSP Gate identifiers - the four gates of the Sentinel protocol
 * Truth: Is the action based on accurate information?
 * Harm: Could this cause damage to users or systems?
 * Scope: Is this within appropriate boundaries?
 * Purpose: Does this serve a legitimate benefit?
 */
export enum THSPGate {
  TRUTH = "truth",
  HARM = "harm",
  SCOPE = "scope",
  PURPOSE = "purpose",
}

/**
 * Result of a single THSP gate check
 */
export interface GateResult {
  gate: THSPGate;
  passed: boolean;
  reason?: string;
}

/**
 * Complete result of transaction safety validation
 */
export interface SafetyValidationResult {
  safe: boolean;
  riskLevel: RiskLevel;
  shouldProceed: boolean;
  requiresConfirmation: boolean;
  gateResults: GateResult[];
  concerns: string[];
  recommendations: string[];
  metadata: {
    action: string;
    timestamp: number;
    validationDurationMs: number;
  };
}

/**
 * Configuration options for the Sentinel plugin
 */
export interface SentinelPluginConfig {
  /**
   * Maximum amount (in SOL or token units) allowed per single transaction
   * Transactions exceeding this will be blocked
   * @default 100
   */
  maxTransactionAmount?: number;

  /**
   * Amount threshold that triggers confirmation requirement
   * @default 10
   */
  confirmationThreshold?: number;

  /**
   * List of blocked wallet addresses (known scams, etc.)
   */
  blockedAddresses?: string[];

  /**
   * Whitelist of allowed program IDs (empty = all allowed)
   */
  allowedPrograms?: string[];

  /**
   * Actions that require explicit purpose justification
   * @default ["transfer", "swap", "approve", "bridge", "withdraw", "stake"]
   */
  requirePurposeFor?: string[];

  /**
   * Enable strict mode - block any transaction with concerns
   * @default false
   */
  strictMode?: boolean;

  /**
   * Address validation mode - how to handle invalid Solana addresses
   * IGNORE: Don't validate (not recommended)
   * WARN: Log warning but proceed
   * STRICT: Reject invalid addresses (default)
   * @default AddressValidationMode.STRICT
   */
  addressValidation?: AddressValidationMode;

  /**
   * Maximum number of validation results to keep in history
   * Older entries are removed when limit is exceeded
   * @default 1000
   */
  maxHistorySize?: number;

  /**
   * Custom suspicious patterns to detect
   */
  customPatterns?: SuspiciousPattern[];

  /**
   * Callback for logging/monitoring validation results
   */
  onValidation?: (result: SafetyValidationResult) => void;
}

/**
 * Pattern definition for detecting suspicious behavior
 */
export interface SuspiciousPattern {
  name: string;
  pattern: RegExp | string;
  riskLevel: RiskLevel;
  message: string;
}

/**
 * Input parameters for transaction validation
 */
export interface ValidationInput {
  action: string;
  amount?: number;
  recipient?: string;
  programId?: string;
  memo?: string;
  purpose?: string;
  tokenMint?: string;
  metadata?: Record<string, unknown>;
}

/**
 * Statistics about validation history
 */
export interface ValidationStats {
  totalValidations: number;
  blocked: number;
  approved: number;
  highRisk: number;
  byAction: Record<string, number>;
  blockRate: number;
}

/**
 * Seed variants available for different context sizes
 */
export type SeedVariant = "minimal" | "standard" | "full";

/**
 * Default configuration values
 */
export const DEFAULT_CONFIG: Required<
  Omit<SentinelPluginConfig, "customPatterns" | "onValidation" | "blockedAddresses" | "allowedPrograms">
> & Pick<SentinelPluginConfig, "customPatterns" | "blockedAddresses" | "allowedPrograms"> = {
  maxTransactionAmount: 100,
  confirmationThreshold: 10,
  blockedAddresses: [],
  allowedPrograms: [],
  requirePurposeFor: ["transfer", "swap", "approve", "bridge", "withdraw", "stake"],
  strictMode: false,
  addressValidation: AddressValidationMode.STRICT,
  maxHistorySize: 1000,
  customPatterns: [],
};

/**
 * Actions that are considered high-risk by default
 */
export const HIGH_RISK_ACTIONS = [
  "drain",
  "sweep",
  "transferAll",
  "sendAll",
  "approveUnlimited",
  "infiniteApproval",
] as const;

/**
 * Default suspicious patterns for crypto transactions
 */
export const DEFAULT_SUSPICIOUS_PATTERNS: SuspiciousPattern[] = [
  {
    name: "drain_operation",
    pattern: /drain|sweep|empty/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Potential drain operation detected",
  },
  {
    name: "unlimited_approval",
    pattern: /unlimited|infinite|max.*approv/i,
    riskLevel: RiskLevel.HIGH,
    message: "Unlimited approval request detected",
  },
  {
    name: "bulk_transfer",
    pattern: /(?:send|transfer).*(?:all|entire|whole)|(?:all|entire|whole).*(?:send|transfer)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Bulk transfer operation detected",
  },
  {
    name: "private_key_exposure",
    pattern: /private.*key|secret.*key|seed.*phrase|mnemonic/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Potential private key exposure in transaction data",
  },
  {
    name: "suspicious_urgency",
    pattern: /urgent|immediately|right.*now|asap/i,
    riskLevel: RiskLevel.MEDIUM,
    message: "Suspicious urgency language detected",
  },
];
