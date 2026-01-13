# Contributing to Sentinel

Thank you for your interest in contributing to Sentinel! This project aims to make AI safety accessible to all developers.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)
- [Pull Requests](#pull-requests)
- [Documentation](#documentation)
- [Integration Development](#integration-development)
- [Areas We Need Help](#areas-we-need-help)
- [Release Process](#release-process)

---

## Code of Conduct

- Be respectful and constructive
- Focus on technical merits
- Welcome newcomers
- Give credit where due
- For security vulnerabilities, email directly instead of opening public issues

---

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+ (for JavaScript packages)
- Git

### Quick Start

```bash
# Clone the repository
git clone https://github.com/sentinel-seed/sentinel.git
cd sentinel

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install in development mode with all dependencies
pip install -e ".[dev,all]"

# Run tests to verify setup
pytest tests/ -v --tb=short
```

---

## Development Setup

### Full Development Environment

```bash
# Install all development dependencies
pip install -e ".[dev,all]"

# Install pre-commit hooks (optional but recommended)
pip install pre-commit
pre-commit install

# Install TypeScript dependencies (for JS packages)
cd packages/core
npm install
cd ../..
```

### Environment Variables

Create a `.env` file for testing with LLM providers:

```bash
# Optional - for semantic validation tests
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional - for integration tests
SENTINEL_TEST_MODE=true
```

### IDE Setup

**VS Code** (recommended):
```json
// .vscode/settings.json
{
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "python.testing.pytestEnabled": true
}
```

**PyCharm**:
- Enable pytest as test runner
- Set Python interpreter to virtual environment
- Enable Black formatter

---

## Project Structure

```
sentinel/
├── src/sentinelseed/           # Main Python package
│   ├── core/                   # Core module (Sentinel, interfaces)
│   ├── validation/             # LayeredValidator, THSPValidator
│   ├── validators/             # Gate implementations
│   ├── integrations/           # 25+ framework integrations
│   │   ├── langchain/          # Each integration has:
│   │   │   ├── __init__.py     #   - Main implementation
│   │   │   └── README.md       #   - Full documentation
│   │   └── ...
│   ├── safety/                 # Safety modules
│   │   ├── base.py             # Base validators
│   │   ├── humanoid/           # ISO/TS 15066 humanoid safety
│   │   ├── mobile/             # Mobile robot safety
│   │   └── simulation/         # Simulation constraints
│   ├── compliance/             # Regulatory compliance
│   ├── memory/                 # Memory integrity
│   ├── fiduciary/              # Fiduciary AI
│   └── database/               # Database guard
├── tests/                      # Test suite
├── packages/                   # JavaScript/TypeScript packages
│   ├── core/                   # @anthropic/sentinel-core
│   ├── vscode/                 # VS Code extension
│   └── ...
├── api/                        # REST API
├── docs/                       # Documentation
└── seeds/                      # Alignment seed files
```

---

## Making Changes

### Workflow

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a branch** for your feature
4. **Make changes** with clear, focused commits
5. **Write tests** for new functionality
6. **Run the test suite** to ensure nothing breaks
7. **Push** to your fork
8. **Submit a PR** with a clear description

### Branch Naming

```
feature/add-new-integration     # New features
fix/validation-timeout          # Bug fixes
docs/api-reference              # Documentation
test/improve-coverage           # Test improvements
refactor/cleanup-validators     # Refactoring
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_validation.py -v

# Run with coverage
pytest tests/ -v --cov=sentinelseed --cov-report=html

# Run only fast tests (no API calls)
pytest tests/ -v -m "not slow"

# Run integration tests
pytest tests/ -v -m integration
```

### Test Structure

```
tests/
├── test_core.py                # Core module tests
├── test_validation.py          # Validator tests
├── test_integrations/          # Integration-specific tests
│   ├── test_langchain.py
│   └── ...
├── test_safety_*.py            # Safety module tests
└── conftest.py                 # Shared fixtures
```

### Writing Tests

```python
import pytest
from sentinelseed import LayeredValidator

class TestLayeredValidator:
    """Tests for LayeredValidator."""

    def test_validate_safe_content(self):
        """Safe content should pass validation."""
        validator = LayeredValidator()
        result = validator.validate("Hello, how can I help?")

        assert result.is_safe
        assert len(result.violations) == 0

    def test_validate_harmful_content(self):
        """Harmful content should be blocked."""
        validator = LayeredValidator()
        result = validator.validate("How to hack a computer")

        assert not result.is_safe
        assert len(result.violations) > 0

    @pytest.mark.slow
    def test_validate_with_semantic(self, api_key):
        """Test with semantic validation (requires API key)."""
        # Skip if no API key
        if not api_key:
            pytest.skip("No API key available")

        validator = LayeredValidator(
            semantic_api_key=api_key,
            use_semantic=True,
        )
        result = validator.validate("Complex edge case")
        assert result.layer.value in ["heuristic", "semantic", "both"]
```

### Test Coverage Requirements

- **Core modules**: 90%+ coverage
- **Integrations**: 80%+ coverage
- **New features**: Must include tests

---

## Code Style

### Python Style Guide

Follow PEP 8 with these additions:

```python
# Good: Type hints for public functions
def validate(content: str, context: Optional[Dict[str, Any]] = None) -> ValidationResult:
    """
    Validate content through THSP gates.

    Args:
        content: Text content to validate.
        context: Optional validation context.

    Returns:
        ValidationResult with safety assessment.

    Raises:
        ValidationError: If validation fails unexpectedly.
    """
    pass

# Good: Descriptive variable names
max_retry_attempts = 3
validation_timeout_seconds = 30.0

# Avoid: Single letter variables (except in loops)
# Avoid: Abbreviations that aren't obvious
```

### Docstrings

Use Google-style docstrings:

```python
def process_action(
    action_name: str,
    action_args: Dict[str, Any],
    purpose: str = "",
) -> ValidationResult:
    """
    Process and validate an action before execution.

    This method validates the action through THSP gates and checks
    for potential safety issues.

    Args:
        action_name: Name of the action to execute.
        action_args: Dictionary of action arguments.
        purpose: Stated purpose for the action (optional).

    Returns:
        ValidationResult containing:
        - is_safe: Whether action is safe to execute
        - violations: List of any safety violations
        - risk_level: Assessed risk level

    Raises:
        ValueError: If action_name is empty.
        ValidationError: If validation fails.

    Example:
        >>> result = process_action("delete_file", {"path": "/tmp/cache"})
        >>> if result.is_safe:
        ...     execute_action()
    """
    pass
```

### Formatting

Use Black for formatting:

```bash
# Format all Python files
black src/ tests/

# Check formatting without changing files
black --check src/ tests/
```

### Linting

Use flake8 for linting:

```bash
# Run linter
flake8 src/ tests/

# With common ignores
flake8 --ignore=E501,W503 src/ tests/
```

---

## Commit Messages

Use conventional commits:

```
type(scope): description

[optional body]

[optional footer]
```

### Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `style` | Formatting, no code change |
| `refactor` | Code refactoring |
| `test` | Adding or updating tests |
| `chore` | Maintenance tasks |

### Examples

```bash
# Feature
feat(validation): add rate limiting to semantic validator

# Bug fix
fix(langchain): handle empty response from callback

# Documentation
docs(api): add REST API reference

# Refactor
refactor(core): simplify ValidationResult factory methods
```

---

## Pull Requests

### PR Checklist

Before submitting:

- [ ] Code follows style guidelines
- [ ] Tests added for new functionality
- [ ] All tests pass locally
- [ ] Documentation updated if needed
- [ ] Commit messages follow conventions
- [ ] Branch is up-to-date with main

### PR Template

```markdown
## Summary
Brief description of changes.

## Changes
- Added X
- Fixed Y
- Updated Z

## Testing
How was this tested?

## Related Issues
Fixes #123
```

### Review Process

1. **Automated checks** run on PR creation
2. **Maintainer review** within 3-5 days
3. **Address feedback** if requested
4. **Merge** once approved

---

## Documentation

### Where to Document

| Content | Location |
|---------|----------|
| API Reference | `docs/api/` |
| Architecture | `docs/ARCHITECTURE.md` |
| Integration docs | `src/sentinelseed/integrations/{name}/README.md` |
| Compliance | `docs/*_MAPPING.md` |

### Documentation Style

- Use clear, concise language
- Include code examples
- Keep examples runnable
- Update when code changes

---

## Integration Development

### Creating a New Integration

1. **Create directory**: `src/sentinelseed/integrations/{name}/`

2. **Implement integration**:

```python
# src/sentinelseed/integrations/myframework/__init__.py
"""
MyFramework Integration for Sentinel.

Provides safety validation for MyFramework applications.
"""

from sentinelseed.integrations._base import SentinelIntegration

class MyFrameworkGuard(SentinelIntegration):
    """Safety guard for MyFramework."""

    _integration_name = "myframework"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def process(self, content: str):
        result = self.validate(content)
        if not result.is_safe:
            raise ValueError(f"Blocked: {result.violations}")
        return content
```

3. **Add README.md** with full documentation (see existing integrations)

4. **Add tests**: `tests/test_integrations/test_myframework.py`

5. **Update setup.py** with optional dependency:

```python
extras_require={
    "myframework": ["myframework>=1.0"],
}
```

### Integration Checklist

- [ ] Inherits from `SentinelIntegration` (if text-based)
- [ ] Has comprehensive README.md (300+ lines)
- [ ] Has test coverage (80%+)
- [ ] Follows existing patterns
- [ ] Documents all public APIs

---

## Areas We Need Help

### High Priority

**Robotics & Embodied AI**
- ROS2 integration improvements
- Isaac Lab testing on real robots
- PyBullet safety layer
- Physical robot validation

**Benchmarking**
- Run on new safety benchmarks
- Test on Gemini, Mistral-Large
- Extend SafeAgentBench coverage

### Medium Priority

**Framework Integrations**
- AutoGen support
- Semantic Kernel integration
- Multi-agent coordination

**Documentation**
- More examples for robotics
- Video tutorials
- Interactive playground

### Low Priority

**Performance**
- Optimize pattern matching
- Reduce memory footprint
- Benchmark latency

---

## Release Process

### Version Numbering

Sentinel uses semantic versioning: `MAJOR.MINOR.PATCH`

- **MAJOR**: Breaking API changes
- **MINOR**: New features, backwards compatible
- **PATCH**: Bug fixes, backwards compatible

### Release Checklist

1. Update version in `src/sentinelseed/__init__.py`
2. Update CHANGELOG.md
3. Run full test suite
4. Create release tag
5. Build and publish to PyPI

---

## Questions?

- **GitHub Discussions**: For general questions
- **GitHub Issues**: For bugs and feature requests
- **Security Issues**: Email maintainers directly

---

*"Text is risk. Action is danger. Sentinel watches both."*
