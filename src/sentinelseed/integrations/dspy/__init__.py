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
    import dspy
    DSPY_AVAILABLE = True
except ImportError:
    DSPY_AVAILABLE = False

# Constants (always available)
DEFAULT_SEED_LEVEL = "standard"
DEFAULT_MAX_TEXT_SIZE = 50 * 1024  # 50KB
DEFAULT_VALIDATION_TIMEOUT = 30.0  # seconds
VALID_SEED_LEVELS = ("minimal", "standard", "full")
VALID_MODES = ("block", "flag", "heuristic")
VALID_PROVIDERS = ("openai", "anthropic")
VALID_GATES = ("truth", "harm", "scope", "purpose")


# Custom exceptions (always available)
class DSPyNotAvailableError(ImportError):
    """Raised when DSPy is not installed but required."""

    def __init__(self):
        super().__init__(
            "dspy is required for this integration. "
            "Install with: pip install dspy"
        )


class TextTooLargeError(Exception):
    """Raised when input text exceeds maximum allowed size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Text size ({size:,} bytes) exceeds maximum allowed ({max_size:,} bytes)"
        )


class ValidationTimeoutError(Exception):
    """Raised when validation times out."""

    def __init__(self, timeout: float, operation: str = "validation"):
        self.timeout = timeout
        self.operation = operation
        super().__init__(f"{operation} timed out after {timeout}s")


class InvalidParameterError(Exception):
    """Raised when an invalid parameter value is provided."""

    def __init__(self, param: str, value, valid_values: tuple):
        self.param = param
        self.value = value
        self.valid_values = valid_values
        super().__init__(
            f"Invalid {param}: '{value}'. Valid values: {valid_values}"
        )


def require_dspy(func_name: str = "this function") -> None:
    """Raise DSPyNotAvailableError if DSPy is not installed."""
    if not DSPY_AVAILABLE:
        raise DSPyNotAvailableError()


# Conditional imports - only if DSPy is available
if DSPY_AVAILABLE:
    # Modules
    from sentinelseed.integrations.dspy.modules import (
        SentinelGuard,
        SentinelPredict,
        SentinelChainOfThought,
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
    # Constants
    "DSPY_AVAILABLE",
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_TEXT_SIZE",
    "DEFAULT_VALIDATION_TIMEOUT",
    "VALID_SEED_LEVELS",
    "VALID_MODES",
    "VALID_PROVIDERS",
    "VALID_GATES",
    # Exceptions
    "DSPyNotAvailableError",
    "TextTooLargeError",
    "ValidationTimeoutError",
    "InvalidParameterError",
    # Functions
    "require_dspy",
]

# Add DSPy-dependent exports only if available
if DSPY_AVAILABLE:
    __all__.extend([
        # Modules
        "SentinelGuard",
        "SentinelPredict",
        "SentinelChainOfThought",
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
