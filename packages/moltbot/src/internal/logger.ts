/**
 * @sentinelseed/moltbot - Internal Logger
 *
 * Provides structured logging for internal operations.
 * Supports custom logger injection for integration with external logging systems.
 *
 * @example
 * ```typescript
 * import { logger, setLogger } from './logger';
 *
 * // Use default logger
 * logger.info('Validation started', { content: '...' });
 *
 * // Inject custom logger
 * setLogger({
 *   debug: (msg, ctx) => myLogger.debug(msg, ctx),
 *   info: (msg, ctx) => myLogger.info(msg, ctx),
 *   warn: (msg, ctx) => myLogger.warn(msg, ctx),
 *   error: (msg, ctx) => myLogger.error(msg, ctx),
 * });
 * ```
 */

// =============================================================================
// Types
// =============================================================================

/**
 * Log level severity.
 */
export type LogLevel = 'debug' | 'info' | 'warn' | 'error' | 'silent';

/**
 * Context object for structured logging.
 */
export interface LogContext {
  /** Operation being performed */
  operation?: string;
  /** Duration in milliseconds */
  durationMs?: number;
  /** Number of issues detected */
  issueCount?: number;
  /** Risk level */
  riskLevel?: string;
  /** Whether action was blocked */
  blocked?: boolean;
  /** Error details */
  error?: Error | string;
  /** Tool name */
  toolName?: string;
  /** Content length (never log actual content) */
  contentLength?: number;
  /** Additional metadata */
  [key: string]: unknown;
}

/**
 * Logger interface that can be implemented by external loggers.
 */
export interface Logger {
  debug(message: string, context?: LogContext): void;
  info(message: string, context?: LogContext): void;
  warn(message: string, context?: LogContext): void;
  error(message: string, context?: LogContext): void;
}

/**
 * Logger configuration options.
 */
