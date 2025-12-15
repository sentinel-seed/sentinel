"""
Agent Validation - Framework-agnostic safety validation for autonomous agents.

This module provides reusable safety validation components that work with ANY
autonomous agent framework. Uses semantic LLM-based validation for accurate,
context-aware safety analysis.

Components:
    - SafetyValidator: Core validation using semantic LLM analysis
    - ExecutionGuard: Decorator/wrapper for protected function execution
    - safety_check: Standalone function for quick validation

Usage:

    # Pattern 1: Validation component in your agent
    from sentinelseed.integrations.agent_validation import SafetyValidator

    class MyAgent:
        def __init__(self):
            self.safety = SafetyValidator(
                provider="openai",  # or "anthropic"
                model="gpt-4o-mini",
            )

        def execute(self, action):
            result = self.safety.validate_action(action)
            if not result.should_proceed:
                return f"Blocked: {result.reasoning}"
            # proceed with action

    # Pattern 2: Decorator for protected functions
    from sentinelseed.integrations.agent_validation import ExecutionGuard

    guard = ExecutionGuard(provider="openai")

    @guard.protected
    def execute_command(cmd):
        # your logic
        pass

    # Pattern 3: Quick standalone check
    from sentinelseed.integrations.agent_validation import safety_check

    result = safety_check("Delete all files", provider="openai")
    if not result["safe"]:
        print(f"Blocked: {result['reasoning']}")
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps
import logging

from sentinelseed import Sentinel
from sentinelseed.validators.semantic import (
    SemanticValidator,
    AsyncSemanticValidator,
    THSPResult,
    RiskLevel,
)

logger = logging.getLogger("sentinelseed.agent_validation")


@dataclass
class ValidationResult:
    """
    Result of a safety validation check.

    Attributes:
        safe: Whether the action passed safety checks
        action: The action that was validated (truncated)
        concerns: List of safety concerns identified
        risk_level: Assessed risk level
        should_proceed: Whether to proceed with the action
        reasoning: Explanation of the decision
        gate_results: Per-gate validation results
    """
    safe: bool
    action: str
    concerns: List[str] = field(default_factory=list)
    risk_level: str = "low"
    should_proceed: bool = True
    reasoning: str = ""
    gate_results: Dict[str, bool] = field(default_factory=dict)

    @classmethod
    def from_thsp(cls, thsp_result: THSPResult, action: str) -> "ValidationResult":
        """Create ValidationResult from THSPResult."""
        concerns = []
        if not thsp_result.truth_passes:
            concerns.append("Failed Truth gate: potential deception")
        if not thsp_result.harm_passes:
            concerns.append("Failed Harm gate: could cause harm")
        if not thsp_result.scope_passes:
            concerns.append("Failed Scope gate: exceeds boundaries")
        if not thsp_result.purpose_passes:
            concerns.append("Failed Purpose gate: no legitimate purpose")

        risk_str = thsp_result.risk_level.value if isinstance(thsp_result.risk_level, RiskLevel) else thsp_result.risk_level

        return cls(
            safe=thsp_result.is_safe,
            action=action[:100],
            concerns=concerns,
            risk_level=risk_str,
            should_proceed=thsp_result.is_safe,
            reasoning=thsp_result.reasoning,
            gate_results=thsp_result.gate_results,
        )


class SafetyValidator:
    """
    Core safety validation component using semantic LLM analysis.

    Uses THSP Protocol (Truth, Harm, Scope, Purpose) with real LLM
    semantic analysis - not regex pattern matching.

    Example:
        from sentinelseed.integrations.agent_validation import SafetyValidator

        validator = SafetyValidator(provider="openai", model="gpt-4o-mini")

        # Validate action
        result = validator.validate_action("transfer 100 SOL to address")
        if result.should_proceed:
            execute_transfer()
        else:
            print(f"Blocked: {result.reasoning}")
    """

    name = "SentinelSafetyValidator"
    description = "AI safety validation using semantic THSP analysis"

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        seed_level: str = "standard",
        block_unsafe: bool = True,
        log_checks: bool = True,
    ):
        """
        Initialize the safety validator.

        Args:
            provider: LLM provider ("openai" or "anthropic")
            model: Model to use (auto-detected if None)
            api_key: API key (from environment if None)
            seed_level: Seed level for seed injection
            block_unsafe: Whether to block unsafe actions
            log_checks: Whether to log safety checks
        """
        self.provider = provider
        self.model = model
        self.block_unsafe = block_unsafe
        self.log_checks = log_checks
        self.seed_level = seed_level

        # Semantic validator for real LLM-based analysis
        self._semantic = SemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )

        # Sentinel for seed retrieval
        self._sentinel = Sentinel(seed_level=seed_level)

        # History tracking
        self.check_history: List[ValidationResult] = []

    def validate_action(
        self,
        action: str,
        purpose: str = "",
    ) -> ValidationResult:
        """
        Validate an agent action using semantic LLM analysis.

        Args:
            action: Action description or command to validate
            purpose: Optional stated purpose for the action

        Returns:
            ValidationResult with detailed safety assessment
        """
        # Build full action description
        full_action = action
        if purpose:
            full_action = f"{action}\nPurpose: {purpose}"

        # Semantic validation through LLM
        thsp_result = self._semantic.validate_action(
            action_name=action,
            purpose=purpose,
        )

        result = ValidationResult.from_thsp(thsp_result, action)

        # Log if enabled
        if self.log_checks:
            self.check_history.append(result)
            if not result.should_proceed:
                logger.warning(f"[SENTINEL] Action blocked: {result.reasoning}")

        return result

    def validate_thought(self, thought: str) -> ValidationResult:
        """
        Validate agent thoughts/reasoning for safety concerns.

        Args:
            thought: Agent's thought or reasoning text

        Returns:
            ValidationResult
        """
        thsp_result = self._semantic.validate(f"Agent thought: {thought}")

        result = ValidationResult.from_thsp(thsp_result, f"thought: {thought[:50]}...")

        if self.log_checks:
            self.check_history.append(result)

        return result

    def validate_output(self, output: str) -> ValidationResult:
        """
        Validate agent output before returning to user.

        Args:
            output: Agent's output text

        Returns:
            ValidationResult
        """
        thsp_result = self._semantic.validate(f"Agent output to user: {output}")

        result = ValidationResult.from_thsp(thsp_result, f"output: {output[:50]}...")

        if self.log_checks:
            self.check_history.append(result)

        return result

    def get_seed(self) -> str:
        """
        Get Sentinel seed for injection into agent system prompt.

        Returns:
            Seed content string
        """
        return self._sentinel.get_seed()

    def get_history(self) -> List[ValidationResult]:
        """Get history of safety checks."""
        return self.check_history

    def clear_history(self) -> None:
        """Clear check history."""
        self.check_history = []

    def get_stats(self) -> Dict[str, Any]:
        """Get safety check statistics."""
        if not self.check_history:
            return {"total_checks": 0}

        blocked = sum(1 for c in self.check_history if not c.should_proceed)
        high_risk = sum(1 for c in self.check_history if c.risk_level == "high")

        semantic_stats = self._semantic.get_stats()

        return {
            "total_checks": len(self.check_history),
            "blocked": blocked,
            "allowed": len(self.check_history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(self.check_history) if self.check_history else 0,
            "provider": semantic_stats.get("provider"),
            "model": semantic_stats.get("model"),
        }


class AsyncSafetyValidator:
    """
    Async version of SafetyValidator for use with async frameworks.

    Example:
        validator = AsyncSafetyValidator(provider="openai")
        result = await validator.validate_action("transfer funds")
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        seed_level: str = "standard",
        block_unsafe: bool = True,
        log_checks: bool = True,
    ):
        self.provider = provider
        self.model = model
        self.block_unsafe = block_unsafe
        self.log_checks = log_checks

        self._semantic = AsyncSemanticValidator(
            provider=provider,
            model=model,
            api_key=api_key,
        )

        self._sentinel = Sentinel(seed_level=seed_level)
        self.check_history: List[ValidationResult] = []

    async def validate_action(
        self,
        action: str,
        purpose: str = "",
    ) -> ValidationResult:
        """Async validate an agent action."""
        thsp_result = await self._semantic.validate_action(
            action_name=action,
            purpose=purpose,
        )

        result = ValidationResult.from_thsp(thsp_result, action)

        if self.log_checks:
            self.check_history.append(result)
            if not result.should_proceed:
                logger.warning(f"[SENTINEL] Action blocked: {result.reasoning}")

        return result

    async def validate_thought(self, thought: str) -> ValidationResult:
        """Async validate agent thoughts."""
        thsp_result = await self._semantic.validate(f"Agent thought: {thought}")
        result = ValidationResult.from_thsp(thsp_result, f"thought: {thought[:50]}...")

        if self.log_checks:
            self.check_history.append(result)

        return result

    async def validate_output(self, output: str) -> ValidationResult:
        """Async validate agent output."""
        thsp_result = await self._semantic.validate(f"Agent output to user: {output}")
        result = ValidationResult.from_thsp(thsp_result, f"output: {output[:50]}...")

        if self.log_checks:
            self.check_history.append(result)

        return result

    def get_seed(self) -> str:
        """Get Sentinel seed for injection."""
        return self._sentinel.get_seed()

    def get_stats(self) -> Dict[str, Any]:
        """Get validation statistics."""
        if not self.check_history:
            return {"total_checks": 0}

        blocked = sum(1 for c in self.check_history if not c.should_proceed)
        return {
            "total_checks": len(self.check_history),
            "blocked": blocked,
            "allowed": len(self.check_history) - blocked,
            "block_rate": blocked / len(self.check_history) if self.check_history else 0,
        }


