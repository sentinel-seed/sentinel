package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.services.SecurityService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory
import dev.sentinelseed.jetbrains.util.SecurityPatterns.SqlCategory
import dev.sentinelseed.jetbrains.util.SecurityPatterns.Severity

/**
 * Action to scan content for SQL injection patterns.
 * Detects destructive queries, UNION attacks, auth bypass, etc.
 */
class ScanSQLInjectionAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val project = e.project ?: return

        // Get text (selection or full file)
        val selectedText = editor.selectionModel.selectedText
        val text = if (selectedText.isNullOrBlank()) {
            editor.document.text
        } else {
            selectedText
        }

        if (text.isBlank()) {
            SentinelToolWindowFactory.showMessage(project, "No content to scan", isError = true)
            return
        }

        val service = SecurityService.getInstance()
        val result = service.scanSqlInjection(text)

        // Record metrics
        MetricsService.getInstance().recordSecurityScan(
            scanType = "sql_injection",
            issuesFound = result.findings.size,
            safe = !result.hasSqlInjection
        )

        if (result.hasSqlInjection) {
            val sb = StringBuilder()
            sb.appendLine("⚠️ SQL INJECTION DETECTED")
            sb.appendLine()
            sb.appendLine("Severity: ${result.severity}")
            sb.appendLine()

            // Group findings by category
            val grouped = service.scanSqlByCategory(text)

            val categoryLabels = mapOf(
                SqlCategory.DESTRUCTIVE to "🔴 Destructive",
                SqlCategory.UNION_ATTACK to "🟠 UNION Attack",
                SqlCategory.AUTHENTICATION_BYPASS to "🟠 Auth Bypass",
                SqlCategory.DATA_EXTRACTION to "🟠 Data Extraction",
                SqlCategory.STACKED_QUERIES to "🟠 Stacked Queries",
                SqlCategory.COMMENT_INJECTION to "🟡 Comment Injection",
                SqlCategory.BLIND_INJECTION to "🟡 Blind Injection",
                SqlCategory.ERROR_BASED to "🟡 Error-Based"
            )

            for ((category, label) in categoryLabels) {
                val findings = grouped[category] ?: emptyList()
                if (findings.isNotEmpty()) {
                    sb.appendLine()
                    sb.appendLine("$label:")
                    for (finding in findings.take(3)) {
                        val truncated = truncate(finding.matchedText, 50)
                        sb.appendLine("  • $truncated")
                        sb.appendLine("    ${finding.description}")
                    }
                    if (findings.size > 3) {
                        sb.appendLine("  ... and ${findings.size - 3} more")
                    }
                }
            }

            sb.appendLine()
            sb.appendLine("🛡️ Review and sanitize this content before use.")

            SentinelToolWindowFactory.showMessage(project, sb.toString(), isError = true)
        } else {
            SentinelToolWindowFactory.showMessage(
                project,
                "✅ No SQL Injection Detected\n\nNo dangerous SQL patterns found."
            )
        }
    }

    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null
    }

    private fun truncate(text: String, maxLength: Int): String {
        return if (text.length > maxLength) {
            text.take(maxLength) + "..."
        } else {
            text
        }
    }
}
