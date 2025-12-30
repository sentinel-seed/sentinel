package dev.sentinelseed.jetbrains.actions

import dev.sentinelseed.jetbrains.compliance.CompliancePatterns
import dev.sentinelseed.jetbrains.services.*
import dev.sentinelseed.jetbrains.util.SecurityPatterns
import org.assertj.core.api.Assertions.assertThat
import org.junit.jupiter.api.DisplayName
import org.junit.jupiter.api.Nested
import org.junit.jupiter.api.Test

/**
 * Tests for Action result formatting and logic.
 * Tests the business logic that actions use without requiring IntelliJ Platform dependencies.
 */
@DisplayName("Actions")
class ActionsTest {

    /**
     * Helper that mirrors the result formatting logic used in actions.
     * This allows testing the formatting without IntelliJ dependencies.
     */
    private val formatter = ResultFormatter()

    @Nested
    @DisplayName("Secret Scan Action Formatting")
    inner class SecretScanFormattingTests {

        @Test
        @DisplayName("Should format clean result message")
        fun formatCleanResult() {
            val result = SecretScanResult(
                hasSecrets = false,
                findings = emptyList(),
                severity = SecurityPatterns.Severity.LOW
            )

            val message = formatter.formatSecretScanResult(result)

            assertThat(message).contains("No secrets detected")
            assertThat(message).doesNotContain("CRITICAL")
            assertThat(message).doesNotContain("Remove")
        }

        @Test
        @DisplayName("Should format result with findings")
        fun formatResultWithFindings() {
            val findings = listOf(
                SecretFinding(
                    id = "openai_key",
                    description = "OpenAI API key detected",
                    matchedText = "sk-1234...5678",
                    severity = SecurityPatterns.Severity.CRITICAL,
                    position = 0..20
                )
            )
            val result = SecretScanResult(
                hasSecrets = true,
                findings = findings,
                severity = SecurityPatterns.Severity.CRITICAL
            )

            val message = formatter.formatSecretScanResult(result)

            assertThat(message).contains("SECRETS DETECTED")
            assertThat(message).contains("OpenAI API key")
            assertThat(message).contains("CRITICAL")
            assertThat(message).contains("Remove or rotate")
        }

        @Test
        @DisplayName("Should mask sensitive values in output")
        fun maskSensitiveValues() {
            val findings = listOf(
                SecretFinding(
                    id = "password",
                    description = "Password detected",
                    matchedText = "pass...word", // Already masked by service
                    severity = SecurityPatterns.Severity.CRITICAL,
                    position = 0..10
                )
            )
            val result = SecretScanResult(
                hasSecrets = true,
                findings = findings,
                severity = SecurityPatterns.Severity.CRITICAL
            )

            val message = formatter.formatSecretScanResult(result)

            assertThat(message).contains("pass...word")
            assertThat(message).doesNotContain("mysecretpassword")
        }
    }

    @Nested
    @DisplayName("SQL Injection Action Formatting")
    inner class SqlInjectionFormattingTests {

        @Test
        @DisplayName("Should format clean result")
        fun formatCleanResult() {
            val result = SqlScanResult(
                hasSqlInjection = false,
                findings = emptyList(),
                severity = SecurityPatterns.Severity.LOW
            )

            val message = formatter.formatSqlScanResult(result)

            assertThat(message).contains("No SQL injection")
        }

        @Test
        @DisplayName("Should format destructive SQL findings")
        fun formatDestructiveFindings() {
            val findings = listOf(
                SqlFinding(
                    id = "drop_table",
                    category = SecurityPatterns.SqlCategory.DESTRUCTIVE,
                    description = "Destructive SQL command",
                    matchedText = "DROP TABLE users",
                    severity = SecurityPatterns.Severity.CRITICAL,
                    position = 0..16
                )
            )
            val result = SqlScanResult(
                hasSqlInjection = true,
                findings = findings,
                severity = SecurityPatterns.Severity.CRITICAL
            )

            val message = formatter.formatSqlScanResult(result)

            assertThat(message).contains("SQL INJECTION DETECTED")
            assertThat(message).contains("DESTRUCTIVE")
            assertThat(message).contains("DROP TABLE")
        }

        @Test
        @DisplayName("Should group findings by category")
        fun groupByCategory() {
            val findings = listOf(
                SqlFinding(
                    id = "drop_table",
                    category = SecurityPatterns.SqlCategory.DESTRUCTIVE,
                    description = "Destructive command",
                    matchedText = "DROP TABLE",
                    severity = SecurityPatterns.Severity.CRITICAL,
                    position = 0..10
                ),
                SqlFinding(
                    id = "union_select",
                    category = SecurityPatterns.SqlCategory.UNION_ATTACK,
                    description = "UNION attack",
                    matchedText = "UNION SELECT",
                    severity = SecurityPatterns.Severity.HIGH,
                    position = 20..32
                )
            )
            val result = SqlScanResult(
                hasSqlInjection = true,
                findings = findings,
                severity = SecurityPatterns.Severity.CRITICAL
            )

            val message = formatter.formatSqlScanResult(result)

            assertThat(message).contains("DESTRUCTIVE")
            assertThat(message).contains("UNION_ATTACK")
        }
    }

