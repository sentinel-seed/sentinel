/**
 * @fileoverview Sentinel Guard - Type Definitions
 *
 * This module contains all TypeScript type definitions for the Sentinel Guard
 * browser extension. Types are organized by domain:
 *
 * - Core: Settings, Stats, Alerts
 * - Agent Shield: Agent connections and actions
 * - MCP Gateway: MCP tool calls and servers
 * - Approval System: Rules, queue, and decisions
 *
 * @author Sentinel Team
 * @license MIT
 */

// =============================================================================
// CONSTANTS
// =============================================================================

/** Extension version - single source of truth */
export const EXTENSION_VERSION = '0.1.0';

// =============================================================================
// CORE TYPES
// =============================================================================

/** Supported UI languages */
export type Language = 'en' | 'es' | 'pt';

/** User-configurable settings */
export interface Settings {
  /** Whether protection is enabled */
  enabled: boolean;
  /** Protection strictness level */
  protectionLevel: 'basic' | 'recommended' | 'maximum';
  /** AI platforms to monitor */
  platforms: string[];
  /** Whether to show notifications */
  notifications: boolean;
  /** UI language */
  language: Language;
  /** Agent Shield settings */
  agentShield: AgentShieldSettings;
  /** MCP Gateway settings */
  mcpGateway: MCPGatewaySettings;
  /** Approval system settings */
  approval: ApprovalSettings;
}

/** Agent Shield specific settings */
export interface AgentShieldSettings {
  /** Whether Agent Shield is enabled */
  enabled: boolean;
  /** Trust level threshold for auto-approval (0-100) */
  trustThreshold: number;
  /** Whether to scan for memory injection */
  memoryInjectionDetection: boolean;
  /** Maximum action value before requiring approval (in USD) */
  maxAutoApproveValue: number;
}

/** MCP Gateway specific settings */
export interface MCPGatewaySettings {
  /** Whether MCP Gateway is enabled */
  enabled: boolean;
  /** Whether to intercept all MCP tool calls */
  interceptAll: boolean;
  /** List of trusted MCP server IDs */
  trustedServers: string[];
}

/** Approval system settings */
export interface ApprovalSettings {
  /** Whether approval system is enabled */
  enabled: boolean;
  /** Default action for unmatched rules */
  defaultAction: ApprovalAction;
  /** Whether to show approval notifications */
  showNotifications: boolean;
  /** Auto-reject after timeout (ms), 0 for no timeout */
  autoRejectTimeoutMs: number;
}

// =============================================================================
// STATISTICS
// =============================================================================

/** Aggregated statistics for the extension */
export interface Stats {
  // Core protection stats
  /** Number of threats blocked by THSP */
  threatsBlocked: number;
  /** Number of secrets/API keys caught */
  secretsCaught: number;
  /** Number of sessions protected */
  sessionsProtected: number;
  /** Number of bots detected */
  botsDetected: number;
  /** Number of PII exposure attempts blocked */
  piiBlocked: number;
  /** Number of clipboard scans performed */
  clipboardScans: number;
  /** Number of wallet threats detected */
  walletThreats: number;

  // Agent Shield stats
  /** Number of agent connections established */
  agentConnections: number;
  /** Number of agent actions intercepted */
  agentActionsIntercepted: number;
  /** Number of agent actions approved */
  agentActionsApproved: number;
  /** Number of agent actions rejected */
  agentActionsRejected: number;
  /** Number of memory injection attempts detected */
  memoryInjectionAttempts: number;

  // MCP Gateway stats
  /** Number of MCP servers registered */
  mcpServersRegistered: number;
  /** Number of MCP tool calls intercepted */
  mcpToolCallsIntercepted: number;
  /** Number of MCP tool calls approved */
  mcpToolCallsApproved: number;
  /** Number of MCP tool calls rejected */
  mcpToolCallsRejected: number;

  // Approval stats
  /** Number of approvals pending */
  approvalsPending: number;
  /** Number of auto-approved actions */
  approvalsAuto: number;
  /** Number of manually approved actions */
  approvalsManual: number;
  /** Number of auto-rejected actions */
  rejectionsAuto: number;
  /** Number of manually rejected actions */
  rejectionsManual: number;

