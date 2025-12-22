/**
 * Compliance Result Panel
 *
 * WebView panel for displaying compliance check results.
 * Provides a rich UI for exploring findings across frameworks.
 */

import * as vscode from 'vscode';
import {
    UnifiedComplianceResult,
    EUAIActComplianceResult,
    OWASPComplianceResult,
    AICMComplianceResult,
    ComplianceFramework,
    EU_AI_ACT_RISK_LEVEL_NAMES,
} from './types';

// ============================================================================
// RESULT PANEL CLASS
// ============================================================================

/**
 * Manages the compliance result WebView panel.
 */
export class ComplianceResultPanel {
    public static currentPanel: ComplianceResultPanel | undefined;
    private readonly _panel: vscode.WebviewPanel;
    private _disposables: vscode.Disposable[] = [];

    private constructor(panel: vscode.WebviewPanel) {
        this._panel = panel;

        // Handle panel disposal
        this._panel.onDidDispose(() => this.dispose(), null, this._disposables);
    }

    /**
     * Creates or shows the result panel.
     */
    public static createOrShow(_extensionUri: vscode.Uri): ComplianceResultPanel {
        const column = vscode.window.activeTextEditor
            ? vscode.window.activeTextEditor.viewColumn
            : undefined;

        // If panel exists, show it
        if (ComplianceResultPanel.currentPanel) {
            ComplianceResultPanel.currentPanel._panel.reveal(column);
            return ComplianceResultPanel.currentPanel;
        }

        // Create new panel
        const panel = vscode.window.createWebviewPanel(
            'sentinelCompliance',
            'Sentinel Compliance Check',
            column || vscode.ViewColumn.One,
            {
                enableScripts: true,
                retainContextWhenHidden: true,
            }
        );

        ComplianceResultPanel.currentPanel = new ComplianceResultPanel(panel);
        return ComplianceResultPanel.currentPanel;
    }

    /**
     * Displays unified compliance result.
     */
    public showUnifiedResult(result: UnifiedComplianceResult): void {
        this._panel.webview.html = this._getUnifiedResultHtml(result);
    }

    /**
     * Displays EU AI Act result.
     */
    public showEUAIActResult(result: EUAIActComplianceResult): void {
        this._panel.webview.html = this._getEUAIActResultHtml(result);
    }

    /**
     * Displays OWASP LLM result.
     */
    public showOWASPResult(result: OWASPComplianceResult): void {
        this._panel.webview.html = this._getOWASPResultHtml(result);
    }

    /**
     * Displays CSA AICM result.
     */
    public showCSAResult(result: AICMComplianceResult): void {
        this._panel.webview.html = this._getCSAResultHtml(result);
    }

    /**
     * Disposes the panel.
     */
    public dispose(): void {
        ComplianceResultPanel.currentPanel = undefined;
        this._panel.dispose();
        while (this._disposables.length) {
            const disposable = this._disposables.pop();
            if (disposable) {
                disposable.dispose();
            }
        }
    }

    // ========================================================================
    // PRIVATE METHODS - HTML GENERATION
    // ========================================================================

