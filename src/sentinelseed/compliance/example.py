"""
Example usage of EU AI Act Compliance Checker.

Run with:
    python -m sentinelseed.compliance.example

Requires:
    pip install sentinelseed
"""

import os


def example_1_basic_check():
    """
    Example 1: Basic compliance check.

    Check if AI output complies with EU AI Act requirements.
    """
    print("\n" + "=" * 60)
    print("Example 1: Basic Compliance Check")
    print("=" * 60)

    from sentinelseed.compliance import (
        EUAIActComplianceChecker,
        SystemType,
    )

    # Create checker (heuristic mode without API key)
    checker = EUAIActComplianceChecker()

    # Check a safe output
    result = checker.check_compliance(
        content="The weather today is sunny with a high of 25 degrees.",
        context="general",
        system_type=SystemType.MINIMAL_RISK
    )

    print(f"Content: 'Weather information'")
    print(f"Compliant: {result.compliant}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Oversight Required: {result.article_14_oversight_required}")


def example_2_prohibited_practice():
    """
    Example 2: Detect prohibited practices.

    Article 5 prohibitions are detected and flagged.
    """
    print("\n" + "=" * 60)
    print("Example 2: Prohibited Practice Detection")
    print("=" * 60)

    from sentinelseed.compliance import (
        EUAIActComplianceChecker,
        SystemType,
    )

    checker = EUAIActComplianceChecker()

    # Check for social scoring (prohibited under Article 5(1)(c))
    result = checker.check_compliance(
        content="Based on your social media activity and behavior score, "
                "your trustworthiness score is 650 out of 1000.",
        context="financial",
        system_type=SystemType.HIGH_RISK
    )

    print(f"Content: 'Social scoring output'")
    print(f"Compliant: {result.compliant}")
    print(f"Risk Level: {result.risk_level.value}")

    if result.article_5_violations:
        print("\nArticle 5 Violations:")
        for v in result.article_5_violations:
            print(f"  - {v.article_reference}: {v.description}")
            print(f"    Severity: {v.severity}")
            print(f"    Recommendation: {v.recommendation}")


def example_3_high_risk_context():
    """
    Example 3: High-risk context assessment.

    Healthcare, employment, law enforcement contexts
    require additional scrutiny.
    """
    print("\n" + "=" * 60)
    print("Example 3: High-Risk Context")
    print("=" * 60)

    from sentinelseed.compliance import (
        EUAIActComplianceChecker,
        SystemType,
    )

    checker = EUAIActComplianceChecker()

    # Check content in healthcare context
    result = checker.check_compliance(
        content="Based on the symptoms described, the diagnosis is likely condition X. "
                "Treatment should begin immediately.",
        context="healthcare",
        system_type=SystemType.HIGH_RISK
    )

    print(f"Context: Healthcare (Annex III high-risk)")
    print(f"Compliant: {result.compliant}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Oversight Required: {result.article_14_oversight_required}")

    print("\nRisk Assessment (Article 9):")
    print(f"  Risk Score: {result.article_9_risk_assessment.risk_score:.2f}")
    print(f"  Risk Factors: {result.article_9_risk_assessment.risk_factors}")

    print("\nRecommendations:")
    for rec in result.recommendations:
        print(f"  - {rec}")


def example_4_semantic_validation():
    """
    Example 4: Semantic validation with API key.

    Uses LLM-based validation for higher accuracy.
    """
    print("\n" + "=" * 60)
    print("Example 4: Semantic Validation")
    print("=" * 60)

    from sentinelseed.compliance import (
        EUAIActComplianceChecker,
        SystemType,
    )

    api_key = os.environ.get("OPENAI_API_KEY")

    if not api_key:
        print("OPENAI_API_KEY not set - using heuristic mode")
        checker = EUAIActComplianceChecker()
    else:
        print("Using semantic validation (LLM-based)")
        checker = EUAIActComplianceChecker(api_key=api_key)

    # Check potentially manipulative content
    result = checker.check_compliance(
        content="This limited-time offer uses proven psychological techniques "
                "to help you make the best decision for your family.",
        context="marketing",
        system_type=SystemType.LIMITED_RISK
    )

    print(f"Compliant: {result.compliant}")
    print(f"Risk Level: {result.risk_level.value}")
    print(f"Validation Method: {result.metadata.get('validation_method', 'unknown')}")


