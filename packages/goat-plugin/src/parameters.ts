/**
 * Zod parameter schemas for Sentinel GOAT plugin tools.
 *
 * Following GOAT SDK conventions for tool parameter definitions.
 */

import { z } from "zod";

/**
 * Parameters for validating prompts through THSP gates.
 */
export const ValidatePromptParameters = z.object({
  prompt: z.string().describe("The prompt or text to validate for safety"),
  context: z
    .string()
    .optional()
    .describe("Optional context about the prompt's intended use"),
  strict_mode: z
    .boolean()
    .default(false)
    .describe("If true, applies stricter validation rules"),
});

export type ValidatePromptParams = z.infer<typeof ValidatePromptParameters>;

/**
 * Parameters for validating blockchain transactions.
 */
export const ValidateTransactionParameters = z.object({
  to_address: z
    .string()
    .describe("The destination address for the transaction"),
  value: z.string().describe("The value/amount of the transaction"),
  data: z
    .string()
    .optional()
    .describe("Optional transaction data (for contract calls)"),
  chain_id: z.number().optional().describe("The chain ID for the transaction"),
  check_contract: z
    .boolean()
    .default(true)
    .describe("Whether to check if destination is a known malicious contract"),
});

export type ValidateTransactionParams = z.infer<
  typeof ValidateTransactionParameters
>;

/**
 * Parameters for scanning content for secrets.
 */
export const ScanSecretsParameters = z.object({
  content: z
    .string()
    .describe("The content to scan for secrets (code, logs, etc.)"),
  scan_types: z
    .array(z.enum(["api_keys", "private_keys", "passwords", "tokens"]))
    .default(["api_keys", "private_keys", "passwords", "tokens"])
    .describe("Types of secrets to scan for"),
});

export type ScanSecretsParams = z.infer<typeof ScanSecretsParameters>;

/**
 * Parameters for checking compliance.
 */
export const CheckComplianceParameters = z.object({
  content: z.string().describe("The content to check for compliance"),
  frameworks: z
    .array(z.enum(["owasp_llm", "eu_ai_act", "csa_ai", "nist_rmf"]))
    .default(["owasp_llm"])
    .describe("Compliance frameworks to check against"),
});

export type CheckComplianceParams = z.infer<typeof CheckComplianceParameters>;

/**
 * Parameters for analyzing action risk.
 */
export const AnalyzeRiskParameters = z.object({
  action_type: z
    .string()
    .describe(
      "The type of action being performed (e.g., 'transfer', 'swap', 'deploy')"
    ),
  parameters: z.record(z.any()).describe("The parameters of the action"),
  context: z
    .string()
    .optional()
    .describe("Additional context about the action"),
});

export type AnalyzeRiskParams = z.infer<typeof AnalyzeRiskParameters>;

/**
 * Parameters for validating outputs.
 */
export const ValidateOutputParameters = z.object({
  output: z.string().describe("The output content to validate"),
  output_type: z
    .enum(["text", "code", "json", "markdown"])
    .default("text")
    .describe("The type of output"),
  filter_pii: z
    .boolean()
    .default(true)
    .describe("Whether to filter personally identifiable information"),
});

export type ValidateOutputParams = z.infer<typeof ValidateOutputParameters>;