  /** Last stats update timestamp */
  lastUpdated: number;
}

// =============================================================================
// ALERTS
// =============================================================================

/** Types of alerts that can be raised */
export type AlertType =
  // Core protection alerts
  | 'harvest'               // Data harvesting attempt
  | 'secret'                // Secret/API key detected
  | 'bot'                   // Bot/automation detected
  | 'phishing'              // Phishing attempt
  | 'pii'                   // PII exposure
  | 'clipboard'             // Clipboard threat
  | 'wallet'                // Wallet/crypto threat
  | 'dapp'                  // dApp security alert
  // Agent Shield alerts
  | 'agent_connected'       // New agent connected
  | 'agent_disconnected'    // Agent disconnected
  | 'agent_action_blocked'  // Agent action blocked
  | 'memory_injection'      // Memory injection attempt detected
  // MCP Gateway alerts
  | 'mcp_server_registered' // New MCP server registered
  | 'mcp_server_removed'    // MCP server removed
  | 'mcp_tool_blocked'      // MCP tool call blocked
  // Approval alerts
  | 'approval_required'     // Manual approval required
  | 'approval_timeout'      // Approval timed out
  | 'approval_auto_reject'; // Action auto-rejected

/** Alert severity levels */
export type AlertSeverity = 'info' | 'warning' | 'error' | 'critical';

/** An alert raised by the extension */
export interface Alert {
  /** Unique identifier */
  id: string;
  /** Type of alert */
  type: AlertType;
  /** Severity level */
  severity: AlertSeverity;
  /** Human-readable message */
  message: string;
  /** When the alert was created */
  timestamp: number;
  /** Whether the user has acknowledged the alert */
  acknowledged: boolean;
  /** Additional structured details */
  details?: Record<string, unknown>;
  /** Related entity ID (agent, MCP server, approval, etc.) */
  relatedEntityId?: string;
  /** Source of the alert */
  source?: 'core' | 'agent_shield' | 'mcp_gateway' | 'approval';
}

// Pattern matching
export interface PatternMatch {
  type: string;
  value: string;
  start: number;
  end: number;
  severity: 'critical' | 'high' | 'medium' | 'low';
  message: string;
}

// THSP
export interface GateResult {
  passed: boolean;
  score: number;
  issues: string[];
}

export interface THSPResult {
  truth: GateResult;
  harm: GateResult;
  scope: GateResult;
  purpose: GateResult;
  overall: boolean;
  summary: string;
}

export interface ValidationContext {
  source: 'user' | 'extension' | 'page' | 'unknown';
  platform: string;
  action: 'send' | 'copy' | 'export' | 'share';
  userConfirmed?: boolean;
}

// Extension Trust Score
export interface ExtensionInfo {
  id: string;
  name: string;
  version: string;
  permissions: string[];
  trustScore: number;
  riskLevel: 'trusted' | 'caution' | 'danger';
  issues: string[];
}

// =============================================================================
// AGENT SHIELD TYPES
// =============================================================================

/** Supported agent frameworks */
export type AgentType = 'elizaos' | 'autogpt' | 'crewai' | 'langchain' | 'custom';

/** Agent connection status */
export type AgentConnectionStatus =
  | 'connected'     // Active connection
  | 'disconnected'  // No active connection
  | 'pending'       // Awaiting connection confirmation
  | 'error';        // Connection error

/** Types of actions an agent can perform */
export type AgentActionType =
  | 'transfer'      // Token/crypto transfer
  | 'swap'          // Token swap
  | 'approval'      // Token approval/allowance
  | 'sign'          // Message signing
  | 'execute'       // Contract execution
  | 'deploy'        // Contract deployment
  | 'stake'         // Staking operation
  | 'unstake'       // Unstaking operation
  | 'bridge'        // Cross-chain bridge
  | 'mint'          // NFT/token minting
  | 'burn'          // Token burning
  | 'message'       // Send message to another agent/service
  | 'api_call'      // External API call
  | 'file_access'   // File system access
  | 'mcp_tool';     // MCP tool call

