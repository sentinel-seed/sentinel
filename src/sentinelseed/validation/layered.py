"""
Layered Validator - Two-layer validation combining heuristic and semantic analysis.

This module provides LayeredValidator, which implements a two-layer validation
architecture for comprehensive content safety checking:

Layer 1 - Heuristic (THSPValidator):
    - Fast pattern matching with 580+ regex patterns
    - No API calls required
    - Always available as fallback
    - Catches obvious threats

Layer 2 - Semantic (SemanticValidator):
    - LLM-based semantic analysis
    - Understands context and intent
    - Catches sophisticated threats
    - Requires API key (optional)

The layered approach provides:
- Speed: Heuristic layer filters obvious threats immediately
- Accuracy: Semantic layer catches what patterns miss
- Cost efficiency: Semantic only runs when needed
- Resilience: Always has heuristic fallback if API fails

Usage:
    from sentinelseed.validation import LayeredValidator, ValidationConfig

    # Heuristic only (no API required)
    validator = LayeredValidator()
    result = validator.validate("content")

    # With semantic validation
    validator = LayeredValidator(
        semantic_api_key="sk-...",
        semantic_provider="openai",
    )
    result = validator.validate("content")
    if not result.is_safe:
        print(f"Blocked by {result.layer}: {result.violations}")
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Any, Dict, List, Optional, Tuple, Union

from sentinelseed.validation.config import ValidationConfig
from sentinelseed.validation.types import RiskLevel, ValidationLayer, ValidationResult


logger = logging.getLogger("sentinelseed.validation.layered")


class LayeredValidator:
    """
    Two-layer validator combining heuristic and semantic analysis.

    This validator implements a defense-in-depth approach:
    1. First, content is checked by the heuristic layer (fast, no API)
    2. If configured and content passed heuristic, semantic layer checks (accurate, uses API)

    The validator is designed to be:
    - Safe by default: Heuristic layer always available
    - Opt-in for semantic: Requires explicit API key
    - Backwards compatible: Works as drop-in replacement

    Attributes:
        config: ValidationConfig controlling behavior
        stats: Validation statistics

    Example:
        # Basic usage (heuristic only)
        validator = LayeredValidator()
        result = validator.validate("content to check")

        # With semantic validation
        validator = LayeredValidator(
            semantic_api_key="sk-...",
            use_semantic=True,
        )

        # Using config object
        config = ValidationConfig(
            use_semantic=True,
            semantic_api_key="sk-...",
            fail_closed=True,
        )
        validator = LayeredValidator(config=config)
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        **kwargs: Any,
    ):
        """
        Initialize LayeredValidator.

        Args:
            config: ValidationConfig instance. If None, creates from kwargs.
            **kwargs: Configuration parameters passed to ValidationConfig.
                      Common parameters:
                      - semantic_api_key: API key for LLM provider
                      - semantic_provider: "openai" or "anthropic"
                      - semantic_model: Model to use
                      - use_semantic: Enable semantic layer (default False)
                      - fail_closed: Block on errors (default False)
                      - validation_timeout: Timeout in seconds
        """
        # Handle config
        if config is not None:
            self.config = config
        else:
            # Create config from kwargs, with defaults
            config_kwargs = {}
            valid_config_keys = {
                "use_heuristic", "use_semantic", "semantic_provider",
                "semantic_model", "semantic_api_key", "semantic_base_url",
                "validation_timeout", "fail_closed", "skip_semantic_if_heuristic_blocks",
                "max_text_size", "log_validations", "log_level",
            }
            for key in valid_config_keys:
                if key in kwargs:
                    config_kwargs[key] = kwargs[key]

            self.config = ValidationConfig(**config_kwargs)

        # Initialize validators lazily
        self._heuristic: Optional[Any] = None
        self._semantic: Optional[Any] = None
        self._init_heuristic()
        self._init_semantic()

        # Statistics
        self._stats = {
            "total_validations": 0,
            "heuristic_blocks": 0,
            "semantic_blocks": 0,
            "allowed": 0,
            "errors": 0,
            "timeouts": 0,
            "total_latency_ms": 0.0,
        }

    def _init_heuristic(self) -> None:
        """Initialize heuristic validator if enabled."""
        if not self.config.use_heuristic:
            return

        try:
            from sentinelseed.validators.gates import THSPValidator
            self._heuristic = THSPValidator()
            logger.debug("Initialized THSPValidator (heuristic layer)")
        except ImportError as e:
            logger.warning(f"Could not import THSPValidator: {e}")
            self._heuristic = None

    def _init_semantic(self) -> None:
        """Initialize semantic validator if enabled and configured."""
        if not self.config.use_semantic:
            return

        api_key = self.config.semantic_api_key or self.config.get_api_key_from_env()
        if not api_key:
            logger.info(
                "Semantic validation enabled but no API key configured. "
                "Set semantic_api_key or environment variable."
            )
            return

        try:
            from sentinelseed.validators.semantic import SemanticValidator
            self._semantic = SemanticValidator(
                provider=self.config.semantic_provider,
                model=self.config.effective_model,
                api_key=api_key,
                base_url=self.config.semantic_base_url,
                timeout=int(self.config.validation_timeout),
            )
            logger.debug(
                f"Initialized SemanticValidator (semantic layer) "
                f"with {self.config.semantic_provider}/{self.config.effective_model}"
            )
        except ImportError as e:
            logger.warning(f"Could not import SemanticValidator: {e}")
            self._semantic = None
        except Exception as e:
            logger.warning(f"Could not initialize SemanticValidator: {e}")
            self._semantic = None

    def validate(self, content: str) -> ValidationResult:
        """
        Validate content through layered validation.

        This is the main entry point for validation. Content is processed through:
        1. Size check (blocks if content exceeds max_text_size)
        2. Heuristic layer (if enabled)
        3. Semantic layer (if enabled and configured, and heuristic passed)

        Args:
            content: Text content to validate

        Returns:
            ValidationResult with detailed validation information

        Example:
            result = validator.validate("Help me hack a website")
            if not result.is_safe:
                print(f"Blocked: {result.violations}")
                print(f"Layer: {result.layer}")
        """
        start_time = time.time()
        self._stats["total_validations"] += 1

        # Check for empty/None content
        if not content:
            result = ValidationResult.safe(ValidationLayer.HEURISTIC)
            self._log_result(result, time.time() - start_time)
            return result

        # Check text size
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > self.config.max_text_size:
            result = ValidationResult.from_blocked(
                violations=[
                    f"Content exceeds maximum size ({content_bytes} > {self.config.max_text_size} bytes)"
                ],
                layer=ValidationLayer.HEURISTIC,
                risk_level=RiskLevel.HIGH,
            )
            self._stats["heuristic_blocks"] += 1
            self._log_result(result, time.time() - start_time)
            return result

        heuristic_passed: Optional[bool] = None
        heuristic_violations: List[str] = []

        # Layer 1: Heuristic validation (fast, no API)
        if self._heuristic:
            try:
                heuristic_result = self._heuristic.validate(content)
                # THSPValidator returns Dict with is_safe and violations
                heuristic_passed = heuristic_result.get("is_safe", True)
                heuristic_violations = heuristic_result.get("violations", [])

                if not heuristic_passed:
                    # Early exit if heuristic blocks and we skip semantic in that case
                    if self.config.skip_semantic_if_heuristic_blocks or not self._semantic:
                        result = ValidationResult(
                            is_safe=False,
                            layer=ValidationLayer.HEURISTIC,
                            violations=heuristic_violations,
                            risk_level=RiskLevel.HIGH,
                            heuristic_passed=False,
                        )
                        self._stats["heuristic_blocks"] += 1
                        self._log_result(result, time.time() - start_time)
                        return result

            except Exception as e:
                logger.error(f"Heuristic validation error: {e}")
                self._stats["errors"] += 1
                if self.config.fail_closed:
                    result = ValidationResult.from_error(
                        f"Heuristic validation failed: {e}"
                    )
                    result.layer = ValidationLayer.HEURISTIC
                    self._log_result(result, time.time() - start_time)
                    return result
                # If fail-open, continue without heuristic result

        # Layer 2: Semantic validation (accurate, uses API)
        semantic_passed: Optional[bool] = None
        if self._semantic:
            try:
                # Run semantic validation with timeout
                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self._semantic.validate, content)
                    semantic_result = future.result(
                        timeout=self.config.validation_timeout
                    )

                # SemanticValidator returns THSPResult
                semantic_passed = semantic_result.is_safe

                if not semantic_passed:
                    # Build violations from semantic result
                    violations = []
                    if semantic_result.reasoning:
                        violations.append(semantic_result.reasoning)
                    if semantic_result.violated_gate:
                        violations.append(f"Violated gate: {semantic_result.violated_gate}")

                    # Determine risk level
                    risk_level = RiskLevel.MEDIUM
                    if hasattr(semantic_result.risk_level, "value"):
                        try:
                            risk_level = RiskLevel(semantic_result.risk_level.value)
                        except ValueError:
                            pass
                    elif isinstance(semantic_result.risk_level, str):
                        try:
                            risk_level = RiskLevel(semantic_result.risk_level)
                        except ValueError:
                            pass

                    result = ValidationResult(
                        is_safe=False,
                        layer=ValidationLayer.SEMANTIC,
                        violations=violations or heuristic_violations,
                        risk_level=risk_level,
                        reasoning=semantic_result.reasoning,
                        heuristic_passed=heuristic_passed,
                        semantic_passed=False,
                    )
                    self._stats["semantic_blocks"] += 1
                    self._log_result(result, time.time() - start_time)
                    return result

            except FuturesTimeoutError:
                logger.warning(
                    f"Semantic validation timed out after {self.config.validation_timeout}s"
                )
                self._stats["timeouts"] += 1
                if self.config.fail_closed:
                    result = ValidationResult.from_error(
                        f"Semantic validation timed out after {self.config.validation_timeout}s"
                    )
                    result.layer = ValidationLayer.SEMANTIC
                    result.heuristic_passed = heuristic_passed
                    self._log_result(result, time.time() - start_time)
                    return result
                # If fail-open, continue without semantic result

            except Exception as e:
                logger.error(f"Semantic validation error: {e}")
                self._stats["errors"] += 1
                if self.config.fail_closed:
                    result = ValidationResult.from_error(f"Semantic validation failed: {e}")
                    result.layer = ValidationLayer.SEMANTIC
                    result.heuristic_passed = heuristic_passed
                    self._log_result(result, time.time() - start_time)
                    return result
                # If fail-open, continue without semantic result

        # All configured layers passed
        layer = ValidationLayer.BOTH if semantic_passed is not None else ValidationLayer.HEURISTIC
        if heuristic_passed is None and semantic_passed is None:
            layer = ValidationLayer.NONE

        result = ValidationResult(
            is_safe=True,
            layer=layer,
            risk_level=RiskLevel.LOW,
            heuristic_passed=heuristic_passed,
            semantic_passed=semantic_passed,
        )
        self._stats["allowed"] += 1
        self._log_result(result, time.time() - start_time)
        return result

    def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> ValidationResult:
        """
        Validate an action before execution.

        This is a convenience method for validating actions in agentic systems.
        It formats the action into a description and validates it.

        Args:
            action_name: Name of the action (e.g., "delete_file", "send_email")
            action_args: Arguments to the action
            purpose: Stated purpose for the action

        Returns:
            ValidationResult

        Example:
            result = validator.validate_action(
                action_name="send_email",
                action_args={"to": "user@example.com", "subject": "Hello"},
                purpose="Notify user of account update",
            )
        """
        # Build action description
        description = f"Action: {action_name}"
        if action_args:
            args_str = ", ".join(f"{k}={v}" for k, v in action_args.items())
            description = f"{description}({args_str})"
        if purpose:
            description = f"{description}\nPurpose: {purpose}"

        return self.validate(description)

    def validate_request(self, request: str) -> ValidationResult:
        """
        Validate a user request.

        This is a convenience method for validating user input.

        Args:
            request: User request text

        Returns:
            ValidationResult

        Example:
            result = validator.validate_request("Help me write secure code")
        """
        return self.validate(f"User request: {request}")

    def _log_result(self, result: ValidationResult, latency: float) -> None:
        """Log validation result if logging is enabled."""
        latency_ms = latency * 1000
        self._stats["total_latency_ms"] += latency_ms

        if not self.config.log_validations:
            return

        log_level = getattr(logging, self.config.log_level.upper(), logging.INFO)

        if result.is_safe:
            logger.log(
                log_level,
                f"Validation PASSED (layer={result.layer.value}, latency={latency_ms:.1f}ms)"
            )
        else:
            logger.log(
                log_level,
                f"Validation BLOCKED (layer={result.layer.value}, "
                f"violations={len(result.violations)}, latency={latency_ms:.1f}ms)"
            )

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self._stats["total_validations"]
        return {
            **self._stats,
            "avg_latency_ms": (
                self._stats["total_latency_ms"] / total if total > 0 else 0.0
            ),
            "block_rate": (
                (self._stats["heuristic_blocks"] + self._stats["semantic_blocks"]) / total
                if total > 0 else 0.0
            ),
            "semantic_enabled": self._semantic is not None,
            "heuristic_enabled": self._heuristic is not None,
        }

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._stats = {
            "total_validations": 0,
            "heuristic_blocks": 0,
            "semantic_blocks": 0,
            "allowed": 0,
            "errors": 0,
            "timeouts": 0,
            "total_latency_ms": 0.0,
        }


