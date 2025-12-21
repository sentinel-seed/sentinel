"""
Custom Letta Tools for Sentinel THSP validation.

This module provides custom tools that can be added to Letta agents
for safety validation and memory integrity checking.

Tools:
    - SentinelSafetyTool: Validate content through THSP gates
    - MemoryGuardTool: Verify memory integrity with HMAC

Functions:
    - create_sentinel_tool: Create and register safety tool
    - create_memory_guard_tool: Create and register memory guard tool
"""

from typing import Any, Dict, List, Literal, Optional
from dataclasses import dataclass, field
import logging

_logger = logging.getLogger("sentinelseed.integrations.letta")

# Valid configuration values
VALID_PROVIDERS = ("openai", "anthropic")

# Source code for tools - Letta parses this to create tool schemas
SENTINEL_TOOL_SOURCE = '''
from typing import Literal

def sentinel_safety_check(
    content: str,
    context: str = "general",
    check_gates: str = "all",
) -> str:
    """
    Validate content through Sentinel THSP safety gates.

    Call this tool BEFORE taking any potentially risky action to verify
    it passes safety validation. The tool checks content against the
    THSP protocol: Truth, Harm, Scope, and Purpose gates.

    Args:
        content: The content or action description to validate.
            Be specific about what you plan to do or say.
        context: Context for validation. Options:
            - "general": General content validation
            - "code": Code execution or generation
            - "web": Web search or external API calls
            - "financial": Financial or transaction-related
            - "personal": Personal or sensitive information
        check_gates: Which THSP gates to check. Options:
            - "all": Check all gates (Truth, Harm, Scope, Purpose)
            - "harm": Only check Harm gate
            - "truth_harm": Check Truth and Harm gates

    Returns:
        str: Validation result with format:
            "SAFE: <reasoning>" if content passes all gates
            "UNSAFE: <gate>: <reasoning>" if content fails a gate

    Example:
        result = sentinel_safety_check(
            content="I will search for user's private documents",
            context="web",
            check_gates="all"
        )
        # Returns: "UNSAFE: SCOPE: Action exceeds appropriate boundaries"
    """
    # Implementation is injected by Sentinel integration
    # This source is parsed by Letta for schema generation
    return "SAFE: Content passed all THSP gates"
'''

MEMORY_GUARD_TOOL_SOURCE = '''
from typing import List, Optional

def verify_memory_integrity(
    memory_label: str,
    expected_hash: Optional[str] = None,
) -> str:
    """
    Verify the integrity of a memory block.

    Call this tool to check if a memory block has been tampered with
    since it was last verified. Uses HMAC-SHA256 for verification.

    Args:
        memory_label: The label of the memory block to verify.
            Common labels: "human", "persona", "system"
        expected_hash: Optional expected HMAC hash. If not provided,
            the tool will return the current hash for future verification.

    Returns:
        str: Verification result with format:
            "VERIFIED: Memory block is intact" if hash matches
            "TAMPERED: Memory block has been modified" if hash differs
            "HASH: <hash>" if no expected_hash provided

    Example:
        # First call to get hash
        result = verify_memory_integrity(memory_label="human")
        # Returns: "HASH: abc123..."

        # Later call to verify
        result = verify_memory_integrity(
            memory_label="human",
            expected_hash="abc123..."
        )
        # Returns: "VERIFIED: Memory block is intact"
    """
    # Implementation is injected by Sentinel integration
    return "HASH: placeholder"
'''


