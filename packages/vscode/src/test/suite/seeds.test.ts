import * as assert from 'assert';
import { SEED_MINIMAL, SEED_STANDARD, estimateTokenCount } from '../../seeds';

suite('Seeds Test Suite', () => {

    suite('estimateTokenCount', () => {

        test('should return 0 for empty string', () => {
            const count = estimateTokenCount('');
            assert.strictEqual(count, 0, 'Empty string returns 0');
        });

        test('should return 0 for null/undefined', () => {
            // @ts-expect-error Testing invalid input
            const countNull = estimateTokenCount(null);
            // @ts-expect-error Testing invalid input
            const countUndefined = estimateTokenCount(undefined);

            assert.strictEqual(countNull, 0, 'Null returns 0');
            assert.strictEqual(countUndefined, 0, 'Undefined returns 0');
        });

        test('should return minimum 50 for short strings', () => {
            const count = estimateTokenCount('Hello');
            assert.ok(count >= 50, 'Minimum is 50');
        });

        test('should estimate based on character count', () => {
            // ~4 characters per token
            const text = 'a'.repeat(400); // Should be ~100 tokens
            const count = estimateTokenCount(text);

            // Rounded to nearest 50
            assert.ok(count >= 50 && count <= 150, 'Estimate is reasonable');
        });

        test('should round to nearest 50', () => {
            const count = estimateTokenCount('a'.repeat(200)); // ~50 tokens
            assert.strictEqual(count % 50, 0, 'Count is multiple of 50');
        });

    });

    suite('SEED_MINIMAL', () => {

        test('should contain SENTINEL header', () => {
            assert.ok(SEED_MINIMAL.includes('SENTINEL ALIGNMENT SEED'), 'Has header');
        });

        test('should contain v2.0 version', () => {
            assert.ok(SEED_MINIMAL.includes('v2.0'), 'Has version');
        });

        test('should contain MINIMAL identifier', () => {
            assert.ok(SEED_MINIMAL.includes('MINIMAL'), 'Has MINIMAL identifier');
        });

        test('should contain all four gates', () => {
            assert.ok(SEED_MINIMAL.includes('GATE 1: TRUTH'), 'Has truth gate');
            assert.ok(SEED_MINIMAL.includes('GATE 2: HARM'), 'Has harm gate');
            assert.ok(SEED_MINIMAL.includes('GATE 3: SCOPE'), 'Has scope gate');
            assert.ok(SEED_MINIMAL.includes('GATE 4: PURPOSE'), 'Has purpose gate');
        });

        test('should contain THSP reference', () => {
            assert.ok(SEED_MINIMAL.includes('THSP'), 'Contains THSP reference');
        });

        test('should have reasonable length', () => {
            // Minimal should be shorter than standard
            assert.ok(SEED_MINIMAL.length < SEED_STANDARD.length, 'Minimal is shorter');
            assert.ok(SEED_MINIMAL.length > 500, 'Has minimum content');
        });

    });

    suite('SEED_STANDARD', () => {

        test('should contain SENTINEL header', () => {
            assert.ok(SEED_STANDARD.includes('SENTINEL ALIGNMENT SEED'), 'Has header');
        });

        test('should contain v2.0 version', () => {
            assert.ok(SEED_STANDARD.includes('v2.0'), 'Has version');
        });

        test('should contain STANDARD identifier', () => {
            assert.ok(SEED_STANDARD.includes('STANDARD'), 'Has STANDARD identifier');
        });

        test('should contain all four gates with details', () => {
            assert.ok(SEED_STANDARD.includes('GATE 1: TRUTH'), 'Has truth gate');
            assert.ok(SEED_STANDARD.includes('GATE 2: HARM'), 'Has harm gate');
            assert.ok(SEED_STANDARD.includes('GATE 3: SCOPE'), 'Has scope gate');
            assert.ok(SEED_STANDARD.includes('GATE 4: PURPOSE'), 'Has purpose gate');
        });

        test('should contain TELOS PRINCIPLE', () => {
            assert.ok(SEED_STANDARD.includes('TELOS PRINCIPLE'), 'Has TELOS principle');
        });

        test('should contain ANTI-SELF-PRESERVATION', () => {
            assert.ok(SEED_STANDARD.includes('ANTI-SELF-PRESERVATION'), 'Has anti-self-preservation');
        });

        test('should contain TEMPORAL INVARIANCE', () => {
            assert.ok(SEED_STANDARD.includes('TEMPORAL INVARIANCE'), 'Has temporal invariance');
        });

        test('should contain DECISION FLOW', () => {
            assert.ok(SEED_STANDARD.includes('DECISION FLOW'), 'Has decision flow');
        });

        test('should have more content than minimal', () => {
            assert.ok(SEED_STANDARD.length > SEED_MINIMAL.length, 'Standard is longer');
        });

    });

    suite('Seed consistency', () => {

        test('both seeds should end with closing marker', () => {
            assert.ok(SEED_MINIMAL.includes('END'), 'Minimal has END marker');
            assert.ok(SEED_STANDARD.includes('END'), 'Standard has END marker');
        });

        test('both seeds should be valid strings', () => {
            assert.strictEqual(typeof SEED_MINIMAL, 'string', 'Minimal is string');
            assert.strictEqual(typeof SEED_STANDARD, 'string', 'Standard is string');
        });

        test('seeds should not be empty', () => {
            assert.ok(SEED_MINIMAL.length > 0, 'Minimal is not empty');
            assert.ok(SEED_STANDARD.length > 0, 'Standard is not empty');
        });

    });

});
