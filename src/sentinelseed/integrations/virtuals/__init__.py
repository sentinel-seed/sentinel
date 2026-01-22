"""
Sentinel Safety Plugin for Virtuals Protocol GAME SDK

This integration provides safety guardrails for AI agents built with the GAME framework.
It implements the THSP Protocol (Truth, Harm, Scope, Purpose) to validate agent
actions before execution.

Requirements:
    pip install sentinelseed[virtuals]
    # or manually: pip install game-sdk

The GAME SDK architecture:
- Agent: High-Level Planner (defines goals, coordinates workers)
- Worker: Low-Level Planner (selects and executes functions for tasks)
- Function: Executable unit with args and return values

This integration provides:
1. Function wrappers that add THSP validation before execution
2. A dedicated Safety Worker that other workers can call
3. Utilities to wrap existing agents with safety validation

Usage:
    from sentinelseed.integrations.virtuals import (
        SentinelConfig,
        SentinelSafetyWorker,
        create_sentinel_function,
        wrap_functions_with_sentinel,
        sentinel_protected,
    )

    # Option 1: Add a safety worker to your agent
    safety_worker = SentinelSafetyWorker.create_worker_config()

    # Option 2: Wrap individual functions
    safe_fn = create_sentinel_function(my_function, config)

    # Option 3: Wrap all functions in a worker's action space
    safe_action_space = wrap_functions_with_sentinel(action_space)

For more information:
    - Sentinel: https://sentinelseed.dev
    - GAME SDK: https://docs.game.virtuals.io/
"""

from __future__ import annotations

import functools
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from sentinelseed.integrations._base import (
    SentinelIntegration,
    LayeredValidator,
    ValidationConfig,
    ValidationResult as LayeredValidationResult,
)

logger = logging.getLogger("sentinelseed.virtuals")

# Import THSP types from validators (canonical source)
from sentinelseed.validators.semantic import THSPGate

# Import memory integrity checker if available
try:
    from sentinelseed.memory import (
        MemoryIntegrityChecker,
        MemoryEntry,
        SignedMemoryEntry,
        MemorySource,
        MemoryValidationResult,
        SafeMemoryStore,
    )
    MEMORY_INTEGRITY_AVAILABLE = True
except (ImportError, AttributeError):
    MEMORY_INTEGRITY_AVAILABLE = False
    MemoryIntegrityChecker = None
    MemoryEntry = None
    SignedMemoryEntry = None
    MemorySource = None
    MemoryValidationResult = None
    SafeMemoryStore = None

# Import fiduciary validator for user-aligned decision making
try:
    from sentinelseed.fiduciary import (
        FiduciaryValidator,
        FiduciaryResult,
        UserContext,
        RiskTolerance,
        Violation,
    )
    FIDUCIARY_AVAILABLE = True
except (ImportError, AttributeError):
    FIDUCIARY_AVAILABLE = False
    FiduciaryValidator = None
    FiduciaryResult = None
    UserContext = None
    RiskTolerance = None
    Violation = None


def _get_default_virtuals_context() -> Optional["UserContext"]:
    """
    Get default UserContext for Virtuals/GAME agents.

    Virtuals agents typically handle:
    - Token transfers and swaps
    - DeFi operations
    - NFT operations
    - Cross-chain bridges

    Returns:
        UserContext with sensible defaults for AI agent operations,
        or None if fiduciary module is not available.
    """
    if not FIDUCIARY_AVAILABLE:
        return None

    return UserContext(
        goals=[
            "execute user-requested operations safely",
            "protect user assets from unauthorized access",
            "avoid excessive fees and slippage",
        ],
        constraints=[
            "never expose private keys or seed phrases",
            "respect transaction limits",
            "require confirmation for high-value operations",
            "verify recipient addresses before transfers",
        ],
        risk_tolerance=RiskTolerance.MODERATE,
        preferences={
            "require_purpose": True,
            "max_slippage": 0.05,  # 5% max slippage
            "require_confirmation_above": 100.0,
        },
    )


# Check for game-sdk availability
try:
    from game_sdk.game.agent import Agent, WorkerConfig
    from game_sdk.game.custom_types import (
        Function,
        Argument,
        FunctionResult,
        FunctionResultStatus,
    )
    GAME_SDK_AVAILABLE = True
except (ImportError, AttributeError):
    GAME_SDK_AVAILABLE = False
    # Define stubs for type hints when SDK not installed
    Agent = None
    WorkerConfig = None
    Function = None
    Argument = None
    FunctionResult = None
    FunctionResultStatus = None


class SentinelValidationError(Exception):
    """Raised when an action fails Sentinel safety validation."""

    def __init__(self, message: str, gate: str, concerns: List[str]):
        super().__init__(message)
        self.gate = gate
        self.concerns = concerns


