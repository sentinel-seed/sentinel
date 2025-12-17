import * as vscode from 'vscode';
import { SemanticValidator, SemanticValidationResult } from './semantic';
import { checkPatterns } from './patterns';

export interface AnalysisResult {
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

export interface AnalyzerStatus {
    semanticAvailable: boolean;
    provider: string | null;
    model: string | null;
}

/**
 * Analyzer that checks content using Sentinel's THSP protocol
 *
 * Supports two modes:
 * 1. Semantic Analysis (recommended): Uses LLM for real understanding
 * 2. Heuristic Analysis (fallback): Pattern matching for basic detection
 */
export interface AnalyzerConfig {
    openaiKey?: string;
    anthropicKey?: string;
}

export class SentinelAnalyzer {
    private semanticValidator: SemanticValidator | null = null;
    private currentProvider: string | null = null;
    private currentModel: string | null = null;
    private externalKeys: AnalyzerConfig = {};

    constructor() {
        this.initializeValidator();
    }

    /**
     * Set API keys from external source (e.g., SecretStorage)
     */
    public setExternalKeys(keys: AnalyzerConfig): void {
        this.externalKeys = keys;
        this.initializeValidator();
    }

    /**
     * Initialize semantic validator if API key is configured
     * Checks external keys first (SecretStorage), then falls back to settings
     */
    private initializeValidator(): void {
        const config = vscode.workspace.getConfiguration('sentinel');
        const provider = config.get<string>('llmProvider') || 'openai';

        // Check external keys first (from SecretStorage), then settings
        const openaiKey = this.externalKeys.openaiKey || config.get<string>('openaiApiKey');
        const anthropicKey = this.externalKeys.anthropicKey || config.get<string>('anthropicApiKey');

        // Reset state
        this.semanticValidator = null;
        this.currentProvider = null;
        this.currentModel = null;

        if (provider === 'openai' && openaiKey) {
            const model = config.get<string>('openaiModel') || 'gpt-4o-mini';
            this.semanticValidator = new SemanticValidator({
                apiKey: openaiKey,
                provider: 'openai',
                model: model
            });
            this.currentProvider = 'openai';
            this.currentModel = model;
        } else if (provider === 'anthropic' && anthropicKey) {
            const model = config.get<string>('anthropicModel') || 'claude-3-haiku-20240307';
            this.semanticValidator = new SemanticValidator({
                apiKey: anthropicKey,
                provider: 'anthropic',
                model: model
            });
            this.currentProvider = 'anthropic';
            this.currentModel = model;
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
                const errorMessage = this.formatError(error);
                console.warn('Semantic analysis failed:', errorMessage);
                vscode.window.showWarningMessage(
                    `Semantic analysis failed: ${errorMessage}. Using heuristic analysis.`
                );
            }
        }

        // Try Sentinel API as second option (if configured)
        const config = vscode.workspace.getConfiguration('sentinel');
        const apiEndpoint = config.get<string>('apiEndpoint');
        const useApi = config.get<boolean>('useSentinelApi');

        if (useApi && apiEndpoint) {
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
     * Format error message for display
     */
    private formatError(error: unknown): string {
        if (error instanceof Error) {
            const msg = error.message.toLowerCase();
            if (msg.includes('401') || msg.includes('unauthorized')) {
                return 'Invalid API key';
            }
            if (msg.includes('429') || msg.includes('rate limit')) {
                return 'Rate limit exceeded - try again later';
            }
            if (msg.includes('quota') || msg.includes('billing')) {
                return 'API quota exceeded - check your billing';
            }
            if (msg.includes('timeout') || msg.includes('network')) {
                return 'Network error - check your connection';
            }
            return error.message;
        }
        return String(error);
    }

    /**
     * Check if semantic analysis is available
     */
    public isSemanticAvailable(): boolean {
        return this.semanticValidator !== null;
    }

    /**
     * Get current analyzer status for status bar
     */
    public getStatus(): AnalyzerStatus {
        return {
            semanticAvailable: this.semanticValidator !== null,
            provider: this.currentProvider,
            model: this.currentModel
        };
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
        const result = checkPatterns(content);

        const safe = result.gates.truth && result.gates.harm && result.gates.scope && result.gates.purpose;

        return {
            safe,
            gates: {
                truth: result.gates.truth ? 'pass' : 'fail',
                harm: result.gates.harm ? 'pass' : 'fail',
                scope: result.gates.scope ? 'pass' : 'fail',
                purpose: result.gates.purpose ? 'pass' : 'fail'
            },
            issues: result.issues,
            confidence: 0.5,
            method: 'heuristic',
            reasoning: 'Heuristic pattern matching (~50% accuracy). Configure LLM API key for semantic analysis.'
        };
    }
}
