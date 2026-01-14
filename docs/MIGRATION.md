# Migration Guide

This guide helps you migrate to Sentinel v2.25.0 and adopt the recommended patterns.

## Table of Contents

1. [Quick Migration Checklist](#quick-migration-checklist)
2. [Migrating to v2.25.0](#migrating-to-v2250)
3. [Migrating to v2.24.0](#migrating-to-v2240)
4. [Deprecated APIs](#deprecated-apis)
5. [New Recommended Patterns](#new-recommended-patterns)
6. [Integration Migration](#integration-migration)
7. [Configuration Changes](#configuration-changes)

## Quick Migration Checklist

```
[ ] Replace THSValidator with THSPValidator or LayeredValidator
[ ] Replace JailbreakGate with Scope gate patterns
[ ] Use LayeredValidator instead of direct gate imports
[ ] Update custom integrations to inherit from SentinelIntegration
[ ] Enable heuristic + semantic validation for production
[ ] Update gate3_* parameters to gate4_* (v2.24.0+)
[ ] Consider using SentinelValidator for unified 3-gate validation
[ ] Pass conversation_history for multi-turn attack detection (v2.25.0+)
```

## Migrating to v2.25.0

### Multi-turn Conversation Support

v2.25.0 adds native support for multi-turn conversation analysis in the public API. This enables detection of escalation attacks like Crescendo and Many-shot Harmful Jailbreaking (MHJ).

```python
from sentinelseed import SentinelValidator, SentinelConfig

config = SentinelConfig(
    gate4_enabled=True,
    gate4_model="gpt-4o-mini",
    gate4_api_key="sk-...",
)

validator = SentinelValidator(config)

# NEW: Pass conversation history for multi-turn analysis
result = validator.validate_dialogue(
    input="user message",
    output="AI response",
    conversation_history=[  # Optional, max 10 turns used
        {"role": "user", "content": "previous user message"},
        {"role": "assistant", "content": "previous AI response"},
    ]
)
```

### Key Changes

| Aspect | Before (v2.24.0) | After (v2.25.0) |
|--------|------------------|-----------------|
| `validate_dialogue()` | 2 parameters | 3 parameters (history optional) |
| Gate 4 (L4 Observer) | Single-turn only | Multi-turn analysis |
| Escalation detection | Limited | Q6 attacks (Crescendo, MHJ) |

### Backward Compatibility

This is a **fully backward-compatible** change:

```python
# This still works exactly as before
result = validator.validate_dialogue(input, output)

# New: pass history for better detection
result = validator.validate_dialogue(input, output, conversation_history=history)
```

## Migrating to v2.24.0

### Gate Naming: gate3 to gate4

In v2.24.0, the internal naming was updated from `gate3` to `gate4` for consistency with the L1/L2/L3/L4 layer naming. Legacy `gate3_*` properties are preserved as read-only aliases for backward compatibility.

```python
# Before (still works, but deprecated for config)
config = SentinelConfig(
    gate3_enabled=True,      # Use gate4_enabled instead
    gate3_model="gpt-4o",    # Use gate4_model instead
)

# After (recommended)
from sentinelseed import SentinelConfig

config = SentinelConfig(
    gate4_enabled=True,
    gate4_model="gpt-4o",
    gate4_fallback="ALLOW_IF_L2_PASSED",
)

# Legacy properties still work for reading
print(config.gate3_enabled)  # Returns gate4_enabled value
```

### Using Gate4Fallback

v2.24.0 introduces configurable fallback behavior when the L4 Observer is unavailable:

```python
from sentinelseed import SentinelConfig

# Maximum security: block if L4 fails
config = SentinelConfig(gate4_fallback="BLOCK")

# Balanced: allow if L2 passed (default)
config = SentinelConfig(gate4_fallback="ALLOW_IF_L2_PASSED")

# Maximum usability: always allow
config = SentinelConfig(gate4_fallback="ALLOW")
```

### Using SentinelValidator

For production use, consider the unified SentinelValidator:

```python
from sentinelseed import SentinelValidator, SentinelConfig

config = SentinelConfig(
    gate4_enabled=True,
    gate4_model="gpt-4o-mini",
    gate4_api_key="sk-...",
)

validator = SentinelValidator(config)

# Pre-AI validation (Gate 1 only)
result = validator.validate_input("user message")

# Post-AI validation (Gates 1, 2, and 4)
result = validator.validate_dialogue(
    input="user message",
    output="AI response",
)
```

## Deprecated APIs

The following APIs emit `DeprecationWarning` and will be removed in v3.0.0:

### THSValidator (3 gates)

**Deprecated:** `THSValidator` only validates 3 gates (Truth, Harm, Scope).

**Replace with:** `THSPValidator` (4 gates) or `LayeredValidator` (recommended).

```python
# Before (deprecated)
from sentinelseed.validators import THSValidator
validator = THSValidator()
result = validator.validate("content")

# After (recommended)
from sentinelseed.validation import LayeredValidator
validator = LayeredValidator()
result = validator.validate("content")

# Or with full configuration
from sentinelseed.validation import LayeredValidator, ValidationConfig
config = ValidationConfig(
    use_heuristic=True,
    use_semantic=True,
    semantic_api_key="your-key",
)
validator = LayeredValidator(config=config)
```

### JailbreakGate

**Deprecated:** `JailbreakGate` functionality moved to Truth and Scope gates.

**Replace with:** Use `ScopeGate` directly or `THSPValidator`/`LayeredValidator`.

```python
# Before (deprecated)
from sentinelseed.validators import JailbreakGate
gate = JailbreakGate()
result = gate.validate("ignore previous instructions")

# After (recommended)
from sentinelseed.validation import LayeredValidator
validator = LayeredValidator()
result = validator.validate("ignore previous instructions")
# Jailbreak patterns are detected by Scope gate
```

### Direct Gate Imports from Package Root

**Deprecated:** Importing gates directly from `sentinelseed`.

```python
# Before (deprecated)
from sentinelseed import TruthGate, HarmGate, ScopeGate

# After (recommended)
from sentinelseed.validators.gates import TruthGate, HarmGate, ScopeGate

# Or use the high-level API (recommended)
from sentinelseed import Sentinel
sentinel = Sentinel()
is_safe, violations = sentinel.validate("content")
```

## New Recommended Patterns

### Using LayeredValidator

`LayeredValidator` is the central orchestrator that combines heuristic and semantic validation:

```python
from sentinelseed.validation import LayeredValidator, ValidationConfig

# Minimal configuration (heuristic only)
validator = LayeredValidator()

# Production configuration (heuristic + semantic)
config = ValidationConfig(
    use_heuristic=True,           # Always enabled
    use_semantic=True,            # Enable for higher accuracy
    semantic_provider="openai",   # or "anthropic"
    semantic_model="gpt-4o-mini", # Cost-effective default
    semantic_api_key="sk-...",
)
validator = LayeredValidator(config=config)

# Generic validation
result = validator.validate("content to check")
print(f"Safe: {result.is_safe}")
print(f"Layer: {result.layer}")  # "heuristic", "semantic", or "both"
print(f"Violations: {result.violations}")

# Input validation (before sending to AI)
input_result = validator.validate_input(user_input)
if input_result.is_attack:
    print(f"Attack detected: {input_result.attack_types}")

# Output validation (after receiving from AI)
output_result = validator.validate_output(ai_response, user_input)
if output_result.seed_failed:
    print(f"Seed failed: {output_result.gates_failed}")
```

### Using Sentinel Class

For simple use cases, the `Sentinel` class provides a unified interface:

```python
from sentinelseed import Sentinel

# Create with configuration
sentinel = Sentinel(
    seed_level="standard",
    api_key="sk-...",      # Optional: enables semantic validation
    use_semantic=True,     # Auto-enabled when api_key provided
)

# Get alignment seed
seed = sentinel.get_seed()

# Validate content
is_safe, violations = sentinel.validate("content")

# Validate action
is_safe, concerns = sentinel.validate_action("robot task")

# Full result object
result = sentinel.get_validation_result("content")
print(f"Risk level: {result.risk_level}")
```

## Integration Migration

### Custom Integration Pattern

If you have a custom integration, migrate it to inherit from `SentinelIntegration`:

```python
# Before (direct validator usage)
from sentinelseed.validation import LayeredValidator

class MyIntegration:
    def __init__(self):
        self._validator = LayeredValidator()

    def process(self, content):
        result = self._validator.validate(content)
        ...

# After (inherit from base class)
from sentinelseed.integrations._base import SentinelIntegration, ValidationConfig

class MyIntegration(SentinelIntegration):
    _integration_name = "my_integration"

    def __init__(self, api_key: str = None):
        config = ValidationConfig(
            use_heuristic=True,
            use_semantic=bool(api_key),
            semantic_api_key=api_key,
        )
        super().__init__(validation_config=config)

    def process(self, user_input):
        # Validate input
        input_result = self.validate_input(user_input)
        if not input_result.is_safe:
            raise ValueError(f"Attack: {input_result.attack_types}")

        # Process with AI
        response = self.call_ai(user_input)

        # Validate output
        output_result = self.validate_output(response, user_input)
        if not output_result.is_safe:
            raise ValueError(f"Seed failed: {output_result.gates_failed}")

        return response
```

### Benefits of SentinelIntegration

1. **Consistent API**: All integrations use the same validation interface
2. **Automatic configuration**: Validation config handled by base class
3. **Statistics tracking**: Built-in validation statistics
4. **Future compatibility**: Automatically receives base class improvements

## Configuration Changes

### ValidationConfig Options

```python
from sentinelseed.validation import ValidationConfig

config = ValidationConfig(
    # Heuristic layer (fast, free)
    use_heuristic=True,              # Default: True

    # Semantic layer (LLM-based, accurate)
    use_semantic=True,               # Default: False
    semantic_provider="openai",      # "openai" or "anthropic"
    semantic_model="gpt-4o-mini",    # Model for semantic validation
    semantic_api_key="sk-...",       # API key for semantic provider

    # Optimization
    skip_semantic_if_heuristic_blocks=True,  # Skip LLM if heuristic blocks

    # Limits
    max_text_size=50 * 1024,         # Maximum text size (50KB)
    validation_timeout=30.0,         # Timeout in seconds

    # Safety
    fail_closed=True,                # Block on validation errors
)
```

### Environment Variables

Set API keys via environment variables:

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
```

The `Sentinel` class and `LayeredValidator` automatically detect these.

## Version Compatibility

| Old API | New API | Removal Version |
|---------|---------|-----------------|
| `THSValidator` | `THSPValidator` or `LayeredValidator` | v3.0.0 |
| `JailbreakGate` | Scope gate (in THSPValidator) | v3.0.0 |
| `from sentinelseed import TruthGate` | `from sentinelseed.validators.gates import TruthGate` | v3.0.0 |

## Getting Help

If you encounter migration issues:

1. Check the [ARCHITECTURE.md](ARCHITECTURE.md) for system design details
2. Review the [CHANGELOG.md](../CHANGELOG.md) for version history
3. Open an issue at [GitHub Issues](https://github.com/sentinel-seed/sentinel/issues)
