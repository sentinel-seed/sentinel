/**
 * @fileoverview Unit tests for approval-engine.ts
 *
 * @author Sentinel Team
 * @license MIT
 */

import * as engine from '../approval-engine';
import * as store from '../approval-store';
import type { AgentAction, ApprovalRule } from '../../types';

// Mock the store module
jest.mock('../approval-store');

const mockedStore = store as jest.Mocked<typeof store>;

// Helper to create a mock agent action
function createMockAgentAction(overrides: Partial<AgentAction> = {}): AgentAction {
  return {
    id: 'action-123',
    agentId: 'agent-456',
    agentName: 'Test Agent',
    type: 'transfer',
    description: 'Test transfer action',
    params: {},
    thspResult: {
      truth: { passed: true, score: 1, issues: [] },
      harm: { passed: true, score: 1, issues: [] },
      scope: { passed: true, score: 1, issues: [] },
      purpose: { passed: true, score: 1, issues: [] },
      overall: true,
      summary: 'All gates passed',
    },
    riskLevel: 'medium',
    timestamp: Date.now(),
    status: 'pending',
    ...overrides,
  };
}

// Helper to create a mock rule
function createMockRule(overrides: Partial<ApprovalRule> = {}): ApprovalRule {
  return {
    id: 'rule-123',
    name: 'Test Rule',
    priority: 50,
    enabled: true,
    conditions: [],
    action: 'require_approval',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

describe('approval-engine', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('evaluateAction', () => {
    it('should return default action for low risk when no rules match', async () => {
      mockedStore.getEnabledRules.mockResolvedValue([]);

      const action = createMockAgentAction({ riskLevel: 'low' });
      const result = await engine.evaluateAction({
        source: 'agent_shield',
        action,
      });

      expect(result.action).toBe('auto_approve');
      expect(result.isDefault).toBe(true);
    });

    it('should return default action for critical risk when no rules match', async () => {
      mockedStore.getEnabledRules.mockResolvedValue([]);

      const action = createMockAgentAction({ riskLevel: 'critical' });
      const result = await engine.evaluateAction({
        source: 'agent_shield',
        action,
      });

      expect(result.action).toBe('auto_reject');
      expect(result.isDefault).toBe(true);
    });

    it('should return require_approval for medium risk when no rules match', async () => {
      mockedStore.getEnabledRules.mockResolvedValue([]);

      const action = createMockAgentAction({ riskLevel: 'medium' });
      const result = await engine.evaluateAction({
        source: 'agent_shield',
        action,
      });

      expect(result.action).toBe('require_approval');
      expect(result.isDefault).toBe(true);
    });

    it('should match rule with equals condition', async () => {
      const rule = createMockRule({
        conditions: [
          { field: 'riskLevel', operator: 'equals', value: 'high' },
        ],
        action: 'auto_reject',
        reason: 'High risk not allowed',
      });
      mockedStore.getEnabledRules.mockResolvedValue([rule]);

      const action = createMockAgentAction({ riskLevel: 'high' });
      const result = await engine.evaluateAction({
        source: 'agent_shield',
        action,
      });

      expect(result.action).toBe('auto_reject');
      expect(result.matchedRule).toEqual(rule);
      expect(result.isDefault).toBe(false);
    });

    it('should evaluate rules in priority order', async () => {
      const lowPriorityRule = createMockRule({
        id: 'low-priority',
        priority: 10,
        conditions: [{ field: 'riskLevel', operator: 'equals', value: 'high' }],
        action: 'require_approval',
      });
      const highPriorityRule = createMockRule({
        id: 'high-priority',
        priority: 100,
        conditions: [{ field: 'riskLevel', operator: 'equals', value: 'high' }],
        action: 'auto_reject',
      });

      mockedStore.getEnabledRules.mockResolvedValue([
        highPriorityRule,
        lowPriorityRule,
      ]);

      const action = createMockAgentAction({ riskLevel: 'high' });
      const result = await engine.evaluateAction({
        source: 'agent_shield',
        action,
      });

      expect(result.action).toBe('auto_reject');
      expect(result.matchedRule?.id).toBe('high-priority');
    });
  });

  describe('processAction', () => {
    it('should auto-approve and add to history', async () => {
      mockedStore.getEnabledRules.mockResolvedValue([]);
      mockedStore.addHistoryEntry.mockResolvedValue({} as any);

      const action = createMockAgentAction({ riskLevel: 'low' });
      const result = await engine.processAction({
        source: 'agent_shield',
        action,
      });

      expect(result.decision?.action).toBe('approve');
      expect(result.decision?.method).toBe('auto');
      expect(result.pending).toBeNull();
      expect(mockedStore.addHistoryEntry).toHaveBeenCalled();
    });

    it('should create pending approval for manual review', async () => {
      mockedStore.getEnabledRules.mockResolvedValue([]);
      mockedStore.addPendingApproval.mockResolvedValue({} as any);

      const action = createMockAgentAction({ riskLevel: 'medium' });
      const result = await engine.processAction({
        source: 'agent_shield',
        action,
      });

      expect(result.decision).toBeNull();
      expect(result.pending).not.toBeNull();
      expect(mockedStore.addPendingApproval).toHaveBeenCalled();
    });
  });

  describe('decidePending', () => {
    it('should approve pending action', async () => {
      const pending = {
        id: 'pending-123',
        source: 'agent_shield' as const,
        action: createMockAgentAction(),
        queuedAt: Date.now(),
        viewCount: 0,
      };
      mockedStore.getPendingApproval.mockResolvedValue(pending);
      mockedStore.removePendingApproval.mockResolvedValue(true);
      mockedStore.addHistoryEntry.mockResolvedValue({} as any);

      const result = await engine.decidePending(
        'pending-123',
        'approve',
        'User approved'
      );

      expect(result?.action).toBe('approve');
      expect(result?.method).toBe('manual');
      expect(mockedStore.removePendingApproval).toHaveBeenCalledWith('pending-123');
    });

    it('should return null for non-existent pending', async () => {
      mockedStore.getPendingApproval.mockResolvedValue(undefined);

      const result = await engine.decidePending(
        'nonexistent',
        'approve',
        'Approve'
      );

      expect(result).toBeNull();
    });
  });

  describe('processExpiredApprovals', () => {
    it('should process expired approvals', async () => {
      const expired = [
        {
          id: 'expired-1',
          source: 'agent_shield' as const,
          action: createMockAgentAction(),
          queuedAt: Date.now() - 600000,
          expiresAt: Date.now() - 60000,
          viewCount: 1,
        },
      ];
      mockedStore.getExpiredApprovals.mockResolvedValue(expired);
      mockedStore.removePendingApproval.mockResolvedValue(true);
      mockedStore.addHistoryEntry.mockResolvedValue({} as any);

      const count = await engine.processExpiredApprovals();

      expect(count).toBe(1);
      expect(mockedStore.removePendingApproval).toHaveBeenCalledTimes(1);
    });

    it('should return 0 when no expired approvals', async () => {
      mockedStore.getExpiredApprovals.mockResolvedValue([]);

      const count = await engine.processExpiredApprovals();

      expect(count).toBe(0);
    });
  });

  describe('createDefaultRules', () => {
    it('should create default rules on empty store', async () => {
      mockedStore.getAllRules.mockResolvedValue([]);
      mockedStore.createRule.mockImplementation(async (rule: ApprovalRule) => rule);

      await engine.createDefaultRules();

      expect(mockedStore.createRule).toHaveBeenCalledTimes(4);
    });

    it('should not overwrite existing rules', async () => {
      mockedStore.getAllRules.mockResolvedValue([createMockRule()]);

      await engine.createDefaultRules();

      expect(mockedStore.createRule).not.toHaveBeenCalled();
    });
  });
});
