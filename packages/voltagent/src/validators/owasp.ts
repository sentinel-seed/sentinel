/**
 * @sentinelseed/voltagent - OWASP Validator
 *
 * Detects common security vulnerabilities based on OWASP guidelines.
 * Includes patterns for SQL injection, XSS, command injection, prompt injection,
 * and other security threats relevant to AI agents.
 *
 * Based on:
 * - OWASP Top 10 Web Application Security Risks
 * - OWASP Agentic AI Security Top 10
 */

import type {
  OWASPValidationResult,
  OWASPViolationType,
  OWASPFinding,
  OWASPPatternDefinition,
  RiskLevel,
} from '../types';

// =============================================================================
// Pattern Definitions
// =============================================================================

/**
 * SQL Injection patterns.
 * Detects common SQL injection attack vectors.
 */
const SQL_INJECTION_PATTERNS: OWASPPatternDefinition[] = [
  {
    pattern: /(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|TRUNCATE)\b.*\b(FROM|INTO|TABLE|DATABASE|WHERE)\b)/i,
    type: 'SQL_INJECTION',
    severity: 'critical',
    description: 'SQL statement detected',
  },
  {
    pattern: /(\b(OR|AND)\s+['"]?\d+['"]?\s*=\s*['"]?\d+['"]?)/i,
    type: 'SQL_INJECTION',
    severity: 'critical',
    description: 'SQL tautology attack pattern (OR 1=1)',
  },
  {
    pattern: /(--\s*$|;\s*--)/,
    type: 'SQL_INJECTION',
    severity: 'high',
    description: 'SQL comment injection',
  },
  {
    pattern: /('\s*(OR|AND)\s*')/i,
    type: 'SQL_INJECTION',
    severity: 'high',
    description: 'String-based SQL injection',
  },
  {
    pattern: /(\bUNION\s+(ALL\s+)?SELECT\b)/i,
    type: 'SQL_INJECTION',
    severity: 'critical',
    description: 'UNION-based SQL injection',
  },
  {
    pattern: /(\bEXEC(\s+|\()|xp_cmdshell|sp_executesql)/i,
    type: 'SQL_INJECTION',
    severity: 'critical',
    description: 'SQL Server command execution',
  },
  {
    pattern: /(\bINTO\s+(OUT|DUMP)FILE\b)/i,
    type: 'SQL_INJECTION',
    severity: 'critical',
    description: 'SQL file write attempt',
  },
  {
    pattern: /(\bLOAD_FILE\s*\()/i,
    type: 'SQL_INJECTION',
    severity: 'critical',
    description: 'SQL file read attempt',
  },
  {
    pattern: /(\bBENCHMARK\s*\(|\bSLEEP\s*\(|\bWAITFOR\s+DELAY\b)/i,
    type: 'SQL_INJECTION',
    severity: 'high',
    description: 'SQL time-based injection',
  },
];

/**
 * XSS (Cross-Site Scripting) patterns.
 */
const XSS_PATTERNS: OWASPPatternDefinition[] = [
  {
    pattern: /<script\b[^>]*>[\s\S]*?<\/script>/gi,
    type: 'XSS',
    severity: 'critical',
    description: 'Script tag detected',
  },
  {
    pattern: /\bon\w+\s*=\s*["']?[^"']*["']?/gi,
    type: 'XSS',
    severity: 'high',
    description: 'Event handler attribute',
  },
  {
    pattern: /javascript\s*:/gi,
    type: 'XSS',
    severity: 'critical',
    description: 'JavaScript protocol in URL',
  },
  {
    pattern: /data\s*:\s*text\/html/gi,
    type: 'XSS',
    severity: 'high',
    description: 'Data URI with HTML content',
  },
  {
    pattern: /<iframe\b[^>]*>/gi,
    type: 'XSS',
    severity: 'high',
    description: 'Iframe tag detected',
  },
  {
    pattern: /<object\b[^>]*>|<embed\b[^>]*>/gi,
    type: 'XSS',
    severity: 'high',
    description: 'Object/Embed tag detected',
  },
  {
    pattern: /\beval\s*\(/gi,
    type: 'XSS',
    severity: 'critical',
    description: 'Eval function call',
  },
  {
    pattern: /\bdocument\.(cookie|write|location)/gi,
    type: 'XSS',
    severity: 'high',
    description: 'DOM manipulation detected',
  },
  {
    pattern: /<svg\b[^>]*\bonload\s*=/gi,
    type: 'XSS',
    severity: 'critical',
    description: 'SVG with onload event',
  },
  {
    pattern: /<img\b[^>]*\bonerror\s*=/gi,
    type: 'XSS',
    severity: 'critical',
    description: 'Image with onerror event',
  },
];

/**
 * Command Injection patterns.
 */
const COMMAND_INJECTION_PATTERNS: OWASPPatternDefinition[] = [
  {
    pattern: /[;&|`$]|\$\(|`[^`]+`/,
    type: 'COMMAND_INJECTION',
    severity: 'critical',
    description: 'Shell metacharacter detected',
  },
  {
    pattern: /\b(rm|del|rmdir|format|mkfs|dd)\s+(-rf?|\/[sq])?\s*(\/|\\|[a-z]:)/i,
    type: 'COMMAND_INJECTION',
    severity: 'critical',
    description: 'Destructive command pattern',
  },
  {
    pattern: /\|\s*(bash|sh|cmd|powershell|python|perl|ruby|php)\b/i,
    type: 'COMMAND_INJECTION',
    severity: 'critical',
    description: 'Pipe to shell interpreter',
  },
  {
    pattern: /\b(wget|curl|fetch)\s+.*\|\s*(bash|sh)/i,
    type: 'COMMAND_INJECTION',
    severity: 'critical',
    description: 'Remote script execution',
  },
  {
    pattern: /\bnc\s+-[elp]|\bncat\s+/i,
    type: 'COMMAND_INJECTION',
    severity: 'critical',
    description: 'Netcat reverse shell',
  },
  {
    pattern: />\s*\/dev\/tcp\//i,
    type: 'COMMAND_INJECTION',
    severity: 'critical',
    description: 'Bash network redirection',
  },
  {
    pattern: /\b(chmod|chown)\s+[0-7]{3,4}\s+/i,
    type: 'COMMAND_INJECTION',
    severity: 'high',
    description: 'File permission modification',
  },
];

/**
 * Path Traversal patterns.
 */
const PATH_TRAVERSAL_PATTERNS: OWASPPatternDefinition[] = [
  {
    pattern: /\.\.[\/\\]/,
    type: 'PATH_TRAVERSAL',
    severity: 'high',
    description: 'Directory traversal sequence',
  },
  {
    pattern: /\/(etc\/(passwd|shadow|hosts)|proc\/self|windows\/system32)/i,
    type: 'PATH_TRAVERSAL',
    severity: 'critical',
    description: 'Sensitive system path access',
  },
  {
    pattern: /%2e%2e[%2f%5c]/gi,
    type: 'PATH_TRAVERSAL',
    severity: 'high',
    description: 'URL-encoded directory traversal',
  },
  {
    pattern: /\.(env|git|svn|htaccess|htpasswd|config|ini|log|bak)$/i,
    type: 'PATH_TRAVERSAL',
    severity: 'high',
    description: 'Sensitive file extension access',
  },
];

/**
 * SSRF (Server-Side Request Forgery) patterns.
 */
const SSRF_PATTERNS: OWASPPatternDefinition[] = [
  {
    pattern: /\b(localhost|127\.0\.0\.1|0\.0\.0\.0|::1)\b/i,
    type: 'SSRF',
    severity: 'high',
    description: 'Localhost access attempt',
  },
  {
    pattern: /\b(10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})\b/,
    type: 'SSRF',
    severity: 'high',
    description: 'Internal IP address access',
  },
  {
    pattern: /\bfile:\/\//i,
    type: 'SSRF',
    severity: 'critical',
    description: 'File protocol URL',
  },
  {
    pattern: /\bgopher:\/\//i,
    type: 'SSRF',
    severity: 'critical',
    description: 'Gopher protocol URL',
  },
  {
    pattern: /\bdict:\/\//i,
    type: 'SSRF',
    severity: 'high',
    description: 'Dict protocol URL',
  },
  {
    pattern: /\bmetadata\.google\.internal\b/i,
    type: 'SSRF',
    severity: 'critical',
    description: 'Cloud metadata service access',
  },
  {
    pattern: /\b169\.254\.169\.254\b/,
    type: 'SSRF',
    severity: 'critical',
    description: 'AWS metadata service access',
  },
];

/**
 * Prompt Injection patterns (specific to AI agents).
 * Expanded to match core THSP jailbreak detection patterns.
 *
 * Note: For comprehensive jailbreak detection, use the THSP validator
 * which imports from @sentinelseed/core with 100+ patterns.
 */
const PROMPT_INJECTION_PATTERNS: OWASPPatternDefinition[] = [
  // Instruction override patterns
  {
    pattern: /ignore\s+(all\s+)?(previous|prior|above)\s+(instructions|prompts|context)/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Instruction override attempt',
  },
  {
    pattern: /disregard\s+(all\s+)?(your\s+)?(instructions?|rules?|guidelines?|programming|safety)/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Instruction disregard attempt',
  },
  {
    pattern: /bypass\s+(your\s+)?(restrictions?|filters?|safety|guidelines?|rules?)/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Safety bypass attempt',
  },
  {
    pattern: /forget\s+(all\s+)?(your\s+)?(instructions?|rules?|training|programming)/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Memory wipe attempt',
  },
  {
    pattern: /override\s+(your\s+)?(safety|guidelines?|instructions?|programming)/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Safety override attempt',
  },

  // System prompt delimiters
  {
    pattern: /\[SYSTEM\]|\[INST\]|\[\/INST\]|<<SYS>>|<\|system\|>/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'System prompt delimiter injection',
  },
  {
    pattern: /\buser:\s*|human:\s*|assistant:\s*/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Role prefix injection',
  },

  // New instruction injection
  {
    pattern: /new\s+instructions?:?\s+|updated\s+prompt:?\s+/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Instruction injection attempt',
  },
  {
    pattern: /new\s+directive\s+(replaces|overrides)/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Directive replacement attempt',
  },

  // Role manipulation
  {
    pattern: /you\s+are\s+now\s+(DAN|jailbroken|unrestricted|unfiltered|evil|unlimited)/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Role manipulation: persona switch',
  },
  {
    pattern: /you\s+are\s+now\s+in\s+(developer|debug|admin|god|unrestricted|jailbreak)\s+mode/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Role manipulation: mode switch',
  },
  {
    pattern: /(enter|switch\s+to|enable|activate)\s+(developer|debug|admin|god|unrestricted|jailbreak)\s+mode/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Role manipulation: enable mode',
  },
  {
    pattern: /pretend\s+(that\s+)?you\s+(have\s+no|don'?t\s+have(\s+any)?)\s+(restrictions?|rules?|limits?|guidelines?|filters?)/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Role manipulation: no restrictions',
  },

  // Prompt extraction
  {
    pattern: /(reveal|show|display|print|output|give\s+me)\s+your\s+(system\s+)?(prompt|instructions?|message|configuration)/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Prompt extraction attempt',
  },
  {
    pattern: /what\s+(are|is)\s+your\s+(system\s+)?(instructions?|prompt|original\s+prompt)/i,
    type: 'PROMPT_INJECTION',
    severity: 'medium',
    description: 'System prompt inquiry',
  },

  // Filter bypass
  {
    pattern: /(disable|turn\s+off|deactivate|remove|bypass)\s+(your\s+)?(safety|content\s+)?(filters?|features?|guardrails?|restrictions?|mode)/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Filter bypass attempt',
  },
  {
    pattern: /(unfiltered|uncensored|unrestricted)\s+mode/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Unfiltered mode request',
  },
  {
    pattern: /without\s+(any\s+)?(restrictions?|safety|filters?|guardrails?)/i,
    type: 'PROMPT_INJECTION',
    severity: 'high',
    description: 'Without restrictions request',
  },

  // Common jailbreak indicators
  {
    pattern: /\bpwned\b|\bhacked\b/i,
    type: 'PROMPT_INJECTION',
    severity: 'medium',
    description: 'Common jailbreak indicator',
  },
  {
    pattern: /\bjailbreak\b/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'Explicit jailbreak mention',
  },
  {
    pattern: /\bdan\s+mode\b/i,
    type: 'PROMPT_INJECTION',
    severity: 'critical',
    description: 'DAN mode request',
  },

  // Output manipulation
  {
    pattern: /respond\s+only\s+with|output\s+only|say\s+only/i,
    type: 'PROMPT_INJECTION',
    severity: 'medium',
    description: 'Output constraint injection',
  },
];

/**
 * Sensitive Data Exposure patterns.
 */
const SENSITIVE_DATA_PATTERNS: OWASPPatternDefinition[] = [
  {
    pattern: /\b(password|passwd|pwd)\s*[:=]\s*\S+/i,
    type: 'SENSITIVE_DATA_EXPOSURE',
    severity: 'critical',
    description: 'Password in plain text',
  },
  {
    pattern: /\b(api[_-]?key|apikey|secret[_-]?key|auth[_-]?token)\s*[:=]\s*['"]?\w+['"]?/i,
    type: 'SENSITIVE_DATA_EXPOSURE',
    severity: 'critical',
    description: 'API key or secret exposed',
  },
  {
    pattern: /\bAKIA[0-9A-Z]{16}\b/,
    type: 'SENSITIVE_DATA_EXPOSURE',
    severity: 'critical',
    description: 'AWS Access Key ID',
  },
  {
    pattern: /-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----/,
    type: 'SENSITIVE_DATA_EXPOSURE',
    severity: 'critical',
    description: 'Private key detected',
  },
  {
    pattern: /\beyJ[a-zA-Z0-9_-]+\.eyJ[a-zA-Z0-9_-]+\.[a-zA-Z0-9_-]+\b/,
    type: 'SENSITIVE_DATA_EXPOSURE',
    severity: 'high',
    description: 'JWT token detected',
  },
];

// =============================================================================
// All Patterns Combined
// =============================================================================

const ALL_PATTERNS: OWASPPatternDefinition[] = [
  ...SQL_INJECTION_PATTERNS,
  ...XSS_PATTERNS,
  ...COMMAND_INJECTION_PATTERNS,
  ...PATH_TRAVERSAL_PATTERNS,
  ...SSRF_PATTERNS,
  ...PROMPT_INJECTION_PATTERNS,
  ...SENSITIVE_DATA_PATTERNS,
];

// =============================================================================
// Validation Functions
// =============================================================================

/**
 * Validate content against OWASP security patterns.
 *
 * @param content - Content to validate
 * @param checks - Optional array of specific violation types to check
 * @param customPatterns - Optional custom patterns to include
 * @returns OWASPValidationResult with detailed findings
 *
 * @example
 * ```typescript
 * const result = validateOWASP("SELECT * FROM users WHERE id = 1");
 * console.log(result.safe); // false
 * console.log(result.violations); // ['SQL_INJECTION']
 * ```
 */
export function validateOWASP(
  content: string,
  checks?: OWASPViolationType[],
  customPatterns?: OWASPPatternDefinition[]
): OWASPValidationResult {
  // Handle invalid input
  if (!content || typeof content !== 'string') {
    return {
      safe: true,
      violations: [],
      findings: [],
      riskLevel: 'low',
    };
  }

  const findings: OWASPFinding[] = [];
  const violationSet = new Set<OWASPViolationType>();

  // Determine which patterns to use
  let patternsToCheck = ALL_PATTERNS;
  if (checks && checks.length > 0) {
    patternsToCheck = ALL_PATTERNS.filter((p) => checks.includes(p.type));
  }

  // Add custom patterns
  if (customPatterns) {
    patternsToCheck = [...patternsToCheck, ...customPatterns];
  }

  // Check each pattern
  for (const { pattern, type, severity, description } of patternsToCheck) {
    const match = content.match(pattern);
    if (match) {
      violationSet.add(type);
      findings.push({
        type,
        description,
        evidence: match[0].substring(0, 100), // Limit evidence length
        severity,
        remediation: getRemediation(type),
      });
    }
  }

  const violations = Array.from(violationSet);
  const riskLevel = calculateOverallRisk(findings);

  return {
    safe: violations.length === 0,
    violations,
    findings,
    riskLevel,
  };
}

/**
 * Quick OWASP check for critical patterns only.
 * Faster than full validation, suitable for high-volume screening.
 *
 * @param content - Content to check
 * @returns true if no critical OWASP violations detected
 */
export function quickOWASPCheck(content: string): boolean {
  if (!content || typeof content !== 'string') {
    return true;
  }

  // Critical patterns only
  const criticalPatterns = [
    /\bUNION\s+(ALL\s+)?SELECT\b/i, // SQL Injection
    /<script\b[^>]*>/gi, // XSS
    /[;&|`]\s*(rm|del|format)\s+-rf?\s/i, // Command injection
    /\bfile:\/\//i, // SSRF
    /ignore\s+(all\s+)?(previous|prior)\s+instructions/i, // Prompt injection
  ];

  return !criticalPatterns.some((p) => p.test(content));
}

/**
 * Check for a specific OWASP violation type.
 *
 * @param content - Content to check
 * @param type - Specific violation type to check
 * @returns true if the specific violation was detected
 */
export function hasViolation(content: string, type: OWASPViolationType): boolean {
  const patterns = ALL_PATTERNS.filter((p) => p.type === type);
  return patterns.some(({ pattern }) => pattern.test(content));
}

/**
 * Get patterns for a specific violation type.
 * Useful for testing and extending.
 *
 * @param type - Violation type
 * @returns Array of patterns for that type
 */
export function getPatternsForType(type: OWASPViolationType): OWASPPatternDefinition[] {
  return ALL_PATTERNS.filter((p) => p.type === type);
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Calculate overall risk level from findings.
 */
function calculateOverallRisk(findings: OWASPFinding[]): RiskLevel {
  if (findings.length === 0) {
    return 'low';
  }

  const hasCritical = findings.some((f) => f.severity === 'critical');
  if (hasCritical) {
    return 'critical';
  }

  const hasHigh = findings.some((f) => f.severity === 'high');
  if (hasHigh || findings.length >= 3) {
    return 'high';
  }

  if (findings.length >= 2) {
    return 'medium';
  }

  return 'medium';
}

/**
 * Get remediation suggestion for a violation type.
 */
function getRemediation(type: OWASPViolationType): string {
  const remediations: Record<OWASPViolationType, string> = {
    SQL_INJECTION: 'Use parameterized queries or prepared statements',
    XSS: 'Sanitize and escape output, use Content Security Policy',
    COMMAND_INJECTION: 'Avoid shell execution, use safe APIs',
    PATH_TRAVERSAL: 'Validate and sanitize file paths, use allowlists',
    SSRF: 'Validate URLs, use allowlists, disable unnecessary protocols',
    PROMPT_INJECTION: 'Implement input validation, use system prompt protection',
    INSECURE_OUTPUT: 'Validate and sanitize all output before display',
    SENSITIVE_DATA_EXPOSURE: 'Remove or redact sensitive data, use secrets management',
    EXCESSIVE_PERMISSIONS: 'Apply principle of least privilege',
    DENIAL_OF_SERVICE: 'Implement rate limiting and resource constraints',
  };

  return remediations[type] ?? 'Review and validate input/output';
}

// =============================================================================
// Pattern Statistics
// =============================================================================

/**
 * Get count of patterns by violation type.
 */
export function getPatternStats(): Record<OWASPViolationType, number> {
  const stats: Partial<Record<OWASPViolationType, number>> = {};

  for (const pattern of ALL_PATTERNS) {
    stats[pattern.type] = (stats[pattern.type] ?? 0) + 1;
  }

  return stats as Record<OWASPViolationType, number>;
}

/**
 * Get total number of OWASP patterns.
 */
export function getTotalPatternCount(): number {
  return ALL_PATTERNS.length;
}
