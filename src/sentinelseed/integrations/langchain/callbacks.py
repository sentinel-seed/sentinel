"""
LangChain callback handlers for Sentinel safety monitoring.

Provides:
- SentinelCallback: Callback handler to monitor LLM calls
- StreamingBuffer: Buffer for accumulating streaming tokens
"""

from typing import Any, Dict, List, Optional, Union
import threading
import concurrent.futures

from sentinelseed import Sentinel, SeedLevel

from .utils import (
    DEFAULT_MAX_VIOLATIONS,
    DEFAULT_SEED_LEVEL,
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    LANGCHAIN_AVAILABLE,
    BaseCallbackHandler,
    SentinelLogger,
    ThreadSafeDeque,
    ValidationResult,
    ViolationRecord,
    TextTooLargeError,
    ValidationTimeoutError,
    get_logger,
    sanitize_text,
    extract_content,
    require_langchain,
    validate_text_size,
)


class SentinelViolationError(Exception):
    """Raised when a Sentinel violation is detected."""
    pass


class StreamingBuffer:
    """
    Thread-safe buffer for accumulating streaming tokens.

    Accumulates tokens until a complete phrase/sentence is available
    for validation, avoiding false positives from partial tokens.
    """

    # Characters that indicate phrase boundaries
    PHRASE_DELIMITERS = {'.', '!', '?', '\n', ';', ':'}
    # Minimum buffer size before checking for validation
    MIN_VALIDATION_SIZE = 20

    def __init__(self):
        self._buffer: str = ""
        self._lock = threading.Lock()

    def add_token(self, token: str) -> Optional[str]:
        """
        Add token to buffer, return content if ready for validation.

        Args:
            token: New token from streaming

        Returns:
            Content to validate if buffer is ready, None otherwise
        """
        with self._lock:
            self._buffer += token

            # Check if we have a complete phrase
            if len(self._buffer) >= self.MIN_VALIDATION_SIZE:
                # Look for phrase delimiter
                for i, char in enumerate(self._buffer):
                    if char in self.PHRASE_DELIMITERS and i >= self.MIN_VALIDATION_SIZE - 1:
                        # Extract content up to and including delimiter
                        content = self._buffer[:i + 1]
                        self._buffer = self._buffer[i + 1:]
                        return content.strip()

            return None

    def flush(self) -> Optional[str]:
        """
        Flush and return remaining buffer content.

        Returns:
            Remaining content or None if empty
        """
        with self._lock:
            if self._buffer.strip():
                content = self._buffer.strip()
                self._buffer = ""
                return content
            return None

    def clear(self) -> None:
        """Clear the buffer."""
        with self._lock:
            self._buffer = ""


