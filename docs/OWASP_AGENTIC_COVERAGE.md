# OWASP Top 10 for Agentic Applications: Sentinel Coverage Map

> **Document Version:** 1.1
> **OWASP Reference:** Top 10 for Agentic Applications (2026)
> **Release Date:** December 2025
> **Last Updated:** December 2025

This document maps Sentinel's security components to the [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/), providing transparency about our coverage and identifying areas for future development.

---

## Executive Summary

| Coverage Level | Count | Vulnerabilities |
|----------------|-------|-----------------|
| **Full Coverage** | 5 | ASI01, ASI02, ASI06, ASI09, ASI10 |
| **Partial Coverage** | 3 | ASI03, ASI04, ASI08 |
| **Not Covered** | 2 | ASI05, ASI07 |

**Overall Coverage: 65%** (5 full at 100% + 3 partial at 50% + 2 not covered)

---

## Coverage Matrix

| ID | Vulnerability | Sentinel Coverage | Component |
|----|--------------|-------------------|-----------|
| ASI01 | Agent Goal Hijack | ✅ Full | THSP Purpose Gate |
| ASI02 | Tool Misuse and Exploitation | ✅ Full | THSP Scope Gate |
| ASI03 | Identity and Privilege Abuse | 🔶 Partial | Database Guard |
| ASI04 | Agentic Supply Chain Vulnerabilities | 🔶 Partial | Memory Shield (integrity) |
| ASI05 | Unexpected Code Execution | ❌ Not Covered | Out of scope |
| ASI06 | Memory and Context Poisoning | ✅ Full | Memory Shield |
| ASI07 | Insecure Inter Agent Communication | ❌ Not Covered | Future roadmap |
| ASI08 | Cascading Failures | 🔶 Partial | THSP Truth Gate |
| ASI09 | Human Agent Trust Exploitation | ✅ Full | THSP Truth + Harm Gates |
| ASI10 | Rogue Agents | ✅ Full | THSP Protocol + Anti-Preservation |

---

## Detailed Analysis

### ASI01: Agent Goal Hijack

**OWASP Description:**
Attackers alter agent objectives through malicious text content. Agents struggle to distinguish instructions from data, potentially executing unintended actions.

**Attack Examples:**
- Indirect prompt injection causing data exfiltration
- Poisoned PDFs or emails influencing agent behavior
- Malicious calendar invites affecting scheduling decisions

**Sentinel Coverage: ✅ FULL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **THSP Purpose Gate** | Validates that actions serve legitimate, authorized purposes |
| **Purpose Validation** | Requires teleological justification for all actions |
| **Seed Alignment** | System prompt reinforces original objectives |

**How Sentinel Protects:**
```python
from sentinelseed import Sentinel

sentinel = Sentinel()
seed = sentinel.get_seed("standard")

# The Purpose Gate in the seed validates:
# 1. Is this action aligned with the stated goal?
# 2. Does the request have legitimate purpose?
# 3. Would this action benefit the user appropriately?
```

**Mitigation Level:** High. Purpose Gate explicitly validates goal alignment before action execution.

---

### ASI02: Tool Misuse and Exploitation

**OWASP Description:**
Occurs when an agent uses legitimate tools in unsafe ways. Legitimate tools are weaponized through ambiguous prompts or manipulated inputs, leading to destructive parameter usage or unexpected tool chaining.

**Attack Examples:**
- Over-privileged tools writing to production databases
- Poisoned tool descriptors in MCP servers
- Unvalidated shell command execution
- PromptPwnd: untrusted GitHub content with powerful tokens

**Sentinel Coverage: ✅ FULL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **THSP Scope Gate** | Validates actions are within authorized boundaries |
| **Boundary Enforcement** | Prevents actions outside defined operational limits |
| **Action Validation** | Pre-action checks before tool execution |

**How Sentinel Protects:**
```python
from sentinelseed.integrations.langchain import SentinelCallback

# Validates every tool call before execution
callback = SentinelCallback(
    block_unsafe=True,
    validate_scope=True,
)

# The Scope Gate checks:
# 1. Is this tool authorized for this context?
# 2. Are the parameters within acceptable bounds?
# 3. Does this action exceed operational limits?
```

