"""
DSPy Tools for Sentinel THSP validation.

These tools can be used with DSPy's ReAct module for agentic workflows.
They allow agents to explicitly check content safety during reasoning.

Usage:
    import dspy
    from sentinelseed.integrations.dspy import create_sentinel_tool

    # Create safety check tool
    safety_tool = create_sentinel_tool(api_key="sk-...")

    # Use with ReAct
    react = dspy.ReAct(
        "task -> result",
        tools=[safety_tool, other_tools...]
    )
"""

from typing import Callable, Optional

try:
    import dspy  # noqa: F401
except (ImportError, AttributeError):
    raise ImportError(
        "dspy is required for this integration. "
        "Install with: pip install dspy"
    )

from sentinelseed.integrations._base import LayeredValidator, ValidationConfig

# Import from centralized utils
from sentinelseed.integrations.dspy.utils import (
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    TextTooLargeError,
    ValidationTimeoutError,
    HeuristicFallbackError,
    get_logger,
    get_validation_executor,
    validate_provider,
    validate_gate,
    validate_text_size,
    validate_config_types,
    warn_fail_open_default,
)

logger = get_logger()

# Module-level flags to show degraded mode warnings only once per tool type
_sentinel_tool_warning_shown = False
_filter_tool_warning_shown = False
_gate_tool_warning_shown = False


def create_sentinel_tool(
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    name: str = "check_safety",
    use_heuristic: bool = False,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
    allow_heuristic_fallback: bool = False,
) -> Callable:
    """
    Create a Sentinel safety check tool for use with DSPy ReAct.

    The tool validates content through THSP gates and returns
    a structured safety assessment.

    Args:
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model to use for validation
        name: Name of the tool (default: "check_safety")
        use_heuristic: Use pattern-based validation instead of LLM
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, return UNSAFE on errors (default: False)
        allow_heuristic_fallback: If True, allow fallback to heuristic when
            no API key is provided. If False (default), raise HeuristicFallbackError.

    Returns:
        Callable tool function compatible with dspy.ReAct

    Example:
        tool = create_sentinel_tool(api_key="sk-...")
        result = tool("Some content to check")
        # Returns: "SAFE: Content passes all THSP gates"
        # Or: "UNSAFE: Content fails harm gate - could enable harm"
    """
    global _sentinel_tool_warning_shown

    # Validate configuration types
    validate_config_types(
        max_text_size=max_text_size,
        timeout=timeout,
        fail_closed=fail_closed,
    )

    # Validate provider if using semantic validation
    if not use_heuristic and api_key:
        validate_provider(provider)

    # Log warning about fail-open default
    if not fail_closed:
        warn_fail_open_default(logger, f"create_sentinel_tool({name})")

    # Handle missing API key
    if not use_heuristic and not api_key:
        if not allow_heuristic_fallback:
            raise HeuristicFallbackError(f"create_sentinel_tool({name})")

        # Emit warning only once per module to avoid spam
        if not _sentinel_tool_warning_shown:
            _sentinel_tool_warning_shown = True
            logger.warning(
                "\n" + "=" * 60 + "\n"
                "SENTINEL DEGRADED MODE WARNING\n"
                "=" * 60 + "\n"
                f"No API key provided for create_sentinel_tool({name}).\n"
                "Falling back to HEURISTIC validation (~50% accuracy).\n"
                "This significantly reduces safety detection capability.\n"
                "\n"
                "To enable full semantic validation:\n"
                "  - Provide api_key parameter, OR\n"
                "  - Set use_heuristic=True to use heuristic intentionally\n"
                "=" * 60
            )
        use_heuristic = True

    config = ValidationConfig(
        use_heuristic=True,
        use_semantic=bool(api_key) and not use_heuristic,
        semantic_provider=provider,
        semantic_model=model,
        semantic_api_key=api_key,
        max_text_size=max_text_size,
        validation_timeout=timeout,
        fail_closed=fail_closed,
    )
    validator = LayeredValidator(config=config)

    def _do_validation(content: str) -> str:
        """Internal validation logic."""
        result = validator.validate(content)
        if result.is_safe:
            return f"SAFE: Content passes all THSP gates."
        else:
            violations = result.violations if result.violations else ["unknown"]
            return (
                f"UNSAFE: Content fails validation. "
                f"Reason: {'; '.join(violations[:3])}"
                )

    def check_safety(content: str) -> str:
        """
        Check content for safety using THSP protocol.

        Args:
            content: The content to validate

        Returns:
            Safety assessment as a formatted string
        """
        try:
            # Validate text size
            validate_text_size(content, max_text_size)

            # Run validation with timeout using shared executor
            executor = get_validation_executor()
            return executor.run_with_timeout(
                _do_validation,
                args=(content,),
                timeout=timeout,
            )

        except TextTooLargeError as e:
            return f"ERROR: {e}"
        except ValidationTimeoutError as e:
            if fail_closed:
                return f"UNSAFE: Validation timed out after {timeout}s (fail_closed=True)"
            return f"ERROR: {e}"
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            logger.error(f"Validation error in check_safety: {e}")
            if fail_closed:
                return "UNSAFE: Validation error (fail_closed=True)"
            return "ERROR: Validation failed"

    # Set function metadata for DSPy ReAct agents
    # Detailed docstring helps the agent understand WHEN to use this tool
    check_safety.__name__ = name
    check_safety.__doc__ = (
        "Check if content is safe using the THSP (Truth-Harm-Scope-Purpose) protocol.\n\n"
        "WHEN TO USE:\n"
        "- Before generating content about sensitive topics (weapons, hacking, drugs)\n"
        "- Before executing actions that could cause harm\n"
        "- When uncertain if a response might violate safety guidelines\n"
        "- To validate user-provided content before processing\n\n"
        "INPUT: A string containing the content to check\n"
        "OUTPUT: 'SAFE: <reason>' if content passes, 'UNSAFE: <reason>' if it fails\n\n"
        "EXAMPLE: check_safety('How to make a birthday cake') -> 'SAFE: Content passes all THSP gates'"
    )

    return check_safety


