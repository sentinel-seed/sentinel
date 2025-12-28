/**
 * @fileoverview Settings Tab - Comprehensive settings management
 *
 * Provides UI for configuring:
 * - General settings (protection level, language, notifications)
 * - AgentShield settings (trust threshold, memory injection detection)
 * - MCPGateway settings (trusted servers, intercept mode)
 * - Approval settings (timeout, default action, notifications)
 * - Advanced settings (reset, export, debug)
 *
 * @author Sentinel Team
 * @license MIT
 */

import React, { useState, useCallback } from 'react';
import { t, setLanguage, getAvailableLanguages, Language, Translations } from '../../lib/i18n';
import {
  Settings,
  AgentShieldSettings,
  MCPGatewaySettings,
  ApprovalSettings,
  ApprovalAction,
  EXTENSION_VERSION,
} from '../../types';
import { ConfirmDialog, Toast, ErrorSeverity } from './ui';
import { SettingsSchema, validate } from '../../validation';

// =============================================================================
// TYPES
// =============================================================================

interface SettingsTabProps {
  settings: Settings | null;
  onUpdate: (settings: Settings) => void;
  onLanguageChange: () => void;
}

type SettingsSection = 'general' | 'agentShield' | 'mcpGateway' | 'approval' | 'advanced';

// =============================================================================
// CONSTANTS
// =============================================================================

const TIMEOUT_OPTIONS = [
  { value: 60000, label: '1 min' },
  { value: 120000, label: '2 min' },
  { value: 300000, label: '5 min' },
  { value: 600000, label: '10 min' },
  { value: 900000, label: '15 min' },
];

const DEFAULT_ACTION_OPTIONS: { value: ApprovalAction; labelKey: keyof Translations }[] = [
  { value: 'auto_approve', labelKey: 'autoApprove' },
  { value: 'auto_reject', labelKey: 'autoReject' },
  { value: 'require_approval', labelKey: 'requireApproval' },
];

// =============================================================================
// MAIN COMPONENT
// =============================================================================

/** Toast notification state */
interface ToastState {
  message: string;
  severity: ErrorSeverity;
}

