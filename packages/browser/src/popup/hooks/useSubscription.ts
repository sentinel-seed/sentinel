/**
 * @fileoverview Custom hook for event-driven updates via chrome.runtime messages
 *
 * Replaces polling with push-based updates for better performance and UX.
 * Subscribes to background script events and updates state accordingly.
 *
 * @author Sentinel Team
 * @license MIT
 */

import { useEffect, useCallback, useRef } from 'react';

/** Event types that can be subscribed to */
export type SubscriptionEvent =
  | 'AGENT_STATE_CHANGED'
  | 'MCP_STATE_CHANGED'
  | 'APPROVAL_STATE_CHANGED'
  | 'STATS_UPDATED'
  | 'ALERT_CREATED';

/** Subscription callback function type */
export type SubscriptionCallback = (data: unknown) => void;

/**
 * Hook to subscribe to background script events
 *
 * @param events - Array of event types to subscribe to
 * @param callback - Function to call when any subscribed event fires
 *
 * @example
 * ```tsx
 * useSubscription(['AGENT_STATE_CHANGED', 'APPROVAL_STATE_CHANGED'], () => {
 *   loadData();
 * });
 * ```
 */
export function useSubscription(
  events: SubscriptionEvent[],
  callback: SubscriptionCallback
): void {
  const callbackRef = useRef(callback);

  // Keep callback ref updated to avoid stale closures
  useEffect(() => {
    callbackRef.current = callback;
  }, [callback]);

  useEffect(() => {
    const handleMessage = (
      message: { type: string; payload?: unknown },
      _sender: chrome.runtime.MessageSender,
      _sendResponse: (response?: unknown) => void
    ): boolean | void => {
      if (events.includes(message.type as SubscriptionEvent)) {
        callbackRef.current(message.payload);
      }
    };

    chrome.runtime.onMessage.addListener(handleMessage);

    return () => {
      chrome.runtime.onMessage.removeListener(handleMessage);
    };
  }, [events]);
}

/**
 * Hook to subscribe to a single event type
 *
 * @param event - Event type to subscribe to
 * @param callback - Function to call when event fires
 */
export function useSingleSubscription(
  event: SubscriptionEvent,
  callback: SubscriptionCallback
): void {
  useSubscription([event], callback);
}

/**
 * Hook that combines initial data fetch with subscription to updates
 *
 * @param fetchFn - Function to fetch initial data
 * @param events - Events that should trigger a refetch
 * @param deps - Additional dependencies for the fetch function
 *
 * @example
 * ```tsx
 * const { data, loading, error, refetch } = useFetchWithSubscription(
 *   async () => chrome.runtime.sendMessage({ type: 'AGENT_LIST' }),
 *   ['AGENT_STATE_CHANGED']
 * );
 * ```
 */
export function useFetchWithSubscription<T>(
  fetchFn: () => Promise<T>,
  events: SubscriptionEvent[],
  deps: React.DependencyList = []
): {
  data: T | null;
  loading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
} {
  const [data, setData] = React.useState<T | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<Error | null>(null);

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
  }, deps);

  // Initial fetch
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Subscribe to events for updates
  useSubscription(events, () => {
    fetchData();
  });

  return { data, loading, error, refetch: fetchData };
}

// Need to import React for the useState/useCallback in useFetchWithSubscription
import * as React from 'react';
