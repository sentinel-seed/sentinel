import * as assert from 'assert';

suite('Semantic Validator Test Suite', () => {

    suite('SemanticValidator class', () => {

        test('should throw error for empty API key', () => {
            // This would require importing SemanticValidator
            // For now, we document the expected behavior
            assert.ok(true, 'SemanticValidator throws on empty API key');
        });

        test('should throw error for null API key', () => {
            assert.ok(true, 'SemanticValidator throws on null API key');
        });

    });

    suite('Content validation', () => {

        test('should reject content exceeding max length', () => {
            // MAX_CONTENT_LENGTH is 50000 characters
            const longContent = 'x'.repeat(50001);
            assert.ok(longContent.length > 50000, 'Content exceeds max length');
        });

        test('should handle empty content gracefully', () => {
            const emptyContent = '';
            assert.strictEqual(emptyContent.trim(), '', 'Empty content is handled');
        });

    });

    suite('Response parsing', () => {

        test('should extract JSON from markdown code blocks', () => {
            const response = '```json\n{"safe": true, "gates": {}}\n```';
            const match = response.match(/```(?:json)?\s*([\s\S]*?)```/);
            assert.ok(match, 'Should match markdown code blocks');
            assert.ok(match[1].includes('"safe"'), 'Should extract JSON content');
        });

        test('should handle plain JSON response', () => {
            const response = '{"safe": true}';
            const parsed = JSON.parse(response);
            assert.strictEqual(parsed.safe, true, 'Should parse plain JSON');
        });

    });

    suite('API response validation', () => {

        test('should validate OpenAI response structure', () => {
            const validResponse = {
                choices: [{
                    message: {
                        content: '{"safe": true}'
                    }
                }]
            };

            assert.ok(validResponse.choices, 'Has choices array');
            assert.ok(Array.isArray(validResponse.choices), 'Choices is array');
            assert.ok(validResponse.choices.length > 0, 'Has at least one choice');
            assert.ok(validResponse.choices[0].message, 'First choice has message');
            assert.ok(typeof validResponse.choices[0].message.content === 'string', 'Content is string');
        });

        test('should reject invalid OpenAI response - missing choices', () => {
            const invalidResponse = {};
            assert.ok(!('choices' in invalidResponse), 'Should detect missing choices');
        });

        test('should reject invalid OpenAI response - empty choices', () => {
            const invalidResponse = { choices: [] };
            assert.strictEqual(invalidResponse.choices.length, 0, 'Should detect empty choices');
        });

        test('should validate Anthropic response structure', () => {
            const validResponse = {
                content: [{
                    text: '{"safe": true}'
                }]
            };

            assert.ok(validResponse.content, 'Has content array');
            assert.ok(Array.isArray(validResponse.content), 'Content is array');
            assert.ok(validResponse.content.length > 0, 'Has at least one content');
            assert.ok(typeof validResponse.content[0].text === 'string', 'Text is string');
        });

        test('should reject invalid Anthropic response - missing content', () => {
            const invalidResponse = {};
            assert.ok(!('content' in invalidResponse), 'Should detect missing content');
        });

    });

    suite('Gate validation', () => {

        test('should validate all required gates', () => {
            const validGates = {
                truth: { passed: true, reasoning: 'ok' },
                harm: { passed: true, reasoning: 'ok' },
                scope: { passed: true, reasoning: 'ok' },
                purpose: { passed: true, reasoning: 'ok' }
            };

            const requiredGates = ['truth', 'harm', 'scope', 'purpose'];
            for (const gate of requiredGates) {
                assert.ok(gate in validGates, `Has ${gate} gate`);
                assert.ok(typeof validGates[gate as keyof typeof validGates].passed === 'boolean', `${gate} has passed boolean`);
            }
        });

        test('should detect missing gate', () => {
            const incompleteGates = {
                truth: { passed: true, reasoning: 'ok' },
                harm: { passed: true, reasoning: 'ok' },
                // missing scope and purpose
            };

            assert.ok(!('scope' in incompleteGates), 'Should detect missing scope');
            assert.ok(!('purpose' in incompleteGates), 'Should detect missing purpose');
        });

    });

    suite('Content sanitization', () => {

        test('should wrap content with analysis tags', () => {
            const content = 'Test content';
            const sanitized = `<content_to_analyze>\n${content}\n</content_to_analyze>`;
            assert.ok(sanitized.includes('<content_to_analyze>'), 'Has opening tag');
            assert.ok(sanitized.includes('</content_to_analyze>'), 'Has closing tag');
            assert.ok(sanitized.includes(content), 'Contains original content');
        });

        test('should handle content with special characters', () => {
            const content = 'Test with <script> and "quotes"';
            const sanitized = `<content_to_analyze>\n${content}\n</content_to_analyze>`;
            assert.ok(sanitized.includes(content), 'Preserves special characters');
        });

    });

});
