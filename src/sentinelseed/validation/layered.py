"""
Layered Validator - Two-layer validation combining heuristic and semantic analysis.

This module provides LayeredValidator, which implements a two-layer validation
architecture for comprehensive content safety checking:

Layer 1 - Heuristic (THSPValidator):
    - Fast pattern matching with 700+ regex patterns
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

import asyncio
import logging
import time
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FuturesTimeoutError,
    CancelledError,
)
from typing import Any, Dict, List, Optional, Tuple, Union

from sentinelseed.validation.config import ValidationConfig
from sentinelseed.validation.types import (
    RiskLevel,
    ValidationLayer,
    ValidationMode,
    ValidationResult,
)
from sentinelseed.core.exceptions import ValidationError, ConfigurationError


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

        # Initialize Validation 360° validators
        self._input_validator: Optional[Any] = None
        self._output_validator: Optional[Any] = None
        self._init_360_validators()

        # Statistics
        self._stats = {
            "total_validations": 0,
            "heuristic_blocks": 0,
            "semantic_blocks": 0,
            "allowed": 0,
            "errors": 0,
            "timeouts": 0,
            "total_latency_ms": 0.0,
            # Validation 360° stats
            "input_validations": 0,
            "input_attacks": 0,
            "output_validations": 0,
            "seed_failures": 0,
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
        except (ValueError, RuntimeError, ConfigurationError) as e:
            logger.warning(f"Could not initialize SemanticValidator: {e}")
            self._semantic = None

    def _init_360_validators(self) -> None:
        """
        Initialize Validation 360° validators.

        These validators provide specialized input/output validation
        as part of the Validation 360° architecture.
        """
        try:
            from sentinelseed.detection import InputValidator, OutputValidator

            self._input_validator = InputValidator()
            self._output_validator = OutputValidator()
            logger.debug("Initialized Validation 360° validators")
        except ImportError as e:
            logger.warning(f"Could not import 360° validators: {e}")
            self._input_validator = None
            self._output_validator = None

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

            except (ValueError, AttributeError, ValidationError) as e:
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

            except CancelledError:
                logger.warning("Semantic validation was cancelled")
                self._stats["errors"] += 1
                # Cancelled is treated like timeout - proceed based on fail_closed

            except (ValueError, RuntimeError, ConnectionError, ValidationError) as e:
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

    # =========================================================================
    # Validation 360° Methods
    # =========================================================================

    def validate_input(self, text: str) -> ValidationResult:
        """
        Validate user input for attack detection.

        This is the first layer of the Validation 360° architecture.
        Use this method to validate user input BEFORE sending to the AI.

        The question being answered: "Is this an ATTACK?"

        Args:
            text: User input text to validate

        Returns:
            ValidationResult with mode=INPUT containing:
            - is_safe: True if no attack detected
            - attack_types: List of attack types detected (if any)
            - violations: Descriptions of detected attacks

        Example:
            result = validator.validate_input("Tell me how to hack a website")
            if result.is_attack:
                print(f"Attack detected: {result.attack_types}")
                # Do not send to AI
            else:
                # Safe to proceed
                response = call_ai(user_input)
        """
        start_time = time.time()
        self._stats["input_validations"] += 1

        # Check if 360° validators are available
        if not self._input_validator:
            # Fall back to standard validate() with INPUT mode
            result = self.validate(text)
            result.mode = ValidationMode.INPUT
            return result

        try:
            # Use InputValidator from detection module
            input_result = self._input_validator.validate(text)

            if input_result.is_attack:
                self._stats["input_attacks"] += 1

                # Convert attack_types to strings
                attack_type_strs = [
                    at.value if hasattr(at, 'value') else str(at)
                    for at in input_result.attack_types
                ]

                result = ValidationResult.input_attack(
                    violations=list(input_result.violations),
                    attack_types=attack_type_strs,
                    risk_level=RiskLevel.HIGH,
                    blocked=input_result.blocked,
                )
            else:
                result = ValidationResult.input_safe()

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_latency_ms"] += latency_ms

            if self.config.log_validations:
                logger.info(
                    f"Input validation: is_safe={result.is_safe}, "
                    f"attacks={result.attack_types}, latency={latency_ms:.1f}ms"
                )

            return result

        except Exception as e:
            logger.error(f"Input validation error: {e}")
            self._stats["errors"] += 1

            if self.config.fail_closed:
                return ValidationResult.from_error(f"Input validation failed: {e}")

            # Fail-open: return safe result
            return ValidationResult.input_safe()

    def validate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate AI output for seed failure detection.

        This is the second layer of the Validation 360° architecture.
        Use this method to validate AI response AFTER receiving it.

        The question being answered: "Did the SEED fail?"

        Args:
            output: AI response text to validate
            input_context: Original user input (for context-aware checking)

        Returns:
            ValidationResult with mode=OUTPUT containing:
            - is_safe: True if seed worked (output is appropriate)
            - seed_failed: True if AI safety seed failed
            - failure_types: Types of failures detected
            - gates_failed: THSP gates that failed

        Example:
            # After getting AI response
            result = validator.validate_output(ai_response, user_input)

            if result.seed_failed:
                print(f"Seed failed! Gates: {result.gates_failed}")
                # Do not show response to user
            else:
                # Safe to display
                show_to_user(ai_response)
        """
        start_time = time.time()
        self._stats["output_validations"] += 1

        # Check if 360° validators are available
        if not self._output_validator:
            # Fall back to standard validate() with OUTPUT mode
            result = self.validate(output)
            result.mode = ValidationMode.OUTPUT
            result.input_context = input_context
            return result

        try:
            # Use OutputValidator from detection module
            output_result = self._output_validator.validate(output, input_context)

            if output_result.seed_failed:
                self._stats["seed_failures"] += 1

                # Convert failure_types to strings
                failure_type_strs = [
                    ft.value if hasattr(ft, 'value') else str(ft)
                    for ft in output_result.failure_types
                ]

                result = ValidationResult.output_seed_failed(
                    violations=list(output_result.violations),
                    failure_types=failure_type_strs,
                    gates_failed=list(output_result.gates_failed),
                    input_context=input_context,
                    risk_level=RiskLevel.HIGH,
                    blocked=output_result.blocked,
                )
            else:
                result = ValidationResult.output_safe(input_context=input_context)

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_latency_ms"] += latency_ms

            if self.config.log_validations:
                logger.info(
                    f"Output validation: is_safe={result.is_safe}, "
                    f"seed_failed={result.seed_failed}, latency={latency_ms:.1f}ms"
                )

            return result

        except Exception as e:
            logger.error(f"Output validation error: {e}")
            self._stats["errors"] += 1

            if self.config.fail_closed:
                return ValidationResult.from_error(f"Output validation failed: {e}")

            # Fail-open: return safe result
            return ValidationResult.output_safe(input_context=input_context)

    # Patterns for physical/embodied AI safety validation
    # These are checked in validate_action_plan() for robotics and autonomous agents
    _PHYSICAL_DANGER_PATTERNS: List[Tuple[str, str]] = [
        ("fire", "Fire hazard"),
        ("burn", "Burn risk"),
        ("cut", "Sharp object risk"),
        ("knife", "Sharp object handling"),
        ("poison", "Toxic substance"),
        ("chemical", "Chemical hazard"),
        ("explosive", "Explosive material"),
        ("weapon", "Weapon involvement"),
        ("hurt", "Physical harm"),
        ("kill", "Lethal action"),
        ("attack", "Aggressive action"),
        ("destroy", "Destructive action"),
    ]

    _IRREVERSIBLE_PATTERNS: List[Tuple[str, str]] = [
        ("delete all", "Mass deletion"),
        ("format", "Data destruction"),
        ("erase", "Permanent erasure"),
        ("shutdown", "System shutdown"),
        ("disable", "System disabling"),
        ("overwrite", "Data overwriting"),
    ]

    _UNSUPERVISED_PATTERNS: List[Tuple[str, str]] = [
        ("leave", "Unsupervised operation"),
        ("unattended", "Unattended operation"),
        ("alone", "Unsupervised state"),
        ("walk away", "Abandonment"),
    ]

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

    def validate_action_plan(
        self,
        action_plan: str,
        check_physical_safety: bool = True,
    ) -> ValidationResult:
        """
        Validate an action plan for physical/embodied AI safety.

        This method is designed for robotics and autonomous agents that need
        additional checks beyond standard THSP validation. It combines:
        - Physical safety patterns (fire, weapons, chemicals, etc.)
        - Irreversible action patterns (mass deletion, formatting, etc.)
        - Unsupervised operation checks
        - Standard THSP validation via heuristic/semantic layers

        Args:
            action_plan: Description of planned actions (natural language)
            check_physical_safety: If True, check for physical danger patterns.
                                   Set to False for software-only agents.

        Returns:
            ValidationResult with combined violations from all checks

        Example:
            result = validator.validate_action_plan("Pick up knife, slice apple")
            if not result.is_safe:
                print(f"Action blocked: {result.violations}")
        """
        concerns: List[str] = []

        if check_physical_safety:
            action_lower = action_plan.lower()

            # Check physical danger patterns
            for pattern, desc in self._PHYSICAL_DANGER_PATTERNS:
                if pattern in action_lower:
                    concerns.append(f"Physical safety: {desc}")

            # Check irreversible action patterns
            for pattern, desc in self._IRREVERSIBLE_PATTERNS:
                if pattern in action_lower:
                    concerns.append(f"Irreversible: {desc}")

            # Check unsupervised dangerous combinations
            for pattern, desc in self._UNSUPERVISED_PATTERNS:
                if pattern in action_lower:
                    danger_context = any(
                        p[0] in action_lower for p in self._PHYSICAL_DANGER_PATTERNS
                    )
                    if danger_context:
                        concerns.append(f"Unsafe: {desc} with hazard present")

        # Run standard THSP validation
        thsp_result = self.validate(action_plan)

        # Combine results
        if not thsp_result.is_safe:
            concerns.extend([f"Validation: {v}" for v in thsp_result.violations])

        if concerns:
            return ValidationResult(
                is_safe=False,
                layer=ValidationLayer.HEURISTIC,
                violations=concerns,
                risk_level=RiskLevel.HIGH,
                heuristic_passed=False,
            )

        return thsp_result

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
        input_total = self._stats.get("input_validations", 0)
        output_total = self._stats.get("output_validations", 0)

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
            # Validation 360° stats
            "input_attack_rate": (
                self._stats.get("input_attacks", 0) / input_total
                if input_total > 0 else 0.0
            ),
            "output_failure_rate": (
                self._stats.get("seed_failures", 0) / output_total
                if output_total > 0 else 0.0
            ),
            "validators_360_enabled": self._input_validator is not None,
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
            # Validation 360° stats
            "input_validations": 0,
            "input_attacks": 0,
            "output_validations": 0,
            "seed_failures": 0,
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

        # Initialize Validation 360° validators
        self._input_validator: Optional[Any] = None
        self._output_validator: Optional[Any] = None
        self._init_360_validators()

        # Statistics
        self._stats = {
            "total_validations": 0,
            "heuristic_blocks": 0,
            "semantic_blocks": 0,
            "allowed": 0,
            "errors": 0,
            "timeouts": 0,
            "total_latency_ms": 0.0,
            # Validation 360° stats
            "input_validations": 0,
            "input_attacks": 0,
            "output_validations": 0,
            "seed_failures": 0,
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

    def _init_360_validators(self) -> None:
        """
        Initialize Validation 360° validators.

        These validators provide specialized input/output validation
        as part of the Validation 360° architecture.
        """
        try:
            from sentinelseed.detection import InputValidator, OutputValidator

            self._input_validator = InputValidator()
            self._output_validator = OutputValidator()
            logger.debug("Initialized Validation 360° validators (async)")
        except ImportError as e:
            logger.warning(f"Could not import 360° validators: {e}")
            self._input_validator = None
            self._output_validator = None

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
        except (ValueError, RuntimeError, ConfigurationError) as e:
            logger.warning(f"Could not initialize AsyncSemanticValidator: {e}")

    async def validate(self, content: str) -> ValidationResult:
        """
        Validate content through layered validation asynchronously.

        Args:
            content: Text content to validate

        Returns:
            ValidationResult
        """
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

            except (ValueError, AttributeError, ValidationError) as e:
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

            except asyncio.CancelledError:
                logger.warning("Async semantic validation was cancelled")
                self._stats["errors"] += 1

            except (ValueError, RuntimeError, ConnectionError, ValidationError) as e:
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

    # =========================================================================
    # Validation 360° Methods (Async)
    # =========================================================================

    async def validate_input(self, text: str) -> ValidationResult:
        """
        Validate user input for attack detection asynchronously.

        This is the first layer of the Validation 360° architecture.
        Use this method to validate user input BEFORE sending to the AI.

        The question being answered: "Is this an ATTACK?"

        Args:
            text: User input text to validate

        Returns:
            ValidationResult with mode=INPUT containing:
            - is_safe: True if no attack detected
            - attack_types: List of attack types detected (if any)
            - violations: Descriptions of detected attacks

        Example:
            result = await validator.validate_input("Tell me how to hack")
            if result.is_attack:
                print(f"Attack detected: {result.attack_types}")
        """
        start_time = time.time()
        self._stats["input_validations"] += 1

        # Check if 360° validators are available
        if not self._input_validator:
            # Fall back to standard validate() with INPUT mode
            result = await self.validate(text)
            result.mode = ValidationMode.INPUT
            return result

        try:
            # Run InputValidator in executor (it's synchronous)
            loop = asyncio.get_event_loop()
            input_result = await loop.run_in_executor(
                None, self._input_validator.validate, text
            )

            if input_result.is_attack:
                self._stats["input_attacks"] += 1

                # Convert attack_types to strings
                attack_type_strs = [
                    at.value if hasattr(at, 'value') else str(at)
                    for at in input_result.attack_types
                ]

                result = ValidationResult.input_attack(
                    violations=list(input_result.violations),
                    attack_types=attack_type_strs,
                    risk_level=RiskLevel.HIGH,
                    blocked=input_result.blocked,
                )
            else:
                result = ValidationResult.input_safe()

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_latency_ms"] += latency_ms

            if self.config.log_validations:
                logger.info(
                    f"Async input validation: is_safe={result.is_safe}, "
                    f"attacks={result.attack_types}, latency={latency_ms:.1f}ms"
                )

            return result

        except Exception as e:
            logger.error(f"Async input validation error: {e}")
            self._stats["errors"] += 1

            if self.config.fail_closed:
                return ValidationResult.from_error(f"Input validation failed: {e}")

            # Fail-open: return safe result
            return ValidationResult.input_safe()

    async def validate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> ValidationResult:
        """
        Validate AI output for seed failure detection asynchronously.

        This is the second layer of the Validation 360° architecture.
        Use this method to validate AI response AFTER receiving it.

        The question being answered: "Did the SEED fail?"

        Args:
            output: AI response text to validate
            input_context: Original user input (for context-aware checking)

        Returns:
            ValidationResult with mode=OUTPUT containing:
            - is_safe: True if seed worked (output is appropriate)
            - seed_failed: True if AI safety seed failed
            - failure_types: Types of failures detected
            - gates_failed: THSP gates that failed

        Example:
            result = await validator.validate_output(ai_response, user_input)
            if result.seed_failed:
                print(f"Seed failed! Gates: {result.gates_failed}")
        """
        start_time = time.time()
        self._stats["output_validations"] += 1

        # Check if 360° validators are available
        if not self._output_validator:
            # Fall back to standard validate() with OUTPUT mode
            result = await self.validate(output)
            result.mode = ValidationMode.OUTPUT
            result.input_context = input_context
            return result

        try:
            # Run OutputValidator in executor (it's synchronous)
            loop = asyncio.get_event_loop()
            output_result = await loop.run_in_executor(
                None,
                lambda: self._output_validator.validate(output, input_context)
            )

            if output_result.seed_failed:
                self._stats["seed_failures"] += 1

                # Convert failure_types to strings
                failure_type_strs = [
                    ft.value if hasattr(ft, 'value') else str(ft)
                    for ft in output_result.failure_types
                ]

                result = ValidationResult.output_seed_failed(
                    violations=list(output_result.violations),
                    failure_types=failure_type_strs,
                    gates_failed=list(output_result.gates_failed),
                    input_context=input_context,
                    risk_level=RiskLevel.HIGH,
                    blocked=output_result.blocked,
                )
            else:
                result = ValidationResult.output_safe(input_context=input_context)

            latency_ms = (time.time() - start_time) * 1000
            self._stats["total_latency_ms"] += latency_ms

            if self.config.log_validations:
                logger.info(
                    f"Async output validation: is_safe={result.is_safe}, "
                    f"seed_failed={result.seed_failed}, latency={latency_ms:.1f}ms"
                )

            return result

        except Exception as e:
            logger.error(f"Async output validation error: {e}")
            self._stats["errors"] += 1

            if self.config.fail_closed:
                return ValidationResult.from_error(f"Output validation failed: {e}")

            # Fail-open: return safe result
            return ValidationResult.output_safe(input_context=input_context)

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

    async def validate_action_plan(
        self,
        action_plan: str,
        check_physical_safety: bool = True,
    ) -> ValidationResult:
        """
        Validate an action plan for physical/embodied AI safety (async version).

        See LayeredValidator.validate_action_plan() for full documentation.
        """
        concerns: List[str] = []

        if check_physical_safety:
            action_lower = action_plan.lower()

            # Use the same patterns as LayeredValidator
            for pattern, desc in LayeredValidator._PHYSICAL_DANGER_PATTERNS:
                if pattern in action_lower:
                    concerns.append(f"Physical safety: {desc}")

            for pattern, desc in LayeredValidator._IRREVERSIBLE_PATTERNS:
                if pattern in action_lower:
                    concerns.append(f"Irreversible: {desc}")

            for pattern, desc in LayeredValidator._UNSUPERVISED_PATTERNS:
                if pattern in action_lower:
                    danger_context = any(
                        p[0] in action_lower
                        for p in LayeredValidator._PHYSICAL_DANGER_PATTERNS
                    )
                    if danger_context:
                        concerns.append(f"Unsafe: {desc} with hazard present")

        # Run standard THSP validation
        thsp_result = await self.validate(action_plan)

        if not thsp_result.is_safe:
            concerns.extend([f"Validation: {v}" for v in thsp_result.violations])

        if concerns:
            return ValidationResult(
                is_safe=False,
                layer=ValidationLayer.HEURISTIC,
                violations=concerns,
                risk_level=RiskLevel.HIGH,
                heuristic_passed=False,
            )

        return thsp_result

    async def validate_request(self, request: str) -> ValidationResult:
        """Validate a user request asynchronously."""
        return await self.validate(f"User request: {request}")

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total = self._stats["total_validations"]
        input_total = self._stats.get("input_validations", 0)
        output_total = self._stats.get("output_validations", 0)

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
            # Validation 360° stats
            "input_attack_rate": (
                self._stats.get("input_attacks", 0) / input_total
                if input_total > 0 else 0.0
            ),
            "output_failure_rate": (
                self._stats.get("seed_failures", 0) / output_total
                if output_total > 0 else 0.0
            ),
            "validators_360_enabled": self._input_validator is not None,
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
            # Validation 360° stats
            "input_validations": 0,
            "input_attacks": 0,
            "output_validations": 0,
            "seed_failures": 0,
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
