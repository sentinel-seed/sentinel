"""
Sentinel Safety Plugin for Virtuals Protocol GAME SDK

Provides safety guardrails for AI agents built on the GAME framework.
Integrates THSP Protocol (Truth, Harm, Scope, Purpose) validation.

Usage:
    from sentinel.integrations.virtuals import (
        SentinelSafetyWorker,
        sentinel_protected,
        wrap_agent_with_sentinel,
    )

    # Option 1: Add safety worker to existing agent
    agent = wrap_agent_with_sentinel(agent, block_unsafe=True)

    # Option 2: Protect individual functions
    @sentinel_protected(level="standard")
    def risky_function(args):
        ...

    # Option 3: Create standalone safety worker
    safety_worker = SentinelSafetyWorker(config)
"""

from .plugin import (
    SentinelSafetyWorker,
    SentinelWorkerConfig,
    SentinelValidator,
    SentinelValidationError,
    ValidationResult,
    THSPGate,
    sentinel_protected,
    wrap_function_with_sentinel,
    wrap_agent_with_sentinel,
    create_safe_agent,
)

__all__ = [
    "SentinelSafetyWorker",
    "SentinelWorkerConfig",
    "SentinelValidator",
    "SentinelValidationError",
    "ValidationResult",
    "THSPGate",
    "sentinel_protected",
    "wrap_function_with_sentinel",
    "wrap_agent_with_sentinel",
    "create_safe_agent",
]
