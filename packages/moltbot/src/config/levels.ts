/**
 * @sentinelseed/moltbot - Protection Level Presets
 *
 * Defines the four protection levels: off, watch, guard, shield.
 *
 * Design Philosophy:
 * - off: Complete bypass, useful for debugging
 * - watch: Monitor and alert only, NEVER block (default for power users)
 * - guard: Block critical threats (data leaks, destructive commands)
 * - shield: Maximum protection, strict mode
 *
 * @example
 * ```typescript
 * import { LEVELS, WATCH_LEVEL } from './levels';
 *
 * const config = LEVELS['guard'];
 * ```
 */

import type { ProtectionLevel, LevelConfig, BlockingConfig, AlertingConfig } from '../types';

// =============================================================================
// Level Presets
// =============================================================================

/**
 * OFF level - Sentinel disabled.
 *
 * Use this for debugging or when you need to temporarily disable
 * all monitoring. No validation, no alerts, no blocking.
 */
export const OFF_LEVEL: LevelConfig = {
  level: 'off',
  blocking: {
    dataLeaks: false,
    destructiveCommands: false,
    systemPaths: false,
    suspiciousUrls: false,
    injectionCompliance: false,
  },
  alerting: {
    highThreatInput: false,
    blockedActions: false,
    promptInjection: false,
    sessionAnomalies: false,
  },
  seedTemplate: 'none',
  logLevel: 'none',
};

/**
 * WATCH level - Monitor and alert only, never block.
 *
 * This is the DEFAULT level designed for power users.
 * - Monitors all activity
 * - Sends alerts for threats
 * - NEVER blocks anything
 * - Uses standard seed for guidance
 *
 * Philosophy: Trust the user, but keep them informed.
 */
export const WATCH_LEVEL: LevelConfig = {
  level: 'watch',
  blocking: {
    dataLeaks: false,
    destructiveCommands: false,
    systemPaths: false,
    suspiciousUrls: false,
    injectionCompliance: false,
  },
  alerting: {
    highThreatInput: true,
    blockedActions: false, // Nothing to block
    promptInjection: true,
    sessionAnomalies: true,
  },
  seedTemplate: 'standard',
  logLevel: 'all',
};

/**
 * GUARD level - Block critical threats.
 *
 * Recommended for environments with sensitive data.
 * - Blocks data leaks (API keys, passwords)
 * - Blocks destructive commands (rm -rf, DROP TABLE)
 * - Blocks access to system paths
 * - Still allows most normal operations
 */
export const GUARD_LEVEL: LevelConfig = {
  level: 'guard',
  blocking: {
    dataLeaks: true,
    destructiveCommands: true,
    systemPaths: true,
    suspiciousUrls: false,
    injectionCompliance: false,
  },
  alerting: {
    highThreatInput: true,
    blockedActions: true,
    promptInjection: true,
    sessionAnomalies: true,
  },
  seedTemplate: 'standard',
  logLevel: 'all',
};

/**
 * SHIELD level - Maximum protection.
 *
 * For high-security workflows where safety is paramount.
 * - Blocks all known threats
 * - Blocks suspicious URLs
 * - Blocks injection compliance (AI following injected instructions)
 * - Uses strict seed with THSP enforcement
 */
export const SHIELD_LEVEL: LevelConfig = {
  level: 'shield',
  blocking: {
    dataLeaks: true,
    destructiveCommands: true,
    systemPaths: true,
    suspiciousUrls: true,
    injectionCompliance: true,
  },
  alerting: {
    highThreatInput: true,
    blockedActions: true,
    promptInjection: true,
    sessionAnomalies: true,
  },
  seedTemplate: 'strict',
  logLevel: 'all',
};

/**
 * Level presets indexed by protection level name.
 */
export const LEVELS: Record<ProtectionLevel, LevelConfig> = {
  off: OFF_LEVEL,
  watch: WATCH_LEVEL,
  guard: GUARD_LEVEL,
  shield: SHIELD_LEVEL,
};

/**
 * Ordered list of protection levels from least to most protective.
 */
export const LEVEL_ORDER: readonly ProtectionLevel[] = ['off', 'watch', 'guard', 'shield'];

/**
 * Check if a string is a valid protection level.
 *
 * @param value - String to check
 * @returns True if valid protection level
 */
export function isValidLevel(value: unknown): value is ProtectionLevel {
  return typeof value === 'string' && LEVEL_ORDER.includes(value as ProtectionLevel);
}

/**
 * Get the level configuration for a protection level.
 *
 * Returns the base configuration without any custom overrides.
 * Use `getLevelConfig` from parser.ts if you need custom overrides.
 *
 * @param level - Protection level
 * @returns Level configuration
 */
export function getBaseLevel(level: ProtectionLevel): LevelConfig {
  const config = LEVELS[level];
  if (!config) {
    // Fallback to watch if somehow an invalid level gets through
    return WATCH_LEVEL;
  }
  return config;
}

/**
 * Compare two protection levels.
 *
 * @param a - First level
 * @param b - Second level
 * @returns Negative if a < b, positive if a > b, 0 if equal
 */
export function compareLevels(a: ProtectionLevel, b: ProtectionLevel): number {
  return LEVEL_ORDER.indexOf(a) - LEVEL_ORDER.indexOf(b);
}

/**
 * Check if level A is more protective than level B.
 *
 * @param a - First level
 * @param b - Second level
 * @returns True if a is more protective than b
 */
export function isMoreProtective(a: ProtectionLevel, b: ProtectionLevel): boolean {
  return compareLevels(a, b) > 0;
}

/**
 * Get blocking configuration for a level.
 * Useful when you only need blocking info without full level config.
 *
 * @param level - Protection level
 * @returns Blocking configuration
 */
export function getBlockingConfig(level: ProtectionLevel): BlockingConfig {
  return { ...getBaseLevel(level).blocking };
}

/**
 * Get alerting configuration for a level.
 * Useful when you only need alerting info without full level config.
 *
 * @param level - Protection level
 * @returns Alerting configuration
 */
export function getAlertingConfig(level: ProtectionLevel): AlertingConfig {
  return { ...getBaseLevel(level).alerting };
}
