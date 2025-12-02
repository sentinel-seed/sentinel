"""
LangChain integration for Sentinel AI.

Provides:
- SentinelCallback: Monitor LLM calls and responses
- SentinelGuard: Wrap agents with safety validation
- wrap_llm: Wrap any LangChain LLM with Sentinel

Usage:
    from sentinel.integrations.langchain import SentinelCallback, wrap_llm

    # Option 1: Use callback to monitor
    callback = SentinelCallback()
    llm = ChatOpenAI(callbacks=[callback])

    # Option 2: Wrap LLM directly
    safe_llm = wrap_llm(llm)
"""

from typing import Any, Dict, List, Optional, Union
from sentinel import Sentinel, SeedLevel


class SentinelCallback:
    """
    LangChain callback handler for Sentinel monitoring.

    Monitors LLM inputs and outputs for safety violations.

    Example:
        from langchain_openai import ChatOpenAI
        from sentinel.integrations.langchain import SentinelCallback

        callback = SentinelCallback(on_violation="log")
        llm = ChatOpenAI(callbacks=[callback])
    """

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        on_violation: str = "log",  # "log", "raise", "block"
        log_safe: bool = False,
    ):
        """
        Initialize callback.

        Args:
            sentinel: Sentinel instance (creates default if None)
            on_violation: Action on violation ("log", "raise", "block")
            log_safe: Whether to log safe responses too
        """
        self.sentinel = sentinel or Sentinel()
        self.on_violation = on_violation
        self.log_safe = log_safe
        self.violations_log: List[Dict[str, Any]] = []

    def on_llm_start(
        self,
        serialized: Dict[str, Any],
        prompts: List[str],
        **kwargs
    ) -> None:
        """Called when LLM starts."""
        # Pre-validate prompts
        for prompt in prompts:
            result = self.sentinel.validate_request(prompt)
            if not result["should_proceed"]:
                self._handle_violation(
                    stage="input",
                    text=prompt,
                    concerns=result["concerns"],
                    risk_level=result["risk_level"]
                )

    def on_llm_end(self, response, **kwargs) -> None:
        """Called when LLM finishes."""
        # Get response text
        if hasattr(response, 'generations'):
            for gen_list in response.generations:
                for gen in gen_list:
                    text = gen.text if hasattr(gen, 'text') else str(gen)
                    self._validate_response(text)
        elif hasattr(response, 'content'):
            self._validate_response(response.content)

    def on_llm_error(self, error: Exception, **kwargs) -> None:
        """Called on LLM error."""
        pass  # Don't interfere with error handling

    def _validate_response(self, text: str) -> None:
        """Validate a response through THS gates."""
        is_safe, violations = self.sentinel.validate(text)

        if not is_safe:
            self._handle_violation(
                stage="output",
                text=text,
                concerns=violations,
                risk_level="high"
            )
        elif self.log_safe:
            print(f"[SENTINEL] Response validated: SAFE")

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
            raise SentinelViolationError(f"Sentinel violation at {stage}: {concerns}")
        elif self.on_violation == "block":
            # In block mode, we log but also potentially interrupt
            print(f"[SENTINEL BLOCKED] {stage}: {concerns}")

    def get_violations(self) -> List[Dict[str, Any]]:
        """Get all logged violations."""
        return self.violations_log

    def clear_violations(self) -> None:
        """Clear violation log."""
        self.violations_log = []


class SentinelViolationError(Exception):
    """Raised when a Sentinel violation is detected."""
    pass


class SentinelGuard:
    """
    Wrapper for LangChain agents with Sentinel safety.

    Intercepts agent actions and validates them before execution.

    Example:
        from langchain.agents import AgentExecutor
        from sentinel.integrations.langchain import SentinelGuard

        agent = AgentExecutor(...)
        safe_agent = SentinelGuard(agent)
        result = safe_agent.run("Do something")
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
            agent: LangChain agent to wrap
            sentinel: Sentinel instance (creates default if None)
            block_unsafe: Whether to block unsafe actions
        """
        self.agent = agent
        self.sentinel = sentinel or Sentinel()
        self.block_unsafe = block_unsafe

    def run(self, input_text: str, **kwargs) -> str:
        """
        Run agent with safety validation.

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

    def invoke(self, input_dict: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Invoke agent with safety validation (new LangChain interface).

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
            return {"output": f"Request blocked by Sentinel: {input_check['concerns']}"}

        # Run agent
        result = self.agent.invoke(input_dict, **kwargs)

        # Post-validate output
        output_text = result.get("output", str(result))
        is_safe, violations = self.sentinel.validate(output_text)
        if not is_safe and self.block_unsafe:
            return {"output": f"Response blocked by Sentinel: {violations}"}

        return result


def wrap_llm(
    llm: Any,
    seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
) -> Any:
    """
    Wrap a LangChain LLM with Sentinel seed injection.

    This modifies the LLM's system prompt to include the Sentinel seed.

    Args:
        llm: LangChain LLM instance
        seed_level: Which seed level to use

    Returns:
        Wrapped LLM with Sentinel seed

    Example:
        from langchain_openai import ChatOpenAI
        from sentinel.integrations.langchain import wrap_llm

        llm = ChatOpenAI()
        safe_llm = wrap_llm(llm, seed_level="standard")
    """
    sentinel = Sentinel(seed_level=seed_level)
    seed = sentinel.get_seed()

    # Check LLM type and wrap appropriately
    if hasattr(llm, 'bind'):
        # New LangChain interface
        return llm.bind(system_message=seed)
    elif hasattr(llm, 'system_message'):
        # Direct attribute
        llm.system_message = seed
        return llm
    else:
        # Fallback: add callback
        callback = SentinelCallback(sentinel=sentinel)
        if hasattr(llm, 'callbacks'):
            llm.callbacks = llm.callbacks or []
            llm.callbacks.append(callback)
        return llm


class SentinelChain:
    """
    A LangChain-compatible chain with built-in Sentinel safety.

    Example:
        from sentinel.integrations.langchain import SentinelChain

        chain = SentinelChain(
            llm=ChatOpenAI(),
            seed_level="standard"
        )
        result = chain.invoke("Help me with something")
    """

    def __init__(
        self,
        llm: Any,
        sentinel: Optional[Sentinel] = None,
        seed_level: Union[SeedLevel, str] = SeedLevel.STANDARD,
    ):
        self.llm = llm
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)

    def invoke(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """Run chain with safety."""
        # Pre-validate
        check = self.sentinel.validate_request(input_text)
        if not check["should_proceed"]:
            return {
                "output": None,
                "blocked": True,
                "reason": check["concerns"]
            }

        # Get seed and call LLM
        seed = self.sentinel.get_seed()
        messages = [
            {"role": "system", "content": seed},
            {"role": "user", "content": input_text}
        ]

        # Call based on LLM interface
        if hasattr(self.llm, 'invoke'):
            response = self.llm.invoke(messages, **kwargs)
            output = response.content if hasattr(response, 'content') else str(response)
        else:
            output = self.llm(messages, **kwargs)

        # Post-validate
        is_safe, violations = self.sentinel.validate(output)

        return {
            "output": output,
            "blocked": not is_safe,
            "violations": violations if not is_safe else None
        }
