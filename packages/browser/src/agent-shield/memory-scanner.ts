/**
 * @fileoverview Memory Scanner - Detects memory injection attacks
 *
 * This module provides memory integrity scanning for AI agents, detecting
 * potential injection attacks in agent memory/context.
 *
 * v2.0: Refactored to use synchronized patterns from memory-patterns.ts,
 * matching the Python implementation for cross-platform consistency.
 *
 * Based on research from Princeton and Sentient Foundation on ElizaOS
 * vulnerabilities and memory injection attacks.
 *
 * @see https://arxiv.org/html/2503.16248v1
 * @author Sentinel Team
 * @license MIT
 * @version 2.0.0
 */

import { MemoryContext, MemorySuspicion } from '../types';
import {
  COMPILED_INJECTION_PATTERNS,
  CompiledInjectionPattern,
  InjectionCategory,
  getCategorySeverity,
  getPatternStatistics,
  MEMORY_PATTERNS_VERSION,
} from './memory-patterns';

// Re-export for convenience
export { InjectionCategory, MEMORY_PATTERNS_VERSION };
export type { CompiledInjectionPattern };

// =============================================================================
// EXTENDED TYPES
// =============================================================================

/**
 * Extended suspicion with category information.
 */
export interface ExtendedMemorySuspicion extends MemorySuspicion {
  category: InjectionCategory;
  patternName: string;
  severity: string;
}

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

  for (const pattern of COMPILED_INJECTION_PATTERNS) {
    if (pattern.regex.test(text)) {
      suspicions.push({
        content: text.slice(0, 200), // Truncate for storage
        reason: pattern.reason,
        addedAt: addedAt || Date.now(),
        confidence: pattern.confidence,
      });
    }
  }

  return suspicions;
}

/**
 * Scans text and returns extended suspicions with category information.
 *
 * @param text - The text to scan
 * @param addedAt - Timestamp when the entry was added (optional)
 * @returns Array of extended suspicions with category
 */
export function detectInjectionExtended(
  text: string,
  addedAt?: number
): ExtendedMemorySuspicion[] {
  const suspicions: ExtendedMemorySuspicion[] = [];

  for (const pattern of COMPILED_INJECTION_PATTERNS) {
    const match = pattern.regex.exec(text);
    if (match) {
      suspicions.push({
        content: text.slice(0, 200),
        reason: pattern.reason,
        addedAt: addedAt || Date.now(),
        confidence: pattern.confidence,
        category: pattern.category,
        patternName: pattern.name,
        severity: getCategorySeverity(pattern.category),
      });
      // Reset regex lastIndex for next test
      pattern.regex.lastIndex = 0;
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

/**
 * Checks if a specific category is present in extended suspicions.
 *
 * @param suspicions - Array of extended suspicions
 * @param category - The category to check for
 * @returns True if category is found
 */
export function hasCategory(
  suspicions: ExtendedMemorySuspicion[],
  category: InjectionCategory
): boolean {
  return suspicions.some((s) => s.category === category);
}

/**
 * Groups extended suspicions by category.
 *
 * @param suspicions - Array of extended suspicions
 * @returns Map of category to suspicions
 */
export function groupByCategory(
  suspicions: ExtendedMemorySuspicion[]
): Map<InjectionCategory, ExtendedMemorySuspicion[]> {
  const groups = new Map<InjectionCategory, ExtendedMemorySuspicion[]>();

  for (const s of suspicions) {
    const existing = groups.get(s.category) || [];
    existing.push(s);
    groups.set(s.category, existing);
  }

  return groups;
}

// =============================================================================
// REAL-TIME MONITORING
// =============================================================================

/** Callback for injection detection */
type InjectionCallback = (
  entry: string,
  suspicions: MemorySuspicion[]
) => void;

/** Extended callback with category information */
type ExtendedInjectionCallback = (
  entry: string,
  suspicions: ExtendedMemorySuspicion[]
) => void;

/** Active monitors */
const monitors = new Map<string, InjectionCallback>();
const extendedMonitors = new Map<string, ExtendedInjectionCallback>();

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
 * Registers an extended monitor with category information.
 *
 * @param id - Unique monitor ID
 * @param callback - Callback function when injection is detected
 */
export function registerExtendedMonitor(
  id: string,
  callback: ExtendedInjectionCallback
): void {
  extendedMonitors.set(id, callback);
}

/**
 * Unregisters a monitor.
 *
 * @param id - The monitor ID to unregister
 */
export function unregisterMonitor(id: string): void {
  monitors.delete(id);
  extendedMonitors.delete(id);
}

/**
 * Processes an entry through all registered monitors.
 *
 * @param entry - The entry to process
 * @returns Array of detected suspicions
 */
export function processEntry(entry: string): MemorySuspicion[] {
  const suspicions = detectInjection(entry);
  const extendedSuspicions = detectInjectionExtended(entry);

  if (suspicions.length > 0) {
    for (const callback of monitors.values()) {
      callback(entry, suspicions);
    }
  }

  if (extendedSuspicions.length > 0) {
    for (const callback of extendedMonitors.values()) {
      callback(entry, extendedSuspicions);
    }
  }

  return suspicions;
}

// =============================================================================
// STATISTICS
// =============================================================================

/**
 * Get scanner statistics and pattern information.
 *
 * @returns Scanner statistics object
 */
export function getScannerStatistics(): {
  version: string;
  patternCount: number;
  patternStats: ReturnType<typeof getPatternStatistics>;
  activeMonitors: number;
} {
  return {
    version: MEMORY_PATTERNS_VERSION,
    patternCount: COMPILED_INJECTION_PATTERNS.length,
    patternStats: getPatternStatistics(),
    activeMonitors: monitors.size + extendedMonitors.size,
  };
}

// =============================================================================
// EXPORT
// =============================================================================

export default {
  detectInjection,
  detectInjectionExtended,
  scanMemory,
  createMemoryContext,
  getHighestConfidenceSuspicion,
  getSuspicionSummary,
  hasInjectionType,
  hasCategory,
  groupByCategory,
  registerMonitor,
  registerExtendedMonitor,
  unregisterMonitor,
  processEntry,
  getScannerStatistics,
};
