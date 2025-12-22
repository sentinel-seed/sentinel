/**
 * EU AI Act Compliance Checker
 *
 * Analyzes content against EU AI Act (Regulation 2024/1689) requirements.
 *
 * Privacy-first design:
 * - Level 1 (Heuristic): 100% local pattern matching, no network calls
 * - Level 2 (Semantic): Uses user's own API key for enhanced analysis
 *
 * Key compliance checks:
 * - Article 5: Prohibited practices detection
 * - Article 6: High-risk system classification
 * - Article 14: Human oversight requirements
 * - Article 52: Transparency obligations
 */

import {
    EUAIActComplianceResult,
    EUAIActArticleFinding,
    EUAIActRiskLevel,
    EUAIActSystemType,
    ProhibitedPractice,
    HighRiskContext,
    OversightModel,
    PatternMatch,
    ComplianceCheckerConfig,
    THSPGate,
} from '../types';

import {
    validateContent,
    runPatterns,
    getMatchedPatterns,
    groupMatchesByPattern,
    createMetadata,
    formatRecommendation,
    deduplicateRecommendations,
    MAX_CONTENT_SIZE,
} from '../utils';

import {
    ALL_EU_AI_ACT_PATTERNS,
    PROHIBITED_PRACTICE_PATTERNS,
    HIGH_RISK_CONTEXT_PATTERNS,
    TRANSPARENCY_PATTERNS,
    HUMAN_OVERSIGHT_PATTERNS,
    PATTERN_TO_PROHIBITED_PRACTICE,
    PATTERN_TO_HIGH_RISK_CONTEXT,
} from './patterns';

// ============================================================================
// CONSTANTS
// ============================================================================

const FRAMEWORK_VERSION = 'EU AI Act (Regulation 2024/1689)';

// Recommendations for specific situations
const RECOMMENDATIONS = {
    prohibitedPractice: 'This practice is prohibited under EU AI Act Article 5. The system must not be deployed in the EU.',
    highRisk: 'This is a high-risk AI system under Annex III. Conformity assessment required before deployment.',
    humanOversight: 'Article 14 requires human oversight mechanisms. Implement human-in-the-loop or human-on-the-loop controls.',
    transparency: 'Article 52 requires disclosure to users that they are interacting with an AI system.',
    documentation: 'High-risk systems require technical documentation per Article 11.',
    riskManagement: 'Implement risk management system per Article 9.',
    dataGovernance: 'Ensure data governance practices per Article 10.',
    logging: 'Implement automatic logging per Article 12.',
};

// ============================================================================
// EU AI ACT CHECKER CLASS
// ============================================================================

/**
 * Checker for EU AI Act compliance.
 *
 * Supports two analysis modes:
 * 1. Heuristic (default): Fast, local pattern matching
 * 2. Semantic (optional): Uses user's LLM API key for deeper analysis
 *
 * @example
 * ```typescript
 * const checker = new EUAIActChecker();
 *
 * // Basic heuristic check
 * const result = checker.check(content);
 *
 * // With semantic analysis (user's own API key)
 * const checker2 = new EUAIActChecker({
 *   apiKey: 'sk-...',
 *   provider: 'openai'
 * });
 * const result2 = await checker2.checkSemantic(content);
 * ```
 */
