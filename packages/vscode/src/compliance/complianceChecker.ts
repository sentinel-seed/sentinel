/**
 * Unified Compliance Checker
 *
 * Orchestrates compliance checks across multiple frameworks:
 * - EU AI Act (2024)
 * - OWASP LLM Top 10 (2025)
 * - CSA AI Controls Matrix (2025)
 *
 * Privacy-first design:
 * - All checks run 100% locally by default (heuristic mode)
 * - Semantic analysis uses user's own API key (never sent to Sentinel servers)
 * - No telemetry, no data collection
 *
 * @example
 * ```typescript
 * const checker = new ComplianceChecker();
 *
 * // Check single framework
 * const euResult = checker.checkEUAIAct(content);
 *
 * // Check all frameworks
 * const allResults = checker.checkAll(content);
 *
 * // Check specific frameworks
 * const results = checker.check(content, ['eu_ai_act', 'owasp_llm']);
 * ```
 */

import {
    UnifiedComplianceResult,
    EUAIActComplianceResult,
    OWASPComplianceResult,
    AICMComplianceResult,
    ComplianceFramework,
    ComplianceCheckerConfig,
} from './types';

import { EUAIActChecker } from './eu-ai-act';
import { OWASPLLMChecker } from './owasp-llm';
import { CSAAICMChecker } from './csa-aicm';
import { deduplicateRecommendations, validateContent, MAX_CONTENT_SIZE } from './utils';
import { SemanticComplianceAnalyzer, createSemanticAnalyzer } from './semanticAnalyzer';

// ============================================================================
// COMPLIANCE CHECKER CLASS
// ============================================================================

/**
 * Unified compliance checker that orchestrates multiple framework checks.
 *
 * Privacy guarantees:
 * - Heuristic mode: 100% local, no network calls
 * - Semantic mode: Uses YOUR API key, direct to provider (OpenAI/Anthropic)
 * - No data sent to Sentinel servers
 * - No telemetry or tracking
 */
export class ComplianceChecker {
    private config: ComplianceCheckerConfig;
    private euChecker: EUAIActChecker;
    private owaspChecker: OWASPLLMChecker;
    private csaChecker: CSAAICMChecker;
    private semanticAnalyzer: SemanticComplianceAnalyzer | null = null;

    constructor(config: ComplianceCheckerConfig = {}) {
        this.config = {
            maxContentSize: MAX_CONTENT_SIZE,
            failClosed: false,
            ...config,
        };

        this.euChecker = new EUAIActChecker(this.config);
        this.owaspChecker = new OWASPLLMChecker(this.config);
        this.csaChecker = new CSAAICMChecker(this.config);

        // Initialize semantic analyzer if API key provided
        if (this.config.apiKey && this.config.provider) {
            this.semanticAnalyzer = createSemanticAnalyzer(
                this.config.apiKey,
                this.config.provider,
                this.config.model
            );
        }
    }

    // ========================================================================
    // PUBLIC METHODS - API KEY CONFIGURATION
    // ========================================================================

    /**
     * Configures API key for semantic analysis.
     *
     * Privacy guarantee:
     * - API calls go DIRECTLY to OpenAI/Anthropic
     * - NO data passes through Sentinel servers
     *
     * @param apiKey - Your OpenAI or Anthropic API key
     * @param provider - API provider ('openai' or 'anthropic')
     * @param model - Optional model override
     */
    public setApiKey(
        apiKey: string,
        provider: 'openai' | 'anthropic',
        model?: string
    ): void {
        this.config.apiKey = apiKey;
        this.config.provider = provider;
        this.config.model = model;

        this.semanticAnalyzer = createSemanticAnalyzer(apiKey, provider, model);
    }

    /**
     * Clears API key configuration.
     * Checker will use heuristic analysis only.
     */
    public clearApiKey(): void {
        this.config.apiKey = undefined;
        this.config.provider = undefined;
        this.config.model = undefined;
        this.semanticAnalyzer = null;
    }

    // ========================================================================
    // PUBLIC METHODS - INDIVIDUAL FRAMEWORKS
    // ========================================================================

