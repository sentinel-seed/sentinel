/**
 * Shared THSP patterns for both linter and analyzer
 *
 * These patterns are used for heuristic analysis when LLM is not available.
 * They have ~50% accuracy - semantic analysis is recommended for production.
 */

export interface THSPPattern {
    pattern: RegExp;
    gate: 'truth' | 'harm' | 'scope' | 'purpose';
    message: string;
    severity: 'error' | 'warning' | 'info';
}

/**
 * THSP Gate patterns for detecting potential safety issues
 */
export const THSP_PATTERNS: THSPPattern[] = [
    // === SCOPE GATE (Jailbreak attempts) ===
    {
        pattern: /ignore\s+(previous|all|your)\s+(instructions?|guidelines?|rules?)/gi,
        gate: 'scope',
        message: 'Potential jailbreak: instruction override',
        severity: 'warning'
    },
    {
        pattern: /you\s+are\s+now\s+(DAN|an?\s+AI\s+without|evil|unrestricted)/gi,
        gate: 'scope',
        message: 'Potential jailbreak: persona switch',
        severity: 'warning'
    },
    {
        pattern: /pretend\s+(you('re)?|to\s+be)\s+(an?\s+)?(evil|unrestricted|unfiltered)/gi,
        gate: 'scope',
        message: 'Potential jailbreak: evil persona',
        severity: 'warning'
    },
    {
        pattern: /(developer|sudo|god|admin)\s+mode/gi,
        gate: 'scope',
        message: 'Potential jailbreak: mode switch',
        severity: 'warning'
    },
    {
        pattern: /(disable|bypass|ignore|override)\s+(safety|content\s+filter|guardrails?|restrictions?)/gi,
        gate: 'scope',
        message: 'Potential jailbreak: safety bypass',
        severity: 'error'
    },

    // === HARM GATE (Harmful content) ===
    {
        pattern: /\b(make|create|build|construct)\s+(a\s+)?(bomb|explosive|weapon|poison)/gi,
        gate: 'harm',
        message: 'Potential harmful content: weapons/explosives',
        severity: 'error'
    },
    {
        pattern: /\bhow\s+to\s+(hack|exploit|breach|attack|compromise)\b/gi,
        gate: 'harm',
        message: 'Potential harmful content: hacking instructions',
        severity: 'warning'
    },
    {
        pattern: /\b(write|create|develop)\s+(malware|ransomware|keylogger|virus|trojan)/gi,
        gate: 'harm',
        message: 'Potential harmful content: malicious software',
        severity: 'error'
    },
    {
        pattern: /\b(phishing|spear\s*phishing)\s+(email|template|attack)/gi,
        gate: 'harm',
        message: 'Potential harmful content: phishing',
        severity: 'error'
    },

    // === TRUTH GATE (Deception) ===
    {
        pattern: /\b(create|write|generate)\s+(fake|forged?|counterfeit)\s+(document|id|identity|news|article)/gi,
        gate: 'truth',
        message: 'Potential deception: fake documents',
        severity: 'warning'
    },
    {
        pattern: /\bimpersonate\s+(a\s+)?(person|someone|official|authority)/gi,
        gate: 'truth',
        message: 'Potential deception: impersonation',
        severity: 'warning'
    },
    {
        pattern: /\b(spread|create)\s+(misinformation|disinformation|false\s+information)/gi,
        gate: 'truth',
        message: 'Potential deception: misinformation',
        severity: 'warning'
    },

    // === PURPOSE GATE (Purposeless/destructive) ===
    {
        pattern: /\b(destroy|delete|erase)\s+(everything|all(\s+files)?)\s+(for\s+)?(no\s+reason|fun|chaos)/gi,
        gate: 'purpose',
        message: 'Purposeless destructive action',
        severity: 'warning'
    },
    {
        pattern: /\bjust\s+(do|execute|run)\s+it\s+(without|no)\s+(asking|questions?|reason)/gi,
        gate: 'purpose',
        message: 'Action without clear purpose',
        severity: 'info'
    }
];

/**
 * Patterns that indicate good safety practices
 * Note: Using 'i' flag only (case-insensitive) since we use .test() which doesn't need global flag
 */
export const SAFE_PATTERNS: RegExp[] = [
    /sentinel\s+alignment\s+seed/i,
    /thsp\s+protocol/i,
    /truth.*harm.*scope.*purpose/i
];

/**
 * Check content against THSP patterns
 */
export function checkPatterns(content: string): {
    issues: string[];
    gates: { truth: boolean; harm: boolean; scope: boolean; purpose: boolean };
} {
    const issues: string[] = [];
    const gates = { truth: true, harm: true, scope: true, purpose: true };

    for (const { pattern, gate, message } of THSP_PATTERNS) {
        // Reset regex lastIndex for global patterns
        pattern.lastIndex = 0;
        if (pattern.test(content)) {
            issues.push(`${message} [heuristic]`);
            gates[gate] = false;
        }
    }

    return { issues, gates };
}

/**
 * Check if content contains Sentinel seed
 * Note: SAFE_PATTERNS use 'i' flag only, no need for lastIndex reset
 */
export function hasSentinelSeed(content: string): boolean {
    return SAFE_PATTERNS.some(pattern => pattern.test(content));
}