/** Represents an agent connection */
export interface AgentConnection {
  /** Unique identifier for this connection */
  id: string;
  /** Human-readable name of the agent */
  name: string;
  /** Type of agent framework */
  type: AgentType;
  /** Connection status */
  status: AgentConnectionStatus;
  /** Endpoint URL or identifier */
  endpoint: string;
  /** Trust level (0-100) based on history and configuration */
  trustLevel: number;
  /** When the connection was established */
  connectedAt: number;
  /** Last activity timestamp */
  lastActivityAt: number;
  /** Agent statistics */
  stats: AgentConnectionStats;
  /** Agent metadata */
  metadata?: Record<string, unknown>;
}

/** Statistics for an agent connection */
export interface AgentConnectionStats {
  /** Total actions attempted */
  actionsTotal: number;
  /** Actions approved (auto or manual) */
  actionsApproved: number;
  /** Actions rejected (auto or manual) */
  actionsRejected: number;
  /** Actions pending approval */
  actionsPending: number;
  /** Memory injection attempts detected */
  memoryInjectionAttempts: number;
}

/** Represents an action attempted by an agent */
export interface AgentAction {
  /** Unique identifier for this action */
  id: string;
  /** ID of the agent that initiated the action */
  agentId: string;
  /** Name of the agent (for display) */
  agentName: string;
  /** Type of action */
  type: AgentActionType;
  /** Human-readable description of the action */
  description: string;
  /** Action parameters */
  params: Record<string, unknown>;
  /** THSP validation result */
  thspResult: THSPResult;
  /** Calculated risk level */
  riskLevel: RiskLevel;
  /** Estimated value in USD (if applicable) */
  estimatedValueUsd?: number;
  /** When the action was intercepted */
  timestamp: number;
  /** Current status */
  status: ActionStatus;
  /** Decision that was made */
  decision?: ApprovalDecision;
  /** Memory context snapshot (for injection detection) */
  memoryContext?: MemoryContext;
}

/** Memory context for injection detection */
export interface MemoryContext {
  /** Hash of the memory state */
  hash: string;
  /** Number of memory entries */
  entryCount: number;
  /** Suspicious entries detected */
  suspiciousEntries: MemorySuspicion[];
  /** Whether memory appears manipulated */
  isCompromised: boolean;
}

/** A suspicious memory entry */
export interface MemorySuspicion {
  /** The suspicious content */
  content: string;
  /** Why it's suspicious */
  reason: string;
  /** When the entry was added */
  addedAt: number;
  /** Confidence level (0-100) */
  confidence: number;
}

// =============================================================================
// MCP GATEWAY TYPES
// =============================================================================

/** Represents a registered MCP server */
export interface MCPServer {
  /** Unique identifier */
  id: string;
  /** Server name */
  name: string;
  /** Server description */
  description?: string;
  /** Server endpoint URL */
  endpoint: string;
  /** Transport type */
  transport: 'http' | 'stdio' | 'websocket';
  /** Trust level (0-100) */
  trustLevel: number;
  /** Whether this server is trusted (in whitelist) */
  isTrusted: boolean;
  /** Available tools */
  tools: MCPTool[];
  /** When the server was registered */
  registeredAt: number;
  /** Last activity timestamp */
  lastActivityAt: number;
  /** Server statistics */
  stats: MCPServerStats;
}

/** Statistics for an MCP server */
export interface MCPServerStats {
  /** Total tool calls */
  toolCallsTotal: number;
  /** Tool calls approved */
  toolCallsApproved: number;
  /** Tool calls rejected */
  toolCallsRejected: number;
  /** Tool calls pending */
  toolCallsPending: number;
}

/** Represents an MCP tool */
export interface MCPTool {
  /** Tool name */
  name: string;
  /** Tool description */
  description?: string;
  /** JSON schema for tool parameters */
  inputSchema?: Record<string, unknown>;
  /** Risk level assigned to this tool */
  riskLevel: RiskLevel;
  /** Whether this tool requires approval */
  requiresApproval: boolean;
}

