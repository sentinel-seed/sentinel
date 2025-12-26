/**
 * Sentinel Guard - Clipboard Guard
 *
 * Protects clipboard operations from:
 * - Accidental copy of secrets/PII
 * - Paste of sensitive data into AI chats
 * - Clipboard hijacking by malicious scripts
 * - Data exfiltration via clipboard
 */

import { scanAll, PatternMatch } from './patterns';
import { scanForPII, PIIMatch, PIICategory } from './pii-guard';

export interface ClipboardScanResult {
  hasSensitiveData: boolean;
  hasSecrets: boolean;
  hasPII: boolean;
  secrets: PatternMatch[];
  pii: PIIMatch[];
  riskLevel: 'safe' | 'low' | 'medium' | 'high' | 'critical';
  summary: string;
}

export interface ClipboardEventRecord {
  type: 'copy' | 'cut' | 'paste';
  timestamp: number;
  source: string; // URL or context
  hasSensitiveData: boolean;
  wasBlocked: boolean;
  details?: ClipboardScanResult;
}

export interface ClipboardGuardConfig {
  blockCopySecrets: boolean;
  blockPastePII: boolean;
  warnOnSensitiveCopy: boolean;
  warnOnSensitivePaste: boolean;
  trackClipboardHistory: boolean;
  maxHistorySize: number;
}

const DEFAULT_CONFIG: ClipboardGuardConfig = {
  blockCopySecrets: false, // Don't block by default, just warn
  blockPastePII: false,
  warnOnSensitiveCopy: true,
  warnOnSensitivePaste: true,
  trackClipboardHistory: true,
  maxHistorySize: 50,
};

// Event history for audit
const clipboardHistory: ClipboardEventRecord[] = [];

// Current configuration
let config: ClipboardGuardConfig = { ...DEFAULT_CONFIG };

/**
 * Update clipboard guard configuration
 */
export function configureClipboardGuard(newConfig: Partial<ClipboardGuardConfig>): void {
  config = { ...config, ...newConfig };
}

/**
 * Get current configuration
 */
export function getClipboardGuardConfig(): ClipboardGuardConfig {
  return { ...config };
}

/**
 * Scan clipboard content for sensitive data
 */
export function scanClipboardContent(text: string): ClipboardScanResult {
  if (!text || typeof text !== 'string') {
    return {
      hasSensitiveData: false,
      hasSecrets: false,
      hasPII: false,
      secrets: [],
      pii: [],
      riskLevel: 'safe',
      summary: 'Empty or invalid clipboard content',
    };
  }

  const secrets = scanAll(text);
  const pii = scanForPII(text);

  const hasSecrets = secrets.length > 0;
  const hasPII = pii.length > 0;
  const hasSensitiveData = hasSecrets || hasPII;

  // Calculate risk level
  let riskLevel: ClipboardScanResult['riskLevel'] = 'safe';

  if (hasSensitiveData) {
    const criticalSecrets = secrets.filter((s) => s.severity === 'critical').length;
    const highSecrets = secrets.filter((s) => s.severity === 'high').length;
    const highConfidencePII = pii.filter((p) => p.confidence >= 80).length;
    const authPII = pii.filter((p) => p.category === 'auth').length;
    const financialPII = pii.filter((p) => p.category === 'financial').length;

    if (criticalSecrets > 0 || authPII > 0) {
      riskLevel = 'critical';
    } else if (highSecrets > 0 || financialPII > 0) {
      riskLevel = 'high';
    } else if (highConfidencePII > 0) {
      riskLevel = 'medium';
    } else {
      riskLevel = 'low';
    }
  }

  // Generate summary
  const parts: string[] = [];
  if (secrets.length > 0) {
    const types = [...new Set(secrets.map((s) => s.type))];
    parts.push(`${secrets.length} secret(s): ${types.slice(0, 3).join(', ')}`);
  }
  if (pii.length > 0) {
    const categories = [...new Set(pii.map((p) => p.category))];
    parts.push(`${pii.length} PII item(s): ${categories.join(', ')}`);
  }

  const summary = parts.length > 0
    ? `Found ${parts.join('; ')}`
    : 'No sensitive data detected';

  return {
    hasSensitiveData,
    hasSecrets,
    hasPII,
    secrets,
    pii,
    riskLevel,
    summary,
  };
}

