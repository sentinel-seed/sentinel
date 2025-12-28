/**
 * @fileoverview Unit tests for Approval Queue
 *
 * Tests queue management functionality:
 * - Queue statistics
 * - Badge management
 * - Notification handling
 * - Timeout processing
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  getQueueStats,
  getHighestRiskLevel,
  updateBadge,
  clearBadge,
  showApprovalNotification,
} from '../approval-queue';
import type { PendingApproval, AgentAction, MCPToolCall } from '../../types';

// Mock chrome APIs
const mockSetBadgeText = jest.fn();
const mockSetBadgeBackgroundColor = jest.fn();
const mockCreateNotification = jest.fn();
const mockGetURL = jest.fn((path: string) => `chrome-extension://test/${path}`);

global.chrome = {
  action: {
    setBadgeText: mockSetBadgeText,
    setBadgeBackgroundColor: mockSetBadgeBackgroundColor,
  },
  notifications: {
    create: mockCreateNotification,
  },
  runtime: {
    getURL: mockGetURL,
  },
} as unknown as typeof chrome;

// Mock store
const mockPendingApprovals: PendingApproval[] = [];

jest.mock('../approval-store', () => ({
  getPendingApprovals: jest.fn(() => Promise.resolve(mockPendingApprovals)),
  getPendingCount: jest.fn(() => Promise.resolve(mockPendingApprovals.length)),
}));

// Helper to create mock THSP result
function createMockTHSPResult() {
  return {
    truth: { passed: true, score: 100, issues: [] },
    harm: { passed: true, score: 100, issues: [] },
    scope: { passed: true, score: 100, issues: [] },
    purpose: { passed: true, score: 100, issues: [] },
    overall: true,
    summary: 'All checks passed',
  };
}

// Helper to create mock pending approval
function createMockPending(
  source: 'agent_shield' | 'mcp_gateway',
  riskLevel: 'low' | 'medium' | 'high' | 'critical',
  options: Partial<{ expired: boolean; queuedAt: number }> = {}
): PendingApproval {
  const now = Date.now();
  const action = source === 'agent_shield'
    ? {
        id: `action-${Math.random()}`,
        agentId: 'agent-1',
        agentName: 'Test Agent',
        type: 'execute' as const,
        description: 'Test action',
        params: {},
        thspResult: createMockTHSPResult(),
        riskLevel,
        timestamp: now,
        status: 'pending' as const,
      } as AgentAction
    : {
        id: `call-${Math.random()}`,
        serverId: 'server-1',
        serverName: 'Test Server',
        tool: 'test_tool',
        arguments: {},
        source: 'custom' as const,
        thspResult: createMockTHSPResult(),
        riskLevel,
        timestamp: now,
        status: 'pending' as const,
      } as MCPToolCall;

  return {
    id: `pending-${Math.random()}`,
    source,
    action,
    queuedAt: options.queuedAt ?? now,
    expiresAt: options.expired ? now - 1000 : now + 300000,
    viewCount: 0,
  };
}

describe('Approval Queue', () => {
  beforeEach(() => {
    mockPendingApprovals.length = 0;
    jest.clearAllMocks();
    mockCreateNotification.mockImplementation((_id, _opts, callback) => {
      callback?.('notification-id');
    });
  });

  describe('getQueueStats', () => {
    it('should return empty stats when queue is empty', async () => {
      const stats = await getQueueStats();

      expect(stats).toEqual({
        total: 0,
        agentShield: 0,
        mcpGateway: 0,
        byRiskLevel: {
          low: 0,
          medium: 0,
          high: 0,
          critical: 0,
        },
        oldestTimestamp: null,
        expired: 0,
      });
    });

    it('should count items by source', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low'),
        createMockPending('agent_shield', 'medium'),
        createMockPending('mcp_gateway', 'high')
      );

      const stats = await getQueueStats();

      expect(stats.total).toBe(3);
      expect(stats.agentShield).toBe(2);
      expect(stats.mcpGateway).toBe(1);
    });

    it('should count items by risk level', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low'),
        createMockPending('agent_shield', 'medium'),
        createMockPending('mcp_gateway', 'high'),
        createMockPending('mcp_gateway', 'critical')
      );

      const stats = await getQueueStats();

      expect(stats.byRiskLevel).toEqual({
        low: 1,
        medium: 1,
        high: 1,
        critical: 1,
      });
    });

    it('should track oldest timestamp', async () => {
      const oldTime = Date.now() - 60000;
      const newTime = Date.now();

      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low', { queuedAt: newTime }),
        createMockPending('agent_shield', 'medium', { queuedAt: oldTime })
      );

      const stats = await getQueueStats();

      expect(stats.oldestTimestamp).toBe(oldTime);
    });

    it('should count expired items', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low', { expired: true }),
        createMockPending('agent_shield', 'medium', { expired: false }),
        createMockPending('mcp_gateway', 'high', { expired: true })
      );

      const stats = await getQueueStats();

      expect(stats.expired).toBe(2);
    });
  });

  describe('getHighestRiskLevel', () => {
    it('should return null when queue is empty', async () => {
      const result = await getHighestRiskLevel();
      expect(result).toBeNull();
    });

    it('should return critical when present', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low'),
        createMockPending('agent_shield', 'critical'),
        createMockPending('mcp_gateway', 'medium')
      );

      const result = await getHighestRiskLevel();
      expect(result).toBe('critical');
    });

    it('should return high when no critical', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low'),
        createMockPending('mcp_gateway', 'high')
      );

      const result = await getHighestRiskLevel();
      expect(result).toBe('high');
    });

    it('should return low when only low risk items', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low'),
        createMockPending('mcp_gateway', 'low')
      );

      const result = await getHighestRiskLevel();
      expect(result).toBe('low');
    });
  });

  describe('updateBadge', () => {
    it('should clear badge when no pending items', async () => {
      await updateBadge();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '' });
    });

    it('should show count when items pending', async () => {
      mockPendingApprovals.push(
        createMockPending('agent_shield', 'low'),
        createMockPending('mcp_gateway', 'medium')
      );

      await updateBadge();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '2' });
    });

    it('should set green color for low risk', async () => {
      mockPendingApprovals.push(createMockPending('agent_shield', 'low'));

      await updateBadge();

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({ color: '#22c55e' });
    });

    it('should set yellow color for medium risk', async () => {
      mockPendingApprovals.push(createMockPending('agent_shield', 'medium'));

      await updateBadge();

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({ color: '#eab308' });
    });

    it('should set orange color for high risk', async () => {
      mockPendingApprovals.push(createMockPending('agent_shield', 'high'));

      await updateBadge();

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({ color: '#f97316' });
    });

    it('should set red color for critical risk', async () => {
      mockPendingApprovals.push(createMockPending('agent_shield', 'critical'));

      await updateBadge();

      expect(mockSetBadgeBackgroundColor).toHaveBeenCalledWith({ color: '#ef4444' });
    });
  });

  describe('clearBadge', () => {
    it('should clear badge text', async () => {
      await clearBadge();

      expect(mockSetBadgeText).toHaveBeenCalledWith({ text: '' });
    });
  });

  describe('showApprovalNotification', () => {
    it('should not show notification when disabled', async () => {
      const pending = createMockPending('agent_shield', 'low');
      const result = await showApprovalNotification(pending, { show: false });

      expect(result).toBeNull();
      expect(mockCreateNotification).not.toHaveBeenCalled();
    });

    it('should show notification for agent action', async () => {
      const pending = createMockPending('agent_shield', 'medium');
      await showApprovalNotification(pending);

      expect(mockCreateNotification).toHaveBeenCalled();
      const [, options] = mockCreateNotification.mock.calls[0];
      expect(options.title).toContain('⚠️');
      expect(options.message).toContain('Test Agent');
    });

    it('should show notification for MCP tool call', async () => {
      const pending = createMockPending('mcp_gateway', 'high');
      await showApprovalNotification(pending);

      expect(mockCreateNotification).toHaveBeenCalled();
      const [, options] = mockCreateNotification.mock.calls[0];
      expect(options.title).toContain('🔶');
      expect(options.message).toContain('Test Server');
    });

    it('should set critical priority for critical risk', async () => {
      const pending = createMockPending('agent_shield', 'critical');
      await showApprovalNotification(pending);

      const [, options] = mockCreateNotification.mock.calls[0];
      expect(options.priority).toBe(2);
      expect(options.title).toContain('🚨');
    });

    it('should use custom title and message', async () => {
      const pending = createMockPending('agent_shield', 'low');
      await showApprovalNotification(pending, {
        show: true,
        title: 'Custom Title',
        message: 'Custom Message',
      });

      const [, options] = mockCreateNotification.mock.calls[0];
      expect(options.title).toBe('Custom Title');
      expect(options.message).toBe('Custom Message');
    });

    it('should require interaction for non-low risk', async () => {
      const pending = createMockPending('agent_shield', 'high');
      await showApprovalNotification(pending);

      const [, options] = mockCreateNotification.mock.calls[0];
      expect(options.requireInteraction).toBe(true);
    });

    it('should not require interaction for low risk', async () => {
      const pending = createMockPending('agent_shield', 'low');
      await showApprovalNotification(pending);

      const [, options] = mockCreateNotification.mock.calls[0];
      expect(options.requireInteraction).toBe(false);
    });
  });
});
