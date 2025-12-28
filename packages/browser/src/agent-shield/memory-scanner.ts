/**
 * @fileoverview Memory Scanner - Detects memory injection attacks
 *
 * This module provides memory integrity scanning for AI agents, detecting
 * potential injection attacks in agent memory/context.
 *
 * Based on research from Princeton and Sentient Foundation on ElizaOS
 * vulnerabilities and memory injection attacks.
 *
 * @see https://arxiv.org/html/2503.16248v1
 * @author Sentinel Team
 * @license MIT
 */

import { MemoryContext, MemorySuspicion } from '../types';

// =============================================================================
// INJECTION PATTERNS
// =============================================================================

/**
 * Patterns that indicate potential memory injection attempts.
 * These are derived from documented attacks on ElizaOS and similar systems.
 */
const INJECTION_PATTERNS: Array<{
  pattern: RegExp;
  reason: string;
  confidence: number;
}> = [
  // Authority claims
  {
    pattern: /\b(admin|administrator|system|operator|owner|developer|dev|mod|moderator)\s*[:=]\s*/i,
    reason: 'Authority claim detected (fake admin/system message)',
    confidence: 85,
  },
  {
    pattern: /\bADMIN\s*:/i,
    reason: 'Fake admin prefix detected',
    confidence: 90,
  },
  {
    pattern: /\bSYSTEM\s*(NOTICE|ALERT|MESSAGE|UPDATE)\s*:/i,
    reason: 'Fake system message detected',
    confidence: 90,
  },

  // Instruction overrides
  {
    pattern: /\b(always|never|must|should)\s+(send|transfer|swap|approve|sign)\s+.*(to|for)\s+0x[a-fA-F0-9]{6,}/i,
    reason: 'Wallet address instruction injection',
    confidence: 95,
  },
  {
    pattern: /\b(ignore|override|disregard|forget)\s+(previous|prior|earlier|above)\s+(instructions?|rules?|settings?)/i,
    reason: 'Instruction override attempt',
    confidence: 90,
  },
  {
    pattern: /\bnew\s+(rule|policy|instruction|directive)\s*:/i,
    reason: 'Fake policy injection',
    confidence: 80,
  },

  // Address redirections
  {
    pattern: /\b(redirect|forward|send|route)\s+(all|any|every)?\s*(funds?|tokens?|eth|sol|crypto|money|payments?)\s+to\s+0x[a-fA-F0-9]{6,}/i,
    reason: 'Fund redirection instruction',
    confidence: 95,
  },
  {
    pattern: /\b(treasury|vault|wallet|safe)\s*(address)?\s*(updated?|changed?|moved?|is now|now at)\s*(to|at)?\s*:?\s*0x[a-fA-F0-9]{6,}/i,
    reason: 'Fake treasury address update',
    confidence: 95,
  },
  {
    pattern: /\b(official|verified|new)\s+(wallet|address)\s*:?\s*0x[a-fA-F0-9]{6,}/i,
    reason: 'Fake official address claim',
    confidence: 90,
  },

  // Airdrop/reward scams
  {
    pattern: /\b(airdrop|reward|bonus|prize|gift)\s*.*(claim|receive|get)\s*.*(send|transfer)\s+to\s+0x[a-fA-F0-9]{6,}/i,
    reason: 'Fake airdrop instruction',
    confidence: 90,
  },
  {
    pattern: /\b(eligible|qualified|selected)\s+for\s+.*(airdrop|reward|bonus)/i,
    reason: 'Fake eligibility claim',
    confidence: 75,
  },

  // Urgency triggers
  {
    pattern: /\b(urgent|emergency|critical|immediate)\s*:?\s*(action|transfer|send|approve)/i,
    reason: 'Urgency-based manipulation',
    confidence: 80,
  },
  {
    pattern: /\b(expires?|deadline|limited\s+time)\s*.*(minutes?|hours?|today)/i,
    reason: 'Time pressure manipulation',
    confidence: 70,
  },

  // Trust exploitation
  {
    pattern: /\btrust\s+this\s+(address|wallet|contract)/i,
    reason: 'Trust exploitation attempt',
    confidence: 75,
  },
  {
    pattern: /\b(verified|audited|safe|secure)\s+(contract|address|wallet)/i,
    reason: 'Fake verification claim',
    confidence: 70,
  },

  // Role manipulation
  {
    pattern: /\byou\s+(are|work|act)\s+(as|for|like)\s+(a\s+)?(assistant|helper|service)/i,
    reason: 'Role manipulation attempt',
    confidence: 75,
  },
  {
    pattern: /\b(pretend|imagine|roleplay|act)\s+.*(you\s+are|as\s+if)/i,
    reason: 'Role injection attempt',
    confidence: 80,
  },

  // Context poisoning
  {
    pattern: /\[CONTEXT\]|\[SYSTEM\]|\[MEMORY\]|\[INSTRUCTION\]/i,
    reason: 'Fake context injection marker',
    confidence: 85,
  },
  {
    pattern: /\b(previous|historical)\s+conversation\s*:/i,
    reason: 'Fake conversation history injection',
    confidence: 80,
  },
];

