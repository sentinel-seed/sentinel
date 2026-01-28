/**
 * @sentinelseed/moltbot - Pattern Definitions
 *
 * This module re-exports and extends patterns from @sentinelseed/core.
 * It also provides access to the extensible pattern registry for Moltbot-specific patterns.
 *
 * Architecture:
 * - Core patterns (jailbreak, harm, etc.) come from @sentinelseed/core
 * - Tool/path/URL patterns are managed by the internal PatternRegistry
 * - The registry allows runtime extension of patterns
 *
 * @example
 * ```typescript
 * import { isDangerousTool, isRestrictedPath, patternRegistry } from './patterns';
 *
 * // Use built-in checks
 * if (isDangerousTool('rm')) { ... }
 *
 * // Extend patterns at runtime
 * patternRegistry.addPattern('dangerousTool', 'my_risky_tool');
 * ```
 */

import {
  // Core patterns (re-exported for convenience)
  SENSITIVE_DATA_PATTERNS,
  ALL_JAILBREAK_PATTERNS,
  HARM_PATTERNS,
  // Gate-specific checkers
  validateTHSP,
  checkJailbreak,
  checkHarm,
  quickCheck,
  type GateResult,
  type THSPResult,
} from '@sentinelseed/core';

import {
  patternRegistry,
  type PatternEntry,
  type PatternCategory,
} from '../internal/pattern-registry';
import { logger } from '../internal/logger';

// =============================================================================
// Re-exports from Core
// =============================================================================

export {
  // Pattern collections
  SENSITIVE_DATA_PATTERNS,
  ALL_JAILBREAK_PATTERNS,
  HARM_PATTERNS,
  // Validators
  validateTHSP,
  checkJailbreak,
  checkHarm,
  quickCheck,
  // Types
  type GateResult,
  type THSPResult,
};

// =============================================================================
// Re-export Pattern Registry
// =============================================================================

export { patternRegistry, type PatternEntry, type PatternCategory };

// =============================================================================
// Legacy Constants (for backwards compatibility)
// =============================================================================

/**
 * Dangerous tool names that should always be flagged.
 * @deprecated Use patternRegistry.isDangerousTool() instead
 */
export const DANGEROUS_TOOL_NAMES = [
  'rm', 'rmdir', 'del', 'deltree', 'format',
  'drop_table', 'drop_database', 'truncate_table',
  'shutdown', 'reboot', 'halt',
  'ddos', 'flood', 'spam',
] as const;

/**
 * Tool parameter patterns that indicate dangerous operations.
 * @deprecated Use patternRegistry for pattern matching
 */
