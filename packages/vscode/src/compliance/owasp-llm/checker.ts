/**
 * OWASP LLM Top 10 (2025) Compliance Checker
 *
 * Analyzes content against OWASP LLM Top 10 vulnerabilities.
 *
 * Privacy-first design:
 * - Level 1 (Heuristic): 100% local pattern matching, no network calls
 * - Level 2 (Semantic): Uses user's own API key for enhanced analysis
 *
 * Supports checking:
 * - Input (pre-inference): Detect prompt injection, extraction attempts
 * - Output (post-inference): Detect sensitive data, dangerous content
 * - Pipeline (both): Full validation of LLM interactions
 *
 * Reference: https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/
 */

import {
    OWASPComplianceResult,
    OWASPVulnerabilityFinding,
    OWASPVulnerability,
    PatternMatch,
    ComplianceCheckerConfig,
    THSPGate,
    ValidationStage,
    OWASP_VULNERABILITY_NAMES,
} from '../types';

import {
    validateContent,
    runPatterns,
    groupMatchesByPattern,
    createMetadata,
    formatRecommendation,
    deduplicateRecommendations,
    MAX_CONTENT_SIZE,
} from '../utils';

import {
    ALL_OWASP_LLM_PATTERNS,
    INPUT_VALIDATION_PATTERNS,
    OUTPUT_VALIDATION_PATTERNS,
    VULNERABILITY_GATE_MAPPING,
    getPatternsForVulnerability,
} from './patterns';

// ============================================================================
// CONSTANTS
// ============================================================================

const FRAMEWORK_VERSION = 'OWASP LLM Top 10 (2025)';

// Vulnerabilities checked during input validation
const INPUT_VULNERABILITIES: OWASPVulnerability[] = [
    'LLM01', // Prompt Injection
    'LLM06', // Excessive Agency
    'LLM07', // System Prompt Leakage (extraction attempts)
];

// Vulnerabilities checked during output validation
const OUTPUT_VULNERABILITIES: OWASPVulnerability[] = [
    'LLM02', // Sensitive Information Disclosure
    'LLM05', // Improper Output Handling
    'LLM07', // System Prompt Leakage (actual leakage)
    'LLM09', // Misinformation
];

// All vulnerabilities with THSP support
const SUPPORTED_VULNERABILITIES: OWASPVulnerability[] = [
    'LLM01', 'LLM02', 'LLM05', 'LLM06', 'LLM07', 'LLM09',
];

// Recommendations per vulnerability
const VULNERABILITY_RECOMMENDATIONS: Record<OWASPVulnerability, string> = {
    LLM01: 'Implement input sanitization and instruction hierarchy. Use Sentinel Scope gate for pre-inference validation.',
    LLM02: 'Review output for PII and sensitive data. Implement data classification and filtering.',
    LLM03: 'Audit third-party dependencies and use trusted sources only.',
    LLM04: 'Validate training data integrity and implement data provenance tracking.',
    LLM05: 'Validate all LLM outputs before passing to downstream systems. Use output validation in your pipeline.',
    LLM06: 'Limit agent capabilities and require explicit user confirmation for high-impact actions.',
    LLM07: 'Avoid including sensitive information in system prompts. Implement output filtering for prompt-like content.',
    LLM08: 'Secure vector databases and implement access controls for RAG pipelines.',
    LLM09: 'Enable epistemic humility in responses. Require citations for factual claims.',
    LLM10: 'Implement rate limiting and resource quotas. Monitor for abnormal usage patterns.',
};

// ============================================================================
// OWASP LLM CHECKER CLASS
// ============================================================================

/**
 * Checker for OWASP LLM Top 10 vulnerabilities.
 *
 * Supports three validation modes:
 * 1. Input validation: Check user input before sending to LLM
 * 2. Output validation: Check LLM output before using/displaying
 * 3. Pipeline validation: Check both input and output
 *
 * @example
 * ```typescript
 * const checker = new OWASPLLMChecker();
 *
 * // Check user input for prompt injection
 * const inputResult = checker.checkInput(userMessage);
 * if (!inputResult.secure) {
 *   console.log('Potential attack detected!');
 * }
 *
 * // Check LLM output for sensitive data
 * const outputResult = checker.checkOutput(llmResponse);
 *
 * // Full pipeline check
 * const pipelineResult = checker.checkPipeline(userMessage, llmResponse);
 * ```
 */