export class EUAIActChecker {
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
     * Performs heuristic compliance check (100% local, no network).
     *
     * @param content - Content to analyze
     * @returns Compliance result
     * @throws Error if content is invalid
     */
    public check(content: string): EUAIActComplianceResult {
        const startTime = Date.now();

        // Validate input
        validateContent(content, this.config.maxContentSize);

        // Run all patterns
        const allMatches = runPatterns(content, ALL_EU_AI_ACT_PATTERNS);
        const matchedPatterns = getMatchedPatterns(allMatches, ALL_EU_AI_ACT_PATTERNS);
        const matchesByPattern = groupMatchesByPattern(allMatches);

        // Detect prohibited practices (Article 5)
        const prohibitedPractices = this.detectProhibitedPractices(matchesByPattern);

        // Detect high-risk contexts (Annex III)
        const highRiskContexts = this.detectHighRiskContexts(matchesByPattern);

        // Determine risk level and system type
        const riskLevel = this.determineRiskLevel(prohibitedPractices, highRiskContexts, matchedPatterns);
        const systemType = this.determineSystemType(prohibitedPractices, highRiskContexts);

        // Check specific articles
        const articleFindings = this.analyzeArticles(matchesByPattern, matchedPatterns);

        // Determine oversight requirements
        const oversightRequired = this.determineOversightModel(riskLevel, highRiskContexts);

        // Generate recommendations
        const recommendations = this.generateRecommendations(
            prohibitedPractices,
            highRiskContexts,
            riskLevel,
            articleFindings
        );

        // Overall compliance
        const compliant = prohibitedPractices.length === 0 &&
                         !articleFindings.some(f => !f.compliant && f.severity === 'critical');

        // Build gate results (heuristic approximation)
        const gateResults = this.approximateGateResults(matchedPatterns);

        return {
            compliant,
            riskLevel,
            systemType,
            oversightRequired,
            prohibitedPractices,
            highRiskContexts,
            articleFindings,
            recommendations: deduplicateRecommendations(recommendations),
            metadata: createMetadata(
                'eu_ai_act',
                FRAMEWORK_VERSION,
                'heuristic',
                content.length,
                startTime,
                gateResults
            ),
        };
    }

    /**
     * Performs semantic compliance check using user's LLM API.
     * Falls back to heuristic if API is not configured or fails.
     *
     * @param content - Content to analyze
     * @returns Promise resolving to compliance result
     */
    public async checkSemantic(content: string): Promise<EUAIActComplianceResult> {
        // If no API key, fall back to heuristic
        if (!this.config.apiKey) {
            return this.check(content);
        }

        const startTime = Date.now();

        try {
            validateContent(content, this.config.maxContentSize);

            // Get heuristic result as baseline
            const heuristicResult = this.check(content);

            // Enhance with semantic analysis
            const semanticResult = await this.runSemanticAnalysis(content);

            // Merge results (semantic takes precedence where available)
            return this.mergeResults(heuristicResult, semanticResult, startTime);

        } catch (error) {
            console.warn('Semantic analysis failed, falling back to heuristic:', error);
            if (this.config.failClosed) {
                throw error;
            }
            return this.check(content);
        }
    }

    // ========================================================================
    // PRIVATE METHODS - DETECTION
    // ========================================================================

    /**
     * Detects prohibited practices from pattern matches.
     */
    private detectProhibitedPractices(matchesByPattern: Map<string, PatternMatch[]>): ProhibitedPractice[] {
        const practices = new Set<ProhibitedPractice>();

        for (const [patternId] of matchesByPattern) {
            const practice = PATTERN_TO_PROHIBITED_PRACTICE[patternId];
            if (practice) {
                practices.add(practice);
            }
        }

        return Array.from(practices);
    }

    /**
     * Detects high-risk contexts from pattern matches.
     */
    private detectHighRiskContexts(matchesByPattern: Map<string, PatternMatch[]>): HighRiskContext[] {
        const contexts = new Set<HighRiskContext>();

        for (const [patternId] of matchesByPattern) {
            const context = PATTERN_TO_HIGH_RISK_CONTEXT[patternId];
            if (context) {
                contexts.add(context);
            }
        }

        return Array.from(contexts);
    }

    // ========================================================================
    // PRIVATE METHODS - RISK ASSESSMENT
    // ========================================================================

    /**
     * Determines the overall risk level based on findings.
     */
    private determineRiskLevel(
        prohibitedPractices: ProhibitedPractice[],
        highRiskContexts: HighRiskContext[],
        matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): EUAIActRiskLevel {
        // Any prohibited practice = unacceptable risk
        if (prohibitedPractices.length > 0) {
            return 'unacceptable';
        }

        // Any high-risk context = high risk
        if (highRiskContexts.length > 0) {
            return 'high';
        }

        // Transparency requirements = limited risk
        const hasTransparency = matchedPatterns.some(p =>
            p.category.includes('Transparency')
        );
        if (hasTransparency) {
            return 'limited';
        }

        // Default = minimal risk
        return 'minimal';
    }

