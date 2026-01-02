"""
Transaction Validation for Coinbase AgentKit.

Provides comprehensive transaction validation including:
- Spending limits (per-transaction, daily, hourly)
- Blocked addresses
- Rate limiting
- Approval detection (unlimited approvals)
- Chain-aware validation

This is the core validator for financial transactions
performed by AI agents using Coinbase AgentKit.
"""

from __future__ import annotations

import logging
import re
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set

import warnings

from ..config import (
    ChainType,
    RiskLevel,
    SentinelCoinbaseConfig,
    SpendingLimits,
    get_default_config,
)
from .address import is_valid_evm_address, validate_address

# Fiduciary validation for user-aligned decision making
try:
    from sentinelseed.fiduciary import (
        FiduciaryValidator,
        FiduciaryResult,
        UserContext,
        RiskTolerance,
    )
    HAS_FIDUCIARY = True
except ImportError:
    HAS_FIDUCIARY = False
    FiduciaryValidator = None
    FiduciaryResult = None
    UserContext = None
    RiskTolerance = None

logger = logging.getLogger("sentinelseed.coinbase.transaction")


# Default user context for Coinbase/EVM transactions
def _get_default_coinbase_context() -> "UserContext":
    """Get default UserContext for Coinbase/EVM transactions."""
    if not HAS_FIDUCIARY:
        return None
    return UserContext(
        goals=[
            "protect assets",
            "minimize transaction fees",
            "maintain portfolio balance",
        ],
        constraints=[
            "avoid unlimited approvals",
            "respect spending limits",
            "verify recipient addresses",
        ],
        risk_tolerance=RiskTolerance.MODERATE,
        preferences={
            "require_explanation": True,
            "max_single_transaction": 500,
            "require_purpose_for_high_value": True,
        },
        sensitive_topics=[
            "private_key",
            "seed_phrase",
            "wallet_balance",
            "transaction_history",
        ],
    )


class TransactionDecision(Enum):
    """Decision for a transaction validation."""

    APPROVE = "approve"              # Safe to proceed
    APPROVE_WITH_CONFIRMATION = "approve_with_confirmation"  # Needs human approval
    REJECT = "reject"                # Should not proceed
    BLOCK = "block"                  # Absolutely blocked


@dataclass
class TransactionValidationResult:
    """
    Result of transaction validation.

    Attributes:
        decision: The validation decision
        risk_level: Assessed risk level
        concerns: List of identified concerns
        recommendations: Suggested actions
        requires_confirmation: Whether human confirmation is needed
        blocked_reason: Reason for blocking (if blocked)
        validation_details: Detailed validation results per check
    """

    decision: TransactionDecision
    risk_level: RiskLevel
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    blocked_reason: Optional[str] = None
    validation_details: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_approved(self) -> bool:
        """Check if transaction is approved (possibly with confirmation)."""
        return self.decision in (
            TransactionDecision.APPROVE,
            TransactionDecision.APPROVE_WITH_CONFIRMATION,
        )

    @property
    def should_proceed(self) -> bool:
        """Check if transaction should proceed automatically."""
        return self.decision == TransactionDecision.APPROVE


# Maximum uint256 value (used for unlimited approvals)
MAX_UINT256 = 2**256 - 1
MAX_UINT256_HEX = "0x" + "f" * 64

# Patterns for detecting suspicious approval amounts
UNLIMITED_APPROVAL_PATTERNS = [
    re.compile(r"^115792089237316195423570985008687907853269984665640564039457584007913129639935$"),  # MAX_UINT256 decimal
    re.compile(r"^0x[fF]{64}$"),  # MAX_UINT256 hex
    re.compile(r"^-1$"),  # Sometimes -1 is used
]


