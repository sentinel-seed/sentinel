/**
 * @fileoverview Broadcast Service for emitting events to all listeners
 *
 * This service runs in the background script and broadcasts events
 * to all connected popup/content scripts when state changes occur.
 *
 * Features:
 * - Strongly typed event emission
 * - Automatic event ID generation
 * - Error handling for disconnected listeners
 * - Event logging for debugging
 *
 * @author Sentinel Team
 * @license MIT
 */

import type {
  BroadcastEventType,
  BroadcastEventPayloadMap,
  BroadcastEvent,
  BroadcastMessage,
} from './types';

// =============================================================================
// BROADCAST SERVICE
// =============================================================================

/**
 * Generates a unique event ID
 */
function generateEventId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Broadcasts an event to all connected listeners
 *
 * @param type - The event type
 * @param payload - The event payload
 * @returns Promise that resolves when broadcast is complete
 *
 * @example
 * ```typescript
 * await broadcast('AGENT_CONNECTED', {
 *   agent: newAgent
 * });
 * ```
 */
export async function broadcast<T extends BroadcastEventType>(
  type: T,
  payload: BroadcastEventPayloadMap[T]
): Promise<void> {
  const event: BroadcastEvent<T> = {
    type,
    payload,
    timestamp: Date.now(),
    eventId: generateEventId(),
  };

  const message: BroadcastMessage<T> = {
    isBroadcast: true,
    event,
  };

  // Log event in development
  if (process.env.NODE_ENV === 'development') {
    console.debug('[Broadcast]', type, payload);
  }

  try {
    // Broadcast to all extension contexts (popup, options, etc.)
    await broadcastToExtension(message);

    // Broadcast to all content scripts
    await broadcastToContentScripts(message);
  } catch (error) {
    // Log but don't throw - broadcast failures shouldn't break the app
    console.warn('[Broadcast] Failed to broadcast event:', type, error);
  }
}

/**
 * Broadcasts to extension contexts (popup, options page, etc.)
 */
async function broadcastToExtension<T extends BroadcastEventType>(
  message: BroadcastMessage<T>
): Promise<void> {
  try {
    // Send to extension runtime - this reaches popup if open
    await chrome.runtime.sendMessage(message);
  } catch (error) {
    // This is expected if no listeners are active (e.g., popup closed)
    // Only log if it's an unexpected error
    const errorMessage = error instanceof Error ? error.message : String(error);
    if (!errorMessage.includes('Receiving end does not exist')) {
      console.warn('[Broadcast] Extension broadcast failed:', errorMessage);
    }
  }
}

/**
 * Broadcasts to all content scripts in all tabs
 */
async function broadcastToContentScripts<T extends BroadcastEventType>(
  message: BroadcastMessage<T>
): Promise<void> {
  try {
    const tabs = await chrome.tabs.query({});

    // Send to each tab, ignoring failures (tab may have no content script)
    const sendPromises = tabs.map(async (tab) => {
      if (!tab.id) return;

      try {
        await chrome.tabs.sendMessage(tab.id, message);
      } catch {
        // Expected if tab doesn't have our content script
      }
    });

    await Promise.allSettled(sendPromises);
  } catch (error) {
    // Log but don't throw
    console.warn('[Broadcast] Content script broadcast failed:', error);
  }
}

// =============================================================================
// CONVENIENCE FUNCTIONS
// =============================================================================

/**
 * Broadcasts an agent-related event
 */
export const broadcastAgent = {
  connected: (agent: BroadcastEventPayloadMap['AGENT_CONNECTED']['agent']) =>
    broadcast('AGENT_CONNECTED', { agent }),

  disconnected: (agentId: string, agentName: string) =>
    broadcast('AGENT_DISCONNECTED', { agentId, agentName }),

  updated: (
    agent: BroadcastEventPayloadMap['AGENT_UPDATED']['agent'],
    changes: BroadcastEventPayloadMap['AGENT_UPDATED']['changes']
  ) => broadcast('AGENT_UPDATED', { agent, changes }),

  actionIntercepted: (
    payload: BroadcastEventPayloadMap['AGENT_ACTION_INTERCEPTED']
  ) => broadcast('AGENT_ACTION_INTERCEPTED', payload),

  actionDecided: (payload: BroadcastEventPayloadMap['AGENT_ACTION_DECIDED']) =>
    broadcast('AGENT_ACTION_DECIDED', payload),
};

