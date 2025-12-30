package dev.sentinelseed.jetbrains.util

import com.intellij.notification.NotificationGroupManager
import com.intellij.notification.NotificationType
import com.intellij.openapi.diagnostic.Logger
import com.intellij.openapi.project.Project
import java.util.regex.PatternSyntaxException

/**
 * Centralized error handling for the Sentinel plugin.
 *
 * Provides consistent error reporting across all plugin components:
 * - Structured logging for diagnostics
 * - User-friendly notifications
 * - Error categorization and severity levels
 */
object ErrorHandler {

    private val logger = Logger.getInstance(ErrorHandler::class.java)
    private const val NOTIFICATION_GROUP = "Sentinel AI Safety"

    /**
     * Error severity levels for categorization.
     */
    enum class ErrorSeverity {
        /** Informational - operation completed with warnings */
        INFO,
        /** Warning - operation completed but may have issues */
        WARNING,
        /** Error - operation failed but recoverable */
        ERROR,
        /** Critical - operation failed, may affect plugin stability */
        CRITICAL
    }

    /**
     * Error categories for classification.
     */
    enum class ErrorCategory {
        /** Configuration-related errors (API keys, settings) */
        CONFIGURATION,
        /** Network/API communication errors */
        NETWORK,
        /** Content analysis errors */
        ANALYSIS,
        /** File I/O errors */
        IO,
        /** Pattern matching/regex errors */
        PATTERN,
        /** Service initialization errors */
        SERVICE,
        /** Unknown/unexpected errors */
        UNKNOWN
    }

    /**
     * Structured error data for logging and reporting.
     */
    data class SentinelError(
        val message: String,
        val category: ErrorCategory,
        val severity: ErrorSeverity,
        val exception: Throwable? = null,
        val context: Map<String, Any?> = emptyMap()
    )

    /**
     * Handle an error with structured logging and optional user notification.
     *
     * @param error The structured error to handle
     * @param project Optional project context for notifications
     * @param showNotification Whether to show a user notification
     */
    fun handle(
        error: SentinelError,
        project: Project? = null,
        showNotification: Boolean = true
    ) {
        // Log the error
        logError(error)

        // Show notification if requested
        if (showNotification && project != null) {
            showNotification(error, project)
        }
    }

    /**
     * Handle an exception with automatic error categorization.
     *
     * @param exception The exception to handle
     * @param message Human-readable error message
     * @param project Optional project context
     * @param category Error category (auto-detected if not provided)
     */
    fun handleException(
        exception: Throwable,
        message: String,
        project: Project? = null,
        category: ErrorCategory = detectCategory(exception)
    ) {
        val error = SentinelError(
            message = message,
            category = category,
            severity = detectSeverity(exception),
            exception = exception,
            context = mapOf(
                "exceptionType" to exception::class.simpleName,
                "stackTrace" to exception.stackTraceToString().take(500)
            )
        )
        handle(error, project)
    }

    /**
     * Log an informational message.
     */
    fun info(message: String, context: Map<String, Any?> = emptyMap()) {
        logger.info(formatMessage(message, context))
    }

    /**
     * Log a warning message.
     */
    fun warn(message: String, context: Map<String, Any?> = emptyMap()) {
        logger.warn(formatMessage(message, context))
    }

    /**
     * Log an error message.
     */
    fun error(message: String, exception: Throwable? = null, context: Map<String, Any?> = emptyMap()) {
        val formattedMessage = formatMessage(message, context)
        if (exception != null) {
            logger.error(formattedMessage, exception)
        } else {
            logger.error(formattedMessage)
        }
    }

    /**
     * Execute a block safely, catching and handling any exceptions.
     *
     * @param message Error message to use if exception occurs
     * @param project Optional project context for notifications
     * @param category Error category
     * @param showNotification Whether to show notification on error
     * @param block The code block to execute
     * @return Result containing the value or null if failed
     */
    inline fun <T> runSafely(
        message: String,
        project: Project? = null,
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        showNotification: Boolean = true,
        block: () -> T
    ): Result<T> {
        return try {
            Result.success(block())
        } catch (e: Exception) {
            handleException(e, message, project, category)
            Result.failure(e)
        }
    }

    /**
     * Execute a block safely, returning a default value on failure.
     */
    inline fun <T> runSafelyOrDefault(
        default: T,
        message: String,
        project: Project? = null,
        block: () -> T
    ): T {
        return runSafely(message, project, block = block).getOrDefault(default)
    }

    // Private helper methods

    private fun logError(error: SentinelError) {
        val contextStr = if (error.context.isNotEmpty()) {
            error.context.entries.joinToString(", ") { "${it.key}=${it.value}" }
        } else {
            ""
        }

        val logMessage = buildString {
            append("[${error.category}] ")
            append(error.message)
            if (contextStr.isNotEmpty()) {
                append(" | Context: $contextStr")
            }
        }

        when (error.severity) {
            ErrorSeverity.INFO -> logger.info(logMessage)
            ErrorSeverity.WARNING -> logger.warn(logMessage)
            ErrorSeverity.ERROR -> {
                if (error.exception != null) {
                    logger.error(logMessage, error.exception)
                } else {
                    logger.error(logMessage)
                }
            }
            ErrorSeverity.CRITICAL -> {
                logger.error("CRITICAL: $logMessage", error.exception)
            }
        }
    }

    private fun showNotification(error: SentinelError, project: Project) {
        val notificationType = when (error.severity) {
            ErrorSeverity.INFO -> NotificationType.INFORMATION
            ErrorSeverity.WARNING -> NotificationType.WARNING
            ErrorSeverity.ERROR, ErrorSeverity.CRITICAL -> NotificationType.ERROR
        }

        val title = when (error.category) {
            ErrorCategory.CONFIGURATION -> "Configuration Error"
            ErrorCategory.NETWORK -> "Network Error"
            ErrorCategory.ANALYSIS -> "Analysis Error"
            ErrorCategory.IO -> "File Error"
            ErrorCategory.PATTERN -> "Pattern Error"
            ErrorCategory.SERVICE -> "Service Error"
            ErrorCategory.UNKNOWN -> "Error"
        }

        try {
            NotificationGroupManager.getInstance()
                .getNotificationGroup(NOTIFICATION_GROUP)
                .createNotification(
                    title,
                    error.message,
                    notificationType
                )
                .notify(project)
        } catch (e: Exception) {
            // Fallback if notification group doesn't exist
            logger.warn("Failed to show notification: ${e.message}")
        }
    }

    private fun formatMessage(message: String, context: Map<String, Any?>): String {
        return if (context.isEmpty()) {
            message
        } else {
            val contextStr = context.entries.joinToString(", ") { "${it.key}=${it.value}" }
            "$message | $contextStr"
        }
    }

    private fun detectCategory(exception: Throwable): ErrorCategory {
        return when (exception) {
            is java.io.IOException -> ErrorCategory.IO
            is java.net.SocketException,
            is java.net.UnknownHostException,
            is java.net.ConnectException -> ErrorCategory.NETWORK
            is IllegalArgumentException,
            is IllegalStateException -> ErrorCategory.CONFIGURATION
            is PatternSyntaxException -> ErrorCategory.PATTERN
            else -> ErrorCategory.UNKNOWN
        }
    }

    private fun detectSeverity(exception: Throwable): ErrorSeverity {
        return when (exception) {
            is OutOfMemoryError,
            is StackOverflowError -> ErrorSeverity.CRITICAL
            is SecurityException,
            is IllegalAccessException -> ErrorSeverity.ERROR
            else -> ErrorSeverity.ERROR
        }
    }
}