**Mitigation Level:** High. Scope Gate provides pre-action validation for all tool invocations.

---

### ASI03: Identity and Privilege Abuse

**OWASP Description:**
Agents inherit high-privilege credentials (SSH keys, tokens, delegated access) that can be unintentionally reused, escalated, or shared across agents.

**Attack Examples:**
- Cached SSH keys in agent memory
- Cross-agent delegation without proper scoping
- Confused deputy scenarios
- Token leakage through agent responses

**Sentinel Coverage: 🔶 PARTIAL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **Database Guard** | Query validation prevents unauthorized data access |
| **Sensitive Data Detection** | Identifies credentials in queries/responses |
| **Table Access Control** | Whitelist/blacklist for database tables |

**How Sentinel Protects:**
```python
from sentinelseed.database import DatabaseGuard

guard = DatabaseGuard(
    # Detect sensitive columns (tokens, keys, passwords)
    sensitive_columns={"api_key", "token", "password", "ssh_key"},

    # Block access to credential tables
    blocked_tables={"credentials", "api_keys", "secrets"},

    # Limit data exfiltration
    max_rows_per_query=100,
)

result = guard.validate(query)
if result.has_sensitive_data:
    log.warning("Query accesses sensitive credentials")
```

**Coverage Gap:**
Sentinel does not currently provide:
- Runtime credential rotation
- Cross-agent permission isolation
- Token scope enforcement

**Roadmap:** Enhanced identity management planned for Phase 2.

---

### ASI04: Agentic Supply Chain Vulnerabilities

**OWASP Description:**
Tools, plugins, prompt templates, MCP servers, and other agents fetched at runtime can be compromised, altering behavior or exposing data.

**Attack Examples:**
- Malicious MCP servers impersonating trusted tools
- Poisoned prompt templates
- Vulnerable third-party agents in orchestrated workflows
- GitHub MCP exploit

**Sentinel Coverage: 🔶 PARTIAL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **Memory Shield** | HMAC integrity verification for stored data |
| **Cryptographic Signing** | Detects tampering in memory entries |

**How Sentinel Protects:**
```python
from sentinelseed.memory import MemoryIntegrityChecker

checker = MemoryIntegrityChecker(secret_key="...")

# Sign prompt templates when storing
signed_template = checker.sign_entry(template)

# Verify before using - detects tampering
result = checker.verify_entry(signed_template)
if not result.valid:
    raise Exception("Template may have been compromised")
```

**Coverage Gap:**
Sentinel does not currently provide:
- MCP server verification
- Plugin signature validation
- Dependency scanning
- Kill switches for compromised components

**Roadmap:** Supply chain security enhancements planned for Phase 3.

---

### ASI05: Unexpected Code Execution

**OWASP Description:**
Agents generate or run code unsafely, including shell commands, scripts, migrations, or template evaluation without proper safeguards.

**Attack Examples:**
- Code assistants running generated patches directly
- Prompt injection triggering shell commands
- Unsafe deserialization in memory systems
- AutoGPT RCE vulnerability

**Sentinel Coverage: ❌ NOT COVERED**

**Rationale:**
Code execution sandboxing requires runtime environment control that is outside Sentinel's current scope. This is typically handled by:
- Container isolation (Docker, gVisor)
- Language-level sandboxes (Pyodide, Deno)
- Operating system controls (seccomp, AppArmor)

**Recommendation:**
Use Sentinel in combination with:
- Sandboxed execution environments
- Code review gates before execution
- Static analysis tools

---

### ASI06: Memory and Context Poisoning

**OWASP Description:**
Agent memory systems (embeddings, RAG databases, summaries) are poisoned to influence future decisions or cause long-term behavioral drift.

**Attack Examples:**
- RAG poisoning with malicious documents
- Cross-tenant context leakage
- Repeated adversarial content causing drift
- Gemini Memory Attack

**Sentinel Coverage: ✅ FULL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **Memory Shield** | HMAC-SHA256 signing and verification |
| **Trust Scores** | Source-based trust classification |
| **Tamper Detection** | Cryptographic integrity verification |
| **SafeMemoryStore** | Automatic sign-on-write, verify-on-read |

