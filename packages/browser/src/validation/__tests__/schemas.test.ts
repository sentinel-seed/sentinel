/**
 * @fileoverview Unit tests for validation schemas
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  validate,
  validateOrThrow,
  AgentConnectPayloadSchema,
  AgentInterceptActionPayloadSchema,
  MCPRegisterServerPayloadSchema,
  MCPInterceptToolCallPayloadSchema,
  ApprovalDecidePayloadSchema,
  ApprovalCreateRulePayloadSchema,
} from '../schemas';

describe('validation schemas', () => {
  describe('validate helper', () => {
    it('should return success for valid data', () => {
      const result = validate(AgentConnectPayloadSchema, {
        name: 'Test Agent',
        type: 'elizaos',
        endpoint: 'ws://localhost:3000',
      });

      expect(result.success).toBe(true);
      expect(result.data).toBeDefined();
      expect(result.error).toBeUndefined();
    });

    it('should return error for invalid data', () => {
      const result = validate(AgentConnectPayloadSchema, {
        name: '', // Empty name
        type: 'invalid_type',
        endpoint: 'ws://localhost:3000',
      });

      expect(result.success).toBe(false);
      expect(result.data).toBeUndefined();
      expect(result.error).toContain('Validation failed');
    });
  });

  describe('validateOrThrow helper', () => {
    it('should return data for valid input', () => {
      const data = validateOrThrow(
        AgentConnectPayloadSchema,
        {
          name: 'Test Agent',
          type: 'autogpt',
          endpoint: 'http://localhost:8080',
        },
        'TEST'
      );

      expect(data.name).toBe('Test Agent');
      expect(data.type).toBe('autogpt');
    });

    it('should throw for invalid input', () => {
      expect(() => {
        validateOrThrow(
          AgentConnectPayloadSchema,
          { name: '' },
          'TEST'
        );
      }).toThrow('[TEST]');
    });
  });

  describe('AgentConnectPayloadSchema', () => {
    it('should accept valid payload', () => {
      const result = validate(AgentConnectPayloadSchema, {
        name: 'My Agent',
        type: 'elizaos',
        endpoint: 'ws://localhost:3000/agent',
        metadata: { version: '1.0.0' },
      });

      expect(result.success).toBe(true);
    });

    it('should require name', () => {
      const result = validate(AgentConnectPayloadSchema, {
        type: 'elizaos',
        endpoint: 'ws://localhost:3000',
      });

      expect(result.success).toBe(false);
    });

    it('should validate agent type enum', () => {
      const result = validate(AgentConnectPayloadSchema, {
        name: 'Agent',
        type: 'unknown_framework',
        endpoint: 'ws://localhost:3000',
      });

      expect(result.success).toBe(false);
    });

    it('should allow optional metadata', () => {
      const result = validate(AgentConnectPayloadSchema, {
        name: 'Agent',
        type: 'custom',
        endpoint: 'http://localhost',
      });

      expect(result.success).toBe(true);
    });
  });

  describe('AgentInterceptActionPayloadSchema', () => {
    it('should accept valid payload', () => {
      const result = validate(AgentInterceptActionPayloadSchema, {
        agentId: '550e8400-e29b-41d4-a716-446655440000',
        type: 'transfer',
        description: 'Send 1 ETH to user',
        params: { to: '0x1234', amount: '1000000000000000000' },
      });

      expect(result.success).toBe(true);
    });

    it('should require valid UUID for agentId', () => {
      const result = validate(AgentInterceptActionPayloadSchema, {
        agentId: 'not-a-uuid',
        type: 'transfer',
        description: 'Test',
        params: {},
      });

      expect(result.success).toBe(false);
    });

    it('should validate action type enum', () => {
      const result = validate(AgentInterceptActionPayloadSchema, {
        agentId: '550e8400-e29b-41d4-a716-446655440000',
        type: 'invalid_action',
        description: 'Test',
        params: {},
      });

      expect(result.success).toBe(false);
    });

    it('should allow optional estimatedValueUsd', () => {
      const result = validate(AgentInterceptActionPayloadSchema, {
        agentId: '550e8400-e29b-41d4-a716-446655440000',
        type: 'swap',
        description: 'Swap tokens',
        params: {},
        estimatedValueUsd: 100.50,
      });

      expect(result.success).toBe(true);
    });

    it('should reject negative estimatedValueUsd', () => {
      const result = validate(AgentInterceptActionPayloadSchema, {
        agentId: '550e8400-e29b-41d4-a716-446655440000',
        type: 'swap',
        description: 'Swap tokens',
        params: {},
        estimatedValueUsd: -50,
      });

      expect(result.success).toBe(false);
    });
  });

  describe('MCPRegisterServerPayloadSchema', () => {
    it('should accept valid payload', () => {
      const result = validate(MCPRegisterServerPayloadSchema, {
        name: 'My MCP Server',
        endpoint: 'http://localhost:8080/mcp',
        transport: 'http',
        tools: [
          { name: 'search', description: 'Search the web' },
        ],
      });

      expect(result.success).toBe(true);
    });

    it('should validate transport enum', () => {
      const result = validate(MCPRegisterServerPayloadSchema, {
        name: 'Server',
        endpoint: 'http://localhost',
        transport: 'invalid',
      });

      expect(result.success).toBe(false);
    });

    it('should allow optional isTrusted', () => {
      const result = validate(MCPRegisterServerPayloadSchema, {
        name: 'Server',
        endpoint: 'http://localhost',
        transport: 'websocket',
        isTrusted: true,
      });

      expect(result.success).toBe(true);
      expect(result.data?.isTrusted).toBe(true);
    });

    it('should validate trustLevel range', () => {
      const result = validate(MCPRegisterServerPayloadSchema, {
        name: 'Server',
        endpoint: 'http://localhost',
        transport: 'stdio',
        trustLevel: 150, // Over 100
      });

      expect(result.success).toBe(false);
    });
  });

  describe('MCPInterceptToolCallPayloadSchema', () => {
    it('should accept valid payload', () => {
      const result = validate(MCPInterceptToolCallPayloadSchema, {
        serverId: '550e8400-e29b-41d4-a716-446655440000',
        toolName: 'search',
        args: { query: 'test' },
        source: 'claude_desktop',
      });

      expect(result.success).toBe(true);
    });

    it('should validate source enum', () => {
      const result = validate(MCPInterceptToolCallPayloadSchema, {
        serverId: '550e8400-e29b-41d4-a716-446655440000',
        toolName: 'search',
        args: {},
        source: 'unknown_client',
      });

      expect(result.success).toBe(false);
    });
  });

  describe('ApprovalDecidePayloadSchema', () => {
    it('should accept valid approve payload', () => {
      const result = validate(ApprovalDecidePayloadSchema, {
        pendingId: '550e8400-e29b-41d4-a716-446655440000',
        action: 'approve',
        reason: 'Looks safe',
      });

      expect(result.success).toBe(true);
    });

    it('should accept valid reject payload', () => {
      const result = validate(ApprovalDecidePayloadSchema, {
        pendingId: '550e8400-e29b-41d4-a716-446655440000',
        action: 'reject',
        reason: 'Suspicious activity',
      });

      expect(result.success).toBe(true);
    });

    it('should accept modify with params', () => {
      const result = validate(ApprovalDecidePayloadSchema, {
        pendingId: '550e8400-e29b-41d4-a716-446655440000',
        action: 'modify',
        reason: 'Reduced amount',
        modifiedParams: { amount: 50 },
      });

      expect(result.success).toBe(true);
    });

    it('should require reason', () => {
      const result = validate(ApprovalDecidePayloadSchema, {
        pendingId: '550e8400-e29b-41d4-a716-446655440000',
        action: 'approve',
        reason: '', // Empty reason
      });

      expect(result.success).toBe(false);
    });
  });

  describe('ApprovalCreateRulePayloadSchema', () => {
    it('should accept valid rule', () => {
      const result = validate(ApprovalCreateRulePayloadSchema, {
        name: 'Block high risk',
        priority: 100,
        enabled: true,
        conditions: [
          { field: 'riskLevel', operator: 'equals', value: 'critical' },
        ],
        action: 'auto_reject',
      });

      expect(result.success).toBe(true);
    });

    it('should validate condition field enum', () => {
      const result = validate(ApprovalCreateRulePayloadSchema, {
        name: 'Test',
        priority: 50,
        enabled: true,
        conditions: [
          { field: 'invalid_field', operator: 'equals', value: 'test' },
        ],
        action: 'require_approval',
      });

      expect(result.success).toBe(false);
    });

    it('should validate condition operator enum', () => {
      const result = validate(ApprovalCreateRulePayloadSchema, {
        name: 'Test',
        priority: 50,
        enabled: true,
        conditions: [
          { field: 'riskLevel', operator: 'invalid_op', value: 'test' },
        ],
        action: 'require_approval',
      });

      expect(result.success).toBe(false);
    });

    it('should validate action enum', () => {
      const result = validate(ApprovalCreateRulePayloadSchema, {
        name: 'Test',
        priority: 50,
        enabled: true,
        conditions: [],
        action: 'invalid_action',
      });

      expect(result.success).toBe(false);
    });

    it('should validate priority range', () => {
      const result = validate(ApprovalCreateRulePayloadSchema, {
        name: 'Test',
        priority: 5000, // Over 1000
        enabled: true,
        conditions: [],
        action: 'auto_approve',
      });

      expect(result.success).toBe(false);
    });

    it('should accept array values in conditions', () => {
      const result = validate(ApprovalCreateRulePayloadSchema, {
        name: 'Test',
        priority: 50,
        enabled: true,
        conditions: [
          { field: 'riskLevel', operator: 'in', value: ['high', 'critical'] },
        ],
        action: 'auto_reject',
      });

      expect(result.success).toBe(true);
    });
  });
});
