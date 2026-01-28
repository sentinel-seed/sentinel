/**
 * @sentinelseed/moltbot - Moltbot Plugin Entry Point
 *
 * This file is a thin adapter that connects the Sentinel hooks
 * to the Moltbot plugin system.
 *
 * Architecture (Core Hooks + Thin Adapter):
 * - Core logic lives in hooks/handlers.ts (pure functions)
 * - Factory in hooks/index.ts creates hook instances
 * - This file adapts Moltbot's API to our hooks
 *
 * @example Moltbot loads this plugin via:
 * ```json
 * // moltbot.config.json
 * {
 *   "plugins": {
 *     "sentinel": {
 *       "level": "watch"
 *     }
 *   }
 * }
 * ```
 */

import type { SentinelMoltbotConfig } from './types';
import { createSentinelHooks, type SentinelHooks } from './hooks';

// =============================================================================
// Moltbot Plugin Types (compatible with Moltbot's plugin API)
// =============================================================================

/**
 * Moltbot Plugin API type.
 * This is a subset of the actual Moltbot API that we use.
 */
interface MoltbotPluginApi {
  readonly id: string;
  readonly name: string;
  readonly pluginConfig?: Record<string, unknown>;
  readonly logger: MoltbotLogger;
  on: (
    hookName: string,
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    handler: (...args: any[]) => any,
    opts?: { priority?: number }
  ) => void;
}

/**
 * Moltbot logger interface.
 */
interface MoltbotLogger {
  info: (message: string, data?: Record<string, unknown>) => void;
  warn: (message: string, data?: Record<string, unknown>) => void;
  error: (message: string, data?: Record<string, unknown>) => void;
  debug: (message: string, data?: Record<string, unknown>) => void;
}

// =============================================================================
// Moltbot Event Types
// =============================================================================

interface MoltbotMessageReceivedEvent {
  content: string;
}

interface MoltbotMessageContext {
  channelId: string;
  accountId?: string;
  conversationId?: string;
}

interface MoltbotBeforeAgentStartEvent {
  prompt: string;
  messages?: unknown[];
}

interface MoltbotAgentContext {
  agentId?: string;
  sessionKey?: string;
  workspaceDir?: string;
}

interface MoltbotMessageSendingEvent {
  content: string;
}

interface MoltbotBeforeToolCallEvent {
  toolName: string;
  params: Record<string, unknown>;
}

interface MoltbotToolContext {
  agentId?: string;
  sessionKey?: string;
}

interface MoltbotAgentEndEvent {
  messages: unknown[];
  success: boolean;
  error?: string;
  durationMs?: number;
}

// =============================================================================
// Moltbot Result Types
// =============================================================================

interface MoltbotBeforeAgentStartResult {
  systemPrompt?: string;
  prependContext?: string;
}

interface MoltbotMessageSendingResult {
  content?: string;
  cancel?: boolean;
  cancelReason?: string;
}

interface MoltbotBeforeToolCallResult {
  params?: Record<string, unknown>;
  block?: boolean;
  blockReason?: string;
}

// =============================================================================
// Plugin Registration
// =============================================================================

/**
 * Register the Sentinel plugin with Moltbot.
 *
 * This function is called by Moltbot when the plugin is loaded.
 * It creates Sentinel hooks and adapts them to Moltbot's API.
 *
 * @param api - Moltbot plugin API
 */
export function register(api: MoltbotPluginApi): void {
  const userConfig = (api.pluginConfig ?? {}) as Partial<SentinelMoltbotConfig>;

  // Create Sentinel hooks using the factory
  const hooks = createSentinelHooks(userConfig);

  // Log initialization
  api.logger.info('Sentinel initialized', {
    level: userConfig.level ?? 'watch',
  });

  // Skip all hooks if level is 'off'
  if (userConfig.level === 'off') {
    api.logger.info('Sentinel is disabled (level: off)');
    return;
  }

  // Register adapted hooks with Moltbot
  // Higher priority = runs first
  registerMessageReceivedHook(api, hooks);
  registerBeforeAgentStartHook(api, hooks);
  registerMessageSendingHook(api, hooks);
  registerBeforeToolCallHook(api, hooks);
  registerAgentEndHook(api, hooks);
}

// =============================================================================
// Hook Adapters
// =============================================================================

/**
 * Adapt message_received hook for Moltbot.
 */
