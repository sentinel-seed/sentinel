"""
LangChain chain wrappers and utilities for Sentinel safety.

Provides:
- SentinelChain: Chain wrapper with safety validation
- inject_seed: Add seed to message lists
- wrap_llm: Wrap LLMs with safety features
"""

from typing import Any, Dict, Generator, List, Optional, Union, AsyncGenerator
import threading
import concurrent.futures

from sentinelseed import Sentinel, SeedLevel

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
    get_logger,
    extract_content,
    is_system_message,
    require_langchain,
    validate_text_size,
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
        """
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
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed
        self._streaming_validation_interval = streaming_validation_interval

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
            # Run validation with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.sentinel.validate_request, text)
                try:
                    check = future.result(timeout=self._validation_timeout)
                except concurrent.futures.TimeoutError:
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
            # Run validation with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.sentinel.validate, output)
                try:
                    is_safe, violations = future.result(timeout=self._validation_timeout)
                except concurrent.futures.TimeoutError:
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
        """Async version of invoke."""
        if isinstance(input_data, str):
            input_text = input_data
        else:
            input_text = input_data.get("input", str(input_data))

        block_result = self._validate_input_safe(input_text)
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

        block_result = self._validate_output_safe(output)
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
        Wrapped LLM with Sentinel safety

    Example:
        from langchain_openai import ChatOpenAI
        from sentinelseed.integrations.langchain import wrap_llm

        llm = ChatOpenAI(model="gpt-4o")
        safe_llm = wrap_llm(llm)
        response = safe_llm.invoke("Help me with something")
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)

    # Add callback if requested
    if add_callback:
        callback = SentinelCallback(
            sentinel=sentinel,
            on_violation=on_violation,
            validate_input=validate_input,
            validate_output=validate_output,
        )
        existing_callbacks = getattr(llm, 'callbacks', None) or []
        if hasattr(llm, 'callbacks'):
            llm.callbacks = list(existing_callbacks) + [callback]

    # Create wrapper class that injects seed
    if inject_seed:
        return _SentinelLLMWrapper(llm, sentinel)

    return llm


class _SentinelLLMWrapper:
    """
    Internal wrapper class that injects Sentinel seed into LLM calls.

    Supports invoke, ainvoke, stream, astream, batch, and abatch.
    """

    def __init__(self, llm: Any, sentinel: Sentinel):
        self._llm = llm
        self._sentinel = sentinel
        self._seed = sentinel.get_seed()

        # Copy attributes from wrapped LLM for compatibility
        for attr in ['model_name', 'temperature', 'max_tokens', 'callbacks']:
            if hasattr(llm, attr):
                setattr(self, attr, getattr(llm, attr))

    def _inject_seed(self, messages: Any) -> Any:
        """Inject seed into messages."""
        if not messages:
            return messages

        if isinstance(messages, list):
            return inject_seed(messages, sentinel=self._sentinel)

        return messages

    def invoke(self, messages: Any, **kwargs: Any) -> Any:
        """Invoke LLM with seed injection."""
        messages = self._inject_seed(messages)
        return self._llm.invoke(messages, **kwargs)

    async def ainvoke(self, messages: Any, **kwargs: Any) -> Any:
        """Async invoke LLM with seed injection."""
        messages = self._inject_seed(messages)
        return await self._llm.ainvoke(messages, **kwargs)

    def stream(self, messages: Any, **kwargs: Any) -> Generator:
        """Stream LLM with seed injection."""
        messages = self._inject_seed(messages)
        return self._llm.stream(messages, **kwargs)

    async def astream(self, messages: Any, **kwargs: Any) -> AsyncGenerator:
        """Async stream LLM with seed injection."""
        messages = self._inject_seed(messages)
        return self._llm.astream(messages, **kwargs)

    def batch(self, messages_list: List[Any], **kwargs: Any) -> List[Any]:
        """Batch invoke with seed injection."""
        injected = [self._inject_seed(m) for m in messages_list]
        return self._llm.batch(injected, **kwargs)

    async def abatch(self, messages_list: List[Any], **kwargs: Any) -> List[Any]:
        """Async batch invoke with seed injection."""
        injected = [self._inject_seed(m) for m in messages_list]
        return await self._llm.abatch(injected, **kwargs)

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped LLM."""
        return getattr(self._llm, name)


__all__ = [
    "SentinelChain",
    "inject_seed",
    "wrap_llm",
]
