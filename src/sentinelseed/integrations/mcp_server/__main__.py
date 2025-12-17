"""
Entry point for running Sentinel MCP Server as a module.

Usage:
    python -m sentinelseed.integrations.mcp_server
"""

from sentinelseed.integrations.mcp_server import run_server

if __name__ == "__main__":
    run_server()
