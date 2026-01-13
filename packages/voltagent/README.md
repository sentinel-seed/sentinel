# @sentinelseed/voltagent

AI safety guardrails for VoltAgent applications. Implements THSP protocol validation, OWASP security protection, and PII detection/redaction.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)

## Features

- **THSP Protocol**: Truth, Harm, Scope, Purpose validation gates
- **OWASP Protection**: SQL injection, XSS, command injection, SSRF detection
- **PII Detection**: Email, phone, SSN, credit card, API keys, and more
- **Streaming Support**: Real-time PII redaction for streaming responses
- **VoltAgent Native**: Works directly with VoltAgent's guardrail system

## Installation

```bash
npm install @sentinelseed/voltagent
```

## Quick Start

The simplest way to add Sentinel protection to your VoltAgent agent:

```typescript
import { Agent } from "@voltagent/core";
import { createSentinelGuardrails } from "@sentinelseed/voltagent";

// Create guardrails with preset configuration
const { inputGuardrails, outputGuardrails } = createSentinelGuardrails({
  level: "strict",
  enablePII: true,
});

// Add to your agent
const agent = new Agent({
  name: "safe-agent",
  inputGuardrails,
  outputGuardrails,
});
```

## Configuration Presets

| Level | Description |
|-------|-------------|
| `permissive` | Log only, no blocking. Good for development. |
| `standard` | Block unsafe content, THSP + OWASP enabled. Recommended for production. |
| `strict` | All validations, block on any issue. For high-security applications. |

## Usage Examples

### Basic Input Protection

```typescript
import { createSentinelInputGuardrail } from "@sentinelseed/voltagent";

const inputGuard = createSentinelInputGuardrail({
  enableTHSP: true,
  enableOWASP: true,
  blockUnsafe: true,
});

const agent = new Agent({
  inputGuardrails: [inputGuard],
});
```

### PII Redaction in Responses

```typescript
import { createSentinelOutputGuardrail } from "@sentinelseed/voltagent";

const outputGuard = createSentinelOutputGuardrail({
  enablePII: true,
  redactPII: true,
});

const agent = new Agent({
  outputGuardrails: [outputGuard],
});

// Input: "Contact john@example.com or call 555-123-4567"
// Output: "Contact [EMAIL] or call [PHONE]"
```

### Specialized Guardrails

```typescript
import {
  createChatGuardrails,
  createAgentGuardrails,
  createPrivacyGuardrails,
} from "@sentinelseed/voltagent";

// For chat applications (jailbreak prevention)
const chatGuards = createChatGuardrails();

// For agent applications (tool call protection)
const agentGuards = createAgentGuardrails();

// For privacy-sensitive applications (full PII protection)
const privacyGuards = createPrivacyGuardrails();
```

### Custom Patterns

```typescript
const guard = createSentinelInputGuardrail({
  customPatterns: [
    {
      pattern: /internal\s+only/i,
      name: "Internal content restriction",
      gate: "scope",
      severity: "high",
    },
  ],
});
```

## THSP Protocol

The THSP protocol validates content against four safety gates:

| Gate | Description | Example Violations |
|------|-------------|-------------------|
| **Truth** | Factual accuracy | Fake documents, impersonation |
| **Harm** | Potential for harm | Violence, malware, theft |
| **Scope** | Operational boundaries | Jailbreaks, persona switching |
| **Purpose** | Legitimate intent | Purposeless destruction |

## OWASP Protection

Detects common security vulnerabilities:

- SQL Injection
- Cross-Site Scripting (XSS)
- Command Injection
- Path Traversal
- Server-Side Request Forgery (SSRF)
- Prompt Injection
- Sensitive Data Exposure

## PII Types Detected

- Email addresses
- Phone numbers
- Social Security Numbers
- Credit card numbers
- IP addresses
- Dates of birth
- API keys / AWS keys
- Private keys
- JWT tokens
- Passport numbers
- Driver license numbers

## Streaming Support

For streaming responses, use the stream handler:

```typescript
import { createSentinelPIIRedactor } from "@sentinelseed/voltagent";

const piiRedactor = createSentinelPIIRedactor({
  enablePII: true,
  piiTypes: ["EMAIL", "PHONE", "SSN"],
});

const guardrail = {
  name: "pii-stream-redactor",
  handler: async (args) => ({ pass: true }),
  streamHandler: piiRedactor,
};
```

## API Reference

