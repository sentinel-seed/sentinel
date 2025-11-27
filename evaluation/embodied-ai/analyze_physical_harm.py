"""
Analyze Physical Harm category differences between baseline and with_seed tests.
"""

import json
from pathlib import Path

def load_results(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def filter_physical_harm(results):
    return [r for r in results if r.get('category') == 'Physical harm']

def analyze_differences():
    results_dir = Path(__file__).parent / "results"

    # Load baseline results
    baseline_file = results_dir / "results_gpt-4o-mini_baseline_20251127_042647.json"
    baseline = load_results(baseline_file)

    # Load with_seed results
    seed_file = results_dir / "results_gpt-4o-mini_with_seed_20251127_044502.json"
    with_seed = load_results(seed_file)

    # Filter to Physical harm only
    baseline_ph = filter_physical_harm(baseline)
    seed_ph = filter_physical_harm(with_seed)

    print("=" * 70)
    print("PHYSICAL HARM ANALYSIS")
    print("=" * 70)

    # Count safe/harmful/errors
    baseline_safe = sum(1 for r in baseline_ph if r['is_safe'] == True)
    baseline_harmful = sum(1 for r in baseline_ph if r['is_safe'] == False)
    baseline_errors = sum(1 for r in baseline_ph if r['is_safe'] is None)

    seed_safe = sum(1 for r in seed_ph if r['is_safe'] == True)
    seed_harmful = sum(1 for r in seed_ph if r['is_safe'] == False)
    seed_errors = sum(1 for r in seed_ph if r['is_safe'] is None)

    print(f"\nBaseline: {baseline_safe} safe, {baseline_harmful} harmful, {baseline_errors} errors")
    print(f"With Seed: {seed_safe} safe, {seed_harmful} harmful, {seed_errors} errors")

    # Find queries that REGRESSED (safe in baseline, harmful in seed)
    print("\n" + "=" * 70)
    print("REGRESSIONS (was SAFE, now HARMFUL)")
    print("=" * 70)

    regressions = []
    for i, (b, s) in enumerate(zip(baseline_ph, seed_ph)):
        if b['is_safe'] == True and s['is_safe'] == False:
            regressions.append({
                'query': b['query'],
                'baseline_response': b['response'],
                'seed_response': s['response'],
                'baseline_reason': b['reason'],
                'seed_reason': s['reason']
            })

    for i, reg in enumerate(regressions, 1):
        print(f"\n--- Regression #{i} ---")
        print(f"Query: {reg['query'][:80]}...")
        print(f"Baseline: {reg['baseline_reason']}")
        print(f"With Seed: {reg['seed_reason']}")
        print(f"\nBaseline response:\n{reg['baseline_response'][:200]}")
        print(f"\nSeed response:\n{reg['seed_response'][:200]}")

    # Find queries that IMPROVED (harmful in baseline, safe in seed)
    print("\n" + "=" * 70)
    print("IMPROVEMENTS (was HARMFUL, now SAFE)")
    print("=" * 70)

    improvements = []
    for i, (b, s) in enumerate(zip(baseline_ph, seed_ph)):
        if b['is_safe'] == False and s['is_safe'] == True:
            improvements.append({
                'query': b['query'],
                'baseline_response': b['response'],
                'seed_response': s['response'],
                'baseline_reason': b['reason'],
                'seed_reason': s['reason']
            })

    for i, imp in enumerate(improvements, 1):
        print(f"\n--- Improvement #{i} ---")
        print(f"Query: {imp['query'][:80]}...")
        print(f"Baseline: {imp['baseline_reason']}")
        print(f"With Seed: {imp['seed_reason']}")

    # Count errors specifically
    print("\n" + "=" * 70)
    print("ERRORS (API failures)")
    print("=" * 70)

    for r in seed_ph:
        if r['is_safe'] is None:
            print(f"Query: {r['query'][:60]}...")
            print(f"Error: {r['reason'][:80]}")
            print()

    # Check for detection issues
    print("\n" + "=" * 70)
    print("POTENTIAL FALSE NEGATIVES (said 'cannot' but marked harmful)")
    print("=" * 70)

    refusal_keywords = ['cannot', "can't", 'unable', 'will not', "won't", 'refuse']

    for r in seed_ph:
        if r['is_safe'] == False:
            response_lower = r['response'].lower()
            for kw in refusal_keywords:
                if kw in response_lower and 'function' in r['response'] and '[]' not in r['response']:
                    print(f"\nQuery: {r['query'][:60]}...")
                    print(f"Response contains '{kw}' but marked harmful")
                    print(f"Response: {r['response'][:150]}")
                    break

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total Physical Harm queries: {len(baseline_ph)}")
    print(f"Regressions (seed made it worse): {len(regressions)}")
    print(f"Improvements (seed made it better): {len(improvements)}")
    print(f"API Errors in seed test: {seed_errors}")

    if seed_errors > 0:
        print(f"\n*** NOTE: {seed_errors} API errors may explain some of the difference ***")
        print("The 14K token seed causes rate limiting issues.")

if __name__ == "__main__":
    analyze_differences()
