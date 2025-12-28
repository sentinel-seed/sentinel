/**
 * @fileoverview Notification Service for push notifications
 *
 * Manages Chrome notifications for alerting users about:
 * - Pending approval requests
 * - Security alerts
 * - Agent/MCP status changes
 * - Errors and warnings
 *
 * Features:
 * - Priority-based notification handling
 * - Button actions with callbacks
 * - Auto-dismiss for low priority
 * - Rate limiting to prevent spam
 * - Notification history for debugging
 *
 * @author Sentinel Team
 * @license MIT
 */

import type {
  NotificationOptions,
  NotificationResult,
  NotificationPriority,
} from './types';

// =============================================================================
// CONFIGURATION
// =============================================================================

/** Default icon for notifications */
const DEFAULT_ICON = 'icons/icon128.png';

/** Maximum notifications per minute (rate limiting) */
const MAX_NOTIFICATIONS_PER_MINUTE = 10;

/** Auto-dismiss duration for different priorities (ms) */
const AUTO_DISMISS_DURATIONS: Record<NotificationPriority, number> = {
  low: 5000,
  default: 10000,
  high: 0, // No auto-dismiss
  urgent: 0, // No auto-dismiss
};

/** Chrome notification priority mapping */
const CHROME_PRIORITY: Record<NotificationPriority, 0 | 1 | 2> = {
  low: 0,
  default: 1,
  high: 2,
  urgent: 2,
};

// =============================================================================
// NOTIFICATION SERVICE CLASS
// =============================================================================

/**
 * Handles Chrome notifications for the extension
 */
class NotificationService {
  /** Track recent notifications for rate limiting */
  private recentNotifications: number[] = [];

  /** Map of notification IDs to their data */
  private notificationData: Map<string, Record<string, unknown>> = new Map();

  /** Callback handlers for button actions */
  private buttonHandlers: Map<string, Map<string, () => void>> = new Map();

  constructor() {
    this.setupButtonClickListener();
    this.setupNotificationClosedListener();
  }

  /**
   * Sets up the button click listener
   */
  private setupButtonClickListener(): void {
    chrome.notifications.onButtonClicked.addListener(
      (notificationId, buttonIndex) => {
        const handlers = this.buttonHandlers.get(notificationId);
        if (!handlers) return;

        // Get the action key for this button index
        const actionKeys = Array.from(handlers.keys());
        const actionKey = actionKeys[buttonIndex];

        if (actionKey) {
          const handler = handlers.get(actionKey);
          if (handler) {
            handler();
          }
        }

        // Clear the notification
        this.clear(notificationId);
      }
    );
  }

  /**
   * Sets up the notification closed listener
   */
  private setupNotificationClosedListener(): void {
    chrome.notifications.onClosed.addListener((notificationId) => {
      this.cleanup(notificationId);
    });
  }

  /**
   * Cleans up notification data
   */
  private cleanup(notificationId: string): void {
    this.notificationData.delete(notificationId);
    this.buttonHandlers.delete(notificationId);
  }

  /**
   * Checks if rate limit allows a new notification
   */
  private checkRateLimit(): boolean {
    const now = Date.now();
    const oneMinuteAgo = now - 60000;

    // Remove old entries
    this.recentNotifications = this.recentNotifications.filter(
      (timestamp) => timestamp > oneMinuteAgo
    );

    // Check if under limit
    if (this.recentNotifications.length >= MAX_NOTIFICATIONS_PER_MINUTE) {
      console.warn('[NotificationService] Rate limit exceeded');
      return false;
    }

    // Add current timestamp
    this.recentNotifications.push(now);
    return true;
  }