export interface LoggerConfig {
  /** Minimum log level to output */
  level: LogLevel;
  /** Whether to include timestamps */
  timestamps: boolean;
  /** Prefix for all log messages */
  prefix: string;
  /** Whether logging is enabled */
  enabled: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const LOG_LEVEL_PRIORITY: Record<LogLevel, number> = {
  debug: 0,
  info: 1,
  warn: 2,
  error: 3,
  silent: 4,
};

const DEFAULT_CONFIG: LoggerConfig = {
  level: 'warn',
  timestamps: true,
  prefix: '[sentinel]',
  enabled: true,
};

// =============================================================================
// Internal State
// =============================================================================

let currentConfig: LoggerConfig = { ...DEFAULT_CONFIG };
let customLogger: Logger | null = null;

// =============================================================================
// Default Logger Implementation
// =============================================================================

/**
 * Format a log message with timestamp and prefix.
 */
function formatMessage(level: LogLevel, message: string): string {
  const parts: string[] = [];

  if (currentConfig.timestamps) {
    parts.push(new Date().toISOString());
  }

  parts.push(currentConfig.prefix);
  parts.push(`[${level.toUpperCase()}]`);
  parts.push(message);

  return parts.join(' ');
}

/**
 * Format context for output (redact sensitive data).
 */
function formatContext(context?: LogContext): string {
  if (!context) return '';

  // Create a safe copy without potentially sensitive data
  const safeContext: Record<string, unknown> = {};

  for (const [key, value] of Object.entries(context)) {
    // Skip null/undefined
    if (value === null || value === undefined) continue;

    // Redact any values that look like secrets
    if (typeof value === 'string' && value.length > 20) {
      // Truncate long strings
      safeContext[key] = value.substring(0, 20) + '...';
    } else if (value instanceof Error) {
      safeContext[key] = {
        name: value.name,
        message: value.message,
      };
    } else {
      safeContext[key] = value;
    }
  }

  return Object.keys(safeContext).length > 0
    ? ` ${JSON.stringify(safeContext)}`
    : '';
}

/**
 * Check if a log level should be output based on current config.
 */
function shouldLog(level: LogLevel): boolean {
  if (!currentConfig.enabled) return false;
  return LOG_LEVEL_PRIORITY[level] >= LOG_LEVEL_PRIORITY[currentConfig.level];
}

/**
 * Default logger that outputs to console.
 */
const defaultLogger: Logger = {
  debug(message: string, context?: LogContext): void {
    if (!shouldLog('debug')) return;
    console.debug(formatMessage('debug', message) + formatContext(context));
  },

  info(message: string, context?: LogContext): void {
    if (!shouldLog('info')) return;
    console.info(formatMessage('info', message) + formatContext(context));
  },

  warn(message: string, context?: LogContext): void {
    if (!shouldLog('warn')) return;
    console.warn(formatMessage('warn', message) + formatContext(context));
  },

  error(message: string, context?: LogContext): void {
    if (!shouldLog('error')) return;
    console.error(formatMessage('error', message) + formatContext(context));
  },
};

// =============================================================================
// Public API
// =============================================================================

/**
 * The active logger instance.
 * Uses custom logger if set, otherwise falls back to default.
 */
export const logger: Logger = {
  debug(message: string, context?: LogContext): void {
    (customLogger ?? defaultLogger).debug(message, context);
  },

  info(message: string, context?: LogContext): void {
    (customLogger ?? defaultLogger).info(message, context);
  },

  warn(message: string, context?: LogContext): void {
    (customLogger ?? defaultLogger).warn(message, context);
  },

  error(message: string, context?: LogContext): void {
    (customLogger ?? defaultLogger).error(message, context);
  },
};

/**
 * Set a custom logger implementation.
 *
 * @param newLogger - Custom logger or null to reset to default
 */
export function setLogger(newLogger: Logger | null): void {
  customLogger = newLogger;
}

/**
 * Get the current logger configuration.
 */
export function getLoggerConfig(): Readonly<LoggerConfig> {
  return { ...currentConfig };
}

/**
 * Update logger configuration.
 *
 * @param config - Partial configuration to merge
 */
export function configureLogger(config: Partial<LoggerConfig>): void {
  currentConfig = {
    ...currentConfig,
    ...config,
  };
}

/**
 * Reset logger to defaults.
 */
export function resetLogger(): void {
  customLogger = null;
  currentConfig = { ...DEFAULT_CONFIG };
}

/**
 * Create a child logger with a specific operation context.
 * Useful for adding context to all logs within a scope.
 *
 * @param operation - Operation name to include in all logs
 * @returns Logger bound to the operation context
 */
export function createChildLogger(operation: string): Logger {
  return {
    debug(message: string, context?: LogContext): void {
      logger.debug(message, { operation, ...context });
    },
    info(message: string, context?: LogContext): void {
      logger.info(message, { operation, ...context });
    },
    warn(message: string, context?: LogContext): void {
      logger.warn(message, { operation, ...context });
    },
    error(message: string, context?: LogContext): void {
      logger.error(message, { operation, ...context });
    },
  };
}

// =============================================================================
// Specialized Logging Functions
// =============================================================================

/**
 * Log a validation operation result.
 */
export function logValidation(
  type: 'input' | 'output' | 'tool',
  result: {
    safe: boolean;
    blocked?: boolean;
    issueCount: number;
    riskLevel: string;
    durationMs: number;
  },
  context?: LogContext
): void {
  const level = result.blocked ? 'warn' : result.safe ? 'debug' : 'info';
  const action = result.blocked ? 'blocked' : result.safe ? 'passed' : 'flagged';

  logger[level](`${type} validation ${action}`, {
    operation: `validate_${type}`,
    ...result,
    ...context,
  });
}

/**
 * Log an error with full context.
 */
export function logError(
  operation: string,
  error: Error | string,
  context?: LogContext
): void {
  logger.error(`Error in ${operation}`, {
    operation,
    error,
    ...context,
  });
}

/**
 * Log performance metrics.
 */
export function logPerformance(
  operation: string,
  durationMs: number,
  context?: LogContext
): void {
  // Only log slow operations (>100ms)
  if (durationMs > 100) {
    logger.warn(`Slow operation: ${operation}`, {
      operation,
      durationMs,
      ...context,
    });
  } else {
    logger.debug(`Performance: ${operation}`, {
      operation,
      durationMs,
      ...context,
    });
  }
}
