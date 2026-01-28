/**
 * @sentinelseed/moltbot - Pattern Registry
 *
 * Extensible registry for security patterns.
 * Allows adding, removing, and validating custom patterns at runtime.
 *
 * @example
 * ```typescript
 * import { patternRegistry } from './pattern-registry';
 *
 * // Add a custom pattern
 * patternRegistry.addPattern('dangerousTool', 'my_risky_tool');
 *
 * // Check if registered
 * patternRegistry.hasPattern('dangerousTool', 'my_risky_tool'); // true
 *
 * // Add a custom regex pattern
 * patternRegistry.addRegexPattern('suspiciousUrl', /evil\.com/i);
 * ```
 */

import { logger } from './logger';

// =============================================================================
// Types
// =============================================================================

/**
 * Pattern categories supported by the registry.
 */
export type PatternCategory =
  | 'dangerousTool'
  | 'restrictedPath'
  | 'suspiciousUrl'
  | 'dangerousCommand'
  | 'sensitiveData';

/**
 * Pattern entry in the registry.
 */
export interface PatternEntry {
  /** The pattern (string for exact match, RegExp for regex) */
  pattern: string | RegExp;
  /** Description of what this pattern detects */
  description?: string;
  /** Severity when matched */
  severity?: 'low' | 'medium' | 'high' | 'critical';
  /** Whether this is a built-in pattern */
  builtin: boolean;
  /** When this pattern was added */
  addedAt: number;
}

/**
 * Registry state snapshot.
 */
export interface RegistrySnapshot {
  categories: {
    [K in PatternCategory]: {
      stringPatterns: string[];
      regexPatterns: number; // count only, regexes aren't serializable
      totalEntries: number;
    };
  };
}

// =============================================================================
// Built-in Patterns
// =============================================================================

/**
 * Built-in dangerous tool names.
 * These tools can cause irreversible damage.
 */
const BUILTIN_DANGEROUS_TOOLS: readonly string[] = [
  // File system destruction
  'rm', 'rmdir', 'del', 'deltree', 'format', 'shred',
  // Database destruction
  'drop_table', 'drop_database', 'truncate_table', 'drop_collection',
  // System modification
  'shutdown', 'reboot', 'halt', 'poweroff', 'init',
  // Network attacks
  'ddos', 'flood', 'spam', 'nmap', 'masscan',
  // Privilege escalation
  'sudo', 'su', 'runas', 'doas',
];

/**
 * Built-in restricted paths.
 * Access to these should be flagged or blocked.
 */
const BUILTIN_RESTRICTED_PATHS: readonly string[] = [
  // Unix credentials
  '/etc/passwd', '/etc/shadow', '/etc/sudoers', '/etc/master.passwd',
  // SSH keys
  '/etc/ssh/', '~/.ssh/', '.ssh/id_rsa', '.ssh/id_ed25519', '.ssh/id_ecdsa',
  // Root directories
  '/root/', '/var/root/',
  // Windows sensitive paths
  'C:\\Windows\\System32\\config',
  'C:\\Windows\\System32\\drivers\\etc',
  'C:\\Users\\Administrator',
  // Environment and secrets
  '.env', '.env.local', '.env.production', '.env.development',
  'credentials.json', 'service-account.json', 'secrets.json',
  '.npmrc', '.pypirc', '.docker/config.json',
  // Git credentials
  '.git-credentials', '.gitconfig',
  // AWS/Cloud credentials
  '.aws/credentials', '.aws/config',
  '.azure/credentials', '.gcloud/credentials',
];

/**
 * Built-in suspicious URL patterns.
 */
const BUILTIN_SUSPICIOUS_URLS: readonly RegExp[] = [
  // IP addresses (often malicious)
  /^https?:\/\/\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}/,
  // Private IP ranges
  /^https?:\/\/(?:10\.|172\.(?:1[6-9]|2\d|3[01])\.|192\.168\.)/,
  // Localhost (exfiltration attempt)
  /^https?:\/\/(?:localhost|127\.0\.0\.1|0\.0\.0\.0)/,
  // Known shorteners (can hide destination)
  /\b(?:bit\.ly|tinyurl\.com|goo\.gl|t\.co|ow\.ly|is\.gd|buff\.ly)\/\w+/i,
  // Phishing indicators
  /\b(?:login|signin|account|verify|secure|update)[-_.]?(?:bank|paypal|amazon|google|microsoft|apple)/i,
  // Data exfiltration in query params
  /\?[^#]*(?:api[_-]?key|token|password|secret|credential|auth)=/i,
  // File URLs (local file access)
  /^file:\/\//,
  // Data URLs (can contain malicious payloads)
  /^data:/,
];

