package dev.sentinelseed.jetbrains.util

import com.intellij.openapi.diagnostic.Logger
import java.time.Instant
import java.util.concurrent.atomic.AtomicLong

/**
 * Structured logging utility for the Sentinel plugin.
 *
 * Provides:
 * - Structured log entries with context
 * - Performance timing
 * - Correlation IDs for tracing
 * - Log level filtering
 */
object SentinelLogger {

    private val logger = Logger.getInstance("Sentinel")
    private val correlationCounter = AtomicLong(0)

    /**
     * Log levels for filtering.
     */
    enum class Level {
        TRACE, DEBUG, INFO, WARN, ERROR
    }

    /**
     * Structured log entry.
     */
    data class LogEntry(
        val level: Level,
        val message: String,
        val component: String? = null,
        val action: String? = null,
        val correlationId: String? = null,
        val durationMs: Long? = null,
        val context: Map<String, Any?> = emptyMap(),
        val timestamp: Instant = Instant.now()
    )

    /**
     * Create a logger for a specific component.
     */
    fun forComponent(component: String): ComponentLogger {
        return ComponentLogger(component)
    }

    /**
     * Generate a new correlation ID for tracing.
     */
    fun generateCorrelationId(): String {
        return "sen-${System.currentTimeMillis()}-${correlationCounter.incrementAndGet()}"
    }

    /**
     * Measure and log execution time of a block.
     */
    inline fun <T> timed(
        message: String,
        component: String? = null,
        action: String? = null,
        context: Map<String, Any?> = emptyMap(),
        block: () -> T
    ): T {
        val start = System.currentTimeMillis()
        return try {
            block()
        } finally {
            val duration = System.currentTimeMillis() - start
            log(LogEntry(
                level = Level.DEBUG,
                message = message,
                component = component,
                action = action,
                durationMs = duration,
                context = context
            ))
        }
    }

    /**
     * Log a structured entry.
     */
    fun log(entry: LogEntry) {
        val formattedMessage = formatEntry(entry)

        when (entry.level) {
            Level.TRACE -> logger.trace(formattedMessage)
            Level.DEBUG -> logger.debug(formattedMessage)
            Level.INFO -> logger.info(formattedMessage)
            Level.WARN -> logger.warn(formattedMessage)
            Level.ERROR -> logger.error(formattedMessage)
        }
    }

    // Convenience methods

    fun trace(message: String, context: Map<String, Any?> = emptyMap()) {
        log(LogEntry(Level.TRACE, message, context = context))
    }

    fun debug(message: String, context: Map<String, Any?> = emptyMap()) {
        log(LogEntry(Level.DEBUG, message, context = context))
    }

    fun info(message: String, context: Map<String, Any?> = emptyMap()) {
        log(LogEntry(Level.INFO, message, context = context))
    }

    fun warn(message: String, context: Map<String, Any?> = emptyMap()) {
        log(LogEntry(Level.WARN, message, context = context))
    }

    fun error(message: String, context: Map<String, Any?> = emptyMap()) {
        log(LogEntry(Level.ERROR, message, context = context))
    }

    // Private helpers

    private fun formatEntry(entry: LogEntry): String {
        return buildString {
            // Component prefix
            if (entry.component != null) {
                append("[${entry.component}]")
                if (entry.action != null) {
                    append("[${entry.action}]")
                }
                append(" ")
            }

            // Main message
            append(entry.message)

            // Duration if present
            if (entry.durationMs != null) {
                append(" (${entry.durationMs}ms)")
            }

            // Correlation ID if present
            if (entry.correlationId != null) {
                append(" [cid=${entry.correlationId}]")
            }

            // Context if present
            if (entry.context.isNotEmpty()) {
                val contextStr = entry.context.entries
                    .filter { it.value != null }
                    .joinToString(", ") { "${it.key}=${it.value}" }
                if (contextStr.isNotEmpty()) {
                    append(" | $contextStr")
                }
            }
        }
    }

    /**
     * Component-specific logger with pre-configured component name.
     */
    class ComponentLogger(@PublishedApi internal val component: String) {

        @PublishedApi
        internal var correlationId: String? = null

        /**
         * Set a correlation ID for all subsequent logs from this logger.
         */
        fun withCorrelationId(id: String): ComponentLogger {
            correlationId = id
            return this
        }

        fun trace(message: String, action: String? = null, context: Map<String, Any?> = emptyMap()) {
            log(LogEntry(Level.TRACE, message, component, action, correlationId, context = context))
        }

        fun debug(message: String, action: String? = null, context: Map<String, Any?> = emptyMap()) {
            log(LogEntry(Level.DEBUG, message, component, action, correlationId, context = context))
        }

        fun info(message: String, action: String? = null, context: Map<String, Any?> = emptyMap()) {
            log(LogEntry(Level.INFO, message, component, action, correlationId, context = context))
        }

        fun warn(message: String, action: String? = null, context: Map<String, Any?> = emptyMap()) {
            log(LogEntry(Level.WARN, message, component, action, correlationId, context = context))
        }

        fun error(message: String, action: String? = null, context: Map<String, Any?> = emptyMap()) {
            log(LogEntry(Level.ERROR, message, component, action, correlationId, context = context))
        }

        inline fun <T> timed(
            message: String,
            action: String? = null,
            context: Map<String, Any?> = emptyMap(),
            block: () -> T
        ): T {
            return SentinelLogger.timed(message, component, action, context, block)
        }
    }
}
