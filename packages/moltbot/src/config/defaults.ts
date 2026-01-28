/**
 * @sentinelseed/moltbot - Default Configuration
 *
 * Default values for plugin configuration.
 * These provide sensible defaults for power users who want zero-friction setup.
 *
 * @example
 * ```typescript
 * import { DEFAULT_CONFIG, getDefaultConfig } from './defaults';
 *
 * const config = { ...DEFAULT_CONFIG, level: 'guard' };
 * ```
 */

import type { SentinelMoltbotConfig } from '../types';

/**
 * Default plugin configuration.
 *
 * - level: 'watch' (monitor only, never block - zero friction)
 * - alerts: enabled by default
 * - no ignored patterns, no trusted/dangerous tools
 */
export const DEFAULT_CONFIG: SentinelMoltbotConfig = {
  level: 'watch',
  alerts: {
    enabled: true,
  },
  ignorePatterns: [],
  trustedTools: [],
  dangerousTools: [],
};

/**
 * Get a fresh copy of the default configuration.
 *
 * This returns a new object each time to prevent accidental mutation.
 *
 * @returns Fresh copy of default configuration
 */
export function getDefaultConfig(): SentinelMoltbotConfig {
  return {
    level: DEFAULT_CONFIG.level,
    alerts: {
      enabled: DEFAULT_CONFIG.alerts?.enabled ?? true,
      webhook: undefined,
    },
    ignorePatterns: [],
    trustedTools: [],
    dangerousTools: [],
  };
}

/**
 * Default blocking configuration (all false - nothing blocked).
 * Used as fallback when no level-specific config is available.
 */
export const DEFAULT_BLOCKING_CONFIG = {
  dataLeaks: false,
  destructiveCommands: false,
  systemPaths: false,
  suspiciousUrls: false,
  injectionCompliance: false,
} as const;

/**
 * Default alerting configuration (all false - no alerts).
 * Used as fallback when no level-specific config is available.
 */
export const DEFAULT_ALERTING_CONFIG = {
  highThreatInput: false,
  blockedActions: false,
  promptInjection: false,
  sessionAnomalies: false,
} as const;