/**
 * Broadcasts an MCP-related event
 */
export const broadcastMCP = {
  serverRegistered: (
    server: BroadcastEventPayloadMap['MCP_SERVER_REGISTERED']['server']
  ) => broadcast('MCP_SERVER_REGISTERED', { server }),

  serverUnregistered: (serverId: string, serverName: string) =>
    broadcast('MCP_SERVER_UNREGISTERED', { serverId, serverName }),

  serverUpdated: (
    server: BroadcastEventPayloadMap['MCP_SERVER_UPDATED']['server'],
    changes: BroadcastEventPayloadMap['MCP_SERVER_UPDATED']['changes']
  ) => broadcast('MCP_SERVER_UPDATED', { server, changes }),

  toolCallIntercepted: (
    payload: BroadcastEventPayloadMap['MCP_TOOL_CALL_INTERCEPTED']
  ) => broadcast('MCP_TOOL_CALL_INTERCEPTED', payload),

  toolCallDecided: (
    payload: BroadcastEventPayloadMap['MCP_TOOL_CALL_DECIDED']
  ) => broadcast('MCP_TOOL_CALL_DECIDED', payload),
};

/**
 * Broadcasts an approval-related event
 */
export const broadcastApproval = {
  queued: (payload: BroadcastEventPayloadMap['APPROVAL_QUEUED']) =>
    broadcast('APPROVAL_QUEUED', payload),

  decided: (payload: BroadcastEventPayloadMap['APPROVAL_DECIDED']) =>
    broadcast('APPROVAL_DECIDED', payload),

  expired: (payload: BroadcastEventPayloadMap['APPROVAL_EXPIRED']) =>
    broadcast('APPROVAL_EXPIRED', payload),

  queueChanged: (queueLength: number, pendingIds: string[]) =>
    broadcast('APPROVAL_QUEUE_CHANGED', { queueLength, pendingIds }),
};

/**
 * Broadcasts a stats update event
 */
export const broadcastStats = {
  updated: (
    stats: BroadcastEventPayloadMap['STATS_UPDATED']['stats'],
    changedFields: BroadcastEventPayloadMap['STATS_UPDATED']['changedFields']
  ) => broadcast('STATS_UPDATED', { stats, changedFields }),
};

/**
 * Broadcasts an alert event
 */
export const broadcastAlert = {
  created: (
    alert: BroadcastEventPayloadMap['ALERT_CREATED']['alert'],
    unacknowledgedCount: number
  ) => broadcast('ALERT_CREATED', { alert, unacknowledgedCount }),

  acknowledged: (alertId: string, unacknowledgedCount: number) =>
    broadcast('ALERT_ACKNOWLEDGED', { alertId, unacknowledgedCount }),
};

// =============================================================================
// BATCH BROADCASTING
// =============================================================================

/**
 * Batch multiple broadcasts together
 * Useful when multiple state changes happen at once
 *
 * @param broadcasts - Array of broadcast functions to execute
 * @returns Promise that resolves when all broadcasts complete
 *
 * @example
 * ```typescript
 * await batchBroadcast([
 *   () => broadcastAgent.connected(agent),
 *   () => broadcastStats.updated(stats, ['agentConnections']),
 * ]);
 * ```
 */
export async function batchBroadcast(
  broadcasts: Array<() => Promise<void>>
): Promise<void> {
  await Promise.allSettled(broadcasts.map((fn) => fn()));
}

export default broadcast;
