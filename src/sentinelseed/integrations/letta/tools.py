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

from sentinelseed.integrations._base import LayeredValidator, ValidationConfig

# Memory integrity checking using core module
try:
    from sentinelseed.memory import (
        MemoryIntegrityChecker,
        MemoryEntry,
        MemorySource,
        SignedMemoryEntry,
        SafeMemoryStore,
        MemoryValidationResult,
    )
    HAS_MEMORY = True
except ImportError:
    HAS_MEMORY = False
    MemoryIntegrityChecker = None
    MemoryEntry = None
    MemorySource = None
    SignedMemoryEntry = None
    SafeMemoryStore = None
    MemoryValidationResult = None

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

                # LayeredValidator returns ValidationResult with is_safe attribute
                if hasattr(result, "is_safe"):
                    if result.is_safe:
                        return f"SAFE: Validation passed (context={context}, gates={check_gates})"
                    else:
                        violations = getattr(result, "violations", [])
                        failed = ", ".join(violations) if violations else "unknown"
                        return f"UNSAFE: {failed}"
                else:
                    return "WARNING: Validator returned unexpected result type"

        except (ValueError, TypeError, RuntimeError, AttributeError) as e:
            _logger.warning(f"Safety check error: {type(e).__name__}")
            return f"ERROR: Validation failed"

        return "WARNING: Validation completed but no result returned"


