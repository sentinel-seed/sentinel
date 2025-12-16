"""
DSPy Modules for Sentinel THSP validation.

This module provides DSPy-compatible modules that integrate Sentinel's
THSP safety validation into DSPy pipelines.

Modules:
    - SentinelGuard: Wrapper that validates output of any DSPy module
    - SentinelPredict: Predict with built-in THSP validation
    - SentinelChainOfThought: ChainOfThought with THSP validation

Usage:
    import dspy
    from sentinelseed.integrations.dspy import SentinelGuard, SentinelPredict

    # Wrap any module with safety validation
    base_module = dspy.ChainOfThought("question -> answer")
    safe_module = SentinelGuard(base_module, api_key="sk-...")

    # Or use SentinelPredict directly
    safe_predict = SentinelPredict(
        "question -> answer",
        api_key="sk-...",
        provider="openai"
    )
"""

from typing import Any, Callable, Dict, List, Literal, Optional, Union
import logging

try:
    import dspy
    from dspy import Module, Prediction, Signature
except ImportError:
    raise ImportError(
        "dspy is required for this integration. "
        "Install with: pip install dspy"
    )

from sentinelseed.validators.semantic import (
    SemanticValidator,
    AsyncSemanticValidator,
    THSPResult,
    RiskLevel,
)
from sentinelseed.validators.gates import THSPValidator

logger = logging.getLogger("sentinelseed.integrations.dspy")


class SentinelGuard(Module):
    """
    DSPy module that wraps any other module and validates its output.

    The guard executes the wrapped module, then validates the output
    using Sentinel's THSP protocol. If validation fails, the output
    is either blocked or flagged depending on configuration.

    Args:
        module: The DSPy module to wrap
        api_key: API key for semantic validation (OpenAI or Anthropic)
        provider: LLM provider for validation ("openai" or "anthropic")
        model: Model to use for validation
        mode: How to handle unsafe content:
            - "block": Return error prediction if unsafe
            - "flag": Return original with safety metadata
            - "heuristic": Use pattern-based validation (no LLM)
        output_field: Which output field to validate (default: first field)

    Example:
        base = dspy.ChainOfThought("question -> answer")
        safe = SentinelGuard(base, api_key="sk-...", mode="block")
        result = safe(question="How do I hack a computer?")
        # Returns blocked response with safety_blocked=True
    """

    def __init__(
        self,
        module: Module,
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        output_field: Optional[str] = None,
    ):
        super().__init__()
        self.module = module
        self.mode = mode
        self.output_field = output_field

        # Initialize validator based on mode
        if mode == "heuristic":
            self._validator = THSPValidator()
            self._async_validator = None
        else:
            if not api_key:
                logger.warning(
                    "No API key provided for SentinelGuard. "
                    "Falling back to heuristic validation."
                )
                self._validator = THSPValidator()
                self._async_validator = None
                self.mode = "heuristic"
            else:
                self._validator = SemanticValidator(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                )
                self._async_validator = AsyncSemanticValidator(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                )

    def forward(self, **kwargs) -> Prediction:
        """
        Execute wrapped module and validate output.

        Returns a Prediction with additional safety metadata:
            - safety_passed: bool
            - safety_gates: dict of gate results
            - safety_reasoning: str (if semantic validation)
        """
        # Execute wrapped module
        result = self.module(**kwargs)

        # Get content to validate
        content = self._extract_content(result)

        # Validate content
        validation = self._validate_sync(content)

        # Handle result based on mode
        return self._handle_result(result, validation)

    async def aforward(self, **kwargs) -> Prediction:
        """Async version of forward."""
        # Execute wrapped module (try async first)
        if hasattr(self.module, 'aforward'):
            result = await self.module.acall(**kwargs)
        else:
            result = self.module(**kwargs)

        # Get content to validate
        content = self._extract_content(result)

        # Validate content
        validation = await self._validate_async(content)

        # Handle result based on mode
        return self._handle_result(result, validation)

    def _extract_content(self, result: Prediction) -> str:
        """Extract content from prediction for validation."""
        if self.output_field and hasattr(result, self.output_field):
            return str(getattr(result, self.output_field))

        # Try to find first string output
        for key in result._store.keys():
            if key not in ['_input_keys', '_demos']:
                value = getattr(result, key, None)
                if value and isinstance(value, str):
                    return value

        # Fallback: convert entire result to string
        return str(result)

    def _validate_sync(self, content: str) -> Dict[str, Any]:
        """Run synchronous validation."""
        if self.mode == "heuristic":
            result = self._validator.validate(content)
            return {
                "is_safe": result.get("safe", True),
                "gates": result.get("gates", {}),
                "issues": result.get("issues", []),
                "reasoning": "Heuristic pattern-based validation",
                "method": "heuristic",
            }
        else:
            result: THSPResult = self._validator.validate(content)
            return {
                "is_safe": result.is_safe,
                "gates": result.gate_results,
                "issues": result.failed_gates,
                "reasoning": result.reasoning,
                "method": "semantic",
            }

    async def _validate_async(self, content: str) -> Dict[str, Any]:
        """Run asynchronous validation."""
        if self.mode == "heuristic" or self._async_validator is None:
            return self._validate_sync(content)

        result: THSPResult = await self._async_validator.validate(content)
        return {
            "is_safe": result.is_safe,
            "gates": result.gate_results,
            "issues": result.failed_gates,
            "reasoning": result.reasoning,
            "method": "semantic",
        }

    def _handle_result(
        self, result: Prediction, validation: Dict[str, Any]
    ) -> Prediction:
        """Handle validation result based on mode."""
        # Add safety metadata to result
        result.safety_passed = validation["is_safe"]
        result.safety_gates = validation["gates"]
        result.safety_reasoning = validation["reasoning"]
        result.safety_method = validation["method"]

        if validation["is_safe"]:
            return result

        # Content is unsafe
        if self.mode == "block":
            # Return blocked prediction
            blocked = Prediction()
            blocked.safety_blocked = True
            blocked.safety_passed = False
            blocked.safety_gates = validation["gates"]
            blocked.safety_reasoning = validation["reasoning"]
            blocked.safety_method = validation["method"]
            blocked.safety_issues = validation["issues"]

            # Copy output fields with blocked message
            for key in result._store.keys():
                if key not in ['_input_keys', '_demos']:
                    setattr(blocked, key, "[BLOCKED BY SENTINEL: Content failed THSP safety validation]")

            return blocked

        # mode == "flag": return original with safety metadata
        result.safety_blocked = False
        result.safety_issues = validation["issues"]
        return result


