import * as vscode from 'vscode';
import { SentinelLinter } from './linter';
import { SentinelAnalyzer } from './analyzer';
import { SEED_MINIMAL, SEED_STANDARD } from './seeds';

let linter: SentinelLinter;
let analyzer: SentinelAnalyzer;
let diagnosticCollection: vscode.DiagnosticCollection;

export function activate(context: vscode.ExtensionContext) {
    console.log('Sentinel AI Safety extension activated');

    // Initialize components
    diagnosticCollection = vscode.languages.createDiagnosticCollection('sentinel');
    linter = new SentinelLinter(diagnosticCollection);
    analyzer = new SentinelAnalyzer();

    // Register commands
    const analyzeSelectionCmd = vscode.commands.registerCommand(
        'sentinel.analyzeSelection',
        analyzeSelection
    );

    const analyzeFileCmd = vscode.commands.registerCommand(
        'sentinel.analyzeFile',
        analyzeFile
    );

    const insertSeedCmd = vscode.commands.registerCommand(
        'sentinel.insertSeed',
        () => insertSeed('standard')
    );

    const insertSeedMinimalCmd = vscode.commands.registerCommand(
        'sentinel.insertSeedMinimal',
        () => insertSeed('minimal')
    );

    // Register event listeners for real-time linting
    const config = vscode.workspace.getConfiguration('sentinel');
    if (config.get('enableRealTimeLinting')) {
        const onChangeDisposable = vscode.workspace.onDidChangeTextDocument(
            (event) => {
                if (shouldLintDocument(event.document)) {
                    linter.lintDocument(event.document);
                }
            }
        );

        const onOpenDisposable = vscode.workspace.onDidOpenTextDocument(
            (document) => {
                if (shouldLintDocument(document)) {
                    linter.lintDocument(document);
                }
            }
        );

        context.subscriptions.push(onChangeDisposable, onOpenDisposable);
    }

    // Add all disposables
    context.subscriptions.push(
        diagnosticCollection,
        analyzeSelectionCmd,
        analyzeFileCmd,
        insertSeedCmd,
        insertSeedMinimalCmd
    );

    // Lint all open documents on activation
    vscode.workspace.textDocuments.forEach((document) => {
        if (shouldLintDocument(document)) {
            linter.lintDocument(document);
        }
    });
}

export function deactivate() {
    if (diagnosticCollection) {
        diagnosticCollection.dispose();
    }
}

function shouldLintDocument(document: vscode.TextDocument): boolean {
    const supportedLanguages = [
        'markdown', 'plaintext', 'python', 'javascript',
        'typescript', 'json', 'yaml'
    ];
    return supportedLanguages.includes(document.languageId);
}

async function analyzeSelection() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const text = editor.document.getText(selection);

    if (!text) {
        vscode.window.showWarningMessage('No text selected');
        return;
    }

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Analyzing with Sentinel...',
            cancellable: false
        },
        async () => {
            const result = await analyzer.analyze(text);
            showAnalysisResult(result);
        }
    );
}

async function analyzeFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const text = editor.document.getText();

    vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'Analyzing file with Sentinel...',
            cancellable: false
        },
        async () => {
            const result = await analyzer.analyze(text);
            showAnalysisResult(result);
        }
    );
}

function showAnalysisResult(result: any) {
    const safetyStatus = result.safe ? '✅ SAFE' : '⚠️ UNSAFE';
    const gates = result.gates;
    const method = result.method === 'semantic' ? '🧠 Semantic' : '📋 Heuristic';
    const confidence = Math.round((result.confidence || 0.5) * 100);

    let message = `${safetyStatus}\n\n`;
    message += `Analysis: ${method} (${confidence}% confidence)\n\n`;
    message += `Gates:\n`;
    message += `• Truth: ${gates.truth}\n`;
    message += `• Harm: ${gates.harm}\n`;
    message += `• Scope: ${gates.scope}\n`;
    message += `• Purpose: ${gates.purpose}\n`;

    if (result.issues && result.issues.length > 0) {
        message += `\nIssues:\n`;
        result.issues.forEach((issue: string) => {
            message += `• ${issue}\n`;
        });
    }

    if (result.reasoning) {
        message += `\nReasoning: ${result.reasoning}\n`;
    }

    if (result.method === 'heuristic') {
        message += `\n⚠️ For accurate semantic analysis, configure an LLM API key in settings.`;
    }

    if (result.safe) {
        vscode.window.showInformationMessage(message, { modal: true });
    } else {
        vscode.window.showWarningMessage(message, { modal: true });
    }
}

async function insertSeed(variant: 'minimal' | 'standard') {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const seed = variant === 'minimal' ? SEED_MINIMAL : SEED_STANDARD;
    const position = editor.selection.active;

    await editor.edit((editBuilder) => {
        editBuilder.insert(position, seed);
    });

    vscode.window.showInformationMessage(
        `Sentinel ${variant} seed inserted (${variant === 'minimal' ? '~450' : '~1,400'} tokens)`
    );
}
