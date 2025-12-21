package dev.sentinelseed.jetbrains.settings

import com.intellij.openapi.options.Configurable
import com.intellij.openapi.ui.ComboBox
import com.intellij.ui.components.JBCheckBox
import com.intellij.ui.components.JBLabel
import com.intellij.ui.components.JBPasswordField
import com.intellij.ui.components.JBTextField
import com.intellij.ui.dsl.builder.*
import javax.swing.JComponent
import javax.swing.JPanel

/**
 * Settings panel for Sentinel AI Safety plugin.
 * Accessible via Settings → Tools → Sentinel AI Safety
 */
class SentinelSettingsConfigurable : Configurable {

    private var panel: JPanel? = null

    // UI components
    private val llmProviderCombo = ComboBox(arrayOf("openai", "anthropic"))
    private val openaiKeyField = JBPasswordField()
    private val openaiModelField = JBTextField()
    private val anthropicKeyField = JBPasswordField()
    private val anthropicModelField = JBTextField()
    private val enableLintingCheckbox = JBCheckBox("Enable real-time linting")
    private val highlightPatternsCheckbox = JBCheckBox("Highlight unsafe patterns")
    private val seedVariantCombo = ComboBox(arrayOf("standard", "minimal"))
    private val showStatusBarCheckbox = JBCheckBox("Show status bar widget")
    private val useSentinelApiCheckbox = JBCheckBox("Use Sentinel API")
    private val apiEndpointField = JBTextField()

    override fun getDisplayName(): String = "Sentinel AI Safety"

    override fun createComponent(): JComponent {
        val settings = SentinelApplicationSettings.getInstance()

        panel = panel {
            group("LLM Provider") {
                row("Provider:") {
                    cell(llmProviderCombo)
                        .comment("Select the LLM provider for semantic analysis")
                }
            }

            group("OpenAI Configuration") {
                row("API Key:") {
                    cell(openaiKeyField)
                        .columns(COLUMNS_LARGE)
                        .comment("Your OpenAI API key (stored securely)")
                }
                row("Model:") {
                    cell(openaiModelField)
                        .columns(COLUMNS_MEDIUM)
                        .comment("e.g., gpt-4o-mini, gpt-4o")
                }
            }

            group("Anthropic Configuration") {
                row("API Key:") {
                    cell(anthropicKeyField)
                        .columns(COLUMNS_LARGE)
                        .comment("Your Anthropic API key (stored securely)")
                }
                row("Model:") {
                    cell(anthropicModelField)
                        .columns(COLUMNS_MEDIUM)
                        .comment("e.g., claude-3-haiku-20240307")
                }
            }

            group("Behavior") {
                row {
                    cell(enableLintingCheckbox)
                        .comment("Analyze files in real-time as you type")
                }
                row {
                    cell(highlightPatternsCheckbox)
                        .comment("Highlight potentially unsafe patterns in the editor")
                }
                row("Default seed variant:") {
                    cell(seedVariantCombo)
                        .comment("Seed variant to insert by default")
                }
                row {
                    cell(showStatusBarCheckbox)
                        .comment("Show Sentinel status in the status bar")
                }
            }

            group("Sentinel API (Optional)") {
                row {
                    cell(useSentinelApiCheckbox)
                        .comment("Use Sentinel's hosted API instead of direct LLM calls")
                }
                row("API Endpoint:") {
                    cell(apiEndpointField)
                        .columns(COLUMNS_LARGE)
                }
            }

            row {
                browserLink("Documentation", "https://sentinelseed.dev/docs")
                browserLink("GitHub", "https://github.com/sentinel-seed/sentinel")
            }
        }

        // Load current values
        reset()

        return panel!!
    }

    override fun isModified(): Boolean {
        val settings = SentinelApplicationSettings.getInstance()

        return llmProviderCombo.selectedItem != settings.llmProvider ||
                String(openaiKeyField.password) != settings.openaiApiKey ||
                openaiModelField.text != settings.openaiModel ||
                String(anthropicKeyField.password) != settings.anthropicApiKey ||
                anthropicModelField.text != settings.anthropicModel ||
                enableLintingCheckbox.isSelected != settings.enableRealTimeLinting ||
                highlightPatternsCheckbox.isSelected != settings.highlightUnsafePatterns ||
                seedVariantCombo.selectedItem != settings.defaultSeedVariant ||
                showStatusBarCheckbox.isSelected != settings.showStatusBarWidget ||
                useSentinelApiCheckbox.isSelected != settings.useSentinelApi ||
                apiEndpointField.text != settings.sentinelApiEndpoint
    }

    override fun apply() {
        val settings = SentinelApplicationSettings.getInstance()

        settings.llmProvider = llmProviderCombo.selectedItem as String
        settings.openaiApiKey = String(openaiKeyField.password)
        settings.openaiModel = openaiModelField.text
        settings.anthropicApiKey = String(anthropicKeyField.password)
        settings.anthropicModel = anthropicModelField.text
        settings.enableRealTimeLinting = enableLintingCheckbox.isSelected
        settings.highlightUnsafePatterns = highlightPatternsCheckbox.isSelected
        settings.defaultSeedVariant = seedVariantCombo.selectedItem as String
        settings.showStatusBarWidget = showStatusBarCheckbox.isSelected
        settings.useSentinelApi = useSentinelApiCheckbox.isSelected
        settings.sentinelApiEndpoint = apiEndpointField.text
    }

    override fun reset() {
        val settings = SentinelApplicationSettings.getInstance()

        llmProviderCombo.selectedItem = settings.llmProvider
        openaiKeyField.text = settings.openaiApiKey
        openaiModelField.text = settings.openaiModel
        anthropicKeyField.text = settings.anthropicApiKey
        anthropicModelField.text = settings.anthropicModel
        enableLintingCheckbox.isSelected = settings.enableRealTimeLinting
        highlightPatternsCheckbox.isSelected = settings.highlightUnsafePatterns
        seedVariantCombo.selectedItem = settings.defaultSeedVariant
        showStatusBarCheckbox.isSelected = settings.showStatusBarWidget
        useSentinelApiCheckbox.isSelected = settings.useSentinelApi
        apiEndpointField.text = settings.sentinelApiEndpoint
    }

    override fun disposeUIResources() {
        panel = null
    }
}
