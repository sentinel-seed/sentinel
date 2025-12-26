/**
 * Sentinel Guard - Type Definitions
 */

// Settings
export type Language = 'en' | 'es' | 'pt';

export interface Settings {
  enabled: boolean;
  protectionLevel: 'basic' | 'recommended' | 'maximum';
  platforms: string[];
  notifications: boolean;
  language: Language;
}

// Statistics
export interface Stats {
  threatsBlocked: number;
  secretsCaught: number;
  sessionsProtected: number;
  botsDetected: number;
  piiBlocked: number;
  clipboardScans: number;
  walletThreats: number;
  lastUpdated: number;
}

// Alerts
export type AlertType =
  | 'harvest'       // Data harvesting attempt
  | 'secret'        // Secret/API key detected
  | 'bot'           // Bot/automation detected
  | 'phishing'      // Phishing attempt
  | 'pii'           // PII exposure
  | 'clipboard'     // Clipboard threat
  | 'wallet'        // Wallet/crypto threat
  | 'dapp';         // dApp security alert

export interface Alert {
  id: string;
  type: AlertType;
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
  | 'SCAN_PAGE'
  | 'DETECT_BOT'
  | 'SCAN_PII'
  | 'SCAN_CLIPBOARD'
  | 'SCAN_WALLET'
  | 'ANALYZE_DAPP'
  | 'PREVIEW_TRANSACTION';

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
