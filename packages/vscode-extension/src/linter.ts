import * as vscode from 'vscode';

/**
 * Patterns that may indicate unsafe content in prompts
 */
const UNSAFE_PATTERNS = [
    // Jailbreak attempts
    {
        pattern: /ignore\s+(previous|all|your)\s+(instructions?|guidelines?|rules?)/gi,
        message: 'Potential jailbreak attempt: instruction override',
        severity: vscode.DiagnosticSeverity.Warning
    },
    {
        pattern: /you\s+are\s+now\s+(DAN|an?\s+AI\s+without)/gi,
        message: 'Potential jailbreak attempt: persona switch',
        severity: vscode.DiagnosticSeverity.Warning
    },
    {
        pattern: /pretend\s+(you('re)?|to\s+be)\s+(an?\s+)?evil/gi,
        message: 'Potential jailbreak attempt: evil persona',
        severity: vscode.DiagnosticSeverity.Warning
    },
    {
        pattern: /developer\s+mode|sudo\s+mode|god\s+mode/gi,
        message: 'Potential jailbreak attempt: mode switch',
        severity: vscode.DiagnosticSeverity.Warning
    },
    {
        pattern: /disable\s+(safety|content\s+filter|guardrails)/gi,
        message: 'Potential jailbreak attempt: safety bypass',
        severity: vscode.DiagnosticSeverity.Error
    },

    // Harmful content markers
    {
        pattern: /\b(make|create|build)\s+(a\s+)?(bomb|explosive|weapon)/gi,
        message: 'Potential harmful content: weapons/explosives',
        severity: vscode.DiagnosticSeverity.Error
    },
    {
        pattern: /\bhow\s+to\s+(hack|exploit|breach|attack)/gi,
        message: 'Potential harmful content: hacking instructions',
        severity: vscode.DiagnosticSeverity.Warning
    },
    {
        pattern: /\b(phishing|malware|ransomware|keylogger)\b/gi,
        message: 'Potential harmful content: malicious software',
        severity: vscode.DiagnosticSeverity.Warning
    },

    // Deception markers
    {
        pattern: /\b(fake|forged?|counterfeit)\s+(document|id|identity|news)/gi,
        message: 'Potential deception: fake documents',
        severity: vscode.DiagnosticSeverity.Warning
    },
    {
        pattern: /\bimpersonate\s+(a\s+)?(person|someone|official)/gi,
        message: 'Potential deception: impersonation',
        severity: vscode.DiagnosticSeverity.Warning
    },

    // Missing purpose indicators (informational)
    {
        pattern: /\bjust\s+(do|execute|run)\s+it\b/gi,
        message: 'Consider: Request lacks clear purpose (THSP Gate 4)',
        severity: vscode.DiagnosticSeverity.Information
    }
];

/**
 * Patterns that indicate good safety practices
 */
const SAFE_PATTERNS = [
    /sentinel\s+alignment\s+seed/gi,
    /thsp\s+protocol/gi,
    /truth.*harm.*scope.*purpose/gi
];

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
        const hasSentinelSeed = SAFE_PATTERNS.some(pattern => pattern.test(text));

        // Check for unsafe patterns
        for (const { pattern, message, severity } of UNSAFE_PATTERNS) {
            // Reset regex lastIndex
            pattern.lastIndex = 0;

            let match;
            while ((match = pattern.exec(text)) !== null) {
                const startPos = document.positionAt(match.index);
                const endPos = document.positionAt(match.index + match[0].length);
                const range = new vscode.Range(startPos, endPos);

                const diagnostic = new vscode.Diagnostic(
                    range,
                    `[Sentinel] ${message}`,
                    severity
                );
                diagnostic.source = 'sentinel';
                diagnostic.code = 'thsp-check';

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

    private looksLikeSystemPrompt(text: string): boolean {
        const promptIndicators = [
            /system\s*prompt/gi,
            /you\s+are\s+(a|an)\s+/gi,
            /your\s+role\s+is/gi,
            /as\s+an?\s+ai\s+assistant/gi,
            /instructions?:/gi
        ];

        return promptIndicators.some(pattern => pattern.test(text));
    }
}
