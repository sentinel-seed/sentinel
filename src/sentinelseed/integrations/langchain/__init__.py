"""
LangChain integration for Sentinel AI.

Provides safety validation for LangChain applications via callbacks,
guards, and chain wrappers.

Components:
- SentinelCallback: Callback handler to monitor LLM calls and responses
- SentinelGuard: Wrap agents with safety validation
- SentinelChain: Chain wrapper with built-in safety validation
- inject_seed: Add seed to message lists
- wrap_llm: Wrap LLMs with safety features

Usage:
    from sentinelseed.integrations.langchain import (
        SentinelCallback,
        SentinelGuard,
        SentinelChain,
        inject_seed,
        wrap_llm,
    )

    # Option 1: Use callback to monitor
    callback = SentinelCallback()
    llm = ChatOpenAI(callbacks=[callback])

    # Option 2: Wrap agent with guard
    safe_agent = SentinelGuard(agent)

    # Option 3: Inject seed into messages
    safe_messages = inject_seed(messages, seed_level="standard")
"""

# Utils
from .utils import (
    # Constants
    DEFAULT_MAX_VIOLATIONS,
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    DEFAULT_STREAMING_VALIDATION_INTERVAL,
    DEFAULT_EXECUTOR_MAX_WORKERS,
    LANGCHAIN_AVAILABLE,
    # Exceptions
    TextTooLargeError,
    ValidationTimeoutError,
    ConfigurationError,
    # LangChain types (may be None if not installed)
    BaseCallbackHandler,
    SystemMessage,
    HumanMessage,
    AIMessage,
    BaseMessage,
    # Functions
    require_langchain,
    get_logger,
    set_logger,
    sanitize_text,
    extract_content,
    get_message_role,
    is_system_message,
    validate_text_size,
    validate_config_types,
    warn_fail_open_default,
    get_validation_executor,
    run_sync_with_timeout_async,
    # Classes
    SentinelLogger,
    ThreadSafeDeque,
    ValidationResult,
    ViolationRecord,
    ValidationExecutor,
)

# Callbacks
from .callbacks import (
    SentinelCallback,
    SentinelViolationError,
    StreamingBuffer,
    create_safe_callback,
    create_sentinel_callback,
)

# Guards
from .guards import SentinelGuard

# Chains
from .chains import (
    SentinelChain,
    inject_seed,
    wrap_llm,
)

# Re-export sanitize_text as _sanitize_text for backward compatibility in tests
_sanitize_text = sanitize_text


__all__ = [
    # Constants
    "DEFAULT_MAX_VIOLATIONS",
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "DEFAULT_STREAMING_VALIDATION_INTERVAL",
    "DEFAULT_EXECUTOR_MAX_WORKERS",
    "LANGCHAIN_AVAILABLE",
    # Exceptions
    "TextTooLargeError",
    "ValidationTimeoutError",
    "ConfigurationError",
    # Classes
    "SentinelCallback",
    "SentinelGuard",
    "SentinelChain",
    "SentinelViolationError",
    "StreamingBuffer",
    "ThreadSafeDeque",
    "ValidationResult",
    "ViolationRecord",
    "ValidationExecutor",
    # Functions
    "inject_seed",
    "wrap_llm",
    "create_safe_callback",
    "create_sentinel_callback",
    "set_logger",
    "get_logger",
    "require_langchain",
    "sanitize_text",
    "extract_content",
    "get_message_role",
    "is_system_message",
    "validate_text_size",
    "validate_config_types",
    "warn_fail_open_default",
    "get_validation_executor",
    "run_sync_with_timeout_async",
    # For backward compatibility
    "_sanitize_text",
]
