# Contributing to Sentinel AI Safety JetBrains Plugin

Thank you for your interest in contributing to Sentinel! This document provides guidelines for contributing to the JetBrains plugin.

## Development Setup

### Prerequisites

- JDK 17 or higher
- Gradle 8.13 or higher
- IntelliJ IDEA (recommended for plugin development)
- Git

### Getting Started

1. Fork and clone the repository:
   ```bash
   git clone https://github.com/sentinel-seed/sentinel.git
   cd sentinel/packages/jetbrains
   ```

2. Build the project:
   ```bash
   ./gradlew buildPlugin
   ```

3. Run tests:
   ```bash
   ./gradlew test
   ```

4. Run the plugin in development mode:
   ```bash
   ./gradlew runIde
   ```

## Project Structure

```
src/
├── main/
│   ├── kotlin/dev/sentinelseed/jetbrains/
│   │   ├── actions/       # User-triggered actions
│   │   ├── compliance/    # Compliance patterns (EU AI Act, CSA)
│   │   ├── services/      # Core business logic
│   │   ├── settings/      # Plugin settings and configuration
│   │   ├── toolWindow/    # Tool window UI components
│   │   ├── ui/            # General UI components
│   │   └── util/          # Utilities (patterns, logging, i18n)
│   └── resources/
│       ├── messages/      # i18n bundles
│       ├── icons/         # Plugin icons
│       └── META-INF/      # Plugin manifest
└── test/
    └── kotlin/            # Unit tests
```

## Code Style

### Kotlin Style Guide

- Follow [Kotlin Coding Conventions](https://kotlinlang.org/docs/coding-conventions.html)
- Use meaningful variable and function names
- Keep functions small and focused
- Document public APIs with KDoc comments

### Comments

- Write comments like a human developer would
- Keep comments concise and practical
- Use English for all code and comments
- Avoid over-explaining obvious things

### Example

```kotlin
/**
 * Scans content for potential secrets and credentials.
 *
 * @param content The text to scan
 * @return ScanResult containing findings and severity
 */
fun scanSecrets(content: String): ScanResult {
    if (content.isBlank()) {
        return ScanResult.empty()
    }

    // Check each pattern category
    val findings = mutableListOf<Finding>()
    for (pattern in SecurityPatterns.SECRET_PATTERNS) {
        findings.addAll(findMatches(content, pattern))
    }

    return ScanResult(findings)
}
```

## Testing

### Running Tests

```bash
# Run all tests
./gradlew test

# Run specific test class
./gradlew test --tests "SecurityPatternsTest"

# Run with verbose output
./gradlew test --info
```

### Writing Tests

- Use JUnit 5 for test structure
- Use AssertJ for fluent assertions
- Use MockK for mocking IntelliJ Platform dependencies
- Use `@DisplayName` for readable test names
- Use `@Nested` for grouping related tests

Example:

```kotlin
@DisplayName("SecurityPatterns")
class SecurityPatternsTest {

    @Nested
    @DisplayName("Secret Patterns")
    inner class SecretPatternTests {

        @Test
        @DisplayName("Should detect OpenAI API keys")
        fun detectOpenAIKey() {
            val pattern = SecurityPatterns.SECRET_PATTERNS.find { it.id == "openai_key" }!!

            assertThat(pattern.regex.containsMatchIn("sk-1234...")).isTrue()
            assertThat(pattern.regex.containsMatchIn("not-a-key")).isFalse()
        }
    }
}
```

## Pull Request Process

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes**
   - Write code following the style guide
   - Add tests for new functionality
   - Update documentation if needed

3. **Test Locally**
   ```bash
   ./gradlew test
   ./gradlew buildPlugin
   ./gradlew verifyPlugin
   ```

4. **Commit Changes**
   - Use conventional commit messages
   - Keep commits focused and atomic

   ```bash
   git commit -m "feat: add new security pattern for AWS tokens"
   git commit -m "fix: handle empty content in compliance check"
   git commit -m "docs: update README with new features"
   ```

5. **Submit PR**
   - Fill out the PR template
   - Link related issues
   - Request review from maintainers

## Commit Messages

Use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `test`: Adding or updating tests
- `refactor`: Code refactoring
- `style`: Code style changes (formatting)
- `perf`: Performance improvements
- `chore`: Build/tooling changes

Examples:
```
feat: add SQL injection detection patterns
fix: correct regex for credit card detection
docs: add contributing guidelines
test: add compliance service tests
```

## Adding New Features

### Adding a New Security Pattern

1. Add the pattern to `SecurityPatterns.kt`:
   ```kotlin
   SecretPattern(
       id = "your_pattern_id",
       name = "Pattern Name",
       description = "What this detects",
       regex = Regex("""your-regex-here"""),
       severity = Severity.HIGH
   )
   ```

2. Add tests in `SecurityPatternsTest.kt`

3. Update documentation if needed

### Adding a New Action

1. Create action class in `actions/`:
   ```kotlin
   class YourAction : AnAction() {
       override fun actionPerformed(e: AnActionEvent) {
           // Implementation
       }
   }
   ```

2. Register in `plugin.xml`:
   ```xml
   <action id="Sentinel.YourAction"
           class="dev.sentinelseed.jetbrains.actions.YourAction"
           text="Your Action"
           description="What it does"/>
   ```

3. Add i18n strings to message bundles

4. Write tests

### Adding i18n Support

1. Add English text to `SentinelBundle.properties`:
   ```properties
   your.key=Your English text
   ```

2. Add translations to locale files (e.g., `SentinelBundle_pt_BR.properties`):
   ```properties
   your.key=Seu texto em português
   ```

3. Use in code:
   ```kotlin
   val message = SentinelBundle.message("your.key")
   ```

## Reporting Issues

When reporting bugs, please include:

1. Plugin version
2. IDE version (e.g., IntelliJ IDEA 2024.3)
3. Operating system
4. Steps to reproduce
5. Expected vs actual behavior
6. Relevant error logs (Help → Diagnostic Tools → Show Log)

## Code of Conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a professional environment

## Questions?

- Open a [GitHub Issue](https://github.com/sentinel-seed/sentinel/issues)
- Check [existing discussions](https://github.com/sentinel-seed/sentinel/discussions)

Thank you for contributing to Sentinel!