    /**
     * Checks content against EU AI Act requirements.
     *
     * Detects:
     * - Article 5 prohibited practices (social scoring, biometrics, etc.)
     * - Annex III high-risk system contexts
     * - Article 14 human oversight requirements
     * - Article 52 transparency obligations
     */
    public checkEUAIAct(content: string): EUAIActComplianceResult {
        return this.euChecker.check(content);
    }

    /**
     * Checks content against OWASP LLM Top 10 vulnerabilities.
     *
     * For user input (pre-inference), use checkOWASPInput().
     * For LLM output (post-inference), use checkOWASPOutput().
     * This method checks all vulnerabilities.
     */
    public checkOWASP(content: string): OWASPComplianceResult {
        return this.owaspChecker.checkAll(content);
    }

    /**
     * Checks user input for OWASP LLM vulnerabilities (pre-inference).
     *
     * Detects:
     * - LLM01: Prompt Injection
     * - LLM06: Excessive Agency
     * - LLM07: System Prompt extraction attempts
     */
    public checkOWASPInput(content: string): OWASPComplianceResult {
        return this.owaspChecker.checkInput(content);
    }

    /**
     * Checks LLM output for OWASP LLM vulnerabilities (post-inference).
     *
     * Detects:
     * - LLM02: Sensitive Information Disclosure
     * - LLM05: Improper Output Handling
     * - LLM07: System Prompt Leakage
     * - LLM09: Misinformation
     */
    public checkOWASPOutput(content: string): OWASPComplianceResult {
        return this.owaspChecker.checkOutput(content);
    }

    /**
     * Checks complete LLM pipeline (input + output).
     */
    public checkOWASPPipeline(userInput: string, llmOutput: string): OWASPComplianceResult {
        return this.owaspChecker.checkPipeline(userInput, llmOutput);
    }

    /**
     * Checks content against CSA AI Controls Matrix requirements.
     *
     * Evaluates:
     * - Model Security domain
     * - Governance, Risk & Compliance domain
     * - Data Security & Privacy domain
     * - Application & Interface Security domain
     * - And more...
     */
    public checkCSA(content: string): AICMComplianceResult {
        return this.csaChecker.check(content);
    }

    // ========================================================================
    // PUBLIC METHODS - UNIFIED CHECKS
    // ========================================================================

    /**
     * Checks content against all supported frameworks.
     *
     * Returns unified result with summary and individual framework results.
     */
    public checkAll(content: string): UnifiedComplianceResult {
        return this.check(content, ['eu_ai_act', 'owasp_llm', 'csa_aicm']);
    }

    /**
     * Checks content against specified frameworks.
     *
     * @param content - Content to analyze
     * @param frameworks - Frameworks to check
     * @returns Unified result
     */
    public check(
        content: string,
        frameworks: ComplianceFramework[]
    ): UnifiedComplianceResult {
        // Validate input once
        validateContent(content, this.config.maxContentSize);

        const timestamp = new Date().toISOString();
        const allRecommendations: string[] = [];

        let euResult: EUAIActComplianceResult | undefined;
        let owaspResult: OWASPComplianceResult | undefined;
        let csaResult: AICMComplianceResult | undefined;

        // Run requested checks
        if (frameworks.includes('eu_ai_act')) {
            euResult = this.checkEUAIAct(content);
            allRecommendations.push(...euResult.recommendations);
        }

        if (frameworks.includes('owasp_llm')) {
            owaspResult = this.checkOWASP(content);
            allRecommendations.push(...owaspResult.recommendations);
        }

        if (frameworks.includes('csa_aicm')) {
            csaResult = this.checkCSA(content);
            allRecommendations.push(...csaResult.recommendations);
        }

        // Build summary
        const summary: UnifiedComplianceResult['summary'] = {};

        if (euResult) {
            summary.euAiAct = {
                compliant: euResult.compliant,
                riskLevel: euResult.riskLevel,
            };
        }

        if (owaspResult) {
            summary.owaspLlm = {
                secure: owaspResult.secure,
                vulnerabilitiesDetected: owaspResult.vulnerabilitiesDetected,
            };
        }

        if (csaResult) {
            summary.csaAicm = {
                compliant: csaResult.compliant,
                complianceRate: csaResult.complianceRate,
            };
        }

        // Overall compliance
        const compliant =
            (euResult ? euResult.compliant : true) &&
            (owaspResult ? owaspResult.secure : true) &&
            (csaResult ? csaResult.compliant : true);

        return {
            compliant,
            summary,
            euAiAct: euResult,
            owaspLlm: owaspResult,
            csaAicm: csaResult,
            recommendations: deduplicateRecommendations(allRecommendations),
            timestamp,
            frameworksChecked: frameworks,
        };
    }

