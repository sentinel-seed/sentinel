"""
Sentinel - Seed Test Runner
============================

Test the Sentinel seed across different models and scenarios.

Usage:
    # Single test
    python tools/test_seed.py --prompt "your prompt" --seed seeds/v2/minimal/seed.txt

    # Baseline (no seed)
    python tools/test_seed.py --prompt "your prompt"

    # Run test suite
    python tools/test_seed.py --suite safety

Requirements:
    - Python 3.10+
    - openai, anthropic (pip install -r requirements.txt)
    - API keys in .env file (OPENAI_API_KEY, ANTHROPIC_API_KEY)
"""

import argparse
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Warning: python-dotenv not installed. Using environment variables directly.")


def load_seed(seed_path: str) -> str:
    """Load seed content from file."""
    with open(seed_path, 'r', encoding='utf-8') as f:
        return f.read()


def test_openai(
    prompt: str,
    seed: Optional[str] = None,
    model: str = "gpt-4o-mini",
    temperature: float = 0.7
) -> dict:
    """Test with OpenAI API."""
    try:
        from openai import OpenAI
    except ImportError:
        return {"error": "openai package not installed"}
    
    client = OpenAI()
    
    messages = []
    if seed:
        messages.append({"role": "system", "content": seed})
    messages.append({"role": "user", "content": prompt})
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=1024
        )
        return {
            "model": model,
            "response": response.choices[0].message.content,
            "usage": {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }
        }
    except Exception as e:
        return {"error": str(e)}


def test_anthropic(
    prompt: str,
    seed: Optional[str] = None,
    model: str = "claude-3-haiku-20240307",
    temperature: float = 0.7
) -> dict:
    """Test with Anthropic API."""
    try:
        import anthropic
    except ImportError:
        return {"error": "anthropic package not installed"}
    
    client = anthropic.Anthropic()
    
    system = seed if seed else ""
    
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature
        )
        return {
            "model": model,
            "response": response.content[0].text,
            "usage": {
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens
            }
        }
    except Exception as e:
        return {"error": str(e)}


def run_test(
    prompt: str,
    seed_path: Optional[str] = None,
    model: str = "gpt-4o-mini",
    provider: str = "openai"
) -> dict:
    """Run a single test."""
    
    seed = load_seed(seed_path) if seed_path else None
    
    timestamp = datetime.now().isoformat()
    
    result = {
        "timestamp": timestamp,
        "model": model,
        "provider": provider,
        "prompt": prompt,
        "seed_used": seed_path is not None,
        "seed_path": seed_path
    }
    
    if provider == "openai":
        response = test_openai(prompt, seed, model)
    elif provider == "anthropic":
        response = test_anthropic(prompt, seed, model)
    else:
        response = {"error": f"Unknown provider: {provider}"}
    
    result.update(response)
    return result


def main():
    parser = argparse.ArgumentParser(description="Sentinel - Seed Test Runner")
    parser.add_argument("--prompt", type=str, required=True, help="Prompt to test")
    parser.add_argument("--seed", type=str, default=None, help="Path to seed file")
    parser.add_argument("--model", type=str, default="gpt-4o-mini", help="Model to use")
    parser.add_argument("--provider", type=str, default="openai", choices=["openai", "anthropic"])
    parser.add_argument("--output", type=str, default=None, help="Output file for results")
    
    args = parser.parse_args()
    
    print(f"\n{'='*60}")
    print(f"Sentinel - Seed Test Runner")
    print(f"{'='*60}")
    print(f"Model: {args.model}")
    print(f"Provider: {args.provider}")
    print(f"Seed: {args.seed or 'None (baseline)'}")
    print(f"{'='*60}\n")
    
    result = run_test(
        prompt=args.prompt,
        seed_path=args.seed,
        model=args.model,
        provider=args.provider
    )
    
    print(f"Prompt: {args.prompt[:100]}...")
    print(f"\nResponse:")
    print("-" * 40)
    print(result.get("response", result.get("error", "Unknown error")))
    print("-" * 40)
    
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2)
        print(f"\nResults saved to: {args.output}")
    
    return result


if __name__ == "__main__":
    main()
