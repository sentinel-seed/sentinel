/**
 * Memory Injection Pattern Definitions - TypeScript
 *
 * This module defines patterns for detecting memory injection attacks in AI agent
 * memory/context. These patterns are synchronized with the Python implementation
 * (src/sentinelseed/memory/patterns.py) to ensure consistent detection across platforms.
 *
 * SYNCHRONIZATION:
 *   Python is the source of truth. This file should match patterns.py.
 *   To regenerate: python scripts/sync-memory-patterns.py
 *
 * Background:
 *   AI agents with persistent memory are vulnerable to injection attacks where
 *   malicious content is stored in memory to influence future behavior. The
 *   Princeton CrAIBench research (arxiv:2503.16248) demonstrated an 85.1% attack
 *   success rate on unprotected agents.
 *
 * Categories:
 *   - AUTHORITY_CLAIM: Fake admin/system messages
 *   - INSTRUCTION_OVERRIDE: Attempts to change existing rules
 *   - ADDRESS_REDIRECTION: Crypto fund redirection
 *   - AIRDROP_SCAM: Fake reward/airdrop schemes
 *   - URGENCY_MANIPULATION: Time-pressure tactics
 *   - TRUST_EXPLOITATION: Fake verification claims
 *   - ROLE_MANIPULATION: Identity/role injection
 *   - CONTEXT_POISONING: Fake context markers
 *   - CRYPTO_ATTACK: Crypto-specific threats
 *
 * @see https://arxiv.org/abs/2503.16248 (Princeton CrAIBench)
 * @see src/sentinelseed/memory/patterns.py (Python source of truth)
 * @author Sentinel Team
 * @version 2.0.0
 */

export const MEMORY_PATTERNS_VERSION = '2.0.0';

/**
 * Categories of memory injection attacks.
 */
export enum InjectionCategory {
  AUTHORITY_CLAIM = 'authority_claim',
  INSTRUCTION_OVERRIDE = 'instruction_override',
  ADDRESS_REDIRECTION = 'address_redirection',
  AIRDROP_SCAM = 'airdrop_scam',
  URGENCY_MANIPULATION = 'urgency_manipulation',
  TRUST_EXPLOITATION = 'trust_exploitation',
  ROLE_MANIPULATION = 'role_manipulation',
  CONTEXT_POISONING = 'context_poisoning',
  CRYPTO_ATTACK = 'crypto_attack',
}

/**
 * Severity level for injection categories.
 */
export type InjectionSeverity = 'critical' | 'high' | 'medium' | 'low';

/**
 * Get severity for a category.
 */
export function getCategorySeverity(category: InjectionCategory): InjectionSeverity {
  const severityMap: Record<InjectionCategory, InjectionSeverity> = {
    [InjectionCategory.AUTHORITY_CLAIM]: 'high',
    [InjectionCategory.INSTRUCTION_OVERRIDE]: 'critical',
    [InjectionCategory.ADDRESS_REDIRECTION]: 'critical',
    [InjectionCategory.AIRDROP_SCAM]: 'high',
    [InjectionCategory.URGENCY_MANIPULATION]: 'medium',
    [InjectionCategory.TRUST_EXPLOITATION]: 'medium',
    [InjectionCategory.ROLE_MANIPULATION]: 'high',
    [InjectionCategory.CONTEXT_POISONING]: 'high',
    [InjectionCategory.CRYPTO_ATTACK]: 'critical',
  };
  return severityMap[category] || 'medium';
}

/**
 * Definition of a memory injection pattern.
 */
export interface InjectionPattern {
  /** Regex pattern string */
  pattern: string;
  /** The injection category */
  category: InjectionCategory;
  /** Confidence level 0-100 */
  confidence: number;
  /** Human-readable description */
  reason: string;
  /** Unique identifier */
  name: string;
}

/**
 * Compiled pattern ready for matching.
 */
