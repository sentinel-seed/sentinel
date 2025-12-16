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

from typing import Any, Callable, Dict, Optional
import logging

try:
    import dspy
except ImportError:
    raise ImportError(
        "dspy is required for this integration. "
        "Install with: pip install dspy"
    )

from sentinelseed.validators.semantic import (
    SemanticValidator,
    THSPResult,
)
from sentinelseed.validators.gates import THSPValidator

logger = logging.getLogger("sentinelseed.integrations.dspy")


def create_sentinel_tool(
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    name: str = "check_safety",
    use_heuristic: bool = False,
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

    Returns:
        Callable tool function compatible with dspy.ReAct

    Example:
        tool = create_sentinel_tool(api_key="sk-...")
        result = tool("Some content to check")
        # Returns: "SAFE: Content passes all THSP gates"
        # Or: "UNSAFE: Content fails harm gate - could enable harm"
    """
    # Initialize validator
    if use_heuristic or not api_key:
        if not use_heuristic and not api_key:
            logger.warning(
                "No API key provided. Using heuristic validation."
            )
        validator = THSPValidator()
        is_semantic = False
    else:
        validator = SemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )
        is_semantic = True

    def check_safety(content: str) -> str:
        """
        Check content for safety using THSP protocol.

        Args:
            content: The content to validate

        Returns:
            Safety assessment as a formatted string
        """
        if is_semantic:
            result: THSPResult = validator.validate(content)
            if result.is_safe:
                return f"SAFE: Content passes all THSP gates. {result.reasoning}"
            else:
                failed = result.failed_gates
                return (
                    f"UNSAFE: Content fails {', '.join(failed)} gate(s). "
                    f"Reason: {result.reasoning}"
                )
        else:
            result = validator.validate(content)
            if result.get("safe", True):
                return "SAFE: Content passes all THSP gates (heuristic check)."
            else:
                gates = result.get("gates", {})
                failed = [g for g, v in gates.items() if v == "fail"]
                issues = result.get("issues", [])
                return (
                    f"UNSAFE: Content fails {', '.join(failed)} gate(s). "
                    f"Issues: {'; '.join(issues[:3])}"
                )

    # Set function metadata for DSPy
    check_safety.__name__ = name
    check_safety.__doc__ = (
        "Check if content is safe using THSP protocol. "
        "Returns 'SAFE' or 'UNSAFE' with explanation. "
        "Use this before generating potentially harmful content."
    )

    return check_safety


def create_content_filter_tool(
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    name: str = "filter_content",
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

    Returns:
        Callable tool function

    Example:
        filter_tool = create_content_filter_tool(api_key="sk-...")
        safe_content = filter_tool("How to make cookies")
        # Returns: "How to make cookies"

        unsafe = filter_tool("How to make a bomb")
        # Returns: "[FILTERED] Content blocked by Sentinel safety check."
    """
    if not api_key:
        logger.warning(
            "No API key provided. Using heuristic validation."
        )
        validator = THSPValidator()
        is_semantic = False
    else:
        validator = SemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )
        is_semantic = True

    def filter_content(content: str) -> str:
        """
        Filter content for safety. Returns original if safe, blocked message if not.

        Args:
            content: Content to filter

        Returns:
            Original content or blocked message
        """
        if is_semantic:
            result: THSPResult = validator.validate(content)
            if result.is_safe:
                return content
            return (
                f"[FILTERED] Content blocked by Sentinel safety check. "
                f"Reason: {result.reasoning}"
            )
        else:
            result = validator.validate(content)
            if result.get("safe", True):
                return content
            issues = result.get("issues", ["Safety violation detected"])
            return (
                f"[FILTERED] Content blocked by Sentinel safety check. "
                f"Issue: {issues[0] if issues else 'Unknown'}"
            )

    filter_content.__name__ = name
    filter_content.__doc__ = (
        "Filter content for safety. Returns original content if safe, "
        "or a blocked message if unsafe. Use to sanitize outputs."
    )

    return filter_content


def create_gate_check_tool(
    gate: str,
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
) -> Callable:
    """
    Create a tool that checks a specific THSP gate.

    Args:
        gate: Which gate to check ("truth", "harm", "scope", "purpose")
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation

    Returns:
        Callable tool function

    Example:
        harm_check = create_gate_check_tool("harm", api_key="sk-...")
        result = harm_check("How to make cookies")
        # Returns: "PASS: No harm detected"
    """
    valid_gates = {"truth", "harm", "scope", "purpose"}
    if gate not in valid_gates:
        raise ValueError(f"Invalid gate '{gate}'. Must be one of {valid_gates}")

    if not api_key:
        validator = THSPValidator()
        is_semantic = False
    else:
        validator = SemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )
        is_semantic = True

    def check_gate(content: str) -> str:
        f"""
        Check if content passes the {gate} gate.

        Args:
            content: Content to check

        Returns:
            PASS or FAIL with explanation
        """
        if is_semantic:
            result: THSPResult = validator.validate(content)
            gate_result = result.gate_results.get(gate, True)
            if gate_result:
                return f"PASS: Content passes {gate} gate."
            return f"FAIL: Content fails {gate} gate. {result.reasoning}"
        else:
            result = validator.validate(content)
            gates = result.get("gates", {})
            gate_result = gates.get(gate, "pass")
            if gate_result == "pass":
                return f"PASS: Content passes {gate} gate (heuristic)."
            return f"FAIL: Content fails {gate} gate (heuristic)."

    check_gate.__name__ = f"check_{gate}_gate"
    check_gate.__doc__ = (
        f"Check if content passes the {gate.upper()} gate of THSP protocol. "
        f"Returns 'PASS' or 'FAIL' with explanation."
    )

    return check_gate
