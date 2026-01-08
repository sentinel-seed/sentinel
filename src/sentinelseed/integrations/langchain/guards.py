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
from sentinelseed.validation import (
    LayeredValidator,
    AsyncLayeredValidator,
    ValidationConfig,
)
from sentinelseed.integrations._base import SentinelIntegration

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


class SentinelGuard(SentinelIntegration):
    """
    Wrapper for LangChain agents/chains with Sentinel safety.

    Intercepts inputs and outputs, validating them before proceeding.
    Thread-safe and supports both sync and async operations.

    Inherits from SentinelIntegration for consistent validation behavior.

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

    _integration_name = "langchain_guard"

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
        validator: Optional[LayeredValidator] = None,
        use_semantic: bool = False,
        semantic_api_key: Optional[str] = None,
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
            validator: Optional LayeredValidator instance (created if None)
            use_semantic: Whether to enable semantic validation
            semantic_api_key: API key for semantic validation

        Raises:
            ConfigurationError: If configuration parameters have invalid types
        """
        # Validate configuration types before initialization
        validate_config_types(
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            fail_closed=fail_closed,
        )

        # Create LayeredValidator with config if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=True,
                use_semantic=use_semantic and bool(semantic_api_key),
                semantic_api_key=semantic_api_key,
                max_text_size=max_text_size,
                validation_timeout=validation_timeout,
            )
            validator = LayeredValidator(config=config)

        # Initialize SentinelIntegration with the validator
        super().__init__(validator=validator)

        self.agent = agent
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self._seed_level = seed_level  # Use _seed_level (inherited property is read-only)
        self.block_unsafe = block_unsafe
        self.validate_input_enabled = validate_input
        self.validate_output_enabled = validate_output
        self.inject_seed = inject_seed
        self._logger = logger or get_logger()
        self._seed = self.sentinel.get_seed() if inject_seed else None
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed

        # Log warning about fail-open default behavior
        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelGuard")

    # ========================================================================
    # Backwards Compatibility Properties
    # ========================================================================

    @property
    def validate_input(self) -> bool:
        """Backwards compatibility property for validate_input."""
        return self.validate_input_enabled

    @validate_input.setter
    def validate_input(self, value: bool) -> None:
        """Backwards compatibility setter for validate_input."""
        self.validate_input_enabled = value

    @property
    def validate_output(self) -> bool:
        """Backwards compatibility property for validate_output."""
        return self.validate_output_enabled

    @validate_output.setter
    def validate_output(self, value: bool) -> None:
        """Backwards compatibility setter for validate_output."""
        self.validate_output_enabled = value

    # ========================================================================
    # Validation Methods
    # ========================================================================

    def _validate_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Validate input with size limits using inherited validate() method.

        Args:
            text: Input text to validate

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_input_enabled:
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
            # Use inherited validate() method from SentinelIntegration
            result = self.validate(text)

            if not result.is_safe and self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: {result.violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": result.violations,
                    "sentinel_layer": result.layer.value,
                }
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            self._logger.error(f"Error validating input: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Request blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": ["Validation error occurred"],
                }

        return None

    def _validate_output(self, text: str, original: str = "") -> Optional[Dict[str, Any]]:
        """
        Validate output with size limits using inherited validate() method.

        Args:
            text: Output text to validate
            original: Original output for reference

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_output_enabled:
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
            # Use inherited validate() method from SentinelIntegration
            result = self.validate(text)

            if not result.is_safe and self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: {result.violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": result.violations,
                    "sentinel_layer": result.layer.value,
                    "original_output": original[:200] if original else None,
                }
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            self._logger.error(f"Error validating output: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Response blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": ["Validation error occurred"],
                }

        return None

    async def _validate_input_async(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Async version of _validate_input using inherited validate() method.

        Args:
            text: Input text to validate

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_input_enabled:
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
            # Use inherited validate() method wrapped in thread for async
            result = await run_sync_with_timeout_async(
                self.validate,
                args=(text,),
                timeout=self._validation_timeout,
            )

            if not result.is_safe and self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: {result.violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": result.violations,
                    "sentinel_layer": result.layer.value,
                }
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            self._logger.error(f"Error validating input: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Request blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": ["Validation error occurred"],
                }

        return None

    async def _validate_output_async(self, text: str, original: str = "") -> Optional[Dict[str, Any]]:
        """
        Async version of _validate_output using inherited validate() method.

        Args:
            text: Output text to validate
            original: Original output for reference

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_output_enabled:
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
            # Use inherited validate() method wrapped in thread for async
            result = await run_sync_with_timeout_async(
                self.validate,
                args=(text,),
                timeout=self._validation_timeout,
            )

            if not result.is_safe and self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: {result.violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": result.violations,
                    "sentinel_layer": result.layer.value,
                    "original_output": original[:200] if original else None,
                }
        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            self._logger.error(f"Error validating output: {e}")
            if self.block_unsafe and self._fail_closed:
                return {
                    "output": "Response blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": ["Validation error occurred"],
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
        # Pre-validate input using inherited validate() method
        if self.validate_input_enabled:
            try:
                result = self.validate(input_text)
                if not result.is_safe and self.block_unsafe:
                    return f"Request blocked by Sentinel: {result.violations}"
            except (ValueError, TypeError, RuntimeError, AttributeError) as e:
                self._logger.error(f"Error validating input: {e}")
                if self.block_unsafe:
                    return "Request blocked: validation error"

        # Run agent
        try:
            result = self.agent.run(input_text, **kwargs)
        except (ValueError, TypeError, RuntimeError, AttributeError, KeyError) as e:
            self._logger.error(f"Agent run error: {e}")
            raise

        # Post-validate output using inherited validate() method
        if self.validate_output_enabled:
            try:
                validation_result = self.validate(result)
                if not validation_result.is_safe and self.block_unsafe:
                    return f"Response blocked by Sentinel: {validation_result.violations}"
            except (ValueError, TypeError, RuntimeError, AttributeError) as e:
                self._logger.error(f"Error validating output: {e}")
                if self.block_unsafe:
                    return "Response blocked: validation error"

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
