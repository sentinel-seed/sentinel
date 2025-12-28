/**
 * @fileoverview Messaging system type definitions
 *
 * Defines the contract for real-time communication between
 * background service worker and popup/content scripts.
 *
 * Architecture:
 * - Background emits BroadcastEvents when state changes
 * - Popup/content scripts subscribe to specific event types
 * - All events are strongly typed for safety
 *
 * @author Sentinel Team
 * @license MIT
 */

import type {
  AgentConnection,
  MCPServer,
  PendingApproval,
  ActionHistoryEntry,
  Alert,
  Stats,
} from '../types';

// =============================================================================
// BROADCAST EVENT TYPES
// =============================================================================

/**
 * All possible broadcast event types
 *
 * Naming convention: DOMAIN_ACTION
 * - AGENT_* for Agent Shield events
 * - MCP_* for MCP Gateway events
 * - APPROVAL_* for Approval System events
 * - STATS_* for statistics events
 * - ALERT_* for alert events
 */
export type BroadcastEventType =
  // Agent Shield events
  | 'AGENT_CONNECTED'
  | 'AGENT_DISCONNECTED'
  | 'AGENT_UPDATED'
  | 'AGENT_ACTION_INTERCEPTED'
  | 'AGENT_ACTION_DECIDED'
  // MCP Gateway events
  | 'MCP_SERVER_REGISTERED'
  | 'MCP_SERVER_UNREGISTERED'
  | 'MCP_SERVER_UPDATED'
  | 'MCP_TOOL_CALL_INTERCEPTED'
  | 'MCP_TOOL_CALL_DECIDED'
  // Approval System events
  | 'APPROVAL_QUEUED'
  | 'APPROVAL_DECIDED'
  | 'APPROVAL_EXPIRED'
  | 'APPROVAL_QUEUE_CHANGED'
  // Stats events
  | 'STATS_UPDATED'
  // Alert events
  | 'ALERT_CREATED'
  | 'ALERT_ACKNOWLEDGED';

// =============================================================================
// EVENT PAYLOADS
// =============================================================================

/** Payload for AGENT_CONNECTED event */
export interface AgentConnectedPayload {
  agent: AgentConnection;
}

/** Payload for AGENT_DISCONNECTED event */
export interface AgentDisconnectedPayload {
  agentId: string;
  agentName: string;
}

/** Payload for AGENT_UPDATED event */
export interface AgentUpdatedPayload {
  agent: AgentConnection;
  changes: Partial<AgentConnection>;
}

/** Payload for AGENT_ACTION_INTERCEPTED event */
export interface AgentActionInterceptedPayload {
  agentId: string;
  agentName: string;
  actionId: string;
  actionType: string;
  riskLevel: string;
  requiresApproval: boolean;
}

/** Payload for AGENT_ACTION_DECIDED event */
export interface AgentActionDecidedPayload {
  agentId: string;
  actionId: string;
  decision: 'approved' | 'rejected';
  method: 'auto' | 'manual';
  reason: string;
}

/** Payload for MCP_SERVER_REGISTERED event */
export interface MCPServerRegisteredPayload {
  server: MCPServer;
}

/** Payload for MCP_SERVER_UNREGISTERED event */
export interface MCPServerUnregisteredPayload {
  serverId: string;
  serverName: string;
}

/** Payload for MCP_SERVER_UPDATED event */
export interface MCPServerUpdatedPayload {
  server: MCPServer;
  changes: Partial<MCPServer>;
}

/** Payload for MCP_TOOL_CALL_INTERCEPTED event */
export interface MCPToolCallInterceptedPayload {
  serverId: string;
  serverName: string;
  callId: string;
  toolName: string;
  riskLevel: string;
  requiresApproval: boolean;
}

/** Payload for MCP_TOOL_CALL_DECIDED event */
export interface MCPToolCallDecidedPayload {
  serverId: string;
  callId: string;
  decision: 'approved' | 'rejected';
  method: 'auto' | 'manual';
  reason: string;
}

/** Payload for APPROVAL_QUEUED event */
export interface ApprovalQueuedPayload {
  pending: PendingApproval;
  queueLength: number;
}

/** Payload for APPROVAL_DECIDED event */
export interface ApprovalDecidedPayload {
  pendingId: string;
  decision: 'approved' | 'rejected';
  method: 'auto' | 'manual';
  reason: string;
  queueLength: number;
}

/** Payload for APPROVAL_EXPIRED event */
export interface ApprovalExpiredPayload {
  pendingId: string;
  source: 'agent_shield' | 'mcp_gateway';
  queueLength: number;
}

/** Payload for APPROVAL_QUEUE_CHANGED event */
export interface ApprovalQueueChangedPayload {
  queueLength: number;
  pendingIds: string[];
}

/** Payload for STATS_UPDATED event */
export interface StatsUpdatedPayload {
  stats: Stats;
  changedFields: (keyof Stats)[];
}

/** Payload for ALERT_CREATED event */
export interface AlertCreatedPayload {
  alert: Alert;
  unacknowledgedCount: number;
}

