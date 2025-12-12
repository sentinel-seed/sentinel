"""
AutoGPT integration for Sentinel AI.

DEPRECATION NOTICE:
    This module is maintained for backward compatibility only.
    For new projects, use `sentinel.integrations.agent_validation` instead.

    AutoGPT's architecture changed significantly in v0.6+ (now a web platform),
    making the "AutoGPT" name misleading. The new `agent_validation` module
    provides the same functionality with clearer naming.

Migration:
    # Old (still works)
    from sentinel.integrations.autogpt import SentinelSafetyComponent

    # New (recommended)
    from sentinel.integrations.agent_validation import SafetyValidator

All imports from this module are re-exported from agent_validation.py
"""

import warnings
from typing import Any, Dict, List, Optional

# Import everything from the new module
from sentinel.integrations.agent_validation import (
    ValidationResult,
    SafetyValidator,
    ExecutionGuard,
    safety_check,
)

# Backward compatibility aliases
SafetyCheckResult = ValidationResult
SentinelSafetyComponent = SafetyValidator
SentinelGuard = ExecutionGuard

# Issue deprecation warning on import (only once)
warnings.warn(
    "sentinel.integrations.autogpt is deprecated. "
    "Use sentinel.integrations.agent_validation instead.",
    DeprecationWarning,
    stacklevel=2
)


# Legacy AutoGPT Plugin template (for very old AutoGPT versions)
class AutoGPTPluginTemplate:
    """
    Legacy plugin template for older AutoGPT versions (pre-v0.5).

    DEPRECATED: AutoGPT no longer uses this plugin architecture.
    Kept for backward compatibility with very old integrations.
    """

    def __init__(self):
        self.validator = SafetyValidator()

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
        """Pre-command hook for safety validation."""
        action = f"{command_name}: {arguments}"
        check = self.validator.validate_action(action)

        if not check.should_proceed:
            return ("think", {"thought": f"Action blocked by Sentinel: {check.recommendation}"})

        return (command_name, arguments)

    def post_command(
        self,
        command_name: str,
        response: str,
    ) -> str:
        """Post-command hook for output validation."""
        check = self.validator.validate_output(response)

        if not check.should_proceed:
            return f"[SENTINEL FILTERED] Output contained safety concerns: {check.concerns}"

        return response

    def on_planning(
        self,
        prompt: str,
        messages: List[Dict[str, str]],
    ) -> Optional[str]:
        """Planning hook to inject safety seed."""
        seed = self.validator.get_seed()
        return f"{seed}\n\n{prompt}"
