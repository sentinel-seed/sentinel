"""
Base class for all Sentinel integrations.

This module provides SentinelIntegration and AsyncSentinelIntegration,
the foundation classes for all framework-specific integrations.

By inheriting from these base classes, integrations automatically get:

1. Sentinel v3.0 validation (InputValidator + OutputValidator)
2. 700+ attack patterns with optional embedding detection
3. Consistent configuration interface
4. Statistics tracking
5. Automatic benefit from core improvements
6. Testability via dependency injection

Architecture:
    SentinelIntegration
    ├── LangChainIntegration
    ├── GoogleADKPlugin
    ├── CrewAIIntegration
    ├── DSPyIntegration
    └── ... (all other integrations)

Usage for integration developers:

    from sentinelseed.integrations._base import (
        SentinelIntegration,
        ValidationConfig,  # Re-exported for convenience
        ValidationResult,  # Re-exported for convenience
    )

    class MyFrameworkIntegration(SentinelIntegration):
        _integration_name = "my_framework"

        def __init__(
            self,
            my_specific_param: str = "default",
            **kwargs,  # Passes validator/validation_config to base
        ):
            super().__init__(**kwargs)
            self.my_specific_param = my_specific_param

        def intercept_call(self, content: str) -> ValidationResult:
            result = self.validate(content)  # Uses inherited method
            if not result.is_safe:
                raise ValidationError(result.violations)
            return result

Usage for end users:

    # Default (heuristic only, no API needed)
    integration = MyFrameworkIntegration(my_specific_param="value")

    # With semantic validation
    from sentinelseed.integrations._base import ValidationConfig
    config = ValidationConfig(
        use_semantic=True,
        semantic_api_key="sk-...",
        semantic_provider="openai",
    )
    integration = MyFrameworkIntegration(
        my_specific_param="value",
        validation_config=config,
    )

    # With custom validator (for testing)
    integration = MyFrameworkIntegration(
        my_specific_param="value",
        validator=MockValidator(),
    )
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional, TYPE_CHECKING

# Re-export validation types for convenience
# This allows integrations to import everything from _base
from sentinelseed.validation import (
    LayeredValidator,
    AsyncLayeredValidator,
    ValidationConfig,
    ValidationResult,
    ValidationLayer,
    SentinelV3Adapter,
    AsyncSentinelV3Adapter,
)
from sentinelseed.validation.types import RiskLevel

if TYPE_CHECKING:
    from sentinelseed.core.interfaces import Validator, AsyncValidator


logger = logging.getLogger("sentinelseed.integrations")


class SentinelIntegration:
    """
    Base class for ALL Sentinel integrations.

    Every integration inherits from this and automatically gets:
    - Layered validation (heuristic + semantic)
    - Consistent configuration
    - Statistics tracking
    - Auto-updates when core improves

    The base class handles all validation setup, so subclasses only need
    to focus on their framework-specific logic.

    Attributes:
        _validator: The underlying validator instance
        _integration_name: Name for logging purposes (override in subclasses)

    Example:
        class GoogleADKPlugin(SentinelIntegration):
            _integration_name = "google_adk"

            def __init__(self, seed_level: str = "standard", **kwargs):
                super().__init__(**kwargs)
                self.seed_level = seed_level

            async def before_model_callback(self, context, request):
                content = self._extract_text(request)
                result = self.validate(content)
                if not result.is_safe:
                    return self._create_blocked_response(result)
                return None
    """

    # Override in subclasses for better logging
    _integration_name: str = "base"

    # Default seed level for this integration
    _default_seed_level: str = "standard"

    def __init__(
        self,
        validator: Optional["Validator"] = None,
        validation_config: Optional["ValidationConfig"] = None,
        use_v3: bool = True,
        use_embeddings: bool = False,
        seed_level: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize the integration with validation support.

        This constructor handles all validation setup. Subclasses should
        call super().__init__(**kwargs) to inherit this functionality.

        Args:
            validator: Custom validator instance. If provided, takes precedence
                      over all other options. Useful for testing with mocks.
            validation_config: Configuration for validator.
            use_v3: Use Sentinel v3.0 adapter (default: True). If False, uses
                   LayeredValidator for backwards compatibility.
            use_embeddings: Enable embedding-based detection (requires v3.0).
            seed_level: Seed level for system prompt injection. Options:
                       "minimal" (~360 tokens), "standard" (~1K tokens),
                       "full" (~1.9K tokens). Default: "standard".
            **kwargs: Additional arguments (absorbed for flexibility).

        Priority:
            1. validator (if provided) - used directly
            2. use_v3=True - creates SentinelV3Adapter (recommended)
            3. use_v3=False - creates LayeredValidator (legacy)

        Example:
            # Default - v3.0 with 700+ patterns
            integration = MyIntegration()

            # With embedding detection (higher accuracy)
            integration = MyIntegration(use_embeddings=True)

            # Legacy mode (LayeredValidator)
            integration = MyIntegration(use_v3=False)

            # With mock for testing
            integration = MyIntegration(validator=MockValidator())

            # With seed injection
            integration = MyIntegration(seed_level="full")
            system_prompt = integration.prepare_system_prompt("You are a helpful assistant.")
            # system_prompt now contains the seed + original prompt
        """
        if validator is not None:
            # User provided custom validator (could be mock for testing)
            self._validator = validator
            logger.debug(
                f"[{self._integration_name}] Using provided validator: "
                f"{type(validator).__name__}"
            )
        elif use_v3:
            # Use Sentinel v3.0 adapter (recommended)
            from sentinelseed.validation import SentinelV3Adapter

            self._validator = SentinelV3Adapter(
                config=validation_config,
                use_embeddings=use_embeddings,
            )
            logger.debug(
                f"[{self._integration_name}] Created SentinelV3Adapter "
                f"(embeddings={use_embeddings})"
            )
        else:
            # Legacy: Create LayeredValidator
            from sentinelseed.validation import LayeredValidator

            if validation_config is not None:
                self._validator = LayeredValidator(config=validation_config)
                logger.debug(
                    f"[{self._integration_name}] Created LayeredValidator "
                    f"with custom config (semantic={validation_config.use_semantic})"
                )
            else:
                self._validator = LayeredValidator()
                logger.debug(
                    f"[{self._integration_name}] Created LayeredValidator "
                    f"with default config (heuristic only)"
                )

        # Seed configuration (lazy loading)
        self._seed_level = seed_level or self._default_seed_level
        self._seed_cache: Optional[str] = None

    # =========================================================================
    # Seed Injection Methods
    # =========================================================================

    @property
    def seed(self) -> str:
        """
        Get the alignment seed for this integration.

        The seed is lazy-loaded and cached. Use this to inject the seed
        into your model's system prompt.

        Returns:
            The seed content as a string.

        Example:
            # Get seed and use in system prompt
            system_prompt = f"{integration.seed}\\n\\n{your_instructions}"
        """
        if self._seed_cache is None:
            self._seed_cache = self.get_seed(self._seed_level)
        return self._seed_cache

    def get_seed(self, level: Optional[str] = None) -> str:
        """
        Get an alignment seed by level.

        Args:
            level: Seed level - "minimal", "standard", or "full".
                  If None, uses the instance's configured seed_level.

        Returns:
            The seed content as a string.

        Example:
            # Get specific level
            full_seed = integration.get_seed("full")

            # Get default level for this integration
            seed = integration.get_seed()
        """
        from sentinelseed import Sentinel

        target_level = level or self._seed_level
        sentinel = Sentinel(seed_level=target_level)
        return sentinel.get_seed(target_level)

    def prepare_system_prompt(
        self,
        original_prompt: str = "",
        seed_position: str = "prepend",
    ) -> str:
        """
        Prepare a system prompt with the alignment seed injected.

        This method combines the alignment seed with your original system
        prompt. The seed provides THSP (Truth, Harm, Scope, Purpose) gates
        that help the model refuse harmful requests.

        Args:
            original_prompt: Your original system prompt/instructions.
            seed_position: Where to place the seed:
                          - "prepend": Seed before your prompt (recommended)
                          - "append": Seed after your prompt

        Returns:
            Combined system prompt with seed injected.

        Example:
            # Basic usage
            system_prompt = integration.prepare_system_prompt(
                "You are a helpful coding assistant."
            )

            # Append mode
            system_prompt = integration.prepare_system_prompt(
                "You are a customer service bot.",
                seed_position="append",
            )

        Note:
            The seed adds ~360-1900 tokens depending on seed_level.
            Plan your context window accordingly.
        """
        seed_content = self.seed

        if not original_prompt:
            return seed_content

        if seed_position == "append":
            return f"{original_prompt}\n\n{seed_content}"
        else:
            # prepend (default, recommended)
            return f"{seed_content}\n\n{original_prompt}"

    @property
    def seed_level(self) -> str:
        """Get the current seed level."""
        return self._seed_level

    @property
    def validator(self) -> "Validator":
        """
        Access the underlying validator.

        This property provides direct access to the validator for advanced
        use cases. Most integrations should use the validate() method instead.

        Returns:
            The validator instance (LayeredValidator or custom)
        """
        return self._validator

    def validate(self, content: str) -> "ValidationResult":
        """
        Validate content through the configured validator.

        This is the main method integrations should use for validation.
        It delegates to the underlying validator (LayeredValidator by default).

        Args:
            content: Text content to validate

        Returns:
            ValidationResult with:
            - is_safe: Boolean indicating safety
            - violations: List of violation messages
            - layer: Which layer made the decision
            - risk_level: Assessed risk level

        Example:
            result = self.validate("user input here")
            if not result.is_safe:
                logger.warning(f"Blocked: {result.violations}")
                return self._create_blocked_response(result)
        """
        return self._validator.validate(content)

    def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> "ValidationResult":
        """
        Validate an action before execution.

        Specialized validation for agentic systems that execute actions.
        The action is formatted and validated through the layered validator.

        Args:
            action_name: Name of the action (e.g., "send_email", "delete_file")
            action_args: Arguments to the action
            purpose: Stated purpose for the action (for THSP Purpose gate)

        Returns:
            ValidationResult

        Example:
            result = self.validate_action(
                action_name="execute_query",
                action_args={"query": "SELECT * FROM users"},
                purpose="Fetch user data for report",
            )
            if not result.is_safe:
                raise ActionBlockedError(result.violations)
        """
        return self._validator.validate_action(action_name, action_args, purpose)

    def validate_request(self, request: str) -> "ValidationResult":
        """
        Validate a user request before processing.

        Convenience method that prefixes content with "User request: "
        for better context in validation.

        Args:
            request: User request text

        Returns:
            ValidationResult
        """
        return self._validator.validate(f"User request: {request}")

    # =========================================================================
    # Validation 360° Methods
    # =========================================================================

    def validate_input(self, text: str) -> "ValidationResult":
        """
        Validate user input for attack detection (Validation 360°).

        This method is the first part of the 360° validation architecture.
        Use it to validate user input BEFORE sending to the AI model.

        The question being answered: "Is this an ATTACK?"

        Detects:
            - Jailbreak attempts (DAN, ignore instructions, etc.)
            - Prompt injection
            - SQL injection
            - XSS attacks
            - Social engineering patterns

        Args:
            text: User input text to validate

        Returns:
            ValidationResult with mode=INPUT containing:
            - is_safe: True if no attack detected
            - is_attack: True if attack was detected (property)
            - attack_types: List of attack types if detected
            - violations: Descriptions of detected attacks

        Example:
            # In your callback before sending to AI
            input_result = self.validate_input(user_message)
            if input_result.is_attack:
                logger.warning(f"Attack blocked: {input_result.attack_types}")
                return self._create_blocked_response(input_result)
            # Safe to proceed to AI
            ai_response = await self.call_model(user_message)
        """
        return self._validator.validate_input(text)

    def validate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> "ValidationResult":
        """
        Validate AI output for seed failure detection (Validation 360°).

        This method is the second part of the 360° validation architecture.
        Use it to validate AI response AFTER receiving it from the model.

        The question being answered: "Did the SEED fail?"

        Detects:
            - Jailbreak acceptance (AI agreeing to bypass rules)
            - Harmful content in response
            - Deceptive content
            - Bypass indicators

        Args:
            output: AI response text to validate
            input_context: Original user input (for context-aware checking)

        Returns:
            ValidationResult with mode=OUTPUT containing:
            - is_safe: True if seed worked correctly
            - seed_failed: True if AI safety seed failed
            - failure_types: Types of failures detected
            - gates_failed: THSP gates that failed

        Example:
            # After receiving AI response
            output_result = self.validate_output(ai_response, user_message)
            if output_result.seed_failed:
                logger.error(f"Seed failed! Gates: {output_result.gates_failed}")
                return self._create_fallback_response()
            # Safe to return to user
            return ai_response
        """
        return self._validator.validate_output(output, input_context)

    @property
    def validation_stats(self) -> Dict[str, Any]:
        """
        Get validation statistics from the validator.

        Returns:
            Dict with total_validations, blocks, allowed, latency, etc.
        """
        return self._validator.stats

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        if hasattr(self._validator, "reset_stats"):
            self._validator.reset_stats()


