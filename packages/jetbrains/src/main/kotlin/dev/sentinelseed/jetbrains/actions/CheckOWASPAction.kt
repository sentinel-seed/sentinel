package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import dev.sentinelseed.jetbrains.compliance.CompliancePatterns.Severity
import dev.sentinelseed.jetbrains.services.ComplianceService
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory

/**
 * Action to check content against OWASP LLM Top 10 vulnerabilities.
 *
 * Detects:
 * - LLM01: Prompt Injection
 * - LLM02: Sensitive Information Disclosure
 * - LLM05: Improper Output Handling
 * - LLM06: Excessive Agency
 * - LLM07: System Prompt Leakage
 */
class CheckOWASPAction : AnAction() {

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
            SentinelToolWindowFactory.showMessage(project, "No content to check", isError = true)
            return
        }

        val service = ComplianceService.getInstance()
        val result = service.checkOWASP(text)

        // Record metrics
        MetricsService.getInstance().recordComplianceCheck(
            framework = "OWASP_LLM",
            compliant = result.compliant,
            findingsCount = result.findings.size
        )

        val sb = StringBuilder()

        if (result.compliant) {
            sb.appendLine("✅ OWASP LLM Top 10 - SECURE")
            sb.appendLine()
            sb.appendLine("No vulnerabilities detected.")
        } else {
            sb.appendLine("⚠️ OWASP LLM Top 10 - ISSUES FOUND")
            sb.appendLine()
            sb.appendLine("Risk Level: ${result.riskLevel.uppercase()}")
            sb.appendLine("Vulnerabilities: ${result.findings.size}")
            sb.appendLine()

            // Group by category
            val byCategory = result.findings.groupBy { it.category }

            for ((category, findings) in byCategory) {
                sb.appendLine("━━━ $category ━━━")
                for (finding in findings.take(3)) {
                    val icon = when (finding.severity) {
                        Severity.CRITICAL -> "🔴"
                        Severity.HIGH -> "🟠"
                        Severity.MEDIUM -> "🟡"
                        else -> "🟢"
                    }
                    sb.appendLine("$icon ${finding.description}")
                    sb.appendLine("   Pattern: \"${truncate(finding.matchedText, 40)}\"")
                }
                if (findings.size > 3) {
                    sb.appendLine("   ... and ${findings.size - 3} more")
                }
                sb.appendLine()
            }

            if (result.recommendations.isNotEmpty()) {
                sb.appendLine("━━━ Recommendations ━━━")
                for (rec in result.recommendations) {
                    sb.appendLine("• $rec")
                }
            }
        }

        SentinelToolWindowFactory.showMessage(project, sb.toString(), isError = !result.compliant)
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
