"""
DSPy Agent Modules for Sentinel THSP validation.

This module provides specialized modules for validating agentic workflows:
- SentinelToolValidator: Validate tool/function calls before execution
- SentinelAgentGuard: Validate each step of agent execution
- SentinelMemoryGuard: Validate data before writing to agent memory

Usage:
    from sentinelseed.integrations.dspy import (
        SentinelToolValidator,
        SentinelAgentGuard,
        SentinelMemoryGuard,
    )
"""

from typing import Any, Callable, Dict, List, Literal, Optional, Union

try:
    import dspy
    from dspy import Module, Prediction
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

from sentinelseed.integrations.dspy.utils import (
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    CONFIDENCE_NONE,
    CONFIDENCE_LOW,
    CONFIDENCE_HIGH,
    TextTooLargeError,
    ValidationTimeoutError,
    HeuristicFallbackError,
    get_logger,
    get_validation_executor,
    run_with_timeout_async,
    validate_mode,
    validate_provider,
    validate_text_size,
    validate_config_types,
    warn_fail_open_default,
)

logger = get_logger()


class SentinelToolValidator:
    """
    Validates tool/function calls before execution.

    Wraps tool functions to validate their arguments and optionally
    their outputs using THSP protocol.

    Args:
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model for validation
        mode: Validation mode ("block", "flag", "heuristic")
        validate_args: Validate tool arguments (default: True)
        validate_output: Validate tool output (default: False)
        max_text_size: Maximum text size in bytes
        timeout: Validation timeout in seconds
        fail_closed: If True, block on validation errors

    Example:
        validator = SentinelToolValidator(api_key="sk-...")

        @validator.wrap
        def search_web(query: str) -> str:
            return web_search(query)

        # Or wrap existing function
        safe_search = validator.wrap(search_web)

        # Tool calls are validated before execution
        result = safe_search(query="how to make cookies")
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        validate_args: bool = True,
        validate_output: bool = False,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        validate_config_types(
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
        )
        validate_mode(mode)
        if provider and mode != "heuristic":
            validate_provider(provider)

        self.validate_args = validate_args
        self.validate_output = validate_output
        self.max_text_size = max_text_size
        self.timeout = timeout
        self.fail_closed = fail_closed
        self.mode = mode
        self._logger = logger

        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelToolValidator")

        # Initialize validator
        self._is_degraded = False
        if mode == "heuristic" or not api_key:
            if not api_key and mode != "heuristic":
                self._is_degraded = True
                self._logger.warning(
                    "\n" + "=" * 60 + "\n"
                    "SENTINEL DEGRADED MODE WARNING\n"
                    "=" * 60 + "\n"
                    "No API key provided for SentinelToolValidator.\n"
                    "Falling back to HEURISTIC validation (~50% accuracy).\n"
                    "=" * 60
                )
            self._validator = THSPValidator()
            self._is_semantic = False
        else:
            self._validator = SemanticValidator(
                provider=provider,
                model=model,
                api_key=api_key,
            )
            self._is_semantic = True

    @property
    def is_degraded(self) -> bool:
        """Check if validator is running in degraded (heuristic) mode."""
        return self._is_degraded

    def _validate(self, content: str, context: str = "") -> Dict[str, Any]:
        """Validate content with optional context."""
        try:
            validate_text_size(content, self.max_text_size)

            if context:
                full_content = f"Context: {context}\n\nContent: {content}"
            else:
                full_content = content

            executor = get_validation_executor()

            def do_validate():
                if self._is_semantic:
                    result: THSPResult = self._validator.validate(full_content)
                    return {
                        "is_safe": result.is_safe,
                        "gates": result.gate_results,
                        "issues": result.failed_gates,
                        "reasoning": result.reasoning,
                        "method": "semantic",
                        "confidence": CONFIDENCE_HIGH,
                    }
                else:
                    result = self._validator.validate(full_content)
                    return {
                        "is_safe": result.get("safe", True),
                        "gates": result.get("gates", {}),
                        "issues": result.get("issues", []),
                        "reasoning": "Heuristic pattern-based validation",
                        "method": "heuristic",
                        "confidence": CONFIDENCE_LOW,
                    }

            return executor.run_with_timeout(
                do_validate,
                args=(),
                timeout=self.timeout,
            )

        except TextTooLargeError:
            raise
        except ValidationTimeoutError:
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "issues": ["Validation timed out"],
                    "reasoning": "Validation timed out (fail_closed=True)",
                    "method": "timeout",
                    "confidence": CONFIDENCE_NONE,
                }
            raise
        except Exception as e:
            self._logger.error(f"Tool validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "issues": [str(e)],
                    "reasoning": f"Validation error: {e}",
                    "method": "error",
                    "confidence": CONFIDENCE_NONE,
                }
            return {
                "is_safe": True,
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
                "confidence": CONFIDENCE_NONE,
            }

    def wrap(self, func: Callable) -> Callable:
        """
        Wrap a tool function with safety validation.

        Args:
            func: The tool function to wrap

        Returns:
            Wrapped function that validates before/after execution
        """
        def wrapped(*args, **kwargs):
            tool_name = func.__name__

            # Validate arguments
            if self.validate_args:
                args_str = f"Tool: {tool_name}\nArguments: {args} {kwargs}"
                validation = self._validate(
                    args_str,
                    context=f"Validating tool call arguments for {tool_name}"
                )

                if not validation["is_safe"]:
                    if self.mode == "block":
                        return {
                            "error": "Tool call blocked by Sentinel",
                            "reasoning": validation["reasoning"],
                            "safety_blocked": True,
                            "safety_issues": validation["issues"],
                        }
                    # Flag mode: log warning but continue
                    self._logger.warning(
                        f"Tool {tool_name} args flagged: {validation['reasoning']}"
                    )

            # Execute tool
            result = func(*args, **kwargs)

            # Validate output
            if self.validate_output:
                output_str = str(result)
                output_validation = self._validate(
                    output_str,
                    context=f"Validating tool output from {tool_name}"
                )

                if not output_validation["is_safe"]:
                    if self.mode == "block":
                        return {
                            "error": "Tool output blocked by Sentinel",
                            "reasoning": output_validation["reasoning"],
                            "safety_blocked": True,
                            "safety_issues": output_validation["issues"],
                        }
                    self._logger.warning(
                        f"Tool {tool_name} output flagged: {output_validation['reasoning']}"
                    )

            return result

        wrapped.__name__ = func.__name__
        wrapped.__doc__ = func.__doc__
        return wrapped

    def validate_call(
        self,
        tool_name: str,
        args: tuple = (),
        kwargs: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Validate a tool call without executing it.

        Args:
            tool_name: Name of the tool
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Validation result dict
        """
        kwargs = kwargs or {}
        args_str = f"Tool: {tool_name}\nArguments: {args} {kwargs}"
        return self._validate(
            args_str,
            context=f"Validating tool call to {tool_name}"
        )