/** Payload for ALERT_ACKNOWLEDGED event */
export interface AlertAcknowledgedPayload {
  alertId: string;
  unacknowledgedCount: number;
}

// =============================================================================
// EVENT TYPE MAPPING
// =============================================================================

/**
 * Maps event types to their payload types for type safety
 */
export interface BroadcastEventPayloadMap {
  AGENT_CONNECTED: AgentConnectedPayload;
  AGENT_DISCONNECTED: AgentDisconnectedPayload;
  AGENT_UPDATED: AgentUpdatedPayload;
  AGENT_ACTION_INTERCEPTED: AgentActionInterceptedPayload;
  AGENT_ACTION_DECIDED: AgentActionDecidedPayload;
  MCP_SERVER_REGISTERED: MCPServerRegisteredPayload;
  MCP_SERVER_UNREGISTERED: MCPServerUnregisteredPayload;
  MCP_SERVER_UPDATED: MCPServerUpdatedPayload;
  MCP_TOOL_CALL_INTERCEPTED: MCPToolCallInterceptedPayload;
  MCP_TOOL_CALL_DECIDED: MCPToolCallDecidedPayload;
  APPROVAL_QUEUED: ApprovalQueuedPayload;
  APPROVAL_DECIDED: ApprovalDecidedPayload;
  APPROVAL_EXPIRED: ApprovalExpiredPayload;
  APPROVAL_QUEUE_CHANGED: ApprovalQueueChangedPayload;
  STATS_UPDATED: StatsUpdatedPayload;
  ALERT_CREATED: AlertCreatedPayload;
  ALERT_ACKNOWLEDGED: AlertAcknowledgedPayload;
}

// =============================================================================
// BROADCAST EVENT
// =============================================================================

/**
 * A strongly-typed broadcast event
 */
export interface BroadcastEvent<T extends BroadcastEventType = BroadcastEventType> {
  /** Event type identifier */
  type: T;
  /** Event payload */
  payload: BroadcastEventPayloadMap[T];
  /** When the event was created */
  timestamp: number;
  /** Unique event ID for deduplication */
  eventId: string;
}

/**
 * Message structure for chrome.runtime.sendMessage broadcasts
 */
export interface BroadcastMessage<T extends BroadcastEventType = BroadcastEventType> {
  /** Identifies this as a broadcast message */
  isBroadcast: true;
  /** The broadcast event */
  event: BroadcastEvent<T>;
}

// =============================================================================
// SUBSCRIPTION TYPES
// =============================================================================

/**
 * Callback function for event subscriptions
 */
export type EventCallback<T extends BroadcastEventType> = (
  payload: BroadcastEventPayloadMap[T],
  event: BroadcastEvent<T>
) => void;

/**
 * Subscription handle for cleanup
 */
export interface Subscription {
  /** Unique subscription ID */
  id: string;
  /** Event types subscribed to */
  eventTypes: BroadcastEventType[];
  /** Unsubscribe function */
  unsubscribe: () => void;
}

// =============================================================================
// NOTIFICATION TYPES
// =============================================================================

/**
 * Priority levels for notifications
 */
export type NotificationPriority = 'low' | 'default' | 'high' | 'urgent';

/**
 * Options for creating a notification
 */
export interface NotificationOptions {
  /** Notification title */
  title: string;
  /** Notification message */
  message: string;
  /** Priority level */
  priority?: NotificationPriority;
  /** Icon URL */
  iconUrl?: string;
  /** Whether to require user interaction */
  requireInteraction?: boolean;
  /** Buttons to show */
  buttons?: Array<{
    title: string;
    action: string;
  }>;
  /** Data to pass to button click handlers */
  data?: Record<string, unknown>;
  /** Auto-dismiss after ms (0 = no auto-dismiss) */
  autoDismissMs?: number;
}

/**
 * Result of showing a notification
 */
export interface NotificationResult {
  /** Notification ID */
  id: string;
  /** Whether the notification was shown */
  shown: boolean;
  /** Error message if not shown */
  error?: string;
}

// =============================================================================
// BADGE TYPES
// =============================================================================

/**
 * Badge configuration
 */
export interface BadgeConfig {
  /** Text to show on badge (max 4 chars) */
  text: string;
  /** Background color */
  backgroundColor: string;
  /** Text color */
  textColor?: string;
}

/**
 * Predefined badge states
 */
export type BadgeState =
  | 'clear'           // No badge
  | 'pending'         // Has pending approvals
  | 'alert'           // Has unacknowledged alerts
  | 'error'           // Error state
  | 'disabled';       // Extension disabled

// =============================================================================
// TYPE GUARDS
// =============================================================================

/**
 * Type guard to check if a message is a broadcast message
 */
export function isBroadcastMessage(
  message: unknown
): message is BroadcastMessage {
  return (
    typeof message === 'object' &&
    message !== null &&
    'isBroadcast' in message &&
    (message as BroadcastMessage).isBroadcast === true &&
    'event' in message
  );
}

/**
 * Type guard to check if an event is of a specific type
 */
export function isEventType<T extends BroadcastEventType>(
  event: BroadcastEvent,
  type: T
): event is BroadcastEvent<T> {
  return event.type === type;
}
