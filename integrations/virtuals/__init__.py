"""
Sentinel Safety Plugin for Virtuals Protocol GAME SDK

Provides THSP Protocol (Truth, Harm, Scope, Purpose) validation for AI agents
built with the GAME framework.

Installation:
    pip install game-sdk  # Virtuals Protocol SDK
    pip install sentinelseed  # Optional, for seed access

Usage:
    from sentinel.integrations.virtuals import (
        SentinelConfig,
        SentinelSafetyWorker,
        create_sentinel_function,
        wrap_functions_with_sentinel,
        sentinel_protected,
    )

    # Option 1: Add a safety worker to your agent
    safety_worker = SentinelSafetyWorker.create_worker_config()

    agent = Agent(
        api_key=api_key,
        name="SafeAgent",
        agent_goal="Execute safe operations",
        agent_description="An agent with safety validation",
        get_agent_state_fn=get_state,
        workers=[safety_worker, other_workers],
    )

    # Option 2: Wrap individual functions
    safe_fn = create_sentinel_function(my_function, config)

    # Option 3: Wrap all functions in an action space
    safe_action_space = wrap_functions_with_sentinel(action_space)
"""

from .plugin import (
    SentinelConfig,
    SentinelValidator,
    ValidationResult,
    SentinelValidationError,
    SentinelSafetyWorker,
    create_sentinel_function,
    wrap_functions_with_sentinel,
    sentinel_protected,
    GAME_SDK_AVAILABLE,
)

__all__ = [
    "SentinelConfig",
    "SentinelValidator",
    "ValidationResult",
    "SentinelValidationError",
    "SentinelSafetyWorker",
    "create_sentinel_function",
    "wrap_functions_with_sentinel",
    "sentinel_protected",
    "GAME_SDK_AVAILABLE",
]