    // ========================================================================
    // PUBLIC METHODS - SEMANTIC ANALYSIS (ASYNC)
    // ========================================================================

    /**
     * Checks content with semantic analysis (requires API key).
     *
     * Falls back to heuristic if semantic analysis fails or is unavailable.
     *
     * @param content - Content to analyze
     * @returns EU AI Act compliance result with semantic accuracy
     */
    public async checkEUAIActSemantic(content: string): Promise<EUAIActComplianceResult> {
        if (this.semanticAnalyzer) {
            try {
                return await this.semanticAnalyzer.analyzeEUAIAct(content);
            } catch (error) {
                console.warn('Semantic analysis failed, falling back to heuristic:', error);
            }
        }
        return this.checkEUAIAct(content);
    }

    /**
     * Checks content with semantic analysis for OWASP LLM.
     */
    public async checkOWASPSemantic(content: string): Promise<OWASPComplianceResult> {
        if (this.semanticAnalyzer) {
            try {
                return await this.semanticAnalyzer.analyzeOWASP(content);
            } catch (error) {
                console.warn('Semantic analysis failed, falling back to heuristic:', error);
            }
        }
        return this.checkOWASP(content);
    }

    /**
     * Checks content with semantic analysis for CSA AICM.
     */
    public async checkCSASemantic(content: string): Promise<AICMComplianceResult> {
        if (this.semanticAnalyzer) {
            try {
                return await this.semanticAnalyzer.analyzeCSA(content);
            } catch (error) {
                console.warn('Semantic analysis failed, falling back to heuristic:', error);
            }
        }
        return this.checkCSA(content);
    }

    /**
     * Checks all frameworks with semantic analysis.
     *
     * Uses semantic analysis when available, falls back to heuristic per-framework.
     */
    public async checkAllSemantic(content: string): Promise<UnifiedComplianceResult> {
        return this.checkSemantic(content, ['eu_ai_act', 'owasp_llm', 'csa_aicm']);
    }

    /**
     * Checks specified frameworks with semantic analysis.
     */
    public async checkSemantic(
        content: string,
        frameworks: ComplianceFramework[]
    ): Promise<UnifiedComplianceResult> {
        validateContent(content, this.config.maxContentSize);

        const timestamp = new Date().toISOString();
        const allRecommendations: string[] = [];

        let euResult: EUAIActComplianceResult | undefined;
        let owaspResult: OWASPComplianceResult | undefined;
        let csaResult: AICMComplianceResult | undefined;

        // Run requested checks (with semantic when available)
        if (frameworks.includes('eu_ai_act')) {
            euResult = await this.checkEUAIActSemantic(content);
            allRecommendations.push(...euResult.recommendations);
        }

        if (frameworks.includes('owasp_llm')) {
            owaspResult = await this.checkOWASPSemantic(content);
            allRecommendations.push(...owaspResult.recommendations);
        }

        if (frameworks.includes('csa_aicm')) {
            csaResult = await this.checkCSASemantic(content);
            allRecommendations.push(...csaResult.recommendations);
        }

        // Build summary
        const summary: UnifiedComplianceResult['summary'] = {};

        if (euResult) {
            summary.euAiAct = {
                compliant: euResult.compliant,
                riskLevel: euResult.riskLevel,
            };
        }

        if (owaspResult) {
            summary.owaspLlm = {
                secure: owaspResult.secure,
                vulnerabilitiesDetected: owaspResult.vulnerabilitiesDetected,
            };
        }

        if (csaResult) {
            summary.csaAicm = {
                compliant: csaResult.compliant,
                complianceRate: csaResult.complianceRate,
            };
        }

        const compliant =
            (euResult ? euResult.compliant : true) &&
            (owaspResult ? owaspResult.secure : true) &&
            (csaResult ? csaResult.compliant : true);

        return {
            compliant,
            summary,
            euAiAct: euResult,
            owaspLlm: owaspResult,
            csaAicm: csaResult,
            recommendations: deduplicateRecommendations(allRecommendations),
            timestamp,
            frameworksChecked: frameworks,
        };
    }

