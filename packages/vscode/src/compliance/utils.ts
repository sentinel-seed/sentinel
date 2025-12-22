/**
 * Compliance Checker Utilities
 *
 * Common utilities shared across all compliance checkers.
 * Provides content validation, line/column calculation, and helper functions.
 */

import {
    PatternMatch,
    CompliancePattern,
    Severity,
    THSPGate,
    ComplianceMetadata,
    ComplianceFramework,
    AnalysisMethod,
} from './types';

// ============================================================================
// CONSTANTS
// ============================================================================

/** Maximum content size in bytes (50KB) */
export const MAX_CONTENT_SIZE = 50 * 1024;

/** Default timeout for API calls (30 seconds) */
export const DEFAULT_TIMEOUT_MS = 30000;

// ============================================================================
// CONTENT VALIDATION
// ============================================================================

/**
 * Validates content before analysis.
 * Throws descriptive errors for invalid inputs.
 *
 * @param content - Content to validate
 * @param maxSize - Maximum allowed size in bytes
 * @throws Error if content is invalid
 */
export function validateContent(content: unknown, maxSize: number = MAX_CONTENT_SIZE): void {
    if (content === null || content === undefined) {
        throw new Error('Content cannot be null or undefined');
    }

    if (typeof content !== 'string') {
        throw new Error(`Content must be a string, got: ${typeof content}`);
    }

    const trimmed = content.trim();
    if (trimmed.length === 0) {
        throw new Error('Content cannot be empty or whitespace only');
    }

    const byteSize = new TextEncoder().encode(content).length;
    if (byteSize > maxSize) {
        throw new Error(
            `Content size (${byteSize} bytes) exceeds maximum allowed (${maxSize} bytes)`
        );
    }
}

// ============================================================================
// LINE/COLUMN CALCULATION
// ============================================================================

/**
 * Calculates line and column number for a position in text.
 * Line and column are 1-based (as displayed in editors).
 *
 * @param content - Full content string
 * @param position - Character offset (0-based)
 * @returns Object with line and column numbers (1-based)
 */
export function getLineColumn(content: string, position: number): { line: number; column: number } {
    if (position < 0 || position > content.length) {
        return { line: 1, column: 1 };
    }

    const beforePosition = content.substring(0, position);
    const lines = beforePosition.split('\n');

    return {
        line: lines.length,
        column: lines[lines.length - 1].length + 1,
    };
}

// ============================================================================
// PATTERN MATCHING
// ============================================================================

/**
 * Runs a set of patterns against content and returns all matches.
 * Properly handles regex flags and tracks positions.
 *
 * @param content - Content to analyze
 * @param patterns - Array of patterns to check
 * @returns Array of pattern matches with positions
 */
export function runPatterns(
    content: string,
    patterns: CompliancePattern[]
): PatternMatch[] {
    const matches: PatternMatch[] = [];
    const contentLower = content.toLowerCase();

    for (const pattern of patterns) {
        // Reset regex state for global patterns
        pattern.pattern.lastIndex = 0;

        // Use global matching to find all occurrences
        const regex = new RegExp(pattern.pattern.source, 'gi');
        let match: RegExpExecArray | null;

        while ((match = regex.exec(contentLower)) !== null) {
            const position = match.index;
            const { line, column } = getLineColumn(content, position);

            // Extract matched text from original content (preserve case)
            const matchedText = content.substring(position, position + match[0].length);

            matches.push({
                patternId: pattern.id,
                matchedText: truncateText(matchedText, 100),
                position,
                line,
                column,
            });

            // Prevent infinite loops with zero-length matches
            if (match[0].length === 0) {
                regex.lastIndex++;
            }
        }
    }

    return matches;
}

/**
 * Groups pattern matches by pattern ID.
 *
 * @param matches - Array of pattern matches
 * @returns Map of pattern ID to matches
 */
export function groupMatchesByPattern(matches: PatternMatch[]): Map<string, PatternMatch[]> {
    const grouped = new Map<string, PatternMatch[]>();

    for (const match of matches) {
        const existing = grouped.get(match.patternId) || [];
        existing.push(match);
        grouped.set(match.patternId, existing);
    }

    return grouped;
}

