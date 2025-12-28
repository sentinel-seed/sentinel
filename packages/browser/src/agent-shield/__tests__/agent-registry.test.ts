/**
 * @fileoverview Unit tests for Agent Registry
 *
 * Tests all agent management functionality:
 * - Registration and lifecycle
 * - Trust level management
 * - Statistics tracking
 * - Query operations
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  registerAgent,
  unregisterAgent,
  removeAgent,
  getAgentConnections,
  getConnectedAgents,
  getAgentConnection,
  getAgentByEndpoint,
  getAgentsByType,
  updateAgentStatus,
  updateLastActivity,
  updateAgentTrustLevel,
  increaseTrust,
  decreaseTrust,
  updateAgentStats,
  incrementAgentStat,
  recordApprovedAction,
  recordRejectedAction,
} from '../agent-registry';
import type { AgentConnection } from '../../types';

// Mock the approval store
jest.mock('../../approval/approval-store', () => {
  const agents = new Map<string, AgentConnection>();

  return {
    getAgents: jest.fn(() => Promise.resolve(Array.from(agents.values()))),
    getAgent: jest.fn((id: string) => Promise.resolve(agents.get(id))),
    saveAgent: jest.fn((agent: AgentConnection) => {
      agents.set(agent.id, agent);
      return Promise.resolve();
    }),
    deleteAgent: jest.fn((id: string) => {
      const existed = agents.has(id);
      agents.delete(id);
      return Promise.resolve(existed);
    }),
    // Reset function for tests
    __reset: () => agents.clear(),
    __getStore: () => agents,
  };
});

// Get reference to mock store
const mockStore = jest.requireMock('../../approval/approval-store');

describe('Agent Registry', () => {
  beforeEach(() => {
    mockStore.__reset();
    jest.clearAllMocks();
  });

  describe('registerAgent', () => {
    it('should register a new agent with default values', async () => {
      const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');

      expect(agent).toMatchObject({
        name: 'Test Agent',
        type: 'elizaos',
        endpoint: 'http://localhost:3000',
        status: 'connected',
        trustLevel: 50,
      });
      expect(agent.id).toBeDefined();
      expect(agent.connectedAt).toBeGreaterThan(0);
      expect(agent.stats.actionsTotal).toBe(0);
    });

    it('should register agent with metadata', async () => {
      const metadata = { version: '1.0.0', capabilities: ['chat', 'tools'] };
      const agent = await registerAgent('Test Agent', 'autogpt', 'http://localhost:3001', metadata);

      expect(agent.metadata).toEqual(metadata);
    });

    it('should return existing agent if endpoint already registered', async () => {
      const agent1 = await registerAgent('Agent 1', 'elizaos', 'http://localhost:3000');
      const agent2 = await registerAgent('Agent 2', 'elizaos', 'http://localhost:3000');

      expect(agent2.id).toBe(agent1.id);
      expect(agent2.status).toBe('connected');
    });

    it('should register different agents for different endpoints', async () => {
      const agent1 = await registerAgent('Agent 1', 'elizaos', 'http://localhost:3000');
      const agent2 = await registerAgent('Agent 2', 'autogpt', 'http://localhost:3001');

      expect(agent1.id).not.toBe(agent2.id);
    });
  });

  describe('unregisterAgent', () => {
    it('should mark agent as disconnected', async () => {
      const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
      const result = await unregisterAgent(agent.id);

      expect(result).toBe(true);

      const updated = await getAgentConnection(agent.id);
      expect(updated?.status).toBe('disconnected');
    });

    it('should return false for non-existent agent', async () => {
      const result = await unregisterAgent('non-existent-id');
      expect(result).toBe(false);
    });
  });

  describe('removeAgent', () => {
    it('should permanently remove agent', async () => {
      const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
      const result = await removeAgent(agent.id);

      expect(result).toBe(true);

      const removed = await getAgentConnection(agent.id);
      expect(removed).toBeUndefined();
    });

    it('should return false for non-existent agent', async () => {
      const result = await removeAgent('non-existent-id');
      expect(result).toBe(false);
    });
  });

  describe('getAgentConnections', () => {
    it('should return all agents', async () => {
      await registerAgent('Agent 1', 'elizaos', 'http://localhost:3000');
      await registerAgent('Agent 2', 'autogpt', 'http://localhost:3001');
      await registerAgent('Agent 3', 'crewai', 'http://localhost:3002');

      const agents = await getAgentConnections();
      expect(agents).toHaveLength(3);
    });

    it('should return empty array when no agents', async () => {
      const agents = await getAgentConnections();
      expect(agents).toEqual([]);
    });
  });

  describe('getConnectedAgents', () => {
    it('should return only connected agents', async () => {
      const agent1 = await registerAgent('Agent 1', 'elizaos', 'http://localhost:3000');
      await registerAgent('Agent 2', 'autogpt', 'http://localhost:3001');
      await unregisterAgent(agent1.id);

      const connected = await getConnectedAgents();
      expect(connected).toHaveLength(1);
      expect(connected[0].name).toBe('Agent 2');
    });
  });

  describe('getAgentsByType', () => {
    it('should filter agents by type', async () => {
      await registerAgent('Agent 1', 'elizaos', 'http://localhost:3000');
      await registerAgent('Agent 2', 'elizaos', 'http://localhost:3001');
      await registerAgent('Agent 3', 'autogpt', 'http://localhost:3002');

      const elizaAgents = await getAgentsByType('elizaos');
      expect(elizaAgents).toHaveLength(2);

      const autogptAgents = await getAgentsByType('autogpt');
      expect(autogptAgents).toHaveLength(1);
    });
  });

  describe('updateAgentStatus', () => {
    it('should update agent status', async () => {
      const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
      const updated = await updateAgentStatus(agent.id, 'error');

      expect(updated.status).toBe('error');
    });

    it('should throw for non-existent agent', async () => {
      await expect(updateAgentStatus('non-existent-id', 'connected')).rejects.toThrow(
        'Agent non-existent-id not found'
      );
    });
  });

  describe('updateLastActivity', () => {
    it('should update lastActivityAt timestamp', async () => {
      const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
      const originalTime = agent.lastActivityAt;

      // Wait a bit to ensure timestamp changes
      await new Promise((resolve) => setTimeout(resolve, 10));

      const updated = await updateLastActivity(agent.id);
      expect(updated.lastActivityAt).toBeGreaterThan(originalTime);
    });
  });

  describe('Trust Management', () => {
    describe('updateAgentTrustLevel', () => {
      it('should update trust level', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await updateAgentTrustLevel(agent.id, 75);

        expect(updated.trustLevel).toBe(75);
      });

      it('should clamp trust level to 0-100', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');

        const tooHigh = await updateAgentTrustLevel(agent.id, 150);
        expect(tooHigh.trustLevel).toBe(100);

        const tooLow = await updateAgentTrustLevel(agent.id, -50);
        expect(tooLow.trustLevel).toBe(0);
      });
    });

    describe('increaseTrust', () => {
      it('should increase trust by default amount', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await increaseTrust(agent.id);

        expect(updated.trustLevel).toBe(51);
      });

      it('should increase trust by custom amount', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await increaseTrust(agent.id, 10);

        expect(updated.trustLevel).toBe(60);
      });
    });

    describe('decreaseTrust', () => {
      it('should decrease trust by default amount', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await decreaseTrust(agent.id);

        expect(updated.trustLevel).toBe(45);
      });

      it('should decrease trust by custom amount', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await decreaseTrust(agent.id, 20);

        expect(updated.trustLevel).toBe(30);
      });
    });
  });

  describe('Statistics', () => {
    describe('updateAgentStats', () => {
      it('should update partial stats', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await updateAgentStats(agent.id, {
          actionsTotal: 10,
          actionsApproved: 8,
        });

        expect(updated.stats.actionsTotal).toBe(10);
        expect(updated.stats.actionsApproved).toBe(8);
        expect(updated.stats.actionsRejected).toBe(0);
      });
    });

    describe('incrementAgentStat', () => {
      it('should increment specific stat', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');

        await incrementAgentStat(agent.id, 'actionsTotal');
        await incrementAgentStat(agent.id, 'actionsTotal');
        const updated = await incrementAgentStat(agent.id, 'actionsApproved');

        expect(updated.stats.actionsTotal).toBe(2);
        expect(updated.stats.actionsApproved).toBe(1);
      });
    });

    describe('recordApprovedAction', () => {
      it('should increment approved count and increase trust', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await recordApprovedAction(agent.id);

        expect(updated.stats.actionsTotal).toBe(1);
        expect(updated.stats.actionsApproved).toBe(1);
        expect(updated.trustLevel).toBe(51);
      });
    });

    describe('recordRejectedAction', () => {
      it('should increment rejected count and decrease trust', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await recordRejectedAction(agent.id);

        expect(updated.stats.actionsTotal).toBe(1);
        expect(updated.stats.actionsRejected).toBe(1);
        expect(updated.trustLevel).toBe(45);
      });

      it('should record memory injection with higher penalty', async () => {
        const agent = await registerAgent('Test Agent', 'elizaos', 'http://localhost:3000');
        const updated = await recordRejectedAction(agent.id, true);

        expect(updated.stats.memoryInjectionAttempts).toBe(1);
        expect(updated.trustLevel).toBe(40);
      });
    });
  });
});
