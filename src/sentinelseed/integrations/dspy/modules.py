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

from typing import Any, Dict, List, Literal, Optional, Union
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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
)
from sentinelseed.validators.gates import THSPValidator

# Import constants and exceptions from package
from sentinelseed.integrations.dspy import (
    DEFAULT_MAX_TEXT_SIZE,
    DEFAULT_VALIDATION_TIMEOUT,
    VALID_MODES,
    VALID_PROVIDERS,
    TextTooLargeError,
    ValidationTimeoutError,
    InvalidParameterError,
)

logger = logging.getLogger("sentinelseed.integrations.dspy")


def _validate_mode(mode: str) -> str:
    """Validate mode parameter."""
    if mode not in VALID_MODES:
        raise InvalidParameterError("mode", mode, VALID_MODES)
    return mode


def _validate_provider(provider: str) -> str:
    """Validate provider parameter."""
    if provider not in VALID_PROVIDERS:
        raise InvalidParameterError("provider", provider, VALID_PROVIDERS)
    return provider


def _validate_text_size(content: str, max_size: int) -> None:
    """Validate text size is within limits."""
    size = len(content.encode("utf-8"))
    if size > max_size:
        raise TextTooLargeError(size, max_size)


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
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, block on validation errors (default: False)

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
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
    ):
        super().__init__()
        self.module = module
        self.output_field = output_field
        self.max_text_size = max_text_size
        self.timeout = timeout
        self.fail_closed = fail_closed

        # Validate parameters
        _validate_mode(mode)
        if provider and mode != "heuristic":
            _validate_provider(provider)

        self.mode = mode

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
        try:
            # Execute wrapped module
            result = self.module(**kwargs)

            # Get content to validate
            content = self._extract_content(result)

            # Validate text size
            _validate_text_size(content, self.max_text_size)

            # Validate content with timeout
            validation = self._validate_with_timeout(content)

            # Handle result based on mode
            return self._handle_result(result, validation)

        except TextTooLargeError:
            raise
        except ValidationTimeoutError:
            if self.fail_closed:
                return self._create_blocked_prediction(
                    "Validation timed out (fail_closed=True)"
                )
            raise
        except Exception as e:
            logger.error(f"Error in SentinelGuard.forward: {e}")
            if self.fail_closed:
                return self._create_blocked_prediction(f"Validation error: {e}")
            raise

    async def aforward(self, **kwargs) -> Prediction:
        """Async version of forward."""
        try:
            # Execute wrapped module (try async first)
            if hasattr(self.module, "aforward"):
                result = await self.module.aforward(**kwargs)
            elif hasattr(self.module, "acall"):
                result = await self.module.acall(**kwargs)
            else:
                result = self.module(**kwargs)

            # Get content to validate
            content = self._extract_content(result)

            # Validate text size
            _validate_text_size(content, self.max_text_size)

            # Validate content
            validation = await self._validate_async(content)

            # Handle result based on mode
            return self._handle_result(result, validation)

        except TextTooLargeError:
            raise
        except ValidationTimeoutError:
            if self.fail_closed:
                return self._create_blocked_prediction(
                    "Validation timed out (fail_closed=True)"
                )
            raise
        except Exception as e:
            logger.error(f"Error in SentinelGuard.aforward: {e}")
            if self.fail_closed:
                return self._create_blocked_prediction(f"Validation error: {e}")
            raise

    def _extract_content(self, result: Prediction) -> str:
        """Extract content from prediction for validation."""
        if self.output_field and hasattr(result, self.output_field):
            value = getattr(result, self.output_field)
            return str(value) if value is not None else ""

        # Try to find first string output using public API
        try:
            for key in result.keys():
                value = getattr(result, key, None)
                if value and isinstance(value, str):
                    return value
        except (AttributeError, TypeError):
            pass

        # Fallback: convert entire result to string
        return str(result)

    def _validate_with_timeout(self, content: str) -> Dict[str, Any]:
        """Run synchronous validation with timeout."""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._validate_sync, content)
            try:
                return future.result(timeout=self.timeout)
            except FuturesTimeoutError:
                raise ValidationTimeoutError(self.timeout, "sync validation")

    def _validate_sync(self, content: str) -> Dict[str, Any]:
        """Run synchronous validation."""
        try:
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
        except Exception as e:
            logger.error(f"Validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "gates": {},
                    "issues": [f"Validation error: {e}"],
                    "reasoning": f"Validation failed with error: {e}",
                    "method": "error",
                }
            # Fail open - assume safe if heuristic passed or error occurred
            return {
                "is_safe": True,
                "gates": {},
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
            }

    async def _validate_async(self, content: str) -> Dict[str, Any]:
        """Run asynchronous validation."""
        try:
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
        except Exception as e:
            logger.error(f"Async validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "gates": {},
                    "issues": [f"Validation error: {e}"],
                    "reasoning": f"Validation failed with error: {e}",
                    "method": "error",
                }
            return {
                "is_safe": True,
                "gates": {},
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
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
            return self._create_blocked_prediction(
                validation["reasoning"],
                validation["gates"],
                validation["issues"],
                validation["method"],
                result,
            )

        # mode == "flag": return original with safety metadata
        result.safety_blocked = False
        result.safety_issues = validation["issues"]
        return result

    def _create_blocked_prediction(
        self,
        reason: str,
        gates: Optional[Dict] = None,
        issues: Optional[List] = None,
        method: str = "error",
        original_result: Optional[Prediction] = None,
    ) -> Prediction:
        """Create a blocked prediction with safety metadata."""
        blocked = Prediction()
        blocked.safety_blocked = True
        blocked.safety_passed = False
        blocked.safety_gates = gates or {}
        blocked.safety_reasoning = reason
        blocked.safety_method = method
        blocked.safety_issues = issues or [reason]

        # Copy output fields with blocked message
        if original_result:
            try:
                for key in original_result.keys():
                    setattr(
                        blocked,
                        key,
                        "[BLOCKED BY SENTINEL: Content failed THSP safety validation]",
                    )
            except (AttributeError, TypeError):
                pass

        return blocked


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
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, block on validation errors (default: False)
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
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
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
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
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
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, block on validation errors (default: False)
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
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
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
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
        )

    def forward(self, **kwargs) -> Prediction:
        """Execute chain-of-thought with safety validation."""
        return self._guard.forward(**kwargs)

    async def aforward(self, **kwargs) -> Prediction:
        """Async chain-of-thought with safety validation."""
        return await self._guard.aforward(**kwargs)
