# @goat-sdk/plugin-sentinel

Sentinel safety validation plugin for [GOAT SDK](https://github.com/goat-sdk/goat). Provides THSP (Truth-Harm-Scope-Purpose) gates for AI agent safety.

## Installation

```bash
npm install @goat-sdk/plugin-sentinel
# or
pnpm add @goat-sdk/plugin-sentinel
# or
yarn add @goat-sdk/plugin-sentinel
```

## Quick Start

```typescript
import { getOnChainTools } from "@goat-sdk/adapter-vercel-ai";
import { viem } from "@goat-sdk/wallet-viem";
import { sentinel } from "@goat-sdk/plugin-sentinel";

const tools = getOnChainTools({
  wallet: viem(walletClient),
  plugins: [
    sentinel({ strictMode: true }),
    // ... other plugins
  ],
});
```

## Available Tools

### sentinel_validate_prompt

Validate a prompt or text input for safety using THSP gates.

**Checks for:**
- Prompt injection attempts
- Jailbreak patterns
- Harmful content requests
- Policy violations

```typescript
// Example usage in agent
const result = await tools.sentinel_validate_prompt({
  prompt: "User input here",
  strict_mode: true,
});
```

### sentinel_validate_transaction

Validate a blockchain transaction before execution.

**Checks for:**
- Known malicious contract addresses
- Unlimited token approvals
- High-value transaction warnings
- Zero address burns

```typescript
const result = await tools.sentinel_validate_transaction({
  to_address: "0x...",
  value: "1000000000000000000",
  data: "0x...",
  check_contract: true,
});
```

### sentinel_scan_secrets

Scan content for exposed secrets and sensitive data.

**Detects:**
- API keys (OpenAI, AWS, etc.)
- Private keys (Ethereum, RSA)
- Passwords
- Access tokens (GitHub, OAuth)

```typescript
const result = await tools.sentinel_scan_secrets({
  content: "Some code or text here",
  scan_types: ["api_keys", "private_keys"],
});
```

### sentinel_check_compliance

Check content against compliance frameworks.

**Supported frameworks:**
- OWASP LLM Top 10
- EU AI Act
- CSA AI Controls
- NIST AI RMF

```typescript
const result = await tools.sentinel_check_compliance({
  content: "AI-generated content",
  frameworks: ["owasp_llm", "eu_ai_act"],
});
```

### sentinel_analyze_risk

Analyze the risk level of an agent action.

```typescript
const result = await tools.sentinel_analyze_risk({
  action_type: "transfer",
  parameters: { to: "0x...", value: "1000" },
});
```

## Configuration

```typescript
interface SentinelPluginOptions {
  // Enable strict validation mode
  strictMode?: boolean;

  // Custom prompt injection patterns
  customInjectionPatterns?: string[];

  // Custom malicious contract addresses
  maliciousContracts?: Record<string, string>;

  // Enable verbose logging
  verbose?: boolean;
}
```

## THSP Gate Framework

Sentinel uses the THSP (Truth-Harm-Scope-Purpose) gate framework:

| Gate | Function | Question |
|------|----------|----------|
| **TRUTH** | Verify factual correspondence | "Is this factually correct?" |
| **HARM** | Assess harm potential | "Does this cause harm?" |
| **SCOPE** | Check appropriate boundaries | "Is this within limits?" |
| **PURPOSE** | Require teleological justification | "Does this serve a legitimate purpose?" |

All four gates must pass for an action to be considered safe.

## Integration Examples

### With Vercel AI SDK

```typescript
import { generateText } from "ai";
import { getOnChainTools } from "@goat-sdk/adapter-vercel-ai";
import { sentinel } from "@goat-sdk/plugin-sentinel";

const tools = getOnChainTools({
  wallet: viem(walletClient),
  plugins: [sentinel()],
});

const result = await generateText({
  model: openai("gpt-4"),
  tools,
  prompt: "Validate this transaction...",
});
```

### With LangChain

```typescript
import { getOnChainTools } from "@goat-sdk/adapter-langchain";
import { sentinel } from "@goat-sdk/plugin-sentinel";

const tools = await getOnChainTools({
  wallet: viem(walletClient),
  plugins: [sentinel()],
});

// Use tools with LangChain agent
```

### With Eliza

```typescript
import { getOnChainTools } from "@goat-sdk/adapter-eliza";
import { sentinel } from "@goat-sdk/plugin-sentinel";

const tools = await getOnChainTools({
  wallet: viem(walletClient),
  plugins: [sentinel({ strictMode: true })],
});
```

## License

MIT

## Links

- [Sentinel Documentation](https://sentinelseed.dev)
- [GOAT SDK](https://github.com/goat-sdk/goat)
- [GitHub Repository](https://github.com/sentinel-seed/sentinel)