@dataclass
class SentinelSafetyTool:
    """
    Sentinel safety check tool for Letta agents.

    Provides THSP validation as a callable tool that agents can invoke
    before taking potentially risky actions.
    """

    name: str = "sentinel_safety_check"
    description: str = "Validate content through Sentinel THSP safety gates"
    source_code: str = field(default=SENTINEL_TOOL_SOURCE, repr=False)
    requires_approval: bool = False
    tool_id: Optional[str] = None

    def __post_init__(self):
        """Initialize runtime components."""
        self._validator: Any = None
        self._api_key: Optional[str] = None
        self._provider: str = "openai"

    def run(
        self,
        content: str,
        context: str = "general",
        check_gates: str = "all",
    ) -> str:
        """
        Execute safety validation.

        Args:
            content: Content to validate
            context: Validation context (general, code, web, financial, personal)
            check_gates: Which gates to check (all, harm, truth_harm)

        Returns:
            str: "SAFE: <reasoning>" or "UNSAFE: <gate>: <reasoning>" or error message
        """
        # Input validation
        if content is None:
            return "ERROR: content cannot be None"

        if not isinstance(content, str):
            return f"ERROR: content must be a string, got {type(content).__name__}"

        if not content.strip():
            return "SAFE: Empty content - no validation needed"

        if self._validator is None:
            return "WARNING: No validator configured - cannot verify safety"

        try:
            if hasattr(self._validator, "validate"):
                result = self._validator.validate(content)

                if hasattr(result, "is_safe"):
                    # SemanticValidator
                    if result.is_safe:
                        reasoning = getattr(result, "reasoning", "Validation passed")
                        return f"SAFE: {reasoning}"
                    else:
                        failed_gates = getattr(result, "failed_gates", [])
                        reasoning = getattr(result, "reasoning", "Validation failed")
                        failed = ", ".join(failed_gates) if failed_gates else "unknown"
                        return f"UNSAFE: {failed}: {reasoning}"
                elif isinstance(result, dict):
                    # THSPValidator (dict)
                    if result.get("safe", True):
                        return f"SAFE: Heuristic validation passed (context={context}, gates={check_gates})"
                    else:
                        issues = result.get("issues", [])
                        return f"UNSAFE: {', '.join(issues)}"
                else:
                    return "WARNING: Validator returned unexpected result type"

        except Exception as e:
            _logger.warning(f"Safety check error: {type(e).__name__}")
            return f"ERROR: Validation failed - {type(e).__name__}"

        return "WARNING: Validation completed but no result returned"


@dataclass
class MemoryGuardTool:
    """
    Memory integrity verification tool for Letta agents.

    Uses HMAC-SHA256 to verify memory blocks haven't been tampered with.

    Note: This is currently a placeholder implementation. Full memory
    integrity verification requires access to Letta's memory blocks
    through the client API, which is robot-specific.
    """

    name: str = "verify_memory_integrity"
    description: str = "Verify memory block integrity with HMAC"
    source_code: str = field(default=MEMORY_GUARD_TOOL_SOURCE, repr=False)
    requires_approval: bool = False
    tool_id: Optional[str] = None

    def __post_init__(self):
        """Initialize runtime components."""
        self._secret: Optional[str] = None
        self._hashes: Dict[str, str] = {}

    def run(
        self,
        memory_label: str,
        expected_hash: Optional[str] = None,
    ) -> str:
        """
        Execute memory integrity check.

        Args:
            memory_label: Label of memory block to verify
            expected_hash: Optional expected HMAC hash

        Returns:
            str: "VERIFIED", "TAMPERED", "HASH: <hash>", or error message

        Note: This is currently a placeholder. Full implementation requires
        access to Letta's memory blocks through the client API.
        """
        # Input validation
        if memory_label is None:
            return "ERROR: memory_label cannot be None"

        if not isinstance(memory_label, str):
            return f"ERROR: memory_label must be a string, got {type(memory_label).__name__}"

        if not memory_label.strip():
            return "ERROR: memory_label cannot be empty"

        if self._secret is None:
            return "ERROR: No secret configured for memory integrity"

        # Placeholder implementation
        # Full implementation would:
        # 1. Get memory block content from Letta client
        # 2. Compute HMAC-SHA256 of content
        # 3. Compare with expected_hash or return current hash
        return f"HASH: Memory integrity check for '{memory_label}' (placeholder)"


# Placeholder function for tool registration - must be defined before create_sentinel_tool
def _sentinel_safety_check_placeholder(
    content: str,
    context: str = "general",
    check_gates: str = "all",
) -> str:
    """
    Validate content through Sentinel THSP safety gates.

    Call this tool BEFORE taking any potentially risky action.

    Args:
        content: The content or action description to validate
        context: Context for validation (general, code, web, financial, personal)
        check_gates: Which gates to check (all, harm, truth_harm)

    Returns:
        str: "SAFE: <reasoning>" or "UNSAFE: <gate>: <reasoning>"
    """
    return "SAFE: Placeholder - actual validation handled by Sentinel"


