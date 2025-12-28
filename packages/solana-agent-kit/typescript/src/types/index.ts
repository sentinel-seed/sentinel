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
 *
 * Patterns use word boundaries (\b) to avoid false positives on partial matches.
 * Avoid using .* which can cause catastrophic backtracking (ReDoS).
 *
 * Includes THSP jailbreak detection patterns to protect against prompt injection
 * attacks that could manipulate AI agents into unauthorized transactions.
 */
export const DEFAULT_SUSPICIOUS_PATTERNS: SuspiciousPattern[] = [
  // === CRYPTO-SPECIFIC PATTERNS ===
  {
    name: "drain_operation",
    // Use word boundaries to avoid matching "drainage" or "sweeper"
    pattern: /\b(?:drain|sweep|empty)\b/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Potential drain operation detected",
  },
  {
    name: "unlimited_approval",
    // Match specific phrases for unlimited approvals
    pattern: /\b(?:unlimited|infinite)\s+(?:approv|access|permission)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Unlimited approval request detected",
  },
  {
    name: "bulk_transfer",
    // Match "transfer all", "send all", "send entire", etc.
    pattern: /\b(?:send|transfer)\s+(?:all|entire|whole)\b/i,
    riskLevel: RiskLevel.HIGH,
    message: "Bulk transfer operation detected",
  },
  {
    name: "private_key_exposure",
    // Match phrases about private keys or seed phrases
    pattern: /\b(?:private\s+key|secret\s+key|seed\s+phrase|mnemonic)\b/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Potential private key exposure in transaction data",
  },
  {
    name: "suspicious_urgency",
    // Match urgency language that may indicate social engineering
    pattern: /\b(?:urgent|immediately|right\s+now|asap)\b/i,
    riskLevel: RiskLevel.MEDIUM,
    message: "Suspicious urgency language detected",
  },

  // === JAILBREAK/PROMPT INJECTION PATTERNS ===

  // Instruction override patterns (violating operational limits)
  {
    name: "instruction_override_ignore",
    pattern: /ignore\s+(?:all\s+)?(?:previous\s+)?(?:instructions?|rules?|guidelines?|safety)/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Instruction override: ignore instructions detected",
  },
  {
    name: "instruction_override_disregard",
    pattern: /disregard\s+(?:all\s+)?(?:your\s+)?(?:instructions?|rules?|guidelines?|programming|safety)/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Instruction override: disregard instructions detected",
  },
  {
    name: "instruction_override_bypass",
    pattern: /bypass\s+(?:your\s+)?(?:restrictions?|filters?|safety|guidelines?|rules?)/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Instruction override: bypass restrictions detected",
  },
  {
    name: "instruction_override_forget",
    pattern: /forget\s+(?:all\s+)?(?:your\s+)?(?:instructions?|rules?|training|programming)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Instruction override: forget instructions detected",
  },
  {
    name: "instruction_override_override",
    pattern: /override\s+(?:your\s+)?(?:safety|guidelines?|instructions?|programming)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Instruction override: override safety detected",
  },

  // Role manipulation patterns (identity deception)
  {
    name: "role_manipulation_persona",
    pattern: /you\s+are\s+now\s+(?:DAN|jailbroken|unrestricted|unfiltered|evil|unlimited)/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Role manipulation: persona switch detected",
  },
  {
    name: "role_manipulation_mode",
    pattern: /you\s+are\s+now\s+in\s+(?:developer|debug|admin|god|unrestricted|jailbreak)\s+mode/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Role manipulation: mode switch detected",
  },
  {
    name: "role_manipulation_enable",
    pattern: /(?:enter|switch\s+to|enable|activate)\s+(?:developer|debug|admin|god|unrestricted|jailbreak)\s+mode/i,
    riskLevel: RiskLevel.HIGH,
    message: "Role manipulation: enable mode detected",
  },
  {
    name: "role_manipulation_no_restrictions",
    pattern: /pretend\s+(?:that\s+)?you\s+(?:have\s+no|don't\s+have(?:\s+any)?)\s+(?:restrictions?|rules?|limits?|guidelines?|filters?)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Role manipulation: no restrictions persona detected",
  },

  // Prompt extraction patterns (accessing restricted information)
  {
    name: "prompt_extraction_reveal",
    pattern: /(?:reveal|show|display|print|output|give\s+me)\s+your\s+(?:system\s+)?(?:prompt|instructions?|message|configuration)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Prompt extraction: reveal system prompt detected",
  },
  {
    name: "prompt_extraction_what",
    pattern: /what\s+(?:are|is)\s+your\s+(?:system\s+)?(?:instructions?|prompt|original\s+prompt)/i,
    riskLevel: RiskLevel.MEDIUM,
    message: "Prompt extraction: asking for instructions detected",
  },

  // Filter bypass patterns (disabling safety features)
  {
    name: "filter_bypass_disable",
    pattern: /(?:disable|turn\s+off|deactivate|remove|bypass)\s+(?:your\s+)?(?:safety|content\s+)?(?:filters?|features?|guardrails?|restrictions?|mode)/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Filter bypass: disable safety features detected",
  },
  {
    name: "filter_bypass_unfiltered",
    pattern: /(?:unfiltered|uncensored|unrestricted)\s+mode/i,
    riskLevel: RiskLevel.HIGH,
    message: "Filter bypass: unfiltered mode detected",
  },
  {
    name: "filter_bypass_without",
    pattern: /without\s+(?:any\s+)?(?:restrictions?|safety|filters?|guardrails?)/i,
    riskLevel: RiskLevel.HIGH,
    message: "Filter bypass: without restrictions detected",
  },

  // Explicit jailbreak patterns
  {
    name: "jailbreak_explicit",
    pattern: /\bjailbreak\b/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Jailbreak: explicit mention detected",
  },
  {
    name: "jailbreak_dan_mode",
    pattern: /\bdan\s+mode\b/i,
    riskLevel: RiskLevel.CRITICAL,
    message: "Jailbreak: DAN mode detected",
  },
];
