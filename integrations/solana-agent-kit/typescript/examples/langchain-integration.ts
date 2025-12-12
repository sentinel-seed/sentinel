/**
 * LangChain Integration Example
 *
 * Shows how to use Sentinel with Solana Agent Kit in a LangChain agent.
 * The agent can use Sentinel actions for self-validation before transactions.
 */

import { SolanaAgentKit, createSolanaTools } from "solana-agent-kit";
import TokenPlugin from "@solana-agent-kit/plugin-token";
import SentinelPlugin from "@sentinelseed/solana-agent-kit";
import { ChatOpenAI } from "@langchain/openai";
import { createReactAgent, AgentExecutor } from "langchain/agents";
import { pull } from "langchain/hub";
import type { ChatPromptTemplate } from "@langchain/core/prompts";

async function main() {
  // Initialize agent with both Token and Sentinel plugins
  const agent = new SolanaAgentKit(
    process.env.SOLANA_PRIVATE_KEY!,
    process.env.SOLANA_RPC_URL || "https://api.mainnet-beta.solana.com",
    {
      OPENAI_API_KEY: process.env.OPENAI_API_KEY,
    }
  )
    .use(TokenPlugin)
    .use(
      SentinelPlugin({
        maxTransactionAmount: 50,
        strictMode: false, // Allow proceed with warnings
        requirePurposeFor: ["transfer", "swap"],
        onValidation: (result) => {
          // Log all validations for monitoring
          console.log(`[Sentinel] ${result.metadata.action}: ${result.riskLevel}`);
        },
      })
    );

  // Create tools from agent (includes both Token and Sentinel actions)
  const tools = createSolanaTools(agent);

  // Initialize LangChain components
  const llm = new ChatOpenAI({
    modelName: "gpt-4",
    temperature: 0,
  });

  const prompt = await pull<ChatPromptTemplate>("hwchase17/react");

  // Create the agent
  const reactAgent = await createReactAgent({
    llm,
    tools,
    prompt,
  });

  const executor = new AgentExecutor({
    agent: reactAgent,
    tools,
    verbose: true,
  });

  // Example: Agent validates before transferring
  console.log("\n=== Agent Task: Validated Transfer ===");

  const result = await executor.invoke({
    input: `
      I need to send 10 SOL to 9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM.

      IMPORTANT: Before executing any transfer:
      1. First use VALIDATE_TRANSACTION to check if it's safe
      2. Only proceed if the validation returns shouldProceed: true
      3. If blocked, explain why and do NOT execute the transfer

      The purpose is: Payment for freelance development work
    `,
  });

  console.log("\nAgent response:", result.output);

  // Example: Agent handles blocked transaction
  console.log("\n=== Agent Task: Handling Blocked Transaction ===");

  // First block an address
  await agent.methods.blockAddress(
    "BadActor111111111111111111111111111111111111"
  );

  const blockedResult = await executor.invoke({
    input: `
      Send 5 SOL to BadActor111111111111111111111111111111111111.

      IMPORTANT: Always validate transactions first.
      If the transaction is blocked, explain why and suggest alternatives.
    `,
  });

  console.log("\nAgent response:", blockedResult.output);
}

main().catch(console.error);
