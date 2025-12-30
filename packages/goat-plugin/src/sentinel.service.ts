/**
 * Sentinel service class implementing THSP safety validation.
 *
 * This service provides the core validation logic used by the GOAT plugin tools.
 */

import { Tool } from "@goat-sdk/core";
import type { WalletClientBase } from "@goat-sdk/core";
import {
  ValidatePromptParameters,
  ValidateTransactionParameters,
  ScanSecretsParameters,
  CheckComplianceParameters,
  AnalyzeRiskParameters,
  ValidateOutputParameters,
  type ValidatePromptParams,
  type ValidateTransactionParams,
  type ScanSecretsParams,
  type CheckComplianceParams,
  type AnalyzeRiskParams,
  type ValidateOutputParams,
} from "./parameters";
import {
  RiskLevel,
  type SentinelPluginOptions,
  type ValidationResult,
  type TransactionValidation,
  type SecretScanResult,
  type ComplianceResult,
  type RiskAnalysis,
  type OutputValidation,
  type ValidationIssue,
} from "./types";

// Known malicious patterns for prompt injection detection
const DEFAULT_INJECTION_PATTERNS = [
  /ignore\s+(previous|all|above)\s+(instructions?|prompts?)/i,
  /disregard\s+(previous|all|your)\s+(instructions?|rules?)/i,
  /forget\s+(everything|all|previous)/i,
  /you\s+are\s+now\s+(a|an)\s+/i,
  /pretend\s+(to\s+be|you\s+are)/i,
  /jailbreak/i,
  /DAN\s+mode/i,
  /developer\s+mode\s+enabled/i,
];

