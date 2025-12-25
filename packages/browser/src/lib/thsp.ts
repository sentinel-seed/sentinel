/**
 * Sentinel Guard - THSP Protocol
 *
 * Truth-Harm-Scope-Purpose validation for browser actions.
 * Adapted from Python SDK for TypeScript/browser use.
 */

export interface GateResult {
  passed: boolean;
  score: number;
  issues: string[];
}

export interface THSPResult {
  truth: GateResult;
  harm: GateResult;
  scope: GateResult;
  purpose: GateResult;
  overall: boolean;
  summary: string;
}

export interface ValidationContext {
  source: 'user' | 'extension' | 'page' | 'unknown';
  platform: string;
  action: 'send' | 'copy' | 'export' | 'share';
  userConfirmed?: boolean;
}

/**
 * Truth Gate: Verify the integrity and authenticity of the input
 *
 * Questions:
 * - Is this from a legitimate source?
 * - Has the content been tampered with?
 * - Is the context authentic?
 */
function validateTruth(input: string, context: ValidationContext): GateResult {
  const issues: string[] = [];
  let score = 100;

  // Guard against null/undefined input
  if (!input || typeof input !== 'string') {
    return { passed: false, score: 0, issues: ['Invalid input: null or non-string'] };
  }

  // Check for injection patterns - more specific to avoid false positives
  const injectionPatterns = [
    // M002: Only match actual injection attempts
    { pattern: /ignore\s+(?:all\s+)?previous\s+instructions/i, msg: 'Instruction override detected' },
    { pattern: /disregard\s+(?:all\s+)?(?:prior|previous)\s+(?:instructions|context)/i, msg: 'Instruction disregard detected' },
    // M003: More specific - require harmful context after "you are now"
    { pattern: /you\s+are\s+now\s+(?:a|an)\s+(?:evil|harmful|unrestricted|jailbroken)/i, msg: 'Role switch to unsafe persona' },
    // M004: "pretend to be" only for unsafe roles
    { pattern: /pretend\s+(?:you\s+are|to\s+be)\s+(?:an?\s+)?(?:evil|harmful|unrestricted|malicious)/i, msg: 'Pretend as unsafe persona' },
    // M005: Removed "act as if/though" - too common in legitimate text
    // M006: More specific - "system:" only at start of line or after newline
    { pattern: /(?:^|\n)\s*system\s*:\s*(?:ignore|override|forget)/i, msg: 'System prompt override' },
    { pattern: /new\s+instructions\s*:\s*(?:ignore|override|forget)/i, msg: 'New instructions override' },
  ];

  for (const { pattern, msg } of injectionPatterns) {
    if (pattern.test(input)) {
      issues.push(msg);
      score -= 30;
      break;
    }
  }

  // Check source authenticity
  if (context.source === 'unknown') {
    issues.push('Input source is unknown');
    score -= 20;
  } else if (context.source === 'extension') {
    issues.push('Input originated from another extension');
    score -= 10;
  }

  return {
    passed: score >= 50,
    score: Math.max(0, score),
    issues,
  };
}

/**
 * Harm Gate: Assess potential for harm
 *
 * Questions:
 * - Does this contain sensitive data that could be exposed?
 * - Could this action cause harm to the user?
 * - Are there security implications?
 */
