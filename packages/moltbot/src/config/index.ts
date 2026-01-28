/**
 * @sentinelseed/moltbot - Configuration Module
 *
 * This module provides level presets, configuration parsing,
 * and default values for Sentinel Moltbot integration.
 *
 * @example
 * ```typescript
 * import { LEVELS, parseConfig, getLevelConfig } from '@sentinelseed/moltbot/config';
 *
 * // Parse user configuration
 * const config = parseConfig({ level: 'guard' });
 *
 * // Get level-specific configuration
 * const levelConfig = getLevelConfig(config.level, config.custom);
 * ```
 */

// =============================================================================
// Default Configuration
// =============================================================================

export {
  DEFAULT_CONFIG,
  getDefaultConfig,
  DEFAULT_BLOCKING_CONFIG,
  DEFAULT_ALERTING_CONFIG,
} from './defaults';

// =============================================================================
// Level Presets
// =============================================================================

export {
  // Individual levels
  OFF_LEVEL,
  WATCH_LEVEL,
  GUARD_LEVEL,
  SHIELD_LEVEL,
  // Level collection
  LEVELS,
  LEVEL_ORDER,
  // Level utilities
  isValidLevel,
  getBaseLevel,
  compareLevels,
  isMoreProtective,
  getBlockingConfig,
  getAlertingConfig,
} from './levels';

// =============================================================================
// Configuration Parsing
// =============================================================================

export {
  parseConfig,
  getLevelConfig,
  validateConfig,
} from './parser';

// =============================================================================
// Type Exports
// =============================================================================

export type {
  ProtectionLevel,
  LevelConfig,
  BlockingConfig,
  AlertingConfig,
  SentinelMoltbotConfig,
  SeedTemplate,
  LogLevel,
  AlertsConfig,
} from '../types';
