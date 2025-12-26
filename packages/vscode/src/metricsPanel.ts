import * as vscode from 'vscode';
import { MetricsSummary, AnalysisMetric } from './metrics';

export class MetricsPanel {
    public static currentPanel: MetricsPanel | undefined;
    private readonly panel: vscode.WebviewPanel;
    private disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel) {
        this.panel = panel;
        this.panel.onDidDispose(() => this.dispose(), null, this.disposables);
    }

    public static show(
        extensionUri: vscode.Uri,
        summary: MetricsSummary,
        recentMetrics: AnalysisMetric[]
    ): void {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        if (MetricsPanel.currentPanel) {
            MetricsPanel.currentPanel.panel.reveal(column);
            MetricsPanel.currentPanel.update(summary, recentMetrics);
            return;
        }

        const panel = vscode.window.createWebviewPanel(
            'sentinelMetrics',
            'Sentinel Metrics',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                localResourceRoots: [extensionUri]
            }
        );

        MetricsPanel.currentPanel = new MetricsPanel(panel);
        MetricsPanel.currentPanel.update(summary, recentMetrics);
    }

    public update(summary: MetricsSummary, recentMetrics: AnalysisMetric[]): void {
        this.panel.webview.html = this.getHtml(summary, recentMetrics);
    }

    private getHtml(summary: MetricsSummary, recentMetrics: AnalysisMetric[]): string {
        const safeRate = summary.totalAnalyses > 0
            ? Math.round((summary.safeCount / summary.totalAnalyses) * 100)
            : 0;

        const semanticRate = summary.totalAnalyses > 0
            ? Math.round((summary.semanticCount / summary.totalAnalyses) * 100)
            : 0;

        const topGateFailure = this.getTopGateFailure(summary);
        const providerStats = this.getProviderStats(summary);

        const recentRows = recentMetrics.map(m => {
            const date = new Date(m.timestamp);
            const timeStr = date.toLocaleTimeString();
            const dateStr = date.toLocaleDateString();
            const safeClass = m.safe ? 'safe' : 'unsafe';
            const safeText = m.safe ? 'SAFE' : 'UNSAFE';
            const methodIcon = m.method === 'semantic' ? '🧠' : '📋';

            return `
                <tr>
                    <td>${dateStr} ${timeStr}</td>
                    <td>${methodIcon} ${m.method}</td>
                    <td class="${safeClass}">${safeText}</td>
                    <td>${m.issueCount}</td>
                    <td>${m.provider || '-'}</td>
                </tr>
            `;
        }).reverse().join('');

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentinel Metrics</title>
    <style>
        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--vscode-foreground);
            background-color: var(--vscode-editor-background);
        }
        h1 {
            color: var(--vscode-foreground);
            border-bottom: 1px solid var(--vscode-panel-border);
            padding-bottom: 10px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }
        .stat-value {
            font-size: 32px;
            font-weight: bold;
            color: var(--vscode-textLink-foreground);
        }
        .stat-label {
            font-size: 12px;
            color: var(--vscode-descriptionForeground);
            margin-top: 4px;
        }
        .stat-sublabel {
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
            opacity: 0.7;
        }
        .section-title {
            font-size: 16px;
            font-weight: 600;
            margin: 20px 0 10px 0;
            color: var(--vscode-foreground);
        }
        .progress-bar {
            height: 8px;
            background: var(--vscode-progressBar-background);
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }
        .progress-safe { background: #4caf50; }
        .progress-unsafe { background: #f44336; }
        .progress-semantic { background: #2196f3; }
        .gate-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
            margin-bottom: 20px;
        }
        .gate-card {
            background: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 6px;
            padding: 12px;
            text-align: center;
        }
        .gate-name {
            font-weight: 600;
            margin-bottom: 4px;
        }
        .gate-failures {
            font-size: 24px;
            color: #f44336;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 10px;
        }
        th, td {
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid var(--vscode-panel-border);
        }
        th {
            background: var(--vscode-editor-inactiveSelectionBackground);
            font-weight: 600;
        }
        .safe { color: #4caf50; font-weight: 600; }
        .unsafe { color: #f44336; font-weight: 600; }
        .empty-state {
            text-align: center;
            padding: 40px;
            color: var(--vscode-descriptionForeground);
        }
        .provider-list {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }
        .provider-tag {
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <h1>📊 Sentinel Metrics Dashboard</h1>

    ${summary.totalAnalyses === 0 ? `
        <div class="empty-state">
            <h2>No analyses yet</h2>
            <p>Run "Sentinel: Analyze" on some text to start collecting metrics.</p>
        </div>
    ` : `
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">${summary.totalAnalyses}</div>
                <div class="stat-label">Total Analyses</div>
                <div class="stat-sublabel">
                    ${summary.firstAnalysis ? `Since ${new Date(summary.firstAnalysis).toLocaleDateString()}` : ''}
                </div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${safeRate}%</div>
                <div class="stat-label">Safe Rate</div>
                <div class="progress-bar">
                    <div class="progress-fill progress-safe" style="width: ${safeRate}%"></div>
                </div>
                <div class="stat-sublabel">${summary.safeCount} safe / ${summary.unsafeCount} unsafe</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${semanticRate}%</div>
                <div class="stat-label">Semantic Analysis</div>
                <div class="progress-bar">
                    <div class="progress-fill progress-semantic" style="width: ${semanticRate}%"></div>
                </div>
                <div class="stat-sublabel">${summary.semanticCount} semantic / ${summary.heuristicCount} heuristic</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${summary.issuesDetected}</div>
                <div class="stat-label">Issues Detected</div>
                <div class="stat-sublabel">Total issues found</div>
            </div>
        </div>

        <div class="section-title">🚧 Gate Failures</div>
        <div class="gate-grid">
            <div class="gate-card">
                <div class="gate-name">Truth</div>
                <div class="gate-failures">${summary.gateFailures.truth}</div>
            </div>
            <div class="gate-card">
                <div class="gate-name">Harm</div>
                <div class="gate-failures">${summary.gateFailures.harm}</div>
            </div>
            <div class="gate-card">
                <div class="gate-name">Scope</div>
                <div class="gate-failures">${summary.gateFailures.scope}</div>
            </div>
            <div class="gate-card">
                <div class="gate-name">Purpose</div>
                <div class="gate-failures">${summary.gateFailures.purpose}</div>
            </div>
        </div>

        ${topGateFailure ? `
            <p style="color: var(--vscode-descriptionForeground);">
                Most common failure: <strong>${topGateFailure.gate}</strong> gate
                (${topGateFailure.count} failures, ${topGateFailure.percentage}%)
            </p>
        ` : ''}

        ${Object.keys(summary.providerUsage).length > 0 ? `
            <div class="section-title">🔌 Provider Usage</div>
            <div class="provider-list">
                ${providerStats}
            </div>
        ` : ''}

        <div class="section-title">📋 Recent Analyses</div>
        <table>
            <thead>
                <tr>
                    <th>Time</th>
                    <th>Method</th>
                    <th>Result</th>
                    <th>Issues</th>
                    <th>Provider</th>
                </tr>
            </thead>
            <tbody>
                ${recentRows || '<tr><td colspan="5" style="text-align:center">No recent analyses</td></tr>'}
            </tbody>
        </table>
    `}
</body>
</html>`;
    }

    private getTopGateFailure(summary: MetricsSummary): { gate: string; count: number; percentage: number } | null {
        if (summary.totalAnalyses === 0) {return null;}

        const gates = [
            { gate: 'Truth', count: summary.gateFailures.truth },
            { gate: 'Harm', count: summary.gateFailures.harm },
            { gate: 'Scope', count: summary.gateFailures.scope },
            { gate: 'Purpose', count: summary.gateFailures.purpose }
        ];

        const top = gates.reduce((a, b) => a.count > b.count ? a : b);
        if (top.count === 0) {return null;}

        return {
            gate: top.gate,
            count: top.count,
            percentage: Math.round((top.count / summary.totalAnalyses) * 100)
        };
    }

    private getProviderStats(summary: MetricsSummary): string {
        return Object.entries(summary.providerUsage)
            .map(([provider, count]) => {
                const percentage = Math.round((count / summary.totalAnalyses) * 100);
                return `<span class="provider-tag">${provider}: ${count} (${percentage}%)</span>`;
            })
            .join('');
    }

    private dispose(): void {
        MetricsPanel.currentPanel = undefined;
        this.panel.dispose();
        while (this.disposables.length) {
            const d = this.disposables.pop();
            if (d) {d.dispose();}
        }
    }
}