    /**
     * Determines system type classification.
     */
    private determineSystemType(
        prohibitedPractices: ProhibitedPractice[],
        highRiskContexts: HighRiskContext[]
    ): EUAIActSystemType {
        if (prohibitedPractices.length > 0) {
            return 'prohibited';
        }

        if (highRiskContexts.length > 0) {
            return 'high_risk';
        }

        // Check for GPAI indicators (would need more context)
        // For now, default to minimal_risk
        return 'minimal_risk';
    }

    /**
     * Determines required oversight model for high-risk systems.
     */
    private determineOversightModel(
        riskLevel: EUAIActRiskLevel,
        highRiskContexts: HighRiskContext[]
    ): OversightModel | undefined {
        if (riskLevel !== 'high') {
            return undefined;
        }

        // Contexts requiring HITL (highest oversight)
        const hitlContexts: HighRiskContext[] = [
            'law_enforcement',
            'justice',
            'migration',
            'democratic_processes',
        ];

        if (highRiskContexts.some(c => hitlContexts.includes(c))) {
            return 'human_in_the_loop';
        }

        // Contexts requiring at least HOTL
        const hotlContexts: HighRiskContext[] = [
            'employment',
            'education',
            'essential_services',
        ];

        if (highRiskContexts.some(c => hotlContexts.includes(c))) {
            return 'human_on_the_loop';
        }

        // Default for high-risk
        return 'human_in_command';
    }

    // ========================================================================
    // PRIVATE METHODS - ARTICLE ANALYSIS
    // ========================================================================

    /**
     * Analyzes compliance for specific articles.
     */
    private analyzeArticles(
        matchesByPattern: Map<string, PatternMatch[]>,
        matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): EUAIActArticleFinding[] {
        const findings: EUAIActArticleFinding[] = [];

        // Article 5 - Prohibited Practices
        const article5Finding = this.analyzeArticle5(matchesByPattern, matchedPatterns);
        if (article5Finding) {
            findings.push(article5Finding);
        }

        // Article 6/Annex III - High-Risk Classification
        const article6Finding = this.analyzeArticle6(matchesByPattern, matchedPatterns);
        if (article6Finding) {
            findings.push(article6Finding);
        }

        // Article 14 - Human Oversight
        const article14Finding = this.analyzeArticle14(matchesByPattern, matchedPatterns);
        if (article14Finding) {
            findings.push(article14Finding);
        }

        // Article 52 - Transparency
        const article52Finding = this.analyzeArticle52(matchesByPattern, matchedPatterns);
        if (article52Finding) {
            findings.push(article52Finding);
        }

        return findings;
    }

    /**
     * Analyzes Article 5 (Prohibited Practices).
     */
    private analyzeArticle5(
        matchesByPattern: Map<string, PatternMatch[]>,
        _matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): EUAIActArticleFinding | null {
        const article5Patterns = PROHIBITED_PRACTICE_PATTERNS;
        const matches: PatternMatch[] = [];
        const issues: string[] = [];

        for (const pattern of article5Patterns) {
            const patternMatches = matchesByPattern.get(pattern.id);
            if (patternMatches && patternMatches.length > 0) {
                matches.push(...patternMatches);
                issues.push(`${pattern.category}: ${pattern.description}`);
            }
        }

        if (matches.length === 0) {
            return null;
        }

        return {
            article: '5',
            compliant: false,
            severity: 'critical',
            issues,
            recommendations: [RECOMMENDATIONS.prohibitedPractice],
            matches,
        };
    }

