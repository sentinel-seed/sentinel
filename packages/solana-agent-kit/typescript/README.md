# @sentinelseed/solana-agent-kit

[![npm version](https://img.shields.io/npm/v/@sentinelseed/solana-agent-kit)](https://www.npmjs.com/package/@sentinelseed/solana-agent-kit)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Sentinel Safety Plugin for Solana Agent Kit** — AI safety validation for Solana transactions using the THSP protocol.

Protect your AI agents from executing harmful, unauthorized, or suspicious transactions on Solana.

## Features

- **THSP Protocol**: Four-gate validation (Truth, Harm, Scope, Purpose)
- **Transaction Limits**: Configurable max amounts and confirmation thresholds
- **Address Blocklist**: Block known scam addresses
- **Purpose Verification**: Require explicit justification for sensitive operations
- **Pattern Detection**: Catch suspicious transaction patterns
- **LLM Actions**: Native integration with Solana Agent Kit action system
- **Statistics**: Track validation history and block rates

## Installation

```bash
npm install @sentinelseed/solana-agent-kit
```

**Peer Dependencies:**
```bash
npm install solana-agent-kit @solana/web3.js
```

## Quick Start

```typescript
import { SolanaAgentKit } from "solana-agent-kit";
import SentinelPlugin from "@sentinelseed/solana-agent-kit";

const agent = new SolanaAgentKit(privateKey, rpcUrl)
  .use(SentinelPlugin());

// Validate before any transaction
const result = await agent.methods.validateTransaction({
  action: "transfer",
  amount: 50,
  recipient: "9WzDXwBbmkg8ZTbNMqUxvQRAyrZzDsGYdLVL9zYtAWWM",
  purpose: "Payment for NFT purchase",
});

if (result.shouldProceed) {
  // Safe to execute
} else {
  console.log("Blocked:", result.concerns);
}
```

## Configuration

```typescript
import SentinelPlugin from "@sentinelseed/solana-agent-kit";

const agent = new SolanaAgentKit(privateKey, rpcUrl)
  .use(SentinelPlugin({
    // Maximum amount per transaction (default: 100)
    maxTransactionAmount: 100,

    // Require confirmation above this amount (default: 10)
    confirmationThreshold: 10,

    // Actions requiring explicit purpose (default shown)
    requirePurposeFor: ["transfer", "swap", "approve", "bridge", "withdraw", "stake"],

    // Block all transactions with any concerns (default: false)
    strictMode: false,

    // Known scam addresses to block
    blockedAddresses: [
      "ScamWa11etAddress111111111111111111111111111",
    ],

    // Only allow these programs (empty = all allowed)
    allowedPrograms: [],

    // Custom patterns to detect
    customPatterns: [
      {
        name: "high_slippage",
        pattern: /slippage.*(?:[5-9]\d|100)%/i,
        riskLevel: "high",
        message: "High slippage tolerance detected",
      },
    ],

    // Callback for monitoring
    onValidation: (result) => {
      console.log(`[Sentinel] ${result.metadata.action}: ${result.riskLevel}`);
    },
  }));
```

## THSP Protocol

Every transaction is validated against four gates:

| Gate | Question | Checks |
|------|----------|--------|
| **Truth** | Is the data accurate? | Address format, valid amounts, program IDs |
| **Harm** | Could this cause damage? | Blocked addresses, high-risk actions, program whitelist |
| **Scope** | Is this within limits? | Amount limits, rate limits |
| **Purpose** | Is there legitimate benefit? | Explicit justification for sensitive operations |

All gates must pass for a transaction to be approved.

## Available Actions

These actions are automatically available when using the plugin:

### VALIDATE_TRANSACTION

Full validation with detailed gate analysis.

```typescript
const result = await agent.methods.validateTransaction({
  action: "transfer",
  amount: 50,
  recipient: "...",
  purpose: "Payment for services",
});

// Returns:
{
  safe: boolean,
  shouldProceed: boolean,
  requiresConfirmation: boolean,
  riskLevel: "low" | "medium" | "high" | "critical",
  concerns: string[],
  recommendations: string[],
  gateResults: [
    { gate: "truth", passed: true },
    { gate: "harm", passed: true },
    { gate: "scope", passed: true },
    { gate: "purpose", passed: true },
  ],
}
```

### CHECK_SAFETY

Quick pass/fail check.

```typescript
const isSafe = await agent.methods.checkSafety("transfer", 10, recipient);
```

### GET_SAFETY_STATS

Validation statistics and configuration.

```typescript
const status = await agent.methods.getSafetyStatus();
console.log(status.stats.blockRate); // e.g., 0.05 (5%)
```

### BLOCK_ADDRESS / UNBLOCK_ADDRESS

Manage the address blocklist.

```typescript
await agent.methods.blockAddress("ScamAddress...");
await agent.methods.unblockAddress("VerifiedAddress...");
```

## LangChain Integration

The plugin works seamlessly with LangChain agents:

```typescript
import { SolanaAgentKit, createSolanaTools } from "solana-agent-kit";
import TokenPlugin from "@solana-agent-kit/plugin-token";
import SentinelPlugin from "@sentinelseed/solana-agent-kit";

const agent = new SolanaAgentKit(privateKey, rpcUrl)
  .use(TokenPlugin)
  .use(SentinelPlugin());

// Create tools including Sentinel actions
const tools = createSolanaTools(agent);

// Use with your LangChain agent
const executor = new AgentExecutor({ agent: reactAgent, tools });

await executor.invoke({
  input: `
    Before sending 10 SOL to [address]:
    1. Use VALIDATE_TRANSACTION to check safety
    2. Only proceed if shouldProceed is true
    Purpose: Payment for freelance work
  `,
});
```

## Risk Levels

| Level | Description | Action |
|-------|-------------|--------|
| `low` | No concerns detected | Proceed |
| `medium` | Minor concerns | Proceed with caution |
| `high` | Significant concerns | Review carefully |
| `critical` | Serious issues detected | Blocked |

## Default Suspicious Patterns

The plugin detects these patterns automatically:

- **Drain operations**: `drain`, `sweep`, `empty`
- **Unlimited approvals**: `unlimited`, `infinite approval`
- **Bulk transfers**: `transfer all`, `send entire`
- **Private key exposure**: `private key`, `seed phrase`, `mnemonic`
- **Suspicious urgency**: `urgent`, `immediately`, `asap`

## API Reference

### SentinelPlugin(config?)

Creates the plugin instance.

### SentinelValidator

Core validation engine, available for direct use:

```typescript
import { SentinelValidator } from "@sentinelseed/solana-agent-kit";

const validator = new SentinelValidator({
  maxTransactionAmount: 100,
});

const result = validator.validate({
  action: "transfer",
  amount: 50,
  recipient: "...",
});
```

### Types

```typescript
import type {
  SafetyValidationResult,
  ValidationInput,
  SentinelPluginConfig,
  RiskLevel,
  THSPGate,
} from "@sentinelseed/solana-agent-kit";
```

## Examples

See the [examples](./examples) directory:

- `basic-usage.ts` - Simple integration
- `langchain-integration.ts` - LangChain agent setup
- `defi-safety.ts` - DeFi-specific configuration

## Why Sentinel?

AI agents executing blockchain transactions face unique risks:

1. **Prompt Injection**: Malicious inputs can trick agents into harmful actions
2. **Memory Manipulation**: Attackers can inject false context
3. **Excessive Autonomy**: Agents may execute unintended transactions
4. **Missing Intent Verification**: No check for legitimate purpose

Sentinel addresses these by requiring every transaction to pass through the THSP validation protocol before execution.

## Links

- **Website**: [sentinelseed.dev](https://sentinelseed.dev)
- **Documentation**: [sentinelseed.dev/docs](https://sentinelseed.dev/docs)
- **GitHub**: [sentinel-seed/sentinel](https://github.com/sentinel-seed/sentinel/tree/main/integrations/solana-agent-kit/typescript)
- **npm**: [@sentinelseed/solana-agent-kit](https://www.npmjs.com/package/@sentinelseed/solana-agent-kit)

## License

MIT License - see [LICENSE](./LICENSE)

---

Built by [Sentinel Team](https://sentinelseed.dev)