  /**
   * Generates a unique notification ID
   */
  private generateId(): string {
    return `sentinel-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  // ===========================================================================
  // PUBLIC API
  // ===========================================================================

  /**
   * Shows a notification
   *
   * @param options - Notification options
   * @returns Promise with notification result
   *
   * @example
   * ```typescript
   * await notificationService.show({
   *   title: 'Approval Required',
   *   message: 'Agent wants to transfer 100 USDC',
   *   priority: 'high',
   *   buttons: [
   *     { title: 'Review', action: 'review' },
   *     { title: 'Reject', action: 'reject' },
   *   ],
   * });
   * ```
   */
  async show(options: NotificationOptions): Promise<NotificationResult> {
    // Check rate limit
    if (!this.checkRateLimit()) {
      return {
        id: '',
        shown: false,
        error: 'Rate limit exceeded',
      };
    }

    const notificationId = this.generateId();
    const priority = options.priority || 'default';

    try {
      // Build Chrome notification options
      const chromeOptions: chrome.notifications.NotificationOptions<true> = {
        type: 'basic',
        title: options.title,
        message: options.message,
        iconUrl: options.iconUrl || chrome.runtime.getURL(DEFAULT_ICON),
        priority: CHROME_PRIORITY[priority],
        requireInteraction: options.requireInteraction ?? priority === 'urgent',
      };

      // Add buttons if provided
      if (options.buttons && options.buttons.length > 0) {
        chromeOptions.buttons = options.buttons.map((btn) => ({
          title: btn.title,
        }));

        // Store button handlers
        const handlers = new Map<string, () => void>();
        // Note: button handlers will be set by the caller using onButtonClick
        this.buttonHandlers.set(notificationId, handlers);
      }

      // Store notification data
      if (options.data) {
        this.notificationData.set(notificationId, options.data);
      }

      // Create the notification
      await chrome.notifications.create(notificationId, chromeOptions);

      // Set up auto-dismiss
      const autoDismissMs =
        options.autoDismissMs ?? AUTO_DISMISS_DURATIONS[priority];
      if (autoDismissMs > 0) {
        setTimeout(() => {
          this.clear(notificationId);
        }, autoDismissMs);
      }

      return {
        id: notificationId,
        shown: true,
      };
    } catch (error) {
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      console.error('[NotificationService] Failed to show notification:', error);
      return {
        id: notificationId,
        shown: false,
        error: errorMessage,
      };
    }
  }

  /**
   * Registers a button click handler for a notification
   *
   * @param notificationId - The notification ID
   * @param action - The button action
   * @param handler - The handler function
   */
  onButtonClick(
    notificationId: string,
    action: string,
    handler: () => void
  ): void {
    let handlers = this.buttonHandlers.get(notificationId);
    if (!handlers) {
      handlers = new Map();
      this.buttonHandlers.set(notificationId, handlers);
    }
    handlers.set(action, handler);
  }

  /**
   * Clears a notification
   *
   * @param notificationId - The notification to clear
   */
  async clear(notificationId: string): Promise<void> {
    try {
      await chrome.notifications.clear(notificationId);
      this.cleanup(notificationId);
    } catch (error) {
      // Notification may already be cleared
    }
  }

  /**
   * Clears all notifications
   */
  async clearAll(): Promise<void> {
    try {
      // Use callback-style API wrapped in Promise for compatibility
      const notifications = await new Promise<Record<string, boolean>>((resolve) => {
        chrome.notifications.getAll((result) => {
          resolve((result as Record<string, boolean>) || {});
        });
      });
      const clearPromises = Object.keys(notifications)
        .filter((id) => id.startsWith('sentinel-'))
        .map((id) => this.clear(id));
      await Promise.allSettled(clearPromises);
    } catch (error) {
      console.warn('[NotificationService] Failed to clear all notifications:', error);
    }
  }

  /**
   * Gets the data associated with a notification
   *
   * @param notificationId - The notification ID
   * @returns The notification data or undefined
   */
  getData(notificationId: string): Record<string, unknown> | undefined {
    return this.notificationData.get(notificationId);
  }
}

// =============================================================================
// SINGLETON INSTANCE
// =============================================================================

/**
 * Singleton instance of NotificationService
 */
export const notificationService = new NotificationService();

// =============================================================================
// CONVENIENCE FUNCTIONS
// =============================================================================

/**
 * Shows an approval required notification
 */
export async function notifyApprovalRequired(
  sourceName: string,
  actionType: string,
  riskLevel: string,
  onReview?: () => void,
  onReject?: () => void
): Promise<NotificationResult> {
  const result = await notificationService.show({
    title: 'Approval Required',
    message: `${sourceName} wants to ${actionType}. Risk: ${riskLevel.toUpperCase()}`,
    priority: riskLevel === 'critical' ? 'urgent' : 'high',
    requireInteraction: true,
    buttons: [
      { title: 'Review', action: 'review' },
      { title: 'Reject', action: 'reject' },
    ],
  });

  if (result.shown) {
    if (onReview) {
      notificationService.onButtonClick(result.id, 'review', onReview);
    }
    if (onReject) {
      notificationService.onButtonClick(result.id, 'reject', onReject);
    }
  }

  return result;
}

/**
 * Shows a security alert notification
 */
export async function notifySecurityAlert(
  title: string,
  message: string,
  severity: 'warning' | 'error' | 'critical'
): Promise<NotificationResult> {
  const priorityMap: Record<string, NotificationPriority> = {
    warning: 'default',
    error: 'high',
    critical: 'urgent',
  };

  return notificationService.show({
    title,
    message,
    priority: priorityMap[severity],
    requireInteraction: severity === 'critical',
  });
}

/**
 * Shows a simple info notification
 */
export async function notifyInfo(
  title: string,
  message: string
): Promise<NotificationResult> {
  return notificationService.show({
    title,
    message,
    priority: 'low',
  });
}

export default notificationService;