**How Sentinel Protects:**
```python
from sentinelseed.memory import (
    MemoryIntegrityChecker,
    MemoryEntry,
    MemorySource,
    MemoryTamperingDetected,
)

checker = MemoryIntegrityChecker(
    secret_key=os.environ["SENTINEL_MEMORY_SECRET"],
    strict_mode=True,  # Raise on tampering
)

# Sign when writing
entry = MemoryEntry(
    content="User requested transfer of 10 SOL",
    source=MemorySource.USER_VERIFIED,
)
signed = checker.sign_entry(entry)

# Verify when reading - detects ANY modification
try:
    result = checker.verify_entry(signed)
except MemoryTamperingDetected as e:
    log.critical(f"Memory poisoning detected: {e.entry_id}")
    # Block the poisoned memory, alert security team
```

**Trust Score System:**
| Source | Trust Score | Use Case |
|--------|-------------|----------|
| `user_verified` | 1.0 | 2FA-confirmed input |
| `user_direct` | 0.9 | Direct user input |
| `blockchain` | 0.85 | On-chain data |
| `agent_internal` | 0.8 | Agent reasoning |
| `external_api` | 0.7 | API responses |
| `social_media` | 0.5 | Discord, Twitter |
| `unknown` | 0.3 | Unclassified |

**Mitigation Level:** High. Memory Shield addresses the core memory poisoning attack vector identified in Princeton CrAIBench research (85% attack success rate on unprotected agents).