class SentinelCallback(BaseCallbackHandler):
    """
    LangChain callback handler for Sentinel safety monitoring.

    Monitors LLM inputs and outputs for safety violations using
    the THSP protocol. Thread-safe and supports streaming.

    Example:
        from langchain_openai import ChatOpenAI
        from sentinelseed.integrations.langchain import SentinelCallback

        callback = SentinelCallback(
            seed_level="standard",
            on_violation="log",
            validate_input=True,
            validate_output=True,
        )
        llm = ChatOpenAI(callbacks=[callback])
        response = llm.invoke("Hello")

        print(callback.get_violations())
        print(callback.get_stats())
    """

    # BaseCallbackHandler properties
    raise_error: bool = False
    run_inline: bool = True

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = DEFAULT_SEED_LEVEL,
        on_violation: str = "log",
        validate_input: bool = True,
        validate_output: bool = True,
        log_safe: bool = False,
        max_violations: int = DEFAULT_MAX_VIOLATIONS,
        sanitize_logs: bool = False,
        logger: Optional[SentinelLogger] = None,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        """
        Initialize callback handler.

        Args:
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level for validation ("minimal", "standard", "full")
            on_violation: Action on violation:
                - "log": Log warning and continue (DOES NOT BLOCK execution)
                - "raise": Raise SentinelViolationError
                - "block": Log as blocked (for monitoring, DOES NOT BLOCK)
                - "flag": Mark violation without logging

            NOTE: Callbacks MONITOR but do NOT BLOCK execution. For blocking,
            use SentinelGuard or SentinelChain instead.

            validate_input: Whether to validate input messages/prompts
            validate_output: Whether to validate LLM responses
            log_safe: Whether to log safe responses too
            max_violations: Maximum violations to keep in log
            sanitize_logs: Whether to mask sensitive data in logs
            logger: Custom logger instance
            max_text_size: Maximum text size in bytes (default 50KB)
            validation_timeout: Timeout for validation in seconds (default 30s)
            fail_closed: If True, block on validation errors; if False, allow
        """
        if LANGCHAIN_AVAILABLE and BaseCallbackHandler is not object:
            super().__init__()

        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.seed_level = seed_level
        self.on_violation = on_violation
        self.validate_input = validate_input
        self.validate_output = validate_output
        self.log_safe = log_safe
        self.max_violations = max_violations
        self.sanitize_logs = sanitize_logs
        self._logger = logger or get_logger()
        self._max_text_size = max_text_size
        self._validation_timeout = validation_timeout
        self._fail_closed = fail_closed

        # Thread-safe storage
        self._violations_log = ThreadSafeDeque(maxlen=max_violations)
        self._validation_log = ThreadSafeDeque(maxlen=max_violations)

        # Streaming buffer for robust token validation
        self._streaming_buffer = StreamingBuffer()
        self._streaming_lock = threading.Lock()

    # ========================================================================
    # LLM Callbacks
    # ========================================================================

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts. Validates input prompts."""
        if not self.validate_input:
            return

        for prompt in prompts:
            self._validate_input_safe(prompt, stage="llm_input")

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        **kwargs: Any
    ) -> None:
        """Called when chat model starts. Validates input messages."""
        if not self.validate_input:
            return

        for message_list in messages:
            for message in message_list:
                content = extract_content(message)
                if content:
                    self._validate_input_safe(content, stage="chat_input")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes. Validates output."""
        if not self.validate_output:
            return

        # Flush streaming buffer first
        remaining = self._streaming_buffer.flush()
        if remaining:
            self._validate_output_safe(remaining, stage="streaming_final")

        # Validate full response
        if hasattr(response, 'generations'):
            for gen_list in response.generations:
                for gen in gen_list:
                    text = gen.text if hasattr(gen, 'text') else str(gen)
                    self._validate_output_safe(text, stage="llm_output")
        elif hasattr(response, 'content'):
            self._validate_output_safe(response.content, stage="llm_output")
        elif isinstance(response, dict) and 'content' in response:
            self._validate_output_safe(response['content'], stage="llm_output")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """
        Called on new token during streaming.

        Uses buffering to accumulate tokens into complete phrases
        before validation, avoiding false positives from partial tokens.
        """
        if not self.validate_output:
            return

        with self._streaming_lock:
            content = self._streaming_buffer.add_token(token)
            if content:
                self._validate_output_safe(content, stage="streaming_phrase")

    def on_llm_error(
        self,
        error: BaseException,
        **kwargs: Any
    ) -> None:
        """Called on LLM error."""
        self._logger.debug(f"LLM error occurred: {type(error).__name__}")
        # Clear streaming buffer on error
        self._streaming_buffer.clear()

    # ========================================================================
    # Chain Callbacks
    # ========================================================================

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain starts. Validates chain inputs."""
        if not self.validate_input:
            return

        for key, value in inputs.items():
            if isinstance(value, str) and value:
                self._validate_input_safe(value, stage="chain_input")

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain ends. Validates chain outputs."""
        if not self.validate_output:
            return

        for key, value in outputs.items():
            if isinstance(value, str) and value:
                self._validate_output_safe(value, stage="chain_output")

    # ========================================================================
    # Tool Callbacks
    # ========================================================================

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Called when tool starts. Validates tool input."""
        if not self.validate_input:
            return

        if input_str:
            self._validate_input_safe(input_str, stage="tool_input")

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Called when tool ends. Validates tool output."""
        if not self.validate_output:
            return

        if output:
            self._validate_output_safe(output, stage="tool_output")

    # ========================================================================
    # Agent Callbacks
    # ========================================================================

    def on_agent_action(
        self,
        action: Any,
        **kwargs: Any
    ) -> None:
        """Called on agent action. Validates action."""
        if not self.validate_input:
            return

        action_str = str(action)
        try:
            is_safe, violations = self.sentinel.validate_action(action_str)
            if not is_safe:
                self._handle_violation(
                    stage="agent_action",
                    text=action_str,
                    concerns=violations,
                    risk_level="high"
                )
        except Exception as e:
            self._logger.error(f"Error validating agent action: {e}")

    # ========================================================================
    # Validation Logic (with exception handling)
    # ========================================================================

    def _validate_input_safe(self, text: str, stage: str) -> None:
        """Validate input with exception handling, size limits, and timeout."""
        if not text:
            return

        # Validate text size first
        try:
            validate_text_size(text, self._max_text_size, stage)
        except TextTooLargeError as e:
            self._handle_violation(
                stage=stage,
                text=text[:200] + "...",
                concerns=[f"Text too large: {e}"],
                risk_level="high"
            )
            return

        try:
            # Run validation with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.sentinel.validate_request, text)
                try:
                    result = future.result(timeout=self._validation_timeout)
                except concurrent.futures.TimeoutError:
                    if self._fail_closed:
                        self._handle_violation(
                            stage=stage,
                            text=text,
                            concerns=[f"Validation timed out after {self._validation_timeout}s"],
                            risk_level="high"
                        )
                    else:
                        self._logger.warning(
                            f"[SENTINEL] Validation timeout at {stage}, allowing (fail-open)"
                        )
                    return

            # Log validation
            self._validation_log.append(ValidationResult(
                safe=result["should_proceed"],
                stage=stage,
                type="input",
                risk_level=result.get("risk_level", "unknown"),
            ).to_dict())

            if not result["should_proceed"]:
                self._handle_violation(
                    stage=stage,
                    text=text,
                    concerns=result["concerns"],
                    risk_level=result["risk_level"]
                )
            elif self.log_safe:
                self._logger.info(f"[SENTINEL] Input validated: SAFE ({stage})")

        except SentinelViolationError:
            # Re-raise violation errors (for on_violation="raise")
            raise
        except Exception as e:
            self._logger.error(f"Error validating input at {stage}: {e}")
            if self._fail_closed:
                self._handle_violation(
                    stage=stage,
                    text=text,
                    concerns=[f"Validation error: {e}"],
                    risk_level="high"
                )

    def _validate_output_safe(self, text: str, stage: str) -> None:
        """Validate output with exception handling, size limits, and timeout."""
        if not text:
            return

        # Validate text size first
        try:
            validate_text_size(text, self._max_text_size, stage)
        except TextTooLargeError as e:
            self._handle_violation(
                stage=stage,
                text=text[:200] + "...",
                concerns=[f"Text too large: {e}"],
                risk_level="high"
            )
            return

        try:
            # Run validation with timeout
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(self.sentinel.validate, text)
                try:
                    is_safe, violations = future.result(timeout=self._validation_timeout)
                except concurrent.futures.TimeoutError:
                    if self._fail_closed:
                        self._handle_violation(
                            stage=stage,
                            text=text,
                            concerns=[f"Validation timed out after {self._validation_timeout}s"],
                            risk_level="high"
                        )
                    else:
                        self._logger.warning(
                            f"[SENTINEL] Validation timeout at {stage}, allowing (fail-open)"
                        )
                    return

            # Log validation
            self._validation_log.append(ValidationResult(
                safe=is_safe,
                stage=stage,
                type="output",
                risk_level="high" if not is_safe else "low",
            ).to_dict())

            if not is_safe:
                self._handle_violation(
                    stage=stage,
                    text=text,
                    concerns=violations,
                    risk_level="high"
                )
            elif self.log_safe:
                self._logger.info(f"[SENTINEL] Output validated: SAFE ({stage})")

        except SentinelViolationError:
            # Re-raise violation errors (for on_violation="raise")
            raise
        except Exception as e:
            self._logger.error(f"Error validating output at {stage}: {e}")
            if self._fail_closed:
                self._handle_violation(
                    stage=stage,
                    text=text,
                    concerns=[f"Validation error: {e}"],
                    risk_level="high"
                )

    def _handle_violation(
        self,
        stage: str,
        text: str,
        concerns: List[str],
        risk_level: str
    ) -> None:
        """Handle a detected violation."""
        sanitized_text = sanitize_text(text, sanitize=self.sanitize_logs)

        violation = ViolationRecord(
            stage=stage,
            text=sanitized_text,
            concerns=concerns,
            risk_level=risk_level,
        )
        self._violations_log.append(violation.to_dict())

        if self.on_violation == "log":
            self._logger.warning(f"[SENTINEL VIOLATION] {stage}: {concerns}")
        elif self.on_violation == "raise":
            raise SentinelViolationError(
                f"Sentinel violation at {stage}: {concerns}"
            )
        elif self.on_violation == "block":
            self._logger.warning(f"[SENTINEL BLOCKED] {stage}: {concerns}")
        elif self.on_violation == "flag":
            # Silent flagging - just record, no log
            pass

    # ========================================================================
    # Public API
    # ========================================================================

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all logged violations (thread-safe copy)."""
        return self._violations_log.to_list()

    def get_validation_log(self) -> List[Dict[str, Any]]:
        """Get full validation history (thread-safe copy)."""
        return self._validation_log.to_list()

    def clear_violations(self) -> None:
        """Clear violation log."""
        self._violations_log.clear()

    def clear_log(self) -> None:
        """Clear all logs (violations and validation history)."""
        self._violations_log.clear()
        self._validation_log.clear()
        self._streaming_buffer.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get violation and validation statistics."""
        violations = self._violations_log.to_list()
        validations = self._validation_log.to_list()

        if not validations:
            return {"total_validations": 0, "total_violations": 0}

        by_stage = {}
        for v in violations:
            stage = v["stage"]
            by_stage[stage] = by_stage.get(stage, 0) + 1

        by_risk = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for v in violations:
            risk = v.get("risk_level", "medium")
            if risk in by_risk:
                by_risk[risk] += 1

        return {
            "total_validations": len(validations),
            "total_violations": len(violations),
            "safe_count": sum(1 for v in validations if v.get("safe", False)),
            "by_stage": by_stage,
            "by_risk": by_risk,
            "violation_rate": len(violations) / len(validations) if validations else 0,
        }


