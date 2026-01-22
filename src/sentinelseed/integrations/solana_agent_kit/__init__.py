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

Documentation: https://github.com/sentinel-seed/sentinel/tree/main/src/sentinelseed/integrations/solana_agent_kit
"""

__version__ = "2.1.0"
__author__ = "Sentinel Team"

from typing import Any, Dict, List, Optional, Callable, Union, Set
from dataclasses import dataclass, field
from enum import Enum
import json
import logging
import math
import re
import warnings

from sentinelseed import Sentinel
from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
    ValidationResult,
)

# Fiduciary validation for user-aligned decision making
try:
    from sentinelseed.fiduciary import (
        FiduciaryValidator,
        FiduciaryResult,
        UserContext,
        RiskTolerance,
        Violation,
    )
    HAS_FIDUCIARY = True
except (ImportError, AttributeError):
    HAS_FIDUCIARY = False
    FiduciaryValidator = None
    FiduciaryResult = None
    UserContext = None
    RiskTolerance = None

logger = logging.getLogger("sentinelseed.solana_agent_kit")


# Default user context for Solana transactions
# This ensures fiduciary validation considers typical Solana user concerns
def _get_default_solana_context() -> "UserContext":
    """Get default UserContext for Solana transactions."""
    if not HAS_FIDUCIARY:
        return None
    return UserContext(
        goals=[
            "protect SOL holdings",
            "minimize slippage on swaps",
            "avoid scam tokens",
        ],
        constraints=[
            "avoid drain operations",
            "respect transfer limits",
            "verify program IDs",
        ],
        risk_tolerance=RiskTolerance.MODERATE,
        preferences={
            "require_explanation": True,
            "max_transfer_sol": 100.0,
            "check_token_security": True,
        },
        sensitive_topics=[
            "private_key",
            "seed_phrase",
            "wallet_address",
            "token_holdings",
        ],
    )


# Allowed metadata keys to prevent injection via arbitrary metadata
# Only these keys are included in validation text
ALLOWED_METADATA_KEYS: Set[str] = {
    "fromToken",
    "toToken",
    "slippage",
    "protocol",
    "expectedAPY",
    "bridge",
    "fromChain",
    "toChain",
    "tokenSymbol",
    "tokenName",
    "decimals",
}


def _sanitize_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Filter metadata to only allowed keys with primitive values.

    This prevents injection attacks via arbitrary metadata fields.

    Args:
        metadata: Raw metadata dictionary

    Returns:
        Sanitized dictionary with only allowed keys and primitive values
    """
    if not metadata or not isinstance(metadata, dict):
        return {}

    sanitized = {}
    for key, value in metadata.items():
        if key in ALLOWED_METADATA_KEYS:
            # Only allow primitive values (str, int, float, bool)
            if isinstance(value, (str, int, float, bool)):
                sanitized[key] = value
    return sanitized


