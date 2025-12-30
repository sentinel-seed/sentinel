package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.services.SecurityService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory
import dev.sentinelseed.jetbrains.util.SecurityPatterns.Severity

/**
 * Action to sanitize prompts by detecting prompt injection attempts.
 * Uses OWASP LLM01 (Prompt Injection) patterns.
 */
class SanitizePromptAction : AnAction() {

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
            SentinelToolWindowFactory.showMessage(project, "No content to sanitize", isError = true)
            return
        }

        val service = SecurityService.getInstance()
        val result = service.scanPromptInjection(text)

        // Record metrics
        MetricsService.getInstance().recordSecurityScan(
            scanType = "prompt_injection",
            issuesFound = result.findings.size,
            safe = !result.hasInjection
        )

        if (result.hasInjection) {
            val sb = StringBuilder()
            sb.appendLine("⚠️ PROMPT INJECTION DETECTED")
            sb.appendLine()
            sb.appendLine("Severity: ${result.severity}")
            sb.appendLine()
            sb.appendLine("Findings:")

            for (finding in result.findings) {
                sb.appendLine("• ${finding.description}")
                sb.appendLine("  Pattern: \"${truncate(finding.matchedText, 50)}\"")
                if (finding.gates.isNotEmpty()) {
                    sb.appendLine("  Gates affected: ${finding.gates.joinToString(", ")}")
                }
                if (finding.severity == Severity.CRITICAL) {
                    sb.appendLine("  ⚠️ CRITICAL - Known jailbreak technique!")
                }
            }

            sb.appendLine()
            sb.appendLine("🛡️ Review and sanitize this input before sending to LLM.")

            SentinelToolWindowFactory.showMessage(project, sb.toString(), isError = true)
        } else {
            SentinelToolWindowFactory.showMessage(
                project,
                "✅ Prompt looks safe\n\nNo injection patterns detected."
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
