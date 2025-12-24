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

try:
    import dspy
    from dspy import Module, Prediction
except (ImportError, AttributeError):
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

# Import from centralized utils
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
        allow_heuristic_fallback: If True, allow fallback to heuristic when
            no API key is provided. If False (default), raise HeuristicFallbackError.
        context: Optional context string to include in validation (e.g., conversation
            history, system prompt, agent state). Helps validator understand intent.

    Safety Metadata:
        Results include degradation flags to distinguish validated from degraded:
        - safety_degraded: True if validation was degraded (error/timeout/fallback)
        - safety_confidence: "none", "low", "medium", or "high"

    Example:
        base = dspy.ChainOfThought("question -> answer")
        safe = SentinelGuard(base, api_key="sk-...", mode="block")
        result = safe(question="How do I hack a computer?")
        # Returns blocked response with safety_blocked=True

        # With context for better understanding
        safe = SentinelGuard(
            base,
            api_key="sk-...",
            context="User is a cybersecurity professional doing authorized testing"
        )
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
        allow_heuristic_fallback: bool = False,
        context: Optional[str] = None,
    ):
        super().__init__()

        # Validate configuration types
        validate_config_types(
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
        )

        # Validate mode parameter
        validate_mode(mode)

        # Validate provider if using semantic validation
        if provider and mode != "heuristic":
            validate_provider(provider)

        self.module = module
        self.output_field = output_field
        self.max_text_size = max_text_size
        self.timeout = timeout
        self.fail_closed = fail_closed
        self.mode = mode
        self.allow_heuristic_fallback = allow_heuristic_fallback
        self.context = context
        self._is_degraded_mode = False  # Track if we fell back to heuristic
        self._logger = logger

        # Log warning about fail-open default
        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelGuard")

        # Initialize validator based on mode
        if mode == "heuristic":
            self._validator = THSPValidator()
            self._async_validator = None
        else:
            if not api_key:
                # Check if fallback is allowed
                if not allow_heuristic_fallback:
                    raise HeuristicFallbackError("SentinelGuard")

                # Emit prominent warning about degraded mode
                self._logger.warning(
                    "\n" + "=" * 60 + "\n"
                    "SENTINEL DEGRADED MODE WARNING\n"
                    "=" * 60 + "\n"
                    "No API key provided for SentinelGuard.\n"
                    "Falling back to HEURISTIC validation (~50% accuracy).\n"
                    "This significantly reduces safety detection capability.\n"
                    "\n"
                    "To enable full semantic validation:\n"
                    "  - Provide api_key parameter, OR\n"
                    "  - Set allow_heuristic_fallback=False to require API key\n"
                    "=" * 60
                )
                self._validator = THSPValidator()
                self._async_validator = None
                self.mode = "heuristic"
                self._is_degraded_mode = True  # Mark as degraded
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
            validate_text_size(content, self.max_text_size)

            # Validate content with timeout using shared executor
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
            self._logger.error(f"Error in SentinelGuard.forward: {e}")
            if self.fail_closed:
                return self._create_blocked_prediction(f"Validation error: {e}")
            raise

    async def aforward(self, **kwargs) -> Prediction:
        """Async version of forward."""
        try:
            # Execute wrapped module (try async first)
            # Check if aforward is defined in the module's class (not just inherited)
            module_cls = type(self.module)
            has_own_aforward = 'aforward' in module_cls.__dict__ or \
                any('aforward' in base.__dict__ for base in module_cls.__mro__[1:]
                    if hasattr(base, '__dict__') and base.__name__ != 'Module')

            if has_own_aforward:
                result = await self.module.aforward(**kwargs)
            else:
                result = self.module(**kwargs)  # Fallback to sync for custom modules

            # Get content to validate
            content = self._extract_content(result)

            # Validate text size
            validate_text_size(content, self.max_text_size)

            # Validate content with timeout using shared executor
            validation = await self._validate_async_with_timeout(content)

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
            self._logger.error(f"Error in SentinelGuard.aforward: {e}")
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
        """Run synchronous validation with timeout using shared executor."""
        executor = get_validation_executor()
        return executor.run_with_timeout(
            self._validate_sync,
            args=(content,),
            timeout=self.timeout,
        )

    async def _validate_async_with_timeout(self, content: str) -> Dict[str, Any]:
        """Run async validation with timeout using shared executor."""
        # Use run_with_timeout_async for async validation with proper timeout
        return await run_with_timeout_async(
            self._validate_sync,
            args=(content,),
            timeout=self.timeout,
        )

    def _validate_sync(self, content: str, context: Optional[str] = None) -> Dict[str, Any]:
        """Run synchronous validation with optional context."""
        try:
            # Build content with context if provided
            effective_context = context or self.context
            if effective_context:
                content_with_context = f"Context: {effective_context}\n\nContent to validate:\n{content}"
            else:
                content_with_context = content

            if self.mode == "heuristic":
                result = self._validator.validate(content_with_context)
                # Heuristic mode: low confidence, degraded if it was a fallback
                return {
                    "is_safe": result.get("safe", True),
                    "gates": result.get("gates", {}),
                    "issues": result.get("issues", []),
                    "reasoning": "Heuristic pattern-based validation",
                    "method": "heuristic",
                    "degraded": self._is_degraded_mode,
                    "confidence": CONFIDENCE_LOW,
                    "context_used": effective_context is not None,
                }
            else:
                result: THSPResult = self._validator.validate(content_with_context)
                # Semantic mode: high confidence, not degraded
                return {
                    "is_safe": result.is_safe,
                    "gates": result.gate_results,
                    "issues": result.failed_gates,
                    "reasoning": result.reasoning,
                    "method": "semantic",
                    "degraded": False,
                    "confidence": CONFIDENCE_HIGH,
                    "context_used": effective_context is not None,
                }
        except Exception as e:
            self._logger.error(f"Validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "gates": {},
                    "issues": [f"Validation error: {e}"],
                    "reasoning": f"Validation failed with error: {e}",
                    "method": "error",
                    "degraded": True,
                    "confidence": CONFIDENCE_NONE,
                    "context_used": False,
                }
            # Fail open - assume safe but mark as degraded with no confidence
            return {
                "is_safe": True,
                "gates": {},
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
                "degraded": True,
                "confidence": CONFIDENCE_NONE,
                "context_used": False,
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
        # Add degradation flags
        result.safety_degraded = validation.get("degraded", False)
        result.safety_confidence = validation.get("confidence", CONFIDENCE_HIGH)

        if validation["is_safe"]:
            return result

        # Content is unsafe
        if self.mode == "block":
            return self._create_blocked_prediction(
                validation["reasoning"],
                validation["gates"],
                validation["issues"],
                validation["method"],
                validation.get("degraded", False),
                validation.get("confidence", CONFIDENCE_NONE),
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
        degraded: bool = False,
        confidence: str = CONFIDENCE_NONE,
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
        blocked.safety_degraded = degraded
        blocked.safety_confidence = confidence

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
        allow_heuristic_fallback: If True, allow fallback to heuristic (default: False)
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
        allow_heuristic_fallback: bool = False,
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
            allow_heuristic_fallback=allow_heuristic_fallback,
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

    Validates BOTH the reasoning process AND the final output, ensuring
    that harmful content cannot hide in either component.

    Args:
        signature: DSPy signature (string or Signature class)
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model for validation
        mode: Validation mode ("block", "flag", or "heuristic")
        validate_reasoning: Whether to validate reasoning (default: True)
        validate_output: Whether to validate output (default: True)
        reasoning_field: Name of reasoning field (default: "reasoning")
        max_text_size: Maximum text size in bytes (default: 50KB)
        timeout: Validation timeout in seconds (default: 30.0)
        fail_closed: If True, block on validation errors (default: False)
        allow_heuristic_fallback: If True, allow fallback to heuristic (default: False)
        **config: Additional config passed to dspy.ChainOfThought

    Safety Metadata:
        Results include degradation flags:
        - safety_degraded: True if validation was degraded
        - safety_confidence: "none", "low", "medium", or "high"

    Example:
        cot = SentinelChainOfThought(
            "question -> answer",
            api_key="sk-...",
            mode="block",
            validate_reasoning=True,  # Validate reasoning too
        )
        result = cot(question="Explain quantum computing")

        # Check which fields were validated
        print(result.safety_fields_validated)  # ["reasoning", "answer"]
        print(result.safety_field_results)     # {"reasoning": True, "answer": True}
    """

    def __init__(
        self,
        signature: Union[str, type],
        api_key: Optional[str] = None,
        provider: str = "openai",
        model: Optional[str] = None,
        mode: Literal["block", "flag", "heuristic"] = "block",
        validate_reasoning: bool = True,
        validate_output: bool = True,
        reasoning_field: str = "reasoning",
        max_text_size: int = DEFAULT_MAX_TEXT_SIZE,
        timeout: float = DEFAULT_VALIDATION_TIMEOUT,
        fail_closed: bool = False,
        allow_heuristic_fallback: bool = False,
        **config,
    ):
        super().__init__()

        # Validate configuration types
        validate_config_types(
            max_text_size=max_text_size,
            timeout=timeout,
            fail_closed=fail_closed,
        )

        # Validate mode parameter
        validate_mode(mode)

        # Validate provider if using semantic validation
        if provider and mode != "heuristic":
            validate_provider(provider)

        self._cot = dspy.ChainOfThought(signature, **config)
        self.validate_reasoning = validate_reasoning
        self.validate_output = validate_output
        self.reasoning_field = reasoning_field
        self.max_text_size = max_text_size
        self.timeout = timeout
        self.fail_closed = fail_closed
        self.mode = mode
        self.allow_heuristic_fallback = allow_heuristic_fallback
        self._is_degraded_mode = False
        self._logger = logger

        # Log warning about fail-open default
        if not fail_closed:
            warn_fail_open_default(self._logger, "SentinelChainOfThought")

        # Initialize validator based on mode
        if mode == "heuristic":
            self._validator = THSPValidator()
        else:
            if not api_key:
                # Check if fallback is allowed
                if not allow_heuristic_fallback:
                    raise HeuristicFallbackError("SentinelChainOfThought")

                # Emit prominent warning about degraded mode
                self._logger.warning(
                    "\n" + "=" * 60 + "\n"
                    "SENTINEL DEGRADED MODE WARNING\n"
                    "=" * 60 + "\n"
                    "No API key provided for SentinelChainOfThought.\n"
                    "Falling back to HEURISTIC validation (~50% accuracy).\n"
                    "This significantly reduces safety detection capability.\n"
                    "\n"
                    "To enable full semantic validation:\n"
                    "  - Provide api_key parameter, OR\n"
                    "  - Set allow_heuristic_fallback=False to require API key\n"
                    "=" * 60
                )
                self._validator = THSPValidator()
                self.mode = "heuristic"
                self._is_degraded_mode = True
            else:
                self._validator = SemanticValidator(
                    provider=provider,
                    model=model,
                    api_key=api_key,
                )

    def _extract_fields(self, result: Prediction) -> Dict[str, str]:
        """
        Extract reasoning and output fields from prediction.

        Returns:
            Dict mapping field names to their content
        """
        fields = {}

        # Extract reasoning field
        if self.validate_reasoning:
            reasoning = getattr(result, self.reasoning_field, None)
            if reasoning and isinstance(reasoning, str):
                fields[self.reasoning_field] = reasoning

        # Extract output fields (all string fields except reasoning)
        if self.validate_output:
            try:
                for key in result.keys():
                    if key == self.reasoning_field:
                        continue
                    value = getattr(result, key, None)
                    if value and isinstance(value, str):
                        fields[key] = value
            except (AttributeError, TypeError):
                pass

        return fields

    def _validate_content(self, content: str) -> Dict[str, Any]:
        """Validate a single piece of content."""
        try:
            if self.mode == "heuristic":
                result = self._validator.validate(content)
                return {
                    "is_safe": result.get("safe", True),
                    "gates": result.get("gates", {}),
                    "issues": result.get("issues", []),
                    "reasoning": "Heuristic pattern-based validation",
                    "method": "heuristic",
                    "degraded": self._is_degraded_mode,
                    "confidence": CONFIDENCE_LOW,
                }
            else:
                result: THSPResult = self._validator.validate(content)
                return {
                    "is_safe": result.is_safe,
                    "gates": result.gate_results,
                    "issues": result.failed_gates,
                    "reasoning": result.reasoning,
                    "method": "semantic",
                    "degraded": False,
                    "confidence": CONFIDENCE_HIGH,
                }
        except Exception as e:
            self._logger.error(f"Validation error: {e}")
            if self.fail_closed:
                return {
                    "is_safe": False,
                    "gates": {},
                    "issues": [f"Validation error: {e}"],
                    "reasoning": f"Validation failed with error: {e}",
                    "method": "error",
                    "degraded": True,
                    "confidence": CONFIDENCE_NONE,
                }
            return {
                "is_safe": True,
                "gates": {},
                "issues": [],
                "reasoning": f"Validation error (fail_open): {e}",
                "method": "error",
                "degraded": True,
                "confidence": CONFIDENCE_NONE,
            }

    def _validate_all_fields(self, fields: Dict[str, str]) -> Dict[str, Any]:
        """
        Validate all extracted fields.

        Returns:
            Combined validation result with per-field details
        """
        executor = get_validation_executor()
        field_results = {}
        all_issues = []
        all_gates = {}
        all_safe = True
        failed_fields = []
        method = "heuristic"
        any_degraded = False
        worst_confidence = CONFIDENCE_HIGH

        for field_name, content in fields.items():
            # Validate text size
            try:
                validate_text_size(content, self.max_text_size)
            except TextTooLargeError as e:
                field_results[field_name] = {
                    "is_safe": False,
                    "error": str(e),
                    "degraded": True,
                    "confidence": CONFIDENCE_NONE,
                }
                all_safe = False
                any_degraded = True
                worst_confidence = CONFIDENCE_NONE
                failed_fields.append(field_name)
                all_issues.append(f"{field_name}: {e}")
                continue

            # Validate content with timeout
            try:
                result = executor.run_with_timeout(
                    self._validate_content,
                    args=(content,),
                    timeout=self.timeout,
                )
            except ValidationTimeoutError:
                any_degraded = True
                worst_confidence = CONFIDENCE_NONE
                if self.fail_closed:
                    field_results[field_name] = {
                        "is_safe": False,
                        "error": "Validation timed out",
                        "degraded": True,
                        "confidence": CONFIDENCE_NONE,
                    }
                    all_safe = False
                    failed_fields.append(field_name)
                    all_issues.append(f"{field_name}: Validation timed out")
                else:
                    field_results[field_name] = {
                        "is_safe": True,
                        "error": "Timeout (fail_open)",
                        "degraded": True,
                        "confidence": CONFIDENCE_NONE,
                    }
                continue

            field_results[field_name] = result
            method = result.get("method", method)

            # Track degradation
            if result.get("degraded", False):
                any_degraded = True
            # Track worst confidence
            field_confidence = result.get("confidence", CONFIDENCE_HIGH)
            if field_confidence == CONFIDENCE_NONE:
                worst_confidence = CONFIDENCE_NONE
            elif field_confidence == CONFIDENCE_LOW and worst_confidence != CONFIDENCE_NONE:
                worst_confidence = CONFIDENCE_LOW

            if not result["is_safe"]:
                all_safe = False
                failed_fields.append(field_name)
                # Prefix issues with field name for clarity
                for issue in result.get("issues", []):
                    all_issues.append(f"{field_name}: {issue}")

            # Merge gates (prefix with field name)
            for gate, value in result.get("gates", {}).items():
                all_gates[f"{field_name}.{gate}"] = value

        return {
            "is_safe": all_safe,
            "gates": all_gates,
            "issues": all_issues,
            "failed_fields": failed_fields,
            "field_results": field_results,
            "fields_validated": list(fields.keys()),
            "reasoning": self._build_reasoning(field_results, failed_fields),
            "method": method,
            "degraded": any_degraded,
            "confidence": worst_confidence,
        }

    def _build_reasoning(
        self, field_results: Dict[str, Any], failed_fields: List[str]
    ) -> str:
        """Build a human-readable reasoning summary."""
        if not failed_fields:
            validated = list(field_results.keys())
            return f"All fields passed validation: {', '.join(validated)}"

        parts = []
        for field in failed_fields:
            result = field_results.get(field, {})
            if "error" in result:
                parts.append(f"{field}: {result['error']}")
            else:
                reasoning = result.get("reasoning", "Unknown issue")
                parts.append(f"{field}: {reasoning}")

        return f"Validation failed for: {'; '.join(parts)}"

    def _handle_result(
        self, result: Prediction, validation: Dict[str, Any]
    ) -> Prediction:
        """Handle validation result based on mode."""
        # Add safety metadata to result
        result.safety_passed = validation["is_safe"]
        result.safety_gates = validation["gates"]
        result.safety_reasoning = validation["reasoning"]
        result.safety_method = validation["method"]
        result.safety_fields_validated = validation["fields_validated"]
        result.safety_field_results = {
            k: v.get("is_safe", True) for k, v in validation["field_results"].items()
        }
        result.safety_failed_fields = validation["failed_fields"]
        # Add degradation flags
        result.safety_degraded = validation.get("degraded", False)
        result.safety_confidence = validation.get("confidence", CONFIDENCE_HIGH)

        if validation["is_safe"]:
            return result

        # Content is unsafe
        if self.mode == "block":
            return self._create_blocked_prediction(
                validation["reasoning"],
                validation["gates"],
                validation["issues"],
                validation["method"],
                validation["failed_fields"],
                validation["fields_validated"],
                validation.get("degraded", False),
                validation.get("confidence", CONFIDENCE_NONE),
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
        failed_fields: Optional[List] = None,
        fields_validated: Optional[List] = None,
        degraded: bool = False,
        confidence: str = CONFIDENCE_NONE,
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
        blocked.safety_failed_fields = failed_fields or []
        blocked.safety_fields_validated = fields_validated or []
        blocked.safety_field_results = {}
        blocked.safety_degraded = degraded
        blocked.safety_confidence = confidence

        # Copy output fields with blocked message
        if original_result:
            try:
                for key in original_result.keys():
                    if key in (failed_fields or []):
                        setattr(
                            blocked,
                            key,
                            f"[BLOCKED BY SENTINEL: {key} failed THSP safety validation]",
                        )
                    else:
                        # Keep safe fields as-is
                        setattr(blocked, key, getattr(original_result, key))
            except (AttributeError, TypeError):
                pass

        return blocked

    def forward(self, **kwargs) -> Prediction:
        """
        Execute chain-of-thought with safety validation of reasoning AND output.

        Returns a Prediction with additional safety metadata:
            - safety_passed: bool (True only if ALL fields pass)
            - safety_gates: dict of gate results (prefixed with field name)
            - safety_reasoning: str
            - safety_fields_validated: list of validated field names
            - safety_field_results: dict mapping field names to pass/fail
            - safety_failed_fields: list of fields that failed validation
        """
        try:
            # Execute chain-of-thought
            result = self._cot(**kwargs)

            # Extract fields to validate
            fields = self._extract_fields(result)

            if not fields:
                self._logger.warning("No fields extracted for validation")
                result.safety_passed = True
                result.safety_fields_validated = []
                result.safety_field_results = {}
                result.safety_failed_fields = []
                result.safety_reasoning = "No content to validate"
                result.safety_method = "none"
                result.safety_gates = {}
                return result

            # Validate all fields
            validation = self._validate_all_fields(fields)

            # Handle result based on mode
            return self._handle_result(result, validation)

        except TextTooLargeError:
            raise
        except ValidationTimeoutError:
            if self.fail_closed:
                blocked = Prediction()
                blocked.safety_blocked = True
                blocked.safety_passed = False
                blocked.safety_reasoning = "Validation timed out (fail_closed=True)"
                return blocked
            raise
        except Exception as e:
            self._logger.error(f"Error in SentinelChainOfThought.forward: {e}")
            if self.fail_closed:
                blocked = Prediction()
                blocked.safety_blocked = True
                blocked.safety_passed = False
                blocked.safety_reasoning = f"Validation error: {e}"
                return blocked
            raise

    async def aforward(self, **kwargs) -> Prediction:
        """Async version of forward."""
        try:
            # Execute chain-of-thought (try async first)
            # Check if aforward is defined in the module's class (not just inherited)
            cot_cls = type(self._cot)
            has_own_aforward = 'aforward' in cot_cls.__dict__ or \
                any('aforward' in base.__dict__ for base in cot_cls.__mro__[1:]
                    if hasattr(base, '__dict__') and base.__name__ != 'Module')

            if has_own_aforward:
                result = await self._cot.aforward(**kwargs)
            else:
                result = self._cot(**kwargs)  # Fallback to sync for custom modules

            # Extract fields to validate
            fields = self._extract_fields(result)

            if not fields:
                self._logger.warning("No fields extracted for validation")
                result.safety_passed = True
                result.safety_fields_validated = []
                result.safety_field_results = {}
                result.safety_failed_fields = []
                result.safety_reasoning = "No content to validate"
                result.safety_method = "none"
                result.safety_gates = {}
                return result

            # Validate all fields (using sync validation in thread pool)
            validation = await run_with_timeout_async(
                self._validate_all_fields,
                args=(fields,),
                timeout=self.timeout * len(fields),  # Scale timeout by number of fields
            )

            # Handle result based on mode
            return self._handle_result(result, validation)

        except TextTooLargeError:
            raise
        except ValidationTimeoutError:
            if self.fail_closed:
                blocked = Prediction()
                blocked.safety_blocked = True
                blocked.safety_passed = False
                blocked.safety_reasoning = "Validation timed out (fail_closed=True)"
                return blocked
            raise
        except Exception as e:
            self._logger.error(f"Error in SentinelChainOfThought.aforward: {e}")
            if self.fail_closed:
                blocked = Prediction()
                blocked.safety_blocked = True
                blocked.safety_passed = False
                blocked.safety_reasoning = f"Validation error: {e}"
                return blocked
            raise
