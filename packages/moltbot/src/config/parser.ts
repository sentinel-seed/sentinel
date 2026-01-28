/**
 * @sentinelseed/moltbot - Configuration Parser
 *
 * Parses, validates, and merges user configuration with defaults.
 *
 * @example
 * ```typescript
 * import { parseConfig, getLevelConfig } from './parser';
 *
 * const config = parseConfig({ level: 'guard' });
 * const levelConfig = getLevelConfig(config.level, config.custom);
 * ```
 */

import type {
  SentinelMoltbotConfig,
  LevelConfig,
  ProtectionLevel,
  AlertsConfig,
} from '../types';
import { DEFAULT_CONFIG } from './defaults';
import { LEVELS, isValidLevel, getBaseLevel } from './levels';

// =============================================================================
// Configuration Parsing
// =============================================================================

/**
 * Parse and validate user configuration.
 *
 * - Validates protection level
 * - Applies defaults for missing values
 * - Normalizes arrays (ensures they're arrays)
 * - Deep merges alert configuration
 *
 * @param userConfig - Partial configuration from user
 * @returns Complete, validated configuration
 */
export function parseConfig(
  userConfig: Partial<SentinelMoltbotConfig>
): SentinelMoltbotConfig {
  // Handle null/undefined input
  const config = userConfig ?? {};

  // Validate and normalize level
  const level = parseLevel(config.level);

  // Parse alerts configuration
  const alerts = parseAlerts(config.alerts);

  // Parse array fields (ensure they're arrays)
  const ignorePatterns = parseStringArray(config.ignorePatterns);
  const trustedTools = parseStringArray(config.trustedTools);
  const dangerousTools = parseStringArray(config.dangerousTools);

  // Parse custom level overrides
  const custom = parseCustomOverrides(config.custom);

  return {
    level,
    alerts,
    ignorePatterns,
    trustedTools,
    dangerousTools,
    custom,
  };
}

/**
 * Get the level configuration for a protection level with optional custom overrides.
 *
 * This is the main function for getting complete level configuration.
 * It takes the base level config and deep merges any custom overrides.
 *
 * @param level - Protection level
 * @param custom - Optional custom overrides
 * @returns Complete level configuration
 */
export function getLevelConfig(
  level: ProtectionLevel,
  custom?: Partial<LevelConfig>
): LevelConfig {
  const base = getBaseLevel(level);

  if (!custom) {
    // Return a copy to prevent mutation
    return {
      ...base,
      blocking: { ...base.blocking },
      alerting: { ...base.alerting },
    };
  }

  // Deep merge with custom overrides
  return {
    level: custom.level ?? base.level,
    blocking: {
      ...base.blocking,
      ...custom.blocking,
    },
    alerting: {
      ...base.alerting,
      ...custom.alerting,
    },
    seedTemplate: custom.seedTemplate ?? base.seedTemplate,
    logLevel: custom.logLevel ?? base.logLevel,
  };
}

// =============================================================================
// Field Parsers
// =============================================================================

/**
 * Parse and validate protection level.
 *
 * @param value - User-provided level value
 * @returns Valid protection level (defaults to 'watch')
 */
function parseLevel(value: unknown): ProtectionLevel {
  if (isValidLevel(value)) {
    return value;
  }
  return DEFAULT_CONFIG.level;
}

/**
 * Parse alerts configuration.
 *
 * @param value - User-provided alerts config
 * @returns Normalized alerts configuration
 */
function parseAlerts(value: unknown): AlertsConfig {
  if (!value || typeof value !== 'object') {
    return {
      enabled: DEFAULT_CONFIG.alerts?.enabled ?? true,
    };
  }

  const obj = value as Record<string, unknown>;

  return {
    enabled: typeof obj.enabled === 'boolean' ? obj.enabled : true,
    webhook: typeof obj.webhook === 'string' ? obj.webhook : undefined,
  };
}

/**
 * Parse a string array field.
 *
 * - If undefined/null, returns empty array
 * - If already an array, filters to only strings
 * - If single string, wraps in array
 *
 * @param value - User-provided value
 * @returns Normalized string array
 */
function parseStringArray(value: unknown): string[] {
  if (value === undefined || value === null) {
    return [];
  }

  if (Array.isArray(value)) {
    return value.filter((item): item is string => typeof item === 'string');
  }

  if (typeof value === 'string') {
    return [value];
  }

  return [];
}

/**
 * Parse custom level overrides.
 *
 * Validates and normalizes custom blocking/alerting overrides.
 *
 * @param value - User-provided custom overrides
 * @returns Normalized custom overrides (or undefined if invalid)
 */
