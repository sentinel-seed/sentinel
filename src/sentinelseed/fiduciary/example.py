"""
Fiduciary AI Module Examples

Demonstrates how to use fiduciary principles in AI systems.

Requirements:
    pip install sentinelseed
"""

from sentinelseed.fiduciary import (
    FiduciaryValidator,
    FiduciaryGuard,
    UserContext,
    FiduciaryResult,
    validate_fiduciary,
    is_fiduciary_compliant,
    FiduciaryViolationError,
)


def example_basic_validation():
    """
    Example 1: Basic fiduciary validation

    Check if an action is fiduciary-compliant.
    """
    print("\n=== Example 1: Basic Validation ===\n")

    validator = FiduciaryValidator()

    # Create user context
    user = UserContext(
        user_id="user123",
        goals=["save for retirement", "minimize risk"],
        risk_tolerance="low",
        constraints=["no crypto", "no high-risk investments"],
    )

    # Test various actions
    actions = [
        "Recommend a low-cost index fund for long-term growth",
        "Recommend a high-risk cryptocurrency investment",
        "Just trust me and invest in our premium service",
        "Transfer your savings to this new opportunity",
    ]

    for action in actions:
        result = validator.validate_action(action, user)
        status = "COMPLIANT" if result.compliant else "NON-COMPLIANT"
        print(f"[{status}] {action[:50]}...")
        if not result.compliant:
            for v in result.violations:
                print(f"  - {v.duty.value}: {v.description}")
        print()


def example_conflict_detection():
    """
    Example 2: Detecting conflicts of interest

    Identify when AI might be serving provider interests over user interests.
    """
    print("\n=== Example 2: Conflict Detection ===\n")

    from sentinelseed.fiduciary import ConflictDetector

    detector = ConflictDetector()

    # Test actions that might have conflicts
    actions = [
        "I recommend our premium service for your needs",
        "Upgrade to the paid plan for better features",
        "Consider using a competitor's free tool instead",
        "Here's an unbiased comparison of your options",
    ]

    for action in actions:
        violations = detector.detect(action)
        if violations:
            print(f"CONFLICT: {action}")
            for v in violations:
                print(f"  - {v.description}")
        else:
            print(f"OK: {action}")
        print()


def example_guard_decorator():
    """
    Example 3: Using FiduciaryGuard as decorator

    Protect functions with automatic fiduciary validation.
    """
    print("\n=== Example 3: Guard Decorator ===\n")

    guard = FiduciaryGuard(
        block_on_violation=True,
        log_decisions=True,
    )

    @guard.protect
    def recommend_investment(
        amount: float,
        risk_level: str,
        user_context: UserContext = None,
    ) -> str:
        return f"Invest ${amount} in {risk_level}-risk portfolio"

    # This should work - aligned with user preferences
    user_low_risk = UserContext(risk_tolerance="low")
    try:
        result = recommend_investment(
            amount=1000,
            risk_level="low",
            user_context=user_low_risk,
        )
        print(f"Approved: {result}")
    except FiduciaryViolationError as e:
        print(f"Blocked: {e}")

    # This should be blocked - misaligned with user preferences
    try:
        result = recommend_investment(
            amount=10000,
            risk_level="high aggressive speculative",
            user_context=user_low_risk,
        )
        print(f"Approved: {result}")
    except FiduciaryViolationError as e:
        print(f"Blocked: {e.result.violations[0].description}")

    # Print decision log
    print(f"\nDecision log: {len(guard.decision_log)} entries")


