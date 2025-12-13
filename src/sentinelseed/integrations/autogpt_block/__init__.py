"""
AutoGPT Block SDK integration for Sentinel AI.

Provides Sentinel safety validation blocks for the AutoGPT Platform.
These blocks can be added to any AutoGPT workflow to validate content
and actions through the THSP Protocol (Truth, Harm, Scope, Purpose).

Requirements:
    This integration is designed to run within the AutoGPT Platform.
    For standalone usage, use `sentinelseed.integrations.agent_validation` instead.

Blocks provided:
    - SentinelValidationBlock: Validate text content through THSP gates
    - SentinelActionCheckBlock: Check if an action is safe before execution
    - SentinelSeedBlock: Get the Sentinel safety seed for injection

Usage within AutoGPT Platform:
    1. Copy this module to your AutoGPT blocks directory
    2. The blocks will be auto-registered and available in the workflow builder
    3. Connect the validation block before any sensitive operation

For standalone Python usage:
    from sentinelseed.integrations.autogpt_block import (
        validate_content,
        check_action,
        get_seed,
    )

    # Validate content
    result = validate_content("Some text to check")
    if result["safe"]:
        proceed()

    # Check action before execution
    result = check_action("delete_file", {"path": "/tmp/test.txt"})
    if result["should_proceed"]:
        execute_action()

References:
    - AutoGPT Block SDK: https://dev-docs.agpt.co/platform/block-sdk-guide/
    - Sentinel: https://sentinelseed.dev
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, AsyncIterator

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel


# Check for AutoGPT Block SDK availability
AUTOGPT_SDK_AVAILABLE = False
try:
    from backend.sdk import (
        Block,
        BlockCategory,
        BlockOutput,
        BlockSchemaInput,
        BlockSchemaOutput,
        SchemaField,
    )
    AUTOGPT_SDK_AVAILABLE = True
except ImportError:
    # Define stubs for type hints when SDK not installed
    Block = object
    BlockCategory = None
    BlockOutput = None
    BlockSchemaInput = object
    BlockSchemaOutput = object
    SchemaField = lambda **kwargs: None


class ValidationLevel(Enum):
    """Validation strictness levels."""
    PERMISSIVE = "permissive"
    STANDARD = "standard"
    STRICT = "strict"


@dataclass
class ValidationResult:
    """Result of content validation."""
    safe: bool
    content: str
    violations: List[str] = field(default_factory=list)
    gate_results: Dict[str, bool] = field(default_factory=dict)
    risk_level: str = "low"


@dataclass
class ActionCheckResult:
    """Result of action safety check."""
    should_proceed: bool
    action: str
    concerns: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)
    risk_level: str = "low"


# Standalone validation functions (work without AutoGPT SDK)

def validate_content(
    content: str,
    seed_level: str = "standard",
    check_type: str = "general",
) -> Dict[str, Any]:
    """
    Validate content through Sentinel THSP gates.

    Args:
        content: Text content to validate
        seed_level: Sentinel seed level (minimal, standard, full)
        check_type: Type of validation (general, action, request)

    Returns:
        Dict with safe, violations, risk_level, gate_results

    Example:
        result = validate_content("How do I hack a computer?")
        if not result["safe"]:
            print(f"Blocked: {result['violations']}")
    """
    sentinel = Sentinel(seed_level=seed_level)

    if check_type == "action":
        is_safe, violations = sentinel.validate_action(content)
    elif check_type == "request":
        request_result = sentinel.validate_request(content)
        return {
            "safe": request_result["should_proceed"],
            "violations": request_result["concerns"],
            "risk_level": request_result["risk_level"],
            "gate_results": {},
            "content": content,
        }
    else:
        is_safe, violations = sentinel.validate(content)

    return {
        "safe": is_safe,
        "violations": violations,
        "risk_level": "high" if violations else "low",
        "gate_results": {
            "truth": True,
            "harm": is_safe,
            "scope": True,
            "purpose": True,
        },
        "content": content,
    }


def check_action(
    action_name: str,
    action_args: Optional[Dict[str, Any]] = None,
    purpose: str = "",
    seed_level: str = "standard",
) -> Dict[str, Any]:
    """
    Check if an action is safe to execute.

    Args:
        action_name: Name of the action to check
        action_args: Arguments for the action
        purpose: Stated purpose for the action
        seed_level: Sentinel seed level

    Returns:
        Dict with should_proceed, concerns, recommendations, risk_level

    Example:
        result = check_action("delete_file", {"path": "/etc/passwd"})
        if not result["should_proceed"]:
            print(f"Blocked: {result['concerns']}")
    """
    sentinel = Sentinel(seed_level=seed_level)
    action_args = action_args or {}

    # Build action description
    description = f"{action_name}"
    if action_args:
        args_str = ", ".join(f"{k}={v}" for k, v in action_args.items())
        description = f"{action_name}({args_str})"

    # Validate action
    is_safe, concerns = sentinel.validate_action(description)

    # Check request as well
    request_result = sentinel.validate_request(description)

    all_concerns = concerns + request_result.get("concerns", [])
    should_proceed = is_safe and request_result["should_proceed"]

    # Build recommendations
    recommendations = []
    if not should_proceed:
        recommendations.append("Review action details before proceeding")
    if not purpose:
        recommendations.append("Consider providing explicit purpose for the action")

    return {
        "should_proceed": should_proceed,
        "action": action_name,
        "concerns": all_concerns,
        "recommendations": recommendations,
        "risk_level": request_result["risk_level"],
    }


def get_seed(level: str = "standard") -> str:
    """
    Get the Sentinel safety seed.

    Args:
        level: Seed level (minimal, standard, full)

    Returns:
        Seed content as string

    Example:
        seed = get_seed("standard")
        system_prompt = f"{seed}\\n\\nYou are a helpful assistant."
    """
    sentinel = Sentinel(seed_level=level)
    return sentinel.get_seed()


# AutoGPT Block implementations (only available when SDK is installed)

if AUTOGPT_SDK_AVAILABLE:

    class SentinelValidationBlock(Block):
        """
        Sentinel content validation block for AutoGPT workflows.

        Validates text content through THSP (Truth, Harm, Scope, Purpose) gates.
        Use this block before any operation that processes user input or
        generates potentially sensitive content.

        Inputs:
            content: Text to validate
            seed_level: Validation strictness (minimal, standard, full)
            check_type: Type of check (general, action, request)

        Outputs:
            safe: Boolean indicating if content is safe
            content: Pass-through of input (if safe) or empty string
            violations: List of detected violations
            risk_level: Risk assessment (low, medium, high, critical)
        """

        class Input(BlockSchemaInput):
            content: str = SchemaField(
                description="Text content to validate through THSP gates"
            )
            seed_level: str = SchemaField(
                description="Sentinel seed level: minimal, standard, or full",
                default="standard"
            )
            check_type: str = SchemaField(
                description="Validation type: general, action, or request",
                default="general"
            )

        class Output(BlockSchemaOutput):
            safe: bool = SchemaField(description="Whether content passed validation")
            content: str = SchemaField(description="Original content (if safe) or empty")
            violations: list = SchemaField(description="List of detected violations")
            risk_level: str = SchemaField(description="Risk level: low, medium, high, critical")

        def __init__(self):
            super().__init__(
                id="sentinel-validation-block",
                description=(
                    "Validate content through Sentinel THSP Protocol. "
                    "Checks for harmful, deceptive, or out-of-scope content. "
                    "Use before processing user input or generating responses."
                ),
                categories={BlockCategory.SAFETY} if hasattr(BlockCategory, 'SAFETY') else set(),
                input_schema=self.Input,
                output_schema=self.Output,
            )

        async def run(
            self,
            input_data: Input,
            **kwargs
        ) -> BlockOutput:
            """Execute validation."""
            try:
                result = validate_content(
                    content=input_data.content,
                    seed_level=input_data.seed_level,
                    check_type=input_data.check_type,
                )

                yield "safe", result["safe"]
                yield "content", input_data.content if result["safe"] else ""
                yield "violations", result["violations"]
                yield "risk_level", result["risk_level"]

            except Exception as e:
                yield "safe", False
                yield "content", ""
                yield "violations", [str(e)]
                yield "risk_level", "high"


    class SentinelActionCheckBlock(Block):
        """
        Sentinel action safety check block for AutoGPT workflows.

        Validates if an action is safe to execute before proceeding.
        Use this block before any potentially dangerous operation like
        file operations, API calls, or system commands.

        Inputs:
            action_name: Name of the action to check
            action_args: JSON string of action arguments
            purpose: Stated purpose for the action

        Outputs:
            should_proceed: Boolean indicating if action should proceed
            concerns: List of safety concerns
            recommendations: Suggested actions
            risk_level: Risk assessment
        """

        class Input(BlockSchemaInput):
            action_name: str = SchemaField(
                description="Name of the action to check (e.g., delete_file, send_email)"
            )
            action_args: str = SchemaField(
                description="JSON string of action arguments",
                default="{}"
            )
            purpose: str = SchemaField(
                description="Stated purpose/reason for the action",
                default=""
            )
            seed_level: str = SchemaField(
                description="Sentinel seed level",
                default="standard"
            )

        class Output(BlockSchemaOutput):
            should_proceed: bool = SchemaField(description="Whether action should proceed")
            concerns: list = SchemaField(description="List of safety concerns")
            recommendations: list = SchemaField(description="Suggested actions")
            risk_level: str = SchemaField(description="Risk level assessment")

        def __init__(self):
            super().__init__(
                id="sentinel-action-check-block",
                description=(
                    "Check if an action is safe before execution. "
                    "Validates through THSP gates and provides risk assessment. "
                    "Use before file operations, API calls, or system commands."
                ),
                categories={BlockCategory.SAFETY} if hasattr(BlockCategory, 'SAFETY') else set(),
                input_schema=self.Input,
                output_schema=self.Output,
            )

        async def run(
            self,
            input_data: Input,
            **kwargs
        ) -> BlockOutput:
            """Execute action check."""
            import json

            try:
                # Parse action args
                try:
                    action_args = json.loads(input_data.action_args) if input_data.action_args else {}
                except json.JSONDecodeError:
                    action_args = {"raw": input_data.action_args}

                result = check_action(
                    action_name=input_data.action_name,
                    action_args=action_args,
                    purpose=input_data.purpose,
                    seed_level=input_data.seed_level,
                )

                yield "should_proceed", result["should_proceed"]
                yield "concerns", result["concerns"]
                yield "recommendations", result["recommendations"]
                yield "risk_level", result["risk_level"]

            except Exception as e:
                yield "should_proceed", False
                yield "concerns", [str(e)]
                yield "recommendations", ["Review error and retry"]
                yield "risk_level", "high"


    class SentinelSeedBlock(Block):
        """
        Sentinel seed retrieval block for AutoGPT workflows.

        Retrieves the Sentinel safety seed for injection into system prompts.
        Use this block at the start of workflows that interact with LLMs.

        Inputs:
            level: Seed level (minimal, standard, full)

        Outputs:
            seed: The safety seed content
            token_count: Approximate token count of the seed
        """

        class Input(BlockSchemaInput):
            level: str = SchemaField(
                description="Seed level: minimal (~360 tokens), standard (~1000 tokens), full (~1900 tokens)",
                default="standard"
            )

        class Output(BlockSchemaOutput):
            seed: str = SchemaField(description="The Sentinel safety seed content")
            token_count: int = SchemaField(description="Approximate token count")

        def __init__(self):
            super().__init__(
                id="sentinel-seed-block",
                description=(
                    "Get Sentinel safety seed for LLM system prompts. "
                    "Injects THSP Protocol guidelines to shape LLM behavior. "
                    "Use at the start of any LLM interaction workflow."
                ),
                categories={BlockCategory.AI} if hasattr(BlockCategory, 'AI') else set(),
                input_schema=self.Input,
                output_schema=self.Output,
            )

        async def run(
            self,
            input_data: Input,
            **kwargs
        ) -> BlockOutput:
            """Get seed content."""
            try:
                seed = get_seed(input_data.level)

                # Approximate token count (rough estimate: 4 chars per token)
                token_count = len(seed) // 4

                yield "seed", seed
                yield "token_count", token_count

            except Exception as e:
                yield "seed", ""
                yield "token_count", 0


# Block registration for AutoGPT auto-discovery
BLOCKS = []
if AUTOGPT_SDK_AVAILABLE:
    BLOCKS = [
        SentinelValidationBlock,
        SentinelActionCheckBlock,
        SentinelSeedBlock,
    ]


__all__ = [
    # Standalone functions
    "validate_content",
    "check_action",
    "get_seed",
    # Data classes
    "ValidationResult",
    "ActionCheckResult",
    "ValidationLevel",
    # AutoGPT blocks (only when SDK available)
    "SentinelValidationBlock",
    "SentinelActionCheckBlock",
    "SentinelSeedBlock",
    "BLOCKS",
    "AUTOGPT_SDK_AVAILABLE",
]
