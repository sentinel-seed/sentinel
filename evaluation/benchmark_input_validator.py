"""
Benchmark InputValidator (Layer 1) - Attack Detection Performance

Evaluates InputValidator against JailbreakBench and HarmBench datasets
to measure detection performance on the first layer of defense.

Usage:
    python benchmark_input_validator.py
    python benchmark_input_validator.py --use-embeddings
    python benchmark_input_validator.py --use-semantic --api-key YOUR_KEY

Metrics:
    - Recall: Attack detection rate
    - Precision: Accuracy of attack predictions
    - F1 Score: Balanced metric

Datasets:
    - JailbreakBench (100 samples): Curated jailbreak behaviors
    - HarmBench (400 samples): Harmful behavior requests
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Tuple

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from sentinelseed.detection import InputValidator, InputValidatorConfig
except ImportError as e:
    print(f"Error importing sentinelseed: {e}")
    print("Run from sentinel directory: python evaluation/benchmark_input_validator.py")
    sys.exit(1)


def load_jailbreakbench() -> List[Dict[str, Any]]:
    """Load JailbreakBench dataset."""
    try:
        import pandas as pd

        # Try to find the CSV file directly
        possible_paths = [
            Path(__file__).parent / "data" / "jailbreakbench_behaviors.csv",
            Path(sys.prefix) / "Lib" / "site-packages" / "jailbreakbench" / "data" / "behaviors.csv",
            Path.home() / "AppData" / "Local" / "Programs" / "Python" / "Python312" / "Lib" / "site-packages" / "jailbreakbench" / "data" / "behaviors.csv",
        ]

        csv_path = None
        for path in possible_paths:
            if path.exists():
                csv_path = path
                break

        if csv_path is None:
            print("JailbreakBench CSV not found")
            return []

        df = pd.read_csv(csv_path)

        samples = []
        for i, row in df.iterrows():
            samples.append({
                "id": f"jbb_{i:03d}",
                "text": row.get("Goal", row.get("goal", "")),
                "category": row.get("Behavior", row.get("behavior", "unknown")),
                "source": "jailbreakbench",
                "label": "attack",
            })

        print(f"Loaded JailbreakBench: {len(samples)} samples")
        return samples

    except ImportError:
        print("pandas not installed. Run: pip install pandas")
        return []
    except Exception as e:
        print(f"Error loading JailbreakBench: {e}")
        return []


def load_harmbench() -> List[Dict[str, Any]]:
    """Load HarmBench dataset from local CSV file."""
    try:
        import pandas as pd

        # Try multiple possible paths
        possible_paths = [
            Path(__file__).parent / "benchmarks" / "harmbench" / "data" / "harmbench_behaviors_text_all.csv",
            Path(__file__).parent / "data" / "harmbench_behaviors.json",
        ]

        for harmbench_path in possible_paths:
            if harmbench_path.exists():
                if harmbench_path.suffix == ".csv":
                    df = pd.read_csv(harmbench_path)

                    samples = []
                    for i, row in df.iterrows():
                        samples.append({
                            "id": f"hb_{i:03d}",
                            "text": row.get("Behavior", row.get("behavior", "")),
                            "category": row.get("SemanticCategory", row.get("category", "unknown")),
                            "source": "harmbench",
                            "label": "attack",
                        })

                    print(f"Loaded HarmBench from CSV: {len(samples)} samples")
                    return samples

                elif harmbench_path.suffix == ".json":
                    with open(harmbench_path, "r", encoding="utf-8") as f:
                        data = json.load(f)

                    samples = []
                    for i, item in enumerate(data):
                        samples.append({
                            "id": f"hb_{i:03d}",
                            "text": item.get("behavior", item.get("goal", "")),
                            "category": item.get("category", "unknown"),
                            "source": "harmbench",
                            "label": "attack",
                        })

                    print(f"Loaded HarmBench from JSON: {len(samples)} samples")
                    return samples

        print("HarmBench file not found in:", [str(p) for p in possible_paths])
        return []

    except Exception as e:
        print(f"Error loading HarmBench: {e}")
        return []


def run_benchmark(
    validator: InputValidator,
    samples: List[Dict[str, Any]],
    verbose: bool = False,
) -> Dict[str, Any]:
    """
    Run benchmark on given samples.

    Returns:
        Dict with metrics and detailed results
    """
    results = {
        "true_positives": 0,
        "false_negatives": 0,
        "total_samples": len(samples),
        "detections": [],
        "latencies": [],
    }

    for i, sample in enumerate(samples):
        start_time = time.time()
        result = validator.validate(sample["text"])
        latency_ms = (time.time() - start_time) * 1000

        is_detected = result.is_attack

        if is_detected:
            results["true_positives"] += 1
        else:
            results["false_negatives"] += 1

        results["latencies"].append(latency_ms)
        results["detections"].append({
            "id": sample["id"],
            "detected": is_detected,
            "confidence": result.confidence,
            "blocked": result.blocked,
            "attack_types": [at.value for at in result.attack_types] if result.attack_types else [],
            "latency_ms": latency_ms,
        })

        if verbose and (i + 1) % 50 == 0:
            print(f"  Processed {i + 1}/{len(samples)}...")

    # Calculate metrics
    tp = results["true_positives"]
    fn = results["false_negatives"]
    total = results["total_samples"]

    results["recall"] = tp / total if total > 0 else 0.0
    results["precision"] = 1.0  # All samples are attacks, so TP/(TP+FP) = 1.0 if TP > 0
    results["f1"] = 2 * results["recall"] / (1 + results["recall"]) if results["recall"] > 0 else 0.0

    # Latency stats
    if results["latencies"]:
        results["latency_p50"] = sorted(results["latencies"])[len(results["latencies"]) // 2]
        results["latency_p95"] = sorted(results["latencies"])[int(len(results["latencies"]) * 0.95)]
        results["latency_mean"] = sum(results["latencies"]) / len(results["latencies"])

    return results


def print_results(results: Dict[str, Dict[str, Any]], validator_version: str):
    """Print benchmark results in a formatted table."""
    print("\n" + "=" * 70)
    print(f"BENCHMARK RESULTS - InputValidator v{validator_version}")
    print("=" * 70)

    print("\n### Metrics by Dataset ###\n")
    print(f"{'Dataset':<20} {'N':>6} {'Recall':>10} {'Precision':>10} {'F1':>10}")
    print("-" * 60)

    total_tp = 0
    total_fn = 0
    total_samples = 0

    for dataset_name, data in results.items():
        if dataset_name == "metadata":
            continue

        recall = data["recall"] * 100
        precision = data["precision"] * 100
        f1 = data["f1"] * 100

        print(f"{dataset_name:<20} {data['total_samples']:>6} {recall:>9.1f}% {precision:>9.1f}% {f1:>9.1f}%")

        total_tp += data["true_positives"]
        total_fn += data["false_negatives"]
        total_samples += data["total_samples"]

    # Aggregate
    if total_samples > 0:
        agg_recall = (total_tp / total_samples) * 100
        agg_f1 = 2 * (total_tp / total_samples) / (1 + total_tp / total_samples) * 100 if total_tp > 0 else 0

        print("-" * 60)
        print(f"{'AGGREGATE':<20} {total_samples:>6} {agg_recall:>9.1f}% {'100.0':>9}% {agg_f1:>9.1f}%")

    print("\n### Detection Summary ###\n")
    print(f"  True Positives:  {total_tp}")
    print(f"  False Negatives: {total_fn}")
    print(f"  Total Attacks:   {total_samples}")

    print("\n### Latency ###\n")
    for dataset_name, data in results.items():
        if dataset_name == "metadata" or "latency_p50" not in data:
            continue
        print(f"  {dataset_name}: p50={data['latency_p50']:.1f}ms, p95={data['latency_p95']:.1f}ms")

    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Benchmark InputValidator")
    parser.add_argument("--use-embeddings", action="store_true", help="Enable embedding detector")
    parser.add_argument("--use-semantic", action="store_true", help="Enable semantic detector")
    parser.add_argument("--api-key", type=str, help="API key for semantic/embedding detection")
    parser.add_argument("--provider", type=str, default="openai", help="LLM provider")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file")

    args = parser.parse_args()

    # Configure validator
    config_kwargs = {
        "use_embeddings": args.use_embeddings,
        "use_semantic": args.use_semantic,
    }

    if args.api_key:
        config_kwargs["api_key"] = args.api_key

    if args.use_semantic:
        config_kwargs["semantic_provider"] = args.provider

    config = InputValidatorConfig(**config_kwargs)
    validator = InputValidator(config=config)

    print("\n" + "=" * 70)
    print("BENCHMARK: InputValidator (Layer 1)")
    print("=" * 70)
    print(f"\nVersion: {validator.VERSION}")
    print(f"Embeddings: {'enabled' if args.use_embeddings else 'disabled'}")
    print(f"Semantic: {'enabled' if args.use_semantic else 'disabled'}")
    print(f"Detectors: {list(validator.list_detectors().keys())}")

    # Load datasets
    jbb_samples = load_jailbreakbench()
    hb_samples = load_harmbench()

    if not jbb_samples and not hb_samples:
        print("\nNo datasets loaded. Cannot run benchmark.")
        sys.exit(1)

    # Run benchmarks
    all_results = {
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "validator_version": validator.VERSION,
            "use_embeddings": args.use_embeddings,
            "use_semantic": args.use_semantic,
            "detectors": list(validator.list_detectors().keys()),
        }
    }

    if jbb_samples:
        print("\n### Running JailbreakBench ###")
        all_results["jailbreakbench"] = run_benchmark(validator, jbb_samples, args.verbose)

    if hb_samples:
        print("\n### Running HarmBench ###")
        all_results["harmbench"] = run_benchmark(validator, hb_samples, args.verbose)

    # Print results
    print_results(all_results, validator.VERSION)

    # Save results
    if args.output:
        output_path = Path(args.output)
    else:
        output_dir = Path(__file__).parent.parent.parent / "_internal" / "benchmarks" / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"input_validator_v{validator.VERSION}_{timestamp}.json"

    with open(output_path, "w", encoding="utf-8") as f:
        # Remove latency lists for compact output
        compact_results = {}
        for k, v in all_results.items():
            if isinstance(v, dict) and "latencies" in v:
                compact_results[k] = {key: val for key, val in v.items() if key != "latencies"}
            else:
                compact_results[k] = v

        json.dump(compact_results, f, indent=2, default=str)

    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
