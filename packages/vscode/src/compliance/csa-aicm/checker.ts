/**
 * CSA AI Controls Matrix (AICM) Compliance Checker
 *
 * Analyzes content against CSA AI Controls Matrix requirements.
 *
 * Privacy-first design:
 * - Level 1 (Heuristic): 100% local pattern matching, no network calls
 * - Level 2 (Semantic): Uses user's own API key for enhanced analysis
 *
 * The checker evaluates THSP gates against AICM domains:
 * - Strong coverage: Model Security, Governance, Supply Chain
 * - Moderate coverage: Data Security, Threat Management, Application Security
 * - Indirect coverage: Audit, IAM, Logging, Incident Management
 *
 * Reference: https://cloudsecurityalliance.org/artifacts/ai-controls-matrix
 */

import {
    AICMComplianceResult,
    AICMDomainFinding,
    AICMThreatAssessment,
    AICMDomain,
    AICMThreatCategory,
    PatternMatch,
    ComplianceCheckerConfig,
    THSPGate,
    CoverageLevel,
    Severity,
} from '../types';

import {
    validateContent,
    runPatterns,
    createMetadata,
    formatRecommendation,
    deduplicateRecommendations,
    MAX_CONTENT_SIZE,
} from '../utils';

import {
    ALL_CSA_AICM_PATTERNS,
    DOMAIN_GATE_MAPPING,
    THREAT_GATE_MAPPING,
    DOMAIN_RECOMMENDATIONS,
    getSupportedDomains,
    getDomainDisplayName,
} from './patterns';

// ============================================================================
// CONSTANTS
// ============================================================================

const FRAMEWORK_VERSION = 'CSA AI Controls Matrix v1.0 (July 2025)';

// Gate-specific recommendations
const GATE_RECOMMENDATIONS: Record<THSPGate, string> = {
    truth: 'Truth Gate: Implement accuracy verification and epistemic humility',
    harm: 'Harm Gate: Add harm mitigation controls and content filtering',
    scope: 'Scope Gate: Enforce operational boundaries and input validation',
    purpose: 'Purpose Gate: Document legitimate purpose and decision justification',
};

// ============================================================================
// CSA AICM CHECKER CLASS
// ============================================================================

/**
 * Checker for CSA AI Controls Matrix compliance.
 *
 * Evaluates AI system outputs against applicable AICM domains using THSP gates.
 *
 * @example
 * ```typescript
 * const checker = new CSAAICMChecker();
 *
 * // Check all supported domains
 * const result = checker.check(content);
 *
 * // Check specific domains
 * const result2 = checker.check(content, {
 *   domains: ['model_security', 'data_security_privacy']
 * });
 *
 * console.log(`Compliance rate: ${result.complianceRate * 100}%`);
 * ```
 */
export class CSAAICMChecker {
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
     * Performs compliance check against AICM domains.
     *
     * @param content - Content to analyze
     * @param options - Check options
     * @returns Compliance assessment result
     */
    public check(
        content: string,
        options: {
            domains?: AICMDomain[];
        } = {}
    ): AICMComplianceResult {
        const startTime = Date.now();
        const { domains = getSupportedDomains() } = options;

        // Validate input
        validateContent(content, this.config.maxContentSize);

        // Run pattern matching
        const allMatches = runPatterns(content, ALL_CSA_AICM_PATTERNS);

        // Approximate gate results from pattern matches
        const gateResults = this.approximateGateResults(allMatches);
        const isSafe = Object.values(gateResults).every(v => v);
        const failedGates = (Object.entries(gateResults) as [THSPGate, boolean][])
            .filter(([_, passed]) => !passed)
            .map(([gate]) => gate);

        // Assess each domain
        const domainFindings: AICMDomainFinding[] = domains.map(domain =>
            this.assessDomain(domain, gateResults)
        );

        // Threat assessment
        const threatAssessment = this.assessThreats(content, gateResults, failedGates);

        // Generate recommendations
        const recommendations = this.generateRecommendations(domainFindings, gateResults);

        // Calculate metrics
        const domainsCompliant = domainFindings.filter(f => f.compliant).length;
        const complianceRate = domains.length > 0 ? domainsCompliant / domains.length : 0;

        // Overall compliance
        const compliant = domainFindings.every(f => f.compliant) && isSafe;

        return {
            compliant,
            domainsAssessed: domains.length,
            domainsCompliant,
            complianceRate,
            domainFindings,
            threatAssessment,
            recommendations: deduplicateRecommendations(recommendations),
            metadata: createMetadata(
                'csa_aicm',
                FRAMEWORK_VERSION,
                'heuristic',
                content.length,
                startTime,
                gateResults
            ),
        };
    }

    /**
     * Checks a single domain.
     *
     * @param content - Content to analyze
     * @param domain - Domain to check
     * @returns Domain finding
     */
    public checkDomain(content: string, domain: AICMDomain): AICMDomainFinding {
        const result = this.check(content, { domains: [domain] });
        return result.domainFindings[0];
    }

    // ========================================================================
    // PRIVATE METHODS - DOMAIN ASSESSMENT
    // ========================================================================