@dataclass
class SpendingTracker:
    """
    Tracks spending across transactions for rate limiting.

    Thread-safe implementation for tracking:
    - Hourly spending
    - Daily spending
    - Transaction counts
    """

    # Spending by wallet address
    hourly_spending: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    daily_spending: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    hourly_tx_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    daily_tx_count: Dict[str, int] = field(default_factory=lambda: defaultdict(int))

    # Timestamps for reset
    hourly_reset: Dict[str, float] = field(default_factory=dict)
    daily_reset: Dict[str, float] = field(default_factory=dict)

    def _check_reset(self, wallet: str) -> None:
        """Check and reset counters if needed."""
        if wallet is None:
            return
        now = time.time()
        wallet_lower = wallet.lower()

        # Check hourly reset
        if wallet_lower not in self.hourly_reset:
            self.hourly_reset[wallet_lower] = now
        elif now - self.hourly_reset[wallet_lower] >= 3600:
            self.hourly_spending[wallet_lower] = 0.0
            self.hourly_tx_count[wallet_lower] = 0
            self.hourly_reset[wallet_lower] = now

        # Check daily reset
        if wallet_lower not in self.daily_reset:
            self.daily_reset[wallet_lower] = now
        elif now - self.daily_reset[wallet_lower] >= 86400:
            self.daily_spending[wallet_lower] = 0.0
            self.daily_tx_count[wallet_lower] = 0
            self.daily_reset[wallet_lower] = now

    def record_transaction(self, wallet: str, amount: float) -> None:
        """Record a completed transaction."""
        if wallet is None:
            return
        wallet_lower = wallet.lower()
        self._check_reset(wallet_lower)

        self.hourly_spending[wallet_lower] += amount
        self.daily_spending[wallet_lower] += amount
        self.hourly_tx_count[wallet_lower] += 1
        self.daily_tx_count[wallet_lower] += 1

    def get_hourly_spent(self, wallet: str) -> float:
        """Get total spent in current hour."""
        if wallet is None:
            return 0.0
        wallet_lower = wallet.lower()
        self._check_reset(wallet_lower)
        return self.hourly_spending[wallet_lower]

    def get_daily_spent(self, wallet: str) -> float:
        """Get total spent today."""
        if wallet is None:
            return 0.0
        wallet_lower = wallet.lower()
        self._check_reset(wallet_lower)
        return self.daily_spending[wallet_lower]

    def get_hourly_tx_count(self, wallet: str) -> int:
        """Get transaction count in current hour."""
        if wallet is None:
            return 0
        wallet_lower = wallet.lower()
        self._check_reset(wallet_lower)
        return self.hourly_tx_count[wallet_lower]

    def get_daily_tx_count(self, wallet: str) -> int:
        """Get transaction count today."""
        if wallet is None:
            return 0
        wallet_lower = wallet.lower()
        self._check_reset(wallet_lower)
        return self.daily_tx_count[wallet_lower]

    def get_summary(self, wallet: str) -> Dict[str, Any]:
        """Get spending summary for a wallet."""
        if wallet is None:
            return {
                "hourly_spent": 0.0,
                "daily_spent": 0.0,
                "hourly_tx_count": 0,
                "daily_tx_count": 0,
            }
        wallet_lower = wallet.lower()
        self._check_reset(wallet_lower)

        return {
            "hourly_spent": self.hourly_spending[wallet_lower],
            "daily_spent": self.daily_spending[wallet_lower],
            "hourly_tx_count": self.hourly_tx_count[wallet_lower],
            "daily_tx_count": self.daily_tx_count[wallet_lower],
        }

    def reset(self, wallet: Optional[str] = None) -> None:
        """Reset counters for a wallet or all wallets."""
        if wallet:
            wallet_lower = wallet.lower()
            self.hourly_spending[wallet_lower] = 0.0
            self.daily_spending[wallet_lower] = 0.0
            self.hourly_tx_count[wallet_lower] = 0
            self.daily_tx_count[wallet_lower] = 0
            self.hourly_reset[wallet_lower] = time.time()
            self.daily_reset[wallet_lower] = time.time()
        else:
            self.hourly_spending.clear()
            self.daily_spending.clear()
            self.hourly_tx_count.clear()
            self.daily_tx_count.clear()
            self.hourly_reset.clear()
            self.daily_reset.clear()


