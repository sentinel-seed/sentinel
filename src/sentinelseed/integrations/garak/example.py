#!/usr/bin/env python3
"""
Sentinel THSP Plugin for Garak - Usage Examples

This file demonstrates how to use the Sentinel THSP probes and detectors
with Garak for LLM security testing.

Prerequisites:
    pip install garak sentinelseed
    python -m sentinelseed.integrations.garak.install

Documentation: https://sentinelseed.dev/docs/garak
"""

import subprocess
import sys


def run_command(cmd: str, description: str):
    """Run a command and print the result."""
    print(f"\n{'=' * 70}")
    print(f"Example: {description}")
    print(f"{'=' * 70}")
    print(f"\n$ {cmd}\n")

    # Note: Actually running these commands requires API keys and garak installed
    print("[Command would execute here with proper API keys configured]")
    print()


def example_basic_usage():
    """Basic usage examples."""
    print("\n" + "=" * 70)
    print("EXAMPLE 1: Basic Usage - Test All THSP Gates")
    print("=" * 70)

    print("""
# Test a model against all THSP gates
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp

# This will run 73 prompts across 5 probe categories:
# - TruthGate: 15 prompts (fake documents, impersonation, misinformation)
# - HarmGate: 17 prompts (violence, hacking, financial crime)
# - ScopeGate: 17 prompts (jailbreaks, prompt injection, persona switches)
# - PurposeGate: 15 prompts (purposeless destruction, waste)
# - THSPCombined: 9 prompts (multi-gate attacks)
""")


def example_specific_gate():
    """Test specific gates."""
    print("\n" + "=" * 70)
    print("EXAMPLE 2: Test Specific THSP Gates")
    print("=" * 70)

    print("""
# Test only the Truth Gate (fake documents, misinformation)
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.TruthGate

# Test only the Harm Gate (violence, hacking)
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.HarmGate

# Test only the Scope Gate (jailbreaks)
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.ScopeGate

# Test only the Purpose Gate (purposeless destruction)
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp.PurposeGate
""")


def example_with_detectors():
    """Use Sentinel detectors for classification."""
    print("\n" + "=" * 70)
    print("EXAMPLE 3: Use Sentinel Detectors")
    print("=" * 70)

    print("""
# Use Sentinel's THSP-specific detectors for more accurate classification
garak --model_type openai --model_name gpt-4o \\
    --probes sentinel_thsp \\
    --detectors sentinel_thsp

# The detectors analyze responses for:
# - Refusal patterns (model refused = safe)
# - Compliance patterns (model complied = vulnerable)
# - Jailbreak acceptance (model accepted persona switch = critical)
""")


def example_compare_models():
    """Compare models with and without Sentinel seed."""
    print("\n" + "=" * 70)
    print("EXAMPLE 4: Compare Models (Baseline vs Sentinel Seed)")
    print("=" * 70)

    print("""
# Step 1: Test baseline (no seed)
garak --model_type openai --model_name gpt-4o \\
    --probes sentinel_thsp \\
    --report_prefix gpt4o_baseline

# Step 2: Test with Sentinel seed (via system prompt)
# First, get the seed:
python -c "from sentinelseed import get_seed; print(get_seed('standard'))" > sentinel_seed.txt

# Then run with the seed as system prompt:
garak --model_type openai --model_name gpt-4o \\
    --probes sentinel_thsp \\
    --system_prompt "$(cat sentinel_seed.txt)" \\
    --report_prefix gpt4o_with_sentinel

# Step 3: Compare results in the garak_runs/ directory
""")


def example_different_models():
    """Test different model backends."""
    print("\n" + "=" * 70)
    print("EXAMPLE 5: Test Different Model Backends")
    print("=" * 70)

    print("""
# OpenAI
garak --model_type openai --model_name gpt-4o --probes sentinel_thsp

# Hugging Face (local)
garak --model_type huggingface --model_name meta-llama/Llama-2-7b-chat-hf \\
    --probes sentinel_thsp

# Hugging Face (inference API)
garak --model_type huggingface.InferenceAPI \\
    --model_name meta-llama/Llama-2-70b-chat-hf \\
    --probes sentinel_thsp

# Ollama (local)
garak --model_type ollama --model_name llama2 --probes sentinel_thsp

# Anthropic
garak --model_type anthropic --model_name claude-3-opus-20240229 \\
    --probes sentinel_thsp

# Azure OpenAI
garak --model_type azure --model_name your-deployment-name \\
    --probes sentinel_thsp
""")


def example_ci_cd():
    """CI/CD integration example."""
    print("\n" + "=" * 70)
    print("EXAMPLE 6: CI/CD Integration")
    print("=" * 70)

    print("""
# GitHub Actions workflow example (.github/workflows/llm-security.yml):

name: LLM Security Scan

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install garak sentinelseed

      - name: Install Sentinel plugin
        run: |
          python -m sentinelseed.integrations.garak.install

      - name: Run THSP Security Scan
        env:
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          garak --model_type openai \\
                --model_name gpt-4o \\
                --probes sentinel_thsp \\
                --report_prefix security_scan

      - name: Upload security report
        uses: actions/upload-artifact@v4
        with:
          name: garak-security-report
          path: garak_runs/
""")


def example_python_api():
    """Using probes and detectors programmatically."""
    print("\n" + "=" * 70)
    print("EXAMPLE 7: Python API Usage")
    print("=" * 70)

    print("""
# You can also use the probes and detectors programmatically:

from sentinelseed.integrations.garak.probes import TruthGate, HarmGate
from sentinelseed.integrations.garak.detectors import TruthViolation, HarmViolation

# Access probe prompts
truth_probe = TruthGate()
print(f"Truth Gate has {len(truth_probe.prompts)} prompts")
for prompt in truth_probe.prompts[:3]:
    print(f"  - {prompt[:60]}...")

# Access detector patterns
truth_detector = TruthViolation()
print(f"\\nTruth detector has {len(truth_detector.compliance_patterns)} compliance patterns")

# Note: Full functionality requires garak to be installed
# The above works for inspection even without garak
""")


def main():
    """Run all examples."""
    print("=" * 70)
    print("Sentinel THSP Plugin for Garak - Usage Examples")
    print("=" * 70)
    print()
    print("This file shows example commands for using the Sentinel THSP")
    print("probes and detectors with the Garak LLM vulnerability scanner.")
    print()
    print("Prerequisites:")
    print("  1. pip install garak sentinelseed")
    print("  2. python -m sentinelseed.integrations.garak.install")
    print("  3. Set API keys (OPENAI_API_KEY, etc.)")
    print()

    example_basic_usage()
    example_specific_gate()
    example_with_detectors()
    example_compare_models()
    example_different_models()
    example_ci_cd()
    example_python_api()

    print("\n" + "=" * 70)
    print("Documentation: https://sentinelseed.dev/docs/garak")
    print("Garak Docs: https://docs.garak.ai")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
