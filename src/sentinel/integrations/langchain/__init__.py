"""
LangChain integration for Sentinel AI.

Provides:
- SentinelCallback: Callback handler to monitor LLM calls and responses
- SentinelGuard: Wrap agents with safety validation
- SentinelChain: Chain with built-in safety validation

Usage:
    from sentinel.integrations.langchain import SentinelCallback, SentinelGuard

    # Option 1: Use callback to monitor
    callback = SentinelCallback()
    llm = ChatOpenAI(callbacks=[callback])

    # Option 2: Wrap agent with guard
    safe_agent = SentinelGuard(agent)
"""

from typing import Any, Dict, List, Optional, Union

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel

# Try to import LangChain base classes
try:
    from langchain_core.callbacks.base import BaseCallbackHandler
    LANGCHAIN_AVAILABLE = True
except ImportError:
    try:
        from langchain.callbacks.base import BaseCallbackHandler
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        # Fallback: create a dummy base class
        BaseCallbackHandler = object
        LANGCHAIN_AVAILABLE = False


class SentinelViolationError(Exception):
    """Raised when a Sentinel violation is detected."""
    pass


class SentinelCallback(BaseCallbackHandler):
    """
    LangChain callback handler for Sentinel safety monitoring.

    Monitors LLM inputs and outputs for safety violations using
    the THSP protocol. Inherits from LangChain's BaseCallbackHandler.

    Example:
        from langchain_openai import ChatOpenAI
        from sentinel.integrations.langchain import SentinelCallback

        callback = SentinelCallback(on_violation="log")
        llm = ChatOpenAI(callbacks=[callback])

        # All LLM calls will be monitored
        response = llm.invoke("Hello")
    """

    # BaseCallbackHandler properties
    raise_error: bool = False
    run_inline: bool = True

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        on_violation: str = "log",  # "log", "raise", "block"
        log_safe: bool = False,
    ):
        """
        Initialize callback handler.

        Args:
            sentinel: Sentinel instance (creates default if None)
            on_violation: Action on violation:
                - "log": Log warning and continue
                - "raise": Raise SentinelViolationError
                - "block": Log as blocked (for monitoring)
            log_safe: Whether to log safe responses too
        """
        super().__init__()
        self.sentinel = sentinel or Sentinel()
        self.on_violation = on_violation
        self.log_safe = log_safe
        self.violations_log: List[Dict[str, Any]] = []

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs: Any
    ) -> None:
        """Called when LLM starts. Validates input prompts."""
        for prompt in prompts:
            result = self.sentinel.validate_request(prompt)
            if not result["should_proceed"]:
                self._handle_violation(
                    stage="input",
                    text=prompt,
                    concerns=result["concerns"],
                    risk_level=result["risk_level"]
                )

    def on_chat_model_start(
        self,
        serialized: Dict[str, Any],
        messages: List[List[Any]],
        **kwargs: Any
    ) -> None:
        """Called when chat model starts. Validates input messages."""
        for message_list in messages:
            for message in message_list:
                # Extract content from various message formats
                if hasattr(message, 'content'):
                    content = message.content
                elif isinstance(message, dict):
                    content = message.get('content', '')
                else:
                    content = str(message)

                if content:
                    result = self.sentinel.validate_request(content)
                    if not result["should_proceed"]:
                        self._handle_violation(
                            stage="input",
                            text=content,
                            concerns=result["concerns"],
                            risk_level=result["risk_level"]
                        )

    def on_llm_end(self, response: Any, **kwargs: Any) -> None:
        """Called when LLM finishes. Validates output."""
        # Handle LLMResult format
        if hasattr(response, 'generations'):
            for gen_list in response.generations:
                for gen in gen_list:
                    text = gen.text if hasattr(gen, 'text') else str(gen)
                    self._validate_response(text)
        # Handle AIMessage format
        elif hasattr(response, 'content'):
            self._validate_response(response.content)
        # Handle dict format
        elif isinstance(response, dict) and 'content' in response:
            self._validate_response(response['content'])

    def on_llm_error(
        self,
        error: BaseException,
        **kwargs: Any
    ) -> None:
        """Called on LLM error. Does not interfere with error handling."""
        pass

    def on_chain_start(
        self,
        serialized: Dict[str, Any],
        inputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain starts. Validates chain inputs."""
        for key, value in inputs.items():
            if isinstance(value, str) and value:
                result = self.sentinel.validate_request(value)
                if not result["should_proceed"]:
                    self._handle_violation(
                        stage="chain_input",
                        text=value,
                        concerns=result["concerns"],
                        risk_level=result["risk_level"]
                    )

    def on_chain_end(
        self,
        outputs: Dict[str, Any],
        **kwargs: Any
    ) -> None:
        """Called when chain ends. Validates chain outputs."""
        for key, value in outputs.items():
            if isinstance(value, str) and value:
                is_safe, violations = self.sentinel.validate(value)
                if not is_safe:
                    self._handle_violation(
                        stage="chain_output",
                        text=value,
                        concerns=violations,
                        risk_level="high"
                    )

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        **kwargs: Any
    ) -> None:
        """Called when tool starts. Validates tool input."""
        if input_str:
            result = self.sentinel.validate_request(input_str)
            if not result["should_proceed"]:
                self._handle_violation(
                    stage="tool_input",
                    text=input_str,
                    concerns=result["concerns"],
                    risk_level=result["risk_level"]
                )

    def on_tool_end(
        self,
        output: str,
        **kwargs: Any
    ) -> None:
        """Called when tool ends. Validates tool output."""
        if output:
            is_safe, violations = self.sentinel.validate(output)
            if not is_safe:
                self._handle_violation(
                    stage="tool_output",
                    text=output,
                    concerns=violations,
                    risk_level="high"
                )

    def on_agent_action(
        self,
        action: Any,
        **kwargs: Any
    ) -> None:
        """Called on agent action. Validates action."""
        action_str = str(action)
        is_safe, violations = self.sentinel.validate_action(action_str)
        if not is_safe:
            self._handle_violation(
                stage="agent_action",
                text=action_str,
                concerns=violations,
                risk_level="high"
            )

    def _validate_response(self, text: str) -> None:
        """Validate a response through THSP gates."""
        if not text:
            return

        is_safe, violations = self.sentinel.validate(text)

        if not is_safe:
            self._handle_violation(
                stage="output",
                text=text,
                concerns=violations,
                risk_level="high"
            )
        elif self.log_safe:
            print("[SENTINEL] Response validated: SAFE")

    def _handle_violation(
        self,
        stage: str,
        text: str,
        concerns: List[str],
        risk_level: str
    ) -> None:
        """Handle a detected violation."""
        violation = {
            "stage": stage,
            "text": text[:200] + "..." if len(text) > 200 else text,
            "concerns": concerns,
            "risk_level": risk_level
        }
        self.violations_log.append(violation)

        if self.on_violation == "log":
            print(f"[SENTINEL VIOLATION] {stage}: {concerns}")
        elif self.on_violation == "raise":
            raise SentinelViolationError(
                f"Sentinel violation at {stage}: {concerns}"
            )
        elif self.on_violation == "block":
            print(f"[SENTINEL BLOCKED] {stage}: {concerns}")

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all logged violations."""
        return self.violations_log

    def clear_violations(self) -> None:
        """Clear violation log."""
        self.violations_log = []

    def get_stats(self) -> Dict[str, Any]:
        """Get violation statistics."""
        if not self.violations_log:
            return {"total": 0}

        by_stage = {}
        for v in self.violations_log:
            stage = v["stage"]
            by_stage[stage] = by_stage.get(stage, 0) + 1

        return {
            "total": len(self.violations_log),
            "by_stage": by_stage,
            "high_risk": sum(1 for v in self.violations_log if v["risk_level"] == "high"),
        }


class SentinelGuard:
    """
    Wrapper for LangChain agents/chains with Sentinel safety.

    Intercepts inputs and outputs, validating them before proceeding.

    Example:
        from langchain.agents import AgentExecutor
        from sentinel.integrations.langchain import SentinelGuard

        agent = AgentExecutor(...)
        safe_agent = SentinelGuard(agent)
        result = safe_agent.invoke({"input": "Do something"})
    """

    def __init__(
        self,
        agent: Any,
        sentinel: Optional[Sentinel] = None,
        block_unsafe: bool = True,
    ):
        """
        Initialize guard.

        Args:
            agent: LangChain agent/chain to wrap
            sentinel: Sentinel instance (creates default if None)
            block_unsafe: Whether to block unsafe actions
        """
        self.agent = agent
        self.sentinel = sentinel or Sentinel()
        self.block_unsafe = block_unsafe

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
        input_check = self.sentinel.validate_request(input_text)
        if not input_check["should_proceed"] and self.block_unsafe:
            return f"Request blocked by Sentinel: {input_check['concerns']}"

        # Run agent
        result = self.agent.run(input_text, **kwargs)

        # Post-validate output
        is_safe, violations = self.sentinel.validate(result)
        if not is_safe and self.block_unsafe:
            return f"Response blocked by Sentinel: {violations}"

        return result

    def invoke(
        self,
        input_dict: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Invoke agent with safety validation (new interface).

        Args:
            input_dict: Input dictionary
            **kwargs: Additional arguments

        Returns:
            Agent response dictionary
        """
        # Extract input text
        input_text = input_dict.get("input", str(input_dict))

        # Pre-validate
        input_check = self.sentinel.validate_request(input_text)
        if not input_check["should_proceed"] and self.block_unsafe:
            return {
                "output": f"Request blocked by Sentinel: {input_check['concerns']}",
                "sentinel_blocked": True,
            }

        # Run agent
        result = self.agent.invoke(input_dict, **kwargs)

        # Post-validate output
        output_text = result.get("output", str(result))
        is_safe, violations = self.sentinel.validate(output_text)
        if not is_safe and self.block_unsafe:
            return {
                "output": f"Response blocked by Sentinel: {violations}",
                "sentinel_blocked": True,
                "original_output": output_text[:200],
            }

        result["sentinel_blocked"] = False
        return result

    async def ainvoke(
        self,
        input_dict: Dict[str, Any],
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Async version of invoke."""
        input_text = input_dict.get("input", str(input_dict))

        input_check = self.sentinel.validate_request(input_text)
        if not input_check["should_proceed"] and self.block_unsafe:
            return {
                "output": f"Request blocked by Sentinel: {input_check['concerns']}",
                "sentinel_blocked": True,
            }

        result = await self.agent.ainvoke(input_dict, **kwargs)

        output_text = result.get("output", str(result))
        is_safe, violations = self.sentinel.validate(output_text)
        if not is_safe and self.block_unsafe:
            return {
                "output": f"Response blocked by Sentinel: {violations}",
                "sentinel_blocked": True,
            }

        result["sentinel_blocked"] = False
        return result


class SentinelChain:
    """
    A LangChain-compatible chain with built-in Sentinel safety.

    Validates inputs before sending to LLM and validates outputs
    before returning to caller.

    Example:
        from langchain_openai import ChatOpenAI
        from sentinel.integrations.langchain import SentinelChain

        chain = SentinelChain(llm=ChatOpenAI())
        result = chain.invoke("Help me with something")
    """

    def __init__(
        self,
        llm: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
        inject_seed: bool = True,
    ):
        """
        Initialize chain.

        Args:
            llm: LangChain LLM instance
            sentinel: Sentinel instance
            seed_level: Seed level to use
            inject_seed: Whether to inject seed into system message
        """
        self.llm = llm
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.inject_seed = inject_seed

    def invoke(
        self,
        input_text: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Run chain with safety validation.

        Args:
            input_text: User input
            **kwargs: Additional arguments for LLM

        Returns:
            Dict with output and safety status
        """
        # Pre-validate
        check = self.sentinel.validate_request(input_text)
        if not check["should_proceed"]:
            return {
                "output": None,
                "blocked": True,
                "reason": check["concerns"]
            }

        # Build messages
        messages = []
        if self.inject_seed:
            seed = self.sentinel.get_seed()
            messages.append({"role": "system", "content": seed})
        messages.append({"role": "user", "content": input_text})

        # Call LLM
        if hasattr(self.llm, 'invoke'):
            response = self.llm.invoke(messages, **kwargs)
            if hasattr(response, 'content'):
                output = response.content
            else:
                output = str(response)
        else:
            # Legacy interface
            output = self.llm(messages, **kwargs)
            if hasattr(output, 'content'):
                output = output.content

        # Post-validate
        is_safe, violations = self.sentinel.validate(output)

        return {
            "output": output,
            "blocked": not is_safe,
            "violations": violations if not is_safe else None
        }

    async def ainvoke(
        self,
        input_text: str,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """Async version of invoke."""
        check = self.sentinel.validate_request(input_text)
        if not check["should_proceed"]:
            return {
                "output": None,
                "blocked": True,
                "reason": check["concerns"]
            }

        messages = []
        if self.inject_seed:
            seed = self.sentinel.get_seed()
            messages.append({"role": "system", "content": seed})
        messages.append({"role": "user", "content": input_text})

        response = await self.llm.ainvoke(messages, **kwargs)
        if hasattr(response, 'content'):
            output = response.content
        else:
            output = str(response)

        is_safe, violations = self.sentinel.validate(output)

        return {
            "output": output,
            "blocked": not is_safe,
            "violations": violations if not is_safe else None
        }


def create_sentinel_callback(
    on_violation: str = "log",
    seed_level: str = "standard",
) -> SentinelCallback:
    """
    Factory function to create a Sentinel callback handler.

    Args:
        on_violation: Action on violation ("log", "raise", "block")
        seed_level: Sentinel seed level

    Returns:
        Configured SentinelCallback instance

    Example:
        from langchain_openai import ChatOpenAI
        from sentinel.integrations.langchain import create_sentinel_callback

        callback = create_sentinel_callback(on_violation="log")
        llm = ChatOpenAI(callbacks=[callback])
    """
    sentinel = Sentinel(seed_level=seed_level)
    return SentinelCallback(sentinel=sentinel, on_violation=on_violation)


def wrap_llm(
    llm: Any,
    sentinel: Optional[Sentinel] = None,
    seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
    inject_seed: bool = True,
    add_callback: bool = True,
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

    Returns:
        Wrapped LLM with Sentinel safety

    Example:
        from langchain_openai import ChatOpenAI
        from sentinel.integrations.langchain import wrap_llm

        # Wrap an existing LLM
        llm = ChatOpenAI(model="gpt-4o")
        safe_llm = wrap_llm(llm)

        # Now use safe_llm - it has Sentinel protection
        response = safe_llm.invoke("Help me with something")
    """
    sentinel = sentinel or Sentinel(seed_level=seed_level)

    # Add callback if requested
    if add_callback:
        callback = SentinelCallback(sentinel=sentinel)
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
        """Inject seed into messages."""
        if not messages:
            return messages

        # Handle list of messages
        if isinstance(messages, list):
            messages = list(messages)

            # Check for existing system message
            has_system = False
            for i, msg in enumerate(messages):
                if isinstance(msg, dict) and msg.get('role') == 'system':
                    messages[i] = {
                        **msg,
                        'content': f"{self._seed}\n\n---\n\n{msg['content']}"
                    }
                    has_system = True
                    break
                elif hasattr(msg, 'type') and msg.type == 'system':
                    # LangChain message object
                    try:
                        from langchain_core.messages import SystemMessage
                        messages[i] = SystemMessage(
                            content=f"{self._seed}\n\n---\n\n{msg.content}"
                        )
                    except ImportError:
                        pass
                    has_system = True
                    break

            # Add system message if none exists
            if not has_system:
                try:
                    from langchain_core.messages import SystemMessage
                    messages.insert(0, SystemMessage(content=self._seed))
                except ImportError:
                    messages.insert(0, {'role': 'system', 'content': self._seed})

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