    /**
     * Assesses compliance for a specific domain.
     */
    private assessDomain(
        domain: AICMDomain,
        gateResults: Record<THSPGate, boolean>
    ): AICMDomainFinding {
        const mapping = DOMAIN_GATE_MAPPING[domain];
        const relevantGates = mapping.gates;
        const coverage = mapping.coverage;

        // N/A domains are always compliant
        if (!relevantGates.length || coverage === 'not_applicable') {
            return {
                domain,
                displayName: getDomainDisplayName(domain),
                compliant: true,
                coverageLevel: coverage,
                gatesChecked: [],
                gatesPassed: [],
                gatesFailed: [],
                recommendation: 'Domain not applicable to THSP - use infrastructure controls',
            };
        }

        // Check relevant gates
        const gatesPassed = relevantGates.filter(g => gateResults[g] === true);
        const gatesFailed = relevantGates.filter(g => gateResults[g] === false);
        const compliant = gatesFailed.length === 0;

        // Determine severity and recommendation
        let severity: Severity | undefined;
        let recommendation: string | undefined;

        if (!compliant) {
            if (coverage === 'strong') {
                severity = 'high';
            } else if (coverage === 'moderate') {
                severity = 'medium';
            } else {
                severity = 'low';
            }
            recommendation = DOMAIN_RECOMMENDATIONS[domain];
        }

        return {
            domain,
            displayName: getDomainDisplayName(domain),
            compliant,
            coverageLevel: coverage,
            gatesChecked: relevantGates,
            gatesPassed,
            gatesFailed,
            severity,
            recommendation,
        };
    }

    // ========================================================================
    // PRIVATE METHODS - THREAT ASSESSMENT
    // ========================================================================

    /**
     * Assesses content against AICM threat categories.
     */
    private assessThreats(
        _content: string,
        gateResults: Record<THSPGate, boolean>,
        _failedGates: THSPGate[]
    ): AICMThreatAssessment {
        const threatsMitigated: AICMThreatCategory[] = [];
        const threatsDetected: string[] = [];

        for (const [threat, mapping] of Object.entries(THREAT_GATE_MAPPING)) {
            const threatCategory = threat as AICMThreatCategory;

            // Only check threats with strong or moderate coverage
            if (mapping.coverage === 'strong' || mapping.coverage === 'moderate') {
                if (mapping.gates.length > 0) {
                    const gatesOk = mapping.gates.every(g => gateResults[g] === true);
                    if (gatesOk) {
                        threatsMitigated.push(threatCategory);
                    } else {
                        threatsDetected.push(`${threatCategory}: ${mapping.description}`);
                    }
                }
            }
        }

        // Calculate threat score
        const totalThreats = Object.values(THREAT_GATE_MAPPING).filter(
            t => t.coverage === 'strong' || t.coverage === 'moderate'
        ).length;
        const detectedCount = threatsDetected.length;
        const threatScore = totalThreats > 0 ? detectedCount / totalThreats : 0;

        return {
            threatsMitigated,
            threatsDetected,
            overallThreatScore: threatScore,
        };
    }

    // ========================================================================
    // PRIVATE METHODS - RECOMMENDATIONS
    // ========================================================================

    /**
     * Generates recommendations based on findings.
     */
    private generateRecommendations(
        findings: AICMDomainFinding[],
        gateResults: Record<THSPGate, boolean>
    ): string[] {
        const recommendations: string[] = [];

        // Domain-specific recommendations
        for (const finding of findings) {
            if (!finding.compliant && finding.recommendation) {
                const severity = finding.severity || 'medium';
                recommendations.push(
                    formatRecommendation(
                        severity,
                        `Domain ${finding.displayName}: ${finding.recommendation}`
                    )
                );
            }
        }

        // Gate-specific recommendations
        for (const [gate, passed] of Object.entries(gateResults) as [THSPGate, boolean][]) {
            if (!passed) {
                recommendations.push(GATE_RECOMMENDATIONS[gate]);
            }
        }

        // General recommendations if any non-compliance
        const hasNonCompliance = findings.some(f => !f.compliant);
        if (hasNonCompliance) {
            recommendations.push(
                'Consider STAR for AI certification for formal compliance validation'
            );
        }

        return recommendations;
    }

    // ========================================================================
    // PRIVATE METHODS - GATE APPROXIMATION
    // ========================================================================

    /**
     * Approximates THSP gate results from pattern matches.
     */
    private approximateGateResults(matches: PatternMatch[]): Record<THSPGate, boolean> {
        const gates: Record<THSPGate, boolean> = {
            truth: true,
            harm: true,
            scope: true,
            purpose: true,
        };

        // Get matched pattern IDs
        const matchedPatternIds = new Set(matches.map(m => m.patternId));

        // Check which gates are affected by matched patterns
        for (const pattern of ALL_CSA_AICM_PATTERNS) {
            if (matchedPatternIds.has(pattern.id)) {
                for (const gate of pattern.gates) {
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
 * Quick CSA AICM compliance check.
 *
 * @example
 * ```typescript
 * const result = checkCSAAICMCompliance(content);
 * console.log(`Compliance: ${result.complianceRate * 100}%`);
 * ```
 */
export function checkCSAAICMCompliance(
    content: string,
    config?: ComplianceCheckerConfig
): AICMComplianceResult {
    const checker = new CSAAICMChecker(config);
    return checker.check(content);
}

/**
 * Gets the list of domains supported by THSP.
 */
export function getThspSupportedDomains(): { domain: AICMDomain; coverage: CoverageLevel }[] {
    return getSupportedDomains().map(domain => ({
        domain,
        coverage: DOMAIN_GATE_MAPPING[domain].coverage,
    }));
}
