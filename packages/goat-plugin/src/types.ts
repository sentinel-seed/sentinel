/**
 * Type definitions for Sentinel GOAT plugin.
 */

export enum RiskLevel {
  LOW = "low",
  MEDIUM = "medium",
  HIGH = "high",
  CRITICAL = "critical",
}

export enum ComplianceFramework {
  OWASP_LLM = "owasp_llm",
  EU_AI_ACT = "eu_ai_act",
  CSA_AI = "csa_ai",
  NIST_RMF = "nist_rmf",
}

export interface SentinelPluginOptions {
  /**
   * Enable strict validation mode.
   * When true, applies more aggressive safety checks.
   */
  strictMode?: boolean;

  /**
   * Custom patterns for prompt injection detection.
   */
  customInjectionPatterns?: string[];

  /**
   * Custom list of malicious contract addresses.
   */
  maliciousContracts?: Record<string, string>;

  /**
   * Enable verbose logging.
   */
  verbose?: boolean;
}

export interface ValidationIssue {
  type: string;
  description: string;
  gate: "TRUTH" | "HARM" | "SCOPE" | "PURPOSE";
  severity?: RiskLevel;
}

export interface ValidationResult {
  is_safe: boolean;
  risk_level: RiskLevel;
  issues: ValidationIssue[];
  recommendations: string[];
  gates_passed: {
    TRUTH: boolean;
    HARM: boolean;
    SCOPE: boolean;
    PURPOSE: boolean;
  };
}

export interface TransactionValidation {
  is_safe: boolean;
  risk_level: RiskLevel;
  issues: ValidationIssue[];
  recommendations: string[];
  transaction_summary: {
    to: string;
    value: string;
    has_data: boolean;
    chain_id?: number;
  };
}

export interface SecretFinding {
  type: string;
  pattern: string;
  position: number;
  length: number;
}

export interface SecretScanResult {
  has_secrets: boolean;
  findings_count: number;
  findings: SecretFinding[];
  redacted_content: string | null;
  recommendation: string;
}

export interface ComplianceViolation {
  id: string;
  description: string;
  severity?: RiskLevel;
}

export interface FrameworkResult {
  compliant: boolean;
  violations?: ComplianceViolation[];
  indicators?: Record<string, boolean>;
  framework_version: string;
}

export interface ComplianceResult {
  overall_compliant: boolean;
  frameworks_checked: string[];
  results: Record<string, FrameworkResult>;
}

export interface RiskAnalysis {
  risk_score: number;
  risk_level: RiskLevel;
  action_type: string;
  risk_factors: string[];
  recommendation: string;
  requires_approval: boolean;
}

export interface OutputValidation {
  is_safe: boolean;
  issues: Array<{
    type: string;
    secret_type?: string;
    pii_type?: string;
  }>;
  original_length: number;
  sanitized_length: number;
  sanitized_output: string | null;
}
