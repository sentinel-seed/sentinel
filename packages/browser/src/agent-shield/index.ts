/**
 * @fileoverview Agent Shield Module - Entry point
 *
 * This module provides protection for AI agent connections and actions.
 * It handles:
 * - Agent connection management
 * - Action interception and validation
 * - Memory injection detection
 * - Trust level management
 *
 * @author Sentinel Team
 * @license MIT
 */

// Re-export types
export type {
  AgentType,
  AgentConnectionStatus,
  AgentActionType,
  AgentConnection,
  AgentConnectionStats,
  AgentAction,
  MemoryContext,
  MemorySuspicion,
} from '../types';

// Export submodules
export * as registry from './agent-registry';
export * as interceptor from './action-interceptor';
export * as memoryScanner from './memory-scanner';

// Re-export commonly used functions
export {
  registerAgent,
  unregisterAgent,
  getAgentConnections,
  getAgentConnection,
  updateAgentStatus,
  updateAgentTrustLevel,
  updateAgentStats,
} from './agent-registry';

export {
  interceptAction,
  createAgentAction,
  calculateRiskLevel,
} from './action-interceptor';

export {
  scanMemory,
  detectInjection,
  createMemoryContext,
} from './memory-scanner';
