# Sentinel API Reference

Complete API documentation for Sentinel AI Safety Toolkit.

## Documentation Index

| Document | Description |
|----------|-------------|
| [Python SDK](python-sdk.md) | Complete Python API reference |
| [REST API](rest-api.md) | HTTP REST API reference |
| [JavaScript SDK](javascript-sdk.md) | TypeScript/JavaScript API reference |

## Quick Links by Use Case

### Basic Validation

```python
from sentinelseed import Sentinel

sentinel = Sentinel()
is_safe, violations = sentinel.validate("content to check")
```

**Full docs:** [Python SDK - Sentinel Class](python-sdk.md#sentinel-class)

### Advanced Validation

```python
from sentinelseed import LayeredValidator, ValidationConfig

validator = LayeredValidator(
    config=ValidationConfig(
        use_semantic=True,
        semantic_api_key="sk-...",
    )
)
result = validator.validate("content")
```

**Full docs:** [Python SDK - LayeredValidator](python-sdk.md#layeredvalidator)

### Memory Integrity (Agents)

```python
from sentinelseed import MemoryIntegrityChecker

checker = MemoryIntegrityChecker(secret_key="your-secret")
signed = checker.sign_entry({"content": "data"})
```

**Full docs:** [Python SDK - Memory Module](python-sdk.md#memory-integrity)

### Fiduciary AI

```python
from sentinelseed import FiduciaryValidator, UserContext

validator = FiduciaryValidator()
result = validator.validate_action("action", UserContext(risk_tolerance="low"))
```

**Full docs:** [Python SDK - Fiduciary Module](python-sdk.md#fiduciary-ai)

### Database Guard

```python
from sentinelseed import DatabaseGuard

guard = DatabaseGuard(max_rows_per_query=1000)
result = guard.validate("SELECT * FROM users")
```

**Full docs:** [Python SDK - Database Module](python-sdk.md#database-guard)

### Compliance Checking

```python
from sentinelseed.compliance import EUAIActComplianceChecker

checker = EUAIActComplianceChecker(api_key="...")
result = checker.check_compliance(content, context="healthcare")
```

**Full docs:** [Python SDK - Compliance Module](python-sdk.md#compliance)

### REST API

```bash
curl -X POST https://api.sentinelseed.dev/validate \
  -H "Content-Type: application/json" \
  -d '{"text": "content to check"}'
```

**Full docs:** [REST API Reference](rest-api.md)

## Version Compatibility

| Sentinel Version | Python | Node.js |
|------------------|--------|---------|
| 2.23.x - 2.24.x | 3.10+ | 18+ |
| 2.19.x - 2.22.x | 3.10+ | 18+ |
| 2.16.x - 2.18.x | 3.9+ | 18+ |

## Related Documentation

- [Architecture Overview](../ARCHITECTURE.md)
- [Migration Guide](../MIGRATION.md)
- [Contributing](../CONTRIBUTING.md)

## Support

- **GitHub Issues:** https://github.com/sentinel-seed/sentinel/issues
- **Website:** https://sentinelseed.dev
