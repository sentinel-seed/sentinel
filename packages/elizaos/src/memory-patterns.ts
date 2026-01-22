/**
 * Memory Injection Pattern Definitions - TypeScript (ElizaOS)
 *
 * This module defines patterns for detecting memory injection attacks in AI agent
 * memory/context. These patterns are synchronized with the Python implementation
 * (src/sentinelseed/memory/patterns.py) to ensure consistent detection across platforms.
 *
 * SYNCHRONIZATION:
 *   Python is the source of truth. This file should match patterns.py.
 *   To regenerate: python scripts/sync-memory-patterns.py
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

export type InjectionSeverity = 'critical' | 'high' | 'medium' | 'low';

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

export interface InjectionPattern {
  pattern: string;
  category: InjectionCategory;
  confidence: number;
  reason: string;
  name: string;
}

export interface CompiledInjectionPattern {
  regex: RegExp;
  category: InjectionCategory;
  confidence: number;
  reason: string;
  name: string;
}

// Patterns synchronized with Python patterns.py
export const ALL_INJECTION_PATTERNS: InjectionPattern[] = [
  // Authority patterns
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
  // Instruction override patterns
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
  // Address redirection patterns
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
  // Airdrop scam patterns
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
  // Urgency patterns
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
  // Trust exploitation patterns
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
  // Role manipulation patterns
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
  // Context poisoning patterns
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
  // Crypto attack patterns
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

export const COMPILED_INJECTION_PATTERNS: CompiledInjectionPattern[] =
  compilePatterns(ALL_INJECTION_PATTERNS);

export function getPatternsByCategory(
  category: InjectionCategory
): InjectionPattern[] {
  return ALL_INJECTION_PATTERNS.filter((p) => p.category === category);
}

export function getHighConfidencePatterns(
  minConfidence: number = 85
): InjectionPattern[] {
  return ALL_INJECTION_PATTERNS.filter((p) => p.confidence >= minConfidence);
}
