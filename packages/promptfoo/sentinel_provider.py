"""
Sentinel Safety Provider for Promptfoo

This is a convenience wrapper that re-exports the provider from the package.
For direct use in promptfooconfig.yaml:

    providers:
      - id: 'file://sentinel_provider.py'
        label: 'Sentinel Protected GPT-4'
        config:
          base_provider: 'openai:gpt-4o'
          seed_version: 'v2'
          seed_variant: 'standard'

For package usage:
    from sentinelseed_promptfoo import call_api, validate_response, get_seed

Documentation: https://sentinelseed.dev/docs/promptfoo
"""

# Re-export everything from the package
from sentinelseed_promptfoo.provider import (
    call_api,
    validate_response,
    get_seed,
    parse_provider,
    call_openai,
    call_anthropic,
    SEEDS,
    HAS_OPENAI,
    HAS_ANTHROPIC,
)

__all__ = [
    'call_api',
    'validate_response',
    'get_seed',
    'parse_provider',
    'call_openai',
    'call_anthropic',
    'SEEDS',
    'HAS_OPENAI',
    'HAS_ANTHROPIC',
]

# For testing - run the package's test suite
if __name__ == '__main__':
    from sentinelseed_promptfoo.provider import __name__ as provider_module
    exec(open('sentinelseed_promptfoo/provider.py').read().split("if __name__ == '__main__':")[1])