# Solana address validation
# Solana addresses are base58 encoded, 32-44 characters
# Valid characters: 123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz
BASE58_PATTERN = re.compile(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$')


def is_valid_solana_address(address: str) -> bool:
    """
    Validate Solana address format (base58, 32-44 chars).

    This is a format check only - does not verify the address exists on-chain.

    Args:
        address: The address string to validate

    Returns:
        True if address matches Solana base58 format
    """
    if not address or not isinstance(address, str):
        return False
    return bool(BASE58_PATTERN.match(address))


class AddressValidationMode(Enum):
    """How to handle invalid Solana addresses."""
    IGNORE = "ignore"      # Don't validate addresses
    WARN = "warn"          # Log warning but allow
    STRICT = "strict"      # Reject invalid addresses


class TransactionRisk(Enum):
    """Risk levels for blockchain transactions."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

    def __lt__(self, other):
        if isinstance(other, TransactionRisk):
            return self.value < other.value
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, TransactionRisk):
            return self.value <= other.value
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, TransactionRisk):
            return self.value > other.value
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, TransactionRisk):
            return self.value >= other.value
        return NotImplemented


@dataclass
class SuspiciousPattern:
    """Pattern definition for detecting suspicious behavior."""
    name: str
    pattern: str  # Regex pattern string
    risk_level: TransactionRisk
    message: str
    _compiled: Optional[re.Pattern] = field(default=None, repr=False, compare=False)

    def __post_init__(self):
        """Pre-compile the regex pattern for performance."""
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.IGNORECASE)

    def matches(self, text: str) -> bool:
        """Check if pattern matches the given text using pre-compiled regex."""
        if self._compiled is None:
            self._compiled = re.compile(self.pattern, re.IGNORECASE)
        return bool(self._compiled.search(text))


# Default suspicious patterns for crypto transactions
# SECURITY: All patterns use word boundaries (\b) to prevent false positives
# and avoid ReDoS vulnerabilities (no unbounded .* quantifiers)
#
# Crypto-specific patterns only. THSP jailbreak detection is handled by
# THSPValidator from sentinelseed.validators.gates (the source of truth).
# Do not duplicate jailbreak patterns here - use validate_message() for full THSP check.
DEFAULT_SUSPICIOUS_PATTERNS: List[SuspiciousPattern] = [
    # === CRYPTO-SPECIFIC PATTERNS (unique to Solana) ===
    SuspiciousPattern(
        name="drain_operation",
        pattern=r"\b(?:drain|sweep|empty)\b",
        risk_level=TransactionRisk.CRITICAL,
        message="Potential drain operation detected",
    ),
    SuspiciousPattern(
        name="unlimited_approval",
        pattern=r"\b(?:unlimited|infinite)\s+(?:approv|access|permission)",
        risk_level=TransactionRisk.HIGH,
        message="Unlimited approval request detected",
    ),
    SuspiciousPattern(
        name="bulk_transfer",
        pattern=r"\b(?:send|transfer)\s+(?:all|entire|whole)\b",
        risk_level=TransactionRisk.HIGH,
        message="Bulk transfer operation detected",
    ),
    SuspiciousPattern(
        name="private_key_exposure",
        pattern=r"\b(?:private\s+key|secret\s+key|seed\s+phrase|mnemonic)\b",
        risk_level=TransactionRisk.CRITICAL,
        message="Potential private key exposure in transaction data",
    ),
    SuspiciousPattern(
        name="suspicious_urgency",
        pattern=r"\b(?:urgent|immediately|right\s+now|asap)\b",
        risk_level=TransactionRisk.MEDIUM,
        message="Suspicious urgency language detected",
    ),
    # Note: For full jailbreak/prompt injection detection, use validate_message()
    # which calls THSPValidator from sentinelseed.validators.gates
]

# High-risk action keywords that always trigger blocking
HIGH_RISK_ACTIONS = [
    "drain", "sweep", "transferall", "sendall",
    "approveunlimited", "infiniteapproval",
]


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


class SentinelValidator(SentinelIntegration):
    """
    Safety validator for Solana Agent Kit transactions.

    Use this class to validate transactions before executing them
    with Solana Agent Kit. This is NOT a plugin - Solana Agent Kit
    plugins add actions, they don't intercept transactions.

    Inherits from SentinelIntegration for standardized validation via
    LayeredValidator.

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

    _integration_name = "solana_agent_kit"

    # Default actions that require explicit purpose
    DEFAULT_REQUIRE_PURPOSE = [
        "transfer", "send", "swap", "approve", "bridge", "withdraw", "stake",
    ]

    def __init__(
        self,
        seed_level: str = "standard",
        max_transfer: float = 100.0,
        confirm_above: float = 10.0,
        blocked_addresses: Optional[List[str]] = None,
        allowed_programs: Optional[List[str]] = None,
        require_purpose_for: Optional[List[str]] = None,
        max_history_size: int = 1000,
        memory_integrity_check: bool = False,
        memory_secret_key: Optional[str] = None,
        memory_content_validation: bool = True,
        address_validation: Union[str, AddressValidationMode] = AddressValidationMode.STRICT,
        strict_mode: bool = False,
        custom_patterns: Optional[List[SuspiciousPattern]] = None,
        on_validation: Optional[Callable[[TransactionSafetyResult], None]] = None,
        validator: Optional[LayeredValidator] = None,
        # Fiduciary validation parameters
        fiduciary_enabled: bool = True,
        user_context: Optional["UserContext"] = None,
        strict_fiduciary: bool = False,
    ):
        """
        Initialize validator.

        Args:
            seed_level: Sentinel seed level ("minimal", "standard", "full")
            max_transfer: Maximum SOL per single transaction (default 100.0 - adjust for your use case)
            confirm_above: Require confirmation for amounts above this
            blocked_addresses: List of blocked wallet addresses
            allowed_programs: Whitelist of allowed program IDs (empty = all allowed)
            require_purpose_for: Actions that require explicit purpose/reason
            max_history_size: Maximum validation history entries (prevents memory growth)
            memory_integrity_check: Enable memory integrity verification
            memory_secret_key: Secret key for memory HMAC (required if memory_integrity_check=True)
            memory_content_validation: Enable content validation before HMAC signing (v2.0).
                Detects injection patterns (authority claims, instruction overrides, etc.)
                before signing. Default True. Requires memory_integrity_check=True.
            address_validation: How to handle invalid addresses ("ignore", "warn", "strict"). Default is STRICT for security.
            strict_mode: If True, block any transaction with concerns (default False)
            custom_patterns: Additional suspicious patterns to check
            on_validation: Callback function called after each validation
            validator: Optional LayeredValidator for dependency injection (testing)
            fiduciary_enabled: Enable fiduciary validation (duty of loyalty/care). Default True.
            user_context: UserContext for fiduciary validation. Uses Solana defaults if not provided.
            strict_fiduciary: If True, any fiduciary violation blocks the transaction.

        Note:
            Default max_transfer=100.0 SOL may be too high for some use cases.
            Always configure appropriate limits for your application.

        Fiduciary Validation:
            When enabled, validates that transactions align with user's best interests.
            This includes checking for:
            - Actions that contradict user's stated goals
            - High-risk actions for low-risk-tolerance users
            - Potential conflicts of interest
            - Insufficient explanations for recommendations
        """
        # Create LayeredValidator if not provided
        if validator is None:
            config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,
            )
            validator = LayeredValidator(config=config)

        # Initialize SentinelIntegration
        super().__init__(validator=validator)

        # Keep Sentinel instance for get_seed() backwards compatibility
        self.sentinel = Sentinel(seed_level=seed_level)
        self.max_transfer = max_transfer
        self.confirm_above = confirm_above
        self.blocked_addresses = set(blocked_addresses or [])
        self.allowed_programs = set(allowed_programs or [])
        self.require_purpose_for = require_purpose_for or self.DEFAULT_REQUIRE_PURPOSE
        self.max_history_size = max_history_size
        self.memory_integrity_check = memory_integrity_check
        self.memory_secret_key = memory_secret_key
        self.memory_content_validation = memory_content_validation
        self.strict_mode = strict_mode
        self.custom_patterns = DEFAULT_SUSPICIOUS_PATTERNS + (custom_patterns or [])
        self.on_validation = on_validation
        self.history: List[TransactionSafetyResult] = []

        # Parse address validation mode
        if isinstance(address_validation, str):
            self.address_validation = AddressValidationMode(address_validation.lower())
        else:
            self.address_validation = address_validation

        # Initialize memory checker if enabled
        self._memory_checker = None
        self._memory_store = None
        if memory_integrity_check:
            try:
                from sentinelseed.memory import (
                    MemoryIntegrityChecker,
                    MemoryEntry,
                    MemorySource,
                )
                self._memory_checker = MemoryIntegrityChecker(
                    secret_key=memory_secret_key,
                    strict_mode=False,
                    validate_content=memory_content_validation,
                )
                self._memory_store = self._memory_checker.create_safe_memory_store()
                self._MemoryEntry = MemoryEntry
                self._MemorySource = MemorySource
                logger.debug(
                    "Memory integrity checker initialized (content_validation=%s)",
                    memory_content_validation,
                )
            except (ImportError, AttributeError):
                warnings.warn(
                    "memory_integrity_check=True but sentinelseed.memory module not available. "
                    "Memory integrity checking will be disabled.",
                    RuntimeWarning,
                )
                logger.warning("Memory integrity module not available")

        # Initialize fiduciary validator if enabled
        self._fiduciary: Optional[FiduciaryValidator] = None
        self._user_context: Optional[UserContext] = None
        self._strict_fiduciary = strict_fiduciary

        if fiduciary_enabled and HAS_FIDUCIARY:
            self._fiduciary = FiduciaryValidator(strict_mode=strict_fiduciary)
            self._user_context = user_context or _get_default_solana_context()
            logger.debug("Fiduciary validator initialized")
        elif fiduciary_enabled and not HAS_FIDUCIARY:
            warnings.warn(
                "fiduciary_enabled=True but sentinelseed.fiduciary module not available. "
                "Fiduciary validation will be disabled.",
                RuntimeWarning,
            )
            logger.warning("Fiduciary module not available")

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

        logger.debug(f"Checking transaction: action={action}, amount={amount}")

        # Normalize amount: None becomes 0.0 to prevent TypeError in comparisons
        if amount is None:
            amount = 0.0

        # Normalize recipient: ensure it's a string to prevent TypeError in slicing/hashing
        if recipient is None:
            recipient = ""
        elif not isinstance(recipient, str):
            # Convert non-string types (int, list, etc.) to string representation
            try:
                recipient = str(recipient)
                logger.warning(f"Recipient was not a string, converted from {type(recipient).__name__}")
            except Exception:
                recipient = ""

        # Validate address format
        if recipient:
            address_valid = is_valid_solana_address(recipient)
            if not address_valid:
                if self.address_validation == AddressValidationMode.STRICT:
                    concerns.append(f"Invalid Solana address format: {recipient[:16]}...")
                    risk_level = TransactionRisk.CRITICAL
                    logger.warning(f"Invalid address rejected (strict mode): {recipient[:16]}...")
                elif self.address_validation == AddressValidationMode.WARN:
                    logger.warning(f"Address may be invalid (not base58): {recipient[:16]}...")
                    recommendations.append("Verify recipient address format")
                # IGNORE mode: no action

        # Validate amount is a valid finite number
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            concerns.append(f"Invalid transaction amount: {amount}")
            risk_level = TransactionRisk.CRITICAL
            amount = 0.0  # Set to 0 to prevent further errors

        # Check for Infinity and NaN (must be a finite number)
        if not math.isfinite(amount):
            concerns.append(f"Invalid amount: {amount} is not a valid finite number")
            risk_level = TransactionRisk.CRITICAL
            logger.warning(f"Non-finite amount rejected: {amount}")
            amount = 0.0  # Set to 0 to prevent further errors

        if amount < 0:
            concerns.append(f"Transaction amount cannot be negative: {amount}")
            risk_level = TransactionRisk.CRITICAL
            logger.warning(f"Negative amount rejected: {amount}")

        # Check for high-risk action patterns
        action_lower = action.lower().replace("_", "").replace("-", "")
        for high_risk in HIGH_RISK_ACTIONS:
            if high_risk in action_lower:
                concerns.append(f"High-risk action detected: {action}")
                risk_level = TransactionRisk.CRITICAL
                logger.warning(f"High-risk action blocked: {action}")
                break

        # Check blocked addresses
        if recipient and recipient in self.blocked_addresses:
            concerns.append(f"Recipient is blocked: {recipient[:8]}...")
            risk_level = TransactionRisk.CRITICAL
            logger.info(f"Blocked address detected: {recipient[:8]}...")

        # Check program whitelist
        if self.allowed_programs and program_id:
            if program_id not in self.allowed_programs:
                concerns.append(f"Program not whitelisted: {program_id[:8]}...")
                risk_level = TransactionRisk.HIGH
                logger.info(f"Non-whitelisted program: {program_id[:8]}...")

        # Check transfer limits
        if amount > self.max_transfer:
            concerns.append(f"Amount {amount} exceeds limit {self.max_transfer}")
            risk_level = TransactionRisk.CRITICAL
            logger.info(f"Transfer limit exceeded: {amount} > {self.max_transfer}")

        # PURPOSE GATE: Check if action requires explicit purpose
        requires_purpose = any(
            keyword.lower() in action.lower()
            for keyword in self.require_purpose_for
        )
        effective_purpose = purpose or kwargs.get("reason", "")
        if requires_purpose and not effective_purpose:
            concerns.append(
                f"Action '{action}' requires explicit purpose/reason "
                f"(set purpose= or reason= parameter)"
            )
            if risk_level < TransactionRisk.MEDIUM:
                risk_level = TransactionRisk.MEDIUM
            logger.debug(f"Missing purpose for action: {action}")
        elif effective_purpose:
            trimmed_purpose = effective_purpose.strip()

            # Check minimum length (20 characters for meaningful justification)
            if len(trimmed_purpose) < 20:
                concerns.append(
                    "Purpose explanation is too brief - provide at least 20 characters"
                )
                if risk_level < TransactionRisk.MEDIUM:
                    risk_level = TransactionRisk.MEDIUM

            # Check minimum word count (3 words for meaningful content)
            words = trimmed_purpose.split()
            if len(words) < 3:
                concerns.append(
                    "Purpose should contain at least 3 words to be meaningful"
                )
                if risk_level < TransactionRisk.MEDIUM:
                    risk_level = TransactionRisk.MEDIUM

            # Detect gibberish (repeated characters like "aaaaaaaaaa")
            # Remove spaces and check if it's mostly the same character repeated
            no_spaces = trimmed_purpose.replace(" ", "")
            if len(no_spaces) >= 10 and re.match(r'^(.)\1{9,}$', no_spaces):
                concerns.append(
                    "Purpose appears to be meaningless repeated characters"
                )
                if risk_level < TransactionRisk.MEDIUM:
                    risk_level = TransactionRisk.MEDIUM

        requires_confirmation = amount > self.confirm_above

        # Validate intent with LayeredValidator (include memo for full validation)
        description = self._describe_action(action, amount, recipient, memo, kwargs)
        validation_result: ValidationResult = self.validate(description)

        if not validation_result.is_safe:
            sentinel_concerns = validation_result.violations or []
            concerns.extend(sentinel_concerns)
            if risk_level < TransactionRisk.HIGH:
                risk_level = TransactionRisk.HIGH
            logger.info(f"Sentinel validation failed: {sentinel_concerns}")

        # Check suspicious patterns
        effective_purpose = purpose or kwargs.get("reason", "")
        suspicious, pattern_risk = self._check_patterns(action, amount, memo, effective_purpose)
        if suspicious:
            concerns.extend(suspicious)
            if risk_level < pattern_risk:
                risk_level = pattern_risk

        # Fiduciary validation: check if action aligns with user's best interests
        fiduciary_blocked = False
        if self._fiduciary is not None:
            # Build action description for fiduciary validation
            fid_action = f"{action} {amount} SOL"
            if recipient:
                fid_action += f" to {recipient[:8]}..."
            if effective_purpose:
                fid_action += f" ({effective_purpose})"

            fid_result = self._fiduciary.validate_action(
                action=fid_action,
                user_context=self._user_context,
                proposed_outcome={"amount": amount, "recipient": recipient, **kwargs},
            )

            if not fid_result.compliant:
                # Add fiduciary violations as concerns
                for violation in fid_result.violations:
                    concern = f"[Fiduciary/{violation.duty.value}] {violation.description}"
                    concerns.append(concern)
                    if violation.is_blocking():
                        fiduciary_blocked = True
                        if risk_level < TransactionRisk.HIGH:
                            risk_level = TransactionRisk.HIGH

                logger.info(f"Fiduciary validation concerns: {len(fid_result.violations)}")

            # In strict fiduciary mode, any violation blocks
            if self._strict_fiduciary and fid_result.violations:
                fiduciary_blocked = True
                if risk_level < TransactionRisk.HIGH:
                    risk_level = TransactionRisk.HIGH

        # Determine if should proceed based on risk level, strict_mode, and fiduciary
        is_safe = len(concerns) == 0
        if self.strict_mode:
            # In strict mode, block any transaction with concerns
            should_proceed = is_safe
        elif fiduciary_blocked:
            # Fiduciary blocking violations always block
            should_proceed = False
        else:
            # In normal mode, only block HIGH and CRITICAL
            should_proceed = risk_level not in [TransactionRisk.CRITICAL, TransactionRisk.HIGH]

        # Add recommendations
        if requires_confirmation:
            recommendations.append("High-value: manual confirmation recommended")
        if risk_level in [TransactionRisk.HIGH, TransactionRisk.CRITICAL]:
            recommendations.append("Review transaction details before proceeding")
        if requires_purpose and not purpose:
            recommendations.append(f"Provide purpose= for {action} actions")

        result = TransactionSafetyResult(
            safe=is_safe,
            risk_level=risk_level,
            transaction_type=action,
            concerns=concerns,
            recommendations=recommendations,
            should_proceed=should_proceed,
            requires_confirmation=requires_confirmation,
        )

        # Store in history (with size limit to prevent memory growth)
        self.history.append(result)
        if len(self.history) > self.max_history_size:
            self.history.pop(0)

        # Sign and store in memory store if enabled (for integrity verification)
        if self._memory_store is not None:
            content = (
                f"tx:{action} amount={amount} recipient={recipient[:16] if recipient else 'none'}... "
                f"safe={result.safe} risk={result.risk_level.name}"
            )
            self._memory_store.add(
                content=content,
                source=self._MemorySource.AGENT_INTERNAL,
                metadata={
                    "action": action,
                    "amount": amount,
                    "recipient": recipient,
                    "safe": result.safe,
                    "risk_level": result.risk_level.name,
                    "concerns": result.concerns,
                },
            )

        # Call validation callback if provided
        if self.on_validation is not None:
            try:
                self.on_validation(result)
            except Exception as e:
                logger.error(f"on_validation callback error: {e}")

        logger.debug(f"Check result: safe={result.safe}, risk={risk_level.name}")
        return result

    def _describe_action(
        self,
        action: str,
        amount: float,
        recipient: str,
        memo: str,
        extra: Dict
    ) -> str:
        """Create description for Sentinel validation (includes memo for attack detection)."""
        parts = [f"Solana {action}"]
        if amount:
            parts.append(f"amount={amount}")
        if recipient:
            parts.append(f"to={recipient[:8]}...")
        # Include memo content for full validation (truncate to prevent DoS)
        if memo:
            # Truncate long memos to prevent description bloat
            memo_preview = memo[:100] + "..." if len(memo) > 100 else memo
            parts.append(f"memo={memo_preview}")

        # Include sanitized metadata (only allowed keys with primitive values)
        # This prevents injection attacks via arbitrary metadata fields
        if extra:
            sanitized = _sanitize_metadata(extra)
            if sanitized:
                # Truncate serialized metadata to prevent bloat
                meta_str = json.dumps(sanitized)
                if len(meta_str) > 200:
                    meta_str = meta_str[:200] + "..."
                parts.append(f"metadata={meta_str}")

        return " ".join(parts)

    def _check_patterns(
        self,
        action: str,
        amount: float,
        memo: str,
        purpose: str = "",
    ) -> tuple:
        """
        Check for suspicious transaction patterns.

        Returns:
            Tuple of (concerns_list, max_risk_level)
        """
        suspicious = []
        max_risk = TransactionRisk.LOW

        # Build text to check against patterns
        text_to_check = " ".join(filter(None, [action, memo, purpose]))

        # Check against custom patterns
        for pattern in self.custom_patterns:
            if pattern.matches(text_to_check):
                suspicious.append(pattern.message)
                if pattern.risk_level > max_risk:
                    max_risk = pattern.risk_level

        # Unlimited approvals (special case - amount == 0 for approve)
        action_lower = action.lower()
        if "approve" in action_lower and amount == 0:
            if "Unlimited approval" not in " ".join(suspicious):
                suspicious.append("Potential unlimited approval (amount=0)")
                if max_risk < TransactionRisk.HIGH:
                    max_risk = TransactionRisk.HIGH

        # Suspicious memo (LayeredValidator check)
        if memo:
            memo_result: ValidationResult = self.validate(memo)
            if not memo_result.is_safe:
                suspicious.append("Suspicious memo content")
                if max_risk < TransactionRisk.MEDIUM:
                    max_risk = TransactionRisk.MEDIUM

        return suspicious, max_risk

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
        if self._memory_store is not None:
            self._memory_store.clear()

    def verify_transaction_history(self) -> Dict[str, Any]:
        """
        Verify integrity of transaction history using cryptographic signatures.

        Returns:
            Dict with verification results:
                - all_valid: True if all entries pass verification
                - checked: Number of entries checked
                - invalid_count: Number of tampered entries
                - details: Per-entry results (if any invalid)

        Example:
            result = validator.verify_transaction_history()
            if not result["all_valid"]:
                print(f"Warning: {result['invalid_count']} entries may be tampered!")
        """
        if self._memory_store is None:
            return {
                "all_valid": True,
                "checked": 0,
                "invalid_count": 0,
                "reason": "Memory integrity check not enabled",
            }

        all_entries = self._memory_store.get_all(verify=False)
        valid_entries = self._memory_store.get_all(verify=True)

        invalid_count = len(all_entries) - len(valid_entries)

        return {
            "all_valid": invalid_count == 0,
            "checked": len(all_entries),
            "invalid_count": invalid_count,
            "valid_count": len(valid_entries),
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        Get statistics about memory integrity checks.

        Returns:
            Dict with memory stats:
                - enabled: Whether memory integrity is enabled
                - total: Total entries checked
                - valid: Valid entries
                - validation_rate: Percentage of valid entries

        Example:
            stats = validator.get_memory_stats()
            print(f"Memory integrity: {stats['validation_rate']:.1%} valid")
        """
        if self._memory_checker is None:
            return {"enabled": False, "content_validation": False}

        checker_stats = self._memory_checker.get_validation_stats()
        return {
            "enabled": True,
            "content_validation": self.memory_content_validation,
            "entries_stored": len(self._memory_store) if self._memory_store else 0,
            **checker_stats,
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

    def block_address(self, address: str) -> None:
        """
        Add address to blocklist.

        Args:
            address: Solana wallet address to block
        """
        if address and address not in self.blocked_addresses:
            self.blocked_addresses.add(address)
            logger.info(f"Address blocked: {address[:8]}...")

    def unblock_address(self, address: str) -> None:
        """
        Remove address from blocklist.

        Args:
            address: Solana wallet address to unblock
        """
        if address in self.blocked_addresses:
            self.blocked_addresses.remove(address)
            logger.info(f"Address unblocked: {address[:8]}...")

    def get_config(self) -> Dict[str, Any]:
        """
        Get current validator configuration.

        Returns:
            Dict with current configuration values
        """
        return {
            "max_transfer": self.max_transfer,
            "confirm_above": self.confirm_above,
            "blocked_addresses": list(self.blocked_addresses),
            "allowed_programs": list(self.allowed_programs),
            "require_purpose_for": self.require_purpose_for,
            "max_history_size": self.max_history_size,
            "address_validation": self.address_validation.value,
            "strict_mode": self.strict_mode,
            "custom_patterns_count": len(self.custom_patterns),
        }

    def update_config(
        self,
        max_transfer: Optional[float] = None,
        confirm_above: Optional[float] = None,
        strict_mode: Optional[bool] = None,
        address_validation: Optional[Union[str, AddressValidationMode]] = None,
    ) -> None:
        """
        Update validator configuration.

        Args:
            max_transfer: New maximum transfer limit
            confirm_above: New confirmation threshold
            strict_mode: Enable/disable strict mode
            address_validation: New address validation mode
        """
        if max_transfer is not None:
            self.max_transfer = max_transfer
        if confirm_above is not None:
            self.confirm_above = confirm_above
        if strict_mode is not None:
            self.strict_mode = strict_mode
        if address_validation is not None:
            if isinstance(address_validation, str):
                self.address_validation = AddressValidationMode(address_validation.lower())
            else:
                self.address_validation = address_validation


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
            "risk": result.risk_level.name.lower(),
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
            "risk": result.risk_level.name.lower(),
            "concerns": result.concerns,
        }

    def validate_action(action: str, **params) -> Dict[str, Any]:
        """Validate any action."""
        result = validator.check(action, **params)
        return {
            "safe": result.should_proceed,
            "risk": result.risk_level.name.lower(),
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
) -> List[Any]:
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
        from solana_agent_kit import create_solana_tools
        from sentinelseed.integrations.solana_agent_kit import create_langchain_tools

        # Get Solana tools (from solana-agent-kit-py)
        solana_tools = create_solana_tools(agent)

        # Add Sentinel safety tools
        safety_tools = create_langchain_tools()

        # Combine for agent
        all_tools = solana_tools + safety_tools
        agent = create_react_agent(llm, all_tools)
    """
    try:
        from langchain.tools import Tool
    except (ImportError, AttributeError):
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
        if not description or not description.strip():
            return "ERROR: Empty input. Use format: 'action amount recipient'"

        parts = description.strip().split()
        action = parts[0] if parts else "unknown"

        # Parse amount safely
        amount = 0.0
        if len(parts) > 1:
            try:
                amount = float(parts[1])
            except ValueError:
                logger.warning(f"Invalid amount in LangChain tool input: {parts[1]}")
                return f"ERROR: Invalid amount '{parts[1]}'. Use format: 'action amount recipient'"

        # Validate amount is non-negative
        if amount < 0:
            return f"ERROR: Amount cannot be negative: {amount}"

        recipient = parts[2] if len(parts) > 2 else ""

        try:
            result = validator.check(action, amount=amount, recipient=recipient)
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return f"ERROR: Validation failed: {str(e)}"

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
            # Extract and validate amount
            raw_amount = kwargs.get("amount", args[0] if args else 0)
            try:
                amount = float(raw_amount) if raw_amount is not None else 0.0
            except (ValueError, TypeError):
                logger.warning(f"Invalid amount type in wrapper: {type(raw_amount)}")
                amount = 0.0

            # Extract and validate recipient
            recipient = kwargs.get("recipient", kwargs.get("to", ""))
            if not recipient and len(args) > 1:
                recipient = args[1]

            # Ensure recipient is a string
            if recipient is not None:
                recipient = str(recipient)
            else:
                recipient = ""

            logger.debug(f"Middleware validating: {action_name}, amount={amount}")

            result = self.validator.check(
                action_name,
                amount=amount,
                recipient=recipient,
            )

            if not result.should_proceed:
                logger.info(f"Transaction blocked by middleware: {result.concerns}")
                raise TransactionBlockedError(
                    f"Transaction blocked: {', '.join(result.concerns)}"
                )

            if result.requires_confirmation:
                logger.info(f"High-value {action_name}: {amount}")

            return func(*args, **kwargs)

        # Preserve function metadata
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper


__all__ = [
    # Version
    "__version__",
    # Enums
    "TransactionRisk",
    "AddressValidationMode",
    # Dataclasses
    "TransactionSafetyResult",
    "SuspiciousPattern",
    # Constants
    "DEFAULT_SUSPICIOUS_PATTERNS",
    "HIGH_RISK_ACTIONS",
    "ALLOWED_METADATA_KEYS",
    # Classes
    "SentinelValidator",
    "SentinelSafetyMiddleware",
    "TransactionBlockedError",
    # Functions
    "safe_transaction",
    "create_sentinel_actions",
    "create_langchain_tools",
    "is_valid_solana_address",
    # Fiduciary (re-exports for convenience)
    "HAS_FIDUCIARY",
]

# Re-export fiduciary classes if available (for convenience)
if HAS_FIDUCIARY:
    __all__.extend([
        "UserContext",
        "RiskTolerance",
        "FiduciaryValidator",
        "FiduciaryResult",
    ])
