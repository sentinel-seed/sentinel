/**
 * Basic Usage Example
 *
 * Demonstrates how to integrate Sentinel with Solana Agent Kit
 * for transaction safety validation.
 */

import { SolanaAgentKit } from "solana-agent-kit";
import SentinelPlugin from "@sentinelseed/solana-agent-kit";

async function main() {
  // Initialize Solana Agent Kit with Sentinel plugin
  const agent = new SolanaAgentKit(
    process.env.SOLANA_PRIVATE_KEY!,
    process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com"
  ).use(
    SentinelPlugin({
      maxTransactionAmount: 100, // Max 100 SOL per transaction
      confirmationThreshold: 10, // Require confirmation above 10 SOL
      requirePurposeFor: ["transfer", "swap", "stake"],
    })
  );

  // Example 1: Validate a transfer before execution
  console.log("\n=== Example 1: Validating a Transfer ===");

  const transferResult = await agent.methods.validateTransaction({
    action: "transfer",
    amount: 50,
    recipient: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
    purpose: "Payment for NFT purchase from verified seller",
  });

  console.log("Validation result:", {
    safe: transferResult.safe,
    shouldProceed: transferResult.shouldProceed,
    riskLevel: transferResult.riskLevel,
    concerns: transferResult.concerns,
  });

  if (transferResult.shouldProceed) {
    console.log("✅ Transaction is safe to execute");
    // Execute your transfer here
    // await agent.transfer(recipient, amount);
  } else {
    console.log("❌ Transaction blocked:", transferResult.concerns);
  }

  // Example 2: Quick safety check
  console.log("\n=== Example 2: Quick Safety Check ===");

  // Note: checkSafety accepts purpose as 4th parameter for actions that require it
  const isSafe = await agent.methods.checkSafety(
    "swap",
    25,
    undefined,
    "Quick swap for portfolio rebalancing purposes"
  );
  console.log("Is swap safe?", isSafe);

  // Example 3: Block a suspicious address
  console.log("\n=== Example 3: Block Suspicious Address ===");

  // Using a valid Solana address for demonstration
  // In production, this would be a known scam address
  const suspiciousAddress = "DezXAZ8z7PnrnRJjz3wXBoRgixCa6xjnB7YaB1pPB263";

  await agent.methods.blockAddress(suspiciousAddress);
  console.log("Address blocked successfully");

  // Now try to validate a transfer to the blocked address
  const blockedResult = await agent.methods.validateTransaction({
    action: "transfer",
    amount: 10,
    recipient: suspiciousAddress,
    purpose: "Testing transfer to blocked address for validation",
  });

  console.log("Transfer to blocked address:", {
    shouldProceed: blockedResult.shouldProceed,
    concerns: blockedResult.concerns,
  });

  // Example 4: Get safety statistics
  console.log("\n=== Example 4: Safety Statistics ===");

  const stats = await agent.methods.getSafetyStatus();
  console.log("Safety stats:", stats.stats);
  console.log("Current config:", stats.config);
}

main().catch(console.error);
