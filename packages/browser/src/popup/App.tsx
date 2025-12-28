import React, { useState, useEffect, useCallback } from 'react';
// M009: Import types from centralized location instead of duplicating
import {
  Settings,
  Stats,
  Alert,
  Language,
  DEFAULT_AGENT_SHIELD_SETTINGS,
  DEFAULT_MCP_GATEWAY_SETTINGS,
  DEFAULT_APPROVAL_SETTINGS,
} from '../types';
import { setLanguage, t, getAvailableLanguages, detectBrowserLanguage, Language as LangType } from '../lib/i18n';
import { AgentsTab, MCPTab } from './components';

type TabType = 'dashboard' | 'agents' | 'mcp' | 'alerts' | 'settings';

const App: React.FC = () => {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('dashboard');
  const [, forceUpdate] = useState({});

  useEffect(() => {
    // Try to load data, with retry if service worker is waking up
    const tryLoad = async (retries = 3) => {
      try {
        await loadData();
      } catch (err) {
        if (retries > 0) {
          // Wait a bit for service worker to wake up and retry
          setTimeout(() => tryLoad(retries - 1), 100);
        }
      }
    };
    tryLoad();
  }, []);

  const loadData = async () => {
    try {
      const [settingsRes, statsRes, alertsRes] = await Promise.all([
        chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }),
        chrome.runtime.sendMessage({ type: 'GET_STATS' }),
        chrome.runtime.sendMessage({ type: 'GET_ALERTS' }),
      ]);

      setSettings(settingsRes);
      setStats(statsRes);
      setAlerts(alertsRes || []);
      // Set language from settings
      if (settingsRes?.language) {
        setLanguage(settingsRes.language);
      }
    } catch (err) {
      // Background script may not be ready, use defaults
      console.warn('[Sentinel Guard] Could not connect to background:', err);
      const defaultLang = detectBrowserLanguage();
      setLanguage(defaultLang);
      setSettings({
        enabled: true,
        protectionLevel: 'recommended',
        platforms: ['chatgpt', 'claude', 'gemini', 'perplexity', 'deepseek', 'grok', 'copilot', 'meta'],
        notifications: true,
        language: defaultLang,
        agentShield: DEFAULT_AGENT_SHIELD_SETTINGS,
        mcpGateway: DEFAULT_MCP_GATEWAY_SETTINGS,
        approval: DEFAULT_APPROVAL_SETTINGS,
      });
      setStats({
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
      });
      setAlerts([]);
    }
  };

  const toggleEnabled = async () => {
    if (!settings) return;
    const updated = await chrome.runtime.sendMessage({
      type: 'UPDATE_SETTINGS',
      payload: { enabled: !settings.enabled },
    });
    setSettings(updated);
  };

  const unacknowledgedAlerts = alerts.filter((a) => !a.acknowledged);

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerContent}>
          <span style={styles.logo}>🛡️</span>
          <span style={styles.title}>Sentinel Guard</span>
        </div>
        <div
          style={{
            ...styles.statusBadge,
            background: settings?.enabled
              ? 'linear-gradient(135deg, #10b981, #059669)'
              : 'rgba(239, 68, 68, 0.2)',
            color: settings?.enabled ? '#fff' : '#ef4444',
          }}
        >
          {settings?.enabled ? `🟢 ${t('protected')}` : `🔴 ${t('disabled')}`}
        </div>
      </div>

      {/* Navigation */}
      <div style={styles.nav}>
        {(['dashboard', 'agents', 'mcp', 'alerts', 'settings'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.navButton,
              ...(activeTab === tab ? styles.navButtonActive : {}),
            }}
          >
            {tab === 'dashboard' && '📊'}
            {tab === 'agents' && '🤖'}
            {tab === 'mcp' && '🔌'}
            {tab === 'alerts' && `🔔 ${unacknowledgedAlerts.length > 0 ? `(${unacknowledgedAlerts.length})` : ''}`}
            {tab === 'settings' && '⚙️'}
            <span style={{ marginLeft: 4 }}>{t(tab)}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={styles.content}>
        {activeTab === 'dashboard' && <Dashboard stats={stats} settings={settings} />}
        {activeTab === 'agents' && <AgentsTab onStatsUpdate={loadData} />}
        {activeTab === 'mcp' && <MCPTab onStatsUpdate={loadData} />}
        {activeTab === 'alerts' && <Alerts alerts={alerts} onRefresh={loadData} />}
        {activeTab === 'settings' && <SettingsPanel settings={settings} onUpdate={setSettings} onLanguageChange={() => forceUpdate({})} />}
      </div>

      {/* Footer */}
      <div style={styles.footer}>
        <a href="https://sentinelseed.dev" target="_blank" rel="noopener noreferrer" style={styles.link}>
          sentinelseed.dev
        </a>
        <span style={styles.version}>v0.1.0</span>
      </div>
    </div>
  );
};

