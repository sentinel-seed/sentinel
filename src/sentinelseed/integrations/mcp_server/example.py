"""
Example: Using Sentinel MCP Server.

Shows how to create an MCP server with Sentinel safety tools.

Requirements:
    pip install mcp sentinelseed
"""

from sentinelseed.integrations.mcp_server import (
    create_sentinel_mcp_server,
    add_sentinel_tools,
)


def example_create_server():
    """Example 1: Create standalone MCP server."""
    print("=== Create MCP Server ===\n")

    try:
        # Create Sentinel MCP server
        mcp = create_sentinel_mcp_server(
            name="sentinel-safety",
            seed_level="standard"
        )

        print("MCP Server created with tools:")
        print("  - sentinel_validate")
        print("  - sentinel_check_action")
        print("  - sentinel_check_request")
        print("  - sentinel_get_seed")
        print("  - sentinel_batch_validate")
        print("\nRun with: mcp.run()")

    except ImportError:
        print("MCP package not installed. Install with: pip install mcp")


def example_add_to_existing():
    """Example 2: Add Sentinel tools to existing server."""
    print("\n=== Add to Existing Server ===\n")

    try:
        from mcp.server.fastmcp import FastMCP

        # Your existing MCP server
        mcp = FastMCP("my-server")

        # Add Sentinel tools
        add_sentinel_tools(mcp)

        print("Sentinel tools added to existing server")

    except ImportError:
        print("MCP package not installed")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel MCP Server Examples")
    print("=" * 60)

    example_create_server()
    example_add_to_existing()

    print("\nTo run the server:")
    print("  python -m sentinel.integrations.mcp_server")