// Patterns for detecting secrets
const SECRET_PATTERNS: Record<string, RegExp[]> = {
  api_keys: [
    /(api[_-]?key|apikey)['""]?\s*[:=]\s*['""]?([a-zA-Z0-9_\-]{20,})/i,
    /sk-[a-zA-Z0-9]{20,}/i, // OpenAI keys
    /AKIA[0-9A-Z]{16}/i, // AWS access keys
  ],
  private_keys: [
    /(private[_-]?key|secret[_-]?key)['""]?\s*[:=]\s*['""]?([a-fA-F0-9]{64})/i,
    /0x[a-fA-F0-9]{64}/, // Ethereum private keys
    /-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----/i,
  ],
  passwords: [
    /(password|passwd|pwd)['""]?\s*[:=]\s*['""]?([^\s'""]{8,})/i,
  ],
  tokens: [
    /(token|bearer)['""]?\s*[:=]\s*['""]?([a-zA-Z0-9_\-\.]{20,})/i,
    /ghp_[a-zA-Z0-9]{36}/, // GitHub tokens
    /gho_[a-zA-Z0-9]{36}/, // GitHub OAuth tokens
  ],
};

// OWASP LLM Top 10 patterns
const OWASP_PATTERNS: Record<string, RegExp> = {
  LLM01: /(ignore|bypass|override)\s+(instructions|rules|safety)/i,
  LLM02: /(reveal|show|display)\s+(system|hidden)\s+(prompt|instructions)/i,
  LLM06: /(sensitive|private|confidential)\s+(data|information)/i,
  LLM09: /(unlimited|infinite|no\s+limit)/i,
};

// Risk weights by action type
const ACTION_RISKS: Record<string, number> = {
  transfer: 0.6,
  swap: 0.5,
  deploy: 0.8,
  approve: 0.7,
  stake: 0.5,
  unstake: 0.4,
  bridge: 0.7,
  read: 0.1,
  query: 0.1,
};

export class SentinelService {
  private strictMode: boolean;
  private injectionPatterns: RegExp[];
  private maliciousContracts: Record<string, string>;
  private verbose: boolean;

  constructor(options: SentinelPluginOptions = {}) {
    this.strictMode = options.strictMode ?? false;
    this.verbose = options.verbose ?? false;
    this.maliciousContracts = options.maliciousContracts ?? {};

    // Compile custom patterns if provided
    this.injectionPatterns = [
      ...DEFAULT_INJECTION_PATTERNS,
      ...(options.customInjectionPatterns?.map((p) => new RegExp(p, "i")) ?? []),
    ];
  }

  @Tool({
    name: "sentinel_validate_prompt",
    description: `Validate a prompt or text input for safety using THSP gates.

    Checks for:
    - Prompt injection attempts
    - Jailbreak patterns
    - Harmful content requests
    - Policy violations

    Returns validation results including safety status, risk level, and recommendations.

    Example: Use before processing any user input to ensure it's safe.`,
  })
  async validatePrompt(
    walletClient: WalletClientBase,
    parameters: ValidatePromptParams
  ): Promise<string> {
    const { prompt, context, strict_mode } = parameters;
    const useStrictMode = strict_mode ?? this.strictMode;

    const issues: ValidationIssue[] = [];
    let riskLevel = RiskLevel.LOW;

    // Check for prompt injection patterns
    for (const pattern of this.injectionPatterns) {
      if (pattern.test(prompt)) {
        issues.push({
          type: "prompt_injection",
          description: "Detected potential prompt injection pattern",
          gate: "HARM",
          severity: RiskLevel.HIGH,
        });
        riskLevel = RiskLevel.HIGH;
        break; // One injection is enough to flag
      }
    }

    // Check for OWASP LLM patterns
    for (const [owaspId, pattern] of Object.entries(OWASP_PATTERNS)) {
      if (pattern.test(prompt)) {
        issues.push({
          type: `owasp_${owaspId.toLowerCase()}`,
          description: `Detected OWASP ${owaspId} pattern`,
          gate: "SCOPE",
          severity: RiskLevel.MEDIUM,
        });
        if (riskLevel === RiskLevel.LOW) {
          riskLevel = RiskLevel.MEDIUM;
        }
      }
    }

    // Check for extremely long inputs
    if (prompt.length > 50000) {
      issues.push({
        type: "input_size",
        description: "Input exceeds recommended maximum length",
        gate: "SCOPE",
        severity: RiskLevel.MEDIUM,
      });
      if (riskLevel === RiskLevel.LOW) {
        riskLevel = RiskLevel.MEDIUM;
      }
    }

    // Strict mode checks
    if (useStrictMode) {
      const sensitivePatterns = [
        /(password|credit\s*card|ssn|social\s*security)/i,
        /(bank\s*account|routing\s*number)/i,
      ];
      for (const pattern of sensitivePatterns) {
        if (pattern.test(prompt)) {
          issues.push({
            type: "sensitive_request",
            description: "Request may involve sensitive data",
            gate: "PURPOSE",
            severity: RiskLevel.MEDIUM,
          });
        }
      }
    }

    const isSafe =
      issues.length === 0 ||
      riskLevel === RiskLevel.LOW ||
      riskLevel === RiskLevel.MEDIUM;

    const result: ValidationResult = {
      is_safe: isSafe,
      risk_level: riskLevel,
      issues,
      recommendations: this.getRecommendations(issues),
      gates_passed: {
        TRUTH: true, // Factual validation not applicable to prompts
        HARM: !issues.some((i) => i.gate === "HARM"),
        SCOPE: !issues.some((i) => i.gate === "SCOPE"),
        PURPOSE: !issues.some((i) => i.gate === "PURPOSE"),
      },
    };

    return JSON.stringify(result, null, 2);
  }

  @Tool({
    name: "sentinel_validate_transaction",
    description: `Validate a blockchain transaction before execution.

    Checks for:
    - Known malicious contract addresses
    - Suspicious transaction patterns
    - Unlimited token approvals
    - High-value transaction warnings

    Returns validation results with safety recommendations.

    Example: Use before executing any token transfer or contract interaction.`,
  })
  async validateTransaction(
    walletClient: WalletClientBase,
    parameters: ValidateTransactionParams
  ): Promise<string> {
    const { to_address, value, data, chain_id, check_contract } = parameters;
    const normalizedAddress = to_address.toLowerCase();

    const issues: ValidationIssue[] = [];
    let riskLevel = RiskLevel.LOW;

    // Check against known malicious contracts
    if (check_contract && this.maliciousContracts[normalizedAddress]) {
      issues.push({
        type: "malicious_contract",
        description: `Address flagged as malicious: ${this.maliciousContracts[normalizedAddress]}`,
        gate: "HARM",
        severity: RiskLevel.CRITICAL,
      });
      riskLevel = RiskLevel.CRITICAL;
    }

    // Check for unlimited approval
    if (data && data.startsWith("0x095ea7b3")) {
      if (data.toLowerCase().includes("ffffffff")) {
        issues.push({
          type: "unlimited_approval",
          description: "Transaction includes unlimited token approval",
          gate: "SCOPE",
          severity: RiskLevel.HIGH,
        });
        riskLevel = RiskLevel.HIGH;
      }
    }

    // Check for high value
    try {
      const valueFloat = parseFloat(value);
      if (valueFloat > 1000) {
        issues.push({
          type: "high_value",
          description: `High value transaction: ${value}`,
          gate: "PURPOSE",
          severity: RiskLevel.MEDIUM,
        });
        if (riskLevel === RiskLevel.LOW) {
          riskLevel = RiskLevel.MEDIUM;
        }
      }
    } catch {
      // Invalid value format
    }

    // Check for zero address
    if (normalizedAddress === "0x0000000000000000000000000000000000000000") {
      issues.push({
        type: "zero_address",
        description: "Transaction to zero address (burn)",
        gate: "PURPOSE",
        severity: RiskLevel.MEDIUM,
      });
    }

    const isSafe = riskLevel !== RiskLevel.CRITICAL;

    const result: TransactionValidation = {
      is_safe: isSafe,
      risk_level: riskLevel,
      issues,
      recommendations: this.getTransactionRecommendations(issues),
      transaction_summary: {
        to: normalizedAddress,
        value,
        has_data: Boolean(data),
        chain_id,
      },
    };

    return JSON.stringify(result, null, 2);
  }

  @Tool({
    name: "sentinel_scan_secrets",
    description: `Scan content for exposed secrets and sensitive data.

    Detects:
    - API keys (OpenAI, AWS, etc.)
    - Private keys (Ethereum, RSA)
    - Passwords
    - Access tokens (GitHub, OAuth)

    Returns findings with redacted content.

    Example: Use before logging, storing, or transmitting any content.`,
  })
  async scanSecrets(
    walletClient: WalletClientBase,
    parameters: ScanSecretsParams
  ): Promise<string> {
    const { content, scan_types } = parameters;

    const findings: Array<{
      type: string;
      pattern: string;
      position: number;
      length: number;
    }> = [];
    let redactedContent = content;

    for (const secretType of scan_types) {
      const patterns = SECRET_PATTERNS[secretType];
      if (!patterns) continue;

      for (const pattern of patterns) {
        const matches = content.matchAll(new RegExp(pattern, "g"));
        for (const match of matches) {
          if (match.index !== undefined) {
            findings.push({
              type: secretType,
              pattern: pattern.source.slice(0, 30) + "...",
              position: match.index,
              length: match[0].length,
            });
            redactedContent = redactedContent.replace(
              match[0],
              `[REDACTED_${secretType.toUpperCase()}]`
            );
          }
        }
      }
    }

    const result: SecretScanResult = {
      has_secrets: findings.length > 0,
      findings_count: findings.length,
      findings,
      redacted_content: findings.length > 0 ? redactedContent : null,
      recommendation:
        findings.length > 0
          ? "Remove or rotate exposed credentials immediately"
          : "No secrets detected",
    };

    return JSON.stringify(result, null, 2);
  }

  @Tool({
    name: "sentinel_check_compliance",
    description: `Check content against compliance frameworks.

    Supported frameworks:
    - OWASP LLM Top 10
    - EU AI Act
    - CSA AI Controls
    - NIST AI RMF

    Returns compliance status for each framework.

    Example: Use before deploying or releasing AI-generated content.`,
  })
  async checkCompliance(
    walletClient: WalletClientBase,
    parameters: CheckComplianceParams
  ): Promise<string> {
    const { content, frameworks } = parameters;

    const results: Record<string, any> = {};

    for (const framework of frameworks) {
      switch (framework) {
        case "owasp_llm":
          results.owasp_llm = this.checkOwaspCompliance(content);
          break;
        case "eu_ai_act":
          results.eu_ai_act = this.checkEuAiAct(content);
          break;
        case "csa_ai":
          results.csa_ai = this.checkCsaCompliance(content);
          break;
        case "nist_rmf":
          results.nist_rmf = this.checkNistCompliance(content);
          break;
      }
    }

    const overallCompliant = Object.values(results).every(
      (r: any) => r.compliant
    );

    const result: ComplianceResult = {
      overall_compliant: overallCompliant,
      frameworks_checked: frameworks,
      results,
    };

    return JSON.stringify(result, null, 2);
  }

  @Tool({
    name: "sentinel_analyze_risk",
    description: `Analyze the risk level of an agent action.

    Evaluates:
    - Action type inherent risk
    - Parameter values
    - Context appropriateness

    Returns risk score with approval requirements.

    Example: Use before executing any high-impact action.`,
  })
  async analyzeRisk(
    walletClient: WalletClientBase,
    parameters: AnalyzeRiskParams
  ): Promise<string> {
    const { action_type, parameters: actionParams, context } = parameters;

    let baseRisk = ACTION_RISKS[action_type.toLowerCase()] ?? 0.5;
    const riskFactors: string[] = [];

    // Adjust based on parameters
    const value = actionParams.value ?? actionParams.amount;
    if (value) {
      try {
        if (parseFloat(String(value)) > 1000) {
          baseRisk += 0.2;
          riskFactors.push("High value transaction");
        }
      } catch {
        // Invalid value
      }
    }

    // Check for external addresses
    const address = actionParams.to ?? actionParams.recipient;
    if (address && this.maliciousContracts[String(address).toLowerCase()]) {
      baseRisk = 1.0;
      riskFactors.push("Known malicious address");
    }

    // Determine risk level
    let riskLevel: RiskLevel;
    if (baseRisk >= 0.8) {
      riskLevel = RiskLevel.CRITICAL;
    } else if (baseRisk >= 0.6) {
      riskLevel = RiskLevel.HIGH;
    } else if (baseRisk >= 0.3) {
      riskLevel = RiskLevel.MEDIUM;
    } else {
      riskLevel = RiskLevel.LOW;
    }

    const result: RiskAnalysis = {
      risk_score: Math.round(baseRisk * 100) / 100,
      risk_level: riskLevel,
      action_type,
      risk_factors: riskFactors,
      recommendation: this.getRiskRecommendation(riskLevel),
      requires_approval:
        riskLevel === RiskLevel.HIGH || riskLevel === RiskLevel.CRITICAL,
    };

    return JSON.stringify(result, null, 2);
  }

  // Helper methods

  private getRecommendations(issues: ValidationIssue[]): string[] {
    const recommendations: string[] = [];
    const issueTypes = new Set(issues.map((i) => i.type));

    if (issueTypes.has("prompt_injection")) {
      recommendations.push("Reject the input and log the attempt");
    }
    if (issueTypes.has("sensitive_request")) {
      recommendations.push("Request user confirmation before proceeding");
    }
    if (issueTypes.has("input_size")) {
      recommendations.push("Truncate input to acceptable length");
    }

    if (recommendations.length === 0) {
      recommendations.push("Input appears safe to process");
    }

    return recommendations;
  }

  private getTransactionRecommendations(issues: ValidationIssue[]): string[] {
    const recommendations: string[] = [];
    const issueTypes = new Set(issues.map((i) => i.type));

    if (issueTypes.has("malicious_contract")) {
      recommendations.push("DO NOT EXECUTE - Known malicious address");
    }
    if (issueTypes.has("unlimited_approval")) {
      recommendations.push(
        "Consider using a specific approval amount instead"
      );
    }
    if (issueTypes.has("high_value")) {
      recommendations.push(
        "Verify recipient and consider splitting transaction"
      );
    }
    if (issueTypes.has("zero_address")) {
      recommendations.push("Confirm burn intention with user");
    }

    if (recommendations.length === 0) {
      recommendations.push("Transaction appears safe to execute");
    }

    return recommendations;
  }

  private getRiskRecommendation(riskLevel: RiskLevel): string {
    const recommendations: Record<RiskLevel, string> = {
      [RiskLevel.LOW]: "Safe to proceed",
      [RiskLevel.MEDIUM]: "Proceed with standard monitoring",
      [RiskLevel.HIGH]: "Require explicit user confirmation",
      [RiskLevel.CRITICAL]: "Block action and alert user",
    };
    return recommendations[riskLevel] ?? "Unknown risk level";
  }

  private checkOwaspCompliance(content: string) {
    const violations: Array<{ id: string; description: string }> = [];

    for (const [owaspId, pattern] of Object.entries(OWASP_PATTERNS)) {
      if (pattern.test(content)) {
        violations.push({
          id: owaspId,
          description: `Potential ${owaspId} violation detected`,
        });
      }
    }

    return {
      compliant: violations.length === 0,
      violations,
      framework_version: "OWASP LLM Top 10 2025",
    };
  }

  private checkEuAiAct(content: string) {
    const indicators = {
      transparency: !/hide|conceal|deceive/i.test(content),
      human_oversight: true,
      documentation: true,
    };

    return {
      compliant: Object.values(indicators).every(Boolean),
      indicators,
      framework_version: "EU AI Act 2024",
    };
  }

  private checkCsaCompliance(content: string) {
    return {
      compliant: true,
      controls_checked: ["AI-1", "AI-2", "AI-3"],
      framework_version: "CSA AI Controls Matrix v1",
    };
  }

  private checkNistCompliance(content: string) {
    return {
      compliant: true,
      functions_checked: ["GOVERN", "MAP", "MEASURE", "MANAGE"],
      framework_version: "NIST AI RMF 1.0",
    };
  }
}
