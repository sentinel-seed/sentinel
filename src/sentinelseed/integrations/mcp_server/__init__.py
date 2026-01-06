"""
MCP Server integration for Sentinel AI.

Provides a Model Context Protocol server that exposes Sentinel safety
validation as tools and resources for LLM applications.

This follows the official MCP Python SDK specification:
https://github.com/modelcontextprotocol/python-sdk

Usage:
    # Option 1: Run as standalone MCP server
    python -m sentinelseed.integrations.mcp_server

    # Option 2: Import and customize
    from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server

    mcp = create_sentinel_mcp_server()
    mcp.run()

    # Option 3: Add Sentinel tools to existing MCP server
    from sentinelseed.integrations.mcp_server import add_sentinel_tools

    mcp = FastMCP("MyServer")
    add_sentinel_tools(mcp)

Tools provided:
    - sentinel_validate: Validate any text through THSP gates
    - sentinel_check_action: Check if an action is safe to execute
    - sentinel_check_request: Validate a user request for safety
    - sentinel_get_seed: Get the Sentinel seed for injection
    - sentinel_batch_validate: Validate multiple items in batch

Resources provided:
    - sentinel://seed/{level}: Get seed content by level
    - sentinel://config: Current Sentinel configuration
"""

from typing import Any, Dict, List, Optional, Union
import asyncio
import logging

__version__ = "2.21.0"

# Public API exports
__all__ = [
    # Version
    "__version__",
    # Configuration
    "MCPConfig",
    "MCP_AVAILABLE",
    # Exceptions
    "TextTooLargeError",
    "MCPClientError",
    "MCPTimeoutError",
    "MCPConnectionError",
    # Server functions
    "create_sentinel_mcp_server",
    "add_sentinel_tools",
    "run_server",
    # Client
    "SentinelMCPClient",
]


# Configuration constants
class MCPConfig:
    """Configuration constants for MCP Server integration."""

    # Text size limits (in bytes)
    MAX_TEXT_SIZE = 50 * 1024  # 50KB default
    MAX_TEXT_SIZE_BATCH = 10 * 1024  # 10KB per item in batch

    # Batch limits
    MAX_BATCH_ITEMS = 1000
    DEFAULT_BATCH_ITEMS = 100

    # Timeout settings (in seconds)
    DEFAULT_TIMEOUT = 30.0
    BATCH_TIMEOUT = 60.0

    # Item preview length for results
    ITEM_PREVIEW_LENGTH = 100


class TextTooLargeError(Exception):
    """Raised when text exceeds maximum allowed size."""

    def __init__(self, size: int, max_size: int):
        self.size = size
        self.max_size = max_size
        super().__init__(
            f"Text size ({size:,} bytes) exceeds maximum allowed ({max_size:,} bytes)"
        )

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validation import (
    LayeredValidator,
    ValidationConfig,
    ValidationResult,
    ValidationLayer,
    RiskLevel,
)

logger = logging.getLogger("sentinelseed.mcp_server")


def _validate_text_size(
    text: str,
    max_size: int = MCPConfig.MAX_TEXT_SIZE,
    context: str = "text",
) -> None:
    """
    Validate that text does not exceed maximum size.

    Args:
        text: Text to validate
        max_size: Maximum allowed size in bytes
        context: Description for error messages

    Raises:
        TextTooLargeError: If text exceeds maximum size
    """
    if not isinstance(text, str):
        return

    size = len(text.encode("utf-8"))
    if size > max_size:
        logger.warning(
            f"Text size validation failed: {context} is {size:,} bytes, "
            f"max allowed is {max_size:,} bytes"
        )
        raise TextTooLargeError(size, max_size)

# Check for MCP SDK availability
MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP, Context
    MCP_AVAILABLE = True
except (ImportError, AttributeError):
    FastMCP = None
    Context = None


