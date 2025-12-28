/**
 * @fileoverview Tool Validator - Validates MCP tool calls for safety
 *
 * This module provides validation for MCP tool calls, checking for:
 * - Dangerous operations
 * - Path traversal attacks
 * - Command injection
 * - Sensitive data exposure
 *
 * @author Sentinel Team
 * @license MIT
 */

import { MCPServer, RiskLevel } from '../types';

// =============================================================================
// TYPES
// =============================================================================

/** Validation result */
export interface ValidationResult {
  /** Whether the tool call is safe */
  safe: boolean;
  /** Risk level */
  riskLevel: RiskLevel;
  /** Reason for failure (if not safe) */
  reason?: string;
  /** Warnings (even if safe) */
  warnings: string[];
}

// =============================================================================
// DANGEROUS PATTERNS
// =============================================================================

/** Patterns that indicate dangerous operations */
const DANGEROUS_PATTERNS = {
  /** Path traversal attempts */
  pathTraversal: [
    /\.\.\//g,
    /\.\.\\/g,
    /\.\.%2f/gi,
    /\.\.%5c/gi,
  ],

  /** Command injection attempts */
  commandInjection: [
    /[;&|`$]/,
    /\$\(/,
    /`.*`/,
    /\|\s*\w+/,
    /;\s*\w+/,
    /&&\s*\w+/,
    /\|\|\s*\w+/,
  ],

  /** SQL injection patterns */
  sqlInjection: [
    /'\s*or\s+/i,
    /;\s*drop\s+/i,
    /;\s*delete\s+/i,
    /union\s+select/i,
    /--\s*$/,
  ],

  /** Sensitive file paths */
  sensitivePaths: [
    /\/etc\/passwd/i,
    /\/etc\/shadow/i,
    /\.ssh\/id_rsa/i,
    /\.aws\/credentials/i,
    /\.env$/i,
    /\.git\/config/i,
    /windows\\system32/i,
    /\.kube\/config/i,
  ],

  /** Dangerous executables */
  dangerousExecutables: [
    /\brm\s+-rf\s+\//,
    /\bdd\s+if=/,
    /\bmkfs\./,
    /\bformat\s+/i,
    /\bdel\s+\/[sfq]/i,
    /\bshutdown\b/i,
    /\breboot\b/i,
  ],
};

/** Sensitive data patterns */
const SENSITIVE_DATA_PATTERNS = [
  // API keys
  /(?:api[_-]?key|apikey)\s*[:=]\s*['"]?[\w-]{20,}/i,
  // Passwords
  /(?:password|passwd|pwd)\s*[:=]\s*['"]?[^\s'"]+/i,
  // Private keys
  /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----/,
  // AWS keys
  /AKIA[0-9A-Z]{16}/,
  // JWT tokens
  /eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*/,
  // Seed phrases (12+ words)
  /(?:\b\w{3,}\s+){11,}\b\w{3,}/,
];

// =============================================================================
// VALIDATION FUNCTIONS
// =============================================================================

/**
 * Checks a string for dangerous patterns.
 *
 * @param value - The string to check
 * @param patterns - Array of patterns to check against
 * @returns True if any pattern matches
 */
function containsPattern(value: string, patterns: RegExp[]): boolean {
  return patterns.some((pattern) => pattern.test(value));
}

/**
 * Validates a single argument value.
 *
 * @param value - The value to validate
 * @param key - The argument key
 * @returns Validation result for this argument
 */
function validateArgument(
  value: unknown,
  key: string
): { safe: boolean; reason?: string; warning?: string } {
  if (value === null || value === undefined) {
    return { safe: true };
  }

  const strValue = typeof value === 'string' ? value : JSON.stringify(value);

  // Check for path traversal
  if (containsPattern(strValue, DANGEROUS_PATTERNS.pathTraversal)) {
    return {
      safe: false,
      reason: `Path traversal detected in argument "${key}"`,
    };
  }

  // Check for command injection (if relevant keys)
  const commandKeys = ['command', 'cmd', 'exec', 'shell', 'script', 'code'];
  if (commandKeys.some((k) => key.toLowerCase().includes(k))) {
    if (containsPattern(strValue, DANGEROUS_PATTERNS.commandInjection)) {
      return {
        safe: false,
        reason: `Potential command injection in argument "${key}"`,
      };
    }

    if (containsPattern(strValue, DANGEROUS_PATTERNS.dangerousExecutables)) {
      return {
        safe: false,
        reason: `Dangerous command detected in argument "${key}"`,
      };
    }
  }

  // Check for SQL injection (if relevant keys)
  const sqlKeys = ['query', 'sql', 'where', 'filter'];
  if (sqlKeys.some((k) => key.toLowerCase().includes(k))) {
    if (containsPattern(strValue, DANGEROUS_PATTERNS.sqlInjection)) {
      return {
        safe: false,
        reason: `Potential SQL injection in argument "${key}"`,
      };
    }
  }

  // Check for sensitive paths
  const pathKeys = ['path', 'file', 'dir', 'directory', 'location'];
  if (pathKeys.some((k) => key.toLowerCase().includes(k))) {
    if (containsPattern(strValue, DANGEROUS_PATTERNS.sensitivePaths)) {
      return {
        safe: false,
        reason: `Access to sensitive path detected in argument "${key}"`,
      };
    }
  }

  // Check for sensitive data exposure (warning only)
  if (SENSITIVE_DATA_PATTERNS.some((p) => p.test(strValue))) {
    return {
      safe: true,
      warning: `Potential sensitive data in argument "${key}"`,
    };
  }

  return { safe: true };
}

/**
 * Validates a tool call's arguments.
 *
 * @param toolName - The name of the tool
 * @param args - The call arguments
 * @param server - The server (optional, for context)
 * @returns Promise resolving to validation result
 */
export async function validateTool(
  toolName: string,
  args: Record<string, unknown>,
  server?: MCPServer
): Promise<ValidationResult> {
  const warnings: string[] = [];
  let riskLevel: RiskLevel = 'low';

  // Validate each argument
  for (const [key, value] of Object.entries(args)) {
    const result = validateArgument(value, key);

    if (!result.safe) {
      return {
        safe: false,
        riskLevel: 'critical',
        reason: result.reason,
        warnings,
      };
    }

    if (result.warning) {
      warnings.push(result.warning);
      if (riskLevel === 'low') {
        riskLevel = 'medium';
      }
    }
  }

  // Check tool name for inherent risk
  const toolRisk = getToolRiskLevel(toolName);
  if (
    toolRisk === 'high' ||
    toolRisk === 'critical'
  ) {
    riskLevel = toolRisk;
  }

  // Adjust for server trust
  if (server) {
    if (!server.isTrusted && riskLevel === 'low') {
      riskLevel = 'medium';
    }
    if (server.trustLevel < 30 && riskLevel !== 'critical') {
      riskLevel = 'high';
    }
  }

  return {
    safe: true,
    riskLevel,
    warnings,
  };
}

/**
 * Checks if a tool is safe to use.
 *
 * @param toolName - The name of the tool
 * @param args - The call arguments
 * @returns Promise resolving to true if safe
 */
export async function isToolSafe(
  toolName: string,
  args: Record<string, unknown>
): Promise<boolean> {
  const result = await validateTool(toolName, args);
  return result.safe;
}

/**
 * Gets the inherent risk level of a tool based on its name.
 *
 * @param toolName - The tool name
 * @returns Risk level
 */
export function getToolRiskLevel(toolName: string): RiskLevel {
  const nameLower = toolName.toLowerCase();

  // Critical risk tools
  const criticalTools = [
    'execute',
    'exec',
    'eval',
    'run_code',
    'shell',
    'terminal',
    'bash',
    'powershell',
    'delete_all',
    'drop',
    'format',
  ];
  if (criticalTools.some((t) => nameLower.includes(t))) {
    return 'critical';
  }

  // High risk tools
  const highRiskTools = [
    'write',
    'create',
    'delete',
    'remove',
    'rm',
    'send',
    'transfer',
    'deploy',
    'install',
    'uninstall',
  ];
  if (highRiskTools.some((t) => nameLower.includes(t))) {
    return 'high';
  }

  // Medium risk tools
  const mediumRiskTools = [
    'read',
    'fetch',
    'download',
    'upload',
    'modify',
    'update',
    'patch',
    'config',
    'settings',
  ];
  if (mediumRiskTools.some((t) => nameLower.includes(t))) {
    return 'medium';
  }

  // Low risk tools
  return 'low';
}

// =============================================================================
// SCHEMA VALIDATION
// =============================================================================

/**
 * Validates arguments against a tool's input schema.
 *
 * @param args - The call arguments
 * @param schema - The tool's input schema
 * @returns Validation result
 */
export function validateAgainstSchema(
  args: Record<string, unknown>,
  schema: Record<string, unknown>
): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  // Check required properties
  if (schema.required && Array.isArray(schema.required)) {
    for (const required of schema.required) {
      if (!(required in args)) {
        errors.push(`Missing required argument: ${required}`);
      }
    }
  }

  // Check property types (basic validation)
  if (schema.properties && typeof schema.properties === 'object') {
    const props = schema.properties as Record<string, { type?: string }>;
    for (const [key, value] of Object.entries(args)) {
      if (key in props) {
        const expectedType = props[key].type;
        if (expectedType) {
          const actualType = Array.isArray(value) ? 'array' : typeof value;
          if (actualType !== expectedType) {
            errors.push(
              `Argument "${key}" has wrong type: expected ${expectedType}, got ${actualType}`
            );
          }
        }
      }
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  validateTool,
  isToolSafe,
  getToolRiskLevel,
  validateAgainstSchema,
};
