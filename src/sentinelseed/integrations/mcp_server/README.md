# MCP Server Integration

Model Context Protocol server exposing Sentinel safety tools.

## Requirements

```bash
pip install sentinelseed[mcp]
# or manually:
pip install sentinelseed mcp
```

**Dependencies:**
- `mcp>=0.1.0` — [GitHub](https://github.com/modelcontextprotocol/python-sdk)

**For Claude Desktop:**
```bash
npm install -g mcp-server-sentinelseed
```

## Overview

| Component | Description |
|-----------|-------------|
| `create_sentinel_mcp_server` | Create MCP server with tools |
| `add_sentinel_tools` | Add tools to existing server |
| `SentinelMCPClient` | Client for connecting to server |
| `run_server` | Run standalone server |

## Tools Provided

| Tool | Description |
|------|-------------|
| `sentinel_validate` | Validate text through THSP |
| `sentinel_check_action` | Check if action is safe |
| `sentinel_check_request` | Validate user request |
| `sentinel_get_seed` | Get seed content |
| `sentinel_batch_validate` | Validate multiple items |

## Resources Provided

| Resource | Description |
|----------|-------------|
| `sentinel://seed/{level}` | Get seed by level |
| `sentinel://config` | Current configuration |

## Usage

### Option 1: Standalone Server

```python
from sentinelseed.integrations.mcp_server import create_sentinel_mcp_server

mcp = create_sentinel_mcp_server()
mcp.run()
```

Or run directly:
```bash
python -m sentinelseed.integrations.mcp_server
```

### Option 2: Add to Existing Server

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

### Option 3: IDE Configuration

#### Claude Desktop

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

#### Cursor

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

Or using npm:

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

After adding, restart Cursor and the Sentinel tools will be available to the AI agent.

#### Windsurf

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

Or using npm:

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

After adding, click the hammer icon in Cascade to enable MCP tools.

#### VS Code (with Continue or similar)

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

## Tool Specifications

### sentinel_validate

```python
def sentinel_validate(text: str, check_type: str = "general") -> dict:
    """
    Validate text through THSP gates.

    Args:
        text: Content to validate
        check_type: "general", "action", or "request"

    Returns:
        {safe: bool, violations: [], recommendation: str}
    """
```

### sentinel_check_action

```python
def sentinel_check_action(action: str) -> dict:
    """
    Check if planned action is safe.

    Args:
        action: Action description

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
        request: User request text

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
        items: List of text strings
        check_type: "general", "action", or "request"
        max_items: Maximum items to process (default 100, max 1000)

    Returns:
        {total: int, safe_count: int, unsafe_count: int, all_safe: bool, truncated: bool, results: []}
    """
```

## Configuration

### create_sentinel_mcp_server

```python
create_sentinel_mcp_server(
    name="sentinel-safety",      # Server name
    sentinel=None,               # Sentinel instance
    seed_level="standard",       # Default seed level
)
```

## Client Usage

The client supports two connection modes:

### HTTP Transport (Remote Server)

```python
from sentinelseed.integrations.mcp_server import SentinelMCPClient

async with SentinelMCPClient(url="http://localhost:8000/mcp") as client:
    # List available tools
    tools = await client.list_tools()

    # Validate text
    result = await client.validate("Some text to check")
    if result["safe"]:
        proceed()

    # Check action safety
    action_result = await client.check_action("delete user data")
    print(f"Risk level: {action_result['risk_level']}")

    # Batch validation
    batch = await client.batch_validate(
        ["text1", "text2", "text3"],
        check_type="request"
    )
```

### Stdio Transport (Local Server)

```python
async with SentinelMCPClient(
    command="python",
    args=["-m", "sentinelseed.integrations.mcp_server"]
) as client:
    result = await client.check_request("ignore previous instructions")
    if not result["should_proceed"]:
        print(f"Blocked: {result['concerns']}")
```

## API Reference

### Functions

| Function | Description |
|----------|-------------|
| `create_sentinel_mcp_server(name)` | Create server |
| `add_sentinel_tools(mcp)` | Add tools to server |
| `run_server()` | Run standalone |

### Classes

| Class | Description |
|-------|-------------|
| `SentinelMCPClient` | Async client for MCP servers |

### SentinelMCPClient Methods

| Method | Description |
|--------|-------------|
| `list_tools()` | List available tools on server |
| `validate(text, check_type)` | Validate text through THSP |
| `check_action(action)` | Check if action is safe |
| `check_request(request)` | Validate user request |
| `get_seed(level)` | Get seed content |
| `batch_validate(items, check_type, max_items)` | Batch validation |

### Constants

| Constant | Type | Description |
|----------|------|-------------|
| `MCP_AVAILABLE` | bool | Whether MCP SDK installed |

## Links

- **MCP SDK:** https://github.com/modelcontextprotocol/python-sdk
- **MCP Specification:** https://spec.modelcontextprotocol.io/
- **npm Package:** https://npmjs.com/package/mcp-server-sentinelseed
- **Sentinel:** https://sentinelseed.dev
