package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.ui.Messages
import dev.sentinelseed.jetbrains.services.SentinelService

/**
 * Action to show current Sentinel analysis status
 */
class ShowStatusAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return
        val service = SentinelService.getInstance()

        val (provider, model) = service.getProviderInfo()
        val message = if (service.isSemanticAvailable()) {
            """
            Sentinel is using semantic analysis.

            Provider: $provider
            Model: $model
            Mode: Comprehensive (LLM-powered)
            """.trimIndent()
        } else {
            """
            Sentinel is using heuristic analysis (pattern matching).

            Mode: Basic (pattern-based, limited coverage)

            To enable semantic analysis:
            • Go to Settings → Tools → Sentinel AI Safety
            • Configure your OpenAI, Anthropic, or Ollama
            """.trimIndent()
        }

        Messages.showInfoMessage(project, message, "Sentinel Status")
    }
}
