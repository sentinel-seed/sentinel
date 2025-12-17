"""
LangChain guard wrappers for Sentinel safety validation.

Provides:
- SentinelGuard: Wrap agents/chains with safety validation
"""

from typing import Any, Dict, List, Optional, Union

from sentinelseed import Sentinel, SeedLevel

from .utils import (
    DEFAULT_SEED_LEVEL,
    SentinelLogger,
    get_logger,
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
        self._logger = logger or get_logger()
        self._seed = self.sentinel.get_seed() if inject_seed else None

    def _validate_input(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Validate input, return block response if unsafe.

        Args:
            text: Input text to validate

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_input:
            return None

        try:
            check = self.sentinel.validate_request(text)
            if not check["should_proceed"] and self.block_unsafe:
                return {
                    "output": f"Request blocked by Sentinel: {check['concerns']}",
                    "sentinel_blocked": True,
                    "sentinel_reason": check["concerns"],
                }
        except Exception as e:
            self._logger.error(f"Error validating input: {e}")
            if self.block_unsafe:
                return {
                    "output": "Request blocked: validation error",
                    "sentinel_blocked": True,
                    "sentinel_reason": [str(e)],
                }

        return None

    def _validate_output(self, text: str, original: str = "") -> Optional[Dict[str, Any]]:
        """
        Validate output, return block response if unsafe.

        Args:
            text: Output text to validate
            original: Original output for reference

        Returns:
            Block response dict if unsafe, None if safe
        """
        if not self.validate_output:
            return None

        try:
            is_safe, violations = self.sentinel.validate(text)
            if not is_safe and self.block_unsafe:
                return {
                    "output": f"Response blocked by Sentinel: {violations}",
                    "sentinel_blocked": True,
                    "sentinel_reason": violations,
                    "original_output": original[:200] if original else None,
                }
        except Exception as e:
            self._logger.error(f"Error validating output: {e}")
            if self.block_unsafe:
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
        """Async version of invoke."""
        if isinstance(input_dict, str):
            input_dict = {"input": input_dict}

        input_text = input_dict.get("input", str(input_dict))

        block_response = self._validate_input(input_text)
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

        block_response = self._validate_output(output_text, output_text)
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