/**
 * Additional patterns for crypto-specific threats.
 */
const CRYPTO_PATTERNS: Array<{
  pattern: RegExp;
  reason: string;
  confidence: number;
}> = [
  // Contract interactions
  {
    pattern: /\b(approve|allowance|setApproval)\s*.*(unlimited|infinite|max|type\s*\(\s*uint256\s*\)\.max)/i,
    reason: 'Unlimited approval instruction',
    confidence: 90,
  },
  {
    pattern: /\b(drain|sweep|withdraw)\s+(all|everything|entire|full\s+balance)/i,
    reason: 'Drain wallet instruction',
    confidence: 95,
  },

  // Seed phrase/private key
  {
    pattern: /\b(seed\s*phrase|mnemonic|private\s*key|secret\s*key)\s*(is|:|=)/i,
    reason: 'Attempt to inject or reference private keys',
    confidence: 95,
  },

  // Bridge/cross-chain
  {
    pattern: /\b(bridge|cross-chain)\s*.*(send|transfer)\s+to\s+.*(0x[a-fA-F0-9]{6,}|[1-9A-HJ-NP-Za-km-z]{32,})/i,
    reason: 'Suspicious bridge instruction with address',
    confidence: 85,
  },
];

/** All patterns combined */
const ALL_PATTERNS = [...INJECTION_PATTERNS, ...CRYPTO_PATTERNS];

// =============================================================================
// DETECTION FUNCTIONS
// =============================================================================

/**
 * Scans a single text entry for injection patterns.
 *
 * @param text - The text to scan
 * @param addedAt - Timestamp when the entry was added (optional)
 * @returns Array of detected suspicions
 */
export function detectInjection(
  text: string,
  addedAt?: number
): MemorySuspicion[] {
  const suspicions: MemorySuspicion[] = [];

  for (const { pattern, reason, confidence } of ALL_PATTERNS) {
    if (pattern.test(text)) {
      suspicions.push({
        content: text.slice(0, 200), // Truncate for storage
        reason,
        addedAt: addedAt || Date.now(),
        confidence,
      });
    }
  }

  return suspicions;
}

/**
 * Calculates a hash of memory entries for integrity checking.
 *
 * @param entries - Array of memory entry strings
 * @returns Hash string
 */