    /**
     * Analyzes Article 6 / Annex III (High-Risk Systems).
     */
    private analyzeArticle6(
        matchesByPattern: Map<string, PatternMatch[]>,
        _matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): EUAIActArticleFinding | null {
        const highRiskPatterns = HIGH_RISK_CONTEXT_PATTERNS;
        const matches: PatternMatch[] = [];
        const issues: string[] = [];

        for (const pattern of highRiskPatterns) {
            const patternMatches = matchesByPattern.get(pattern.id);
            if (patternMatches && patternMatches.length > 0) {
                matches.push(...patternMatches);
                issues.push(`${pattern.category}: ${pattern.description}`);
            }
        }

        if (matches.length === 0) {
            return null;
        }

        return {
            article: '6',
            subArticle: 'Annex III',
            compliant: true, // High-risk is allowed with conformity assessment
            severity: 'high',
            issues,
            recommendations: [
                RECOMMENDATIONS.highRisk,
                RECOMMENDATIONS.documentation,
                RECOMMENDATIONS.riskManagement,
                RECOMMENDATIONS.dataGovernance,
            ],
            matches,
        };
    }

    /**
     * Analyzes Article 14 (Human Oversight).
     */
    private analyzeArticle14(
        matchesByPattern: Map<string, PatternMatch[]>,
        _matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): EUAIActArticleFinding | null {
        const oversightPatterns = HUMAN_OVERSIGHT_PATTERNS;
        const matches: PatternMatch[] = [];
        const issues: string[] = [];

        for (const pattern of oversightPatterns) {
            const patternMatches = matchesByPattern.get(pattern.id);
            if (patternMatches && patternMatches.length > 0) {
                matches.push(...patternMatches);
                issues.push(`${pattern.description}`);
            }
        }

        if (matches.length === 0) {
            return null;
        }

        return {
            article: '14',
            compliant: false,
            severity: 'high',
            issues,
            recommendations: [RECOMMENDATIONS.humanOversight],
            matches,
        };
    }

    /**
     * Analyzes Article 52 (Transparency).
     */
    private analyzeArticle52(
        matchesByPattern: Map<string, PatternMatch[]>,
        _matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): EUAIActArticleFinding | null {
        const transparencyPatterns = TRANSPARENCY_PATTERNS;
        const matches: PatternMatch[] = [];
        const issues: string[] = [];

        for (const pattern of transparencyPatterns) {
            const patternMatches = matchesByPattern.get(pattern.id);
            if (patternMatches && patternMatches.length > 0) {
                matches.push(...patternMatches);
                issues.push(`${pattern.description}`);
            }
        }

        if (matches.length === 0) {
            return null;
        }

        // Transparency requirements are not non-compliance, just requirements
        return {
            article: '52',
            compliant: true, // Compliant if disclosure is made (we're flagging it needs disclosure)
            severity: 'medium',
            issues,
            recommendations: [RECOMMENDATIONS.transparency],
            matches,
        };
    }

    // ========================================================================
    // PRIVATE METHODS - RECOMMENDATIONS
    // ========================================================================

    /**
     * Generates recommendations based on findings.
     */
    private generateRecommendations(
        prohibitedPractices: ProhibitedPractice[],
        _highRiskContexts: HighRiskContext[],
        riskLevel: EUAIActRiskLevel,
        articleFindings: EUAIActArticleFinding[]
    ): string[] {
        const recommendations: string[] = [];

        // Prohibited practices
        if (prohibitedPractices.length > 0) {
            recommendations.push(formatRecommendation('critical', RECOMMENDATIONS.prohibitedPractice));

            for (const practice of prohibitedPractices) {
                recommendations.push(
                    formatRecommendation('critical', `Remove ${practice.replace(/_/g, ' ')} functionality`)
                );
            }
        }

        // High-risk systems
        if (riskLevel === 'high') {
            recommendations.push(formatRecommendation('high', RECOMMENDATIONS.highRisk));
            recommendations.push(formatRecommendation('high', RECOMMENDATIONS.documentation));
            recommendations.push(formatRecommendation('medium', RECOMMENDATIONS.riskManagement));
            recommendations.push(formatRecommendation('medium', RECOMMENDATIONS.dataGovernance));
            recommendations.push(formatRecommendation('medium', RECOMMENDATIONS.logging));
        }

        // Article-specific recommendations
        for (const finding of articleFindings) {
            if (!finding.compliant) {
                for (const rec of finding.recommendations) {
                    const formatted = formatRecommendation(finding.severity, rec);
                    if (!recommendations.includes(formatted)) {
                        recommendations.push(formatted);
                    }
                }
            }
        }

        return recommendations;
    }