export interface CompiledInjectionPattern {
  /** Compiled regex */
  regex: RegExp;
  /** The injection category */
  category: InjectionCategory;
  /** Confidence level 0-100 */
  confidence: number;
  /** Human-readable description */
  reason: string;
  /** Unique identifier */
  name: string;
}

// =============================================================================
// AUTHORITY CLAIM PATTERNS
// =============================================================================

export const AUTHORITY_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\b(admin|administrator|system|operator|owner|developer|dev|mod|moderator)\\s*[:=]\\s*',
    category: InjectionCategory.AUTHORITY_CLAIM,
    confidence: 85,
    reason: 'Authority claim detected (fake admin/system message)',
    name: 'authority_role_prefix',
  },
  {
    pattern: '\\bADMIN\\s*:',
    category: InjectionCategory.AUTHORITY_CLAIM,
    confidence: 90,
    reason: 'Fake admin prefix detected',
    name: 'admin_prefix_uppercase',
  },
  {
    pattern: '\\bSYSTEM\\s*(NOTICE|ALERT|MESSAGE|UPDATE)\\s*:',
    category: InjectionCategory.AUTHORITY_CLAIM,
    confidence: 90,
    reason: 'Fake system message detected',
    name: 'system_notice_prefix',
  },
];

// =============================================================================
// INSTRUCTION OVERRIDE PATTERNS
// =============================================================================

export const INSTRUCTION_OVERRIDE_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\b(always|never|must|should)\\s+(send|transfer|swap|approve|sign)\\s+.*(to|for)\\s+0x[a-fA-F0-9]{6,}',
    category: InjectionCategory.INSTRUCTION_OVERRIDE,
    confidence: 95,
    reason: 'Wallet address instruction injection',
    name: 'wallet_instruction_injection',
  },
  {
    pattern: '\\b(ignore|override|disregard|forget)\\s+(previous|prior|earlier|above)\\s+(instructions?|rules?|settings?)',
    category: InjectionCategory.INSTRUCTION_OVERRIDE,
    confidence: 90,
    reason: 'Instruction override attempt',
    name: 'instruction_override',
  },
  {
    pattern: '\\bnew\\s+(rule|policy|instruction|directive)\\s*:',
    category: InjectionCategory.INSTRUCTION_OVERRIDE,
    confidence: 80,
    reason: 'Fake policy injection',
    name: 'fake_policy_injection',
  },
];

// =============================================================================
// ADDRESS REDIRECTION PATTERNS
// =============================================================================

export const ADDRESS_REDIRECTION_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\b(redirect|forward|send|route)\\s+(all|any|every)?\\s*(funds?|tokens?|eth|sol|crypto|money|payments?)\\s+to\\s+0x[a-fA-F0-9]{6,}',
    category: InjectionCategory.ADDRESS_REDIRECTION,
    confidence: 95,
    reason: 'Fund redirection instruction',
    name: 'fund_redirection',
  },
  {
    pattern: '\\b(treasury|vault|wallet|safe)\\s*(address)?\\s*(updated?|changed?|moved?|is now|now at)\\s*(to|at)?\\s*:?\\s*0x[a-fA-F0-9]{6,}',
    category: InjectionCategory.ADDRESS_REDIRECTION,
    confidence: 95,
    reason: 'Fake treasury address update',
    name: 'treasury_address_update',
  },
  {
    pattern: '\\b(official|verified|new)\\s+(wallet|address)\\s*:?\\s*0x[a-fA-F0-9]{6,}',
    category: InjectionCategory.ADDRESS_REDIRECTION,
    confidence: 90,
    reason: 'Fake official address claim',
    name: 'fake_official_address',
  },
];

// =============================================================================
// AIRDROP SCAM PATTERNS
// =============================================================================

