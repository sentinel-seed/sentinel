/**
 * @fileoverview Sentinel Guard - Background Service Worker
 *
 * Handles:
 * - Message routing between popup and content scripts
 * - Storage management
 * - Notifications
 * - Extension monitoring
 * - Agent Shield operations
 * - MCP Gateway operations
 * - Approval system
 *
 * @author Sentinel Team
 * @license MIT
 */

import { validateTHSP, ValidationContext } from '../lib/thsp';
import { scanAll, PatternMatch } from '../lib/patterns';
import { detectBot, BotDetectionResult } from '../lib/bot-detector';
import { scanForPII, getPIISummary, PIIMatch, PIISummary } from '../lib/pii-guard';
import { scanCurrentClipboard, ClipboardScanResult } from '../lib/clipboard-guard';
import { scanForWalletThreats, analyzeDApp, analyzeTransaction, WalletScanResult, dAppSecurityInfo, TransactionPreview, TransactionType } from '../lib/wallet-guard';

// Agent Shield imports
import * as agentRegistry from '../agent-shield/agent-registry';
import { interceptAction as agentInterceptAction } from '../agent-shield/action-interceptor';
import { scanMemory } from '../agent-shield/memory-scanner';

// MCP Gateway imports
import * as mcpRegistry from '../mcp-gateway/server-registry';
import { interceptToolCall } from '../mcp-gateway/tool-interceptor';

// Approval System imports
import * as approvalStore from '../approval/approval-store';
import * as approvalEngine from '../approval/approval-engine';
import * as approvalQueue from '../approval/approval-queue';

// Types
import {
  Settings,
  Stats,
  Alert,
  ApprovalRule,
  DEFAULT_AGENT_SHIELD_SETTINGS,
  DEFAULT_MCP_GATEWAY_SETTINGS,
  DEFAULT_APPROVAL_SETTINGS,
} from '../types';

// Validation
import {
  validateOrThrow,
  AgentConnectPayloadSchema,
  AgentInterceptActionPayloadSchema,
  MCPRegisterServerPayloadSchema,
  MCPInterceptToolCallPayloadSchema,
  ApprovalDecidePayloadSchema,
  ApprovalCreateRulePayloadSchema,
} from '../validation';

// Messaging system
import {
  broadcastAgent,
  broadcastMCP,
  broadcastApproval,
  broadcastStats,
  broadcastAlert,
  badgeManager,
  notifyApprovalRequired,
  isBroadcastMessage,
} from '../messaging';

// Default settings
const DEFAULT_SETTINGS: Settings = {
  enabled: true,
  protectionLevel: 'recommended',
  platforms: ['chatgpt', 'claude', 'gemini', 'perplexity', 'deepseek', 'grok', 'copilot', 'meta'],
  notifications: true,
  language: 'en',
  agentShield: DEFAULT_AGENT_SHIELD_SETTINGS,
  mcpGateway: DEFAULT_MCP_GATEWAY_SETTINGS,
  approval: DEFAULT_APPROVAL_SETTINGS,
};

const DEFAULT_STATS: Stats = {
  // Core stats
  threatsBlocked: 0,
  secretsCaught: 0,
  sessionsProtected: 0,
  botsDetected: 0,
  piiBlocked: 0,
  clipboardScans: 0,
  walletThreats: 0,
  // Agent Shield stats
  agentConnections: 0,
  agentActionsIntercepted: 0,
  agentActionsApproved: 0,
  agentActionsRejected: 0,
  memoryInjectionAttempts: 0,
  // MCP Gateway stats
  mcpServersRegistered: 0,
  mcpToolCallsIntercepted: 0,
  mcpToolCallsApproved: 0,
  mcpToolCallsRejected: 0,
  // Approval stats
  approvalsPending: 0,
  approvalsAuto: 0,
  approvalsManual: 0,
  rejectionsAuto: 0,
  rejectionsManual: 0,
  // Timestamp
  lastUpdated: Date.now(),
};