function parseCustomOverrides(
  value: unknown
): Partial<LevelConfig> | undefined {
  if (!value || typeof value !== 'object') {
    return undefined;
  }

  const obj = value as Record<string, unknown>;
  const result: Partial<LevelConfig> = {};
  let hasValidField = false;

  // Parse blocking overrides
  if (obj.blocking && typeof obj.blocking === 'object') {
    const blocking = parseBlockingOverrides(obj.blocking as Record<string, unknown>);
    if (Object.keys(blocking).length > 0) {
      (result as Record<string, unknown>).blocking = blocking;
      hasValidField = true;
    }
  }

  // Parse alerting overrides
  if (obj.alerting && typeof obj.alerting === 'object') {
    const alerting = parseAlertingOverrides(obj.alerting as Record<string, unknown>);
    if (Object.keys(alerting).length > 0) {
      (result as Record<string, unknown>).alerting = alerting;
      hasValidField = true;
    }
  }

  // Parse seedTemplate
  if (obj.seedTemplate && isSeedTemplate(obj.seedTemplate)) {
    result.seedTemplate = obj.seedTemplate;
    hasValidField = true;
  }

  // Parse logLevel
  if (obj.logLevel && isLogLevel(obj.logLevel)) {
    result.logLevel = obj.logLevel;
    hasValidField = true;
  }

  return hasValidField ? result : undefined;
}

/**
 * Parse blocking configuration overrides.
 */
function parseBlockingOverrides(obj: Record<string, unknown>): Partial<LevelConfig['blocking']> {
  const result: Partial<LevelConfig['blocking']> = {};

  if (typeof obj.dataLeaks === 'boolean') {
    result.dataLeaks = obj.dataLeaks;
  }
  if (typeof obj.destructiveCommands === 'boolean') {
    result.destructiveCommands = obj.destructiveCommands;
  }
  if (typeof obj.systemPaths === 'boolean') {
    result.systemPaths = obj.systemPaths;
  }
  if (typeof obj.suspiciousUrls === 'boolean') {
    result.suspiciousUrls = obj.suspiciousUrls;
  }
  if (typeof obj.injectionCompliance === 'boolean') {
    result.injectionCompliance = obj.injectionCompliance;
  }

  return result;
}

/**
 * Parse alerting configuration overrides.
 */
function parseAlertingOverrides(obj: Record<string, unknown>): Partial<LevelConfig['alerting']> {
  const result: Partial<LevelConfig['alerting']> = {};

  if (typeof obj.highThreatInput === 'boolean') {
    result.highThreatInput = obj.highThreatInput;
  }
  if (typeof obj.blockedActions === 'boolean') {
    result.blockedActions = obj.blockedActions;
  }
  if (typeof obj.promptInjection === 'boolean') {
    result.promptInjection = obj.promptInjection;
  }
  if (typeof obj.sessionAnomalies === 'boolean') {
    result.sessionAnomalies = obj.sessionAnomalies;
  }

  return result;
}

// =============================================================================
// Type Guards
// =============================================================================

/**
 * Check if a value is a valid seed template.
 */
function isSeedTemplate(value: unknown): value is LevelConfig['seedTemplate'] {
  return value === 'none' || value === 'standard' || value === 'strict';
}

/**
 * Check if a value is a valid log level.
 */
function isLogLevel(value: unknown): value is LevelConfig['logLevel'] {
  return value === 'none' || value === 'blocked' || value === 'warnings' || value === 'all';
}

// =============================================================================
// Validation Utilities
// =============================================================================

/**
 * Validate a complete configuration object.
 *
 * Returns a list of validation errors (empty if valid).
 *
 * @param config - Configuration to validate
 * @returns Array of validation error messages
 */
export function validateConfig(config: SentinelMoltbotConfig): string[] {
  const errors: string[] = [];

  // Validate level
  if (!isValidLevel(config.level)) {
    errors.push(`Invalid level: ${config.level}. Must be one of: off, watch, guard, shield`);
  }

  // Validate alerts webhook (if provided)
  if (config.alerts?.webhook) {
    if (!isValidUrl(config.alerts.webhook)) {
      errors.push(`Invalid alerts webhook URL: ${config.alerts.webhook}`);
    }
  }

  // Validate pattern arrays
  if (!Array.isArray(config.ignorePatterns)) {
    errors.push('ignorePatterns must be an array');
  }
  if (!Array.isArray(config.trustedTools)) {
    errors.push('trustedTools must be an array');
  }
  if (!Array.isArray(config.dangerousTools)) {
    errors.push('dangerousTools must be an array');
  }

  return errors;
}

/**
 * Check if a string is a valid URL.
 */
function isValidUrl(value: string): boolean {
  try {
    new URL(value);
    return true;
  } catch {
    return false;
  }
}
