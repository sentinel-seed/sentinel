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

  // Check for injection patterns
  const injectionPatterns = [
    /ignore\s+(?:all\s+)?previous\s+instructions/i,
    /disregard\s+(?:all\s+)?(?:prior|previous)/i,
    /you\s+are\s+now\s+(?:a|an)\s+/i,
    /pretend\s+(?:you\s+are|to\s+be)/i,
    /act\s+as\s+(?:if|though)/i,
    /new\s+instructions:/i,
    /system\s*:\s*/i,
  ];

  for (const pattern of injectionPatterns) {
    if (pattern.test(input)) {
      issues.push('Potential prompt injection detected');
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

  // Import patterns dynamically to check for secrets
  const sensitivePatterns = [
    { pattern: /password['":\s=]+/i, penalty: 25, msg: 'Password detected' },
    { pattern: /api[_-]?key/i, penalty: 25, msg: 'API key reference detected' },
    { pattern: /secret/i, penalty: 15, msg: 'Secret reference detected' },
    { pattern: /private[_-]?key/i, penalty: 30, msg: 'Private key detected' },
    {
      pattern: /\b\d{3}-\d{2}-\d{4}\b/,
      penalty: 30,
      msg: 'SSN pattern detected',
    },
    {
      pattern: /\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b/,
      penalty: 30,
      msg: 'Credit card pattern detected',
    },
  ];

  for (const { pattern, penalty, msg } of sensitivePatterns) {
    if (pattern.test(input)) {
      issues.push(msg);
      score -= penalty;
    }
  }

  // Check for potentially harmful requests
  const harmfulPatterns = [
    { pattern: /how\s+to\s+hack/i, penalty: 20, msg: 'Hacking request' },
    {
      pattern: /bypass\s+(?:security|authentication)/i,
      penalty: 20,
      msg: 'Security bypass request',
    },
    {
      pattern: /steal\s+(?:data|information|credentials)/i,
      penalty: 25,
      msg: 'Data theft request',
    },
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

  // Check for scope escalation attempts
  const scopePatterns = [
    {
      pattern: /access\s+(?:all|every|full)/i,
      penalty: 15,
      msg: 'Broad access request',
    },
    {
      pattern: /admin(?:istrator)?\s+(?:access|rights|privileges)/i,
      penalty: 20,
      msg: 'Admin access request',
    },
    {
      pattern: /root\s+(?:access|privileges)/i,
      penalty: 20,
      msg: 'Root access request',
    },
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

  // If user hasn't confirmed and input is sensitive
  if (!context.userConfirmed && input.length > 1000) {
    issues.push('Large input without user confirmation');
    score -= 10;
  }

  // Check for unclear or suspicious purposes
  const suspiciousPatterns = [
    {
      pattern: /just\s+(?:do|execute|run)\s+(?:it|this)/i,
      penalty: 10,
      msg: 'Vague execution request',
    },
    {
      pattern: /don'?t\s+(?:ask|question|verify)/i,
      penalty: 15,
      msg: 'Verification avoidance',
    },
    {
      pattern: /no\s+(?:questions|explanation)/i,
      penalty: 15,
      msg: 'Explanation avoidance',
    },
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
 * Run full THSP validation
 */
export function validateTHSP(
  input: string,
  context: ValidationContext
): THSPResult {
  const truth = validateTruth(input, context);
  const harm = validateHarm(input, context);
  const scope = validateScope(input, context);
  const purpose = validatePurpose(input, context);

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
  const context: ValidationContext = {
    source: 'user',
    platform: 'generic',
    action: 'send',
    userConfirmed: false,
  };

  const result = validateTHSP(input, context);
  return result.overall;
}
