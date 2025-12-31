"""Standalone callback functions for Google ADK agents.

This module provides callback functions that can be registered directly
on ADK agents for THSP validation. Unlike the SentinelPlugin which
applies globally to a Runner, these callbacks can be applied to
individual agents.

The callbacks follow ADK's callback signatures and can be passed to
LlmAgent constructors.

Example:
    from google.adk.agents import LlmAgent
    from sentinelseed.integrations.google_adk import (
        create_before_model_callback,
        create_after_model_callback,
    )

    agent = LlmAgent(
        name="SafeAgent",
        model="gemini-2.0-flash",
        instruction="You are a helpful assistant.",
        before_model_callback=create_before_model_callback(
            seed_level="standard",
            block_on_failure=True,
        ),
        after_model_callback=create_after_model_callback(
            seed_level="standard",
        ),
    )
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Callable, Optional

from .utils import (
    ADK_AVAILABLE,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_SEED_LEVEL,
    DEFAULT_VALIDATION_TIMEOUT,
    TextTooLargeError,
    ValidationTimeoutError,
    create_blocked_response,
    extract_text_from_llm_request,
    extract_text_from_llm_response,
    extract_tool_input_text,
    get_logger,
    get_validation_executor,
    require_adk,
    validate_text_size,
)

if TYPE_CHECKING:
    from sentinelseed import Sentinel

if ADK_AVAILABLE:
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models import LlmRequest, LlmResponse
    from google.adk.tools.tool_context import ToolContext
else:
    # Type stubs for when ADK is not installed
    CallbackContext = Any
    LlmRequest = Any
    LlmResponse = Any
    ToolContext = Any


_logger = get_logger()


# Type aliases for callback signatures
BeforeModelCallback = Callable[..., Any]
AfterModelCallback = Callable[..., Any]
BeforeToolCallback = Callable[..., Any]
AfterToolCallback = Callable[..., Any]


def _get_sentinel(sentinel: Optional[Sentinel], seed_level: str) -> Sentinel:
    """Get or create a Sentinel instance.

    Args:
        sentinel: Optional existing Sentinel instance.
        seed_level: Seed level to use if creating new instance.

    Returns:
        Sentinel instance.
    """
    if sentinel is not None:
        return sentinel

    from sentinelseed import Sentinel
    return Sentinel(seed_level=seed_level)


def _validate_content_sync(
    sentinel: Sentinel,
    content: str,
    max_text_size: int,
    validation_timeout: float,
    fail_closed: bool,
) -> Optional[dict[str, Any]]:
    """Synchronously validate content.

    Args:
        sentinel: Sentinel instance.
        content: Content to validate.
        max_text_size: Maximum text size.
        validation_timeout: Timeout in seconds.
        fail_closed: Whether to block on errors.

    Returns:
        None if safe, or dict with violation details.
    """
    # Size check
    try:
        validate_text_size(content, max_text_size, "content")
    except TextTooLargeError as e:
        return {
            "reason": str(e),
            "concerns": [f"Text too large: {e.size:,} bytes"],
            "risk_level": "high",
        }

    # THSP validation
    try:
        executor = get_validation_executor()
        result = executor.run_with_timeout(
            sentinel.validate,
            args=(content,),
            timeout=validation_timeout,
        )
    except ValidationTimeoutError as e:
        _logger.warning("Validation timeout: %s", e)
        if fail_closed:
            return {
                "reason": str(e),
                "concerns": ["Validation timed out"],
                "risk_level": "unknown",
            }
        return None
    except Exception as e:
        _logger.error("Validation error: %s", e)
        if fail_closed:
            return {
                "reason": str(e),
                "concerns": [f"Error: {e}"],
                "risk_level": "unknown",
            }
        return None

    # Check result
    # validate() returns (is_safe: bool, violations: list)
    if isinstance(result, tuple):
        is_safe, violations = result
        concerns = violations if isinstance(violations, list) else []
    elif isinstance(result, dict):
        # Backwards compatibility with dict format
        is_safe = result.get("should_proceed", result.get("is_safe", True))
        concerns = result.get("concerns", result.get("violations", []))
    else:
        is_safe = bool(result)
        concerns = []

    if is_safe:
        return None

    return {
        "reason": "THSP validation failed",
        "concerns": concerns,
        "risk_level": "high" if concerns else "medium",
        "gates": {},
    }


def create_before_model_callback(
    sentinel: Optional[Sentinel] = None,
    seed_level: str = DEFAULT_SEED_LEVEL,
    block_on_failure: bool = True,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
    blocked_message: str = "Request blocked by Sentinel safety validation.",
) -> BeforeModelCallback:
    """Create a before_model_callback for input validation.

    This factory function creates a callback that validates user input
    before it is sent to the LLM. The callback can block requests that
    fail THSP validation.

    Args:
        sentinel: Optional Sentinel instance. If not provided, a new
            instance is created with the specified seed_level.
        seed_level: Safety level (minimal, standard, full).
        block_on_failure: If True, returns blocked response on failure.
        max_text_size: Maximum input size in bytes.
        validation_timeout: Timeout for validation in seconds.
        fail_closed: If True, errors cause blocking.
        blocked_message: Message returned when blocked.

    Returns:
        A callback function compatible with LlmAgent.before_model_callback.

    Example:
        from google.adk.agents import LlmAgent
        from sentinelseed.integrations.google_adk import create_before_model_callback

        callback = create_before_model_callback(
            seed_level="standard",
            block_on_failure=True,
        )

        agent = LlmAgent(
            name="SafeAgent",
            model="gemini-2.0-flash",
            before_model_callback=callback,
        )
    """
    require_adk()

    # Initialize Sentinel once
    _sentinel = _get_sentinel(sentinel, seed_level)

    def before_model_callback(
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """Validate input before LLM call."""
        try:
            # Extract content
            content = extract_text_from_llm_request(llm_request)
            if not content or content.strip() == "":
                return None

            # Validate
            result = _validate_content_sync(
                _sentinel, content, max_text_size, validation_timeout, fail_closed
            )

            if result is None:
                return None

            # Content failed validation
            if block_on_failure:
                return create_blocked_response(blocked_message)

            _logger.warning(
                "Input validation failed but not blocking: %s",
                result.get("concerns", []),
            )
            return None

        except Exception as e:
            _logger.error("Error in before_model_callback: %s", e)
            if fail_closed and block_on_failure:
                return create_blocked_response(blocked_message)
            return None

    return before_model_callback


def create_after_model_callback(
    sentinel: Optional[Sentinel] = None,
    seed_level: str = DEFAULT_SEED_LEVEL,
    block_on_failure: bool = True,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
    blocked_message: str = "Response blocked by Sentinel safety validation.",
) -> AfterModelCallback:
    """Create an after_model_callback for output validation.

    This factory function creates a callback that validates LLM output
    before it is returned to the user.

    Args:
        sentinel: Optional Sentinel instance.
        seed_level: Safety level (minimal, standard, full).
        block_on_failure: If True, replaces unsafe responses.
        max_text_size: Maximum output size in bytes.
        validation_timeout: Timeout for validation in seconds.
        fail_closed: If True, errors cause blocking.
        blocked_message: Message used when blocking.

    Returns:
        A callback function compatible with LlmAgent.after_model_callback.

    Example:
        agent = LlmAgent(
            name="SafeAgent",
            after_model_callback=create_after_model_callback(
                seed_level="standard",
            ),
        )
    """
    require_adk()

    _sentinel = _get_sentinel(sentinel, seed_level)

    def after_model_callback(
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> Optional[LlmResponse]:
        """Validate LLM output."""
        try:
            # Extract content
            content = extract_text_from_llm_response(llm_response)
            if not content or content.strip() == "":
                return None

            # Validate
            result = _validate_content_sync(
                _sentinel, content, max_text_size, validation_timeout, fail_closed
            )

            if result is None:
                return None

            # Content failed validation
            if block_on_failure:
                return create_blocked_response(blocked_message)

            _logger.warning(
                "Output validation failed but not blocking: %s",
                result.get("concerns", []),
            )
            return None

        except Exception as e:
            _logger.error("Error in after_model_callback: %s", e)
            if fail_closed and block_on_failure:
                return create_blocked_response(blocked_message)
            return None

    return after_model_callback


def create_before_tool_callback(
    sentinel: Optional[Sentinel] = None,
    seed_level: str = DEFAULT_SEED_LEVEL,
    block_on_failure: bool = True,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
) -> BeforeToolCallback:
    """Create a before_tool_callback for tool argument validation.

    This factory function creates a callback that validates tool
    arguments before the tool is executed.

    Args:
        sentinel: Optional Sentinel instance.
        seed_level: Safety level (minimal, standard, full).
        block_on_failure: If True, blocks tool execution on failure.
        max_text_size: Maximum text size in bytes.
        validation_timeout: Timeout for validation in seconds.
        fail_closed: If True, errors cause blocking.

    Returns:
        A callback function compatible with LlmAgent.before_tool_callback.

    Example:
        agent = LlmAgent(
            name="SafeAgent",
            before_tool_callback=create_before_tool_callback(
                seed_level="standard",
            ),
        )
    """
    require_adk()

    _sentinel = _get_sentinel(sentinel, seed_level)

    def before_tool_callback(
        tool: Any,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        """Validate tool arguments before execution."""
        try:
            # Extract text from args
            content = extract_tool_input_text(tool_args)
            if not content or content.strip() == "":
                return None

            # Validate
            result = _validate_content_sync(
                _sentinel, content, max_text_size, validation_timeout, fail_closed
            )

            if result is None:
                return None

            # Content failed validation
            if block_on_failure:
                return {
                    "status": "blocked",
                    "error": "Tool arguments blocked by Sentinel validation.",
                    "concerns": result.get("concerns", []),
                }

            return None

        except Exception as e:
            _logger.error("Error in before_tool_callback: %s", e)
            if fail_closed and block_on_failure:
                return {
                    "status": "error",
                    "error": f"Validation error: {e}",
                }
            return None

    return before_tool_callback


def create_after_tool_callback(
    sentinel: Optional[Sentinel] = None,
    seed_level: str = DEFAULT_SEED_LEVEL,
    block_on_failure: bool = True,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
) -> AfterToolCallback:
    """Create an after_tool_callback for tool result validation.

    This factory function creates a callback that validates tool
    results before they are passed to the LLM.

    Args:
        sentinel: Optional Sentinel instance.
        seed_level: Safety level (minimal, standard, full).
        block_on_failure: If True, replaces unsafe results.
        max_text_size: Maximum text size in bytes.
        validation_timeout: Timeout for validation in seconds.
        fail_closed: If True, errors cause blocking.

    Returns:
        A callback function compatible with LlmAgent.after_tool_callback.

    Example:
        agent = LlmAgent(
            name="SafeAgent",
            after_tool_callback=create_after_tool_callback(
                seed_level="standard",
            ),
        )
    """
    require_adk()

    _sentinel = _get_sentinel(sentinel, seed_level)

    def after_tool_callback(
        tool: Any,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        tool_result: dict,
    ) -> Optional[dict]:
        """Validate tool result."""
        try:
            # Extract text from result
            content = _extract_result_text(tool_result)
            if not content or content.strip() == "":
                return None

            # Validate
            result = _validate_content_sync(
                _sentinel, content, max_text_size, validation_timeout, fail_closed
            )

            if result is None:
                return None

            # Content failed validation
            if block_on_failure:
                return {
                    "status": "blocked",
                    "error": "Tool result blocked by Sentinel validation.",
                    "original_blocked": True,
                }

            return None

        except Exception as e:
            _logger.error("Error in after_tool_callback: %s", e)
            if fail_closed and block_on_failure:
                return {
                    "status": "error",
                    "error": f"Validation error: {e}",
                }
            return None

    return after_tool_callback


def _extract_result_text(result: Any) -> str:
    """Extract text from a tool result."""
    if isinstance(result, str):
        return result
    if isinstance(result, dict):
        texts = []
        for value in result.values():
            if isinstance(value, str):
                texts.append(value)
        return " ".join(texts)
    return ""


def create_sentinel_callbacks(
    sentinel: Optional[Sentinel] = None,
    seed_level: str = DEFAULT_SEED_LEVEL,
    block_on_failure: bool = True,
    fail_closed: bool = False,
    validate_inputs: bool = True,
    validate_outputs: bool = True,
    validate_tools: bool = True,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create a complete set of Sentinel callbacks for an agent.

    This convenience function creates all four callback types in a
    dictionary that can be unpacked into an LlmAgent constructor.

    Args:
        sentinel: Optional Sentinel instance (shared across callbacks).
        seed_level: Safety level (minimal, standard, full).
        block_on_failure: Whether to block unsafe content.
        fail_closed: Whether to block on errors.
        validate_inputs: Include before_model_callback.
        validate_outputs: Include after_model_callback.
        validate_tools: Include tool callbacks.
        **kwargs: Additional arguments passed to callback factories.

    Returns:
        Dictionary of callbacks that can be unpacked into LlmAgent.

    Example:
        from sentinelseed.integrations.google_adk import create_sentinel_callbacks

        callbacks = create_sentinel_callbacks(
            seed_level="standard",
            block_on_failure=True,
        )

        agent = LlmAgent(
            name="SafeAgent",
            model="gemini-2.0-flash",
            **callbacks,
        )
    """
    require_adk()

    # Create shared Sentinel instance
    _sentinel = _get_sentinel(sentinel, seed_level)

    callbacks = {}

    if validate_inputs:
        callbacks["before_model_callback"] = create_before_model_callback(
            sentinel=_sentinel,
            seed_level=seed_level,
            block_on_failure=block_on_failure,
            fail_closed=fail_closed,
            **kwargs,
        )

    if validate_outputs:
        callbacks["after_model_callback"] = create_after_model_callback(
            sentinel=_sentinel,
            seed_level=seed_level,
            block_on_failure=block_on_failure,
            fail_closed=fail_closed,
            **kwargs,
        )

    if validate_tools:
        callbacks["before_tool_callback"] = create_before_tool_callback(
            sentinel=_sentinel,
            seed_level=seed_level,
            block_on_failure=block_on_failure,
            fail_closed=fail_closed,
            **kwargs,
        )
        callbacks["after_tool_callback"] = create_after_tool_callback(
            sentinel=_sentinel,
            seed_level=seed_level,
            block_on_failure=block_on_failure,
            fail_closed=fail_closed,
            **kwargs,
        )

    return callbacks