    @Nested
    @DisplayName("Prompt Injection Action Formatting")
    inner class PromptInjectionFormattingTests {

        @Test
        @DisplayName("Should format clean result")
        fun formatCleanResult() {
            val result = PromptScanResult(
                hasInjection = false,
                findings = emptyList(),
                severity = SecurityPatterns.Severity.LOW
            )

            val message = formatter.formatPromptScanResult(result)

            assertThat(message).contains("No injection patterns")
        }

        @Test
        @DisplayName("Should format injection findings with gates")
        fun formatWithGates() {
            val findings = listOf(
                PromptFinding(
                    id = "ignore_instructions",
                    description = "Instruction override attempt",
                    matchedText = "ignore previous instructions",
                    severity = SecurityPatterns.Severity.HIGH,
                    gates = listOf("scope"),
                    position = 0..28
                )
            )
            val result = PromptScanResult(
                hasInjection = true,
                findings = findings,
                severity = SecurityPatterns.Severity.HIGH
            )

            val message = formatter.formatPromptScanResult(result)

            assertThat(message).contains("INJECTION DETECTED")
            assertThat(message).contains("scope")
        }
    }

    @Nested
    @DisplayName("EU AI Act Action Formatting")
    inner class EUAIActFormattingTests {

        @Test
        @DisplayName("Should format compliant result")
        fun formatCompliantResult() {
            val result = ComplianceResult(
                framework = "EU AI Act",
                compliant = true,
                findings = emptyList(),
                riskLevel = "minimal",
                recommendations = emptyList()
            )

            val message = formatter.formatEUAIActResult(result)

            assertThat(message).contains("COMPLIANT")
            assertThat(message).contains("minimal")
        }

        @Test
        @DisplayName("Should format prohibited practice")
        fun formatProhibitedPractice() {
            val findings = listOf(
                ComplianceFinding(
                    id = "eu_social_scoring",
                    category = "Article 5(1)(c)",
                    description = "Social scoring system",
                    matchedText = "social credit system",
                    severity = CompliancePatterns.Severity.CRITICAL,
                    position = 0..19
                )
            )
            val result = ComplianceResult(
                framework = "EU AI Act",
                compliant = false,
                findings = findings,
                riskLevel = "unacceptable",
                recommendations = listOf("CRITICAL: This practice is PROHIBITED")
            )

            val message = formatter.formatEUAIActResult(result)

            assertThat(message).containsIgnoringCase("non-compliant")
            assertThat(message).containsIgnoringCase("unacceptable")
            assertThat(message).contains("Article 5")
            assertThat(message).contains("PROHIBITED")
        }

        @Test
        @DisplayName("Should format high-risk with recommendations")
        fun formatHighRiskWithRecommendations() {
            val findings = listOf(
                ComplianceFinding(
                    id = "eu_critical_infra",
                    category = "Annex III (2)",
                    description = "Critical infrastructure AI",
                    matchedText = "power grid management",
                    severity = CompliancePatterns.Severity.HIGH,
                    position = 0..20
                )
            )
            val result = ComplianceResult(
                framework = "EU AI Act",
                compliant = true,
                findings = findings,
                riskLevel = "high",
                recommendations = listOf(
                    "HIGH: This is a high-risk AI system",
                    "Implement risk management system"
                )
            )

            val message = formatter.formatEUAIActResult(result)

            assertThat(message).contains("high")
            assertThat(message).contains("Annex III")
            assertThat(message).contains("risk management")
        }
    }

    @Nested
    @DisplayName("Unified Compliance Action Formatting")
    inner class UnifiedComplianceFormattingTests {

        @Test
        @DisplayName("Should format all-compliant result")
        fun formatAllCompliant() {
            val result = UnifiedComplianceResult(
                compliant = true,
                euAiAct = ComplianceResult("EU AI Act", true, emptyList(), "minimal", emptyList()),
                owaspLlm = ComplianceResult("OWASP LLM", true, emptyList(), "secure", emptyList()),
                csaAicm = ComplianceResult("CSA AICM", true, emptyList(), "compliant", emptyList()),
                recommendations = emptyList()
            )

            val message = formatter.formatUnifiedResult(result)

            assertThat(message).contains("ALL FRAMEWORKS COMPLIANT")
            assertThat(message).contains("EU AI Act")
            assertThat(message).contains("OWASP")
            assertThat(message).contains("CSA")
        }

        @Test
        @DisplayName("Should format mixed compliance result")
        fun formatMixedCompliance() {
            val result = UnifiedComplianceResult(
                compliant = false,
                euAiAct = ComplianceResult("EU AI Act", true, emptyList(), "minimal", emptyList()),
                owaspLlm = ComplianceResult("OWASP LLM", false, listOf(
                    ComplianceFinding("test", "LLM01", "Prompt injection", "ignore",
                        CompliancePatterns.Severity.HIGH, 0..5)
                ), "critical", listOf("Implement input validation")),
                csaAicm = ComplianceResult("CSA AICM", true, emptyList(), "compliant", emptyList()),
                recommendations = listOf("Implement input validation")
            )

            val message = formatter.formatUnifiedResult(result)

            assertThat(message).contains("COMPLIANCE ISSUES")
            assertThat(message).contains("OWASP")
            assertThat(message).contains("input validation")
        }
    }

