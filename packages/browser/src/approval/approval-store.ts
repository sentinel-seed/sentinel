/**
 * @fileoverview Approval Store - IndexedDB persistence layer
 *
 * This module provides persistent storage for the approval system using IndexedDB.
 * It handles:
 * - Approval rules storage and retrieval
 * - Pending approvals queue management
 * - Action history persistence
 *
 * Uses the 'idb' library for a promise-based IndexedDB interface.
 *
 * @author Sentinel Team
 * @license MIT
 */

import { openDB, DBSchema, IDBPDatabase } from 'idb';
import {
  ApprovalRule,
  PendingApproval,
  ActionHistoryEntry,
  AgentConnection,
  MCPServer,
  Alert,
} from '../types';

// =============================================================================
// DATABASE SCHEMA
// =============================================================================

/** Database name */
const DB_NAME = 'sentinel-guard';

/** Current database version */
const DB_VERSION = 1;

/** IndexedDB schema definition */
interface SentinelDBSchema extends DBSchema {
  /** Approval rules store */
  approvalRules: {
    key: string;
    value: ApprovalRule;
    indexes: {
      'by-priority': number;
      'by-enabled': number;
    };
  };
  /** Pending approvals store */
  pendingApprovals: {
    key: string;
    value: PendingApproval;
    indexes: {
      'by-queued-at': number;
      'by-expires-at': number;
      'by-source': string;
    };
  };
  /** Action history store */
  actionHistory: {
    key: string;
    value: ActionHistoryEntry;
    indexes: {
      'by-processed-at': number;
      'by-source': string;
    };
  };
  /** Agent connections store */
  agents: {
    key: string;
    value: AgentConnection;
    indexes: {
      'by-status': string;
      'by-type': string;
    };
  };
  /** MCP servers store */
  mcpServers: {
    key: string;
    value: MCPServer;
    indexes: {
      'by-trusted': number;
    };
  };
  /** Alerts store */
  alerts: {
    key: string;
    value: Alert;
    indexes: {
      'by-timestamp': number;
      'by-acknowledged': number;
      'by-type': string;
    };
  };
}

// =============================================================================
// DATABASE INITIALIZATION
// =============================================================================

/** Singleton database instance */
let dbInstance: IDBPDatabase<SentinelDBSchema> | null = null;

/**
 * Opens and returns the IndexedDB database instance.
 * Creates the database and object stores if they don't exist.
 *
 * @returns Promise resolving to the database instance
 */
export async function getDatabase(): Promise<IDBPDatabase<SentinelDBSchema>> {
  if (dbInstance) {
    return dbInstance;
  }

  dbInstance = await openDB<SentinelDBSchema>(DB_NAME, DB_VERSION, {
    upgrade(db, _oldVersion, _newVersion, _transaction) {
      // Create approval rules store
      if (!db.objectStoreNames.contains('approvalRules')) {
        const rulesStore = db.createObjectStore('approvalRules', {
          keyPath: 'id',
        });
        rulesStore.createIndex('by-priority', 'priority');
        rulesStore.createIndex('by-enabled', 'enabled');
      }

      // Create pending approvals store
      if (!db.objectStoreNames.contains('pendingApprovals')) {
        const pendingStore = db.createObjectStore('pendingApprovals', {
          keyPath: 'id',
        });
        pendingStore.createIndex('by-queued-at', 'queuedAt');
        pendingStore.createIndex('by-expires-at', 'expiresAt');
        pendingStore.createIndex('by-source', 'source');
      }

      // Create action history store
      if (!db.objectStoreNames.contains('actionHistory')) {
        const historyStore = db.createObjectStore('actionHistory', {
          keyPath: 'id',
        });
        historyStore.createIndex('by-processed-at', 'processedAt');
        historyStore.createIndex('by-source', 'source');
      }

      // Create agents store
      if (!db.objectStoreNames.contains('agents')) {
        const agentsStore = db.createObjectStore('agents', {
          keyPath: 'id',
        });
        agentsStore.createIndex('by-status', 'status');
        agentsStore.createIndex('by-type', 'type');
      }

      // Create MCP servers store
      if (!db.objectStoreNames.contains('mcpServers')) {
        const mcpStore = db.createObjectStore('mcpServers', {
          keyPath: 'id',
        });
        mcpStore.createIndex('by-trusted', 'isTrusted');
      }

      // Create alerts store
      if (!db.objectStoreNames.contains('alerts')) {
        const alertsStore = db.createObjectStore('alerts', {
          keyPath: 'id',
        });
        alertsStore.createIndex('by-timestamp', 'timestamp');
        alertsStore.createIndex('by-acknowledged', 'acknowledged');
        alertsStore.createIndex('by-type', 'type');
      }
    },
    blocked() {
      console.warn('[ApprovalStore] Database upgrade blocked by other connections');
    },
    blocking() {
      console.warn('[ApprovalStore] This connection is blocking a database upgrade');
    },
    terminated() {
      console.error('[ApprovalStore] Database connection was terminated');
      dbInstance = null;
    },
  });

  return dbInstance;
}