// Quick action handlers
const handleScanPage = async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab?.id) {
    chrome.tabs.sendMessage(tab.id, { type: 'SCAN_PAGE' });
  }
};

const handleCheckClipboard = async () => {
  try {
    const text = await navigator.clipboard.readText();
    if (text) {
      const response = await chrome.runtime.sendMessage({ type: 'SCAN_TEXT', payload: text });
      if (response?.hasCritical) {
        alert(`${response.matches.length} ${t('clipboardWarning')}`);
      } else if (response?.matches?.length > 0) {
        alert(`${response.matches.length} ${t('itemsToReview')}`);
      } else {
        alert(t('clipboardSafe'));
      }
    } else {
      alert(t('clipboardSafe'));
    }
  } catch {
    alert(t('clipboardSafe'));
  }
};

// Dashboard Component
const Dashboard: React.FC<{ stats: Stats | null; settings: Settings | null }> = ({ stats, settings }) => (
  <div>
    {/* Core Protection Stats */}
    <div style={styles.statsGrid}>
      <StatCard icon="🛑" label={t('threatsBlocked')} value={stats?.threatsBlocked || 0} color="#ef4444" />
      <StatCard icon="🔑" label={t('secretsCaught')} value={stats?.secretsCaught || 0} color="#f59e0b" />
      <StatCard icon="💬" label={t('sessionsProtected')} value={stats?.sessionsProtected || 0} color="#10b981" />
    </div>

    {/* Agent & MCP Stats */}
    <div style={styles.statsGrid}>
      <StatCard
        icon="🤖"
        label={t('agentsConnected')}
        value={stats?.agentConnections || 0}
        color="#6366f1"
      />
      <StatCard
        icon="🔌"
        label={t('servers')}
        value={stats?.mcpServersRegistered || 0}
        color="#8b5cf6"
      />
      <StatCard
        icon="⏳"
        label={t('pendingApprovals')}
        value={stats?.approvalsPending || 0}
        color="#f59e0b"
      />
    </div>

    <div style={styles.currentLevel}>
      <span style={styles.shieldIcon}>🛡️</span>
      <span style={styles.levelText}>
        {settings?.protectionLevel === 'basic' && `🔓 ${t('basic')}`}
        {settings?.protectionLevel === 'recommended' && `🔐 ${t('recommended')}`}
        {settings?.protectionLevel === 'maximum' && `🔒 ${t('maximum')}`}
      </span>
      <span style={styles.levelSubtext}>{t('protection')}</span>
    </div>

    {/* Activity Summary */}
    {(stats?.agentActionsIntercepted || 0) > 0 || (stats?.mcpToolCallsIntercepted || 0) > 0 ? (
      <div style={styles.activitySummary}>
        <h3 style={styles.sectionTitle}>{t('actionHistory')}</h3>
        <div style={styles.activityRow}>
          <span style={styles.activityLabel}>{t('agentShield')}</span>
          <span style={styles.activityStats}>
            <span style={{ color: '#10b981' }}>✓{stats?.agentActionsApproved || 0}</span>
            {' / '}
            <span style={{ color: '#ef4444' }}>✗{stats?.agentActionsRejected || 0}</span>
          </span>
        </div>
        <div style={styles.activityRow}>
          <span style={styles.activityLabel}>{t('mcpGateway')}</span>
          <span style={styles.activityStats}>
            <span style={{ color: '#10b981' }}>✓{stats?.mcpToolCallsApproved || 0}</span>
            {' / '}
            <span style={{ color: '#ef4444' }}>✗{stats?.mcpToolCallsRejected || 0}</span>
          </span>
        </div>
      </div>
    ) : null}

    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>{t('quickActions')}</h3>
      <div style={styles.actions}>
        <button style={styles.actionButton} onClick={handleScanPage}>
          🔍 {t('scanPage')}
        </button>
        <button style={styles.actionButton} onClick={handleCheckClipboard}>
          📋 {t('checkClipboard')}
        </button>
      </div>
    </div>
  </div>
);

// Stat Card Component
const StatCard: React.FC<{ icon: string; label: string; value: number; color: string }> = ({
  icon,
  label,
  value,
  color,
}) => (
  <div style={styles.statCard}>
    <span style={{ fontSize: 24 }}>{icon}</span>
    <span style={{ ...styles.statValue, color }}>{value}</span>
    <span style={styles.statLabel}>{label}</span>
  </div>
);