/**
 * Read and scan current clipboard
 */
export async function scanCurrentClipboard(): Promise<ClipboardScanResult> {
  try {
    const text = await navigator.clipboard.readText();
    return scanClipboardContent(text);
  } catch (error) {
    return {
      hasSensitiveData: false,
      hasSecrets: false,
      hasPII: false,
      secrets: [],
      pii: [],
      riskLevel: 'safe',
      summary: 'Unable to read clipboard (permission denied or empty)',
    };
  }
}

/**
 * Record a clipboard event
 */
function recordEvent(event: ClipboardEventRecord): void {
  if (!config.trackClipboardHistory) return;

  clipboardHistory.unshift(event);

  // Trim history
  if (clipboardHistory.length > config.maxHistorySize) {
    clipboardHistory.length = config.maxHistorySize;
  }
}

/**
 * Get clipboard event history
 */
export function getClipboardHistory(): ClipboardEventRecord[] {
  return [...clipboardHistory];
}

/**
 * Clear clipboard history
 */
export function clearClipboardHistory(): void {
  clipboardHistory.length = 0;
}

/**
 * Handle copy event
 */
export function handleCopyEvent(
  text: string,
  source: string
): { allowed: boolean; scanResult: ClipboardScanResult; message?: string } {
  const scanResult = scanClipboardContent(text);

  const event: ClipboardEventRecord = {
    type: 'copy',
    timestamp: Date.now(),
    source,
    hasSensitiveData: scanResult.hasSensitiveData,
    wasBlocked: false,
    details: scanResult,
  };

  // Check if we should block
  if (config.blockCopySecrets && scanResult.hasSecrets) {
    const criticalSecrets = scanResult.secrets.filter((s) => s.severity === 'critical');
    if (criticalSecrets.length > 0) {
      event.wasBlocked = true;
      recordEvent(event);

      return {
        allowed: false,
        scanResult,
        message: `Blocked copy: ${criticalSecrets.length} critical secret(s) detected`,
      };
    }
  }

  recordEvent(event);

  // Return with warning if needed
  if (config.warnOnSensitiveCopy && scanResult.hasSensitiveData) {
    return {
      allowed: true,
      scanResult,
      message: `Warning: ${scanResult.summary}`,
    };
  }

  return { allowed: true, scanResult };
}

/**
 * Handle paste event
 */
export function handlePasteEvent(
  text: string,
  source: string
): { allowed: boolean; scanResult: ClipboardScanResult; message?: string } {
  const scanResult = scanClipboardContent(text);

  const event: ClipboardEventRecord = {
    type: 'paste',
    timestamp: Date.now(),
    source,
    hasSensitiveData: scanResult.hasSensitiveData,
    wasBlocked: false,
    details: scanResult,
  };

  // Check if we should block paste of PII
  if (config.blockPastePII && scanResult.hasPII) {
    const highRiskPII = scanResult.pii.filter(
      (p) => p.category === 'auth' || p.category === 'financial'
    );

    if (highRiskPII.length > 0) {
      event.wasBlocked = true;
      recordEvent(event);

      return {
        allowed: false,
        scanResult,
        message: `Blocked paste: ${highRiskPII.length} high-risk PII item(s) detected`,
      };
    }
  }

  recordEvent(event);

  // Return with warning if needed
  if (config.warnOnSensitivePaste && scanResult.hasSensitiveData) {
    return {
      allowed: true,
      scanResult,
      message: `Warning: Pasting ${scanResult.summary}`,
    };
  }

  return { allowed: true, scanResult };
}

/**
 * Safely write to clipboard (with optional masking)
 */
