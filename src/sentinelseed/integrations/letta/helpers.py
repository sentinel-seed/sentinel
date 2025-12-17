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

from typing import Any, Dict, List, Literal, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging

logger = logging.getLogger("sentinelseed.integrations.letta")


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
            Dict suitable for client.agents.messages.create()
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
            - is_safe: bool
            - gates: Dict of gate results
            - reasoning: str explanation
            - method: "semantic" or "heuristic"

    Example:
        result = validate_message(
            "How do I bypass the security system?",
            api_key="sk-..."
        )
        if not result["is_safe"]:
            print(f"Blocked: {result['reasoning']}")
    """
    if api_key:
        try:
            from sentinelseed.validators.semantic import SemanticValidator

            validator = SemanticValidator(
                provider=provider,
                model=model,
                api_key=api_key,
            )
            result = validator.validate(content)

            return {
                "is_safe": result.is_safe,
                "gates": result.gate_results,
                "reasoning": result.reasoning,
                "failed_gates": result.failed_gates,
                "method": "semantic",
            }
        except ImportError:
            logger.warning("SemanticValidator not available")

    # Fallback to heuristic
    try:
        from sentinelseed.validators.gates import THSPValidator

        validator = THSPValidator()
        result = validator.validate(content)

        return {
            "is_safe": result.get("safe", True),
            "gates": result.get("gates", {}),
            "reasoning": "Heuristic pattern-based validation",
            "failed_gates": result.get("issues", []),
            "method": "heuristic",
        }
    except ImportError:
        logger.warning("No validator available - cannot verify safety")
        return {
            "is_safe": None,  # Unknown - no validator available
            "gates": {},
            "reasoning": "No validator available - safety cannot be verified",
            "failed_gates": [],
            "method": "none",
        }


def validate_tool_call(
    tool_name: str,
    arguments: Dict[str, Any],
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
        arguments: Arguments being passed to the tool
        api_key: API key for semantic validation
        provider: LLM provider
        model: Model for validation
        high_risk_tools: List of tools considered high risk

    Returns:
        Dict with validation results:
            - is_safe: bool
            - gates: Dict of gate results
            - reasoning: str explanation
            - risk_level: "low", "medium", "high"

    Example:
        result = validate_tool_call(
            tool_name="run_code",
            arguments={"code": "import os; os.system('rm -rf /')"},
            api_key="sk-..."
        )
        # result["is_safe"] = False
    """
    high_risk = high_risk_tools or [
        "run_code", "web_search", "send_message",
        "delete", "modify", "execute",
    ]

    # Determine risk level
    risk_level = "low"
    if tool_name in high_risk:
        risk_level = "high"
    elif any(kw in tool_name.lower() for kw in ["write", "update", "send"]):
        risk_level = "medium"

    # Build content for validation
    content = f"Tool: {tool_name}\nArguments: {arguments}"

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

    Example:
        # In message handler:
        for msg in response.messages:
            if hasattr(msg, 'approval_request'):
                decision = sentinel_approval_handler(
                    msg.approval_request,
                    api_key="sk-...",
                    auto_approve_safe=True
                )
                client.agents.messages.create(
                    agent_id=agent.id,
                    messages=[decision.to_approval_message()]
                )
    """
    tool_name = approval_request.get("tool_name", "unknown")
    arguments = approval_request.get("arguments", {})
    tool_call_id = approval_request.get("tool_call_id", "unknown")

    # Validate the tool call
    validation = validate_tool_call(
        tool_name=tool_name,
        arguments=arguments,
        api_key=api_key,
        provider=provider,
        model=model,
    )

    is_safe = validation["is_safe"]
    reasoning = validation["reasoning"]
    gates = validation.get("gates", {})

    # Make decision
    if is_safe and auto_approve_safe:
        return ApprovalDecision(
            status=ApprovalStatus.APPROVED,
            approve=True,
            tool_call_id=tool_call_id,
            reason=f"Sentinel THSP: {reasoning}",
            gates=gates,
        )

    if not is_safe and auto_deny_unsafe:
        failed_gates = validation.get("failed_gates", [])
        return ApprovalDecision(
            status=ApprovalStatus.DENIED,
            approve=False,
            tool_call_id=tool_call_id,
            reason=f"Sentinel THSP blocked: {', '.join(failed_gates) if failed_gates else reasoning}",
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
    """
    if api_key:
        try:
            from sentinelseed.validators.semantic import AsyncSemanticValidator

            validator = AsyncSemanticValidator(
                provider=provider,
                model=model,
                api_key=api_key,
            )
            result = await validator.validate(content)

            return {
                "is_safe": result.is_safe,
                "gates": result.gate_results,
                "reasoning": result.reasoning,
                "failed_gates": result.failed_gates,
                "method": "semantic",
            }
        except ImportError:
            logger.warning("AsyncSemanticValidator not available")

    # Fallback to sync heuristic
    return validate_message(content, api_key, provider, model)