// Alerts Component
const Alerts: React.FC<{ alerts: Alert[]; onRefresh: () => void }> = ({ alerts, onRefresh }) => {
  const acknowledgeAlert = async (id: string) => {
    await chrome.runtime.sendMessage({ type: 'ACKNOWLEDGE_ALERT', payload: id });
    onRefresh();
  };

  if (alerts.length === 0) {
    return (
      <div style={styles.emptyState}>
        <span style={{ fontSize: 48 }}>✅</span>
        <p>{t('noAlerts')}</p>
        <p style={{ color: '#666', fontSize: 12 }}>{t('noAlertsDesc')}</p>
      </div>
    );
  }

  return (
    <div>
      {alerts.slice(0, 10).map((alert) => (
        <div
          key={alert.id}
          style={{
            ...styles.alertCard,
            opacity: alert.acknowledged ? 0.5 : 1,
          }}
        >
          <div style={styles.alertHeader}>
            <span style={styles.alertType}>
              {alert.type === 'secret' && '🔑'}
              {alert.type === 'harvest' && '👁️'}
              {alert.type === 'bot' && '🤖'}
              {alert.type === 'phishing' && '🎣'}
            </span>
            <span style={styles.alertTime}>
              {new Date(alert.timestamp).toLocaleTimeString()}
            </span>
          </div>
          <p style={styles.alertMessage}>{alert.message}</p>
          {!alert.acknowledged && (
            <button
              onClick={() => acknowledgeAlert(alert.id)}
              style={styles.acknowledgeButton}
            >
              {t('acknowledge')}
            </button>
          )}
        </div>
      ))}
    </div>
  );
};

