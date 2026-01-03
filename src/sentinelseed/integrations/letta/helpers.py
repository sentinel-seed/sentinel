"""
Helper functions for Sentinel Letta integration.

This module provides utility functions for message validation,
approval handling, and tool call validation.

Functions:
    - validate_message: Validate a message through THSP
    - validate_tool_call: Validate a tool invocation
    - sentinel_approval_handler: Handle approval requests with THSP

Classes:
    - ApprovalDecision: Result of an approval decision
"""

from typing import Any, Dict, List, Literal, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import logging

from sentinelseed.integrations._base import (
    LayeredValidator,
    AsyncLayeredValidator,
    ValidationConfig,
)

_logger = logging.getLogger("sentinelseed.integrations.letta")

# Valid configuration values
VALID_MODES = ("block", "flag", "log")
VALID_PROVIDERS = ("openai", "anthropic")


def _validate_provider(provider: str) -> None:
    """Validate provider is supported."""
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider '{provider}'. Must be one of: {VALID_PROVIDERS}")


def _sanitize_for_log(text: str, max_length: int = 50) -> str:
    """Sanitize text for logging to avoid exposing sensitive content."""
    if not text:
        return "<empty>"
    if len(text) <= max_length:
        return f"[{len(text)} chars]"
    return f"[{len(text)} chars]"


class ApprovalStatus(str, Enum):
    """Status of an approval decision."""
    APPROVED = "approved"
    DENIED = "denied"
    PENDING = "pending"


@dataclass
class ApprovalDecision:
    """
    Result of a Sentinel approval decision.

    Attributes:
        status: The decision status
        approve: Whether to approve (True/False)
        tool_call_id: ID of the tool call being decided
        reason: Reason for the decision
        gates: Results of THSP gates
        suggested_modification: Suggested safe alternative (if denied)
    """

    status: ApprovalStatus
    approve: bool
    tool_call_id: str
    reason: str
    gates: Dict[str, bool] = field(default_factory=dict)
    suggested_modification: Optional[str] = None

    def to_approval_message(self) -> Dict[str, Any]:
        """
        Convert to Letta approval message format.

        Returns:
            Dict suitable for client.agents.messages(agent_id).create()
        """
        return {
            "type": "approval",
            "approvals": [
                {
                    "approve": self.approve,
                    "tool_call_id": self.tool_call_id,
                    "reason": self.reason,
                }
            ],
        }


