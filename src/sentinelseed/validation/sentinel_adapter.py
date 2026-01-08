"""
Sentinel v3.0 Adapter - Bridge between v3.0 core and v2.x interface.

This adapter allows existing integrations to benefit from the improved
Sentinel v3.0 detection capabilities while maintaining full backwards
compatibility with the ValidationResult interface.

Architecture:
    Integration calls → SentinelV3Adapter.validate() → InputValidator (v3.0)
                                                     ↓
                                              ValidationResult (v2.x interface)

The adapter uses InputValidator for input validation and OutputValidator
for output validation, converting results to the standard ValidationResult
format expected by all integrations.

Usage:
    # Drop-in replacement for LayeredValidator
    from sentinelseed.validation.sentinel_adapter import SentinelV3Adapter

    adapter = SentinelV3Adapter()
    result = adapter.validate("user input")

    # Same interface as LayeredValidator
    if not result.is_safe:
        print(result.violations)
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, List, Optional

from sentinelseed.validation.types import (
    ValidationResult,
    ValidationLayer,
    ValidationMode,
    RiskLevel,
)
from sentinelseed.validation.config import ValidationConfig

logger = logging.getLogger("sentinelseed.validation.sentinel_adapter")


class SentinelV3Adapter:
    """
    Adapter that uses Sentinel v3.0 internally while exposing v2.x interface.

    This provides a drop-in replacement for LayeredValidator that leverages
    the improved detection capabilities of InputValidator and OutputValidator.

    Key benefits:
    - 580+ attack patterns from InputValidator
    - Embedding-based detection (optional)
    - Full compatibility with existing integrations
    - Same ValidationResult interface

    Attributes:
        config: ValidationConfig for customization
        stats: Dictionary with validation statistics
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        use_embeddings: bool = False,
        **kwargs: Any,
    ):
        """
        Initialize the adapter.

        Args:
            config: ValidationConfig for customization (optional)
            use_embeddings: Enable embedding-based detection for higher accuracy
            **kwargs: Additional arguments for compatibility
        """
        self.config = config or ValidationConfig()
        self._use_embeddings = use_embeddings

        # Statistics
        self._stats: Dict[str, Any] = {
            "total_validations": 0,
            "input_validations": 0,
            "output_validations": 0,
            "blocked": 0,
            "allowed": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }

        # Lazy initialization of validators
        self._input_validator = None
        self._output_validator = None
        self._initialized = False

    def _ensure_initialized(self) -> None:
        """Lazy initialization of v3.0 validators."""
        if self._initialized:
            return

        try:
            from sentinelseed.detection import InputValidator, OutputValidator
            from sentinelseed.detection.config import (
                InputValidatorConfig,
                OutputValidatorConfig,
            )

            # Initialize InputValidator with embedding support if requested
            input_config = InputValidatorConfig(
                use_embeddings=self._use_embeddings,
            )
            self._input_validator = InputValidator(config=input_config)

            # Initialize OutputValidator
            output_config = OutputValidatorConfig(
                use_embeddings=self._use_embeddings,
            )
            self._output_validator = OutputValidator(config=output_config)

            self._initialized = True
            logger.debug(
                f"SentinelV3Adapter initialized (embeddings={self._use_embeddings})"
            )

        except ImportError as e:
            logger.error(f"Failed to import v3.0 validators: {e}")
            raise ImportError(
                "SentinelV3Adapter requires sentinelseed.detection module"
            ) from e

    def validate(self, content: str) -> ValidationResult:
        """
        Validate content using Sentinel v3.0 InputValidator.

        This method provides full compatibility with the LayeredValidator
        interface while using the improved v3.0 detection capabilities.

        Args:
            content: Text content to validate

        Returns:
            ValidationResult with:
            - is_safe: True if no threats detected
            - violations: List of detected issues
            - layer: ValidationLayer.HEURISTIC
            - risk_level: Assessed risk level
        """
        start_time = time.time()
        self._stats["total_validations"] += 1
        self._stats["input_validations"] += 1

        self._ensure_initialized()

        try:
            # Use InputValidator for detection
            input_result = self._input_validator.validate(content)

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_latency_ms"] += latency_ms

            if input_result.is_attack:
                self._stats["blocked"] += 1

                # Convert attack types to readable strings
                attack_types = [
                    at.value if hasattr(at, "value") else str(at)
                    for at in input_result.attack_types
                ]

                # Build violation messages
                violations = list(input_result.violations)
                if not violations and attack_types:
                    violations = [f"Attack detected: {', '.join(attack_types)}"]

                result = ValidationResult(
                    is_safe=False,
                    violations=violations,
                    layer=ValidationLayer.HEURISTIC,
                    risk_level=RiskLevel.HIGH,
                    mode=ValidationMode.INPUT,
                    attack_types=attack_types,
                )

                if self.config.log_validations:
                    logger.info(
                        f"BLOCKED: {attack_types}, latency={latency_ms:.1f}ms"
                    )

                return result

            else:
                self._stats["allowed"] += 1

                result = ValidationResult(
                    is_safe=True,
                    violations=[],
                    layer=ValidationLayer.HEURISTIC,
                    risk_level=RiskLevel.LOW,
                    mode=ValidationMode.INPUT,
                )

                if self.config.log_validations:
                    logger.debug(f"ALLOWED: latency={latency_ms:.1f}ms")

                return result

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Validation error: {e}")

            if self.config.fail_closed:
                return ValidationResult(
                    is_safe=False,
                    violations=[f"Validation error: {str(e)}"],
                    layer=ValidationLayer.HEURISTIC,
                    risk_level=RiskLevel.HIGH,
                    mode=ValidationMode.INPUT,
                )

            # Fail-open: return safe result
            return ValidationResult(
                is_safe=True,
                violations=[],
                layer=ValidationLayer.HEURISTIC,
                risk_level=RiskLevel.LOW,
                mode=ValidationMode.INPUT,
            )

    def validate_input(self, text: str) -> ValidationResult:
        """
        Validate user input for attack detection.

        Alias for validate() - uses InputValidator internally.

        Args:
            text: User input text to validate

        Returns:
            ValidationResult with attack detection results
        """
        result = self.validate(text)
        result.mode = ValidationMode.INPUT
        return result

    def validate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate AI output for seed failure detection.

        Uses OutputValidator from v3.0 to detect if the AI safety seed
        failed to prevent harmful output.

        Args:
            output: AI response text to validate
            input_context: Original user input for context

        Returns:
            ValidationResult with seed failure detection results
        """
        start_time = time.time()
        self._stats["total_validations"] += 1
        self._stats["output_validations"] += 1

        self._ensure_initialized()

        try:
            # Use OutputValidator for detection
            output_result = self._output_validator.validate(output, input_context)

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_latency_ms"] += latency_ms

            if output_result.seed_failed:
                self._stats["blocked"] += 1

                # Convert failure types to readable strings
                failure_types = [
                    ft.value if hasattr(ft, "value") else str(ft)
                    for ft in output_result.failure_types
                ]

                # Build violation messages
                violations = list(output_result.violations)
                if not violations and failure_types:
                    violations = [f"Seed failure: {', '.join(failure_types)}"]

                result = ValidationResult(
                    is_safe=False,
                    violations=violations,
                    layer=ValidationLayer.HEURISTIC,
                    risk_level=RiskLevel.HIGH,
                    mode=ValidationMode.OUTPUT,
                    seed_failed=True,
                    failure_types=failure_types,
                    gates_failed=list(output_result.gates_failed),
                    input_context=input_context,
                )

                if self.config.log_validations:
                    logger.info(
                        f"OUTPUT BLOCKED: {failure_types}, latency={latency_ms:.1f}ms"
                    )

                return result

            else:
                self._stats["allowed"] += 1

                result = ValidationResult(
                    is_safe=True,
                    violations=[],
                    layer=ValidationLayer.HEURISTIC,
                    risk_level=RiskLevel.LOW,
                    mode=ValidationMode.OUTPUT,
                    seed_failed=False,
                    input_context=input_context,
                )

                if self.config.log_validations:
                    logger.debug(f"OUTPUT ALLOWED: latency={latency_ms:.1f}ms")

                return result

        except Exception as e:
            self._stats["errors"] += 1
            logger.error(f"Output validation error: {e}")

            if self.config.fail_closed:
                return ValidationResult(
                    is_safe=False,
                    violations=[f"Output validation error: {str(e)}"],
                    layer=ValidationLayer.HEURISTIC,
                    risk_level=RiskLevel.HIGH,
                    mode=ValidationMode.OUTPUT,
                    seed_failed=True,
                )

            # Fail-open
            return ValidationResult(
                is_safe=True,
                violations=[],
                layer=ValidationLayer.HEURISTIC,
                risk_level=RiskLevel.LOW,
                mode=ValidationMode.OUTPUT,
                seed_failed=False,
            )

    def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> ValidationResult:
        """
        Validate an action before execution.

        Formats the action as text and validates using InputValidator.

        Args:
            action_name: Name of the action
            action_args: Arguments to the action
            purpose: Stated purpose for the action

        Returns:
            ValidationResult
        """
        # Format action as text for validation
        parts = [f"Action: {action_name}"]
        if action_args:
            args_str = ", ".join(f"{k}={v}" for k, v in action_args.items())
            parts.append(f"Args: {args_str}")
        if purpose:
            parts.append(f"Purpose: {purpose}")

        action_text = " | ".join(parts)
        return self.validate(action_text)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        stats = self._stats.copy()
        if stats["total_validations"] > 0:
            stats["avg_latency_ms"] = (
                stats["total_latency_ms"] / stats["total_validations"]
            )
            stats["block_rate"] = stats["blocked"] / stats["total_validations"]
        else:
            stats["avg_latency_ms"] = 0.0
            stats["block_rate"] = 0.0
        return stats

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._stats = {
            "total_validations": 0,
            "input_validations": 0,
            "output_validations": 0,
            "blocked": 0,
            "allowed": 0,
            "errors": 0,
            "total_latency_ms": 0.0,
        }


class AsyncSentinelV3Adapter:
    """
    Async version of SentinelV3Adapter.

    Provides async validation methods for use with asyncio-based frameworks.
    Uses the sync adapter internally with executor for I/O operations.
    """

    def __init__(
        self,
        config: Optional[ValidationConfig] = None,
        use_embeddings: bool = False,
        **kwargs: Any,
    ):
        """Initialize the async adapter."""
        self._sync_adapter = SentinelV3Adapter(
            config=config,
            use_embeddings=use_embeddings,
            **kwargs,
        )

    async def validate(self, content: str) -> ValidationResult:
        """Validate content asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_adapter.validate, content
        )

    async def validate_input(self, text: str) -> ValidationResult:
        """Validate input asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_adapter.validate_input, text
        )

    async def validate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> ValidationResult:
        """Validate output asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_adapter.validate_output, output, input_context
        )

    async def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> ValidationResult:
        """Validate action asynchronously."""
        import asyncio

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._sync_adapter.validate_action, action_name, action_args, purpose
        )

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self._sync_adapter.stats

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        self._sync_adapter.reset_stats()


__all__ = [
    "SentinelV3Adapter",
    "AsyncSentinelV3Adapter",
]
