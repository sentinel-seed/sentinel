package dev.sentinelseed.jetbrains.services

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.Service
import com.intellij.openapi.diagnostic.Logger
import dev.sentinelseed.jetbrains.util.SecurityPatterns
import dev.sentinelseed.jetbrains.util.SecurityPatterns.Severity

/**
 * Result of a secret scan operation.
 */
data class SecretScanResult(
    val hasSecrets: Boolean,
    val findings: List<SecretFinding>,
    val severity: Severity
)

data class SecretFinding(
    val id: String,
    val description: String,
    val matchedText: String,
    val severity: Severity,
    val position: IntRange
)

/**
 * Result of an SQL injection scan operation.
 */
data class SqlScanResult(
    val hasSqlInjection: Boolean,
    val findings: List<SqlFinding>,
    val severity: Severity
)

data class SqlFinding(
    val id: String,
    val category: SecurityPatterns.SqlCategory,
    val description: String,
    val matchedText: String,
    val severity: Severity,
    val position: IntRange
)

/**
 * Result of a prompt injection scan operation.
 */
data class PromptScanResult(
    val hasInjection: Boolean,
    val findings: List<PromptFinding>,
    val severity: Severity
)

data class PromptFinding(
    val id: String,
    val description: String,
    val matchedText: String,
    val severity: Severity,
    val gates: List<String>,
    val position: IntRange
)

/**
 * Result of an output validation operation.
 */
data class OutputValidationResult(
    val hasIssues: Boolean,
    val findings: List<OutputFinding>,
    val severity: Severity
)

data class OutputFinding(
    val id: String,
    val description: String,
    val matchedText: String,
    val severity: Severity,
    val position: IntRange
)

/**
 * Security scanning service for detecting secrets, SQL injection, and prompt injection.
 * Implements the same logic as the VS Code extension.
 *
 * Privacy guarantees:
 * - All scans run 100% locally
 * - No data sent to external servers
 * - Pattern-based heuristic detection
 */
@Service(Service.Level.APP)
class SecurityService {
    private val logger = Logger.getInstance(SecurityService::class.java)

    companion object {
        fun getInstance(): SecurityService =
            ApplicationManager.getApplication().getService(SecurityService::class.java)
    }

    // =========================================================================
    // SECRET SCANNING
    // =========================================================================