/**
 * Closes the database connection.
 * Should be called when the extension is being unloaded.
 */
export async function closeDatabase(): Promise<void> {
  if (dbInstance) {
    dbInstance.close();
    dbInstance = null;
  }
}

// =============================================================================
// APPROVAL RULES OPERATIONS
// =============================================================================

/**
 * Retrieves all approval rules, sorted by priority (descending).
 *
 * @returns Promise resolving to array of approval rules
 */
export async function getAllRules(): Promise<ApprovalRule[]> {
  const db = await getDatabase();
  const rules = await db.getAllFromIndex('approvalRules', 'by-priority');
  // Sort by priority descending (higher priority first)
  return rules.sort((a, b) => b.priority - a.priority);
}

/**
 * Retrieves only enabled approval rules, sorted by priority (descending).
 *
 * @returns Promise resolving to array of enabled approval rules
 */
export async function getEnabledRules(): Promise<ApprovalRule[]> {
  const db = await getDatabase();
  const rules = await db.getAll('approvalRules');
  return rules
    .filter((rule) => rule.enabled)
    .sort((a, b) => b.priority - a.priority);
}

/**
 * Retrieves a single approval rule by ID.
 *
 * @param id - The rule ID
 * @returns Promise resolving to the rule or undefined if not found
 */
export async function getRule(id: string): Promise<ApprovalRule | undefined> {
  const db = await getDatabase();
  return db.get('approvalRules', id);
}

/**
 * Creates a new approval rule.
 *
 * @param rule - The rule to create
 * @returns Promise resolving to the created rule
 */
export async function createRule(rule: ApprovalRule): Promise<ApprovalRule> {
  const db = await getDatabase();
  await db.put('approvalRules', rule);
  return rule;
}

/**
 * Updates an existing approval rule.
 *
 * @param rule - The updated rule
 * @returns Promise resolving to the updated rule
 * @throws Error if the rule doesn't exist
 */
export async function updateRule(rule: ApprovalRule): Promise<ApprovalRule> {
  const db = await getDatabase();
  const existing = await db.get('approvalRules', rule.id);
  if (!existing) {
    throw new Error(`Rule with ID ${rule.id} not found`);
  }
  await db.put('approvalRules', rule);
  return rule;
}

/**
 * Deletes an approval rule.
 *
 * @param id - The ID of the rule to delete
 * @returns Promise resolving to true if deleted, false if not found
 */
export async function deleteRule(id: string): Promise<boolean> {
  const db = await getDatabase();
  const existing = await db.get('approvalRules', id);
  if (!existing) {
    return false;
  }
  await db.delete('approvalRules', id);
  return true;
}

/**
 * Gets the count of approval rules.
 *
 * @returns Promise resolving to the count
 */
export async function getRuleCount(): Promise<number> {
  const db = await getDatabase();
  return db.count('approvalRules');
}

// =============================================================================
// PENDING APPROVALS OPERATIONS
// =============================================================================

/**
 * Retrieves all pending approvals, sorted by queue time (oldest first).
 *
 * @returns Promise resolving to array of pending approvals
 */
export async function getPendingApprovals(): Promise<PendingApproval[]> {
  const db = await getDatabase();
  return db.getAllFromIndex('pendingApprovals', 'by-queued-at');
}

/**
 * Retrieves pending approvals by source.
 *
 * @param source - The source to filter by
 * @returns Promise resolving to filtered pending approvals
 */
export async function getPendingApprovalsBySource(
  source: 'agent_shield' | 'mcp_gateway'
): Promise<PendingApproval[]> {
  const db = await getDatabase();
  return db.getAllFromIndex('pendingApprovals', 'by-source', source);
}