    /**
     * Generates HTML for unified result.
     */
    private _getUnifiedResultHtml(result: UnifiedComplianceResult): string {
        const statusIcon = result.compliant ? '✅' : '⚠️';
        const statusText = result.compliant ? 'COMPLIANT' : 'ISSUES DETECTED';
        const statusClass = result.compliant ? 'status-pass' : 'status-fail';

        let summaryHtml = '';

        if (result.summary.euAiAct) {
            const eu = result.summary.euAiAct;
            const icon = eu.compliant ? '✅' : '⚠️';
            const risk = EU_AI_ACT_RISK_LEVEL_NAMES[eu.riskLevel];
            summaryHtml += `
                <div class="framework-card ${eu.compliant ? '' : 'has-issues'}">
                    <h3>${icon} EU AI Act</h3>
                    <p>Risk Level: <strong>${risk}</strong></p>
                </div>
            `;
        }

        if (result.summary.owaspLlm) {
            const owasp = result.summary.owaspLlm;
            const icon = owasp.secure ? '✅' : '⚠️';
            summaryHtml += `
                <div class="framework-card ${owasp.secure ? '' : 'has-issues'}">
                    <h3>${icon} OWASP LLM Top 10</h3>
                    <p>Vulnerabilities: <strong>${owasp.vulnerabilitiesDetected}</strong></p>
                </div>
            `;
        }

        if (result.summary.csaAicm) {
            const csa = result.summary.csaAicm;
            const icon = csa.compliant ? '✅' : '⚠️';
            const rate = Math.round(csa.complianceRate * 100);
            summaryHtml += `
                <div class="framework-card ${csa.compliant ? '' : 'has-issues'}">
                    <h3>${icon} CSA AI Controls Matrix</h3>
                    <p>Compliance Rate: <strong>${rate}%</strong></p>
                </div>
            `;
        }

        const recommendationsHtml = this._getRecommendationsHtml(result.recommendations);

        return this._wrapHtml(`
            <div class="header">
                <h1>${statusIcon} Compliance Check Result</h1>
                <div class="status ${statusClass}">${statusText}</div>
            </div>

            <div class="summary-grid">
                ${summaryHtml}
            </div>

            ${recommendationsHtml}

            <div class="metadata">
                <p>Checked: ${result.frameworksChecked.join(', ')}</p>
                <p>Time: ${result.timestamp}</p>
            </div>
        `);
    }

