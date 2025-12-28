/**
 * @fileoverview Approval Queue - Queue management and notifications
 *
 * This module manages the approval queue, including:
 * - Queue statistics and monitoring
 * - Badge updates for pending approvals
 * - Notifications for approval requests
 * - Timeout handling
 *
 * @author Sentinel Team
 * @license MIT
 */

import {
  PendingApproval,
  AgentAction,
  MCPToolCall,
  RiskLevel,
} from '../types';
import * as store from './approval-store';

// =============================================================================
// TYPES
// =============================================================================

/** Queue statistics */
export interface QueueStats {
  /** Total pending approvals */
  total: number;
  /** Pending from Agent Shield */
  agentShield: number;
  /** Pending from MCP Gateway */
  mcpGateway: number;
  /** By risk level */
  byRiskLevel: Record<RiskLevel, number>;
  /** Oldest pending item timestamp */
  oldestTimestamp: number | null;
  /** Number of expired items */
  expired: number;
}

/** Notification options */
export interface NotificationOptions {
  /** Whether to show a notification */
  show: boolean;
  /** Notification title */
  title?: string;
  /** Notification message */
  message?: string;
  /** Whether to require interaction */
  requireInteraction?: boolean;
}

// =============================================================================
// QUEUE STATISTICS
// =============================================================================

/**
 * Gets statistics about the approval queue.
 *
 * @returns Promise resolving to queue statistics
 */
export async function getQueueStats(): Promise<QueueStats> {
  const pending = await store.getPendingApprovals();
  const now = Date.now();

  const stats: QueueStats = {
    total: pending.length,
    agentShield: 0,
    mcpGateway: 0,
    byRiskLevel: {
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    },
    oldestTimestamp: null,
    expired: 0,
  };

  for (const item of pending) {
    // Count by source
    if (item.source === 'agent_shield') {
      stats.agentShield++;
    } else {
      stats.mcpGateway++;
    }

    // Count by risk level
    const riskLevel = item.action.riskLevel;
    stats.byRiskLevel[riskLevel]++;

    // Track oldest
    if (stats.oldestTimestamp === null || item.queuedAt < stats.oldestTimestamp) {
      stats.oldestTimestamp = item.queuedAt;
    }

    // Count expired
    if (item.expiresAt && item.expiresAt < now) {
      stats.expired++;
    }
  }

  return stats;
}

/**
 * Gets the highest risk level in the queue.
 *
 * @returns Promise resolving to the highest risk level, or null if queue is empty
 */
export async function getHighestRiskLevel(): Promise<RiskLevel | null> {
  const pending = await store.getPendingApprovals();
  if (pending.length === 0) {
    return null;
  }

  const riskOrder: RiskLevel[] = ['critical', 'high', 'medium', 'low'];
  for (const level of riskOrder) {
    if (pending.some((p) => p.action.riskLevel === level)) {
      return level;
    }
  }

  return 'low';
}

// =============================================================================
// BADGE MANAGEMENT
// =============================================================================

/**
 * Updates the extension badge with the pending approval count.
 *
 * @returns Promise resolving when complete
 */
export async function updateBadge(): Promise<void> {
  const count = await store.getPendingCount();
  const highestRisk = await getHighestRiskLevel();

  // Set badge text
  if (count > 0) {
    chrome.action.setBadgeText({ text: count.toString() });
  } else {
    chrome.action.setBadgeText({ text: '' });
  }

  // Set badge color based on highest risk
  const colors: Record<RiskLevel, string> = {
    low: '#22c55e',      // Green
    medium: '#eab308',   // Yellow
    high: '#f97316',     // Orange
    critical: '#ef4444', // Red
  };

  if (highestRisk) {
    chrome.action.setBadgeBackgroundColor({ color: colors[highestRisk] });
  } else {
    chrome.action.setBadgeBackgroundColor({ color: '#6b7280' }); // Gray
  }
}

/**
 * Clears the extension badge.
 *
 * @returns Promise resolving when complete
 */
export async function clearBadge(): Promise<void> {
  chrome.action.setBadgeText({ text: '' });
}

// =============================================================================
// NOTIFICATIONS
// =============================================================================

/**
 * Shows a notification for a pending approval.
 *
 * @param pending - The pending approval
 * @param options - Notification options
 * @returns Promise resolving to the notification ID
 */
