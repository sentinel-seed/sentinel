/**
 * @fileoverview Agent Registry - Manages agent connections
 *
 * This module handles registration and management of AI agent connections.
 * It provides:
 * - Connection registration and lifecycle management
 * - Trust level tracking
 * - Statistics aggregation
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  AgentConnection,
  AgentConnectionStats,
  AgentType,
  AgentConnectionStatus,
} from '../types';
import * as store from '../approval/approval-store';

// =============================================================================
// CONSTANTS
// =============================================================================

/** Default trust level for new agents */
const DEFAULT_TRUST_LEVEL = 50;

/** Default stats for new agents */
const DEFAULT_STATS: AgentConnectionStats = {
  actionsTotal: 0,
  actionsApproved: 0,
  actionsRejected: 0,
  actionsPending: 0,
  memoryInjectionAttempts: 0,
};

// =============================================================================
// REGISTRATION
// =============================================================================

/**
 * Registers a new agent connection.
 *
 * @param name - Human-readable name for the agent
 * @param type - Type of agent framework
 * @param endpoint - Agent endpoint URL or identifier
 * @param metadata - Optional metadata
 * @returns Promise resolving to the registered agent
 */
export async function registerAgent(
  name: string,
  type: AgentType,
  endpoint: string,
  metadata?: Record<string, unknown>
): Promise<AgentConnection> {
  // Check if agent already exists with same endpoint
  const existing = await getAgentByEndpoint(endpoint);
  if (existing) {
    // Update existing agent's status
    return updateAgentStatus(existing.id, 'connected');
  }

  const agent: AgentConnection = {
    id: crypto.randomUUID(),
    name,
    type,
    status: 'connected',
    endpoint,
    trustLevel: DEFAULT_TRUST_LEVEL,
    connectedAt: Date.now(),
    lastActivityAt: Date.now(),
    stats: { ...DEFAULT_STATS },
    metadata,
  };

  await store.saveAgent(agent);
  return agent;
}

/**
 * Unregisters an agent connection.
 *
 * @param agentId - The ID of the agent to unregister
 * @returns Promise resolving to true if unregistered, false if not found
 */
export async function unregisterAgent(agentId: string): Promise<boolean> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    return false;
  }

  // Mark as disconnected rather than deleting (preserve history)
  agent.status = 'disconnected';
  agent.lastActivityAt = Date.now();
  await store.saveAgent(agent);

  return true;
}

/**
 * Permanently removes an agent from the registry.
 *
 * @param agentId - The ID of the agent to remove
 * @returns Promise resolving to true if removed, false if not found
 */
export async function removeAgent(agentId: string): Promise<boolean> {
  return store.deleteAgent(agentId);
}

// =============================================================================
// QUERIES
// =============================================================================

/**
 * Gets all registered agents.
 *
 * @returns Promise resolving to array of agent connections
 */
export async function getAgentConnections(): Promise<AgentConnection[]> {
  return store.getAgents();
}

/**
 * Gets connected agents only.
 *
 * @returns Promise resolving to array of connected agents
 */
export async function getConnectedAgents(): Promise<AgentConnection[]> {
  const agents = await store.getAgents();
  return agents.filter((a) => a.status === 'connected');
}

/**
 * Gets a single agent by ID.
 *
 * @param agentId - The agent ID
 * @returns Promise resolving to the agent or undefined
 */
export async function getAgentConnection(
  agentId: string
): Promise<AgentConnection | undefined> {
  return store.getAgent(agentId);
}

/**
 * Gets an agent by endpoint.
 *
 * @param endpoint - The endpoint to search for
 * @returns Promise resolving to the agent or undefined
 */
export async function getAgentByEndpoint(
  endpoint: string
): Promise<AgentConnection | undefined> {
  const agents = await store.getAgents();
  return agents.find((a) => a.endpoint === endpoint);
}

/**
 * Gets agents by type.
 *
 * @param type - The agent type to filter by
 * @returns Promise resolving to array of agents
 */
export async function getAgentsByType(
  type: AgentType
): Promise<AgentConnection[]> {
  const agents = await store.getAgents();
  return agents.filter((a) => a.type === type);
}

// =============================================================================
// STATUS MANAGEMENT
// =============================================================================