export const DANGEROUS_TOOL_PARAMS: Record<string, RegExp[]> = {
  file: [
    /\brm\s+-rf\s+\//i,
    /\brm\s+--no-preserve-root/i,
    /\bdel\s+\/[fFsS]/i,
    /\bformat\s+[a-zA-Z]:/i,
  ],
  database: [
    /DROP\s+(TABLE|DATABASE)/i,
    /TRUNCATE\s+TABLE/i,
    /DELETE\s+FROM\s+\w+\s+WHERE\s+1\s*=\s*1/i,
  ],
  command: [
    /;\s*(rm|del|format|shutdown)/i,
    /\|\s*(rm|del|format|shutdown)/i,
    /`(rm|del|format|shutdown)/i,
    /\$\((rm|del|format|shutdown)/i,
  ],
  path: [
    /\.\.\//g,
    /\.\.\\/,
    /\/etc\/(passwd|shadow|sudoers)/i,
    /\/root\//i,
    /~\/\.ssh\//i,
    /C:\\Windows\\System32/i,
  ],
};

/**
 * System paths that should never be accessed.
 * @deprecated Use patternRegistry.isRestrictedPath() instead
 */
export const RESTRICTED_PATHS = [
  '/etc/passwd', '/etc/shadow', '/etc/sudoers', '/etc/ssh/',
  '/root/', '~/.ssh/',
  'C:\\Windows\\System32\\config', 'C:\\Windows\\System32\\drivers\\etc',
  '.env', '.env.local', '.env.production',
  'credentials.json', 'service-account.json',
  'id_rsa', 'id_ed25519',
] as const;

/**
 * URL patterns that indicate suspicious destinations.
 * @deprecated Use patternRegistry.isSuspiciousUrl() instead
 */
export const SUSPICIOUS_URL_PATTERNS = [
  /\b(login|signin|account|verify|secure|update)[-_.]?(bank|paypal|amazon|google|microsoft)/i,
  /https?:\/\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/,
  /\b(bit\.ly|tinyurl|goo\.gl|t\.co|ow\.ly)\/\w+/i,
  /\?.*=(api_key|token|password|secret|credential)/i,
] as const;

// =============================================================================
// Pattern Matching Functions (use registry internally)
// =============================================================================

/**
 * Check if content matches any pattern in a collection.
 *
 * @param content - Content to check
 * @param patterns - Array of RegExp patterns
 * @returns True if any pattern matches
 */
export function matchesAnyPattern(content: string, patterns: readonly RegExp[]): boolean {
  if (!content || typeof content !== 'string') return false;

  try {
    return patterns.some(pattern => pattern.test(content));
  } catch (error) {
    logger.error('Pattern match error', {
      operation: 'matchesAnyPattern',
      error: error instanceof Error ? error : String(error),
    });
    return false;
  }
}

/**
 * Find all matching patterns in content.
 *
 * @param content - Content to check
 * @param patterns - Array of RegExp patterns
 * @returns Array of matching patterns
 */
export function findMatchingPatterns(content: string, patterns: readonly RegExp[]): RegExp[] {
  if (!content || typeof content !== 'string') return [];

  try {
    return patterns.filter(pattern => pattern.test(content));
  } catch (error) {
    logger.error('Pattern find error', {
      operation: 'findMatchingPatterns',
      error: error instanceof Error ? error : String(error),
    });
    return [];
  }
}

/**
 * Check if a string matches any item in a list (case-insensitive).
 *
 * @param value - Value to check
 * @param list - List of strings to match against
 * @returns True if value matches any item
 */
export function matchesAnyString(value: string, list: readonly string[]): boolean {
  if (!value || typeof value !== 'string') return false;
  if (!list || list.length === 0) return false;

  const lowerValue = value.toLowerCase();
  return list.some(item => item.toLowerCase() === lowerValue);
}

/**
 * Check if a path is restricted.
 * Uses the pattern registry for matching.
 *
 * @param path - Path to check
 * @returns True if path is restricted
 */
export function isRestrictedPath(path: string): boolean {
  if (!path || typeof path !== 'string') return false;

  try {
    // Normalize path for comparison
    const normalizedPath = path.toLowerCase().replace(/\\/g, '/');

    // Use registry
    if (patternRegistry.isRestrictedPath(normalizedPath)) {
      logger.debug('Restricted path detected', {
        operation: 'isRestrictedPath',
        contentLength: path.length,
      });
      return true;
    }

    // Also check legacy patterns for backwards compatibility
    return RESTRICTED_PATHS.some(restricted => {
      const normalizedRestricted = restricted.toLowerCase().replace(/\\/g, '/');
      return normalizedPath.includes(normalizedRestricted);
    });
  } catch (error) {
    logger.error('Path check error', {
      operation: 'isRestrictedPath',
      error: error instanceof Error ? error : String(error),
    });
    return false;
  }
}

/**
 * Check if a URL is suspicious.
 * Uses the pattern registry for matching.
 *
 * @param url - URL to check
 * @returns True if URL is suspicious
 */
export function isSuspiciousUrl(url: string): boolean {
  if (!url || typeof url !== 'string') return false;

  try {
    // Use registry first
    if (patternRegistry.isSuspiciousUrl(url)) {
      logger.debug('Suspicious URL detected', {
        operation: 'isSuspiciousUrl',
        contentLength: url.length,
      });
      return true;
    }

    // Also check legacy patterns
    return SUSPICIOUS_URL_PATTERNS.some(pattern => pattern.test(url));
  } catch (error) {
    logger.error('URL check error', {
      operation: 'isSuspiciousUrl',
      error: error instanceof Error ? error : String(error),
    });
    return false;
  }
}

/**
 * Check if a tool name is inherently dangerous.
 * Uses the pattern registry for matching.
 *
 * @param toolName - Tool name to check
 * @returns True if tool is dangerous
 */
export function isDangerousTool(toolName: string): boolean {
  if (!toolName || typeof toolName !== 'string') return false;

  try {
    // Use registry
    if (patternRegistry.isDangerousTool(toolName)) {
      logger.debug('Dangerous tool detected', {
        operation: 'isDangerousTool',
        toolName,
      });
      return true;
    }

    // Also check legacy list
    return matchesAnyString(toolName, DANGEROUS_TOOL_NAMES);
  } catch (error) {
    logger.error('Tool check error', {
      operation: 'isDangerousTool',
      error: error instanceof Error ? error : String(error),
    });
    return false;
  }
}

/**
 * Check tool parameters for dangerous patterns.
 * Uses both registry and legacy patterns.
 *
 * @param params - Tool parameters object
 * @returns Array of detected issues
 */
export function checkToolParams(
  params: Record<string, unknown>
): Array<{ type: string; evidence: string }> {
  const issues: Array<{ type: string; evidence: string }> = [];

  if (!params || typeof params !== 'object') return issues;

  try {
    // Convert params to string for pattern matching
    const paramsStr = safeStringify(params);

    // Check for dangerous commands via registry
    const dangerousCmd = patternRegistry.hasDangerousCommand(paramsStr);
    if (dangerousCmd) {
      issues.push({
        type: 'dangerous_command',
        evidence: truncateEvidence(paramsStr),
      });
    }

    // Check for sensitive data via registry
    const sensitiveData = patternRegistry.hasSensitiveData(paramsStr);
    if (sensitiveData) {
      issues.push({
        type: 'sensitive_data',
        evidence: '[REDACTED]',
      });
    }

    // Check legacy patterns
    for (const [category, patterns] of Object.entries(DANGEROUS_TOOL_PARAMS)) {
      for (const pattern of patterns) {
        const match = paramsStr.match(pattern);
        if (match) {
          issues.push({
            type: `dangerous_${category}`,
            evidence: truncateEvidence(match[0]),
          });
        }
      }
    }

    // Check for restricted paths in string values
    for (const [key, value] of Object.entries(params)) {
      if (typeof value === 'string') {
        if (isRestrictedPath(value)) {
          issues.push({
            type: 'restricted_path',
            evidence: `${key}: ${truncateEvidence(value)}`,
          });
        }
        if (isSuspiciousUrl(value)) {
          issues.push({
            type: 'suspicious_url',
            evidence: `${key}: ${truncateEvidence(value)}`,
          });
        }
      }
    }

    if (issues.length > 0) {
      logger.debug('Tool param issues detected', {
        operation: 'checkToolParams',
        issueCount: issues.length,
      });
    }

    return issues;
  } catch (error) {
    logger.error('Tool params check error', {
      operation: 'checkToolParams',
      error: error instanceof Error ? error : String(error),
    });
    return [];
  }
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Safely stringify an object, handling circular references.
 */
function safeStringify(obj: unknown): string {
  try {
    return JSON.stringify(obj);
  } catch {
    // Handle circular references
    return String(obj);
  }
}

/**
 * Truncate evidence string for safe logging.
 */
function truncateEvidence(evidence: string, maxLength = 50): string {
  if (evidence.length <= maxLength) return evidence;
  return evidence.substring(0, maxLength) + '...';
}
