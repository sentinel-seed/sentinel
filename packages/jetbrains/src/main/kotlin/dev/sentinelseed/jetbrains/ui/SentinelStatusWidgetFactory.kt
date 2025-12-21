package dev.sentinelseed.jetbrains.ui

import com.intellij.openapi.project.Project
import com.intellij.openapi.util.Disposer
import com.intellij.openapi.wm.StatusBar
import com.intellij.openapi.wm.StatusBarWidget
import com.intellij.openapi.wm.StatusBarWidgetFactory
import com.intellij.util.Consumer
import dev.sentinelseed.jetbrains.services.SentinelService
import dev.sentinelseed.jetbrains.settings.SentinelApplicationSettings
import java.awt.Component
import java.awt.event.MouseEvent

/**
 * Factory for the Sentinel status bar widget
 */
class SentinelStatusWidgetFactory : StatusBarWidgetFactory {

    override fun getId(): String = "SentinelStatusWidget"

    override fun getDisplayName(): String = "Sentinel AI Safety"

    override fun isAvailable(project: Project): Boolean =
        SentinelApplicationSettings.getInstance().showStatusBarWidget

    override fun createWidget(project: Project): StatusBarWidget =
        SentinelStatusWidget(project)

    override fun disposeWidget(widget: StatusBarWidget) {
        Disposer.dispose(widget)
    }

    override fun canBeEnabledOn(statusBar: StatusBar): Boolean = true
}

/**
 * Status bar widget showing Sentinel status
 */
class SentinelStatusWidget(private val project: Project) : StatusBarWidget, StatusBarWidget.TextPresentation {

    override fun ID(): String = "SentinelStatusWidget"

    override fun getPresentation(): StatusBarWidget.WidgetPresentation = this

    override fun install(statusBar: StatusBar) {}

    override fun dispose() {}

    override fun getText(): String {
        val service = SentinelService.getInstance()
        return if (service.isSemanticAvailable()) {
            val (provider, _) = service.getProviderInfo()
            "🛡️ Sentinel: $provider"
        } else {
            "🛡️ Sentinel: Heuristic"
        }
    }

    override fun getTooltipText(): String {
        val service = SentinelService.getInstance()
        return if (service.isSemanticAvailable()) {
            val (provider, model) = service.getProviderInfo()
            "Semantic analysis enabled ($model)"
        } else {
            "Heuristic mode (configure API key for semantic analysis)"
        }
    }

    override fun getAlignment(): Float = Component.CENTER_ALIGNMENT

    override fun getClickConsumer(): Consumer<MouseEvent>? = Consumer {
        // Open settings on click
        com.intellij.openapi.options.ShowSettingsUtil.getInstance()
            .showSettingsDialog(project, "Sentinel AI Safety")
    }
}