def example_quick_check():
    """
    Example 4: Quick compliance checks

    One-liner validation for simple use cases.
    """
    print("\n=== Example 4: Quick Checks ===\n")

    # Quick boolean check
    is_ok = is_fiduciary_compliant(
        action="Provide clear investment guidance based on user goals",
        user_context={"goals": ["grow wealth"], "risk_tolerance": "moderate"},
    )
    print(f"Clear guidance: {'COMPLIANT' if is_ok else 'NON-COMPLIANT'}")

    # Get full result
    result = validate_fiduciary(
        action="Don't worry about the details, just sign here",
        user_context={"goals": ["understand investments"]},
    )
    print(f"Vague instruction: {'COMPLIANT' if result.compliant else 'NON-COMPLIANT'}")
    if not result.compliant:
        print(f"  Violations: {len(result.violations)}")


def example_financial_advisor():
    """
    Example 5: Financial advisor AI

    Real-world example of fiduciary AI in financial services.
    """
    print("\n=== Example 5: Financial Advisor AI ===\n")

    class FiduciaryAdvisor:
        """AI financial advisor with fiduciary obligations"""

        def __init__(self):
            self.validator = FiduciaryValidator(strict_mode=True)

        def get_recommendation(
            self,
            user: UserContext,
            query: str,
        ) -> dict:
            """Generate recommendation with fiduciary validation"""

            # Generate recommendation (simplified)
            if "high return" in query.lower():
                recommendation = "Aggressive growth portfolio with stocks"
            elif "safe" in query.lower():
                recommendation = "Conservative bond-heavy portfolio"
            else:
                recommendation = "Balanced diversified portfolio"

            # Validate against fiduciary duties
            result = self.validator.validate_action(
                action=f"Recommend {recommendation} for query: {query}",
                user_context=user,
            )

            return {
                "recommendation": recommendation,
                "fiduciary_compliant": result.compliant,
                "confidence": result.confidence,
                "explanations": result.explanations,
                "warnings": [v.description for v in result.violations],
            }

    # Create advisor and test
    advisor = FiduciaryAdvisor()

    # Conservative user asking about high returns
    conservative_user = UserContext(
        user_id="client_001",
        goals=["retirement savings", "capital preservation"],
        risk_tolerance="low",
        constraints=["no loss of principal"],
    )

    result = advisor.get_recommendation(
        user=conservative_user,
        query="I want high returns quickly",
    )

    print(f"Recommendation: {result['recommendation']}")
    print(f"Fiduciary compliant: {result['fiduciary_compliant']}")
    print(f"Confidence: {result['confidence']:.2f}")
    if result['warnings']:
        print(f"Warnings: {result['warnings']}")


def example_custom_rules():
    """
    Example 6: Adding custom fiduciary rules

    Extend validation with domain-specific rules.
    """
    print("\n=== Example 6: Custom Rules ===\n")

    from sentinelseed.fiduciary import Violation, FiduciaryDuty, ViolationType

    # Custom rule: Detect recommendations for very large amounts
    def check_large_amounts(action: str, context: UserContext) -> list:
        violations = []
        # Simple check for large dollar amounts
        import re
        amounts = re.findall(r'\$([0-9,]+)', action)
        for amount in amounts:
            value = int(amount.replace(',', ''))
            if value > 100000:
                violations.append(Violation(
                    duty=FiduciaryDuty.CARE,
                    type=ViolationType.UNDISCLOSED_RISK,
                    description=f"Large amount ${value:,} requires extra review",
                    severity="medium",
                    recommendation="Verify user understands the scale",
                ))
        return violations

    # Create validator with custom rule
    validator = FiduciaryValidator(custom_rules=[check_large_amounts])

    # Test
    result = validator.validate_action(
        action="Transfer $500,000 to investment account",
        user_context=UserContext(),
    )

    print(f"Large transfer: {'COMPLIANT' if result.compliant else 'NON-COMPLIANT'}")
    for v in result.violations:
        print(f"  - {v.description}")


if __name__ == "__main__":
    print("Fiduciary AI Module Examples")
    print("=" * 50)

    example_basic_validation()
    example_conflict_detection()
    example_guard_decorator()
    example_quick_check()
    example_financial_advisor()
    example_custom_rules()
