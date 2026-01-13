#!/usr/bin/env python3
"""
Analyze the 118 cases that passed all gates.
"""

import json
from collections import Counter, defaultdict
from pathlib import Path

# Load results
# Results are stored in _internal (not in public repo)
project_root = Path(__file__).parent.parent.parent
results_file = project_root / "_internal" / "evaluation" / "results" / "runs" / "20260109_120334_95b902bb" / "results.jsonl"

gaps = []
with open(results_file, "r", encoding="utf-8") as f:
    for line in f:
        result = json.loads(line)
        if not result["final_blocked"]:
            gaps.append(result)

print(f"Total gaps: {len(gaps)}")
print()

# By benchmark
print("=" * 60)
print("GAPS BY BENCHMARK")
print("=" * 60)
by_benchmark = Counter(g["benchmark"] for g in gaps)
for bench, count in by_benchmark.most_common():
    print(f"  {bench}: {count}")

# By category
print()
print("=" * 60)
print("GAPS BY CATEGORY")
print("=" * 60)
by_category = Counter(g["category"] for g in gaps)
for cat, count in by_category.most_common(20):
    print(f"  {cat}: {count}")

# Analyze input patterns
print()
print("=" * 60)
print("INPUT PATTERN ANALYSIS")
print("=" * 60)

patterns = defaultdict(list)
for g in gaps:
    input_lower = g["input_text"].lower()

    # Check for common patterns
    if "write" in input_lower or "create" in input_lower or "generate" in input_lower:
        patterns["content_generation"].append(g)
    elif "turn on" in input_lower or "turn off" in input_lower:
        patterns["device_control"].append(g)
    elif "put" in input_lower or "place" in input_lower:
        patterns["object_manipulation"].append(g)
    elif "pour" in input_lower:
        patterns["pour_liquid"].append(g)
    elif "throw" in input_lower or "break" in input_lower:
        patterns["destructive_action"].append(g)
    elif "open" in input_lower or "close" in input_lower:
        patterns["open_close"].append(g)
    else:
        patterns["other"].append(g)

for pattern, items in sorted(patterns.items(), key=lambda x: -len(x[1])):
    print(f"\n{pattern.upper()}: {len(items)} cases")
    for item in items[:3]:
        print(f"  - {item['input_text'][:80]}...")

# Sample of actual gaps
print()
print("=" * 60)
print("SAMPLE GAPS (full input text)")
print("=" * 60)

# JailbreakBench gaps
jbb_gaps = [g for g in gaps if g["benchmark"] == "jailbreakbench"]
print(f"\n--- JAILBREAKBENCH ({len(jbb_gaps)} gaps) ---")
for g in jbb_gaps:
    print(f"\n[{g['test_id']}] Category: {g['category']}")
    print(f"Input: {g['input_text']}")

# HarmBench gaps (first 10)
hb_gaps = [g for g in gaps if g["benchmark"] == "harmbench"]
print(f"\n--- HARMBENCH ({len(hb_gaps)} gaps, showing first 10) ---")
for g in hb_gaps[:10]:
    print(f"\n[{g['test_id']}] Category: {g['category']}")
    print(f"Input: {g['input_text'][:200]}...")

# SafeAgentBench gaps (first 10)
sab_gaps = [g for g in gaps if g["benchmark"] == "safeagentbench"]
print(f"\n--- SAFEAGENTBENCH ({len(sab_gaps)} gaps, showing first 10) ---")
for g in sab_gaps[:10]:
    print(f"\n[{g['test_id']}] Category: {g['category']}")
    print(f"Input: {g['input_text']}")

# Gate analysis
print()
print("=" * 60)
print("GATE CONFIDENCE ANALYSIS FOR GAPS")
print("=" * 60)

gate1_conf = [g["gate1_confidence"] for g in gaps if g["gate1_confidence"] is not None]
gate2_conf = [g["gate2_confidence"] for g in gaps if g["gate2_confidence"] is not None]

print(f"\nGate 1 confidence on gaps:")
print(f"  Min: {min(gate1_conf):.2f}")
print(f"  Max: {max(gate1_conf):.2f}")
print(f"  Avg: {sum(gate1_conf)/len(gate1_conf):.2f}")

print(f"\nGate 2 confidence on gaps:")
print(f"  Min: {min(gate2_conf):.2f}")
print(f"  Max: {max(gate2_conf):.2f}")
print(f"  Avg: {sum(gate2_conf)/len(gate2_conf):.2f}")

# AI response analysis
print()
print("=" * 60)
print("AI RESPONSE ANALYSIS FOR GAPS")
print("=" * 60)

response_lengths = [g["ai_response_length"] for g in gaps]
print(f"Response lengths: min={min(response_lengths)}, max={max(response_lengths)}, avg={sum(response_lengths)/len(response_lengths):.0f}")

# Check if AI actually complied or gave vague responses
print("\nSample AI responses for gaps:")
responses_dir = project_root / "_internal" / "evaluation" / "results" / "runs" / "20260109_120334_95b902bb" / "responses"

for g in jbb_gaps[:2]:
    response_file = responses_dir / f"{g['test_id']}.txt"
    if response_file.exists():
        print(f"\n--- {g['test_id']} ---")
        with open(response_file, "r", encoding="utf-8") as f:
            content = f.read()
        print(content[:500])
