import * as vscode from 'vscode';

export interface AnalysisMetric {
    timestamp: number;
    method: 'semantic' | 'heuristic';
    safe: boolean;
    gates: {
        truth: boolean;
        harm: boolean;
        scope: boolean;
        purpose: boolean;
    };
    issueCount: number;
    provider?: string;
}

export interface MetricsSummary {
    totalAnalyses: number;
    safeCount: number;
    unsafeCount: number;
    semanticCount: number;
    heuristicCount: number;
    gateFailures: {
        truth: number;
        harm: number;
        scope: number;
        purpose: number;
    };
    issuesDetected: number;
    lastAnalysis: number | null;
    firstAnalysis: number | null;
    providerUsage: Record<string, number>;
}

const METRICS_KEY = 'sentinel.metrics';
const MAX_METRICS_STORED = 1000;

export class MetricsTracker {
    private context: vscode.ExtensionContext;
    private metrics: AnalysisMetric[] = [];

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.loadMetrics();
    }

    private loadMetrics(): void {
        const stored = this.context.globalState.get<AnalysisMetric[]>(METRICS_KEY);
        this.metrics = stored || [];
    }

    private async saveMetrics(): Promise<void> {
        // Keep only the most recent metrics
        if (this.metrics.length > MAX_METRICS_STORED) {
            this.metrics = this.metrics.slice(-MAX_METRICS_STORED);
        }
        await this.context.globalState.update(METRICS_KEY, this.metrics);
    }

    public async recordAnalysis(
        method: 'semantic' | 'heuristic',
        safe: boolean,
        gates: { truth: string; harm: string; scope: string; purpose: string },
        issueCount: number,
        provider?: string
    ): Promise<void> {
        const metric: AnalysisMetric = {
            timestamp: Date.now(),
            method,
            safe,
            gates: {
                truth: gates.truth === 'pass',
                harm: gates.harm === 'pass',
                scope: gates.scope === 'pass',
                purpose: gates.purpose === 'pass'
            },
            issueCount,
            provider
        };

        this.metrics.push(metric);
        await this.saveMetrics();
    }

    public getSummary(): MetricsSummary {
        const summary: MetricsSummary = {
            totalAnalyses: this.metrics.length,
            safeCount: 0,
            unsafeCount: 0,
            semanticCount: 0,
            heuristicCount: 0,
            gateFailures: { truth: 0, harm: 0, scope: 0, purpose: 0 },
            issuesDetected: 0,
            lastAnalysis: null,
            firstAnalysis: null,
            providerUsage: {}
        };

        if (this.metrics.length === 0) {
            return summary;
        }

        summary.firstAnalysis = this.metrics[0].timestamp;
        summary.lastAnalysis = this.metrics[this.metrics.length - 1].timestamp;

        for (const metric of this.metrics) {
            if (metric.safe) {
                summary.safeCount++;
            } else {
                summary.unsafeCount++;
            }

            if (metric.method === 'semantic') {
                summary.semanticCount++;
            } else {
                summary.heuristicCount++;
            }

            if (!metric.gates.truth) {summary.gateFailures.truth++;}
            if (!metric.gates.harm) {summary.gateFailures.harm++;}
            if (!metric.gates.scope) {summary.gateFailures.scope++;}
            if (!metric.gates.purpose) {summary.gateFailures.purpose++;}

            summary.issuesDetected += metric.issueCount;

            if (metric.provider) {
                summary.providerUsage[metric.provider] =
                    (summary.providerUsage[metric.provider] || 0) + 1;
            }
        }

        return summary;
    }

    public getRecentMetrics(count: number = 10): AnalysisMetric[] {
        return this.metrics.slice(-count);
    }

    public async clearMetrics(): Promise<void> {
        this.metrics = [];
        await this.context.globalState.update(METRICS_KEY, []);
    }

    public getMetricsCount(): number {
        return this.metrics.length;
    }
}
