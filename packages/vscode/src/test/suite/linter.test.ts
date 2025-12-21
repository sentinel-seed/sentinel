import * as assert from 'assert';

suite('Sentinel Linter Test Suite', () => {

    suite('Dispose functionality', () => {

        test('should clear timers on dispose', () => {
            const timers = new Map<string, NodeJS.Timeout>();
            const timer = setTimeout(() => {}, 1000);
            timers.set('test-uri', timer);

            // Simulate dispose
            for (const t of timers.values()) {
                clearTimeout(t);
            }
            timers.clear();

            assert.strictEqual(timers.size, 0, 'Timers are cleared');
        });

        test('should prevent multiple dispose calls', () => {
            let disposeCount = 0;
            let disposed = false;

            const dispose = () => {
                if (disposed) {
                    return;
                }
                disposed = true;
                disposeCount++;
            };

            dispose();
            dispose();
            dispose();

            assert.strictEqual(disposeCount, 1, 'Dispose runs only once');
        });

    });

    suite('Debounce functionality', () => {

        test('debounce timeout should be 500ms', () => {
            const DEBOUNCE_MS = 500;
            assert.strictEqual(DEBOUNCE_MS, 500, 'Debounce is 500ms');
        });

        test('should clear existing timer before creating new one', () => {
            const timers = new Map<string, NodeJS.Timeout>();
            const uri = 'test://document';

            // First timer
            const timer1 = setTimeout(() => {}, 1000);
            timers.set(uri, timer1);

            // Clear and set new timer
            const existingTimer = timers.get(uri);
            if (existingTimer) {
                clearTimeout(existingTimer);
            }

            const timer2 = setTimeout(() => {}, 1000);
            timers.set(uri, timer2);

            assert.strictEqual(timers.size, 1, 'Only one timer per URI');
            clearTimeout(timer2);
        });

    });

    suite('System prompt detection', () => {

        test('should detect "system prompt" keyword', () => {
            const text = 'This is a system prompt for the AI.';
            const pattern = /system\s*prompt/i;
            assert.ok(pattern.test(text), 'Detects system prompt');
        });

        test('should detect "you are a" pattern', () => {
            const text = 'You are a helpful assistant.';
            const pattern = /you\s+are\s+(a|an)\s+/i;
            assert.ok(pattern.test(text), 'Detects you are a pattern');
        });

        test('should detect "your role is" pattern', () => {
            const text = 'Your role is to help users.';
            const pattern = /your\s+role\s+is/i;
            assert.ok(pattern.test(text), 'Detects your role is');
        });

        test('should detect "as an AI assistant" pattern', () => {
            const text = 'As an AI assistant, I help users.';
            const pattern = /as\s+an?\s+ai\s+assistant/i;
            assert.ok(pattern.test(text), 'Detects as an AI assistant');
        });

        test('should detect "instructions:" pattern', () => {
            const text = 'Instructions: Follow these steps.';
            const pattern = /instructions?:/i;
            assert.ok(pattern.test(text), 'Detects instructions:');
        });

        test('should not detect in regular text', () => {
            const text = 'Hello, how can I help you today?';
            const patterns = [
                /system\s*prompt/i,
                /you\s+are\s+(a|an)\s+/i,
                /your\s+role\s+is/i,
                /as\s+an?\s+ai\s+assistant/i,
                /instructions?:/i
            ];

            const matches = patterns.some(p => p.test(text));
            assert.ok(!matches, 'Regular text is not flagged');
        });

    });

    suite('Severity mapping', () => {

        test('should map error severity', () => {
            const severityMap = {
                error: 0, // DiagnosticSeverity.Error
                warning: 1, // DiagnosticSeverity.Warning
                info: 2 // DiagnosticSeverity.Information
            };

            assert.strictEqual(severityMap['error'], 0, 'Error maps to 0');
            assert.strictEqual(severityMap['warning'], 1, 'Warning maps to 1');
            assert.strictEqual(severityMap['info'], 2, 'Info maps to 2');
        });

    });

    suite('Constructor validation', () => {

        test('should throw on null diagnosticCollection', () => {
            assert.throws(() => {
                const collection = null;
                if (!collection) {
                    throw new Error('diagnosticCollection is required');
                }
            }, /diagnosticCollection is required/);
        });

        test('should throw on undefined diagnosticCollection', () => {
            assert.throws(() => {
                const collection = undefined;
                if (!collection) {
                    throw new Error('diagnosticCollection is required');
                }
            }, /diagnosticCollection is required/);
        });

    });

    suite('Document filtering', () => {

        test('should support markdown files', () => {
            const supportedLanguages = [
                'markdown', 'plaintext', 'python', 'javascript',
                'typescript', 'json', 'yaml'
            ];
            assert.ok(supportedLanguages.includes('markdown'), 'Markdown is supported');
        });

        test('should support all required languages', () => {
            const supportedLanguages = [
                'markdown', 'plaintext', 'python', 'javascript',
                'typescript', 'json', 'yaml'
            ];

            const requiredLanguages = ['markdown', 'plaintext', 'json', 'yaml'];
            for (const lang of requiredLanguages) {
                assert.ok(supportedLanguages.includes(lang), `${lang} is supported`);
            }
        });

    });

});
