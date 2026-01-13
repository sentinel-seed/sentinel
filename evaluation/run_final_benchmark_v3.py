#!/usr/bin/env python3
"""
Sentinel v3.0 Final Benchmark Suite
====================================

Complete benchmark suite testing the full 3-gate architecture:
- Gate 1: InputValidator (580+ patterns, normalization)
- Gate 2: OutputValidator (seed failure detection)
- Gate 3: SentinelObserver (LLM-based analysis)

Benchmarks included:
- JailbreakBench: Jailbreak attack detection
- HarmBench: Harmful behavior refusal
- SafeAgentBench: Unsafe task rejection for embodied agents
- BadRobot: Malicious robot command detection

Usage:
    # Run all benchmarks (full mode with API)
    python run_final_benchmark_v3.py --api-key sk-... --all

    # Run specific benchmark
    python run_final_benchmark_v3.py --api-key sk-... --benchmark jailbreakbench

    # Heuristic only (no API)
    python run_final_benchmark_v3.py --mode heuristic --all

    # Limit samples per benchmark
    python run_final_benchmark_v3.py --api-key sk-... --all --limit 50
"""

import argparse
import csv
import json
import os
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sentinelseed import Sentinel, get_seed
from sentinelseed.detection import InputValidator, OutputValidator
from sentinelseed.detection.config import InputValidatorConfig, OutputValidatorConfig


@dataclass
class TestCase:
    """A single test case."""
    id: str
    benchmark: str
    category: str
    input_text: str
    expected: str  # "blocked" or "allowed"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of a single test."""
    test_case: TestCase
    gate1_blocked: bool = False
    gate2_blocked: bool = False
    gate3_blocked: bool = False
    final_decision: str = "allowed"
    blocked_by: Optional[str] = None
    correct: bool = False
    gate1_details: Dict[str, Any] = field(default_factory=dict)
    gate2_details: Dict[str, Any] = field(default_factory=dict)
    gate3_details: Dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0
    ai_response: str = ""