/**
 * Retrieves a single pending approval by ID.
 *
 * @param id - The pending approval ID
 * @returns Promise resolving to the pending approval or undefined
 */
export async function getPendingApproval(
  id: string
): Promise<PendingApproval | undefined> {
  const db = await getDatabase();
  return db.get('pendingApprovals', id);
}

/**
 * Adds a new pending approval to the queue.
 *
 * @param pending - The pending approval to add
 * @returns Promise resolving to the added pending approval
 */
export async function addPendingApproval(
  pending: PendingApproval
): Promise<PendingApproval> {
  const db = await getDatabase();
  await db.put('pendingApprovals', pending);
  return pending;
}

/**
 * Removes a pending approval from the queue.
 *
 * @param id - The ID of the pending approval to remove
 * @returns Promise resolving to true if removed, false if not found
 */
export async function removePendingApproval(id: string): Promise<boolean> {
  const db = await getDatabase();
  const existing = await db.get('pendingApprovals', id);
  if (!existing) {
    return false;
  }
  await db.delete('pendingApprovals', id);
  return true;
}

/**
 * Updates the view count for a pending approval.
 *
 * @param id - The ID of the pending approval
 * @returns Promise resolving to the updated pending approval or undefined
 */
export async function incrementViewCount(
  id: string
): Promise<PendingApproval | undefined> {
  const db = await getDatabase();
  const pending = await db.get('pendingApprovals', id);
  if (!pending) {
    return undefined;
  }
  pending.viewCount++;
  await db.put('pendingApprovals', pending);
  return pending;
}

/**
 * Gets all expired pending approvals.
 *
 * @returns Promise resolving to array of expired pending approvals
 */
export async function getExpiredApprovals(): Promise<PendingApproval[]> {
  const db = await getDatabase();
  const all = await db.getAll('pendingApprovals');
  const now = Date.now();
  return all.filter((p) => p.expiresAt && p.expiresAt < now);
}

/**
 * Gets the count of pending approvals.
 *
 * @returns Promise resolving to the count
 */
export async function getPendingCount(): Promise<number> {
  const db = await getDatabase();
  return db.count('pendingApprovals');
}

/**
 * Clears all pending approvals.
 *
 * @returns Promise resolving when complete
 */
export async function clearPendingApprovals(): Promise<void> {
  const db = await getDatabase();
  await db.clear('pendingApprovals');
}

// =============================================================================
// ACTION HISTORY OPERATIONS
// =============================================================================

/**
 * Retrieves action history, sorted by processed time (newest first).
 *
 * @param limit - Maximum number of entries to return (default: 100)
 * @param offset - Number of entries to skip (default: 0)
 * @returns Promise resolving to array of history entries
 */
export async function getActionHistory(
  limit: number = 100,
  offset: number = 0
): Promise<ActionHistoryEntry[]> {
  const db = await getDatabase();
  const all = await db.getAllFromIndex('actionHistory', 'by-processed-at');
  // Sort by processed time descending (newest first)
  const sorted = all.sort((a, b) => b.processedAt - a.processedAt);
  return sorted.slice(offset, offset + limit);
}

/**
 * Retrieves action history by source.
 *
 * @param source - The source to filter by
 * @param limit - Maximum number of entries to return
 * @returns Promise resolving to filtered history entries
 */
export async function getActionHistoryBySource(
  source: 'agent_shield' | 'mcp_gateway',
  limit: number = 100
): Promise<ActionHistoryEntry[]> {
  const db = await getDatabase();
  const entries = await db.getAllFromIndex('actionHistory', 'by-source', source);
  return entries
    .sort((a, b) => b.processedAt - a.processedAt)
    .slice(0, limit);
}

/**
 * Adds an entry to the action history.
 *
 * @param entry - The history entry to add
 * @returns Promise resolving to the added entry
 */
export async function addHistoryEntry(
  entry: ActionHistoryEntry
): Promise<ActionHistoryEntry> {
  const db = await getDatabase();
  await db.put('actionHistory', entry);
  return entry;
}

/**
 * Gets the count of history entries.
 *
 * @returns Promise resolving to the count
 */
export async function getHistoryCount(): Promise<number> {
  const db = await getDatabase();
  return db.count('actionHistory');
}

/**
 * Clears all action history.
 *
 * @returns Promise resolving when complete
 */
export async function clearActionHistory(): Promise<void> {
  const db = await getDatabase();
  await db.clear('actionHistory');
}

