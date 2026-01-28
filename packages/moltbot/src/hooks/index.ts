/**
 * @sentinelseed/moltbot - Hooks Module
 *
 * This module provides Moltbot hook implementations for
 * integrating Sentinel safety monitoring.
 *
 * Architecture:
 * - types.ts: All type definitions (events, results, session state)
 * - handlers.ts: Pure function implementations (Phase 2)
 * - seeds.ts: Seed template generator (Phase 2)
 * - index.ts: Factory function and exports (this file)
 *
 * @example
 * ```typescript
 * import { createSentinelHooks } from '@sentinelseed/moltbot/hooks';
 *
 * const hooks = createSentinelHooks({ level: 'guard' });
 * // Register hooks with Moltbot
 * ```
 *
 * @module hooks
 */

import type { SentinelMoltbotConfig, LevelConfig } from '../types';
import { parseConfig, getLevelConfig } from '../config';

// Re-export all types from types.ts
export type {
  // Event types
  MessageReceivedEvent,
  BeforeAgentStartEvent,
  MessageSendingEvent,
  BeforeToolCallEvent,
  AgentEndEvent,
  // Sentinel result types (rich)
  MessageReceivedResult,
  BeforeAgentStartResult,
  MessageSendingResult,
  BeforeToolCallResult,
  AgentEndResult,
  // Context types
  HookContext,
  AlertDecisionContext,
  // Moltbot-compatible result types
  MoltbotAgentStartResult,
  MoltbotMessageSendingResult,
  MoltbotToolCallResult,
} from './types';

// Re-export type guards from types (factories moved to state.ts)
export {
  isMessageReceivedEvent,
  isBeforeAgentStartEvent,
  isMessageSendingEvent,
  isBeforeToolCallEvent,
  isAgentEndEvent,
} from './types';

// Re-export seed functions and constants
export {
  STANDARD_SEED,
  STRICT_SEED,
  SEED_TEMPLATES,
  getSeedContent,
  getSeedForLevel,
  hasSeed,
  createCustomizedSeed,
  isValidSeedTemplate,
  getRecommendedSeedTemplate,
  getSeedTemplateMetadata,
  getAllSeedTemplateMetadata,
} from './seeds';

export type { SeedCustomizationOptions, SeedTemplateMetadata } from './seeds';

// Re-export state management functions
export {
  // Re-exports from types.ts
  createSessionState,
  createSessionSummary,
  // State update functions
  recordMessageReceived,
  recordToolCall,
  recordOutputValidation,
  recordAlert,
  // Anomaly detection
  detectAnomalies,
  DEFAULT_ANOMALY_CONFIG,
  // Session manager
  SessionStateManager,
  // Utilities
  getSessionDuration,
  isSessionActive,
  getSessionRiskLevel,
} from './state';

export type {
  SessionState,
  SessionSummary,
  SessionAnomalyType,
  AnomalyDetectionConfig,
  AnomalyDetectionResult,
  SessionStateManagerOptions,
  AggregateSessionStats,
} from './state';

// Re-export handlers
export {
  handleMessageReceived,
  handleBeforeAgentStart,
  handleMessageSending,
  handleBeforeToolCall,
  handleAgentEnd,
} from './handlers';

export type { HandlerContext } from './handlers';

// Import handlers for internal use
import {
  handleMessageReceived,
  handleBeforeAgentStart,
  handleMessageSending,
  handleBeforeToolCall,
  handleAgentEnd,
  type HandlerContext,
} from './handlers';

// Import types for internal use
import type {
  MessageReceivedEvent,
  BeforeAgentStartEvent,
  MessageSendingEvent,
  BeforeToolCallEvent,
  AgentEndEvent,
  MoltbotAgentStartResult,
  MoltbotMessageSendingResult,
  MoltbotToolCallResult,
} from './types';

// Import session manager
import { SessionStateManager } from './state';

// =============================================================================
// Sentinel Hooks Bundle
// =============================================================================

/**
 * Complete set of Sentinel hooks for Moltbot.
 *
 * These hooks return Moltbot-compatible result types.
 * Internally, they use the richer Sentinel result types for
 * logging, metrics, and decision-making.
 */
export interface SentinelHooks {
  /** Handler for message_received (fire-and-forget, no return) */
  messageReceived: (event: MessageReceivedEvent) => void;
  /** Handler for before_agent_start (returns seed context) */
  beforeAgentStart: (event: BeforeAgentStartEvent) => MoltbotAgentStartResult | undefined;
  /** Handler for message_sending (can cancel/modify) */
  messageSending: (event: MessageSendingEvent) => Promise<MoltbotMessageSendingResult | undefined>;
  /** Handler for before_tool_call (can block/modify) */
  beforeToolCall: (event: BeforeToolCallEvent) => Promise<MoltbotToolCallResult | undefined>;
  /** Handler for agent_end (fire-and-forget, no return) */
  agentEnd: (event: AgentEndEvent) => void;
}

/**
 * Internal state for hooks.
 *
 * Holds configuration, level settings, and session manager
 * for all hooks created by the factory.
 */