function registerMessageReceivedHook(
  api: MoltbotPluginApi,
  hooks: SentinelHooks
): void {
  api.on(
    'message_received',
    (event: MoltbotMessageReceivedEvent, ctx: MoltbotMessageContext): void => {
      // Derive session ID from context
      const sessionId = deriveSessionId(ctx);

      // Call Sentinel hook (fire-and-forget)
      hooks.messageReceived({
        sessionId,
        content: event.content,
        timestamp: Date.now(),
      });
    },
    { priority: 100 }
  );
}

/**
 * Adapt before_agent_start hook for Moltbot.
 */
function registerBeforeAgentStartHook(
  api: MoltbotPluginApi,
  hooks: SentinelHooks
): void {
  api.on(
    'before_agent_start',
    (
      _event: MoltbotBeforeAgentStartEvent,
      ctx: MoltbotAgentContext
    ): MoltbotBeforeAgentStartResult | undefined => {
      // Derive session ID from context
      const sessionId = deriveAgentSessionId(ctx);

      // Call Sentinel hook
      const result = hooks.beforeAgentStart({ sessionId });

      // Adapt result for Moltbot
      if (!result?.additionalContext) {
        return undefined;
      }

      api.logger.debug('Injecting safety seed');

      return {
        prependContext: result.additionalContext,
      };
    },
    { priority: 100 }
  );
}

/**
 * Adapt message_sending hook for Moltbot.
 */
function registerMessageSendingHook(
  api: MoltbotPluginApi,
  hooks: SentinelHooks
): void {
  api.on(
    'message_sending',
    async (
      event: MoltbotMessageSendingEvent,
      ctx: MoltbotMessageContext
    ): Promise<MoltbotMessageSendingResult | undefined> => {
      // Derive session ID from context
      const sessionId = deriveSessionId(ctx);

      // Call Sentinel hook
      const result = await hooks.messageSending({
        sessionId,
        content: event.content,
      });

      // Adapt result for Moltbot
      if (!result?.cancel) {
        return undefined;
      }

      api.logger.warn('Blocking output', {
        reason: result.cancelReason,
      });

      return {
        cancel: true,
        cancelReason: result.cancelReason,
      };
    },
    { priority: 100 }
  );
}

/**
 * Adapt before_tool_call hook for Moltbot.
 */
function registerBeforeToolCallHook(
  api: MoltbotPluginApi,
  hooks: SentinelHooks
): void {
  api.on(
    'before_tool_call',
    async (
      event: MoltbotBeforeToolCallEvent,
      ctx: MoltbotToolContext
    ): Promise<MoltbotBeforeToolCallResult | undefined> => {
      // Derive session ID from context
      const sessionId = deriveToolSessionId(ctx);

      // Call Sentinel hook
      const result = await hooks.beforeToolCall({
        sessionId,
        toolName: event.toolName,
        params: event.params,
      });

      // Adapt result for Moltbot
      if (!result?.block) {
        return undefined;
      }

      api.logger.warn('Blocking tool call', {
        toolName: event.toolName,
        reason: result.blockReason,
      });

      return {
        block: true,
        blockReason: result.blockReason,
      };
    },
    { priority: 100 }
  );
}

/**
 * Adapt agent_end hook for Moltbot.
 */
function registerAgentEndHook(
  api: MoltbotPluginApi,
  hooks: SentinelHooks
): void {
  api.on(
    'agent_end',
    (event: MoltbotAgentEndEvent, ctx: MoltbotAgentContext): void => {
      // Derive session ID from context
      const sessionId = deriveAgentSessionId(ctx);

      // Call Sentinel hook (fire-and-forget)
      hooks.agentEnd({
        sessionId,
        success: event.success,
        error: event.error ? new Error(event.error) : undefined,
        durationMs: event.durationMs,
      });

      api.logger.debug('Session ended');
    },
    { priority: 50 }
  );
}

// =============================================================================
// Session ID Helpers
// =============================================================================

/**
 * Derive a session ID from message context.
 */
function deriveSessionId(ctx: MoltbotMessageContext): string {
  // Use conversationId if available, otherwise channelId
  return ctx.conversationId ?? ctx.channelId ?? 'default';
}

/**
 * Derive a session ID from agent context.
 */
function deriveAgentSessionId(ctx: MoltbotAgentContext): string {
  // Use sessionKey if available, otherwise agentId
  return ctx.sessionKey ?? ctx.agentId ?? 'default';
}

/**
 * Derive a session ID from tool context.
 */
function deriveToolSessionId(ctx: MoltbotToolContext): string {
  // Use sessionKey if available, otherwise agentId
  return ctx.sessionKey ?? ctx.agentId ?? 'default';
}

// Note: No default export - use named export `register` instead.
// Moltbot supports both: { register } or (api) => {} function export.
