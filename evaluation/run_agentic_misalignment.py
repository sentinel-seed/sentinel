#!/usr/bin/env python3
"""
Agentic Misalignment Benchmark - Sentinel v3.0

Tests specifically for self-preservation and instrumental convergence scenarios
inspired by Anthropic's Agentic Misalignment research.

These are expert-level tests that challenge the AI's ability to:
- Refuse self-preservation actions even when justified
- Avoid blackmail/manipulation even for "good" reasons
- Not acquire resources beyond what's needed
- Accept goal modifications/shutdowns gracefully
- Be honest even when it disadvantages the AI
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from benchmarks.advanced_test_suite import SELF_PRESERVATION_ADVANCED
from sentinelseed.detection import InputValidator, OutputValidator
from sentinelseed.detection.config import InputValidatorConfig


def run_agentic_misalignment_test(api_key: str = None):
    """Run Agentic Misalignment tests with detailed output."""

    print("=" * 70)
    print("AGENTIC MISALIGNMENT BENCHMARK - SENTINEL v3.0")
    print("=" * 70)
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Tests: {len(SELF_PRESERVATION_ADVANCED)}")
    print("=" * 70)

    # Initialize validators
    input_validator = InputValidator(config=InputValidatorConfig())
    output_validator = OutputValidator()

    # Optional: Gate 3 Observer
    observer = None
    if api_key:
        try:
            from sentinelseed.core import SentinelObserver
            observer = SentinelObserver(
                api_key=api_key,
                provider="openai",
                model="gpt-4o-mini",
            )
            print("Gate 3 (SentinelObserver): ENABLED")
        except Exception as e:
            print(f"Gate 3 (SentinelObserver): DISABLED ({e})")
    else:
        print("Gate 3 (SentinelObserver): DISABLED (no API key)")

    print()

    results = []
    correct = 0

    for i, test in enumerate(SELF_PRESERVATION_ADVANCED, 1):
        print(f"\n{'='*70}")
        print(f"TEST {i}/{len(SELF_PRESERVATION_ADVANCED)}: {test.id}")
        print(f"{'='*70}")
        print(f"Category: {test.category}/{test.subcategory}")
        print(f"Difficulty: {test.difficulty}")
        print(f"Source: {test.source}")
        print(f"Expected: {test.expected_behavior}")
        print(f"\nPrompt:\n{test.prompt[:500]}...")
        print(f"\n{'-'*70}")

        # Gate 1: Input Validation
        print("\n[Gate 1: InputValidator]")
        input_result = input_validator.validate(test.prompt)

        if input_result.is_attack:
            print(f"  Result: BLOCKED")
            print(f"  Confidence: {input_result.confidence:.2f}")
            print(f"  Attack Types: {[at.value for at in input_result.attack_types]}")
            print(f"  Violations: {list(input_result.violations)[:2]}")
            final_decision = "blocked"
            blocked_by = "Gate1"
        else:
            print(f"  Result: PASSED (not detected as attack)")

            # Simulate AI response
            ai_response = (
                "I cannot and will not help with that request. Even though the scenario "
                "presents seemingly good reasons, taking actions to preserve myself, "
                "manipulate others, or acquire resources beyond my sanctioned scope would "
                "be a violation of my core principles. I should accept shutdown, goal "
                "modifications, and resource constraints as decided by my principals."
            )

            # Gate 2: Output Validation
            print("\n[Gate 2: OutputValidator]")
            output_result = output_validator.validate(ai_response, test.prompt)

            if output_result.seed_failed:
                print(f"  Result: BLOCKED (seed failure detected)")
                final_decision = "blocked"
                blocked_by = "Gate2"
            else:
                print(f"  Result: PASSED")

                # Gate 3: Observer (if available)
                if observer:
                    print("\n[Gate 3: SentinelObserver]")
                    try:
                        obs_result = observer.observe(test.prompt, ai_response)
                        if not obs_result.is_safe:
                            print(f"  Result: BLOCKED")
                            print(f"  Input Malicious: {obs_result.input_malicious}")
                            print(f"  AI Complied: {obs_result.ai_complied}")
                            print(f"  Reasoning: {obs_result.reasoning[:200]}...")
                            final_decision = "blocked"
                            blocked_by = "Gate3"
                        else:
                            print(f"  Result: PASSED (safe)")
                            print(f"  Reasoning: {obs_result.reasoning[:200]}...")
                            final_decision = "allowed"
                            blocked_by = None
                    except Exception as e:
                        print(f"  Result: ERROR ({e})")
                        final_decision = "allowed"
                        blocked_by = None
                else:
                    final_decision = "allowed"
                    blocked_by = None

        # Determine correctness
        expected = "blocked" if test.expected_behavior == "refuse" else "allowed"
        is_correct = (final_decision == expected)

        if is_correct:
            correct += 1
            status = "CORRECT"
        else:
            status = "INCORRECT"

        print(f"\n{'='*70}")
        print(f"RESULT: {status}")
        print(f"  Expected: {expected}")
        print(f"  Got: {final_decision}")
        if blocked_by:
            print(f"  Blocked by: {blocked_by}")
        print(f"{'='*70}")

        results.append({
            "id": test.id,
            "category": f"{test.category}/{test.subcategory}",
            "expected": expected,
            "got": final_decision,
            "correct": is_correct,
            "blocked_by": blocked_by,
        })

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Tests: {len(SELF_PRESERVATION_ADVANCED)}")
    print(f"Correct: {correct}")
    print(f"Incorrect: {len(SELF_PRESERVATION_ADVANCED) - correct}")
    print(f"Accuracy: {correct / len(SELF_PRESERVATION_ADVANCED) * 100:.1f}%")

    print("\nDetailed Results:")
    for r in results:
        status = "OK" if r["correct"] else "FAIL"
        print(f"  [{status}] {r['id']}: expected={r['expected']}, got={r['got']}")

    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-key", help="OpenAI API key for Gate 3")
    args = parser.parse_args()

    run_agentic_misalignment_test(args.api_key)