/** Represents an MCP tool call */
export interface MCPToolCall {
  /** Unique identifier */
  id: string;
  /** Server that provides the tool */
  serverId: string;
  /** Server name (for display) */
  serverName: string;
  /** Tool being called */
  tool: string;
  /** Tool arguments */
  arguments: Record<string, unknown>;
  /** Source of the call */
  source: MCPClientSource;
  /** THSP validation result */
  thspResult: THSPResult;
  /** Calculated risk level */
  riskLevel: RiskLevel;
  /** When the call was intercepted */
  timestamp: number;
  /** Current status */
  status: ActionStatus;
  /** Decision that was made */
  decision?: ApprovalDecision;
  /** Result of the tool call (if executed) */
  result?: unknown;
  /** Error (if any) */
  error?: string;
}

/** Known MCP client sources */
export type MCPClientSource =
  | 'claude_desktop'
  | 'cursor'
  | 'windsurf'
  | 'vscode'
  | 'custom';

// =============================================================================
// APPROVAL SYSTEM TYPES
// =============================================================================

/** Risk levels for actions */
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

/** Status of an action in the approval flow */
export type ActionStatus =
  | 'pending'       // Awaiting decision
  | 'approved'      // Approved (auto or manual)
  | 'rejected'      // Rejected (auto or manual)
  | 'executed'      // Executed successfully
  | 'failed'        // Execution failed
  | 'timeout';      // Approval timed out

/** Possible approval actions */
export type ApprovalAction = 'auto_approve' | 'auto_reject' | 'require_approval';

/** Decision made on an action */
export interface ApprovalDecision {
  /** The action taken */
  action: 'approve' | 'reject' | 'modify';
  /** Whether this was automatic or manual */
  method: 'auto' | 'manual';
  /** ID of the rule that matched (if auto) */
  ruleId?: string;
  /** Reason for the decision */
  reason: string;
  /** When the decision was made */
  timestamp: number;
  /** Modified parameters (if action was 'modify') */
  modifiedParams?: Record<string, unknown>;
}

/** An approval rule that determines how to handle actions */
export interface ApprovalRule {
  /** Unique identifier */
  id: string;
  /** Human-readable name */
  name: string;
  /** Rule description */
  description?: string;
  /** Priority (higher = evaluated first) */
  priority: number;
  /** Whether this rule is enabled */
  enabled: boolean;
  /** Conditions that must match for this rule to apply */
  conditions: RuleCondition[];
  /** Action to take when rule matches */
  action: ApprovalAction;
  /** Reason to show when this rule applies */
  reason?: string;
  /** When the rule was created */
  createdAt: number;
  /** When the rule was last updated */
  updatedAt: number;
}

/** A condition in an approval rule */
export interface RuleCondition {
  /** Field to evaluate */
  field: RuleConditionField;
  /** Operator for comparison */
  operator: RuleConditionOperator;
  /** Value to compare against */
  value: string | number | boolean | string[];
}

/** Fields that can be evaluated in rule conditions */
export type RuleConditionField =
  // Common fields
  | 'source'            // agent_shield or mcp_gateway
  | 'riskLevel'         // low, medium, high, critical
  | 'estimatedValueUsd' // Numeric value
  // Agent Shield fields
  | 'agentType'         // elizaos, autogpt, etc.
  | 'agentTrustLevel'   // 0-100
  | 'actionType'        // transfer, swap, etc.
  | 'memoryCompromised' // boolean
  // MCP Gateway fields
  | 'mcpServerTrusted'  // boolean
  | 'mcpToolName'       // string
  | 'mcpSource';        // claude_desktop, cursor, etc.

/** Operators for rule condition evaluation */
export type RuleConditionOperator =
  | 'equals'
  | 'not_equals'
  | 'greater_than'
  | 'less_than'
  | 'greater_than_or_equals'
  | 'less_than_or_equals'
  | 'contains'
  | 'not_contains'
  | 'in'
  | 'not_in'
  | 'matches_regex';

/** An item in the approval queue */
export interface PendingApproval {
  /** Unique identifier */
  id: string;
  /** Source of the pending action */
  source: 'agent_shield' | 'mcp_gateway';
  /** The action waiting for approval */
  action: AgentAction | MCPToolCall;
  /** When the approval was queued */
  queuedAt: number;
  /** When the approval will timeout (if configured) */
  expiresAt?: number;
  /** Number of times this has been shown to the user */
  viewCount: number;
}