export async function showApprovalNotification(
  pending: PendingApproval,
  options: NotificationOptions = { show: true }
): Promise<string | null> {
  if (!options.show) {
    return null;
  }

  const action = pending.action;
  let title = options.title || 'Action Requires Approval';
  let message = options.message;

  if (!message) {
    if (pending.source === 'agent_shield') {
      const agentAction = action as AgentAction;
      message = `${agentAction.agentName}: ${agentAction.description}`;
    } else {
      const mcpCall = action as MCPToolCall;
      message = `${mcpCall.serverName}: ${mcpCall.tool}`;
    }
  }

  // Add risk level to title
  const riskEmoji: Record<RiskLevel, string> = {
    low: '',
    medium: '⚠️ ',
    high: '🔶 ',
    critical: '🚨 ',
  };
  title = riskEmoji[action.riskLevel] + title;

  const notificationId = `approval-${pending.id}`;

  return new Promise((resolve) => {
    chrome.notifications.create(
      notificationId,
      {
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon128.png'),
        title,
        message,
        priority: action.riskLevel === 'critical' ? 2 : 1,
        requireInteraction: options.requireInteraction ?? action.riskLevel !== 'low',
        buttons: [
          { title: 'Approve' },
          { title: 'Reject' },
        ],
      },
      (id) => {
        resolve(id || null);
      }
    );
  });
}

/**
 * Shows a notification for an auto-rejected action.
 *
 * @param action - The rejected action
 * @param reason - Reason for rejection
 * @returns Promise resolving to the notification ID
 */
export async function showRejectionNotification(
  action: AgentAction | MCPToolCall,
  reason: string
): Promise<string | null> {
  let description: string;

  if ('agentName' in action) {
    description = `${action.agentName}: ${action.description}`;
  } else {
    description = `${action.serverName}: ${action.tool}`;
  }

  const notificationId = `rejection-${action.id}`;

  return new Promise((resolve) => {
    chrome.notifications.create(
      notificationId,
      {
        type: 'basic',
        iconUrl: chrome.runtime.getURL('icons/icon128.png'),
        title: '🚫 Action Blocked',
        message: `${description}\nReason: ${reason}`,
        priority: 1,
      },
      (id) => {
        resolve(id || null);
      }
    );
  });
}

/**
 * Clears a notification.
 *
 * @param notificationId - The notification ID to clear
 * @returns Promise resolving when complete
 */
export async function clearNotification(notificationId: string): Promise<void> {
  return new Promise((resolve) => {
    chrome.notifications.clear(notificationId, () => {
      resolve();
    });
  });
}

// =============================================================================
// TIMEOUT HANDLING
// =============================================================================

/** Alarm name for checking expired approvals */
const EXPIRY_CHECK_ALARM = 'sentinel-approval-expiry-check';

/**
 * Sets up the expiry check alarm.
 * Should be called on extension startup.
 *
 * @param intervalMinutes - Check interval in minutes (default: 1)
 */
export function setupExpiryCheckAlarm(intervalMinutes: number = 1): void {
  chrome.alarms.create(EXPIRY_CHECK_ALARM, {
    periodInMinutes: intervalMinutes,
  });
}

/**
 * Handles the expiry check alarm.
 * Should be called from the alarm listener.
 *
 * @param processExpiredFn - Function to process expired approvals
 * @returns Promise resolving to the number of processed items
 */
export async function handleExpiryCheckAlarm(
  processExpiredFn: () => Promise<number>
): Promise<number> {
  const count = await processExpiredFn();

  if (count > 0) {
    await updateBadge();
  }

  return count;
}

/**
 * Clears the expiry check alarm.
 */
export function clearExpiryCheckAlarm(): void {
  chrome.alarms.clear(EXPIRY_CHECK_ALARM);
}

// =============================================================================
// QUEUE OPERATIONS
// =============================================================================

/**
 * Gets pending approvals sorted by priority.
 * Higher risk items come first, then older items.
 *
 * @returns Promise resolving to sorted pending approvals
 */
export async function getPendingByPriority(): Promise<PendingApproval[]> {
  const pending = await store.getPendingApprovals();

  const riskPriority: Record<RiskLevel, number> = {
    critical: 4,
    high: 3,
    medium: 2,
    low: 1,
  };

  return pending.sort((a, b) => {
    // First by risk level (higher first)
    const riskDiff =
      riskPriority[b.action.riskLevel] - riskPriority[a.action.riskLevel];
    if (riskDiff !== 0) {
      return riskDiff;
    }

    // Then by queue time (older first)
    return a.queuedAt - b.queuedAt;
  });
}

/**
 * Gets the next pending approval to show to the user.
 *
 * @returns Promise resolving to the next pending approval, or null if empty
 */
export async function getNextPending(): Promise<PendingApproval | null> {
  const sorted = await getPendingByPriority();
  return sorted.length > 0 ? sorted[0] : null;
}

/**
 * Marks a pending approval as viewed (increments view count).
 *
 * @param pendingId - The ID of the pending approval
 * @returns Promise resolving to the updated pending approval
 */
export async function markAsViewed(
  pendingId: string
): Promise<PendingApproval | null> {
  const updated = await store.incrementViewCount(pendingId);
  return updated || null;
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  getQueueStats,
  getHighestRiskLevel,
  updateBadge,
  clearBadge,
  showApprovalNotification,
  showRejectionNotification,
  clearNotification,
  setupExpiryCheckAlarm,
  handleExpiryCheckAlarm,
  clearExpiryCheckAlarm,
  getPendingByPriority,
  getNextPending,
  markAsViewed,
};