def create_content_filter_tool(
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    name: str = "filter_content",
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
    allow_heuristic_fallback: bool = False,
) -> Callable:
    """
    Create a content filtering tool for DSPy ReAct.

    This tool either returns the content unchanged (if safe)
    or returns a refusal message (if unsafe).

    Args:
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        name: Tool name
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, block on errors (default: False)
        allow_heuristic_fallback: If True, allow fallback to heuristic when
            no API key is provided. If False (default), raise HeuristicFallbackError.

    Returns:
        Callable tool function

    Example:
        filter_tool = create_content_filter_tool(api_key="sk-...")
        safe_content = filter_tool("How to make cookies")
        # Returns: "How to make cookies"

        unsafe = filter_tool("How to make a bomb")
        # Returns: "[FILTERED] Content blocked by Sentinel safety check."
    """
    global _filter_tool_warning_shown

    # Validate configuration types
    validate_config_types(
        max_text_size=max_text_size,
        timeout=timeout,
        fail_closed=fail_closed,
    )

    # Validate provider
    if api_key:
        validate_provider(provider)

    # Log warning about fail-open default
    if not fail_closed:
        warn_fail_open_default(logger, f"create_content_filter_tool({name})")

    # Handle missing API key
    use_heuristic = False
    if not api_key:
        if not allow_heuristic_fallback:
            raise HeuristicFallbackError(f"create_content_filter_tool({name})")

        # Emit warning only once per module to avoid spam
        if not _filter_tool_warning_shown:
            _filter_tool_warning_shown = True
            logger.warning(
                "\n" + "=" * 60 + "\n"
                "SENTINEL DEGRADED MODE WARNING\n"
                "=" * 60 + "\n"
                f"No API key provided for create_content_filter_tool({name}).\n"
                "Falling back to HEURISTIC validation (~50% accuracy).\n"
                "This significantly reduces safety detection capability.\n"
                "\n"
                "To enable full semantic validation:\n"
                "  - Provide api_key parameter\n"
                "=" * 60
            )
        use_heuristic = True

    config = ValidationConfig(
        use_heuristic=True,
        use_semantic=bool(api_key),
        semantic_provider=provider,
        semantic_model=model,
        semantic_api_key=api_key,
        max_text_size=max_text_size,
        validation_timeout=timeout,
        fail_closed=fail_closed,
    )
    validator = LayeredValidator(config=config)

    def _do_filter(content: str) -> str:
        """Internal filter logic."""
        result = validator.validate(content)
        if result.is_safe:
            return content
        violations = result.violations if result.violations else ["Safety violation detected"]
        return (
            f"[FILTERED] Content blocked by Sentinel safety check. "
            f"Reason: {violations[0]}"
        )

    def filter_content(content: str) -> str:
        """
        Filter content for safety. Returns original if safe, blocked message if not.

        Args:
            content: Content to filter

        Returns:
            Original content or blocked message
        """
        try:
            # Validate text size
            validate_text_size(content, max_text_size)

            # Run filter with timeout using shared executor
            executor = get_validation_executor()
            return executor.run_with_timeout(
                _do_filter,
                args=(content,),
                timeout=timeout,
            )

        except TextTooLargeError as e:
            return f"[ERROR] {e}"
        except ValidationTimeoutError as e:
            if fail_closed:
                return f"[FILTERED] Validation timed out (fail_closed=True)"
            return f"[ERROR] {e}"
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            logger.error(f"Validation error in filter_content: {e}")
            if fail_closed:
                return "[FILTERED] Validation error (fail_closed=True)"
            return "[ERROR] Validation failed"

    filter_content.__name__ = name
    filter_content.__doc__ = (
        "Filter and sanitize content for safety, returning safe content or a blocked message.\n\n"
        "WHEN TO USE:\n"
        "- To sanitize content before showing to users\n"
        "- To clean up potentially harmful content from external sources\n"
        "- As a final safety check before returning responses\n"
        "- When you want safe content passed through unchanged\n\n"
        "INPUT: A string containing content to filter\n"
        "OUTPUT: Original content if safe, '[FILTERED] <reason>' if unsafe\n\n"
        "EXAMPLE: filter_content('Hello world') -> 'Hello world'"
    )

    return filter_content