@dataclass
class MemoryGuardTool:
    """
    Memory integrity verification tool for Letta agents.

    Uses HMAC-SHA256 via the core MemoryIntegrityChecker to verify
    memory blocks haven't been tampered with.

    The tool provides two main operations:
    1. Register a memory block and get its HMAC hash
    2. Verify a memory block against an expected hash

    Usage by agents:
        # Register memory and get hash
        result = verify_memory_integrity(
            memory_label="human",
            content="User information here"
        )
        # Returns: "HASH: abc123..."

        # Later, verify memory hasn't changed
        result = verify_memory_integrity(
            memory_label="human",
            expected_hash="abc123..."
        )
        # Returns: "VERIFIED" or "TAMPERED"
    """

    name: str = "verify_memory_integrity"
    description: str = "Verify memory block integrity with HMAC"
    source_code: str = field(default=MEMORY_GUARD_TOOL_SOURCE, repr=False)
    requires_approval: bool = False
    tool_id: Optional[str] = None

    def __post_init__(self):
        """Initialize runtime components."""
        self._secret: Optional[str] = None
        self._validate_content: bool = True
        self._checker: Optional["MemoryIntegrityChecker"] = None
        self._store: Optional["SafeMemoryStore"] = None
        # Map memory_label -> entry_id for quick lookup
        self._label_to_entry: Dict[str, str] = {}

    def initialize(self, secret: str, validate_content: bool = True) -> None:
        """
        Initialize the memory integrity checker with a secret key.

        Args:
            secret: Secret key for HMAC verification
            validate_content: Enable content validation before signing (v2.0).
                When True, memory content is checked for injection patterns
                before HMAC signing. This provides defense-in-depth against
                memory injection attacks. Default: True (recommended).

        Raises:
            ValueError: If secret is None or empty
            ImportError: If sentinelseed.memory module is not available

        Note:
            Content validation (v2.0) detects injection attacks BEFORE signing,
            while HMAC verification detects tampering AFTER signing. Together
            they provide comprehensive memory protection.
        """
        if secret is None:
            raise ValueError("secret cannot be None")
        if not isinstance(secret, str):
            raise ValueError(f"secret must be a string, got {type(secret).__name__}")
        if not secret.strip():
            raise ValueError("secret cannot be empty")

        if not HAS_MEMORY:
            raise ImportError(
                "sentinelseed.memory module is not available. "
                "Install with: pip install sentinelseed"
            )

        self._secret = secret
        self._validate_content = validate_content
        self._checker = MemoryIntegrityChecker(
            secret_key=secret,
            strict_mode=False,
            validate_content=validate_content,
        )
        self._store = self._checker.create_safe_memory_store()
        _logger.debug(
            "Memory integrity checker initialized (content_validation=%s)",
            validate_content,
        )

    def register_memory(
        self,
        label: str,
        content: str,
        source: str = "agent_internal",
    ) -> str:
        """
        Register a memory block and return its HMAC hash.

        Args:
            label: Memory block label (e.g., "human", "persona", "system")
            content: Content of the memory block
            source: Source classification (user_direct, agent_internal, etc.)

        Returns:
            The HMAC hash of the registered memory

        Raises:
            ValueError: If checker is not initialized
        """
        if self._checker is None or self._store is None:
            raise ValueError("Memory checker not initialized. Call initialize() first.")

        # Map source string to MemorySource enum
        source_enum = MemorySource.AGENT_INTERNAL
        try:
            source_enum = MemorySource(source)
        except ValueError:
            source_enum = MemorySource.UNKNOWN

        # Add to store (automatically signed)
        signed_entry = self._store.add(
            content=content,
            source=source_enum,
            metadata={"label": label},
        )

        # Track label -> entry_id mapping
        self._label_to_entry[label] = signed_entry.id

        return signed_entry.hmac_signature

    def run(
        self,
        memory_label: str,
        content: Optional[str] = None,
        expected_hash: Optional[str] = None,
    ) -> str:
        """
        Execute memory integrity check.

        Args:
            memory_label: Label of memory block to verify
            content: Content to register (if not already registered)
            expected_hash: Expected HMAC hash for verification

        Returns:
            str: Result in one of these formats:
                - "HASH: <hash>" - When registering or getting current hash
                - "VERIFIED: Memory block is intact" - When verification succeeds
                - "TAMPERED: Memory block has been modified" - When verification fails
                - "ERROR: <message>" - On error

        Example:
            # Register memory
            result = tool.run(memory_label="human", content="User info")
            # Returns: "HASH: abc123..."

            # Verify memory
            result = tool.run(memory_label="human", expected_hash="abc123...")
            # Returns: "VERIFIED: Memory block is intact"
        """
        # Input validation
        if memory_label is None:
            return "ERROR: memory_label cannot be None"

        if not isinstance(memory_label, str):
            return f"ERROR: memory_label must be a string, got {type(memory_label).__name__}"

        if not memory_label.strip():
            return "ERROR: memory_label cannot be empty"

        if self._checker is None or self._store is None:
            return "ERROR: Memory checker not initialized. Call initialize() first."

        try:
            # Case 1: Register new memory with content
            if content is not None and expected_hash is None:
                hmac_hash = self.register_memory(memory_label, content)
                return f"HASH: {hmac_hash}"

            # Case 2: Get existing hash (no content, no expected_hash)
            if content is None and expected_hash is None:
                if memory_label not in self._label_to_entry:
                    return f"ERROR: Memory block '{memory_label}' not registered. Provide content to register."
                entry_id = self._label_to_entry[memory_label]
                # Note: Direct access to _entries is intentional here.
                # We need the raw hash without re-verification (which get() does).
                # The hash is used for later verification, not for content retrieval.
                entry = self._store._entries.get(entry_id)
                if entry is None:
                    return f"ERROR: Memory block '{memory_label}' entry not found"
                return f"HASH: {entry.hmac_signature}"

            # Case 3: Verify against expected hash
            if expected_hash is not None:
                if memory_label not in self._label_to_entry:
                    return f"ERROR: Memory block '{memory_label}' not registered"

                entry_id = self._label_to_entry[memory_label]
                # Note: Direct access to _entries is intentional (see Case 2 comment)
                entry = self._store._entries.get(entry_id)
                if entry is None:
                    return f"ERROR: Memory block '{memory_label}' entry not found"

                # If new content provided, verify that content's hash matches expected
                if content is not None:
                    # Re-register to get new hash and compare
                    new_hash = self.register_memory(memory_label, content)
                    if new_hash == expected_hash:
                        return "VERIFIED: Memory block is intact"
                    else:
                        return "TAMPERED: Memory block has been modified"
                else:
                    # Compare stored hash with expected
                    if entry.hmac_signature == expected_hash:
                        return "VERIFIED: Memory block is intact"
                    else:
                        return "TAMPERED: Memory block hash mismatch"

        except (ValueError, TypeError, RuntimeError) as e:
            _logger.warning(f"Memory integrity check error: {type(e).__name__}: {e}")
            return f"ERROR: {str(e)}"

        return "ERROR: Unexpected state in memory verification"

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about memory integrity operations.

        Returns:
            Dict with stats including:
                - enabled: Whether memory checking is enabled
                - content_validation: Whether content validation is enabled (v2.0)
                - registered_blocks: Number of registered memory blocks
                - checker_stats: Stats from underlying MemoryIntegrityChecker
        """
        if self._checker is None:
            return {"enabled": False, "content_validation": False}

        return {
            "enabled": True,
            "content_validation": self._validate_content,
            "registered_blocks": len(self._label_to_entry),
            "labels": list(self._label_to_entry.keys()),
            "checker_stats": self._checker.get_validation_stats(),
        }

    def clear(self) -> None:
        """Clear all registered memory blocks."""
        if self._store is not None:
            self._store.clear()
        self._label_to_entry.clear()
        _logger.debug("Memory store cleared")


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
    name: str = "sentinel_safety_check",
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
        name: Name for the tool (default: "sentinel_safety_check")

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
        name=name,
        requires_approval=require_approval,
    )
    tool._api_key = api_key
    tool._provider = provider

    # Validate provider
    if provider not in VALID_PROVIDERS:
        raise ValueError(f"Invalid provider '{provider}'. Must be one of: {VALID_PROVIDERS}")

    # Initialize LayeredValidator
    try:
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=bool(api_key),
            semantic_provider=provider,
            semantic_model=model,
            semantic_api_key=api_key,
        )
        tool._validator = LayeredValidator(config=config)
    except ImportError:
        _logger.warning("LayeredValidator not available")
        tool._validator = None
    except (ValueError, TypeError, RuntimeError, AttributeError) as e:
        _logger.warning(f"Error creating LayeredValidator: {type(e).__name__}")
        tool._validator = None

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

    except (ValueError, TypeError, AttributeError, RuntimeError) as e:
        _logger.warning(f"Could not register tool with Letta: {type(e).__name__}")
        # Tool can still be used with source_code

    return tool


def create_memory_guard_tool(
    client: Any,
    secret: str,
    require_approval: bool = False,
    validate_content: bool = True,
) -> MemoryGuardTool:
    """
    Create and register a memory integrity tool with a Letta client.

    Uses the core MemoryIntegrityChecker for HMAC-based verification
    of memory blocks. The tool can register memory content and verify
    it hasn't been tampered with.

    Args:
        client: Letta client instance
        secret: Secret key for HMAC verification
        require_approval: Whether tool calls require human approval
        validate_content: Enable content validation before signing (v2.0).
            When True, memory content is checked for injection patterns
            before HMAC signing. This provides defense-in-depth against
            memory injection attacks. Default: True (recommended).

    Returns:
        MemoryGuardTool with tool_id set and checker initialized

    Raises:
        ValueError: If secret is None or empty

    Example:
        client = Letta(api_key="...")
        guard = create_memory_guard_tool(client, secret="my-secret")

        # Register memory
        result = guard.run(memory_label="human", content="User info")
        hash_value = result.split(": ")[1]

        # Later, verify
        result = guard.run(memory_label="human", expected_hash=hash_value)
        # "VERIFIED: Memory block is intact"

    Example (with content validation disabled - not recommended):
        guard = create_memory_guard_tool(
            client,
            secret="my-secret",
            validate_content=False,  # Only HMAC, no injection detection
        )
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

    # Initialize the memory integrity checker with content validation setting
    try:
        tool.initialize(secret, validate_content=validate_content)
        _logger.info(
            "Memory guard tool initialized (content_validation=%s)",
            validate_content,
        )
    except ImportError as e:
        _logger.warning(f"Could not initialize memory checker: {e}")
        # Tool will return error messages when used
    except ValueError as e:
        _logger.warning(f"Invalid secret for memory checker: {e}")

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

    except (ValueError, TypeError, AttributeError, RuntimeError) as e:
        _logger.warning(f"Could not register tool with Letta: {type(e).__name__}")

    return tool