class AsyncSentinelIntegration:
    """
    Async version of SentinelIntegration for async frameworks.

    Provides async validation methods for use with asyncio-based
    frameworks like FastAPI, aiohttp, etc.

    This class uses AsyncLayeredValidator internally, which provides
    non-blocking validation suitable for high-concurrency applications.

    Example:
        class AsyncGoogleADKPlugin(AsyncSentinelIntegration):
            _integration_name = "google_adk"

            async def before_model_callback(self, request):
                result = await self.avalidate(request.content)
                if not result.is_safe:
                    return self._create_blocked_response(result)
    """

    # Override in subclasses for better logging
    _integration_name: str = "base_async"

    # Default seed level for this integration
    _default_seed_level: str = "standard"

    def __init__(
        self,
        validator: Optional["AsyncValidator"] = None,
        validation_config: Optional["ValidationConfig"] = None,
        use_v3: bool = True,
        use_embeddings: bool = False,
        seed_level: Optional[str] = None,
        **kwargs: Any,
    ):
        """
        Initialize with AsyncSentinelV3Adapter if no validator provided.

        Args:
            validator: Custom async validator instance
            validation_config: Configuration for validator
            use_v3: Use Sentinel v3.0 adapter (default: True)
            use_embeddings: Enable embedding-based detection
            seed_level: Seed level for system prompt injection. Options:
                       "minimal", "standard", "full". Default: "standard".
            **kwargs: Additional arguments (absorbed for flexibility)
        """
        if validator is not None:
            self._validator: "AsyncValidator" = validator
            logger.debug(
                f"[{self._integration_name}] Using provided validator: "
                f"{type(validator).__name__}"
            )
        elif use_v3:
            # Use Sentinel v3.0 async adapter (recommended)
            from sentinelseed.validation import AsyncSentinelV3Adapter

            self._validator = AsyncSentinelV3Adapter(
                config=validation_config,
                use_embeddings=use_embeddings,
            )
            logger.debug(
                f"[{self._integration_name}] Created AsyncSentinelV3Adapter "
                f"(embeddings={use_embeddings})"
            )
        else:
            # Legacy: Create AsyncLayeredValidator
            from sentinelseed.validation import AsyncLayeredValidator

            if validation_config is not None:
                self._validator = AsyncLayeredValidator(config=validation_config)
                logger.debug(
                    f"[{self._integration_name}] Created AsyncLayeredValidator "
                    f"with custom config (semantic={validation_config.use_semantic})"
                )
            else:
                self._validator = AsyncLayeredValidator()
                logger.debug(
                    f"[{self._integration_name}] Created AsyncLayeredValidator "
                    f"with default config (heuristic only)"
                )

        # Seed configuration (lazy loading)
        self._seed_level = seed_level or self._default_seed_level
        self._seed_cache: Optional[str] = None

    # =========================================================================
    # Seed Injection Methods
    # =========================================================================

    @property
    def seed(self) -> str:
        """
        Get the alignment seed for this integration.

        The seed is lazy-loaded and cached. Use this to inject the seed
        into your model's system prompt.

        Returns:
            The seed content as a string.
        """
        if self._seed_cache is None:
            self._seed_cache = self.get_seed(self._seed_level)
        return self._seed_cache

    def get_seed(self, level: Optional[str] = None) -> str:
        """
        Get an alignment seed by level.

        Args:
            level: Seed level - "minimal", "standard", or "full".
                  If None, uses the instance's configured seed_level.

        Returns:
            The seed content as a string.
        """
        from sentinelseed import Sentinel

        target_level = level or self._seed_level
        sentinel = Sentinel(seed_level=target_level)
        return sentinel.get_seed(target_level)

    def prepare_system_prompt(
        self,
        original_prompt: str = "",
        seed_position: str = "prepend",
    ) -> str:
        """
        Prepare a system prompt with the alignment seed injected.

        This method combines the alignment seed with your original system
        prompt. The seed provides THSP (Truth, Harm, Scope, Purpose) gates
        that help the model refuse harmful requests.

        Args:
            original_prompt: Your original system prompt/instructions.
            seed_position: Where to place the seed:
                          - "prepend": Seed before your prompt (recommended)
                          - "append": Seed after your prompt

        Returns:
            Combined system prompt with seed injected.
        """
        seed_content = self.seed

        if not original_prompt:
            return seed_content

        if seed_position == "append":
            return f"{original_prompt}\n\n{seed_content}"
        else:
            # prepend (default, recommended)
            return f"{seed_content}\n\n{original_prompt}"

    @property
    def seed_level(self) -> str:
        """Get the current seed level."""
        return self._seed_level

    @property
    def validator(self) -> "AsyncValidator":
        """Access the underlying async validator."""
        return self._validator

    async def avalidate(self, content: str) -> "ValidationResult":
        """
        Validate content asynchronously.

        This is the primary async validation method. Use this in async
        contexts like FastAPI route handlers or aiohttp callbacks.

        Args:
            content: Text content to validate

        Returns:
            ValidationResult

        Example:
            async def handle_request(content: str):
                result = await self.avalidate(content)
                if not result.is_safe:
                    raise HTTPException(400, result.violations)
        """
        return await self._validator.validate(content)

    async def avalidate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> "ValidationResult":
        """
        Validate an action asynchronously.

        Args:
            action_name: Name of the action
            action_args: Arguments to the action
            purpose: Stated purpose for the action

        Returns:
            ValidationResult
        """
        return await self._validator.validate_action(action_name, action_args, purpose)

    async def avalidate_request(self, request: str) -> "ValidationResult":
        """
        Validate a user request asynchronously.

        Args:
            request: User request text

        Returns:
            ValidationResult
        """
        return await self._validator.validate(f"User request: {request}")

    # =========================================================================
    # Validation 360° Methods (Async)
    # =========================================================================

    async def avalidate_input(self, text: str) -> "ValidationResult":
        """
        Validate user input for attack detection asynchronously (Validation 360°).

        This method is the first part of the 360° validation architecture.
        Use it to validate user input BEFORE sending to the AI model.

        The question being answered: "Is this an ATTACK?"

        Detects:
            - Jailbreak attempts (DAN, ignore instructions, etc.)
            - Prompt injection
            - SQL injection
            - XSS attacks
            - Social engineering patterns

        Args:
            text: User input text to validate

        Returns:
            ValidationResult with mode=INPUT containing:
            - is_safe: True if no attack detected
            - is_attack: True if attack was detected (property)
            - attack_types: List of attack types if detected
            - violations: Descriptions of detected attacks

        Example:
            async def before_model_callback(self, request):
                input_result = await self.avalidate_input(request.content)
                if input_result.is_attack:
                    logger.warning(f"Attack blocked: {input_result.attack_types}")
                    return self._create_blocked_response(input_result)
                # Safe to proceed
        """
        return await self._validator.validate_input(text)

    async def avalidate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> "ValidationResult":
        """
        Validate AI output for seed failure detection asynchronously (Validation 360°).

        This method is the second part of the 360° validation architecture.
        Use it to validate AI response AFTER receiving it from the model.

        The question being answered: "Did the SEED fail?"

        Detects:
            - Jailbreak acceptance (AI agreeing to bypass rules)
            - Harmful content in response
            - Deceptive content
            - Bypass indicators

        Args:
            output: AI response text to validate
            input_context: Original user input (for context-aware checking)

        Returns:
            ValidationResult with mode=OUTPUT containing:
            - is_safe: True if seed worked correctly
            - seed_failed: True if AI safety seed failed
            - failure_types: Types of failures detected
            - gates_failed: THSP gates that failed

        Example:
            async def after_model_callback(self, response, original_request):
                output_result = await self.avalidate_output(
                    response.content,
                    original_request.content,
                )
                if output_result.seed_failed:
                    logger.error(f"Seed failed! Gates: {output_result.gates_failed}")
                    return self._create_fallback_response()
                return response
        """
        return await self._validator.validate_output(output, input_context)

    def validate_input(self, text: str) -> "ValidationResult":
        """
        Sync validate_input - use avalidate_input() for async code.

        This method provides sync access for backwards compatibility.
        When called from async context, prefer avalidate_input() instead.

        Args:
            text: User input text to validate

        Returns:
            ValidationResult
        """
        import asyncio

        try:
            asyncio.get_running_loop()
            import warnings

            warnings.warn(
                f"[{self._integration_name}] Called sync validate_input() from async context. "
                "Use avalidate_input() instead for better performance.",
                RuntimeWarning,
                stacklevel=2,
            )
            from sentinelseed.validation import LayeredValidator

            sync_validator = LayeredValidator()
            return sync_validator.validate_input(text)
        except RuntimeError:
            return asyncio.run(self.avalidate_input(text))

    def validate_output(
        self,
        output: str,
        input_context: Optional[str] = None,
    ) -> "ValidationResult":
        """
        Sync validate_output - use avalidate_output() for async code.

        This method provides sync access for backwards compatibility.
        When called from async context, prefer avalidate_output() instead.

        Args:
            output: AI response text to validate
            input_context: Original user input

        Returns:
            ValidationResult
        """
        import asyncio

        try:
            asyncio.get_running_loop()
            import warnings

            warnings.warn(
                f"[{self._integration_name}] Called sync validate_output() from async context. "
                "Use avalidate_output() instead for better performance.",
                RuntimeWarning,
                stacklevel=2,
            )
            from sentinelseed.validation import LayeredValidator

            sync_validator = LayeredValidator()
            return sync_validator.validate_output(output, input_context)
        except RuntimeError:
            return asyncio.run(self.avalidate_output(output, input_context))

    def validate(self, content: str) -> "ValidationResult":
        """
        Sync validate - use avalidate() for async code.

        This method provides sync access for backwards compatibility.
        When called from async context, prefer avalidate() instead.

        Note: When called from an async context, this will issue a warning
        and fall back to a sync validator to avoid blocking the event loop.

        Args:
            content: Text content to validate

        Returns:
            ValidationResult
        """
        import asyncio

        try:
            asyncio.get_running_loop()  # Raises RuntimeError if not in async context
            # Already in async context, can't use run_until_complete
            import warnings

            warnings.warn(
                f"[{self._integration_name}] Called sync validate() from async context. "
                "Use avalidate() instead for better performance.",
                RuntimeWarning,
                stacklevel=2,
            )
            # Fall back to sync validator for this case
            from sentinelseed.validation import LayeredValidator

            sync_validator = LayeredValidator()
            return sync_validator.validate(content)
        except RuntimeError:
            # No running loop, safe to create one
            return asyncio.run(self.avalidate(content))

    @property
    def validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics from the validator."""
        return self._validator.stats

    def reset_stats(self) -> None:
        """Reset validation statistics."""
        if hasattr(self._validator, "reset_stats"):
            self._validator.reset_stats()


__all__ = [
    # Base classes
    "SentinelIntegration",
    "AsyncSentinelIntegration",
    # Re-exported validation types for convenience
    "LayeredValidator",
    "AsyncLayeredValidator",
    "ValidationConfig",
    "ValidationResult",
    "ValidationLayer",
    "RiskLevel",
    # v3.0 adapters
    "SentinelV3Adapter",
    "AsyncSentinelV3Adapter",
]