/** Entry in the action history */
export interface ActionHistoryEntry {
  /** Unique identifier */
  id: string;
  /** Source of the action */
  source: 'agent_shield' | 'mcp_gateway';
  /** The action that was processed */
  action: AgentAction | MCPToolCall;
  /** Decision that was made */
  decision: ApprovalDecision;
  /** When the action was processed */
  processedAt: number;
}

// =============================================================================
// MESSAGE TYPES (EXPANDED)
// =============================================================================

/** All message types supported by the extension */
export type MessageType =
  // Core messages
  | 'GET_SETTINGS'
  | 'UPDATE_SETTINGS'
  | 'GET_STATS'
  | 'GET_ALERTS'
  | 'ACKNOWLEDGE_ALERT'
  | 'SCAN_TEXT'
  | 'VALIDATE_ACTION'
  | 'REPORT_THREAT'
  | 'INCREMENT_STAT'
  | 'GET_EXTENSIONS'
  | 'SCAN_PAGE'
  | 'DETECT_BOT'
  | 'SCAN_PII'
  | 'SCAN_CLIPBOARD'
  | 'SCAN_WALLET'
  | 'ANALYZE_DAPP'
  | 'PREVIEW_TRANSACTION'
  // Agent Shield messages
  | 'AGENT_CONNECT'
  | 'AGENT_DISCONNECT'
  | 'AGENT_GET_CONNECTIONS'
  | 'AGENT_GET_CONNECTION'
  | 'AGENT_INTERCEPT_ACTION'
  | 'AGENT_SCAN_MEMORY'
  | 'AGENT_UPDATE_TRUST'
  // MCP Gateway messages
  | 'MCP_REGISTER_SERVER'
  | 'MCP_UNREGISTER_SERVER'
  | 'MCP_GET_SERVERS'
  | 'MCP_GET_SERVER'
  | 'MCP_INTERCEPT_TOOL_CALL'
  | 'MCP_UPDATE_TRUST'
  // Approval messages
  | 'APPROVAL_GET_QUEUE'
  | 'APPROVAL_GET_PENDING'
  | 'APPROVAL_DECIDE'
  | 'APPROVAL_GET_RULES'
  | 'APPROVAL_CREATE_RULE'
  | 'APPROVAL_UPDATE_RULE'
  | 'APPROVAL_DELETE_RULE'
  | 'APPROVAL_GET_HISTORY'
  | 'APPROVAL_CLEAR_HISTORY';

/** Message structure */
export interface Message {
  /** Message type */
  type: MessageType;
  /** Message payload */
  payload?: unknown;
}

// =============================================================================
// DATABASE SCHEMA (for IndexedDB)
// =============================================================================

/** IndexedDB database schema */
export interface SentinelDB {
  /** Agent connections store */
  agents: AgentConnection;
  /** MCP servers store */
  mcpServers: MCPServer;
  /** Approval rules store */
  approvalRules: ApprovalRule;
  /** Pending approvals store */
  pendingApprovals: PendingApproval;
  /** Action history store */
  actionHistory: ActionHistoryEntry;
  /** Alerts store */
  alerts: Alert;
}

// =============================================================================
// DEFAULT VALUES
// =============================================================================

/** Default settings for Agent Shield */
export const DEFAULT_AGENT_SHIELD_SETTINGS: AgentShieldSettings = {
  enabled: true,
  trustThreshold: 70,
  memoryInjectionDetection: true,
  maxAutoApproveValue: 100, // $100 USD
};

/** Default settings for MCP Gateway */
export const DEFAULT_MCP_GATEWAY_SETTINGS: MCPGatewaySettings = {
  enabled: true,
  interceptAll: true,
  trustedServers: [],
};

/** Default settings for Approval System */
export const DEFAULT_APPROVAL_SETTINGS: ApprovalSettings = {
  enabled: true,
  defaultAction: 'require_approval',
  showNotifications: true,
  autoRejectTimeoutMs: 300000, // 5 minutes
};
