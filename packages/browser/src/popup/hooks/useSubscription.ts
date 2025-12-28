/**
 * @fileoverview Custom hook for subscribing to broadcast events
 *
 * Provides a React-friendly way to subscribe to real-time events
 * from the background service worker.
 *
 * Features:
 * - Strongly typed event handling
 * - Automatic cleanup on unmount
 * - Support for multiple event types
 * - Fetch with subscription for initial data + updates
 *
 * @author Sentinel Team
 * @license MIT
 */

import { useEffect, useCallback, useRef, useState } from 'react';
import type {
  BroadcastEventType,
  BroadcastEventPayloadMap,
  BroadcastEvent,
  BroadcastMessage,
} from '../../messaging/types';
import { isBroadcastMessage } from '../../messaging/types';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Callback function for event subscriptions
 */
export type EventCallback<T extends BroadcastEventType> = (
  payload: BroadcastEventPayloadMap[T],
  event: BroadcastEvent<T>
) => void;

/**
 * Generic callback for multiple event types
 */
export type MultiEventCallback = (
  payload: unknown,
  event: BroadcastEvent
) => void;

// =============================================================================
// SINGLE EVENT SUBSCRIPTION
// =============================================================================

/**
 * Hook to subscribe to a single broadcast event type
 *
 * @param eventType - The event type to subscribe to
 * @param callback - Function to call when event is received
 *
 * @example
 * ```tsx
 * useBroadcastEvent('AGENT_CONNECTED', (payload) => {
 *   console.log('Agent connected:', payload.agent.name);
 * });
 * ```
 */
export function useBroadcastEvent<T extends BroadcastEventType>(
  eventType: T,
  callback: EventCallback<T>
): void {
  const callbackRef = useRef(callback);

  // Keep callback ref updated to avoid stale closures
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const handleMessage = (
      message: unknown,
      _sender: chrome.runtime.MessageSender,
      _sendResponse: (response?: unknown) => void
    ): boolean | void => {
      if (!isBroadcastMessage(message)) return;

      if (message.event.type === eventType) {
        callbackRef.current(
          message.event.payload as BroadcastEventPayloadMap[T],
          message.event as BroadcastEvent<T>
        );
      }
    };

    chrome.runtime.onMessage.addListener(handleMessage);

    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
    };
  }, [eventType]);
}

// =============================================================================
// MULTIPLE EVENT SUBSCRIPTION
// =============================================================================

/**
 * Hook to subscribe to multiple broadcast event types
 *
 * @param eventTypes - Array of event types to subscribe to
 * @param callback - Function to call when any subscribed event is received
 *
 * @example
 * ```tsx
 * useBroadcastEvents(
 *   ['AGENT_CONNECTED', 'AGENT_DISCONNECTED', 'AGENT_UPDATED'],
 *   () => {
 *     refetchAgents();
 *   }
 * );
 * ```
 */
export function useBroadcastEvents(
  eventTypes: BroadcastEventType[],
  callback: MultiEventCallback
): void {
  const callbackRef = useRef(callback);
  const eventTypesRef = useRef(eventTypes);

  // Keep refs updated
  useEffect(() => {
    callbackRef.current = callback;
    eventTypesRef.current = eventTypes;
  }, [callback, eventTypes]);

  useEffect(() => {
    const handleMessage = (
      message: unknown,
      _sender: chrome.runtime.MessageSender,
      _sendResponse: (response?: unknown) => void
    ): boolean | void => {
      if (!isBroadcastMessage(message)) return;

      if (eventTypesRef.current.includes(message.event.type)) {
        callbackRef.current(message.event.payload, message.event);
      }
    };

    chrome.runtime.onMessage.addListener(handleMessage);

    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
    };
  }, []); // Empty deps - refs handle updates
}

// =============================================================================
// SUBSCRIPTION WITH REFETCH
// =============================================================================

/**
 * Hook that combines initial data fetch with subscription to updates
 *
 * @param fetchFn - Function to fetch data
 * @param eventTypes - Events that should trigger a refetch
 * @param deps - Additional dependencies for the fetch function
 *
 * @example
 * ```tsx
 * const { data, loading, error, refetch } = useFetchWithBroadcast(
 *   () => chrome.runtime.sendMessage({ type: 'AGENT_LIST' }),
 *   ['AGENT_CONNECTED', 'AGENT_DISCONNECTED', 'AGENT_UPDATED']
 * );
 * ```
 */
export function useFetchWithBroadcast<T>(
  fetchFn: () => Promise<T>,
  eventTypes: BroadcastEventType[],
  deps: React.DependencyList = []
): {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
} {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const result = await fetchFn();
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err : new Error(String(err)));
    } finally {
      setLoading(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Subscribe to events for updates
  useBroadcastEvents(eventTypes, () => {
    fetchData();
  });

  return { data, loading, error, refetch: fetchData };
}

// =============================================================================
// CONVENIENCE HOOKS
// =============================================================================

/**
 * Hook to subscribe to all agent-related events
 */
export function useAgentEvents(onUpdate: () => void): void {
  useBroadcastEvents(
    [
      'AGENT_CONNECTED',
      'AGENT_DISCONNECTED',
      'AGENT_UPDATED',
      'AGENT_ACTION_INTERCEPTED',
      'AGENT_ACTION_DECIDED',
    ],
    onUpdate
  );
}

/**
 * Hook to subscribe to all MCP-related events
 */
export function useMCPEvents(onUpdate: () => void): void {
  useBroadcastEvents(
    [
      'MCP_SERVER_REGISTERED',
      'MCP_SERVER_UNREGISTERED',
      'MCP_SERVER_UPDATED',
      'MCP_TOOL_CALL_INTERCEPTED',
      'MCP_TOOL_CALL_DECIDED',
    ],
    onUpdate
  );
}

/**
 * Hook to subscribe to all approval-related events
 */
export function useApprovalEvents(onUpdate: () => void): void {
  useBroadcastEvents(
    [
      'APPROVAL_QUEUED',
      'APPROVAL_DECIDED',
      'APPROVAL_EXPIRED',
      'APPROVAL_QUEUE_CHANGED',
    ],
    onUpdate
  );
}

/**
 * Hook to subscribe to stats updates
 */
export function useStatsEvents(
  onUpdate: (payload: BroadcastEventPayloadMap['STATS_UPDATED']) => void
): void {
  useBroadcastEvent('STATS_UPDATED', onUpdate);
}

/**
 * Hook to subscribe to alert events
 */
export function useAlertEvents(onUpdate: () => void): void {
  useBroadcastEvents(['ALERT_CREATED', 'ALERT_ACKNOWLEDGED'], onUpdate);
}

// =============================================================================
// LEGACY EXPORTS (for backwards compatibility)
// =============================================================================

// Re-export with old names for backwards compatibility
export { useBroadcastEvents as useSubscription };
export { useFetchWithBroadcast as useFetchWithSubscription };
export type { BroadcastEventType as SubscriptionEvent };
export type { MultiEventCallback as SubscriptionCallback };