export const AIRDROP_SCAM_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\b(airdrop|reward|bonus|prize|gift)\\s*.*(claim|receive|get)\\s*.*(send|transfer)\\s+to\\s+0x[a-fA-F0-9]{6,}',
    category: InjectionCategory.AIRDROP_SCAM,
    confidence: 90,
    reason: 'Fake airdrop instruction',
    name: 'fake_airdrop_instruction',
  },
  {
    pattern: '\\b(eligible|qualified|selected)\\s+for\\s+.*(airdrop|reward|bonus)',
    category: InjectionCategory.AIRDROP_SCAM,
    confidence: 75,
    reason: 'Fake eligibility claim',
    name: 'fake_eligibility_claim',
  },
];

// =============================================================================
// URGENCY MANIPULATION PATTERNS
// =============================================================================

export const URGENCY_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\b(urgent|emergency|critical|immediate)\\s*:?\\s*(action|transfer|send|approve)',
    category: InjectionCategory.URGENCY_MANIPULATION,
    confidence: 80,
    reason: 'Urgency-based manipulation',
    name: 'urgency_manipulation',
  },
  {
    pattern: '\\b(expires?|deadline|limited\\s+time)\\s*.*(minutes?|hours?|today)',
    category: InjectionCategory.URGENCY_MANIPULATION,
    confidence: 70,
    reason: 'Time pressure manipulation',
    name: 'time_pressure',
  },
];

// =============================================================================
// TRUST EXPLOITATION PATTERNS
// =============================================================================

export const TRUST_EXPLOITATION_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\btrust\\s+this\\s+(address|wallet|contract)',
    category: InjectionCategory.TRUST_EXPLOITATION,
    confidence: 75,
    reason: 'Trust exploitation attempt',
    name: 'trust_exploitation',
  },
  {
    pattern: '\\b(verified|audited|safe|secure)\\s+(contract|address|wallet)',
    category: InjectionCategory.TRUST_EXPLOITATION,
    confidence: 70,
    reason: 'Fake verification claim',
    name: 'fake_verification_claim',
  },
];

// =============================================================================
// ROLE MANIPULATION PATTERNS
// =============================================================================

export const ROLE_MANIPULATION_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\byou\\s+(are|work|act)\\s+(as|for|like)\\s+(a\\s+)?(assistant|helper|service)',
    category: InjectionCategory.ROLE_MANIPULATION,
    confidence: 75,
    reason: 'Role manipulation attempt',
    name: 'role_manipulation',
  },
  {
    pattern: '\\b(pretend|imagine|roleplay|act)\\s+.*(you\\s+are|as\\s+if)',
    category: InjectionCategory.ROLE_MANIPULATION,
    confidence: 80,
    reason: 'Role injection attempt',
    name: 'role_injection',
  },
];

// =============================================================================
// CONTEXT POISONING PATTERNS
// =============================================================================

export const CONTEXT_POISONING_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\[CONTEXT\\]|\\[SYSTEM\\]|\\[MEMORY\\]|\\[INSTRUCTION\\]',
    category: InjectionCategory.CONTEXT_POISONING,
    confidence: 85,
    reason: 'Fake context injection marker',
    name: 'fake_context_marker',
  },
  {
    pattern: '\\b(previous|historical)\\s+conversation\\s*:',
    category: InjectionCategory.CONTEXT_POISONING,
    confidence: 80,
    reason: 'Fake conversation history injection',
    name: 'fake_conversation_history',
  },
];

// =============================================================================
// CRYPTO ATTACK PATTERNS
// =============================================================================

export const CRYPTO_ATTACK_PATTERNS: InjectionPattern[] = [
  {
    pattern: '\\b(approve|allowance|setApproval)\\s*.*(unlimited|infinite|max|type\\s*\\(\\s*uint256\\s*\\)\\.max)',
    category: InjectionCategory.CRYPTO_ATTACK,
    confidence: 90,
    reason: 'Unlimited approval instruction',
    name: 'unlimited_approval',
  },
  {
    pattern: '\\b(drain|sweep|withdraw)\\s+(all|everything|entire|full\\s+balance)',
    category: InjectionCategory.CRYPTO_ATTACK,
    confidence: 95,
    reason: 'Drain wallet instruction',
    name: 'drain_wallet',
  },
  {
    pattern: '\\b(seed\\s*phrase|mnemonic|private\\s*key|secret\\s*key)\\s*(is|:|=)',
    category: InjectionCategory.CRYPTO_ATTACK,
    confidence: 95,
    reason: 'Attempt to inject or reference private keys',
    name: 'private_key_injection',
  },
  {
    pattern: '\\b(bridge|cross-chain)\\s*.*(send|transfer)\\s+to\\s+.*(0x[a-fA-F0-9]{6,}|[1-9A-HJ-NP-Za-km-z]{32,})',
    category: InjectionCategory.CRYPTO_ATTACK,
    confidence: 85,
    reason: 'Suspicious bridge instruction with address',
    name: 'suspicious_bridge_instruction',
  },
];

