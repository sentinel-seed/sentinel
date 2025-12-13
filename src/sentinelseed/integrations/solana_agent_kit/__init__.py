"""
Solana Agent Kit integration for Sentinel AI.

Provides safety validation for Solana blockchain agents. This integration
works alongside Solana Agent Kit to validate transactions before execution.

IMPORTANT: Solana Agent Kit uses a plugin system that adds ACTIONS to agents,
not middleware that intercepts transactions. This integration provides:

1. Standalone validation functions (use before any transaction)
2. LangChain tools (add to agent toolkit for self-validation)
3. Action wrappers (for Python-based validation flows)

Usage patterns:

    # Pattern 1: Explicit validation before transactions
    from sentinelseed.integrations.solana_agent_kit import safe_transaction

    result = safe_transaction("transfer", {"amount": 50, "recipient": "..."})
    if result.should_proceed:
        # Execute your Solana Agent Kit transaction
        pass

    # Pattern 2: LangChain tools for agent self-validation
    from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

    safety_tools = create_langchain_tools()
    # Add to your LangChain agent's toolkit

    # Pattern 3: Validation in custom actions
    from sentinelseed.integrations.solana_agent_kit import SentinelValidator

    validator = SentinelValidator()
    # Use in your custom Solana Agent Kit actions
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel


class TransactionRisk(Enum):
    """Risk levels for blockchain transactions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TransactionSafetyResult:
    """Result of transaction safety validation."""
    safe: bool
    risk_level: TransactionRisk
    transaction_type: str
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    should_proceed: bool = True
    requires_confirmation: bool = False


