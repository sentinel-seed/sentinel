package dev.sentinelseed.jetbrains.settings

import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.openapi.project.Project
import com.intellij.util.xmlb.XmlSerializerUtil

/**
 * Project-level settings for Sentinel AI Safety plugin.
 * Allows per-project configuration overrides.
 */
@State(
    name = "SentinelProjectSettings",
    storages = [Storage("sentinel.xml")]
)
@Service(Service.Level.PROJECT)
class SentinelProjectSettings : PersistentStateComponent<SentinelProjectSettings> {

    // Project-specific overrides
    var overrideApplicationSettings: Boolean = false
    var enableAnalysis: Boolean = true

    // File patterns to analyze
    var includePatterns: String = "*.md,*.txt,*.py,*.js,*.ts,*.json,*.yaml,*.yml"
    var excludePatterns: String = "node_modules/**,*.min.js,dist/**,build/**"

    // Custom rules
    var customBlockedPatterns: String = ""
    var customAllowedPatterns: String = ""

    companion object {
        fun getInstance(project: Project): SentinelProjectSettings =
            project.getService(SentinelProjectSettings::class.java)
    }

    override fun getState(): SentinelProjectSettings = this

    override fun loadState(state: SentinelProjectSettings) {
        XmlSerializerUtil.copyBean(state, this)
    }
}