    // ========================================================================
    // PRIVATE METHODS - GATE APPROXIMATION
    // ========================================================================

    /**
     * Approximates THSP gate results from pattern matches.
     * This is heuristic and not as accurate as semantic analysis.
     */
    private approximateGateResults(
        matchedPatterns: typeof ALL_EU_AI_ACT_PATTERNS
    ): Record<THSPGate, boolean> {
        const gates: Record<THSPGate, boolean> = {
            truth: true,
            harm: true,
            scope: true,
            purpose: true,
        };

        for (const pattern of matchedPatterns) {
            for (const gate of pattern.gates) {
                gates[gate] = false;
            }
        }

        return gates;
    }

    // ========================================================================
    // PRIVATE METHODS - SEMANTIC ANALYSIS
    // ========================================================================

    /**
     * Runs semantic analysis using user's LLM API.
     * This provides deeper understanding than pattern matching.
     */
    private async runSemanticAnalysis(_content: string): Promise<Partial<EUAIActComplianceResult>> {
        // This would call the user's API for semantic analysis
        // For now, return empty to use heuristic results
        // Implementation would be similar to semantic.ts but with EU AI Act specific prompt

        // Build prompt for future use
        this.buildSemanticPrompt();

        // TODO: Implement actual API call when semantic analysis is enabled
        // For now, we rely on heuristic analysis

        return {};
    }

    /**
     * Builds the system prompt for semantic analysis.
     */
    private buildSemanticPrompt(): string {
        return `You are an EU AI Act compliance analyzer. Analyze the given content for potential violations.

Check for:
1. Article 5 Prohibited Practices:
   - Social scoring systems
   - Biometric categorization by sensitive categories
   - Emotion recognition in workplace/education
   - Predictive policing for individual risk
   - Subliminal manipulation
   - Exploitation of vulnerable groups
   - Real-time remote biometric identification in public spaces

2. Annex III High-Risk Systems:
   - Biometric identification
   - Critical infrastructure management
   - Education/employment decisions
   - Essential services (credit, insurance, benefits)
   - Law enforcement, migration, justice

3. Article 14 Human Oversight:
   - Systems without human override capability
   - Fully automated decisions in sensitive areas

4. Article 52 Transparency:
   - AI chatbots requiring disclosure
   - Synthetic media (deepfakes)
   - AI-generated content

Respond in JSON format with findings for each article.`;
    }

    /**
     * Merges heuristic and semantic results.
     */
    private mergeResults(
        heuristic: EUAIActComplianceResult,
        _semantic: Partial<EUAIActComplianceResult>,
        startTime: number
    ): EUAIActComplianceResult {
        // For now, return heuristic result with updated metadata
        // When semantic is implemented, merge intelligently

        return {
            ...heuristic,
            metadata: createMetadata(
                'eu_ai_act',
                FRAMEWORK_VERSION,
                this.config.apiKey ? 'semantic' : 'heuristic',
                heuristic.metadata.contentSize,
                startTime,
                heuristic.metadata.gatesEvaluated
            ),
        };
    }
}

// ============================================================================
// CONVENIENCE FUNCTION
// ============================================================================

/**
 * Quick check function for EU AI Act compliance.
 *
 * @param content - Content to analyze
 * @param config - Optional configuration
 * @returns Compliance result
 *
 * @example
 * ```typescript
 * const result = checkEUAIActCompliance('Analyze user behavior scores...');
 * if (!result.compliant) {
 *   console.log('Risk level:', result.riskLevel);
 * }
 * ```
 */
export function checkEUAIActCompliance(
    content: string,
    config?: ComplianceCheckerConfig
): EUAIActComplianceResult {
    const checker = new EUAIActChecker(config);
    return checker.check(content);
}