// Settings Component
const SettingsPanel: React.FC<{
  settings: Settings | null;
  onUpdate: (s: Settings) => void;
  onLanguageChange: () => void;
}> = ({ settings, onUpdate, onLanguageChange }) => {
  const updateSetting = async (key: keyof Settings, value: unknown) => {
    const updated = await chrome.runtime.sendMessage({
      type: 'UPDATE_SETTINGS',
      payload: { [key]: value },
    });
    onUpdate(updated);

    // If language changed, update the i18n system and trigger re-render
    if (key === 'language') {
      setLanguage(value as LangType);
      onLanguageChange();
    }
  };

  if (!settings) return null;

  const availableLanguages = getAvailableLanguages();

  return (
    <div>
      <div style={styles.settingRow}>
        <div>
          <div style={styles.settingLabel}>{t('enabled')}</div>
          <div style={styles.settingDesc}>{t('enableProtection')}</div>
        </div>
        <button
          onClick={() => updateSetting('enabled', !settings.enabled)}
          style={{
            ...styles.toggle,
            background: settings.enabled
              ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
              : 'rgba(255, 255, 255, 0.1)',
          }}
        >
          {settings.enabled ? 'ON' : 'OFF'}
        </button>
      </div>

      <div style={styles.settingRow}>
        <div>
          <div style={styles.settingLabel}>{t('protectionLevel')}</div>
          <div style={styles.settingDesc}>{t('howAggressive')}</div>
        </div>
        <select
          value={settings.protectionLevel}
          onChange={(e) => updateSetting('protectionLevel', e.target.value)}
          style={styles.select}
        >
          <option value="basic">{t('basic')}</option>
          <option value="recommended">{t('recommended')}</option>
          <option value="maximum">{t('maximum')}</option>
        </select>
      </div>

      <div style={styles.settingRow}>
        <div>
          <div style={styles.settingLabel}>{t('notifications')}</div>
          <div style={styles.settingDesc}>{t('showNotifications')}</div>
        </div>
        <button
          onClick={() => updateSetting('notifications', !settings.notifications)}
          style={{
            ...styles.toggle,
            background: settings.notifications
              ? 'linear-gradient(135deg, #6366f1, #8b5cf6)'
              : 'rgba(255, 255, 255, 0.1)',
          }}
        >
          {settings.notifications ? 'ON' : 'OFF'}
        </button>
      </div>

      <div style={styles.settingRow}>
        <div>
          <div style={styles.settingLabel}>{t('language')}</div>
          <div style={styles.settingDesc}>{t('selectLanguage')}</div>
        </div>
        <select
          value={settings.language}
          onChange={(e) => updateSetting('language', e.target.value)}
          style={styles.select}
        >
          {availableLanguages.map((lang) => (
            <option key={lang.code} value={lang.code}>
              {lang.name}
            </option>
          ))}
        </select>
      </div>

      <div style={{ ...styles.section, marginTop: 20 }}>
        <h3 style={styles.sectionTitle}>{t('protectedPlatforms')}</h3>
        <div style={styles.platforms}>
          {['chatgpt', 'claude', 'gemini', 'perplexity', 'deepseek', 'grok', 'copilot', 'meta'].map((platform) => (
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
                cursor: 'pointer',
              }}
            >
              {platform.charAt(0).toUpperCase() + platform.slice(1)}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

// Styles
const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    minHeight: 480,
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 20px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
    background: 'linear-gradient(180deg, #0f0f1a 0%, #0a0a0f 100%)',
  },
  headerContent: {
    display: 'flex',
    alignItems: 'center',
    gap: 8,
  },
  logo: {
    fontSize: 24,
  },
  title: {
    fontSize: 16,
    fontWeight: 600,
    color: '#fff',
  },
  statusBadge: {
    padding: '4px 12px',
    borderRadius: 12,
    fontSize: 12,
    fontWeight: 500,
  },
  nav: {
    display: 'flex',
    gap: 4,
    padding: '8px 16px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
  },
  navButton: {
    flex: 1,
    padding: '8px 12px',
    background: 'transparent',
    border: 'none',
    borderRadius: 8,
    color: '#888',
    fontSize: 12,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  navButtonActive: {
    background: 'rgba(99, 102, 241, 0.2)',
    color: '#818cf8',
  },
  content: {
    flex: 1,
    padding: 16,
    overflowY: 'auto',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 20px',
    borderTop: '1px solid rgba(255, 255, 255, 0.05)',
    fontSize: 11,
    color: '#666',
  },
  link: {
    color: '#6366f1',
    textDecoration: 'none',
  },
  version: {
    color: '#444',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(3, 1fr)',
    gap: 8,
    marginBottom: 20,
  },
  statCard: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 12,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 700,
  },
  statLabel: {
    fontSize: 10,
    color: '#666',
    textAlign: 'center',
  },
  section: {
    marginBottom: 16,
  },
  sectionTitle: {
    fontSize: 12,
    color: '#888',
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 1,
  },
  actions: {
    display: 'flex',
    gap: 8,
  },
  actionButton: {
    flex: 1,
    padding: '10px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 8,
    color: '#fff',
    fontSize: 12,
    cursor: 'pointer',
  },
  emptyState: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 40,
    textAlign: 'center',
  },
  alertCard: {
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    marginBottom: 8,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  alertHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    marginBottom: 8,
  },
  alertType: {
    fontSize: 16,
  },
  alertTime: {
    fontSize: 10,
    color: '#666',
  },
  alertMessage: {
    fontSize: 12,
    color: '#ccc',
    marginBottom: 8,
  },
  acknowledgeButton: {
    padding: '4px 12px',
    background: 'transparent',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 4,
    color: '#888',
    fontSize: 11,
    cursor: 'pointer',
  },
  settingRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 0',
    borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
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
  },
  select: {
    padding: '6px 12px',
    background: '#1a1a2e',
    border: '1px solid rgba(255, 255, 255, 0.2)',
    borderRadius: 6,
    color: '#fff',
    fontSize: 12,
    cursor: 'pointer',
  },
  platforms: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
  },
  platformChip: {
    padding: '6px 12px',
    background: '#1a1a2e',
    borderRadius: 16,
    fontSize: 11,
    color: '#aaa',
    border: '1px solid rgba(255, 255, 255, 0.1)',
  },
  platformChipActive: {
    background: 'rgba(99, 102, 241, 0.2)',
    borderColor: 'rgba(99, 102, 241, 0.5)',
    color: '#a5b4fc',
  },
  currentLevel: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    padding: '12px 16px',
    marginBottom: 16,
    background: 'rgba(99, 102, 241, 0.1)',
    borderRadius: 8,
    border: '1px solid rgba(99, 102, 241, 0.2)',
  },
  shieldIcon: {
    fontSize: 18,
  },
  levelText: {
    fontSize: 14,
    fontWeight: 600,
    color: '#a5b4fc',
  },
  levelSubtext: {
    fontSize: 12,
    color: '#888',
  },
  activitySummary: {
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    marginBottom: 16,
    border: '1px solid rgba(255, 255, 255, 0.05)',
  },
  activityRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 0',
  },
  activityLabel: {
    fontSize: 12,
    color: '#888',
  },
  activityStats: {
    fontSize: 12,
    fontWeight: 600,
  },
};

export default App;
