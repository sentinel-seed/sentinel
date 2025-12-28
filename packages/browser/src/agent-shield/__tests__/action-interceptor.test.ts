/**
 * @fileoverview Unit tests for Action Interceptor
 *
 * Tests action interception functionality:
 * - Risk calculation
 * - Action creation
 * - Interception and approval routing
 * - Batch operations
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  calculateRiskLevel,
  createAgentAction,
  interceptAction,
  interceptBatch,
} from '../action-interceptor';
import type { AgentConnection, MemoryContext, MemorySuspicion } from '../../types';

// Helper to create mock suspicion
function createMockSuspicion(content: string): MemorySuspicion {
  return {
    content,
    reason: 'Test suspicion',
    addedAt: Date.now(),
    confidence: 90,
  };
}

// Mock dependencies
jest.mock('../../lib/thsp', () => ({
  validateTHSP: jest.fn(() => ({
    truth: { passed: true, score: 100, issues: [] },
    harm: { passed: true, score: 100, issues: [] },
    scope: { passed: true, score: 100, issues: [] },
    purpose: { passed: true, score: 100, issues: [] },
    overall: true,
    summary: 'All checks passed',
  })),
}));

jest.mock('../../approval/approval-engine', () => ({
  processAction: jest.fn(() =>
    Promise.resolve({
      decision: {
        action: 'approve',
        method: 'auto',
        reason: 'Auto-approved by rule',
        timestamp: Date.now(),
      },
    })
  ),
}));

jest.mock('../../approval/approval-queue', () => ({
  updateBadge: jest.fn(() => Promise.resolve()),
  showApprovalNotification: jest.fn(() => Promise.resolve()),
}));

jest.mock('../memory-scanner', () => ({
  scanMemory: jest.fn(() =>
    Promise.resolve({
      hash: 'mock-hash',
      entryCount: 0,
      isCompromised: false,
      suspiciousEntries: [],
    })
  ),
}));

const mockAgent: AgentConnection = {
  id: 'agent-1',
  name: 'Test Agent',
  type: 'elizaos',
  endpoint: 'http://localhost:3000',
  status: 'connected',
  trustLevel: 50,
  connectedAt: Date.now(),
  lastActivityAt: Date.now(),
  stats: {
    actionsTotal: 0,
    actionsApproved: 0,
    actionsRejected: 0,
    actionsPending: 0,
    memoryInjectionAttempts: 0,
  },
};

jest.mock('../agent-registry', () => ({
  getAgentConnection: jest.fn(() => Promise.resolve(mockAgent)),
  incrementAgentStat: jest.fn(() => Promise.resolve(mockAgent)),
  recordApprovedAction: jest.fn(() => Promise.resolve(mockAgent)),
  recordRejectedAction: jest.fn(() => Promise.resolve(mockAgent)),
}));

const mockRegistry = jest.requireMock('../agent-registry');
const mockApprovalEngine = jest.requireMock('../../approval/approval-engine');
const mockApprovalQueue = jest.requireMock('../../approval/approval-queue');
const mockMemoryScanner = jest.requireMock('../memory-scanner');

describe('Action Interceptor', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockRegistry.getAgentConnection.mockResolvedValue(mockAgent);
  });

  describe('calculateRiskLevel', () => {
    const createAgent = (trustLevel: number): AgentConnection => ({
      ...mockAgent,
      trustLevel,
    });

    it('should return low risk for safe actions with trusted agent', () => {
      const agent = createAgent(90);
      const risk = calculateRiskLevel({ type: 'message' }, agent);

      expect(risk).toBe('low');
    });

    it('should return high risk for dangerous action types', () => {
      const agent = createAgent(50);
      const risk = calculateRiskLevel({ type: 'deploy' }, agent);

      // deploy has base risk 85, which is critical threshold
      expect(['high', 'critical']).toContain(risk);
    });

    it('should return critical for high-value transactions', () => {
      const agent = createAgent(30);
      const risk = calculateRiskLevel(
        { type: 'transfer', estimatedValueUsd: 5000 },
        agent
      );

      expect(risk).toBe('critical');
    });

    it('should increase risk for low trust agents', () => {
      const lowTrust = createAgent(10);
      const highTrust = createAgent(90);

      const lowTrustRisk = calculateRiskLevel({ type: 'swap' }, lowTrust);
      const highTrustRisk = calculateRiskLevel({ type: 'swap' }, highTrust);

      expect(['high', 'critical']).toContain(lowTrustRisk);
      expect(['low', 'medium']).toContain(highTrustRisk);
    });

    it('should significantly increase risk for compromised memory', () => {
      const agent = createAgent(80);
      const memoryContext: MemoryContext = {
        hash: 'test-hash',
        entryCount: 1,
        isCompromised: true,
        suspiciousEntries: [createMockSuspicion('malicious entry')],
      };

      const risk = calculateRiskLevel({ type: 'message' }, agent, memoryContext);
      const riskWithoutMemory = calculateRiskLevel({ type: 'message' }, agent);

      // Compromised memory should increase risk significantly
      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(risk)).toBeGreaterThan(riskOrder.indexOf(riskWithoutMemory));
    });

    it('should add risk for suspicious memory entries', () => {
      const agent = createAgent(70);
      const memoryContext: MemoryContext = {
        hash: 'test-hash',
        entryCount: 3,
        isCompromised: false,
        suspiciousEntries: [
          createMockSuspicion('entry1'),
          createMockSuspicion('entry2'),
          createMockSuspicion('entry3'),
        ],
      };

      const riskWithSuspicious = calculateRiskLevel({ type: 'message' }, agent, memoryContext);
      const riskWithoutSuspicious = calculateRiskLevel({ type: 'message' }, agent);

      // The one with suspicious entries should have higher risk
      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(riskWithSuspicious)).toBeGreaterThanOrEqual(
        riskOrder.indexOf(riskWithoutSuspicious)
      );
    });

    it('should handle various action types', () => {
      const agent = createAgent(50);

      const messageRisk = calculateRiskLevel({ type: 'message' }, agent);
      const transferRisk = calculateRiskLevel({ type: 'transfer' }, agent);
      const approvalRisk = calculateRiskLevel({ type: 'approval' }, agent);
      const deployRisk = calculateRiskLevel({ type: 'deploy' }, agent);

      expect(messageRisk).toBe('low');
      expect(['high', 'critical']).toContain(transferRisk);
      expect(['high', 'critical']).toContain(approvalRisk);
      expect(['high', 'critical']).toContain(deployRisk);
    });

    it('should add risk tiers based on estimated value', () => {
      const agent = createAgent(60);

      const low = calculateRiskLevel({ type: 'transfer', estimatedValueUsd: 5 }, agent);
      const medium = calculateRiskLevel({ type: 'transfer', estimatedValueUsd: 50 }, agent);
      const high = calculateRiskLevel({ type: 'transfer', estimatedValueUsd: 500 }, agent);
      const critical = calculateRiskLevel({ type: 'transfer', estimatedValueUsd: 5000 }, agent);

      // Higher values should have higher risk
      const riskOrder = ['low', 'medium', 'high', 'critical'];
      expect(riskOrder.indexOf(critical)).toBeGreaterThanOrEqual(riskOrder.indexOf(high));
      expect(riskOrder.indexOf(high)).toBeGreaterThanOrEqual(riskOrder.indexOf(medium));
      expect(riskOrder.indexOf(medium)).toBeGreaterThanOrEqual(riskOrder.indexOf(low));
    });

    it('should default to execute type when type is missing', () => {
      const agent = createAgent(50);
      const risk = calculateRiskLevel({}, agent);

      expect(['high', 'critical']).toContain(risk);
    });
  });

  describe('createAgentAction', () => {
    it('should create an action with all required fields', async () => {
      const action = await createAgentAction(
        'agent-1',
        'transfer',
        'Transfer 100 USDC',
        { amount: 100, token: 'USDC' }
      );

      expect(action).toMatchObject({
        agentId: 'agent-1',
        agentName: 'Test Agent',
        type: 'transfer',
        description: 'Transfer 100 USDC',
        params: { amount: 100, token: 'USDC' },
        status: 'pending',
      });
      expect(action.id).toBeDefined();
      expect(action.timestamp).toBeGreaterThan(0);
      expect(action.thspResult).toBeDefined();
      expect(action.riskLevel).toBeDefined();
    });

    it('should throw error for unknown agent', async () => {
      mockRegistry.getAgentConnection.mockResolvedValueOnce(undefined);

      await expect(
        createAgentAction('unknown', 'message', 'Test', {})
      ).rejects.toThrow('Agent unknown not found');
    });

    it('should include estimated value when provided', async () => {
      const action = await createAgentAction(
        'agent-1',
        'swap',
        'Swap ETH for USDC',
        {},
        { estimatedValueUsd: 500 }
      );

      expect(action.estimatedValueUsd).toBe(500);
    });

    it('should scan memory when entries provided', async () => {
      const memoryEntries = ['entry1', 'entry2'];

      await createAgentAction('agent-1', 'execute', 'Execute task', {}, {
        memoryEntries,
      });

      expect(mockMemoryScanner.scanMemory).toHaveBeenCalledWith(memoryEntries);
    });

    it('should include memory context in action', async () => {
      const suspicion = createMockSuspicion('suspicious');
      mockMemoryScanner.scanMemory.mockResolvedValueOnce({
        hash: 'test-hash',
        entryCount: 1,
        isCompromised: false,
        suspiciousEntries: [suspicion],
      });

      const action = await createAgentAction('agent-1', 'message', 'Test', {}, {
        memoryEntries: ['entry'],
      });

      expect(action.memoryContext).toMatchObject({
        isCompromised: false,
        suspiciousEntries: [suspicion],
      });
    });
  });

  describe('interceptAction', () => {
    it('should intercept and auto-approve safe action', async () => {
      const result = await interceptAction(
        'agent-1',
        'message',
        'Send greeting',
        { message: 'Hello' }
      );

      expect(result.decision).toBe('approved');
      expect(result.action.status).toBe('approved');
      expect(mockRegistry.recordApprovedAction).toHaveBeenCalledWith('agent-1');
    });

    it('should increment action count on intercept', async () => {
      await interceptAction('agent-1', 'message', 'Test', {});

      expect(mockRegistry.incrementAgentStat).toHaveBeenCalledWith(
        'agent-1',
        'actionsTotal'
      );
    });

    it('should immediately reject compromised memory', async () => {
      mockMemoryScanner.scanMemory.mockResolvedValueOnce({
        hash: 'compromised-hash',
        entryCount: 1,
        isCompromised: true,
        suspiciousEntries: [createMockSuspicion('injection attempt')],
      });

      const result = await interceptAction(
        'agent-1',
        'execute',
        'Execute command',
        {},
        { memoryEntries: ['compromised'] }
      );

      expect(result.decision).toBe('rejected');
      expect(result.reason).toBe('Memory injection detected');
      expect(mockRegistry.recordRejectedAction).toHaveBeenCalledWith('agent-1', true);
    });

    it('should handle auto-rejection', async () => {
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: {
          action: 'reject',
          method: 'auto',
          reason: 'High risk',
          timestamp: Date.now(),
        },
      });

      const result = await interceptAction(
        'agent-1',
        'deploy',
        'Deploy contract',
        {}
      );

      expect(result.decision).toBe('rejected');
      expect(result.reason).toBe('High risk');
      expect(mockRegistry.recordRejectedAction).toHaveBeenCalledWith('agent-1', false);
    });

    it('should handle pending approval', async () => {
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: null,
        pending: {
          id: 'pending-1',
          source: 'agent_shield',
          action: {},
          queuedAt: Date.now(),
          expiresAt: Date.now() + 300000,
          viewCount: 0,
        },
      });

      const result = await interceptAction(
        'agent-1',
        'transfer',
        'Transfer funds',
        {}
      );

      expect(result.decision).toBe('pending');
      expect(result.reason).toBe('Manual approval required');
      expect(mockRegistry.incrementAgentStat).toHaveBeenCalledWith('agent-1', 'actionsPending');
      expect(mockApprovalQueue.updateBadge).toHaveBeenCalled();
    });

    it('should show notification for pending approval by default', async () => {
      const pending = {
        id: 'pending-1',
        source: 'agent_shield',
        action: {},
        queuedAt: Date.now(),
        expiresAt: Date.now() + 300000,
        viewCount: 0,
      };
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: null,
        pending,
      });

      await interceptAction('agent-1', 'transfer', 'Transfer', {});

      expect(mockApprovalQueue.showApprovalNotification).toHaveBeenCalledWith(
        pending,
        { show: true }
      );
    });

    it('should not show notification when disabled', async () => {
      mockApprovalEngine.processAction.mockResolvedValueOnce({
        decision: null,
        pending: {
          id: 'pending-1',
          source: 'agent_shield',
          action: {},
          queuedAt: Date.now(),
          expiresAt: Date.now() + 300000,
          viewCount: 0,
        },
      });

      await interceptAction('agent-1', 'transfer', 'Transfer', {}, {
        showNotification: false,
      });

      expect(mockApprovalQueue.showApprovalNotification).not.toHaveBeenCalled();
    });

    it('should pass custom timeout to approval engine', async () => {
      await interceptAction('agent-1', 'message', 'Test', {}, {
        autoRejectTimeoutMs: 60000,
      });

      expect(mockApprovalEngine.processAction).toHaveBeenCalledWith(
        expect.anything(),
        60000
      );
    });
  });

  describe('interceptBatch', () => {
    it('should process multiple actions', async () => {
      const actions = [
        { type: 'message' as const, description: 'Message 1', params: {} },
        { type: 'message' as const, description: 'Message 2', params: {} },
        { type: 'transfer' as const, description: 'Transfer', params: {} },
      ];

      const results = await interceptBatch('agent-1', actions);

      expect(results).toHaveLength(3);
      expect(mockRegistry.incrementAgentStat).toHaveBeenCalledTimes(3);
    });

    it('should update badge once after batch', async () => {
      const actions = [
        { type: 'message' as const, description: 'Message 1', params: {} },
        { type: 'message' as const, description: 'Message 2', params: {} },
      ];

      await interceptBatch('agent-1', actions);

      // Badge should be updated once at end, not for each action
      expect(mockApprovalQueue.updateBadge).toHaveBeenCalledTimes(1);
    });

    it('should process actions with estimated values', async () => {
      const actions = [
        { type: 'transfer' as const, description: 'Transfer 1', params: {}, estimatedValueUsd: 100 },
        { type: 'swap' as const, description: 'Swap 1', params: {}, estimatedValueUsd: 500 },
      ];

      const results = await interceptBatch('agent-1', actions);

      expect(results[0].action.estimatedValueUsd).toBe(100);
      expect(results[1].action.estimatedValueUsd).toBe(500);
    });

    it('should return empty array for empty input', async () => {
      const results = await interceptBatch('agent-1', []);

      expect(results).toEqual([]);
      expect(mockApprovalQueue.updateBadge).toHaveBeenCalledTimes(1);
    });

    it('should handle mixed approval results', async () => {
      mockApprovalEngine.processAction
        .mockResolvedValueOnce({
          decision: { action: 'approve', method: 'auto', reason: 'OK', timestamp: Date.now() },
        })
        .mockResolvedValueOnce({
          decision: { action: 'reject', method: 'auto', reason: 'Denied', timestamp: Date.now() },
        });

      const actions = [
        { type: 'message' as const, description: 'Safe', params: {} },
        { type: 'deploy' as const, description: 'Risky', params: {} },
      ];

      const results = await interceptBatch('agent-1', actions);

      expect(results[0].decision).toBe('approved');
      expect(results[1].decision).toBe('rejected');
    });
  });
});