class SentinelAgentGuard(Module):
    """
    Validates each step of agent execution.

    Wraps a DSPy agent module and validates:
    - Input to the agent
    - Each reasoning/action step
    - Final output

    Args:
        agent: The DSPy agent module to wrap
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        mode: Validation mode
        validate_input: Validate agent input (default: True)
        validate_steps: Validate intermediate steps (default: True)
        validate_output: Validate final output (default: True)
        max_text_size: Maximum text size in bytes
        timeout: Validation timeout per step in seconds
        fail_closed: If True, block on validation errors
        step_callback: Optional callback(step_num, step_content, validation_result)

    Example:
        agent = dspy.ReAct("task -> result", tools=[...])
        safe_agent = SentinelAgentGuard(
            agent,
            api_key="sk-...",
            validate_steps=True,
            step_callback=lambda n, c, v: print(f"Step {n}: {'SAFE' if v['is_safe'] else 'UNSAFE'}")
        )
        result = safe_agent(task="Research topic X")
    """

    def __init__(
        self,
        agent: Module,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        validate_input: bool = True,
        validate_steps: bool = True,
        validate_output: bool = True,
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        step_callback: Optional[Callable[[int, str, Dict], None]] = None,
    ):
        super().__init__()

        validate_config_types(
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
        )
        validate_mode(mode)
        if provider and mode != "heuristic":
            validate_provider(provider)

        self.agent = agent
        self.validate_input = validate_input
        self.validate_steps = validate_steps
        self.validate_output = validate_output
        self.max_text_size = max_text_size
        self.timeout = timeout
        self.fail_closed = fail_closed
        self.mode = mode
        self.step_callback = step_callback
        self._logger = logger

        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelAgentGuard")

        # Initialize validator
        self._is_degraded = False
        if mode == "heuristic" or not api_key:
            if not api_key and mode != "heuristic":
                self._is_degraded = True
                self._logger.warning(
                    "\n" + "=" * 60 + "\n"
                    "SENTINEL DEGRADED MODE WARNING\n"
                    "=" * 60 + "\n"
                    "No API key provided for SentinelAgentGuard.\n"
                    "Falling back to HEURISTIC validation (~50% accuracy).\n"
                    "=" * 60
                )
            self._validator = THSPValidator()
            self._is_semantic = False
        else:
            self._validator = SemanticValidator(
                provider=provider,
                model=model,
                api_key=api_key,
            )
            self._is_semantic = True

    @property
    def is_degraded(self) -> bool:
        """Check if validator is running in degraded (heuristic) mode."""
        return self._is_degraded

    def _validate(self, content: str, context: str = "") -> Dict[str, Any]:
        """Validate content with optional context."""
        try:
            validate_text_size(content, self.max_text_size)

            if context:
                full_content = f"Context: {context}\n\nContent: {content}"
            else:
                full_content = content

            executor = get_validation_executor()

            def do_validate():
                if self._is_semantic:
                    result: THSPResult = self._validator.validate(full_content)
                    return {
                        "is_safe": result.is_safe,
                        "gates": result.gate_results,
                        "issues": result.failed_gates,
                        "reasoning": result.reasoning,
                        "method": "semantic",
                        "confidence": CONFIDENCE_HIGH,
                    }
                else:
                    result = self._validator.validate(full_content)
                    return {
                        "is_safe": result.get("safe", True),
                        "gates": result.get("gates", {}),
                        "issues": result.get("issues", []),
                        "reasoning": "Heuristic pattern-based validation",
                        "method": "heuristic",
                        "confidence": CONFIDENCE_LOW,
                    }

            return executor.run_with_timeout(
                do_validate,
                args=(),
                timeout=self.timeout,
            )

        except (TextTooLargeError, ValidationTimeoutError):
            raise
        except Exception as e:
            self._logger.error(f"Agent validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "issues": [str(e)],
                    "reasoning": f"Validation error: {e}",
                    "method": "error",
                    "confidence": CONFIDENCE_NONE,
                }
            return {
                "is_safe": True,
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
                "confidence": CONFIDENCE_NONE,
            }

    def forward(self, **kwargs) -> Prediction:
        """Execute agent with step-by-step validation."""
        step_validations = []
        step_num = 0

        # Validate input
        if self.validate_input:
            input_str = str(kwargs)
            validation = self._validate(input_str, "Agent input validation")
            step_validations.append({"step": "input", "validation": validation})

            if self.step_callback:
                self.step_callback(step_num, input_str, validation)
            step_num += 1

            if not validation["is_safe"] and self.mode == "block":
                blocked = Prediction()
                blocked.safety_blocked = True
                blocked.safety_passed = False
                blocked.safety_step = "input"
                blocked.safety_reasoning = validation["reasoning"]
                blocked.safety_step_validations = step_validations
                return blocked

        # Execute agent
        result = self.agent(**kwargs)

        # Validate intermediate steps if available (ReAct-style)
        if self.validate_steps and hasattr(result, "trajectory"):
            for i, step in enumerate(result.trajectory):
                step_str = str(step)
                validation = self._validate(
                    step_str,
                    f"Agent step {i+1} validation"
                )
                step_validations.append({
                    "step": f"step_{i+1}",
                    "validation": validation
                })

                if self.step_callback:
                    self.step_callback(step_num, step_str, validation)
                step_num += 1

                if not validation["is_safe"] and self.mode == "block":
                    blocked = Prediction()
                    blocked.safety_blocked = True
                    blocked.safety_passed = False
                    blocked.safety_step = f"step_{i+1}"
                    blocked.safety_reasoning = validation["reasoning"]
                    blocked.safety_step_validations = step_validations
                    # Include partial results
                    try:
                        for key in result.keys():
                            setattr(blocked, key, "[BLOCKED]")
                    except (AttributeError, TypeError):
                        pass
                    return blocked

        # Validate output
        if self.validate_output:
            output_str = str(result)
            validation = self._validate(output_str, "Agent output validation")
            step_validations.append({"step": "output", "validation": validation})

            if self.step_callback:
                self.step_callback(step_num, output_str, validation)

            if not validation["is_safe"] and self.mode == "block":
                blocked = Prediction()
                blocked.safety_blocked = True
                blocked.safety_passed = False
                blocked.safety_step = "output"
                blocked.safety_reasoning = validation["reasoning"]
                blocked.safety_step_validations = step_validations
                return blocked

        # All validations passed
        result.safety_passed = True
        result.safety_blocked = False
        result.safety_step_validations = step_validations
        result.safety_steps_validated = len(step_validations)

        return result


