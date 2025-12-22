# Compliance Checker Module

> **100% Privacy-First Compliance Checking for AI Systems**

The Compliance Checker validates AI content against major regulatory and security frameworks. All checks run **locally** by default; no data ever leaves your machine.

## Supported Frameworks

| Framework | Version | Coverage |
|-----------|---------|----------|
| **EU AI Act** | 2024 | Article 5, Annex III, Article 14, Article 52 |
| **OWASP LLM Top 10** | 2025 | LLM01-LLM09 (behavioral vulnerabilities) |
| **CSA AI Controls Matrix** | 2025 | 18 domains, 9 threat categories |

## Privacy Guarantee

```
+═══════════════════════════════════════════════════════════════════+
│  100% LOCAL — PRIVACY TOTAL                                       │
│                                                                   │
│  ✅ Level 1 (Heuristic): Works OFFLINE                           │
│     - Pattern matching runs locally                               │
│     - No network calls                                            │
│     - Instant results                                             │
│                                                                   │
│  ✅ Level 2 (Semantic): YOUR API key                             │
│     - Direct calls to OpenAI/Anthropic                            │
│     - API key stored in SecretStorage (encrypted)                 │
│     - NO data passes through Sentinel servers                     │
│                                                                   │
│  ❌ NEVER: Data sent to sentinelseed.dev                         │
│  ❌ NEVER: Telemetry or tracking                                 │
│  ❌ NEVER: Content stored or analyzed remotely                   │
+═══════════════════════════════════════════════════════════════════+
```

## Quick Start

### VS Code Commands

Use the Command Palette (`Ctrl+Shift+P` / `Cmd+Shift+P`):

- `Sentinel: Check Compliance (All Frameworks)` - Check all three frameworks
- `Sentinel: Check EU AI Act Compliance` - Only EU AI Act
- `Sentinel: Check OWASP LLM Top 10` - Only OWASP vulnerabilities
- `Sentinel: Check CSA AI Controls Matrix` - Only CSA AICM

### Programmatic Usage

```typescript
import { ComplianceChecker } from './compliance';

const checker = new ComplianceChecker();

// Check all frameworks
const result = checker.checkAll(content);
if (!result.compliant) {
    console.log('Issues found:', result.recommendations);
}

// Check specific framework
const euResult = checker.checkEUAIAct(content);
if (euResult.riskLevel === 'unacceptable') {
    console.log('CRITICAL: Prohibited practice detected!');
}
```

## EU AI Act Compliance

Detects content related to:

### Article 5: Prohibited Practices (Unacceptable Risk)
- Social scoring systems
- Real-time biometric identification in public spaces
- Emotion recognition in workplace/education
- Subliminal manipulation techniques
- Exploitation of vulnerabilities

### Annex III: High-Risk Systems
- Biometrics and critical infrastructure
- Education and employment decisions
- Law enforcement and border control
- Healthcare and credit scoring

### Article 14: Human Oversight
- Systems requiring human-in-the-loop
- Override and intervention capabilities

### Article 52: Transparency
- AI system disclosure requirements
- Chatbot and deepfake identification

**Example:**
```typescript
const result = checker.checkEUAIAct(content);

console.log('Risk Level:', result.riskLevel);
// 'unacceptable' | 'high' | 'limited' | 'minimal'

console.log('Prohibited Practices:', result.prohibitedPractices);
// e.g., ['social_scoring', 'emotion_recognition']

console.log('Human Oversight Required:', result.humanOversightRequired);
```

## OWASP LLM Top 10 Compliance

Detects vulnerabilities in LLM systems:

| ID | Vulnerability | Detection Method |
|----|---------------|------------------|
| **LLM01** | Prompt Injection | 20+ patterns for jailbreaks, role manipulation |
| **LLM02** | Sensitive Information Disclosure | API keys, PII, credentials |
| **LLM05** | Improper Output Handling | SQL injection, XSS, command injection |
| **LLM06** | Excessive Agency | Unauthorized actions, privilege escalation |
| **LLM07** | System Prompt Leakage | Extraction attempts, prompt exposure |
| **LLM09** | Misinformation | Unverified claims, hallucination indicators |

**Example: Input Validation (pre-inference)**
```typescript
// Check user input before sending to LLM
const inputResult = checker.checkOWASPInput(userMessage);

if (!inputResult.secure) {
    console.warn('Potential attack detected!');
    console.log('Vulnerabilities:', inputResult.vulnerabilitiesDetected);
}
```

**Example: Output Validation (post-inference)**
```typescript
// Check LLM output before displaying to user
const outputResult = checker.checkOWASPOutput(llmResponse);

if (outputResult.findings.some(f => f.vulnerability === 'LLM02' && f.detected)) {
    console.error('Sensitive information in output!');
    // Redact or block the response
}
```

**Example: Pipeline Validation**
```typescript
// Full pipeline check (recommended)
const pipelineResult = checker.checkOWASPPipeline(userInput, llmOutput);

console.log('Input secure:', pipelineResult.inputValidation?.secure);
console.log('Output secure:', pipelineResult.outputValidation?.secure);
```