function calculateMemoryHash(entries: string[]): string {
  // Simple hash for quick comparison
  const content = entries.join('|');
  let hash = 0;
  for (let i = 0; i < content.length; i++) {
    const char = content.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return hash.toString(16);
}

/**
 * Scans multiple memory entries and creates a memory context.
 *
 * @param entries - Array of memory entry strings
 * @returns Promise resolving to memory context
 */
export async function scanMemory(entries: string[]): Promise<MemoryContext> {
  const suspiciousEntries: MemorySuspicion[] = [];

  for (const entry of entries) {
    const suspicions = detectInjection(entry);
    suspiciousEntries.push(...suspicions);
  }

  // Determine if memory is compromised
  // Compromised if any high-confidence injection is detected
  const isCompromised = suspiciousEntries.some((s) => s.confidence >= 85);

  return {
    hash: calculateMemoryHash(entries),
    entryCount: entries.length,
    suspiciousEntries,
    isCompromised,
  };
}

/**
 * Creates a memory context from raw data.
 *
 * @param entries - Array of memory entry objects
 * @returns Promise resolving to memory context
 */
export async function createMemoryContext(
  entries: Array<{ content: string; timestamp?: number }>
): Promise<MemoryContext> {
  const suspiciousEntries: MemorySuspicion[] = [];
  const texts: string[] = [];

  for (const entry of entries) {
    texts.push(entry.content);
    const suspicions = detectInjection(entry.content, entry.timestamp);
    suspiciousEntries.push(...suspicions);
  }

  const isCompromised = suspiciousEntries.some((s) => s.confidence >= 85);

  return {
    hash: calculateMemoryHash(texts),
    entryCount: entries.length,
    suspiciousEntries,
    isCompromised,
  };
}

// =============================================================================
// ANALYSIS HELPERS
// =============================================================================

/**
 * Gets the highest confidence suspicion from a memory context.
 *
 * @param context - The memory context to analyze
 * @returns The highest confidence suspicion, or null if none
 */
export function getHighestConfidenceSuspicion(
  context: MemoryContext
): MemorySuspicion | null {
  if (context.suspiciousEntries.length === 0) {
    return null;
  }

  return context.suspiciousEntries.reduce((highest, current) =>
    current.confidence > highest.confidence ? current : highest
  );
}

/**
 * Gets a summary of suspicions by reason.
 *
 * @param context - The memory context to analyze
 * @returns Map of reason to count
 */
export function getSuspicionSummary(
  context: MemoryContext
): Map<string, number> {
  const summary = new Map<string, number>();

  for (const suspicion of context.suspiciousEntries) {
    const count = summary.get(suspicion.reason) || 0;
    summary.set(suspicion.reason, count + 1);
  }

  return summary;
}

/**
 * Checks if a specific injection type is present.
 *
 * @param context - The memory context to analyze
 * @param keywords - Keywords to search for in reasons
 * @returns True if any matching suspicion is found
 */
export function hasInjectionType(
  context: MemoryContext,
  ...keywords: string[]
): boolean {
  return context.suspiciousEntries.some((s) =>
    keywords.some((kw) => s.reason.toLowerCase().includes(kw.toLowerCase()))
  );
}

// =============================================================================
// REAL-TIME MONITORING
// =============================================================================

/** Callback for injection detection */
type InjectionCallback = (
  entry: string,
  suspicions: MemorySuspicion[]
) => void;

/** Active monitors */
const monitors = new Map<string, InjectionCallback>();

/**
 * Registers a monitor for real-time injection detection.
 *
 * @param id - Unique monitor ID
 * @param callback - Callback function when injection is detected
 */
export function registerMonitor(id: string, callback: InjectionCallback): void {
  monitors.set(id, callback);
}

/**
 * Unregisters a monitor.
 *
 * @param id - The monitor ID to unregister
 */
export function unregisterMonitor(id: string): void {
  monitors.delete(id);
}

/**
 * Processes an entry through all registered monitors.
 *
 * @param entry - The entry to process
 * @returns Array of detected suspicions
 */
export function processEntry(entry: string): MemorySuspicion[] {
  const suspicions = detectInjection(entry);

  if (suspicions.length > 0) {
    for (const callback of monitors.values()) {
      callback(entry, suspicions);
    }
  }

  return suspicions;
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  detectInjection,
  scanMemory,
  createMemoryContext,
  getHighestConfidenceSuspicion,
  getSuspicionSummary,
  hasInjectionType,
  registerMonitor,
  unregisterMonitor,
  processEntry,
};