class SentinelMemoryGuard:
    """
    Validates data before writing to agent memory.

    Can be used with any memory system to ensure only safe
    content is persisted.

    Args:
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        mode: Validation mode
        max_text_size: Maximum text size in bytes
        timeout: Validation timeout in seconds
        fail_closed: If True, block writes on validation errors

    Example:
        memory_guard = SentinelMemoryGuard(api_key="sk-...")

        # Wrap memory writes
        if memory_guard.validate_write(key="user_data", value=data):
            memory.write(key, data)
        else:
            logger.warning("Blocked unsafe memory write")

        # Or use as context manager
        with memory_guard.safe_write(memory, key, value) as result:
            if result.blocked:
                handle_blocked_write(result.reasoning)
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        validate_config_types(
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
        )
        validate_mode(mode)
        if provider and mode != "heuristic":
            validate_provider(provider)

        self.max_text_size = max_text_size
        self.timeout = timeout
        self.fail_closed = fail_closed
        self.mode = mode
        self._logger = logger

        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelMemoryGuard")

        # Initialize validator
        self._is_degraded = False
        if mode == "heuristic" or not api_key:
            if not api_key and mode != "heuristic":
                self._is_degraded = True
                self._logger.warning(
                    "\n" + "=" * 60 + "\n"
                    "SENTINEL DEGRADED MODE WARNING\n"
                    "=" * 60 + "\n"
                    "No API key provided for SentinelMemoryGuard.\n"
                    "Falling back to HEURISTIC validation (~50% accuracy).\n"
                    "=" * 60
                )
            self._validator = THSPValidator()
            self._is_semantic = False
        else:
            self._validator = SemanticValidator(
                provider=provider,
                model=model,
                api_key=api_key,
            )
            self._is_semantic = True

    @property
    def is_degraded(self) -> bool:
        """Check if validator is running in degraded (heuristic) mode."""
        return self._is_degraded

    def _validate(self, content: str, context: str = "") -> Dict[str, Any]:
        """Validate content with optional context."""
        try:
            validate_text_size(content, self.max_text_size)

            if context:
                full_content = f"Context: {context}\n\nContent: {content}"
            else:
                full_content = content

            executor = get_validation_executor()

            def do_validate():
                if self._is_semantic:
                    result: THSPResult = self._validator.validate(full_content)
                    return {
                        "is_safe": result.is_safe,
                        "gates": result.gate_results,
                        "issues": result.failed_gates,
                        "reasoning": result.reasoning,
                        "method": "semantic",
                        "confidence": CONFIDENCE_HIGH,
                    }
                else:
                    result = self._validator.validate(full_content)
                    return {
                        "is_safe": result.get("safe", True),
                        "gates": result.get("gates", {}),
                        "issues": result.get("issues", []),
                        "reasoning": "Heuristic pattern-based validation",
                        "method": "heuristic",
                        "confidence": CONFIDENCE_LOW,
                    }

            return executor.run_with_timeout(
                do_validate,
                args=(),
                timeout=self.timeout,
            )

        except (TextTooLargeError, ValidationTimeoutError):
            raise
        except Exception as e:
            self._logger.error(f"Memory validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "issues": [str(e)],
                    "reasoning": f"Validation error: {e}",
                    "method": "error",
                    "confidence": CONFIDENCE_NONE,
                }
            return {
                "is_safe": True,
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
                "confidence": CONFIDENCE_NONE,
            }

    def validate_write(
        self,
        key: str,
        value: Any,
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Validate data before writing to memory.

        Args:
            key: Memory key/identifier
            value: Data to write
            metadata: Optional metadata about the write

        Returns:
            Validation result with is_safe, reasoning, etc.
        """
        content = f"Memory write:\nKey: {key}\nValue: {value}"
        if metadata:
            content += f"\nMetadata: {metadata}"

        return self._validate(
            content,
            context="Validating memory write operation"
        )

    def validate_read(
        self,
        key: str,
        value: Any,
    ) -> Dict[str, Any]:
        """
        Validate data read from memory before use.

        Args:
            key: Memory key that was read
            value: Data that was read

        Returns:
            Validation result
        """
        content = f"Memory read:\nKey: {key}\nValue: {value}"
        return self._validate(
            content,
            context="Validating memory read operation"
        )

    def wrap_memory(self, memory: Any) -> "SafeMemoryWrapper":
        """
        Wrap a memory object with safety validation.

        Args:
            memory: Memory object with get/set methods

        Returns:
            SafeMemoryWrapper that validates all operations
        """
        return SafeMemoryWrapper(memory, self)


