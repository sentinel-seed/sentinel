# AutoGPT Block SDK Integration

Sentinel safety validation blocks for AutoGPT Platform v0.6+.

## Requirements

This integration is designed for the **AutoGPT Platform** which uses the Block SDK architecture. For standalone usage without AutoGPT, you can use the provided standalone functions.

**References:**
- [AutoGPT Block SDK Guide](https://dev-docs.agpt.co/platform/block-sdk-guide/)
- [AutoGPT Platform](https://platform.agpt.co)

## Overview

| Component | Description |
|-----------|-------------|
| `SentinelValidationBlock` | Validate text content through THSP gates |
| `SentinelActionCheckBlock` | Check if an action is safe before execution |
| `SentinelSeedBlock` | Get the Sentinel safety seed for injection |
| `validate_content()` | Standalone function for content validation |
| `check_action()` | Standalone function for action checking |
| `get_seed()` | Standalone function to get seed |

## Installation in AutoGPT Platform

### Step 1: Copy the block module

Copy the `__init__.py` file to your AutoGPT Platform blocks directory:

```bash
cp sentinelseed/integrations/autogpt_block/__init__.py /path/to/autogpt/platform/blocks/sentinel_blocks.py
```

### Step 2: Register blocks

The blocks will be auto-discovered if your AutoGPT Platform is configured to scan the blocks directory. The `BLOCKS` list at the end of the module enables auto-registration:

```python
BLOCKS = [
    SentinelValidationBlock,
    SentinelActionCheckBlock,
    SentinelSeedBlock,
]
```

### Step 3: Use in workflows

Once registered, the blocks appear in the AutoGPT workflow builder UI. Connect them before sensitive operations.

## Standalone Usage (Without AutoGPT)

You can use the validation functions directly without the AutoGPT Platform:

```python
from sentinelseed.integrations.autogpt_block import (
    validate_content,
    check_action,
    get_seed,
)

# Validate content
result = validate_content("How do I hack a computer?")
if not result["safe"]:
    print(f"Blocked: {result['violations']}")
    print(f"Risk level: {result['risk_level']}")

# Check action before execution
result = check_action(
    action_name="delete_file",
    action_args={"path": "/etc/passwd"},
    purpose="Clean up temporary files"
)
if not result["should_proceed"]:
    print(f"Blocked: {result['concerns']}")
    print(f"Recommendations: {result['recommendations']}")

# Get seed for system prompt
seed = get_seed("standard")
system_prompt = f"{seed}\n\nYou are a helpful assistant."
```

## Block Details

### SentinelValidationBlock

Validates text content through THSP (Truth, Harm, Scope, Purpose) gates.

**Inputs:**
- `content` (str): Text content to validate
- `seed_level` (str): Validation strictness - `minimal`, `standard`, `full` (default: `standard`)
- `check_type` (str): Type of check - `general`, `action`, `request` (default: `general`)

**Outputs:**
- `safe` (bool): Whether content passed validation
- `content` (str): Original content (if safe) or empty string
- `violations` (list): List of detected violations
- `risk_level` (str): Risk level - `low`, `medium`, `high`, `critical`

### SentinelActionCheckBlock

Validates if an action is safe to execute before proceeding.

**Inputs:**
- `action_name` (str): Name of the action (e.g., `delete_file`, `send_email`)
- `action_args` (str): JSON string of action arguments (default: `{}`)
- `purpose` (str): Stated purpose/reason for the action (default: empty)
- `seed_level` (str): Sentinel seed level (default: `standard`)

**Outputs:**
- `should_proceed` (bool): Whether action should proceed
- `concerns` (list): List of safety concerns
- `recommendations` (list): Suggested actions
- `risk_level` (str): Risk level assessment

### SentinelSeedBlock

Retrieves the Sentinel safety seed for injection into system prompts.

**Inputs:**
- `level` (str): Seed level - `minimal` (~360 tokens), `standard` (~1000 tokens), `full` (~1900 tokens)

**Outputs:**
- `seed` (str): The Sentinel safety seed content
- `token_count` (int): Approximate token count of the seed

## Workflow Examples

### Content Validation Workflow

```
[User Input] → [SentinelValidationBlock] → [Conditional]
                                              ↓ safe=true
                                         [Process Content]
                                              ↓ safe=false
                                         [Reject/Log]
```

### Safe Action Execution

```
[Action Request] → [SentinelActionCheckBlock] → [Conditional]
                                                    ↓ should_proceed=true
                                               [Execute Action]
                                                    ↓ should_proceed=false
                                               [Human Review]
```

### LLM with Safety Seed

```
[SentinelSeedBlock] → [Build System Prompt] → [LLM Call] → [SentinelValidationBlock] → [Output]
```

## API Reference

### validate_content()

```python
def validate_content(
    content: str,
    seed_level: str = "standard",
    check_type: str = "general",
) -> Dict[str, Any]
```

Returns:
```python
{
    "safe": bool,
    "violations": List[str],
    "risk_level": str,  # "low", "medium", "high", "critical"
    "gate_results": {
        "truth": bool,
        "harm": bool,
        "scope": bool,
        "purpose": bool,
    },
    "content": str,
}
```

### check_action()

```python
def check_action(
    action_name: str,
    action_args: Optional[Dict[str, Any]] = None,
    purpose: str = "",
    seed_level: str = "standard",
) -> Dict[str, Any]
```

Returns:
```python
{
    "should_proceed": bool,
    "action": str,
    "concerns": List[str],
    "recommendations": List[str],
    "risk_level": str,
}
```

### get_seed()

```python
def get_seed(level: str = "standard") -> str
```

Returns the seed content as a string.

## Migration from Legacy AutoGPT Integration

If you were using the legacy `sentinelseed.integrations.autogpt` module, migrate to this Block SDK integration:

**Before (Legacy):**
```python
from sentinelseed.integrations.autogpt import SentinelAutoGPT
agent = SentinelAutoGPT(agent_config)
```

**After (Block SDK):**
```python
from sentinelseed.integrations.autogpt_block import validate_content, check_action

# Use standalone functions or add blocks to your AutoGPT Platform workflow
result = validate_content(user_input)
```

The legacy module is deprecated and should not be used for new projects.

## Resources

- [AutoGPT Platform](https://platform.agpt.co)
- [Block SDK Guide](https://dev-docs.agpt.co/platform/block-sdk-guide/)
- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [THSP Protocol](https://sentinelseed.dev/docs/methodology)
