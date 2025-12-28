/**
 * @fileoverview Unit tests for ApprovalStore (IndexedDB persistence layer)
 *
 * Tests CRUD operations for:
 * - Approval rules
 * - Pending approvals
 * - Action history
 * - Agents
 * - MCP servers
 *
 * @author Sentinel Team
 * @license MIT
 */

import 'fake-indexeddb/auto';
import * as store from '../approval-store';
import type {
  ApprovalRule,
  PendingApproval,
  ActionHistoryEntry,
  AgentConnection,
  MCPServer,
  THSPResult,
} from '../../types';

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

// Helper to create a mock approval rule
function createMockRule(overrides: Partial<ApprovalRule> = {}): ApprovalRule {
  return {
    id: crypto.randomUUID(),
    name: 'Test Rule',
    description: 'A test rule',
    priority: 50,
    enabled: true,
    conditions: [{ field: 'riskLevel', operator: 'equals', value: 'high' }],
    action: 'require_approval',
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

// Helper to create a mock pending approval
function createMockPending(overrides: Partial<PendingApproval> = {}): PendingApproval {
  return {
    id: crypto.randomUUID(),
    source: 'agent_shield',
    action: {
      id: crypto.randomUUID(),
      agentId: crypto.randomUUID(),
      agentName: 'Test Agent',
      type: 'transfer',
      description: 'Test action',
      params: {},
      thspResult: createMockTHSPResult(),
      riskLevel: 'medium',
      timestamp: Date.now(),
      status: 'pending',
    },
    queuedAt: Date.now(),
    expiresAt: Date.now() + 300000,
    viewCount: 0,
    ...overrides,
  };
}

// Helper to create a mock history entry
function createMockHistoryEntry(
  overrides: Partial<ActionHistoryEntry> = {}
): ActionHistoryEntry {
  return {
    id: crypto.randomUUID(),
    source: 'agent_shield',
    action: {
      id: crypto.randomUUID(),
      agentId: crypto.randomUUID(),
      agentName: 'Test Agent',
      type: 'transfer',
      description: 'Test action',
      params: {},
      thspResult: createMockTHSPResult(),
      riskLevel: 'low',
      timestamp: Date.now(),
      status: 'approved',
    },
    decision: {
      action: 'approve',
      method: 'auto',
      reason: 'Low risk',
      timestamp: Date.now(),
    },
    processedAt: Date.now(),
    ...overrides,
  };
}

// Helper to create a mock agent
function createMockAgent(overrides: Partial<AgentConnection> = {}): AgentConnection {
  return {
    id: crypto.randomUUID(),
    name: 'Test Agent',
    type: 'elizaos',
    status: 'connected',
    endpoint: 'ws://localhost:3000',
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
    ...overrides,
  };
}

// Helper to create a mock MCP server
function createMockMCPServer(overrides: Partial<MCPServer> = {}): MCPServer {
  return {
    id: crypto.randomUUID(),
    name: 'Test Server',
    endpoint: 'http://localhost:8080',
    transport: 'http',
    tools: [],
    isTrusted: false,
    trustLevel: 50,
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

describe('ApprovalStore', () => {
  beforeEach(async () => {
    // Close any existing database connection and delete database
    await store.closeDatabase();
    // Delete the database to ensure clean state
    indexedDB.deleteDatabase('sentinel-guard');
  });

  afterEach(async () => {
    await store.closeDatabase();
    indexedDB.deleteDatabase('sentinel-guard');
  });

  describe('database initialization', () => {
    it('should open database successfully', async () => {
      const db = await store.getDatabase();
      expect(db).toBeDefined();
      expect(db.name).toBe('sentinel-guard');
    });

    it('should return same instance on subsequent calls', async () => {
      const db1 = await store.getDatabase();
      const db2 = await store.getDatabase();
      expect(db1).toBe(db2);
    });
  });

  describe('approval rules operations', () => {
    it('should create and retrieve a rule', async () => {
      const rule = createMockRule({ name: 'My Rule' });
      await store.createRule(rule);

      const retrieved = await store.getRule(rule.id);
      expect(retrieved).toBeDefined();
      expect(retrieved?.name).toBe('My Rule');
    });

    it('should get all rules sorted by priority', async () => {
      const rule1 = createMockRule({ priority: 10 });
      const rule2 = createMockRule({ priority: 100 });
      const rule3 = createMockRule({ priority: 50 });

      await store.createRule(rule1);
      await store.createRule(rule2);
      await store.createRule(rule3);

      const rules = await store.getAllRules();
      expect(rules.length).toBe(3);
      expect(rules[0].priority).toBe(100);
      expect(rules[1].priority).toBe(50);
      expect(rules[2].priority).toBe(10);
    });

    it('should get only enabled rules', async () => {
      const enabled = createMockRule({ enabled: true, name: 'Enabled' });
      const disabled = createMockRule({ enabled: false, name: 'Disabled' });

      await store.createRule(enabled);
      await store.createRule(disabled);

      const rules = await store.getEnabledRules();
      expect(rules.length).toBe(1);
      expect(rules[0].name).toBe('Enabled');
    });

    it('should update a rule', async () => {
      const rule = createMockRule({ name: 'Original' });
      await store.createRule(rule);

      rule.name = 'Updated';
      await store.updateRule(rule);

      const retrieved = await store.getRule(rule.id);
      expect(retrieved?.name).toBe('Updated');
    });

    it('should delete a rule', async () => {
      const rule = createMockRule();
      await store.createRule(rule);

      let retrieved = await store.getRule(rule.id);
      expect(retrieved).toBeDefined();

      await store.deleteRule(rule.id);

      retrieved = await store.getRule(rule.id);
      expect(retrieved).toBeUndefined();
    });

    it('should count rules', async () => {
      await store.createRule(createMockRule());
      await store.createRule(createMockRule());

      const count = await store.getRuleCount();
      expect(count).toBe(2);
    });
  });

  describe('pending approvals operations', () => {
    it('should add and retrieve pending approval', async () => {
      const pending = createMockPending();
      await store.addPendingApproval(pending);

      const retrieved = await store.getPendingApproval(pending.id);
      expect(retrieved).toBeDefined();
      expect(retrieved?.id).toBe(pending.id);
    });

    it('should get all pending approvals', async () => {
      const pending1 = createMockPending();
      const pending2 = createMockPending();

      await store.addPendingApproval(pending1);
      await store.addPendingApproval(pending2);

      const all = await store.getPendingApprovals();
      expect(all.length).toBe(2);
    });

    it('should get pending approvals by source', async () => {
      await store.addPendingApproval(createMockPending({ source: 'agent_shield' }));
      await store.addPendingApproval(createMockPending({ source: 'mcp_gateway' }));

      const agentOnly = await store.getPendingApprovalsBySource('agent_shield');
      expect(agentOnly.length).toBe(1);
    });

    it('should remove pending approval', async () => {
      const pending = createMockPending();
      await store.addPendingApproval(pending);

      await store.removePendingApproval(pending.id);

      const retrieved = await store.getPendingApproval(pending.id);
      expect(retrieved).toBeUndefined();
    });

    it('should get expired pending approvals', async () => {
      const expired = createMockPending({ expiresAt: Date.now() - 1000 });
      const valid = createMockPending({ expiresAt: Date.now() + 100000 });

      await store.addPendingApproval(expired);
      await store.addPendingApproval(valid);

      const expiredList = await store.getExpiredApprovals();
      expect(expiredList.length).toBe(1);
      expect(expiredList[0].id).toBe(expired.id);
    });

    it('should count pending approvals', async () => {
      await store.addPendingApproval(createMockPending());
      await store.addPendingApproval(createMockPending());

      const count = await store.getPendingCount();
      expect(count).toBe(2);
    });

    it('should clear all pending approvals', async () => {
      await store.addPendingApproval(createMockPending());
      await store.addPendingApproval(createMockPending());

      await store.clearPendingApprovals();

      const count = await store.getPendingCount();
      expect(count).toBe(0);
    });
  });

  describe('action history operations', () => {
    it('should add and retrieve history entry', async () => {
      const entry = createMockHistoryEntry();
      await store.addHistoryEntry(entry);

      const history = await store.getActionHistory();
      expect(history.length).toBe(1);
      expect(history[0].id).toBe(entry.id);
    });

    it('should get history with pagination', async () => {
      // Create 5 entries
      for (let i = 0; i < 5; i++) {
        await store.addHistoryEntry(
          createMockHistoryEntry({ processedAt: Date.now() + i * 1000 })
        );
      }

      const page1 = await store.getActionHistory(2, 0);
      expect(page1.length).toBe(2);

      const page2 = await store.getActionHistory(2, 2);
      expect(page2.length).toBe(2);
    });

    it('should get history by source', async () => {
      await store.addHistoryEntry(createMockHistoryEntry({ source: 'agent_shield' }));
      await store.addHistoryEntry(createMockHistoryEntry({ source: 'mcp_gateway' }));

      const agentOnly = await store.getActionHistoryBySource('agent_shield');
      expect(agentOnly.length).toBe(1);
    });

    it('should count history entries', async () => {
      await store.addHistoryEntry(createMockHistoryEntry());
      await store.addHistoryEntry(createMockHistoryEntry());

      const count = await store.getHistoryCount();
      expect(count).toBe(2);
    });

    it('should clear action history', async () => {
      await store.addHistoryEntry(createMockHistoryEntry());
      await store.addHistoryEntry(createMockHistoryEntry());

      await store.clearActionHistory();

      const count = await store.getHistoryCount();
      expect(count).toBe(0);
    });

    it('should prune old history entries', async () => {
      // Create 10 entries
      for (let i = 0; i < 10; i++) {
        await store.addHistoryEntry(
          createMockHistoryEntry({ processedAt: Date.now() + i * 1000 })
        );
      }

      // Prune to keep only 5
      const pruned = await store.pruneHistory(5);
      expect(pruned).toBe(5);

      const count = await store.getHistoryCount();
      expect(count).toBe(5);
    });
  });

  describe('agent operations', () => {
    it('should save and retrieve agent', async () => {
      const agent = createMockAgent({ name: 'My Agent' });
      await store.saveAgent(agent);

      const retrieved = await store.getAgent(agent.id);
      expect(retrieved).toBeDefined();
      expect(retrieved?.name).toBe('My Agent');
    });

    it('should get all agents', async () => {
      await store.saveAgent(createMockAgent());
      await store.saveAgent(createMockAgent());

      const agents = await store.getAgents();
      expect(agents.length).toBe(2);
    });

    it('should update agent', async () => {
      const agent = createMockAgent({ name: 'Original' });
      await store.saveAgent(agent);

      agent.name = 'Updated';
      await store.saveAgent(agent);

      const retrieved = await store.getAgent(agent.id);
      expect(retrieved?.name).toBe('Updated');
    });

    it('should delete agent', async () => {
      const agent = createMockAgent();
      await store.saveAgent(agent);

      await store.deleteAgent(agent.id);

      const retrieved = await store.getAgent(agent.id);
      expect(retrieved).toBeUndefined();
    });
  });

  describe('MCP server operations', () => {
    it('should save and retrieve MCP server', async () => {
      const server = createMockMCPServer({ name: 'My Server' });
      await store.saveMCPServer(server);

      const retrieved = await store.getMCPServer(server.id);
      expect(retrieved).toBeDefined();
      expect(retrieved?.name).toBe('My Server');
    });

    it('should get all MCP servers', async () => {
      await store.saveMCPServer(createMockMCPServer());
      await store.saveMCPServer(createMockMCPServer());

      const servers = await store.getMCPServers();
      expect(servers.length).toBe(2);
    });

    it('should update MCP server', async () => {
      const server = createMockMCPServer({ name: 'Original' });
      await store.saveMCPServer(server);

      server.name = 'Updated';
      await store.saveMCPServer(server);

      const retrieved = await store.getMCPServer(server.id);
      expect(retrieved?.name).toBe('Updated');
    });

    it('should delete MCP server', async () => {
      const server = createMockMCPServer();
      await store.saveMCPServer(server);

      await store.deleteMCPServer(server.id);

      const retrieved = await store.getMCPServer(server.id);
      expect(retrieved).toBeUndefined();
    });
  });
});