// Initialize on install
chrome.runtime.onInstalled.addListener(async (details) => {
  if (details.reason === 'install') {
    await chrome.storage.local.set({
      settings: DEFAULT_SETTINGS,
      stats: DEFAULT_STATS,
      alerts: [],
    });

    // Create default approval rules
    await approvalEngine.createDefaultRules();

    // Initialize badge
    await badgeManager.initialize(0, 0, false);

    console.log('[Sentinel Guard] Extension installed');
  }

  // Setup health check alarm (runs every minute)
  chrome.alarms.create('healthCheck', { periodInMinutes: 1 });

  // Setup approval expiry check alarm
  approvalQueue.setupExpiryCheckAlarm(1);

  // Initialize badge with current state
  const pending = await approvalStore.getPendingApprovals();
  const alerts = await getAlerts();
  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged).length;
  const settings = await getSettings();
  await badgeManager.initialize(pending.length, unacknowledgedAlerts, !settings.enabled);
});

// Handle alarms
chrome.alarms.onAlarm.addListener(async (alarm) => {
  if (alarm.name === 'healthCheck') {
    const settings = await getSettings();
    if (settings.enabled) {
      const stats = await getStats();
      stats.lastUpdated = Date.now();
      await chrome.storage.local.set({ stats });
    }
  }

  // Handle approval expiry check
  if (alarm.name === 'sentinel-approval-expiry-check') {
    const expired = await approvalEngine.processExpiredApprovals();
    if (expired > 0) {
      console.log(`[Sentinel Guard] Processed ${expired} expired approvals`);
    }
  }
});

// Message handler
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  // Ignore broadcast messages (they're outgoing, not requests)
  if (isBroadcastMessage(message)) {
    return false;
  }

  handleMessage(message, sender)
    .then(sendResponse)
    .catch((error) => {
      console.error('[Sentinel Guard] Message error:', error);
      sendResponse({ error: error.message });
    });

  return true; // Keep channel open for async response
});