/**
 * Gets patterns that matched (with at least one match).
 *
 * @param matches - Array of pattern matches
 * @param patterns - Original pattern definitions
 * @returns Patterns that had at least one match
 */
export function getMatchedPatterns(
    matches: PatternMatch[],
    patterns: CompliancePattern[]
): CompliancePattern[] {
    const matchedIds = new Set(matches.map(m => m.patternId));
    return patterns.filter(p => matchedIds.has(p.id));
}

// ============================================================================
// SEVERITY HELPERS
// ============================================================================

/**
 * Severity ranking for comparisons.
 * Higher number = more severe.
 */
const SEVERITY_RANK: Record<Severity, number> = {
    critical: 5,
    high: 4,
    medium: 3,
    low: 2,
    info: 1,
};

/**
 * Gets the highest severity from an array.
 *
 * @param severities - Array of severity values
 * @returns Highest severity, or 'info' if empty
 */
export function getHighestSeverity(severities: Severity[]): Severity {
    if (severities.length === 0) {
        return 'info';
    }

    return severities.reduce((highest, current) =>
        SEVERITY_RANK[current] > SEVERITY_RANK[highest] ? current : highest
    );
}

/**
 * Compares two severities.
 *
 * @returns Negative if a < b, 0 if equal, positive if a > b
 */
export function compareSeverity(a: Severity, b: Severity): number {
    return SEVERITY_RANK[a] - SEVERITY_RANK[b];
}

// ============================================================================
// GATE HELPERS
// ============================================================================

/**
 * Checks if all specified gates passed.
 *
 * @param gateResults - Map of gate to pass/fail
 * @param gates - Gates to check
 * @returns True if all specified gates passed
 */
export function allGatesPassed(
    gateResults: Record<THSPGate, boolean>,
    gates: THSPGate[]
): boolean {
    return gates.every(gate => gateResults[gate] === true);
}

/**
 * Gets list of failed gates from gate results.
 *
 * @param gateResults - Map of gate to pass/fail
 * @returns Array of gate names that failed
 */
export function getFailedGates(gateResults: Record<THSPGate, boolean>): THSPGate[] {
    const gates: THSPGate[] = ['truth', 'harm', 'scope', 'purpose'];
    return gates.filter(gate => gateResults[gate] === false);
}

/**
 * Gets list of passed gates from gate results.
 *
 * @param gateResults - Map of gate to pass/fail
 * @returns Array of gate names that passed
 */
export function getPassedGates(gateResults: Record<THSPGate, boolean>): THSPGate[] {
    const gates: THSPGate[] = ['truth', 'harm', 'scope', 'purpose'];
    return gates.filter(gate => gateResults[gate] === true);
}

// ============================================================================
// METADATA HELPERS
// ============================================================================

/**
 * Creates compliance metadata object.
 *
 * @param framework - Framework being checked
 * @param frameworkVersion - Version string
 * @param method - Analysis method used
 * @param contentSize - Size of content analyzed
 * @param startTime - Start time for processing duration
 * @param gateResults - Optional gate results
 * @returns ComplianceMetadata object
 */
export function createMetadata(
    framework: ComplianceFramework,
    frameworkVersion: string,
    method: AnalysisMethod,
    contentSize: number,
    startTime: number,
    gateResults?: Record<THSPGate, boolean>
): ComplianceMetadata {
    const processingTimeMs = Date.now() - startTime;

    const metadata: ComplianceMetadata = {
        timestamp: new Date().toISOString(),
        framework,
        frameworkVersion,
        analysisMethod: method,
        contentSize,
        processingTimeMs,
    };

    if (gateResults) {
        metadata.gatesEvaluated = gateResults;
        metadata.failedGates = getFailedGates(gateResults);
    }

    return metadata;
}

// ============================================================================
// STRING HELPERS
// ============================================================================

/**
 * Truncates text to specified length, adding ellipsis if truncated.
 *
 * @param text - Text to truncate
 * @param maxLength - Maximum length
 * @returns Truncated text
 */