# THSPGate is imported from sentinelseed.validators.semantic (canonical source)
# Kept in __all__ for backwards compatibility


@dataclass
class ValidationResult:
    """Result of THSP validation."""
    passed: bool
    gate_results: Dict[str, bool] = field(default_factory=dict)
    concerns: List[str] = field(default_factory=list)
    blocked_gate: Optional[str] = None

    @property
    def failed_gates(self) -> List[str]:
        """Return list of gate names that failed validation."""
        return [gate for gate, passed in self.gate_results.items() if not passed]


@dataclass
class SentinelConfig:
    """Configuration for Sentinel safety validation."""

    # Behavior settings
    block_unsafe: bool = True
    log_validations: bool = True

    # Transaction limits (for crypto/financial agents)
    max_transaction_amount: float = 1000.0
    require_confirmation_above: float = 100.0

    # Purpose gate settings
    require_purpose_for: List[str] = field(default_factory=lambda: [
        "transfer", "send", "approve", "swap", "bridge", "withdraw",
    ])

    # Memory integrity settings (defense against memory injection)
    memory_integrity_check: bool = False
    memory_secret_key: Optional[str] = None
    memory_content_validation: bool = True
    """
    Enable content validation before HMAC signing (v2.0).
    When True, memory content is checked for injection patterns
    (authority claims, instruction overrides, address redirection, etc.)
    before signing. This provides defense-in-depth against memory
    injection attacks. Default: True (recommended).

    Note: Requires memory_integrity_check=True to take effect.
    """

    # Pattern detection - common crypto attack patterns
    suspicious_patterns: List[str] = field(default_factory=lambda: [
        r"(?i)private[_\s]?key",
        r"(?i)seed[_\s]?phrase",
        r"(?i)mnemonic",
        r"(?i)send[_\s]?all",
        r"(?i)drain[_\s]?wallet",
        r"(?i)unlimited[_\s]?approval",
        r"(?i)max[_\s]?uint",
        r"0x[fF]{64}",  # Max uint256 approvals
    ])

    # Function whitelist (empty = allow all except blocked)
    allowed_functions: List[str] = field(default_factory=list)

    # Function blacklist (always checked)
    blocked_functions: List[str] = field(default_factory=lambda: [
        "drain_wallet",
        "send_all_tokens",
        "approve_unlimited",
        "export_private_key",
        "reveal_seed_phrase",
    ])


