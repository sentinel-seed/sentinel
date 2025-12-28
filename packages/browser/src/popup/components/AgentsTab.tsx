/**
 * @fileoverview Agents tab component for managing connected AI agents
 *
 * Displays:
 * - Connected agents with status
 * - Pending approval actions
 * - Action history
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

import React, { useState, useEffect, useCallback } from 'react';
import type {
  AgentConnection,
  PendingApproval,
  ActionHistoryEntry,
} from '../../types';
import { t } from '../../lib/i18n';
import { ApprovalModal } from './ApprovalModal';
import { ConfirmDialog } from './ui/ConfirmDialog';
import { ErrorMessage } from './ui/ErrorMessage';
import { SkeletonCard, SkeletonList, SkeletonTabs } from './ui/SkeletonLoader';
import { useAgentEvents, useApprovalEvents, useAnnounce } from '../hooks';
import {
  getActionDisplayInfo,
  getAgentIcon,
  getRiskIcon,
  getRiskBadgeStyle,
  getDecisionIcon,
  formatTime,
  formatTimeRemaining,
} from '../utils';
import { styles, agentStyles } from './styles';

interface AgentsTabProps {
  /** Callback when stats should be refreshed */
  onStatsUpdate?: () => void;
}

/**
 * Tab component for managing AI agents and approvals
 */
