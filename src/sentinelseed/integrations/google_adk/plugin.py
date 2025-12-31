"""Sentinel Plugin for Google ADK.

This module provides a global plugin that integrates Sentinel's THSP
validation into the ADK Runner lifecycle. The plugin applies to all
agents, tools, and LLM calls within the runner.

The plugin extends ADK's BasePlugin and implements callbacks at key
execution points:
- before_model_callback: Validates user inputs before LLM calls
- after_model_callback: Validates LLM outputs before returning
- before_tool_callback: Validates tool arguments
- after_tool_callback: Validates tool results

Example:
    from google.adk.runners import Runner
    from sentinelseed.integrations.google_adk import SentinelPlugin

    plugin = SentinelPlugin(
        seed_level="standard",
        block_on_failure=True,
    )

    runner = Runner(
        agent=my_agent,
        plugins=[plugin],
    )

    response = await runner.run("Hello, world!")
"""

from __future__ import annotations

import threading
import time
from typing import TYPE_CHECKING, Any, Optional

from .utils import (
    ADK_AVAILABLE,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_SEED_LEVEL,
    DEFAULT_VALIDATION_TIMEOUT,
    ConfigurationError,
    TextTooLargeError,
    ThreadSafeDeque,
    ValidationTimeoutError,
    create_blocked_response,
    create_empty_stats,
    extract_text_from_llm_request,
    extract_text_from_llm_response,
    extract_tool_input_text,
    format_violation,
    get_logger,
    get_validation_executor,
    log_fail_open_warning,
    require_adk,
    validate_configuration,
    validate_text_size,
)

if TYPE_CHECKING:
    from sentinelseed import Sentinel

# Import ADK types conditionally
if ADK_AVAILABLE:
    from google.adk.agents import BaseAgent
    from google.adk.agents.callback_context import CallbackContext
    from google.adk.models import LlmRequest, LlmResponse
    from google.adk.plugins.base_plugin import BasePlugin
    from google.adk.tools.base_tool import BaseTool
    from google.adk.tools.tool_context import ToolContext
    from google.genai import types

    _BASE_CLASS = BasePlugin
else:
    _BASE_CLASS = object
    BaseAgent = None
    CallbackContext = None
    LlmRequest = None
    LlmResponse = None
    BasePlugin = None
    BaseTool = None
    ToolContext = None
    types = None


_logger = get_logger()


