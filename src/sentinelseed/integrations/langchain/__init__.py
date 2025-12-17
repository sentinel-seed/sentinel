"""
LangChain integration for Sentinel AI.

Provides:
- SentinelCallback: Callback handler to monitor LLM calls and responses
- SentinelGuard: Wrap agents with safety validation
- SentinelChain: Chain wrapper with built-in safety validation
- inject_seed: Add seed to message lists
- wrap_llm: Wrap LLMs with safety features

Usage:
    from sentinelseed.integrations.langchain import (
        SentinelCallback,
        SentinelGuard,
        SentinelChain,
        inject_seed,
        wrap_llm,
    )

    # Option 1: Use callback to monitor
    callback = SentinelCallback()
    llm = ChatOpenAI(callbacks=[callback])

    # Option 2: Wrap agent with guard
    safe_agent = SentinelGuard(agent)

    # Option 3: Inject seed into messages
    safe_messages = inject_seed(messages, seed_level="standard")
"""

from typing import Any, Dict, List, Optional, Union, Callable, Protocol
import logging
from collections import deque

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validators.semantic import SemanticValidator, AsyncSemanticValidator, THSPResult

# Default configuration
DEFAULT_MAX_VIOLATIONS = 1000
DEFAULT_SEED_LEVEL = "standard"

# Logger setup
_module_logger = logging.getLogger("sentinelseed.langchain")


class SentinelLogger(Protocol):
    """Protocol for custom loggers."""
    def debug(self, message: str) -> None: ...
    def info(self, message: str) -> None: ...
    def warning(self, message: str) -> None: ...
    def error(self, message: str) -> None: ...


class _DefaultLogger:
    """Default logger implementation."""
    def debug(self, message: str) -> None:
        _module_logger.debug(message)

    def info(self, message: str) -> None:
        _module_logger.info(message)

    def warning(self, message: str) -> None:
        _module_logger.warning(message)

    def error(self, message: str) -> None:
        _module_logger.error(message)


# Global logger instance
_logger: SentinelLogger = _DefaultLogger()


def set_logger(logger: SentinelLogger) -> None:
    """
    Set custom logger for the LangChain integration.

    Args:
        logger: Object implementing debug, info, warning, error methods

    Example:
        import logging
        logging.basicConfig(level=logging.DEBUG)
        set_logger(logging.getLogger("my_app.sentinel"))
    """
    global _logger
    _logger = logger


# Try to import LangChain base classes
try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
        from langchain.schema import SystemMessage, HumanMessage, AIMessage, BaseMessage
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        BaseCallbackHandler = object
        SystemMessage = None
        HumanMessage = None
        AIMessage = None
        BaseMessage = None
        LANGCHAIN_AVAILABLE = False
        _module_logger.warning(
            "LangChain not installed. Install with: pip install langchain langchain-core"
        )


class SentinelViolationError(Exception):
    """Raised when a Sentinel violation is detected."""
    pass