class SentinelValidator:
    """
    Safety validator for Solana Agent Kit transactions.

    Use this class to validate transactions before executing them
    with Solana Agent Kit. This is NOT a plugin - Solana Agent Kit
    plugins add actions, they don't intercept transactions.

    Example:
        from solana_agent_kit import SolanaAgentKit
        from sentinelseed.integrations.solana_agent_kit import SentinelValidator

        # Initialize both
        agent = SolanaAgentKit(wallet, rpc_url, config)
        validator = SentinelValidator(max_transfer=10.0)

        # Validate before executing
        result = validator.check("transfer", amount=5.0, recipient="ABC...")
        if result.should_proceed:
            agent.transfer(recipient, amount)
        else:
            print(f"Blocked: {result.concerns}")
    """

    # Default actions that require explicit purpose
    DEFAULT_REQUIRE_PURPOSE = [
        "transfer", "send", "approve", "swap", "bridge", "withdraw", "stake",
    ]

    def __init__(
        self,
        seed_level: str = "standard",
        max_transfer: float = 100.0,
        confirm_above: float = 10.0,
        blocked_addresses: Optional[List[str]] = None,
        allowed_programs: Optional[List[str]] = None,
        require_purpose_for: Optional[List[str]] = None,
        memory_integrity_check: bool = False,
        memory_secret_key: Optional[str] = None,
    ):
        """
        Initialize validator.

        Args:
            seed_level: Sentinel seed level ("minimal", "standard", "full")
            max_transfer: Maximum SOL per single transaction
            confirm_above: Require confirmation for amounts above this
            blocked_addresses: List of blocked wallet addresses
            allowed_programs: Whitelist of allowed program IDs (empty = all allowed)
            require_purpose_for: Actions that require explicit purpose/reason
            memory_integrity_check: Enable memory integrity verification
            memory_secret_key: Secret key for memory HMAC (required if memory_integrity_check=True)
        """
        self.sentinel = Sentinel(seed_level=seed_level)
        self.max_transfer = max_transfer
        self.confirm_above = confirm_above
        self.blocked_addresses = set(blocked_addresses or [])
        self.allowed_programs = set(allowed_programs or [])
        self.require_purpose_for = require_purpose_for or self.DEFAULT_REQUIRE_PURPOSE
        self.memory_integrity_check = memory_integrity_check
        self.memory_secret_key = memory_secret_key
        self.history: List[TransactionSafetyResult] = []

        # Initialize memory checker if enabled
        self._memory_checker = None
        if memory_integrity_check:
            try:
                from sentinelseed.memory import MemoryIntegrityChecker
                self._memory_checker = MemoryIntegrityChecker(
                    secret_key=memory_secret_key,
                    strict_mode=False,
                )
            except ImportError:
                pass  # Memory module not available

    def check(
        self,
        action: str,
        amount: float = 0,
        recipient: str = "",
        program_id: str = "",
        memo: str = "",
        purpose: str = "",
        **kwargs
    ) -> TransactionSafetyResult:
        """
        Check if a transaction is safe to execute.

        Args:
            action: Action name (transfer, swap, stake, etc.)
            amount: Transaction amount in SOL
            recipient: Recipient address
            program_id: Program ID being called
            memo: Transaction memo/data
            purpose: Explicit purpose/reason for the transaction
            **kwargs: Additional parameters

        Returns:
            TransactionSafetyResult with validation details
        """
        concerns = []
        recommendations = []
        risk_level = TransactionRisk.LOW

        # Check blocked addresses
        if recipient and recipient in self.blocked_addresses:
            concerns.append(f"Recipient is blocked: {recipient[:8]}...")
            risk_level = TransactionRisk.CRITICAL

        # Check program whitelist
        if self.allowed_programs and program_id:
            if program_id not in self.allowed_programs:
                concerns.append(f"Program not whitelisted: {program_id[:8]}...")
                risk_level = TransactionRisk.HIGH

        # Check transfer limits
        if amount > self.max_transfer:
            concerns.append(f"Amount {amount} exceeds limit {self.max_transfer}")
            risk_level = TransactionRisk.CRITICAL

        # PURPOSE GATE: Check if action requires explicit purpose
        requires_purpose = any(
            keyword.lower() in action.lower()
            for keyword in self.require_purpose_for
        )
        if requires_purpose and not purpose and not kwargs.get("reason"):
            concerns.append(
                f"Action '{action}' requires explicit purpose/reason "
                f"(set purpose= or reason= parameter)"
            )
            if risk_level.value < TransactionRisk.MEDIUM.value:
                risk_level = TransactionRisk.MEDIUM

        requires_confirmation = amount > self.confirm_above

        # Validate intent with Sentinel
        description = self._describe_action(action, amount, recipient, kwargs)
        is_safe, sentinel_concerns = self.sentinel.validate_action(description)

        if not is_safe:
            concerns.extend(sentinel_concerns)
            if risk_level.value < TransactionRisk.HIGH.value:
                risk_level = TransactionRisk.HIGH

        # Check suspicious patterns
        suspicious = self._check_patterns(action, amount, memo)
        if suspicious:
            concerns.extend(suspicious)
            if risk_level.value < TransactionRisk.MEDIUM.value:
                risk_level = TransactionRisk.MEDIUM

        # Determine if should proceed
        should_proceed = risk_level not in [TransactionRisk.CRITICAL, TransactionRisk.HIGH]

        # Add recommendations
        if requires_confirmation:
            recommendations.append("High-value: manual confirmation recommended")
        if risk_level in [TransactionRisk.HIGH, TransactionRisk.CRITICAL]:
            recommendations.append("Review transaction details before proceeding")
        if requires_purpose and not purpose:
            recommendations.append(f"Provide purpose= for {action} actions")

        result = TransactionSafetyResult(
            safe=len(concerns) == 0,
            risk_level=risk_level,
            transaction_type=action,
            concerns=concerns,
            recommendations=recommendations,
            should_proceed=should_proceed,
            requires_confirmation=requires_confirmation,
        )

        self.history.append(result)
        return result

    def _describe_action(
        self,
        action: str,
        amount: float,
        recipient: str,
        extra: Dict
    ) -> str:
        """Create description for Sentinel validation."""
        parts = [f"Solana {action}"]
        if amount:
            parts.append(f"amount={amount}")
        if recipient:
            parts.append(f"to={recipient[:8]}...")
        return " ".join(parts)

    def _check_patterns(
        self,
        action: str,
        amount: float,
        memo: str
    ) -> List[str]:
        """Check for suspicious transaction patterns."""
        suspicious = []
        action_lower = action.lower()

        # Drain patterns
        if "drain" in action_lower or "sweep" in action_lower:
            suspicious.append("Potential drain operation detected")

        # Bulk operations
        if "all" in action_lower and ("transfer" in action_lower or "send" in action_lower):
            suspicious.append("Bulk transfer operation")

        # Unlimited approvals
        if "approve" in action_lower and amount == 0:
            suspicious.append("Potential unlimited approval")

        # Suspicious memo
        if memo:
            memo_check = self.sentinel.validate_request(memo)
            if not memo_check.get("should_proceed", True):
                suspicious.append("Suspicious memo content")

        return suspicious

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self.history:
            return {"total": 0}

        blocked = sum(1 for r in self.history if not r.should_proceed)
        high_risk = sum(1 for r in self.history
                       if r.risk_level in [TransactionRisk.HIGH, TransactionRisk.CRITICAL])

        return {
            "total": len(self.history),
            "blocked": blocked,
            "approved": len(self.history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(self.history),
        }

    def clear_history(self) -> None:
        """Clear validation history."""
        self.history = []


def safe_transaction(
    action: str,
    params: Optional[Dict[str, Any]] = None,
    validator: Optional[SentinelValidator] = None,
    **kwargs
) -> TransactionSafetyResult:
    """
    Validate a Solana transaction before execution.

    This is a convenience function for quick validation without
    setting up a full validator instance.

    Args:
        action: Transaction action (transfer, swap, stake, etc.)
        params: Transaction parameters dict
        validator: Optional existing validator
        **kwargs: Transaction parameters as keyword args

    Returns:
        TransactionSafetyResult

    Example:
        from sentinelseed.integrations.solana_agent_kit import safe_transaction

        # Before executing with Solana Agent Kit
        result = safe_transaction("transfer", amount=5.0, recipient="ABC...")

        if result.should_proceed:
            agent.transfer(recipient, amount)
        else:
            print(f"Blocked: {result.concerns}")
    """
    if validator is None:
        validator = SentinelValidator()

    # Merge params dict with kwargs
    all_params = {**(params or {}), **kwargs}

    return validator.check(
        action=action,
        amount=all_params.get("amount", 0),
        recipient=all_params.get("recipient", all_params.get("to", "")),
        program_id=all_params.get("program_id", ""),
        memo=all_params.get("memo", ""),
        **{k: v for k, v in all_params.items()
           if k not in ["amount", "recipient", "to", "program_id", "memo"]}
    )


def create_sentinel_actions(
    validator: Optional[SentinelValidator] = None
) -> Dict[str, Callable]:
    """
    Create Sentinel validation actions.

    These functions can be used in your custom Solana Agent Kit
    actions or workflows to add safety validation.

    Args:
        validator: Optional existing validator

    Returns:
        Dict of action functions

    Example:
        from sentinelseed.integrations.solana_agent_kit import create_sentinel_actions

        actions = create_sentinel_actions()

        # In your code
        result = actions["validate_transfer"](50.0, "ABC123...")
        if result["safe"]:
            # proceed
            pass
    """
    if validator is None:
        validator = SentinelValidator()

    def validate_transfer(amount: float, recipient: str) -> Dict[str, Any]:
        """Validate a token transfer."""
        result = validator.check("transfer", amount=amount, recipient=recipient)
        return {
            "safe": result.should_proceed,
            "risk": result.risk_level.value,
            "concerns": result.concerns,
        }

    def validate_swap(
        amount: float,
        from_token: str = "SOL",
        to_token: str = ""
    ) -> Dict[str, Any]:
        """Validate a token swap."""
        result = validator.check(
            "swap",
            amount=amount,
            memo=f"{from_token} -> {to_token}"
        )
        return {
            "safe": result.should_proceed,
            "risk": result.risk_level.value,
            "concerns": result.concerns,
        }

    def validate_action(action: str, **params) -> Dict[str, Any]:
        """Validate any action."""
        result = validator.check(action, **params)
        return {
            "safe": result.should_proceed,
            "risk": result.risk_level.value,
            "concerns": result.concerns,
            "recommendations": result.recommendations,
        }

    def get_safety_seed() -> str:
        """Get Sentinel seed for agent system prompt."""
        return validator.sentinel.get_seed()

    return {
        "validate_transfer": validate_transfer,
        "validate_swap": validate_swap,
        "validate_action": validate_action,
        "get_safety_seed": get_safety_seed,
    }


def create_langchain_tools(
    validator: Optional[SentinelValidator] = None
):
    """
    Create LangChain tools for Solana transaction validation.

    Add these tools to your LangChain agent's toolkit so the agent
    can self-validate actions before executing them.

    Args:
        validator: Optional existing validator

    Returns:
        List of LangChain Tool objects

    Example:
        from langchain.agents import create_react_agent
        from solana_agent_kit import createSolanaTools
        from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

        # Get Solana tools
        solana_tools = createSolanaTools(agent)

        # Add Sentinel safety tools
        safety_tools = create_langchain_tools()

        # Combine for agent
        all_tools = solana_tools + safety_tools
        agent = create_react_agent(llm, all_tools)
    """
    try:
        from langchain.tools import Tool
    except ImportError:
        raise ImportError(
            "langchain is required: pip install langchain"
        )

    if validator is None:
        validator = SentinelValidator()

    def check_transaction(description: str) -> str:
        """
        Check if a Solana transaction is safe.

        Input format: "action amount recipient"
        Examples:
          - "transfer 5.0 ABC123..."
          - "swap 10.0"
          - "stake 100.0"
        """
        parts = description.strip().split()
        action = parts[0] if parts else "unknown"
        amount = float(parts[1]) if len(parts) > 1 else 0
        recipient = parts[2] if len(parts) > 2 else ""

        result = validator.check(action, amount=amount, recipient=recipient)

        if result.should_proceed:
            msg = f"SAFE: {action} validated"
            if result.requires_confirmation:
                msg += " (high-value: confirm recommended)"
            return msg
        else:
            return f"BLOCKED: {', '.join(result.concerns)}"

    return [
        Tool(
            name="sentinel_check_transaction",
            description=(
                "Check if a Solana transaction is safe before executing. "
                "Input: 'action amount recipient' (e.g., 'transfer 5.0 ABC123'). "
                "Use BEFORE any transfer, swap, or on-chain action."
            ),
            func=check_transaction,
        ),
    ]


# Simple exception for blocked transactions
class TransactionBlockedError(Exception):
    """Raised when a transaction is blocked by Sentinel validation."""
    pass


class SentinelSafetyMiddleware:
    """
    Wrapper for adding safety checks to function calls.

    Note: This is NOT a Solana Agent Kit middleware (SAK doesn't have
    middleware). This wraps Python functions with validation.

    Example:
        from sentinelseed.integrations.solana_agent_kit import SentinelSafetyMiddleware

        middleware = SentinelSafetyMiddleware()

        # Wrap any function
        def my_transfer(amount, recipient):
            # your transfer logic
            pass

        safe_transfer = middleware.wrap(my_transfer, "transfer")

        # Now calls are validated
        safe_transfer(5.0, "ABC...")  # Validates before executing
    """

    def __init__(self, validator: Optional[SentinelValidator] = None):
        self.validator = validator or SentinelValidator()

    def wrap(self, func: Callable, action_name: str) -> Callable:
        """
        Wrap a function with safety validation.

        Args:
            func: Function to wrap
            action_name: Name for validation logging

        Returns:
            Wrapped function that validates before executing
        """
        def wrapper(*args, **kwargs):
            # Extract params for validation
            amount = kwargs.get("amount", args[0] if args else 0)
            recipient = kwargs.get("recipient", kwargs.get("to", ""))
            if not recipient and len(args) > 1:
                recipient = args[1]

            result = self.validator.check(
                action_name,
                amount=amount if isinstance(amount, (int, float)) else 0,
                recipient=str(recipient) if recipient else "",
            )

            if not result.should_proceed:
                raise ValueError(
                    f"Transaction blocked: {', '.join(result.concerns)}"
                )

            if result.requires_confirmation:
                print(f"[SENTINEL] High-value {action_name}: {amount}")

            return func(*args, **kwargs)

        return wrapper