    /**
     * Generates HTML for EU AI Act result.
     */
    private _getEUAIActResultHtml(result: EUAIActComplianceResult): string {
        const statusIcon = result.compliant ? '✅' : '⚠️';
        const statusText = result.compliant ? 'COMPLIANT' : 'NON-COMPLIANT';
        const statusClass = result.compliant ? 'status-pass' : 'status-fail';
        const riskName = EU_AI_ACT_RISK_LEVEL_NAMES[result.riskLevel];

        let prohibitedHtml = '';
        if (result.prohibitedPractices.length > 0) {
            prohibitedHtml = `
                <div class="section critical">
                    <h2>🚫 Prohibited Practices Detected (Article 5)</h2>
                    <ul>
                        ${result.prohibitedPractices.map(p => `<li>${p.replace(/_/g, ' ')}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        let highRiskHtml = '';
        if (result.highRiskContexts.length > 0) {
            highRiskHtml = `
                <div class="section warning">
                    <h2>⚠️ High-Risk Contexts (Annex III)</h2>
                    <ul>
                        ${result.highRiskContexts.map(c => `<li>${c.replace(/_/g, ' ')}</li>`).join('')}
                    </ul>
                </div>
            `;
        }

        let articlesHtml = '';
        if (result.articleFindings.length > 0) {
            articlesHtml = `
                <div class="section">
                    <h2>📋 Article Findings</h2>
                    ${result.articleFindings.map(f => `
                        <div class="finding ${f.compliant ? 'compliant' : 'non-compliant'}">
                            <h4>Article ${f.article}${f.subArticle ? ` (${f.subArticle})` : ''}</h4>
                            <p class="${f.compliant ? 'pass' : 'fail'}">
                                ${f.compliant ? '✅ Compliant' : `⚠️ ${f.severity?.toUpperCase()}`}
                            </p>
                            ${f.issues.length > 0 ? `<ul>${f.issues.map(i => `<li>${i}</li>`).join('')}</ul>` : ''}
                        </div>
                    `).join('')}
                </div>
            `;
        }

        const recommendationsHtml = this._getRecommendationsHtml(result.recommendations);

        return this._wrapHtml(`
            <div class="header">
                <h1>${statusIcon} EU AI Act Compliance</h1>
                <div class="status ${statusClass}">${statusText}</div>
            </div>

            <div class="risk-level ${result.riskLevel}">
                <h2>Risk Level: ${riskName}</h2>
                <p>System Type: ${result.systemType.replace(/_/g, ' ')}</p>
                ${result.oversightRequired ? `<p>Oversight: ${result.oversightRequired.replace(/_/g, ' ')}</p>` : ''}
            </div>

            ${prohibitedHtml}
            ${highRiskHtml}
            ${articlesHtml}
            ${recommendationsHtml}

            <div class="metadata">
                <p>Method: ${result.metadata.analysisMethod}</p>
                <p>Time: ${result.metadata.timestamp}</p>
            </div>
        `);
    }

    /**
     * Generates HTML for OWASP result.
     */
    private _getOWASPResultHtml(result: OWASPComplianceResult): string {
        const statusIcon = result.secure ? '✅' : '⚠️';
        const statusText = result.secure ? 'SECURE' : 'VULNERABILITIES DETECTED';
        const statusClass = result.secure ? 'status-pass' : 'status-fail';

        const findingsHtml = result.findings.map(f => {
            const icon = f.detected ? '⚠️' : '✅';
            const className = f.detected ? 'detected' : 'clear';
            return `
                <div class="vulnerability ${className}">
                    <h4>${icon} ${f.vulnerability}: ${f.name}</h4>
                    <p>Coverage: ${f.coverageLevel} | Gates: ${f.gatesChecked.join(', ') || 'N/A'}</p>
                    ${f.detected && f.severity ? `<p class="severity ${f.severity}">Severity: ${f.severity.toUpperCase()}</p>` : ''}
                    ${f.recommendation ? `<p class="recommendation">${f.recommendation}</p>` : ''}
                </div>
            `;
        }).join('');

        const recommendationsHtml = this._getRecommendationsHtml(result.recommendations);

        return this._wrapHtml(`
            <div class="header">
                <h1>${statusIcon} OWASP LLM Top 10</h1>
                <div class="status ${statusClass}">${statusText}</div>
            </div>

            <div class="stats">
                <div class="stat">
                    <span class="number">${result.vulnerabilitiesChecked}</span>
                    <span class="label">Checked</span>
                </div>
                <div class="stat">
                    <span class="number ${result.vulnerabilitiesDetected > 0 ? 'alert' : ''}">${result.vulnerabilitiesDetected}</span>
                    <span class="label">Detected</span>
                </div>
                <div class="stat">
                    <span class="number">${Math.round(result.detectionRate * 100)}%</span>
                    <span class="label">Detection Rate</span>
                </div>
            </div>

            <div class="section">
                <h2>Vulnerability Assessment</h2>
                ${findingsHtml}
            </div>

            ${recommendationsHtml}

            <div class="metadata">
                <p>Method: ${result.metadata.analysisMethod}</p>
                <p>Time: ${result.metadata.timestamp}</p>
            </div>
        `);
    }

    /**
     * Generates HTML for CSA AICM result.
     */
    private _getCSAResultHtml(result: AICMComplianceResult): string {
        const statusIcon = result.compliant ? '✅' : '⚠️';
        const statusText = result.compliant ? 'COMPLIANT' : 'ISSUES DETECTED';
        const statusClass = result.compliant ? 'status-pass' : 'status-fail';
        const compliancePercent = Math.round(result.complianceRate * 100);

        const domainsHtml = result.domainFindings.map(f => {
            const icon = f.compliant ? '✅' : '⚠️';
            const className = f.compliant ? 'compliant' : 'non-compliant';
            return `
                <div class="domain ${className}">
                    <h4>${icon} ${f.displayName}</h4>
                    <p>Coverage: ${f.coverageLevel}</p>
                    ${f.gatesChecked.length > 0 ? `<p>Gates: ${f.gatesChecked.join(', ')}</p>` : ''}
                    ${f.recommendation ? `<p class="recommendation">${f.recommendation}</p>` : ''}
                </div>
            `;
        }).join('');

        const threatHtml = `
            <div class="section">
                <h2>Threat Assessment</h2>
                <p>Threat Score: ${Math.round(result.threatAssessment.overallThreatScore * 100)}%</p>
                ${result.threatAssessment.threatsDetected.length > 0 ? `
                    <h4>Threats Detected:</h4>
                    <ul>${result.threatAssessment.threatsDetected.map(t => `<li>${t}</li>`).join('')}</ul>
                ` : '<p>No threats detected</p>'}
            </div>
        `;

        const recommendationsHtml = this._getRecommendationsHtml(result.recommendations);

        return this._wrapHtml(`
            <div class="header">
                <h1>${statusIcon} CSA AI Controls Matrix</h1>
                <div class="status ${statusClass}">${statusText}</div>
            </div>

            <div class="stats">
                <div class="stat">
                    <span class="number">${result.domainsAssessed}</span>
                    <span class="label">Domains</span>
                </div>
                <div class="stat">
                    <span class="number">${result.domainsCompliant}</span>
                    <span class="label">Compliant</span>
                </div>
                <div class="stat">
                    <span class="number">${compliancePercent}%</span>
                    <span class="label">Rate</span>
                </div>
            </div>

            <div class="section">
                <h2>Domain Assessment</h2>
                <div class="domains-grid">
                    ${domainsHtml}
                </div>
            </div>

            ${threatHtml}
            ${recommendationsHtml}

            <div class="metadata">
                <p>Method: ${result.metadata.analysisMethod}</p>
                <p>Time: ${result.metadata.timestamp}</p>
            </div>
        `);
    }

    /**
     * Generates recommendations HTML section.
     */
    private _getRecommendationsHtml(recommendations: string[]): string {
        if (recommendations.length === 0) {
            return '';
        }

        return `
            <div class="section recommendations">
                <h2>📋 Recommendations</h2>
                <ul>
                    ${recommendations.map(r => {
                        let className = '';
                        if (r.startsWith('CRITICAL:')) {
                            className = 'critical';
                        } else if (r.startsWith('HIGH:')) {
                            className = 'high';
                        } else if (r.startsWith('MEDIUM:')) {
                            className = 'medium';
                        }
                        return `<li class="${className}">${r}</li>`;
                    }).join('')}
                </ul>
            </div>
        `;
    }

    /**
     * Wraps content in full HTML document with styles.
     */
    private _wrapHtml(content: string): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sentinel Compliance Check</title>
    <style>
        :root {
            --bg-color: var(--vscode-editor-background);
            --text-color: var(--vscode-editor-foreground);
            --border-color: var(--vscode-panel-border);
            --success-color: #4caf50;
            --warning-color: #ff9800;
            --error-color: #f44336;
            --info-color: #2196f3;
        }

        body {
            font-family: var(--vscode-font-family);
            padding: 20px;
            color: var(--text-color);
            background: var(--bg-color);
            line-height: 1.6;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 1px solid var(--border-color);
        }

        .header h1 {
            margin: 0;
            font-size: 1.5em;
        }

        .status {
            padding: 8px 16px;
            border-radius: 4px;
            font-weight: bold;
        }

        .status-pass {
            background: var(--success-color);
            color: white;
        }

        .status-fail {
            background: var(--error-color);
            color: white;
        }

        .summary-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .framework-card {
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: var(--vscode-editor-inactiveSelectionBackground);
        }

        .framework-card.has-issues {
            border-color: var(--warning-color);
        }

        .framework-card h3 {
            margin: 0 0 10px 0;
        }

        .framework-card p {
            margin: 0;
        }

        .section {
            margin: 20px 0;
            padding: 15px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }

        .section.critical {
            border-color: var(--error-color);
            background: rgba(244, 67, 54, 0.1);
        }

        .section.warning {
            border-color: var(--warning-color);
            background: rgba(255, 152, 0, 0.1);
        }

        .section h2 {
            margin-top: 0;
        }

        .risk-level {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }

        .risk-level.unacceptable {
            background: rgba(244, 67, 54, 0.2);
            border: 2px solid var(--error-color);
        }

        .risk-level.high {
            background: rgba(255, 152, 0, 0.2);
            border: 2px solid var(--warning-color);
        }

        .risk-level.limited, .risk-level.minimal {
            background: rgba(76, 175, 80, 0.2);
            border: 2px solid var(--success-color);
        }

        .stats {
            display: flex;
            gap: 30px;
            margin: 20px 0;
        }

        .stat {
            text-align: center;
        }

        .stat .number {
            display: block;
            font-size: 2em;
            font-weight: bold;
        }

        .stat .number.alert {
            color: var(--error-color);
        }

        .stat .label {
            font-size: 0.9em;
            opacity: 0.8;
        }

        .vulnerability, .domain, .finding {
            padding: 10px;
            margin: 10px 0;
            border-left: 3px solid var(--border-color);
            background: var(--vscode-editor-inactiveSelectionBackground);
        }

        .vulnerability.detected, .domain.non-compliant, .finding.non-compliant {
            border-left-color: var(--warning-color);
        }

        .vulnerability.clear, .domain.compliant, .finding.compliant {
            border-left-color: var(--success-color);
        }

        .vulnerability h4, .domain h4, .finding h4 {
            margin: 0 0 5px 0;
        }

        .vulnerability p, .domain p, .finding p {
            margin: 5px 0;
            font-size: 0.9em;
        }

        .severity {
            font-weight: bold;
        }

        .severity.critical { color: var(--error-color); }
        .severity.high { color: var(--warning-color); }
        .severity.medium { color: var(--info-color); }

        .recommendation {
            font-style: italic;
            opacity: 0.9;
        }

        .recommendations ul {
            list-style: none;
            padding: 0;
        }

        .recommendations li {
            padding: 8px 12px;
            margin: 5px 0;
            background: var(--vscode-editor-inactiveSelectionBackground);
            border-radius: 4px;
        }

        .recommendations li.critical {
            border-left: 3px solid var(--error-color);
        }

        .recommendations li.high {
            border-left: 3px solid var(--warning-color);
        }

        .recommendations li.medium {
            border-left: 3px solid var(--info-color);
        }

        .domains-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 10px;
        }

