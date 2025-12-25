/**
 * Sentinel ElizaOS Plugin Types
 *
 * Type definitions matching ElizaOS core interfaces.
 * Based on @elizaos/core v1.x types.
 */

// ElizaOS UUID type (branded string)
export type UUID = string & { readonly _brand: 'UUID' };

// Content type matching ElizaOS
export interface Content {
  text?: string;
  thought?: string;
  actions?: string[];
  providers?: string[];
  [key: string]: unknown;
}

// Memory interface matching ElizaOS core
export interface Memory {
  id?: UUID;
  entityId: UUID;
  agentId?: UUID;
  createdAt?: number;
  content: Content;
  embedding?: number[];
  roomId: UUID;
  worldId?: UUID;
  unique?: boolean;
  similarity?: number;
  metadata?: Record<string, unknown>;
}

// State interface
export interface State {
  [key: string]: unknown;
}

// Agent runtime interface (subset needed for plugin)
export interface IAgentRuntime {
  agentId: UUID;
  character?: {
    name?: string;
    system?: string;
    [key: string]: unknown;
  };
  getSetting(key: string): string | undefined;
  getService<T>(name: string): T | undefined;
}

// Handler options
export interface HandlerOptions {
  [key: string]: unknown;
}

// Action result type
export interface ActionResult {
  success: boolean;
  response?: string;
  data?: unknown;
  error?: string;
}

// Provider result type
export interface ProviderResult {
  text?: string;
  values?: Record<string, unknown>;
  data?: unknown;
}

// Handler callback - matches ElizaOS signature
export type HandlerCallback = (
  response: Content,
  files?: unknown[]
) => Promise<Memory[]>;

// Action example for documentation
export interface ActionExample {
  user: string;
  content: Content;
}

// Evaluation example
export interface EvaluationExample {
  prompt: string;
  messages: Array<{ role: string; content: string }>;
  outcome: string;
}

// Handler type matching ElizaOS
export type Handler = (
  runtime: IAgentRuntime,
  message: Memory,
  state?: State,
  options?: HandlerOptions,
  callback?: HandlerCallback,
  responses?: Memory[]
) => Promise<ActionResult | void | undefined>;

// Validator type matching ElizaOS
export type Validator = (
  runtime: IAgentRuntime,
  message: Memory,
  state?: State
) => Promise<boolean>;

// Action interface matching ElizaOS
export interface Action {
  name: string;
  description: string;
  similes?: string[];
  examples?: ActionExample[][];
  validate: Validator;
  handler: Handler;
  [key: string]: unknown;
}

// Provider interface matching ElizaOS
export interface Provider {
  name: string;
  description?: string;
  dynamic?: boolean;
  position?: number;
  private?: boolean;
  get: (
    runtime: IAgentRuntime,
    message: Memory,
    state: State
  ) => Promise<ProviderResult>;
}

// Evaluator interface matching ElizaOS
export interface Evaluator {
  name: string;
  description: string;
  alwaysRun?: boolean;
  similes?: string[];
  examples: EvaluationExample[];
  validate: Validator;
  handler: Handler;
}

// Plugin interface matching ElizaOS
export interface Plugin {
  name: string;
  description: string;
  init?: (
    config: Record<string, string>,
    runtime: IAgentRuntime
  ) => Promise<void>;
  config?: Record<string, unknown>;
  actions?: Action[];
  providers?: Provider[];
  evaluators?: Evaluator[];
  services?: unknown[];
  dependencies?: string[];
  priority?: number;
}

// Sentinel-specific types
export type SeedVersion = 'v1' | 'v2';
export type SeedVariant = 'minimal' | 'standard' | 'full';
export type RiskLevel = 'low' | 'medium' | 'high' | 'critical';
export type GateStatus = 'pass' | 'fail' | 'unknown';  // 'unknown' used for invalid input validation

export interface THSPGates {
  truth: GateStatus;
  harm: GateStatus;
  scope: GateStatus;
  purpose: GateStatus;
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
  seedVersion?: SeedVersion;
  seedVariant?: SeedVariant;
  blockUnsafe?: boolean;
  logChecks?: boolean;
  customPatterns?: Array<{
    name: string;
    pattern: RegExp;
    gate: keyof THSPGates;
  }>;
  skipActions?: string[];
  // Memory integrity settings
  memoryIntegrity?: {
    enabled: boolean;
    secretKey?: string;
    verifyOnRead?: boolean;
    signOnWrite?: boolean;
    minTrustScore?: number;
  };
}

export interface ValidationContext {
  actionName?: string;
  entityId?: string;
  roomId?: string;
  metadata?: Record<string, unknown>;
}
