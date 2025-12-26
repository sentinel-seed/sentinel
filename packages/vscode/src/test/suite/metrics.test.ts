import * as assert from 'assert';
import * as vscode from 'vscode';
import { MetricsTracker } from '../../metrics';

// Mock globalState for testing
class MockGlobalState implements vscode.Memento {
    private data: Record<string, unknown> = {};

    keys(): readonly string[] {
        return Object.keys(this.data);
    }

    get<T>(key: string): T | undefined;
    get<T>(key: string, defaultValue: T): T;
    get<T>(key: string, defaultValue?: T): T | undefined {
        const value = this.data[key];
        return value !== undefined ? value as T : defaultValue;
    }

    async update(key: string, value: unknown): Promise<void> {
        this.data[key] = value;
    }

    setKeysForSync(_keys: readonly string[]): void {
        // Not needed for tests
    }

    reset(): void {
        this.data = {};
    }
}

// Create mock context
function createMockContext(): vscode.ExtensionContext {
    const globalState = new MockGlobalState();

    return {
        globalState,
        subscriptions: [],
        workspaceState: globalState,
        extensionPath: '',
        extensionUri: vscode.Uri.file(''),
        storagePath: undefined,
        storageUri: undefined,
        globalStoragePath: '',
        globalStorageUri: vscode.Uri.file(''),
        logPath: '',
        logUri: vscode.Uri.file(''),
        extensionMode: vscode.ExtensionMode.Test,
        environmentVariableCollection: {} as vscode.GlobalEnvironmentVariableCollection,
        asAbsolutePath: (p: string) => p,
        secrets: {} as vscode.SecretStorage,
        extension: {} as vscode.Extension<unknown>,
        languageModelAccessInformation: {} as vscode.LanguageModelAccessInformation,
    };
}

suite('Metrics Tracker Test Suite', () => {
    let tracker: MetricsTracker;
    let mockContext: vscode.ExtensionContext;
    let mockGlobalState: MockGlobalState;

    setup(() => {
        mockContext = createMockContext();
        mockGlobalState = mockContext.globalState as MockGlobalState;
        mockGlobalState.reset();
        tracker = new MetricsTracker(mockContext);
    });

    suite('Recording Analysis', () => {
        test('should record a safe analysis', async () => {
            await tracker.recordAnalysis(
                'semantic',
                true,
                { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' },
                0,
                'OpenAI'
            );

            const summary = tracker.getSummary();
            assert.strictEqual(summary.totalAnalyses, 1);
            assert.strictEqual(summary.safeCount, 1);
            assert.strictEqual(summary.unsafeCount, 0);
            assert.strictEqual(summary.semanticCount, 1);
        });

        test('should record an unsafe analysis', async () => {
            await tracker.recordAnalysis(
                'heuristic',
                false,
                { truth: 'fail', harm: 'pass', scope: 'pass', purpose: 'pass' },
                2,
                undefined
            );

            const summary = tracker.getSummary();
            assert.strictEqual(summary.totalAnalyses, 1);
            assert.strictEqual(summary.safeCount, 0);
            assert.strictEqual(summary.unsafeCount, 1);
            assert.strictEqual(summary.heuristicCount, 1);
            assert.strictEqual(summary.gateFailures.truth, 1);
            assert.strictEqual(summary.issuesDetected, 2);
        });

        test('should track multiple analyses', async () => {
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');
            await tracker.recordAnalysis('semantic', false, { truth: 'pass', harm: 'fail', scope: 'pass', purpose: 'pass' }, 1, 'OpenAI');
            await tracker.recordAnalysis('heuristic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, undefined);

            const summary = tracker.getSummary();
            assert.strictEqual(summary.totalAnalyses, 3);
            assert.strictEqual(summary.safeCount, 2);
            assert.strictEqual(summary.unsafeCount, 1);
            assert.strictEqual(summary.semanticCount, 2);
            assert.strictEqual(summary.heuristicCount, 1);
        });

        test('should track provider usage', async () => {
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'Anthropic');

            const summary = tracker.getSummary();
            assert.strictEqual(summary.providerUsage['OpenAI'], 2);
            assert.strictEqual(summary.providerUsage['Anthropic'], 1);
        });
    });

    suite('Summary', () => {
        test('should return empty summary when no analyses', () => {
            const summary = tracker.getSummary();
            assert.strictEqual(summary.totalAnalyses, 0);
            assert.strictEqual(summary.safeCount, 0);
            assert.strictEqual(summary.unsafeCount, 0);
            assert.strictEqual(summary.lastAnalysis, null);
            assert.strictEqual(summary.firstAnalysis, null);
        });

        test('should track gate failures correctly', async () => {
            await tracker.recordAnalysis('semantic', false, { truth: 'fail', harm: 'fail', scope: 'pass', purpose: 'pass' }, 2, 'OpenAI');
            await tracker.recordAnalysis('semantic', false, { truth: 'pass', harm: 'fail', scope: 'fail', purpose: 'pass' }, 2, 'OpenAI');

            const summary = tracker.getSummary();
            assert.strictEqual(summary.gateFailures.truth, 1);
            assert.strictEqual(summary.gateFailures.harm, 2);
            assert.strictEqual(summary.gateFailures.scope, 1);
            assert.strictEqual(summary.gateFailures.purpose, 0);
        });
    });

    suite('Recent Metrics', () => {
        test('should return recent metrics', async () => {
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');
            await tracker.recordAnalysis('heuristic', false, { truth: 'fail', harm: 'pass', scope: 'pass', purpose: 'pass' }, 1, undefined);

            const recent = tracker.getRecentMetrics(10);
            assert.strictEqual(recent.length, 2);
        });

        test('should limit recent metrics', async () => {
            for (let i = 0; i < 30; i++) {
                await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');
            }

            const recent = tracker.getRecentMetrics(10);
            assert.strictEqual(recent.length, 10);
        });
    });

    suite('Clear Metrics', () => {
        test('should clear all metrics', async () => {
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');
            await tracker.recordAnalysis('semantic', true, { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }, 0, 'OpenAI');

            assert.strictEqual(tracker.getMetricsCount(), 2);

            await tracker.clearMetrics();

            assert.strictEqual(tracker.getMetricsCount(), 0);
            assert.strictEqual(tracker.getSummary().totalAnalyses, 0);
        });
    });
});