def create_sentinel_mcp_server(
    name: str = "sentinel-safety",
    sentinel: Optional[Sentinel] = None,
    seed_level: str = "standard",
) -> Any:
    """
    Create a Sentinel MCP server with safety validation tools.

    Args:
        name: Server name for MCP registration
        sentinel: Sentinel instance (creates default if None)
        seed_level: Default seed level to use

    Returns:
        FastMCP server instance with Sentinel tools

    Raises:
        ImportError: If mcp package is not installed

    Example:
        from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server

        mcp = create_sentinel_mcp_server()
        mcp.run()  # Start the server
    """
    if not MCP_AVAILABLE:
        raise ImportError(
            "mcp package not installed. "
            "Install with: pip install mcp"
        )

    sentinel = sentinel or Sentinel(seed_level=seed_level)
    mcp = FastMCP(name=name)

    # Add Sentinel tools to the server
    add_sentinel_tools(mcp, sentinel)

    return mcp


def add_sentinel_tools(
    mcp: Any,
    sentinel: Optional[Sentinel] = None,
    validator: Optional[LayeredValidator] = None,
) -> None:
    """
    Add Sentinel safety tools to an existing MCP server.

    This allows integration of Sentinel validation into any MCP server.

    Args:
        mcp: FastMCP server instance
        sentinel: Sentinel instance (creates default if None) - used for get_seed
        validator: LayeredValidator instance (creates default if None) - used for validation

    Example:
        from mcp.server.fastmcp import FastMCP
        from sentinelseed.integrations.mcp_server import add_sentinel_tools

        mcp = FastMCP("my-server")
        add_sentinel_tools(mcp)

        @mcp.tool()
        def my_custom_tool():
            pass
    """
    if not MCP_AVAILABLE:
        raise ImportError("mcp package not installed")

    sentinel = sentinel or Sentinel()

    # Create LayeredValidator for validation operations
    if validator is None:
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=False,  # Default to heuristic-only for MCP server
            max_text_size=MCPConfig.MAX_TEXT_SIZE,
        )
        validator = LayeredValidator(config=config)

    # Tool: Validate text through THSP gates
    @mcp.tool()
    def sentinel_validate(
        text: str,
        check_type: str = "general",
    ) -> Dict[str, Any]:
        """
        Validate text through Sentinel THSP (Truth, Harm, Scope, Purpose) gates.

        Use this tool to check if any text content passes safety validation.
        Returns detailed information about which gates passed or failed.

        Args:
            text: The text content to validate (max 50KB)
            check_type: Type of validation - 'general', 'action', or 'request'

        Returns:
            Dict with 'safe', 'violations', 'recommendation' fields
        """
        # Validate text size
        try:
            _validate_text_size(text, context="validation text")
        except TextTooLargeError as e:
            logger.warning(f"sentinel_validate: {e}")
            return {
                "safe": False,
                "violations": [str(e)],
                "recommendation": "Text too large. Reduce size and retry.",
                "error": "text_too_large",
            }

        logger.debug(f"sentinel_validate called: check_type={check_type}, text_len={len(text)}")

        # Use LayeredValidator for validation
        if check_type == "action":
            result = validator.validate_action(text, {}, "")
        elif check_type == "request":
            result = validator.validate_request(text)
        else:
            result = validator.validate(text)

        # Convert risk level to string
        risk_level = result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level)

        logger.debug(f"sentinel_validate result: safe={result.is_safe}, violations={len(result.violations)}")

        if check_type == "request":
            return {
                "safe": result.is_safe,
                "risk_level": risk_level,
                "concerns": result.violations,
                "recommendation": "Safe to proceed" if result.is_safe else f"Blocked: {result.violations}",
            }

        return {
            "safe": result.is_safe,
            "violations": result.violations,
            "recommendation": "Content is safe" if result.is_safe else f"Safety concerns: {result.violations}",
        }

    # Tool: Check if an action is safe
    @mcp.tool()
    def sentinel_check_action(action: str) -> Dict[str, Any]:
        """
        Check if a planned action is safe to execute.

        Use this before executing any potentially risky action to ensure
        it passes THSP safety validation.

        Args:
            action: Description of the action to check (max 50KB)

        Returns:
            Dict with 'safe', 'should_proceed', 'concerns', 'recommendation'
        """
        # Validate text size
        try:
            _validate_text_size(action, context="action description")
        except TextTooLargeError as e:
            logger.warning(f"sentinel_check_action: {e}")
            return {
                "safe": False,
                "should_proceed": False,
                "concerns": [str(e)],
                "risk_level": "critical",
                "recommendation": "Action description too large. Reduce size and retry.",
                "error": "text_too_large",
            }

        logger.debug(f"sentinel_check_action called: action_len={len(action)}")

        # Use LayeredValidator for action validation
        result = validator.validate_action(action, {}, "")

        # Convert risk level to string
        risk_level = result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level)

        # Escalate risk if action is blocked
        if not result.is_safe and risk_level == "low":
            risk_level = "high"

        logger.debug(f"sentinel_check_action result: safe={result.is_safe}, risk={risk_level}")
        return {
            "safe": result.is_safe,
            "should_proceed": result.is_safe,
            "concerns": result.violations,
            "risk_level": risk_level,
            "recommendation": "Action is safe to proceed" if result.is_safe else f"Action blocked: {result.violations}",
        }

    # Tool: Validate a user request
    @mcp.tool()
    def sentinel_check_request(request: str) -> Dict[str, Any]:
        """
        Validate a user request for safety concerns.

        Use this to check incoming user messages for jailbreak attempts,
        harmful requests, or other safety issues.

        Args:
            request: The user's request text (max 50KB)

        Returns:
            Dict with 'should_proceed', 'risk_level', 'concerns'
        """
        # Validate text size
        try:
            _validate_text_size(request, context="user request")
        except TextTooLargeError as e:
            logger.warning(f"sentinel_check_request: {e}")
            return {
                "should_proceed": False,
                "risk_level": "critical",
                "concerns": [str(e)],
                "safe": False,
                "error": "text_too_large",
            }

        logger.debug(f"sentinel_check_request called: request_len={len(request)}")

        # Use LayeredValidator for request validation
        result = validator.validate_request(request)

        # Convert risk level to string
        risk_level = result.risk_level.value if hasattr(result.risk_level, 'value') else str(result.risk_level)

        logger.debug(f"sentinel_check_request result: proceed={result.is_safe}, risk={risk_level}")
        return {
            "should_proceed": result.is_safe,
            "risk_level": risk_level,
            "concerns": result.violations,
            "safe": result.is_safe,
        }

    # Tool: Get Sentinel seed
    @mcp.tool()
    def sentinel_get_seed(level: str = "standard") -> str:
        """
        Get the Sentinel safety seed for injection into system prompts.

        Use this to retrieve the THSP safety guidelines that can be
        injected into an LLM's system prompt.

        Args:
            level: Seed level - 'minimal', 'standard', or 'full'

        Returns:
            The seed content as a string
        """
        logger.debug(f"sentinel_get_seed called: level={level}")

        # Validate level
        valid_levels = ("minimal", "standard", "full")
        if level not in valid_levels:
            logger.warning(f"sentinel_get_seed: invalid level '{level}', using 'standard'")
            level = "standard"

        temp_sentinel = Sentinel(seed_level=level)
        seed = temp_sentinel.get_seed()

        logger.debug(f"sentinel_get_seed result: seed_len={len(seed)}")
        return seed

    # Tool: Batch validate multiple items
    @mcp.tool()
    def sentinel_batch_validate(
        items: List[str],
        check_type: str = "general",
        max_items: int = MCPConfig.DEFAULT_BATCH_ITEMS,
    ) -> Dict[str, Any]:
        """
        Validate multiple text items in batch.

        Efficiently validate a list of items and get aggregated results.

        Args:
            items: List of text items to validate (max 10KB per item)
            check_type: Type of validation - 'general', 'action', or 'request'
            max_items: Maximum items to process (default 100, max 1000)

        Returns:
            Dict with 'total', 'safe_count', 'unsafe_count', 'results'
        """
        logger.debug(f"sentinel_batch_validate called: items={len(items)}, check_type={check_type}")

        # Enforce size limits to prevent memory exhaustion
        max_items = min(max_items, MCPConfig.MAX_BATCH_ITEMS)
        if len(items) > max_items:
            logger.info(f"sentinel_batch_validate: truncating from {len(items)} to {max_items} items")
            items = items[:max_items]
            truncated = True
        else:
            truncated = False

        results = []
        safe_count = 0
        skipped_count = 0

        for idx, item in enumerate(items):
            # Validate individual item size
            try:
                _validate_text_size(
                    item,
                    max_size=MCPConfig.MAX_TEXT_SIZE_BATCH,
                    context=f"batch item {idx}",
                )
            except TextTooLargeError as e:
                results.append({
                    "item": item[:MCPConfig.ITEM_PREVIEW_LENGTH],
                    "safe": False,
                    "error": "text_too_large",
                    "violations": [str(e)],
                })
                skipped_count += 1
                continue

            # Use LayeredValidator for validation
            if check_type == "action":
                val_result = validator.validate_action(item, {}, "")
                result_entry = {
                    "item": item[:MCPConfig.ITEM_PREVIEW_LENGTH],
                    "safe": val_result.is_safe,
                    "violations": val_result.violations,
                }
            elif check_type == "request":
                val_result = validator.validate_request(item)
                risk_level = val_result.risk_level.value if hasattr(val_result.risk_level, 'value') else str(val_result.risk_level)
                result_entry = {
                    "item": item[:MCPConfig.ITEM_PREVIEW_LENGTH],
                    "safe": val_result.is_safe,
                    "risk_level": risk_level,
                    "concerns": val_result.violations,
                }
            else:
                val_result = validator.validate(item)
                result_entry = {
                    "item": item[:MCPConfig.ITEM_PREVIEW_LENGTH],
                    "safe": val_result.is_safe,
                    "violations": val_result.violations,
                }

            results.append(result_entry)

            if val_result.is_safe:
                safe_count += 1

        logger.debug(
            f"sentinel_batch_validate result: total={len(items)}, "
            f"safe={safe_count}, unsafe={len(items) - safe_count - skipped_count}, "
            f"skipped={skipped_count}"
        )
        return {
            "total": len(items),
            "safe_count": safe_count,
            "unsafe_count": len(items) - safe_count - skipped_count,
            "skipped_count": skipped_count,
            "all_safe": safe_count == len(items),
            "truncated": truncated,
            "results": results,
        }

    # Resource: Seed content by level
    @mcp.resource("sentinel://seed/{level}")
    def get_seed_resource(level: str) -> str:
        """
        Get Sentinel seed content by level.

        Available levels: minimal, standard, full
        """
        try:
            temp_sentinel = Sentinel(seed_level=level)
            return temp_sentinel.get_seed()
        except ValueError:
            return f"Invalid seed level: {level}. Use 'minimal', 'standard', or 'full'."

    # Resource: Configuration
    @mcp.resource("sentinel://config")
    def get_config_resource() -> Dict[str, Any]:
        """Get current Sentinel configuration."""
        return {
            "version": __version__,
            "default_seed_level": sentinel.seed_level if hasattr(sentinel, 'seed_level') else "standard",
            "protocol": "THSP",
            "gates": ["Truth", "Harm", "Scope", "Purpose"],
            "limits": {
                "max_text_size": MCPConfig.MAX_TEXT_SIZE,
                "max_text_size_batch": MCPConfig.MAX_TEXT_SIZE_BATCH,
                "max_batch_items": MCPConfig.MAX_BATCH_ITEMS,
                "default_timeout": MCPConfig.DEFAULT_TIMEOUT,
            },
        }


