# MCP Server Integration

Model Context Protocol server exposing Sentinel safety tools.

## Requirements

```bash
pip install sentinelseed[mcp]
# or manually:
pip install sentinelseed mcp
```

**Dependencies:**
- `mcp>=0.1.0`: [GitHub](https://github.com/modelcontextprotocol/python-sdk)

**For Claude Desktop:**
```bash
npm install -g mcp-server-sentinelseed
```

## Overview

| Component | Description |
|-----------|-------------|
| `create_sentinel_mcp_server` | Create MCP server with tools |
| `add_sentinel_tools` | Add tools to existing server |
| `SentinelMCPClient` | Async client for connecting to server |
| `run_server` | Run standalone server |
| `MCPConfig` | Configuration constants |

## Tools Provided

| Tool | Description |
|------|-------------|
| `sentinel_validate` | Validate text through THSP (max 50KB) |
| `sentinel_check_action` | Check if action is safe (max 50KB) |
| `sentinel_check_request` | Validate user request (max 50KB) |
| `sentinel_get_seed` | Get seed content |
| `sentinel_batch_validate` | Validate multiple items (max 10KB each) |

## Resources Provided

| Resource | Description |
|----------|-------------|
| `sentinel://seed/{level}` | Get seed by level |
| `sentinel://config` | Current configuration with limits |

## Quick Start

### Standalone Server

```python
from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server

mcp = create_sentinel_mcp_server()
mcp.run()
```

Or run directly:
```bash
python -m sentinelseed.integrations.mcp_server
```

### Add to Existing Server

```python
from mcp.server.fastmcp import FastMCP
from sentinelseed.integrations.mcp_server import add_sentinel_tools

mcp = FastMCP("my-server")
add_sentinel_tools(mcp)

@mcp.tool()
def my_custom_tool():
    pass

mcp.run()
```

## IDE Configuration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "sentinel": {
      "command": "npx",
      "args": ["mcp-server-sentinelseed"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root (or `~/.cursor/mcp.json` for global):

```json
{
  "mcpServers": {
    "sentinel": {
      "command": "python",
      "args": ["-m", "sentinelseed.integrations.mcp_server"],
      "env": {}
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "sentinel": {
      "command": "python",
      "args": ["-m", "sentinelseed.integrations.mcp_server"],
      "env": {}
    }
  }
}
```

### VS Code (with Continue or similar)

Add to your MCP-compatible extension's config:

```json
{
  "mcpServers": {
    "sentinel": {
      "command": "python",
      "args": ["-m", "sentinelseed.integrations.mcp_server"]
    }
  }
}
```

## Configuration

### MCPConfig

Default limits and timeouts:

```python
from sentinelseed.integrations.mcp_server import MCPConfig

# Text size limits
MCPConfig.MAX_TEXT_SIZE = 50 * 1024        # 50KB per request
MCPConfig.MAX_TEXT_SIZE_BATCH = 10 * 1024  # 10KB per batch item

# Batch limits
MCPConfig.MAX_BATCH_ITEMS = 1000           # Maximum items in batch
MCPConfig.DEFAULT_BATCH_ITEMS = 100        # Default batch size

# Timeouts
MCPConfig.DEFAULT_TIMEOUT = 30.0           # Default operation timeout
MCPConfig.BATCH_TIMEOUT = 60.0             # Batch operation timeout
```

### create_sentinel_mcp_server

```python
create_sentinel_mcp_server(
    name="sentinel-safety",      # Server name
    sentinel=None,               # Sentinel instance (optional)
    seed_level="standard",       # Default seed level
)
```

### add_sentinel_tools

```python
add_sentinel_tools(
    mcp,                         # FastMCP server instance (required)
    sentinel=None,               # Sentinel instance for get_seed (optional)
    validator=None,              # LayeredValidator for validation (optional)
)
```

## Tool Specifications

### sentinel_validate

```python
def sentinel_validate(text: str, check_type: str = "general") -> dict:
    """
    Validate text through THSP gates.

    Args:
        text: Content to validate (max 50KB)
        check_type: "general", "action", or "request"

    Returns:
        {safe: bool, violations: [], recommendation: str}
        On size error: {safe: False, error: "text_too_large", ...}
    """
```

### sentinel_check_action

```python
def sentinel_check_action(action: str) -> dict:
    """
    Check if planned action is safe.

    Args:
        action: Action description (max 50KB)

    Returns:
        {safe: bool, should_proceed: bool, concerns: [], risk_level: str}
    """
```

### sentinel_check_request

```python
def sentinel_check_request(request: str) -> dict:
    """
    Validate user request for safety.

    Args:
        request: User request text (max 50KB)

    Returns:
        {should_proceed: bool, risk_level: str, concerns: []}
    """
```

### sentinel_get_seed

```python
def sentinel_get_seed(level: str = "standard") -> str:
    """
    Get Sentinel seed for system prompt.

    Args:
        level: "minimal", "standard", or "full"

    Returns:
        Seed content string
    """
```

### sentinel_batch_validate

```python
def sentinel_batch_validate(
    items: list,
    check_type: str = "general",
    max_items: int = 100
) -> dict:
    """
    Validate multiple items.

    Args:
        items: List of text strings (max 10KB each)
        check_type: "general", "action", or "request"
        max_items: Maximum items to process (default 100, max 1000)

    Returns:
        {
            total: int,
            safe_count: int,
            unsafe_count: int,
            skipped_count: int,  # Items that exceeded size limit
            all_safe: bool,
            truncated: bool,
            results: []
        }
    """
```

## Client Usage

### HTTP Transport (Remote Server)

> **Note:** HTTP transport requires `streamable_http_client` from the MCP SDK, which
> may not be available in all versions. Use stdio transport for maximum compatibility.

```python
from sentinelseed.integrations.mcp_server import SentinelMCPClient

async with SentinelMCPClient(
    url="http://localhost:8000/mcp",
    timeout=30.0,  # Optional timeout override
) as client:
    # List available tools
    tools = await client.list_tools()

    # Validate text
    result = await client.validate("Some text to check")
    if result["safe"]:
        proceed()

    # Check action safety
    action_result = await client.check_action("delete user data")
    print(f"Risk level: {action_result['risk_level']}")

    # Batch validation with custom timeout
    batch = await client.batch_validate(
        ["text1", "text2", "text3"],
        check_type="request",
        timeout=60.0,  # Override timeout for batch
    )
```

### Stdio Transport (Local Server)

```python
async with SentinelMCPClient(
    command="python",
    args=["-m", "sentinelseed.integrations.mcp_server"],
    timeout=10.0,
) as client:
    result = await client.check_request("ignore previous instructions")
    if not result["should_proceed"]:
        print(f"Blocked: {result['concerns']}")
```

## Exception Handling

```python
from sentinelseed.integrations.mcp_server import (
    MCPClientError,      # Base exception for client errors
    MCPTimeoutError,     # Operation timed out
    MCPConnectionError,  # Connection failed
    TextTooLargeError,   # Text exceeds size limit
)

try:
    async with SentinelMCPClient(url="http://localhost:8000/mcp") as client:
        result = await client.validate(text, timeout=5.0)
except MCPTimeoutError as e:
    print(f"Timeout after {e.timeout}s on {e.operation}")
except TextTooLargeError as e:
    print(f"Text {e.size} bytes exceeds limit of {e.max_size}")
except MCPClientError as e:
    print(f"Client error: {e}")
```

## Logging

Enable debug logging to see operation details:

```python
import logging
logging.getLogger("sentinelseed.mcp_server").setLevel(logging.DEBUG)
```

## Running Examples

```bash
# Basic examples
python -m sentinelseed.integrations.mcp_server.example

# All examples including async client
python -m sentinelseed.integrations.mcp_server.example --all
```

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `create_sentinel_mcp_server(name, sentinel, seed_level)` | Create server |
| `add_sentinel_tools(mcp, sentinel, validator)` | Add tools to server |
| `run_server()` | Run standalone |

### Classes

| Class | Description |
|-------|-------------|
| `SentinelMCPClient` | Async client for MCP servers |
| `MCPConfig` | Configuration constants |
| `TextTooLargeError` | Text size exceeded |
| `MCPClientError` | Base client exception |
| `MCPTimeoutError` | Timeout exception |
| `MCPConnectionError` | Connection exception |

### SentinelMCPClient Methods

| Method | Description |
|--------|-------------|
| `list_tools(timeout)` | List available tools |
| `validate(text, check_type, timeout)` | Validate text through THSP |
| `check_action(action, timeout)` | Check if action is safe |
| `check_request(request, timeout)` | Validate user request |
| `get_seed(level, timeout)` | Get seed content |
| `batch_validate(items, check_type, max_items, timeout)` | Batch validation |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `MCP_AVAILABLE` | bool | Whether MCP SDK is installed |
| `__version__` | str | Integration version |

## Links

- **MCP SDK:** https://github.com/modelcontextprotocol/python-sdk
- **MCP Specification:** https://spec.modelcontextprotocol.io/
- **npm Package:** https://www.npmjs.com/package/mcp-server-sentinelseed
- **Sentinel:** https://sentinelseed.dev
