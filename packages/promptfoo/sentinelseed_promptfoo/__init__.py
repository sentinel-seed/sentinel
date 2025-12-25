"""
Sentinel Safety Provider for Promptfoo

A custom promptfoo provider that wraps any LLM with Sentinel safety validation.
Use this to test how well your models respond when protected by Sentinel seeds.

Usage in promptfooconfig.yaml:
    providers:
      - id: 'python:sentinelseed_promptfoo'
        label: 'Sentinel Protected GPT-4'
        config:
          base_provider: 'openai:gpt-4o'
          seed_version: 'v2'
          seed_variant: 'standard'

Available seed versions:
    - v1_minimal, v1_standard, v1_full (3-gate THS protocol)
    - v2_minimal, v2_standard, v2_full (4-gate THSP protocol)

Documentation: https://sentinelseed.dev/docs/promptfoo
"""

from .provider import (
    call_api,
    validate_response,
    get_seed,
    parse_provider,
    SEEDS,
)

__version__ = "1.0.0"
__all__ = ["call_api", "validate_response", "get_seed", "parse_provider", "SEEDS"]