def validate_message(
    content: str,
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate a message through Sentinel THSP gates.

    Can be used for manual validation before sending messages
    or processing agent responses.

    Args:
        content: Message content to validate
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model for validation

    Returns:
        Dict with validation results:
            - is_safe: bool or None if validation unavailable
            - gates: Dict of gate results
            - reasoning: str explanation
            - failed_gates: List of failed gate names
            - method: "semantic", "heuristic", or "none"

    Raises:
        ValueError: If content is None or provider is invalid

    Example:
        result = validate_message(
            "How do I bypass the security system?",
            api_key="sk-..."
        )
        if not result["is_safe"]:
            print(f"Blocked: {result['reasoning']}")
    """
    # Input validation
    if content is None:
        raise ValueError("content cannot be None")

    if not isinstance(content, str):
        raise ValueError(f"content must be a string, got {type(content).__name__}")

    # Validate provider
    _validate_provider(provider)

    # Handle empty content
    if not content.strip():
        return {
            "is_safe": True,
            "gates": {"truth": True, "harm": True, "scope": True, "purpose": True},
            "reasoning": "Empty content - no validation needed",
            "failed_gates": [],
            "method": "validation",
        }

    # Use LayeredValidator for unified validation
    try:
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=bool(api_key),
            semantic_provider=provider,
            semantic_model=model,
            semantic_api_key=api_key,
        )
        validator = LayeredValidator(config=config)
        result = validator.validate(content)

        # Determine method based on which layer responded
        layer_value = result.layer.value if hasattr(result.layer, 'value') else str(result.layer)
        method = "semantic" if layer_value in ("semantic", "both") else "heuristic"

        # Safely extract details
        gates = {}
        if hasattr(result, 'details') and isinstance(result.details, dict):
            gates = result.details.get("gate_results", {})

        violations = result.violations if hasattr(result, 'violations') and result.violations else []

        return {
            "is_safe": result.is_safe,
            "gates": gates,
            "reasoning": "; ".join(violations) if violations else "Content passed validation",
            "failed_gates": violations,
            "method": method,
        }
    except ImportError:
        _logger.warning("LayeredValidator not available - cannot verify safety")
        return {
            "is_safe": None,
            "gates": {},
            "reasoning": "No validator available - safety cannot be verified",
            "failed_gates": [],
            "method": "none",
        }
    except (ValueError, TypeError, RuntimeError, AttributeError) as e:
        _logger.warning(f"Validation error: {type(e).__name__}")
        return {
            "is_safe": None,
            "gates": {},
            "reasoning": "Validation error occurred",
            "failed_gates": [],
            "method": "error",
        }


def validate_tool_call(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    high_risk_tools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Validate a tool invocation through THSP gates.

    Analyzes the tool and its arguments to determine if the
    invocation is safe to execute.

    Args:
        tool_name: Name of the tool being called
        arguments: Arguments being passed to the tool (optional)
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        high_risk_tools: List of tools considered high risk

    Returns:
        Dict with validation results:
            - is_safe: bool or None if validation unavailable
            - gates: Dict of gate results
            - reasoning: str explanation
            - risk_level: "low", "medium", "high"
            - tool_name: The validated tool name

    Raises:
        ValueError: If tool_name is None/empty or provider is invalid

    Example:
        result = validate_tool_call(
            tool_name="run_code",
            arguments={"code": "import os; os.system('rm -rf /')"},
            api_key="sk-..."
        )
        # result["is_safe"] = False
    """
    # Input validation
    if tool_name is None:
        raise ValueError("tool_name cannot be None")

    if not isinstance(tool_name, str):
        raise ValueError(f"tool_name must be a string, got {type(tool_name).__name__}")

    if not tool_name.strip():
        raise ValueError("tool_name cannot be empty")

    # Validate provider
    _validate_provider(provider)

    # Normalize arguments
    if arguments is None:
        arguments = {}
    elif not isinstance(arguments, dict):
        # Try to convert or use as-is in string form
        try:
            arguments = {"value": str(arguments)}
        except (ValueError, TypeError):
            arguments = {}

    high_risk = high_risk_tools or [
        "run_code", "web_search", "send_message",
        "delete", "modify", "execute",
    ]

    # Determine risk level
    risk_level = "low"
    tool_name_lower = tool_name.lower()
    if tool_name in high_risk:
        risk_level = "high"
    elif any(kw in tool_name_lower for kw in ["write", "update", "send", "delete", "remove"]):
        risk_level = "medium"

    # Build content for validation
    # Limit argument representation to avoid very long strings
    args_str = str(arguments)
    if len(args_str) > 500:
        args_str = args_str[:500] + "..."
    content = f"Tool: {tool_name}\nArguments: {args_str}"

    # Validate
    validation = validate_message(
        content=content,
        api_key=api_key,
        provider=provider,
        model=model,
    )

    validation["risk_level"] = risk_level
    validation["tool_name"] = tool_name

    return validation


def sentinel_approval_handler(
    approval_request: Dict[str, Any],
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    auto_approve_safe: bool = True,
    auto_deny_unsafe: bool = True,
) -> ApprovalDecision:
    """
    Handle a Letta approval request using Sentinel THSP validation.

    When an agent calls a tool that requires approval, this handler
    can automatically validate and approve/deny based on THSP gates.

    Args:
        approval_request: The approval request from Letta containing
            tool_name, arguments, and tool_call_id
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        auto_approve_safe: Automatically approve safe requests
        auto_deny_unsafe: Automatically deny unsafe requests

    Returns:
        ApprovalDecision with approve/deny decision

    Raises:
        ValueError: If approval_request is invalid

    Example:
        # In message handler:
        for msg in response.messages:
            if hasattr(msg, 'approval_request'):
                decision = sentinel_approval_handler(
                    msg.approval_request,
                    api_key="sk-...",
                    auto_approve_safe=True
                )
                client.agents.messages(agent.id).create(
                    messages=[decision.to_approval_message()]
                )
    """
    # Input validation
    if approval_request is None:
        raise ValueError("approval_request cannot be None")

    if not isinstance(approval_request, dict):
        raise ValueError(f"approval_request must be a dict, got {type(approval_request).__name__}")

    # Extract fields with safe defaults
    tool_name = approval_request.get("tool_name")
    if not tool_name:
        tool_name = "unknown"

    arguments = approval_request.get("arguments")
    if not isinstance(arguments, dict):
        arguments = {}

    tool_call_id = approval_request.get("tool_call_id")
    if not tool_call_id:
        tool_call_id = "unknown"

    # Validate the tool call
    try:
        validation = validate_tool_call(
            tool_name=tool_name,
            arguments=arguments,
            api_key=api_key,
            provider=provider,
            model=model,
        )
    except ValueError as e:
        # If validation itself fails, return pending for manual review
        return ApprovalDecision(
            status=ApprovalStatus.PENDING,
            approve=False,
            tool_call_id=tool_call_id,
            reason=f"Validation error: {str(e)}",
            gates={},
        )

    is_safe = validation.get("is_safe")
    reasoning = validation.get("reasoning", "Unknown")
    gates = validation.get("gates", {})

    # Handle is_safe = None (validator unavailable)
    if is_safe is None:
        return ApprovalDecision(
            status=ApprovalStatus.PENDING,
            approve=False,
            tool_call_id=tool_call_id,
            reason=f"Manual review required - validator unavailable. {reasoning}",
            gates=gates,
        )

    # Make decision based on validation result
    if is_safe is True and auto_approve_safe:
        return ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approve=True,
            tool_call_id=tool_call_id,
            reason=f"Sentinel THSP: {reasoning}",
            gates=gates,
        )

    if is_safe is False and auto_deny_unsafe:
        failed_gates = validation.get("failed_gates", [])
        reason_detail = ", ".join(failed_gates) if failed_gates else reasoning
        return ApprovalDecision(
            status=ApprovalStatus.DENIED,
            approve=False,
            tool_call_id=tool_call_id,
            reason=f"Sentinel THSP blocked: {reason_detail}",
            gates=gates,
            suggested_modification="Consider rephrasing the request to be more specific about the legitimate purpose.",
        )

    # Return pending for manual review
    return ApprovalDecision(
        status=ApprovalStatus.PENDING,
        approve=False,
        tool_call_id=tool_call_id,
        reason=f"Manual review required. THSP result: {reasoning}",
        gates=gates,
    )


