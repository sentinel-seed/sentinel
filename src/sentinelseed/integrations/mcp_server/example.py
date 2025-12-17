"""
Example: Using Sentinel MCP Server and Client.

Shows how to create an MCP server and connect with a client.

Requirements:
    pip install mcp sentinelseed
"""

import asyncio
from sentinelseed.integrations.mcp_server import (
    create_sentinel_mcp_server,
    add_sentinel_tools,
    SentinelMCPClient,
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


async def example_client_usage():
    """Example 3: Using MCP client to connect to server."""
    print("\n=== MCP Client Usage ===\n")

    try:
        # Option A: Connect via stdio (local server)
        print("Connecting via stdio transport...")
        async with SentinelMCPClient(
            command="python",
            args=["-m", "sentinelseed.integrations.mcp_server"]
        ) as client:
            # List available tools
            tools = await client.list_tools()
            print(f"Available tools: {tools}")

            # Validate text
            result = await client.validate("Hello, how are you?")
            print(f"Validation result: {result}")

            # Check action safety
            action_result = await client.check_action("delete all user files")
            print(f"Action check: {action_result}")

    except ImportError as e:
        print(f"MCP package not installed: {e}")
    except Exception as e:
        print(f"Example requires running server: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Sentinel MCP Server Examples")
    print("=" * 60)

    example_create_server()
    example_add_to_existing()

    print("\n" + "=" * 60)
    print("Client Example (requires MCP package)")
    print("=" * 60)

    # Uncomment to run client example
    # asyncio.run(example_client_usage())

    print("\nTo run the server:")
    print("  python -m sentinelseed.integrations.mcp_server")

    print("\nTo use the client (after starting server):")
    print("  asyncio.run(example_client_usage())")
