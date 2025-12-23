/**
 * Sentinel Guard - Type Definitions
 */

// Settings
export interface Settings {
  enabled: boolean;
  protectionLevel: 'basic' | 'recommended' | 'maximum';
  platforms: string[];
  notifications: boolean;
}

// Statistics
export interface Stats {
  threatsBlocked: number;
  secretsCaught: number;
  sessionsProtected: number;
  lastUpdated: number;
}

// Alerts
export interface Alert {
  id: string;
  type: 'harvest' | 'secret' | 'bot' | 'phishing';
  message: string;
  timestamp: number;
  acknowledged: boolean;
  details?: Record<string, unknown>;
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

// Messages
export type MessageType =
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
  | 'SCAN_PAGE';

export interface Message {
  type: MessageType;
  payload?: unknown;
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