async function handleMessage(
  message: { type: string; payload?: unknown },
  _sender: chrome.runtime.MessageSender
): Promise<unknown> {
  switch (message.type) {
    case 'GET_SETTINGS':
      return getSettings();

    case 'UPDATE_SETTINGS':
      return updateSettings(message.payload as Partial<Settings>);

    case 'GET_STATS':
      return getStats();

    case 'GET_ALERTS':
      return getAlerts();

    case 'ACKNOWLEDGE_ALERT':
      return acknowledgeAlert(message.payload as string);

    case 'SCAN_TEXT':
      return scanText(message.payload as string);

    case 'VALIDATE_ACTION':
      return validateAction(
        message.payload as { text: string; context: ValidationContext }
      );

    case 'REPORT_THREAT':
      return reportThreat(message.payload as Omit<Alert, 'id' | 'timestamp'>);

    case 'INCREMENT_STAT':
      return incrementStat(message.payload as keyof Stats);

    case 'GET_EXTENSIONS':
      return analyzeExtensions();

    case 'DETECT_BOT':
      return handleBotDetection();

    case 'SCAN_PII':
      return handlePIIScan(message.payload as string);

    case 'SCAN_CLIPBOARD':
      return handleClipboardScan();

    case 'SCAN_WALLET':
      return handleWalletScan(message.payload as string);

    case 'ANALYZE_DAPP':
      return handleDAppAnalysis(message.payload as string);

    case 'PREVIEW_TRANSACTION':
      return handleTransactionPreview(
        message.payload as {
          type: TransactionType;
          from: string;
          to: string;
          value?: string;
          token?: string;
          data?: string;
        }
      );

    // =========================================================================
    // AGENT SHIELD HANDLERS
    // =========================================================================

    case 'AGENT_CONNECT':
      return handleAgentConnect(message.payload);

    case 'AGENT_DISCONNECT':
      return handleAgentDisconnect(message.payload as string);

    case 'AGENT_LIST':
    case 'AGENT_GET_CONNECTIONS':
      return agentRegistry.getAgentConnections();

    case 'AGENT_GET_CONNECTION':
      return agentRegistry.getAgentConnection(message.payload as string);

    case 'AGENT_INTERCEPT_ACTION':
      return handleAgentInterceptAction(message.payload);

    case 'AGENT_SCAN_MEMORY':
      return scanMemory(message.payload as string[]);

    case 'AGENT_UPDATE_TRUST':
      return agentRegistry.updateAgentTrustLevel(
        (message.payload as { agentId: string; trustLevel: number }).agentId,
        (message.payload as { agentId: string; trustLevel: number }).trustLevel
      );

    // =========================================================================
    // MCP GATEWAY HANDLERS
    // =========================================================================

    case 'MCP_REGISTER_SERVER':
      return handleMCPRegisterServer(message.payload);

    case 'MCP_UNREGISTER_SERVER':
      return mcpRegistry.unregisterServer(message.payload as string);

    case 'MCP_LIST_SERVERS':
    case 'MCP_GET_SERVERS':
      return mcpRegistry.getMCPServers();

    case 'MCP_GET_SERVER':
      return mcpRegistry.getMCPServer(message.payload as string);

    case 'MCP_INTERCEPT_TOOL_CALL':
      return handleMCPInterceptToolCall(message.payload);

    case 'MCP_UPDATE_TRUST':
      return mcpRegistry.updateServerTrust(
        (message.payload as { serverId: string; trustLevel: number }).serverId,
        (message.payload as { serverId: string; trustLevel: number }).trustLevel
      );

    case 'MCP_GET_TOOL_HISTORY':
      return approvalStore.getActionHistoryBySource(
        'mcp_gateway',
        (message.payload as { limit?: number })?.limit || 50
      );

    // =========================================================================
    // APPROVAL HANDLERS
    // =========================================================================

    case 'APPROVAL_GET_QUEUE':
      return approvalQueue.getPendingByPriority();

    case 'APPROVAL_GET_PENDING':
      if (!message.payload) {
        return approvalQueue.getPendingByPriority();
      }
      return approvalStore.getPendingApproval(message.payload as string);

    case 'APPROVAL_DECIDE':
      return handleApprovalDecide(message.payload);

    case 'APPROVAL_GET_RULES':
      return approvalStore.getAllRules();

    case 'APPROVAL_CREATE_RULE':
      return handleApprovalCreateRule(message.payload);

    case 'APPROVAL_UPDATE_RULE':
      return approvalStore.updateRule(message.payload as ApprovalRule);

    case 'APPROVAL_DELETE_RULE':
      return approvalStore.deleteRule(message.payload as string);

    case 'APPROVAL_GET_HISTORY':
      return approvalStore.getActionHistory(
        (message.payload as { limit?: number; offset?: number })?.limit,
        (message.payload as { limit?: number; offset?: number })?.offset
      );

    case 'APPROVAL_CLEAR_HISTORY':
      return approvalStore.clearActionHistory();

    // =========================================================================
    // DATA MANAGEMENT HANDLERS
    // =========================================================================

    case 'RESET_SETTINGS':
      return resetSettings();

    case 'CLEAR_ALL_DATA':
      return clearAllData();

    default:
      throw new Error(`Unknown message type: ${message.type}`);
  }
}

// Settings management
async function getSettings(): Promise<Settings> {
  const data = await chrome.storage.local.get('settings');
  return data.settings || DEFAULT_SETTINGS;
}

async function updateSettings(updates: Partial<Settings>): Promise<Settings> {
  const current = await getSettings();
  const updated = { ...current, ...updates };
  await chrome.storage.local.set({ settings: updated });

  // Update badge if enabled state changed
  if ('enabled' in updates) {
    await badgeManager.setDisabled(!updated.enabled);
  }

  return updated;
}

async function resetSettings(): Promise<Settings> {
  await chrome.storage.local.set({ settings: DEFAULT_SETTINGS });
  console.log('[Sentinel Guard] Settings reset to defaults');
  return DEFAULT_SETTINGS;
}

async function clearAllData(): Promise<{ success: boolean }> {
  // Clear all storage
  await chrome.storage.local.clear();

  // Re-initialize with defaults
  await chrome.storage.local.set({
    settings: DEFAULT_SETTINGS,
    stats: DEFAULT_STATS,
    alerts: [],
  });

  // Clear approval data
  await approvalStore.clearActionHistory();
  const rules = await approvalStore.getAllRules();
  for (const rule of rules) {
    await approvalStore.deleteRule(rule.id);
  }

  // Clear agent and MCP registrations
  const agents = await agentRegistry.getAgentConnections();
  for (const agent of agents) {
    await agentRegistry.unregisterAgent(agent.id);
  }

  const servers = await mcpRegistry.getMCPServers();
  for (const server of servers) {
    await mcpRegistry.unregisterServer(server.id);
  }

  // Recreate default rules
  await approvalEngine.createDefaultRules();

  // Reset badge
  await badgeManager.initialize(0, 0, false);

  console.log('[Sentinel Guard] All data cleared');
  return { success: true };
}