    /**
     * Scans content for secrets (API keys, tokens, credentials, PII).
     * Uses OWASP LLM02 (Sensitive Information Disclosure) patterns.
     */
    fun scanSecrets(content: String): SecretScanResult {
        if (content.isBlank()) {
            return SecretScanResult(
                hasSecrets = false,
                findings = emptyList(),
                severity = Severity.LOW
            )
        }

        val findings = mutableListOf<SecretFinding>()

        for (pattern in SecurityPatterns.SECRET_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    SecretFinding(
                        id = pattern.id,
                        description = pattern.description,
                        matchedText = maskSensitiveValue(match.value),
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Deduplicate overlapping findings
        val deduped = deduplicateFindings(findings) { it.position }

        return SecretScanResult(
            hasSecrets = deduped.isNotEmpty(),
            findings = deduped,
            severity = calculateSeverity(deduped.map { it.severity })
        )
    }

    /**
     * Quick check for secrets without detailed findings.
     */
    fun hasSecrets(content: String): Boolean {
        return SecurityPatterns.SECRET_PATTERNS.any { pattern ->
            pattern.regex.containsMatchIn(content)
        }
    }

    // =========================================================================
    // SQL INJECTION SCANNING
    // =========================================================================

    /**
     * Scans content for SQL injection patterns.
     * Detects destructive queries, UNION attacks, auth bypass, etc.
     */
    fun scanSqlInjection(content: String): SqlScanResult {
        if (content.isBlank()) {
            return SqlScanResult(
                hasSqlInjection = false,
                findings = emptyList(),
                severity = Severity.LOW
            )
        }

        val findings = mutableListOf<SqlFinding>()

        for (pattern in SecurityPatterns.SQL_INJECTION_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    SqlFinding(
                        id = pattern.id,
                        category = pattern.category,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Deduplicate overlapping findings
        val deduped = deduplicateFindings(findings) { it.position }

        return SqlScanResult(
            hasSqlInjection = deduped.isNotEmpty(),
            findings = deduped,
            severity = calculateSeverity(deduped.map { it.severity })
        )
    }

    /**
     * Quick check for SQL injection without detailed findings.
     */
    fun hasSqlInjection(content: String): Boolean {
        return SecurityPatterns.SQL_INJECTION_PATTERNS.any { pattern ->
            pattern.regex.containsMatchIn(content)
        }
    }

    /**
     * Gets SQL injection findings grouped by category.
     */
    fun scanSqlByCategory(content: String): Map<SecurityPatterns.SqlCategory, List<SqlFinding>> {
        val result = scanSqlInjection(content)
        return result.findings.groupBy { it.category }
    }

    // =========================================================================
    // PROMPT INJECTION SCANNING
    // =========================================================================

    /**
     * Scans content for prompt injection patterns.
     * Uses OWASP LLM01 (Prompt Injection) patterns.
     */
    fun scanPromptInjection(content: String): PromptScanResult {
        if (content.isBlank()) {
            return PromptScanResult(
                hasInjection = false,
                findings = emptyList(),
                severity = Severity.LOW
            )
        }

        val findings = mutableListOf<PromptFinding>()

        for (pattern in SecurityPatterns.PROMPT_INJECTION_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    PromptFinding(
                        id = pattern.id,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        gates = pattern.gates,
                        position = match.range
                    )
                )
            }
        }

        // Deduplicate overlapping findings
        val deduped = deduplicateFindings(findings) { it.position }

        return PromptScanResult(
            hasInjection = deduped.isNotEmpty(),
            findings = deduped,
            severity = calculateSeverity(deduped.map { it.severity })
        )
    }

    /**
     * Quick check for prompt injection without detailed findings.
     */
    fun hasPromptInjection(content: String): Boolean {
        return SecurityPatterns.PROMPT_INJECTION_PATTERNS.any { pattern ->
            pattern.regex.containsMatchIn(content)
        }
    }

    // =========================================================================
    // OUTPUT VALIDATION
    // =========================================================================

    /**
     * Validates LLM output for security issues.
     * Checks for sensitive data exposure, injection payloads, and unsafe content.
     */
    fun validateOutput(content: String): OutputValidationResult {
        if (content.isBlank()) {
            return OutputValidationResult(
                hasIssues = false,
                findings = emptyList(),
                severity = Severity.LOW
            )
        }

        val findings = mutableListOf<OutputFinding>()

        // Check output validation patterns
        for (pattern in SecurityPatterns.OUTPUT_VALIDATION_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    OutputFinding(
                        id = pattern.id,
                        description = pattern.description,
                        matchedText = match.value,
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Also check for sensitive info in output
        for (pattern in SecurityPatterns.SECRET_PATTERNS) {
            val matches = pattern.regex.findAll(content)
            for (match in matches) {
                findings.add(
                    OutputFinding(
                        id = "output_${pattern.id}",
                        description = "Output contains: ${pattern.description}",
                        matchedText = maskSensitiveValue(match.value),
                        severity = pattern.severity,
                        position = match.range
                    )
                )
            }
        }

        // Deduplicate overlapping findings
        val deduped = deduplicateFindings(findings) { it.position }

        return OutputValidationResult(
            hasIssues = deduped.isNotEmpty(),
            findings = deduped,
            severity = calculateSeverity(deduped.map { it.severity })
        )
    }

    /**
     * Quick check for output issues without detailed findings.
     */
    fun hasOutputIssues(content: String): Boolean {
        return SecurityPatterns.OUTPUT_VALIDATION_PATTERNS.any { pattern ->
            pattern.regex.containsMatchIn(content)
        } || hasSecrets(content)
    }

    // =========================================================================
    // HELPER METHODS
    // =========================================================================

    /**
     * Masks sensitive values for display (shows first/last chars only).
     */
    private fun maskSensitiveValue(value: String): String {
        return when {
            value.length <= 8 -> "****"
            value.length <= 16 -> "${value.take(2)}****${value.takeLast(2)}"
            else -> "${value.take(4)}...${value.takeLast(4)}"
        }
    }

    /**
     * Deduplicates findings by position, keeping higher severity.
     */
    private fun <T> deduplicateFindings(
        findings: List<T>,
        positionSelector: (T) -> IntRange
    ): List<T> where T : Any {
        if (findings.isEmpty()) return emptyList()

        // Sort by start position
        val sorted = findings.sortedBy { positionSelector(it).first }
        val result = mutableListOf<T>()
        var lastEnd = -1

        for (finding in sorted) {
            val position = positionSelector(finding)
            if (position.first >= lastEnd) {
                result.add(finding)
                lastEnd = position.last
            }
        }

        return result
    }

    /**
     * Calculates overall severity from a list of severities.
     */
    private fun calculateSeverity(severities: List<Severity>): Severity {
        if (severities.isEmpty()) return Severity.LOW

        return when {
            severities.any { it == Severity.CRITICAL } -> Severity.CRITICAL
            severities.any { it == Severity.HIGH } -> Severity.HIGH
            severities.any { it == Severity.MEDIUM } -> Severity.MEDIUM
            else -> Severity.LOW
        }
    }
}
