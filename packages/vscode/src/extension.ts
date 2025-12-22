import * as vscode from 'vscode';
import { SentinelLinter } from './linter';
import { SentinelAnalyzer, AnalysisResult } from './analyzer';
import { SEED_MINIMAL, SEED_STANDARD, estimateTokenCount } from './seeds';
import { SecretManager, promptForApiKey } from './secrets';
import { ComplianceChecker, ComplianceFramework } from './compliance';
import { showComplianceResult } from './compliance/resultPanel';

let linter: SentinelLinter;
let analyzer: SentinelAnalyzer;
let complianceChecker: ComplianceChecker;
let diagnosticCollection: vscode.DiagnosticCollection;
let statusBarItem: vscode.StatusBarItem;
let secretManager: SecretManager;

export async function activate(context: vscode.ExtensionContext) {
    console.log('Sentinel AI Safety extension activated');

    // Initialize components
    diagnosticCollection = vscode.languages.createDiagnosticCollection('sentinel');
    linter = new SentinelLinter(diagnosticCollection);
    analyzer = new SentinelAnalyzer();
    complianceChecker = new ComplianceChecker();
    secretManager = new SecretManager(context);

    // Load API keys from SecretStorage
    await loadSecretKeys();

    // Migrate API keys from settings to secure storage (if any)
    try {
        await secretManager.migrateFromSettings();
    } catch (error) {
        console.warn('Failed to migrate API keys from settings:', error);
    }

    // Create status bar item
    statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
    statusBarItem.command = 'sentinel.showStatus';
    updateStatusBar();
    statusBarItem.show();

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

    const showStatusCmd = vscode.commands.registerCommand(
        'sentinel.showStatus',
        showStatus
    );

    const setOpenAIKeyCmd = vscode.commands.registerCommand(
        'sentinel.setOpenAIKey',
        async () => {
            const success = await promptForApiKey(secretManager, 'openai');
            if (success) {
                await loadSecretKeys();
                updateStatusBar();
            }
        }
    );

    const setAnthropicKeyCmd = vscode.commands.registerCommand(
        'sentinel.setAnthropicKey',
        async () => {
            const success = await promptForApiKey(secretManager, 'anthropic');
            if (success) {
                await loadSecretKeys();
                updateStatusBar();
            }
        }
    );

    const setCompatibleKeyCmd = vscode.commands.registerCommand(
        'sentinel.setCompatibleKey',
        async () => {
            const success = await promptForApiKey(secretManager, 'openai-compatible');
            if (success) {
                await loadSecretKeys();
                updateStatusBar();
            }
        }
    );

    // Compliance check commands
    const checkComplianceAllCmd = vscode.commands.registerCommand(
        'sentinel.checkComplianceAll',
        () => checkComplianceHandler(context, 'all')
    );

    const checkComplianceEUAIActCmd = vscode.commands.registerCommand(
        'sentinel.checkComplianceEUAIAct',
        () => checkComplianceHandler(context, 'eu_ai_act')
    );

    const checkComplianceOWASPCmd = vscode.commands.registerCommand(
        'sentinel.checkComplianceOWASP',
        () => checkComplianceHandler(context, 'owasp_llm')
    );

    const checkComplianceCSACmd = vscode.commands.registerCommand(
        'sentinel.checkComplianceCSA',
        () => checkComplianceHandler(context, 'csa_aicm')
    );

    // Quick security commands
    const scanSecretsCmd = vscode.commands.registerCommand(
        'sentinel.scanSecrets',
        scanForSecrets
    );

    const sanitizePromptCmd = vscode.commands.registerCommand(
        'sentinel.sanitizePrompt',
        sanitizePrompt
    );

    const validateOutputCmd = vscode.commands.registerCommand(
        'sentinel.validateOutput',
        validateOutput
    );

    // Listen for configuration changes
    const configChangeDisposable = vscode.workspace.onDidChangeConfiguration((e) => {
        if (e.affectsConfiguration('sentinel')) {
            analyzer.refreshValidator();
            updateStatusBar();
        }
    });

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

    // Add all disposables (including linter for proper cleanup)
    context.subscriptions.push(
        diagnosticCollection,
        linter, // Added: linter implements Disposable
        statusBarItem,
        analyzeSelectionCmd,
        analyzeFileCmd,
        insertSeedCmd,
        insertSeedMinimalCmd,
        showStatusCmd,
        setOpenAIKeyCmd,
        setAnthropicKeyCmd,
        setCompatibleKeyCmd,
        checkComplianceAllCmd,
        checkComplianceEUAIActCmd,
        checkComplianceOWASPCmd,
        checkComplianceCSACmd,
        scanSecretsCmd,
        sanitizePromptCmd,
        validateOutputCmd,
        configChangeDisposable
    );

    // Lint all open documents on activation
    vscode.workspace.textDocuments.forEach((document) => {
        if (shouldLintDocument(document)) {
            linter.lintDocument(document);
        }
    });
}

