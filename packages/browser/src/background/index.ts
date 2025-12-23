/**
 * Sentinel Guard - Background Service Worker
 *
 * Handles:
 * - Message routing between popup and content scripts
 * - Storage management
 * - Notifications
 * - Extension monitoring
 */

import { validateTHSP, ValidationContext } from '../lib/thsp';
import { scanAll, PatternMatch } from '../lib/patterns';

// Types
interface StorageData {
  settings: Settings;
  stats: Stats;
  alerts: Alert[];
}

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
  type: 'harvest' | 'secret' | 'bot' | 'phishing';
  message: string;
  timestamp: number;
  acknowledged: boolean;
  details?: Record<string, unknown>;
}

// Default settings
const DEFAULT_SETTINGS: Settings = {
  enabled: true,
  protectionLevel: 'recommended',
  platforms: ['chatgpt', 'claude', 'gemini', 'perplexity', 'deepseek', 'grok', 'copilot', 'meta'],
  notifications: true,
};

const DEFAULT_STATS: Stats = {
  threatsBlocked: 0,
  secretsCaught: 0,
  sessionsProtected: 0,
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

    console.log('[Sentinel Guard] Extension installed');
  }

  // Setup health check alarm (runs every minute)
  chrome.alarms.create('healthCheck', { periodInMinutes: 1 });
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
});

// Message handler
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
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
  sender: chrome.runtime.MessageSender
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
  return updated;
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

console.log('[Sentinel Guard] Background service worker started');
