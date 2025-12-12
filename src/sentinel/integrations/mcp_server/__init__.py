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
    from sentinel.integrations.mcp_server import create_sentinel_mcp_server

    mcp = create_sentinel_mcp_server()
    mcp.run()

    # Option 3: Add Sentinel tools to existing MCP server
    from sentinel.integrations.mcp_server import add_sentinel_tools

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

try:
    from sentinel import Sentinel, SeedLevel
except ImportError:
    from sentinelseed import Sentinel, SeedLevel

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
        from sentinel.integrations.mcp_server import create_sentinel_mcp_server

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
        from sentinel.integrations.mcp_server import add_sentinel_tools

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

        return {
            "safe": should_proceed,
            "should_proceed": should_proceed,
            "concerns": all_concerns,
            "risk_level": request_check["risk_level"],
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
    ) -> Dict[str, Any]:
        """
        Validate multiple text items in batch.

        Efficiently validate a list of items and get aggregated results.

        Args:
            items: List of text items to validate
            check_type: Type of validation for all items

        Returns:
            Dict with 'total', 'safe_count', 'unsafe_count', 'results'
        """
        results = []
        safe_count = 0

        for item in items:
            if check_type == "action":
                is_safe, violations = sentinel.validate_action(item)
            else:
                is_safe, violations = sentinel.validate(item)

            results.append({
                "item": item[:100],
                "safe": is_safe,
                "violations": violations,
            })

            if is_safe:
                safe_count += 1

        return {
            "total": len(items),
            "safe_count": safe_count,
            "unsafe_count": len(items) - safe_count,
            "all_safe": safe_count == len(items),
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
    Client wrapper for connecting to Sentinel MCP servers.

    Provides a convenient interface for applications that want to
    use Sentinel validation via MCP.

    Example:
        from sentinel.integrations.mcp_server import SentinelMCPClient

        async with SentinelMCPClient("http://localhost:3000") as client:
            result = await client.validate("Some text to check")
            if result["safe"]:
                proceed()
    """

    def __init__(self, server_url: str):
        """
        Initialize MCP client.

        Args:
            server_url: URL of the Sentinel MCP server
        """
        self.server_url = server_url
        self._client = None

    async def __aenter__(self):
        """Async context manager entry."""
        try:
            from mcp import ClientSession
            from mcp.client.streamable_http import streamablehttp_client
        except ImportError:
            raise ImportError("mcp package not installed")

        # Connection would be established here
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._client:
            await self._client.close()

    async def validate(self, text: str, check_type: str = "general") -> Dict[str, Any]:
        """
        Validate text via the MCP server.

        Args:
            text: Text to validate
            check_type: Type of validation

        Returns:
            Validation result dict
        """
        # This would call the MCP tool
        # For now, fall back to local validation
        sentinel = Sentinel()
        is_safe, violations = sentinel.validate(text)
        return {
            "safe": is_safe,
            "violations": violations,
        }


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