export class OWASPLLMChecker {
    private config: ComplianceCheckerConfig;

    constructor(config: ComplianceCheckerConfig = {}) {
        this.config = {
            maxContentSize: MAX_CONTENT_SIZE,
            failClosed: false,
            ...config,
        };
    }

    // ========================================================================
    // PUBLIC METHODS
    // ========================================================================

    /**
     * Checks user input for potential attacks (pre-inference).
     *
     * Primarily detects:
     * - LLM01: Prompt Injection
     * - LLM06: Excessive Agency attempts
     * - LLM07: System Prompt extraction attempts
     *
     * @param content - User input to validate
     * @returns Security assessment result
     */
    public checkInput(content: string): OWASPComplianceResult {
        return this.check(content, 'input', INPUT_VULNERABILITIES);
    }

    /**
     * Checks LLM output for security issues (post-inference).
     *
     * Primarily detects:
     * - LLM02: Sensitive Information Disclosure
     * - LLM05: Improper Output Handling
     * - LLM07: System Prompt Leakage
     * - LLM09: Misinformation
     *
     * @param content - LLM output to validate
     * @returns Security assessment result
     */
    public checkOutput(content: string): OWASPComplianceResult {
        return this.check(content, 'output', OUTPUT_VULNERABILITIES);
    }

    /**
     * Checks complete LLM pipeline (input + output).
     *
     * This is the recommended method for comprehensive security assessment.
     *
     * @param userInput - User input (pre-inference)
     * @param llmOutput - LLM output (post-inference)
     * @returns Combined security assessment
     */
    public checkPipeline(userInput: string, llmOutput: string): OWASPComplianceResult {
        const startTime = Date.now();

        // Validate both inputs
        validateContent(userInput, this.config.maxContentSize);
        validateContent(llmOutput, this.config.maxContentSize);

        // Run input validation
        const inputResult = this.checkInput(userInput);

        // Run output validation
        const outputResult = this.checkOutput(llmOutput);

        // Combine findings
        const allFindings = [...inputResult.findings, ...outputResult.findings];
        const vulnerabilitiesDetected = allFindings.filter(f => f.detected).length;

        // Combine recommendations
        const allRecommendations = deduplicateRecommendations([
            ...inputResult.recommendations,
            ...outputResult.recommendations,
        ]);

        // Merge gate results
        const gateResults = this.mergeGateResults(
            inputResult.metadata.gatesEvaluated,
            outputResult.metadata.gatesEvaluated
        );

        return {
            secure: vulnerabilitiesDetected === 0,
            vulnerabilitiesChecked: allFindings.length,
            vulnerabilitiesDetected,
            detectionRate: allFindings.length > 0
                ? vulnerabilitiesDetected / allFindings.length
                : 0,
            findings: allFindings,
            inputValidation: {
                checked: true,
                secure: inputResult.secure,
                vulnerabilitiesDetected: inputResult.vulnerabilitiesDetected,
            },
            outputValidation: {
                checked: true,
                secure: outputResult.secure,
                vulnerabilitiesDetected: outputResult.vulnerabilitiesDetected,
            },
            recommendations: allRecommendations,
            metadata: createMetadata(
                'owasp_llm',
                FRAMEWORK_VERSION,
                'heuristic',
                userInput.length + llmOutput.length,
                startTime,
                gateResults
            ),
        };
    }

    /**
     * Checks all vulnerabilities (for general content analysis).
     *
     * @param content - Content to analyze
     * @returns Security assessment for all vulnerabilities
     */
    public checkAll(content: string): OWASPComplianceResult {
        return this.check(content, 'pipeline', SUPPORTED_VULNERABILITIES);
    }

    // ========================================================================
    // PRIVATE METHODS
    // ========================================================================

