/**
 * @goat-sdk/plugin-sentinel
 *
 * Sentinel safety validation plugin for GOAT SDK.
 * Provides THSP (Truth-Harm-Scope-Purpose) gates for AI agent safety.
 *
 * @example
 * ```typescript
 * import { getOnChainTools } from "@goat-sdk/adapter-vercel-ai";
 * import { sentinel } from "@goat-sdk/plugin-sentinel";
 *
 * const tools = getOnChainTools({
 *   wallet: viem(walletClient),
 *   plugins: [
 *     sentinel({ strictMode: true }),
 *   ],
 * });
 * ```
 */

export { SentinelPlugin, sentinel } from "./sentinel.plugin";
export { SentinelService } from "./sentinel.service";
export {
  type SentinelPluginOptions,
  type ValidationResult,
  type TransactionValidation,
  type SecretScanResult,
  type ComplianceResult,
  type RiskAnalysis,
  RiskLevel,
  ComplianceFramework,
} from "./types";
export {
  ValidatePromptParameters,
  ValidateTransactionParameters,
  ScanSecretsParameters,
  CheckComplianceParameters,
  AnalyzeRiskParameters,
} from "./parameters";