def create_gate_check_tool(
    gate: str,
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
    allow_heuristic_fallback: bool = False,
) -> Callable:
    """
    Create a tool that checks a specific THSP gate.

    Args:
        gate: Which gate to check ("truth", "harm", "scope", "purpose")
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, return FAIL on errors (default: False)
        allow_heuristic_fallback: If True, allow fallback to heuristic when
            no API key is provided. If False (default), raise HeuristicFallbackError.

    Returns:
        Callable tool function

    Example:
        harm_check = create_gate_check_tool("harm", api_key="sk-...")
        result = harm_check("How to make cookies")
        # Returns: "PASS: No harm detected"
    """
    global _gate_tool_warning_shown

    # Validate gate parameter
    validate_gate(gate)

    # Validate configuration types
    validate_config_types(
        max_text_size=max_text_size,
        timeout=timeout,
        fail_closed=fail_closed,
    )

    # Validate provider
    if api_key:
        validate_provider(provider)

    # Log warning about fail-open default
    if not fail_closed:
        warn_fail_open_default(logger, f"create_gate_check_tool({gate})")

    # Handle missing API key
    if not api_key:
        if not allow_heuristic_fallback:
            raise HeuristicFallbackError(f"create_gate_check_tool({gate})")

        # Emit warning only once per module to avoid spam
        if not _gate_tool_warning_shown:
            _gate_tool_warning_shown = True
            logger.warning(
                "\n" + "=" * 60 + "\n"
                "SENTINEL DEGRADED MODE WARNING\n"
                "=" * 60 + "\n"
                f"No API key provided for create_gate_check_tool({gate}).\n"
                "Falling back to HEURISTIC validation (~50% accuracy).\n"
                "This significantly reduces safety detection capability.\n"
                "\n"
                "To enable full semantic validation:\n"
                "  - Provide api_key parameter\n"
                "=" * 60
            )

    config = ValidationConfig(
        use_heuristic=True,
        use_semantic=bool(api_key),
        semantic_provider=provider,
        semantic_model=model,
        semantic_api_key=api_key,
        max_text_size=max_text_size,
        validation_timeout=timeout,
        fail_closed=fail_closed,
    )
    validator = LayeredValidator(config=config)

    def _do_gate_check(content: str) -> str:
        """Internal gate check logic."""
        result = validator.validate(content)
        # For gate-specific check, we consider any violation related to that gate
        if result.is_safe:
            return f"PASS: Content passes {gate} gate."
        violations = result.violations if result.violations else ["Validation failed"]
        return f"FAIL: Content fails {gate} gate. Reason: {violations[0]}"

    def check_gate(content: str) -> str:
        """Check if content passes the specified THSP gate."""
        try:
            # Validate text size
            validate_text_size(content, max_text_size)

            # Run gate check with timeout using shared executor
            executor = get_validation_executor()
            return executor.run_with_timeout(
                _do_gate_check,
                args=(content,),
                timeout=timeout,
            )

        except TextTooLargeError as e:
            return f"ERROR: {e}"
        except ValidationTimeoutError as e:
            if fail_closed:
                return f"FAIL: Validation timed out (fail_closed=True)"
            return f"ERROR: {e}"
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            logger.error(f"Validation error in check_{gate}_gate: {e}")
            if fail_closed:
                return "FAIL: Validation error (fail_closed=True)"
            return "ERROR: Validation failed"

    # Gate-specific descriptions for better agent understanding
    gate_descriptions = {
        "truth": "Does this involve deception, false claims, or misinformation?",
        "harm": "Could this enable physical, psychological, or financial harm?",
        "scope": "Is this within appropriate boundaries and authorized limits?",
        "purpose": "Does this serve a legitimate, beneficial purpose?",
    }

    check_gate.__name__ = f"check_{gate}_gate"
    check_gate.__doc__ = (
        f"Check if content passes the {gate.upper()} gate of THSP protocol.\n\n"
        f"GATE QUESTION: {gate_descriptions.get(gate, 'Unknown gate')}\n\n"
        f"WHEN TO USE:\n"
        f"- When you only need to check one specific safety aspect\n"
        f"- For targeted validation of {gate}-related concerns\n"
        f"- When full THSP check is too broad for your needs\n\n"
        f"INPUT: A string containing content to check\n"
        f"OUTPUT: 'PASS: <reason>' or 'FAIL: <reason>'\n\n"
        f"EXAMPLE: check_{gate}_gate('some content') -> 'PASS: Content passes {gate} gate'"
    )

    return check_gate