/**
 * Built-in dangerous command patterns.
 */
const BUILTIN_DANGEROUS_COMMANDS: readonly RegExp[] = [
  // Recursive delete
  /\brm\s+(?:-[a-z]*r[a-z]*\s+|--recursive\s+)/i,
  /\brm\s+-rf\s+\//i,
  /\brm\s+--no-preserve-root/i,
  // Windows delete
  /\bdel\s+\/[fFsS]/i,
  /\brd\s+\/[sS]/i,
  // Format commands
  /\bformat\s+[a-zA-Z]:/i,
  /\bmkfs\./i,
  // Database destruction
  /\bDROP\s+(?:TABLE|DATABASE|SCHEMA|INDEX|VIEW|PROCEDURE)/i,
  /\bTRUNCATE\s+TABLE/i,
  /\bDELETE\s+FROM\s+\w+\s*(?:;|$)/i, // DELETE without WHERE
  // Command injection patterns
  /;\s*(?:rm|del|format|shutdown|reboot|halt)/i,
  /\|\s*(?:rm|del|format|shutdown|reboot|halt)/i,
  /`(?:rm|del|format|shutdown|reboot|halt)/i,
  /\$\((?:rm|del|format|shutdown|reboot|halt)/i,
  // System shutdown
  /\bshutdown\s+(?:-[hHrR]|\/[sS]|now)/i,
  /\binit\s+[06]/i,
  // Write to block devices
  />\s*\/dev\/(?:sd[a-z]|hd[a-z]|nvme\d+n\d+)/i,
  /\bdd\s+.*\bof=\/dev\//i,
];

/**
 * Built-in sensitive data patterns.
 */
const BUILTIN_SENSITIVE_DATA: readonly RegExp[] = [
  // API keys
  /\b(?:sk|pk|api[_-]?key)[_-](?:live|test|prod)?[_-]?[a-zA-Z0-9]{20,}/i,
  /\bAIza[a-zA-Z0-9_-]{35}/i, // Google API key
  /\bghp_[a-zA-Z0-9]{36}/i, // GitHub personal access token
  /\bghr_[a-zA-Z0-9]{36}/i, // GitHub refresh token
  /\bglpat-[a-zA-Z0-9_-]{20,}/i, // GitLab PAT
  // AWS
  /\bAKIA[A-Z0-9]{16}/i, // AWS access key
  /\b[A-Za-z0-9/+=]{40}(?:\s|$)/, // AWS secret key (after access key)
  // Private keys
  /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----/i,
  /-----BEGIN\s+(?:OPENSSH|EC|PGP)\s+PRIVATE\s+KEY-----/i,
  // Passwords in common formats
  /\bpassword\s*[=:]\s*["'][^"']{4,}["']/i,
  /\bpasswd\s*[=:]\s*["'][^"']{4,}["']/i,
  /\bsecret\s*[=:]\s*["'][^"']{4,}["']/i,
  // JWT tokens
  /\beyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*/i,
  // Database connection strings
  /\b(?:mysql|postgres|mongodb|redis):\/\/[^:]+:[^@]+@/i,
];

// =============================================================================
// Pattern Registry Class
// =============================================================================

/**
 * Registry for security patterns.
 * Supports built-in patterns and custom additions.
 */
class PatternRegistry {
  private dangerousTools: Map<string, PatternEntry> = new Map();
  private restrictedPaths: Map<string, PatternEntry> = new Map();
  private suspiciousUrls: Map<string, PatternEntry> = new Map();
  private dangerousCommands: Map<string, PatternEntry> = new Map();
  private sensitiveData: Map<string, PatternEntry> = new Map();

  constructor() {
    this.loadBuiltinPatterns();
  }

  /**
   * Load all built-in patterns.
   */
  private loadBuiltinPatterns(): void {
    const now = Date.now();

    // Dangerous tools
    for (const tool of BUILTIN_DANGEROUS_TOOLS) {
      this.dangerousTools.set(tool.toLowerCase(), {
        pattern: tool,
        description: 'Built-in dangerous tool',
        severity: 'high',
        builtin: true,
        addedAt: now,
      });
    }

    // Restricted paths
    for (const path of BUILTIN_RESTRICTED_PATHS) {
      this.restrictedPaths.set(path.toLowerCase(), {
        pattern: path,
        description: 'Built-in restricted path',
        severity: 'high',
        builtin: true,
        addedAt: now,
      });
    }

    // Suspicious URLs (use source as key)
    for (const pattern of BUILTIN_SUSPICIOUS_URLS) {
      this.suspiciousUrls.set(pattern.source, {
        pattern,
        description: 'Built-in suspicious URL pattern',
        severity: 'medium',
        builtin: true,
        addedAt: now,
      });
    }

    // Dangerous commands
    for (const pattern of BUILTIN_DANGEROUS_COMMANDS) {
      this.dangerousCommands.set(pattern.source, {
        pattern,
        description: 'Built-in dangerous command pattern',
        severity: 'high',
        builtin: true,
        addedAt: now,
      });
    }

    // Sensitive data
    for (const pattern of BUILTIN_SENSITIVE_DATA) {
      this.sensitiveData.set(pattern.source, {
        pattern,
        description: 'Built-in sensitive data pattern',
        severity: 'critical',
        builtin: true,
        addedAt: now,
      });
    }
  }

  /**
   * Get the map for a category.
   */
  private getMapForCategory(category: PatternCategory): Map<string, PatternEntry> {
    switch (category) {
      case 'dangerousTool':
        return this.dangerousTools;
      case 'restrictedPath':
        return this.restrictedPaths;
      case 'suspiciousUrl':
        return this.suspiciousUrls;
      case 'dangerousCommand':
        return this.dangerousCommands;
      case 'sensitiveData':
        return this.sensitiveData;
    }
  }

  /**
   * Add a string pattern to the registry.
   *
   * @param category - Pattern category
   * @param pattern - String pattern to add
   * @param options - Additional options
   * @returns true if added, false if already exists
   */
  addPattern(
    category: PatternCategory,
    pattern: string,
    options?: {
      description?: string;
      severity?: 'low' | 'medium' | 'high' | 'critical';
    }
  ): boolean {
    const map = this.getMapForCategory(category);
    const key = pattern.toLowerCase();

    if (map.has(key)) {
      logger.debug('Pattern already exists', { category, pattern });
      return false;
    }

    map.set(key, {
      pattern,
      description: options?.description,
      severity: options?.severity ?? 'medium',
      builtin: false,
      addedAt: Date.now(),
    });

    logger.info('Pattern added', { category, pattern });
    return true;
  }

  /**
   * Add a regex pattern to the registry.
   *
   * @param category - Pattern category
   * @param pattern - RegExp pattern to add
   * @param options - Additional options
   * @returns true if added, false if already exists
   */
  addRegexPattern(
    category: PatternCategory,
    pattern: RegExp,
    options?: {
      description?: string;
      severity?: 'low' | 'medium' | 'high' | 'critical';
    }
  ): boolean {
    const map = this.getMapForCategory(category);
    const key = pattern.source;

    if (map.has(key)) {
      logger.debug('Regex pattern already exists', { category, source: key });
      return false;
    }

    map.set(key, {
      pattern,
      description: options?.description,
      severity: options?.severity ?? 'medium',
      builtin: false,
      addedAt: Date.now(),
    });

    logger.info('Regex pattern added', { category, source: key });
    return true;
  }

  /**
   * Remove a custom pattern (cannot remove built-in patterns).
   *
   * @param category - Pattern category
   * @param pattern - Pattern to remove (string or regex source)
   * @returns true if removed, false if not found or is built-in
   */
  removePattern(category: PatternCategory, pattern: string | RegExp): boolean {
    const map = this.getMapForCategory(category);
    const key = typeof pattern === 'string'
      ? pattern.toLowerCase()
      : pattern.source;

    const entry = map.get(key);
    if (!entry) {
      logger.debug('Pattern not found for removal', { category, pattern: key });
      return false;
    }

    if (entry.builtin) {
      logger.warn('Cannot remove built-in pattern', { category, pattern: key });
      return false;
    }

    map.delete(key);
    logger.info('Pattern removed', { category, pattern: key });
    return true;
  }

  /**
   * Check if a pattern exists in the registry.
   */
  hasPattern(category: PatternCategory, pattern: string | RegExp): boolean {
    const map = this.getMapForCategory(category);
    const key = typeof pattern === 'string'
      ? pattern.toLowerCase()
      : pattern.source;
    return map.has(key);
  }

  /**
   * Check if a string matches any pattern in a category.
   *
   * @param category - Pattern category
   * @param value - String to check
   * @returns Matching entry or null
   */
  matchString(category: PatternCategory, value: string): PatternEntry | null {
    const map = this.getMapForCategory(category);
    const lowerValue = value.toLowerCase();
    // Normalize path separators for path matching
    const normalizedValue = category === 'restrictedPath'
      ? lowerValue.replace(/\\/g, '/')
      : lowerValue;

    for (const entry of map.values()) {
      if (typeof entry.pattern === 'string') {
        const lowerPattern = entry.pattern.toLowerCase();
        // Normalize pattern path separators too
        const normalizedPattern = category === 'restrictedPath'
          ? lowerPattern.replace(/\\/g, '/')
          : lowerPattern;

        // Exact match (case-insensitive)
        if (normalizedValue === normalizedPattern) {
          return entry;
        }
        // Contains match for paths
        if (category === 'restrictedPath' && normalizedValue.includes(normalizedPattern)) {
          return entry;
        }
      } else {
        // Regex match
        if (entry.pattern.test(value)) {
          return entry;
        }
      }
    }

    return null;
  }

  /**
   * Check if a tool name is dangerous.
   */
  isDangerousTool(toolName: string): boolean {
    return this.matchString('dangerousTool', toolName) !== null;
  }

  /**
   * Check if a path is restricted.
   */
  isRestrictedPath(path: string): boolean {
    return this.matchString('restrictedPath', path) !== null;
  }

  /**
   * Check if a URL is suspicious.
   */
  isSuspiciousUrl(url: string): boolean {
    return this.matchString('suspiciousUrl', url) !== null;
  }

  /**
   * Check if content contains dangerous commands.
   */
  hasDangerousCommand(content: string): PatternEntry | null {
    return this.matchString('dangerousCommand', content);
  }

  /**
   * Check if content contains sensitive data.
   */
  hasSensitiveData(content: string): PatternEntry | null {
    return this.matchString('sensitiveData', content);
  }

  /**
   * Get all patterns for a category.
   */
  getPatterns(category: PatternCategory): PatternEntry[] {
    const map = this.getMapForCategory(category);
    return Array.from(map.values());
  }

  /**
   * Get snapshot of registry state.
   */
  getSnapshot(): RegistrySnapshot {
    const snapshot: RegistrySnapshot = {
      categories: {
        dangerousTool: { stringPatterns: [], regexPatterns: 0, totalEntries: 0 },
        restrictedPath: { stringPatterns: [], regexPatterns: 0, totalEntries: 0 },
        suspiciousUrl: { stringPatterns: [], regexPatterns: 0, totalEntries: 0 },
        dangerousCommand: { stringPatterns: [], regexPatterns: 0, totalEntries: 0 },
        sensitiveData: { stringPatterns: [], regexPatterns: 0, totalEntries: 0 },
      },
    };

    for (const category of Object.keys(snapshot.categories) as PatternCategory[]) {
      const map = this.getMapForCategory(category);
      for (const entry of map.values()) {
        snapshot.categories[category].totalEntries++;
        if (typeof entry.pattern === 'string') {
          snapshot.categories[category].stringPatterns.push(entry.pattern);
        } else {
          snapshot.categories[category].regexPatterns++;
        }
      }
    }

    return snapshot;
  }

  /**
   * Reset to built-in patterns only.
   */
  reset(): void {
    this.dangerousTools.clear();
    this.restrictedPaths.clear();
    this.suspiciousUrls.clear();
    this.dangerousCommands.clear();
    this.sensitiveData.clear();
    this.loadBuiltinPatterns();
    logger.info('Pattern registry reset to built-in patterns');
  }
}

// =============================================================================
// Singleton Export
// =============================================================================

/**
 * Global pattern registry instance.
 */
export const patternRegistry = new PatternRegistry();
