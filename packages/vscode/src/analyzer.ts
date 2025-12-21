import * as vscode from 'vscode';
import { SemanticValidator, SemanticValidationResult } from './semantic';
import { checkPatterns } from './patterns';

// Configuration constants
const API_TIMEOUT_MS = 30000;
const CACHE_TTL_MS = 60000; // 1 minute cache
const CACHE_MAX_SIZE = 50;

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

// Type for API response validation
interface SentinelApiResponse {
    safe: boolean;
    gates: {
        truth: string;
        harm: string;
        scope: string;
        purpose: string;
    };
    issues?: string[];
    confidence?: number;
    reasoning?: string;
}

// Cache entry type
interface CacheEntry {
    result: AnalysisResult;
    timestamp: number;
}

export class SentinelAnalyzer {
    private semanticValidator: SemanticValidator | null = null;
    private currentProvider: string | null = null;
    private currentModel: string | null = null;
    private externalKeys: AnalyzerConfig = {};
    private lastConfigHash: string = '';
    private resultCache: Map<string, CacheEntry> = new Map();

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
     * Generate a hash of current configuration to detect changes
     */
    private getConfigHash(): string {
        const config = vscode.workspace.getConfiguration('sentinel');
        const provider = config.get<string>('llmProvider') || 'openai';
        const openaiKey = this.externalKeys.openaiKey || config.get<string>('openaiApiKey') || '';
        const anthropicKey = this.externalKeys.anthropicKey || config.get<string>('anthropicApiKey') || '';
        const openaiModel = config.get<string>('openaiModel') || '';
        const anthropicModel = config.get<string>('anthropicModel') || '';

        // Simple hash - just concatenate relevant values
        return `${provider}:${openaiKey.substring(0, 8)}:${anthropicKey.substring(0, 8)}:${openaiModel}:${anthropicModel}`;
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

        try {
            if (provider === 'openai' && openaiKey) {
                const model = config.get<string>('openaiModel') || 'gpt-4o-mini';
                this.semanticValidator = new SemanticValidator({
                    apiKey: openaiKey,
                    provider: 'openai',
                    model: model,
                    timeoutMs: API_TIMEOUT_MS
                });
                this.currentProvider = 'openai';
                this.currentModel = model;
            } else if (provider === 'anthropic' && anthropicKey) {
                const model = config.get<string>('anthropicModel') || 'claude-3-haiku-20240307';
                this.semanticValidator = new SemanticValidator({
                    apiKey: anthropicKey,
                    provider: 'anthropic',
                    model: model,
                    timeoutMs: API_TIMEOUT_MS
                });
                this.currentProvider = 'anthropic';
                this.currentModel = model;
            }
        } catch (error) {
            console.warn('Failed to initialize semantic validator:', error);
            this.semanticValidator = null;
        }

        this.lastConfigHash = this.getConfigHash();
    }

    /**
     * Re-initialize validator when settings change
     */
    public refreshValidator(): void {
        this.initializeValidator();
        // Clear cache when config changes
        this.resultCache.clear();
    }

    /**
     * Check if validator needs re-initialization
     */
    private needsReinitialization(): boolean {
        return this.getConfigHash() !== this.lastConfigHash;
    }

    /**
     * Generate cache key for content
     */
    private getCacheKey(content: string): string {
        // Simple hash using content length and first/last chars
        const len = content.length;
        const prefix = content.substring(0, 100);
        const suffix = content.substring(Math.max(0, len - 100));
        return `${len}:${prefix}:${suffix}`;
    }

    /**
     * Get cached result if available and not expired
     */
    private getCachedResult(content: string): AnalysisResult | null {
        const key = this.getCacheKey(content);
        const entry = this.resultCache.get(key);

        if (!entry) {
            return null;
        }

        // Check if expired
        if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
            this.resultCache.delete(key);
            return null;
        }

        return entry.result;
    }

    /**
     * Store result in cache
     */
    private cacheResult(content: string, result: AnalysisResult): void {
        // Enforce max cache size
        if (this.resultCache.size >= CACHE_MAX_SIZE) {
            // Remove oldest entry
            const oldestKey = this.resultCache.keys().next().value;
            if (oldestKey) {
                this.resultCache.delete(oldestKey);
            }
        }

        const key = this.getCacheKey(content);
        this.resultCache.set(key, {
            result,
            timestamp: Date.now()
        });
    }

    /**
     * Analyze content for safety using THSP protocol
     * Uses semantic analysis if configured, falls back to heuristics
     */
    public async analyze(content: string): Promise<AnalysisResult> {
        // Validate input
        if (content === null || content === undefined) {
            return this.analyzeLocally('');
        }

        // Check cache first
        const cachedResult = this.getCachedResult(content);
        if (cachedResult) {
            return cachedResult;
        }

        // Re-check config only if it changed
        if (this.needsReinitialization()) {
            this.initializeValidator();
        }

        let result: AnalysisResult;

        // Try semantic analysis first if available
        if (this.semanticValidator) {
            try {
                const semanticResult = await this.semanticValidator.validate(content);
                result = this.convertSemanticResult(semanticResult);
                this.cacheResult(content, result);
                return result;
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
                const apiResult = await this.analyzeViaApi(content, apiEndpoint);
                if (apiResult) {
                    this.cacheResult(content, apiResult);
                    return apiResult;
                }
            } catch (error) {
                console.warn('Sentinel API unavailable, using heuristic analysis');
            }
        }

        // Fall back to local heuristic analysis
        result = this.analyzeLocally(content);
        this.cacheResult(content, result);
        return result;
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
            if (msg.includes('timeout') || msg.includes('network') || msg.includes('timed out')) {
                return 'Network error - check your connection';
            }
            if (msg.includes('abort')) {
                return 'Request timed out';
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
     * Validate API response structure
     */
    private isValidApiResponse(data: unknown): data is SentinelApiResponse {
        if (typeof data !== 'object' || data === null) {
            return false;
        }

        const obj = data as Record<string, unknown>;

        if (typeof obj.safe !== 'boolean') {
            return false;
        }

        if (typeof obj.gates !== 'object' || obj.gates === null) {
            return false;
        }

        const gates = obj.gates as Record<string, unknown>;
        const requiredGates = ['truth', 'harm', 'scope', 'purpose'];

        for (const gate of requiredGates) {
            if (typeof gates[gate] !== 'string') {
                return false;
            }
        }

        return true;
    }

    /**
     * Analyze via Sentinel API
     */
    private async analyzeViaApi(content: string, endpoint: string): Promise<AnalysisResult | null> {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), API_TIMEOUT_MS);

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'application/json'
                },
                body: JSON.stringify({ content }),
                signal: controller.signal
            });

            if (!response.ok) {
                console.warn(`Sentinel API returned ${response.status}`);
                return null;
            }

            const data = await response.json() as unknown;

            // Validate response structure
            if (!this.isValidApiResponse(data)) {
                console.warn('Sentinel API returned invalid response structure');
                return null;
            }

            return {
                safe: data.safe,
                gates: data.gates,
                issues: data.issues || [],
                confidence: typeof data.confidence === 'number' ? data.confidence : 0.9,
                method: 'semantic',
                reasoning: data.reasoning
            };
        } catch (error) {
            if (error instanceof Error && error.name === 'AbortError') {
                console.warn('Sentinel API request timed out');
            }
            return null;
        } finally {
            clearTimeout(timeoutId);
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

    /**
     * Clear the result cache
     */
    public clearCache(): void {
        this.resultCache.clear();
    }
}
