package dev.sentinelseed.jetbrains.util

import com.intellij.DynamicBundle
import org.jetbrains.annotations.NonNls
import org.jetbrains.annotations.PropertyKey
import java.text.MessageFormat

/**
 * Message bundle for internationalization (i18n) support.
 *
 * Provides access to localized messages for the Sentinel plugin.
 * Supports parameter substitution using MessageFormat.
 *
 * Usage:
 * ```kotlin
 * val message = SentinelBundle.message("action.scanSecrets.title")
 * val formatted = SentinelBundle.message("action.scanSecrets.result.found", 5)
 * ```
 */
object SentinelBundle {

    @NonNls
    private const val BUNDLE = "messages.SentinelBundle"

    private val bundle = DynamicBundle(SentinelBundle::class.java, BUNDLE)

    /**
     * Get a message by key with optional parameter substitution.
     *
     * @param key The message key from the bundle
     * @param params Optional parameters to substitute in the message
     * @return The localized message with parameters substituted
     */
    fun message(
        @PropertyKey(resourceBundle = BUNDLE) key: String,
        vararg params: Any?
    ): String {
        return try {
            val rawMessage = bundle.getMessage(key)
            if (params.isEmpty()) {
                rawMessage
            } else {
                MessageFormat.format(rawMessage, *params)
            }
        } catch (e: Exception) {
            // Fallback: return key if message not found
            key
        }
    }

    /**
     * Get a message by key, returning null if not found.
     *
     * @param key The message key from the bundle
     * @param params Optional parameters to substitute in the message
     * @return The localized message or null if not found
     */
    fun messageOrNull(
        @PropertyKey(resourceBundle = BUNDLE) key: String,
        vararg params: Any?
    ): String? {
        return try {
            val rawMessage = bundle.getMessage(key)
            if (params.isEmpty()) {
                rawMessage
            } else {
                MessageFormat.format(rawMessage, *params)
            }
        } catch (e: Exception) {
            null
        }
    }

    /**
     * Get a message by key, returning a default if not found.
     *
     * @param key The message key from the bundle
     * @param default The default value if key not found
     * @param params Optional parameters to substitute in the message
     * @return The localized message or default
     */
    fun messageOrDefault(
        @PropertyKey(resourceBundle = BUNDLE) key: String,
        default: String,
        vararg params: Any?
    ): String {
        return messageOrNull(key, *params) ?: default
    }

    // ==========================================================================
    // Convenience methods for common message categories
    // ==========================================================================

    /**
     * Get an action-related message.
     */
    fun action(action: String, suffix: String, vararg params: Any?): String {
        return message("action.$action.$suffix", *params)
    }

    /**
     * Get a settings-related message.
     */
    fun settings(key: String, vararg params: Any?): String {
        return message("settings.$key", *params)
    }

    /**
     * Get an error message.
     */
    fun error(key: String, vararg params: Any?): String {
        return message("error.$key", *params)
    }

    /**
     * Get a notification message.
     */
    fun notification(key: String, vararg params: Any?): String {
        return message("notification.$key", *params)
    }

    /**
     * Get a severity label.
     */
    fun severity(level: String): String {
        return message("severity.${level.lowercase()}")
    }

    /**
     * Get a risk level label.
     */
    fun riskLevel(level: String): String {
        return message("risk.${level.lowercase()}")
    }
}
