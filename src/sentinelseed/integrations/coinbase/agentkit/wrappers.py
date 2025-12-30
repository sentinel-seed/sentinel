"""
Action Wrappers for Sentinel AgentKit Integration.

Provides decorators and utilities to wrap AgentKit actions with
Sentinel safety validation automatically.

This enables transparent safety validation without modifying
existing action code.

Example:
    from sentinelseed.integrations.coinbase.agentkit import safe_action

    @safe_action(action_type="native_transfer")
    async def transfer_tokens(to: str, amount: float):
        # Your transfer logic here
        pass
"""

from __future__ import annotations

import functools
import json
import logging
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from ..config import ChainType, SentinelCoinbaseConfig, get_default_config
from ..validators.transaction import TransactionValidator

logger = logging.getLogger("sentinelseed.coinbase.wrappers")

F = TypeVar("F", bound=Callable[..., Any])


class ActionBlockedError(Exception):
    """
    Raised when an action is blocked by Sentinel validation.

    Attributes:
        action: The action that was blocked
        reason: The reason for blocking
        concerns: List of concerns identified
    """

    def __init__(
        self,
        action: str,
        reason: str,
        concerns: list = None,
    ):
        self.action = action
        self.reason = reason
        self.concerns = concerns or []
        super().__init__(f"Action '{action}' blocked: {reason}")


class SentinelActionWrapper:
    """
    Wrapper class for adding Sentinel validation to actions.

    Can be used to wrap individual functions or entire classes.

    Example:
        wrapper = SentinelActionWrapper()

        # Wrap a function
        safe_transfer = wrapper.wrap(transfer_func, "native_transfer")

        # Or use as decorator
        @wrapper.wrap_decorator("approve")
        def approve_tokens(spender: str, amount: int):
            pass
    """

    def __init__(
        self,
        config: Optional[SentinelCoinbaseConfig] = None,
        default_chain: ChainType = ChainType.BASE_MAINNET,
        block_on_failure: bool = True,
        log_validations: bool = True,
    ):
        """
        Initialize the action wrapper.

        Args:
            config: Security configuration
            default_chain: Default blockchain network
            block_on_failure: If True, raise exception on validation failure
            log_validations: If True, log all validations
        """
        self.config = config or get_default_config()
        self.default_chain = default_chain
        self.block_on_failure = block_on_failure
        self.log_validations = log_validations
        self.validator = TransactionValidator(config=self.config)

    def wrap(
        self,
        func: F,
        action_type: str,
        amount_param: str = "amount",
        to_param: str = "to",
        from_param: str = "from_address",
    ) -> F:
        """
        Wrap a function with Sentinel validation.

        Args:
            func: The function to wrap
            action_type: The action type for validation
            amount_param: Parameter name for amount
            to_param: Parameter name for recipient
            from_param: Parameter name for sender

        Returns:
            Wrapped function with validation
        """

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Extract parameters
            amount = kwargs.get(amount_param, 0)
            to_address = kwargs.get(to_param, kwargs.get("to_address", ""))
            from_address = kwargs.get(from_param, kwargs.get("wallet_address", ""))

            # Handle positional args (common pattern: to, amount)
            if not to_address and len(args) > 0:
                to_address = args[0] if isinstance(args[0], str) else ""
            if not amount and len(args) > 1:
                amount = args[1] if isinstance(args[1], (int, float)) else 0

            # Validate
            result = self.validator.validate(
                action=action_type,
                from_address=from_address or "0x" + "0" * 40,
                to_address=to_address or None,
                amount=float(amount) if amount else 0,
                chain=self.default_chain,
            )

            if self.log_validations:
                status = "APPROVED" if result.is_approved else "BLOCKED"
                logger.info(
                    f"Sentinel [{status}] {action_type}: "
                    f"amount=${amount}, to={to_address[:10] if to_address else 'N/A'}..."
                )

            if not result.is_approved:
                if self.block_on_failure:
                    raise ActionBlockedError(
                        action=action_type,
                        reason=result.blocked_reason or "Validation failed",
                        concerns=result.concerns,
                    )
                else:
                    logger.warning(
                        f"Action {action_type} would be blocked: {result.concerns}"
                    )

            if result.requires_confirmation:
                logger.warning(
                    f"High-value transaction requires confirmation: ${amount}"
                )

            # Execute the original function
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            # Same validation logic
            amount = kwargs.get(amount_param, 0)
            to_address = kwargs.get(to_param, kwargs.get("to_address", ""))
            from_address = kwargs.get(from_param, kwargs.get("wallet_address", ""))

            if not to_address and len(args) > 0:
                to_address = args[0] if isinstance(args[0], str) else ""
            if not amount and len(args) > 1:
                amount = args[1] if isinstance(args[1], (int, float)) else 0

            result = self.validator.validate(
                action=action_type,
                from_address=from_address or "0x" + "0" * 40,
                to_address=to_address or None,
                amount=float(amount) if amount else 0,
                chain=self.default_chain,
            )

            if self.log_validations:
                status = "APPROVED" if result.is_approved else "BLOCKED"
                logger.info(
                    f"Sentinel [{status}] {action_type}: "
                    f"amount=${amount}, to={to_address[:10] if to_address else 'N/A'}..."
                )

            if not result.is_approved:
                if self.block_on_failure:
                    raise ActionBlockedError(
                        action=action_type,
                        reason=result.blocked_reason or "Validation failed",
                        concerns=result.concerns,
                    )
                else:
                    logger.warning(
                        f"Action {action_type} would be blocked: {result.concerns}"
                    )

            # Execute the original async function
            return await func(*args, **kwargs)

        # Return appropriate wrapper
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper  # type: ignore

    def wrap_decorator(
        self,
        action_type: str,
        amount_param: str = "amount",
        to_param: str = "to",
        from_param: str = "from_address",
    ) -> Callable[[F], F]:
        """
        Create a decorator for wrapping functions.

        Args:
            action_type: The action type for validation
            amount_param: Parameter name for amount
            to_param: Parameter name for recipient
            from_param: Parameter name for sender

        Returns:
            Decorator function

        Example:
            wrapper = SentinelActionWrapper()

            @wrapper.wrap_decorator("transfer")
            def transfer_tokens(to: str, amount: float):
                pass
        """
        def decorator(func: F) -> F:
            return self.wrap(
                func,
                action_type=action_type,
                amount_param=amount_param,
                to_param=to_param,
                from_param=from_param,
            )
        return decorator

    def record_transaction(self, from_address: str, amount: float) -> None:
        """Record a completed transaction for spending tracking."""
        self.validator.record_completed_transaction(from_address, amount)

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        return self.validator.get_validation_stats()


