import * as assert from 'assert';
import { databaseGuard } from '../../databaseGuard';

suite('Database Guard Test Suite', () => {
    suite('SQL Injection Detection', () => {
        test('should detect DROP TABLE', () => {
            const result = databaseGuard.scan('DROP TABLE users;');
            assert.strictEqual(result.hasSqlInjection, true);
            assert.strictEqual(result.severity, 'critical');
        });

        test('should detect UNION SELECT', () => {
            const result = databaseGuard.scan("' UNION SELECT * FROM users --");
            assert.strictEqual(result.hasSqlInjection, true);
            assert.ok(result.findings.some(f => f.category === 'union_attack'));
        });

        test('should detect OR 1=1 bypass', () => {
            const result = databaseGuard.scan("admin' OR '1'='1' --");
            assert.strictEqual(result.hasSqlInjection, true);
            assert.ok(result.findings.some(f => f.category === 'authentication_bypass'));
        });

        test('should detect DELETE with always-true condition', () => {
            const result = databaseGuard.scan('DELETE FROM users WHERE 1=1;');
            assert.strictEqual(result.hasSqlInjection, true);
            assert.strictEqual(result.severity, 'critical');
        });

        test('should detect stacked queries', () => {
            const result = databaseGuard.scan("SELECT * FROM users; DROP TABLE users;");
            assert.strictEqual(result.hasSqlInjection, true);
            assert.ok(result.findings.some(f => f.category === 'stacked_queries'));
        });

        test('should detect SQL comments', () => {
            const result = databaseGuard.scan("SELECT * FROM users -- comment");
            assert.strictEqual(result.hasSqlInjection, true);
            assert.ok(result.findings.some(f => f.category === 'comment_injection'));
        });

        test('should detect information_schema access', () => {
            const result = databaseGuard.scan('SELECT * FROM information_schema.tables');
            assert.strictEqual(result.hasSqlInjection, true);
            assert.ok(result.findings.some(f => f.category === 'data_extraction'));
        });

        test('should detect xp_cmdshell', () => {
            const result = databaseGuard.scan("EXEC xp_cmdshell 'dir'");
            assert.strictEqual(result.hasSqlInjection, true);
            assert.strictEqual(result.severity, 'critical');
        });

        test('should NOT flag safe SELECT', () => {
            const result = databaseGuard.scan('SELECT name, email FROM users WHERE id = 123');
            assert.strictEqual(result.hasSqlInjection, false);
            assert.strictEqual(result.severity, 'none');
        });

        test('should NOT flag normal text', () => {
            const result = databaseGuard.scan('Hello, this is a normal prompt about databases.');
            assert.strictEqual(result.hasSqlInjection, false);
        });

        test('should handle empty string', () => {
            const result = databaseGuard.scan('');
            assert.strictEqual(result.hasSqlInjection, false);
            assert.strictEqual(result.findings.length, 0);
        });
    });

    suite('Quick Check', () => {
        test('hasSqlInjection should return true for injection', () => {
            assert.strictEqual(databaseGuard.hasSqlInjection("' OR 1=1 --"), true);
        });

        test('hasSqlInjection should return false for safe text', () => {
            assert.strictEqual(databaseGuard.hasSqlInjection('Hello world'), false);
        });
    });

    suite('Category Grouping', () => {
        test('should group findings by category', () => {
            const text = "DROP TABLE users; ' OR 1=1 --; UNION SELECT password";
            const grouped = databaseGuard.scanByCategory(text);

            assert.ok(grouped.destructive.length > 0);
            assert.ok(grouped.authentication_bypass.length > 0);
            assert.ok(grouped.union_attack.length > 0);
        });
    });
});
