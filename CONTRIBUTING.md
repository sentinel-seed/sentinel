# Contributing to Sentinel AI

Thank you for your interest in contributing to Sentinel AI! This project aims to make AI safety accessible to all developers.

## How to Contribute

### Reporting Issues

- Check existing issues before creating a new one
- Include reproduction steps, expected vs actual behavior
- For security vulnerabilities, please email directly instead of opening a public issue

### Pull Requests

1. **Fork** the repository
2. **Create a branch** for your feature (`git checkout -b feature/amazing-feature`)
3. **Make your changes** with clear, concise commits
4. **Add tests** if applicable
5. **Run tests** (`pytest tests/ -v`)
6. **Submit a PR** with a clear description

### Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/sentinel.git
cd sentinel

# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

### Code Style

- Follow PEP 8
- Use type hints where possible
- Write docstrings for public functions
- Keep functions focused and small

### Areas We Need Help

- **Benchmarking**: Run Sentinel on new safety benchmarks
- **Integrations**: Add support for more LLM frameworks
- **Documentation**: Improve examples and guides
- **Testing**: Expand test coverage
- **Translations**: Help translate documentation

## Seed Development

If you want to contribute to the alignment seeds:

1. **Test thoroughly** - Run against multiple benchmarks
2. **Document changes** - Explain what you changed and why
3. **Measure impact** - Include before/after metrics
4. **Consider edge cases** - Think about false refusals

## Community Guidelines

- Be respectful and constructive
- Focus on the technical merits
- Welcome newcomers
- Give credit where due

## Questions?

Open a Discussion on GitHub or reach out to maintainers.

---

*"The best safety is the kind you don't have to think about."*