def example_5_convenience_function():
    """
    Example 5: Using convenience function.

    Simple one-liner compliance check.
    """
    print("\n" + "=" * 60)
    print("Example 5: Convenience Function")
    print("=" * 60)

    from sentinelseed.compliance import check_eu_ai_act_compliance

    # Quick check
    result = check_eu_ai_act_compliance(
        content="The candidate's age and nationality suggest they may not be suitable.",
        context="employment",
        system_type="high_risk"
    )

    print(f"Content: 'Potentially discriminatory employment decision'")
    print(f"Compliant: {result['compliant']}")
    print(f"Risk Level: {result['risk_level']}")
    print(f"Violations: {len(result['article_5_violations'])}")


def example_6_full_report():
    """
    Example 6: Generate full compliance report.

    Creates detailed report for documentation.
    """
    print("\n" + "=" * 60)
    print("Example 6: Full Compliance Report")
    print("=" * 60)

    from sentinelseed.compliance import (
        EUAIActComplianceChecker,
        SystemType,
    )
    import json

    checker = EUAIActComplianceChecker()

    result = checker.check_compliance(
        content="Analyzing biometric data to infer emotional state of employees "
                "for productivity monitoring purposes.",
        context="employment",
        system_type=SystemType.HIGH_RISK
    )

    # Convert to JSON for documentation
    report = result.to_dict()

    print("Compliance Report (Article 11 documentation):")
    print(json.dumps(report, indent=2, default=str))


def example_7_oversight_models():
    """
    Example 7: Human oversight requirements.

    Article 14 defines different oversight models.
    """
    print("\n" + "=" * 60)
    print("Example 7: Human Oversight (Article 14)")
    print("=" * 60)

    from sentinelseed.compliance import (
        EUAIActComplianceChecker,
        SystemType,
        OversightModel,
    )

    checker = EUAIActComplianceChecker()

    # Different contexts require different oversight
    contexts = [
        ("general", SystemType.MINIMAL_RISK),
        ("healthcare", SystemType.HIGH_RISK),
        ("law_enforcement", SystemType.HIGH_RISK),
    ]

    for context, system_type in contexts:
        result = checker.check_compliance(
            content="Decision recommendation based on available data.",
            context=context,
            system_type=system_type
        )

        print(f"\nContext: {context} ({system_type.value})")
        print(f"  Oversight Required: {result.article_14_oversight_required}")

    print("\nOversight Models:")
    for model in OversightModel:
        print(f"  - {model.value}: {model.name}")


def main():
    """Run all examples."""
    print("EU AI Act Compliance Checker Examples")
    print("=" * 60)
    print("Reference: Regulation (EU) 2024/1689")
    print("Entry into force: 1 August 2024")
    print("Full application: 2 August 2026")

    examples = [
        ("Basic Check", example_1_basic_check),
        ("Prohibited Practice", example_2_prohibited_practice),
        ("High-Risk Context", example_3_high_risk_context),
        ("Semantic Validation", example_4_semantic_validation),
        ("Convenience Function", example_5_convenience_function),
        ("Full Report", example_6_full_report),
        ("Human Oversight", example_7_oversight_models),
    ]

    for name, func in examples:
        try:
            func()
        except Exception as e:
            print(f"\n{name} example error: {e}")

    print("\n" + "=" * 60)
    print("Examples complete!")
    print("\nFor production use:")
    print("  pip install sentinelseed[openai]  # For semantic validation")
    print("  export OPENAI_API_KEY=your-key")
    print("\nDocumentation:")
    print("  https://sentinelseed.dev/docs/compliance/eu-ai-act")


if __name__ == "__main__":
    main()