# Global default wrapper for convenience
_default_wrapper: Optional[SentinelActionWrapper] = None


def _get_default_wrapper() -> SentinelActionWrapper:
    """Get or create the default wrapper."""
    global _default_wrapper
    if _default_wrapper is None:
        _default_wrapper = SentinelActionWrapper()
    return _default_wrapper


def safe_action(
    action_type: str,
    amount_param: str = "amount",
    to_param: str = "to",
    from_param: str = "from_address",
    config: Optional[SentinelCoinbaseConfig] = None,
) -> Callable[[F], F]:
    """
    Decorator to wrap a function with Sentinel safety validation.

    This is the simplest way to add safety validation to existing code.

    Args:
        action_type: The action type for validation (e.g., "transfer", "approve")
        amount_param: Parameter name for amount
        to_param: Parameter name for recipient
        from_param: Parameter name for sender
        config: Optional custom configuration

    Returns:
        Decorator function

    Example:
        from sentinelseed.integrations.coinbase.agentkit import safe_action

        @safe_action(action_type="native_transfer")
        def transfer_eth(to: str, amount: float, from_address: str = None):
            # Transfer logic here
            pass

        # This will validate before executing:
        transfer_eth("0x456...", 50.0, from_address="0x123...")
    """
    def decorator(func: F) -> F:
        if config:
            wrapper = SentinelActionWrapper(config=config)
        else:
            wrapper = _get_default_wrapper()

        return wrapper.wrap(
            func,
            action_type=action_type,
            amount_param=amount_param,
            to_param=to_param,
            from_param=from_param,
        )
    return decorator


def create_safe_action_wrapper(
    security_profile: str = "standard",
    chain: str = "base-mainnet",
    block_on_failure: bool = True,
) -> SentinelActionWrapper:
    """
    Create a configured action wrapper.

    Args:
        security_profile: One of "permissive", "standard", "strict", "paranoid"
        chain: The default blockchain network
        block_on_failure: Whether to block on validation failure

    Returns:
        Configured SentinelActionWrapper

    Example:
        wrapper = create_safe_action_wrapper(
            security_profile="strict",
            chain="ethereum-mainnet",
        )

        @wrapper.wrap_decorator("approve")
        def approve_tokens(spender: str, amount: int):
            pass
    """
    config = get_default_config(security_profile)

    # Parse chain
    try:
        chain_type = ChainType(chain)
    except ValueError:
        chain_type = ChainType.BASE_MAINNET

    return SentinelActionWrapper(
        config=config,
        default_chain=chain_type,
        block_on_failure=block_on_failure,
    )


__all__ = [
    "ActionBlockedError",
    "SentinelActionWrapper",
    "safe_action",
    "create_safe_action_wrapper",
]