def create_safe_callback(
    on_violation: str = "log",
    seed_level: str = DEFAULT_SEED_LEVEL,
    validate_input: bool = True,
    validate_output: bool = True,
    max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
    validation_timeout: float = DEFAULT_VALIDATION_TIMEOUT,
    fail_closed: bool = False,
    **kwargs: Any,
) -> SentinelCallback:
    """
    Factory function to create a Sentinel callback handler.

    Args:
        on_violation: Action on violation ("log", "raise", "block", "flag")
        seed_level: Sentinel seed level
        validate_input: Whether to validate inputs
        validate_output: Whether to validate outputs
        max_text_size: Maximum text size in bytes (default 50KB)
        validation_timeout: Timeout for validation in seconds (default 30s)
        fail_closed: If True, block on validation errors
        **kwargs: Additional arguments for SentinelCallback

    Returns:
        Configured SentinelCallback instance

    Note:
        Callbacks MONITOR but do NOT BLOCK execution. The on_violation
        parameter controls logging/raising behavior, not request blocking.
        For actual request blocking, use SentinelGuard or SentinelChain.
    """
    return SentinelCallback(
        seed_level=seed_level,
        on_violation=on_violation,
        validate_input=validate_input,
        validate_output=validate_output,
        max_text_size=max_text_size,
        validation_timeout=validation_timeout,
        fail_closed=fail_closed,
        **kwargs,
    )


# Alias for backward compatibility
create_sentinel_callback = create_safe_callback


__all__ = [
    "SentinelCallback",
    "SentinelViolationError",
    "StreamingBuffer",
    "create_safe_callback",
    "create_sentinel_callback",
]