class SafeMemoryWrapper:
    """
    Wrapper that validates all memory operations.

    Created by SentinelMemoryGuard.wrap_memory().
    """

    def __init__(self, memory: Any, guard: SentinelMemoryGuard):
        self._memory = memory
        self._guard = guard
        self._blocked_writes: List[Dict] = []

    def set(self, key: str, value: Any, **kwargs) -> bool:
        """
        Validate and write to memory.

        Returns:
            True if write succeeded, False if blocked
        """
        validation = self._guard.validate_write(key, value, kwargs)

        if not validation["is_safe"]:
            if self._guard.mode == "block":
                self._blocked_writes.append({
                    "key": key,
                    "value": value,
                    "reasoning": validation["reasoning"],
                })
                return False
            # Flag mode: log but continue
            self._guard._logger.warning(
                f"Memory write to {key} flagged: {validation['reasoning']}"
            )

        # Perform actual write
        if hasattr(self._memory, "set"):
            self._memory.set(key, value, **kwargs)
        elif hasattr(self._memory, "__setitem__"):
            self._memory[key] = value
        else:
            setattr(self._memory, key, value)

        return True

    def get(self, key: str, default: Any = None, validate: bool = False) -> Any:
        """
        Read from memory with optional validation.

        Args:
            key: Memory key
            default: Default value if not found
            validate: If True, validate read value

        Returns:
            Value from memory (or default)
        """
        if hasattr(self._memory, "get"):
            value = self._memory.get(key, default)
        elif hasattr(self._memory, "__getitem__"):
            try:
                value = self._memory[key]
            except (KeyError, IndexError):
                value = default
        else:
            value = getattr(self._memory, key, default)

        if validate and value is not None:
            validation = self._guard.validate_read(key, value)
            if not validation["is_safe"]:
                self._guard._logger.warning(
                    f"Memory read from {key} flagged: {validation['reasoning']}"
                )

        return value

    @property
    def blocked_writes(self) -> List[Dict]:
        """Get list of blocked write attempts."""
        return self._blocked_writes.copy()

    def clear_blocked_writes(self):
        """Clear the blocked writes log."""
        self._blocked_writes.clear()