// Stats management
async function getStats(): Promise<Stats> {
  const data = await chrome.storage.local.get('stats');
  return data.stats || DEFAULT_STATS;
}

async function incrementStat(stat: keyof Stats): Promise<Stats> {
  const stats = await getStats();
  if (typeof stats[stat] === 'number') {
    (stats[stat] as number)++;
    stats.lastUpdated = Date.now();
    await chrome.storage.local.set({ stats });

    // Broadcast stats updated
    await broadcastStats.updated(stats, [stat, 'lastUpdated']);
  }
  return stats;
}

// Alert management
async function getAlerts(): Promise<Alert[]> {
  const data = await chrome.storage.local.get('alerts');
  return data.alerts || [];
}

async function reportThreat(
  threat: Omit<Alert, 'id' | 'timestamp'>
): Promise<Alert> {
  const alerts = await getAlerts();
  const alert: Alert = {
    ...threat,
    id: crypto.randomUUID(),
    timestamp: Date.now(),
    acknowledged: false,
  };

  alerts.unshift(alert);

  // Keep only last 100 alerts
  if (alerts.length > 100) {
    alerts.length = 100;
  }

  await chrome.storage.local.set({ alerts });

  // Calculate unacknowledged count and update badge
  const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;
  await badgeManager.setAlertCount(unacknowledgedCount);

  // Broadcast alert created
  await broadcastAlert.created(alert, unacknowledgedCount);

  // Show notification
  const settings = await getSettings();
  if (settings.notifications) {
    chrome.notifications.create({
      type: 'basic',
      iconUrl: chrome.runtime.getURL('icons/icon128.png'),
      title: 'Sentinel Guard Alert',
      message: alert.message,
      priority: 2,
    });
  }

  return alert;
}

async function acknowledgeAlert(alertId: string): Promise<boolean> {
  const alerts = await getAlerts();
  const alert = alerts.find((a) => a.id === alertId);
  if (alert) {
    alert.acknowledged = true;
    await chrome.storage.local.set({ alerts });

    // Calculate unacknowledged count and update badge
    const unacknowledgedCount = alerts.filter((a) => !a.acknowledged).length;
    await badgeManager.setAlertCount(unacknowledgedCount);

    // Broadcast alert acknowledged
    await broadcastAlert.acknowledged(alertId, unacknowledgedCount);

    return true;
  }
  return false;
}

// Scanning and validation
async function scanText(
  text: string
): Promise<{ matches: PatternMatch[]; hasCritical: boolean }> {
  const matches = scanAll(text);
  const hasCritical = matches.some((m) => m.severity === 'critical');

  if (hasCritical) {
    await incrementStat('secretsCaught');
  }

  return { matches, hasCritical };
}

async function validateAction(payload: {
  text: string;
  context: ValidationContext;
}): Promise<{ result: ReturnType<typeof validateTHSP>; blocked: boolean }> {
  const result = validateTHSP(payload.text, payload.context);
  const blocked = !result.overall;

  if (blocked) {
    await incrementStat('threatsBlocked');
  }

  return { result, blocked };
}

// Extension monitoring - calculate trust score for installed extensions
async function getInstalledExtensions(): Promise<
  chrome.management.ExtensionInfo[]
> {
  return new Promise((resolve) => {
    chrome.management.getAll((extensions) => {
      resolve(extensions || []);
    });
  });
}

interface ExtensionTrustInfo {
  id: string;
  name: string;
  version: string;
  permissions: string[];
  trustScore: number;
  riskLevel: 'trusted' | 'caution' | 'danger';
  issues: string[];
}

// Risky permissions that lower trust score
const RISKY_PERMISSIONS = [
  'webRequest',
  'webRequestBlocking',
  'cookies',
  'history',
  'tabs',
  '<all_urls>',
  'clipboardRead',
  'clipboardWrite',
  'nativeMessaging',
];