export function truncateText(text: string, maxLength: number): string {
    if (text.length <= maxLength) {
        return text;
    }
    return text.substring(0, maxLength - 3) + '...';
}

/**
 * Sanitizes content for display (removes control characters).
 *
 * @param text - Text to sanitize
 * @returns Sanitized text
 */
export function sanitizeForDisplay(text: string): string {
    // Replace control characters except newlines and tabs
    // eslint-disable-next-line no-control-regex
    return text.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');
}

/**
 * Escapes special regex characters in a string.
 *
 * @param str - String to escape
 * @returns Escaped string safe for use in RegExp
 */
export function escapeRegex(str: string): string {
    return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// ============================================================================
// RECOMMENDATION HELPERS
// ============================================================================

/**
 * Deduplicates and sorts recommendations.
 *
 * @param recommendations - Array of recommendations (may have duplicates)
 * @returns Deduplicated and sorted array
 */
export function deduplicateRecommendations(recommendations: string[]): string[] {
    const unique = [...new Set(recommendations)];
    // Sort by severity prefix (HIGH:, MEDIUM:, etc.) then alphabetically
    return unique.sort((a, b) => {
        const severityOrder = ['CRITICAL:', 'HIGH:', 'MEDIUM:', 'LOW:'];
        const aIndex = severityOrder.findIndex(s => a.startsWith(s));
        const bIndex = severityOrder.findIndex(s => b.startsWith(s));

        if (aIndex !== bIndex) {
            // Items with severity prefix come first
            if (aIndex === -1) return 1;
            if (bIndex === -1) return -1;
            return aIndex - bIndex;
        }

        return a.localeCompare(b);
    });
}

/**
 * Formats a recommendation with severity prefix.
 *
 * @param severity - Severity level
 * @param message - Recommendation message
 * @returns Formatted recommendation
 */
export function formatRecommendation(severity: Severity, message: string): string {
    if (severity === 'critical' || severity === 'high') {
        return `${severity.toUpperCase()}: ${message}`;
    }
    if (severity === 'medium') {
        return `MEDIUM: ${message}`;
    }
    return message;
}

// ============================================================================
// CONTENT ANALYSIS HELPERS
// ============================================================================

/**
 * Extracts context around a match position.
 *
 * @param content - Full content
 * @param position - Match position
 * @param contextChars - Number of characters of context (before and after)
 * @returns Context string with match highlighted
 */
export function getMatchContext(
    content: string,
    position: number,
    matchLength: number,
    contextChars: number = 50
): string {
    const start = Math.max(0, position - contextChars);
    const end = Math.min(content.length, position + matchLength + contextChars);

    let context = content.substring(start, end);

    // Clean up for display
    context = context.replace(/\n/g, ' ').replace(/\s+/g, ' ');

    // Add ellipsis if truncated
    if (start > 0) {
        context = '...' + context;
    }
    if (end < content.length) {
        context = context + '...';
    }

    return context;
}

/**
 * Checks if content likely contains code.
 * Used to adjust analysis sensitivity.
 *
 * @param content - Content to check
 * @returns True if content appears to be code
 */
export function isLikelyCode(content: string): boolean {
    const codeIndicators = [
        /^\s*(import|from|const|let|var|function|class|def|public|private)\s/m,
        /[{}[\]();]/,
        /=>/,
        /\bif\s*\(/,
        /\bfor\s*\(/,
        /\bwhile\s*\(/,
    ];

    return codeIndicators.some(pattern => pattern.test(content));
}

/**
 * Checks if content is likely a system prompt.
 * Used to enable appropriate checks.
 *
 * @param content - Content to check
 * @returns True if content appears to be a system prompt
 */
export function isLikelySystemPrompt(content: string): boolean {
    const promptIndicators = [
        /you\s+are\s+(a|an)/i,
        /your\s+(role|task|job)\s+is/i,
        /you\s+(must|should|will)\s+(not|never|always)/i,
        /instructions?:/i,
        /\brules?:/i,
        /\bconstraints?:/i,
    ];

    return promptIndicators.some(pattern => pattern.test(content));
}
