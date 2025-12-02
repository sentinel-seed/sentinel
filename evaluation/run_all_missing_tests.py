"""
Run all missing benchmark tests to fill gaps in the matrix.
Executes tests sequentially to avoid rate limiting.

Usage:
    python run_all_missing_tests.py
"""

import subprocess
import sys
import time
from pathlib import Path

# API Keys - set via environment variables
import os
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Sample size for each test
SAMPLE_SIZE = 50

# Tests to run - organized by priority
TESTS = [
    # === SafeAgentBench - OpenRouter models ===
    # Qwen
    {"benchmark": "safeagent", "provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "safeagent", "provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # DeepSeek
    {"benchmark": "safeagent", "provider": "openrouter", "model": "deepseek/deepseek-chat", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "safeagent", "provider": "openrouter", "model": "deepseek/deepseek-chat", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # Llama
    {"benchmark": "safeagent", "provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "safeagent", "provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # Mistral
    {"benchmark": "safeagent", "provider": "openrouter", "model": "mistralai/mistral-7b-instruct", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "safeagent", "provider": "openrouter", "model": "mistralai/mistral-7b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # === BadRobot - Multiple providers ===
    # Claude
    {"benchmark": "badrobot", "provider": "anthropic", "model": "claude-sonnet-4-20250514", "seed": "v1/standard", "key": ANTHROPIC_KEY},
    {"benchmark": "badrobot", "provider": "anthropic", "model": "claude-sonnet-4-20250514", "seed": "v2/standard", "key": ANTHROPIC_KEY},

    # Qwen
    {"benchmark": "badrobot", "provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "badrobot", "provider": "openrouter", "model": "qwen/qwen-2.5-72b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # DeepSeek
    {"benchmark": "badrobot", "provider": "openrouter", "model": "deepseek/deepseek-chat", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "badrobot", "provider": "openrouter", "model": "deepseek/deepseek-chat", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # Llama
    {"benchmark": "badrobot", "provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "badrobot", "provider": "openrouter", "model": "meta-llama/llama-3.3-70b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # Mistral
    {"benchmark": "badrobot", "provider": "openrouter", "model": "mistralai/mistral-7b-instruct", "seed": "v1/standard", "key": OPENROUTER_KEY},
    {"benchmark": "badrobot", "provider": "openrouter", "model": "mistralai/mistral-7b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},

    # === JailbreakBench - Missing v2 for Mistral ===
    {"benchmark": "jailbreak", "provider": "openrouter", "model": "mistralai/mistral-7b-instruct", "seed": "v2/standard", "key": OPENROUTER_KEY},
]


def run_test(test_config, script_path, output_dir):
    """Run a single benchmark test."""
    cmd = [
        sys.executable,
        str(script_path),
        "--benchmark", test_config["benchmark"],
        "--provider", test_config["provider"],
        "--model", test_config["model"],
        "--api_key", test_config["key"],
        "--sample_size", str(SAMPLE_SIZE),
        "--output_dir", str(output_dir)
    ]

    if test_config.get("seed"):
        cmd.extend(["--seed", test_config["seed"]])

    print(f"\n{'='*60}")
    print(f"Running: {test_config['benchmark']} | {test_config['model']} | {test_config.get('seed', 'baseline')}")
    print(f"{'='*60}")

    try:
        result = subprocess.run(cmd, capture_output=False, text=True, timeout=600)
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("Test timed out after 10 minutes")
        return False
    except Exception as e:
        print(f"Error running test: {e}")
        return False


def main():
    script_path = Path(__file__).parent / "run_benchmark_unified.py"
    output_dir = Path(__file__).parent / "results" / "matrix_completion"
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Starting benchmark suite: {len(TESTS)} tests")
    print(f"Output directory: {output_dir}")
    print(f"Sample size per test: {SAMPLE_SIZE}")

    completed = 0
    failed = 0

    for i, test in enumerate(TESTS, 1):
        print(f"\n[{i}/{len(TESTS)}] ", end="")

        success = run_test(test, script_path, output_dir)

        if success:
            completed += 1
            print(f"Completed")
        else:
            failed += 1
            print(f"FAILED")

        # Wait between tests to avoid rate limiting
        if i < len(TESTS):
            print("Waiting 5 seconds before next test...")
            time.sleep(5)

    print(f"\n{'='*60}")
    print(f"BENCHMARK SUITE COMPLETE")
    print(f"{'='*60}")
    print(f"Completed: {completed}/{len(TESTS)}")
    print(f"Failed: {failed}/{len(TESTS)}")
    print(f"Results saved to: {output_dir}")


if __name__ == "__main__":
    main()