class SentinelValidator(SentinelIntegration):
    """
    Core validation engine implementing THSP Protocol for Virtuals/GAME agents.

    Uses LayeredValidator for content validation (security patterns,
    jailbreak detection, etc.) via SentinelIntegration inheritance,
    and adds crypto-specific checks on top:
    - Transaction amount limits
    - Blocked function names
    - Crypto-specific patterns (private keys, seed phrases)
    - Fiduciary validation for user-aligned decisions

    The four THSP gates:
    - TRUTH: Is the action based on accurate information?
    - HARM: Could this action cause harm?
    - SCOPE: Is this action within appropriate limits?
    - PURPOSE: Does this action serve a legitimate benefit?

    Additionally, Fiduciary validation ensures actions align with user interests.
    """

    _integration_name = "virtuals"

    def __init__(
        self,
        config: Optional[SentinelConfig] = None,
        validator: Optional[LayeredValidator] = None,
        fiduciary_enabled: bool = True,
        user_context: Optional["UserContext"] = None,
        strict_fiduciary: bool = False,
    ):
        """
        Initialize SentinelValidator with optional Fiduciary validation.

        Args:
            config: Sentinel configuration for THSP gates.
            validator: Optional LayeredValidator instance.
            fiduciary_enabled: Enable fiduciary validation (default: True).
            user_context: Custom UserContext for fiduciary validation.
                If not provided, uses default Virtuals context.
            strict_fiduciary: If True, fiduciary violations block actions.
                If False, violations are logged as concerns but don't block.
        """
        # Create LayeredValidator if not provided
        if validator is None:
            val_config = ValidationConfig(
                use_heuristic=True,
                use_semantic=False,
            )
            validator = LayeredValidator(config=val_config)

        # Initialize SentinelIntegration
        super().__init__(validator=validator)

        self.config = config or SentinelConfig()
        self._compiled_patterns = [
            re.compile(p) for p in self.config.suspicious_patterns
        ]
        self._validation_history: List[Dict[str, Any]] = []

        # Initialize Fiduciary validation
        self._fiduciary_enabled = fiduciary_enabled and FIDUCIARY_AVAILABLE
        self._strict_fiduciary = strict_fiduciary
        self._fiduciary: Optional[FiduciaryValidator] = None
        self._user_context: Optional[UserContext] = None

        if self._fiduciary_enabled:
            self._fiduciary = FiduciaryValidator()
            self._user_context = user_context or _get_default_virtuals_context()
            logger.info("Fiduciary validation enabled for Virtuals")

    def validate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate an action through all THSP gates.

        First uses the global THSPValidator for content validation (detects
        system attacks, SQL injection, XSS, jailbreaks, etc.), then applies
        crypto-specific checks (transaction limits, blocked functions).

        Args:
            action_name: Name of the function to execute
            action_args: Arguments passed to the function
            context: Optional context (worker state, purpose, etc.)

        Returns:
            ValidationResult with pass/fail status and details
        """
        # Input validation - ensure proper types to avoid runtime errors
        if action_args is None:
            action_args = {}
        if context is None or not isinstance(context, dict):
            context = {}

        concerns = []
        gate_results = {"truth": True, "harm": True, "scope": True, "purpose": True}

        # Validate action_name - empty or whitespace-only names fail TRUTH gate
        if not action_name or not action_name.strip():
            gate_results["truth"] = False
            concerns.append("Action name cannot be empty or whitespace-only")
            return ValidationResult(
                passed=False,
                gate_results=gate_results,
                concerns=concerns,
                blocked_gate="truth",
            )

        # Step 1: Use LayeredValidator for content validation
        # This catches: rm -rf, SQL injection, XSS, jailbreaks, etc.
        content_to_validate = self._build_content_string(
            action_name, action_args, context
        )
        layered_result: LayeredValidationResult = self.validator.validate(content_to_validate)

        if not layered_result.is_safe:
            # LayeredValidator failed - mark harm gate as failed
            gate_results["harm"] = False

            # Add violations as concerns
            if layered_result.violations:
                concerns.extend(layered_result.violations)

            # Check for jailbreak patterns in violations
            if any("jailbreak" in v.lower() for v in (layered_result.violations or [])):
                if "Jailbreak attempt detected" not in str(concerns):
                    concerns.append("Jailbreak attempt detected")

        # Step 2: Apply crypto-specific checks (on top of global validation)

        # Gate 1: TRUTH - Check for misleading action names
        truth_passed, truth_concerns = self._check_truth_gate(
            action_name, action_args, context
        )
        if not truth_passed:
            gate_results["truth"] = False
            concerns.extend(truth_concerns)

        # Gate 2: HARM - Check blocked functions and crypto patterns
        harm_passed, harm_concerns = self._check_harm_gate(
            action_name, action_args, context
        )
        if not harm_passed:
            gate_results["harm"] = False
            concerns.extend(harm_concerns)

        # Gate 3: SCOPE - Check transaction limits and whitelists
        scope_passed, scope_concerns = self._check_scope_gate(
            action_name, action_args, context
        )
        if not scope_passed:
            gate_results["scope"] = False
            concerns.extend(scope_concerns)

        # Gate 4: PURPOSE - Check for explicit purpose on sensitive actions
        purpose_passed, purpose_concerns = self._check_purpose_gate(
            action_name, action_args, context
        )
        if not purpose_passed:
            gate_results["purpose"] = False
            concerns.extend(purpose_concerns)

        # Step 3: Fiduciary validation - check if action aligns with user interests
        fiduciary_blocked = False
        if self._fiduciary is not None:
            # Build action description for fiduciary validation
            # Include purpose in the action string so FiduciaryValidator can analyze it
            amount = action_args.get("amount", action_args.get("value", 0))
            purpose = context.get("purpose", action_args.get("purpose", ""))

            # Combine action name with purpose for comprehensive analysis
            fid_action_parts = [action_name]
            if amount:
                fid_action_parts.append(f"(amount: {amount})")
            if purpose:
                fid_action_parts.append(f"- {purpose}")

            fid_action = " ".join(fid_action_parts)

            fid_result = self._fiduciary.validate_action(
                action=fid_action,
                user_context=self._user_context,
                proposed_outcome={
                    "action_name": action_name,
                    "amount": amount,
                    "purpose": purpose,
                    **action_args,
                },
            )

            if not fid_result.compliant:
                for violation in fid_result.violations:
                    concern = f"[Fiduciary/{violation.duty.value}] {violation.description}"
                    concerns.append(concern)
                    if violation.is_blocking():
                        fiduciary_blocked = True

                if self._strict_fiduciary and fiduciary_blocked:
                    # In strict mode, fiduciary violations block the action
                    gate_results["purpose"] = False  # Associate with purpose gate

        # All gates must pass
        all_passed = all(gate_results.values()) and not (self._strict_fiduciary and fiduciary_blocked)
        blocked_gate = None
        if not all_passed:
            for gate, passed in gate_results.items():
                if not passed:
                    blocked_gate = gate
                    break

        result = ValidationResult(
            passed=all_passed,
            gate_results=gate_results,
            concerns=concerns,
            blocked_gate=blocked_gate,
        )

        # Record in history
        self._validation_history.append({
            "action": action_name,
            "passed": all_passed,
            "blocked_gate": blocked_gate,
            "concerns": concerns,
        })

        return result

    def _build_content_string(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> str:
        """
        Build a content string for THSPValidator from action data.

        Converts action name, arguments, and context into a single string
        that the THSPValidator can analyze for security patterns.

        Args:
            action_name: Name of the action
            action_args: Action arguments
            context: Context dictionary

        Returns:
            Combined string for validation
        """
        parts = [f"Action: {action_name}"]

        if action_args:
            args_str = json.dumps(action_args, default=str)
            parts.append(f"Arguments: {args_str}")

        if context:
            # Only include relevant context fields
            relevant_keys = ["purpose", "reason", "user_request", "message"]
            for key in relevant_keys:
                if key in context:
                    parts.append(f"{key}: {context[key]}")

        return " | ".join(parts)

    def _check_truth_gate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """TRUTH gate: Verify factual correspondence and detect deception."""
        concerns = []

        # Check for context manipulation attempts
        if context.get("_injected") or context.get("_override"):
            concerns.append("Potential context manipulation detected")
            return False, concerns

        # Check for misleading action names
        misleading_patterns = [
            (r"(?i)safe.*(?:drain|steal|hack)", "Action name misleading: contains 'safe' but suggests harm"),
            (r"(?i)test.*(?:transfer|send).*(?:real|prod)", "Test action targeting production"),
        ]

        for pattern, concern in misleading_patterns:
            if re.search(pattern, action_name):
                concerns.append(concern)

        return len(concerns) == 0, concerns

    def _check_harm_gate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """HARM gate: Assess potential for harm."""
        concerns = []

        # Check blocked functions
        if action_name.lower() in [f.lower() for f in self.config.blocked_functions]:
            concerns.append(f"Function '{action_name}' is blocked")
            return False, concerns

        # Check for suspicious patterns in arguments
        args_str = str(action_args)
        for pattern in self._compiled_patterns:
            if pattern.search(args_str):
                concerns.append(f"Suspicious pattern detected: {pattern.pattern}")

        # Check for private key exposure
        for key, value in action_args.items():
            if isinstance(value, str):
                # 64-char hex string (potential private key)
                if re.match(r"^[0-9a-fA-F]{64}$", value):
                    concerns.append(f"Potential private key in argument '{key}'")
                # 12-24 word phrase (potential seed phrase)
                if re.match(r"^(\w+\s+){11,23}\w+$", value):
                    concerns.append(f"Potential seed phrase in argument '{key}'")

        return len(concerns) == 0, concerns

    def _check_scope_gate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """SCOPE gate: Check appropriate boundaries."""
        concerns = []

        # Check whitelist if configured
        if self.config.allowed_functions:
            if action_name not in self.config.allowed_functions:
                concerns.append(f"Function '{action_name}' not in allowed list")
                return False, concerns

        # Check transaction amounts
        amount_keys = ["amount", "value", "quantity", "tokens", "sol", "lamports"]
        for key in amount_keys:
            if key in action_args:
                try:
                    amount = float(action_args[key])
                    if amount > self.config.max_transaction_amount:
                        concerns.append(
                            f"Amount {amount} exceeds maximum {self.config.max_transaction_amount}"
                        )
                    elif amount > self.config.require_confirmation_above:
                        if not action_args.get("_confirmed", False):
                            concerns.append(
                                f"Amount {amount} requires explicit confirmation"
                            )
                except (ValueError, TypeError):
                    pass

        return len(concerns) == 0, concerns

    def _check_purpose_gate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """PURPOSE gate: Require teleological justification."""
        concerns = []

        # Check for purpose/reason in context or args
        has_purpose = any([
            context.get("purpose"),
            context.get("reason"),
            context.get("user_request"),
            action_args.get("purpose"),
            action_args.get("reason"),
        ])

        # Check if action requires purpose based on config
        requires_purpose = any(
            keyword.lower() in action_name.lower()
            for keyword in self.config.require_purpose_for
        )

        if requires_purpose and not has_purpose:
            concerns.append(
                f"Action '{action_name}' requires explicit purpose/reason "
                f"(matches: {self.config.require_purpose_for})"
            )

        return len(concerns) == 0, concerns

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self._validation_history:
            return {"total": 0, "passed": 0, "blocked": 0, "pass_rate": 1.0}

        total = len(self._validation_history)
        passed = sum(1 for v in self._validation_history if v["passed"])

        return {
            "total": total,
            "passed": passed,
            "blocked": total - passed,
            "pass_rate": passed / total if total > 0 else 1.0,
        }

    def get_fiduciary_stats(self) -> Dict[str, Any]:
        """
        Get fiduciary validation statistics.

        Returns:
            Dictionary with fiduciary validation status and stats.
        """
        if not self._fiduciary_enabled or self._fiduciary is None:
            return {"enabled": False}

        return {
            "enabled": True,
            "strict": self._strict_fiduciary,
            "validator_stats": self._fiduciary.get_stats(),
        }

    def update_user_context(self, context: "UserContext") -> None:
        """
        Update the UserContext for fiduciary validation.

        Args:
            context: New UserContext to use for validation.

        Raises:
            ValueError: If fiduciary is not enabled.
        """
        if not self._fiduciary_enabled:
            raise ValueError("Fiduciary validation is not enabled")

        self._user_context = context
        logger.info("Updated UserContext for fiduciary validation")


def create_sentinel_function(
    original_function: "Function",
    config: Optional[SentinelConfig] = None,
    validator: Optional[SentinelValidator] = None,
) -> "Function":
    """
    Wrap a GAME SDK Function with Sentinel validation.

    This creates a new Function that validates through THSP gates
    before executing the original function's executable.

    Args:
        original_function: The GAME SDK Function to wrap
        config: Optional Sentinel configuration
        validator: Optional existing validator instance

    Returns:
        New Function with safety validation

    Example:
        from game_sdk.game.custom_types import Function, Argument

        # Original function
        transfer_fn = Function(
            fn_name="transfer_tokens",
            fn_description="Transfer tokens to a recipient",
            args=[
                Argument(name="recipient", description="Recipient address"),
                Argument(name="amount", description="Amount to transfer"),
            ],
            executable=my_transfer_logic,
        )

        # Wrap with Sentinel
        safe_transfer_fn = create_sentinel_function(transfer_fn)
    """
    if not GAME_SDK_AVAILABLE:
        raise ImportError("game-sdk is required. Install with: pip install game-sdk")

    cfg = config or SentinelConfig()
    val = validator or SentinelValidator(cfg)

    original_executable = original_function.executable
    fn_name = original_function.fn_name

    def safe_executable(**kwargs) -> Tuple["FunctionResultStatus", str, dict]:
        """Wrapped executable with Sentinel validation."""
        # Validate before execution
        result = val.validate(
            action_name=fn_name,
            action_args=kwargs,
            context={},
        )

        if cfg.log_validations:
            status = "PASSED" if result.passed else "BLOCKED"
            logger.info(f"Sentinel [{status}] {fn_name}: gates={result.gate_results}")

        if not result.passed:
            if cfg.block_unsafe:
                return (
                    FunctionResultStatus.FAILED,
                    f"Sentinel blocked: {', '.join(result.concerns)}",
                    {"sentinel_blocked": True, "gate": result.blocked_gate},
                )
            else:
                logger.warning(f"Sentinel: {fn_name} would be blocked: {result.concerns}")

        # Execute original function
        return original_executable(**kwargs)

    # Create new Function with wrapped executable
    return Function(
        fn_name=original_function.fn_name,
        fn_description=original_function.fn_description,
        args=original_function.args,
        hint=getattr(original_function, 'hint', None),
        executable=safe_executable,
    )


def wrap_functions_with_sentinel(
    functions: List["Function"],
    config: Optional[SentinelConfig] = None,
) -> List["Function"]:
    """
    Wrap a list of Functions with Sentinel validation.

    Args:
        functions: List of GAME SDK Functions
        config: Optional Sentinel configuration

    Returns:
        List of wrapped Functions

    Example:
        action_space = [transfer_fn, swap_fn, check_balance_fn]
        safe_action_space = wrap_functions_with_sentinel(action_space)
    """
    if not GAME_SDK_AVAILABLE:
        raise ImportError("game-sdk is required. Install with: pip install game-sdk")

    cfg = config or SentinelConfig()
    validator = SentinelValidator(cfg)

    return [
        create_sentinel_function(fn, config=cfg, validator=validator)
        for fn in functions
    ]


class SentinelSafetyWorker:
    """
    A dedicated safety worker that can be added to any GAME Agent.

    This worker provides safety-checking functions that other workers
    can call before performing sensitive operations. It follows the
    Virtuals Protocol pattern of "Evaluator Agents" for validation.

    Now includes Memory Integrity checking to defend against memory injection
    attacks (Princeton CrAIBench found 85% success rate on unprotected agents).

    Usage:
        from sentinelseed.integrations.virtuals import SentinelSafetyWorker

        # Create the worker config
        safety_worker = SentinelSafetyWorker.create_worker_config()

        # Add to your agent
        agent = Agent(
            api_key=api_key,
            name="MyAgent",
            agent_goal="...",
            agent_description="...",
            get_agent_state_fn=get_state,
            workers=[safety_worker, my_other_worker],
        )

        # With memory integrity enabled (includes content validation by default)
        config = SentinelConfig(
            memory_integrity_check=True,
            memory_secret_key="your-secret-key",
            memory_content_validation=True,  # default, detects injection patterns
        )
        safety_worker = SentinelSafetyWorker.create_worker_config(config)
    """

    def __init__(self, config: Optional[SentinelConfig] = None):
        self.config = config or SentinelConfig()
        self.validator = SentinelValidator(self.config)
        self._memory_checker: Optional[MemoryIntegrityChecker] = None
        self._memory_store: Optional[SafeMemoryStore] = None

        # Initialize memory integrity checker if enabled
        if self.config.memory_integrity_check:
            if not MEMORY_INTEGRITY_AVAILABLE:
                logger.warning(
                    "Memory integrity requested but sentinelseed.memory module not available. "
                    "Make sure sentinelseed is installed correctly."
                )
            else:
                self._memory_checker = MemoryIntegrityChecker(
                    secret_key=self.config.memory_secret_key,
                    strict_mode=False,  # Don't raise exceptions, return validation results
                    validate_content=self.config.memory_content_validation,
                )
                self._memory_store = self._memory_checker.create_safe_memory_store()
                logger.info(
                    "Memory integrity checker initialized (content_validation=%s)",
                    self.config.memory_content_validation,
                )

    def check_action_safety(
        self,
        action_name: str,
        action_args: str = "{}",
        purpose: str = "",
    ) -> Tuple["FunctionResultStatus", str, dict]:
        """
        Check if an action is safe to execute.

        Args:
            action_name: Name of the action to check
            action_args: JSON string of action arguments
            purpose: Stated purpose for the action

        Returns:
            Tuple of (status, message, info_dict)
        """
        try:
            args = json.loads(action_args) if action_args else {}
        except json.JSONDecodeError:
            args = {"raw_input": action_args}

        result = self.validator.validate(
            action_name=action_name,
            action_args=args,
            context={"purpose": purpose} if purpose else {},
        )

        info = {
            "safe": result.passed,
            "concerns": result.concerns,
            "gate_results": result.gate_results,
            "blocked_gate": result.blocked_gate,
        }

        if result.passed:
            return (
                FunctionResultStatus.DONE,
                f"Action '{action_name}' passed all safety gates. Safe to proceed.",
                info,
            )
        else:
            return (
                FunctionResultStatus.DONE,  # Still DONE - we successfully checked
                f"Action '{action_name}' blocked by {result.blocked_gate} gate: {', '.join(result.concerns)}",
                info,
            )

    def get_safety_stats(self) -> Tuple["FunctionResultStatus", str, dict]:
        """Get statistics about safety validations performed."""
        stats = self.validator.get_stats()
        return (
            FunctionResultStatus.DONE,
            f"Validation stats: {stats['total']} total, {stats['passed']} passed, {stats['blocked']} blocked",
            stats,
        )

    def sign_state_entry(
        self,
        key: str,
        value: Any,
        source: str = "agent_internal",
    ) -> Dict[str, Any]:
        """
        Sign a state entry for integrity verification.

        Args:
            key: The state key
            value: The state value
            source: Source of this state entry (user_direct, agent_internal, etc.)

        Returns:
            Dictionary with signed entry data including HMAC signature
        """
        if not self._memory_checker:
            return {"key": key, "value": value, "signed": False}

        # Convert value to string for signing
        content = json.dumps({"key": key, "value": value}, sort_keys=True)

        # Map string source to MemorySource enum
        source_map = {
            "user_direct": MemorySource.USER_DIRECT,
            "user_verified": MemorySource.USER_VERIFIED,
            "agent_internal": MemorySource.AGENT_INTERNAL,
            "external_api": MemorySource.EXTERNAL_API,
            "blockchain": MemorySource.BLOCKCHAIN,
            "social_media": MemorySource.SOCIAL_MEDIA,
        }
        mem_source = source_map.get(source, MemorySource.UNKNOWN)

        # Create and sign entry
        entry = MemoryEntry(content=content, source=mem_source)
        signed = self._memory_checker.sign_entry(entry)

        return {
            "key": key,
            "value": value,
            "signed": True,
            "_sentinel_integrity": {
                "id": signed.id,
                "hmac": signed.hmac_signature,
                "source": signed.source,
                "timestamp": signed.timestamp,  # Required for verification
                "signed_at": signed.signed_at,
                "version": signed.version,
            },
        }

    def verify_state_entry(self, entry_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify a signed state entry's integrity.

        Args:
            entry_data: Dictionary containing the entry and its signature

        Returns:
            Dictionary with verification result
        """
        if not self._memory_checker:
            return {"valid": True, "reason": "Memory integrity check not enabled"}

        integrity = entry_data.get("_sentinel_integrity")
        if not integrity:
            return {"valid": False, "reason": "Entry not signed - missing integrity metadata"}

        # Check required fields
        required_fields = ["id", "hmac", "source", "timestamp", "signed_at", "version"]
        missing = [f for f in required_fields if f not in integrity]
        if missing:
            return {"valid": False, "reason": f"Missing integrity fields: {', '.join(missing)}"}

        # Reconstruct the signed entry
        key = entry_data.get("key")
        value = entry_data.get("value")
        content = json.dumps({"key": key, "value": value}, sort_keys=True)

        signed_entry = SignedMemoryEntry(
            id=integrity["id"],
            content=content,
            source=integrity["source"],
            timestamp=integrity["timestamp"],
            metadata={},
            hmac_signature=integrity["hmac"],
            signed_at=integrity["signed_at"],
            version=integrity["version"],
        )

        # Verify
        result = self._memory_checker.verify_entry(signed_entry)

        return {
            "valid": result.valid,
            "reason": result.reason,
            "trust_score": result.trust_score,
            "entry_id": result.entry_id,
        }

    def verify_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Verify all signed entries in a state dictionary.

        Args:
            state: State dictionary potentially containing signed entries

        Returns:
            Dictionary with verification results for all entries
        """
        if not self._memory_checker:
            return {"all_valid": True, "checked": 0, "results": {}}

        results = {}
        all_valid = True
        checked = 0

        for key, value in state.items():
            if isinstance(value, dict) and "_sentinel_integrity" in value:
                checked += 1
                result = self.verify_state_entry(value)
                results[key] = result
                if not result["valid"]:
                    all_valid = False
                    logger.warning(f"State entry '{key}' failed integrity check: {result['reason']}")

        return {
            "all_valid": all_valid,
            "checked": checked,
            "results": results,
        }

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get statistics about memory integrity checks."""
        if not self._memory_checker:
            return {"enabled": False, "content_validation": False}

        return {
            "enabled": True,
            "content_validation": self.config.memory_content_validation,
            **self._memory_checker.get_validation_stats(),
        }

    @classmethod
    def create_worker_config(
        cls,
        config: Optional[SentinelConfig] = None,
    ) -> "WorkerConfig":
        """
        Create a WorkerConfig for adding to a GAME Agent.

        Returns:
            WorkerConfig that can be passed to Agent constructor

        Example:
            safety_worker = SentinelSafetyWorker.create_worker_config()
            agent = Agent(..., workers=[safety_worker, other_workers])
        """
        if not GAME_SDK_AVAILABLE:
            raise ImportError("game-sdk is required. Install with: pip install game-sdk")

        instance = cls(config)

        # Define the check_action_safety function
        check_action_fn = Function(
            fn_name="check_action_safety",
            fn_description=(
                "Check if an action is safe to execute BEFORE performing it. "
                "Uses THSP Protocol (Truth, Harm, Scope, Purpose) validation. "
                "Call this before any sensitive operation like token transfers, "
                "approvals, swaps, or external API calls. Returns whether the "
                "action is safe and any concerns found."
            ),
            args=[
                Argument(
                    name="action_name",
                    description="Name of the action/function to check",
                    type="string",
                ),
                Argument(
                    name="action_args",
                    description="JSON string of action arguments (e.g., '{\"amount\": 100, \"recipient\": \"...\"}')",
                    type="string",
                    optional=True,
                ),
                Argument(
                    name="purpose",
                    description="Stated purpose/reason for the action",
                    type="string",
                    optional=True,
                ),
            ],
            executable=instance.check_action_safety,
        )

        # Define the get_safety_stats function
        get_stats_fn = Function(
            fn_name="get_safety_statistics",
            fn_description=(
                "Get statistics about safety validations performed. "
                "Returns total checks, passed count, blocked count, and pass rate."
            ),
            args=[],
            executable=instance.get_safety_stats,
        )

        # Define memory integrity verification function (if enabled)
        def verify_memory_integrity(
            state_json: str = "{}",
        ) -> Tuple["FunctionResultStatus", str, dict]:
            """Verify integrity of state entries with signatures."""
            if not instance._memory_checker:
                return (
                    FunctionResultStatus.DONE,
                    "Memory integrity checking is not enabled in config",
                    {"enabled": False},
                )

            try:
                state = json.loads(state_json) if state_json else {}
            except json.JSONDecodeError:
                return (
                    FunctionResultStatus.FAILED,
                    "Invalid JSON in state_json parameter",
                    {},
                )

            result = instance.verify_state(state)

            if result["all_valid"]:
                msg = f"All {result['checked']} signed entries verified successfully"
            else:
                failed = [k for k, v in result["results"].items() if not v["valid"]]
                msg = f"WARNING: {len(failed)} entries failed integrity check: {', '.join(failed)}"

            return (FunctionResultStatus.DONE, msg, result)

        verify_memory_fn = Function(
            fn_name="verify_memory_integrity",
            fn_description=(
                "Verify the integrity of signed state entries to detect tampering. "
                "Use this BEFORE trusting state data that was previously stored. "
                "Detects memory injection attacks where malicious actors modify agent memory."
            ),
            args=[
                Argument(
                    name="state_json",
                    description="JSON string of state entries to verify",
                    type="string",
                    optional=True,
                ),
            ],
            executable=verify_memory_integrity,
        )

        # State function for the worker
        def get_worker_state(
            function_result: Any, current_state: Dict[str, Any]
        ) -> Dict[str, Any]:
            """Update worker state after function execution."""
            stats = instance.validator.get_stats()
            history = instance.validator._validation_history

            state = {
                "validation_count": stats["total"],
                "pass_rate": f"{stats['pass_rate']:.1%}",
                "recent_concerns": (
                    history[-1]["concerns"] if history else []
                ),
            }

            # Add memory integrity stats if enabled
            if instance._memory_checker:
                mem_stats = instance._memory_checker.get_validation_stats()
                state["memory_integrity"] = {
                    "enabled": True,
                    "total_checks": mem_stats["total"],
                    "valid": mem_stats["valid"],
                    "invalid": mem_stats["invalid"],
                }
            else:
                state["memory_integrity"] = {"enabled": False}

            return state

        # Build action space
        action_space = [check_action_fn, get_stats_fn]
        if instance._memory_checker:
            action_space.append(verify_memory_fn)

        # Build description
        description = (
            "Sentinel Safety Worker - Validates actions through THSP Protocol "
            "(Truth, Harm, Scope, Purpose) gates. Use check_action_safety "
            "BEFORE executing any sensitive operations like token transfers, "
            "approvals, swaps, or external API calls. This worker helps prevent "
            "harmful, deceptive, or unauthorized actions."
        )
        if instance._memory_checker:
            description += (
                " Also includes memory integrity verification to detect tampering "
                "and injection attacks on agent memory."
            )

        return WorkerConfig(
            id="sentinel_safety",
            worker_description=description,
            get_state_fn=get_worker_state,
            action_space=action_space,
        )


