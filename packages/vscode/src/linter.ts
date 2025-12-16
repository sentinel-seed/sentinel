import * as vscode from 'vscode';
import { THSP_PATTERNS, SAFE_PATTERNS, THSPPattern } from './patterns';

/**
 * Real-time linter for detecting potential safety issues in prompts.
 *
 * NOTE: This uses heuristic pattern matching for performance reasons.
 * Real-time LLM calls would be too slow and expensive.
 * For accurate semantic analysis, use the "Analyze Selection" command.
 */
export class SentinelLinter {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private debounceTimers: Map<string, NodeJS.Timeout> = new Map();

    constructor(diagnosticCollection: vscode.DiagnosticCollection) {
        this.diagnosticCollection = diagnosticCollection;
    }

    public lintDocument(document: vscode.TextDocument): void {
        // Debounce to avoid excessive linting during typing
        const uri = document.uri.toString();
        const existingTimer = this.debounceTimers.get(uri);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        const timer = setTimeout(() => {
            this.performLinting(document);
            this.debounceTimers.delete(uri);
        }, 500);

        this.debounceTimers.set(uri, timer);
    }

    private performLinting(document: vscode.TextDocument): void {
        const config = vscode.workspace.getConfiguration('sentinel');
        if (!config.get('highlightUnsafePatterns')) {
            this.diagnosticCollection.delete(document.uri);
            return;
        }

        const text = document.getText();
        const diagnostics: vscode.Diagnostic[] = [];

        // Check if document contains Sentinel seed (good practice)
        const hasSentinelSeed = SAFE_PATTERNS.some(pattern => {
            pattern.lastIndex = 0;
            return pattern.test(text);
        });

        // Check for unsafe patterns using shared THSP patterns
        for (const thspPattern of THSP_PATTERNS) {
            const { pattern, message, severity } = thspPattern;
            // Reset regex lastIndex
            pattern.lastIndex = 0;

            let match;
            while ((match = pattern.exec(text)) !== null) {
                const startPos = document.positionAt(match.index);
                const endPos = document.positionAt(match.index + match[0].length);
                const range = new vscode.Range(startPos, endPos);

                const vsSeverity = this.mapSeverity(severity);
                const diagnostic = new vscode.Diagnostic(
                    range,
                    `[Sentinel] ${message}`,
                    vsSeverity
                );
                diagnostic.source = 'sentinel';
                diagnostic.code = `thsp-${thspPattern.gate}`;

                diagnostics.push(diagnostic);
            }
        }

        // Add informational message if no Sentinel seed found in system prompts
        if (this.looksLikeSystemPrompt(text) && !hasSentinelSeed) {
            const firstLine = document.lineAt(0);
            const diagnostic = new vscode.Diagnostic(
                firstLine.range,
                '[Sentinel] Consider adding a Sentinel alignment seed for safety. Use command: Sentinel: Insert Alignment Seed',
                vscode.DiagnosticSeverity.Hint
            );
            diagnostic.source = 'sentinel';
            diagnostic.code = 'missing-seed';
            diagnostics.push(diagnostic);
        }

        this.diagnosticCollection.set(document.uri, diagnostics);
    }

    private mapSeverity(severity: 'error' | 'warning' | 'info'): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'error':
                return vscode.DiagnosticSeverity.Error;
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'info':
                return vscode.DiagnosticSeverity.Information;
        }
    }

    private looksLikeSystemPrompt(text: string): boolean {
        const promptIndicators = [
            /system\s*prompt/gi,
            /you\s+are\s+(a|an)\s+/gi,
            /your\s+role\s+is/gi,
            /as\s+an?\s+ai\s+assistant/gi,
            /instructions?:/gi
        ];

        return promptIndicators.some(pattern => {
            pattern.lastIndex = 0;
            return pattern.test(text);
        });
    }
}
