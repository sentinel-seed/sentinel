/**
 * @fileoverview Messaging module exports
 *
 * @author Sentinel Team
 * @license MIT
 */

// Types
export type {
  BroadcastEventType,
  BroadcastEventPayloadMap,
  BroadcastEvent,
  BroadcastMessage,
  EventCallback,
  Subscription,
  NotificationPriority,
  NotificationOptions,
  NotificationResult,
  BadgeConfig,
  BadgeState,
  // Event payloads
  AgentConnectedPayload,
  AgentDisconnectedPayload,
  AgentUpdatedPayload,
  AgentActionInterceptedPayload,
  AgentActionDecidedPayload,
  MCPServerRegisteredPayload,
  MCPServerUnregisteredPayload,
  MCPServerUpdatedPayload,
  MCPToolCallInterceptedPayload,
  MCPToolCallDecidedPayload,
  ApprovalQueuedPayload,
  ApprovalDecidedPayload,
  ApprovalExpiredPayload,
  ApprovalQueueChangedPayload,
  StatsUpdatedPayload,
  AlertCreatedPayload,
  AlertAcknowledgedPayload,
} from './types';

// Type guards
export { isBroadcastMessage, isEventType } from './types';

// Broadcast service
export {
  broadcast,
  broadcastAgent,
  broadcastMCP,
  broadcastApproval,
  broadcastStats,
  broadcastAlert,
  batchBroadcast,
} from './broadcast-service';

// Badge manager
export { badgeManager } from './badge-manager';

// Notification service
export {
  notificationService,
  notifyApprovalRequired,
  notifySecurityAlert,
  notifyInfo,
} from './notification-service';