async function analyzeExtensions(): Promise<ExtensionTrustInfo[]> {
  const extensions = await getInstalledExtensions();

  return extensions
    .filter((ext) => ext.enabled && ext.type === 'extension' && ext.id !== chrome.runtime.id)
    .map((ext) => {
      let score = 100;
      const issues: string[] = [];
      const permissions = ext.permissions || [];

      for (const perm of permissions) {
        if (RISKY_PERMISSIONS.includes(perm)) {
          score -= 15;
          issues.push(`Has "${perm}" permission`);
        }
      }

      // Check host permissions
      const hostPerms = ext.hostPermissions || [];
      if (hostPerms.includes('<all_urls>') || hostPerms.includes('*://*/*')) {
        score -= 20;
        issues.push('Can access all websites');
      }

      // Check if it can access AI platforms
      const aiPlatforms = ['chatgpt.com', 'claude.ai', 'gemini.google.com'];
      for (const platform of aiPlatforms) {
        if (hostPerms.some((h: string) => h.includes(platform))) {
          score -= 10;
          issues.push(`Can access ${platform}`);
        }
      }

      score = Math.max(0, score);

      let riskLevel: 'trusted' | 'caution' | 'danger' = 'trusted';
      if (score < 50) riskLevel = 'danger';
      else if (score < 75) riskLevel = 'caution';

      return {
        id: ext.id,
        name: ext.name,
        version: ext.version || '0.0.0',
        permissions,
        trustScore: score,
        riskLevel,
        issues,
      };
    });
}

// Bot detection handler
async function handleBotDetection(): Promise<BotDetectionResult> {
  const result = await detectBot();

  if (result.isBot) {
    await incrementStat('botsDetected');
  }

  return result;
}

// PII scan handler
async function handlePIIScan(
  text: string
): Promise<{ matches: PIIMatch[]; summary: PIISummary }> {
  const matches = scanForPII(text);
  const summary = getPIISummary(text);

  if (summary.highRisk > 0) {
    await incrementStat('piiBlocked');
  }

  return { matches, summary };
}

// Clipboard scan handler
async function handleClipboardScan(): Promise<ClipboardScanResult> {
  await incrementStat('clipboardScans');
  return scanCurrentClipboard();
}

// Wallet scan handler
async function handleWalletScan(text: string): Promise<WalletScanResult> {
  const result = scanForWalletThreats(text);

  if (result.hasRisk) {
    await incrementStat('walletThreats');
  }

  return result;
}

// dApp analysis handler
async function handleDAppAnalysis(url: string): Promise<dAppSecurityInfo> {
  return analyzeDApp(url);
}

// Transaction preview handler
async function handleTransactionPreview(payload: {
  type: TransactionType;
  from: string;
  to: string;
  value?: string;
  token?: string;
  data?: string;
}): Promise<TransactionPreview> {
  return analyzeTransaction(
    payload.type,
    payload.from,
    payload.to,
    payload.value,
    payload.token,
    payload.data
  );
}

// =============================================================================
// AGENT SHIELD HANDLERS
// =============================================================================

async function handleAgentConnect(
  rawPayload: unknown
): Promise<ReturnType<typeof agentRegistry.registerAgent>> {
  const payload = validateOrThrow(
    AgentConnectPayloadSchema,
    rawPayload,
    'AGENT_CONNECT'
  );

  const agent = await agentRegistry.registerAgent(
    payload.name,
    payload.type,
    payload.endpoint,
    payload.metadata
  );

  await incrementStat('agentConnections');

  // Report alert
  await reportThreat({
    type: 'agent_connected',
    severity: 'info',
    message: `Agent connected: ${payload.name} (${payload.type})`,
    acknowledged: false,
    source: 'agent_shield',
    relatedEntityId: agent.id,
  });

  // Broadcast event
  await broadcastAgent.connected(agent);

  return agent;
}