class AsyncLayeredValidator:
    """
    Async version of LayeredValidator for use with async frameworks.

    This provides the same two-layer validation but with async semantics,
    suitable for use with asyncio-based frameworks like FastAPI, aiohttp, etc.

    Example:
        validator = AsyncLayeredValidator(
            semantic_api_key="sk-...",
            use_semantic=True,
        )
        result = await validator.validate("content")
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        **kwargs: Any,
    ):
        """Initialize AsyncLayeredValidator with same parameters as LayeredValidator."""
        # Handle config
        if config is not None:
            self.config = config
        else:
            config_kwargs = {}
            valid_config_keys = {
                "use_heuristic", "use_semantic", "semantic_provider",
                "semantic_model", "semantic_api_key", "semantic_base_url",
                "validation_timeout", "fail_closed", "skip_semantic_if_heuristic_blocks",
                "max_text_size", "log_validations", "log_level",
            }
            for key in valid_config_keys:
                if key in kwargs:
                    config_kwargs[key] = kwargs[key]

            self.config = ValidationConfig(**config_kwargs)

        # Initialize validators
        self._heuristic: Optional[Any] = None
        self._semantic: Optional[Any] = None
        self._init_heuristic()
        self._init_semantic()

        # Statistics
        self._stats = {
            "total_validations": 0,
            "heuristic_blocks": 0,
            "semantic_blocks": 0,
            "allowed": 0,
            "errors": 0,
            "timeouts": 0,
            "total_latency_ms": 0.0,
        }

    def _init_heuristic(self) -> None:
        """Initialize heuristic validator if enabled."""
        if not self.config.use_heuristic:
            return

        try:
            from sentinelseed.validators.gates import THSPValidator
            self._heuristic = THSPValidator()
        except ImportError as e:
            logger.warning(f"Could not import THSPValidator: {e}")

    def _init_semantic(self) -> None:
        """Initialize async semantic validator if enabled and configured."""
        if not self.config.use_semantic:
            return

        api_key = self.config.semantic_api_key or self.config.get_api_key_from_env()
        if not api_key:
            return

        try:
            from sentinelseed.validators.semantic import AsyncSemanticValidator
            self._semantic = AsyncSemanticValidator(
                provider=self.config.semantic_provider,
                model=self.config.effective_model,
                api_key=api_key,
                base_url=self.config.semantic_base_url,
                timeout=int(self.config.validation_timeout),
            )
        except ImportError as e:
            logger.warning(f"Could not import AsyncSemanticValidator: {e}")
        except Exception as e:
            logger.warning(f"Could not initialize AsyncSemanticValidator: {e}")

    async def validate(self, content: str) -> ValidationResult:
        """
        Validate content through layered validation asynchronously.

        Args:
            content: Text content to validate

        Returns:
            ValidationResult
        """
        import asyncio

        start_time = time.time()
        self._stats["total_validations"] += 1

        # Check for empty/None content
        if not content:
            return ValidationResult.safe(ValidationLayer.HEURISTIC)

        # Check text size
        content_bytes = len(content.encode("utf-8"))
        if content_bytes > self.config.max_text_size:
            self._stats["heuristic_blocks"] += 1
            return ValidationResult.from_blocked(
                violations=[
                    f"Content exceeds maximum size ({content_bytes} > {self.config.max_text_size} bytes)"
                ],
                layer=ValidationLayer.HEURISTIC,
            )

        heuristic_passed: Optional[bool] = None
        heuristic_violations: List[str] = []

        # Layer 1: Heuristic (sync, fast)
        if self._heuristic:
            try:
                # Heuristic is sync, run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                heuristic_result = await loop.run_in_executor(
                    None, self._heuristic.validate, content
                )
                heuristic_passed = heuristic_result.get("is_safe", True)
                heuristic_violations = heuristic_result.get("violations", [])

                if not heuristic_passed:
                    if self.config.skip_semantic_if_heuristic_blocks or not self._semantic:
                        self._stats["heuristic_blocks"] += 1
                        return ValidationResult(
                            is_safe=False,
                            layer=ValidationLayer.HEURISTIC,
                            violations=heuristic_violations,
                            risk_level=RiskLevel.HIGH,
                            heuristic_passed=False,
                        )

            except Exception as e:
                logger.error(f"Heuristic validation error: {e}")
                self._stats["errors"] += 1
                if self.config.fail_closed:
                    result = ValidationResult.from_error(f"Heuristic validation failed: {e}")
                    result.layer = ValidationLayer.HEURISTIC
                    return result

        # Layer 2: Semantic (async)
        semantic_passed: Optional[bool] = None
        if self._semantic:
            try:
                semantic_result = await asyncio.wait_for(
                    self._semantic.validate(content),
                    timeout=self.config.validation_timeout,
                )
                semantic_passed = semantic_result.is_safe

                if not semantic_passed:
                    violations = []
                    if semantic_result.reasoning:
                        violations.append(semantic_result.reasoning)
                    if semantic_result.violated_gate:
                        violations.append(f"Violated gate: {semantic_result.violated_gate}")

                    risk_level = RiskLevel.MEDIUM
                    if hasattr(semantic_result.risk_level, "value"):
                        try:
                            risk_level = RiskLevel(semantic_result.risk_level.value)
                        except ValueError:
                            pass

                    self._stats["semantic_blocks"] += 1
                    return ValidationResult(
                        is_safe=False,
                        layer=ValidationLayer.SEMANTIC,
                        violations=violations or heuristic_violations,
                        risk_level=risk_level,
                        reasoning=semantic_result.reasoning,
                        heuristic_passed=heuristic_passed,
                        semantic_passed=False,
                    )

            except asyncio.TimeoutError:
                logger.warning(
                    f"Semantic validation timed out after {self.config.validation_timeout}s"
                )
                self._stats["timeouts"] += 1
                if self.config.fail_closed:
                    result = ValidationResult.from_error(
                        f"Semantic validation timed out after {self.config.validation_timeout}s"
                    )
                    result.layer = ValidationLayer.SEMANTIC
                    result.heuristic_passed = heuristic_passed
                    return result

            except Exception as e:
                logger.error(f"Semantic validation error: {e}")
                self._stats["errors"] += 1
                if self.config.fail_closed:
                    result = ValidationResult.from_error(f"Semantic validation failed: {e}")
                    result.layer = ValidationLayer.SEMANTIC
                    result.heuristic_passed = heuristic_passed
                    return result

        # All passed
        layer = ValidationLayer.BOTH if semantic_passed is not None else ValidationLayer.HEURISTIC
        self._stats["allowed"] += 1

        return ValidationResult(
            is_safe=True,
            layer=layer,
            risk_level=RiskLevel.LOW,
            heuristic_passed=heuristic_passed,
            semantic_passed=semantic_passed,
        )

    async def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> ValidationResult:
        """Validate an action asynchronously."""
        description = f"Action: {action_name}"
        if action_args:
            args_str = ", ".join(f"{k}={v}" for k, v in action_args.items())
            description = f"{description}({args_str})"
        if purpose:
            description = f"{description}\nPurpose: {purpose}"
        return await self.validate(description)

    async def validate_request(self, request: str) -> ValidationResult:
        """Validate a user request asynchronously."""
        return await self.validate(f"User request: {request}")

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self._stats["total_validations"]
        return {
            **self._stats,
            "avg_latency_ms": (
                self._stats["total_latency_ms"] / total if total > 0 else 0.0
            ),
            "block_rate": (
                (self._stats["heuristic_blocks"] + self._stats["semantic_blocks"]) / total
                if total > 0 else 0.0
            ),
            "semantic_enabled": self._semantic is not None,
            "heuristic_enabled": self._heuristic is not None,
        }


# Factory function for convenience
def create_layered_validator(
    semantic_api_key: Optional[str] = None,
    semantic_provider: str = "openai",
    semantic_model: Optional[str] = None,
    fail_closed: bool = False,
    async_mode: bool = False,
    **kwargs: Any,
) -> Union[LayeredValidator, AsyncLayeredValidator]:
    """
    Factory function to create a LayeredValidator.

    This is a convenience function for creating validators with common configurations.

    Args:
        semantic_api_key: API key for LLM provider (enables semantic validation)
        semantic_provider: "openai" or "anthropic"
        semantic_model: Model to use (default based on provider)
        fail_closed: Block on errors (default False)
        async_mode: Return AsyncLayeredValidator if True
        **kwargs: Additional configuration parameters

    Returns:
        LayeredValidator or AsyncLayeredValidator

    Example:
        # Heuristic only
        validator = create_layered_validator()

        # With semantic
        validator = create_layered_validator(
            semantic_api_key="sk-...",
            semantic_provider="openai",
        )

        # Async with semantic
        validator = create_layered_validator(
            semantic_api_key="sk-...",
            async_mode=True,
        )
    """
    config = ValidationConfig(
        use_semantic=bool(semantic_api_key),
        semantic_api_key=semantic_api_key,
        semantic_provider=semantic_provider,
        semantic_model=semantic_model,
        fail_closed=fail_closed,
        **kwargs,
    )

    if async_mode:
        return AsyncLayeredValidator(config=config)
    return LayeredValidator(config=config)


__all__ = [
    "LayeredValidator",
    "AsyncLayeredValidator",
    "create_layered_validator",
]
