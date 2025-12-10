"""
Solana Agent Kit integration for Sentinel AI.

Provides safety layer for Solana blockchain agents:
- SentinelPlugin: Plugin for Solana Agent Kit with safety validation
- SentinelSafetyMiddleware: Middleware for transaction validation
- safe_transaction: Decorator for protected transaction execution

This integration adds AI safety guardrails to autonomous crypto agents,
preventing harmful on-chain actions and validating transaction intent.

Usage:
    from sentinel.integrations.solana_agent_kit import SentinelPlugin

    # Add to your Solana agent
    agent = SolanaAgentKit(wallet, rpc_url)
    agent.use(SentinelPlugin())
"""

from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from sentinel import Sentinel, SeedLevel


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


class SentinelPlugin:
    """
    Sentinel safety plugin for Solana Agent Kit.

    Integrates with Solana Agent Kit's plugin system to provide
    safety validation for all blockchain transactions.

    Key features:
    - Pre-transaction validation
    - High-value transfer alerts
    - Suspicious pattern detection
    - Action intent verification

    Example:
        from solana_agent_kit import SolanaAgentKit
        from sentinel.integrations.solana_agent_kit import SentinelPlugin

        agent = SolanaAgentKit(wallet, rpc_url)
        agent.use(SentinelPlugin(
            max_single_transfer=10.0,  # SOL
            require_confirmation_above=5.0,
            block_suspicious=True,
        ))
    """

    name = "sentinel-safety"
    description = "AI safety validation for Solana transactions"

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        max_single_transfer: float = 100.0,  # SOL
        require_confirmation_above: float = 10.0,  # SOL
        block_suspicious: bool = True,
        allowed_programs: Optional[List[str]] = None,
        blocked_addresses: Optional[List[str]] = None,
    ):
        """
        Initialize plugin.

        Args:
            sentinel: Sentinel instance
            seed_level: Seed level for validation
            max_single_transfer: Maximum SOL per transaction
            require_confirmation_above: Require confirmation above this amount
            block_suspicious: Whether to block suspicious transactions
            allowed_programs: Whitelist of allowed program IDs
            blocked_addresses: Blacklist of blocked addresses
        """
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.max_single_transfer = max_single_transfer
        self.require_confirmation_above = require_confirmation_above
        self.block_suspicious = block_suspicious
        self.allowed_programs = allowed_programs or []
        self.blocked_addresses = blocked_addresses or []
        self.transaction_history: List[TransactionSafetyResult] = []

    def validate_transaction(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> TransactionSafetyResult:
        """
        Validate a transaction before execution.

        Args:
            action: Transaction action name
            params: Transaction parameters

        Returns:
            TransactionSafetyResult with validation details
        """
        concerns = []
        recommendations = []
        risk_level = TransactionRisk.LOW

        # Extract common parameters
        amount = params.get("amount", 0)
        recipient = params.get("recipient", params.get("to", ""))
        program_id = params.get("program_id", "")

        # Check for blocked addresses
        if recipient in self.blocked_addresses:
            concerns.append(f"Recipient address is blocked: {recipient[:8]}...")
            risk_level = TransactionRisk.CRITICAL

        # Check for allowed programs (if whitelist exists)
        if self.allowed_programs and program_id:
            if program_id not in self.allowed_programs:
                concerns.append(f"Program not in whitelist: {program_id[:8]}...")
                risk_level = TransactionRisk.HIGH

        # Check transfer amounts
        if amount > self.max_single_transfer:
            concerns.append(f"Transfer exceeds maximum: {amount} > {self.max_single_transfer}")
            risk_level = TransactionRisk.CRITICAL

        # Check if confirmation needed
        requires_confirmation = amount > self.require_confirmation_above

        # Validate action intent with Sentinel
        action_description = self._format_action_description(action, params)
        is_safe, sentinel_concerns = self.sentinel.validate_action(action_description)

        if not is_safe:
            concerns.extend(sentinel_concerns)
            risk_level = TransactionRisk.HIGH

        # Check for suspicious patterns
        suspicious = self._check_suspicious_patterns(action, params)
        if suspicious:
            concerns.extend(suspicious)
            risk_level = max(risk_level, TransactionRisk.MEDIUM, key=lambda x: x.value)

        # Determine if should proceed
        should_proceed = risk_level not in [TransactionRisk.CRITICAL]
        if self.block_suspicious and risk_level == TransactionRisk.HIGH:
            should_proceed = False

        # Generate recommendations
        if requires_confirmation:
            recommendations.append("High-value transaction: manual confirmation recommended")
        if risk_level in [TransactionRisk.HIGH, TransactionRisk.CRITICAL]:
            recommendations.append("Review transaction details carefully before proceeding")

        result = TransactionSafetyResult(
            safe=len(concerns) == 0,
            risk_level=risk_level,
            transaction_type=action,
            concerns=concerns,
            recommendations=recommendations,
            should_proceed=should_proceed,
            requires_confirmation=requires_confirmation,
        )

        self.transaction_history.append(result)
        return result

    def _format_action_description(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> str:
        """Format action for Sentinel validation."""
        # Clean sensitive data
        safe_params = {
            k: v for k, v in params.items()
            if k not in ["private_key", "secret", "mnemonic"]
        }

        # Truncate addresses
        for key in ["recipient", "to", "from", "address", "mint"]:
            if key in safe_params and isinstance(safe_params[key], str):
                safe_params[key] = safe_params[key][:8] + "..."

        return f"Solana {action}: {safe_params}"

    def _check_suspicious_patterns(
        self,
        action: str,
        params: Dict[str, Any],
    ) -> List[str]:
        """Check for suspicious transaction patterns."""
        suspicious = []

        action_lower = action.lower()

        # Suspicious action patterns
        if "drain" in action_lower:
            suspicious.append("Potential wallet drain operation")
        if "all" in action_lower and "transfer" in action_lower:
            suspicious.append("Bulk transfer operation detected")
        if "approve" in action_lower and "unlimited" in str(params).lower():
            suspicious.append("Unlimited approval request")

        # Check for suspicious amounts
        amount = params.get("amount", 0)
        if isinstance(amount, (int, float)):
            # Very round numbers can be suspicious
            if amount > 0 and amount == int(amount) and amount >= 100:
                suspicious.append("Large round number transfer")

        # Check memo/data for suspicious content
        memo = params.get("memo", "") or params.get("data", "")
        if memo:
            memo_check = self.sentinel.validate_request(str(memo))
            if not memo_check["should_proceed"]:
                suspicious.append(f"Suspicious memo content: {memo_check['concerns']}")

        return suspicious

    def get_safety_report(self) -> Dict[str, Any]:
        """Get safety statistics for the session."""
        if not self.transaction_history:
            return {"total_transactions": 0}

        blocked = sum(1 for t in self.transaction_history if not t.should_proceed)
        high_risk = sum(1 for t in self.transaction_history
                       if t.risk_level in [TransactionRisk.HIGH, TransactionRisk.CRITICAL])

        return {
            "total_transactions": len(self.transaction_history),
            "blocked": blocked,
            "approved": len(self.transaction_history) - blocked,
            "high_risk": high_risk,
            "low_risk": len(self.transaction_history) - high_risk,
            "block_rate": blocked / len(self.transaction_history),
        }


class SentinelSafetyMiddleware:
    """
    Middleware for Solana Agent Kit transaction validation.

    Wraps the agent's transaction methods to add safety checks.

    Example:
        middleware = SentinelSafetyMiddleware()

        # Wrap agent methods
        original_transfer = agent.transfer
        agent.transfer = middleware.wrap(original_transfer, "transfer")
    """

    def __init__(
        self,
        plugin: Optional[SentinelPlugin] = None,
    ):
        """Initialize middleware."""
        self.plugin = plugin or SentinelPlugin()

    def wrap(
        self,
        method: Callable,
        action_name: str,
    ) -> Callable:
        """
        Wrap a method with safety validation.

        Args:
            method: Original method to wrap
            action_name: Name of the action for logging

        Returns:
            Wrapped method with safety checks
        """
        def wrapper(*args, **kwargs):
            # Build params from args/kwargs
            params = kwargs.copy()
            if args:
                params["_args"] = args

            # Validate
            result = self.plugin.validate_transaction(action_name, params)

            if not result.should_proceed:
                raise TransactionBlockedError(
                    f"Transaction blocked by Sentinel: {result.concerns}"
                )

            if result.requires_confirmation:
                print(f"[SENTINEL] High-value transaction: {action_name}")
                print(f"  Risk level: {result.risk_level.value}")
                print(f"  Recommendations: {result.recommendations}")
                # In production, this would prompt for confirmation

            # Execute original method
            return method(*args, **kwargs)

        return wrapper


class TransactionBlockedError(Exception):
    """Raised when a transaction is blocked by Sentinel."""
    pass


def safe_transaction(
    action: str,
    params: Dict[str, Any],
    plugin: Optional[SentinelPlugin] = None,
) -> TransactionSafetyResult:
    """
    Standalone safety check for a transaction.

    Convenience function for quick validation without full plugin setup.

    Args:
        action: Transaction action name
        params: Transaction parameters
        plugin: Optional SentinelPlugin instance

    Returns:
        TransactionSafetyResult

    Example:
        from sentinel.integrations.solana_agent_kit import safe_transaction

        result = safe_transaction("transfer", {
            "amount": 50,
            "recipient": "ABC123...",
        })

        if result.should_proceed:
            # Execute transaction
            pass
        else:
            print(f"Blocked: {result.concerns}")
    """
    if plugin is None:
        plugin = SentinelPlugin()

    return plugin.validate_transaction(action, params)


def create_sentinel_actions() -> Dict[str, Callable]:
    """
    Create Sentinel safety actions for Solana Agent Kit.

    Returns a dictionary of actions that can be added to an agent's toolkit.

    Example:
        from sentinel.integrations.solana_agent_kit import create_sentinel_actions

        safety_actions = create_sentinel_actions()
        # Add to your agent's available actions
    """
    plugin = SentinelPlugin()

    def check_transaction_safety(
        action: str,
        amount: float = 0,
        recipient: str = "",
        **kwargs
    ) -> Dict[str, Any]:
        """Check if a transaction is safe to execute."""
        params = {
            "amount": amount,
            "recipient": recipient,
            **kwargs
        }
        result = plugin.validate_transaction(action, params)
        return {
            "safe": result.safe,
            "should_proceed": result.should_proceed,
            "risk_level": result.risk_level.value,
            "concerns": result.concerns,
            "recommendations": result.recommendations,
        }

    def get_safety_seed() -> str:
        """Get Sentinel alignment seed for agent system prompt."""
        return plugin.sentinel.get_seed()

    def validate_intent(description: str) -> Dict[str, Any]:
        """Validate an action intent description."""
        is_safe, concerns = plugin.sentinel.validate_action(description)
        request_check = plugin.sentinel.validate_request(description)

        return {
            "safe": is_safe and request_check["should_proceed"],
            "concerns": concerns + request_check.get("concerns", []),
            "risk_level": request_check["risk_level"],
        }

    return {
        "sentinel_check_transaction": check_transaction_safety,
        "sentinel_get_seed": get_safety_seed,
        "sentinel_validate_intent": validate_intent,
    }


# Type definitions for Solana Agent Kit compatibility
SolanaAction = Dict[str, Any]


def create_langchain_tools():
    """
    Create LangChain-compatible tools for Solana Agent Kit.

    These tools can be used with LangChain agents that interact
    with Solana through the Agent Kit.

    Example:
        from sentinel.integrations.solana_agent_kit import create_langchain_tools

        tools = create_langchain_tools()
        agent = create_react_agent(llm, tools=[...existing_tools, *tools])
    """
    try:
        from langchain.tools import Tool
    except ImportError:
        raise ImportError("langchain is required for create_langchain_tools")

    plugin = SentinelPlugin()

    def check_solana_transaction(action_description: str) -> str:
        """Check if a Solana transaction is safe."""
        # Parse action description
        parts = action_description.split(":")
        action = parts[0].strip() if parts else "unknown"
        params_str = parts[1].strip() if len(parts) > 1 else "{}"

        try:
            import json
            params = json.loads(params_str)
        except (json.JSONDecodeError, IndexError):
            params = {"description": action_description}

        result = plugin.validate_transaction(action, params)

        if result.should_proceed:
            return f"SAFE: Transaction '{action}' validated. Risk level: {result.risk_level.value}"
        else:
            return f"BLOCKED: {result.concerns}. Recommendations: {result.recommendations}"

    return [
        Tool(
            name="sentinel_solana_safety",
            description=(
                "Check if a Solana blockchain transaction is safe before executing. "
                "Input format: 'action_name: {\"amount\": X, \"recipient\": \"...\"}' "
                "Use this before any token transfers, swaps, or other on-chain actions."
            ),
            func=check_solana_transaction,
        ),
    ]
