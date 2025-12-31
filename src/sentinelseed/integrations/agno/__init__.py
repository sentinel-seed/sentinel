"""Sentinel integration for Agno AI agents.

This module provides THSP-based guardrails that integrate natively with
Agno's guardrail system for AI safety validation.

Components:
    SentinelGuardrail: Input validation guardrail for pre_hooks.
    SentinelOutputGuardrail: Output validation guardrail for post_hooks.
    InputGuardrail: Alias for SentinelGuardrail.
    OutputGuardrail: Alias for SentinelOutputGuardrail.

Quick Start:
    from sentinelseed.integrations.agno import SentinelGuardrail
    from agno.agent import Agent
    from agno.models.openai import OpenAIChat

    agent = Agent(
        name="Safe Agent",
        model=OpenAIChat(id="gpt-4o-mini"),
        pre_hooks=[SentinelGuardrail()],
    )

    response = agent.run("Hello!")

Configuration Options:
    SentinelGuardrail accepts the following parameters:

    - sentinel: Optional[Sentinel] - Custom Sentinel instance
    - seed_level: str - Safety level ('minimal', 'standard', 'full')
    - block_on_failure: bool - Whether to block unsafe content (default: True)
    - max_text_size: int - Maximum input size in bytes (default: 100,000)
    - validation_timeout: float - Timeout in seconds (default: 5.0)
    - fail_closed: bool - Block on errors (default: False)
    - log_violations: bool - Record violations (default: True)

Monitoring:
    Both guardrails provide methods for monitoring:

    - get_violations(): Returns list of recorded violations
    - get_stats(): Returns validation statistics (SentinelGuardrail only)
    - clear_violations(): Clears recorded violations

Example with Custom Configuration:
    from sentinelseed.integrations.agno import SentinelGuardrail

    guardrail = SentinelGuardrail(
        seed_level="full",          # Maximum safety
        block_on_failure=True,      # Block unsafe content
        fail_closed=True,           # Block on errors too
        max_text_size=50000,        # 50KB limit
        validation_timeout=10.0,    # 10 second timeout
    )

    # Use with agent
    agent = Agent(name="Secure", model=model, pre_hooks=[guardrail])

    # Later, check stats
    stats = guardrail.get_stats()
    print(f"Blocked: {stats['blocked_count']}/{stats['total_validations']}")

Note:
    Agno must be installed separately: pip install agno
    This integration requires Agno version 2.0.0 or higher.

See Also:
    - Agno documentation: https://docs.agno.com
    - Sentinel documentation: https://sentinelseed.dev/docs
"""

from __future__ import annotations

from .guardrails import (
    InputGuardrail,
    OutputGuardrail,
    SentinelGuardrail,
    SentinelOutputGuardrail,
)
from .utils import (
    ConfigurationError,
    TextTooLargeError,
    ValidationTimeoutError,
)

__all__ = [
    # Primary classes
    "SentinelGuardrail",
    "SentinelOutputGuardrail",
    # Aliases
    "InputGuardrail",
    "OutputGuardrail",
    # Exceptions
    "ConfigurationError",
    "ValidationTimeoutError",
    "TextTooLargeError",
]

__version__ = "1.0.0"
