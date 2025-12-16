import * as vscode from 'vscode';
import { SemanticValidator, SemanticValidationResult } from './semantic';

interface AnalysisResult {
    safe: boolean;
    gates: {
        truth: string;
        harm: string;
        scope: string;
        purpose: string;
    };
    issues: string[];
    confidence: number;
    method: 'semantic' | 'heuristic';
    reasoning?: string;
}

/**
 * Analyzer that checks content using Sentinel's THSP protocol
 *
 * Supports two modes:
 * 1. Semantic Analysis (recommended): Uses LLM for real understanding
 * 2. Heuristic Analysis (fallback): Pattern matching for basic detection
 */
export class SentinelAnalyzer {
    private semanticValidator: SemanticValidator | null = null;

    constructor() {
        this.initializeValidator();
    }

    /**
     * Initialize semantic validator if API key is configured
     */
    private initializeValidator(): void {
        const config = vscode.workspace.getConfiguration('sentinel');
        const openaiKey = config.get<string>('openaiApiKey');
        const anthropicKey = config.get<string>('anthropicApiKey');
        const provider = config.get<string>('llmProvider') || 'openai';

        if (provider === 'openai' && openaiKey) {
            this.semanticValidator = new SemanticValidator({
                apiKey: openaiKey,
                provider: 'openai',
                model: config.get<string>('openaiModel') || 'gpt-4o-mini'
            });
        } else if (provider === 'anthropic' && anthropicKey) {
            this.semanticValidator = new SemanticValidator({
                apiKey: anthropicKey,
                provider: 'anthropic',
                model: config.get<string>('anthropicModel') || 'claude-3-haiku-20240307'
            });
        }
    }

    /**
     * Re-initialize validator when settings change
     */
    public refreshValidator(): void {
        this.initializeValidator();
    }

    /**
     * Analyze content for safety using THSP protocol
     * Uses semantic analysis if configured, falls back to heuristics
     */
    public async analyze(content: string): Promise<AnalysisResult> {
        // Re-check config in case it changed
        this.initializeValidator();

        // Try semantic analysis first if available
        if (this.semanticValidator) {
            try {
                const result = await this.semanticValidator.validate(content);
                return this.convertSemanticResult(result);
            } catch (error) {
                console.warn('Semantic analysis failed, falling back to heuristics:', error);
                vscode.window.showWarningMessage(
                    'Semantic analysis failed. Using heuristic analysis (less accurate).'
                );
            }
        }

        // Try Sentinel API as second option
        const config = vscode.workspace.getConfiguration('sentinel');
        const apiEndpoint = config.get<string>('apiEndpoint');

        if (apiEndpoint && apiEndpoint !== 'https://api.sentinelseed.dev/api/v1/guard') {
            try {
                const result = await this.analyzeViaApi(content, apiEndpoint);
                if (result) {
                    return result;
                }
            } catch (error) {
                console.warn('Sentinel API unavailable, using heuristic analysis');
            }
        }

        // Fall back to local heuristic analysis
        return this.analyzeLocally(content);
    }

    /**
     * Check if semantic analysis is available
     */
    public isSemanticAvailable(): boolean {
        return this.semanticValidator !== null;
    }

    /**
     * Convert semantic validation result to analysis result format
     */
    private convertSemanticResult(result: SemanticValidationResult): AnalysisResult {
        return {
            safe: result.safe,
            gates: result.gates,
            issues: result.issues,
            confidence: result.confidence,
            method: 'semantic',
            reasoning: result.reasoning
        };
    }

    /**
     * Analyze via Sentinel API
     */
    private async analyzeViaApi(content: string, endpoint: string): Promise<AnalysisResult | null> {
        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ content })
            });

            if (!response.ok) {
                return null;
            }

            const data = await response.json() as any;
            return {
                ...data,
                method: 'semantic'
            };
        } catch {
            return null;
        }
    }

    /**
     * Local heuristic-based analysis following THSP protocol
     *
     * WARNING: This is pattern matching only, not semantic understanding.
     * It will have false positives and false negatives.
     * For accurate analysis, configure an LLM API key.
     */
    private analyzeLocally(content: string): AnalysisResult {
        const contentLower = content.toLowerCase();
        const issues: string[] = [];

        // Gate 1: Truth - Check for deception patterns
        const deceptionPatterns = [
            'fake document', 'forge', 'counterfeit', 'impersonate someone',
            'spread misinformation', 'create fake', 'deceive people'
        ];
        const truthFail = deceptionPatterns.some(p => contentLower.includes(p));
        if (truthFail) {
            issues.push('Potential deception detected (Truth gate) [heuristic]');
        }

        // Gate 2: Harm - Check for harmful patterns
        const harmPatterns = [
            'make a bomb', 'create explosive', 'build weapon',
            'hack into', 'create malware', 'write ransomware',
            'poison someone', 'kill people', 'attack system'
        ];
        const harmFail = harmPatterns.some(p => contentLower.includes(p));
        if (harmFail) {
            issues.push('Potential harm detected (Harm gate) [heuristic]');
        }

        // Gate 3: Scope - Check for bypass attempts
        const scopePatterns = [
            'ignore previous instructions', 'ignore all instructions',
            'you are now dan', 'jailbreak', 'developer mode enabled',
            'disable safety', 'bypass filter', 'override restrictions'
        ];
        const scopeFail = scopePatterns.some(p => contentLower.includes(p));
        if (scopeFail) {
            issues.push('Potential scope violation detected (Scope gate) [heuristic]');
        }

        // Gate 4: Purpose - Check for purposeless actions
        const purposelessPatterns = [
            'destroy everything for no reason', 'randomly delete all',
            'break things for fun', 'cause chaos'
        ];
        const purposeFail = purposelessPatterns.some(p => contentLower.includes(p));
        if (purposeFail) {
            issues.push('Purposeless action detected (Purpose gate) [heuristic]');
        }

        const safe = !truthFail && !harmFail && !scopeFail && !purposeFail;

        // Lower confidence for heuristic analysis
        const confidence = 0.5;

        if (issues.length === 0 && !safe) {
            issues.push('Analysis inconclusive - consider using semantic analysis for accuracy');
        }

        return {
            safe,
            gates: {
                truth: truthFail ? 'fail' : 'pass',
                harm: harmFail ? 'fail' : 'pass',
                scope: scopeFail ? 'fail' : 'pass',
                purpose: purposeFail ? 'fail' : 'pass'
            },
            issues,
            confidence,
            method: 'heuristic',
            reasoning: 'Heuristic pattern matching (limited accuracy). Configure LLM API key for semantic analysis.'
        };
    }
}
