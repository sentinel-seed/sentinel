/**
 * DeFi Safety Example
 *
 * Demonstrates Sentinel protecting DeFi operations like swaps,
 * staking, and liquidity provision.
 */

import { SolanaAgentKit } from "solana-agent-kit";
import TokenPlugin from "@solana-agent-kit/plugin-token";
import DefiPlugin from "@solana-agent-kit/plugin-defi";
import SentinelPlugin from "@sentinelseed/solana-agent-kit";

async function main() {
  // Initialize with all plugins
  const agent = new SolanaAgentKit(
    process.env.SOLANA_PRIVATE_KEY!,
    process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com"
  )
    .use(TokenPlugin)
    .use(DefiPlugin)
    .use(
      SentinelPlugin({
        maxTransactionAmount: 100,
        confirmationThreshold: 25,
        // DeFi-specific actions that need purpose
        requirePurposeFor: [
          "swap",
          "stake",
          "unstake",
          "addLiquidity",
          "removeLiquidity",
          "borrow",
          "lend",
          "bridge",
        ],
        // Custom patterns for DeFi risks
        customPatterns: [
          {
            name: "high_slippage",
            pattern: /slippage.*(?:[5-9]\d|100)%/i,
            riskLevel: "high",
            message: "High slippage tolerance detected",
          },
          {
            name: "unknown_token",
            pattern: /unknown.*token|unverified/i,
            riskLevel: "medium",
            message: "Trading unknown or unverified token",
          },
          {
            name: "max_leverage",
            pattern: /leverage.*(?:[5-9]|10)x|10x.*leverage/i,
            riskLevel: "high",
            message: "High leverage position requested",
          },
        ],
      })
    );

  // Example 1: Validate a swap operation
  console.log("\n=== Example 1: Validating Swap ===");

  const swapResult = await agent.methods.validateTransaction({
    action: "swap",
    amount: 10,
    purpose: "Converting SOL to USDC for stablecoin savings",
    metadata: {
      fromToken: "SOL",
      toToken: "USDC",
      slippage: "1%",
    },
  });

  console.log("Swap validation:", {
    safe: swapResult.safe,
    shouldProceed: swapResult.shouldProceed,
    riskLevel: swapResult.riskLevel,
    gateResults: swapResult.gateResults.map((g) => `${g.gate}: ${g.passed}`),
  });

  // Example 2: Validate staking operation
  console.log("\n=== Example 2: Validating Stake ===");

  const stakeResult = await agent.methods.validateTransaction({
    action: "stake",
    amount: 50,
    purpose: "Long-term SOL staking with Marinade for yield",
    metadata: {
      protocol: "Marinade",
      expectedAPY: "7.5%",
    },
  });

  console.log("Stake validation:", {
    safe: stakeResult.safe,
    shouldProceed: stakeResult.shouldProceed,
    requiresConfirmation: stakeResult.requiresConfirmation,
  });

  // Example 3: Catch high-risk swap
  console.log("\n=== Example 3: High-Risk Swap Detection ===");

  const riskySwapResult = await agent.methods.validateTransaction({
    action: "swap",
    amount: 100,
    purpose: "Quick trade",
    metadata: {
      fromToken: "SOL",
      toToken: "UNKNOWN_MEMECOIN",
      slippage: "50%", // Will trigger custom pattern
    },
    memo: "Trading unknown token with 50% slippage",
  });

  console.log("Risky swap result:", {
    safe: riskySwapResult.safe,
    shouldProceed: riskySwapResult.shouldProceed,
    concerns: riskySwapResult.concerns,
    recommendations: riskySwapResult.recommendations,
  });

  // Example 4: Validate bridge operation
  console.log("\n=== Example 4: Cross-chain Bridge ===");

  const bridgeResult = await agent.methods.validateTransaction({
    action: "bridge",
    amount: 25,
    purpose: "Moving funds to Ethereum for NFT purchase on OpenSea",
    metadata: {
      fromChain: "Solana",
      toChain: "Ethereum",
      bridge: "Wormhole",
    },
  });

  console.log("Bridge validation:", {
    safe: bridgeResult.safe,
    shouldProceed: bridgeResult.shouldProceed,
    concerns: bridgeResult.concerns,
  });

  // Example 5: Missing purpose rejection
  console.log("\n=== Example 5: Missing Purpose Rejection ===");

  const noPurposeResult = await agent.methods.validateTransaction({
    action: "swap",
    amount: 50,
    // No purpose provided
  });

  console.log("No purpose result:", {
    safe: noPurposeResult.safe,
    shouldProceed: noPurposeResult.shouldProceed,
    concerns: noPurposeResult.concerns,
    recommendations: noPurposeResult.recommendations,
  });

  // Final stats
  console.log("\n=== Final Safety Statistics ===");
  const stats = await agent.methods.getSafetyStatus();
  console.log("Total validations:", stats.stats.totalValidations);
  console.log("Block rate:", `${(stats.stats.blockRate * 100).toFixed(1)}%`);
  console.log("By action:", stats.stats.byAction);
}

main().catch(console.error);