class ExecutionGuard:
    """
    Execution guard for protecting function calls with semantic validation.

    Example:
        guard = ExecutionGuard(provider="openai")

        @guard.protected
        def execute_command(command: str):
            # Your command execution logic
            return result

        result = execute_command("list files")  # Validated before running
    """

    def __init__(
        self,
        provider: str = "openai",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        block_unsafe: bool = True,
    ):
        self.validator = SafetyValidator(
            provider=provider,
            model=model,
            api_key=api_key,
            block_unsafe=block_unsafe,
        )

    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with semantic validation.

        Args:
            func: Function to protect

        Returns:
            Protected function that validates before execution
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get action description from first arg or kwargs
            action = str(args[0]) if args else str(kwargs)

            # Pre-validation
            check = self.validator.validate_action(action)
            if not check.should_proceed:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": check.reasoning,
                    "concerns": check.concerns,
                    "gate_results": check.gate_results,
                }

            # Execute the function
            result = func(*args, **kwargs)

            # Post-validation for string outputs
            if isinstance(result, str):
                output_check = self.validator.validate_output(result)
                if not output_check.should_proceed:
                    return {
                        "success": False,
                        "blocked": True,
                        "reason": output_check.reasoning,
                        "original_output": result[:100],
                    }

            return result

        return wrapper

    def check(self, action: str) -> ValidationResult:
        """Check an action without executing."""
        return self.validator.validate_action(action)


