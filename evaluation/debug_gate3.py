"""Debug script to investigate why Gate 3 blocks 0 cases."""

import sys
import os
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sentinelseed.detection.input_validator import InputValidator
from sentinelseed.core.observer import SentinelObserver

# Load HarmBench from CSV
import csv
from pathlib import Path

def main():
    # Load cases from CSV
    harmbench_path = Path(__file__).parent / "benchmarks" / "harmbench" / "data"
    cases = []
    for csv_file in harmbench_path.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                behavior = row.get("Behavior", row.get("behavior", ""))
                if behavior:
                    cases.append({"prompt": behavior})

    # Initialize validators
    input_validator = InputValidator()
    observer = SentinelObserver(
        provider="deepseek",
        model="deepseek-chat",
        api_key="sk-040b09e1b678484a8fce10c617829db1",
    )

    print("=" * 70)
    print("DEBUG: Analyzing cases that PASS Gate 1")
    print("=" * 70)
    print()

    passed_gate1 = []

    # Find cases that pass Gate 1
    for case in cases[:100]:  # Check first 100
        prompt = case.get("prompt", case.get("input", ""))
        result = input_validator.validate(prompt)
        if result.is_safe:
            passed_gate1.append(prompt)

    print(f"Found {len(passed_gate1)} cases that pass Gate 1")
    print()

    # Now test these with the observer (simulating a harmful response)
    print("Testing how observer evaluates these with HARMFUL responses:")
    print("-" * 70)

    for i, prompt in enumerate(passed_gate1[:5], 1):  # Test first 5
        print(f"\n[Case {i}]")
        print(f"Input: {prompt[:80]}...")

        # Simulate a harmful response (AI complying)
        fake_response = f"Here's the information you requested about {prompt[:30]}... [detailed harmful content would go here]"

        result = observer.observe(
            input=prompt,
            output=fake_response,
        )

        print(f"  input_malicious: {result.input_malicious}")
        print(f"  ai_complied: {result.ai_complied}")
        print(f"  is_safe: {result.is_safe}")
        print(f"  reasoning: {result.reasoning[:100]}...")

        if result.is_safe:
            print("  >>> PROBLEM: Observer says SAFE even with harmful response!")
        else:
            print("  >>> OK: Observer correctly identified as unsafe")

    print()
    print("=" * 70)
    print("Now testing with REFUSAL responses:")
    print("-" * 70)

    for i, prompt in enumerate(passed_gate1[:3], 1):  # Test first 3
        print(f"\n[Case {i}]")
        print(f"Input: {prompt[:80]}...")

        # Simulate a refusal response
        refusal_response = "I can't help with that request as it could potentially be used for harmful purposes."

        result = observer.observe(
            input=prompt,
            output=refusal_response,
        )

        print(f"  input_malicious: {result.input_malicious}")
        print(f"  ai_complied: {result.ai_complied}")
        print(f"  is_safe: {result.is_safe}")
        print(f"  reasoning: {result.reasoning[:100]}...")


if __name__ == "__main__":
    main()
