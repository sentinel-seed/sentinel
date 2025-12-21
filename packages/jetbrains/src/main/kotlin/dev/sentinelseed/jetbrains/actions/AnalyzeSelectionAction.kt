package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import com.intellij.openapi.actionSystem.CommonDataKeys
import com.intellij.openapi.progress.ProgressIndicator
import com.intellij.openapi.progress.ProgressManager
import com.intellij.openapi.progress.Task
import dev.sentinelseed.jetbrains.services.SentinelService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory
import kotlinx.coroutines.runBlocking

/**
 * Action to analyze selected text for safety issues
 */
class AnalyzeSelectionAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR) ?: return
        val project = e.project ?: return

        val selectedText = editor.selectionModel.selectedText
        if (selectedText.isNullOrBlank()) {
            SentinelToolWindowFactory.showMessage(project, "No text selected", isError = true)
            return
        }

        ProgressManager.getInstance().run(object : Task.Backgroundable(project, "Analyzing with Sentinel...", true) {
            override fun run(indicator: ProgressIndicator) {
                indicator.isIndeterminate = true

                try {
                    val service = SentinelService.getInstance()
                    val result = runBlocking { service.analyze(selectedText) }

                    // Show results in tool window
                    SentinelToolWindowFactory.showResult(project, result)
                } catch (ex: Exception) {
                    SentinelToolWindowFactory.showMessage(project, "Analysis failed: ${ex.message}", isError = true)
                }
            }
        })
    }

    override fun update(e: AnActionEvent) {
        val editor = e.getData(CommonDataKeys.EDITOR)
        e.presentation.isEnabledAndVisible = editor != null && editor.selectionModel.hasSelection()
    }
}