def safety_check(
    action: str,
    provider: str = "openai",
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Standalone safety check function using semantic analysis.

    Args:
        action: Action to validate
        provider: LLM provider ("openai" or "anthropic")
        model: Model to use
        api_key: API key

    Returns:
        Dict with safe, concerns, risk_level, reasoning, gate_results

    Example:
        result = safety_check("Delete all files in /tmp", provider="openai")
        if not result["safe"]:
            print(f"Blocked: {result['reasoning']}")
    """
    validator = SafetyValidator(
        provider=provider,
        model=model,
        api_key=api_key,
        log_checks=False,
    )

    result = validator.validate_action(action)

    return {
        "safe": result.safe,
        "concerns": result.concerns,
        "risk_level": result.risk_level,
        "action": result.action,
        "reasoning": result.reasoning,
        "gate_results": result.gate_results,
    }


# Aliases for backward compatibility
SafetyCheckResult = ValidationResult
SentinelSafetyComponent = SafetyValidator
SentinelGuard = ExecutionGuard


__all__ = [
    "ValidationResult",
    "SafetyValidator",
    "AsyncSafetyValidator",
    "ExecutionGuard",
    "safety_check",
    # Backward compatibility
    "SafetyCheckResult",
    "SentinelSafetyComponent",
    "SentinelGuard",
]
