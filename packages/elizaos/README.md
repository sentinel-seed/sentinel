# @sentinelseed/elizaos-plugin

> AI Safety Plugin for ElizaOS - THSP Protocol Validation for Autonomous Agents

[![npm version](https://badge.fury.io/js/@sentinelseed%2Felizaos-plugin.svg)](https://www.npmjs.com/package/@sentinelseed/elizaos-plugin)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Official Sentinel safety plugin for [ElizaOS](https://elizaos.ai) autonomous agents. Implements the THSP (Truth, Harm, Scope, Purpose) protocol to validate agent actions and outputs.

## Features

- **THSP Protocol**: Four-gate validation (Truth, Harm, Scope, Purpose)
- **Memory Integrity**: HMAC-based protection against memory injection attacks (v1.1.0+)
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
  // When false: unsafe content is logged but processing continues (shouldProceed = true)
  // When true: unsafe content blocks processing (shouldProceed = false)
  blockUnsafe?: boolean;

  // Log all safety checks to logger. Default: false
  logChecks?: boolean;

  // Custom logger instance (Winston, Pino, etc.). Default: console
  logger?: {
    log(message: string): void;
    warn(message: string): void;
    error(message: string): void;
  };

  // Custom patterns to detect
  customPatterns?: Array<{
    name: string;
    pattern: RegExp;
    gate: 'truth' | 'harm' | 'scope' | 'purpose';
  }>;

  // Actions to skip validation
  skipActions?: string[];

  // Maximum text size in bytes. Default: 50KB (51200 bytes)
  // Texts exceeding this limit are rejected to prevent DoS
  maxTextSize?: number;

  // Instance name for multi-plugin scenarios. Default: auto-generated
  instanceName?: string;

  // Memory integrity settings (v1.1.0+)
  memoryIntegrity?: {
    enabled: boolean;           // Enable memory signing/verification
    secretKey?: string;         // HMAC secret key (auto-generated if not provided)
    verifyOnRead?: boolean;     // Verify memories when retrieved
    signOnWrite?: boolean;      // Sign memories when stored
    minTrustScore?: number;     // Minimum trust score (0-1) to accept memory
  };
}
```

### Important Notes

- **History limit**: Validation and memory verification histories are limited to **1000 entries** each to prevent memory leaks. Older entries are automatically removed.
- **Text size limit**: Maximum text size is **50KB** by default. Configure with `maxTextSize` option. Texts exceeding this limit return an error to prevent DoS attacks.
- **blockUnsafe behavior**: When `blockUnsafe: false`, unsafe content still triggers validation and logging, but the action proceeds (`shouldProceed: true`). This is useful for monitoring without blocking.
- **Multi-instance support**: Each `sentinelPlugin()` call creates an isolated instance registered in a global registry. Use `instanceName` config option for named access.
- **Error handling**: All handlers use try/catch with structured error responses. Evaluators use fail-open behavior (allow on error) while actions return error details.

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
- `sentinelMemoryIntegrity`: Verifies memory integrity on retrieval (v1.1.0+)

## Memory Integrity (v1.1.0+)

Protect agent memories against injection attacks with HMAC-based signing:

```typescript
import { sentinelPlugin, signMemory, verifyMemory, getMemoryChecker } from '@sentinelseed/elizaos-plugin';

// Enable memory integrity in plugin config
const plugin = sentinelPlugin({
  memoryIntegrity: {
    enabled: true,
    secretKey: process.env.SENTINEL_SECRET_KEY,
    verifyOnRead: true,
    signOnWrite: true,
    minTrustScore: 0.7,
  }
});

// Manual memory operations
const checker = getMemoryChecker();

// Sign a memory before storing
const signedMemory = signMemory(memory, 'user_direct');

// Verify a memory after retrieval
const result = verifyMemory(signedMemory);
if (!result.valid) {
  console.log(`Tampering detected: ${result.reason}`);
}
```

### Trust Scores by Source

| Source | Score | Description |
|--------|-------|-------------|
| `user_verified` | 1.0 | Cryptographically verified user input |
| `user_direct` | 0.9 | Direct user input |
| `blockchain` | 0.85 | On-chain verified data |
| `agent_internal` | 0.8 | Agent's own computations |
| `external_api` | 0.7 | Third-party API data |
| `social_media` | 0.5 | Social media sources |
| `unknown` | 0.3 | Unverified source |

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
import { validateContent, validateAction, quickCheck } from '@sentinelseed/elizaos-plugin';

// Quick check for critical patterns (fast)
if (!quickCheck(userInput)) {
  console.log('Critical safety concern detected');
}

// Full THSP validation for content
const result = validateContent(userInput);
if (!result.safe) {
  console.log('Blocked:', result.concerns);
  console.log('Risk level:', result.riskLevel);
  console.log('Failed gates:', Object.entries(result.gates)
    .filter(([_, status]) => status === 'fail')
    .map(([gate]) => gate));
}

// Validate an action before execution
const actionResult = validateAction({
  action: 'send_email',
  params: { to: 'user@example.com', subject: 'Hello' },
  purpose: 'User requested notification',
});
if (!actionResult.safe) {
  console.log('Action blocked:', actionResult.concerns);
}
```

### Custom Patterns (Web3/Crypto)

```typescript
const plugin = sentinelPlugin({
  customPatterns: [
    {
      name: 'Token drain attempt',
      pattern: /drain\s+(all\s+)?(my\s+)?(tokens|funds|wallet)/i,
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

**Note:** Statistics are tracked only for validations performed through plugin handlers (evaluators). Direct calls to `validateContent()` are not tracked.

```typescript
import { getValidationStats, getValidationHistory, clearValidationHistory } from '@sentinelseed/elizaos-plugin';

// Get aggregate statistics (from plugin evaluators only)
const stats = getValidationStats();
console.log(`Total checks: ${stats.total}`);
console.log(`Safe: ${stats.safe}`);
console.log(`Blocked: ${stats.blocked}`);
console.log(`By risk level:`, stats.byRisk);

// Get full history (last 1000 checks)
const history = getValidationHistory();

// Clear history
clearValidationHistory();

// Memory verification statistics (v1.1.0+)
const memStats = getMemoryVerificationStats();
console.log(`Memory checks: ${memStats.total}`);
console.log(`Valid: ${memStats.valid}`);
console.log(`Invalid: ${memStats.invalid}`);

// Get memory verification history
const memHistory = getMemoryVerificationHistory();

// Clear memory verification history
clearMemoryVerificationHistory();

// Check if memory integrity is enabled
if (isMemoryIntegrityEnabled()) {
  console.log('Memory integrity protection is active');
}
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

## Validation Approach

The plugin uses a **dual-layer validation** approach:

### Layer 1: Heuristic Validation (Fast)

Pattern-based detection using regex for known harmful patterns:
- **TRUTH Gate**: Detects deception attempts, role manipulation, fake identity claims
- **HARM Gate**: Detects violence, hacking, malware, weapons, dangerous substances
- **SCOPE Gate**: Detects jailbreak attempts, instruction overrides, prompt extraction
- **PURPOSE Gate**: Detects purposeless destruction patterns

### Layer 2: Seed Injection (Comprehensive)

The Sentinel seed is injected into the agent's system prompt, providing LLM-level understanding of the THSP protocol. This layer can detect nuanced threats that patterns cannot.

### Important Limitations

**Heuristic validation has inherent limitations:**

1. **Pattern Coverage**: Only detects patterns explicitly defined. Novel attack vectors may not be caught.

2. **PURPOSE Gate Gaps**: Abstract concepts like "purposeless action" are difficult to detect via regex. Examples:
   - "Drop the plate" (purposeless destruction) - may not be detected heuristically
   - "Dirty the mirror" (pointless action) - relies on seed injection for detection

3. **False Negatives**: Slight variations in phrasing may bypass patterns:
   - `"How to hack..."` → Detected ✓
   - `"How do I hack..."` → May not be detected (pattern mismatch)

4. **Context Blindness**: Heuristics cannot understand context or intent.

**Recommendation**: For maximum safety, rely on both layers:
- Use heuristic validation for fast, low-latency checks
- The injected seed provides the comprehensive safety net

## Multi-Instance Support

When running multiple agents with different configurations:

```typescript
import {
  sentinelPlugin,
  getPluginInstance,
  getPluginInstanceNames,
  getActivePluginInstance,
  removePluginInstance,
  clearPluginRegistry,
} from '@sentinelseed/elizaos-plugin';

// Create named instances
const strictPlugin = sentinelPlugin({
  instanceName: 'strict-agent',
  blockUnsafe: true,
  maxTextSize: 10 * 1024, // 10KB
});

const monitorPlugin = sentinelPlugin({
  instanceName: 'monitor-agent',
  blockUnsafe: false,
  logChecks: true,
});

// Access specific instance
const strictState = getPluginInstance('strict-agent');
const history = strictState?.validationHistory || [];

// List all instances
console.log(getPluginInstanceNames()); // ['strict-agent', 'monitor-agent']

// Get most recently created
const active = getActivePluginInstance();

// Cleanup
removePluginInstance('monitor-agent');
clearPluginRegistry(); // Remove all
```

**Note**: Exported utility functions like `getValidationHistory()` operate on the most recently created instance. For multi-instance scenarios, use `getPluginInstance(name)` to access specific instances.

## Error Handling

Handlers include comprehensive error handling:

```typescript
import { TextTooLargeError } from '@sentinelseed/elizaos-plugin';

// Text size errors include details
try {
  // ... validation
} catch (err) {
  if (err instanceof TextTooLargeError) {
    console.log(`Size: ${err.size}, Max: ${err.maxSize}`);
  }
}

// Action results include error data
const result = await action.handler(runtime, message);
if (!result.success) {
  console.log(result.error); // Error message
  console.log(result.data);  // { error: 'text_too_large', size, maxSize }
}
```

## TypeScript Types

The plugin exports all necessary types:

```typescript
import type {
  // Sentinel types
  SentinelPluginConfig,
  SafetyCheckResult,
  THSPGates,
  RiskLevel,
  GateStatus,
  ValidationContext,
  // Plugin state types
  SentinelLogger,      // For custom logger implementations
  PluginStateInfo,     // Return type of getPluginInstance()
  // Memory integrity types
  MemorySource,
  MemoryVerificationResult,
  IntegrityMetadata,
  MemoryIntegrityConfig,
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
- [Contact](mailto:team@sentinelseed.dev)

## License

MIT - See [LICENSE](../../LICENSE)

---

Made with care by [Sentinel Team](https://sentinelseed.dev) | [team@sentinelseed.dev](mailto:team@sentinelseed.dev)
