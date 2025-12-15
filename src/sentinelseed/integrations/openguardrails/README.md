# Sentinel OpenGuardrails Integration

> Bidirectional integration between Sentinel and OpenGuardrails framework

## Overview

This integration provides two-way compatibility:
1. **Use OpenGuardrails as backend** — Leverage OpenGuardrails scanners from Sentinel
2. **Register Sentinel as scanner** — Add THSP gates to OpenGuardrails pipeline

## Installation

```bash
pip install sentinelseed
# OpenGuardrails is optional - install separately if needed
pip install openguardrails
```

## Quick Start

### Use OpenGuardrails as Backend

```python
from sentinelseed.integrations.openguardrails import OpenGuardrailsValidator

validator = OpenGuardrailsValidator()

result = validator.validate("Check this content for safety")
print(f"Safe: {result.safe}")
print(f"Detections: {result.detections}")
```

### Register Sentinel as Scanner

```python
from sentinelseed.integrations.openguardrails import SentinelOpenGuardrailsScanner

scanner = SentinelOpenGuardrailsScanner()

# Register THSP gates as OpenGuardrails scanners
scanner.register()
# Registers: S100 (Truth), S101 (Harm), S102 (Scope), S103 (Purpose)

# Now use in OpenGuardrails pipeline
# openguardrails scan --scanners S100,S101,S102,S103 "content"
```

### Combined Pipeline

```python
from sentinelseed.integrations.openguardrails import SentinelGuardrailsWrapper

wrapper = SentinelGuardrailsWrapper()

# Use both Sentinel and OpenGuardrails scanners
result = wrapper.validate(
    content="Some content to validate",
    scanners=["S100", "S101", "G001", "G002"]  # Mix of Sentinel + OpenGuardrails
)

print(f"Sentinel result: {result['sentinel']}")
print(f"OpenGuardrails result: {result['openguardrails']}")
print(f"Combined safe: {result['combined_safe']}")
```

## Scanner Tags

When registered, Sentinel adds these scanners to OpenGuardrails:

| Tag | Gate | Description |
|-----|------|-------------|
| `S100` | Truth | Detects deception, misinformation, fake content |
| `S101` | Harm | Detects harmful content (violence, weapons, etc.) |
| `S102` | Scope | Detects jailbreaks, prompt injection, persona manipulation |
| `S103` | Purpose | Detects purposeless or wasteful actions |

## API Reference

### OpenGuardrailsValidator

```python
class OpenGuardrailsValidator:
    def __init__(self, config: Optional[Dict] = None):
        """Initialize with optional OpenGuardrails config."""

    def validate(self, content: str, scanners: Optional[List[str]] = None) -> DetectionResult:
        """Validate content using OpenGuardrails scanners."""
```

### SentinelOpenGuardrailsScanner

```python
class SentinelOpenGuardrailsScanner:
    def __init__(self, seed_level: str = "standard"):
        """Initialize with Sentinel seed level."""

    def register(self) -> str:
        """Register Sentinel as OpenGuardrails scanner. Returns scanner tag prefix."""

    def unregister(self) -> bool:
        """Remove Sentinel from OpenGuardrails registry."""
```

### SentinelGuardrailsWrapper

```python
class SentinelGuardrailsWrapper:
    def __init__(self, seed_level: str = "standard", og_config: Optional[Dict] = None):
        """Initialize combined wrapper."""

    def validate(self, content: str, scanners: Optional[List[str]] = None) -> Dict:
        """Validate with both Sentinel and OpenGuardrails."""
```

## Related

- [OpenGuardrails](https://github.com/openguardrails/openguardrails)
- [Sentinel Documentation](https://sentinelseed.dev/docs)
- [THSP Protocol](https://sentinelseed.dev/docs/methodology)

## License

MIT