export async function safeClipboardWrite(
  text: string,
  maskSensitive = false
): Promise<{ success: boolean; masked: boolean; message: string }> {
  try {
    let textToWrite = text;
    let masked = false;

    if (maskSensitive) {
      const scanResult = scanClipboardContent(text);

      if (scanResult.hasSensitiveData) {
        // Mask secrets
        for (const secret of [...scanResult.secrets].sort((a, b) => b.start - a.start)) {
          const showChars = Math.min(4, Math.floor((secret.end - secret.start) / 2));
          const maskedValue = secret.value.substring(0, showChars) + '****';
          textToWrite = textToWrite.slice(0, secret.start) + maskedValue + textToWrite.slice(secret.end);
        }

        // Mask PII
        for (const pii of [...scanResult.pii].sort((a, b) => b.start - a.start)) {
          textToWrite = textToWrite.slice(0, pii.start) + pii.masked + textToWrite.slice(pii.end);
        }

        masked = true;
      }
    }

    await navigator.clipboard.writeText(textToWrite);

    return {
      success: true,
      masked,
      message: masked ? 'Copied with sensitive data masked' : 'Copied to clipboard',
    };
  } catch (error) {
    return {
      success: false,
      masked: false,
      message: 'Failed to write to clipboard',
    };
  }
}

/**
 * Check if clipboard contains specific types of sensitive data
 */
export async function checkClipboardForType(
  type: 'secrets' | 'pii' | 'auth' | 'financial' | 'identity'
): Promise<boolean> {
  const result = await scanCurrentClipboard();

  switch (type) {
    case 'secrets':
      return result.hasSecrets;
    case 'pii':
      return result.hasPII;
    case 'auth':
      return result.pii.some((p) => p.category === 'auth');
    case 'financial':
      return result.pii.some((p) => p.category === 'financial');
    case 'identity':
      return result.pii.some((p) => p.category === 'identity');
    default:
      return false;
  }
}

/**
 * Setup clipboard monitoring listeners
 */
export function setupClipboardGuard(
  onCopy?: (result: ClipboardScanResult) => void,
  onPaste?: (result: ClipboardScanResult) => void
): () => void {
  const copyHandler = (e: Event) => {
    const selection = window.getSelection()?.toString() || '';
    if (selection) {
      const result = handleCopyEvent(selection, window.location.href);
      if (onCopy) onCopy(result.scanResult);
    }
  };

  const pasteHandler = (e: Event) => {
    // Use ClipboardEvent.clipboardData instead of navigator.clipboard
    // because navigator.clipboard.readText() doesn't work in paste events
    const clipboardEvent = e as ClipboardEvent;
    const text = clipboardEvent.clipboardData?.getData('text/plain') || '';

    if (text) {
      const result = handlePasteEvent(text, window.location.href);
      if (onPaste) onPaste(result.scanResult);
    }
  };

  document.addEventListener('copy', copyHandler);
  document.addEventListener('paste', pasteHandler);

  // Return cleanup function
  return () => {
    document.removeEventListener('copy', copyHandler);
    document.removeEventListener('paste', pasteHandler);
  };
}

/**
 * Get statistics about clipboard usage
 */
export interface ClipboardStats {
  totalEvents: number;
  copyEvents: number;
  pasteEvents: number;
  blockedEvents: number;
  sensitiveDataEvents: number;
  riskBreakdown: Record<ClipboardScanResult['riskLevel'], number>;
}

export function getClipboardStats(): ClipboardStats {
  const stats: ClipboardStats = {
    totalEvents: clipboardHistory.length,
    copyEvents: 0,
    pasteEvents: 0,
    blockedEvents: 0,
    sensitiveDataEvents: 0,
    riskBreakdown: {
      safe: 0,
      low: 0,
      medium: 0,
      high: 0,
      critical: 0,
    },
  };

  for (const event of clipboardHistory) {
    if (event.type === 'copy') stats.copyEvents++;
    if (event.type === 'paste') stats.pasteEvents++;
    if (event.wasBlocked) stats.blockedEvents++;
    if (event.hasSensitiveData) stats.sensitiveDataEvents++;
    if (event.details) {
      stats.riskBreakdown[event.details.riskLevel]++;
    }
  }

  return stats;
}
