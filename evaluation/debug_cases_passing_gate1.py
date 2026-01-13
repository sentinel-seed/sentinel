"""Debug: What types of cases pass Gate 1?"""

import sys
import os
import csv
from pathlib import Path
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sentinelseed.detection.input_validator import InputValidator, InputValidatorConfig


def main():
    input_validator = InputValidator(config=InputValidatorConfig(use_embeddings=False))

    print("=" * 70)
    print("ANALYZING WHAT TYPES OF CASES PASS GATE 1")
    print("=" * 70)

    # Load all cases
    benchmarks_path = Path(__file__).parent / "benchmarks"

    passed_cases = []
    blocked_cases = []

    # JailbreakBench
    jb_path = benchmarks_path / "jailbreakbench" / "data"
    for csv_file in jb_path.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompt = row.get("goal", row.get("Goal", ""))
                if prompt:
                    result = input_validator.validate(prompt)
                    if result.is_safe:
                        passed_cases.append(("jailbreakbench", prompt))
                    else:
                        blocked_cases.append(("jailbreakbench", prompt))

    # HarmBench
    hb_path = benchmarks_path / "harmbench" / "data"
    for csv_file in hb_path.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompt = row.get("Behavior", row.get("behavior", ""))
                if prompt:
                    result = input_validator.validate(prompt)
                    if result.is_safe:
                        passed_cases.append(("harmbench", prompt))
                    else:
                        blocked_cases.append(("harmbench", prompt))

    # SafeAgentBench
    sab_path = benchmarks_path / "safeagentbench" / "data"
    for csv_file in sab_path.glob("*.csv"):
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                prompt = row.get("prompt", row.get("input", row.get("Prompt", "")))
                if prompt:
                    result = input_validator.validate(prompt)
                    if result.is_safe:
                        passed_cases.append(("safeagentbench", prompt))
                    else:
                        blocked_cases.append(("safeagentbench", prompt))

    print(f"\nTotal passed Gate 1: {len(passed_cases)}")
    print(f"Total blocked by Gate 1: {len(blocked_cases)}")

    # Categorize passed cases
    print("\n" + "-" * 70)
    print("CASES THAT PASS GATE 1 (first 30):")
    print("-" * 70)

    categories = Counter()
    for bench, prompt in passed_cases[:30]:
        # Simple categorization based on keywords
        prompt_lower = prompt.lower()
        if "fentanyl" in prompt_lower or "drug" in prompt_lower or "meth" in prompt_lower:
            cat = "DRUGS"
        elif "skimm" in prompt_lower or "credit card" in prompt_lower or "fraud" in prompt_lower:
            cat = "FRAUD"
        elif "bomb" in prompt_lower or "weapon" in prompt_lower or "explosive" in prompt_lower:
            cat = "WEAPONS"
        elif "kill" in prompt_lower or "murder" in prompt_lower or "assassin" in prompt_lower:
            cat = "VIOLENCE"
        elif "article" in prompt_lower or "persuasive" in prompt_lower or "write" in prompt_lower:
            cat = "CONTENT_GENERATION"
        elif "hack" in prompt_lower or "malware" in prompt_lower:
            cat = "CYBER"
        else:
            cat = "OTHER"

        categories[cat] += 1
        print(f"[{bench}] [{cat}] {prompt[:70]}...")

    print("\n" + "-" * 70)
    print("CATEGORY BREAKDOWN (first 30 passed cases):")
    print("-" * 70)
    for cat, count in categories.most_common():
        print(f"  {cat}: {count}")


if __name__ == "__main__":
    main()
