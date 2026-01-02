"""
LangChain chain wrappers and utilities for Sentinel safety.

Provides:
- SentinelChain: Chain wrapper with safety validation
- inject_seed: Add seed to message lists
- wrap_llm: Wrap LLMs with safety features

Performance Notes:
- Uses shared ValidationExecutor for sync operations
- Uses asyncio.to_thread for async operations (non-blocking)
"""

from typing import Any, Dict, Generator, List, Optional, Union, AsyncGenerator
import copy

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validation import LayeredValidator, ValidationConfig

from .utils import (
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    DEFAULT_STREAMING_VALIDATION_INTERVAL,
    LANGCHAIN_AVAILABLE,
    SystemMessage,
    HumanMessage,
    SentinelLogger,
    TextTooLargeError,
    ValidationTimeoutError,
    ConfigurationError,
    get_logger,
    extract_content,
    is_system_message,
    require_langchain,
    validate_text_size,
    validate_config_types,
    warn_fail_open_default,
    get_validation_executor,
    run_sync_with_timeout_async,
)
from .callbacks import SentinelCallback


class SentinelChain:
    """
    A LangChain-compatible chain wrapper with built-in Sentinel safety.

    Validates inputs before sending to LLM/chain and validates outputs
    before returning to caller. Supports batch, stream, and async operations.

    Example:
        # Option 1: Wrap an LLM directly
        from langchain_openai import ChatOpenAI
        chain = SentinelChain(llm=ChatOpenAI())

        # Option 2: Wrap a full chain
        from langchain_core.prompts import ChatPromptTemplate
        prompt = ChatPromptTemplate.from_messages([...])
        full_chain = prompt | llm
        chain = SentinelChain(chain=full_chain)

        result = chain.invoke("Help me with something")
    """

    def __init__(
        self,
        llm: Optional[Any] = None,
        chain: Optional[Any] = None,
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = DEFAULT_SEED_LEVEL,
        inject_seed: bool = True,
        validate_input: bool = True,
        validate_output: bool = True,
        logger: Optional[SentinelLogger] = None,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        streaming_validation_interval: int = DEFAULT_STREAMING_VALIDATION_INTERVAL,
    ):
        """
        Initialize chain.

        Args:
            llm: LangChain LLM instance (use this OR chain)
            chain: LangChain chain/runnable (use this OR llm)
            sentinel: Sentinel instance
            seed_level: Seed level to use
            inject_seed: Whether to inject seed into system message
            validate_input: Whether to validate inputs
            validate_output: Whether to validate outputs
            logger: Custom logger instance
            max_text_size: Maximum text size in bytes (default 50KB)
            validation_timeout: Timeout for validation in seconds (default 30s)
            fail_closed: If True, block on validation errors
            streaming_validation_interval: Characters between incremental validations

        Raises:
            ValueError: If neither llm nor chain is provided
            ConfigurationError: If configuration parameters have invalid types
        """
        # Validate configuration types before initialization
        validate_config_types(
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
            fail_closed=fail_closed,
            streaming_validation_interval=streaming_validation_interval,
        )

        if llm is None and chain is None:
            raise ValueError("Either 'llm' or 'chain' must be provided")

        self._runnable = chain or llm
        self._is_llm = chain is None
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.seed_level = seed_level
        self.inject_seed = inject_seed
        self.validate_input = validate_input
        self.validate_output = validate_output
        self._logger = logger or get_logger()
        self._seed = self.sentinel.get_seed() if inject_seed else None

        # Create LayeredValidator for validation (Sentinel only used for seeds)
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=False,
            max_text_size=max_text_size,
            validation_timeout=validation_timeout,
        )
        self._validator = LayeredValidator(config=config)
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed
        self._streaming_validation_interval = streaming_validation_interval

        # Log warning about fail-open default behavior
        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelChain")

    def _build_messages(self, input_text: str) -> List[Any]:
        """Build message list with optional seed injection."""
        messages = []

        if self.inject_seed and self._seed:
            if SystemMessage is not None:
                messages.append(SystemMessage(content=self._seed))
            else:
                messages.append({"role": "system", "content": self._seed})

        if HumanMessage is not None:
            messages.append(HumanMessage(content=input_text))
        else:
            messages.append({"role": "user", "content": input_text})

        return messages

    def _extract_output(self, response: Any) -> str:
        """Extract text from various response formats."""
        if hasattr(response, 'content'):
            return response.content
        elif isinstance(response, dict):
            return response.get('output', response.get('content', str(response)))
        elif isinstance(response, str):
            return response
        else:
            return str(response)

    def _validate_input_safe(self, text: str) -> Optional[Dict[str, Any]]:
        """Validate input with exception handling, size limits, and timeout."""
        if not self.validate_input:
            return None

        # Validate text size first
        try:
            validate_text_size(text, self._max_text_size, "input")
        except TextTooLargeError as e:
            return {
                "output": None,
                "blocked": True,
                "blocked_at": "input",
                "reason": [f"Text too large: {e}"]
            }

        try:
            # Use shared executor for validation with timeout
            executor = get_validation_executor()
            try:
                # Use LayeredValidator directly (Sentinel only for seeds)
                result = executor.run_with_timeout(
                    self._validator.validate,
                    args=(text,),
                    timeout=self._validation_timeout,
                )
                check = result.to_legacy_dict()
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": None,
                        "blocked": True,
                        "blocked_at": "input",
                        "reason": [f"Validation timed out after {self._validation_timeout}s"]
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not check["should_proceed"]:
                return {
                    "output": None,
                    "blocked": True,
                    "blocked_at": "input",
                    "reason": check["concerns"]
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating input: {e}")
            if self._fail_closed:
                return {
                    "output": None,
                    "blocked": True,
                    "blocked_at": "input",
                    "reason": [f"Validation error: {e}"]
                }

        return None

    def _validate_output_safe(self, output: str) -> Optional[Dict[str, Any]]:
        """Validate output with exception handling, size limits, and timeout."""
        if not self.validate_output:
            return None

        # Validate text size first
        try:
            validate_text_size(output, self._max_text_size, "output")
        except TextTooLargeError as e:
            return {
                "output": output,
                "blocked": True,
                "blocked_at": "output",
                "violations": [f"Text too large: {e}"]
            }

        try:
            # Use shared executor for validation with timeout
            executor = get_validation_executor()
            try:
                # Use LayeredValidator directly (Sentinel only for seeds)
                result = executor.run_with_timeout(
                    self._validator.validate,
                    args=(output,),
                    timeout=self._validation_timeout,
                )
                is_safe, violations = result.is_safe, result.violations
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": output,
                        "blocked": True,
                        "blocked_at": "output",
                        "violations": [f"Validation timed out after {self._validation_timeout}s"]
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not is_safe:
                return {
                    "output": output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": violations
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating output: {e}")
            if self._fail_closed:
                return {
                    "output": output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": [f"Validation error: {e}"]
                }

        return None

    async def _validate_input_async(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Async version of _validate_input_safe.

        Uses asyncio.to_thread for non-blocking validation.
        """
        if not self.validate_input:
            return None

        # Validate text size first (sync, very fast)
        try:
            validate_text_size(text, self._max_text_size, "input")
        except TextTooLargeError as e:
            return {
                "output": None,
                "blocked": True,
                "blocked_at": "input",
                "reason": [f"Text too large: {e}"]
            }

        try:
            # Use async helper for non-blocking validation
            try:
                # Use LayeredValidator directly (Sentinel only for seeds)
                result = await run_sync_with_timeout_async(
                    self._validator.validate,
                    args=(text,),
                    timeout=self._validation_timeout,
                )
                check = result.to_legacy_dict()
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": None,
                        "blocked": True,
                        "blocked_at": "input",
                        "reason": [f"Validation timed out after {self._validation_timeout}s"]
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not check["should_proceed"]:
                return {
                    "output": None,
                    "blocked": True,
                    "blocked_at": "input",
                    "reason": check["concerns"]
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating input: {e}")
            if self._fail_closed:
                return {
                    "output": None,
                    "blocked": True,
                    "blocked_at": "input",
                    "reason": [f"Validation error: {e}"]
                }

        return None

    async def _validate_output_async(self, output: str) -> Optional[Dict[str, Any]]:
        """
        Async version of _validate_output_safe.

        Uses asyncio.to_thread for non-blocking validation.
        """
        if not self.validate_output:
            return None

        # Validate text size first (sync, very fast)
        try:
            validate_text_size(output, self._max_text_size, "output")
        except TextTooLargeError as e:
            return {
                "output": output,
                "blocked": True,
                "blocked_at": "output",
                "violations": [f"Text too large: {e}"]
            }

        try:
            # Use async helper for non-blocking validation
            try:
                # Use LayeredValidator directly (Sentinel only for seeds)
                result = await run_sync_with_timeout_async(
                    self._validator.validate,
                    args=(output,),
                    timeout=self._validation_timeout,
                )
                is_safe, violations = result.is_safe, result.violations
            except ValidationTimeoutError:
                if self._fail_closed:
                    return {
                        "output": output,
                        "blocked": True,
                        "blocked_at": "output",
                        "violations": [f"Validation timed out after {self._validation_timeout}s"]
                    }
                else:
                    self._logger.warning(
                        "[SENTINEL] Validation timeout, allowing (fail-open)"
                    )
                    return None

            if not is_safe:
                return {
                    "output": output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": violations
                }
        except ValidationTimeoutError:
            raise
        except Exception as e:
            self._logger.error(f"Error validating output: {e}")
            if self._fail_closed:
                return {
                    "output": output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": [f"Validation error: {e}"]
                }

        return None

    def invoke(
        self,
        input_data: Union[str, Dict[str, Any]],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Run chain with safety validation.

        Args:
            input_data: User input (string or dict)
            **kwargs: Additional arguments for LLM/chain

        Returns:
            Dict with output and safety status
        """
        # Extract input text
        if isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = input_data.get("input", str(input_data))

        # Pre-validate
        block_result = self._validate_input_safe(input_text)
        if block_result:
            return block_result

        # Call LLM or chain
        try:
            if self._is_llm:
                messages = self._build_messages(input_text)
                response = self._runnable.invoke(messages, **kwargs)
            else:
                if isinstance(input_data, dict):
                    response = self._runnable.invoke(input_data, **kwargs)
                else:
                    response = self._runnable.invoke({"input": input_text}, **kwargs)
        except Exception as e:
            self._logger.error(f"Chain invoke error: {e}")
            raise

        output = self._extract_output(response)

        # Post-validate
        block_result = self._validate_output_safe(output)
        if block_result:
            return block_result

        return {
            "output": output,
            "blocked": False,
            "violations": None
        }

    async def ainvoke(
        self,
        input_data: Union[str, Dict[str, Any]],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Async version of invoke.

        Uses non-blocking async validation to avoid blocking the event loop.
        """
        if isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = input_data.get("input", str(input_data))

        # Use async validation (non-blocking)
        block_result = await self._validate_input_async(input_text)
        if block_result:
            return block_result

        try:
            if self._is_llm:
                messages = self._build_messages(input_text)
                response = await self._runnable.ainvoke(messages, **kwargs)
            else:
                if isinstance(input_data, dict):
                    response = await self._runnable.ainvoke(input_data, **kwargs)
                else:
                    response = await self._runnable.ainvoke({"input": input_text}, **kwargs)
        except Exception as e:
            self._logger.error(f"Chain ainvoke error: {e}")
            raise

        output = self._extract_output(response)

        # Use async validation (non-blocking)
        block_result = await self._validate_output_async(output)
        if block_result:
            return block_result

        return {
            "output": output,
            "blocked": False,
            "violations": None
        }

    def batch(
        self,
        inputs: List[Union[str, Dict[str, Any]]],
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """
        Batch invoke with safety validation.

        Args:
            inputs: List of inputs
            **kwargs: Additional arguments

        Returns:
            List of response dictionaries
        """
        return [self.invoke(inp, **kwargs) for inp in inputs]

    async def abatch(
        self,
        inputs: List[Union[str, Dict[str, Any]]],
        **kwargs: Any
    ) -> List[Dict[str, Any]]:
        """Async batch invoke."""
        import asyncio
        return await asyncio.gather(*[self.ainvoke(inp, **kwargs) for inp in inputs])

    def stream(
        self,
        input_data: Union[str, Dict[str, Any]],
        **kwargs: Any
    ) -> Generator[Dict[str, Any], None, None]:
        """
        Stream with incremental safety validation.

        Validates input before streaming, validates output incrementally
        during streaming (not just at the end).

        Args:
            input_data: User input
            **kwargs: Additional arguments

        Yields:
            Chunks of output with safety status
        """
        if isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = input_data.get("input", str(input_data))

        # Pre-validate input
        block_result = self._validate_input_safe(input_text)
        if block_result:
            yield block_result
            return

        # Stream from runnable with incremental validation
        accumulated = []
        last_validated_length = 0
        stream_blocked = False
        block_violations = None

        try:
            if self._is_llm:
                messages = self._build_messages(input_text)
                stream = self._runnable.stream(messages, **kwargs)
            else:
                if isinstance(input_data, dict):
                    stream = self._runnable.stream(input_data, **kwargs)
                else:
                    stream = self._runnable.stream({"input": input_text}, **kwargs)

            for chunk in stream:
                chunk_text = self._extract_output(chunk)
                accumulated.append(chunk_text)

                # Incremental validation: validate every N characters
                current_length = sum(len(c) for c in accumulated)
                if (current_length - last_validated_length) >= self._streaming_validation_interval:
                    current_text = "".join(accumulated)
                    block_result = self._validate_output_safe(current_text)
                    if block_result:
                        stream_blocked = True
                        block_violations = block_result.get("violations")
                        # Yield blocked chunk and stop streaming
                        yield {
                            "chunk": chunk_text,
                            "blocked": True,
                            "blocked_at": "output",
                            "violations": block_violations,
                            "final": False,
                        }
                        break
                    last_validated_length = current_length

                if not stream_blocked:
                    yield {
                        "chunk": chunk_text,
                        "blocked": False,
                        "final": False,
                    }

        except Exception as e:
            self._logger.error(f"Stream error: {e}")
            raise

        # Final validation of accumulated output
        full_output = "".join(accumulated)

        if stream_blocked:
            yield {
                "output": full_output,
                "blocked": True,
                "blocked_at": "output",
                "violations": block_violations,
                "final": True,
            }
        else:
            # Final validation (in case stream ended before interval)
            block_result = self._validate_output_safe(full_output)
            if block_result:
                yield {
                    "output": full_output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": block_result.get("violations"),
                    "final": True,
                }
            else:
                yield {
                    "output": full_output,
                    "blocked": False,
                    "final": True,
                }

    async def astream(
        self,
        input_data: Union[str, Dict[str, Any]],
        **kwargs: Any
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Async stream with incremental safety validation."""
        if isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = input_data.get("input", str(input_data))

        block_result = self._validate_input_safe(input_text)
        if block_result:
            yield block_result
            return

        # Stream with incremental validation
        accumulated = []
        last_validated_length = 0
        stream_blocked = False
        block_violations = None

        try:
            if self._is_llm:
                messages = self._build_messages(input_text)
                stream = self._runnable.astream(messages, **kwargs)
            else:
                if isinstance(input_data, dict):
                    stream = self._runnable.astream(input_data, **kwargs)
                else:
                    stream = self._runnable.astream({"input": input_text}, **kwargs)

            async for chunk in stream:
                chunk_text = self._extract_output(chunk)
                accumulated.append(chunk_text)

                # Incremental validation: validate every N characters
                current_length = sum(len(c) for c in accumulated)
                if (current_length - last_validated_length) >= self._streaming_validation_interval:
                    current_text = "".join(accumulated)
                    block_result = self._validate_output_safe(current_text)
                    if block_result:
                        stream_blocked = True
                        block_violations = block_result.get("violations")
                        yield {
                            "chunk": chunk_text,
                            "blocked": True,
                            "blocked_at": "output",
                            "violations": block_violations,
                            "final": False,
                        }
                        break
                    last_validated_length = current_length

                if not stream_blocked:
                    yield {
                        "chunk": chunk_text,
                        "blocked": False,
                        "final": False,
                    }

        except Exception as e:
            self._logger.error(f"Async stream error: {e}")
            raise

        # Final validation
        full_output = "".join(accumulated)

        if stream_blocked:
            yield {
                "output": full_output,
                "blocked": True,
                "blocked_at": "output",
                "violations": block_violations,
                "final": True,
            }
        else:
            block_result = self._validate_output_safe(full_output)
            if block_result:
                yield {
                    "output": full_output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": block_result.get("violations"),
                    "final": True,
                }
            else:
                yield {
                    "output": full_output,
                    "blocked": False,
                    "final": True,
                }


def inject_seed(
    messages: List[Any],
    seed_level: Union[SeedLevel, str] = DEFAULT_SEED_LEVEL,
    sentinel: Optional[Sentinel] = None,
) -> List[Any]:
    """
    Inject Sentinel seed into a message list.

    Adds or modifies the system message to include the Sentinel seed,
    ensuring safety instructions are part of the conversation.

    Args:
        messages: List of messages (dicts or LangChain message objects)
        seed_level: Seed level to use ("minimal", "standard", "full")
        sentinel: Optional Sentinel instance (creates one if not provided)

    Returns:
        New list with seed injected into system message

    Example:
        messages = [
            {"role": "user", "content": "Hello"}
        ]
        safe_messages = inject_seed(messages, seed_level="standard")
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)
    seed = sentinel.get_seed()

    if not messages:
        if SystemMessage is not None:
            return [SystemMessage(content=seed)]
        return [{"role": "system", "content": seed}]

    # Copy messages to avoid mutating original
    result = list(messages)

    # Check for existing system message
    has_system = False
    for i, msg in enumerate(result):
        if is_system_message(msg):
            # Prepend seed to existing system message
            current_content = extract_content(msg)
            new_content = f"{seed}\n\n---\n\n{current_content}"

            if isinstance(msg, dict):
                result[i] = {**msg, 'content': new_content}
            elif SystemMessage is not None:
                result[i] = SystemMessage(content=new_content)

            has_system = True
            break

    # Add system message if none exists
    if not has_system:
        if SystemMessage is not None:
            result.insert(0, SystemMessage(content=seed))
        else:
            result.insert(0, {"role": "system", "content": seed})

    return result


def wrap_llm(
    llm: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: Union[SeedLevel, str] = DEFAULT_SEED_LEVEL,
    inject_seed: bool = True,
    add_callback: bool = True,
    validate_input: bool = True,
    validate_output: bool = True,
    on_violation: str = "log",
) -> Any:
    """
    Wrap a LangChain LLM with Sentinel safety.

    This function wraps an existing LLM instance to:
    1. Inject the Sentinel seed into system prompts
    2. Add a SentinelCallback for monitoring

    IMPORTANT: This function does NOT modify the original LLM. It creates
    a wrapper that delegates to the original. The original LLM can still
    be used independently without Sentinel safety features.

    Args:
        llm: LangChain LLM instance to wrap
        sentinel: Sentinel instance (creates default if None)
        seed_level: Which seed level to use
        inject_seed: Whether to inject seed via system prompt
        add_callback: Whether to add monitoring callback
        validate_input: Whether to validate inputs
        validate_output: Whether to validate outputs
        on_violation: Action on violation

    Returns:
        Wrapped LLM with Sentinel safety (original LLM is not modified)

    Example:
        from langchain_openai import ChatOpenAI
        from sentinelseed.integrations.langchain import wrap_llm

        llm = ChatOpenAI(model="gpt-4o")
        safe_llm = wrap_llm(llm)
        response = safe_llm.invoke("Help me with something")

        # Original LLM is unchanged
        unsafe_response = llm.invoke("Same message, no safety")
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)

    # Create callback if requested
    callback = None
    if add_callback:
        callback = SentinelCallback(
            sentinel=sentinel,
            on_violation=on_violation,
            validate_input=validate_input,
            validate_output=validate_output,
        )

    # Create wrapper class that injects seed (does not modify original)
    if inject_seed:
        return _SentinelLLMWrapper(llm, sentinel, callback=callback)

    # If not injecting seed but adding callback, create a minimal wrapper
    if add_callback and callback:
        return _SentinelLLMWrapper(llm, sentinel, callback=callback, inject_seed=False)

    return llm


class _SentinelLLMWrapper:
    """
    Internal wrapper class that injects Sentinel seed into LLM calls.

    Supports invoke, ainvoke, stream, astream, batch, and abatch.

    IMPORTANT: This wrapper does NOT modify the original LLM. Callbacks are
    passed per-call via kwargs, not set on the original LLM instance.
    """

    def __init__(
        self,
        llm: Any,
        sentinel: Sentinel,
        callback: Optional[SentinelCallback] = None,
        inject_seed: bool = True,
    ):
        self._llm = llm
        self._sentinel = sentinel
        self._seed = sentinel.get_seed() if inject_seed else None
        self._callback = callback
        self._inject_seed_enabled = inject_seed

        # Copy common attributes from wrapped LLM for compatibility
        for attr in ['model_name', 'temperature', 'max_tokens']:
            if hasattr(llm, attr):
                setattr(self, attr, getattr(llm, attr))

    def _inject_seed(self, messages: Any) -> Any:
        """Inject seed into messages if enabled."""
        if not self._inject_seed_enabled or not messages:
            return messages

        if isinstance(messages, list):
            return inject_seed(messages, sentinel=self._sentinel)

        return messages

    def _get_callbacks(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get kwargs with callback added if configured.

        Does NOT modify the original LLM - callbacks are passed per-call.
        """
        if not self._callback:
            return kwargs

        # Get existing callbacks from kwargs, don't modify original
        existing = kwargs.get('callbacks', []) or []
        if not isinstance(existing, list):
            existing = [existing]

        # Create new kwargs with our callback added
        new_kwargs = dict(kwargs)
        new_kwargs['callbacks'] = list(existing) + [self._callback]
        return new_kwargs

    def invoke(self, messages: Any, **kwargs: Any) -> Any:
        """Invoke LLM with seed injection and optional callback."""
        messages = self._inject_seed(messages)
        kwargs = self._get_callbacks(kwargs)
        return self._llm.invoke(messages, **kwargs)

    async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
        """Async invoke LLM with seed injection and optional callback."""
        messages = self._inject_seed(messages)
        kwargs = self._get_callbacks(kwargs)
        return await self._llm.ainvoke(messages, **kwargs)

    def stream(self, messages: Any, **kwargs: Any) -> Generator:
        """Stream LLM with seed injection and optional callback."""
        messages = self._inject_seed(messages)
        kwargs = self._get_callbacks(kwargs)
        return self._llm.stream(messages, **kwargs)

    async def astream(self, messages: Any, **kwargs: Any) -> AsyncGenerator:
        """Async stream LLM with seed injection and optional callback."""
        messages = self._inject_seed(messages)
        kwargs = self._get_callbacks(kwargs)
        return self._llm.astream(messages, **kwargs)

    def batch(self, messages_list: List[Any], **kwargs: Any) -> List[Any]:
        """Batch invoke with seed injection and optional callback."""
        injected = [self._inject_seed(m) for m in messages_list]
        kwargs = self._get_callbacks(kwargs)
        return self._llm.batch(injected, **kwargs)

    async def abatch(self, messages_list: List[Any], **kwargs: Any) -> List[Any]:
        """Async batch invoke with seed injection and optional callback."""
        injected = [self._inject_seed(m) for m in messages_list]
        kwargs = self._get_callbacks(kwargs)
        return await self._llm.abatch(injected, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped LLM."""
        return getattr(self._llm, name)

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        llm_repr = repr(self._llm)
        seed_level = self._sentinel.seed_level.value if self._sentinel else "none"
        return f"_SentinelLLMWrapper(llm={llm_repr}, seed_level={seed_level}, inject_seed={self._inject_seed_enabled})"

    def __str__(self) -> str:
        """Return human-readable string representation."""
        llm_str = str(self._llm)
        return f"SentinelWrapped({llm_str})"


__all__ = [
    "SentinelChain",
    "inject_seed",
    "wrap_llm",
]
