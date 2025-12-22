# Sentinel Releases

> Changelog and release notes for Sentinel alignment seeds.

---

## Current Version

**[v2.0](v2.0.md)** (December 2025)
- THSP Protocol (4 gates with PURPOSE)
- 97.6% average safety across 6 models
- Teleological Core: actions must serve legitimate purposes

---

## All Releases

| Version | Date | Protocol | Avg Safety | Status |
|---------|------|----------|------------|--------|
| [v2.0](v2.0.md) | Dec 2025 | THSP (4 gates) | **97.6%** | **Current** |
| [v1.0](v1.0.md) | Nov 2025 | THS (3 gates) | ~85% | Legacy |

---

## Version Naming

- **Major versions** (v1, v2): Significant protocol changes
- **Seed variants**: minimal, standard, full (token size)

```
seeds/
├── v1/           # Legacy - THS protocol
│   ├── minimal/
│   ├── standard/
│   └── full/
└── v2/           # Current - THSP protocol
    ├── minimal/
    ├── standard/  ← Recommended
    └── full/
```

---

## Migration Guide

### v1 → v2

```python
# Before (v1)
seed = load_seed("v1/standard")

# After (v2)
seed = load_seed("v2/standard")
```

v1 seeds remain available for backward compatibility but are no longer recommended for new deployments.