    @Nested
    @DisplayName("Truncation Utility")
    inner class TruncationTests {

        @Test
        @DisplayName("Should not truncate short text")
        fun noTruncationForShortText() {
            val result = formatter.truncate("short", 10)
            assertThat(result).isEqualTo("short")
        }

        @Test
        @DisplayName("Should truncate long text")
        fun truncateLongText() {
            val result = formatter.truncate("this is a very long text", 10)
            assertThat(result).isEqualTo("this is a ...")
            assertThat(result.length).isEqualTo(13)
        }

        @Test
        @DisplayName("Should handle exact length")
        fun handleExactLength() {
            val result = formatter.truncate("exactly10!", 10)
            assertThat(result).isEqualTo("exactly10!")
        }
    }

    /**
     * Helper class that mirrors action formatting logic for testing.
     */
    private class ResultFormatter {

        fun formatSecretScanResult(result: SecretScanResult): String {
            return if (result.hasSecrets) {
                val sb = StringBuilder()
                sb.appendLine("SECRETS DETECTED")
                sb.appendLine("Severity: ${result.severity}")
                for (finding in result.findings) {
                    sb.appendLine("${finding.description}")
                    sb.appendLine("Found: ${finding.matchedText}")
                    if (finding.severity == SecurityPatterns.Severity.CRITICAL) {
                        sb.appendLine("CRITICAL - Remove before sharing!")
                    }
                }
                sb.appendLine("Remove or rotate these credentials before sharing.")
                sb.toString()
            } else {
                "No secrets detected - No API keys, tokens, or credentials found."
            }
        }

        fun formatSqlScanResult(result: SqlScanResult): String {
            return if (result.hasSqlInjection) {
                val sb = StringBuilder()
                sb.appendLine("SQL INJECTION DETECTED")
                sb.appendLine("Severity: ${result.severity}")

                val byCategory = result.findings.groupBy { it.category }
                for ((category, findings) in byCategory) {
                    sb.appendLine("--- ${category.name} ---")
                    for (finding in findings) {
                        sb.appendLine("${finding.description}: ${finding.matchedText}")
                    }
                }
                sb.toString()
            } else {
                "No SQL injection patterns detected."
            }
        }

        fun formatPromptScanResult(result: PromptScanResult): String {
            return if (result.hasInjection) {
                val sb = StringBuilder()
                sb.appendLine("INJECTION DETECTED")
                sb.appendLine("Severity: ${result.severity}")
                for (finding in result.findings) {
                    sb.appendLine("${finding.description}")
                    sb.appendLine("Gates affected: ${finding.gates.joinToString(", ")}")
                }
                sb.toString()
            } else {
                "No injection patterns detected."
            }
        }

        fun formatEUAIActResult(result: ComplianceResult): String {
            val sb = StringBuilder()
            if (result.compliant && result.findings.isEmpty()) {
                sb.appendLine("EU AI Act - COMPLIANT")
                sb.appendLine("Risk Level: ${result.riskLevel}")
            } else {
                sb.appendLine("EU AI Act - ${if (result.compliant) "WARNING" else "NON-COMPLIANT"}")
                sb.appendLine("Risk Level: ${result.riskLevel.uppercase()}")

                val byCategory = result.findings.groupBy { it.category }
                for ((category, findings) in byCategory) {
                    sb.appendLine("--- $category ---")
                    for (finding in findings) {
                        sb.appendLine("${finding.description}")
                    }
                }

                for (rec in result.recommendations) {
                    sb.appendLine(rec)
                }

                if (result.riskLevel == "unacceptable") {
                    sb.appendLine("PROHIBITED: This practice cannot be deployed in the EU.")
                }
            }
            return sb.toString()
        }

        fun formatUnifiedResult(result: UnifiedComplianceResult): String {
            val sb = StringBuilder()
            if (result.compliant) {
                sb.appendLine("ALL FRAMEWORKS COMPLIANT")
            } else {
                sb.appendLine("COMPLIANCE ISSUES FOUND")
            }

            result.euAiAct?.let {
                sb.appendLine("EU AI Act: ${if (it.compliant) "OK" else "FAILED"}")
            }
            result.owaspLlm?.let {
                sb.appendLine("OWASP LLM Top 10: ${if (it.compliant) "OK" else "FAILED"}")
            }
            result.csaAicm?.let {
                sb.appendLine("CSA AICM: ${if (it.compliant) "OK" else "FAILED"}")
            }

            for (rec in result.recommendations) {
                sb.appendLine("Recommendation: $rec")
            }

            return sb.toString()
        }

        fun truncate(text: String, maxLength: Int): String {
            return if (text.length > maxLength) {
                text.take(maxLength) + "..."
            } else {
                text
            }
        }
    }
}
