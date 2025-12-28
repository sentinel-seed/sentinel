/**
 * @fileoverview Custom hooks exports
 *
 * @author Sentinel Team
 * @license MIT
 */

export {
  useSubscription,
  useBroadcastEvent as useSingleSubscription,
  useFetchWithSubscription,
  useAgentEvents,
  useMCPEvents,
  useApprovalEvents,
  type SubscriptionEvent,
  type SubscriptionCallback,
} from './useSubscription';

export {
  useFocusTrap,
  useAnnounce,
} from './useFocusTrap';

export {
  useAccessibilityPreferences,
  useAnnouncer,
  useRovingTabindex,
  useSkipLink,
  useKeyboardNavigation,
  type AnnouncementPriority,
  type AccessibilityPreferences,
} from './useAccessibility';
