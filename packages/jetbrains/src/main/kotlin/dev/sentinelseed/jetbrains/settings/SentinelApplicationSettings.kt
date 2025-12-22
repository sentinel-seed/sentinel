package dev.sentinelseed.jetbrains.settings

import com.intellij.openapi.application.ApplicationManager
import com.intellij.openapi.components.PersistentStateComponent
import com.intellij.openapi.components.Service
import com.intellij.openapi.components.State
import com.intellij.openapi.components.Storage
import com.intellij.util.xmlb.XmlSerializerUtil
import com.intellij.credentialStore.CredentialAttributes
import com.intellij.credentialStore.Credentials
import com.intellij.credentialStore.generateServiceName
import com.intellij.ide.passwordSafe.PasswordSafe

/**
 * Application-level settings for Sentinel AI Safety plugin.
 * Persisted across all projects.
 */
@State(
    name = "SentinelApplicationSettings",
    storages = [Storage("SentinelAISafety.xml")]
)
@Service(Service.Level.APP)
class SentinelApplicationSettings : PersistentStateComponent<SentinelApplicationSettings> {

    // LLM Provider settings
    var llmProvider: String = "openai"
    var openaiModel: String = "gpt-4o-mini"
    var anthropicModel: String = "claude-3-haiku-20240307"

    // Ollama settings (local, free)
    var ollamaEndpoint: String = "http://localhost:11434"
    var ollamaModel: String = "llama3.2"

    // OpenAI-compatible settings (Groq, Together AI, etc.)
    var openaiCompatibleEndpoint: String = ""
    var openaiCompatibleModel: String = "llama-3.3-70b-versatile"

    // Behavior settings
    var enableRealTimeLinting: Boolean = true
    var highlightUnsafePatterns: Boolean = true
    var defaultSeedVariant: String = "standard"
    var showStatusBarWidget: Boolean = true

    // API settings
    var useSentinelApi: Boolean = false
    var sentinelApiEndpoint: String = "https://api.sentinelseed.dev/api/v1/guard"

    companion object {
        private const val OPENAI_KEY_ID = "sentinel.openai.apikey"
        private const val ANTHROPIC_KEY_ID = "sentinel.anthropic.apikey"
        private const val COMPATIBLE_KEY_ID = "sentinel.compatible.apikey"

        fun getInstance(): SentinelApplicationSettings =
            ApplicationManager.getApplication().getService(SentinelApplicationSettings::class.java)
    }

    override fun getState(): SentinelApplicationSettings = this

    override fun loadState(state: SentinelApplicationSettings) {
        XmlSerializerUtil.copyBean(state, this)
    }

    // Secure storage for API keys using PasswordSafe
    var openaiApiKey: String
        get() = getSecureKey(OPENAI_KEY_ID) ?: ""
        set(value) = setSecureKey(OPENAI_KEY_ID, value)

    var anthropicApiKey: String
        get() = getSecureKey(ANTHROPIC_KEY_ID) ?: ""
        set(value) = setSecureKey(ANTHROPIC_KEY_ID, value)

    var openaiCompatibleApiKey: String
        get() = getSecureKey(COMPATIBLE_KEY_ID) ?: ""
        set(value) = setSecureKey(COMPATIBLE_KEY_ID, value)

    private fun createCredentialAttributes(key: String): CredentialAttributes {
        return CredentialAttributes(generateServiceName("SentinelAISafety", key))
    }

    private fun getSecureKey(key: String): String? {
        val attributes = createCredentialAttributes(key)
        return PasswordSafe.instance.getPassword(attributes)
    }

    private fun setSecureKey(key: String, value: String) {
        val attributes = createCredentialAttributes(key)
        if (value.isBlank()) {
            PasswordSafe.instance.set(attributes, null)
        } else {
            PasswordSafe.instance.set(attributes, Credentials("", value))
        }
    }
}