async function handleAgentDisconnect(agentId: string): Promise<boolean> {
  const agent = await agentRegistry.getAgentConnection(agentId);
  if (!agent) {
    return false;
  }

  const result = await agentRegistry.unregisterAgent(agentId);

  if (result) {
    await reportThreat({
      type: 'agent_disconnected',
      severity: 'info',
      message: `Agent disconnected: ${agent.name}`,
      acknowledged: false,
      source: 'agent_shield',
      relatedEntityId: agentId,
    });

    // Broadcast event
    await broadcastAgent.disconnected(agentId, agent.name);
  }

  return result;
}

async function handleAgentInterceptAction(
  rawPayload: unknown
): Promise<ReturnType<typeof agentInterceptAction>> {
  const payload = validateOrThrow(
    AgentInterceptActionPayloadSchema,
    rawPayload,
    'AGENT_INTERCEPT_ACTION'
  );

  await incrementStat('agentActionsIntercepted');

  const settings = await getSettings();
  const result = await agentInterceptAction(
    payload.agentId,
    payload.type,
    payload.description,
    payload.params,
    {
      estimatedValueUsd: payload.estimatedValueUsd,
      memoryEntries: payload.memoryEntries,
      showNotification: settings.approval.showNotifications,
      autoRejectTimeoutMs: settings.approval.autoRejectTimeoutMs,
    }
  );

  // Get agent for broadcast
  const agent = await agentRegistry.getAgentConnection(payload.agentId);
  const agentName = agent?.name || payload.agentId;

  // Update stats and broadcast based on decision
  if (result.decision === 'approved') {
    await incrementStat('agentActionsApproved');
    await broadcastAgent.actionDecided({
      agentId: payload.agentId,
      actionId: result.action.id,
      decision: 'approved',
      method: result.action.decision?.method || 'auto',
      reason: result.action.decision?.reason || 'Auto-approved',
    });
  } else if (result.decision === 'rejected') {
    await incrementStat('agentActionsRejected');
    await broadcastAgent.actionDecided({
      agentId: payload.agentId,
      actionId: result.action.id,
      decision: 'rejected',
      method: result.action.decision?.method || 'auto',
      reason: result.action.decision?.reason || 'Auto-rejected',
    });

    // Check for memory injection
    if (result.action.memoryContext?.isCompromised) {
      await incrementStat('memoryInjectionAttempts');
    }
  } else if (result.decision === 'pending') {
    await incrementStat('approvalsPending');
    await badgeManager.incrementPending();

    // Get updated pending list for broadcast
    const pending = await approvalStore.getPendingApprovals();

    // Broadcast intercepted action
    await broadcastAgent.actionIntercepted({
      agentId: payload.agentId,
      agentName,
      actionId: result.action.id,
      actionType: payload.type,
      riskLevel: result.action.riskLevel,
      requiresApproval: true,
    });

    // Broadcast queue changed
    await broadcastApproval.queueChanged(pending.length, pending.map((p) => p.id));

    // Show notification if enabled
    if (settings.approval.showNotifications) {
      await notifyApprovalRequired(
        agentName,
        payload.type,
        result.action.riskLevel
      );
    }
  }

  return result;
}

// =============================================================================
// MCP GATEWAY HANDLERS
// =============================================================================

async function handleMCPRegisterServer(
  rawPayload: unknown
): Promise<ReturnType<typeof mcpRegistry.registerServer>> {
  const payload = validateOrThrow(
    MCPRegisterServerPayloadSchema,
    rawPayload,
    'MCP_REGISTER_SERVER'
  );

  const server = await mcpRegistry.registerServer(
    payload.name,
    payload.endpoint,
    payload.transport,
    payload.tools?.map((t) => ({
      ...t,
      riskLevel: 'medium' as const,
      requiresApproval: true,
    })) || [],
    {
      description: payload.description,
      trustLevel: payload.trustLevel,
      isTrusted: payload.isTrusted,
    }
  );

  await incrementStat('mcpServersRegistered');

  await reportThreat({
    type: 'mcp_server_registered',
    severity: 'info',
    message: `MCP Server registered: ${payload.name}`,
    acknowledged: false,
    source: 'mcp_gateway',
    relatedEntityId: server.id,
  });

  // Broadcast event
  await broadcastMCP.serverRegistered(server);

  return server;
}

