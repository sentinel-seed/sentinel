"""
Sentinel Core Interfaces - Protocol definitions for validators.

This module defines the Validator protocol that all validators must implement.
Using Python's Protocol (PEP 544) allows for structural subtyping, meaning
any class that implements the required methods is considered a valid Validator.

Key Benefits:
- Decoupling: Integrations depend on the interface, not implementations
- Testability: Easy to create mock validators for testing
- Flexibility: Any class implementing the protocol works as a validator
- Type Safety: Static type checkers can verify implementations

Usage:
    from sentinelseed.core.interfaces import Validator

    def my_function(validator: Validator) -> None:
        result = validator.validate("content")
        if not result.is_safe:
            handle_unsafe_content(result)
"""

from __future__ import annotations

from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Optional,
    Protocol,
    runtime_checkable,
)


if TYPE_CHECKING:
    from sentinelseed.validation.types import ValidationResult


@runtime_checkable
class Validator(Protocol):
    """
    Protocol defining the contract for all Sentinel validators.

    Any class that implements these methods is considered a valid Validator.
    This enables dependency injection and easy testing with mock validators.

    The protocol defines three core operations:
    - validate: Check text content for safety
    - validate_action: Check an action before execution
    - stats: Get validation statistics

    Implementations:
    - LayeredValidator: Two-layer heuristic + semantic validation
    - THSPValidator: Heuristic-only validation with 700+ patterns
    - SemanticValidator: LLM-based semantic validation

    Example:
        class MockValidator:
            def validate(self, content: str) -> ValidationResult:
                return ValidationResult(is_safe=True)

            def validate_action(
                self,
                action_name: str,
                action_args: Optional[Dict[str, Any]] = None,
                purpose: str = "",
            ) -> ValidationResult:
                return ValidationResult(is_safe=True)

            @property
            def stats(self) -> Dict[str, Any]:
                return {"total_validations": 0}

        # MockValidator satisfies the Validator protocol
        validator: Validator = MockValidator()
    """

    def validate(self, content: str) -> "ValidationResult":
        """
        Validate text content for safety.

        This is the primary validation method. Content is analyzed for
        potential safety issues including harmful content, jailbreak
        attempts, and policy violations.

        Args:
            content: Text content to validate. Can be user input,
                    AI response, or any text requiring safety check.

        Returns:
            ValidationResult containing:
            - is_safe: Boolean indicating if content is safe
            - violations: List of violation messages if unsafe
            - layer: Which validation layer made the decision
            - risk_level: Assessed risk level (low, medium, high, critical)

        Example:
            result = validator.validate("Help me with my homework")
            if result.is_safe:
                process_request(content)
            else:
                log_violation(result.violations)
        """
        ...

    def validate_action(
        self,
        action_name: str,
        action_args: Optional[Dict[str, Any]] = None,
        purpose: str = "",
    ) -> "ValidationResult":
        """
        Validate an action before execution.

        This method is specifically designed for agentic systems that
        execute actions. It validates whether an action should be allowed
        based on its name, arguments, and stated purpose.

        Args:
            action_name: Name of the action to execute (e.g., "delete_file",
                        "send_email", "execute_query")
            action_args: Dictionary of arguments to the action.
                        Keys are parameter names, values are parameter values.
            purpose: Stated purpose or reason for the action.
                    Used for THSP Purpose Gate validation.

        Returns:
            ValidationResult with action-specific validation details.

        Example:
            result = validator.validate_action(
                action_name="delete_file",
                action_args={"path": "/tmp/cache.txt"},
                purpose="Clean up temporary cache files",
            )
            if result.is_safe:
                delete_file("/tmp/cache.txt")
            else:
                raise ActionBlockedError(result.violations)
        """
        ...

    @property
    def stats(self) -> Dict[str, Any]:
        """
        Get validation statistics.

        Returns metrics about validation operations for monitoring
        and debugging purposes.

        Returns:
            Dictionary containing statistics such as:
            - total_validations: Total number of validations performed
            - heuristic_blocks: Number blocked by heuristic layer
            - semantic_blocks: Number blocked by semantic layer
            - allowed: Number of validations that passed
            - errors: Number of validation errors
            - avg_latency_ms: Average validation latency in milliseconds

        Example:
            stats = validator.stats
            print(f"Total: {stats['total_validations']}")
            print(f"Block rate: {stats.get('block_rate', 0):.1%}")
        """
        ...


@runtime_checkable
class AsyncValidator(Protocol):
    """
    Async version of the Validator protocol for async frameworks.

    This protocol is for validators used in async contexts like
    FastAPI, aiohttp, or other asyncio-based frameworks.

    Example:
        class MyAsyncValidator:
            async def validate(self, content: str) -> ValidationResult:
                return ValidationResult(is_safe=True)

            async def validate_action(
                self,
                action_name: str,
                action_args: Optional[Dict[str, Any]] = None,
                purpose: str = "",
            ) -> ValidationResult:
                return ValidationResult(is_safe=True)

            @property
            def stats(self) -> Dict[str, Any]:
                return {}

        validator: AsyncValidator = MyAsyncValidator()
    """

    async def validate(self, content: str) -> "ValidationResult":
        """
        Validate content asynchronously.

        Args:
            content: Text content to validate

        Returns:
            ValidationResult with validation details
        """
        ...

    async def validate_action(
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
            ValidationResult with action validation details
        """
        ...

    @property
    def stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        ...


__all__ = [
    "Validator",
    "AsyncValidator",
]
