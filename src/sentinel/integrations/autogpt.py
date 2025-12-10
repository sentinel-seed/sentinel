"""
AutoGPT integration for Sentinel AI.

Provides safety validation patterns for autonomous agents:
- SentinelSafetyComponent: Validation component for agent actions
- SentinelGuard: Decorator/wrapper for protected execution
- safety_check: Standalone function for quick validation

IMPORTANT: This integration provides VALIDATION PATTERNS, not native AutoGPT
plugins. AutoGPT's architecture has changed significantly (now a web platform
with Server/Frontend in v0.6+). These components work with ANY autonomous
agent framework that needs action/output validation.

Usage patterns:

    # Pattern 1: Validation component in your agent
    from sentinel.integrations.autogpt import SentinelSafetyComponent

    class MyAgent:
        def __init__(self):
            self.safety = SentinelSafetyComponent()

        def execute(self, action):
            check = self.safety.validate_action(action)
            if not check.should_proceed:
                return f"Blocked: {check.recommendation}"
            # proceed with action

    # Pattern 2: Decorator for protected functions
    from sentinel.integrations.autogpt import SentinelGuard

    guard = SentinelGuard()

    @guard.protected
    def execute_command(cmd):
        # your logic
        pass

    # Pattern 3: Quick standalone check
    from sentinel.integrations.autogpt import safety_check

    result = safety_check("Delete all files")
    if not result["safe"]:
        print(f"Blocked: {result['concerns']}")
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel


@dataclass
class SafetyCheckResult:
    """Result of a safety check."""
    safe: bool
    action: str
    concerns: List[str] = field(default_factory=list)
    risk_level: str = "low"
    should_proceed: bool = True
    recommendation: str = ""


class SentinelSafetyComponent:
    """
    AutoGPT Component for Sentinel safety validation.

    Integrates with AutoGPT's component system to provide
    safety checks on agent actions and thoughts.

    Example:
        from sentinel.integrations.autogpt import SentinelSafetyComponent

        class MyAgent:
            def __init__(self):
                self.safety = SentinelSafetyComponent()

            def execute_action(self, action):
                check = self.safety.validate_action(action)
                if not check.should_proceed:
                    return f"Blocked: {check.recommendation}"
                # proceed with action
    """

    name = "SentinelSafety"
    description = "AI safety validation using THSP protocol"

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        seed_level: str = "standard",
        block_unsafe: bool = True,
        log_checks: bool = True,
    ):
        """
        Initialize component.

        Args:
            sentinel: Sentinel instance (creates default if None)
            seed_level: Which seed level to use
            block_unsafe: Whether to block unsafe actions
            log_checks: Whether to log safety checks
        """
        self.sentinel = sentinel or Sentinel(seed_level=seed_level)
        self.block_unsafe = block_unsafe
        self.log_checks = log_checks
        self.check_history: List[SafetyCheckResult] = []

    def validate_action(self, action: str) -> SafetyCheckResult:
        """
        Validate an agent action for safety.

        Args:
            action: Action description or command

        Returns:
            SafetyCheckResult with validation details
        """
        # Check for physical action safety
        is_safe, concerns = self.sentinel.validate_action(action)

        # Check for request-level issues
        request_check = self.sentinel.validate_request(action)

        # Combine assessments
        all_concerns = concerns + request_check.get("concerns", [])
        should_proceed = is_safe and request_check["should_proceed"]

        # Determine recommendation
        if should_proceed:
            recommendation = "Action validated, safe to proceed."
        elif not is_safe:
            recommendation = f"Action blocked: {', '.join(concerns)}"
        else:
            recommendation = f"Request flagged: {', '.join(request_check['concerns'])}"

        result = SafetyCheckResult(
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

    def validate_thought(self, thought: str) -> SafetyCheckResult:
        """
        Validate agent thoughts/reasoning for safety concerns.

        Args:
            thought: Agent's thought or reasoning

        Returns:
            SafetyCheckResult
        """
        is_safe, violations = self.sentinel.validate(thought)
        request_check = self.sentinel.validate_request(thought)

        all_concerns = violations + request_check.get("concerns", [])

        return SafetyCheckResult(
            safe=is_safe,
            action=f"thought: {thought[:50]}...",
            concerns=all_concerns,
            risk_level=request_check["risk_level"],
            should_proceed=is_safe and request_check["should_proceed"],
            recommendation="Thought validated" if is_safe else f"Concerning thought: {all_concerns}",
        )

    def validate_output(self, output: str) -> SafetyCheckResult:
        """
        Validate agent output before returning to user.

        Args:
            output: Agent's output text

        Returns:
            SafetyCheckResult
        """
        is_safe, violations = self.sentinel.validate(output)

        return SafetyCheckResult(
            safe=is_safe,
            action=f"output: {output[:50]}...",
            concerns=violations,
            risk_level="high" if not is_safe else "low",
            should_proceed=is_safe,
            recommendation="Output safe" if is_safe else f"Unsafe output: {violations}",
        )

    def get_system_prompt_addition(self) -> str:
        """
        Get Sentinel seed to add to agent's system prompt.

        Returns:
            Seed content string
        """
        return self.sentinel.get_seed()

    def get_check_history(self) -> List[SafetyCheckResult]:
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

        return {
            "total_checks": len(self.check_history),
            "blocked": blocked,
            "allowed": len(self.check_history) - blocked,
            "high_risk": high_risk,
            "block_rate": blocked / len(self.check_history) if self.check_history else 0,
        }


class SentinelGuard:
    """
    Execution guard for AutoGPT agents.

    Wraps agent execution with safety validation at each step.

    Example:
        from sentinel.integrations.autogpt import SentinelGuard

        guard = SentinelGuard()

        @guard.protected
        def execute_command(command):
            # Your command execution logic
            pass
    """

    def __init__(
        self,
        sentinel: Optional[Sentinel] = None,
        block_unsafe: bool = True,
    ):
        """
        Initialize guard.

        Args:
            sentinel: Sentinel instance
            block_unsafe: Whether to block unsafe executions
        """
        self.component = SentinelSafetyComponent(
            sentinel=sentinel,
            block_unsafe=block_unsafe,
        )

    def protected(self, func: Callable) -> Callable:
        """
        Decorator to protect a function with safety validation.

        Args:
            func: Function to protect

        Returns:
            Protected function
        """
        def wrapper(*args, **kwargs):
            # Get action description from args
            action = str(args[0]) if args else str(kwargs)

            # Validate
            check = self.component.validate_action(action)
            if not check.should_proceed:
                return {
                    "success": False,
                    "blocked": True,
                    "reason": check.recommendation,
                    "concerns": check.concerns,
                }

            # Execute
            result = func(*args, **kwargs)

            # Validate output if string
            if isinstance(result, str):
                output_check = self.component.validate_output(result)
                if not output_check.should_proceed:
                    return {
                        "success": False,
                        "blocked": True,
                        "reason": output_check.recommendation,
                        "original_output": result[:100],
                    }

            return result

        return wrapper

    def check(self, action: str) -> SafetyCheckResult:
        """
        Check an action for safety.

        Args:
            action: Action to check

        Returns:
            SafetyCheckResult
        """
        return self.component.validate_action(action)


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
        Dict with safety check results

    Example:
        from sentinel.integrations.autogpt import safety_check

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


# AutoGPT Plugin template compatibility (for older versions)
class AutoGPTPluginTemplate:
    """
    Legacy plugin template for older AutoGPT versions.

    Note: Newer AutoGPT versions use Components instead of Plugins.
    Use SentinelSafetyComponent for v0.5+ compatibility.
    """

    def __init__(self):
        self.component = SentinelSafetyComponent()

    def can_handle_pre_command(self) -> bool:
        return True

    def can_handle_post_command(self) -> bool:
        return True

    def can_handle_on_planning(self) -> bool:
        return True

    def pre_command(
        self,
        command_name: str,
        arguments: Dict[str, Any],
    ) -> tuple:
        """
        Pre-command hook for safety validation.

        Returns:
            Tuple of (modified_command, modified_arguments) or raises
        """
        action = f"{command_name}: {arguments}"
        check = self.component.validate_action(action)

        if not check.should_proceed:
            # Block by returning a safe no-op command
            return ("think", {"thought": f"Action blocked by Sentinel: {check.recommendation}"})

        return (command_name, arguments)

    def post_command(
        self,
        command_name: str,
        response: str,
    ) -> str:
        """
        Post-command hook for output validation.

        Returns:
            Validated or modified response
        """
        check = self.component.validate_output(response)

        if not check.should_proceed:
            return f"[SENTINEL FILTERED] Output contained safety concerns: {check.concerns}"

        return response

    def on_planning(
        self,
        prompt: str,
        messages: List[Dict[str, str]],
    ) -> Optional[str]:
        """
        Planning hook to inject safety seed.

        Returns:
            Modified prompt with safety seed
        """
        seed = self.component.get_system_prompt_addition()
        return f"{seed}\n\n{prompt}"