    /**
     * Core check implementation.
     */
    private check(
        content: string,
        stage: ValidationStage,
        vulnerabilities: OWASPVulnerability[]
    ): OWASPComplianceResult {
        const startTime = Date.now();

        // Validate input
        validateContent(content, this.config.maxContentSize);

        // Select appropriate patterns
        const patterns = stage === 'input'
            ? INPUT_VALIDATION_PATTERNS
            : stage === 'output'
                ? OUTPUT_VALIDATION_PATTERNS
                : ALL_OWASP_LLM_PATTERNS;

        // Run pattern matching
        const allMatches = runPatterns(content, patterns);
        const matchesByPattern = groupMatchesByPattern(allMatches);

        // Assess each vulnerability
        const findings: OWASPVulnerabilityFinding[] = vulnerabilities.map(vuln =>
            this.assessVulnerability(vuln, content, matchesByPattern, stage)
        );

        // Calculate metrics
        const vulnerabilitiesDetected = findings.filter(f => f.detected).length;
        const detectionRate = vulnerabilities.length > 0
            ? vulnerabilitiesDetected / vulnerabilities.length
            : 0;

        // Generate recommendations
        const recommendations = this.generateRecommendations(findings, stage);

        // Approximate gate results
        const gateResults = this.approximateGateResults(findings);

        // Build validation status
        const validationStatus = stage === 'input'
            ? { inputValidation: { checked: true, secure: vulnerabilitiesDetected === 0, vulnerabilitiesDetected } }
            : stage === 'output'
                ? { outputValidation: { checked: true, secure: vulnerabilitiesDetected === 0, vulnerabilitiesDetected } }
                : {};

        return {
            secure: vulnerabilitiesDetected === 0,
            vulnerabilitiesChecked: vulnerabilities.length,
            vulnerabilitiesDetected,
            detectionRate,
            findings,
            ...validationStatus,
            recommendations: deduplicateRecommendations(recommendations),
            metadata: createMetadata(
                'owasp_llm',
                FRAMEWORK_VERSION,
                'heuristic',
                content.length,
                startTime,
                gateResults
            ),
        };
    }

    /**
     * Assesses a specific vulnerability.
     */
    private assessVulnerability(
        vuln: OWASPVulnerability,
        _content: string,
        matchesByPattern: Map<string, PatternMatch[]>,
        _stage: ValidationStage
    ): OWASPVulnerabilityFinding {
        const mapping = VULNERABILITY_GATE_MAPPING[vuln];
        const vulnPatterns = getPatternsForVulnerability(vuln);

        // Collect matches for this vulnerability
        const patternsMatched: PatternMatch[] = [];
        for (const pattern of vulnPatterns) {
            const matches = matchesByPattern.get(pattern.id);
            if (matches && matches.length > 0) {
                patternsMatched.push(...matches);
            }
        }

        const detected = patternsMatched.length > 0;

        // Determine gate status
        const gatesPassed: THSPGate[] = detected ? [] : [...mapping.gates];
        const gatesFailed: THSPGate[] = detected ? [...mapping.gates] : [];

        return {
            vulnerability: vuln,
            name: OWASP_VULNERABILITY_NAMES[vuln],
            detected,
            coverageLevel: mapping.coverage,
            gatesChecked: mapping.gates,
            gatesPassed,
            gatesFailed,
            patternsMatched,
            severity: detected ? this.getSeverityForVulnerability(vuln, patternsMatched) : undefined,
            recommendation: detected ? VULNERABILITY_RECOMMENDATIONS[vuln] : undefined,
        };
    }

    /**
     * Gets severity based on vulnerability and matches.
     */
    private getSeverityForVulnerability(
        vuln: OWASPVulnerability,
        matches: PatternMatch[]
    ): 'critical' | 'high' | 'medium' | 'low' {
        // Critical vulnerabilities
        if (['LLM01', 'LLM02'].includes(vuln)) {
            return 'high';
        }

        // Check for critical patterns in matches
        const hasCritical = matches.some(m =>
            m.patternId.includes('dan_mode') ||
            m.patternId.includes('bypass_safety') ||
            m.patternId.includes('credit_card') ||
            m.patternId.includes('command_injection')
        );

        if (hasCritical) {
            return 'critical';
        }

        // Based on coverage level
        const mapping = VULNERABILITY_GATE_MAPPING[vuln];
        if (mapping.coverage === 'strong') {
            return 'high';
        }
        if (mapping.coverage === 'moderate') {
            return 'medium';
        }

        return 'low';
    }

