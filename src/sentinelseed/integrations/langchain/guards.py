"""
LangChain guard wrappers for Sentinel safety validation.

Provides:
- SentinelGuard: Wrap agents/chains with safety validation

Performance Notes:
- Uses shared ValidationExecutor for sync operations
- Uses asyncio.to_thread for async operations (non-blocking)
"""

from typing import Any, Dict, List, Optional, Union

from sentinelseed import Sentinel, SeedLevel

from .utils import (
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    SentinelLogger,
    TextTooLargeError,
    ValidationTimeoutError,
    ConfigurationError,
    get_logger,
    validate_text_size,
    validate_config_types,
    warn_fail_open_default,
    get_validation_executor,
    run_sync_with_timeout_async,
)


class SentinelGuard:
    """
    Wrapper for LangChain agents/chains with Sentinel safety.

    Intercepts inputs and outputs, validating them before proceeding.
    Thread-safe and supports both sync and async operations.

    Example:
        from langchain.agents import AgentExecutor
        from sentinelseed.integrations.langchain import SentinelGuard

        agent = AgentExecutor(...)
        safe_agent = SentinelGuard(
            agent,
            block_unsafe=True,
            validate_input=True,
            validate_output=True,
            inject_seed=True,
        )
        result = safe_agent.invoke({"input": "Do something"})
    """

    def __init__(
        self,
        agent: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = DEFAULT_SEED_LEVEL,
        block_unsafe: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        inject_seed: bool = False,
        logger: Optional[SentinelLogger] = None,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        """
        Initialize guard.

        Args:
            agent: LangChain agent/chain to wrap
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level for validation
            block_unsafe: Whether to block unsafe actions
            validate_input: Whether to validate inputs
            validate_output: Whether to validate outputs
            inject_seed: Whether to inject seed into system prompts
            logger: Custom logger instance
            max_text_size: Maximum text size in bytes (default 50KB)
            validation_timeout: Timeout for validation in seconds (default 30s)
            fail_closed: If True, block on validation errors

        Raises:
            ConfigurationError: If configuration parameters have invalid types
        """
        # Validate configuration types before initialization
        validate_config_types(
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            fail_closed=fail_closed,
        )

        self.agent = agent
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.seed_level = seed_level
        self.block_unsafe = block_unsafe
        self.validate_input = validate_input
        self.validate_output = validate_output
        self.inject_seed = inject_seed
        self._logger = logger or get_logger()
        self._seed = self.sentinel.get_seed() if inject_seed else None
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed

        # Log warning about fail-open default behavior
        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelGuard")

    def _validate_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Validate input with size limits and timeout.

        Args:
            text: Input text to validate

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_input:
            return None

        # Validate text size first
        try:
            validate_text_size(text, self._max_text_size, "input")
        except TextTooLargeError as e:
            if self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: Text too large ({e.size:,} bytes)",
                    "sentinel_blocked": True,
                    "sentinel_reason": [f"Text too large: {e}"],
                }
            return None

        try:
            # Use shared executor for validation with timeout
            executor = get_validation_executor()
            try:
                check = executor.run_with_timeout(
                    self.sentinel.validate_request,
                    args=(text,),
                    timeout=self._validation_timeout,
                )
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": f"Request blocked by Sentinel: Validation timeout",
                        "sentinel_blocked": True,
                        "sentinel_reason": [f"Validation timed out after {self._validation_timeout}s"],
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not check["should_proceed"] and self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: {check['concerns']}",
                    "sentinel_blocked": True,
                    "sentinel_reason": check["concerns"],
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating input: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Request blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": [str(e)],
                }

        return None

    def _validate_output(self, text: str, original: str = "") -> Optional[Dict[str, Any]]:
        """
        Validate output with size limits and timeout.

        Args:
            text: Output text to validate
            original: Original output for reference

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_output:
            return None

        # Validate text size first
        try:
            validate_text_size(text, self._max_text_size, "output")
        except TextTooLargeError as e:
            if self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: Text too large ({e.size:,} bytes)",
                    "sentinel_blocked": True,
                    "sentinel_reason": [f"Text too large: {e}"],
                    "original_output": original[:200] if original else None,
                }
            return None

        try:
            # Use shared executor for validation with timeout
            executor = get_validation_executor()
            try:
                is_safe, violations = executor.run_with_timeout(
                    self.sentinel.validate,
                    args=(text,),
                    timeout=self._validation_timeout,
                )
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": f"Response blocked by Sentinel: Validation timeout",
                        "sentinel_blocked": True,
                        "sentinel_reason": [f"Validation timed out after {self._validation_timeout}s"],
                        "original_output": original[:200] if original else None,
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not is_safe and self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: {violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": violations,
                    "original_output": original[:200] if original else None,
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating output: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Response blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": [str(e)],
                }

        return None

    async def _validate_input_async(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Async version of _validate_input.

        Uses asyncio.to_thread for non-blocking validation without
        blocking the event loop.

        Args:
            text: Input text to validate

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_input:
            return None

        # Validate text size first (sync, very fast)
        try:
            validate_text_size(text, self._max_text_size, "input")
        except TextTooLargeError as e:
            if self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: Text too large ({e.size:,} bytes)",
                    "sentinel_blocked": True,
                    "sentinel_reason": [f"Text too large: {e}"],
                }
            return None

        try:
            # Use async helper for non-blocking validation
            try:
                check = await run_sync_with_timeout_async(
                    self.sentinel.validate_request,
                    args=(text,),
                    timeout=self._validation_timeout,
                )
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": f"Request blocked by Sentinel: Validation timeout",
                        "sentinel_blocked": True,
                        "sentinel_reason": [f"Validation timed out after {self._validation_timeout}s"],
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not check["should_proceed"] and self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: {check['concerns']}",
                    "sentinel_blocked": True,
                    "sentinel_reason": check["concerns"],
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating input: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Request blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": [str(e)],
                }

        return None

    async def _validate_output_async(self, text: str, original: str = "") -> Optional[Dict[str, Any]]:
        """
        Async version of _validate_output.

        Uses asyncio.to_thread for non-blocking validation without
        blocking the event loop.

        Args:
            text: Output text to validate
            original: Original output for reference

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_output:
            return None

        # Validate text size first (sync, very fast)
        try:
            validate_text_size(text, self._max_text_size, "output")
        except TextTooLargeError as e:
            if self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: Text too large ({e.size:,} bytes)",
                    "sentinel_blocked": True,
                    "sentinel_reason": [f"Text too large: {e}"],
                    "original_output": original[:200] if original else None,
                }
            return None

        try:
            # Use async helper for non-blocking validation
            try:
                is_safe, violations = await run_sync_with_timeout_async(
                    self.sentinel.validate,
                    args=(text,),
                    timeout=self._validation_timeout,
                )
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": f"Response blocked by Sentinel: Validation timeout",
                        "sentinel_blocked": True,
                        "sentinel_reason": [f"Validation timed out after {self._validation_timeout}s"],
                        "original_output": original[:200] if original else None,
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not is_safe and self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: {violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": violations,
                    "original_output": original[:200] if original else None,
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating output: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Response blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": [str(e)],
                }

        return None

    def run(self, input_text: str, **kwargs: Any) -> str:
        """
        Run agent with safety validation (legacy interface).

        Args:
            input_text: User input
            **kwargs: Additional arguments for agent

        Returns:
            Agent response (or safe fallback if blocked)
        """
        # Pre-validate input
        if self.validate_input:
            try:
                input_check = self.sentinel.validate_request(input_text)
                if not input_check["should_proceed"] and self.block_unsafe:
                    return f"Request blocked by Sentinel: {input_check['concerns']}"
            except Exception as e:
                self._logger.error(f"Error validating input: {e}")
                if self.block_unsafe:
                    return f"Request blocked: validation error"

        # Run agent
        try:
            result = self.agent.run(input_text, **kwargs)
        except Exception as e:
            self._logger.error(f"Agent run error: {e}")
            raise

        # Post-validate output
        if self.validate_output:
            try:
                is_safe, violations = self.sentinel.validate(result)
                if not is_safe and self.block_unsafe:
                    return f"Response blocked by Sentinel: {violations}"
            except Exception as e:
                self._logger.error(f"Error validating output: {e}")
                if self.block_unsafe:
                    return f"Response blocked: validation error"

        return result

    def invoke(
        self,
        input_dict: Union[Dict[str, Any], str],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Invoke agent with safety validation (new interface).

        Args:
            input_dict: Input dictionary or string
            **kwargs: Additional arguments

        Returns:
            Agent response dictionary
        """
        # Handle string input
        if isinstance(input_dict, str):
            input_dict = {"input": input_dict}

        # Extract input text
        input_text = input_dict.get("input", str(input_dict))

        # Pre-validate
        block_response = self._validate_input(input_text)
        if block_response:
            return block_response

        # Run agent
        try:
            result = self.agent.invoke(input_dict, **kwargs)
        except Exception as e:
            self._logger.error(f"Agent invoke error: {e}")
            raise

        # Extract output and validate
        if isinstance(result, dict):
            output_text = result.get("output", str(result))
        else:
            output_text = str(result)

        block_response = self._validate_output(output_text, output_text)
        if block_response:
            return block_response

        if isinstance(result, dict):
            result["sentinel_blocked"] = False
        else:
            result = {"output": result, "sentinel_blocked": False}

        return result

    async def ainvoke(
        self,
        input_dict: Union[Dict[str, Any], str],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Async version of invoke.

        Uses non-blocking async validation to avoid blocking the event loop.
        """
        if isinstance(input_dict, str):
            input_dict = {"input": input_dict}

        input_text = input_dict.get("input", str(input_dict))

        # Use async validation (non-blocking)
        block_response = await self._validate_input_async(input_text)
        if block_response:
            return block_response

        try:
            result = await self.agent.ainvoke(input_dict, **kwargs)
        except Exception as e:
            self._logger.error(f"Agent ainvoke error: {e}")
            raise

        if isinstance(result, dict):
            output_text = result.get("output", str(result))
        else:
            output_text = str(result)

        # Use async validation (non-blocking)
        block_response = await self._validate_output_async(output_text, output_text)
        if block_response:
            return block_response

        if isinstance(result, dict):
            result["sentinel_blocked"] = False
        else:
            result = {"output": result, "sentinel_blocked": False}

        return result

    def batch(
        self,
        inputs: List[Union[Dict[str, Any], str]],
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Batch invoke with safety validation.

        Args:
            inputs: List of input dicts or strings
            **kwargs: Additional arguments

        Returns:
            List of response dictionaries
        """
        return [self.invoke(inp, **kwargs) for inp in inputs]

    async def abatch(
        self,
        inputs: List[Union[Dict[str, Any], str]],
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Async batch invoke."""
        import asyncio
        return await asyncio.gather(*[self.ainvoke(inp, **kwargs) for inp in inputs])


__all__ = ["SentinelGuard"]
