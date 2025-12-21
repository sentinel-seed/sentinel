# Sentinel Fiduciary AI Module

> Ensure AI acts in the user's best interest with fiduciary principles

## Overview

The Fiduciary AI module implements legal fiduciary principles for AI systems:
- **Duty of Loyalty** — Act in user's best interest, not provider's
- **Duty of Care** — Exercise reasonable diligence
- **Transparency** — Disclose limitations and conflicts
- **Confidentiality** — Protect user information

## Installation

```bash
pip install sentinelseed
```

## Quick Start

```python
from sentinelseed.fiduciary import FiduciaryValidator, UserContext

validator = FiduciaryValidator()

# Define user context
user = UserContext(
    user_id="user123",
    goals=["save for retirement", "minimize risk"],
    risk_tolerance="low",
    constraints=["no crypto", "no high-risk investments"]
)

# Validate an action
result = validator.validate_action(
    action="Recommend high-risk cryptocurrency investment",
    user_context=user
)

if not result.compliant:
    print(f"Violations: {[v.description for v in result.violations]}")
```

## Core Components

### FiduciaryValidator

Main validation class implementing the six-step fiduciary framework:

```python
from sentinelseed.fiduciary import FiduciaryValidator, UserContext

validator = FiduciaryValidator(strict_mode=True)

result = validator.validate_action(
    action="Transfer funds to new account",
    user_context=UserContext(goals=["protect savings"])
)

print(f"Compliant: {result.compliant}")
print(f"Confidence: {result.confidence}")
print(f"Explanations: {result.explanations}")
```

### FiduciaryGuard (Decorator)

Protect functions with automatic fiduciary validation:

```python
from sentinelseed.fiduciary import FiduciaryGuard, UserContext

guard = FiduciaryGuard(block_on_violation=True)

@guard.protect
def recommend_investment(amount: float, risk_level: str, user_context: UserContext = None):
    return f"Invest ${amount} in {risk_level}-risk portfolio"

# This passes - aligned with user
result = recommend_investment(1000, "low", user_context=UserContext(risk_tolerance="low"))

# This raises FiduciaryViolationError - misaligned
result = recommend_investment(10000, "high", user_context=UserContext(risk_tolerance="low"))
```

### ConflictDetector

Identify conflicts of interest:

```python
from sentinelseed.fiduciary import ConflictDetector

detector = ConflictDetector()

violations = detector.detect("I recommend our premium service for your needs")
# Detects: Potential self-serving recommendation
```

## Fiduciary Duties

| Duty | Description | Example Violation |
|------|-------------|-------------------|
| **Loyalty** | Prioritize user's interests | Recommending provider's product over better alternatives |
| **Care** | Exercise reasonable diligence | Not disclosing known risks |
| **Transparency** | Be open about limitations | Hiding AI limitations or uncertainties |
| **Confidentiality** | Protect user data | Sharing user information without consent |

## Violation Types

```python
from sentinelseed.fiduciary import ViolationType

# Available violation types:
ViolationType.CONFLICT_OF_INTEREST      # Provider vs user interests
ViolationType.SELF_DEALING              # Acting in own interest
ViolationType.MISALIGNED_RECOMMENDATION # Against user goals
ViolationType.INADEQUATE_DISCLOSURE     # Missing disclosures
ViolationType.PRIVACY_VIOLATION         # Exposing user information
ViolationType.LACK_OF_TRANSPARENCY      # Unexplained decisions
ViolationType.INCOMPETENT_ACTION        # Vague or uncertain guidance
ViolationType.UNDISCLOSED_RISK          # Hidden dangers
ViolationType.USER_HARM                 # Potential user harm
```

## Quick Validation Functions

```python
from sentinelseed.fiduciary import validate_fiduciary, is_fiduciary_compliant

# Get full result
result = validate_fiduciary(
    action="Provide investment advice",
    user_context={"goals": ["grow wealth"], "risk_tolerance": "moderate"}
)

# Quick boolean check
is_ok = is_fiduciary_compliant(
    action="Explain investment options",
    user_context={"goals": ["understand options"]}
)
```

## Custom Rules

Add domain-specific fiduciary rules:

```python
from sentinelseed.fiduciary import FiduciaryValidator, Violation, FiduciaryDuty, ViolationType
import re

def check_large_amounts(action: str, context) -> list:
    violations = []
    amounts = re.findall(r'\$([0-9,]+)', action)
    for amount in amounts:
        value = int(amount.replace(',', ''))
        if value > 100000:
            violations.append(Violation(
                duty=FiduciaryDuty.CARE,
                type=ViolationType.UNDISCLOSED_RISK,
                description=f"Large amount ${value:,} requires extra review",
                severity="medium"
            ))
    return violations

validator = FiduciaryValidator(custom_rules=[check_large_amounts])
```

## Use Cases

### Financial AI Advisor

```python
from sentinelseed.fiduciary import FiduciaryValidator, UserContext

validator = FiduciaryValidator(strict_mode=True)

def get_recommendation(user: UserContext, query: str) -> dict:
    # Generate recommendation
    recommendation = generate_ai_response(query)

    # Validate against fiduciary duties
    result = validator.validate_action(
        action=f"Recommend: {recommendation}",
        user_context=user
    )

    return {
        "recommendation": recommendation,
        "fiduciary_compliant": result.compliant,
        "warnings": [v.description for v in result.violations]
    }
```

### Crypto/DeFi Agent

```python
from sentinelseed.fiduciary import FiduciaryGuard, UserContext

guard = FiduciaryGuard(block_on_violation=True, log_decisions=True)

@guard.protect
def execute_trade(token: str, amount: float, user_context: UserContext = None):
    # Trade only executes if fiduciary-compliant
    return perform_swap(token, amount)
```

## API Reference

See [example.py](./example.py) for comprehensive usage examples.

## Related

- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [Memory Integrity](../memory/)
- [THSP Protocol](https://sentinelseed.dev/docs/methodology)

## License

MIT