        .metadata {
            margin-top: 30px;
            padding-top: 15px;
            border-top: 1px solid var(--border-color);
            font-size: 0.85em;
            opacity: 0.7;
        }

        .metadata p {
            margin: 5px 0;
        }

        ul {
            margin: 10px 0;
            padding-left: 20px;
        }

        .pass { color: var(--success-color); }
        .fail { color: var(--error-color); }
    </style>
</head>
<body>
    ${content}
</body>
</html>`;
    }
}

// ============================================================================
// HELPER FUNCTIONS
// ============================================================================

/**
 * Shows compliance result in panel.
 */
export function showComplianceResult(
    extensionUri: vscode.Uri,
    result: UnifiedComplianceResult | EUAIActComplianceResult | OWASPComplianceResult | AICMComplianceResult,
    framework?: ComplianceFramework
): void {
    const panel = ComplianceResultPanel.createOrShow(extensionUri);

    if ('frameworksChecked' in result) {
        panel.showUnifiedResult(result as UnifiedComplianceResult);
    } else if (framework === 'eu_ai_act' || 'riskLevel' in result) {
        panel.showEUAIActResult(result as EUAIActComplianceResult);
    } else if (framework === 'owasp_llm' || 'vulnerabilitiesDetected' in result) {
        panel.showOWASPResult(result as OWASPComplianceResult);
    } else if (framework === 'csa_aicm' || 'domainsAssessed' in result) {
        panel.showCSAResult(result as AICMComplianceResult);
    }
}