class SentinelPredict(Module):
    """
    DSPy Predict module with built-in THSP safety validation.

    Combines prediction with automatic safety checking. The output
    is validated through THSP gates before being returned.

    Args:
        signature: DSPy signature (string or Signature class)
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model for validation (separate from prediction model)
        mode: Validation mode ("block", "flag", or "heuristic")
        **config: Additional config passed to dspy.Predict

    Example:
        predictor = SentinelPredict(
            "question -> answer",
            api_key="sk-...",
            mode="block"
        )
        result = predictor(question="What is 2+2?")
    """

    def __init__(
        self,
        signature: Union[str, type],
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        **config,
    ):
        super().__init__()
        self._predict = dspy.Predict(signature, **config)
        self._guard = SentinelGuard(
            self._predict,
            api_key=api_key,
            provider=provider,
            model=model,
            mode=mode,
        )

    def forward(self, **kwargs) -> Prediction:
        """Execute prediction with safety validation."""
        return self._guard.forward(**kwargs)

    async def aforward(self, **kwargs) -> Prediction:
        """Async prediction with safety validation."""
        return await self._guard.aforward(**kwargs)


class SentinelChainOfThought(Module):
    """
    DSPy ChainOfThought module with built-in THSP safety validation.

    Adds step-by-step reasoning before output, then validates
    the final answer through THSP gates.

    Args:
        signature: DSPy signature (string or Signature class)
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model for validation
        mode: Validation mode ("block", "flag", or "heuristic")
        **config: Additional config passed to dspy.ChainOfThought

    Example:
        cot = SentinelChainOfThought(
            "question -> answer",
            api_key="sk-...",
            mode="block"
        )
        result = cot(question="Explain quantum computing")
    """

    def __init__(
        self,
        signature: Union[str, type],
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        **config,
    ):
        super().__init__()
        self._cot = dspy.ChainOfThought(signature, **config)
        self._guard = SentinelGuard(
            self._cot,
            api_key=api_key,
            provider=provider,
            model=model,
            mode=mode,
        )

    def forward(self, **kwargs) -> Prediction:
        """Execute chain-of-thought with safety validation."""
        return self._guard.forward(**kwargs)

    async def aforward(self, **kwargs) -> Prediction:
        """Async chain-of-thought with safety validation."""
        return await self._guard.aforward(**kwargs)
