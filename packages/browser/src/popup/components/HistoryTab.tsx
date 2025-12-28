/**
 * @fileoverview History Tab - View action history with filtering
 *
 * Provides UI for:
 * - Viewing action history with pagination
 * - Filtering by source, decision, date
 * - Viewing action details
 * - Clearing history
 * - Exporting history
 *
 * @author Sentinel Team
 * @license MIT
 */

import React, { useState, useEffect, useCallback } from 'react';
import { t } from '../../lib/i18n';
import { ActionHistoryEntry } from '../../types';
import { ConfirmDialog } from './ui';
import { formatRelativeTime, formatDate } from '../utils/format';

// =============================================================================
// TYPES
// =============================================================================

interface HistoryTabProps {
  onStatsUpdate?: () => void;
}

interface HistoryFilters {
  source: 'all' | 'agent_shield' | 'mcp_gateway';
  decision: 'all' | 'approved' | 'rejected';
}

// =============================================================================
// CONSTANTS
// =============================================================================

const PAGE_SIZE = 20;

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export const HistoryTab: React.FC<HistoryTabProps> = ({ onStatsUpdate }) => {
  const [history, setHistory] = useState<ActionHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [totalCount, setTotalCount] = useState(0);
  const [filters, setFilters] = useState<HistoryFilters>({
    source: 'all',
    decision: 'all',
  });
  const [selectedEntry, setSelectedEntry] = useState<ActionHistoryEntry | null>(null);
  const [clearConfirm, setClearConfirm] = useState(false);

  // Load history
  const loadHistory = useCallback(async (reset = false) => {
    try {
      setLoading(true);
      setError(null);

      const offset = reset ? 0 : page * PAGE_SIZE;
      const response = await chrome.runtime.sendMessage({
        type: 'APPROVAL_GET_HISTORY',
        payload: { limit: PAGE_SIZE + 1, offset },
      });

      const entries = response || [];

      // Check if there are more entries
      setHasMore(entries.length > PAGE_SIZE);
      const pageEntries = entries.slice(0, PAGE_SIZE);

      if (reset) {
        setHistory(pageEntries);
        setPage(0);
      } else {
        setHistory(pageEntries);
      }

      // Get total count (for display)
      // This is an approximation based on what we loaded
      if (reset) {
        setTotalCount(entries.length);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    loadHistory(page === 0);
  }, [page, loadHistory]);

  // Apply filters client-side for simplicity
  const filteredHistory = history.filter((entry) => {
    if (filters.source !== 'all' && entry.source !== filters.source) {
      return false;
    }
    if (filters.decision !== 'all') {
      const isApproved = entry.decision.action === 'approve';
      if (filters.decision === 'approved' && !isApproved) return false;
      if (filters.decision === 'rejected' && isApproved) return false;
    }
    return true;
  });

  // Clear history
  const clearHistory = async () => {
    try {
      await chrome.runtime.sendMessage({ type: 'APPROVAL_CLEAR_HISTORY' });
      setClearConfirm(false);
      setHistory([]);
      setTotalCount(0);
      onStatsUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear history');
    }
  };

  // Export history
  const exportHistory = async () => {
    try {
      // Load all history for export
      const response = await chrome.runtime.sendMessage({
        type: 'APPROVAL_GET_HISTORY',
        payload: { limit: 10000, offset: 0 },
      });

      const data = JSON.stringify(response || [], null, 2);
      const blob = new Blob([data], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `sentinel-history-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to export history');
    }
  };

  // Get action name from entry
  const getActionName = (entry: ActionHistoryEntry): string => {
    if (entry.source === 'agent_shield') {
      return (entry.action as { type?: string }).type || 'Unknown action';
    } else {
      return (entry.action as { toolName?: string }).toolName || 'Unknown tool';
    }
  };

  // Get source name from entry
  const getSourceName = (entry: ActionHistoryEntry): string => {
    if (entry.source === 'agent_shield') {
      return (entry.action as { agentName?: string }).agentName || 'Agent';
    } else {
      return (entry.action as { serverName?: string }).serverName || 'MCP Server';
    }
  };

  // Render loading state
  if (loading && history.length === 0) {
    return (
      <div style={styles.loading}>
        <span style={styles.spinner}>Loading history...</span>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div style={styles.error}>
        <span style={styles.errorIcon}>Error</span>
        <p>{error}</p>
        <button onClick={() => loadHistory(true)} style={styles.retryButton}>
          Retry
        </button>
      </div>
    );
  }

  // Render detail view
  if (selectedEntry) {
    return (
      <HistoryDetail
        entry={selectedEntry}
        onBack={() => setSelectedEntry(null)}
      />
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>{t('history')}</h2>
        <div style={styles.actions}>
          <button onClick={exportHistory} style={styles.secondaryButton}>
            {t('export')}
          </button>
          <button
            onClick={() => setClearConfirm(true)}
            style={{ ...styles.secondaryButton, color: '#ef4444' }}
          >
            {t('clear')}
          </button>
        </div>
      </div>

      {/* Filters */}
      <div style={styles.filters}>
        <select
          value={filters.source}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              source: e.target.value as HistoryFilters['source'],
            }))
          }
          style={styles.filterSelect}
        >
          <option value="all">{t('allSources')}</option>
          <option value="agent_shield">{t('agentShield')}</option>
          <option value="mcp_gateway">{t('mcpGateway')}</option>
        </select>
        <select
          value={filters.decision}
          onChange={(e) =>
            setFilters((prev) => ({
              ...prev,
              decision: e.target.value as HistoryFilters['decision'],
            }))
          }
          style={styles.filterSelect}
        >
          <option value="all">{t('allDecisions')}</option>
          <option value="approved">{t('approved')}</option>
          <option value="rejected">{t('rejected')}</option>
        </select>
      </div>

      {/* History list */}
      {filteredHistory.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={{ fontSize: 48 }}>No history</span>
          <p>{t('noHistoryDesc')}</p>
        </div>
      ) : (
        <>
          <div style={styles.historyList}>
            {filteredHistory.map((entry) => (
              <button
                key={entry.id}
                onClick={() => setSelectedEntry(entry)}
                style={styles.historyCard}
              >
                <div style={styles.historyHeader}>
                  <span
                    style={{
                      ...styles.sourceIcon,
                      background:
                        entry.source === 'agent_shield'
                          ? 'rgba(99, 102, 241, 0.2)'
                          : 'rgba(139, 92, 246, 0.2)',
                    }}
                  >
                    {entry.source === 'agent_shield' ? 'A' : 'M'}
                  </span>
                  <div style={styles.historyInfo}>
                    <span style={styles.historyAction}>
                      {getActionName(entry)}
                    </span>
                    <span style={styles.historySource}>
                      {getSourceName(entry)}
                    </span>
                  </div>
                  <div style={styles.historyMeta}>
                    <span
                      style={{
                        ...styles.decisionBadge,
                        background:
                          entry.decision.action === 'approve'
                            ? 'rgba(16, 185, 129, 0.2)'
                            : 'rgba(239, 68, 68, 0.2)',
                        color:
                          entry.decision.action === 'approve'
                            ? '#10b981'
                            : '#ef4444',
                      }}
                    >
                      {entry.decision.action === 'approve' ? 'Yes' : 'No'}
                    </span>
                    <span style={styles.historyTime}>
                      {formatRelativeTime(entry.processedAt)}
                    </span>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Pagination */}
          <div style={styles.pagination}>
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              style={{
                ...styles.pageButton,
                opacity: page === 0 ? 0.5 : 1,
              }}
            >
              Previous
            </button>
            <span style={styles.pageInfo}>Page {page + 1}</span>
            <button
              onClick={() => setPage((p) => p + 1)}
              disabled={!hasMore}
              style={{
                ...styles.pageButton,
                opacity: !hasMore ? 0.5 : 1,
              }}
            >
              Next
            </button>
          </div>
        </>
      )}

      {/* Clear confirmation dialog */}
      <ConfirmDialog
        isOpen={clearConfirm}
        title={t('clearHistory')}
        message={t('clearHistoryConfirm')}
        confirmText={t('clear')}
        cancelText={t('cancel')}
        onConfirm={clearHistory}
        onCancel={() => setClearConfirm(false)}
        variant="danger"
      />
    </div>
  );
};

// =============================================================================
// HISTORY DETAIL COMPONENT
// =============================================================================

interface HistoryDetailProps {
  entry: ActionHistoryEntry;
  onBack: () => void;
}

const HistoryDetail: React.FC<HistoryDetailProps> = ({ entry, onBack }) => {
  const isAgent = entry.source === 'agent_shield';
  const action = entry.action as unknown as Record<string, unknown>;

  return (
    <div style={styles.detail}>
      <button onClick={onBack} style={styles.backButton}>
        Back to list
      </button>

      <h2 style={styles.detailTitle}>
        {isAgent ? String(action.type || 'Unknown') : String(action.toolName || 'Unknown')}
      </h2>

      <div style={styles.detailSection}>
        <h3 style={styles.detailSectionTitle}>{t('overview')}</h3>
        <div style={styles.detailRow}>
          <span style={styles.detailLabel}>{t('source')}</span>
          <span style={styles.detailValue}>
            {isAgent ? t('agentShield') : t('mcpGateway')}
          </span>
        </div>
        <div style={styles.detailRow}>
          <span style={styles.detailLabel}>
            {isAgent ? t('agent') : t('server')}
          </span>
          <span style={styles.detailValue}>
            {isAgent ? String(action.agentName || 'Unknown') : String(action.serverName || 'Unknown')}
          </span>
        </div>
        <div style={styles.detailRow}>
          <span style={styles.detailLabel}>{t('processedAt')}</span>
          <span style={styles.detailValue}>
            {formatDate(entry.processedAt)}
          </span>
        </div>
      </div>

      <div style={styles.detailSection}>
        <h3 style={styles.detailSectionTitle}>Decision</h3>
        <div style={styles.detailRow}>
          <span style={styles.detailLabel}>{t('action')}</span>
          <span
            style={{
              ...styles.detailValue,
              color:
                entry.decision.action === 'approve' ? '#10b981' : '#ef4444',
            }}
          >
            {entry.decision.action === 'approve'
              ? t('approved')
              : t('rejected')}
          </span>
        </div>
        <div style={styles.detailRow}>
          <span style={styles.detailLabel}>{t('method')}</span>
          <span style={styles.detailValue}>{entry.decision.method}</span>
        </div>
        {entry.decision.reason && (
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>{t('reason')}</span>
            <span style={styles.detailValue}>{entry.decision.reason}</span>
          </div>
        )}
        {entry.decision.ruleId && (
          <div style={styles.detailRow}>
            <span style={styles.detailLabel}>{t('ruleId')}</span>
            <span style={styles.detailValue}>{entry.decision.ruleId}</span>
          </div>
        )}
      </div>

      {Boolean(action.description) && (
        <div style={styles.detailSection}>
          <h3 style={styles.detailSectionTitle}>{t('description')}</h3>
          <p style={styles.detailDescription}>{String(action.description)}</p>
        </div>
      )}

      {Boolean(action.params) && (
        <div style={styles.detailSection}>
          <h3 style={styles.detailSectionTitle}>{t('parameters')}</h3>
          <pre style={styles.detailCode}>
            {typeof action.params === 'object' ? JSON.stringify(action.params, null, 2) : String(action.params)}
          </pre>
        </div>
      )}
    </div>
  );
};

// =============================================================================
// STYLES
// =============================================================================

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
    margin: 0,
  },
  actions: {
    display: 'flex',
    gap: 8,
  },
  secondaryButton: {
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
  },
  filters: {
    display: 'flex',
    gap: 8,
  },
  filterSelect: {
    flex: 1,
    padding: '6px 10px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#fff',
    fontSize: 11,
  },
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
  },
  spinner: {
    color: '#888',
  },
  error: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    padding: 20,
    gap: 8,
  },
  errorIcon: {
    fontSize: 16,
    color: '#ef4444',
  },
  retryButton: {
    padding: '8px 16px',
    background: 'rgba(255, 255, 255, 0.1)',
    border: 'none',
    borderRadius: 6,
    color: '#fff',
    cursor: 'pointer',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    textAlign: 'center',
    gap: 12,
    color: '#888',
  },
  historyList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  historyCard: {
    display: 'flex',
    flexDirection: 'column',
    padding: 10,
    background: 'rgba(255, 255, 255, 0.02)',
    border: '1px solid rgba(255, 255, 255, 0.05)',
    borderRadius: 6,
    cursor: 'pointer',
    textAlign: 'left',
    width: '100%',
  },
  historyHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  sourceIcon: {
    width: 28,
    height: 28,
    borderRadius: 6,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 600,
    color: '#fff',
    flexShrink: 0,
  },
  historyInfo: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
    minWidth: 0,
  },
  historyAction: {
    fontSize: 12,
    fontWeight: 600,
    color: '#fff',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  historySource: {
    fontSize: 10,
    color: '#888',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap',
  },
  historyMeta: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'flex-end',
    gap: 2,
  },
  decisionBadge: {
    fontSize: 9,
    fontWeight: 600,
    padding: '2px 6px',
    borderRadius: 4,
    textTransform: 'uppercase',
  },
  historyTime: {
    fontSize: 9,
    color: '#666',
  },
  pagination: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 16,
    marginTop: 8,
  },
  pageButton: {
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
  },
  pageInfo: {
    fontSize: 11,
    color: '#888',
  },
  detail: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  backButton: {
    alignSelf: 'flex-start',
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
  },
  detailTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: '#fff',
    margin: 0,
  },
  detailSection: {
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  detailSectionTitle: {
    fontSize: 11,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    margin: '0 0 8px 0',
  },
  detailRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '4px 0',
  },
  detailLabel: {
    fontSize: 12,
    color: '#888',
  },
  detailValue: {
    fontSize: 12,
    color: '#fff',
    fontWeight: 500,
  },
  detailDescription: {
    fontSize: 12,
    color: '#ccc',
    margin: 0,
    lineHeight: 1.5,
  },
  detailCode: {
    fontSize: 10,
    color: '#aaa',
    background: 'rgba(0, 0, 0, 0.3)',
    padding: 8,
    borderRadius: 4,
    overflow: 'auto',
    maxHeight: 150,
    margin: 0,
  },
};

export default HistoryTab;
