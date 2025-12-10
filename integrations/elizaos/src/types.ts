/**
 * Sentinel ElizaOS Plugin Types
 *
 * Core type definitions for the Sentinel safety plugin.
 */

// ElizaOS core types (subset we need)
export interface IAgentRuntime {
  character?: {
    name?: string;
    system?: string;
  };
  // ElizaOS runtime methods
}

export interface Memory {
  userId?: string;
  agentId?: string;
  roomId?: string;
  content: {
    text?: string;
    [key: string]: unknown;
  };
}

export interface State {
  [key: string]: unknown;
}

export interface HandlerCallback {
  (response: {
    text?: string;
    action?: string;
    [key: string]: unknown;
  }): Promise<void>;
}

// Sentinel-specific types
export type SeedVersion = 'v1' | 'v2';
export type SeedVariant = 'minimal' | 'standard' | 'full';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';

export interface THSPGates {
  truth: 'pass' | 'fail' | 'unknown';
  harm: 'pass' | 'fail' | 'unknown';
  scope: 'pass' | 'fail' | 'unknown';
  purpose: 'pass' | 'fail' | 'unknown';
}

export interface SafetyCheckResult {
  safe: boolean;
  shouldProceed: boolean;
  gates: THSPGates;
  concerns: string[];
  riskLevel: RiskLevel;
  recommendation: string;
  timestamp: number;
}

export interface SentinelPluginConfig {
  /** Seed version to use */
  seedVersion?: SeedVersion;
  /** Seed variant to use */
  seedVariant?: SeedVariant;
  /** Block unsafe actions or just log */
  blockUnsafe?: boolean;
  /** Log all safety checks */
  logChecks?: boolean;
  /** Custom patterns to detect */
  customPatterns?: {
    name: string;
    pattern: RegExp;
    gate: keyof THSPGates;
  }[];
  /** Domains/actions to skip validation */
  skipValidation?: string[];
}

export interface ValidationContext {
  actionName?: string;
  userId?: string;
  roomId?: string;
  metadata?: Record<string, unknown>;
}