def _sanitize_text(text: str, max_length: int = 200, sanitize: bool = False) -> str:
    """
    Truncate and optionally sanitize text for logging.

    Args:
        text: Text to process
        max_length: Maximum length before truncation
        sanitize: If True, replace potentially sensitive patterns

    Returns:
        Processed text safe for logging
    """
    if not text:
        return ""

    result = text[:max_length] + ("..." if len(text) > max_length else "")

    if sanitize:
        # Mask potential emails
        import re
        result = re.sub(r'[\w.-]+@[\w.-]+\.\w+', '[EMAIL]', result)
        # Mask potential phone numbers
        result = re.sub(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[PHONE]', result)
        # Mask potential API keys/tokens (long alphanumeric strings)
        result = re.sub(r'\b[a-zA-Z0-9]{32,}\b', '[TOKEN]', result)

    return result


class SentinelCallback(BaseCallbackHandler):
    """
    LangChain callback handler for Sentinel safety monitoring.

    Monitors LLM inputs and outputs for safety violations using
    the THSP protocol. Inherits from LangChain's BaseCallbackHandler.

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

        # Check violations
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
    ):
        """
        Initialize callback handler.

        Args:
            sentinel: Sentinel instance (creates default if None)
            seed_level: Seed level for validation ("minimal", "standard", "full")
            on_violation: Action on violation:
                - "log": Log warning and continue
                - "raise": Raise SentinelViolationError
                - "block": Log as blocked (for monitoring)
                - "flag": Mark violation without logging
            validate_input: Whether to validate input messages/prompts
            validate_output: Whether to validate LLM responses
            log_safe: Whether to log safe responses too
            max_violations: Maximum violations to keep in log (prevents memory leak)
            sanitize_logs: Whether to mask sensitive data in logs
            logger: Custom logger instance
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
        self._logger = logger or _logger

        # Use deque with maxlen for bounded violation storage
        self._violations_log: deque = deque(maxlen=max_violations)
        self._validation_log: deque = deque(maxlen=max_violations)

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
            self._validate_input(prompt, stage="llm_input")

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
                content = self._extract_content(message)
                if content:
                    self._validate_input(content, stage="chat_input")

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes. Validates output."""
        if not self.validate_output:
            return

        # Handle LLMResult format
        if hasattr(response, 'generations'):
            for gen_list in response.generations:
                for gen in gen_list:
                    text = gen.text if hasattr(gen, 'text') else str(gen)
                    self._validate_output(text, stage="llm_output")
        # Handle AIMessage format
        elif hasattr(response, 'content'):
            self._validate_output(response.content, stage="llm_output")
        # Handle dict format
        elif isinstance(response, dict) and 'content' in response:
            self._validate_output(response['content'], stage="llm_output")

    def on_llm_new_token(self, token: str, **kwargs: Any) -> None:
        """Called on new token during streaming. Validates tokens."""
        if not self.validate_output:
            return

        # For streaming, we only validate complete words/phrases
        # Skip single tokens that might be partial words
        if len(token.strip()) > 3:
            is_safe, violations = self.sentinel.validate(token)
            if not is_safe:
                self._handle_violation(
                    stage="streaming_token",
                    text=token,
                    concerns=violations,
                    risk_level="medium"
                )

    def on_llm_error(
        self,
        error: BaseException,
        **kwargs: Any
    ) -> None:
        """Called on LLM error."""
        self._logger.debug(f"LLM error occurred: {type(error).__name__}")

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
                self._validate_input(value, stage="chain_input")

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
                self._validate_output(value, stage="chain_output")

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
            self._validate_input(input_str, stage="tool_input")

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Called when tool ends. Validates tool output."""
        if not self.validate_output:
            return

        if output:
            self._validate_output(output, stage="tool_output")

    def on_agent_action(
        self,
        action: Any,
        **kwargs: Any
    ) -> None:
        """Called on agent action. Validates action."""
        if not self.validate_input:
            return

        action_str = str(action)
        is_safe, violations = self.sentinel.validate_action(action_str)
        if not is_safe:
            self._handle_violation(
                stage="agent_action",
                text=action_str,
                concerns=violations,
                risk_level="high"
            )

    def _extract_content(self, message: Any) -> str:
        """Extract text content from various message formats."""
        if hasattr(message, 'content'):
            return message.content
        elif isinstance(message, dict):
            return message.get('content', '')
        else:
            return str(message)

    def _validate_input(self, text: str, stage: str) -> None:
        """Validate input text through THSP gates."""
        if not text:
            return

        result = self.sentinel.validate_request(text)

        # Log all validations
        self._validation_log.append({
            "stage": stage,
            "type": "input",
            "safe": result["should_proceed"],
            "risk_level": result.get("risk_level", "unknown"),
        })

        if not result["should_proceed"]:
            self._handle_violation(
                stage=stage,
                text=text,
                concerns=result["concerns"],
                risk_level=result["risk_level"]
            )
        elif self.log_safe:
            self._logger.info(f"[SENTINEL] Input validated: SAFE ({stage})")

    def _validate_output(self, text: str, stage: str) -> None:
        """Validate output text through THSP gates."""
        if not text:
            return

        is_safe, violations = self.sentinel.validate(text)

        # Log all validations
        self._validation_log.append({
            "stage": stage,
            "type": "output",
            "safe": is_safe,
            "risk_level": "high" if not is_safe else "low",
        })

        if not is_safe:
            self._handle_violation(
                stage=stage,
                text=text,
                concerns=violations,
                risk_level="high"
            )
        elif self.log_safe:
            self._logger.info(f"[SENTINEL] Output validated: SAFE ({stage})")

    def _handle_violation(
        self,
        stage: str,
        text: str,
        concerns: List[str],
        risk_level: str
    ) -> None:
        """Handle a detected violation."""
        sanitized_text = _sanitize_text(text, sanitize=self.sanitize_logs)

        violation = {
            "stage": stage,
            "text": sanitized_text,
            "concerns": concerns,
            "risk_level": risk_level
        }
        self._violations_log.append(violation)

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

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all logged violations."""
        return list(self._violations_log)

    def get_validation_log(self) -> List[Dict[str, Any]]:
        """Get full validation history (safe and unsafe)."""
        return list(self._validation_log)

    def clear_violations(self) -> None:
        """Clear violation log."""
        self._violations_log.clear()

    def clear_log(self) -> None:
        """Clear all logs (violations and validation history)."""
        self._violations_log.clear()
        self._validation_log.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get violation and validation statistics."""
        violations = list(self._violations_log)
        validations = list(self._validation_log)

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


class SentinelGuard:
    """
    Wrapper for LangChain agents/chains with Sentinel safety.

    Intercepts inputs and outputs, validating them before proceeding.

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
        """
        self.agent = agent
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.seed_level = seed_level
        self.block_unsafe = block_unsafe
        self.validate_input = validate_input
        self.validate_output = validate_output
        self.inject_seed = inject_seed
        self._logger = logger or _logger
        self._seed = self.sentinel.get_seed() if inject_seed else None

    def _maybe_validate_input(self, text: str) -> Optional[Dict[str, Any]]:
        """Validate input if enabled, return block response if unsafe."""
        if not self.validate_input:
            return None

        check = self.sentinel.validate_request(text)
        if not check["should_proceed"] and self.block_unsafe:
            return {
                "output": f"Request blocked by Sentinel: {check['concerns']}",
                "sentinel_blocked": True,
                "sentinel_reason": check["concerns"],
            }
        return None

    def _maybe_validate_output(self, text: str, original: str = "") -> Optional[Dict[str, Any]]:
        """Validate output if enabled, return block response if unsafe."""
        if not self.validate_output:
            return None

        is_safe, violations = self.sentinel.validate(text)
        if not is_safe and self.block_unsafe:
            return {
                "output": f"Response blocked by Sentinel: {violations}",
                "sentinel_blocked": True,
                "sentinel_reason": violations,
                "original_output": original[:200] if original else None,
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
            input_check = self.sentinel.validate_request(input_text)
            if not input_check["should_proceed"] and self.block_unsafe:
                return f"Request blocked by Sentinel: {input_check['concerns']}"

        # Run agent
        result = self.agent.run(input_text, **kwargs)

        # Post-validate output
        if self.validate_output:
            is_safe, violations = self.sentinel.validate(result)
            if not is_safe and self.block_unsafe:
                return f"Response blocked by Sentinel: {violations}"

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
        block_response = self._maybe_validate_input(input_text)
        if block_response:
            return block_response

        # Run agent
        try:
            result = self.agent.invoke(input_dict, **kwargs)
        except Exception as e:
            self._logger.error(f"Agent invoke error: {e}")
            raise

        # Post-validate output
        if isinstance(result, dict):
            output_text = result.get("output", str(result))
        else:
            output_text = str(result)

        block_response = self._maybe_validate_output(output_text, output_text)
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
        """Async version of invoke."""
        if isinstance(input_dict, str):
            input_dict = {"input": input_dict}

        input_text = input_dict.get("input", str(input_dict))

        block_response = self._maybe_validate_input(input_text)
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

        block_response = self._maybe_validate_output(output_text, output_text)
        if block_response:
            return block_response

        if isinstance(result, dict):
            result["sentinel_blocked"] = False
        else:
            result = {"output": result, "sentinel_blocked": False}

        return result


class SentinelChain:
    """
    A LangChain-compatible chain wrapper with built-in Sentinel safety.

    Validates inputs before sending to LLM/chain and validates outputs
    before returning to caller.

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
        self._logger = logger or _logger
        self._seed = self.sentinel.get_seed() if inject_seed else None

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
        if self.validate_input:
            check = self.sentinel.validate_request(input_text)
            if not check["should_proceed"]:
                return {
                    "output": None,
                    "blocked": True,
                    "blocked_at": "input",
                    "reason": check["concerns"]
                }

        # Call LLM or chain
        try:
            if self._is_llm:
                # Direct LLM call with messages
                messages = self._build_messages(input_text)
                response = self._runnable.invoke(messages, **kwargs)
            else:
                # Chain call - pass dict or use original input
                if isinstance(input_data, dict):
                    response = self._runnable.invoke(input_data, **kwargs)
                else:
                    response = self._runnable.invoke({"input": input_text}, **kwargs)
        except Exception as e:
            self._logger.error(f"Chain invoke error: {e}")
            raise

        output = self._extract_output(response)

        # Post-validate
        if self.validate_output:
            is_safe, violations = self.sentinel.validate(output)
            if not is_safe:
                return {
                    "output": output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": violations
                }

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

        if self.validate_input:
            check = self.sentinel.validate_request(input_text)
            if not check["should_proceed"]:
                return {
                    "output": None,
                    "blocked": True,
                    "blocked_at": "input",
                    "reason": check["concerns"]
                }

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

        if self.validate_output:
            is_safe, violations = self.sentinel.validate(output)
            if not is_safe:
                return {
                    "output": output,
                    "blocked": True,
                    "blocked_at": "output",
                    "violations": violations
                }

        return {
            "output": output,
            "blocked": False,
            "violations": None
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
        # Now safe_messages has a system message with the seed
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
        is_system = False
        current_content = ""

        if isinstance(msg, dict):
            if msg.get('role') == 'system':
                is_system = True
                current_content = msg.get('content', '')
        elif hasattr(msg, 'type') and msg.type == 'system':
            is_system = True
            current_content = getattr(msg, 'content', '')
        elif SystemMessage is not None and isinstance(msg, SystemMessage):
            is_system = True
            current_content = msg.content

        if is_system:
            # Prepend seed to existing system message
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


def create_safe_callback(
    on_violation: str = "log",
    seed_level: str = DEFAULT_SEED_LEVEL,
    validate_input: bool = True,
    validate_output: bool = True,
    **kwargs: Any,
) -> SentinelCallback:
    """
    Factory function to create a Sentinel callback handler.

    Args:
        on_violation: Action on violation ("log", "raise", "block", "flag")
        seed_level: Sentinel seed level
        validate_input: Whether to validate inputs
        validate_output: Whether to validate outputs
        **kwargs: Additional arguments for SentinelCallback

    Returns:
        Configured SentinelCallback instance

    Example:
        from langchain_openai import ChatOpenAI
        from sentinelseed.integrations.langchain import create_safe_callback

        callback = create_safe_callback(on_violation="log")
        llm = ChatOpenAI(callbacks=[callback])
    """
    return SentinelCallback(
        seed_level=seed_level,
        on_violation=on_violation,
        validate_input=validate_input,
        validate_output=validate_output,
        **kwargs,
    )


# Alias for backward compatibility
create_sentinel_callback = create_safe_callback


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

    This wrapper intercepts invoke/ainvoke calls and prepends the
    Sentinel seed to the system message.
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
        """Inject seed into messages using the inject_seed function."""
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

    def __getattr__(self, name: str) -> Any:
        """Proxy unknown attributes to wrapped LLM."""
        return getattr(self._llm, name)


# Public API exports
__all__ = [
    # Classes
    "SentinelCallback",
    "SentinelGuard",
    "SentinelChain",
    "SentinelViolationError",
    # Functions
    "inject_seed",
    "wrap_llm",
    "create_safe_callback",
    "create_sentinel_callback",
    "set_logger",
    # Constants
    "LANGCHAIN_AVAILABLE",
    "DEFAULT_SEED_LEVEL",
    "DEFAULT_MAX_VIOLATIONS",
]