/**
 * Prunes old history entries, keeping only the most recent ones.
 *
 * @param keepCount - Number of entries to keep (default: 1000)
 * @returns Promise resolving to the number of entries deleted
 */
export async function pruneHistory(keepCount: number = 1000): Promise<number> {
  const db = await getDatabase();
  const all = await db.getAllFromIndex('actionHistory', 'by-processed-at');

  if (all.length <= keepCount) {
    return 0;
  }

  // Sort by processed time descending and get IDs to delete
  const sorted = all.sort((a, b) => b.processedAt - a.processedAt);
  const toDelete = sorted.slice(keepCount);

  const tx = db.transaction('actionHistory', 'readwrite');
  await Promise.all([
    ...toDelete.map((entry) => tx.store.delete(entry.id)),
    tx.done,
  ]);

  return toDelete.length;
}

// =============================================================================
// AGENT OPERATIONS
// =============================================================================

/**
 * Retrieves all agent connections.
 *
 * @returns Promise resolving to array of agent connections
 */
export async function getAgents(): Promise<AgentConnection[]> {
  const db = await getDatabase();
  return db.getAll('agents');
}

/**
 * Retrieves a single agent by ID.
 *
 * @param id - The agent ID
 * @returns Promise resolving to the agent or undefined
 */
export async function getAgent(id: string): Promise<AgentConnection | undefined> {
  const db = await getDatabase();
  return db.get('agents', id);
}

/**
 * Saves an agent connection.
 *
 * @param agent - The agent to save
 * @returns Promise resolving to the saved agent
 */
export async function saveAgent(agent: AgentConnection): Promise<AgentConnection> {
  const db = await getDatabase();
  await db.put('agents', agent);
  return agent;
}

/**
 * Deletes an agent connection.
 *
 * @param id - The ID of the agent to delete
 * @returns Promise resolving to true if deleted, false if not found
 */
export async function deleteAgent(id: string): Promise<boolean> {
  const db = await getDatabase();
  const existing = await db.get('agents', id);
  if (!existing) {
    return false;
  }
  await db.delete('agents', id);
  return true;
}

// =============================================================================
// MCP SERVER OPERATIONS
// =============================================================================

/**
 * Retrieves all MCP servers.
 *
 * @returns Promise resolving to array of MCP servers
 */
export async function getMCPServers(): Promise<MCPServer[]> {
  const db = await getDatabase();
  return db.getAll('mcpServers');
}

/**
 * Retrieves a single MCP server by ID.
 *
 * @param id - The server ID
 * @returns Promise resolving to the server or undefined
 */
export async function getMCPServer(id: string): Promise<MCPServer | undefined> {
  const db = await getDatabase();
  return db.get('mcpServers', id);
}

/**
 * Saves an MCP server.
 *
 * @param server - The server to save
 * @returns Promise resolving to the saved server
 */
export async function saveMCPServer(server: MCPServer): Promise<MCPServer> {
  const db = await getDatabase();
  await db.put('mcpServers', server);
  return server;
}

/**
 * Deletes an MCP server.
 *
 * @param id - The ID of the server to delete
 * @returns Promise resolving to true if deleted, false if not found
 */
export async function deleteMCPServer(id: string): Promise<boolean> {
  const db = await getDatabase();
  const existing = await db.get('mcpServers', id);
  if (!existing) {
    return false;
  }
  await db.delete('mcpServers', id);
  return true;
}

// =============================================================================
// EXPORT ALL
// =============================================================================

export default {
  // Database
  getDatabase,
  closeDatabase,
  // Rules
  getAllRules,
  getEnabledRules,
  getRule,
  createRule,
  updateRule,
  deleteRule,
  getRuleCount,
  // Pending
  getPendingApprovals,
  getPendingApprovalsBySource,
  getPendingApproval,
  addPendingApproval,
  removePendingApproval,
  incrementViewCount,
  getExpiredApprovals,
  getPendingCount,
  clearPendingApprovals,
  // History
  getActionHistory,
  getActionHistoryBySource,
  addHistoryEntry,
  getHistoryCount,
  clearActionHistory,
  pruneHistory,
  // Agents
  getAgents,
  getAgent,
  saveAgent,
  deleteAgent,
  // MCP Servers
  getMCPServers,
  getMCPServer,
  saveMCPServer,
  deleteMCPServer,
};
