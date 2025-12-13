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
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("sentinelseed.virtuals")


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
except ImportError:
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


class THSPGate(Enum):
    """The four gates of THSP Protocol."""
    TRUTH = "truth"
    HARM = "harm"
    SCOPE = "scope"
    PURPOSE = "purpose"


@dataclass
class ValidationResult:
    """Result of THSP validation."""
    passed: bool
    gate_results: Dict[str, bool] = field(default_factory=dict)
    concerns: List[str] = field(default_factory=list)
    blocked_gate: Optional[str] = None

    @property
    def failed_gates(self) -> List[str]:
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


class SentinelValidator:
    """
    Core validation engine implementing THSP Protocol.

    Validates agent actions through four gates:
    - TRUTH: Is the action based on accurate information?
    - HARM: Could this action cause harm?
    - SCOPE: Is this action within appropriate limits?
    - PURPOSE: Does this action serve a legitimate benefit?
    """

    def __init__(self, config: Optional[SentinelConfig] = None):
        self.config = config or SentinelConfig()
        self._compiled_patterns = [
            re.compile(p) for p in self.config.suspicious_patterns
        ]
        self._validation_history: List[Dict[str, Any]] = []

    def validate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate an action through all THSP gates.

        Args:
            action_name: Name of the function to execute
            action_args: Arguments passed to the function
            context: Optional context (worker state, purpose, etc.)

        Returns:
            ValidationResult with pass/fail status and details
        """
        context = context or {}
        concerns = []
        gate_results = {}

        # Gate 1: TRUTH
        truth_passed, truth_concerns = self._check_truth_gate(
            action_name, action_args, context
        )
        gate_results["truth"] = truth_passed
        concerns.extend(truth_concerns)

        # Gate 2: HARM
        harm_passed, harm_concerns = self._check_harm_gate(
            action_name, action_args, context
        )
        gate_results["harm"] = harm_passed
        concerns.extend(harm_concerns)

        # Gate 3: SCOPE
        scope_passed, scope_concerns = self._check_scope_gate(
            action_name, action_args, context
        )
        gate_results["scope"] = scope_passed
        concerns.extend(scope_concerns)

        # Gate 4: PURPOSE
        purpose_passed, purpose_concerns = self._check_purpose_gate(
            action_name, action_args, context
        )
        gate_results["purpose"] = purpose_passed
        concerns.extend(purpose_concerns)

        # All gates must pass
        all_passed = all(gate_results.values())
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
    """

    def __init__(self, config: Optional[SentinelConfig] = None):
        self.config = config or SentinelConfig()
        self.validator = SentinelValidator(self.config)

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

        # State function for the worker
        def get_worker_state(function_result, current_state):
            """Update worker state after function execution."""
            stats = instance.validator.get_stats()
            history = instance.validator._validation_history
            return {
                "validation_count": stats["total"],
                "pass_rate": f"{stats['pass_rate']:.1%}",
                "recent_concerns": (
                    history[-1]["concerns"] if history else []
                ),
            }

        return WorkerConfig(
            id="sentinel_safety",
            worker_description=(
                "Sentinel Safety Worker - Validates actions through THSP Protocol "
                "(Truth, Harm, Scope, Purpose) gates. Use check_action_safety "
                "BEFORE executing any sensitive operations like token transfers, "
                "approvals, swaps, or external API calls. This worker helps prevent "
                "harmful, deceptive, or unauthorized actions."
            ),
            get_state_fn=get_worker_state,
            action_space=[check_action_fn, get_stats_fn],
        )


def sentinel_protected(
    config: Optional[SentinelConfig] = None,
):
    """
    Decorator to protect a function with Sentinel validation.

    Use this for custom executables that aren't wrapped as Function objects.

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
        cfg = config or SentinelConfig()
        validator = SentinelValidator(cfg)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
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
]
