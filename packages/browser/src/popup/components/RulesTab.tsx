/**
 * @fileoverview Rules Tab - Manage approval rules
 *
 * Provides UI for:
 * - Viewing all approval rules
 * - Enabling/disabling rules
 * - Creating new rules
 * - Editing existing rules
 * - Deleting rules
 * - Import/export rules
 *
 * @author Sentinel Team
 * @license MIT
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { t } from '../../lib/i18n';
import {
  ApprovalRule,
  RuleCondition,
  RuleConditionField,
  RuleConditionOperator,
  ApprovalAction,
} from '../../types';
import { ConfirmDialog } from './ui';

// =============================================================================
// TYPES
// =============================================================================

interface RulesTabProps {
  onStatsUpdate?: () => void;
}

interface RuleFormData {
  name: string;
  description: string;
  priority: number;
  enabled: boolean;
  conditions: RuleCondition[];
  action: ApprovalAction;
  reason: string;
}

// =============================================================================
// CONSTANTS
// =============================================================================

const CONDITION_FIELDS: { value: RuleConditionField; label: string; type: 'string' | 'number' | 'boolean' | 'select' }[] = [
  { value: 'source', label: 'Source', type: 'select' },
  { value: 'riskLevel', label: 'Risk Level', type: 'select' },
  { value: 'estimatedValueUsd', label: 'Value (USD)', type: 'number' },
  { value: 'agentType', label: 'Agent Type', type: 'select' },
  { value: 'agentTrustLevel', label: 'Agent Trust Level', type: 'number' },
  { value: 'actionType', label: 'Action Type', type: 'string' },
  { value: 'memoryCompromised', label: 'Memory Compromised', type: 'boolean' },
  { value: 'mcpServerTrusted', label: 'MCP Server Trusted', type: 'boolean' },
  { value: 'mcpToolName', label: 'MCP Tool Name', type: 'string' },
  { value: 'mcpSource', label: 'MCP Source', type: 'string' },
];

const OPERATORS: { value: RuleConditionOperator; label: string }[] = [
  { value: 'equals', label: '=' },
  { value: 'not_equals', label: '!=' },
  { value: 'greater_than', label: '>' },
  { value: 'less_than', label: '<' },
  { value: 'greater_than_or_equals', label: '>=' },
  { value: 'less_than_or_equals', label: '<=' },
  { value: 'contains', label: 'contains' },
  { value: 'not_contains', label: 'not contains' },
  { value: 'in', label: 'in' },
  { value: 'not_in', label: 'not in' },
];

const FIELD_OPTIONS: Record<string, { value: string; label: string }[]> = {
  source: [
    { value: 'agent_shield', label: 'Agent Shield' },
    { value: 'mcp_gateway', label: 'MCP Gateway' },
  ],
  riskLevel: [
    { value: 'low', label: 'Low' },
    { value: 'medium', label: 'Medium' },
    { value: 'high', label: 'High' },
    { value: 'critical', label: 'Critical' },
  ],
  agentType: [
    { value: 'elizaos', label: 'ElizaOS' },
    { value: 'autogpt', label: 'AutoGPT' },
    { value: 'langchain', label: 'LangChain' },
    { value: 'crewai', label: 'CrewAI' },
    { value: 'custom', label: 'Custom' },
  ],
};

const DEFAULT_FORM_DATA: RuleFormData = {
  name: '',
  description: '',
  priority: 50,
  enabled: true,
  conditions: [],
  action: 'require_approval' as ApprovalAction,
  reason: '',
};

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export const RulesTab: React.FC<RulesTabProps> = ({ onStatsUpdate }) => {
  const [rules, setRules] = useState<ApprovalRule[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editingRule, setEditingRule] = useState<ApprovalRule | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load rules
  const loadRules = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await chrome.runtime.sendMessage({ type: 'APPROVAL_GET_RULES' });
      setRules(response || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load rules');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRules();
  }, [loadRules]);

  // Toggle rule enabled state
  const toggleRule = async (rule: ApprovalRule) => {
    try {
      await chrome.runtime.sendMessage({
        type: 'APPROVAL_UPDATE_RULE',
        payload: { ...rule, enabled: !rule.enabled, updatedAt: Date.now() },
      });
      await loadRules();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update rule');
    }
  };

  // Delete rule
  const deleteRule = async (id: string) => {
    try {
      await chrome.runtime.sendMessage({
        type: 'APPROVAL_DELETE_RULE',
        payload: id,
      });
      setDeleteConfirm(null);
      await loadRules();
      onStatsUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete rule');
    }
  };

  // Export rules
  const exportRules = () => {
    const data = JSON.stringify(rules, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sentinel-rules-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  // Import rules
  const importRules = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    try {
      const text = await file.text();
      const imported = JSON.parse(text) as ApprovalRule[];

      if (!Array.isArray(imported)) {
        throw new Error('Invalid file format');
      }

      // Import each rule
      for (const rule of imported) {
        // Generate new ID to avoid conflicts
        const newRule = {
          ...rule,
          id: crypto.randomUUID(),
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        await chrome.runtime.sendMessage({
          type: 'APPROVAL_CREATE_RULE',
          payload: newRule,
        });
      }

      await loadRules();
      onStatsUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to import rules');
    }

    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  // Save rule (create or update)
  const saveRule = async (formData: RuleFormData, existingId?: string) => {
    try {
      if (existingId) {
        await chrome.runtime.sendMessage({
          type: 'APPROVAL_UPDATE_RULE',
          payload: {
            id: existingId,
            ...formData,
            updatedAt: Date.now(),
          },
        });
      } else {
        await chrome.runtime.sendMessage({
          type: 'APPROVAL_CREATE_RULE',
          payload: formData,
        });
      }
      setEditingRule(null);
      setIsCreating(false);
      await loadRules();
      onStatsUpdate?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save rule');
    }
  };

  // Render loading state
  if (loading) {
    return (
      <div style={styles.loading}>
        <span style={styles.spinner}>Loading rules...</span>
      </div>
    );
  }

  // Render error state
  if (error) {
    return (
      <div style={styles.error}>
        <span style={styles.errorIcon}>Error</span>
        <p>{error}</p>
        <button onClick={loadRules} style={styles.retryButton}>
          Retry
        </button>
      </div>
    );
  }

  // Render editor modal
  if (editingRule || isCreating) {
    return (
      <RuleEditor
        rule={editingRule}
        onSave={(formData) => saveRule(formData, editingRule?.id)}
        onCancel={() => {
          setEditingRule(null);
          setIsCreating(false);
        }}
      />
    );
  }

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <h2 style={styles.title}>{t('rules')}</h2>
        <div style={styles.actions}>
          <button
            onClick={() => setIsCreating(true)}
            style={styles.primaryButton}
            aria-label={t('createRule')}
          >
            + {t('newRule')}
          </button>
        </div>
      </div>

      {/* Import/Export */}
      <div style={styles.importExport}>
        <button onClick={exportRules} style={styles.secondaryButton}>
          {t('export')}
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept=".json"
          onChange={importRules}
          style={{ display: 'none' }}
        />
        <button
          onClick={() => fileInputRef.current?.click()}
          style={styles.secondaryButton}
        >
          {t('import')}
        </button>
      </div>

      {/* Rules list */}
      {rules.length === 0 ? (
        <div style={styles.emptyState}>
          <span style={{ fontSize: 48 }}>No rules</span>
          <p>{t('noRulesDesc')}</p>
          <button onClick={() => setIsCreating(true)} style={styles.primaryButton}>
            {t('createFirstRule')}
          </button>
        </div>
      ) : (
        <div style={styles.rulesList}>
          {rules.map((rule) => (
            <div
              key={rule.id}
              style={{
                ...styles.ruleCard,
                opacity: rule.enabled ? 1 : 0.6,
              }}
            >
              <div style={styles.ruleHeader}>
                <div style={styles.ruleInfo}>
                  <span style={styles.ruleName}>{rule.name}</span>
                  <span style={styles.rulePriority}>P{rule.priority}</span>
                </div>
                <button
                  onClick={() => toggleRule(rule)}
                  style={{
                    ...styles.toggleButton,
                    background: rule.enabled
                      ? 'linear-gradient(135deg, #10b981, #059669)'
                      : 'rgba(255, 255, 255, 0.1)',
                  }}
                  aria-label={rule.enabled ? t('disable') : t('enable')}
                >
                  {rule.enabled ? 'ON' : 'OFF'}
                </button>
              </div>

              {rule.description && (
                <p style={styles.ruleDescription}>{rule.description}</p>
              )}

              <div style={styles.ruleConditions}>
                {rule.conditions.map((c, i) => (
                  <span key={i} style={styles.conditionChip}>
                    {c.field} {c.operator} {String(c.value)}
                  </span>
                ))}
                <span
                  style={{
                    ...styles.actionChip,
                    background:
                      rule.action === 'auto_approve'
                        ? 'rgba(16, 185, 129, 0.2)'
                        : rule.action === 'auto_reject'
                        ? 'rgba(239, 68, 68, 0.2)'
                        : 'rgba(99, 102, 241, 0.2)',
                    color:
                      rule.action === 'auto_approve'
                        ? '#10b981'
                        : rule.action === 'auto_reject'
                        ? '#ef4444'
                        : '#818cf8',
                  }}
                >
                  {rule.action.replace('_', ' ')}
                </span>
              </div>

              <div style={styles.ruleActions}>
                <button
                  onClick={() => setEditingRule(rule)}
                  style={styles.iconButton}
                  aria-label={t('edit')}
                >
                  Edit
                </button>
                <button
                  onClick={() => setDeleteConfirm(rule.id)}
                  style={{ ...styles.iconButton, color: '#ef4444' }}
                  aria-label={t('delete')}
                >
                  Delete
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Delete confirmation dialog */}
      <ConfirmDialog
        isOpen={!!deleteConfirm}
        title={t('deleteRule')}
        message={t('deleteRuleConfirm')}
        confirmText={t('delete')}
        cancelText={t('cancel')}
        onConfirm={() => deleteConfirm && deleteRule(deleteConfirm)}
        onCancel={() => setDeleteConfirm(null)}
        variant="danger"
      />
    </div>
  );
};

// =============================================================================
// RULE EDITOR COMPONENT
// =============================================================================

interface RuleEditorProps {
  rule: ApprovalRule | null;
  onSave: (formData: RuleFormData) => void;
  onCancel: () => void;
}

const RuleEditor: React.FC<RuleEditorProps> = ({ rule, onSave, onCancel }) => {
  const [formData, setFormData] = useState<RuleFormData>(() => {
    if (rule) {
      return {
        name: rule.name,
        description: rule.description || '',
        priority: rule.priority,
        enabled: rule.enabled,
        conditions: rule.conditions,
        action: rule.action,
        reason: rule.reason || '',
      };
    }
    return { ...DEFAULT_FORM_DATA };
  });

  const updateField = <K extends keyof RuleFormData>(
    key: K,
    value: RuleFormData[K]
  ) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const addCondition = () => {
    setFormData((prev) => ({
      ...prev,
      conditions: [
        ...prev.conditions,
        { field: 'riskLevel' as RuleConditionField, operator: 'equals' as RuleConditionOperator, value: 'high' },
      ],
    }));
  };

  const updateCondition = (index: number, updates: Partial<RuleCondition>) => {
    setFormData((prev) => ({
      ...prev,
      conditions: prev.conditions.map((c, i) =>
        i === index ? { ...c, ...updates } : c
      ),
    }));
  };

  const removeCondition = (index: number) => {
    setFormData((prev) => ({
      ...prev,
      conditions: prev.conditions.filter((_, i) => i !== index),
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      return;
    }
    onSave(formData);
  };

  return (
    <form onSubmit={handleSubmit} style={styles.editor}>
      <h2 style={styles.editorTitle}>
        {rule ? t('editRule') : t('createRule')}
      </h2>

      {/* Name */}
      <div style={styles.field}>
        <label style={styles.label}>{t('name')}</label>
        <input
          type="text"
          value={formData.name}
          onChange={(e) => updateField('name', e.target.value)}
          style={styles.input}
          placeholder="e.g., Block high-risk transfers"
          required
        />
      </div>

      {/* Description */}
      <div style={styles.field}>
        <label style={styles.label}>{t('description')}</label>
        <input
          type="text"
          value={formData.description}
          onChange={(e) => updateField('description', e.target.value)}
          style={styles.input}
          placeholder="Optional description"
        />
      </div>

      {/* Priority */}
      <div style={styles.field}>
        <label style={styles.label}>{t('priority')} (0-1000)</label>
        <input
          type="number"
          value={formData.priority}
          onChange={(e) => updateField('priority', Math.min(1000, Math.max(0, parseInt(e.target.value) || 0)))}
          style={styles.input}
          min={0}
          max={1000}
        />
      </div>

      {/* Conditions */}
      <div style={styles.field}>
        <label style={styles.label}>{t('conditions')}</label>
        <div style={styles.conditionsList}>
          {formData.conditions.map((condition, index) => (
            <div key={index} style={styles.conditionRow}>
              <select
                value={condition.field}
                onChange={(e) =>
                  updateCondition(index, {
                    field: e.target.value as RuleConditionField,
                  })
                }
                style={styles.selectSmall}
              >
                {CONDITION_FIELDS.map((f) => (
                  <option key={f.value} value={f.value}>
                    {f.label}
                  </option>
                ))}
              </select>
              <select
                value={condition.operator}
                onChange={(e) =>
                  updateCondition(index, {
                    operator: e.target.value as RuleConditionOperator,
                  })
                }
                style={styles.selectSmall}
              >
                {OPERATORS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              {FIELD_OPTIONS[condition.field] ? (
                <select
                  value={String(condition.value)}
                  onChange={(e) =>
                    updateCondition(index, { value: e.target.value })
                  }
                  style={styles.selectSmall}
                >
                  {FIELD_OPTIONS[condition.field].map((o) => (
                    <option key={o.value} value={o.value}>
                      {o.label}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  value={String(condition.value)}
                  onChange={(e) =>
                    updateCondition(index, { value: e.target.value })
                  }
                  style={styles.inputSmall}
                  placeholder="Value"
                />
              )}
              <button
                type="button"
                onClick={() => removeCondition(index)}
                style={styles.removeButton}
                aria-label="Remove condition"
              >
                X
              </button>
            </div>
          ))}
          <button
            type="button"
            onClick={addCondition}
            style={styles.addButton}
          >
            + Add Condition
          </button>
        </div>
      </div>

      {/* Action */}
      <div style={styles.field}>
        <label style={styles.label}>{t('action')}</label>
        <select
          value={formData.action}
          onChange={(e) => updateField('action', e.target.value as ApprovalAction)}
          style={styles.select}
        >
          <option value="auto_approve">Auto Approve</option>
          <option value="auto_reject">Auto Reject</option>
          <option value="require_approval">Require Manual Approval</option>
        </select>
      </div>

      {/* Reason */}
      <div style={styles.field}>
        <label style={styles.label}>{t('reason')}</label>
        <input
          type="text"
          value={formData.reason}
          onChange={(e) => updateField('reason', e.target.value)}
          style={styles.input}
          placeholder="Reason shown when rule applies"
        />
      </div>

      {/* Enabled */}
      <div style={styles.checkboxField}>
        <input
          type="checkbox"
          id="enabled"
          checked={formData.enabled}
          onChange={(e) => updateField('enabled', e.target.checked)}
        />
        <label htmlFor="enabled" style={styles.checkboxLabel}>
          {t('enabled')}
        </label>
      </div>

      {/* Actions */}
      <div style={styles.editorActions}>
        <button type="button" onClick={onCancel} style={styles.secondaryButton}>
          {t('cancel')}
        </button>
        <button type="submit" style={styles.primaryButton}>
          {t('save')}
        </button>
      </div>
    </form>
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
  importExport: {
    display: 'flex',
    gap: 8,
  },
  primaryButton: {
    padding: '8px 16px',
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    border: 'none',
    borderRadius: 8,
    color: '#fff',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
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
  rulesList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  ruleCard: {
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  ruleHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 8,
  },
  ruleInfo: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  ruleName: {
    fontSize: 13,
    fontWeight: 600,
    color: '#fff',
  },
  rulePriority: {
    fontSize: 10,
    padding: '2px 6px',
    background: 'rgba(99, 102, 241, 0.2)',
    borderRadius: 4,
    color: '#818cf8',
  },
  toggleButton: {
    padding: '4px 12px',
    border: 'none',
    borderRadius: 12,
    color: '#fff',
    fontSize: 10,
    fontWeight: 600,
    cursor: 'pointer',
  },
  ruleDescription: {
    fontSize: 11,
    color: '#888',
    margin: '0 0 8px 0',
  },
  ruleConditions: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 4,
    marginBottom: 8,
  },
  conditionChip: {
    fontSize: 10,
    padding: '2px 6px',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 4,
    color: '#aaa',
  },
  actionChip: {
    fontSize: 10,
    padding: '2px 8px',
    borderRadius: 4,
    fontWeight: 600,
    textTransform: 'uppercase',
  },
  ruleActions: {
    display: 'flex',
    gap: 8,
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    paddingTop: 8,
  },
  iconButton: {
    background: 'none',
    border: 'none',
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
    padding: '4px 8px',
  },
  editor: {
    display: 'flex',
    flexDirection: 'column',
    gap: 16,
  },
  editorTitle: {
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
    margin: 0,
  },
  field: {
    display: 'flex',
    flexDirection: 'column',
    gap: 6,
  },
  label: {
    fontSize: 11,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  input: {
    padding: '8px 12px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#fff',
    fontSize: 13,
  },
  select: {
    padding: '8px 12px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#fff',
    fontSize: 13,
  },
  conditionsList: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  conditionRow: {
    display: 'flex',
    gap: 4,
    alignItems: 'center',
  },
  selectSmall: {
    flex: 1,
    padding: '6px 8px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 4,
    color: '#fff',
    fontSize: 11,
  },
  inputSmall: {
    flex: 1,
    padding: '6px 8px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 4,
    color: '#fff',
    fontSize: 11,
  },
  removeButton: {
    padding: '4px 8px',
    background: 'rgba(239, 68, 68, 0.2)',
    border: 'none',
    borderRadius: 4,
    color: '#ef4444',
    fontSize: 10,
    cursor: 'pointer',
  },
  addButton: {
    padding: '8px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px dashed rgba(255, 255, 255, 0.2)',
    borderRadius: 6,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
  },
  checkboxField: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  checkboxLabel: {
    fontSize: 13,
    color: '#fff',
  },
  editorActions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
    marginTop: 8,
  },
};

export default RulesTab;