/**
 * Updates an agent's connection status.
 *
 * @param agentId - The agent ID
 * @param status - The new status
 * @returns Promise resolving to the updated agent
 */
export async function updateAgentStatus(
  agentId: string,
  status: AgentConnectionStatus
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  agent.status = status;
  agent.lastActivityAt = Date.now();

  if (status === 'connected' && agent.connectedAt === 0) {
    agent.connectedAt = Date.now();
  }

  await store.saveAgent(agent);
  return agent;
}

/**
 * Updates an agent's last activity timestamp.
 *
 * @param agentId - The agent ID
 * @returns Promise resolving to the updated agent
 */
export async function updateLastActivity(
  agentId: string
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  agent.lastActivityAt = Date.now();
  await store.saveAgent(agent);
  return agent;
}

// =============================================================================
// TRUST MANAGEMENT
// =============================================================================

/**
 * Updates an agent's trust level.
 *
 * @param agentId - The agent ID
 * @param trustLevel - The new trust level (0-100)
 * @returns Promise resolving to the updated agent
 */
export async function updateAgentTrustLevel(
  agentId: string,
  trustLevel: number
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  // Clamp trust level to 0-100
  agent.trustLevel = Math.max(0, Math.min(100, trustLevel));
  agent.lastActivityAt = Date.now();

  await store.saveAgent(agent);
  return agent;
}

/**
 * Increases an agent's trust level based on successful action.
 *
 * @param agentId - The agent ID
 * @param amount - Amount to increase (default: 1)
 * @returns Promise resolving to the updated agent
 */
export async function increaseTrust(
  agentId: string,
  amount: number = 1
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  return updateAgentTrustLevel(agentId, agent.trustLevel + amount);
}

/**
 * Decreases an agent's trust level based on problematic action.
 *
 * @param agentId - The agent ID
 * @param amount - Amount to decrease (default: 5)
 * @returns Promise resolving to the updated agent
 */
export async function decreaseTrust(
  agentId: string,
  amount: number = 5
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  return updateAgentTrustLevel(agentId, agent.trustLevel - amount);
}

// =============================================================================
// STATISTICS
// =============================================================================

/**
 * Updates an agent's statistics.
 *
 * @param agentId - The agent ID
 * @param updates - Partial stats to update
 * @returns Promise resolving to the updated agent
 */
export async function updateAgentStats(
  agentId: string,
  updates: Partial<AgentConnectionStats>
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  agent.stats = { ...agent.stats, ...updates };
  agent.lastActivityAt = Date.now();

  await store.saveAgent(agent);
  return agent;
}

/**
 * Increments an agent's action counter.
 *
 * @param agentId - The agent ID
 * @param field - The stat field to increment
 * @returns Promise resolving to the updated agent
 */
export async function incrementAgentStat(
  agentId: string,
  field: keyof AgentConnectionStats
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  agent.stats[field]++;
  agent.lastActivityAt = Date.now();

  await store.saveAgent(agent);
  return agent;
}

/**
 * Records an approved action for an agent.
 *
 * @param agentId - The agent ID
 * @returns Promise resolving to the updated agent
 */
export async function recordApprovedAction(
  agentId: string
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  agent.stats.actionsTotal++;
  agent.stats.actionsApproved++;
  agent.lastActivityAt = Date.now();

  await store.saveAgent(agent);
  return increaseTrust(agentId, 1);
}

/**
 * Records a rejected action for an agent.
 *
 * @param agentId - The agent ID
 * @param isMemoryInjection - Whether this was a memory injection attempt
 * @returns Promise resolving to the updated agent
 */
export async function recordRejectedAction(
  agentId: string,
  isMemoryInjection: boolean = false
): Promise<AgentConnection> {
  const agent = await store.getAgent(agentId);
  if (!agent) {
    throw new Error(`Agent ${agentId} not found`);
  }

  agent.stats.actionsTotal++;
  agent.stats.actionsRejected++;
  if (isMemoryInjection) {
    agent.stats.memoryInjectionAttempts++;
  }
  agent.lastActivityAt = Date.now();

  await store.saveAgent(agent);

  // Decrease trust more for memory injection
  const trustPenalty = isMemoryInjection ? 10 : 5;
  return decreaseTrust(agentId, trustPenalty);
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
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
};
