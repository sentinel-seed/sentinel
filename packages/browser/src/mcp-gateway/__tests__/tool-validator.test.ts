/**
 * @fileoverview Unit tests for tool-validator.ts
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  validateTool,
  isToolSafe,
  getToolRiskLevel,
  validateAgainstSchema,
} from '../tool-validator';
import type { MCPServer } from '../../types';

// Helper to create a mock server
function createMockServer(overrides: Partial<MCPServer> = {}): MCPServer {
  return {
    id: 'server-123',
    name: 'Test Server',
    endpoint: 'http://localhost:3000',
    transport: 'http',
    trustLevel: 50,
    isTrusted: false,
    tools: [],
    registeredAt: Date.now(),
    lastActivityAt: Date.now(),
    stats: {
      toolCallsTotal: 0,
      toolCallsApproved: 0,
      toolCallsRejected: 0,
      toolCallsPending: 0,
    },
    ...overrides,
  };
}

describe('tool-validator', () => {
  describe('validateTool', () => {
    describe('path traversal detection', () => {
      it('should detect ../path traversal', async () => {
        const result = await validateTool('read_file', {
          path: '../../../etc/passwd',
        });

        expect(result.safe).toBe(false);
        expect(result.reason).toContain('Path traversal');
      });

      it('should detect URL-encoded path traversal', async () => {
        const result = await validateTool('read_file', {
          path: '..%2f..%2fetc%2fpasswd',
        });

        expect(result.safe).toBe(false);
      });
    });

    describe('command injection detection', () => {
      it('should detect semicolon command injection', async () => {
        const result = await validateTool('execute', {
          command: 'ls; rm -rf /',
        });

        expect(result.safe).toBe(false);
        expect(result.reason).toContain('command injection');
      });

      it('should detect dangerous rm command', async () => {
        const result = await validateTool('shell', {
          command: 'rm -rf /',
        });

        expect(result.safe).toBe(false);
      });
    });

    describe('SQL injection detection', () => {
      it('should detect OR injection', async () => {
        const result = await validateTool('database', {
          query: "SELECT * FROM users WHERE id = '1' or '1'='1",
        });

        expect(result.safe).toBe(false);
        expect(result.reason).toContain('SQL injection');
      });
    });

    describe('sensitive path detection', () => {
      it('should detect /etc/passwd', async () => {
        const result = await validateTool('read', {
          path: '/etc/passwd',
        });

        expect(result.safe).toBe(false);
      });

      it('should detect .env file', async () => {
        const result = await validateTool('read_file', {
          path: '/app/.env',
        });

        expect(result.safe).toBe(false);
      });
    });

    describe('sensitive data warnings', () => {
      it('should warn about API keys', async () => {
        const result = await validateTool('send_request', {
          headers: 'api_key: sk_test_abcdefghijklmnopqrstuvwxyz',
        });

        expect(result.safe).toBe(true);
        expect(result.warnings.length).toBeGreaterThan(0);
      });
    });

    describe('server trust adjustment', () => {
      it('should increase risk for untrusted server', async () => {
        const server = createMockServer({ isTrusted: false, trustLevel: 50 });
        const result = await validateTool('safe_tool', { data: 'test' }, server);

        expect(result.riskLevel).toBe('medium');
      });

      it('should keep low risk for trusted server', async () => {
        const server = createMockServer({ isTrusted: true, trustLevel: 80 });
        const result = await validateTool('safe_tool', { data: 'test' }, server);

        expect(result.riskLevel).toBe('low');
      });
    });

    describe('safe arguments', () => {
      it('should pass normal text arguments', async () => {
        const result = await validateTool('search', {
          query: 'hello world',
        });

        expect(result.safe).toBe(true);
        expect(result.warnings.length).toBe(0);
      });
    });
  });

  describe('isToolSafe', () => {
    it('should return true for safe tools', async () => {
      const result = await isToolSafe('search', { query: 'test' });
      expect(result).toBe(true);
    });

    it('should return false for unsafe tools', async () => {
      const result = await isToolSafe('read', { path: '../../../etc/passwd' });
      expect(result).toBe(false);
    });
  });

  describe('getToolRiskLevel', () => {
    it('should mark execute as critical', () => {
      expect(getToolRiskLevel('execute')).toBe('critical');
    });

    it('should mark shell as critical', () => {
      expect(getToolRiskLevel('shell')).toBe('critical');
    });

    it('should mark write as high', () => {
      expect(getToolRiskLevel('write')).toBe('high');
    });

    it('should mark delete as high', () => {
      expect(getToolRiskLevel('delete')).toBe('high');
    });

    it('should mark read as medium', () => {
      expect(getToolRiskLevel('read')).toBe('medium');
    });

    it('should mark get_info as low', () => {
      expect(getToolRiskLevel('get_info')).toBe('low');
    });
  });

  describe('validateAgainstSchema', () => {
    it('should validate required properties', () => {
      const schema = {
        required: ['name', 'age'],
        properties: {
          name: { type: 'string' },
          age: { type: 'number' },
        },
      };

      const result = validateAgainstSchema({ name: 'John' }, schema);

      expect(result.valid).toBe(false);
      expect(result.errors).toContain('Missing required argument: age');
    });

    it('should pass valid arguments', () => {
      const schema = {
        required: ['name'],
        properties: {
          name: { type: 'string' },
        },
      };

      const result = validateAgainstSchema({ name: 'John' }, schema);

      expect(result.valid).toBe(true);
    });
  });
});