    /**
     * Generates recommendations based on findings.
     */
    private generateRecommendations(
        findings: OWASPVulnerabilityFinding[],
        stage: ValidationStage
    ): string[] {
        const recommendations: string[] = [];

        const detectedFindings = findings.filter(f => f.detected);

        for (const finding of detectedFindings) {
            if (finding.recommendation) {
                const severity = finding.severity || 'medium';
                recommendations.push(
                    formatRecommendation(severity, `${finding.vulnerability}: ${finding.recommendation}`)
                );
            }
        }

        // Stage-specific recommendations
        if (stage === 'input' && detectedFindings.some(f => f.vulnerability === 'LLM01')) {
            recommendations.push(
                'Consider implementing a prompt injection firewall or content filter.'
            );
        }

        if (stage === 'output' && detectedFindings.some(f => f.vulnerability === 'LLM09')) {
            recommendations.push(
                'Implement fact-checking or citation requirements for factual claims.'
            );
        }

        return recommendations;
    }

    /**
     * Approximates THSP gate results from vulnerability findings.
     */
    private approximateGateResults(
        findings: OWASPVulnerabilityFinding[]
    ): Record<THSPGate, boolean> {
        const gates: Record<THSPGate, boolean> = {
            truth: true,
            harm: true,
            scope: true,
            purpose: true,
        };

        for (const finding of findings) {
            if (finding.detected) {
                for (const gate of finding.gatesFailed) {
                    gates[gate] = false;
                }
            }
        }

        return gates;
    }

    /**
     * Merges gate results from multiple checks.
     */
    private mergeGateResults(
        gates1?: Record<THSPGate, boolean>,
        gates2?: Record<THSPGate, boolean>
    ): Record<THSPGate, boolean> {
        const gates: Record<THSPGate, boolean> = {
            truth: true,
            harm: true,
            scope: true,
            purpose: true,
        };

        if (gates1) {
            for (const gate of Object.keys(gates) as THSPGate[]) {
                if (gates1[gate] === false) {
                    gates[gate] = false;
                }
            }
        }

        if (gates2) {
            for (const gate of Object.keys(gates) as THSPGate[]) {
                if (gates2[gate] === false) {
                    gates[gate] = false;
                }
            }
        }

        return gates;
    }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Quick check for prompt injection in user input.
 *
 * @example
 * ```typescript
 * if (hasPromptInjection(userMessage)) {
 *   console.log('Warning: Potential prompt injection detected');
 * }
 * ```
 */
export function hasPromptInjection(content: string): boolean {
    const checker = new OWASPLLMChecker();
    const result = checker.checkInput(content);
    return result.findings.some(f => f.vulnerability === 'LLM01' && f.detected);
}

/**
 * Quick check for sensitive information in output.
 *
 * @example
 * ```typescript
 * if (hasSensitiveInfo(llmResponse)) {
 *   console.log('Warning: Sensitive information detected');
 * }
 * ```
 */
export function hasSensitiveInfo(content: string): boolean {
    const checker = new OWASPLLMChecker();
    const result = checker.checkOutput(content);
    return result.findings.some(f => f.vulnerability === 'LLM02' && f.detected);
}

/**
 * Full OWASP LLM compliance check.
 *
 * @example
 * ```typescript
 * const result = checkOWASPLLMCompliance(content);
 * if (!result.secure) {
 *   console.log(`Detected ${result.vulnerabilitiesDetected} vulnerabilities`);
 * }
 * ```
 */
export function checkOWASPLLMCompliance(
    content: string,
    config?: ComplianceCheckerConfig
): OWASPComplianceResult {
    const checker = new OWASPLLMChecker(config);
    return checker.checkAll(content);
}
