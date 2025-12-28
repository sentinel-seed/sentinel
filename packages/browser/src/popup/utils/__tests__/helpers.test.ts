/**
 * @fileoverview Unit tests for UI helper functions
 *
 * @author Sentinel Team
 * @license MIT
 */

import type { AgentAction, MCPToolCall, MCPServer, THSPResult } from '../../../types';
import {
  isAgentAction,
  isMCPToolCall,
  getActionDisplayInfo,
  getAgentIcon,
  getTransportIcon,
  getRiskIcon,
  getDecisionIcon,
  getRiskBadgeStyle,
  getRiskColor,
  getToolRiskLevel,
  getServerName,
  generateId,
  combineDescribedBy,
  isActivationKey,
  handleKeyboardActivation,
} from '../helpers';

// Helper to create mock THSP result
function createMockTHSPResult(): THSPResult {
  return {
    truth: { passed: true, score: 1, issues: [] },
    harm: { passed: true, score: 1, issues: [] },
    scope: { passed: true, score: 1, issues: [] },
    purpose: { passed: true, score: 1, issues: [] },
    overall: true,
    summary: 'All gates passed',
  };
}

// Mock agent action
const mockAgentAction: AgentAction = {
  id: 'action-123',
  agentId: 'agent-456',
  agentName: 'Test Agent',
  type: 'transfer',
  description: 'Transfer funds',
  params: { amount: 100 },
  thspResult: createMockTHSPResult(),
  riskLevel: 'medium',
  timestamp: Date.now(),
  status: 'pending',
  estimatedValueUsd: 500,
};

// Mock MCP tool call
const mockMCPToolCall: MCPToolCall = {
  id: 'tool-123',
  serverId: 'server-456',
  serverName: 'Test Server',
  tool: 'read_file',
  arguments: { path: '/test' },
  source: 'claude_desktop',
  thspResult: createMockTHSPResult(),
  riskLevel: 'low',
  timestamp: Date.now(),
  status: 'pending',
};

