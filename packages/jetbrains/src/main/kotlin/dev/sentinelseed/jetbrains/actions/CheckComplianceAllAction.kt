package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import dev.sentinelseed.jetbrains.services.ComplianceService
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory

/**
 * Action to check content against all supported compliance frameworks.
 *
 * Runs checks for:
 * - EU AI Act (2024)
 * - OWASP LLM Top 10 (2025)
 * - CSA AI Controls Matrix (2025)
 */
class CheckComplianceAllAction : AnAction() {

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
        val result = service.checkAll(text)

        // Record metrics for all frameworks
        result.euAiAct?.let {
            MetricsService.getInstance().recordComplianceCheck("EU_AI_Act", it.compliant, it.findings.size)
        }
        result.owaspLlm?.let {
            MetricsService.getInstance().recordComplianceCheck("OWASP_LLM", it.compliant, it.findings.size)
        }
        result.csaAicm?.let {
            MetricsService.getInstance().recordComplianceCheck("CSA_AICM", it.compliant, it.findings.size)
        }

        val sb = StringBuilder()

        // Overall status
        if (result.compliant) {
            sb.appendLine("✅ ALL FRAMEWORKS - COMPLIANT")
        } else {
            sb.appendLine("⚠️ COMPLIANCE ISSUES DETECTED")
        }
        sb.appendLine()

        // Summary table
        sb.appendLine("━━━━━━━━━━━━ SUMMARY ━━━━━━━━━━━━")
        sb.appendLine()

        // EU AI Act
        result.euAiAct?.let { eu ->
            val icon = if (eu.compliant) "✅" else "⚠️"
            sb.appendLine("$icon EU AI Act")
            sb.appendLine("   Risk Level: ${eu.riskLevel}")
            sb.appendLine("   Findings: ${eu.findings.size}")
        }
        sb.appendLine()

        // OWASP LLM
        result.owaspLlm?.let { owasp ->
            val icon = if (owasp.compliant) "✅" else "⚠️"
            sb.appendLine("$icon OWASP LLM Top 10")
            sb.appendLine("   Status: ${owasp.riskLevel}")
            sb.appendLine("   Vulnerabilities: ${owasp.findings.size}")
        }
        sb.appendLine()

        // CSA AICM
        result.csaAicm?.let { csa ->
            val icon = if (csa.compliant) "✅" else "⚠️"
            sb.appendLine("$icon CSA AI Controls Matrix")
            sb.appendLine("   Status: ${csa.riskLevel}")
            sb.appendLine("   Control Gaps: ${csa.findings.size}")
        }
        sb.appendLine()

        // All recommendations
        if (result.recommendations.isNotEmpty()) {
            sb.appendLine("━━━━━━━ RECOMMENDATIONS ━━━━━━━")
            sb.appendLine()
            for ((index, rec) in result.recommendations.withIndex()) {
                sb.appendLine("${index + 1}. $rec")
            }
        }

        sb.appendLine()
        sb.appendLine("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        sb.appendLine("ℹ️ All checks run 100% locally - no data sent to servers")

        SentinelToolWindowFactory.showMessage(project, sb.toString(), isError = !result.compliant)
    }

    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null
    }
}