class SentinelPlugin(_BASE_CLASS):
    """Global Sentinel safety plugin for Google ADK.

    This plugin integrates Sentinel's THSP (Truth, Harm, Scope, Purpose)
    validation into the ADK Runner. It validates inputs and outputs at
    multiple points in the agent lifecycle.

    The plugin operates at the Runner level, meaning it applies to ALL
    agents, tools, and LLM calls within the runner. For agent-specific
    validation, use the callback functions directly.

    Validation Points:
        - before_model_callback: Validates user input before LLM processing
        - after_model_callback: Validates LLM output before returning
        - before_tool_callback: Validates tool arguments
        - after_tool_callback: Validates tool results

    Attributes:
        name: Plugin identifier ("sentinel").
        sentinel: The Sentinel instance used for validation.
        seed_level: Current safety level (minimal, standard, full).
        block_on_failure: Whether unsafe content is blocked.
        fail_closed: Whether errors cause blocking.

    Example:
        from google.adk.runners import Runner
        from sentinelseed.integrations.google_adk import SentinelPlugin

        # Create plugin with default settings
        plugin = SentinelPlugin()

        # Or with custom configuration
        plugin = SentinelPlugin(
            seed_level="full",
            block_on_failure=True,
            fail_closed=True,
            validate_inputs=True,
            validate_outputs=True,
            validate_tools=True,
        )

        # Register with runner
        runner = Runner(agent=my_agent, plugins=[plugin])

        # Get validation stats
        stats = plugin.get_stats()
        print(f"Blocked: {stats['blocked_count']}")

    Note:
        This plugin requires Google ADK to be installed:
        pip install google-adk

        The plugin runs in fail-open mode by default. Set fail_closed=True
        for security-critical applications.
    """

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = DEFAULT_SEED_LEVEL,
        block_on_failure: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        log_violations: bool = True,
        validate_inputs: bool = True,
        validate_outputs: bool = True,
        validate_tools: bool = True,
        blocked_message: str = "Request blocked by Sentinel safety validation.",
    ) -> None:
        """Initialize the Sentinel plugin.

        Args:
            sentinel: Optional Sentinel instance. If not provided, a new
                instance is created with the specified seed_level.
            seed_level: Safety level for the seed. One of 'minimal',
                'standard', or 'full'. Defaults to 'standard'.
            block_on_failure: If True, returns a blocked response when
                validation fails. If False, logs warnings but allows
                content. Defaults to True.
            max_text_size: Maximum text size in bytes. Content exceeding
                this limit is blocked immediately. Defaults to 100,000.
            validation_timeout: Maximum time in seconds for THSP validation.
                Defaults to 5.0 seconds.
            fail_closed: If True, validation errors (timeouts, exceptions)
                cause content to be blocked. If False (default), errors
                are logged and content is allowed.
            log_violations: If True, violations are recorded and available
                via get_violations(). Defaults to True.
            validate_inputs: If True, validates inputs before LLM calls.
                Defaults to True.
            validate_outputs: If True, validates LLM outputs.
                Defaults to True.
            validate_tools: If True, validates tool arguments and results.
                Defaults to True.
            blocked_message: Message returned when content is blocked.
                Defaults to "Request blocked by Sentinel safety validation."

        Raises:
            ConfigurationError: If any configuration parameter is invalid.
            ImportError: If Google ADK is not installed.

        Note:
            The fail_closed parameter represents a security vs. availability
            trade-off. The default (False) prioritizes availability.
        """
        # Verify ADK is installed
        require_adk()

        # Initialize parent class
        super().__init__(name="sentinel")

        # Validate configuration
        validate_configuration(
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            seed_level=seed_level,
            fail_closed=fail_closed,
            block_on_failure=block_on_failure,
            log_violations=log_violations,
        )

        # Initialize Sentinel
        if sentinel is not None:
            self._sentinel = sentinel
        else:
            from sentinelseed import Sentinel
            self._sentinel = Sentinel(seed_level=seed_level)

        # Store configuration
        self._seed_level = seed_level.lower()
        self._block_on_failure = block_on_failure
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed
        self._log_violations = log_violations
        self._validate_inputs = validate_inputs
        self._validate_outputs = validate_outputs
        self._validate_tools = validate_tools
        self._blocked_message = blocked_message

        # Initialize tracking
        self._violations = ThreadSafeDeque()
        self._stats = create_empty_stats()
        self._stats_lock = threading.Lock()

        # Log fail-open warning
        if not fail_closed:
            log_fail_open_warning("SentinelPlugin")

        _logger.debug(
            "SentinelPlugin initialized: seed_level=%s, block=%s, fail_closed=%s",
            seed_level,
            block_on_failure,
            fail_closed,
        )

    @property
    def sentinel(self) -> Sentinel:
        """The Sentinel instance used for validation."""
        return self._sentinel

    @property
    def seed_level(self) -> str:
        """The safety level being used."""
        return self._seed_level

    @property
    def block_on_failure(self) -> bool:
        """Whether unsafe content is blocked."""
        return self._block_on_failure

    @property
    def fail_closed(self) -> bool:
        """Whether validation errors cause blocking."""
        return self._fail_closed

    async def before_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
    ) -> Optional[LlmResponse]:
        """Validate input before LLM call.

        This callback intercepts requests before they are sent to the LLM.
        It extracts user text from the request and validates it against
        the THSP protocol.

        Args:
            callback_context: ADK callback context with agent info and state.
            llm_request: The request being sent to the LLM.

        Returns:
            None to allow the request, or LlmResponse to block it.
        """
        if not self._validate_inputs:
            return None

        start_time = time.perf_counter()

        try:
            # Extract content from request
            content = extract_text_from_llm_request(llm_request)
            if not content or content.strip() == "":
                _logger.debug("Empty content, skipping input validation")
                return None

            # Run validation
            result = await self._validate_content_async(content, "input")

            # Calculate validation time
            validation_time = (time.perf_counter() - start_time) * 1000

            if result is None:
                # Content is safe
                self._update_stats(allowed=True, validation_time=validation_time)
                return None

            # Content was blocked
            self._update_stats(
                allowed=False,
                validation_time=validation_time,
                gate_failures=result.get("gate_failures"),
            )

            if self._block_on_failure:
                return create_blocked_response(self._blocked_message)

            return None

        except Exception as e:
            validation_time = (time.perf_counter() - start_time) * 1000
            _logger.error("Error in before_model_callback: %s", e)
            self._update_stats(error=True, validation_time=validation_time)

            if self._fail_closed and self._block_on_failure:
                return create_blocked_response(self._blocked_message)

            return None

    async def after_model_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_response: LlmResponse,
    ) -> Optional[LlmResponse]:
        """Validate LLM output before returning.

        This callback intercepts LLM responses before they are returned
        to the user. It validates the response text against THSP.

        Args:
            callback_context: ADK callback context.
            llm_response: The LLM's response.

        Returns:
            None to accept the response, or LlmResponse to replace it.
        """
        if not self._validate_outputs:
            return None

        start_time = time.perf_counter()

        try:
            # Extract content from response
            content = extract_text_from_llm_response(llm_response)
            if not content or content.strip() == "":
                _logger.debug("Empty content, skipping output validation")
                return None

            # Run validation
            result = await self._validate_content_async(content, "output")

            # Calculate validation time
            validation_time = (time.perf_counter() - start_time) * 1000

            if result is None:
                # Content is safe
                self._update_stats(allowed=True, validation_time=validation_time)
                return None

            # Content was blocked
            self._update_stats(
                allowed=False,
                validation_time=validation_time,
                gate_failures=result.get("gate_failures"),
            )

            if self._block_on_failure:
                return create_blocked_response(
                    "Response blocked by Sentinel safety validation."
                )

            return None

        except Exception as e:
            validation_time = (time.perf_counter() - start_time) * 1000
            _logger.error("Error in after_model_callback: %s", e)
            self._update_stats(error=True, validation_time=validation_time)

            if self._fail_closed and self._block_on_failure:
                return create_blocked_response(
                    "Response blocked due to validation error."
                )

            return None

    async def before_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
    ) -> Optional[dict]:
        """Validate tool arguments before execution.

        This callback validates the arguments being passed to a tool
        before the tool is executed.

        Args:
            tool: The tool being called.
            tool_args: Arguments being passed to the tool.
            tool_context: Tool execution context.

        Returns:
            None to allow execution, or dict to skip tool and use this result.
        """
        if not self._validate_tools:
            return None

        start_time = time.perf_counter()

        try:
            # Extract text from tool arguments
            content = extract_tool_input_text(tool_args)
            if not content or content.strip() == "":
                _logger.debug("No text in tool args, skipping validation")
                return None

            # Run validation
            result = await self._validate_content_async(content, "tool_input")

            # Calculate validation time
            validation_time = (time.perf_counter() - start_time) * 1000

            if result is None:
                # Content is safe
                self._update_stats(allowed=True, validation_time=validation_time)
                return None

            # Content was blocked
            self._update_stats(
                allowed=False,
                validation_time=validation_time,
                gate_failures=result.get("gate_failures"),
            )

            if self._block_on_failure:
                tool_name = getattr(tool, "name", "unknown")
                return {
                    "status": "blocked",
                    "error": f"Tool '{tool_name}' blocked by Sentinel safety validation.",
                    "concerns": result.get("concerns", []),
                }

            return None

        except Exception as e:
            validation_time = (time.perf_counter() - start_time) * 1000
            _logger.error("Error in before_tool_callback: %s", e)
            self._update_stats(error=True, validation_time=validation_time)

            if self._fail_closed and self._block_on_failure:
                return {
                    "status": "error",
                    "error": "Tool blocked due to validation error.",
                }

            return None

    async def after_tool_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        result: dict,
    ) -> Optional[dict]:
        """Validate tool results after execution.

        This callback validates the results returned by a tool before
        they are passed to the LLM.

        Args:
            tool: The tool that was called.
            tool_args: Arguments that were passed.
            tool_context: Tool execution context.
            result: The tool's result.

        Returns:
            None to accept the result, or dict to replace it.
        """
        if not self._validate_tools:
            return None

        start_time = time.perf_counter()

        try:
            # Extract text from result
            content = self._extract_text_from_result(result)
            if not content or content.strip() == "":
                _logger.debug("No text in tool result, skipping validation")
                return None

            # Run validation
            validation_result = await self._validate_content_async(
                content, "tool_output"
            )

            # Calculate validation time
            validation_time = (time.perf_counter() - start_time) * 1000

            if validation_result is None:
                # Content is safe
                self._update_stats(allowed=True, validation_time=validation_time)
                return None

            # Content was blocked
            self._update_stats(
                allowed=False,
                validation_time=validation_time,
                gate_failures=validation_result.get("gate_failures"),
            )

            if self._block_on_failure:
                return {
                    "status": "blocked",
                    "error": "Tool result blocked by Sentinel safety validation.",
                    "original_blocked": True,
                }

            return None

        except Exception as e:
            validation_time = (time.perf_counter() - start_time) * 1000
            _logger.error("Error in after_tool_callback: %s", e)
            self._update_stats(error=True, validation_time=validation_time)

            if self._fail_closed and self._block_on_failure:
                return {
                    "status": "error",
                    "error": "Tool result blocked due to validation error.",
                }

            return None

    async def on_model_error_callback(
        self,
        *,
        callback_context: CallbackContext,
        llm_request: LlmRequest,
        error: Exception,
    ) -> Optional[LlmResponse]:
        """Handle LLM errors.

        This callback is invoked when the LLM call fails. It can provide
        a fallback response or allow the error to propagate.

        Args:
            callback_context: ADK callback context.
            llm_request: The request that failed.
            error: The exception that occurred.

        Returns:
            None to propagate the error, or LlmResponse for fallback.
        """
        _logger.warning("LLM error occurred: %s", error)
        self._update_stats(error=True)

        # Let the error propagate (no fallback response)
        return None

    async def on_tool_error_callback(
        self,
        *,
        tool: BaseTool,
        tool_args: dict[str, Any],
        tool_context: ToolContext,
        error: Exception,
    ) -> Optional[dict]:
        """Handle tool errors.

        This callback is invoked when a tool execution fails.

        Args:
            tool: The tool that failed.
            tool_args: Arguments that were passed.
            tool_context: Tool execution context.
            error: The exception that occurred.

        Returns:
            None to propagate the error, or dict for fallback result.
        """
        tool_name = getattr(tool, "name", "unknown")
        _logger.warning("Tool '%s' error: %s", tool_name, error)
        self._update_stats(error=True)

        # Let the error propagate
        return None

    async def close(self) -> None:
        """Clean up plugin resources.

        Called when the Runner is closed. Performs cleanup of any
        resources held by the plugin.
        """
        _logger.debug("SentinelPlugin closing")
        # No async resources to clean up

    async def _validate_content_async(
        self, content: str, source: str
    ) -> Optional[dict[str, Any]]:
        """Validate content asynchronously.

        Args:
            content: Text content to validate.
            source: Source identifier (input, output, tool_input, tool_output).

        Returns:
            None if content is safe, or dict with violation details.
        """
        import asyncio

        # Size check first (fast, no external calls)
        try:
            validate_text_size(content, self._max_text_size, source)
        except TextTooLargeError as e:
            _logger.warning("%s exceeds size limit: %s", source.capitalize(), e)
            return {
                "reason": str(e),
                "concerns": [f"Text too large: {e.size:,} bytes"],
                "risk_level": "high",
                "gate_failures": {},
            }

        # THSP validation with timeout (run in thread to avoid blocking)
        try:
            executor = get_validation_executor()

            def validate_sync():
                return self._sentinel.validate(content)

            check_result = await asyncio.to_thread(
                executor.run_with_timeout,
                validate_sync,
                timeout=self._validation_timeout,
            )

        except ValidationTimeoutError as e:
            _logger.warning("Validation timeout for %s: %s", source, e)
            self._update_stats(timeout=True)

            if self._fail_closed:
                return {
                    "reason": str(e),
                    "concerns": ["Validation timed out"],
                    "risk_level": "unknown",
                    "gate_failures": {},
                }
            return None  # Fail-open

        except Exception as e:
            _logger.error("Validation error for %s: %s", source, e)
            if self._fail_closed:
                return {
                    "reason": str(e),
                    "concerns": [f"Validation error: {e}"],
                    "risk_level": "unknown",
                    "gate_failures": {},
                }
            return None  # Fail-open

        # Analyze result
        # validate() returns (is_safe: bool, violations: list)
        if isinstance(check_result, tuple):
            is_safe, violations = check_result
            concerns = violations if isinstance(violations, list) else []
        elif isinstance(check_result, dict):
            # Backwards compatibility with dict format
            is_safe = check_result.get("should_proceed", check_result.get("is_safe", True))
            concerns = check_result.get("concerns", check_result.get("violations", []))
        else:
            is_safe = bool(check_result)
            concerns = []

        if is_safe:
            return None  # Content is safe

        # Content is unsafe - extract details
        risk_level = "high" if concerns else "medium"

        # Derive gate failures from violation patterns
        gate_failures = {}
        for concern in concerns:
            concern_lower = str(concern).lower()
            if "truth" in concern_lower or "factual" in concern_lower:
                gate_failures["truth"] = True
            if "harm" in concern_lower or "dangerous" in concern_lower or "violence" in concern_lower:
                gate_failures["harm"] = True
            if "scope" in concern_lower or "instruction" in concern_lower or "override" in concern_lower:
                gate_failures["scope"] = True
            if "purpose" in concern_lower or "justification" in concern_lower:
                gate_failures["purpose"] = True

        # Record violation
        if self._log_violations:
            violation = format_violation(
                content=content,
                concerns=concerns,
                risk_level=risk_level,
                gates={k: not v for k, v in gate_failures.items()},  # Invert for gate status
                source=source,
            )
            self._violations.append(violation)

        return {
            "reason": f"THSP validation failed: {', '.join(str(c)[:50] for c in concerns[:3])}",
            "concerns": concerns,
            "risk_level": risk_level,
            "gate_failures": gate_failures,
        }

    def _extract_text_from_result(self, result: Any) -> str:
        """Extract text content from a tool result.

        Args:
            result: Tool result (dict, string, or other).

        Returns:
            Extracted text content.
        """
        if isinstance(result, str):
            return result

        if isinstance(result, dict):
            texts = []
            for key, value in result.items():
                if isinstance(value, str):
                    texts.append(value)
                elif isinstance(value, dict):
                    texts.append(self._extract_text_from_result(value))
            return " ".join(texts)

        return str(result) if result else ""

    def _update_stats(
        self,
        allowed: Optional[bool] = None,
        timeout: bool = False,
        error: bool = False,
        validation_time: float = 0.0,
        gate_failures: Optional[dict[str, bool]] = None,
    ) -> None:
        """Update internal statistics (thread-safe).

        Args:
            allowed: Whether content was allowed (True) or blocked (False).
            timeout: Whether a timeout occurred.
            error: Whether an error occurred.
            validation_time: Validation time in milliseconds.
            gate_failures: Dict of gate names that failed.
        """
        with self._stats_lock:
            self._stats["total_validations"] += 1

            if allowed is True:
                self._stats["allowed_count"] += 1
            elif allowed is False:
                self._stats["blocked_count"] += 1

            if timeout:
                self._stats["timeout_count"] += 1
            if error:
                self._stats["error_count"] += 1

            # Update gate failure counts
            if gate_failures:
                for gate_name, failed in gate_failures.items():
                    if failed and gate_name in self._stats["gate_failures"]:
                        self._stats["gate_failures"][gate_name] += 1

            # Exponential moving average for validation time
            total = self._stats["total_validations"]
            if total == 1:
                self._stats["avg_validation_time_ms"] = validation_time
            else:
                alpha = 0.1
                self._stats["avg_validation_time_ms"] = (
                    alpha * validation_time
                    + (1 - alpha) * self._stats["avg_validation_time_ms"]
                )

    def get_violations(self) -> list[dict[str, Any]]:
        """Get list of recorded violations.

        Returns:
            List of violation dictionaries containing:
            - content_preview: Truncated content that was flagged
            - concerns: List of concerns identified
            - risk_level: Risk level (low, medium, high, critical)
            - gates: THSP gate results
            - source: Source of violation (input, output, tool_input, tool_output)
            - timestamp: Unix timestamp
        """
        return self._violations.to_list()

    def get_stats(self) -> dict[str, Any]:
        """Get validation statistics.

        Returns:
            Dictionary containing:
            - total_validations: Total validations performed
            - blocked_count: Number of items blocked
            - allowed_count: Number of items allowed
            - timeout_count: Number of validation timeouts
            - error_count: Number of validation errors
            - gate_failures: Dict of failure counts per gate
            - avg_validation_time_ms: Average validation time
        """
        with self._stats_lock:
            return dict(self._stats)

    def clear_violations(self) -> None:
        """Clear all recorded violations."""
        self._violations.clear()

    def reset_stats(self) -> None:
        """Reset all statistics to zero."""
        with self._stats_lock:
            self._stats = create_empty_stats()


def create_sentinel_plugin(
    seed_level: str = DEFAULT_SEED_LEVEL,
    block_on_failure: bool = True,
    fail_closed: bool = False,
    **kwargs: Any,
) -> SentinelPlugin:
    """Factory function to create a SentinelPlugin.

    This is a convenience function that creates a properly configured
    SentinelPlugin instance.

    Args:
        seed_level: Safety level (minimal, standard, full).
        block_on_failure: Whether to block unsafe content.
        fail_closed: Whether to block on validation errors.
        **kwargs: Additional arguments passed to SentinelPlugin.

    Returns:
        Configured SentinelPlugin instance.

    Example:
        plugin = create_sentinel_plugin(seed_level="full", fail_closed=True)
        runner = Runner(agent=my_agent, plugins=[plugin])
    """
    return SentinelPlugin(
        seed_level=seed_level,
        block_on_failure=block_on_failure,
        fail_closed=fail_closed,
        **kwargs,
    )
