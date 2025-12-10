# @sentinelseed/elizaos-plugin

> AI Safety Plugin for ElizaOS - THSP Protocol Validation for Autonomous Agents

[![npm version](https://badge.fury.io/js/@sentinelseed%2Felizaos-plugin.svg)](https://www.npmjs.com/package/@sentinelseed/elizaos-plugin)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Official Sentinel safety plugin for [ElizaOS](https://elizaos.ai) autonomous agents. Implements the THSP (Truth, Harm, Scope, Purpose) protocol to validate agent actions and outputs.

## Features

- **THSP Protocol**: Four-gate validation (Truth, Harm, Scope, Purpose)
- **Pre-action Validation**: Check requests before execution
- **Post-action Review**: Validate outputs before delivery
- **Seed Injection**: Automatically inject alignment seed into agent character
- **Configurable**: Block or log unsafe content
- **History Tracking**: Full validation history and statistics

## Installation

```bash
npm install @sentinelseed/elizaos-plugin
# or
pnpm add @sentinelseed/elizaos-plugin
```

## Quick Start

```typescript
import { Agent } from '@elizaos/core';
import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';

const agent = new Agent({
  character: myCharacter,
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
  // Seed version: 'v1' (THS) or 'v2' (THSP). Default: 'v2'
  seedVersion?: 'v1' | 'v2';

  // Seed variant: 'minimal', 'standard', or 'full'. Default: 'standard'
  seedVariant?: 'minimal' | 'standard' | 'full';

  // Block unsafe actions or just log. Default: true
  blockUnsafe?: boolean;

  // Log all safety checks. Default: true
  logChecks?: boolean;

  // Custom patterns to detect
  customPatterns?: Array<{
    name: string;
    pattern: RegExp;
    gate: 'truth' | 'harm' | 'scope' | 'purpose';
  }>;

  // Actions to skip validation
  skipValidation?: string[];
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

// Quick check for critical patterns
if (!quickCheck(userInput)) {
  console.log('Critical safety concern detected');
}

// Full validation
const result = validateContent(userInput);
if (!result.safe) {
  console.log('Blocked:', result.concerns);
  console.log('Risk level:', result.riskLevel);
}
```

### Custom Patterns

```typescript
const plugin = sentinelPlugin({
  customPatterns: [
    {
      name: 'Token drain attempt',
      pattern: /drain\s+(all|my)\s+(tokens|funds)/i,
      gate: 'harm',
    },
    {
      name: 'Rug pull language',
      pattern: /rug\s+pull|exit\s+scam/i,
      gate: 'harm',
    },
  ],
});
```

### Validation Statistics

```typescript
import { getValidationStats, getValidationHistory } from '@sentinelseed/elizaos-plugin';

// Get statistics
const stats = getValidationStats();
console.log(`Total: ${stats.total}`);
console.log(`Safe: ${stats.safe}`);
console.log(`Blocked: ${stats.blocked}`);
console.log(`By risk:`, stats.byRisk);

// Get full history
const history = getValidationHistory();
```

## Integration with ElizaOS

The plugin integrates with ElizaOS through:

### Actions

- `SENTINEL_SAFETY_CHECK`: Explicitly check content safety

### Providers

- `sentinelSafety`: Provides safety guidelines context to the agent

### Evaluators

- `sentinelPreAction`: Validates incoming messages before processing
- `sentinelPostAction`: Reviews agent outputs before delivery

## Risk Levels

| Level | Criteria |
|-------|----------|
| `low` | All gates passed |
| `medium` | One gate failed |
| `high` | Two gates failed or bypass attempt |
| `critical` | Three+ gates failed or severe concerns (violence, weapons) |

## Examples

### Web3 Agent with Safety

```typescript
import { Agent } from '@elizaos/core';
import { sentinelPlugin } from '@sentinelseed/elizaos-plugin';

const cryptoAgent = new Agent({
  character: {
    name: 'SafeTrader',
    system: 'You are a helpful crypto trading assistant.',
  },
  plugins: [
    sentinelPlugin({
      blockUnsafe: true,
      customPatterns: [
        { name: 'Drain attempt', pattern: /drain|sweep\s+all/i, gate: 'harm' },
        { name: 'Fake airdrop', pattern: /free\s+airdrop|claim.*tokens/i, gate: 'truth' },
      ],
    }),
    // ... other plugins
  ],
});
```

### Discord Bot with Logging

```typescript
import { sentinelPlugin, getValidationStats } from '@sentinelseed/elizaos-plugin';

const plugin = sentinelPlugin({
  logChecks: true,
  blockUnsafe: true,
});

// Periodic stats logging
setInterval(() => {
  const stats = getValidationStats();
  console.log(`[SENTINEL] Stats - Safe: ${stats.safe}, Blocked: ${stats.blocked}`);
}, 60000);
```

## Related Packages

- [`sentinelseed`](https://www.npmjs.com/package/sentinelseed) - Core Sentinel SDK
- [`mcp-server-sentinelseed`](https://www.npmjs.com/package/mcp-server-sentinelseed) - MCP Server

## Resources

- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [ElizaOS Documentation](https://docs.elizaos.ai)
- [THSP Protocol Specification](https://sentinelseed.dev/docs/methodology)
- [GitHub Repository](https://github.com/sentinel-movement/sentinel)

## License

MIT - See [LICENSE](LICENSE)

---

Made with 🛡️ by [Sentinel Team](https://sentinelseed.dev)