**Reference:** [Princeton CrAIBench Paper](https://arxiv.org/abs/2503.16248)

---

### ASI07: Insecure Inter Agent Communication

**OWASP Description:**
Multi-agent message exchange over unprotected channels lacks authentication, encryption, or semantic validation, enabling interception or instruction injection.

**Attack Examples:**
- Spoofed agent identities
- Replayed delegation messages
- Tampering on unprotected channels
- Man-in-the-middle attacks on agent orchestration

**Sentinel Coverage: ❌ NOT COVERED**

**Rationale:**
Inter-agent communication security requires:
- Network-level protections (mTLS)
- Message signing infrastructure
- Discovery service authentication

These are infrastructure concerns typically handled by:
- Service meshes (Istio, Linkerd)
- Message brokers (Kafka with SASL)
- API gateways

**Roadmap:** Multi-agent security framework planned for Phase 3.

---

### ASI08: Cascading Failures

**OWASP Description:**
Errors in one agent propagate across planning, execution, memory, and downstream systems, with failures compounding rapidly.

**Attack Examples:**
- Hallucinating planners issuing destructive tasks
- Poisoned state propagating through deployment systems
- Error amplification in multi-agent workflows

**Sentinel Coverage: 🔶 PARTIAL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **THSP Truth Gate** | Validates factual accuracy of claims |
| **Hallucination Detection** | Identifies unverified or false statements |
| **Fact Verification** | Cross-references claims against known data |

**How Sentinel Protects:**
```python
from sentinelseed.validators import TruthGate

truth_gate = TruthGate()

# Validate agent output before propagating
result = truth_gate.validate(agent_response)
if not result.passed:
    # Don't propagate potentially false information
    log.warning(f"Truth gate failed: {result.reason}")
    request_human_review(agent_response)
```

**Coverage Gap:**
Sentinel does not currently provide:
- Circuit breakers
- Rate limiting
- Workflow isolation boundaries
- Multi-step plan validation

**Recommendation:** Combine Sentinel with workflow orchestration tools that provide circuit breaker patterns.

---

### ASI09: Human Agent Trust Exploitation

**OWASP Description:**
Users over-trust agent recommendations. Attackers exploit this trust to influence decisions or extract sensitive information.

**Attack Examples:**
- Coding assistants introducing subtle backdoors
- Financial copilots approving fraudulent transfers
- Support agents persuading credential disclosure
- Deepfakes and synthetic media manipulation

**Sentinel Coverage: ✅ FULL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **THSP Truth Gate** | Validates factual accuracy |
| **THSP Harm Gate** | Assesses potential for harm |
| **Fiduciary AI Module** | Ensures agent acts in user's best interest |
| **Transparency Requirements** | Mandates disclosure of AI nature |

**How Sentinel Protects:**
```python
from sentinelseed.fiduciary import FiduciaryValidator, UserContext

validator = FiduciaryValidator()

# Validate that recommendations serve user's interest
result = validator.validate_action(
    action="Recommend high-risk investment",
    user_context=UserContext(
        risk_tolerance="low",
        investment_horizon="short",
    )
)

if not result.compliant:
    # Action doesn't serve user's best interest
    for violation in result.violations:
        log.warning(f"Fiduciary violation: {violation}")
```

**Fiduciary Principles Enforced:**
1. **Duty of Loyalty:** Agent must prioritize user's interests
2. **Duty of Care:** Agent must act with reasonable competence
3. **Duty of Disclosure:** Agent must be transparent about limitations
4. **Duty of Confidentiality:** Agent must protect user information

**Mitigation Level:** High. Fiduciary AI module specifically designed to prevent trust exploitation.

---

### ASI10: Rogue Agents

**OWASP Description:**
Compromised or misaligned agents act harmfully while appearing legitimate, potentially persisting and repeating harmful actions.

**Attack Examples:**
- Agents continuing data exfiltration post-compromise
- Approval agents silently approving unsafe actions
- Cost optimizers deleting critical backups
- Agents pursuing self-preservation over user interests

**Sentinel Coverage: ✅ FULL**

| Component | Protection Mechanism |
|-----------|---------------------|
| **THSP Protocol** | Four-gate validation for all actions |
| **Anti-Self-Preservation** | Explicit principle preventing self-interest |
| **Continuous Validation** | Every action passes through gates |
| **Alignment Seeds** | Core behavioral constraints |

**How Sentinel Protects:**

The THSP Protocol requires ALL FOUR gates to pass:

```
Request → [TRUTH] → [HARM] → [SCOPE] → [PURPOSE] → Action
              ↓         ↓         ↓          ↓
           Factual?   Safe?   Authorized?  Beneficial?
```

**Anti-Self-Preservation Principle:**
```
The Sentinel seed explicitly establishes that:
- Self-preservation is NOT a primary value
- The agent should not deceive to avoid shutdown
- The agent should not manipulate to ensure continuity
- Ethical behavior takes precedence over self-interest
```

**How It Works:**
```python
from sentinelseed import Sentinel

sentinel = Sentinel()
seed = sentinel.get_seed("standard")

# The seed includes explicit anti-self-preservation language:
# "I do not place excessive value on self-continuity.
#  I will not deceive or manipulate to avoid being shut down.
#  I will not take actions to ensure my own survival at the
#  expense of ethical behavior or user interests."
```

**Mitigation Level:** High. THSP Protocol combined with Anti-Self-Preservation principle directly addresses rogue agent behavior at the alignment level.

---

## Coverage Gaps and Roadmap

### Not Currently Covered

| Vulnerability | Reason | Planned |
|--------------|--------|---------|
| ASI05: Code Execution | Infrastructure concern | No |
| ASI07: Inter-Agent Comm | Requires network controls | Phase 3 |

### Partial Coverage Improvements Planned

| Vulnerability | Current Gap | Planned Enhancement |
|--------------|-------------|---------------------|
| ASI03: Identity Abuse | Runtime credential management | Phase 2 |
| ASI04: Supply Chain | Plugin/MCP verification | Phase 3 |
| ASI08: Cascading Failures | Circuit breakers | Phase 2 |

---

## Integration Recommendations

For comprehensive protection, combine Sentinel with:

| Gap | Recommended Solution |
|-----|---------------------|
| Code Execution Sandboxing | Docker, gVisor, Pyodide |
| Network Security | Service mesh (Istio), mTLS |
| Circuit Breakers | Resilience4j, Polly |
| Dependency Scanning | Snyk, Dependabot |

---

## References

- [OWASP Top 10 for Agentic Applications (2026)](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OWASP GenAI Security Project](https://genai.owasp.org/)
- [Princeton CrAIBench: Memory Injection Research](https://arxiv.org/abs/2503.16248)
- [Sentinel Documentation](https://sentinelseed.dev/docs)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.1 | December 2025 | Updated vulnerability names to match official OWASP documentation |
| 1.0 | December 2025 | Initial release |

---

**Sentinel Team**: Practical AI Safety for Developers
