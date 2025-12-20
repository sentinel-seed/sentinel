"""
AutoGPT integration for Sentinel AI.

MIGRATION NOTICE:
    AutoGPT Platform (v0.6+) uses a Block SDK architecture. For the new
    AutoGPT Platform, use the `autogpt_block` integration instead:

    # For AutoGPT Platform (v0.6+) - Block SDK
    from sentinelseed.integrations.autogpt_block import (
        SentinelValidationBlock,
        SentinelActionCheckBlock,
        SentinelSeedBlock,
    )

    # For standalone validation (no AutoGPT dependency)
    from sentinelseed.integrations.agent_validation import SafetyValidator

    # Legacy (this module) - for old AutoGPT versions only
    from sentinelseed.integrations.autogpt import SentinelSafetyComponent

This module is maintained for backward compatibility with pre-v0.6 AutoGPT.
All imports are re-exported from agent_validation.py.
"""

import warnings
from typing import Any, Dict, List, Optional

# Import everything from the new module
from sentinelseed.integrations.agent_validation import (
    ValidationResult,
    SafetyValidator,
    ExecutionGuard,
    safety_check,
)

# Backward compatibility aliases
SafetyCheckResult = ValidationResult
SentinelSafetyComponent = SafetyValidator
SentinelGuard = ExecutionGuard

# Issue migration warning on import (only once)
warnings.warn(
    "sentinelseed.integrations.autogpt is for legacy AutoGPT (pre-v0.6). "
    "For AutoGPT Platform v0.6+, use sentinelseed.integrations.autogpt_block. "
    "For standalone validation, use sentinelseed.integrations.agent_validation.",
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
            return ("think", {"thought": f"Action blocked by Sentinel: {check.reasoning}"})

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
