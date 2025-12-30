/**
 * Sentinel GOAT Plugin
 *
 * Provides THSP (Truth-Harm-Scope-Purpose) safety validation for AI agents.
 *
 * Based on official GOAT SDK plugin documentation:
 * https://github.com/goat-sdk/goat/blob/main/typescript/docs/3-create-a-plugin.md
 */

import { PluginBase, type Chain } from "@goat-sdk/core";
import type { WalletClientBase } from "@goat-sdk/core";
import { SentinelService } from "./sentinel.service";
import type { SentinelPluginOptions } from "./types";

/**
 * Sentinel plugin for GOAT SDK.
 *
 * Adds THSP safety validation tools to any GOAT-powered AI agent.
 *
 * @example
 * ```typescript
 * import { getOnChainTools } from "@goat-sdk/adapter-vercel-ai";
 * import { viem } from "@goat-sdk/wallet-viem";
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
export class SentinelPlugin extends PluginBase<WalletClientBase> {
  private options: SentinelPluginOptions;

  constructor(options: SentinelPluginOptions = {}) {
    // Initialize with plugin name and service instances
    super("sentinel", [new SentinelService(options)]);
    this.options = options;
  }

  /**
   * Sentinel supports all chains since it's a safety layer,
   * not a chain-specific integration.
   */
  supportsChain = (chain: Chain): boolean => true;
}

/**
 * Factory function to create a Sentinel plugin instance.
 *
 * @param options - Configuration options for the plugin
 * @returns A new SentinelPlugin instance
 *
 * @example
 * ```typescript
 * import { sentinel } from "@goat-sdk/plugin-sentinel";
 *
 * // Basic usage
 * const plugin = sentinel();
 *
 * // With strict mode
 * const strictPlugin = sentinel({ strictMode: true });
 *
 * // With custom malicious contracts
 * const customPlugin = sentinel({
 *   maliciousContracts: {
 *     "0x123...": "Known scam contract",
 *   },
 * });
 * ```
 */
export function sentinel(options: SentinelPluginOptions = {}): SentinelPlugin {
  return new SentinelPlugin(options);
}