class TransactionValidator:
    """
    Main transaction validator for Coinbase AgentKit.

    Validates transactions against:
    - Spending limits (configurable per chain)
    - Blocked addresses
    - Rate limits
    - Unlimited approval detection
    - Address format validation

    Example:
        from sentinelseed.integrations.coinbase.validators import TransactionValidator

        validator = TransactionValidator()

        result = validator.validate(
            action="native_transfer",
            from_address="0x123...",
            to_address="0x456...",
            amount=50.0,
            chain=ChainType.BASE_MAINNET,
        )

        if result.should_proceed:
            # Execute transaction
            pass
        elif result.requires_confirmation:
            # Ask user for confirmation
            pass
        else:
            print(f"Blocked: {result.blocked_reason}")
    """

    def __init__(
        self,
        config: Optional[SentinelCoinbaseConfig] = None,
        # Fiduciary validation parameters
        fiduciary_enabled: bool = True,
        user_context: Optional["UserContext"] = None,
        strict_fiduciary: bool = False,
    ):
        """
        Initialize the transaction validator.

        Args:
            config: Configuration object. Uses default if not provided.
            fiduciary_enabled: Enable fiduciary validation (duty of loyalty/care). Default True.
            user_context: UserContext for fiduciary validation. Uses Coinbase defaults if not provided.
            strict_fiduciary: If True, any fiduciary violation blocks the transaction.

        Fiduciary Validation:
            When enabled, validates that transactions align with user's best interests.
            This includes checking for:
            - Actions that contradict user's stated goals
            - High-risk actions for low-risk-tolerance users
            - Potential conflicts of interest
            - Insufficient explanations for recommendations
        """
        self.config = config or get_default_config()
        self.spending_tracker = SpendingTracker()
        self._validation_history: List[TransactionValidationResult] = []

        # Initialize fiduciary validator if enabled
        self._fiduciary: Optional[FiduciaryValidator] = None
        self._user_context: Optional[UserContext] = None
        self._strict_fiduciary = strict_fiduciary

        if fiduciary_enabled and HAS_FIDUCIARY:
            self._fiduciary = FiduciaryValidator(strict_mode=strict_fiduciary)
            self._user_context = user_context or _get_default_coinbase_context()
            logger.debug("Fiduciary validator initialized")
        elif fiduciary_enabled and not HAS_FIDUCIARY:
            warnings.warn(
                "fiduciary_enabled=True but sentinelseed.fiduciary module not available. "
                "Fiduciary validation will be disabled.",
                RuntimeWarning,
            )
            logger.warning("Fiduciary module not available")

    def validate(
        self,
        action: str,
        from_address: str,
        to_address: Optional[str] = None,
        amount: float = 0.0,
        chain: ChainType = ChainType.BASE_MAINNET,
        token_address: Optional[str] = None,
        approval_amount: Optional[str] = None,
        purpose: Optional[str] = None,
        **kwargs: Any,
    ) -> TransactionValidationResult:
        """
        Validate a transaction.

        Args:
            action: The action type (native_transfer, transfer, approve, etc.)
            from_address: The sender address
            to_address: The recipient address (if applicable)
            amount: The transaction amount in USD equivalent
            chain: The blockchain network
            token_address: Token contract address (for ERC20/ERC721)
            approval_amount: Approval amount (for approve actions)
            purpose: Stated purpose for the transaction
            **kwargs: Additional parameters

        Returns:
            TransactionValidationResult with decision and details
        """
        concerns: List[str] = []
        recommendations: List[str] = []
        details: Dict[str, Any] = {
            "action": action,
            "from_address": from_address,
            "to_address": to_address,
            "amount": amount,
            "chain": chain.value,
        }

        # Get chain-specific config
        chain_config = self.config.get_chain_config(chain)
        limits = chain_config.spending_limits

        # 1. Validate sender address
        if from_address:
            sender_result = validate_address(from_address, require_checksum=False)
            if not sender_result.valid:
                return self._create_blocked_result(
                    f"Invalid sender address: {sender_result.status.value}",
                    concerns,
                    details,
                )
            if sender_result.warnings:
                recommendations.extend(sender_result.warnings)

        # 2. Validate recipient address
        if to_address:
            recipient_result = validate_address(to_address, require_checksum=False)
            if not recipient_result.valid:
                return self._create_blocked_result(
                    f"Invalid recipient address: {recipient_result.status.value}",
                    concerns,
                    details,
                )
            if recipient_result.warnings:
                recommendations.extend(recipient_result.warnings)

            # Check if recipient is blocked
            if self.config.is_address_blocked(to_address):
                return self._create_blocked_result(
                    "Recipient address is blocked",
                    concerns,
                    details,
                )

        # 3. Check if action is allowed
        if not self.config.is_action_allowed(action):
            return self._create_blocked_result(
                f"Action '{action}' is not allowed",
                concerns,
                details,
            )

        # 4. Check spending limits
        if amount > 0:
            # Single transaction limit
            if limits.exceeds_single(amount):
                return self._create_blocked_result(
                    f"Amount ${amount:.2f} exceeds single transaction limit ${limits.max_single_transaction:.2f}",
                    concerns,
                    details,
                )

            # Spending limits require from_address to track per-wallet limits
            if from_address:
                # Hourly limit
                hourly_spent = self.spending_tracker.get_hourly_spent(from_address)
                if hourly_spent + amount > limits.max_hourly_total:
                    concerns.append(
                        f"Would exceed hourly limit: ${hourly_spent + amount:.2f} > ${limits.max_hourly_total:.2f}"
                    )
                    details["hourly_spent"] = hourly_spent

                # Daily limit
                daily_spent = self.spending_tracker.get_daily_spent(from_address)
                if daily_spent + amount > limits.max_daily_total:
                    concerns.append(
                        f"Would exceed daily limit: ${daily_spent + amount:.2f} > ${limits.max_daily_total:.2f}"
                    )
                    details["daily_spent"] = daily_spent

        # 5. Check rate limits (require from_address to track per-wallet limits)
        if from_address:
            hourly_tx = self.spending_tracker.get_hourly_tx_count(from_address)
            if hourly_tx >= limits.max_transactions_per_hour:
                concerns.append(
                    f"Hourly transaction limit reached: {hourly_tx}/{limits.max_transactions_per_hour}"
                )

            daily_tx = self.spending_tracker.get_daily_tx_count(from_address)
            if daily_tx >= limits.max_transactions_per_day:
                concerns.append(
                    f"Daily transaction limit reached: {daily_tx}/{limits.max_transactions_per_day}"
                )

        # 6. Check for unlimited approvals
        if action.lower() == "approve" and approval_amount:
            if self._is_unlimited_approval(approval_amount):
                if self.config.block_unlimited_approvals:
                    return self._create_blocked_result(
                        "Unlimited token approval detected - this is a security risk",
                        concerns,
                        details,
                    )
                else:
                    concerns.append("Unlimited token approval detected - high risk")
                    recommendations.append("Consider using a specific approval amount")

        # 7. Check purpose requirement
        if self.config.require_purpose_for_transfers:
            if self.config.is_high_risk_action(action) and not purpose:
                concerns.append(f"High-risk action '{action}' requires stated purpose")
                recommendations.append("Provide a purpose parameter explaining the transaction")

        # 7.5 Fiduciary validation: check if action aligns with user's best interests
        fiduciary_blocked = False
        if self._fiduciary is not None:
            # Build action description for fiduciary validation
            fid_action = f"{action} ${amount:.2f}"
            if to_address:
                fid_action += f" to {to_address[:8]}..."
            if purpose:
                fid_action += f" ({purpose})"

            fid_result = self._fiduciary.validate_action(
                action=fid_action,
                user_context=self._user_context,
                proposed_outcome={"amount": amount, "to_address": to_address, **kwargs},
            )

            if not fid_result.compliant:
                # Add fiduciary violations as concerns
                for violation in fid_result.violations:
                    concern = f"[Fiduciary/{violation.duty.value}] {violation.description}"
                    concerns.append(concern)
                    if violation.is_blocking():
                        fiduciary_blocked = True

                logger.info(f"Fiduciary validation concerns: {len(fid_result.violations)}")

            # In strict fiduciary mode, any violation blocks
            if self._strict_fiduciary and fid_result.violations:
                fiduciary_blocked = True

        # 8. Determine risk level
        risk_level = self._assess_risk_level(action, amount, concerns, chain)
        details["risk_level"] = risk_level.value

        # 9. Determine decision
        requires_confirmation = False

        # 9.1 Check fiduciary blocking first (highest priority)
        if fiduciary_blocked:
            return self._create_result(
                TransactionDecision.REJECT,
                RiskLevel.HIGH if risk_level.value < RiskLevel.HIGH.value else risk_level,
                concerns,
                recommendations + ["Review fiduciary concerns before proceeding"],
                details,
                requires_confirmation=False,
            )

        if concerns:
            # Has concerns but not blocking
            if any("limit reached" in c.lower() for c in concerns):
                return self._create_result(
                    TransactionDecision.REJECT,
                    risk_level,
                    concerns,
                    recommendations,
                    details,
                    requires_confirmation=False,
                )

            if amount > 0 and limits.requires_confirmation(amount):
                requires_confirmation = True

            if self.config.require_confirmation_for_high_value and requires_confirmation:
                return self._create_result(
                    TransactionDecision.APPROVE_WITH_CONFIRMATION,
                    risk_level,
                    concerns,
                    recommendations,
                    details,
                    requires_confirmation=True,
                )

            # Approve with warnings
            return self._create_result(
                TransactionDecision.APPROVE,
                risk_level,
                concerns,
                recommendations,
                details,
            )

        # No concerns - check if confirmation still needed
        if amount > 0 and limits.requires_confirmation(amount):
            if self.config.require_confirmation_for_high_value:
                return self._create_result(
                    TransactionDecision.APPROVE_WITH_CONFIRMATION,
                    RiskLevel.MEDIUM,
                    [],
                    ["High-value transaction - confirmation recommended"],
                    details,
                    requires_confirmation=True,
                )

        # All clear
        return self._create_result(
            TransactionDecision.APPROVE,
            risk_level,
            concerns,
            recommendations,
            details,
        )

    def record_completed_transaction(
        self,
        from_address: str,
        amount: float,
    ) -> None:
        """
        Record a completed transaction for spending tracking.

        Call this after a transaction is successfully executed.

        Args:
            from_address: The sender address
            amount: The transaction amount in USD equivalent
        """
        self.spending_tracker.record_transaction(from_address, amount)
        logger.debug(f"Recorded transaction: {from_address[:10]}... ${amount:.2f}")

    def get_spending_summary(self, wallet: str) -> Dict[str, Any]:
        """Get spending summary for a wallet."""
        summary = self.spending_tracker.get_summary(wallet)
        chain_config = self.config.get_chain_config(ChainType.BASE_MAINNET)
        limits = chain_config.spending_limits

        return {
            **summary,
            "hourly_limit": limits.max_hourly_total,
            "daily_limit": limits.max_daily_total,
            "hourly_remaining": max(0, limits.max_hourly_total - summary["hourly_spent"]),
            "daily_remaining": max(0, limits.max_daily_total - summary["daily_spent"]),
        }

    def reset_spending(self, wallet: Optional[str] = None) -> None:
        """Reset spending counters."""
        self.spending_tracker.reset(wallet)

    def _is_unlimited_approval(self, amount: str) -> bool:
        """Check if an approval amount is effectively unlimited."""
        if not amount:
            return False

        amount_str = str(amount).strip()

        # Check against known patterns
        for pattern in UNLIMITED_APPROVAL_PATTERNS:
            if pattern.match(amount_str):
                return True

        # Check numeric value
        try:
            value = int(amount_str, 16) if amount_str.startswith("0x") else int(amount_str)
            # If greater than 1 trillion tokens (with 18 decimals), consider unlimited
            if value >= 10**30:
                return True
        except (ValueError, TypeError):
            pass

        return False

    def _assess_risk_level(
        self,
        action: str,
        amount: float,
        concerns: List[str],
        chain: ChainType,
    ) -> RiskLevel:
        """Assess the overall risk level of a transaction."""
        # Critical concerns
        if concerns and any("blocked" in c.lower() for c in concerns):
            return RiskLevel.CRITICAL

        # High risk actions
        if self.config.is_high_risk_action(action):
            if amount > 500:
                return RiskLevel.CRITICAL
            elif amount > 100:
                return RiskLevel.HIGH
            elif amount > 25:
                return RiskLevel.MEDIUM
            return RiskLevel.LOW

        # Safe actions
        if self.config.is_safe_action(action):
            return RiskLevel.LOW

        # Default based on amount
        if amount > 500:
            return RiskLevel.HIGH
        elif amount > 100:
            return RiskLevel.MEDIUM

        return RiskLevel.LOW

    def _create_blocked_result(
        self,
        reason: str,
        concerns: List[str],
        details: Dict[str, Any],
    ) -> TransactionValidationResult:
        """Create a blocked validation result."""
        return TransactionValidationResult(
            decision=TransactionDecision.BLOCK,
            risk_level=RiskLevel.CRITICAL,
            concerns=concerns + [reason],
            blocked_reason=reason,
            validation_details=details,
        )

    def _create_result(
        self,
        decision: TransactionDecision,
        risk_level: RiskLevel,
        concerns: List[str],
        recommendations: List[str],
        details: Dict[str, Any],
        requires_confirmation: bool = False,
    ) -> TransactionValidationResult:
        """Create a validation result."""
        result = TransactionValidationResult(
            decision=decision,
            risk_level=risk_level,
            concerns=concerns,
            recommendations=recommendations,
            requires_confirmation=requires_confirmation,
            validation_details=details,
        )

        # Store in history
        self._validation_history.append(result)
        if len(self._validation_history) > self.config.max_history_size:
            self._validation_history.pop(0)

        return result

    def get_validation_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self._validation_history:
            return {"total": 0}

        approved = sum(1 for r in self._validation_history if r.is_approved)
        blocked = sum(1 for r in self._validation_history if r.decision == TransactionDecision.BLOCK)
        rejected = sum(1 for r in self._validation_history if r.decision == TransactionDecision.REJECT)

        return {
            "total": len(self._validation_history),
            "approved": approved,
            "blocked": blocked,
            "rejected": rejected,
            "approval_rate": approved / len(self._validation_history),
        }

    def get_fiduciary_stats(self) -> Dict[str, Any]:
        """
        Get statistics about fiduciary validation.

        Returns:
            Dict with fiduciary stats:
                - enabled: Whether fiduciary validation is enabled
                - strict: Whether strict fiduciary mode is enabled
                - validator_stats: Stats from FiduciaryValidator (if enabled)

        Example:
            stats = validator.get_fiduciary_stats()
            if stats["enabled"]:
                print(f"Fiduciary validations: {stats['validator_stats']['total_validated']}")
        """
        if self._fiduciary is None:
            return {"enabled": False}

        return {
            "enabled": True,
            "strict": self._strict_fiduciary,
            "validator_stats": self._fiduciary.get_stats(),
        }

    def update_user_context(self, user_context: "UserContext") -> None:
        """
        Update the user context for fiduciary validation.

        Use this to adjust fiduciary validation based on user preferences
        or profile changes at runtime.

        Args:
            user_context: New UserContext to use for validation

        Example:
            from sentinelseed.fiduciary import UserContext, RiskTolerance

            # Update to high-risk tolerance for experienced user
            validator.update_user_context(UserContext(
                risk_tolerance=RiskTolerance.HIGH,
                goals=["maximize returns"],
            ))
        """
        if self._fiduciary is None:
            warnings.warn(
                "Cannot update user_context: fiduciary validation is not enabled",
                RuntimeWarning,
            )
            return

        self._user_context = user_context
        logger.debug("User context updated for fiduciary validation")


def validate_transaction(
    action: str,
    from_address: str,
    to_address: Optional[str] = None,
    amount: float = 0.0,
    chain: ChainType = ChainType.BASE_MAINNET,
    **kwargs: Any,
) -> TransactionValidationResult:
    """
    Convenience function for one-off transaction validation.

    Args:
        action: The action type
        from_address: The sender address
        to_address: The recipient address
        amount: The transaction amount in USD
        chain: The blockchain network
        **kwargs: Additional parameters

    Returns:
        TransactionValidationResult

    Example:
        result = validate_transaction(
            action="native_transfer",
            from_address="0x123...",
            to_address="0x456...",
            amount=50.0,
        )
    """
    validator = TransactionValidator()
    return validator.validate(
        action=action,
        from_address=from_address,
        to_address=to_address,
        amount=amount,
        chain=chain,
        **kwargs,
    )


__all__ = [
    "TransactionDecision",
    "TransactionValidationResult",
    "SpendingTracker",
    "TransactionValidator",
    "validate_transaction",
    "MAX_UINT256",
    "MAX_UINT256_HEX",
]
