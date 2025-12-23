import React, { useState, useEffect } from 'react';

interface Settings {
  enabled: boolean;
  protectionLevel: 'basic' | 'recommended' | 'maximum';
  platforms: string[];
  notifications: boolean;
}

interface Stats {
  threatsBlocked: number;
  secretsCaught: number;
  sessionsProtected: number;
  lastUpdated: number;
}

interface Alert {
  id: string;
  type: string;
  message: string;
  timestamp: number;
  acknowledged: boolean;
}

const App: React.FC = () => {
  const [settings, setSettings] = useState<Settings | null>(null);
  const [stats, setStats] = useState<Stats | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'alerts' | 'settings'>('dashboard');

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    const [settingsRes, statsRes, alertsRes] = await Promise.all([
      chrome.runtime.sendMessage({ type: 'GET_SETTINGS' }),
      chrome.runtime.sendMessage({ type: 'GET_STATS' }),
      chrome.runtime.sendMessage({ type: 'GET_ALERTS' }),
    ]);

    setSettings(settingsRes);
    setStats(statsRes);
    setAlerts(alertsRes || []);
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
          {settings?.enabled ? '🟢 Protected' : '🔴 Disabled'}
        </div>
      </div>

      {/* Navigation */}
      <div style={styles.nav}>
        {(['dashboard', 'alerts', 'settings'] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            style={{
              ...styles.navButton,
              ...(activeTab === tab ? styles.navButtonActive : {}),
            }}
          >
            {tab === 'dashboard' && '📊'}
            {tab === 'alerts' && `🔔 ${unacknowledgedAlerts.length > 0 ? `(${unacknowledgedAlerts.length})` : ''}`}
            {tab === 'settings' && '⚙️'}
            <span style={{ marginLeft: 4 }}>{tab.charAt(0).toUpperCase() + tab.slice(1)}</span>
          </button>
        ))}
      </div>

      {/* Content */}
      <div style={styles.content}>
        {activeTab === 'dashboard' && <Dashboard stats={stats} settings={settings} />}
        {activeTab === 'alerts' && <Alerts alerts={alerts} onRefresh={loadData} />}
        {activeTab === 'settings' && <SettingsPanel settings={settings} onUpdate={setSettings} />}
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
        alert(`Warning: ${response.matches.length} sensitive item(s) found in clipboard!`);
      } else if (response?.matches?.length > 0) {
        alert(`Found ${response.matches.length} item(s) to review in clipboard.`);
      } else {
        alert('Clipboard is clean!');
      }
    } else {
      alert('Clipboard is empty.');
    }
  } catch {
    alert('Unable to read clipboard. Please grant permission.');
  }
};

// Dashboard Component
const Dashboard: React.FC<{ stats: Stats | null; settings: Settings | null }> = ({ stats, settings }) => (
  <div>
    <div style={styles.statsGrid}>
      <StatCard icon="🛑" label="Threats Blocked" value={stats?.threatsBlocked || 0} color="#ef4444" />
      <StatCard icon="🔑" label="Secrets Caught" value={stats?.secretsCaught || 0} color="#f59e0b" />
      <StatCard icon="💬" label="Sessions Protected" value={stats?.sessionsProtected || 0} color="#10b981" />
    </div>

    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>Protection Level</h3>
      <div style={styles.protectionLevels}>
        {(['basic', 'recommended', 'maximum'] as const).map((level) => (
          <div
            key={level}
            style={{
              ...styles.levelCard,
              ...(settings?.protectionLevel === level ? styles.levelCardActive : {}),
            }}
          >
            <span style={styles.levelIcon}>
              {level === 'basic' && '🔓'}
              {level === 'recommended' && '🔐'}
              {level === 'maximum' && '🔒'}
            </span>
            <span style={styles.levelName}>{level.charAt(0).toUpperCase() + level.slice(1)}</span>
          </div>
        ))}
      </div>
    </div>

    <div style={styles.section}>
      <h3 style={styles.sectionTitle}>Quick Actions</h3>
      <div style={styles.actions}>
        <button style={styles.actionButton} onClick={handleScanPage}>
          🔍 Scan Page
        </button>
        <button style={styles.actionButton} onClick={handleCheckClipboard}>
          📋 Check Clipboard
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
        <p>No alerts</p>
        <p style={{ color: '#666', fontSize: 12 }}>You're all clear!</p>
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
              Dismiss
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
}> = ({ settings, onUpdate }) => {
  const updateSetting = async (key: keyof Settings, value: unknown) => {
    const updated = await chrome.runtime.sendMessage({
      type: 'UPDATE_SETTINGS',
      payload: { [key]: value },
    });
    onUpdate(updated);
  };

  if (!settings) return null;

  return (
    <div>
      <div style={styles.settingRow}>
        <div>
          <div style={styles.settingLabel}>Protection Enabled</div>
          <div style={styles.settingDesc}>Enable or disable all protection</div>
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
          <div style={styles.settingLabel}>Protection Level</div>
          <div style={styles.settingDesc}>How aggressive should protection be?</div>
        </div>
        <select
          value={settings.protectionLevel}
          onChange={(e) => updateSetting('protectionLevel', e.target.value)}
          style={styles.select}
        >
          <option value="basic">Basic</option>
          <option value="recommended">Recommended</option>
          <option value="maximum">Maximum</option>
        </select>
      </div>

      <div style={styles.settingRow}>
        <div>
          <div style={styles.settingLabel}>Notifications</div>
          <div style={styles.settingDesc}>Show desktop notifications</div>
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

      <div style={{ ...styles.section, marginTop: 20 }}>
        <h3 style={styles.sectionTitle}>Protected Platforms</h3>
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
  protectionLevels: {
    display: 'flex',
    gap: 8,
  },
  levelCard: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 4,
    padding: 12,
    background: 'rgba(255, 255, 255, 0.02)',
    borderRadius: 8,
    border: '1px solid rgba(255, 255, 255, 0.05)',
    cursor: 'pointer',
  },
  levelCardActive: {
    background: 'rgba(99, 102, 241, 0.1)',
    borderColor: 'rgba(99, 102, 241, 0.3)',
  },
  levelIcon: {
    fontSize: 20,
  },
  levelName: {
    fontSize: 11,
    color: '#aaa',
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
    background: 'rgba(255, 255, 255, 0.05)',
    border: '1px solid rgba(255, 255, 255, 0.1)',
    borderRadius: 6,
    color: '#fff',
    fontSize: 12,
  },
  platforms: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 8,
  },
  platformChip: {
    padding: '6px 12px',
    background: 'rgba(255, 255, 255, 0.05)',
    borderRadius: 16,
    fontSize: 11,
    color: '#888',
    border: '1px solid transparent',
  },
  platformChipActive: {
    background: 'rgba(99, 102, 241, 0.1)',
    borderColor: 'rgba(99, 102, 241, 0.3)',
    color: '#818cf8',
  },
};

export default App;
