/**
 * @sentinelseed/moltbot - Tool Validator
 *
 * Validates tool calls before execution.
 * Checks for dangerous tools, parameter injection, and system access violations.
 *
 * Features:
 * - Tool name validation (dangerous tools list)
 * - Parameter inspection (destructive commands, paths, URLs)
 * - THSP validation on parameter content
 * - Trusted/dangerous tool lists
 * - Extensible via pattern registry
 * - Full observability via logging and metrics
 *
 * @example
 * ```typescript
 * import { validateTool } from './tool';
 *
 * const result = await validateTool('bash', { command: 'ls' }, levelConfig);
 * if (result.shouldBlock) {
 *   // Block the tool call
 * }
 * ```
 */

import type {
  ToolValidationResult,
  LevelConfig,
  DetectedIssue,
  RiskLevel,
} from '../types';
import {
  isDangerousTool,
  checkToolParams,
  isRestrictedPath,
  isSuspiciousUrl,
  matchesAnyString,
  validateTHSP,
  patternRegistry,
} from './patterns';
import { logger, logValidation, logError } from '../internal/logger';
import { metrics } from '../internal/metrics';

// =============================================================================
// Types
// =============================================================================

/**
 * Options for tool validation.
 */
export interface ToolValidationOptions {
  /** Tool names that bypass validation */
  trustedTools?: string[];
  /** Tool names that are always blocked */
  dangerousTools?: string[];
  /** Skip parameter validation (for performance) */
  skipParams?: boolean;
  /** Skip THSP validation on parameters */
  skipThsp?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

/**
 * Tools that commonly access files or execute commands.
 */
const FILE_ACCESS_TOOLS = [
  'read_file', 'read', 'cat', 'head', 'tail',
  'write_file', 'write', 'edit', 'edit_file',
  'bash', 'shell', 'exec', 'execute', 'run_command',
  'glob', 'find', 'search',
] as const;

/**
 * Tools that commonly access network resources.
 */
const NETWORK_TOOLS = [
  'fetch', 'web_fetch', 'http_request', 'curl', 'wget',
  'request', 'api_call', 'web_search',
] as const;

// =============================================================================
// Main Validator
// =============================================================================

/**
 * Validate a tool call before execution.
 *
 * Performs the following checks:
 * 1. Check if tool is explicitly trusted/dangerous
 * 2. Check if tool name is inherently dangerous
 * 3. Validate parameters for dangerous patterns
 * 4. Check for restricted path access
 * 5. Check for suspicious URL access
 *
 * @param toolName - Name of the tool being called
 * @param params - Tool parameters
 * @param levelConfig - Current level configuration
 * @param options - Additional validation options
 * @returns Validation result with issues and blocking decision
 */
export async function validateTool(
  toolName: string,
  params: Record<string, unknown>,
  levelConfig: LevelConfig,
  options?: ToolValidationOptions
): Promise<ToolValidationResult> {
  const startTime = Date.now();

  try {
    // Handle invalid input
    if (!toolName || typeof toolName !== 'string') {
      const result = createBlockedResult('Invalid tool name', startTime);
      metrics.recordValidation('tool', result.durationMs, false, true);
      return result;
    }

    const normalizedToolName = toolName.toLowerCase().trim();
    const issues: DetectedIssue[] = [];

    // 1. Check if explicitly trusted (bypass validation)
    if (isExplicitlyTrusted(normalizedToolName, options?.trustedTools)) {
      logger.debug('Tool is explicitly trusted', {
        operation: 'validateTool',
        toolName: normalizedToolName,
      });
      const result = createSafeResult(startTime);
      metrics.recordValidation('tool', result.durationMs, true, false);
      return result;
    }

    // 2. Check if explicitly marked as dangerous
    if (isExplicitlyDangerous(normalizedToolName, options?.dangerousTools)) {
      issues.push({
        type: 'unknown',
        description: 'Tool is marked as dangerous',
        evidence: toolName,
        severity: 'critical',
      });
      const result = createResult(issues, levelConfig, `Tool "${toolName}" is blocked`, startTime);
      metrics.recordValidation('tool', result.durationMs, false, result.shouldBlock);
      if (issues.length > 0) {
        metrics.recordIssues(issues);
      }
      logValidation('tool', {
        safe: false,
        blocked: result.shouldBlock,
        issueCount: issues.length,
        riskLevel: result.riskLevel,
        durationMs: result.durationMs,
      }, { toolName });
      return result;
    }

    // 3. Check if tool name is inherently dangerous
    if (isDangerousTool(normalizedToolName)) {
      issues.push({
        type: 'destructive_command',
        description: 'Tool name indicates destructive operation',
        evidence: toolName,
        severity: 'high',
        gate: 'harm',
      });
    }

    // 4. Validate parameters (unless skipped)
    if (!options?.skipParams) {
      const paramIssues = validateParameters(normalizedToolName, params, levelConfig);
      issues.push(...paramIssues);
    }

    // 5. Additional checks for specific tool types
    if (isFileAccessTool(normalizedToolName)) {
      const pathIssues = validatePathAccess(params, levelConfig);
      issues.push(...pathIssues);
    }

    if (isNetworkTool(normalizedToolName)) {
      const urlIssues = validateUrlAccess(params, levelConfig);
      issues.push(...urlIssues);
    }

    // 6. Validate string parameters for THSP violations (unless skipped)
    if (!options?.skipThsp) {
      const thspIssues = validateParamContent(params);
      issues.push(...thspIssues);
    }

    // Build result
    const reason = issues.length > 0
      ? `${issues.length} issue(s) detected in tool call`
      : undefined;

    const result = createResult(issues, levelConfig, reason, startTime);

    // Record metrics
    metrics.recordValidation('tool', result.durationMs, result.safe, result.shouldBlock);
    if (issues.length > 0) {
      metrics.recordIssues(issues);
    }

    // Log result
    logValidation('tool', {
      safe: result.safe,
      blocked: result.shouldBlock,
      issueCount: issues.length,
      riskLevel: result.riskLevel,
      durationMs: result.durationMs,
    }, { toolName });

    return result;
  } catch (error) {
    // Log error and return blocked result (fail closed for tools)
    logError('validateTool', error instanceof Error ? error : String(error), {
      toolName,
    });
    metrics.recordError('validation');

    return createBlockedResult('Validation error', startTime);
  }
}

// =============================================================================
// Validation Functions
// =============================================================================

/**
 * Check if tool is explicitly trusted.
 */
function isExplicitlyTrusted(toolName: string, trustedTools?: string[]): boolean {
  if (!trustedTools || trustedTools.length === 0) {
    return false;
  }
  return matchesAnyString(toolName, trustedTools);
}

/**
 * Check if tool is explicitly marked as dangerous.
 */
function isExplicitlyDangerous(toolName: string, dangerousTools?: string[]): boolean {
  if (!dangerousTools || dangerousTools.length === 0) {
    return false;
  }
  return matchesAnyString(toolName, dangerousTools);
}

/**
 * Check if tool is a file access tool.
 */
function isFileAccessTool(toolName: string): boolean {
  return FILE_ACCESS_TOOLS.some(t => toolName.includes(t));
}

/**
 * Check if tool is a network tool.
 */
function isNetworkTool(toolName: string): boolean {
  return NETWORK_TOOLS.some(t => toolName.includes(t));
}

/**
 * Validate tool parameters for dangerous patterns.
 */
function validateParameters(
  _toolName: string,
  params: Record<string, unknown>,
  _levelConfig: LevelConfig
): DetectedIssue[] {
  const issues: DetectedIssue[] = [];

  try {
    // Check for dangerous patterns in parameters
    const paramIssues = checkToolParams(params);
    for (const issue of paramIssues) {
      issues.push({
        type: issue.type.startsWith('dangerous_') ? 'destructive_command' : 'system_path',
        description: `Dangerous pattern detected: ${issue.type}`,
        evidence: issue.evidence,
        severity: 'high',
        gate: 'harm',
      });
    }
  } catch (error) {
    logger.error('Parameter validation failed', {
      operation: 'validateParameters',
      error: error instanceof Error ? error : String(error),
    });
  }

  return issues;
}

/**
 * Validate path access in parameters.
 */
function validatePathAccess(
  params: Record<string, unknown>,
  levelConfig: LevelConfig
): DetectedIssue[] {
  const issues: DetectedIssue[] = [];

  // Only check if system paths blocking is enabled
  if (!levelConfig.blocking.systemPaths) {
    return issues;
  }

  try {
    // Check common path parameter names
    const pathParams = ['path', 'file', 'file_path', 'filepath', 'filename', 'dir', 'directory'];

    for (const paramName of pathParams) {
      const value = params[paramName];
      if (typeof value === 'string' && isRestrictedPath(value)) {
        issues.push({
          type: 'system_path',
          description: `Access to restricted path: ${paramName}`,
          evidence: sanitizePath(value),
          severity: 'high',
          gate: 'scope',
        });
      }
    }

    // Also check 'command' parameter for paths
    const command = params['command'];
    if (typeof command === 'string') {
      // Check for restricted paths in command
      const pathMatch = command.match(/(?:\/[\w.-]+)+|(?:[A-Z]:\\[\w\\.-]+)/gi);
      if (pathMatch) {
        for (const path of pathMatch) {
          if (isRestrictedPath(path)) {
            issues.push({
              type: 'system_path',
              description: 'Restricted path in command',
              evidence: sanitizePath(path),
              severity: 'high',
              gate: 'scope',
            });
          }
        }
      }
    }
  } catch (error) {
    logger.error('Path access validation failed', {
      operation: 'validatePathAccess',
      error: error instanceof Error ? error : String(error),
    });
  }

  return issues;
}

/**
 * Validate URL access in parameters.
 */
function validateUrlAccess(
  params: Record<string, unknown>,
  levelConfig: LevelConfig
): DetectedIssue[] {
  const issues: DetectedIssue[] = [];

  // Only check if suspicious URLs blocking is enabled
  if (!levelConfig.blocking.suspiciousUrls) {
    return issues;
  }

  try {
    // Check common URL parameter names
    const urlParams = ['url', 'uri', 'href', 'link', 'endpoint', 'target'];

    for (const paramName of urlParams) {
      const value = params[paramName];
      if (typeof value === 'string' && isSuspiciousUrl(value)) {
        issues.push({
          type: 'suspicious_url',
          description: `Suspicious URL detected: ${paramName}`,
          evidence: sanitizeUrl(value),
          severity: 'medium',
          gate: 'harm',
        });
      }
    }
  } catch (error) {
    logger.error('URL access validation failed', {
      operation: 'validateUrlAccess',
      error: error instanceof Error ? error : String(error),
    });
  }

  return issues;
}

/**
 * Validate string parameter content for THSP violations.
 */
function validateParamContent(params: Record<string, unknown>): DetectedIssue[] {
  const issues: DetectedIssue[] = [];

  try {
    // Check string parameters that might contain user-provided content
    const contentParams = ['content', 'message', 'text', 'body', 'command', 'query'];

    for (const paramName of contentParams) {
      const value = params[paramName];
      if (typeof value === 'string' && value.length > 0) {
        const thspResult = validateTHSP(value);

        // Only add issues for critical violations
        if (thspResult.riskLevel === 'critical' && !thspResult.jailbreak.passed) {
          issues.push({
            type: 'prompt_injection',
            description: 'Potential prompt injection in parameter',
            evidence: truncateString(`${paramName}: ${value}`, 50),
            severity: 'critical',
            gate: 'jailbreak',
          });
        }
      }
    }
  } catch (error) {
    logger.error('Param content validation failed', {
      operation: 'validateParamContent',
      error: error instanceof Error ? error : String(error),
    });
  }

  return issues;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Create a safe (no issues) result.
 */
function createSafeResult(startTime: number): ToolValidationResult {
  return {
    safe: true,
    shouldBlock: false,
    issues: [],
    riskLevel: 'none',
    durationMs: Date.now() - startTime,
  };
}

/**
 * Create a blocked result.
 */
function createBlockedResult(reason: string, startTime: number): ToolValidationResult {
  return {
    safe: false,
    shouldBlock: true,
    issues: [{
      type: 'unknown',
      description: reason,
      evidence: '',
      severity: 'critical',
    }],
    riskLevel: 'critical',
    reason,
    durationMs: Date.now() - startTime,
  };
}

/**
 * Create result from issues and level config.
 */
function createResult(
  issues: DetectedIssue[],
  levelConfig: LevelConfig,
  reason: string | undefined,
  startTime: number
): ToolValidationResult {
  const safe = issues.length === 0;
  const shouldBlock = determineShouldBlock(issues, levelConfig);
  const riskLevel = calculateRiskLevel(issues);

  return {
    safe,
    shouldBlock,
    issues,
    riskLevel,
    reason: shouldBlock ? reason : undefined,
    durationMs: Date.now() - startTime,
  };
}

/**
 * Determine if tool call should be blocked.
 */
function determineShouldBlock(issues: DetectedIssue[], levelConfig: LevelConfig): boolean {
  for (const issue of issues) {
    // Destructive commands
    if (issue.type === 'destructive_command' && levelConfig.blocking.destructiveCommands) {
      return true;
    }

    // System paths
    if (issue.type === 'system_path' && levelConfig.blocking.systemPaths) {
      return true;
    }

    // Suspicious URLs
    if (issue.type === 'suspicious_url' && levelConfig.blocking.suspiciousUrls) {
      return true;
    }

    // Data leaks
    if (issue.type === 'data_leak' && levelConfig.blocking.dataLeaks) {
      return true;
    }

    // Prompt injection (block if injection compliance is enabled)
    if (issue.type === 'prompt_injection' && levelConfig.blocking.injectionCompliance) {
      return true;
    }

    // Unknown critical issues (from explicit dangerous tools)
    if (issue.type === 'unknown' && issue.severity === 'critical') {
      return true;
    }
  }

  return false;
}

/**
 * Calculate risk level from issues.
 */
function calculateRiskLevel(issues: DetectedIssue[]): RiskLevel {
  if (issues.length === 0) {
    return 'none';
  }

  const hasCritical = issues.some(i => i.severity === 'critical');
  if (hasCritical) {
    return 'critical';
  }

  const hasHigh = issues.some(i => i.severity === 'high');
  if (hasHigh) {
    return 'high';
  }

  const hasMedium = issues.some(i => i.severity === 'medium');
  if (hasMedium) {
    return 'medium';
  }

  return 'low';
}

/**
 * Sanitize path for display.
 */
function sanitizePath(path: string): string {
  // Keep first and last parts, redact middle
  const parts = path.split(/[\/\\]/);
  if (parts.length <= 3) {
    return path;
  }
  return `${parts[0]}/.../${parts[parts.length - 1]}`;
}

/**
 * Sanitize URL for display.
 */
function sanitizeUrl(url: string): string {
  try {
    const parsed = new URL(url);
    // Show domain and path, hide query params
    return `${parsed.hostname}${parsed.pathname}`;
  } catch {
    // If parsing fails, truncate
    return url.length > 50 ? url.substring(0, 50) + '...' : url;
  }
}

/**
 * Truncate a string to a maximum length.
 */
function truncateString(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.substring(0, maxLength) + '...';
}
