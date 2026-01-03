"""
AutoGPT integration for Sentinel AI.

MIGRATION NOTICE:
    AutoGPT Platform (v0.6+) uses a Block SDK architecture. For the new
    AutoGPT Platform, use the `autogpt_block` integration instead:

    # For AutoGPT Platform (v0.6+) - Standalone functions
    from sentinelseed.integrations.autogpt_block import (
        validate_content,      # Validate text content
        check_action,          # Check if action is safe
        get_seed,              # Get safety seed
        AUTOGPT_SDK_AVAILABLE, # Check if SDK is installed
    )

    # Block classes (only when AutoGPT SDK is installed)
    if AUTOGPT_SDK_AVAILABLE:
        from sentinelseed.integrations.autogpt_block import (
            SentinelValidationBlock,
            SentinelActionCheckBlock,
            SentinelSeedBlock,
        )

    # For standalone validation (no AutoGPT dependency)
    from sentinelseed.integrations.agent_validation import SafetyValidator

    # Legacy (this module) - for old AutoGPT versions only
    from sentinelseed.integrations.autogpt import SentinelSafetyComponent

    NOTE: The autogpt_block integration uses heuristic validation. For
    security-critical applications requiring semantic validation, configure
    an API key or use sentinelseed.integrations.agent_validation directly.

This module is maintained for backward compatibility with pre-v0.6 AutoGPT.
All imports are re-exported from agent_validation.py.
"""

import warnings
from typing import Any, Dict, List, Optional, Tuple

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
    "For standalone validation, use sentinelseed.integrations.agent_validation. "
    "See: https://sentinelseed.dev/docs/integrations/autogpt",
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
    ) -> Tuple[str, Dict[str, Any]]:
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


# B001: Explicit exports
__all__ = [
    # From agent_validation
    "ValidationResult",
    "SafetyValidator",
    "ExecutionGuard",
    "safety_check",
    # Backward compatibility aliases
    "SafetyCheckResult",
    "SentinelSafetyComponent",
    "SentinelGuard",
    # Legacy
    "AutoGPTPluginTemplate",
]