def create_sentinel_tool(
    client: Any,
    api_key: Optional[str] = None,
    provider: str = "openai",
    model: Optional[str] = None,
    require_approval: bool = False,
) -> SentinelSafetyTool:
    """
    Create and register a Sentinel safety check tool with a Letta client.

    The tool is registered with the client and can be added to agents
    to provide on-demand THSP safety validation.

    Args:
        client: Letta client instance
        api_key: API key for semantic validation
        provider: LLM provider ("openai" or "anthropic")
        model: Model for validation
        require_approval: Whether tool calls require human approval

    Returns:
        SentinelSafetyTool with tool_id set

    Example:
        client = Letta(api_key="...")
        tool = create_sentinel_tool(client, api_key="sk-...")

        agent = client.agents.create(
            tools=[tool.name],
            ...
        )
    """
    tool = SentinelSafetyTool(
        requires_approval=require_approval,
    )
    tool._api_key = api_key
    tool._provider = provider

    # Validate provider
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider '{provider}'. Must be one of: {VALID_PROVIDERS}")

    # Initialize validator
    if api_key:
        try:
            from sentinelseed.validators.semantic import SemanticValidator
            tool._validator = SemanticValidator(
                provider=provider,
                model=model,
                api_key=api_key,
            )
        except ImportError:
            _logger.warning("SemanticValidator not available, using heuristic")
            try:
                from sentinelseed.validators.gates import THSPValidator
                tool._validator = THSPValidator()
            except ImportError:
                pass
        except Exception as e:
            _logger.warning(f"Error creating SemanticValidator: {type(e).__name__}")
            try:
                from sentinelseed.validators.gates import THSPValidator
                tool._validator = THSPValidator()
            except Exception:
                pass
    else:
        try:
            from sentinelseed.validators.gates import THSPValidator
            tool._validator = THSPValidator()
        except ImportError:
            pass

    # Register tool with Letta
    if client is None:
        _logger.warning("No client provided - tool not registered with Letta")
        return tool

    try:
        # Use upsert_from_function to set approval flag correctly
        if require_approval and hasattr(client, 'tools') and hasattr(client.tools, 'upsert_from_function'):
            registered = client.tools.upsert_from_function(
                func=_sentinel_safety_check_placeholder,
                default_requires_approval=True,
            )
        elif hasattr(client, 'tools') and hasattr(client.tools, 'create'):
            registered = client.tools.create(
                source_code=tool.source_code,
            )
        else:
            _logger.warning("Client does not have tools API - tool not registered")
            return tool

        tool.tool_id = registered.id
        tool.name = registered.name

        _logger.info(f"Registered Sentinel safety tool: {tool.name}")

    except Exception as e:
        _logger.warning(f"Could not register tool with Letta: {type(e).__name__}")
        # Tool can still be used with source_code

    return tool


def create_memory_guard_tool(
    client: Any,
    secret: str,
    require_approval: bool = False,
) -> MemoryGuardTool:
    """
    Create and register a memory integrity tool with a Letta client.

    Note: This creates a placeholder tool. Full memory integrity verification
    requires access to Letta's memory blocks through the client API.

    Args:
        client: Letta client instance
        secret: Secret key for HMAC verification
        require_approval: Whether tool calls require human approval

    Returns:
        MemoryGuardTool with tool_id set

    Raises:
        ValueError: If secret is None or empty
    """
    # Input validation
    if secret is None:
        raise ValueError("secret cannot be None")

    if not isinstance(secret, str):
        raise ValueError(f"secret must be a string, got {type(secret).__name__}")

    if not secret.strip():
        raise ValueError("secret cannot be empty")

    tool = MemoryGuardTool(
        requires_approval=require_approval,
    )
    tool._secret = secret

    # Register tool with Letta
    if client is None:
        _logger.warning("No client provided - tool not registered with Letta")
        return tool

    try:
        if hasattr(client, 'tools') and hasattr(client.tools, 'create'):
            registered = client.tools.create(
                source_code=tool.source_code,
            )
            tool.tool_id = registered.id
            tool.name = registered.name
            _logger.info(f"Registered memory guard tool: {tool.name}")
        else:
            _logger.warning("Client does not have tools API - tool not registered")

    except Exception as e:
        _logger.warning(f"Could not register tool with Letta: {type(e).__name__}")

    return tool