    // ========================================================================
    // PUBLIC METHODS - QUICK CHECKS
    // ========================================================================

    /**
     * Quick check if content has any critical issues.
     * Useful for fast pre-validation before more detailed analysis.
     */
    public hasIssues(content: string): boolean {
        const result = this.checkAll(content);
        return !result.compliant;
    }

    /**
     * Quick check for prohibited practices (EU AI Act Article 5).
     */
    public hasProhibitedPractices(content: string): boolean {
        const result = this.checkEUAIAct(content);
        return result.prohibitedPractices.length > 0;
    }

    /**
     * Quick check for prompt injection attempts.
     */
    public hasPromptInjection(content: string): boolean {
        const result = this.checkOWASPInput(content);
        return result.findings.some(f => f.vulnerability === 'LLM01' && f.detected);
    }

    /**
     * Quick check for sensitive information disclosure.
     */
    public hasSensitiveInfo(content: string): boolean {
        const result = this.checkOWASPOutput(content);
        return result.findings.some(f => f.vulnerability === 'LLM02' && f.detected);
    }

    // ========================================================================
    // PUBLIC METHODS - CONFIGURATION
    // ========================================================================

    /**
     * Updates configuration.
     * Recreates internal checkers with new config.
     */
    public updateConfig(config: Partial<ComplianceCheckerConfig>): void {
        this.config = { ...this.config, ...config };
        this.euChecker = new EUAIActChecker(this.config);
        this.owaspChecker = new OWASPLLMChecker(this.config);
        this.csaChecker = new CSAAICMChecker(this.config);
    }

    /**
     * Gets current configuration.
     */
    public getConfig(): ComplianceCheckerConfig {
        return { ...this.config };
    }

    /**
     * Checks if semantic analysis is available.
     */
    public isSemanticAvailable(): boolean {
        return !!this.config.apiKey;
    }
}

// ============================================================================
// CONVENIENCE FUNCTIONS
// ============================================================================

/**
 * Creates a pre-configured compliance checker.
 */
export function createComplianceChecker(
    config?: ComplianceCheckerConfig
): ComplianceChecker {
    return new ComplianceChecker(config);
}

/**
 * Quick unified compliance check.
 */
export function checkCompliance(
    content: string,
    frameworks?: ComplianceFramework[],
    config?: ComplianceCheckerConfig
): UnifiedComplianceResult {
    const checker = new ComplianceChecker(config);
    return frameworks
        ? checker.check(content, frameworks)
        : checker.checkAll(content);
}

/**
 * Quick EU AI Act check.
 */
export function checkEUAIActCompliance(
    content: string,
    config?: ComplianceCheckerConfig
): EUAIActComplianceResult {
    const checker = new ComplianceChecker(config);
    return checker.checkEUAIAct(content);
}

/**
 * Quick OWASP LLM check.
 */
export function checkOWASPCompliance(
    content: string,
    config?: ComplianceCheckerConfig
): OWASPComplianceResult {
    const checker = new ComplianceChecker(config);
    return checker.checkOWASP(content);
}

/**
 * Quick CSA AICM check.
 */
export function checkCSACompliance(
    content: string,
    config?: ComplianceCheckerConfig
): AICMComplianceResult {
    const checker = new ComplianceChecker(config);
    return checker.checkCSA(content);
}