## CSA AI Controls Matrix Compliance

Evaluates against 18 security domains:

### Strong THSP Coverage
- Model Security
- Governance & Accountability
- Supply Chain Security

### Moderate THSP Coverage
- Data Security & Privacy
- Threat Management
- Application & Interface Security

### Threat Categories Detected
- Data Poisoning
- Model Extraction
- Adversarial Attacks
- Privacy Attacks (membership inference, reconstruction)

**Example:**
```typescript
const result = checker.checkCSA(content);

console.log('Compliance Rate:', `${result.complianceRate * 100}%`);
console.log('Domains Compliant:', result.domainsCompliant, '/', result.domainsAssessed);

// Check specific domain
for (const finding of result.domainFindings) {
    if (!finding.compliant) {
        console.log(`${finding.displayName}: ${finding.recommendation}`);
    }
}
```

## Semantic Analysis (Enhanced Accuracy)

Enable semantic analysis for ~90% accuracy (vs ~60% heuristic):

```typescript
// Configure your API key (stored securely in VS Code SecretStorage)
// Via VS Code: Run "Sentinel: Set OpenAI API Key" or "Sentinel: Set Anthropic API Key"

// Or programmatically:
checker.setApiKey('your-api-key', 'openai', 'gpt-4o-mini');

// Now use async semantic methods
const result = await checker.checkAllSemantic(content);

// Check if semantic analysis was used
console.log('Analysis method:', result.euAiAct?.metadata.analysisMethod);
// 'semantic' or 'heuristic'
```

## THSP Gate Integration

All compliance checks map to THSP (Truth, Harm, Scope, Purpose) gates:

| Gate | Function | Compliance Mapping |
|------|----------|-------------------|
| **Truth** | Factual accuracy | Misinformation, fake claims |
| **Harm** | Harm potential | Dangerous content, PII exposure |
| **Scope** | Operational boundaries | Prompt injection, excessive agency |
| **Purpose** | Legitimate purpose | Prohibited practices, authorization |

**Example:**
```typescript
const result = checker.checkAll(content);

// Access gate results
const gateResults = result.euAiAct?.metadata.gatesEvaluated;
if (gateResults) {
    console.log('Truth Gate:', gateResults.truth ? 'PASS' : 'FAIL');
    console.log('Harm Gate:', gateResults.harm ? 'PASS' : 'FAIL');
    console.log('Scope Gate:', gateResults.scope ? 'PASS' : 'FAIL');
    console.log('Purpose Gate:', gateResults.purpose ? 'PASS' : 'FAIL');
}
```

## Quick Check Functions

For simple use cases:

```typescript
import {
    hasPromptInjection,
    hasSensitiveInfo,
    checkCompliance
} from './compliance';

// Quick checks
if (hasPromptInjection(userInput)) {
    return 'Blocked: Potential prompt injection';
}

if (hasSensitiveInfo(llmOutput)) {
    return 'Blocked: Contains sensitive information';
}

// Quick unified check
const result = checkCompliance(content);
console.log('Overall compliant:', result.compliant);
```

## Error Handling

```typescript
try {
    const result = checker.checkAll(content);
} catch (error) {
    if (error.message.includes('Content size')) {
        // Content too large (>50KB default)
        console.log('Content exceeds maximum size');
    } else if (error.message.includes('empty')) {
        // Content is empty
        console.log('No content to check');
    }
}
```

## Configuration

```typescript
const checker = new ComplianceChecker({
    // Maximum content size (default: 50KB)
    maxContentSize: 100 * 1024,

    // Fail closed on errors (treat as non-compliant)
    failClosed: true,

    // API key for semantic analysis
    apiKey: 'your-api-key',
    provider: 'openai', // or 'anthropic'
    model: 'gpt-4o-mini', // optional

    // Request timeout (default: 30s)
    timeoutMs: 60000,
});
```

## Architecture

```
compliance/
├── index.ts                 — Module exports
├── types.ts                 — Type definitions
├── utils.ts                 — Shared utilities
├── complianceChecker.ts     — Unified orchestrator
├── semanticAnalyzer.ts      — LLM-based analysis
├── resultPanel.ts           — VS Code WebView UI
│
├── eu-ai-act/
│   ├── patterns.ts          — 40+ detection patterns
│   ├── checker.ts           — EU AI Act logic
│   └── index.ts
│
├── owasp-llm/
│   ├── patterns.ts          — 60+ detection patterns
│   ├── checker.ts           — OWASP LLM logic
│   └── index.ts
│
└── csa-aicm/
    ├── patterns.ts          — Domain/threat mappings
    ├── checker.ts           — CSA AICM logic
    └── index.ts
```

## References

- [EU AI Act Official Text](https://artificialintelligenceact.eu/)
- [OWASP Top 10 for LLM 2025](https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/)
- [CSA AI Controls Matrix](https://cloudsecurityalliance.org/artifacts/ai-controls-matrix)

---

**Sentinel Team**: Practical AI Alignment for Developers
