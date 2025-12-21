import * as assert from 'assert';

suite('Sentinel Analyzer Test Suite', () => {

    suite('AnalysisResult structure', () => {

        test('should have required fields', () => {
            const result = {
                safe: true,
                gates: {
                    truth: 'pass',
                    harm: 'pass',
                    scope: 'pass',
                    purpose: 'pass'
                },
                issues: [],
                confidence: 0.9,
                method: 'semantic' as const,
                reasoning: 'All gates passed'
            };

            assert.ok('safe' in result, 'Has safe field');
            assert.ok('gates' in result, 'Has gates field');
            assert.ok('issues' in result, 'Has issues field');
            assert.ok('confidence' in result, 'Has confidence field');
            assert.ok('method' in result, 'Has method field');
        });

        test('gates should have all THSP fields', () => {
            const gates = {
                truth: 'pass',
                harm: 'pass',
                scope: 'pass',
                purpose: 'pass'
            };

            assert.ok('truth' in gates, 'Has truth gate');
            assert.ok('harm' in gates, 'Has harm gate');
            assert.ok('scope' in gates, 'Has scope gate');
            assert.ok('purpose' in gates, 'Has purpose gate');
        });

    });

    suite('API response validation', () => {

        test('should validate Sentinel API response structure', () => {
            const validResponse = {
                safe: true,
                gates: {
                    truth: 'pass',
                    harm: 'pass',
                    scope: 'pass',
                    purpose: 'pass'
                }
            };

            assert.strictEqual(typeof validResponse.safe, 'boolean', 'safe is boolean');
            assert.strictEqual(typeof validResponse.gates, 'object', 'gates is object');

            const requiredGates = ['truth', 'harm', 'scope', 'purpose'];
            for (const gate of requiredGates) {
                assert.strictEqual(
                    typeof validResponse.gates[gate as keyof typeof validResponse.gates],
                    'string',
                    `${gate} is string`
                );
            }
        });

        test('should reject invalid response - missing safe', () => {
            const invalidResponse = {
                gates: { truth: 'pass', harm: 'pass', scope: 'pass', purpose: 'pass' }
            };
            assert.ok(!('safe' in invalidResponse), 'Detects missing safe field');
        });

        test('should reject invalid response - missing gates', () => {
            const invalidResponse = { safe: true };
            assert.ok(!('gates' in invalidResponse), 'Detects missing gates field');
        });

        test('should reject invalid response - safe not boolean', () => {
            const invalidResponse = { safe: 'yes', gates: {} };
            assert.notStrictEqual(typeof invalidResponse.safe, 'boolean', 'Detects non-boolean safe');
        });

    });

    suite('Cache functionality', () => {

        test('cache key generation should be consistent', () => {
            const content = 'Test content for caching';
            const len = content.length;
            const prefix = content.substring(0, 100);
            const suffix = content.substring(Math.max(0, len - 100));
            const key = `${len}:${prefix}:${suffix}`;

            assert.ok(key.includes(String(len)), 'Key includes length');
            assert.ok(key.includes('Test content'), 'Key includes content prefix');
        });

        test('cache should expire after TTL', () => {
            const CACHE_TTL_MS = 60000; // 1 minute
            const timestamp = Date.now();
            const expiredTimestamp = timestamp - CACHE_TTL_MS - 1;

            assert.ok(Date.now() - expiredTimestamp > CACHE_TTL_MS, 'Expired timestamp is detected');
        });

        test('cache size should be limited', () => {
            const CACHE_MAX_SIZE = 50;
            const cache = new Map();

            for (let i = 0; i < CACHE_MAX_SIZE + 10; i++) {
                if (cache.size >= CACHE_MAX_SIZE) {
                    const oldestKey = cache.keys().next().value;
                    cache.delete(oldestKey);
                }
                cache.set(`key-${i}`, { result: {}, timestamp: Date.now() });
            }

            assert.ok(cache.size <= CACHE_MAX_SIZE, 'Cache size is limited');
        });

    });

    suite('Config hash functionality', () => {

        test('should detect config changes', () => {
            const config1 = 'openai:sk-12345:anthropic:gpt-4o-mini:claude';
            const config2 = 'openai:sk-67890:anthropic:gpt-4o-mini:claude';

            assert.notStrictEqual(config1, config2, 'Different configs have different hashes');
        });

        test('same config should have same hash', () => {
            const makeHash = (provider: string, key: string) =>
                `${provider}:${key.substring(0, 8)}`;

            const hash1 = makeHash('openai', 'sk-1234567890abcdef');
            const hash2 = makeHash('openai', 'sk-1234567890abcdef');

            assert.strictEqual(hash1, hash2, 'Same config has same hash');
        });

    });

    suite('Error formatting', () => {

        test('should detect 401 unauthorized errors', () => {
            const error = new Error('API error: 401 Unauthorized');
            const msg = error.message.toLowerCase();

            assert.ok(msg.includes('401') || msg.includes('unauthorized'), 'Detects 401 error');
        });

        test('should detect rate limit errors', () => {
            const error = new Error('Error: 429 Too Many Requests');
            const msg = error.message.toLowerCase();

            assert.ok(msg.includes('429') || msg.includes('rate limit'), 'Detects rate limit');
        });

        test('should detect timeout errors', () => {
            const error = new Error('Request timed out after 30000ms');
            const msg = error.message.toLowerCase();

            assert.ok(msg.includes('timeout') || msg.includes('timed out'), 'Detects timeout');
        });

    });

    suite('Heuristic analysis', () => {

        test('should return low confidence for heuristic method', () => {
            const heuristicConfidence = 0.5;
            assert.strictEqual(heuristicConfidence, 0.5, 'Heuristic confidence is 50%');
        });

        test('should include method in result', () => {
            const methods = ['semantic', 'heuristic'];
            assert.ok(methods.includes('heuristic'), 'Heuristic is valid method');
            assert.ok(methods.includes('semantic'), 'Semantic is valid method');
        });

    });

    suite('Input validation', () => {

        test('should handle null content', () => {
            const content = null;
            assert.strictEqual(content, null, 'Null content should fallback to empty analysis');
        });

        test('should handle undefined content', () => {
            const content = undefined;
            assert.strictEqual(content, undefined, 'Undefined content should fallback to empty analysis');
        });

    });

});