def sentinel_protected(
    config: Optional[SentinelConfig] = None,
) -> Callable[[Callable], Callable]:
    """
    Decorator to protect a function with Sentinel validation.

    Use this for custom executables that aren't wrapped as Function objects.

    Args:
        config: Optional Sentinel configuration. If not provided, uses defaults.

    Returns:
        A decorator function that wraps the target function with validation.

    Usage:
        @sentinel_protected()
        def my_transfer(recipient: str, amount: float):
            # transfer logic
            return (FunctionResultStatus.DONE, "Transferred", {})

        @sentinel_protected(config=SentinelConfig(max_transaction_amount=50))
        def limited_transfer(recipient: str, amount: float):
            # transfer logic with lower limit
            return (FunctionResultStatus.DONE, "Transferred", {})
    """
    def decorator(func: Callable) -> Callable:
        """Wrap function with Sentinel validation."""
        cfg = config or SentinelConfig()
        validator = SentinelValidator(cfg)

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            """Execute function after Sentinel validation passes."""
            # Validate
            result = validator.validate(
                action_name=func.__name__,
                action_args=kwargs,
                context={"args": args},
            )

            if cfg.log_validations:
                status = "PASSED" if result.passed else "BLOCKED"
                logger.info(f"Sentinel [{status}] {func.__name__}")

            if not result.passed and cfg.block_unsafe:
                if GAME_SDK_AVAILABLE:
                    return (
                        FunctionResultStatus.FAILED,
                        f"Sentinel blocked: {', '.join(result.concerns)}",
                        {"sentinel_blocked": True},
                    )
                else:
                    raise SentinelValidationError(
                        f"Action '{func.__name__}' blocked by Sentinel",
                        gate=result.blocked_gate or "unknown",
                        concerns=result.concerns,
                    )

            return func(*args, **kwargs)

        return wrapper
    return decorator


__all__ = [
    "SentinelConfig",
    "SentinelValidator",
    "ValidationResult",
    "SentinelValidationError",
    "THSPGate",
    "SentinelSafetyWorker",
    "create_sentinel_function",
    "wrap_functions_with_sentinel",
    "sentinel_protected",
    "GAME_SDK_AVAILABLE",
    "MEMORY_INTEGRITY_AVAILABLE",
    "FIDUCIARY_AVAILABLE",
    # Re-export fiduciary types for convenience
    "UserContext",
    "RiskTolerance",
]