describe('helpers utilities', () => {
  describe('type guards', () => {
    describe('isAgentAction', () => {
      it('should return true for AgentAction', () => {
        expect(isAgentAction(mockAgentAction)).toBe(true);
      });

      it('should return false for MCPToolCall', () => {
        expect(isAgentAction(mockMCPToolCall)).toBe(false);
      });
    });

    describe('isMCPToolCall', () => {
      it('should return true for MCPToolCall', () => {
        expect(isMCPToolCall(mockMCPToolCall)).toBe(true);
      });

      it('should return false for AgentAction', () => {
        expect(isMCPToolCall(mockAgentAction)).toBe(false);
      });
    });
  });

  describe('getActionDisplayInfo', () => {
    it('should extract info from AgentAction', () => {
      const info = getActionDisplayInfo(mockAgentAction);
      expect(info.type).toBe('transfer');
      expect(info.sourceName).toBe('Test Agent');
      expect(info.description).toBe('Transfer funds');
      expect(info.riskLevel).toBe('medium');
      expect(info.estimatedValueUsd).toBe(500);
    });

    it('should extract info from MCPToolCall', () => {
      const info = getActionDisplayInfo(mockMCPToolCall);
      expect(info.type).toBe('read_file');
      expect(info.sourceName).toBe('Test Server');
      expect(info.description).toBe('Tool call: read_file');
      expect(info.riskLevel).toBe('low');
      expect(info.estimatedValueUsd).toBeUndefined();
    });
  });

  describe('icon helpers', () => {
    describe('getAgentIcon', () => {
      it('should return correct icons for known types', () => {
        expect(getAgentIcon('elizaos')).toBe('🎭');
        expect(getAgentIcon('autogpt')).toBe('🤖');
        expect(getAgentIcon('langchain')).toBe('🔗');
        expect(getAgentIcon('crewai')).toBe('👥');
        expect(getAgentIcon('custom')).toBe('⚙️');
      });

      it('should return default icon for unknown type', () => {
        expect(getAgentIcon('unknown')).toBe('🤖');
      });
    });

    describe('getTransportIcon', () => {
      it('should return correct icons for known transports', () => {
        expect(getTransportIcon('http')).toBe('🌐');
        expect(getTransportIcon('websocket')).toBe('🔌');
        expect(getTransportIcon('stdio')).toBe('💻');
      });

      it('should return default icon for unknown transport', () => {
        expect(getTransportIcon('grpc')).toBe('🔧');
      });
    });

    describe('getRiskIcon', () => {
      it('should return correct icons for risk levels', () => {
        expect(getRiskIcon('low')).toBe('🟢');
        expect(getRiskIcon('medium')).toBe('🟡');
        expect(getRiskIcon('high')).toBe('🟠');
        expect(getRiskIcon('critical')).toBe('🔴');
      });

      it('should return default icon for unknown level', () => {
        expect(getRiskIcon('unknown')).toBe('⚪');
      });
    });

    describe('getDecisionIcon', () => {
      it('should return correct icons for decision methods', () => {
        expect(getDecisionIcon('auto')).toBe('🤖');
        expect(getDecisionIcon('manual')).toBe('👤');
      });
    });
  });

  describe('risk level utilities', () => {
    describe('getRiskBadgeStyle', () => {
      it('should return styles for known levels', () => {
        const lowStyle = getRiskBadgeStyle('low');
        expect(lowStyle.color).toBe('#10b981');

        const criticalStyle = getRiskBadgeStyle('critical');
        expect(criticalStyle.color).toBe('#ef4444');
      });

      it('should return empty object for unknown level', () => {
        expect(getRiskBadgeStyle('unknown')).toEqual({});
      });
    });

    describe('getRiskColor', () => {
      it('should return correct colors', () => {
        expect(getRiskColor('low')).toBe('#10b981');
        expect(getRiskColor('medium')).toBe('#f59e0b');
        expect(getRiskColor('high')).toBe('#f97316');
        expect(getRiskColor('critical')).toBe('#ef4444');
      });

      it('should return default color for unknown level', () => {
        expect(getRiskColor('unknown')).toBe('#888');
      });
    });

    describe('getToolRiskLevel', () => {
      it('should identify critical tools', () => {
        expect(getToolRiskLevel('execute_command')).toBe('critical');
        expect(getToolRiskLevel('shell')).toBe('critical');
        expect(getToolRiskLevel('run_command')).toBe('critical');
        expect(getToolRiskLevel('eval')).toBe('critical');
      });

      it('should identify high risk tools', () => {
        expect(getToolRiskLevel('write_file')).toBe('high');
        expect(getToolRiskLevel('delete_record')).toBe('high');
        expect(getToolRiskLevel('remove_user')).toBe('high');
        expect(getToolRiskLevel('update_config')).toBe('high');
      });

      it('should identify medium risk tools', () => {
        expect(getToolRiskLevel('read_file')).toBe('medium');
        expect(getToolRiskLevel('get_user')).toBe('medium');
        expect(getToolRiskLevel('fetch_data')).toBe('medium');
        expect(getToolRiskLevel('download_file')).toBe('medium');
      });

      it('should return low for safe tools', () => {
        expect(getToolRiskLevel('list_files')).toBe('low');
        expect(getToolRiskLevel('search')).toBe('low');
        expect(getToolRiskLevel('info')).toBe('low');
      });
    });
  });

  describe('server helpers', () => {
    describe('getServerName', () => {
      const servers: MCPServer[] = [
        {
          id: 'server-1',
          name: 'File Server',
          endpoint: 'http://localhost:8080',
          transport: 'http',
          tools: [],
          isTrusted: true,
          trustLevel: 100,
          registeredAt: Date.now(),
          lastActivityAt: Date.now(),
          stats: {
            toolCallsTotal: 0,
            toolCallsApproved: 0,
            toolCallsRejected: 0,
            toolCallsPending: 0,
          },
        },
      ];

      it('should return server name for known ID', () => {
        expect(getServerName(servers, 'server-1')).toBe('File Server');
      });

      it('should return ID for unknown server', () => {
        expect(getServerName(servers, 'unknown-id')).toBe('unknown-id');
      });
    });
  });

  describe('accessibility helpers', () => {
    describe('generateId', () => {
      it('should generate unique IDs with prefix', () => {
        const id1 = generateId('btn');
        const id2 = generateId('btn');
        expect(id1).toMatch(/^btn-/);
        expect(id2).toMatch(/^btn-/);
        expect(id1).not.toBe(id2);
      });
    });

    describe('combineDescribedBy', () => {
      it('should combine valid IDs', () => {
        const result = combineDescribedBy('id1', 'id2', 'id3');
        expect(result).toBe('id1 id2 id3');
      });

      it('should filter undefined values', () => {
        const result = combineDescribedBy('id1', undefined, 'id3');
        expect(result).toBe('id1 id3');
      });

      it('should return undefined for no valid IDs', () => {
        expect(combineDescribedBy(undefined, undefined)).toBeUndefined();
      });
    });
  });

  describe('keyboard helpers', () => {
    describe('isActivationKey', () => {
      it('should return true for Enter', () => {
        const event = { key: 'Enter' } as React.KeyboardEvent;
        expect(isActivationKey(event)).toBe(true);
      });

      it('should return true for Space', () => {
        const event = { key: ' ' } as React.KeyboardEvent;
        expect(isActivationKey(event)).toBe(true);
      });

      it('should return false for other keys', () => {
        const event = { key: 'Tab' } as React.KeyboardEvent;
        expect(isActivationKey(event)).toBe(false);
      });
    });

    describe('handleKeyboardActivation', () => {
      it('should call handler for activation keys', () => {
        const handler = jest.fn();
        const event = {
          key: 'Enter',
          preventDefault: jest.fn(),
        } as unknown as React.KeyboardEvent;

        handleKeyboardActivation(event, handler);

        expect(handler).toHaveBeenCalled();
        expect(event.preventDefault).toHaveBeenCalled();
      });

      it('should not call handler for other keys', () => {
        const handler = jest.fn();
        const event = {
          key: 'Tab',
          preventDefault: jest.fn(),
        } as unknown as React.KeyboardEvent;

        handleKeyboardActivation(event, handler);

        expect(handler).not.toHaveBeenCalled();
        expect(event.preventDefault).not.toHaveBeenCalled();
      });
    });
  });
});
