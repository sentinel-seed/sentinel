import * as assert from 'assert';
import * as vscode from 'vscode';

/**
 * Extension Test Suite
 *
 * Tests the extension's main entry point (extension.ts).
 * These are integration tests that verify real behavior.
 */
suite('Extension Test Suite', () => {

    suite('Extension Activation', () => {

        test('extension should be present', () => {
            const extension = vscode.extensions.getExtension('sentinelseed.sentinel-ai-safety');
            assert.ok(extension, 'Extension should be installed');
        });

        test('extension should activate successfully', async function() {
            this.timeout(10000); // Allow time for activation

            const extension = vscode.extensions.getExtension('sentinelseed.sentinel-ai-safety');
            assert.ok(extension, 'Extension should be installed');

            if (!extension.isActive) {
                await extension.activate();
            }

            assert.strictEqual(extension.isActive, true, 'Extension should be active');
        });

    });

    suite('Command Registration', () => {

        const EXPECTED_COMMANDS = [
            'sentinel.analyzeSelection',
            'sentinel.analyzeFile',
            'sentinel.insertSeed',
            'sentinel.insertSeedMinimal',
            'sentinel.showStatus',
            'sentinel.setOpenAIKey',
            'sentinel.setAnthropicKey',
            'sentinel.setCompatibleKey',
            'sentinel.checkComplianceAll',
            'sentinel.checkComplianceEUAIAct',
            'sentinel.checkComplianceOWASP',
            'sentinel.checkComplianceCSA',
            'sentinel.scanSecrets',
            'sentinel.sanitizePrompt',
            'sentinel.validateOutput'
        ];

        test('all sentinel commands should be registered', async function() {
            this.timeout(10000);

            // Ensure extension is activated
            const extension = vscode.extensions.getExtension('sentinelseed.sentinel-ai-safety');
            if (extension && !extension.isActive) {
                await extension.activate();
            }

            // Get all registered commands
            const allCommands = await vscode.commands.getCommands(true);

            // Check each expected command is registered
            for (const expectedCmd of EXPECTED_COMMANDS) {
                const isRegistered = allCommands.includes(expectedCmd);
                assert.ok(isRegistered, `Command '${expectedCmd}' should be registered`);
            }
        });

        test('should have exactly 15 sentinel commands', async function() {
            this.timeout(5000);

            const allCommands = await vscode.commands.getCommands(true);
            const sentinelCommands = allCommands.filter(c => c.startsWith('sentinel.'));

            assert.strictEqual(
                sentinelCommands.length,
                15,
                `Expected 15 sentinel commands, found ${sentinelCommands.length}: ${sentinelCommands.join(', ')}`
            );
        });

    });

    suite('Configuration', () => {

        test('sentinel configuration should exist', () => {
            const config = vscode.workspace.getConfiguration('sentinel');
            assert.ok(config, 'Sentinel configuration should exist');
        });

        test('enableRealTimeLinting should default to true', () => {
            const config = vscode.workspace.getConfiguration('sentinel');
            const value = config.get<boolean>('enableRealTimeLinting');
            assert.strictEqual(value, true, 'enableRealTimeLinting should default to true');
        });

        test('seedVariant should default to standard', () => {
            const config = vscode.workspace.getConfiguration('sentinel');
            const value = config.get<string>('seedVariant');
            assert.strictEqual(value, 'standard', 'seedVariant should default to standard');
        });

        test('llmProvider should default to openai', () => {
            const config = vscode.workspace.getConfiguration('sentinel');
            const value = config.get<string>('llmProvider');
            assert.strictEqual(value, 'openai', 'llmProvider should default to openai');
        });

        test('highlightUnsafePatterns should default to true', () => {
            const config = vscode.workspace.getConfiguration('sentinel');
            const value = config.get<boolean>('highlightUnsafePatterns');
            assert.strictEqual(value, true, 'highlightUnsafePatterns should default to true');
        });

    });

    suite('Diagnostic Collection', () => {

        test('sentinel diagnostic collection should exist', async function() {
            this.timeout(5000);

            // Ensure extension is activated
            const extension = vscode.extensions.getExtension('sentinelseed.sentinel-ai-safety');
            if (extension && !extension.isActive) {
                await extension.activate();
            }

            // The diagnostic collection is internal, but we can check that
            // the extension doesn't throw errors on activation
            assert.ok(extension?.isActive, 'Extension should activate without errors');
        });

    });

    suite('Status Bar', () => {

        test('extension should contribute to status bar', async function() {
            this.timeout(5000);

            // Ensure extension is activated
            const extension = vscode.extensions.getExtension('sentinelseed.sentinel-ai-safety');
            if (extension && !extension.isActive) {
                await extension.activate();
            }

            // Status bar item is internal, but we verify activation doesn't fail
            assert.ok(extension?.isActive, 'Extension should activate with status bar');
        });

    });

    suite('Package.json Consistency', () => {

        test('package.json commands should match registered commands', async function() {
            this.timeout(5000);

            const extension = vscode.extensions.getExtension('sentinelseed.sentinel-ai-safety');
            assert.ok(extension, 'Extension should be installed');

            // Get commands from package.json
            const packageCommands = extension.packageJSON.contributes?.commands || [];
            const packageCommandIds = packageCommands.map((c: { command: string }) => c.command);

            // Get registered commands
            const allCommands = await vscode.commands.getCommands(true);
            const registeredSentinelCommands = allCommands.filter(c => c.startsWith('sentinel.'));

            // Each package.json command should be registered
            for (const pkgCmd of packageCommandIds) {
                assert.ok(
                    registeredSentinelCommands.includes(pkgCmd),
                    `Package command '${pkgCmd}' should be registered`
                );
            }

            // Each registered command should be in package.json
            for (const regCmd of registeredSentinelCommands) {
                assert.ok(
                    packageCommandIds.includes(regCmd),
                    `Registered command '${regCmd}' should be in package.json`
                );
            }
        });

    });

});
