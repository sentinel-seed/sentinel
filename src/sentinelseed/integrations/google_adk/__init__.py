"""Google Agent Development Kit (ADK) integration for Sentinel.

This module provides THSP-based guardrails for Google ADK agents and
multi-agent systems. The integration offers two approaches:

1. **Plugin-based (Recommended for multi-agent systems)**:
   Use SentinelPlugin to apply guardrails globally to all agents in a Runner.

2. **Callback-based (For individual agents)**:
   Use callback factory functions to add guardrails to specific agents.

Installation:
    pip install google-adk sentinelseed

Quick Start with Plugin:
    from google.adk.runners import Runner
    from google.adk.agents import LlmAgent
    from google.adk.sessions import InMemorySessionService
    from sentinelseed.integrations.google_adk import SentinelPlugin

    # Create your agent
    agent = LlmAgent(
        name="Assistant",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
    )

    # Create runner with Sentinel plugin
    plugin = SentinelPlugin(seed_level="standard", block_on_failure=True)
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="my_app",
        agent=agent,
        plugins=[plugin],
        session_service=session_service,
    )

    # Run with automatic safety validation
    response = await runner.run("Hello, how can you help?")

Quick Start with Callbacks:
    from google.adk.agents import LlmAgent
    from sentinelseed.integrations.google_adk import create_sentinel_callbacks

    # Create all callbacks at once
    callbacks = create_sentinel_callbacks(seed_level="standard")

    agent = LlmAgent(
        name="SafeAssistant",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
        **callbacks,  # Unpacks all callback functions
    )

Features:
    - THSP (Truth, Harm, Scope, Purpose) validation at all execution points
    - Input validation before LLM calls (blocks harmful requests)
    - Output validation after LLM responses (filters unsafe content)
    - Tool argument and result validation (prevents tool misuse)
    - Configurable fail-open/fail-closed modes
    - Timeout protection for validation
    - Violation logging and statistics
    - Thread-safe operation for concurrent requests

See Also:
    - Google ADK Docs: https://google.github.io/adk-docs/
    - Sentinel Docs: https://sentinelseed.dev/docs/
"""

from __future__ import annotations

# Utils - always available
from .utils import (
    # Constants
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    DEFAULT_MAX_VIOLATIONS,
    VALID_SEED_LEVELS,
    ADK_AVAILABLE,
    # Exceptions
    ConfigurationError,
    TextTooLargeError,
    ValidationTimeoutError,
    # Logging
    SentinelLogger,
    DefaultLogger,
    get_logger,
    set_logger,
    # Functions
    require_adk,
    validate_configuration,
    validate_text_size,
    extract_text_from_llm_request,
    extract_text_from_llm_response,
    extract_tool_input_text,
    create_blocked_response,
    create_empty_stats,
    format_violation,
    log_fail_open_warning,
    get_validation_executor,
    shutdown_validation_executor,
    # Classes
    ThreadSafeDeque,
    ValidationExecutor,
)

# Plugin
from .plugin import (
    SentinelPlugin,
    create_sentinel_plugin,
)

# Callbacks
from .callbacks import (
    create_before_model_callback,
    create_after_model_callback,
    create_before_tool_callback,
    create_after_tool_callback,
    create_sentinel_callbacks,
)


__all__ = [
    # Constants
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "DEFAULT_MAX_VIOLATIONS",
    "VALID_SEED_LEVELS",
    "ADK_AVAILABLE",
    # Exceptions
    "ConfigurationError",
    "TextTooLargeError",
    "ValidationTimeoutError",
    # Logging
    "SentinelLogger",
    "DefaultLogger",
    "get_logger",
    "set_logger",
    # Utils functions
    "require_adk",
    "validate_configuration",
    "validate_text_size",
    "extract_text_from_llm_request",
    "extract_text_from_llm_response",
    "extract_tool_input_text",
    "create_blocked_response",
    "create_empty_stats",
    "format_violation",
    "log_fail_open_warning",
    "get_validation_executor",
    "shutdown_validation_executor",
    # Classes
    "ThreadSafeDeque",
    "ValidationExecutor",
    # Plugin
    "SentinelPlugin",
    "create_sentinel_plugin",
    # Callbacks
    "create_before_model_callback",
    "create_after_model_callback",
    "create_before_tool_callback",
    "create_after_tool_callback",
    "create_sentinel_callbacks",
]


__version__ = "1.0.0"