interface HooksState {
  /** Parsed plugin configuration */
  readonly config: SentinelMoltbotConfig;
  /** Resolved level configuration */
  readonly levelConfig: LevelConfig;
  /** Session state manager for tracking per-session state */
  readonly sessionManager: SessionStateManager;
}

// =============================================================================
// Hook Factory
// =============================================================================

/**
 * Create Sentinel hooks for Moltbot integration.
 *
 * @param userConfig - Plugin configuration
 * @returns Object with all hook handlers
 *
 * @example
 * ```typescript
 * const hooks = createSentinelHooks({ level: 'guard' });
 *
 * // In Moltbot plugin registration:
 * export const hooks = {
 *   message_received: hooks.messageReceived,
 *   before_agent_start: hooks.beforeAgentStart,
 *   message_sending: hooks.messageSending,
 *   before_tool_call: hooks.beforeToolCall,
 *   agent_end: hooks.agentEnd,
 * };
 * ```
 */
export function createSentinelHooks(
  userConfig: Partial<SentinelMoltbotConfig>
): SentinelHooks {
  const config = parseConfig(userConfig);
  const levelConfig = getLevelConfig(config.level, config.custom);

  // Create session manager with default settings
  const sessionManager = new SessionStateManager({
    sessionTimeoutMs: 30 * 60 * 1000, // 30 minutes
    maxSessions: 1000,
  });

  const state: HooksState = {
    config,
    levelConfig,
    sessionManager,
  };

  return {
    messageReceived: createMessageReceivedHook(state),
    beforeAgentStart: createBeforeAgentStartHook(state),
    messageSending: createMessageSendingHook(state),
    beforeToolCall: createBeforeToolCallHook(state),
    agentEnd: createAgentEndHook(state),
  };
}

// =============================================================================
// Individual Hook Factories
// =============================================================================

/**
 * Create a handler context for use with core handlers.
 *
 * @param state - Hooks state
 * @param sessionId - Session identifier
 * @returns Handler context with optional session state
 */
function createContext(state: HooksState, sessionId: string): HandlerContext {
  return {
    config: state.config,
    levelConfig: state.levelConfig,
    sessionState: state.sessionManager.getOrCreate(sessionId),
  };
}

/**
 * Create the message_received hook.
 *
 * This hook analyzes incoming messages for threats and updates session state.
 * It's fire-and-forget (returns void).
 */
function createMessageReceivedHook(state: HooksState) {
  return (event: MessageReceivedEvent): void => {
    // Fire and forget - run async but don't block
    const context = createContext(state, event.sessionId);

    // Execute handler (async but we don't await)
    handleMessageReceived(event, context).catch(() => {
      // Fail silently - this is fire-and-forget
    });
  };
}

/**
 * Create the before_agent_start hook.
 *
 * This hook injects safety seeds into the agent's context.
 * Returns Moltbot-compatible result with additionalContext.
 */
function createBeforeAgentStartHook(state: HooksState) {
  return (event: BeforeAgentStartEvent): MoltbotAgentStartResult | undefined => {
    const context = createContext(state, event.sessionId);
    const result = handleBeforeAgentStart(event, context);

    // Convert to Moltbot format
    if (!result.seedInjected || !result.additionalContext) {
      return undefined;
    }

    return {
      additionalContext: result.additionalContext,
    };
  };
}

/**
 * Create the message_sending hook.
 *
 * This hook validates outgoing messages and can block them.
 * Returns Moltbot-compatible result with cancel flag.
 */
function createMessageSendingHook(state: HooksState) {
  return async (event: MessageSendingEvent): Promise<MoltbotMessageSendingResult | undefined> => {
    const context = createContext(state, event.sessionId);
    const result = await handleMessageSending(event, context);

    // Convert to Moltbot format
    if (!result.shouldBlock) {
      return undefined; // Allow message
    }

    return {
      cancel: true,
      cancelReason: result.cancelReason,
    };
  };
}

/**
 * Create the before_tool_call hook.
 *
 * This hook validates tool calls and can block them.
 * Returns Moltbot-compatible result with block flag.
 */
function createBeforeToolCallHook(state: HooksState) {
  return async (event: BeforeToolCallEvent): Promise<MoltbotToolCallResult | undefined> => {
    const context = createContext(state, event.sessionId);
    const result = await handleBeforeToolCall(event, context);

    // Convert to Moltbot format
    if (!result.shouldBlock) {
      return undefined; // Allow tool call
    }

    return {
      block: true,
      blockReason: result.blockReason,
    };
  };
}

/**
 * Create the agent_end hook.
 *
 * This hook finalizes session state and performs anomaly detection.
 * It's fire-and-forget (returns void) and cleans up session state.
 */
function createAgentEndHook(state: HooksState) {
  return (event: AgentEndEvent): void => {
    const context = createContext(state, event.sessionId);

    // Execute handler synchronously
    handleAgentEnd(event, context);

    // Clean up session state
    state.sessionManager.endSession(event.sessionId, event.success);
  };
}

// =============================================================================
// Re-exports from parent types
// =============================================================================

export type {
  SentinelMoltbotConfig,
  LevelConfig,
  ProtectionLevel,
  DetectedIssue,
  RiskLevel,
  SeedTemplate,
} from '../types';