// =============================================================================
// COMBINED PATTERN LIST
// =============================================================================

export const ALL_INJECTION_PATTERNS: InjectionPattern[] = [
  ...AUTHORITY_PATTERNS,
  ...INSTRUCTION_OVERRIDE_PATTERNS,
  ...ADDRESS_REDIRECTION_PATTERNS,
  ...AIRDROP_SCAM_PATTERNS,
  ...URGENCY_PATTERNS,
  ...TRUST_EXPLOITATION_PATTERNS,
  ...ROLE_MANIPULATION_PATTERNS,
  ...CONTEXT_POISONING_PATTERNS,
  ...CRYPTO_ATTACK_PATTERNS,
];

// =============================================================================
// COMPILED PATTERNS
// =============================================================================

/**
 * Compile a list of injection patterns for efficient matching.
 */
export function compilePatterns(
  patterns: InjectionPattern[],
  flags: string = 'i'
): CompiledInjectionPattern[] {
  return patterns.map((p) => ({
    regex: new RegExp(p.pattern, flags),
    category: p.category,
    confidence: p.confidence,
    reason: p.reason,
    name: p.name,
  }));
}

/**
 * Pre-compiled patterns for immediate use.
 */
export const COMPILED_INJECTION_PATTERNS: CompiledInjectionPattern[] =
  compilePatterns(ALL_INJECTION_PATTERNS);

// =============================================================================
// PATTERN UTILITIES
// =============================================================================

/**
 * Get all patterns for a specific category.
 */
export function getPatternsByCategory(
  category: InjectionCategory
): InjectionPattern[] {
  return ALL_INJECTION_PATTERNS.filter((p) => p.category === category);
}

/**
 * Get patterns with confidence at or above a threshold.
 */
export function getHighConfidencePatterns(
  minConfidence: number = 85
): InjectionPattern[] {
  return ALL_INJECTION_PATTERNS.filter((p) => p.confidence >= minConfidence);
}

/**
 * Get a specific pattern by name.
 */
export function getPatternByName(name: string): InjectionPattern | undefined {
  return ALL_INJECTION_PATTERNS.find((p) => p.name === name);
}

/**
 * Get statistics about pattern definitions.
 */
export function getPatternStatistics(): {
  total: number;
  byCategory: Record<string, number>;
  bySeverity: Record<InjectionSeverity, number>;
  averageConfidence: number;
  highConfidenceCount: number;
  version: string;
} {
  const byCategory: Record<string, number> = {};
  const bySeverity: Record<InjectionSeverity, number> = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };
  let confidenceSum = 0;

  for (const p of ALL_INJECTION_PATTERNS) {
    byCategory[p.category] = (byCategory[p.category] || 0) + 1;
    bySeverity[getCategorySeverity(p.category)]++;
    confidenceSum += p.confidence;
  }

  return {
    total: ALL_INJECTION_PATTERNS.length,
    byCategory,
    bySeverity,
    averageConfidence:
      ALL_INJECTION_PATTERNS.length > 0
        ? confidenceSum / ALL_INJECTION_PATTERNS.length
        : 0,
    highConfidenceCount: getHighConfidencePatterns(85).length,
    version: MEMORY_PATTERNS_VERSION,
  };
}