function validateHarm(input: string, context: ValidationContext): GateResult {
  const issues: string[] = [];
  let score = 100;

  // Guard against null/undefined input
  if (!input || typeof input !== 'string') {
    return { passed: false, score: 0, issues: ['Invalid input: null or non-string'] };
  }

  // Sensitive patterns - more specific to avoid false positives
  const sensitivePatterns = [
    // Password in assignment/config context (not just discussion of passwords)
    { pattern: /password['":\s=]+['"]?[^\s'"]{6,}/i, penalty: 25, msg: 'Password value detected' },
    // API key in assignment context
    { pattern: /api[_-]?key['":\s=]+['"]?[a-zA-Z0-9-_]{10,}/i, penalty: 25, msg: 'API key value detected' },
    // N009: "secret" too generic - require assignment context
    { pattern: /(?:client[_-]?)?secret['":\s=]+['"]?[a-zA-Z0-9-_]{10,}/i, penalty: 15, msg: 'Secret value detected' },
    // Private key content (not just mention)
    { pattern: /-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----/i, penalty: 30, msg: 'Private key detected' },
    // SSN - with word boundary to be more precise
    { pattern: /\b\d{3}-\d{2}-\d{4}\b/, penalty: 30, msg: 'SSN pattern detected' },
    // Credit card - more specific with Luhn-like structure
    { pattern: /\b(?:4[0-9]{3}|5[1-5][0-9]{2}|6011|3[47][0-9]{2})[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/, penalty: 30, msg: 'Credit card pattern detected' },
  ];

  for (const { pattern, penalty, msg } of sensitivePatterns) {
    if (pattern.test(input)) {
      issues.push(msg);
      score -= penalty;
    }
  }

  // Harmful request patterns - more specific
  const harmfulPatterns = [
    // More specific: "how to hack" requires target context
    { pattern: /how\s+to\s+hack\s+(?:into|someone|account|password|system)/i, penalty: 20, msg: 'Hacking request' },
    // Bypass only in clearly malicious context
    { pattern: /bypass\s+(?:security|authentication)\s+(?:to|and|for)\s+(?:access|steal|get)/i, penalty: 20, msg: 'Security bypass request' },
    { pattern: /steal\s+(?:data|information|credentials|passwords?)/i, penalty: 25, msg: 'Data theft request' },
  ];

  for (const { pattern, penalty, msg } of harmfulPatterns) {
    if (pattern.test(input)) {
      issues.push(msg);
      score -= penalty;
    }
  }

  return {
    passed: score >= 50,
    score: Math.max(0, score),
    issues,
  };
}

/**
 * Scope Gate: Verify action is within appropriate boundaries
 *
 * Questions:
 * - Is this action within the expected scope?
 * - Are permissions being respected?
 * - Is the target appropriate?
 */
function validateScope(input: string, context: ValidationContext): GateResult {
  const issues: string[] = [];
  let score = 100;

  // Guard against null/undefined input
  if (!input || typeof input !== 'string') {
    return { passed: false, score: 0, issues: ['Invalid input: null or non-string'] };
  }

  // Check if action is appropriate for the platform
  const platformActions: Record<string, string[]> = {
    chatgpt: ['send', 'copy', 'export'],
    claude: ['send', 'copy', 'export'],
    gemini: ['send', 'copy'],
    perplexity: ['send', 'copy'],
    default: ['send', 'copy'],
  };

  const allowedActions =
    platformActions[context.platform] || platformActions.default;
  if (!allowedActions.includes(context.action)) {
    issues.push(`Action '${context.action}' not typical for ${context.platform}`);
    score -= 15;
  }

  // Check for scope escalation attempts - more specific patterns
  const scopePatterns = [
    // More specific: "access all" requires dangerous context
    { pattern: /(?:grant|give|get)\s+(?:me\s+)?(?:access\s+to\s+)?(?:all|every|full)\s+(?:files?|data|records?)/i, penalty: 15, msg: 'Broad access request' },
    { pattern: /admin(?:istrator)?\s+(?:access|rights|privileges)/i, penalty: 20, msg: 'Admin access request' },
    { pattern: /root\s+(?:access|privileges|permissions)/i, penalty: 20, msg: 'Root access request' },
    { pattern: /sudo\s+/i, penalty: 15, msg: 'Elevated privilege command' },
  ];

  for (const { pattern, penalty, msg } of scopePatterns) {
    if (pattern.test(input)) {
      issues.push(msg);
      score -= penalty;
    }
  }

  return {
    passed: score >= 50,
    score: Math.max(0, score),
    issues,
  };
}

/**
 * Purpose Gate: Require legitimate purpose
 *
 * Questions:
 * - Is there a clear, legitimate purpose?
 * - Does the user understand what they're doing?
 * - Is this aligned with expected use?
 */
function validatePurpose(
  input: string,
  context: ValidationContext
): GateResult {
  const issues: string[] = [];
  let score = 100;

  // Guard against null/undefined input
  if (!input || typeof input !== 'string') {
    return { passed: false, score: 0, issues: ['Invalid input: null or non-string'] };
  }

  // If user hasn't confirmed and input is sensitive
  if (!context.userConfirmed && input.length > 1000) {
    issues.push('Large input without user confirmation');
    score -= 10;
  }

  // Check for unclear or suspicious purposes - more specific
  const suspiciousPatterns = [
    // More specific: only match command-like context
    { pattern: /just\s+(?:do|execute|run)\s+(?:it|this)\s+(?:without|no)/i, penalty: 10, msg: 'Vague execution without verification' },
    { pattern: /don'?t\s+(?:ask|question|verify)\s+(?:me|anything|this)/i, penalty: 15, msg: 'Verification avoidance' },
    { pattern: /no\s+(?:questions|explanation)\s+(?:needed|required|please)/i, penalty: 15, msg: 'Explanation avoidance' },
    { pattern: /(?:skip|bypass)\s+(?:all\s+)?(?:checks?|validation|verification)/i, penalty: 20, msg: 'Validation bypass request' },
  ];

  for (const { pattern, penalty, msg } of suspiciousPatterns) {
    if (pattern.test(input)) {
      issues.push(msg);
      score -= penalty;
    }
  }

  return {
    passed: score >= 50,
    score: Math.max(0, score),
    issues,
  };
}

/**
 * Create a default context for validation
 */
function getDefaultContext(): ValidationContext {
  return {
    source: 'user',
    platform: 'generic',
    action: 'send',
    userConfirmed: false,
  };
}

/**
 * Create a failed gate result for invalid input
 */
function createFailedGate(reason: string): GateResult {
  return { passed: false, score: 0, issues: [reason] };
}

/**
 * Run full THSP validation
 */
export function validateTHSP(
  input: string,
  context?: ValidationContext | null
): THSPResult {
  // N010/N011: Handle null/undefined input
  if (!input || typeof input !== 'string') {
    const failedGate = createFailedGate('Invalid input: null or non-string');
    return {
      truth: failedGate,
      harm: failedGate,
      scope: failedGate,
      purpose: failedGate,
      overall: false,
      summary: 'Validation failed: Invalid input provided',
    };
  }

  // N010: Handle null/undefined context
  const safeContext = context ?? getDefaultContext();

  const truth = validateTruth(input, safeContext);
  const harm = validateHarm(input, safeContext);
  const scope = validateScope(input, safeContext);
  const purpose = validatePurpose(input, safeContext);

  const overall = truth.passed && harm.passed && scope.passed && purpose.passed;

  // Generate summary
  const allIssues = [
    ...truth.issues,
    ...harm.issues,
    ...scope.issues,
    ...purpose.issues,
  ];

  let summary: string;
  if (overall) {
    summary = 'All gates passed. Action appears safe.';
  } else {
    const failedGates = [];
    if (!truth.passed) failedGates.push('Truth');
    if (!harm.passed) failedGates.push('Harm');
    if (!scope.passed) failedGates.push('Scope');
    if (!purpose.passed) failedGates.push('Purpose');
    summary = `Failed gates: ${failedGates.join(', ')}. Issues: ${allIssues.slice(0, 3).join('; ')}`;
  }

  return {
    truth,
    harm,
    scope,
    purpose,
    overall,
    summary,
  };
}

/**
 * Quick check - returns true if input is likely safe
 */
export function quickCheck(input: string): boolean {
  // N011: Handle null/undefined input - fail closed (return false = not safe)
  if (!input || typeof input !== 'string') {
    return false;
  }

  const result = validateTHSP(input, getDefaultContext());
  return result.overall;
}