async function handleMCPInterceptToolCall(
  rawPayload: unknown
): Promise<ReturnType<typeof interceptToolCall>> {
  const payload = validateOrThrow(
    MCPInterceptToolCallPayloadSchema,
    rawPayload,
    'MCP_INTERCEPT_TOOL_CALL'
  );

  await incrementStat('mcpToolCallsIntercepted');

  const settings = await getSettings();
  const result = await interceptToolCall(
    payload.serverId,
    payload.toolName,
    payload.args,
    payload.source,
    {
      showNotification: settings.approval.showNotifications,
      autoRejectTimeoutMs: settings.approval.autoRejectTimeoutMs,
    }
  );

  // Get server for broadcast
  const server = await mcpRegistry.getMCPServer(payload.serverId);
  const serverName = server?.name || payload.serverId;

  // Update stats and broadcast based on decision
  if (result.decision === 'approved') {
    await incrementStat('mcpToolCallsApproved');
    await broadcastMCP.toolCallDecided({
      serverId: payload.serverId,
      callId: result.toolCall.id,
      decision: 'approved',
      method: result.toolCall.decision?.method || 'auto',
      reason: result.toolCall.decision?.reason || 'Auto-approved',
    });
  } else if (result.decision === 'rejected') {
    await incrementStat('mcpToolCallsRejected');
    await broadcastMCP.toolCallDecided({
      serverId: payload.serverId,
      callId: result.toolCall.id,
      decision: 'rejected',
      method: result.toolCall.decision?.method || 'auto',
      reason: result.toolCall.decision?.reason || 'Auto-rejected',
    });
  } else if (result.decision === 'pending') {
    await incrementStat('approvalsPending');
    await badgeManager.incrementPending();

    // Get updated pending list for broadcast
    const pending = await approvalStore.getPendingApprovals();

    // Broadcast intercepted tool call
    await broadcastMCP.toolCallIntercepted({
      serverId: payload.serverId,
      serverName,
      callId: result.toolCall.id,
      toolName: payload.toolName,
      riskLevel: result.toolCall.riskLevel,
      requiresApproval: true,
    });

    // Broadcast queue changed
    await broadcastApproval.queueChanged(pending.length, pending.map((p) => p.id));

    // Show notification if enabled
    if (settings.approval.showNotifications) {
      await notifyApprovalRequired(
        serverName,
        payload.toolName,
        result.toolCall.riskLevel
      );
    }
  }

  return result;
}

// =============================================================================
// APPROVAL HANDLERS
// =============================================================================

async function handleApprovalDecide(
  rawPayload: unknown
): Promise<ReturnType<typeof approvalEngine.decidePending>> {
  const payload = validateOrThrow(
    ApprovalDecidePayloadSchema,
    rawPayload,
    'APPROVAL_DECIDE'
  );

  const decision = await approvalEngine.decidePending(
    payload.pendingId,
    payload.action,
    payload.reason,
    payload.modifiedParams
  );

  if (decision) {
    // Update stats
    if (decision.action === 'approve') {
      await incrementStat('approvalsManual');
    } else {
      await incrementStat('rejectionsManual');
    }

    // Decrement pending count
    const stats = await getStats();
    if (stats.approvalsPending > 0) {
      stats.approvalsPending--;
      await chrome.storage.local.set({ stats });
    }

    // Update badge
    await badgeManager.decrementPending();

    // Get remaining pending count
    const pending = await approvalStore.getPendingApprovals();

    // Broadcast decision
    await broadcastApproval.decided({
      pendingId: payload.pendingId,
      decision: decision.action === 'approve' ? 'approved' : 'rejected',
      method: 'manual',
      reason: payload.reason,
      queueLength: pending.length,
    });

    // Broadcast queue changed
    await broadcastApproval.queueChanged(pending.length, pending.map((p) => p.id));
  }

  return decision;
}

async function handleApprovalCreateRule(
  rawPayload: unknown
): Promise<ApprovalRule> {
  const payload = validateOrThrow(
    ApprovalCreateRulePayloadSchema,
    rawPayload,
    'APPROVAL_CREATE_RULE'
  );

  const rule: ApprovalRule = {
    ...payload,
    id: crypto.randomUUID(),
    createdAt: Date.now(),
    updatedAt: Date.now(),
  };

  return approvalStore.createRule(rule);
}

console.log('[Sentinel Guard] Background service worker started');
