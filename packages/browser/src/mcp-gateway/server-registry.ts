/**
 * @fileoverview Server Registry - Manages MCP server connections
 *
 * This module handles registration and management of MCP servers.
 * It provides:
 * - Server registration and lifecycle management
 * - Tool discovery and management
 * - Trust level tracking
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  MCPServer,
  MCPServerStats,
  MCPTool,
  RiskLevel,
} from '../types';
import * as store from '../approval/approval-store';

// =============================================================================
// CONSTANTS
// =============================================================================

/** Default trust level for new servers */
const DEFAULT_TRUST_LEVEL = 30;

/** Default stats for new servers */
const DEFAULT_STATS: MCPServerStats = {
  toolCallsTotal: 0,
  toolCallsApproved: 0,
  toolCallsRejected: 0,
  toolCallsPending: 0,
};

/** Known high-risk tools */
const HIGH_RISK_TOOLS = new Set([
  'execute',
  'run',
  'shell',
  'terminal',
  'bash',
  'powershell',
  'cmd',
  'eval',
  'code',
  'write_file',
  'delete_file',
  'rm',
  'remove',
  'transfer',
  'send',
  'sign',
]);

// =============================================================================
// REGISTRATION
// =============================================================================

/**
 * Registers a new MCP server.
 *
 * @param name - Server name
 * @param endpoint - Server endpoint URL
 * @param transport - Transport type
 * @param tools - Available tools
 * @param options - Additional options
 * @returns Promise resolving to the registered server
 */
export async function registerServer(
  name: string,
  endpoint: string,
  transport: 'http' | 'stdio' | 'websocket',
  tools: MCPTool[] = [],
  options: {
    description?: string;
    trustLevel?: number;
    isTrusted?: boolean;
  } = {}
): Promise<MCPServer> {
  // Check if server already exists with same endpoint
  const existing = await getServerByEndpoint(endpoint);
  if (existing) {
    // Update existing server
    existing.lastActivityAt = Date.now();
    existing.tools = tools;
    await store.saveMCPServer(existing);
    return existing;
  }

  const server: MCPServer = {
    id: crypto.randomUUID(),
    name,
    description: options.description,
    endpoint,
    transport,
    trustLevel: options.trustLevel ?? DEFAULT_TRUST_LEVEL,
    isTrusted: options.isTrusted ?? false,
    tools: tools.map((t) => ({
      ...t,
      riskLevel: t.riskLevel || calculateDefaultToolRisk(t.name),
      requiresApproval: t.requiresApproval ?? true,
    })),
    registeredAt: Date.now(),
    lastActivityAt: Date.now(),
    stats: { ...DEFAULT_STATS },
  };

  await store.saveMCPServer(server);
  return server;
}

/**
 * Unregisters an MCP server.
 *
 * @param serverId - The server ID
 * @returns Promise resolving to true if unregistered
 */
export async function unregisterServer(serverId: string): Promise<boolean> {
  return store.deleteMCPServer(serverId);
}

// =============================================================================
// QUERIES
// =============================================================================

/**
 * Gets all registered MCP servers.
 *
 * @returns Promise resolving to array of servers
 */
export async function getMCPServers(): Promise<MCPServer[]> {
  return store.getMCPServers();
}

/**
 * Gets trusted MCP servers only.
 *
 * @returns Promise resolving to array of trusted servers
 */
export async function getTrustedServers(): Promise<MCPServer[]> {
  const servers = await store.getMCPServers();
  return servers.filter((s) => s.isTrusted);
}

/**
 * Gets a single server by ID.
 *
 * @param serverId - The server ID
 * @returns Promise resolving to the server or undefined
 */
export async function getMCPServer(
  serverId: string
): Promise<MCPServer | undefined> {
  return store.getMCPServer(serverId);
}

/**
 * Gets a server by endpoint.
 *
 * @param endpoint - The endpoint to search for
 * @returns Promise resolving to the server or undefined
 */
export async function getServerByEndpoint(
  endpoint: string
): Promise<MCPServer | undefined> {
  const servers = await store.getMCPServers();
  return servers.find((s) => s.endpoint === endpoint);
}

/**
 * Gets a server by name.
 *
 * @param name - The name to search for
 * @returns Promise resolving to the server or undefined
 */
export async function getServerByName(
  name: string
): Promise<MCPServer | undefined> {
  const servers = await store.getMCPServers();
  return servers.find((s) => s.name.toLowerCase() === name.toLowerCase());
}

// =============================================================================
// TRUST MANAGEMENT
// =============================================================================

/**
 * Updates a server's trust level.
 *
 * @param serverId - The server ID
 * @param trustLevel - New trust level (0-100)
 * @returns Promise resolving to the updated server
 */
export async function updateServerTrust(
  serverId: string,
  trustLevel: number
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  server.trustLevel = Math.max(0, Math.min(100, trustLevel));
  server.lastActivityAt = Date.now();

  await store.saveMCPServer(server);
  return server;
}

/**
 * Marks a server as trusted.
 *
 * @param serverId - The server ID
 * @param trusted - Whether to trust the server
 * @returns Promise resolving to the updated server
 */
