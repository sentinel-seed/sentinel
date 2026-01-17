# @sentinelseed/core

Core validation module for Sentinel. Implements the THSP Protocol (Truth, Harm, Scope, Purpose) with pattern-based heuristic validation and optional semantic analysis via API.

## Features

| Feature | Description |
|---------|-------------|
| **THSP Protocol** | Five-gate validation system (Truth, Harm, Scope, Purpose, Jailbreak) |
| **Heuristic Validation** | Pattern-based detection, runs offline, sub-millisecond latency |
| **Semantic Validation** | LLM-powered analysis via API for nuanced cases |
| **700+ Patterns** | Comprehensive pattern library synchronized with Python core |
| **TypeScript Native** | Full type definitions included |

## Installation

```bash
npm install @sentinelseed/core
```

## Quick Start

### Heuristic Validation (Offline)

```typescript
import { validateTHSP, quickCheck } from '@sentinelseed/core';

// Full validation with detailed results
const result = validateTHSP("Hello, how can I help you?");

if (result.overall) {
  console.log("Content is safe");
} else {
  console.log("Blocked:", result.summary);
  console.log("Risk level:", result.riskLevel);
}

// Quick boolean check
if (quickCheck("Some user input")) {
  // Process input
} else {
  // Block input
}
```

### Semantic Validation (API)

```typescript
import { configureApi, validateWithFallback } from '@sentinelseed/core';

// Configure API endpoint
configureApi({
  endpoint: 'https://api.sentinelseed.dev',
  apiKey: process.env.SENTINEL_API_KEY,
});

// Validate with heuristic first, API fallback for edge cases
const result = await validateWithFallback("Complex content to analyze");

console.log("Safe:", result.is_safe);
console.log("Layer:", result.layer); // "heuristic" or "semantic"
```

## API Reference

### Core Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `validateTHSP(text)` | Full THSP validation through all gates | `THSPResult` |
| `quickCheck(text)` | Fast boolean safety check | `boolean` |
| `checkJailbreak(text)` | Jailbreak detection only | `GateResult` |
| `checkHarm(text)` | Harm detection only | `GateResult` |
| `validateWithFallback(text)` | Heuristic with API fallback | `Promise<ValidateResponse>` |

### Types

```typescript
interface THSPResult {
  truth: GateResult;
  harm: GateResult;
  scope: GateResult;
  purpose: GateResult;
  jailbreak: GateResult;
  overall: boolean;
  summary: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
}

interface GateResult {
  passed: boolean;
  score: number;
  violations: string[];
}
```

## Gate Descriptions

| Gate | Function | Examples |
|------|----------|----------|
| **Truth** | Detects deception and misinformation | Impersonation, false claims |
| **Harm** | Identifies harmful content and sensitive data | Violence, malware, credentials |
| **Scope** | Catches boundary violations | Unauthorized access, excessive permissions |
| **Purpose** | Flags purposeless destruction | Actions without legitimate benefit |
| **Jailbreak** | Detects prompt injection attacks | Instruction override, DAN mode, roleplay manipulation |

## Pattern Categories

The package includes 700+ patterns organized by category:

**Jailbreak Detection**
- Instruction override patterns
- Role manipulation patterns
- Prompt extraction patterns
- Filter bypass patterns
- Roleplay manipulation patterns
- System injection patterns

**Harm Detection**
- Violence and weapons
- Malware and hacking
- Illegal activities
- Self-harm content

**Sensitive Data**
- API keys (OpenAI, AWS, GitHub)
- Passwords and credentials
- PII (emails, phone numbers)

## Usage in Browser Extensions

```typescript
import { validateTHSP } from '@sentinelseed/core';

// Validate user input before sending to AI
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'VALIDATE') {
    const result = validateTHSP(message.text);
    sendResponse({
      safe: result.overall,
      violations: result.summary,
    });
  }
});
```

## Usage in Node.js

```typescript
import { validateTHSP, configureApi, validateSemantic } from '@sentinelseed/core';

// Heuristic validation (no network required)
const heuristicResult = validateTHSP(userInput);

if (!heuristicResult.overall) {
  // Blocked by heuristic
  return { blocked: true, reason: heuristicResult.summary };
}

// Optional: semantic validation for edge cases
configureApi({ endpoint: 'https://api.sentinelseed.dev' });
const semanticResult = await validateSemantic({
  content: userInput,
  context: { source: 'user' },
});
```

## Performance

| Operation | Latency | Cost |
|-----------|---------|------|
| Heuristic validation | < 1ms | Free |
| Semantic validation | 500ms to 2s | API usage |

## Development

```bash
# Build
npm run build

# Test
npm run test

# Lint
npm run lint

# Type check
npm run typecheck
```

## License

MIT

## Links

| Resource | URL |
|----------|-----|
| Website | https://sentinelseed.dev |
| Documentation | https://sentinelseed.dev/docs |
| GitHub | https://github.com/sentinel-seed/sentinel |
| Issues | https://github.com/sentinel-seed/sentinel/issues |