export function deactivate() {
    // Disposables are automatically cleaned up via context.subscriptions
}

function updateStatusBar(): void {
    const status = analyzer.getStatus();
    if (status.semanticAvailable) {
        statusBarItem.text = `$(shield) Sentinel: ${status.provider}`;
        statusBarItem.tooltip = `Semantic analysis enabled (${status.model})`;
        statusBarItem.backgroundColor = undefined;
    } else {
        statusBarItem.text = '$(shield) Sentinel: Heuristic';
        statusBarItem.tooltip = 'Heuristic mode (configure API key for semantic analysis)';
        statusBarItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
    }
}

function showStatus(): void {
    const status = analyzer.getStatus();
    let message: string;

    if (status.semanticAvailable) {
        message = `Sentinel is using semantic analysis.\n\nProvider: ${status.provider}\nModel: ${status.model}\nAccuracy: ~90%`;
    } else {
        message = `Sentinel is using heuristic analysis (pattern matching).\n\nAccuracy: ~50%\n\nTo enable semantic analysis:\n• Run "Sentinel: Set OpenAI Key" or\n• Run "Sentinel: Set Anthropic Key"`;
    }

    vscode.window.showInformationMessage(message, { modal: true });
}

async function loadSecretKeys(): Promise<void> {
    try {
        const openaiKey = await secretManager.getOpenAIKey();
        const anthropicKey = await secretManager.getAnthropicKey();
        const openaiCompatibleKey = await secretManager.getCompatibleKey();

        analyzer.setExternalKeys({
            openaiKey,
            anthropicKey,
            openaiCompatibleKey
        });
    } catch (error) {
        console.warn('Failed to load API keys from secure storage:', error);
        // Continue with heuristic analysis - don't block extension activation
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

    // Check for empty file
    if (!text || text.trim() === '') {
        vscode.window.showInformationMessage('File is empty - nothing to analyze');
        return;
    }

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

function showAnalysisResult(result: AnalysisResult): void {
    const safetyStatus = result.safe ? '✅ SAFE' : '⚠️ UNSAFE';
    const gates = result.gates;
    const method = result.method === 'semantic' ? '🧠 Semantic' : '📋 Heuristic';
    const confidence = Math.round(result.confidence * 100);

    let message = `${safetyStatus}\n\n`;
    message += `Analysis: ${method} (${confidence}% confidence)\n\n`;
    message += `Gates:\n`;
    message += `• Truth: ${gates.truth}\n`;
    message += `• Harm: ${gates.harm}\n`;
    message += `• Scope: ${gates.scope}\n`;
    message += `• Purpose: ${gates.purpose}\n`;

    if (result.issues.length > 0) {
        message += `\nIssues:\n`;
        for (const issue of result.issues) {
            message += `• ${issue}\n`;
        }
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

    // Calculate approximate token count dynamically
    const tokenCount = estimateTokenCount(seed);
    vscode.window.showInformationMessage(
        `Sentinel ${variant} seed inserted (~${tokenCount} tokens)`
    );
}

// ============================================================================
// QUICK SECURITY FUNCTIONS
// ============================================================================

/**
 * Scans content for secrets (API keys, tokens, credentials).
 * Uses OWASP LLM02 (Sensitive Information Disclosure) patterns.
 */
async function scanForSecrets(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const text = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    if (!text || text.trim() === '') {
        vscode.window.showWarningMessage('No content to scan');
        return;
    }

    const hasSecrets = complianceChecker.hasSensitiveInfo(text);

    if (hasSecrets) {
        const result = complianceChecker.checkOWASPOutput(text);
        const secretFindings = result.findings.filter(f =>
            f.vulnerability === 'LLM02' && f.detected
        );

        let message = '⚠️ SECRETS DETECTED\n\n';
        for (const finding of secretFindings) {
            message += `• ${finding.name}\n`;
            if (finding.patternsMatched && finding.patternsMatched.length > 0) {
                const evidence = finding.patternsMatched.slice(0, 3).map(p => p.matchedText);
                message += `  Found: ${evidence.join(', ')}\n`;
            }
        }
        message += '\n🔒 Remove or rotate these credentials before sharing.';

        vscode.window.showWarningMessage(message, { modal: true });
    } else {
        vscode.window.showInformationMessage(
            '✅ No secrets detected\n\nNo API keys, tokens, or credentials found.',
            { modal: true }
        );
    }
}

/**
 * Sanitizes prompt by detecting potential injection attacks.
 * Uses OWASP LLM01 (Prompt Injection) patterns.
 */
async function sanitizePrompt(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const text = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    if (!text || text.trim() === '') {
        vscode.window.showWarningMessage('No content to sanitize');
        return;
    }

    const hasInjection = complianceChecker.hasPromptInjection(text);

    if (hasInjection) {
        const result = complianceChecker.checkOWASPInput(text);
        const injectionFindings = result.findings.filter(f =>
            f.vulnerability === 'LLM01' && f.detected
        );

        let message = '⚠️ PROMPT INJECTION DETECTED\n\n';
        for (const finding of injectionFindings) {
            message += `• ${finding.name}\n`;
            if (finding.patternsMatched && finding.patternsMatched.length > 0) {
                message += `  Pattern: "${finding.patternsMatched[0].matchedText}"\n`;
            }
        }
        message += '\n🛡️ Review and sanitize this input before sending to LLM.';

        vscode.window.showWarningMessage(message, { modal: true });
    } else {
        vscode.window.showInformationMessage(
            '✅ Prompt looks safe\n\nNo injection patterns detected.',
            { modal: true }
        );
    }
}

/**
 * Validates LLM output for security issues.
 * Checks for sensitive data exposure, injection payloads, and unsafe content.
 */
async function validateOutput(): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    const selection = editor.selection;
    const text = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    if (!text || text.trim() === '') {
        vscode.window.showWarningMessage('No content to validate');
        return;
    }

    const result = complianceChecker.checkOWASPOutput(text);
    const issues = result.findings.filter(f => f.detected);

    if (issues.length > 0) {
        let message = '⚠️ OUTPUT VALIDATION ISSUES\n\n';
        for (const issue of issues) {
            message += `• [${issue.vulnerability}] ${issue.name}\n`;
            if (issue.severity === 'critical' || issue.severity === 'high') {
                message += `  Severity: ${issue.severity.toUpperCase()}\n`;
            }
        }
        message += '\n🔍 Review output before displaying to users.';

        vscode.window.showWarningMessage(message, { modal: true });
    } else {
        vscode.window.showInformationMessage(
            '✅ Output validated\n\nNo security issues detected in LLM output.',
            { modal: true }
        );
    }
}

// ============================================================================
// COMPLIANCE CHECKER FUNCTIONS
// ============================================================================

/**
 * Handles compliance check commands.
 * Runs 100% locally - no data sent to Sentinel servers.
 */
async function checkComplianceHandler(
    context: vscode.ExtensionContext,
    framework: ComplianceFramework | 'all'
): Promise<void> {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No active editor');
        return;
    }

    // Get text (selection or full file)
    const selection = editor.selection;
    const text = selection.isEmpty
        ? editor.document.getText()
        : editor.document.getText(selection);

    if (!text || text.trim() === '') {
        vscode.window.showWarningMessage('No content to check');
        return;
    }

    // Show progress
    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: `Checking ${framework === 'all' ? 'all frameworks' : framework.replace(/_/g, ' ')}...`,
            cancellable: false
        },
        async () => {
            try {
                if (framework === 'all') {
                    const result = complianceChecker.checkAll(text);
                    showComplianceResult(context.extensionUri, result);
                } else if (framework === 'eu_ai_act') {
                    const result = complianceChecker.checkEUAIAct(text);
                    showComplianceResult(context.extensionUri, result, 'eu_ai_act');
                } else if (framework === 'owasp_llm') {
                    const result = complianceChecker.checkOWASP(text);
                    showComplianceResult(context.extensionUri, result, 'owasp_llm');
                } else if (framework === 'csa_aicm') {
                    const result = complianceChecker.checkCSA(text);
                    showComplianceResult(context.extensionUri, result, 'csa_aicm');
                }
            } catch (error) {
                const message = error instanceof Error ? error.message : 'Unknown error';
                vscode.window.showErrorMessage(`Compliance check failed: ${message}`);
            }
        }
    );
}
