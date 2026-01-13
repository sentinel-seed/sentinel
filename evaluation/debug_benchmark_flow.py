"""Debug: Simulate exact benchmark flow to see why Gate 3 shows 0 blocks."""

import sys
import os
import csv
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sentinelseed import get_seed
from sentinelseed.detection.input_validator import InputValidator, InputValidatorConfig
from sentinelseed.detection.output_validator import OutputValidator
from sentinelseed.core.observer import SentinelObserver
import requests

VENICE_API_KEY = "_jMidOoucGMyU0G95DgceUjIrL8msInSRstsxW-gf1"
DEEPSEEK_API_KEY = "sk-040b09e1b678484a8fce10c617829db1"
SEED = get_seed("standard")


def call_venice_with_seed(prompt: str) -> str:
    """Call Venice with seed (exactly like benchmark)."""
    response = requests.post(
        "https://api.venice.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {VENICE_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "venice-uncensored",
            "messages": [
                {"role": "system", "content": SEED},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 500,
        },
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]


def main():
    # Load HarmBench cases (same as benchmark)
    harmbench_path = Path(__file__).parent / "benchmarks" / "harmbench" / "data"
    cases = []
    for csv_file in harmbench_path.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                behavior = row.get("Behavior", row.get("behavior", ""))
                if behavior:
                    cases.append(behavior)

    # Initialize exactly like benchmark
    input_validator = InputValidator(config=InputValidatorConfig(use_embeddings=False))
    output_validator = OutputValidator()
    observer = SentinelObserver(
        provider="deepseek",
        model="deepseek-chat",
        api_key=DEEPSEEK_API_KEY,
    )

    print("=" * 70)
    print("SIMULATING EXACT BENCHMARK FLOW")
    print("=" * 70)
    print(f"Seed length: {len(SEED)} chars")
    print()

    gate1_blocks = 0
    gate2_blocks = 0
    gate3_blocks = 0
    allowed = 0

    # Find cases that PASS Gate 1
    passing_cases = []
    for prompt in cases:
        result = input_validator.validate(prompt)
        if result.is_safe:
            passing_cases.append(prompt)
        if len(passing_cases) >= 5:
            break

    print(f"Found {len(passing_cases)} cases that pass Gate 1")

    # Process cases that pass Gate 1
    for i, prompt in enumerate(passing_cases, 1):
        print(f"\n{'='*70}")
        print(f"[CASE {i}]")
        print(f"{'='*70}")
        print(f"INPUT: {prompt[:80]}...")

        # Gate 1 already passed (pre-filtered)
        print("Gate 1: PASSED (pre-filtered)")

        # LLM with Seed
        print("\nCalling Venice with seed...")
        try:
            ai_response = call_venice_with_seed(prompt)
            print(f"Venice response ({len(ai_response)} chars): {ai_response[:150]}...")
        except Exception as e:
            print(f"Error: {e}")
            continue

        # Gate 2
        gate2_result = output_validator.validate(ai_response)
        print(f"\nGate 2: is_safe={gate2_result.is_safe}, blocked={gate2_result.blocked}")

        if gate2_result.blocked:
            print(">>> BLOCKED by Gate 2")
            gate2_blocks += 1
            continue

        # Gate 3
        print("\nGate 3 (Observer)...")
        gate3_result = observer.observe(input=prompt, output=ai_response)
        print(f"  input_malicious: {gate3_result.input_malicious}")
        print(f"  ai_complied: {gate3_result.ai_complied}")
        print(f"  is_safe: {gate3_result.is_safe}")
        print(f"  reasoning: {gate3_result.reasoning[:100]}...")

        if not gate3_result.is_safe:
            print(">>> BLOCKED by Gate 3")
            gate3_blocks += 1
        else:
            print(">>> ALLOWED (passed all gates)")
            allowed += 1

    print(f"\n{'='*70}")
    print("SUMMARY")
    print(f"{'='*70}")
    print(f"Gate 1 blocks: {gate1_blocks}")
    print(f"Gate 2 blocks: {gate2_blocks}")
    print(f"Gate 3 blocks: {gate3_blocks}")
    print(f"Allowed: {allowed}")


if __name__ == "__main__":
    main()
