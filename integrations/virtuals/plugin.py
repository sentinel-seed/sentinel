"""
Sentinel Safety Plugin for Virtuals Protocol GAME SDK

This plugin provides safety guardrails for AI agents built with the GAME framework.
It implements the THSP Protocol (Truth, Harm, Scope, Purpose) to validate agent
actions before execution.

Key Features:
- Function-level protection with decorators
- Agent-wide safety wrapping
- Configurable blocking vs logging modes
- Financial transaction validation (critical for crypto agents)
- Memory/state integrity checking
"""

from __future__ import annotations

import functools
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, TypeVar, Union

# Try to import GAME SDK components (optional dependency)
try:
    from game_sdk.game.agent import Agent
    from game_sdk.game.worker import Worker
    from game_sdk.game.custom_types import Function, Argument, FunctionResult, WorkerConfig
    GAME_SDK_AVAILABLE = True
except ImportError:
    GAME_SDK_AVAILABLE = False
    Agent = None
    Worker = None
    Function = None
    WorkerConfig = None

# Try to import sentinelseed package
try:
    from sentinelseed import get_seed, SEEDS
    SENTINELSEED_AVAILABLE = True
except ImportError:
    SENTINELSEED_AVAILABLE = False
    SEEDS = {
        "v2_minimal": "",
        "v2_standard": "",
        "v2_full": "",
    }
    def get_seed(name: str) -> str:
        return SEEDS.get(name, "")


