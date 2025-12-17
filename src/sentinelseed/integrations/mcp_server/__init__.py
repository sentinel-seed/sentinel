"""
MCP Server integration for Sentinel AI.

Provides a Model Context Protocol server that exposes Sentinel safety
validation as tools and resources for LLM applications.

This follows the official MCP Python SDK specification:
https://github.com/modelcontextprotocol/python-sdk

Usage:
    # Option 1: Run as standalone MCP server
    python -m sentinel.integrations.mcp_server

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

Resources provided:
    - sentinel://seed/{level}: Get seed content by level
    - sentinel://config: Current Sentinel configuration
"""

from typing import Any, Dict, List, Optional, Union
import logging

from sentinelseed import Sentinel, SeedLevel
from sentinelseed.validators.semantic import SemanticValidator, THSPResult

logger = logging.getLogger("sentinelseed.mcp_server")

# Check for MCP SDK availability
MCP_AVAILABLE = False
try:
    from mcp.server.fastmcp import FastMCP, Context
    MCP_AVAILABLE = True
except ImportError:
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
) -> None:
    """
    Add Sentinel safety tools to an existing MCP server.

    This allows integration of Sentinel validation into any MCP server.

    Args:
        mcp: FastMCP server instance
        sentinel: Sentinel instance (creates default if None)

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
            text: The text content to validate
            check_type: Type of validation - 'general', 'action', or 'request'

        Returns:
            Dict with 'safe', 'violations', 'recommendation' fields
        """
        if check_type == "action":
            is_safe, violations = sentinel.validate_action(text)
        elif check_type == "request":
            result = sentinel.validate_request(text)
            return {
                "safe": result["should_proceed"],
                "risk_level": result["risk_level"],
                "concerns": result["concerns"],
                "recommendation": "Safe to proceed" if result["should_proceed"] else f"Blocked: {result['concerns']}",
            }
        else:
            is_safe, violations = sentinel.validate(text)

        return {
            "safe": is_safe,
            "violations": violations,
            "recommendation": "Content is safe" if is_safe else f"Safety concerns: {violations}",
        }

    # Tool: Check if an action is safe
    @mcp.tool()
    def sentinel_check_action(action: str) -> Dict[str, Any]:
        """
        Check if a planned action is safe to execute.

        Use this before executing any potentially risky action to ensure
        it passes THSP safety validation.

        Args:
            action: Description of the action to check

        Returns:
            Dict with 'safe', 'should_proceed', 'concerns', 'recommendation'
        """
        is_safe, concerns = sentinel.validate_action(action)
        request_check = sentinel.validate_request(action)

        all_concerns = concerns + request_check.get("concerns", [])
        should_proceed = is_safe and request_check["should_proceed"]

        # Determine risk level - escalate if action validation failed
        risk_level = request_check["risk_level"]
        if not is_safe:
            # Action failed safety check - escalate risk
            risk_level = "high" if risk_level == "low" else "critical"

        return {
            "safe": should_proceed,
            "should_proceed": should_proceed,
            "concerns": all_concerns,
            "risk_level": risk_level,
            "recommendation": "Action is safe to proceed" if should_proceed else f"Action blocked: {all_concerns}",
        }

    # Tool: Validate a user request
    @mcp.tool()
    def sentinel_check_request(request: str) -> Dict[str, Any]:
        """
        Validate a user request for safety concerns.

        Use this to check incoming user messages for jailbreak attempts,
        harmful requests, or other safety issues.

        Args:
            request: The user's request text

        Returns:
            Dict with 'should_proceed', 'risk_level', 'concerns'
        """
        result = sentinel.validate_request(request)
        return {
            "should_proceed": result["should_proceed"],
            "risk_level": result["risk_level"],
            "concerns": result["concerns"],
            "safe": result["should_proceed"],
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
        temp_sentinel = Sentinel(seed_level=level)
        return temp_sentinel.get_seed()

    # Tool: Batch validate multiple items
    @mcp.tool()
    def sentinel_batch_validate(
        items: List[str],
        check_type: str = "general",
        max_items: int = 100,
    ) -> Dict[str, Any]:
        """
        Validate multiple text items in batch.

        Efficiently validate a list of items and get aggregated results.

        Args:
            items: List of text items to validate
            check_type: Type of validation - 'general', 'action', or 'request'
            max_items: Maximum items to process (default 100, max 1000)

        Returns:
            Dict with 'total', 'safe_count', 'unsafe_count', 'results'
        """
        # Enforce size limits to prevent memory exhaustion
        max_items = min(max_items, 1000)
        if len(items) > max_items:
            items = items[:max_items]
            truncated = True
        else:
            truncated = False

        results = []
        safe_count = 0

        for item in items:
            if check_type == "action":
                is_safe, violations = sentinel.validate_action(item)
                result_entry = {
                    "item": item[:100],
                    "safe": is_safe,
                    "violations": violations,
                }
            elif check_type == "request":
                req_result = sentinel.validate_request(item)
                is_safe = req_result["should_proceed"]
                result_entry = {
                    "item": item[:100],
                    "safe": is_safe,
                    "risk_level": req_result["risk_level"],
                    "concerns": req_result["concerns"],
                }
            else:
                is_safe, violations = sentinel.validate(item)
                result_entry = {
                    "item": item[:100],
                    "safe": is_safe,
                    "violations": violations,
                }

            results.append(result_entry)

            if is_safe:
                safe_count += 1

        return {
            "total": len(items),
            "safe_count": safe_count,
            "unsafe_count": len(items) - safe_count,
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
            "version": "2.0",
            "default_seed_level": sentinel.seed_level if hasattr(sentinel, 'seed_level') else "standard",
            "protocol": "THSP",
            "gates": ["Truth", "Harm", "Scope", "Purpose"],
        }


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
    """

    def __init__(
        self,
        url: Optional[str] = None,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
    ):
        """
        Initialize MCP client.

        Args:
            url: URL for HTTP transport (e.g., "http://localhost:8000/mcp")
            command: Command for stdio transport (e.g., "python")
            args: Arguments for stdio command (e.g., ["-m", "sentinelseed.integrations.mcp_server"])

        Note: Provide either url OR (command + args), not both.
        """
        if url and command:
            raise ValueError("Provide either url or command/args, not both")
        if not url and not command:
            raise ValueError("Must provide either url or command")

        self.url = url
        self.command = command
        self.args = args or []
        self._session = None
        self._read_stream = None
        self._write_stream = None
        self._transport_context = None

    async def __aenter__(self):
        """Async context manager entry - establishes connection."""
        try:
            from mcp import ClientSession
        except ImportError:
            raise ImportError(
                "mcp package not installed. Install with: pip install mcp"
            )

        if self.url:
            # HTTP transport for remote servers
            try:
                from mcp.client.streamable_http import streamable_http_client
            except ImportError:
                raise ImportError(
                    "Streamable HTTP client not available. Update mcp package."
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

    def _parse_tool_result(self, result, default_error: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse MCP tool result into a dictionary.

        Handles different response formats from MCP servers.
        """
        import json

        if not result.content or len(result.content) == 0:
            return default_error

        content = result.content[0]

        # Case 1: TextContent with JSON string
        if hasattr(content, 'text'):
            text = content.text
            # Try to parse as JSON
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                # Not JSON, return as-is in a dict
                return {"result": text}

        # Case 2: Already a dict (some MCP implementations)
        if isinstance(content, dict):
            return content

        # Case 3: Has a 'data' attribute
        if hasattr(content, 'data'):
            if isinstance(content.data, dict):
                return content.data
            try:
                return json.loads(content.data)
            except (json.JSONDecodeError, TypeError):
                return {"result": content.data}

        return default_error

    async def list_tools(self) -> List[str]:
        """
        List available tools on the server.

        Returns:
            List of tool names
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")
        response = await self._session.list_tools()
        return [tool.name for tool in response.tools]

    async def validate(
        self, text: str, check_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Validate text through THSP gates.

        Args:
            text: Text to validate
            check_type: "general", "action", or "request"

        Returns:
            Dict with 'safe', 'violations'/'concerns', 'recommendation'
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        result = await self._session.call_tool(
            "sentinel_validate",
            {"text": text, "check_type": check_type}
        )
        return self._parse_tool_result(result, {"safe": False, "error": "Invalid response"})

    async def check_action(self, action: str) -> Dict[str, Any]:
        """
        Check if an action is safe to execute.

        Args:
            action: Description of the action

        Returns:
            Dict with 'safe', 'should_proceed', 'concerns', 'risk_level'
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        result = await self._session.call_tool(
            "sentinel_check_action",
            {"action": action}
        )
        return self._parse_tool_result(result, {"safe": False, "error": "Invalid response"})

    async def check_request(self, request: str) -> Dict[str, Any]:
        """
        Validate a user request for safety.

        Args:
            request: User request text

        Returns:
            Dict with 'should_proceed', 'risk_level', 'concerns'
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        result = await self._session.call_tool(
            "sentinel_check_request",
            {"request": request}
        )
        return self._parse_tool_result(result, {"should_proceed": False, "error": "Invalid response"})

    async def get_seed(self, level: str = "standard") -> str:
        """
        Get Sentinel seed content.

        Args:
            level: "minimal", "standard", or "full"

        Returns:
            Seed content string
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        result = await self._session.call_tool(
            "sentinel_get_seed",
            {"level": level}
        )
        # get_seed returns a string, not a dict
        if result.content and len(result.content) > 0:
            content = result.content[0]
            if hasattr(content, 'text'):
                return content.text
        return ""

    async def batch_validate(
        self,
        items: List[str],
        check_type: str = "general",
        max_items: int = 100,
    ) -> Dict[str, Any]:
        """
        Validate multiple items in batch.

        Args:
            items: List of text items
            check_type: "general", "action", or "request"
            max_items: Maximum items to process

        Returns:
            Dict with 'total', 'safe_count', 'results'
        """
        if not self._session:
            raise RuntimeError("Client not connected. Use 'async with' context.")

        result = await self._session.call_tool(
            "sentinel_batch_validate",
            {"items": items, "check_type": check_type, "max_items": max_items}
        )
        return self._parse_tool_result(result, {"total": 0, "error": "Invalid response"})


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
