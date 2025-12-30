package dev.sentinelseed.jetbrains.actions

import com.intellij.openapi.actionSystem.AnAction
import com.intellij.openapi.actionSystem.AnActionEvent
import dev.sentinelseed.jetbrains.services.MetricsService
import dev.sentinelseed.jetbrains.ui.SentinelToolWindowFactory

/**
 * Action to display the Sentinel metrics dashboard.
 *
 * Shows statistics about:
 * - Total analyses performed
 * - Safe/unsafe rate
 * - THSP gate failure statistics
 * - Analysis methods (semantic vs heuristic)
 * - Provider usage
 */
class ShowMetricsAction : AnAction() {

    override fun actionPerformed(e: AnActionEvent) {
        val project = e.project ?: return

        val service = MetricsService.getInstance()
        val dashboard = service.getFormattedDashboard()

        SentinelToolWindowFactory.showMessage(project, dashboard)
    }

    override fun update(e: AnActionEvent) {
        e.presentation.isEnabledAndVisible = e.project != null
    }
}