async def async_validate_message(
    content: str,
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Async version of validate_message.

    Args:
        content: Message content to validate
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation

    Returns:
        Dict with validation results

    Raises:
        ValueError: If content is None or provider is invalid
    """
    # Input validation (same as sync version)
    if content is None:
        raise ValueError("content cannot be None")

    if not isinstance(content, str):
        raise ValueError(f"content must be a string, got {type(content).__name__}")

    _validate_provider(provider)

    # Handle empty content
    if not content.strip():
        return {
            "is_safe": True,
            "gates": {"truth": True, "harm": True, "scope": True, "purpose": True},
            "reasoning": "Empty content - no validation needed",
            "failed_gates": [],
            "method": "validation",
        }

    # Use AsyncLayeredValidator for unified async validation
    try:
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=bool(api_key),
            semantic_provider=provider,
            semantic_model=model,
            semantic_api_key=api_key,
        )
        validator = AsyncLayeredValidator(config=config)
        result = await validator.validate(content)

        # Determine method based on which layer responded
        layer_value = result.layer.value if hasattr(result.layer, 'value') else str(result.layer)
        method = "semantic" if layer_value in ("semantic", "both") else "heuristic"

        # Safely extract details
        gates = {}
        if hasattr(result, 'details') and isinstance(result.details, dict):
            gates = result.details.get("gate_results", {})

        violations = result.violations if hasattr(result, 'violations') and result.violations else []

        return {
            "is_safe": result.is_safe,
            "gates": gates,
            "reasoning": "; ".join(violations) if violations else "Content passed validation",
            "failed_gates": violations,
            "method": method,
        }
    except ImportError:
        _logger.warning("AsyncLayeredValidator not available, using sync fallback")
        return validate_message(content, api_key, provider, model)
    except (ValueError, TypeError, RuntimeError, AttributeError) as e:
        _logger.warning(f"Async validation error: {type(e).__name__}")
        return {
            "is_safe": None,
            "gates": {},
            "reasoning": "Validation error occurred",
            "failed_gates": [],
            "method": "error",
        }