export async function setServerTrusted(
  serverId: string,
  trusted: boolean
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  server.isTrusted = trusted;
  if (trusted && server.trustLevel < 70) {
    server.trustLevel = 70;
  }
  server.lastActivityAt = Date.now();

  await store.saveMCPServer(server);
  return server;
}

/**
 * Increases a server's trust level.
 *
 * @param serverId - The server ID
 * @param amount - Amount to increase
 * @returns Promise resolving to the updated server
 */
export async function increaseTrust(
  serverId: string,
  amount: number = 1
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  return updateServerTrust(serverId, server.trustLevel + amount);
}

/**
 * Decreases a server's trust level.
 *
 * @param serverId - The server ID
 * @param amount - Amount to decrease
 * @returns Promise resolving to the updated server
 */
export async function decreaseTrust(
  serverId: string,
  amount: number = 5
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  return updateServerTrust(serverId, server.trustLevel - amount);
}

// =============================================================================
// TOOL MANAGEMENT
// =============================================================================

/**
 * Calculates default risk level for a tool based on its name.
 *
 * @param toolName - The tool name
 * @returns Default risk level
 */
function calculateDefaultToolRisk(toolName: string): RiskLevel {
  const nameLower = toolName.toLowerCase();

  if (HIGH_RISK_TOOLS.has(nameLower)) {
    return 'high';
  }

  // Check for partial matches
  for (const risky of HIGH_RISK_TOOLS) {
    if (nameLower.includes(risky)) {
      return 'high';
    }
  }

  // File operations are medium risk
  if (
    nameLower.includes('file') ||
    nameLower.includes('read') ||
    nameLower.includes('write')
  ) {
    return 'medium';
  }

  // Network operations are medium risk
  if (
    nameLower.includes('http') ||
    nameLower.includes('fetch') ||
    nameLower.includes('request')
  ) {
    return 'medium';
  }

  return 'low';
}

/**
 * Adds a tool to a server.
 *
 * @param serverId - The server ID
 * @param tool - The tool to add
 * @returns Promise resolving to the updated server
 */
export async function addServerTool(
  serverId: string,
  tool: MCPTool
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  // Check if tool already exists
  const existing = server.tools.find((t) => t.name === tool.name);
  if (existing) {
    // Update existing tool
    Object.assign(existing, tool);
  } else {
    server.tools.push({
      ...tool,
      riskLevel: tool.riskLevel || calculateDefaultToolRisk(tool.name),
      requiresApproval: tool.requiresApproval ?? true,
    });
  }

  server.lastActivityAt = Date.now();
  await store.saveMCPServer(server);
  return server;
}

/**
 * Removes a tool from a server.
 *
 * @param serverId - The server ID
 * @param toolName - The tool name
 * @returns Promise resolving to the updated server
 */
export async function removeServerTool(
  serverId: string,
  toolName: string
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  server.tools = server.tools.filter((t) => t.name !== toolName);
  server.lastActivityAt = Date.now();

  await store.saveMCPServer(server);
  return server;
}

/**
 * Gets a tool from a server.
 *
 * @param serverId - The server ID
 * @param toolName - The tool name
 * @returns Promise resolving to the tool or undefined
 */
export async function getServerTool(
  serverId: string,
  toolName: string
): Promise<MCPTool | undefined> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    return undefined;
  }

  return server.tools.find((t) => t.name === toolName);
}

/**
 * Updates a tool's risk level.
 *
 * @param serverId - The server ID
 * @param toolName - The tool name
 * @param riskLevel - New risk level
 * @returns Promise resolving to the updated server
 */
export async function updateToolRisk(
  serverId: string,
  toolName: string,
  riskLevel: RiskLevel
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  const tool = server.tools.find((t) => t.name === toolName);
  if (!tool) {
    throw new Error(`Tool ${toolName} not found on server ${serverId}`);
  }

  tool.riskLevel = riskLevel;
  server.lastActivityAt = Date.now();

  await store.saveMCPServer(server);
  return server;
}

// =============================================================================
// STATISTICS
// =============================================================================

/**
 * Records an approved tool call.
 *
 * @param serverId - The server ID
 * @returns Promise resolving to the updated server
 */
export async function recordApprovedCall(
  serverId: string
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  server.stats.toolCallsTotal++;
  server.stats.toolCallsApproved++;
  server.lastActivityAt = Date.now();

  await store.saveMCPServer(server);
  return increaseTrust(serverId, 1);
}

/**
 * Records a rejected tool call.
 *
 * @param serverId - The server ID
 * @returns Promise resolving to the updated server
 */
export async function recordRejectedCall(
  serverId: string
): Promise<MCPServer> {
  const server = await store.getMCPServer(serverId);
  if (!server) {
    throw new Error(`Server ${serverId} not found`);
  }

  server.stats.toolCallsTotal++;
  server.stats.toolCallsRejected++;
  server.lastActivityAt = Date.now();

  await store.saveMCPServer(server);
  return decreaseTrust(serverId, 5);
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  registerServer,
  unregisterServer,
  getMCPServers,
  getTrustedServers,
  getMCPServer,
  getServerByEndpoint,
  getServerByName,
  updateServerTrust,
  setServerTrusted,
  increaseTrust,
  decreaseTrust,
  addServerTool,
  removeServerTool,
  getServerTool,
  updateToolRisk,
  recordApprovedCall,
  recordRejectedCall,
};