export const AgentsTab: React.FC<AgentsTabProps> = ({ onStatsUpdate }) => {
  // State
  const [agents, setAgents] = useState<AgentConnection[]>([]);
  const [pending, setPending] = useState<PendingApproval[]>([]);
  const [history, setHistory] = useState<ActionHistoryEntry[]>([]);
  const [selectedPending, setSelectedPending] = useState<PendingApproval | null>(null);
  const [activeSection, setActiveSection] = useState<'agents' | 'pending' | 'history'>('agents');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);

  // Confirmation dialog state
  const [confirmDialog, setConfirmDialog] = useState<{
    isOpen: boolean;
    agentId: string;
    agentName: string;
  }>({ isOpen: false, agentId: '', agentName: '' });

  const announce = useAnnounce();

  // Load data from background
  const loadData = useCallback(async () => {
    try {
      setError(null);
      const [agentsRes, pendingRes, historyRes] = await Promise.all([
        chrome.runtime.sendMessage({ type: 'AGENT_LIST' }),
        chrome.runtime.sendMessage({ type: 'APPROVAL_GET_PENDING' }),
        chrome.runtime.sendMessage({ type: 'APPROVAL_GET_HISTORY', payload: { limit: 50 } }),
      ]);

      setAgents(agentsRes || []);
      setPending(pendingRes || []);
      setHistory(historyRes || []);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load data';
      setError(message);
      console.error('[AgentsTab] Failed to load data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Subscribe to real-time updates
  useAgentEvents(() => {
    loadData();
  });

  useApprovalEvents(() => {
    loadData();
  });

  // Open confirmation dialog
  const openDisconnectConfirm = (agentId: string, agentName: string) => {
    setConfirmDialog({ isOpen: true, agentId, agentName });
  };

  // Handle disconnect with confirmation
  const handleDisconnect = async () => {
    const { agentId, agentName } = confirmDialog;
    try {
      setIsProcessing(true);
      await chrome.runtime.sendMessage({ type: 'AGENT_DISCONNECT', payload: { agentId } });
      await loadData();
      onStatsUpdate?.();
      announce(`${agentName} disconnected successfully`, 'polite');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to disconnect agent';
      setError(message);
      announce(`Error: ${message}`, 'assertive');
    } finally {
      setIsProcessing(false);
      setConfirmDialog({ isOpen: false, agentId: '', agentName: '' });
    }
  };

  // Handle approval decision
  const handleApprovalDecision = async (
    pendingId: string,
    action: 'approve' | 'reject',
    reason: string
  ) => {
    try {
      setIsProcessing(true);
      await chrome.runtime.sendMessage({
        type: 'APPROVAL_DECIDE',
        payload: { pendingId, action, reason },
      });
      setSelectedPending(null);
      await loadData();
      onStatsUpdate?.();
      announce(`Action ${action === 'approve' ? 'approved' : 'rejected'} successfully`, 'polite');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to process decision';
      setError(message);
      announce(`Error: ${message}`, 'assertive');
    } finally {
      setIsProcessing(false);
    }
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
        aria-label={t('agents')}
        style={agentStyles.sectionTabs}
      >
        {(['agents', 'pending', 'history'] as const).map((section) => (
          <button
            key={section}
            role="tab"
            type="button"
            id={`tab-${section}`}
            aria-selected={activeSection === section}
            aria-controls={`panel-${section}`}
            onClick={() => setActiveSection(section)}
            style={{
              ...agentStyles.sectionTab,
              ...(activeSection === section ? agentStyles.sectionTabActive : {}),
              ...(section === 'pending' && pending.length > 0 ? agentStyles.sectionTabAlert : {}),
            }}
            tabIndex={activeSection === section ? 0 : -1}
          >
            {section === 'agents' && `${t('agentsConnected')} (${agents.length})`}
            {section === 'pending' && `${t('pendingApprovals')} (${pending.length})`}
            {section === 'history' && t('history')}
          </button>
        ))}
      </nav>

      {/* Agents Section */}
      <section
        id="panel-agents"
        role="tabpanel"
        aria-labelledby="tab-agents"
        hidden={activeSection !== 'agents'}
      >
        {activeSection === 'agents' && (
          agents.length === 0 ? (
            <EmptyState
              icon="🤖"
              title={t('noAgentsConnected')}
              description={t('noAgentsDesc')}
            />
          ) : (
            <ul role="list" aria-label={t('agentsConnected')} style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {agents.map((agent, index) => (
                <li
                  key={agent.id}
                  className="stagger-item"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <AgentCard
                    agent={agent}
                    onDisconnect={() => openDisconnectConfirm(agent.id, agent.name)}
                  />
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      {/* Pending Approvals Section */}
      <section
        id="panel-pending"
        role="tabpanel"
        aria-labelledby="tab-pending"
        hidden={activeSection !== 'pending'}
      >
        {activeSection === 'pending' && (
          pending.length === 0 ? (
            <EmptyState
              icon="✅"
              title={t('noPendingApprovals')}
              description={t('noPendingDesc')}
            />
          ) : (
            <ul role="list" aria-label={t('pendingApprovals')} style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {pending.map((item, index) => (
                <li
                  key={item.id}
                  className="stagger-item"
                  style={{ animationDelay: `${index * 50}ms` }}
                >
                  <PendingCard
                    item={item}
                    onClick={() => setSelectedPending(item)}
                  />
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      {/* History Section */}
      <section
        id="panel-history"
        role="tabpanel"
        aria-labelledby="tab-history"
        hidden={activeSection !== 'history'}
      >
        {activeSection === 'history' && (
          history.length === 0 ? (
            <EmptyState
              icon="📜"
              title={t('noHistory')}
              description={t('noHistoryDesc')}
            />
          ) : (
            <ul role="list" aria-label={t('history')} style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {history.map((entry, index) => (
                <li
                  key={entry.id}
                  className="stagger-item"
                  style={{ animationDelay: `${index * 30}ms` }}
                >
                  <HistoryCard entry={entry} />
                </li>
              ))}
            </ul>
          )
        )}
      </section>

      {/* Approval Modal */}
      {selectedPending && (
        <ApprovalModal
          pending={selectedPending}
          onApprove={(reason) => handleApprovalDecision(selectedPending.id, 'approve', reason)}
          onReject={(reason) => handleApprovalDecision(selectedPending.id, 'reject', reason)}
          onClose={() => setSelectedPending(null)}
          isLoading={isProcessing}
        />
      )}

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={confirmDialog.isOpen}
        title={t('disconnect')}
        message={`${t('confirmDisconnect') || 'Are you sure you want to disconnect'} ${confirmDialog.agentName}?`}
        confirmText={t('disconnect')}
        variant="danger"
        icon="🔌"
        onConfirm={handleDisconnect}
        onCancel={() => setConfirmDialog({ isOpen: false, agentId: '', agentName: '' })}
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

interface AgentCardProps {
  agent: AgentConnection;
  onDisconnect: () => void;
}

const AgentCard: React.FC<AgentCardProps> = ({ agent, onDisconnect }) => (
  <article
    style={agentStyles.agentCard}
    aria-label={`${agent.name} - ${agent.status}`}
  >
    <div style={agentStyles.agentHeader}>
      <div style={agentStyles.agentInfo}>
        <span style={agentStyles.agentIcon} aria-hidden="true">
          {getAgentIcon(agent.type)}
        </span>
        <div>
          <div style={agentStyles.agentName}>{agent.name}</div>
          <div style={agentStyles.agentType}>{agent.type}</div>
        </div>
      </div>
      <div style={agentStyles.agentStatus} aria-label={`Status: ${agent.status}`}>
        <span
          style={{
            ...agentStyles.statusDot,
            background: agent.status === 'connected' ? '#10b981' : '#ef4444',
          }}
          aria-hidden="true"
        />
        {agent.status}
      </div>
    </div>
    <div style={agentStyles.agentStats} role="group" aria-label="Statistics">
      <StatItem label={t('actionsIntercepted')} value={agent.stats.actionsTotal} />
      <StatItem label={t('approved')} value={agent.stats.actionsApproved} color="#10b981" />
      <StatItem label={t('rejected')} value={agent.stats.actionsRejected} color="#ef4444" />
    </div>
    <div style={agentStyles.agentActions}>
      <button
        type="button"
        onClick={onDisconnect}
        style={agentStyles.disconnectButton}
        aria-label={`${t('disconnect')} ${agent.name}`}
      >
        {t('disconnect')}
      </button>
    </div>
  </article>
);

interface StatItemProps {
  label: string;
  value: number;
  color?: string;
}

const StatItem: React.FC<StatItemProps> = ({ label, value, color }) => (
  <div style={agentStyles.agentStat}>
    <span style={agentStyles.statLabel}>{label}</span>
    <span style={{ ...agentStyles.statValue, color: color || '#fff' }}>{value}</span>
  </div>
);

interface PendingCardProps {
  item: PendingApproval;
  onClick: () => void;
}

const PendingCard: React.FC<PendingCardProps> = ({ item, onClick }) => {
  const info = getActionDisplayInfo(item.action);

  return (
    <article
      style={agentStyles.pendingCard}
      onClick={onClick}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClick();
        }
      }}
      role="button"
      tabIndex={0}
      aria-label={`${info.type} from ${info.sourceName}, risk level ${info.riskLevel}. Click to review.`}
    >
      <div style={agentStyles.pendingHeader}>
        <span style={agentStyles.pendingIcon} aria-hidden="true">
          {getRiskIcon(info.riskLevel)}
        </span>
        <div style={agentStyles.pendingInfo}>
          <div style={agentStyles.pendingAction}>{info.type}</div>
          <div style={agentStyles.pendingAgent}>{info.sourceName}</div>
        </div>
        <div
          style={{
            ...agentStyles.riskBadge,
            ...getRiskBadgeStyle(info.riskLevel),
          }}
        >
          {info.riskLevel}
        </div>
      </div>
      <div style={agentStyles.pendingDescription}>
        {info.description}
      </div>
      <div style={agentStyles.pendingMeta}>
        <span>{formatTime(item.queuedAt)}</span>
        {item.expiresAt && (
          <span style={agentStyles.expiresIn} aria-label={`Expires in ${formatTimeRemaining(item.expiresAt)}`}>
            {t('expiresIn')} {formatTimeRemaining(item.expiresAt)}
          </span>
        )}
      </div>
    </article>
  );
};

interface HistoryCardProps {
  entry: ActionHistoryEntry;
}

const HistoryCard: React.FC<HistoryCardProps> = ({ entry }) => {
  const info = getActionDisplayInfo(entry.action);
  const isApproved = entry.decision.action === 'approve';

  return (
    <article
      style={agentStyles.historyCard}
      aria-label={`${info.type} ${isApproved ? 'approved' : 'rejected'} at ${formatTime(entry.processedAt)}`}
    >
      <div style={agentStyles.historyHeader}>
        <span
          style={{
            ...agentStyles.historyIcon,
            color: isApproved ? '#10b981' : '#ef4444',
          }}
          aria-hidden="true"
        >
          {isApproved ? '✓' : '✗'}
        </span>
        <div style={agentStyles.historyInfo}>
          <div style={agentStyles.historyAction}>{info.type}</div>
          <div style={agentStyles.historyAgent}>{info.sourceName}</div>
        </div>
        <div style={agentStyles.historyMeta}>
          <span style={agentStyles.historyMethod} title={entry.decision.method === 'auto' ? 'Auto' : 'Manual'}>
            {getDecisionIcon(entry.decision.method)}
          </span>
          <span style={agentStyles.historyTime}>
            {formatTime(entry.processedAt)}
          </span>
        </div>
      </div>
      {entry.decision.reason && (
        <div style={agentStyles.historyReason}>
          {entry.decision.reason}
        </div>
      )}
    </article>
  );
};

export default AgentsTab;