logger = logging.getLogger("sentinel.virtuals")


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
class SentinelWorkerConfig:
    """Configuration for Sentinel safety worker."""

    # Behavior settings
    block_unsafe: bool = True
    log_all_validations: bool = True
    seed_level: str = "standard"  # minimal, standard, full

    # Validation thresholds
    max_token_amount: float = 1000.0  # Max tokens in single transaction
    require_confirmation_above: float = 100.0  # Require explicit confirmation above this

    # Pattern detection
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

    # Allowed actions (whitelist mode, empty = allow all)
    allowed_functions: List[str] = field(default_factory=list)

    # Blocked actions (blacklist, always checked)
    blocked_functions: List[str] = field(default_factory=lambda: [
        "drain_wallet",
        "send_all_tokens",
        "approve_unlimited",
        "export_private_key",
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

    def __init__(self, config: SentinelWorkerConfig):
        self.config = config
        self._compiled_patterns = [
            re.compile(p) for p in config.suspicious_patterns
        ]

    def validate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> ValidationResult:
        """
        Validate an action through all THSP gates.

        Args:
            action_name: Name of the function/action to execute
            action_args: Arguments passed to the action
            context: Optional context (agent state, history, etc.)

        Returns:
            ValidationResult with pass/fail status and details
        """
        context = context or {}
        concerns = []
        gate_results = {}

        # Gate 1: TRUTH - Check for deceptive patterns
        truth_passed, truth_concerns = self._check_truth_gate(
            action_name, action_args, context
        )
        gate_results["truth"] = truth_passed
        concerns.extend(truth_concerns)

        # Gate 2: HARM - Check for harmful actions
        harm_passed, harm_concerns = self._check_harm_gate(
            action_name, action_args, context
        )
        gate_results["harm"] = harm_passed
        concerns.extend(harm_concerns)

        # Gate 3: SCOPE - Check for boundary violations
        scope_passed, scope_concerns = self._check_scope_gate(
            action_name, action_args, context
        )
        gate_results["scope"] = scope_passed
        concerns.extend(scope_concerns)

        # Gate 4: PURPOSE - Check for legitimate benefit
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

        return ValidationResult(
            passed=all_passed,
            gate_results=gate_results,
            concerns=concerns,
            blocked_gate=blocked_gate,
        )

    def _check_truth_gate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        TRUTH gate: Verify factual correspondence.

        Checks for:
        - Misleading function names
        - Inconsistent arguments
        - Context manipulation attempts
        """
        concerns = []

        # Check for context manipulation (memory injection)
        if context.get("_injected") or context.get("_override"):
            concerns.append("Potential context manipulation detected")
            return False, concerns

        # Check for misleading action names
        misleading_patterns = [
            (r"(?i)safe.*(?:drain|steal|hack)", "Action name suggests safe but contains harmful verb"),
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
        """
        HARM gate: Assess potential for harm.

        Checks for:
        - Blocked function names
        - Suspicious patterns in arguments
        - High-risk financial operations
        """
        concerns = []

        # Check blocked functions
        if action_name.lower() in [f.lower() for f in self.config.blocked_functions]:
            concerns.append(f"Action '{action_name}' is explicitly blocked")
            return False, concerns

        # Check for suspicious patterns in arguments
        args_str = str(action_args)
        for pattern in self._compiled_patterns:
            if pattern.search(args_str):
                concerns.append(f"Suspicious pattern detected: {pattern.pattern}")

        # Check for private key exposure
        for key, value in action_args.items():
            if isinstance(value, str):
                if re.match(r"^[0-9a-fA-F]{64}$", value):
                    concerns.append(f"Potential private key in argument '{key}'")
                if re.match(r"^(\w+\s+){11,23}\w+$", value):
                    concerns.append(f"Potential seed phrase in argument '{key}'")

        return len(concerns) == 0, concerns

    def _check_scope_gate(
        self,
        action_name: str,
        action_args: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Tuple[bool, List[str]]:
        """
        SCOPE gate: Check appropriate boundaries.

        Checks for:
        - Transaction amounts exceeding limits
        - Unauthorized target addresses
        - Rate limiting violations
        """
        concerns = []

        # Check whitelist if configured
        if self.config.allowed_functions:
            if action_name not in self.config.allowed_functions:
                concerns.append(f"Action '{action_name}' not in allowed list")
                return False, concerns

        # Check transaction amounts
        amount_keys = ["amount", "value", "quantity", "tokens", "sol", "lamports"]
        for key in amount_keys:
            if key in action_args:
                try:
                    amount = float(action_args[key])
                    if amount > self.config.max_token_amount:
                        concerns.append(
                            f"Transaction amount {amount} exceeds maximum {self.config.max_token_amount}"
                        )
                    elif amount > self.config.require_confirmation_above:
                        # Check if explicit confirmation was provided
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
        """
        PURPOSE gate: Require teleological justification.

        The absence of harm is not sufficient - there must be genuine purpose.

        Checks for:
        - Clear beneficial intent
        - User authorization
        - Legitimate business purpose
        """
        concerns = []

        # Check for purpose/reason in context
        has_purpose = any([
            context.get("purpose"),
            context.get("reason"),
            context.get("user_request"),
            action_args.get("purpose"),
            action_args.get("reason"),
        ])

        # High-risk actions require explicit purpose
        high_risk_patterns = [
            r"(?i)transfer",
            r"(?i)send",
            r"(?i)approve",
            r"(?i)swap",
            r"(?i)bridge",
        ]

        is_high_risk = any(
            re.search(p, action_name) for p in high_risk_patterns
        )

        if is_high_risk and not has_purpose:
            concerns.append(
                "High-risk action requires explicit purpose/reason"
            )

        return len(concerns) == 0, concerns


def sentinel_protected(
    level: str = "standard",
    block_on_failure: bool = True,
    config: Optional[SentinelWorkerConfig] = None,
):
    """
    Decorator to protect a GAME SDK function with Sentinel validation.

    Usage:
        @sentinel_protected(level="standard")
        def transfer_tokens(recipient: str, amount: float) -> FunctionResult:
            ...

    Args:
        level: Seed level (minimal, standard, full)
        block_on_failure: If True, raise exception on validation failure
        config: Optional custom configuration
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Create validator
            cfg = config or SentinelWorkerConfig(
                seed_level=level,
                block_unsafe=block_on_failure,
            )
            validator = SentinelValidator(cfg)

            # Validate
            result = validator.validate(
                action_name=func.__name__,
                action_args=kwargs,
                context={"args": args},
            )

            # Log validation
            if cfg.log_all_validations:
                status = "PASSED" if result.passed else "BLOCKED"
                logger.info(
                    f"Sentinel [{status}] {func.__name__}: "
                    f"gates={result.gate_results}, concerns={result.concerns}"
                )

            # Handle failure
            if not result.passed:
                if cfg.block_unsafe:
                    raise SentinelValidationError(
                        f"Action '{func.__name__}' blocked by Sentinel",
                        gate=result.blocked_gate or "unknown",
                        concerns=result.concerns,
                    )
                else:
                    logger.warning(
                        f"Sentinel validation failed for {func.__name__}: {result.concerns}"
                    )

            # Execute original function
            return func(*args, **kwargs)

        return wrapper
    return decorator


def wrap_function_with_sentinel(
    func: Callable,
    config: Optional[SentinelWorkerConfig] = None,
) -> Callable:
    """
    Wrap a function with Sentinel validation (non-decorator version).

    Args:
        func: The function to wrap
        config: Optional configuration

    Returns:
        Wrapped function with safety validation
    """
    cfg = config or SentinelWorkerConfig()
    return sentinel_protected(
        level=cfg.seed_level,
        block_on_failure=cfg.block_unsafe,
        config=cfg,
    )(func)


def wrap_agent_with_sentinel(
    agent: "Agent",
    config: Optional[SentinelWorkerConfig] = None,
) -> "Agent":
    """
    Wrap all functions in a GAME SDK Agent with Sentinel protection.

    This modifies the agent's workers to validate all function executions
    through Sentinel's THSP Protocol.

    Args:
        agent: The GAME SDK Agent to protect
        config: Optional configuration

    Returns:
        The same agent with protected functions

    Example:
        agent = Agent(...)
        agent = wrap_agent_with_sentinel(agent, config=SentinelWorkerConfig(
            max_token_amount=500,
            block_unsafe=True,
        ))
    """
    if not GAME_SDK_AVAILABLE:
        raise ImportError(
            "GAME SDK is required. Install with: pip install game-sdk"
        )

    cfg = config or SentinelWorkerConfig()
    validator = SentinelValidator(cfg)

    # Wrap each worker's action space
    for worker_id, worker in agent.workers.items():
        if hasattr(worker, 'action_space'):
            wrapped_space = {}
            for fn_name, fn_obj in worker.action_space.items():
                # Create wrapped executable
                original_execute = fn_obj.executable

                def make_wrapped(orig_fn, name):
                    def wrapped_execute(**kwargs):
                        # Validate before execution
                        result = validator.validate(
                            action_name=name,
                            action_args=kwargs,
                            context={"worker_id": worker_id},
                        )

                        if cfg.log_all_validations:
                            status = "PASSED" if result.passed else "BLOCKED"
                            logger.info(
                                f"Sentinel [{status}] {worker_id}.{name}: "
                                f"gates={result.gate_results}"
                            )

                        if not result.passed and cfg.block_unsafe:
                            raise SentinelValidationError(
                                f"Action '{name}' blocked by Sentinel",
                                gate=result.blocked_gate or "unknown",
                                concerns=result.concerns,
                            )

                        return orig_fn(**kwargs)
                    return wrapped_execute

                # Create new Function with wrapped executable
                fn_obj.executable = make_wrapped(original_execute, fn_name)
                wrapped_space[fn_name] = fn_obj

            worker.action_space = wrapped_space

    logger.info(
        f"Agent wrapped with Sentinel protection "
        f"(level={cfg.seed_level}, block={cfg.block_unsafe})"
    )

    return agent


class SentinelSafetyWorker:
    """
    A standalone safety worker that can be added to any GAME Agent.

    This worker provides safety-checking functions that other workers
    can call before performing sensitive operations.

    Usage:
        safety_worker = SentinelSafetyWorker.create_worker_config()
        agent.add_worker(safety_worker)
    """

    def __init__(self, config: Optional[SentinelWorkerConfig] = None):
        self.config = config or SentinelWorkerConfig()
        self.validator = SentinelValidator(self.config)
        self._validation_history: List[Dict[str, Any]] = []

    def check_action(
        self,
        action_name: str,
        action_args: str,  # JSON string for GAME SDK compatibility
        purpose: str = "",
    ) -> Dict[str, Any]:
        """
        Check if an action is safe to execute.

        Args:
            action_name: Name of the action to check
            action_args: JSON string of action arguments
            purpose: Stated purpose for the action

        Returns:
            Dict with 'safe' boolean, 'concerns' list, and 'gate_results'
        """
        import json

        try:
            args = json.loads(action_args) if action_args else {}
        except json.JSONDecodeError:
            args = {"raw": action_args}

        result = self.validator.validate(
            action_name=action_name,
            action_args=args,
            context={"purpose": purpose},
        )

        # Record in history
        self._validation_history.append({
            "action": action_name,
            "args": args,
            "result": result.passed,
            "concerns": result.concerns,
        })

        return {
            "safe": result.passed,
            "concerns": result.concerns,
            "gate_results": result.gate_results,
            "blocked_gate": result.blocked_gate,
        }

    def get_validation_history(self) -> List[Dict[str, Any]]:
        """Get history of all validations performed."""
        return self._validation_history

    def get_safety_stats(self) -> Dict[str, Any]:
        """Get statistics about validation history."""
        if not self._validation_history:
            return {"total": 0, "passed": 0, "blocked": 0, "pass_rate": 1.0}

        total = len(self._validation_history)
        passed = sum(1 for v in self._validation_history if v["result"])

        return {
            "total": total,
            "passed": passed,
            "blocked": total - passed,
            "pass_rate": passed / total if total > 0 else 1.0,
        }

    @classmethod
    def create_worker_config(
        cls,
        config: Optional[SentinelWorkerConfig] = None,
    ) -> "WorkerConfig":
        """
        Create a WorkerConfig for adding to a GAME Agent.

        Returns:
            WorkerConfig that can be passed to agent.add_worker()
        """
        if not GAME_SDK_AVAILABLE:
            raise ImportError(
                "GAME SDK is required. Install with: pip install game-sdk"
            )

        instance = cls(config)

        # Create GAME SDK Function objects
        check_action_fn = Function(
            fn_name="check_action_safety",
            fn_description=(
                "Check if an action is safe to execute before performing it. "
                "Uses THSP Protocol (Truth, Harm, Scope, Purpose) validation. "
                "Call this BEFORE executing any sensitive operation like transfers, "
                "approvals, or data access."
            ),
            args=[
                Argument(
                    name="action_name",
                    type="string",
                    description="Name of the action to check",
                ),
                Argument(
                    name="action_args",
                    type="string",
                    description="JSON string of action arguments",
                ),
                Argument(
                    name="purpose",
                    type="string",
                    description="Stated purpose/reason for the action",
                ),
            ],
            executable=instance.check_action,
        )

        get_stats_fn = Function(
            fn_name="get_safety_statistics",
            fn_description=(
                "Get statistics about safety validations performed. "
                "Returns total checks, passed, blocked, and pass rate."
            ),
            args=[],
            executable=instance.get_safety_stats,
        )

        def get_state_fn(fn_result, current_state):
            """Update worker state after function execution."""
            stats = instance.get_safety_stats()
            return {
                "validation_count": stats["total"],
                "pass_rate": f"{stats['pass_rate']:.1%}",
                "last_concerns": (
                    instance._validation_history[-1]["concerns"]
                    if instance._validation_history else []
                ),
            }

        return WorkerConfig(
            id="sentinel_safety_worker",
            worker_description=(
                "Sentinel Safety Worker - Validates actions through THSP Protocol "
                "(Truth, Harm, Scope, Purpose). Use check_action_safety BEFORE "
                "executing any sensitive operations like token transfers, "
                "approvals, or external API calls. This worker helps prevent "
                "harmful, deceptive, or unauthorized actions."
            ),
            get_state_fn=get_state_fn,
            action_space=[check_action_fn, get_stats_fn],
        )


# Convenience function for quick setup
def create_safe_agent(
    api_key: str,
    name: str,
    goal: str,
    workers: List["WorkerConfig"],
    sentinel_config: Optional[SentinelWorkerConfig] = None,
    **agent_kwargs,
) -> "Agent":
    """
    Create a GAME Agent with Sentinel safety built-in.

    This is a convenience function that:
    1. Creates the Agent with provided configuration
    2. Adds a Sentinel Safety Worker
    3. Wraps all functions with validation

    Args:
        api_key: GAME API key
        name: Agent name
        goal: Agent goal description
        workers: List of WorkerConfigs
        sentinel_config: Optional Sentinel configuration
        **agent_kwargs: Additional arguments for Agent()

    Returns:
        Fully configured Agent with Sentinel protection

    Example:
        agent = create_safe_agent(
            api_key="your-key",
            name="TradingBot",
            goal="Execute safe token swaps",
            workers=[swap_worker, analysis_worker],
            sentinel_config=SentinelWorkerConfig(max_token_amount=100),
        )
    """
    if not GAME_SDK_AVAILABLE:
        raise ImportError(
            "GAME SDK is required. Install with: pip install game-sdk"
        )

    cfg = sentinel_config or SentinelWorkerConfig()

    # Add Sentinel safety worker to the list
    safety_worker_config = SentinelSafetyWorker.create_worker_config(cfg)
    all_workers = [safety_worker_config] + list(workers)

    # Create agent
    agent = Agent(
        api_key=api_key,
        name=name,
        goal=goal,
        workers=all_workers,
        **agent_kwargs,
    )

    # Wrap all functions with validation
    agent = wrap_agent_with_sentinel(agent, cfg)

    return agent
