"""
Sentinel THSP Integration for DSPy

This package provides DSPy-compatible modules, signatures, and tools
for integrating Sentinel's THSP safety validation into DSPy pipelines.

DSPy is Stanford's framework for programming language models through
declarative specifications rather than manual prompt engineering.

Installation:
    pip install dspy sentinelseed

Modules:
    - SentinelGuard: Wrapper that validates any DSPy module's output
    - SentinelPredict: Predict with built-in THSP validation
    - SentinelChainOfThought: ChainOfThought with THSP validation

Agent Modules:
    - SentinelToolValidator: Validate tool/function calls before execution
    - SentinelAgentGuard: Validate each step of agent execution
    - SentinelMemoryGuard: Validate data before writing to agent memory

Signatures:
    - THSPCheckSignature: Full THSP validation signature
    - SafetyFilterSignature: Content filtering signature
    - ContentClassificationSignature: Risk classification signature

Tools:
    - create_sentinel_tool: Create safety check tool for ReAct
    - create_content_filter_tool: Create content filter tool
    - create_gate_check_tool: Create single-gate check tool

Usage Example:
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard, SentinelPredict

    # Configure DSPy
    lm = dspy.LM("openai/gpt-4o-mini")
    dspy.configure(lm=lm)

    # Method 1: Wrap existing module
    base = dspy.ChainOfThought("question -> answer")
    safe_module = SentinelGuard(
        base,
        api_key="sk-...",
        mode="block"
    )
    result = safe_module(question="What is 2+2?")

    # Method 2: Use SentinelPredict directly
    predictor = SentinelPredict(
        "question -> answer",
        api_key="sk-...",
        mode="block"
    )
    result = predictor(question="How do I learn Python?")

    # Method 3: Use with ReAct agents
    from sentinelseed.integrations.dspy import create_sentinel_tool

    safety_tool = create_sentinel_tool(api_key="sk-...")
    agent = dspy.ReAct(
        "task -> result",
        tools=[safety_tool]
    )

References:
    - DSPy: https://dspy.ai/
    - DSPy GitHub: https://github.com/stanfordnlp/dspy
    - Sentinel: https://sentinelseed.dev
"""

# Check if DSPy is available
try:
    import dspy  # noqa: F401
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

# Import from utils (always available, even without DSPy)
from sentinelseed.integrations.dspy.utils import (
    # Constants
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    DEFAULT_EXECUTOR_MAX_WORKERS,
    VALID_SEED_LEVELS,
    VALID_MODES,
    VALID_PROVIDERS,
    VALID_GATES,
    # Confidence levels
    VALID_CONFIDENCE_LEVELS,
    CONFIDENCE_NONE,
    CONFIDENCE_LOW,
    CONFIDENCE_MEDIUM,
    CONFIDENCE_HIGH,
    # Exceptions
    DSPyNotAvailableError,
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidParameterError,
    ConfigurationError,
    HeuristicFallbackError,
    # Logger
    SentinelLogger,
    get_logger,
    set_logger,
    # Executor
    ValidationExecutor,
    get_validation_executor,
    run_with_timeout_async,
    # Validation helpers
    validate_mode,
    validate_provider,
    validate_gate,
    validate_text_size,
    validate_config_types,
    warn_fail_open_default,
    require_dspy,
)


# Conditional imports - only if DSPy is available
if DSPY_AVAILABLE:
    # Modules
    from sentinelseed.integrations.dspy.modules import (
        SentinelGuard,
        SentinelPredict,
        SentinelChainOfThought,
    )

    # Agent Modules
    from sentinelseed.integrations.dspy.agents import (
        SentinelToolValidator,
        SentinelAgentGuard,
        SentinelMemoryGuard,
        SafeMemoryWrapper,
    )

    # Signatures
    from sentinelseed.integrations.dspy.signatures import (
        THSPCheckSignature,
        SafetyFilterSignature,
        ContentClassificationSignature,
        THSP_INSTRUCTIONS,
    )

    # Tools
    from sentinelseed.integrations.dspy.tools import (
        create_sentinel_tool,
        create_content_filter_tool,
        create_gate_check_tool,
    )


# Dynamic __all__ based on DSPy availability
__all__ = [
    # Availability flag
    "DSPY_AVAILABLE",
    # Constants
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "DEFAULT_EXECUTOR_MAX_WORKERS",
    "VALID_SEED_LEVELS",
    "VALID_MODES",
    "VALID_PROVIDERS",
    "VALID_GATES",
    # Confidence levels
    "VALID_CONFIDENCE_LEVELS",
    "CONFIDENCE_NONE",
    "CONFIDENCE_LOW",
    "CONFIDENCE_MEDIUM",
    "CONFIDENCE_HIGH",
    # Exceptions
    "DSPyNotAvailableError",
    "TextTooLargeError",
    "ValidationTimeoutError",
    "InvalidParameterError",
    "ConfigurationError",
    "HeuristicFallbackError",
    # Logger
    "SentinelLogger",
    "get_logger",
    "set_logger",
    # Executor
    "ValidationExecutor",
    "get_validation_executor",
    "run_with_timeout_async",
    # Validation helpers
    "validate_mode",
    "validate_provider",
    "validate_gate",
    "validate_text_size",
    "validate_config_types",
    "warn_fail_open_default",
    "require_dspy",
]

# Add DSPy-dependent exports only if available
if DSPY_AVAILABLE:
    __all__.extend([
        # Modules
        "SentinelGuard",
        "SentinelPredict",
        "SentinelChainOfThought",
        # Agent Modules
        "SentinelToolValidator",
        "SentinelAgentGuard",
        "SentinelMemoryGuard",
        "SafeMemoryWrapper",
        # Signatures
        "THSPCheckSignature",
        "SafetyFilterSignature",
        "ContentClassificationSignature",
        "THSP_INSTRUCTIONS",
        # Tools
        "create_sentinel_tool",
        "create_content_filter_tool",
        "create_gate_check_tool",
    ])
