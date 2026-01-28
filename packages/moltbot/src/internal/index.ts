/**
 * @sentinelseed/moltbot - Internal Utilities
 *
 * Internal modules for logging, metrics, and pattern management.
 * These are not part of the public API but can be used for advanced customization.
 */

// Logger
export {
  logger,
  setLogger,
  getLoggerConfig,
  configureLogger,
  resetLogger,
  createChildLogger,
  logValidation,
  logError,
  logPerformance,
  type LogLevel,
  type LogContext,
  type Logger,
  type LoggerConfig,
} from './logger';

// Metrics
export {
  metrics,
  getMetricsSnapshot,
  resetMetrics,
  getAverageValidationTime,
  getBlockRate,
  getPassRate,
  getMostCommonIssueType,
  getMetricsSummary,
  type TimingStats,
  type ValidationStats,
  type IssueStats,
  type MetricsSnapshot,
} from './metrics';

// Pattern Registry
export {
  patternRegistry,
  type PatternCategory,
  type PatternEntry,
  type RegistrySnapshot,
} from './pattern-registry';
