"""
Base class for all Sentinel integrations.

This module provides SentinelIntegration and AsyncSentinelIntegration,
the foundation classes for all framework-specific integrations.

By inheriting from these base classes, integrations automatically get:

1. THSP validation (Truth, Harm, Scope, Purpose gates)
2. Layered validation (heuristic 580+ patterns + optional semantic)
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

    def __init__(
        self,
        validator: Optional["Validator"] = None,
        validation_config: Optional["ValidationConfig"] = None,
        **kwargs: Any,
    ):
        """
        Initialize the integration with validation support.

        This constructor handles all validation setup. Subclasses should
        call super().__init__(**kwargs) to inherit this functionality.

        Args:
            validator: Custom validator instance. If provided, takes precedence
                      over validation_config. Useful for testing with mocks.
            validation_config: Configuration for LayeredValidator.
                              If None, uses default config (heuristic only).
            **kwargs: Additional arguments (absorbed for flexibility).

        Priority:
            1. validator (if provided) - used directly
            2. validation_config (if provided) - creates LayeredValidator
            3. Neither - creates LayeredValidator with defaults (heuristic only)

        Example:
            # Default - heuristic only, no API needed
            integration = MyIntegration()

            # With semantic validation
            config = ValidationConfig(use_semantic=True, semantic_api_key="sk-...")
            integration = MyIntegration(validation_config=config)

            # With mock for testing
            integration = MyIntegration(validator=MockValidator())
        """
        if validator is not None:
            # User provided custom validator (could be mock for testing)
            self._validator = validator
            logger.debug(
                f"[{self._integration_name}] Using provided validator: "
                f"{type(validator).__name__}"
            )
        else:
            # Create LayeredValidator
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

    def __init__(
        self,
        validator: Optional["AsyncValidator"] = None,
        validation_config: Optional["ValidationConfig"] = None,
        **kwargs: Any,
    ):
        """
        Initialize with AsyncLayeredValidator if no validator provided.

        Args:
            validator: Custom async validator instance
            validation_config: Configuration for AsyncLayeredValidator
            **kwargs: Additional arguments (absorbed for flexibility)
        """
        if validator is not None:
            self._validator: "AsyncValidator" = validator
            logger.debug(
                f"[{self._integration_name}] Using provided validator: "
                f"{type(validator).__name__}"
            )
        else:
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
]
