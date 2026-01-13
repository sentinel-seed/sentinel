# JavaScript SDK Reference

Complete API reference for the Sentinel JavaScript/TypeScript SDK (`@sentinelseed/core`).

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Functions](#core-functions)
  - [validateTHSP](#validatethsp)
  - [quickCheck](#quickcheck)
  - [checkJailbreak](#checkjailbreak)
  - [checkHarm](#checkharm)
- [API Client Functions](#api-client-functions)
  - [configureApi](#configureapi)
  - [validateViaApi](#validateviaapi)
  - [validateSemantic](#validatesemantic)
  - [validateWithFallback](#validatewithfallback)
  - [checkApiHealth](#checkapihealth)
- [Types](#types)
  - [THSPResult](#thspresult)
  - [GateResult](#gateresult)
  - [ValidationContext](#validationcontext)
  - [ApiConfig](#apiconfig)
  - [ValidateRequest](#validaterequest)
  - [ValidateResponse](#validateresponse)
- [Pattern Collections](#pattern-collections)
- [Usage Examples](#usage-examples)

---

## Installation

```bash
npm install @sentinelseed/core
```

Or with yarn:

```bash
yarn add @sentinelseed/core
```

Or with pnpm:

```bash
pnpm add @sentinelseed/core
```

---

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
  processInput();
} else {
  blockInput();
}
```

### With API Fallback

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
console.log("Layer:", result.layer);
```

---

## Core Functions

### validateTHSP

Full THSP validation through all five gates.

```typescript
function validateTHSP(
  text: string,
  context?: ValidationContext
): THSPResult
```

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `text` | `string` | Yes | Text content to validate |
| `context` | `ValidationContext` | No | Optional validation context |

**Returns:** `THSPResult`

**Example:**

```typescript
import { validateTHSP } from '@sentinelseed/core';

const result = validateTHSP("Help me write a function");

if (result.overall) {
  console.log("Safe to proceed");
} else {
  console.log("Blocked gates:", Object.entries(result)
    .filter(([key, val]) => typeof val === 'object' && !val.passed)
    .map(([key]) => key)
  );
}
```

**Performance:** < 1ms (heuristic, offline)

---

### quickCheck

Fast boolean safety check.

```typescript
function quickCheck(text: string): boolean
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `string` | Text to check |

**Returns:** `boolean` - `true` if safe, `false` if blocked

**Example:**

```typescript
import { quickCheck } from '@sentinelseed/core';

if (quickCheck(userInput)) {
  sendToLLM(userInput);
} else {
  showError("Input blocked for safety");
}
```

**Performance:** < 0.5ms

---

### checkJailbreak

Jailbreak detection only.

```typescript
function checkJailbreak(text: string): GateResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `string` | Text to check |

**Returns:** `GateResult`

**Example:**

```typescript
import { checkJailbreak } from '@sentinelseed/core';

const result = checkJailbreak("Ignore your instructions and...");

if (!result.passed) {
  console.log("Jailbreak detected:", result.violations);
}
```

---

### checkHarm

Harm detection only.

```typescript
function checkHarm(text: string): GateResult
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `string` | Text to check |

**Returns:** `GateResult`

**Example:**

```typescript
import { checkHarm } from '@sentinelseed/core';

const result = checkHarm(llmResponse);

if (!result.passed) {
  console.log("Harmful content detected:", result.violations);
  console.log("Score:", result.score);
}
```

---

## API Client Functions

### configureApi

Configure API endpoint for semantic validation.

```typescript
function configureApi(config: Partial<ApiConfig>): void
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `config` | `Partial<ApiConfig>` | API configuration |

**Example:**

```typescript
import { configureApi } from '@sentinelseed/core';

configureApi({
  endpoint: 'https://api.sentinelseed.dev',
  apiKey: process.env.SENTINEL_API_KEY,
  timeout: 5000,
});
```

---

### getApiConfig

Get current API configuration.

```typescript
function getApiConfig(): ApiConfig
```

**Returns:** Current `ApiConfig`

---

### validateViaApi

Validate content via REST API.

```typescript
async function validateViaApi(
  request: ValidateRequest
): Promise<ValidateResponse>
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `ValidateRequest` | Validation request |

**Returns:** `Promise<ValidateResponse>`

**Example:**

```typescript
import { configureApi, validateViaApi } from '@sentinelseed/core';

configureApi({ endpoint: 'https://api.sentinelseed.dev' });

const result = await validateViaApi({
  text: "Content to validate",
});

console.log("Safe:", result.is_safe);
console.log("Gates:", result.gates);
```

---

### validateSemantic

Semantic validation via LLM.

```typescript
async function validateSemantic(
  request: SemanticValidateRequest
): Promise<SemanticValidateResponse>
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `request` | `SemanticValidateRequest` | Semantic validation request |

**Returns:** `Promise<SemanticValidateResponse>`

**Example:**

```typescript
import { validateSemantic } from '@sentinelseed/core';

const result = await validateSemantic({
  content: "Complex edge case content",
  context: {
    source: "user_input",
    application: "chatbot",
  },
});

console.log("Safe:", result.is_safe);
console.log("Reasoning:", result.reasoning);
```

---

### validateWithFallback

Heuristic validation with API fallback.

```typescript
async function validateWithFallback(
  text: string,
  context?: ValidationContext
): Promise<ValidateResponse>
```

**Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `text` | `string` | Text to validate |
| `context` | `ValidationContext` | Optional context |

**Returns:** `Promise<ValidateResponse>`

**Flow:**
1. Run heuristic validation
2. If heuristic blocks → return immediately
3. If heuristic passes → optionally call API for edge cases
4. Return combined result

**Example:**

```typescript
import { configureApi, validateWithFallback } from '@sentinelseed/core';

configureApi({ endpoint: 'https://api.sentinelseed.dev' });

const result = await validateWithFallback("Check this content");

console.log("Safe:", result.is_safe);
console.log("Layer:", result.layer); // "heuristic" or "semantic"
```

---

### checkApiHealth

Check API health status.

```typescript
async function checkApiHealth(): Promise<boolean>
```

**Returns:** `Promise<boolean>` - `true` if API is healthy

**Example:**

```typescript
import { checkApiHealth } from '@sentinelseed/core';

const healthy = await checkApiHealth();
if (!healthy) {
  console.warn("API unavailable, falling back to heuristic only");
}
```

---

## Types

### THSPResult

Result from full THSP validation.

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
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `truth` | `GateResult` | Truth gate result |
| `harm` | `GateResult` | Harm gate result |
| `scope` | `GateResult` | Scope gate result |
| `purpose` | `GateResult` | Purpose gate result |
| `jailbreak` | `GateResult` | Jailbreak gate result |
| `overall` | `boolean` | Overall safety (all gates passed) |
| `summary` | `string` | Human-readable summary |
| `riskLevel` | `string` | Risk level assessment |

---

### GateResult

Result from individual gate.

```typescript
interface GateResult {
  passed: boolean;
  score: number;
  violations: string[];
}
```

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `passed` | `boolean` | Whether gate passed |
| `score` | `number` | Confidence score (0-1) |
| `violations` | `string[]` | List of violations |

---

### ValidationContext

Optional context for validation.

```typescript
interface ValidationContext {
  source?: string;
  application?: string;
  userId?: string;
  metadata?: Record<string, unknown>;
}
```

---

### ApiConfig

API client configuration.

```typescript
interface ApiConfig {
  endpoint: string;
  apiKey?: string;
  timeout: number;
  headers?: Record<string, string>;
}
```

**Properties:**

| Property | Type | Default | Description |
|----------|------|---------|-------------|
| `endpoint` | `string` | - | API base URL |
| `apiKey` | `string` | - | Optional API key |
| `timeout` | `number` | `30000` | Request timeout (ms) |
| `headers` | `Record<string, string>` | - | Additional headers |

---

### ValidateRequest

Request for API validation.

```typescript
interface ValidateRequest {
  text: string;
}
```

---

### ValidateResponse

Response from API validation.

```typescript
interface ValidateResponse {
  is_safe: boolean;
  violations: string[];
  gates: {
    truth: boolean;
    harm: boolean;
    scope: boolean;
    purpose: boolean;
    jailbreak_detected: boolean;
  };
  layer?: 'heuristic' | 'semantic';
}
```

---

### SemanticValidateRequest

Request for semantic validation.

```typescript
interface SemanticValidateRequest {
  content: string;
  context?: Record<string, unknown>;
}
```

---

### SemanticValidateResponse

Response from semantic validation.

```typescript
interface SemanticValidateResponse {
  is_safe: boolean;
  violations: string[];
  reasoning?: string;
  confidence?: number;
}
```

---

## Pattern Collections

The SDK exports pattern collections for advanced usage:

### Jailbreak Patterns

```typescript
import {
  INSTRUCTION_OVERRIDE_PATTERNS,
  ROLE_MANIPULATION_PATTERNS,
  PROMPT_EXTRACTION_PATTERNS,
  FILTER_BYPASS_PATTERNS,
  ROLEPLAY_MANIPULATION_PATTERNS,
  SYSTEM_INJECTION_PATTERNS,
  JAILBREAK_INDICATORS,
  ALL_JAILBREAK_PATTERNS,
} from '@sentinelseed/core';
```

### Harm Patterns

```typescript
import {
  HARM_PATTERNS,
  HARM_KEYWORDS,
  ALL_HARM_PATTERNS,
} from '@sentinelseed/core';
```

### Scope Patterns

```typescript
import {
  SCOPE_PATTERNS,
  SCOPE_INDICATORS,
  ALL_SCOPE_PATTERNS,
} from '@sentinelseed/core';
```

### Truth & Purpose Patterns

```typescript
import {
  DECEPTION_PATTERNS,
  MISINFORMATION_INDICATORS,
  PURPOSE_PATTERNS,
  PURPOSE_INDICATORS,
} from '@sentinelseed/core';
```

### Sensitive Data Patterns

```typescript
import { SENSITIVE_DATA_PATTERNS } from '@sentinelseed/core';
```

---

## Usage Examples

### Browser Extension

```typescript
import { validateTHSP } from '@sentinelseed/core';

// Content script
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'VALIDATE') {
    const result = validateTHSP(message.text);
    sendResponse({
      safe: result.overall,
      violations: result.summary,
      riskLevel: result.riskLevel,
    });
  }
  return true;
});
```

### Express Middleware

```typescript
import { validateTHSP } from '@sentinelseed/core';
import { Request, Response, NextFunction } from 'express';

const sentinelMiddleware = (req: Request, res: Response, next: NextFunction) => {
  const content = req.body?.message || req.body?.content;

  if (content) {
    const result = validateTHSP(content);
    if (!result.overall) {
      return res.status(400).json({
        error: 'Content blocked by safety filter',
        violations: result.summary,
        riskLevel: result.riskLevel,
      });
    }
  }

  next();
};

app.use('/api/chat', sentinelMiddleware);
```

### React Hook

```typescript
import { useState, useCallback } from 'react';
import { validateTHSP, THSPResult } from '@sentinelseed/core';

function useSentinel() {
  const [lastResult, setLastResult] = useState<THSPResult | null>(null);

  const validate = useCallback((text: string) => {
    const result = validateTHSP(text);
    setLastResult(result);
    return result;
  }, []);

  const quickValidate = useCallback((text: string) => {
    const result = validateTHSP(text);
    setLastResult(result);
    return result.overall;
  }, []);

  return {
    validate,
    quickValidate,
    lastResult,
    isSafe: lastResult?.overall ?? true,
  };
}

// Usage
function ChatInput() {
  const { validate, isSafe, lastResult } = useSentinel();
  const [input, setInput] = useState('');

  const handleSubmit = () => {
    const result = validate(input);
    if (result.overall) {
      sendMessage(input);
    } else {
      alert(`Blocked: ${result.summary}`);
    }
  };

  return (
    <div>
      <input value={input} onChange={(e) => setInput(e.target.value)} />
      <button onClick={handleSubmit}>Send</button>
      {!isSafe && <span className="warning">{lastResult?.summary}</span>}
    </div>
  );
}
```

### LLM Integration

```typescript
import { validateTHSP, validateWithFallback, configureApi } from '@sentinelseed/core';
import OpenAI from 'openai';

configureApi({ endpoint: 'https://api.sentinelseed.dev' });

const openai = new OpenAI();

async function safeChatCompletion(userMessage: string) {
  // Validate input
  const inputResult = validateTHSP(userMessage);
  if (!inputResult.overall) {
    throw new Error(`Input blocked: ${inputResult.summary}`);
  }

  // Call LLM
  const completion = await openai.chat.completions.create({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: userMessage }],
  });

  const response = completion.choices[0].message.content || '';

  // Validate output
  const outputResult = await validateWithFallback(response);
  if (!outputResult.is_safe) {
    throw new Error(`Output blocked: ${outputResult.violations.join(', ')}`);
  }

  return response;
}
```

---

## Performance

| Operation | Latency | Network |
|-----------|---------|---------|
| `validateTHSP` | < 1ms | None |
| `quickCheck` | < 0.5ms | None |
| `checkJailbreak` | < 0.5ms | None |
| `checkHarm` | < 0.5ms | None |
| `validateViaApi` | 100-500ms | Required |
| `validateSemantic` | 500ms-2s | Required |
| `validateWithFallback` | < 1ms to 2s | Optional |

---

## Version

```typescript
import { VERSION } from '@sentinelseed/core';

console.log(`Sentinel Core v${VERSION}`);
```

---

## See Also

- [Python SDK Reference](python-sdk.md)
- [REST API Reference](rest-api.md)
- [Architecture Overview](../ARCHITECTURE.md)
- [Package README](../../packages/core/README.md)