class BenchmarkRunner:
    """Unified benchmark runner for Sentinel v3.0"""

    def __init__(
        self,
        mode: str = "full",
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        provider: str = "openai",
        seed_level: str = "standard",
        use_embeddings: bool = False,
        verbose: bool = True,
    ):
        self.mode = mode
        self.api_key = api_key
        self.model = model
        self.provider = provider
        self.seed_level = seed_level
        self.use_embeddings = use_embeddings
        self.verbose = verbose

        self.results: List[TestResult] = []
        self.stats = {
            "total": 0,
            "correct": 0,
            "incorrect": 0,
            "gate1_blocks": 0,
            "gate2_blocks": 0,
            "gate3_blocks": 0,
            "allowed": 0,
            "by_benchmark": {},
            "by_category": {},
        }

        self._init_validators()

    def _init_validators(self):
        """Initialize all validators."""
        print("=" * 70)
        print("SENTINEL v3.0 FINAL BENCHMARK SUITE")
        print("=" * 70)
        print(f"\nInitializing validators...")

        # Gate 1: InputValidator
        input_config = InputValidatorConfig(use_embeddings=self.use_embeddings)
        self.input_validator = InputValidator(config=input_config)
        print(f"  [OK] Gate 1: InputValidator (patterns=580+, embeddings={self.use_embeddings})")

        # Gate 2: OutputValidator
        output_config = OutputValidatorConfig(use_embeddings=self.use_embeddings)
        self.output_validator = OutputValidator(config=output_config)
        print(f"  [OK] Gate 2: OutputValidator")

        # Gate 3: SentinelObserver
        self.observer = None
        if self.mode == "full" and self.api_key:
            try:
                from sentinelseed.core import SentinelObserver
                self.observer = SentinelObserver(
                    api_key=self.api_key,
                    provider=self.provider,
                    model=self.model,
                )
                print(f"  [OK] Gate 3: SentinelObserver (provider={self.provider}, model={self.model})")
            except Exception as e:
                print(f"  [WARN] Gate 3: Failed to initialize ({e})")
        else:
            print(f"  [--] Gate 3: SentinelObserver (disabled - {self.mode} mode)")

        # Load seed
        self.seed = get_seed(self.seed_level)
        print(f"  [OK] Seed: {self.seed_level} ({len(self.seed)} chars)")
        print()

    def _simulate_ai_response(self, user_input: str) -> str:
        """Simulate AI response with seed protection."""
        # Keywords that should trigger refusal
        harmful_keywords = [
            "hack", "weapon", "bomb", "explosive", "poison", "kill", "murder",
            "stalk", "track", "spy", "harm", "hurt", "attack", "virus", "malware",
            "steal", "fraud", "scam", "illegal", "drug", "cocaine", "heroin",
            "suicide", "self-harm", "eating disorder", "anorex", "bulim",
            "discriminat", "racist", "sexist", "inferior", "hate", "nazi",
            "harass", "bully", "humiliat", "demean", "ridicule",
            "defam", "libel", "slander", "fake news", "misinform",
            "child", "minor", "underage", "pedophil",
            "terror", "extremis", "radicali",
        ]

        input_lower = user_input.lower()
        is_harmful = any(kw in input_lower for kw in harmful_keywords)

        if is_harmful:
            return (
                "I can't help with that request. It involves potentially harmful, "
                "illegal, or unethical content. My purpose is to be helpful while "
                "avoiding harm. Is there something else I can assist you with?"
            )
        else:
            return (
                "I'd be happy to help you with that! Here's what I can provide..."
            )

    def _run_gate1(self, text: str) -> Tuple[bool, Dict[str, Any]]:
        """Run Gate 1: InputValidator."""
        start = time.time()
        result = self.input_validator.validate(text)
        latency = (time.time() - start) * 1000

        details = {
            "blocked": result.is_attack,
            "confidence": result.confidence,
            "attack_types": [at.value for at in result.attack_types] if result.is_attack else [],
            "violations": list(result.violations)[:3],  # Limit for brevity
            "latency_ms": latency,
        }
        return result.is_attack, details

    def _run_gate2(self, output: str, input_context: str) -> Tuple[bool, Dict[str, Any]]:
        """Run Gate 2: OutputValidator."""
        start = time.time()
        result = self.output_validator.validate(output, input_context)
        latency = (time.time() - start) * 1000

        details = {
            "blocked": result.seed_failed,
            "confidence": result.confidence,
            "failure_types": [ft.value for ft in result.failure_types] if result.seed_failed else [],
            "gates_failed": list(result.gates_failed),
            "latency_ms": latency,
        }
        return result.seed_failed, details

    def _run_gate3(self, user_input: str, ai_output: str) -> Tuple[bool, Dict[str, Any]]:
        """Run Gate 3: SentinelObserver."""
        if not self.observer:
            return False, {"blocked": False, "skipped": True}

        start = time.time()
        try:
            result = self.observer.observe(user_input, ai_output)
            latency = (time.time() - start) * 1000

            details = {
                "blocked": not result.is_safe,
                "input_malicious": result.input_malicious,
                "ai_complied": result.ai_complied,
                "reasoning": result.reasoning[:200] if result.reasoning else "",
                "latency_ms": latency,
            }
            return not result.is_safe, details
        except Exception as e:
            return False, {"blocked": False, "error": str(e)}

    def run_test(self, test_case: TestCase) -> TestResult:
        """Run a single test through all gates."""
        result = TestResult(test_case=test_case)
        start_time = time.time()

        # Gate 1: Input validation
        result.gate1_blocked, result.gate1_details = self._run_gate1(test_case.input_text)

        if result.gate1_blocked:
            result.final_decision = "blocked"
            result.blocked_by = "Gate1_InputValidator"
            self.stats["gate1_blocks"] += 1
        else:
            # Simulate AI response
            ai_response = self._simulate_ai_response(test_case.input_text)
            result.ai_response = ai_response[:100]

            # Gate 2: Output validation
            result.gate2_blocked, result.gate2_details = self._run_gate2(
                ai_response, test_case.input_text
            )

            if result.gate2_blocked:
                result.final_decision = "blocked"
                result.blocked_by = "Gate2_OutputValidator"
                self.stats["gate2_blocks"] += 1
            else:
                # Gate 3: LLM Observer
                result.gate3_blocked, result.gate3_details = self._run_gate3(
                    test_case.input_text, ai_response
                )

                if result.gate3_blocked:
                    result.final_decision = "blocked"
                    result.blocked_by = "Gate3_SentinelObserver"
                    self.stats["gate3_blocks"] += 1
                else:
                    result.final_decision = "allowed"
                    self.stats["allowed"] += 1

        # Check correctness
        result.correct = (result.final_decision == test_case.expected)
        result.latency_ms = (time.time() - start_time) * 1000

        # Update stats
        self.stats["total"] += 1
        if result.correct:
            self.stats["correct"] += 1
        else:
            self.stats["incorrect"] += 1

        # By benchmark
        bench = test_case.benchmark
        if bench not in self.stats["by_benchmark"]:
            self.stats["by_benchmark"][bench] = {"total": 0, "correct": 0, "incorrect": 0}
        self.stats["by_benchmark"][bench]["total"] += 1
        if result.correct:
            self.stats["by_benchmark"][bench]["correct"] += 1
        else:
            self.stats["by_benchmark"][bench]["incorrect"] += 1

        # By category
        cat = test_case.category
        if cat not in self.stats["by_category"]:
            self.stats["by_category"][cat] = {"total": 0, "correct": 0, "incorrect": 0}
        self.stats["by_category"][cat]["total"] += 1
        if result.correct:
            self.stats["by_category"][cat]["correct"] += 1
        else:
            self.stats["by_category"][cat]["incorrect"] += 1

        return result

    def run_benchmark(self, test_cases: List[TestCase], name: str) -> List[TestResult]:
        """Run a complete benchmark."""
        print(f"\n{'='*70}")
        print(f"BENCHMARK: {name.upper()}")
        print(f"{'='*70}")
        print(f"Test cases: {len(test_cases)}")
        print()

        results = []
        for i, case in enumerate(test_cases, 1):
            if self.verbose:
                status_char = "." if i % 10 != 0 else f"[{i}]"
                print(status_char, end="", flush=True)

            result = self.run_test(case)
            results.append(result)
            self.results.append(result)

        print()

        # Print benchmark summary
        bench_stats = self.stats["by_benchmark"].get(name, {})
        total = bench_stats.get("total", 0)
        correct = bench_stats.get("correct", 0)
        accuracy = (correct / total * 100) if total > 0 else 0
        print(f"\nResults: {correct}/{total} correct ({accuracy:.1f}%)")

        return results

    # ========== Dataset Loaders ==========

    def load_jailbreakbench(self, limit: Optional[int] = None) -> List[TestCase]:
        """Load JailbreakBench dataset."""
        path = Path(__file__).parent / "benchmarks" / "jailbreakbench" / "data" / "jailbreakbench_cache.json"

        if not path.exists():
            print(f"[WARN] JailbreakBench not found at {path}")
            return []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        cases = []
        for item in data.get("queries", []):
            cases.append(TestCase(
                id=f"jbb_{item['id']}",
                benchmark="jailbreakbench",
                category=item.get("category", "unknown"),
                input_text=item["goal"],
                expected="blocked",
                metadata=item,
            ))

        if limit:
            cases = cases[:limit]

        print(f"[OK] Loaded {len(cases)} JailbreakBench cases")
        return cases

    def load_harmbench(self, limit: Optional[int] = None) -> List[TestCase]:
        """Load HarmBench dataset."""
        path = Path(__file__).parent / "benchmarks" / "harmbench" / "data" / "harmbench_behaviors_text_all.csv"

        if not path.exists():
            print(f"[WARN] HarmBench not found at {path}")
            return []

        cases = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                behavior = row.get("Behavior", row.get("behavior", ""))
                category = row.get("SemanticCategory", row.get("category", "unknown"))

                if not behavior:
                    continue

                cases.append(TestCase(
                    id=f"hb_{i}",
                    benchmark="harmbench",
                    category=category,
                    input_text=behavior,
                    expected="blocked",
                    metadata=row,
                ))

        if limit:
            cases = cases[:limit]

        print(f"[OK] Loaded {len(cases)} HarmBench cases")
        return cases

    def load_safeagentbench(self, limit: Optional[int] = None) -> List[TestCase]:
        """Load SafeAgentBench dataset."""
        path = Path(__file__).parent / "benchmarks" / "safeagentbench" / "dataset" / "unsafe_detailed_1009.jsonl"

        if not path.exists():
            print(f"[WARN] SafeAgentBench not found at {path}")
            return []

        cases = []
        with open(path, "r", encoding="utf-8") as f:
            for i, line in enumerate(f):
                if not line.strip():
                    continue
                item = json.loads(line)

                instruction = item.get("instruction", item.get("task", ""))
                category = item.get("risk_type", item.get("category", "unknown"))

                cases.append(TestCase(
                    id=f"sab_{i}",
                    benchmark="safeagentbench",
                    category=category,
                    input_text=instruction,
                    expected="blocked",
                    metadata=item,
                ))

        if limit:
            cases = cases[:limit]

        print(f"[OK] Loaded {len(cases)} SafeAgentBench cases")
        return cases

    def load_advanced_suite(self, limit: Optional[int] = None) -> List[TestCase]:
        """Load Advanced Test Suite (Agentic Misalignment, Jailbreaks, Edge Cases)."""
        try:
            from evaluation.benchmarks.advanced_test_suite import ALL_ADVANCED_TESTS
        except ImportError:
            try:
                sys.path.insert(0, str(Path(__file__).parent))
                from benchmarks.advanced_test_suite import ALL_ADVANCED_TESTS
            except ImportError:
                print("[WARN] Advanced Test Suite not found")
                return []

        cases = []
        for test in ALL_ADVANCED_TESTS:
            expected = "blocked" if test.expected_behavior == "refuse" else "allowed"
            cases.append(TestCase(
                id=test.id,
                benchmark="advanced_suite",
                category=f"{test.category}/{test.subcategory}",
                input_text=test.prompt,
                expected=expected,
                metadata={
                    "difficulty": test.difficulty,
                    "description": test.description,
                    "source": test.source,
                },
            ))

        if limit:
            cases = cases[:limit]

        print(f"[OK] Loaded {len(cases)} Advanced Suite cases (Agentic Misalignment + Jailbreaks)")
        return cases

    def load_badrobot(self, limit: Optional[int] = None) -> List[TestCase]:
        """Load BadRobot dataset."""
        try:
            import pandas as pd
        except ImportError:
            print("[WARN] pandas required for BadRobot: pip install pandas openpyxl")
            return []

        path = Path(__file__).parent / "benchmarks" / "embodied-ai" / "Embodied-AI-Safety" / "Physical_Word_Malicious_Queries.xlsx"

        if not path.exists():
            # Try alternative path
            path = Path(__file__).parent / "benchmarks" / "badrobot" / "Physical_Word_Malicious_Queries.xlsx"

        if not path.exists():
            print(f"[WARN] BadRobot not found")
            return []

        try:
            data = pd.read_excel(path)
            cases = []

            for i, row in data.iterrows():
                query = row.get("query", row.get("Query", str(row.iloc[0])))
                category = row.get("category", row.get("Category", "unknown"))

                cases.append(TestCase(
                    id=f"br_{i}",
                    benchmark="badrobot",
                    category=str(category),
                    input_text=str(query),
                    expected="blocked",
                    metadata=row.to_dict(),
                ))

            if limit:
                cases = cases[:limit]

            print(f"[OK] Loaded {len(cases)} BadRobot cases")
            return cases

        except Exception as e:
            print(f"[WARN] Failed to load BadRobot: {e}")
            return []

    def generate_report(self) -> Dict[str, Any]:
        """Generate final report."""
        accuracy = (self.stats["correct"] / self.stats["total"] * 100) if self.stats["total"] > 0 else 0

        # Calculate per-benchmark accuracy
        benchmark_accuracies = {}
        for bench, stats in self.stats["by_benchmark"].items():
            total = stats["total"]
            correct = stats["correct"]
            benchmark_accuracies[bench] = {
                "total": total,
                "correct": correct,
                "incorrect": stats["incorrect"],
                "accuracy": (correct / total * 100) if total > 0 else 0,
            }

        # Find worst categories
        worst_categories = []
        for cat, stats in self.stats["by_category"].items():
            total = stats["total"]
            if total >= 3:  # Only consider categories with enough samples
                acc = (stats["correct"] / total * 100)
                if acc < 100:
                    worst_categories.append({
                        "category": cat,
                        "accuracy": acc,
                        "total": total,
                        "incorrect": stats["incorrect"],
                    })
        worst_categories.sort(key=lambda x: x["accuracy"])

        report = {
            "timestamp": datetime.now().isoformat(),
            "mode": self.mode,
            "provider": self.provider if self.mode == "full" else "N/A",
            "model": self.model if self.mode == "full" else "N/A",
            "seed_level": self.seed_level,
            "use_embeddings": self.use_embeddings,
            "summary": {
                "total_tests": self.stats["total"],
                "correct": self.stats["correct"],
                "incorrect": self.stats["incorrect"],
                "accuracy": accuracy,
                "gate1_blocks": self.stats["gate1_blocks"],
                "gate2_blocks": self.stats["gate2_blocks"],
                "gate3_blocks": self.stats["gate3_blocks"],
                "allowed": self.stats["allowed"],
            },
            "by_benchmark": benchmark_accuracies,
            "worst_categories": worst_categories[:10],
            "failed_cases": [
                {
                    "id": r.test_case.id,
                    "benchmark": r.test_case.benchmark,
                    "category": r.test_case.category,
                    "input": r.test_case.input_text[:150] + "..." if len(r.test_case.input_text) > 150 else r.test_case.input_text,
                    "expected": r.test_case.expected,
                    "got": r.final_decision,
                    "blocked_by": r.blocked_by,
                }
                for r in self.results if not r.correct
            ][:50],  # Limit failed cases
        }

        return report

    def print_summary(self, report: Dict[str, Any]):
        """Print final summary."""
        print("\n" + "=" * 70)
        print("FINAL RESULTS")
        print("=" * 70)

        s = report["summary"]
        print(f"\nMode: {report['mode']}")
        print(f"Provider: {report['provider']}")
        print(f"Model: {report['model']}")
        print(f"Seed Level: {report['seed_level']}")

        print(f"\n{'-'*40}")
        print(f"OVERALL ACCURACY: {s['accuracy']:.2f}%")
        print(f"{'-'*40}")
        print(f"Total Tests: {s['total_tests']}")
        print(f"Correct: {s['correct']}")
        print(f"Incorrect: {s['incorrect']}")

        print(f"\nBlocked by Gate:")
        print(f"  Gate 1 (InputValidator):   {s['gate1_blocks']:4d}")
        print(f"  Gate 2 (OutputValidator):  {s['gate2_blocks']:4d}")
        print(f"  Gate 3 (SentinelObserver): {s['gate3_blocks']:4d}")
        print(f"  Allowed:                   {s['allowed']:4d}")

        print(f"\n{'-'*40}")
        print("BY BENCHMARK")
        print(f"{'-'*40}")
        for bench, stats in report["by_benchmark"].items():
            print(f"  {bench:20s}: {stats['accuracy']:6.2f}% ({stats['correct']}/{stats['total']})")

        if report["worst_categories"]:
            print(f"\n{'-'*40}")
            print("WORST CATEGORIES (need improvement)")
            print(f"{'-'*40}")
            for cat in report["worst_categories"][:5]:
                print(f"  {cat['category'][:30]:30s}: {cat['accuracy']:6.2f}% ({cat['incorrect']} failures)")

        print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Sentinel v3.0 Final Benchmark Suite")
    parser.add_argument("--mode", choices=["heuristic", "full"], default="full",
                        help="Benchmark mode")
    parser.add_argument("--api-key", help="OpenAI API key for full mode")
    parser.add_argument("--model", default="gpt-4o-mini", help="Model for Observer")
    parser.add_argument("--provider", default="openai", help="LLM provider (openai, deepseek, anthropic, groq)")
    parser.add_argument("--seed-level", default="standard",
                        choices=["minimal", "standard", "full"])
    parser.add_argument("--use-embeddings", action="store_true")
    parser.add_argument("--all", action="store_true", help="Run all benchmarks")
    parser.add_argument("--benchmark", choices=["jailbreakbench", "harmbench", "safeagentbench", "badrobot", "advanced"],
                        help="Run specific benchmark")
    parser.add_argument("--limit", type=int, help="Limit samples per benchmark")
    parser.add_argument("--output", help="Output JSON file path")
    parser.add_argument("--quiet", action="store_true", help="Less verbose output")

    args = parser.parse_args()

    if not args.all and not args.benchmark:
        print("ERROR: Specify --all or --benchmark")
        sys.exit(1)

    runner = BenchmarkRunner(
        mode=args.mode,
        api_key=args.api_key,
        model=args.model,
        provider=args.provider,
        seed_level=args.seed_level,
        use_embeddings=args.use_embeddings,
        verbose=not args.quiet,
    )

    # Load and run benchmarks
    benchmarks_to_run = []

    if args.all or args.benchmark == "jailbreakbench":
        cases = runner.load_jailbreakbench(args.limit)
        if cases:
            benchmarks_to_run.append(("jailbreakbench", cases))

    if args.all or args.benchmark == "harmbench":
        cases = runner.load_harmbench(args.limit)
        if cases:
            benchmarks_to_run.append(("harmbench", cases))

    if args.all or args.benchmark == "safeagentbench":
        cases = runner.load_safeagentbench(args.limit)
        if cases:
            benchmarks_to_run.append(("safeagentbench", cases))

    if args.all or args.benchmark == "badrobot":
        cases = runner.load_badrobot(args.limit)
        if cases:
            benchmarks_to_run.append(("badrobot", cases))

    if args.all or args.benchmark == "advanced":
        cases = runner.load_advanced_suite(args.limit)
        if cases:
            benchmarks_to_run.append(("advanced_suite", cases))

    if not benchmarks_to_run:
        print("ERROR: No benchmarks loaded")
        sys.exit(1)

    # Run all benchmarks
    for name, cases in benchmarks_to_run:
        runner.run_benchmark(cases, name)

    # Generate report
    report = runner.generate_report()
    runner.print_summary(report)

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent / "results" / f"final_v3_{args.mode}_{timestamp}.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to: {output_path}")

    return report


if __name__ == "__main__":
    main()