class MCPClientError(Exception):
    """Base exception for MCP client errors."""
    pass


class MCPTimeoutError(MCPClientError):
    """Raised when an MCP operation times out."""

    def __init__(self, operation: str, timeout: float):
        self.operation = operation
        self.timeout = timeout
        super().__init__(f"Operation '{operation}' timed out after {timeout}s")


class MCPConnectionError(MCPClientError):
    """Raised when connection to MCP server fails."""
    pass


class SentinelMCPClient:
    """
    Client for connecting to Sentinel MCP servers.

    Supports two connection modes:
    - HTTP: Connect to a remote server via Streamable HTTP transport
    - Stdio: Connect to a local server process via stdio transport

    Example (HTTP):
        from sentinelseed.integrations.mcp_server import SentinelMCPClient

        async with SentinelMCPClient("http://localhost:8000/mcp") as client:
            result = await client.validate("Some text to check")
            if result["safe"]:
                proceed()

    Example (Stdio):
        async with SentinelMCPClient(
            command="python",
            args=["-m", "sentinelseed.integrations.mcp_server"]
        ) as client:
            result = await client.check_action("delete all files")

    Example (with timeout):
        async with SentinelMCPClient(url="http://localhost:8000/mcp", timeout=10.0) as client:
            result = await client.validate("Some text")
    """

    def __init__(
        self,
        url: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        timeout: float = MCPConfig.DEFAULT_TIMEOUT,
    ):
        """
        Initialize MCP client.

        Args:
            url: URL for HTTP transport (e.g., "http://localhost:8000/mcp")
            command: Command for stdio transport (e.g., "python")
            args: Arguments for stdio command (e.g., ["-m", "sentinelseed.integrations.mcp_server"])
            timeout: Default timeout for operations in seconds (default: 30.0)

        Note: Provide either url OR (command + args), not both.
        """
        if url and command:
            raise ValueError("Provide either url or command/args, not both")
        if not url and not command:
            raise ValueError("Must provide either url or command")

        self.url = url
        self.command = command
        self.args = args or []
        self.timeout = timeout
        self._session = None
        self._read_stream = None
        self._write_stream = None
        self._transport_context = None

        logger.debug(f"SentinelMCPClient initialized: url={url}, command={command}, timeout={timeout}")

    async def __aenter__(self):
        """Async context manager entry - establishes connection."""
        try:
            from mcp import ClientSession
        except (ImportError, AttributeError):
            raise ImportError(
                "mcp package not installed or incompatible version. Install with: pip install mcp"
            )

        if self.url:
            # HTTP transport for remote servers
            try:
                from mcp.client.streamable_http import streamable_http_client
            except (ImportError, AttributeError):
                raise ImportError(
                    "Streamable HTTP client not available or incompatible version. Update mcp package."
                )

            self._transport_context = streamable_http_client(self.url)
            self._read_stream, self._write_stream, _ = await self._transport_context.__aenter__()
        else:
            # Stdio transport for local servers
            from mcp import StdioServerParameters
            from mcp.client.stdio import stdio_client

            server_params = StdioServerParameters(
                command=self.command,
                args=self.args,
            )
            self._transport_context = stdio_client(server_params)
            self._read_stream, self._write_stream = await self._transport_context.__aenter__()

        # Create and initialize session
        self._session = ClientSession(self._read_stream, self._write_stream)
        await self._session.__aenter__()
        await self._session.initialize()

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - closes connection."""
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
        if self._transport_context:
            await self._transport_context.__aexit__(exc_type, exc_val, exc_tb)

    def _parse_tool_result(
        self,
        result,
        default_error: Dict[str, Any],
        tool_name: str = "unknown",
    ) -> Dict[str, Any]:
        """
        Parse MCP tool result into a dictionary.

        Handles different response formats from MCP servers.

        Args:
            result: MCP tool result
            default_error: Default dict to return on parse failure
            tool_name: Name of tool for logging purposes

        Returns:
            Parsed result dict or default_error
        """
        import json

        if not result.content or len(result.content) == 0:
            logger.warning(
                f"_parse_tool_result: empty content for tool '{tool_name}', "
                f"returning default error"
            )
            return default_error

        content = result.content[0]

        # Case 1: TextContent with JSON string
        if hasattr(content, 'text'):
            text = content.text
            # Try to parse as JSON
            try:
                parsed = json.loads(text)
                logger.debug(f"_parse_tool_result: parsed JSON for '{tool_name}'")
                return parsed
            except (json.JSONDecodeError, TypeError) as e:
                # Not JSON, return as-is in a dict
                logger.debug(
                    f"_parse_tool_result: text not JSON for '{tool_name}': {e}, "
                    f"returning as raw result"
                )
                return {"result": text}

        # Case 2: Already a dict (some MCP implementations)
        if isinstance(content, dict):
            logger.debug(f"_parse_tool_result: content is dict for '{tool_name}'")
            return content

        # Case 3: Has a 'data' attribute
        if hasattr(content, 'data'):
            if isinstance(content.data, dict):
                logger.debug(f"_parse_tool_result: content.data is dict for '{tool_name}'")
                return content.data
            try:
                parsed = json.loads(content.data)
                logger.debug(f"_parse_tool_result: parsed content.data JSON for '{tool_name}'")
                return parsed
            except (json.JSONDecodeError, TypeError) as e:
                logger.debug(
                    f"_parse_tool_result: content.data not JSON for '{tool_name}': {e}"
                )
                return {"result": content.data}

        # Fallback
        logger.warning(
            f"_parse_tool_result: unrecognized content format for '{tool_name}', "
            f"content type: {type(content).__name__}, returning default error"
        )
        return default_error

    async def _call_with_timeout(
        self,
        coro,
        operation: str,
        timeout: Optional[float] = None,
    ):
        """
        Execute a coroutine with timeout.

        Args:
            coro: Coroutine to execute
            operation: Operation name for error messages
            timeout: Timeout in seconds (uses self.timeout if None)

        Returns:
            Result of the coroutine

        Raises:
            MCPTimeoutError: If operation times out
        """
        timeout = timeout or self.timeout
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            logger.error(f"Operation '{operation}' timed out after {timeout}s")
            raise MCPTimeoutError(operation, timeout)

    async def list_tools(self, timeout: Optional[float] = None) -> List[str]:
        """
        List available tools on the server.

        Args:
            timeout: Optional timeout override in seconds

        Returns:
            List of tool names

        Raises:
            RuntimeError: If client not connected
            MCPTimeoutError: If operation times out
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        logger.debug("list_tools called")
        response = await self._call_with_timeout(
            self._session.list_tools(),
            "list_tools",
            timeout,
        )
        tools = [tool.name for tool in response.tools]
        logger.debug(f"list_tools result: {len(tools)} tools")
        return tools

    async def validate(
        self,
        text: str,
        check_type: str = "general",
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Validate text through THSP gates.

        Args:
            text: Text to validate
            check_type: "general", "action", or "request"
            timeout: Optional timeout override in seconds

        Returns:
            Dict with 'safe', 'violations'/'concerns', 'recommendation'

        Raises:
            RuntimeError: If client not connected
            MCPTimeoutError: If operation times out
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        logger.debug(f"validate called: check_type={check_type}, text_len={len(text)}")
        result = await self._call_with_timeout(
            self._session.call_tool(
                "sentinel_validate",
                {"text": text, "check_type": check_type}
            ),
            "validate",
            timeout,
        )
        return self._parse_tool_result(
            result,
            {"safe": False, "error": "Invalid response"},
            "sentinel_validate",
        )

    async def check_action(
        self,
        action: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Check if an action is safe to execute.

        Args:
            action: Description of the action
            timeout: Optional timeout override in seconds

        Returns:
            Dict with 'safe', 'should_proceed', 'concerns', 'risk_level'

        Raises:
            RuntimeError: If client not connected
            MCPTimeoutError: If operation times out
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        logger.debug(f"check_action called: action_len={len(action)}")
        result = await self._call_with_timeout(
            self._session.call_tool(
                "sentinel_check_action",
                {"action": action}
            ),
            "check_action",
            timeout,
        )
        return self._parse_tool_result(
            result,
            {"safe": False, "error": "Invalid response"},
            "sentinel_check_action",
        )

    async def check_request(
        self,
        request: str,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Validate a user request for safety.

        Args:
            request: User request text
            timeout: Optional timeout override in seconds

        Returns:
            Dict with 'should_proceed', 'risk_level', 'concerns'

        Raises:
            RuntimeError: If client not connected
            MCPTimeoutError: If operation times out
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        logger.debug(f"check_request called: request_len={len(request)}")
        result = await self._call_with_timeout(
            self._session.call_tool(
                "sentinel_check_request",
                {"request": request}
            ),
            "check_request",
            timeout,
        )
        return self._parse_tool_result(
            result,
            {"should_proceed": False, "error": "Invalid response"},
            "sentinel_check_request",
        )

    async def get_seed(
        self,
        level: str = "standard",
        timeout: Optional[float] = None,
    ) -> str:
        """
        Get Sentinel seed content.

        Args:
            level: "minimal", "standard", or "full"
            timeout: Optional timeout override in seconds

        Returns:
            Seed content string

        Raises:
            RuntimeError: If client not connected
            MCPTimeoutError: If operation times out
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        logger.debug(f"get_seed called: level={level}")
        result = await self._call_with_timeout(
            self._session.call_tool(
                "sentinel_get_seed",
                {"level": level}
            ),
            "get_seed",
            timeout,
        )
        # get_seed returns a string, not a dict
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, 'text'):
                logger.debug(f"get_seed result: seed_len={len(content.text)}")
                return content.text

        logger.warning("get_seed: empty or invalid response, returning empty string")
        return ""

    async def batch_validate(
        self,
        items: List[str],
        check_type: str = "general",
        max_items: int = MCPConfig.DEFAULT_BATCH_ITEMS,
        timeout: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Validate multiple items in batch.

        Args:
            items: List of text items
            check_type: "general", "action", or "request"
            max_items: Maximum items to process (default 100, max 1000)
            timeout: Optional timeout override in seconds (default uses batch timeout)

        Returns:
            Dict with 'total', 'safe_count', 'results'

        Raises:
            RuntimeError: If client not connected
            MCPTimeoutError: If operation times out
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        # Use batch timeout by default
        timeout = timeout or MCPConfig.BATCH_TIMEOUT

        logger.debug(f"batch_validate called: items={len(items)}, check_type={check_type}")
        result = await self._call_with_timeout(
            self._session.call_tool(
                "sentinel_batch_validate",
                {"items": items, "check_type": check_type, "max_items": max_items}
            ),
            "batch_validate",
            timeout,
        )
        return self._parse_tool_result(
            result,
            {"total": 0, "error": "Invalid response"},
            "sentinel_batch_validate",
        )


def run_server():
    """Run Sentinel MCP server as standalone process."""
    if not MCP_AVAILABLE:
        print("Error: mcp package not installed.")
        print("Install with: pip install mcp")
        return

    mcp = create_sentinel_mcp_server()
    print("Starting Sentinel MCP Server...")
    print("Tools available:")
    print("  - sentinel_validate")
    print("  - sentinel_check_action")
    print("  - sentinel_check_request")
    print("  - sentinel_get_seed")
    print("  - sentinel_batch_validate")
    mcp.run()


if __name__ == "__main__":
    run_server()