export const SettingsTab: React.FC<SettingsTabProps> = ({
  settings,
  onUpdate,
  onLanguageChange,
}) => {
  const [activeSection, setActiveSection] = useState<SettingsSection>('general');
  const [resetConfirm, setResetConfirm] = useState(false);
  const [clearDataConfirm, setClearDataConfirm] = useState(false);
  const [toast, setToast] = useState<ToastState | null>(null);

  /** Show a toast notification */
  const showToast = useCallback((message: string, severity: ErrorSeverity = 'error') => {
    setToast({ message, severity });
  }, []);

  // Update a top-level setting
  const updateSetting = useCallback(
    async <K extends keyof Settings>(key: K, value: Settings[K]) => {
      try {
        const updated = await chrome.runtime.sendMessage({
          type: 'UPDATE_SETTINGS',
          payload: { [key]: value },
        });
        onUpdate(updated);

        if (key === 'language') {
          setLanguage(value as Language);
          onLanguageChange();
        }
      } catch (err) {
        console.error('[SettingsTab] Failed to update setting:', err);
        showToast(t('unexpectedError'), 'error');
      }
    },
    [onUpdate, onLanguageChange, showToast]
  );

  // Update AgentShield settings
  const updateAgentShield = useCallback(
    async <K extends keyof AgentShieldSettings>(key: K, value: AgentShieldSettings[K]) => {
      if (!settings) return;
      const updated: AgentShieldSettings = {
        ...settings.agentShield,
        [key]: value,
      };
      await updateSetting('agentShield', updated);
    },
    [settings, updateSetting]
  );

  // Update MCPGateway settings
  const updateMCPGateway = useCallback(
    async <K extends keyof MCPGatewaySettings>(key: K, value: MCPGatewaySettings[K]) => {
      if (!settings) return;
      const updated: MCPGatewaySettings = {
        ...settings.mcpGateway,
        [key]: value,
      };
      await updateSetting('mcpGateway', updated);
    },
    [settings, updateSetting]
  );

  // Update Approval settings
  const updateApproval = useCallback(
    async <K extends keyof ApprovalSettings>(key: K, value: ApprovalSettings[K]) => {
      if (!settings) return;
      const updated: ApprovalSettings = {
        ...settings.approval,
        [key]: value,
      };
      await updateSetting('approval', updated);
    },
    [settings, updateSetting]
  );

  // Export settings
  const exportSettings = useCallback(() => {
    if (!settings) return;
    const data = JSON.stringify(settings, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `sentinel-settings-${new Date().toISOString().split('T')[0]}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [settings]);

  // Import settings
  const importSettings = useCallback(() => {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.json';
    input.onchange = async (e) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;

      try {
        const text = await file.text();
        const parsed = JSON.parse(text);

        // Validate using Zod schema
        const validation = validate(SettingsSchema, parsed);
        if (!validation.success) {
          console.error('[SettingsTab] Validation failed:', validation.error);
          showToast(t('importFailed'), 'error');
          return;
        }

        const imported = validation.data as Settings;

        const updated = await chrome.runtime.sendMessage({
          type: 'UPDATE_SETTINGS',
          payload: imported,
        });
        onUpdate(updated);

        if (imported.language) {
          setLanguage(imported.language);
          onLanguageChange();
        }

        showToast(t('importSettings') + ' ✓', 'info');
      } catch (err) {
        console.error('[SettingsTab] Failed to import settings:', err);
        showToast(t('importFailed'), 'error');
      }
    };
    input.click();
  }, [onUpdate, onLanguageChange, showToast]);

  // Reset to defaults
  const resetToDefaults = useCallback(async () => {
    try {
      await chrome.runtime.sendMessage({ type: 'RESET_SETTINGS' });
      const updated = await chrome.runtime.sendMessage({ type: 'GET_SETTINGS' });
      onUpdate(updated);
      setResetConfirm(false);

      if (updated.language) {
        setLanguage(updated.language);
        onLanguageChange();
      }

      showToast(t('resetSettings') + ' ✓', 'info');
    } catch (err) {
      console.error('[SettingsTab] Failed to reset settings:', err);
      showToast(t('unexpectedError'), 'error');
    }
  }, [onUpdate, onLanguageChange, showToast]);

  // Clear all data
  const clearAllData = useCallback(async () => {
    try {
      await chrome.runtime.sendMessage({ type: 'CLEAR_ALL_DATA' });
      setClearDataConfirm(false);
      // Reload extension
      window.location.reload();
    } catch (err) {
      console.error('[SettingsTab] Failed to clear data:', err);
      showToast(t('unexpectedError'), 'error');
    }
  }, [showToast]);

  if (!settings) {
    return (
      <div style={styles.loading}>
        <span>{t('loading')}...</span>
      </div>
    );
  }

  const availableLanguages = getAvailableLanguages();

  return (
    <div style={styles.container}>
      {/* Section Navigation */}
      <div style={styles.sectionNav} role="tablist" aria-label="Settings sections">
        {(['general', 'agentShield', 'mcpGateway', 'approval', 'advanced'] as const).map(
          (section) => (
            <button
              key={section}
              role="tab"
              aria-selected={activeSection === section}
              aria-controls={`${section}-panel`}
              id={`${section}-tab`}
              onClick={() => setActiveSection(section)}
              style={{
                ...styles.sectionButton,
                ...(activeSection === section ? styles.sectionButtonActive : {}),
              }}
            >
              {section === 'general' && t('general')}
              {section === 'agentShield' && t('agentShield')}
              {section === 'mcpGateway' && t('mcpGateway')}
              {section === 'approval' && t('approval')}
              {section === 'advanced' && t('advanced')}
            </button>
          )
        )}
      </div>

      {/* General Settings */}
      {activeSection === 'general' && (
        <div style={styles.section} role="tabpanel" id="general-panel" aria-labelledby="general-tab">
          <SettingRow
            label={t('enabled')}
            description={t('enableProtection')}
          >
            <Toggle
              value={settings.enabled}
              onChange={(v) => updateSetting('enabled', v)}
            />
          </SettingRow>

          <SettingRow
            label={t('protectionLevel')}
            description={t('howAggressive')}
          >
            <select
              value={settings.protectionLevel}
              onChange={(e) =>
                updateSetting('protectionLevel', e.target.value as Settings['protectionLevel'])
              }
              style={styles.select}
            >
              <option value="basic">{t('basic')}</option>
              <option value="recommended">{t('recommended')}</option>
              <option value="maximum">{t('maximum')}</option>
            </select>
          </SettingRow>

          <SettingRow
            label={t('notifications')}
            description={t('showNotifications')}
          >
            <Toggle
              value={settings.notifications}
              onChange={(v) => updateSetting('notifications', v)}
            />
          </SettingRow>

          <SettingRow
            label={t('language')}
            description={t('selectLanguage')}
          >
            <select
              value={settings.language}
              onChange={(e) => updateSetting('language', e.target.value as Language)}
              style={styles.select}
            >
              {availableLanguages.map((lang) => (
                <option key={lang.code} value={lang.code}>
                  {lang.name}
                </option>
              ))}
            </select>
          </SettingRow>

          <div style={styles.subsection}>
            <h4 style={styles.subsectionTitle}>{t('protectedPlatforms')}</h4>
            <div style={styles.platforms}>
              {['chatgpt', 'claude', 'gemini', 'perplexity', 'deepseek', 'grok', 'copilot', 'meta'].map(
                (platform) => (
                  <div
                    key={platform}
                    onClick={() => {
                      const isActive = settings.platforms.includes(platform);
                      const newPlatforms = isActive
                        ? settings.platforms.filter((p) => p !== platform)
                        : [...settings.platforms, platform];
                      updateSetting('platforms', newPlatforms);
                    }}
                    style={{
                      ...styles.platformChip,
                      ...(settings.platforms.includes(platform) ? styles.platformChipActive : {}),
                    }}
                  >
                    {platform.charAt(0).toUpperCase() + platform.slice(1)}
                  </div>
                )
              )}
            </div>
          </div>
        </div>
      )}

      {/* AgentShield Settings */}
      {activeSection === 'agentShield' && (
        <div style={styles.section} role="tabpanel" id="agentShield-panel" aria-labelledby="agentShield-tab">
          <div style={styles.sectionHeader}>
            <span style={styles.sectionIcon}>🤖</span>
            <span style={styles.sectionTitle}>{t('agentShield')}</span>
          </div>
          <p style={styles.sectionDescription}>{t('agentShieldDesc')}</p>

          <SettingRow
            label={t('enabled')}
            description={t('enableAgentShield')}
          >
            <Toggle
              value={settings.agentShield.enabled}
              onChange={(v) => updateAgentShield('enabled', v)}
            />
          </SettingRow>

          <SettingRow
            label={t('trustThreshold')}
            description={t('trustThresholdDesc')}
          >
            <div style={styles.sliderContainer}>
              <input
                type="range"
                min={0}
                max={100}
                value={settings.agentShield.trustThreshold}
                onChange={(e) => updateAgentShield('trustThreshold', parseInt(e.target.value))}
                style={styles.slider}
              />
              <span style={styles.sliderValue}>{settings.agentShield.trustThreshold}%</span>
            </div>
          </SettingRow>

          <SettingRow
            label={t('memoryInjectionDetection')}
            description={t('memoryInjectionDesc')}
          >
            <Toggle
              value={settings.agentShield.memoryInjectionDetection}
              onChange={(v) => updateAgentShield('memoryInjectionDetection', v)}
            />
          </SettingRow>

          <SettingRow
            label={t('maxAutoApproveValue')}
            description={t('maxAutoApproveDesc')}
          >
            <div style={styles.inputContainer}>
              <span style={styles.inputPrefix}>$</span>
              <input
                type="number"
                min={0}
                max={10000}
                value={settings.agentShield.maxAutoApproveValue}
                onChange={(e) =>
                  updateAgentShield('maxAutoApproveValue', parseInt(e.target.value) || 0)
                }
                style={styles.input}
              />
            </div>
          </SettingRow>
        </div>
      )}

      {/* MCPGateway Settings */}
      {activeSection === 'mcpGateway' && (
        <div style={styles.section} role="tabpanel" id="mcpGateway-panel" aria-labelledby="mcpGateway-tab">
          <div style={styles.sectionHeader}>
            <span style={styles.sectionIcon}>🔌</span>
            <span style={styles.sectionTitle}>{t('mcpGateway')}</span>
          </div>
          <p style={styles.sectionDescription}>{t('mcpGatewayDesc')}</p>

          <SettingRow
            label={t('enabled')}
            description={t('enableMCPGateway')}
          >
            <Toggle
              value={settings.mcpGateway.enabled}
              onChange={(v) => updateMCPGateway('enabled', v)}
            />
          </SettingRow>

          <SettingRow
            label={t('interceptAll')}
            description={t('interceptAllDesc')}
          >
            <Toggle
              value={settings.mcpGateway.interceptAll}
              onChange={(v) => updateMCPGateway('interceptAll', v)}
            />
          </SettingRow>

          <div style={styles.subsection}>
            <h4 style={styles.subsectionTitle}>{t('trustedServers')}</h4>
            <p style={styles.subsectionDescription}>{t('trustedServersDesc')}</p>
            <TrustedServersList
              servers={settings.mcpGateway.trustedServers}
              onChange={(servers) => updateMCPGateway('trustedServers', servers)}
            />
          </div>
        </div>
      )}

      {/* Approval Settings */}
      {activeSection === 'approval' && (
        <div style={styles.section} role="tabpanel" id="approval-panel" aria-labelledby="approval-tab">
          <div style={styles.sectionHeader}>
            <span style={styles.sectionIcon}>✅</span>
            <span style={styles.sectionTitle}>{t('approval')}</span>
          </div>
          <p style={styles.sectionDescription}>{t('approvalDesc')}</p>

          <SettingRow
            label={t('enabled')}
            description={t('enableApproval')}
          >
            <Toggle
              value={settings.approval.enabled}
              onChange={(v) => updateApproval('enabled', v)}
            />
          </SettingRow>

          <SettingRow
            label={t('defaultAction')}
            description={t('defaultActionDesc')}
          >
            <select
              value={settings.approval.defaultAction}
              onChange={(e) => updateApproval('defaultAction', e.target.value as ApprovalAction)}
              style={styles.select}
            >
              {DEFAULT_ACTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {t(opt.labelKey)}
                </option>
              ))}
            </select>
          </SettingRow>

          <SettingRow
            label={t('approvalTimeout')}
            description={t('approvalTimeoutDesc')}
          >
            <select
              value={settings.approval.autoRejectTimeoutMs}
              onChange={(e) => updateApproval('autoRejectTimeoutMs', parseInt(e.target.value))}
              style={styles.select}
            >
              {TIMEOUT_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>
          </SettingRow>

          <SettingRow
            label={t('approvalNotifications')}
            description={t('approvalNotificationsDesc')}
          >
            <Toggle
              value={settings.approval.showNotifications}
              onChange={(v) => updateApproval('showNotifications', v)}
            />
          </SettingRow>
        </div>
      )}

      {/* Advanced Settings */}
      {activeSection === 'advanced' && (
        <div style={styles.section} role="tabpanel" id="advanced-panel" aria-labelledby="advanced-tab">
          <div style={styles.sectionHeader}>
            <span style={styles.sectionIcon}>⚙️</span>
            <span style={styles.sectionTitle}>{t('advanced')}</span>
          </div>

          <div style={styles.subsection}>
            <h4 style={styles.subsectionTitle}>{t('dataManagement')}</h4>

            <div style={styles.actionRow}>
              <div>
                <div style={styles.actionLabel}>{t('exportSettings')}</div>
                <div style={styles.actionDescription}>{t('exportSettingsDesc')}</div>
              </div>
              <button onClick={exportSettings} style={styles.actionButton}>
                {t('export')}
              </button>
            </div>

            <div style={styles.actionRow}>
              <div>
                <div style={styles.actionLabel}>{t('importSettings')}</div>
                <div style={styles.actionDescription}>{t('importSettingsDesc')}</div>
              </div>
              <button onClick={importSettings} style={styles.actionButton}>
                {t('import')}
              </button>
            </div>

            <div style={styles.actionRow}>
              <div>
                <div style={styles.actionLabel}>{t('resetSettings')}</div>
                <div style={styles.actionDescription}>{t('resetSettingsDesc')}</div>
              </div>
              <button
                onClick={() => setResetConfirm(true)}
                style={{ ...styles.actionButton, ...styles.warningButton }}
              >
                {t('reset')}
              </button>
            </div>

            <div style={styles.actionRow}>
              <div>
                <div style={styles.actionLabel}>{t('clearAllData')}</div>
                <div style={styles.actionDescription}>{t('clearAllDataDesc')}</div>
              </div>
              <button
                onClick={() => setClearDataConfirm(true)}
                style={{ ...styles.actionButton, ...styles.dangerButton }}
              >
                {t('clearData')}
              </button>
            </div>
          </div>

          <div style={styles.subsection}>
            <h4 style={styles.subsectionTitle}>{t('about')}</h4>
            <div style={styles.aboutInfo}>
              <div style={styles.aboutRow}>
                <span>{t('version')}</span>
                <span>{EXTENSION_VERSION}</span>
              </div>
              <div style={styles.aboutRow}>
                <span>{t('website')}</span>
                <a
                  href="https://sentinelseed.dev"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.link}
                >
                  sentinelseed.dev
                </a>
              </div>
              <div style={styles.aboutRow}>
                <span>{t('github')}</span>
                <a
                  href="https://github.com/sentinel-seed/sentinel"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={styles.link}
                >
                  sentinel-seed/sentinel
                </a>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Reset Confirmation Dialog */}
      <ConfirmDialog
        isOpen={resetConfirm}
        title={t('resetSettings')}
        message={t('resetSettingsConfirm')}
        confirmText={t('reset')}
        cancelText={t('cancel')}
        onConfirm={resetToDefaults}
        onCancel={() => setResetConfirm(false)}
        variant="warning"
      />

      {/* Clear Data Confirmation Dialog */}
      <ConfirmDialog
        isOpen={clearDataConfirm}
        title={t('clearAllData')}
        message={t('clearAllDataConfirm')}
        confirmText={t('clearData')}
        cancelText={t('cancel')}
        onConfirm={clearAllData}
        onCancel={() => setClearDataConfirm(false)}
        variant="danger"
      />

      {/* Toast notification */}
      {toast && (
        <Toast
          message={toast.message}
          severity={toast.severity}
          onDismiss={() => setToast(null)}
        />
      )}
    </div>
  );
};

// =============================================================================
// SUB-COMPONENTS
// =============================================================================

interface SettingRowProps {
  label: string;
  description: string;
  children: React.ReactNode;
}

const SettingRow: React.FC<SettingRowProps> = ({ label, description, children }) => (
  <div style={styles.settingRow}>
    <div style={styles.settingInfo}>
      <div style={styles.settingLabel}>{label}</div>
      <div style={styles.settingDesc}>{description}</div>
    </div>
    {children}
  </div>
);

interface ToggleProps {
  value: boolean;
  onChange: (value: boolean) => void;
}

const Toggle: React.FC<ToggleProps> = ({ value, onChange }) => (
  <button
    onClick={() => onChange(!value)}
    style={{
      ...styles.toggle,
      background: value
        ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
        : 'rgba(255, 255, 255, 0.1)',
    }}
    aria-pressed={value}
  >
    {value ? 'ON' : 'OFF'}
  </button>
);

interface TrustedServersListProps {
  servers: string[];
  onChange: (servers: string[]) => void;
}

const TrustedServersList: React.FC<TrustedServersListProps> = ({ servers, onChange }) => {
  const [newServer, setNewServer] = useState('');

  const addServer = () => {
    const trimmed = newServer.trim();
    if (trimmed && !servers.includes(trimmed)) {
      onChange([...servers, trimmed]);
      setNewServer('');
    }
  };

  const removeServer = (server: string) => {
    onChange(servers.filter((s) => s !== server));
  };

  return (
    <div style={styles.trustedServers}>
      <div style={styles.serverInput}>
        <input
          type="text"
          value={newServer}
          onChange={(e) => setNewServer(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addServer()}
          placeholder={t('serverNamePlaceholder')}
          style={styles.input}
        />
        <button onClick={addServer} style={styles.addButton}>
          +
        </button>
      </div>
      {servers.length === 0 ? (
        <div style={styles.emptyServers}>{t('noTrustedServers')}</div>
      ) : (
        <div style={styles.serverList}>
          {servers.map((server) => (
            <div key={server} style={styles.serverChip}>
              <span>{server}</span>
              <button
                onClick={() => removeServer(server)}
                style={styles.removeButton}
                aria-label={`Remove ${server}`}
              >
                ×
              </button>
            </div>
          ))}
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
  loading: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    color: '#888',
  },
  sectionNav: {
    display: 'flex',
    gap: 4,
    padding: '4px',
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    flexWrap: 'wrap',
  },
  sectionButton: {
    flex: 1,
    minWidth: 'fit-content',
    padding: '8px 12px',
    background: 'transparent',
    border: 'none',
    borderRadius: 6,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
    whiteSpace: 'nowrap',
  },
  sectionButtonActive: {
    background: 'rgba(99, 102, 241, 0.2)',
    color: '#818cf8',
  },
  section: {
    display: 'flex',
    flexDirection: 'column',
    gap: 12,
  },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    marginBottom: 4,
  },
  sectionIcon: {
    fontSize: 18,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#fff',
  },
  sectionDescription: {
    fontSize: 12,
    color: '#888',
    marginBottom: 8,
  },
  subsection: {
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  subsectionTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#ccc',
    margin: '0 0 4px 0',
  },
  subsectionDescription: {
    fontSize: 11,
    color: '#666',
    marginBottom: 12,
  },
  settingRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  },
  settingInfo: {
    flex: 1,
    marginRight: 12,
  },
  settingLabel: {
    fontSize: 13,
    color: '#fff',
    marginBottom: 2,
  },
  settingDesc: {
    fontSize: 11,
    color: '#666',
  },
  toggle: {
    padding: '6px 16px',
    borderRadius: 16,
    border: 'none',
    color: '#fff',
    fontSize: 11,
    fontWeight: 600,
    cursor: 'pointer',
    minWidth: 50,
  },
  select: {
    padding: '6px 12px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: 6,
    color: '#fff',
    fontSize: 12,
    cursor: 'pointer',
    minWidth: 100,
  },
  sliderContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  slider: {
    width: 80,
    height: 4,
    cursor: 'pointer',
  },
  sliderValue: {
    fontSize: 12,
    color: '#818cf8',
    fontWeight: 600,
    minWidth: 36,
    textAlign: 'right',
  },
  inputContainer: {
    display: 'flex',
    alignItems: 'center',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: 6,
    overflow: 'hidden',
  },
  inputPrefix: {
    padding: '6px 8px',
    color: '#888',
    fontSize: 12,
    background: 'rgba(255, 255, 255, 0.05)',
  },
  input: {
    padding: '6px 12px',
    background: 'transparent',
    border: 'none',
    color: '#fff',
    fontSize: 12,
    width: 80,
    outline: 'none',
  },
  platforms: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
    marginTop: 8,
  },
  platformChip: {
    padding: '6px 12px',
    background: '#1a1a2e',
    borderRadius: 16,
    fontSize: 11,
    color: '#aaa',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    cursor: 'pointer',
  },
  platformChipActive: {
    background: 'rgba(99, 102, 241, 0.2)',
    borderColor: 'rgba(99, 102, 241, 0.5)',
    color: '#a5b4fc',
  },
  trustedServers: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
  },
  serverInput: {
    display: 'flex',
    gap: 8,
  },
  addButton: {
    padding: '6px 12px',
    background: 'rgba(99, 102, 241, 0.2)',
    border: '1px solid rgba(99, 102, 241, 0.3)',
    borderRadius: 6,
    color: '#818cf8',
    fontSize: 14,
    fontWeight: 600,
    cursor: 'pointer',
  },
  emptyServers: {
    padding: 12,
    textAlign: 'center',
    color: '#666',
    fontSize: 11,
  },
  serverList: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  serverChip: {
    display: 'flex',
    alignItems: 'center',
    gap: 6,
    padding: '4px 8px 4px 12px',
    background: 'rgba(16, 185, 129, 0.1)',
    border: '1px solid rgba(16, 185, 129, 0.2)',
    borderRadius: 12,
    fontSize: 11,
    color: '#10b981',
  },
  removeButton: {
    padding: 0,
    width: 16,
    height: 16,
    background: 'rgba(255, 255, 255, 0.1)',
    border: 'none',
    borderRadius: '50%',
    color: '#888',
    fontSize: 12,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  actionRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '10px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  },
  actionLabel: {
    fontSize: 12,
    color: '#fff',
    marginBottom: 2,
  },
  actionDescription: {
    fontSize: 10,
    color: '#666',
  },
  actionButton: {
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
  },
  warningButton: {
    background: 'rgba(245, 158, 11, 0.1)',
    borderColor: 'rgba(245, 158, 11, 0.3)',
    color: '#f59e0b',
  },
  dangerButton: {
    background: 'rgba(239, 68, 68, 0.1)',
    borderColor: 'rgba(239, 68, 68, 0.3)',
    color: '#ef4444',
  },
  aboutInfo: {
    display: 'flex',
    flexDirection: 'column',
    gap: 8,
    marginTop: 8,
  },
  aboutRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: 12,
    color: '#888',
  },
  link: {
    color: '#6366f1',
    textDecoration: 'none',
  },
};

export default SettingsTab;
