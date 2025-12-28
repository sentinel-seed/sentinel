/**
 * @fileoverview MCP Gateway Module - Entry point
 *
 * This module provides protection for MCP (Model Context Protocol) tool calls.
 * It handles:
 * - MCP server registration and management
 * - Tool call interception and validation
 * - Trust level management for servers
 *
 * @author Sentinel Team
 * @license MIT
 */

// Re-export types
export type {
  MCPServer,
  MCPServerStats,
  MCPTool,
  MCPToolCall,
  MCPClientSource,
} from '../types';

// Export submodules
export * as registry from './server-registry';
export * as interceptor from './tool-interceptor';
export * as validator from './tool-validator';

// Re-export commonly used functions
export {
  registerServer,
  unregisterServer,
  getMCPServers,
  getMCPServer,
  updateServerTrust,
  addServerTool,
  removeServerTool,
} from './server-registry';

export {
  interceptToolCall,
  createToolCall,
  calculateToolRisk,
} from './tool-interceptor';

export {
  validateTool,
  isToolSafe,
  getToolRiskLevel,
} from './tool-validator';
