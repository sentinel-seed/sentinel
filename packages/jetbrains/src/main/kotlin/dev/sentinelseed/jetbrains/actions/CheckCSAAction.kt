package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import dev.sentinelseed.jetbrains.compliance.CompliancePatterns.Severity
import dev.sentinelseed.jetbrains.services.ComplianceService
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory

/**
 * Action to check content against CSA AI Controls Matrix requirements.
 *
 * Evaluates:
 * - Model Security domain
 * - Data Governance domain
 * - Supply Chain domain
 * - Application Security domain
 */
class CheckCSAAction : AnAction() {

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
        val result = service.checkCSA(text)

        // Record metrics
        MetricsService.getInstance().recordComplianceCheck(
            framework = "CSA_AICM",
            compliant = result.compliant,
            findingsCount = result.findings.size
        )

        val sb = StringBuilder()

        if (result.compliant) {
            sb.appendLine("✅ CSA AI Controls Matrix - COMPLIANT")
            sb.appendLine()
            sb.appendLine("Status: ${result.riskLevel}")
            sb.appendLine("No control gaps detected.")
        } else {
            sb.appendLine("⚠️ CSA AI Controls Matrix - REVIEW NEEDED")
            sb.appendLine()
            sb.appendLine("Status: ${result.riskLevel.uppercase()}")
            sb.appendLine("Control Gaps: ${result.findings.size}")
            sb.appendLine()

            // Group by domain
            val byDomain = result.findings.groupBy { it.category }

            for ((domain, findings) in byDomain) {
                sb.appendLine("━━━ $domain ━━━")

                for (finding in findings.take(3)) {
                    val severityIcon = when (finding.severity) {
                        Severity.CRITICAL -> "🔴"
                        Severity.HIGH -> "🟠"
                        Severity.MEDIUM -> "🟡"
                        else -> "🟢"
                    }
                    sb.appendLine("$severityIcon ${finding.description}")
                    sb.appendLine("   Detected: \"${truncate(finding.matchedText, 40)}\"")
                }
                if (findings.size > 3) {
                    sb.appendLine("   ... and ${findings.size - 3} more")
                }
                sb.appendLine()
            }

            if (result.recommendations.isNotEmpty()) {
                sb.appendLine("━━━ Control Recommendations ━━━")
                for (rec in result.recommendations) {
                    sb.appendLine("• $rec")
                }
            }
        }

        sb.appendLine()
        sb.appendLine("ℹ️ Reference: CSA AI Controls Matrix v1.0 (July 2025)")

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
