package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.services.SecurityService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory
import dev.sentinelseed.jetbrains.util.SecurityPatterns.Severity

/**
 * Action to scan content for secrets (API keys, tokens, credentials, PII).
 * Uses OWASP LLM02 (Sensitive Information Disclosure) patterns.
 */
class ScanSecretsAction : AnAction() {

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
        val result = service.scanSecrets(text)

        // Record metrics
        MetricsService.getInstance().recordSecurityScan(
            scanType = "secrets",
            issuesFound = result.findings.size,
            safe = !result.hasSecrets
        )

        if (result.hasSecrets) {
            val sb = StringBuilder()
            sb.appendLine("⚠️ SECRETS DETECTED")
            sb.appendLine()
            sb.appendLine("Severity: ${result.severity}")
            sb.appendLine()
            sb.appendLine("Findings:")

            for (finding in result.findings) {
                sb.appendLine("• ${finding.description}")
                sb.appendLine("  Found: ${finding.matchedText}")
                if (finding.severity == Severity.CRITICAL) {
                    sb.appendLine("  ⚠️ CRITICAL - Remove before sharing!")
                }
            }

            sb.appendLine()
            sb.appendLine("🔒 Remove or rotate these credentials before sharing.")

            SentinelToolWindowFactory.showMessage(project, sb.toString(), isError = true)
        } else {
            SentinelToolWindowFactory.showMessage(
                project,
                "✅ No secrets detected\n\nNo API keys, tokens, or credentials found."
            )
        }
    }

    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null
    }
}
