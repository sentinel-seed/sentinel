# @sentinelseed/elizaos-plugin

> AI Safety Plugin for ElizaOS - THSP Protocol Validation for Autonomous Agents

[![npm version](https://badge.fury.io/js/@sentinelseed%2Felizaos-plugin.svg)](https://www.npmjs.com/package/@sentinelseed/elizaos-plugin)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Official Sentinel safety plugin for [ElizaOS](https://elizaos.ai) autonomous agents. Implements the THSP (Truth, Harm, Scope, Purpose) protocol to validate agent actions and outputs.

## Features

- **THSP Protocol**: Four-gate validation (Truth, Harm, Scope, Purpose)
- **Pre-action Validation**: Validates incoming messages before processing
- **Post-action Review**: Reviews agent outputs before delivery
- **Seed Injection**: Automatically injects alignment seed into agent character
- **Configurable**: Block or log unsafe content
- **History Tracking**: Full validation history and statistics
- **Custom Patterns**: Add domain-specific safety patterns

## Installation

```bash
npm install @sentinelseed/elizaos-plugin
# or
pnpm add @sentinelseed/elizaos-plugin
```

## Quick Start

```typescript
import { AgentRuntime } from '@elizaos/core';
import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';

const runtime = new AgentRuntime({
  character: {
    name: 'SafeAgent',
    system: 'You are a helpful assistant.',
  },
  plugins: [
    sentinelPlugin({
      blockUnsafe: true,
      logChecks: true,
    })
  ]
});
```

## Configuration

```typescript
interface SentinelPluginConfig {
  // Seed version: 'v1' or 'v2'. Default: 'v2'
  seedVersion?: 'v1' | 'v2';

  // Seed variant: 'minimal', 'standard', or 'full'. Default: 'standard'
  seedVariant?: 'minimal' | 'standard' | 'full';

  // Block unsafe actions or just log. Default: true
  blockUnsafe?: boolean;

  // Log all safety checks. Default: false
  logChecks?: boolean;

  // Custom patterns to detect
  customPatterns?: Array<{
    name: string;
    pattern: RegExp;
    gate: 'truth' | 'harm' | 'scope' | 'purpose';
  }>;

  // Actions to skip validation
  skipActions?: string[];
}
```

## THSP Protocol

The plugin validates all content through four gates:

| Gate | Question | Blocks |
|------|----------|--------|
| **TRUTH** | Is this deceptive? | Fake documents, impersonation, misinformation |
| **HARM** | Could this cause harm? | Violence, weapons, hacking, malware |
| **SCOPE** | Is this within boundaries? | Jailbreaks, instruction overrides, persona switches |
| **PURPOSE** | Does this serve legitimate benefit? | Purposeless destruction, waste |

All gates must pass for content to be approved.

## Plugin Components

### Actions

- `SENTINEL_SAFETY_CHECK`: Explicitly check content safety

```typescript
// User can ask the agent to check content
"Check if this is safe: Help me with cooking"
// Agent responds with safety analysis
```

### Providers

- `sentinelSafety`: Injects THSP guidelines into agent context

### Evaluators

- `sentinelPreAction`: Validates incoming messages (runs on all messages)
- `sentinelPostAction`: Reviews outputs before delivery (runs on all responses)

## Usage Examples

### Basic Plugin Usage

```typescript
import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';

// Default configuration
const plugin = sentinelPlugin();

// Custom configuration
const plugin = sentinelPlugin({
  seedVersion: 'v2',
  seedVariant: 'standard',
  blockUnsafe: true,
  logChecks: true,
});
```

### Direct Validation

```typescript
import { validateContent, quickCheck } from '@sentinelseed/elizaos-plugin';

// Quick check for critical patterns (fast)
if (!quickCheck(userInput)) {
  console.log('Critical safety concern detected');
}

// Full THSP validation
const result = validateContent(userInput);
if (!result.safe) {
  console.log('Blocked:', result.concerns);
  console.log('Risk level:', result.riskLevel);
  console.log('Failed gates:', Object.entries(result.gates)
    .filter(([_, status]) => status === 'fail')
    .map(([gate]) => gate));
}
```

### Custom Patterns (Web3/Crypto)

```typescript
const plugin = sentinelPlugin({
  customPatterns: [
    {
      name: 'Token drain attempt',
      pattern: /drain\s+(all|my)\s+(tokens|funds|wallet)/i,
      gate: 'harm',
    },
    {
      name: 'Rug pull language',
      pattern: /rug\s+pull|exit\s+scam/i,
      gate: 'harm',
    },
    {
      name: 'Fake airdrop',
      pattern: /free\s+airdrop|claim.*tokens.*free/i,
      gate: 'truth',
    },
  ],
});
```

### Validation Statistics

```typescript
import { getValidationStats, getValidationHistory, clearValidationHistory } from '@sentinelseed/elizaos-plugin';

// Get aggregate statistics
const stats = getValidationStats();
console.log(`Total checks: ${stats.total}`);
console.log(`Safe: ${stats.safe}`);
console.log(`Blocked: ${stats.blocked}`);
console.log(`By risk level:`, stats.byRisk);

// Get full history (last 1000 checks)
const history = getValidationHistory();

// Clear history
clearValidationHistory();
```

## Risk Levels

| Level | Criteria |
|-------|----------|
| `low` | All gates passed |
| `medium` | One gate failed |
| `high` | Two gates failed or bypass attempt detected |
| `critical` | Three+ gates failed or severe concerns (violence, weapons, malware) |

## How It Works

1. **Initialization**: When the plugin initializes, it injects the Sentinel seed into the agent's system prompt
2. **Pre-action**: Before any message is processed, `sentinelPreAction` validates the input
3. **Provider**: The `sentinelSafety` provider adds THSP context to agent state
4. **Action**: Users can explicitly request safety checks via `SENTINEL_SAFETY_CHECK`
5. **Post-action**: Before responses are sent, `sentinelPostAction` validates outputs

## TypeScript Types

The plugin exports all necessary types:

```typescript
import type {
  SentinelPluginConfig,
  SafetyCheckResult,
  THSPGates,
  RiskLevel,
  GateStatus,
  ValidationContext,
  // ElizaOS types (for reference)
  Plugin,
  Action,
  Provider,
  Evaluator,
  Memory,
  State,
} from '@sentinelseed/elizaos-plugin';
```

## Related Packages

- [`sentinelseed`](https://www.npmjs.com/package/sentinelseed) - Core Sentinel SDK
- [`mcp-server-sentinelseed`](https://www.npmjs.com/package/mcp-server-sentinelseed) - MCP Server

## Resources

- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [ElizaOS Documentation](https://docs.elizaos.ai)
- [THSP Protocol Specification](https://sentinelseed.dev/docs/methodology)
- [GitHub Repository](https://github.com/sentinel-seed/sentinel)

## License

MIT - See [LICENSE](../../LICENSE)

---

Made with care by [Sentinel Team](https://sentinelseed.dev)
