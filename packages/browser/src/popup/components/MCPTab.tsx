/**
 * @fileoverview MCP tab component for managing MCP servers and tool calls
 *
 * Displays:
 * - Registered MCP servers with trust levels
 * - Available tools per server
 * - Tool call history with validation results
 *
 * Features:
 * - Full accessibility support
 * - Confirmation dialogs for destructive actions
 * - Error handling with user feedback
 * - Skeleton loading states
 *
 * @author Sentinel Team
 * @license MIT
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import type { MCPServer, MCPToolCall } from '../../types';
import { t } from '../../lib/i18n';
import { ConfirmDialog } from './ui/ConfirmDialog';
import { ErrorMessage } from './ui/ErrorMessage';
import { SkeletonCard, SkeletonList, SkeletonTabs } from './ui/SkeletonLoader';
import { useSubscription, useAnnounce } from '../hooks';
import {
  getTransportIcon,
  getServerName,
  getToolRiskLevel,
  getRiskIcon,
  truncateEndpoint,
  formatTime,
} from '../utils';
import { styles, mcpStyles } from './styles';

interface MCPTabProps {
  /** Callback when stats should be refreshed */
  onStatsUpdate?: () => void;
}

/**
 * Tab component for managing MCP servers and tool calls
 */
export const MCPTab: React.FC<MCPTabProps> = ({ onStatsUpdate }) => {
  // State
  const [servers, setServers] = useState<MCPServer[]>([]);
  const [toolCalls, setToolCalls] = useState<MCPToolCall[]>([]);
  const [activeSection, setActiveSection] = useState<'servers' | 'tools' | 'history'>('servers');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedServer, setExpandedServer] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    serverId: string;
    serverName: string;
  }>({ isOpen: false, serverId: '', serverName: '' });

  const announce = useAnnounce();

  // Load data from background
  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [serversRes, historyRes] = await Promise.all([
        chrome.runtime.sendMessage({ type: 'MCP_LIST_SERVERS' }),
        chrome.runtime.sendMessage({ type: 'MCP_GET_TOOL_HISTORY', payload: { limit: 50 } }),
      ]);

      setServers(serversRes || []);
      setToolCalls(historyRes || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
      console.error('[MCPTab] Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Subscribe to real-time updates
  useSubscription(
    ['MCP_STATE_CHANGED'],
    () => {
      loadData();
    }
  );

  // Memoized all tools from all servers
  const allTools = useMemo(() =>
    servers.flatMap((server) =>
      server.tools.map((tool) => ({
        ...tool,
        serverName: server.name,
        serverId: server.id,
      }))
    ),
    [servers]
  );

  // Open confirmation dialog
  const openUnregisterConfirm = (serverId: string, serverName: string) => {
    setConfirmDialog({ isOpen: true, serverId, serverName });
  };

  // Handle unregister with confirmation
  const handleUnregister = async () => {
    const { serverId, serverName } = confirmDialog;
    try {
      setIsProcessing(true);
      await chrome.runtime.sendMessage({
        type: 'MCP_UNREGISTER_SERVER',
        payload: { serverId },
      });
      await loadData();
      onStatsUpdate?.();
      announce(`${serverName} unregistered successfully`, 'polite');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to unregister server';
      setError(message);
      announce(`Error: ${message}`, 'assertive');
    } finally {
      setIsProcessing(false);
      setConfirmDialog({ isOpen: false, serverId: '', serverName: '' });
    }
  };

  // Handle trust toggle
  const handleToggleTrust = async (serverId: string, isTrusted: boolean) => {
    try {
      await chrome.runtime.sendMessage({
        type: 'MCP_UPDATE_SERVER',
        payload: { serverId, updates: { isTrusted: !isTrusted } },
      });
      await loadData();
      announce(`Server trust ${!isTrusted ? 'enabled' : 'disabled'}`, 'polite');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to update trust';
      setError(message);
      announce(`Error: ${message}`, 'assertive');
    }
  };

  // Toggle expanded server
  const handleToggleExpanded = (serverId: string) => {
    setExpandedServer(expandedServer === serverId ? null : serverId);
  };

  // Retry after error
  const handleRetry = () => {
    setLoading(true);
    loadData();
  };

  // Loading state with skeleton
  if (loading) {
    return (
      <div role="status" aria-label={t('loading')}>
        <SkeletonTabs tabs={3} />
        <SkeletonCard />
        <SkeletonCard />
      </div>
    );
  }

  return (
    <div>
      {/* Error Message */}
      {error && (
        <ErrorMessage
          message={error}
          severity="error"
          onRetry={handleRetry}
          onDismiss={() => setError(null)}
        />
      )}

      {/* Section Tabs */}
      <nav
        role="tablist"
        aria-label={t('mcp')}
        style={mcpStyles.sectionTabs}
      >
        {(['servers', 'tools', 'history'] as const).map((section) => (
          <button
            key={section}
            role="tab"
            type="button"
            id={`mcp-tab-${section}`}
            aria-selected={activeSection === section}
            aria-controls={`mcp-panel-${section}`}
            onClick={() => setActiveSection(section)}
            style={{
              ...mcpStyles.sectionTab,
              ...(activeSection === section ? mcpStyles.sectionTabActive : {}),
            }}
            tabIndex={activeSection === section ? 0 : -1}
          >
            {section === 'servers' && `${t('servers')} (${servers.length})`}
            {section === 'tools' && `${t('tools')} (${allTools.length})`}
            {section === 'history' && t('history')}
          </button>
        ))}
      </nav>

      {/* Servers Section */}
      <section
        id="mcp-panel-servers"
        role="tabpanel"
        aria-labelledby="mcp-tab-servers"
        hidden={activeSection !== 'servers'}
      >
        {activeSection === 'servers' && (
          servers.length === 0 ? (
            <EmptyState
              icon="🔌"
              title={t('noMCPServers')}
              description={t('noMCPServersDesc')}
            />
          ) : (
            <ul role="list" aria-label={t('servers')} style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {servers.map((server, index) => (
                <li
                  key={server.id}
                  className="stagger-item"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <ServerCard
                    server={server}
                    isExpanded={expandedServer === server.id}
                    onToggleExpand={() => handleToggleExpanded(server.id)}
                    onToggleTrust={() => handleToggleTrust(server.id, server.isTrusted)}
                    onUnregister={() => openUnregisterConfirm(server.id, server.name)}
                  />
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      {/* Tools Section */}
      <section
        id="mcp-panel-tools"
        role="tabpanel"
        aria-labelledby="mcp-tab-tools"
        hidden={activeSection !== 'tools'}
      >
        {activeSection === 'tools' && (
          allTools.length === 0 ? (
            <EmptyState
              icon="🔧"
              title={t('noTools')}
              description={t('noToolsDesc')}
            />
          ) : (
            <ul role="list" aria-label={t('tools')} style={{ listStyle: 'none', margin: 0, padding: 0, display: 'flex', flexDirection: 'column', gap: 6 }}>
              {allTools.map((tool, index) => (
                <li
                  key={`${tool.serverId}-${tool.name}-${index}`}
                  className="stagger-item"
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  <ToolCard tool={tool} />
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      {/* History Section */}
      <section
        id="mcp-panel-history"
        role="tabpanel"
        aria-labelledby="mcp-tab-history"
        hidden={activeSection !== 'history'}
      >
        {activeSection === 'history' && (
          toolCalls.length === 0 ? (
            <EmptyState
              icon="📜"
              title={t('noToolHistory')}
              description={t('noToolHistoryDesc')}
            />
          ) : (
            <ul role="list" aria-label={t('history')} style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {toolCalls.map((call, index) => (
                <li
                  key={call.id}
                  className="stagger-item"
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  <ToolCallHistoryCard call={call} servers={servers} />
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={t('unregister')}
        message={`${t('confirmUnregister') || 'Are you sure you want to unregister'} ${confirmDialog.serverName}?`}
        confirmText={t('unregister')}
        variant="danger"
        icon="🔌"
        onConfirm={handleUnregister}
        onCancel={() => setConfirmDialog({ isOpen: false, serverId: '', serverName: '' })}
        isLoading={isProcessing}
      />
    </div>
  );
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

interface EmptyStateProps {
  icon: string;
  title: string;
  description: string;
}

const EmptyState: React.FC<EmptyStateProps> = ({ icon, title, description }) => (
  <div style={styles.emptyState} role="status">
    <span style={{ fontSize: 48 }} aria-hidden="true">{icon}</span>
    <p style={{ fontWeight: 500, marginBottom: 4 }}>{title}</p>
    <p style={{ color: '#666', fontSize: 12 }}>{description}</p>
  </div>
);

interface ServerCardProps {
  server: MCPServer;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onToggleTrust: () => void;
  onUnregister: () => void;
}

const ServerCard: React.FC<ServerCardProps> = ({
  server,
  isExpanded,
  onToggleExpand,
  onToggleTrust,
  onUnregister,
}) => (
  <article
    style={mcpStyles.serverCard}
    aria-label={`${server.name} - ${server.isTrusted ? t('trusted') : t('untrusted')}`}
  >
    <div style={mcpStyles.serverHeader}>
      <div style={mcpStyles.serverInfo}>
        <span style={mcpStyles.serverIcon} aria-hidden="true">
          {getTransportIcon(server.transport)}
        </span>
        <div>
          <div style={mcpStyles.serverName}>{server.name}</div>
          <div style={mcpStyles.serverEndpoint} title={server.endpoint}>
            {truncateEndpoint(server.endpoint)}
          </div>
        </div>
      </div>
      <button
        type="button"
        onClick={onToggleTrust}
        style={{
          ...mcpStyles.trustBadge,
          ...(server.isTrusted
            ? mcpStyles.trustBadgeTrusted
            : mcpStyles.trustBadgeUntrusted),
          cursor: 'pointer',
          border: 'none',
        }}
        title={t('clickToToggleTrust')}
        aria-label={`${server.isTrusted ? t('trusted') : t('untrusted')}. ${t('clickToToggleTrust')}`}
        aria-pressed={server.isTrusted}
      >
        {server.isTrusted ? t('trusted') : t('untrusted')}
      </button>
    </div>

    <div style={mcpStyles.serverStats} role="group" aria-label="Statistics">
      <StatItem label={t('trustLevel')} value={`${server.trustLevel}%`} />
      <StatItem label={t('toolCalls')} value={server.stats.toolCallsTotal} />
      <StatItem label={t('approved')} value={server.stats.toolCallsApproved} color="#10b981" />
      <StatItem label={t('rejected')} value={server.stats.toolCallsRejected} color="#ef4444" />
    </div>

    {/* Tools list (collapsible) */}
    <button
      type="button"
      onClick={onToggleExpand}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onToggleExpand();
        }
      }}
      style={{
        background: 'none',
        border: 'none',
        cursor: 'pointer',
        marginTop: 8,
        padding: 0,
        width: '100%',
        textAlign: 'left',
      }}
      aria-expanded={isExpanded}
      aria-controls={`server-tools-${server.id}`}
    >
      <span style={{ fontSize: 12, color: '#888' }}>
        <span aria-hidden="true">{isExpanded ? '▼' : '▶'}</span>{' '}
        {server.tools.length} {t('toolsAvailable')}
      </span>
    </button>

    {isExpanded && (
      <div
        id={`server-tools-${server.id}`}
        style={mcpStyles.toolsList}
        role="list"
        aria-label={`${server.name} tools`}
        className="animate-slideDown"
      >
        {server.tools.map((tool, idx) => (
          <span
            key={idx}
            role="listitem"
            style={mcpStyles.toolChip}
            title={tool.description}
          >
            {tool.name}
          </span>
        ))}
      </div>
    )}

    <div style={mcpStyles.serverActions}>
      <button
        type="button"
        onClick={onUnregister}
        style={mcpStyles.unregisterButton}
        aria-label={`${t('unregister')} ${server.name}`}
      >
        {t('unregister')}
      </button>
    </div>
  </article>
);

interface StatItemProps {
  label: string;
  value: string | number;
  color?: string;
}

const StatItem: React.FC<StatItemProps> = ({ label, value, color }) => (
  <div style={mcpStyles.serverStat}>
    <span style={mcpStyles.statLabel}>{label}</span>
    <span style={{ ...mcpStyles.statValue, color: color || '#fff' }}>{value}</span>
  </div>
);

interface ToolCardProps {
  tool: {
    name: string;
    description?: string;
    serverName: string;
    serverId: string;
  };
}

const ToolCard: React.FC<ToolCardProps> = ({ tool }) => {
  const riskLevel = getToolRiskLevel(tool.name);

  return (
    <article
      style={mcpStyles.toolCallCard}
      aria-label={`${tool.name} from ${tool.serverName}`}
    >
      <div style={mcpStyles.toolCallHeader}>
        <span style={mcpStyles.toolCallIcon} aria-hidden="true">🔧</span>
        <div style={mcpStyles.toolCallInfo}>
          <div style={mcpStyles.toolCallName}>{tool.name}</div>
          <div style={mcpStyles.toolCallServer}>{tool.serverName}</div>
        </div>
        <div style={mcpStyles.toolCallMeta}>
          <span
            style={{ fontSize: 10, color: '#888' }}
            title={`Risk level: ${riskLevel}`}
            aria-label={`Risk level: ${riskLevel}`}
          >
            {getRiskIcon(riskLevel)}
          </span>
        </div>
      </div>
      {tool.description && (
        <div style={{ fontSize: 11, color: '#888', marginTop: 6 }}>
          {tool.description}
        </div>
      )}
    </article>
  );
};

interface ToolCallHistoryCardProps {
  call: MCPToolCall;
  servers: MCPServer[];
}

const ToolCallHistoryCard: React.FC<ToolCallHistoryCardProps> = ({ call, servers }) => {
  const isApproved = call.status === 'approved';
  const serverName = getServerName(servers, call.serverId);

  return (
    <article
      style={mcpStyles.toolCallCard}
      aria-label={`${call.tool} ${isApproved ? 'approved' : 'rejected'} at ${formatTime(call.timestamp)}`}
    >
      <div style={mcpStyles.toolCallHeader}>
        <span
          style={{
            ...mcpStyles.toolCallIcon,
            color: isApproved ? '#10b981' : '#ef4444',
          }}
          aria-hidden="true"
        >
          {isApproved ? '✓' : '✗'}
        </span>
        <div style={mcpStyles.toolCallInfo}>
          <div style={mcpStyles.toolCallName}>{call.tool}</div>
          <div style={mcpStyles.toolCallServer}>{serverName}</div>
        </div>
        <div style={mcpStyles.toolCallMeta}>
          <span style={mcpStyles.toolCallTime}>
            {formatTime(call.timestamp)}
          </span>
        </div>
      </div>
      {!call.thspResult.overall && (
        <div
          style={{ fontSize: 11, color: '#ef4444', marginTop: 6 }}
          role="alert"
        >
          {call.thspResult.summary}
        </div>
      )}
    </article>
  );
};

export default MCPTab;
