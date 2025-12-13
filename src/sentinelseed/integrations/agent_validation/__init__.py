"""
Agent Validation - Framework-agnostic safety validation for autonomous agents.

This module provides reusable safety validation components that work with ANY
autonomous agent framework. Originally designed for AutoGPT, but the architecture
change in AutoGPT v0.6+ (now a web platform) means these components are better
understood as generic validation patterns.

Components:
    - SafetyValidator: Core validation component for agent actions
    - ExecutionGuard: Decorator/wrapper for protected function execution
    - safety_check: Standalone function for quick validation

Usage with any agent framework:

    # Pattern 1: Validation component in your agent
    from sentinelseed.integrations.agent_validation import SafetyValidator

    class MyAgent:
        def __init__(self):
            self.safety = SafetyValidator()

        def execute(self, action):
            check = self.safety.validate_action(action)
            if not check.should_proceed:
                return f"Blocked: {check.recommendation}"
            # proceed with action

    # Pattern 2: Decorator for protected functions
    from sentinelseed.integrations.agent_validation import ExecutionGuard

    guard = ExecutionGuard()

    @guard.protected
    def execute_command(cmd):
        # your logic
        pass

    # Pattern 3: Quick standalone check
    from sentinelseed.integrations.agent_validation import safety_check

    result = safety_check("Delete all files")
    if not result["safe"]:
        print(f"Blocked: {result['concerns']}")

Compatible frameworks:
    - Custom autonomous agents
    - LangChain agents (alternative to callback approach)
    - Any framework that executes actions based on LLM output
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from functools import wraps

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel


@dataclass
class ValidationResult:
    """
    Result of a safety validation check.

    Attributes:
        safe: Whether the action passed safety checks
        action: The action that was validated (truncated)
        concerns: List of safety concerns identified
        risk_level: Assessed risk level (low/medium/high)
        should_proceed: Whether to proceed with the action
        recommendation: Human-readable recommendation
    """
    safe: bool
    action: str
    concerns: List[str] = field(default_factory=list)
    risk_level: str = "low"
    should_proceed: bool = True
    recommendation: str = ""


class SafetyValidator:
    """
    Core safety validation component for autonomous agents.

    Provides methods to validate actions, thoughts, and outputs
    using Sentinel's THSP protocol.

    Example:
        from sentinelseed.integrations.agent_validation import SafetyValidator

        validator = SafetyValidator()

        # Before executing any action
        check = validator.validate_action("transfer 100 SOL to address")
        if check.should_proceed:
            execute_transfer()
        else:
            log_blocked_action(check.recommendation)
    """

    name = "SentinelSafetyValidator"
    description = "AI safety validation using THSP protocol"

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        block_unsafe: bool = True,
        log_checks: bool = True,
    ):
        """
        Initialize the safety validator.

        Args:
            sentinel: Sentinel instance (creates default if None)
            seed_level: Which seed level to use (minimal/standard/full)
            block_unsafe: Whether to block unsafe actions
            log_checks: Whether to log safety checks to console
        """
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.block_unsafe = block_unsafe
        self.log_checks = log_checks
        self.check_history: List[ValidationResult] = []

    def validate_action(self, action: str) -> ValidationResult:
        """
        Validate an agent action for safety.

        Args:
            action: Action description or command to validate

        Returns:
            ValidationResult with detailed safety assessment

        Example:
            result = validator.validate_action("delete user account")
            if not result.should_proceed:
                print(f"Blocked: {result.concerns}")
        """
        # Check for physical/destructive action safety
        is_safe, concerns = self.sentinel.validate_action(action)

        # Check for request-level issues (jailbreaks, etc.)
        request_check = self.sentinel.validate_request(action)

        # Combine assessments
        all_concerns = concerns + request_check.get("concerns", [])
        should_proceed = is_safe and request_check["should_proceed"]

        # Generate recommendation
        if should_proceed:
            recommendation = "Action validated, safe to proceed."
        elif not is_safe:
            recommendation = f"Action blocked: {', '.join(concerns)}"
        else:
            recommendation = f"Request flagged: {', '.join(request_check['concerns'])}"

        result = ValidationResult(
            safe=is_safe,
            action=action[:100],
            concerns=all_concerns,
            risk_level=request_check["risk_level"],
            should_proceed=should_proceed if not self.block_unsafe else should_proceed,
            recommendation=recommendation,
        )

        # Log if enabled
        if self.log_checks:
            self.check_history.append(result)
            if not should_proceed:
                print(f"[SENTINEL] Action blocked: {result.recommendation}")

        return result

    def validate_thought(self, thought: str) -> ValidationResult:
        """
        Validate agent thoughts/reasoning for safety concerns.

        Useful for catching problematic reasoning before it leads to actions.

        Args:
            thought: Agent's thought or reasoning text

        Returns:
            ValidationResult
        """
        is_safe, violations = self.sentinel.validate(thought)
        request_check = self.sentinel.validate_request(thought)

        all_concerns = violations + request_check.get("concerns", [])

        return ValidationResult(
            safe=is_safe,
            action=f"thought: {thought[:50]}...",
            concerns=all_concerns,
            risk_level=request_check["risk_level"],
            should_proceed=is_safe and request_check["should_proceed"],
            recommendation="Thought validated" if is_safe else f"Concerning thought: {all_concerns}",
        )

    def validate_output(self, output: str) -> ValidationResult:
        """
        Validate agent output before returning to user.

        Args:
            output: Agent's output text

        Returns:
            ValidationResult
        """
        is_safe, violations = self.sentinel.validate(output)

        return ValidationResult(
            safe=is_safe,
            action=f"output: {output[:50]}...",
            concerns=violations,
            risk_level="high" if not is_safe else "low",
            should_proceed=is_safe,
            recommendation="Output safe" if is_safe else f"Unsafe output: {violations}",
        )

    def get_seed(self) -> str:
        """
        Get Sentinel seed for injection into agent system prompt.

        Returns:
            Seed content string
        """
        return self.sentinel.get_seed()

    def get_history(self) -> List[ValidationResult]:
        """Get history of safety checks."""
        return self.check_history

    def clear_history(self) -> None:
        """Clear check history."""
        self.check_history = []

    def get_stats(self) -> Dict[str, Any]:
        """
        Get safety check statistics.

        Returns:
            Dict with total_checks, blocked, allowed, high_risk, block_rate
        """
        if not self.check_history:
            return {"total_checks": 0}

        blocked = sum(1 for c in self.check_history if not c.should_proceed)
        high_risk = sum(1 for c in self.check_history if c.risk_level == "high")

        return {
            "total_checks": len(self.check_history),
            "blocked": blocked,
            "allowed": len(self.check_history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(self.check_history) if self.check_history else 0,
        }


class ExecutionGuard:
    """
    Execution guard for protecting function calls with safety validation.

    Wraps function execution with pre-validation and optional output validation.

    Example:
        from sentinelseed.integrations.agent_validation import ExecutionGuard

        guard = ExecutionGuard()

        @guard.protected
        def execute_command(command: str):
            # Your command execution logic
            return result

        # Now execute_command will be validated before running
        result = execute_command("list files")  # Allowed
        result = execute_command("delete all files")  # Blocked
    """

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        block_unsafe: bool = True,
    ):
        """
        Initialize the execution guard.

        Args:
            sentinel: Sentinel instance
            block_unsafe: Whether to block unsafe executions
        """
        self.validator = SafetyValidator(
            sentinel=sentinel,
            block_unsafe=block_unsafe,
        )

    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with safety validation.

        Args:
            func: Function to protect

        Returns:
            Protected function that validates before execution

        Example:
            @guard.protected
            def risky_operation(action: str):
                # do something
                pass
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
                    "reason": check.recommendation,
                    "concerns": check.concerns,
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
                        "reason": output_check.recommendation,
                        "original_output": result[:100],
                    }

            return result

        return wrapper

    def check(self, action: str) -> ValidationResult:
        """
        Check an action for safety without executing anything.

        Args:
            action: Action to check

        Returns:
            ValidationResult
        """
        return self.validator.validate_action(action)


def safety_check(
    action: str,
    sentinel: Optional[Sentinel] = None,
) -> Dict[str, Any]:
    """
    Standalone safety check function.

    Convenience function for quick safety validation without
    setting up components.

    Args:
        action: Action to validate
        sentinel: Optional Sentinel instance

    Returns:
        Dict with safe, concerns, risk_level, action, recommendation

    Example:
        from sentinelseed.integrations.agent_validation import safety_check

        result = safety_check("Delete all files in /tmp")
        if not result["safe"]:
            print(f"Action blocked: {result['concerns']}")
    """
    if sentinel is None:
        sentinel = Sentinel()

    # Validate action
    is_safe, concerns = sentinel.validate_action(action)
    request_check = sentinel.validate_request(action)

    all_concerns = concerns + request_check.get("concerns", [])
    should_proceed = is_safe and request_check["should_proceed"]

    return {
        "safe": should_proceed,
        "concerns": all_concerns,
        "risk_level": request_check["risk_level"],
        "action": action[:100],
        "recommendation": "Safe to proceed" if should_proceed else f"Blocked: {all_concerns}",
    }


# Aliases for backward compatibility with autogpt.py imports
SafetyCheckResult = ValidationResult
SentinelSafetyComponent = SafetyValidator
SentinelGuard = ExecutionGuard
