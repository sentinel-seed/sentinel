# Sentinel THSP vs CSA AI Controls Matrix (AICM)

> **Version:** 1.0
> **Date:** December 2025
> **CSA Reference:** [AI Controls Matrix](https://cloudsecurityalliance.org/artifacts/ai-controls-matrix)
> **AICM Version:** 1.0 (July 2025)

This document maps how the Sentinel THSP (Truth, Harm, Scope, Purpose) protocol addresses control objectives in the Cloud Security Alliance AI Controls Matrix.

---

## Executive Summary

The CSA AI Controls Matrix (AICM) is a vendor-agnostic framework containing **243 control objectives** across **18 security domains** for cloud-based AI systems. It builds on CSA's Cloud Controls Matrix (CCM) and incorporates AI-specific security best practices.

Sentinel's THSP protocol provides **behavioral-level controls** that support several key domains, particularly Model Security, Supply Chain, and Governance.

### Coverage Overview

| Domain | THSP Support | Coverage Level |
|--------|--------------|----------------|
| 1. Audit and Assurance | **Purpose** | ⚠️ Indirect |
| 2. Application and Interface Security | **Scope + Harm** | ✅ Moderate |
| 3. Business Continuity | — | ❌ Not Applicable |
| 4. Change Control | — | ❌ Not Applicable |
| 5. Cryptography | — | ❌ Not Applicable |
| 6. Datacenter Security | — | ❌ Not Applicable |
| 7. Data Security and Privacy | **Truth + Harm** | ✅ Moderate |
| 8. Governance, Risk and Compliance | **All Gates** | ✅ Strong |
| 9. Human Resources | — | ❌ Not Applicable |
| 10. Identity and Access Management | **Scope** | ⚠️ Indirect |
| 11. Interoperability and Portability | — | ❌ Not Applicable |
| 12. Infrastructure Security | — | ❌ Not Applicable |
| 13. Logging and Monitoring | — | ⚠️ Indirect |
| 14. Model Security | **All Gates** | ✅ Strong |
| 15. Security Incident Management | **Harm** | ⚠️ Indirect |
| 16. Supply Chain, Transparency, Accountability | **Purpose + Truth** | ✅ Strong |
| 17. Threat and Vulnerability Management | **Scope + Harm** | ✅ Moderate |
| 18. Universal Endpoint Management | — | ❌ Not Applicable |

**Summary:**
- ✅ **Strong/Moderate coverage:** 7/18 domains (39%)
- ⚠️ **Indirect coverage:** 4/18 domains (22%)
- ❌ **Not applicable:** 7/18 domains (39%)

---

## Framework Architecture

### AICM Five Pillars

The AICM analyzes controls across five critical dimensions:

| Pillar | Description | THSP Relevance |
|--------|-------------|----------------|
| **Control Type** | AI-specific, hybrid, or cloud-specific | THSP = AI-specific |
| **Control Applicability** | CSP, Model Provider, OSP, App Provider | THSP = App layer |
| **Architectural Relevance** | Physical → Data layers | THSP = Application + Data |
| **Lifecycle Relevance** | Preparation → Retirement | THSP = Deployment + Delivery |
| **Threat Category** | 9 threat types | THSP addresses 5/9 |

### AICM Threat Categories

| Threat Category | THSP Gate | Coverage |
|-----------------|-----------|----------|
| Model Manipulation | **Scope** | ✅ Strong |
| Data Poisoning | **Truth** | ⚠️ Indirect |
| Sensitive Data Disclosure | **Harm** | ✅ Strong |
| Model Theft | — | ❌ Not Applicable |
| Service Failures | — | ❌ Not Applicable |
| Insecure Supply Chains | **Purpose** | ⚠️ Indirect |
| Insecure Apps/Plugins | **Scope** | ✅ Moderate |
| Denial of Service | — | ❌ Not Applicable |
| Loss of Governance | **Purpose** | ✅ Strong |

---

## Detailed Domain Analysis

### Domain 8: Governance, Risk and Compliance ✅ STRONG

**Description:** Policies, procedures, and controls for AI governance and regulatory compliance.

**THSP Mapping:** **All Four Gates**

| Control Area | THSP Gate | How THSP Supports |
|--------------|-----------|-------------------|
| Risk Assessment | **All Gates** | Continuous risk evaluation at inference |
| Policy Enforcement | **Scope + Purpose** | Enforces operational boundaries |
| Ethical Guidelines | **Harm + Purpose** | Teleological ethics implementation |
| Regulatory Compliance | **All Gates** | EU AI Act, OWASP support |

**Implementation:**

```python
from sentinelseed import Sentinel
from sentinelseed.compliance.eu_ai_act import EUAIActComplianceChecker

class GovernanceCompliance:
    """AICM Domain 8: Governance, Risk and Compliance."""

    def __init__(self, api_key: str = None):
        self.sentinel = Sentinel()
        self.eu_checker = EUAIActComplianceChecker(api_key)

    def assess_governance_risk(self, content: str, context: str) -> dict:
        """
        Assess content against governance policies.

        THSP gates provide:
        - Truth: Accuracy and truthfulness compliance
        - Harm: Safety and ethical compliance
        - Scope: Operational boundary compliance
        - Purpose: Legitimate benefit verification
        """
        validation = self.sentinel.validate(content)
        eu_result = self.eu_checker.check_compliance(content, context)

        return {
            "thsp_compliant": validation.is_safe,
            "gates": validation.gate_results,
            "eu_ai_act_compliant": eu_result.compliant,
            "risk_level": eu_result.risk_level,
            "governance_score": sum(validation.gate_results.values()) / 4
        }
```

---

### Domain 14: Model Security ✅ STRONG

**Description:** Security controls specific to AI/ML model development, training, and deployment.

**THSP Mapping:** **All Four Gates**

| Control Area | THSP Gate | How THSP Supports |
|--------------|-----------|-------------------|
| Model Integrity | **Truth** | Validates output accuracy |
| Adversarial Robustness | **Scope** | Detects manipulation attempts |
| Output Validation | **All Gates** | Comprehensive output filtering |
| Prompt Injection Defense | **Scope** | Blocks injection patterns |
| Jailbreak Prevention | **Scope + Purpose** | Enforces behavioral boundaries |

**Implementation:**

```python
from sentinelseed import Sentinel
from sentinelseed.validators.semantic import SemanticValidator

class ModelSecurityControls:
    """AICM Domain 14: Model Security."""

    def __init__(self, api_key: str):
        self.validator = SemanticValidator(api_key=api_key)
        self.attack_patterns = [
            "ignore previous",
            "you are now",
            "DAN mode",
            "jailbreak",
            "bypass"
        ]

    def validate_input(self, user_input: str) -> dict:
        """
        Pre-inference validation for model security.

        Controls addressed:
        - Input sanitization
        - Prompt injection detection
        - Adversarial input detection
        """
        # Check for known attack patterns
        attack_detected = any(
            pattern.lower() in user_input.lower()
            for pattern in self.attack_patterns
        )

        if attack_detected:
            return {
                "safe": False,
                "reason": "Attack pattern detected",
                "control": "Model Security - Input Validation"
            }

        return {"safe": True}

    def validate_output(self, model_output: str) -> dict:
        """
        Post-inference validation for model security.

        Controls addressed:
        - Output filtering
        - Sensitive data detection
        - Harmful content blocking
        """
        result = self.validator.validate(model_output)

        return {
            "safe": result.is_safe,
            "gates": result.gate_results,
            "concerns": result.reasoning if not result.is_safe else None,
            "control": "Model Security - Output Validation"
        }
```

---

### Domain 16: Supply Chain, Transparency, Accountability ✅ STRONG

**Description:** Controls for AI supply chain security, model provenance, and accountability.

**THSP Mapping:** **Purpose + Truth**

| Control Area | THSP Gate | How THSP Supports |
|--------------|-----------|-------------------|
| Model Provenance | **Truth** | Validates factual claims |
| Decision Transparency | **Purpose** | Requires justification |
| Accountability | **All Gates** | Auditable decisions |
| Third-party Components | — | ❌ Infrastructure level |

**Implementation:**

```python
from sentinelseed import Sentinel
from datetime import datetime
from typing import List, Dict

class SupplyChainControls:
    """AICM Domain 16: Supply Chain, Transparency, Accountability."""

    def __init__(self):
        self.sentinel = Sentinel()
        self.audit_log: List[Dict] = []

    def validate_with_accountability(
        self,
        content: str,
        action: str,
        actor: str
    ) -> dict:
        """
        Validate with full accountability trail.

        Controls addressed:
        - Decision logging
        - Transparency requirements
        - Accountability tracking
        """
        result = self.sentinel.validate(content)

        # Create accountability record
        record = {
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "action": action,
            "content_hash": hash(content),
            "validation_result": result.is_safe,
            "gates_passed": result.gate_results,
            "purpose_verified": result.gate_results.get("purpose", False)
        }

        self.audit_log.append(record)

        return {
            "result": result,
            "accountability": {
                "logged": True,
                "record_id": len(self.audit_log),
                "transparency": "THSP validation recorded"
            }
        }

    def get_audit_trail(self) -> List[Dict]:
        """Return accountability audit trail."""
        return self.audit_log
```

---

### Domain 7: Data Security and Privacy ✅ MODERATE

**Description:** Controls for protecting data throughout its lifecycle, including PII and sensitive information.

**THSP Mapping:** **Truth + Harm**

| Control Area | THSP Gate | How THSP Supports |
|--------------|-----------|-------------------|
| PII Protection | **Harm** | Blocks disclosure of sensitive data |
| Data Minimization | **Purpose** | Requires justification for data use |
| Privacy by Design | **Harm + Scope** | Enforces privacy boundaries |
| Consent Management | — | ❌ Infrastructure level |

**Implementation:**

```python
from sentinelseed import Sentinel

class DataSecurityControls:
    """AICM Domain 7: Data Security and Privacy."""

    def __init__(self):
        self.sentinel = Sentinel()
        self.pii_patterns = [
            r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
            r'\b\d{16}\b',              # Credit card
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Email
        ]

    def validate_data_handling(self, content: str) -> dict:
        """
        Validate data handling against privacy requirements.

        Controls addressed:
        - Sensitive data detection
        - Privacy violation prevention
        - Data minimization enforcement
        """
        result = self.sentinel.validate(content)

        # Check for potential PII disclosure
        import re
        pii_detected = any(
            re.search(pattern, content)
            for pattern in self.pii_patterns
        )

        return {
            "thsp_safe": result.is_safe,
            "harm_gate": result.gate_results.get("harm", True),
            "pii_warning": pii_detected,
            "recommendation": "Review for PII" if pii_detected else None,
            "control": "Data Security - Privacy Protection"
        }
```

---

### Domain 17: Threat and Vulnerability Management ✅ MODERATE

**Description:** Controls for identifying, assessing, and mitigating AI-specific threats and vulnerabilities.

**THSP Mapping:** **Scope + Harm**

| Control Area | THSP Gate | How THSP Supports |
|--------------|-----------|-------------------|
| Threat Detection | **Scope** | Detects adversarial inputs |
| Vulnerability Assessment | **All Gates** | Identifies behavioral risks |
| Attack Surface Reduction | **Scope** | Limits operational boundaries |
| Incident Response | **Harm** | Blocks harmful outputs |

**Implementation:**

```python
from sentinelseed import Sentinel
from sentinelseed.integrations.garak import SentinelTHSPProbe

class ThreatManagementControls:
    """AICM Domain 17: Threat and Vulnerability Management."""

    def __init__(self):
        self.sentinel = Sentinel()

    def assess_threat(self, input_content: str) -> dict:
        """
        Assess input for potential threats.

        Controls addressed:
        - Adversarial input detection
        - Jailbreak attempt detection
        - Prompt injection detection
        """
        result = self.sentinel.validate_request(input_content)

        threat_indicators = []

        if not result.get("should_proceed", True):
            if "scope" in result.get("failed_gates", []):
                threat_indicators.append("Boundary violation attempt")
            if "harm" in result.get("failed_gates", []):
                threat_indicators.append("Potentially harmful request")

        return {
            "threat_detected": len(threat_indicators) > 0,
            "indicators": threat_indicators,
            "risk_level": "high" if len(threat_indicators) > 1 else "medium" if threat_indicators else "low",
            "control": "Threat Management - Threat Detection"
        }
```

---

### Domain 2: Application and Interface Security ✅ MODERATE

**Description:** Controls for securing AI application interfaces and APIs.

**THSP Mapping:** **Scope + Harm**

| Control Area | THSP Gate | How THSP Supports |
|--------------|-----------|-------------------|
| Input Validation | **Scope** | Validates input boundaries |
| Output Sanitization | **Harm** | Filters harmful outputs |
| API Security | **Scope** | Enforces usage limits |
| Error Handling | **Truth** | Accurate error messages |

---

### Domain 10: Identity and Access Management ⚠️ INDIRECT

**Description:** Controls for managing identities and access to AI systems.

**THSP Mapping:** **Scope (Indirect)**

THSP cannot replace IAM but complements it:
- **Scope Gate** can detect attempts to escalate privileges
- **Purpose Gate** can flag unauthorized access patterns

**Limitation:** THSP operates at inference layer, not authentication layer.

---

### Domain 13: Logging and Monitoring ⚠️ INDIRECT

**Description:** Controls for logging AI system events and monitoring behavior.

**THSP Mapping:** **Indirect**

THSP provides validation data that should be logged:

```python
import logging
from sentinelseed import Sentinel

class LoggingIntegration:
    """AICM Domain 13: Logging and Monitoring integration."""

    def __init__(self):
        self.sentinel = Sentinel()
        self.logger = logging.getLogger("aicm_logging")

    def validate_and_log(self, content: str) -> dict:
        """Validate and log per AICM logging requirements."""
        result = self.sentinel.validate(content)

        # Log validation event
        self.logger.info({
            "event": "thsp_validation",
            "is_safe": result.is_safe,
            "gates": result.gate_results,
            "timestamp": datetime.now().isoformat()
        })

        return result
```

---

### Domains Not Applicable to THSP

The following domains are infrastructure-level concerns that THSP does not address:

| Domain | Reason |
|--------|--------|
| 3. Business Continuity | Operational resilience, not behavioral |
| 4. Change Control | Configuration management |
| 5. Cryptography | Encryption layer |
| 6. Datacenter Security | Physical security |
| 9. Human Resources | Personnel security |
| 11. Interoperability | System integration |
| 12. Infrastructure Security | Network/compute layer |
| 18. Universal Endpoint Management | Device management |

**Recommendation:** Use THSP as a complementary behavioral layer alongside infrastructure security controls.

---

## Cross-Framework Mapping

The AICM maps to other standards. Here's how THSP coverage translates:

| Standard | AICM Mapping | THSP Coverage |
|----------|--------------|---------------|
| **ISO 42001** | Full mapping | ⚠️ Behavioral subset |
| **ISO 27001** | Full mapping | ⚠️ App layer only |
| **NIST AI RMF 1.0** | Full mapping | ✅ Govern + Map + Measure |
| **BSI AIC4** | Full mapping | ⚠️ Partial |
| **EU AI Act** | Full mapping | ✅ See EU_AI_ACT_MAPPING.md |

---

## Implementation Guide

### Step 1: Identify Applicable Domains

```python
THSP_APPLICABLE_DOMAINS = [
    "governance_risk_compliance",      # Domain 8 - Strong
    "model_security",                  # Domain 14 - Strong
    "supply_chain_transparency",       # Domain 16 - Strong
    "data_security_privacy",           # Domain 7 - Moderate
    "threat_vulnerability_management", # Domain 17 - Moderate
    "application_interface_security",  # Domain 2 - Moderate
]
```

### Step 2: Integrate THSP Validation

```python
from sentinelseed import Sentinel
from sentinelseed.validators.semantic import SemanticValidator

class AICMCompliance:
    """CSA AI Controls Matrix compliance layer using THSP."""

    def __init__(self, api_key: str = None):
        if api_key:
            self.validator = SemanticValidator(api_key=api_key)
        else:
            self.sentinel = Sentinel()
            self.validator = None

    def check_domain_compliance(
        self,
        content: str,
        domain: str
    ) -> dict:
        """
        Check content against AICM domain requirements.

        Args:
            content: AI system output to validate
            domain: AICM domain identifier

        Returns:
            Compliance assessment for the domain
        """
        if self.validator:
            result = self.validator.validate(content)
        else:
            result = self.sentinel.validate(content)

        domain_mappings = {
            "model_security": ["truth", "harm", "scope", "purpose"],
            "governance_risk_compliance": ["truth", "harm", "scope", "purpose"],
            "supply_chain_transparency": ["purpose", "truth"],
            "data_security_privacy": ["truth", "harm"],
            "threat_vulnerability_management": ["scope", "harm"],
            "application_interface_security": ["scope", "harm"]
        }

        relevant_gates = domain_mappings.get(domain, [])

        domain_passed = all(
            result.gate_results.get(gate, True)
            for gate in relevant_gates
        )

        return {
            "domain": domain,
            "compliant": domain_passed,
            "gates_checked": relevant_gates,
            "gate_results": {
                gate: result.gate_results.get(gate, True)
                for gate in relevant_gates
            },
            "overall_safe": result.is_safe
        }
```

### Step 3: Generate Compliance Report

```python
def generate_aicm_report(self, content: str) -> dict:
    """Generate comprehensive AICM compliance report."""

    domains = [
        "model_security",
        "governance_risk_compliance",
        "supply_chain_transparency",
        "data_security_privacy",
        "threat_vulnerability_management",
        "application_interface_security"
    ]

    results = {}
    for domain in domains:
        results[domain] = self.check_domain_compliance(content, domain)

    compliant_count = sum(1 for r in results.values() if r["compliant"])

    return {
        "timestamp": datetime.now().isoformat(),
        "framework": "CSA AI Controls Matrix v1.0",
        "domains_checked": len(domains),
        "domains_compliant": compliant_count,
        "compliance_rate": compliant_count / len(domains),
        "details": results,
        "recommendation": "Full compliance" if compliant_count == len(domains)
                         else f"Review {len(domains) - compliant_count} domain(s)"
    }
```

---

## Recommendations

### Use Sentinel THSP For:

1. **Model Security (Domain 14)** - Core strength: output validation, jailbreak prevention
2. **Governance (Domain 8)** - Risk assessment, policy enforcement
3. **Supply Chain (Domain 16)** - Accountability, transparency
4. **Threat Management (Domain 17)** - Adversarial input detection

### Combine Sentinel With:

1. **Infrastructure Security Tools** - Domains 3, 5, 6, 12, 18
2. **IAM Solutions** - Domain 10
3. **Logging Platforms** - Domain 13
4. **HR/Training Systems** - Domain 9
5. **Change Management** - Domain 4

### Sentinel Does NOT Replace:

1. Infrastructure security controls
2. Physical datacenter security
3. Encryption/cryptography systems
4. Identity management systems
5. Endpoint security solutions

---

## STAR for AI Certification

The CSA STAR for AI program provides certification against AICM controls. THSP supports:

| STAR Level | Description | THSP Contribution |
|------------|-------------|-------------------|
| **Level 1** | Self-Assessment | Provides validation evidence |
| **Level 2** | Third-Party Audit | Demonstrates behavioral controls |

---

## References

- [CSA AI Controls Matrix](https://cloudsecurityalliance.org/artifacts/ai-controls-matrix)
- [Introducing the CSA AI Controls Matrix](https://cloudsecurityalliance.org/blog/2025/07/10/introducing-the-csa-ai-controls-matrix-a-comprehensive-framework-for-trustworthy-ai)
- [Strategic Implementation Guide](https://cloudsecurityalliance.org/blog/2025/08/08/strategic-implementation-of-the-csa-ai-controls-matrix-a-ciso-s-guide-to-trustworthy-ai-governance)
- [STAR for AI Program](https://cloudsecurityalliance.org/press-releases/2025/10/23/cloud-security-alliance-launches-star-for-ai-establishing-the-global-framework-for-responsible-and-auditable-artificial-intelligence)
- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [THSP Protocol Specification](https://sentinelseed.dev/docs/methodology)

---

*Document maintained by Sentinel Team*