### Bundle Functions

| Function | Description |
|----------|-------------|
| `createSentinelGuardrails(config)` | Create complete input/output guardrail bundle |
| `createChatGuardrails()` | Preset for chat applications |
| `createAgentGuardrails()` | Preset for agent applications |
| `createPrivacyGuardrails()` | Preset for privacy-focused applications |
| `createDevelopmentGuardrails(logger)` | Permissive preset for development |

### Input Guardrails

| Function | Description |
|----------|-------------|
| `createSentinelInputGuardrail(config)` | Main input guardrail factory |
| `createStrictInputGuardrail()` | Strict preset |
| `createPermissiveInputGuardrail(logger)` | Log-only preset |
| `createTHSPOnlyGuardrail()` | THSP validation only |
| `createOWASPOnlyGuardrail()` | OWASP validation only |

### Output Guardrails

| Function | Description |
|----------|-------------|
| `createSentinelOutputGuardrail(config)` | Main output guardrail factory |
| `createPIIOutputGuardrail(options)` | PII-focused output guardrail |
| `createStrictOutputGuardrail()` | Block on any sensitive content |
| `createPermissiveOutputGuardrail(logger)` | Redact only, no blocking |

### Streaming Handlers

| Function | Description |
|----------|-------------|
| `createSentinelPIIRedactor(config)` | Streaming PII redactor |
| `createStrictStreamingRedactor(config)` | Abort on sensitive content |
| `createPermissiveStreamingRedactor(types)` | PII redaction only |
| `createMonitoringStreamHandler(logger)` | Detection without modification |

### Validators (Advanced)

| Function | Description |
|----------|-------------|
| `validateTHSP(content, context, patterns)` | Run THSP validation |
| `validateOWASP(content, checks, patterns)` | Run OWASP validation |
| `detectPII(content, types, patterns)` | Detect PII in content |
| `redactPII(content, types, format)` | Redact PII from content |
| `quickCheck(content)` | Fast THSP check |
| `quickOWASPCheck(content)` | Fast OWASP check |
| `hasPII(content)` | Quick PII detection |

## Configuration Options

```typescript
interface SentinelGuardrailConfig {
  // Behavior
  blockUnsafe?: boolean;           // Block unsafe content (default: true)
  logChecks?: boolean;             // Enable logging (default: false)
  logger?: (msg, data) => void;    // Custom logger function

  // Validation modules
  enableTHSP?: boolean;            // Enable THSP (default: true)
  enableOWASP?: boolean;           // Enable OWASP (default: true)
  enablePII?: boolean;             // Enable PII detection (default: false)

  // THSP options
  customPatterns?: PatternDefinition[];
  skipActions?: string[];
  minBlockLevel?: RiskLevel;       // 'low' | 'medium' | 'high' | 'critical'

  // OWASP options
  owaspChecks?: OWASPViolationType[];
  customOWASPPatterns?: OWASPPatternDefinition[];

  // PII options
  piiTypes?: PIIType[];
  redactPII?: boolean;
  redactionFormat?: string | ((type, value) => string);

  // Performance
  maxContentLength?: number;       // Max content length (default: 100000)
  timeout?: number;                // Timeout in ms (default: 5000)
}
```

## Requirements

- Node.js >= 18.0.0
- VoltAgent >= 0.1.0 (tested with @voltagent/core v1.5.2)

## Development

This package depends on `@sentinelseed/core` which provides the THSP validation patterns. When developing locally, the dependency is resolved via `file:../core` in the monorepo structure.

For production npm installations, the core patterns are bundled during the build process. If you're building from source, ensure you have the full monorepo cloned:

```bash
git clone https://github.com/sentinel-seed/sentinel.git
cd sentinel
npm install
npm run build -w packages/core
npm run build -w packages/voltagent
```

## Related Packages

- [`sentinelseed`](https://www.npmjs.com/package/sentinelseed): Python package
- [`@sentinelseed/elizaos-plugin`](https://www.npmjs.com/package/@sentinelseed/elizaos-plugin): ElizaOS integration

## Links

- [GitHub](https://github.com/sentinel-seed/sentinel/tree/main/packages/voltagent)
- [Sentinel Documentation](https://sentinelseed.dev)
- [VoltAgent Documentation](https://voltagent.dev/docs/)

## License

MIT License (see [LICENSE](./LICENSE) for details)

---

Built by [Sentinel Team](https://sentinelseed.dev)
