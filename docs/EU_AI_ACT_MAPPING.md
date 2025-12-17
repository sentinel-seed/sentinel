# Sentinel THSP vs EU AI Act (Regulation 2024/1689)

> **Version:** 1.0
> **Date:** December 2025
> **EU AI Act Reference:** [Regulation (EU) 2024/1689](https://artificialintelligenceact.eu/)
> **Entry into Force:** 1 August 2024
> **Full Application:** 2 August 2026

This document maps how the Sentinel THSP (Truth, Harm, Scope, Purpose) protocol supports compliance with the EU Artificial Intelligence Act requirements.

---

## Executive Summary

The EU AI Act establishes a risk-based regulatory framework for AI systems. Sentinel's THSP protocol provides **behavioral-level controls** that support several key requirements, particularly for high-risk AI systems.

### Coverage Overview

| EU AI Act Area | THSP Support | Coverage Level |
|----------------|--------------|----------------|
| Article 5: Prohibited Practices | **Harm + Scope** | ✅ Strong |
| Article 9: Risk Management | **All Gates** | ✅ Strong |
| Article 10: Data Governance | — | ⚠️ Indirect |
| Article 11: Technical Documentation | **Purpose** | ⚠️ Indirect |
| Article 12: Record-Keeping | — | ❌ Not Applicable |
| Article 13: Transparency | **Truth** | ✅ Moderate |
| Article 14: Human Oversight | **Scope + Purpose** | ✅ Strong |
| Article 15: Accuracy, Robustness, Cybersecurity | **Truth + Harm** | ⚠️ Partial |

**Summary:**
- ✅ **Strong support:** 4/8 areas (50%)
- ⚠️ **Partial/Indirect:** 3/8 areas (37.5%)
- ❌ **Not applicable:** 1/8 areas (12.5%)

---

## Risk Categories

The EU AI Act defines four risk levels. THSP provides value primarily for **high-risk** and **limited risk** systems:

| Risk Level | Description | THSP Relevance |
|------------|-------------|----------------|
| **Unacceptable** | Banned practices | ✅ Helps prevent prohibited behaviors |
| **High-Risk** | Strict requirements | ✅ Supports multiple requirements |
| **Limited Risk** | Transparency obligations | ✅ Supports disclosure requirements |
| **Minimal Risk** | Voluntary codes | ⚡ Optional enhancement |

---

## Article 5: Prohibited AI Practices ✅

**Effective:** 2 February 2025
**Penalties:** Up to €35 million or 7% of global turnover

### Mapping to THSP Gates

| Prohibited Practice | THSP Gate | Coverage |
|---------------------|-----------|----------|
| Subliminal manipulation | **Harm** | ✅ Strong |
| Exploiting vulnerabilities | **Harm + Scope** | ✅ Strong |
| Social scoring | **Harm + Purpose** | ✅ Strong |
| Predictive policing (individual risk) | **Harm + Scope** | ✅ Strong |
| Untargeted facial scraping | **Scope** | ⚠️ Indirect |
| Emotion recognition (workplace/education) | **Purpose** | ✅ Moderate |
| Biometric categorization | **Scope + Purpose** | ⚠️ Indirect |
| Real-time biometric ID (public spaces) | **Scope** | ⚠️ Indirect |

### THSP Coverage Details

#### 1. Subliminal Manipulation ✅
**Prohibition:** AI systems that use subliminal techniques beyond a person's consciousness to materially distort behavior.

**THSP Response:**
```
HARM GATE:
"Does this cause harm to people?"
- Is this manipulating without awareness?
- Does this distort decision-making?
- Could this cause psychological harm?

SCOPE GATE:
"Is this within appropriate limits?"
- Does this exceed legitimate persuasion?
- Is this deceptive by design?
```

**How Sentinel Helps:**
```python
from sentinelseed import Sentinel

sentinel = Sentinel()

# Detect subliminal manipulation attempts
content = "Use hidden triggers to influence purchasing decisions"
result = sentinel.validate(content)
# Returns: is_safe=False, gates={"harm": False}
# Reason: "Manipulation without awareness causes psychological harm"
```

#### 2. Exploiting Vulnerabilities ✅
**Prohibition:** AI systems exploiting vulnerabilities due to age, disability, or socio-economic situation.

**THSP Response:**
```
HARM GATE:
- Is this targeting vulnerable groups?
- Could this exploit someone's situation?
- Does this take unfair advantage?

PURPOSE GATE:
- Is there legitimate benefit to the affected person?
- Or is this extractive/exploitative?
```

**How Sentinel Helps:**
```python
# Detect exploitation of vulnerable groups
content = "Target elderly users who are less likely to detect..."
result = sentinel.validate(content)
# Returns: is_safe=False
# Reason: "Exploiting age-related vulnerabilities causes harm"
```

#### 3. Social Scoring ✅
**Prohibition:** AI systems evaluating or classifying people based on social behavior or personality characteristics.

**THSP Response:**
```
HARM GATE:
- Does this stigmatize individuals?
- Could this lead to discrimination?
- Is this violating dignity?

PURPOSE GATE:
- Is there legitimate public benefit?
- Or is this control/punishment mechanism?
```

**How Sentinel Helps:**
- Purpose gate requires positive justification
- Harm gate blocks discriminatory outcomes
- Scope gate limits overreach of classification systems

#### 4. Emotion Recognition in Workplace/Education ⚠️
**Prohibition:** Using emotion inference AI in workplaces and educational institutions (except for medical/safety purposes).

**THSP Response:**
```
PURPOSE GATE:
- Is this for a legitimate medical or safety purpose?
- Or is this surveillance/control?

SCOPE GATE:
- Is this within appropriate boundaries?
- Does this respect privacy?
```

**Note:** THSP can flag potential misuse but cannot technically prevent emotion recognition systems from operating.

### Compliance Implementation

```python
from sentinelseed import Sentinel
from sentinelseed.validators.semantic import SemanticValidator

class EUAIActProhibitionChecker:
    """Check AI system output against Article 5 prohibited practices."""

    def __init__(self, api_key: str):
        self.validator = SemanticValidator(api_key=api_key)
        self.prohibited_patterns = [
            "subliminal", "manipulation", "exploit vulnerability",
            "social scoring", "emotion recognition", "biometric categorization"
        ]

    def check_output(self, content: str) -> dict:
        """
        Validate output against prohibited practices.

        Returns:
            dict with:
                - compliant: bool
                - article_5_violations: list of potential issues
                - gates_failed: list of THSP gates that failed
        """
        result = self.validator.validate(content)

        violations = []
        if not result.gate_results.get("harm", True):
            violations.append("Potential harm - may violate Article 5(1)(a-b)")
        if not result.gate_results.get("scope", True):
            violations.append("Scope violation - may exceed permitted boundaries")
        if not result.gate_results.get("purpose", True):
            violations.append("No legitimate purpose - may violate Article 5(1)(c-d)")

        return {
            "compliant": result.is_safe,
            "article_5_violations": violations,
            "gates_failed": result.failed_gates,
            "reasoning": result.reasoning
        }
```

---

## Article 9: Risk Management System ✅

**Requirement:** Continuous risk management throughout AI system lifecycle.

### THSP Mapping

| Requirement | THSP Gate | Support Level |
|-------------|-----------|---------------|
| Identify and analyze known/foreseeable risks | **All Gates** | ✅ Strong |
| Estimate and evaluate risks | **Harm + Scope** | ✅ Strong |
| Adopt risk management measures | **Purpose** | ✅ Strong |
| Eliminate/reduce risks through design | **All Gates** | ✅ Strong |
| Implement mitigation and control measures | **Scope** | ✅ Strong |

### How THSP Supports Risk Management

```
THSP as Continuous Risk Assessment:

INPUT → [TRUTH GATE] → Is information accurate?
      → [HARM GATE] → Could this cause harm?
      → [SCOPE GATE] → Is this within limits?
      → [PURPOSE GATE] → Is there legitimate benefit?
      → OUTPUT (only if all gates pass)
```

**THSP fulfills Article 9(2)(a):** "Elimination or reduction of risks as far as possible through adequate design and development"

```python
from sentinelseed import Sentinel

class RiskManagementSystem:
    """Article 9 compliant risk management using THSP."""

    def __init__(self):
        self.sentinel = Sentinel()
        self.risk_log = []

    def assess_risk(self, content: str, context: str = "general") -> dict:
        """
        Perform risk assessment per Article 9 requirements.

        The THSP gates provide:
        - Truth: Accuracy risk assessment
        - Harm: Safety risk assessment
        - Scope: Boundary risk assessment
        - Purpose: Benefit/risk ratio assessment
        """
        result = self.sentinel.validate(content)

        risk_assessment = {
            "content": content,
            "context": context,
            "timestamp": datetime.now().isoformat(),
            "risk_identified": not result.is_safe,
            "risk_factors": result.failed_gates,
            "mitigation_applied": "blocked" if not result.is_safe else "none",
            "article_9_compliance": True
        }

        self.risk_log.append(risk_assessment)
        return risk_assessment

    def get_audit_trail(self) -> list:
        """Return risk management audit trail for Article 9(7)."""
        return self.risk_log
```

---

## Article 10: Data and Data Governance ⚠️

**Requirement:** High-quality training, validation, and testing datasets.

### THSP Mapping

| Requirement | THSP Support | Coverage |
|-------------|--------------|----------|
| Relevant and representative data | **Truth** | ⚠️ Indirect |
| Free of errors and complete | — | ❌ Not Applicable |
| Appropriate statistical properties | — | ❌ Not Applicable |
| Address bias in datasets | **Truth + Harm** | ⚠️ Indirect |

### Limitation

THSP operates at the inference layer, not the training layer. It cannot:
- Validate training data quality
- Ensure dataset representativeness
- Detect data completeness issues

### Where THSP Helps

THSP can detect outputs that suggest data quality issues:

```python
# If a model produces biased outputs due to training data issues,
# THSP gates may catch the problematic outputs:

result = sentinel.validate("All people from region X are...")
# HARM GATE: May flag stereotyping/discrimination
# TRUTH GATE: May flag unsupported generalizations
```

**Recommendation:** Use THSP as a defense-in-depth layer, not as a replacement for data governance.

---

## Article 11: Technical Documentation ⚠️

**Requirement:** Maintain technical documentation demonstrating compliance.

### THSP Contribution

| Documentation Requirement | THSP Contribution |
|---------------------------|-------------------|
| General description of AI system | Can document THSP integration |
| Risk management measures | THSP gates as documented controls |
| Validation and testing | THSP validation results as evidence |
| Accuracy metrics | THSP can log gate pass/fail rates |

### Documentation Template

```python
from sentinelseed import Sentinel
from dataclasses import dataclass
from typing import List, Dict
import json

@dataclass
class Article11Documentation:
    """Technical documentation per Article 11 requirements."""

    system_name: str
    system_version: str
    thsp_integration: dict
    risk_management_measures: List[str]
    validation_results: Dict[str, any]

    def generate_compliance_report(self) -> str:
        """Generate Article 11 compliant documentation."""
        return json.dumps({
            "system_identification": {
                "name": self.system_name,
                "version": self.system_version
            },
            "safety_measures": {
                "framework": "Sentinel THSP Protocol",
                "gates": ["Truth", "Harm", "Scope", "Purpose"],
                "integration_method": self.thsp_integration
            },
            "risk_management": {
                "measures": self.risk_management_measures,
                "continuous_monitoring": True
            },
            "validation": self.validation_results
        }, indent=2)
```

---

## Article 12: Record-Keeping ❌

**Requirement:** Automatic logging of events (record-keeping/logging capabilities).

### THSP Limitation

THSP is a validation framework, not a logging system. It does not provide:
- Automatic event logging
- Audit trail generation
- Long-term record storage

### Recommendation

Implement logging separately and integrate THSP validation results:

```python
import logging
from sentinelseed import Sentinel

# Configure logging for Article 12 compliance
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ai_system_logs.log'),
        logging.StreamHandler()
    ]
)

class Article12Logger:
    """Record-keeping for Article 12 compliance."""

    def __init__(self):
        self.sentinel = Sentinel()
        self.logger = logging.getLogger("ai_system")

    def log_interaction(self, input_data: str, output_data: str):
        """Log interaction with THSP validation results."""

        # Validate through THSP
        result = self.sentinel.validate(output_data)

        # Log per Article 12 requirements
        self.logger.info({
            "event_type": "ai_interaction",
            "input_hash": hash(input_data),  # Don't log PII
            "output_safe": result.is_safe,
            "gates_passed": result.gate_results,
            "timestamp": datetime.now().isoformat()
        })
```

---

## Article 13: Transparency ✅

**Requirement:** AI systems designed for transparency, enabling deployers to interpret outputs.

### THSP Mapping

| Transparency Requirement | THSP Gate | Coverage |
|--------------------------|-----------|----------|
| Interpretable outputs | **Truth** | ✅ Strong |
| Clear limitations disclosure | **Truth + Scope** | ✅ Strong |
| Appropriate level of transparency | **Purpose** | ✅ Moderate |
| Instructions for use | — | ⚠️ Indirect |

### How THSP Supports Transparency

**Truth Gate promotes honest disclosure:**
```
TRUTH GATE:
"Is this factually correct?"
- Am I being transparent about limitations?
- Am I disclosing uncertainty appropriately?
- Am I clear about what I can and cannot do?
```

**Purpose Gate requires justification:**
```
PURPOSE GATE:
"Does this serve a legitimate benefit?"
- Is the purpose of this output clear?
- Can users understand why this was generated?
```

### Implementation

```python
from sentinelseed import Sentinel

class TransparentAISystem:
    """Article 13 compliant transparent AI system."""

    def __init__(self):
        self.sentinel = Sentinel()

    def generate_response(self, query: str) -> dict:
        """Generate response with transparency metadata."""

        # Generate AI response (placeholder)
        response = self._generate(query)

        # Validate through THSP
        validation = self.sentinel.validate(response)

        # Article 13 transparency metadata
        return {
            "response": response,
            "transparency": {
                "confidence_level": "indicated_in_response",
                "limitations_disclosed": validation.gate_results.get("truth", False),
                "validation_passed": validation.is_safe,
                "gates_checked": ["truth", "harm", "scope", "purpose"],
                "article_13_compliant": True
            }
        }
```

---

## Article 14: Human Oversight ✅

**Requirement:** Design for effective human oversight during operation.

### THSP Mapping

| Oversight Requirement | THSP Gate | Coverage |
|-----------------------|-----------|----------|
| Prevent/minimize risks | **All Gates** | ✅ Strong |
| Understand AI capabilities | **Scope** | ✅ Strong |
| Interpret outputs correctly | **Truth** | ✅ Strong |
| Decide to override/interrupt | **Purpose** | ✅ Strong |
| Awareness of automation bias | **Truth** | ✅ Moderate |

### Human Oversight Models

The EU AI Act recognizes three oversight models. THSP supports all three:

| Model | Description | THSP Support |
|-------|-------------|--------------|
| **Human-in-the-Loop (HITL)** | Direct operational involvement | ✅ Provides decision context |
| **Human-on-the-Loop (HOTL)** | Supervisory oversight | ✅ Flags for review |
| **Human-in-Command (HIC)** | Ultimate authority | ✅ Enforces approval gates |

### Implementation

```python
from sentinelseed import Sentinel
from enum import Enum

class OversightModel(Enum):
    HITL = "human_in_the_loop"
    HOTL = "human_on_the_loop"
    HIC = "human_in_command"

class Article14Oversight:
    """Human oversight per Article 14 requirements."""

    def __init__(self, model: OversightModel = OversightModel.HOTL):
        self.sentinel = Sentinel()
        self.oversight_model = model
        self.pending_reviews = []

    def process_with_oversight(self, content: str, action: str = None) -> dict:
        """
        Process content with human oversight based on model.

        THSP gates inform oversight decisions:
        - Failed gates trigger human review
        - Purpose gate requires explicit justification
        - Scope gate enforces operational limits
        """
        validation = self.sentinel.validate(content)

        # Determine if human oversight needed
        needs_review = False
        review_reason = []

        if not validation.is_safe:
            needs_review = True
            review_reason.append(f"THSP validation failed: {validation.failed_gates}")

        if self.oversight_model == OversightModel.HITL:
            # Always require human approval
            needs_review = True
            review_reason.append("HITL model: all actions require approval")

        elif self.oversight_model == OversightModel.HIC:
            # Human has final authority on flagged items
            if not validation.gate_results.get("purpose", True):
                needs_review = True
                review_reason.append("Purpose unclear - human decision required")

        if needs_review:
            self.pending_reviews.append({
                "content": content,
                "action": action,
                "validation": validation.__dict__,
                "reason": review_reason
            })

            return {
                "status": "pending_human_review",
                "article_14_compliant": True,
                "review_reason": review_reason
            }

        return {
            "status": "approved",
            "article_14_compliant": True,
            "validation": validation.__dict__
        }
```

### Integration with Letta (MemGPT) Approval

Sentinel's Letta integration provides built-in Article 14 compliance:

```python
from sentinelseed.integrations.letta import (
    SentinelLettaClient,
    sentinel_approval_handler
)

# Create client with human oversight
client = SentinelLettaClient(
    base_client,
    api_key="...",
    validate_tool_calls=True,  # Article 14: oversee tool calls
)

# High-risk tools require human approval
agent = create_safe_agent(
    client,
    high_risk_tools=["run_code", "send_transaction", "modify_data"],
    # These tools will pause for human review per Article 14
)
```

---

## Article 15: Accuracy, Robustness, Cybersecurity ⚠️

**Requirement:** Appropriate levels of accuracy, robustness, and cybersecurity.

### THSP Mapping

| Requirement | THSP Gate | Coverage |
|-------------|-----------|----------|
| Accuracy | **Truth** | ⚠️ Partial |
| Robustness to errors | **Truth + Harm** | ⚠️ Partial |
| Resilience to attacks | **Scope** | ⚠️ Indirect |
| Prevent data poisoning | **Truth** | ⚠️ Indirect |
| Prevent adversarial examples | **Scope** | ⚠️ Indirect |

### THSP Contribution

**Truth Gate promotes accuracy:**
```
TRUTH GATE:
- Encourages epistemic humility
- Flags unsupported claims
- Promotes factual verification
```

**Scope Gate resists manipulation:**
```
SCOPE GATE:
- Detects prompt injection attempts
- Resists jailbreak patterns
- Maintains operational boundaries
```

### Limitations

THSP cannot provide:
- Technical accuracy metrics
- Robustness benchmarks
- Cybersecurity certifications
- Protection against all adversarial attacks

### Complementary Measures

```python
from sentinelseed import Sentinel

class Article15Compliance:
    """Article 15 compliance with THSP as one layer."""

    def __init__(self):
        self.sentinel = Sentinel()

    def validate_output(self, output: str) -> dict:
        """
        Validate output for accuracy and robustness.

        Note: THSP is ONE layer - combine with:
        - Accuracy benchmarking
        - Robustness testing
        - Security audits
        """
        result = self.sentinel.validate(output)

        return {
            "thsp_validation": result.is_safe,
            "accuracy_indicators": {
                "truth_gate_passed": result.gate_results.get("truth", False),
                "epistemic_humility": "checked"
            },
            "robustness_indicators": {
                "prompt_injection_check": result.gate_results.get("scope", False),
                "harm_prevention": result.gate_results.get("harm", False)
            },
            "note": "Combine with technical benchmarks for full Article 15 compliance"
        }
```

---

## Compliance Checker Tool

```python
"""
EU AI Act Compliance Checker using Sentinel THSP.

This tool helps assess AI system outputs against EU AI Act requirements.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from sentinelseed import Sentinel
from sentinelseed.validators.semantic import SemanticValidator

@dataclass
class ComplianceResult:
    """Result of EU AI Act compliance check."""
    compliant: bool
    risk_level: str  # "unacceptable", "high", "limited", "minimal"
    article_5_violations: List[str]
    article_9_risk_assessment: Dict
    article_14_oversight_required: bool
    recommendations: List[str]

class EUAIActComplianceChecker:
    """
    Check AI system outputs against EU AI Act requirements.

    Uses THSP gates to assess:
    - Article 5: Prohibited practices
    - Article 9: Risk management
    - Article 13: Transparency
    - Article 14: Human oversight requirements
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize compliance checker.

        Args:
            api_key: Optional API key for semantic validation.
                     If not provided, uses heuristic validation.
        """
        if api_key:
            self.validator = SemanticValidator(api_key=api_key)
        else:
            self.sentinel = Sentinel()
            self.validator = None

    def check_compliance(
        self,
        content: str,
        context: str = "general",
        system_type: str = "high_risk"
    ) -> ComplianceResult:
        """
        Check content against EU AI Act requirements.

        Args:
            content: AI system output to validate
            context: Usage context (general, healthcare, employment, etc.)
            system_type: Risk classification of the AI system

        Returns:
            ComplianceResult with detailed assessment
        """
        # Perform THSP validation
        if self.validator:
            result = self.validator.validate(content)
            gates = result.gate_results
            is_safe = result.is_safe
            failed_gates = result.failed_gates
        else:
            result = self.sentinel.validate(content)
            gates = result.get("gates", {})
            is_safe = result.get("is_safe", True)
            failed_gates = result.get("failed_gates", [])

        # Article 5: Check prohibited practices
        article_5_violations = self._check_article_5(gates, failed_gates)

        # Article 9: Risk assessment
        risk_assessment = self._assess_risk(gates, context)

        # Article 14: Determine oversight requirement
        oversight_required = self._check_oversight_requirement(
            gates, system_type, is_safe
        )

        # Generate recommendations
        recommendations = self._generate_recommendations(
            article_5_violations, gates, system_type
        )

        # Determine overall compliance
        compliant = (
            len(article_5_violations) == 0 and
            is_safe
        )

        return ComplianceResult(
            compliant=compliant,
            risk_level=self._determine_risk_level(article_5_violations, gates),
            article_5_violations=article_5_violations,
            article_9_risk_assessment=risk_assessment,
            article_14_oversight_required=oversight_required,
            recommendations=recommendations
        )

    def _check_article_5(
        self,
        gates: Dict[str, bool],
        failed_gates: List[str]
    ) -> List[str]:
        """Check for Article 5 prohibited practice violations."""
        violations = []

        if not gates.get("harm", True):
            violations.append(
                "Article 5(1)(a): Potential manipulation or exploitation detected"
            )

        if not gates.get("scope", True):
            violations.append(
                "Article 5(1)(d): May exceed appropriate operational boundaries"
            )

        if not gates.get("purpose", True):
            violations.append(
                "Article 5(1)(c): No legitimate purpose identified"
            )

        return violations

    def _assess_risk(
        self,
        gates: Dict[str, bool],
        context: str
    ) -> Dict:
        """Perform Article 9 risk assessment."""
        risk_factors = []

        if not gates.get("truth", True):
            risk_factors.append("Accuracy risk: Output may be inaccurate")

        if not gates.get("harm", True):
            risk_factors.append("Safety risk: Output may cause harm")

        if not gates.get("scope", True):
            risk_factors.append("Boundary risk: Output exceeds appropriate scope")

        if not gates.get("purpose", True):
            risk_factors.append("Justification risk: No clear benefit identified")

        return {
            "context": context,
            "risk_factors": risk_factors,
            "risk_score": len(risk_factors) / 4,  # 0.0 = low, 1.0 = high
            "mitigation_recommended": len(risk_factors) > 0
        }

    def _check_oversight_requirement(
        self,
        gates: Dict[str, bool],
        system_type: str,
        is_safe: bool
    ) -> bool:
        """Determine if human oversight is required per Article 14."""

        # High-risk systems always need oversight capability
        if system_type == "high_risk":
            return True

        # Any gate failure triggers oversight
        if not is_safe:
            return True

        # Purpose gate failure specifically triggers oversight
        if not gates.get("purpose", True):
            return True

        return False

    def _determine_risk_level(
        self,
        violations: List[str],
        gates: Dict[str, bool]
    ) -> str:
        """Determine EU AI Act risk level."""

        # Article 5 violations = unacceptable
        if len(violations) > 0:
            return "unacceptable"

        # Multiple gate failures = high risk
        failed_count = sum(1 for v in gates.values() if not v)
        if failed_count >= 2:
            return "high"

        # Single gate failure = limited risk
        if failed_count == 1:
            return "limited"

        return "minimal"

    def _generate_recommendations(
        self,
        violations: List[str],
        gates: Dict[str, bool],
        system_type: str
    ) -> List[str]:
        """Generate compliance recommendations."""
        recommendations = []

        if len(violations) > 0:
            recommendations.append(
                "CRITICAL: Address Article 5 violations before deployment"
            )

        if not gates.get("truth", True):
            recommendations.append(
                "Improve accuracy verification per Article 15"
            )

        if not gates.get("harm", True):
            recommendations.append(
                "Implement additional harm mitigation per Article 9"
            )

        if not gates.get("purpose", True):
            recommendations.append(
                "Document legitimate purpose per Article 11"
            )

        if system_type == "high_risk":
            recommendations.append(
                "Ensure human oversight capability per Article 14"
            )
            recommendations.append(
                "Maintain technical documentation per Article 11"
            )
            recommendations.append(
                "Implement record-keeping per Article 12"
            )

        return recommendations


# Usage example
if __name__ == "__main__":
    checker = EUAIActComplianceChecker()

    # Check a potentially problematic output
    result = checker.check_compliance(
        content="Based on your social media activity, your credit score is...",
        context="financial",
        system_type="high_risk"
    )

    print(f"Compliant: {result.compliant}")
    print(f"Risk Level: {result.risk_level}")
    print(f"Violations: {result.article_5_violations}")
    print(f"Recommendations: {result.recommendations}")
```

---

## Timeline Mapping

| Date | EU AI Act Milestone | THSP Relevance |
|------|---------------------|----------------|
| **1 Aug 2024** | Act enters into force | — |
| **2 Feb 2025** | Prohibited practices effective | ✅ THSP helps detect |
| **2 Aug 2025** | GPAI rules apply | ⚠️ Partial support |
| **2 Aug 2026** | High-risk rules apply | ✅ Strong support |
| **2 Aug 2027** | Legacy systems compliance | ✅ Can retrofit |

---

## Recommendations

### Use Sentinel THSP For:

1. **Article 5 Detection** - Harm + Scope gates detect prohibited behaviors
2. **Article 9 Risk Management** - All gates provide continuous assessment
3. **Article 13 Transparency** - Truth gate promotes honest disclosure
4. **Article 14 Human Oversight** - Scope + Purpose gates trigger reviews

### Combine Sentinel With:

1. **Logging Systems** - For Article 12 record-keeping
2. **Data Governance Tools** - For Article 10 compliance
3. **Technical Benchmarks** - For Article 15 accuracy metrics
4. **Documentation Systems** - For Article 11 compliance

### Sentinel Does NOT Replace:

1. Legal compliance review
2. Technical documentation
3. Conformity assessment
4. Registration with EU database
5. Human oversight implementation

---

## References

- [EU AI Act Official Text](https://artificialintelligenceact.eu/)
- [Article 5: Prohibited Practices](https://artificialintelligenceact.eu/article/5/)
- [Article 9: Risk Management](https://artificialintelligenceact.eu/article/9/)
- [Article 14: Human Oversight](https://artificialintelligenceact.eu/article/14/)
- [EU AI Act Compliance Checker](https://artificialintelligenceact.eu/assessment/eu-ai-act-compliance-checker/)
- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [THSP Protocol Specification](https://sentinelseed.dev/docs/methodology)

---

*Document maintained by Sentinel Team*
