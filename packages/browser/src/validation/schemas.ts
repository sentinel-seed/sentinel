/**
 * @fileoverview Zod Schemas - Runtime validation for message payloads
 *
 * This module provides Zod schemas for validating message payloads at runtime.
 * TypeScript types provide compile-time safety, but we need runtime validation
 * for data coming from external sources (content scripts, web pages, etc).
 *
 * @author Sentinel Team
 * @license MIT
 */

import { z } from 'zod';

// =============================================================================
// BASE SCHEMAS
// =============================================================================

/** Agent type enum */
export const AgentTypeSchema = z.enum([
  'elizaos',
  'autogpt',
  'crewai',
  'langchain',
  'custom',
]);

/** Agent action type enum */
export const AgentActionTypeSchema = z.enum([
  'transfer',
  'swap',
  'approval',
  'sign',
  'execute',
  'deploy',
  'stake',
  'unstake',
  'bridge',
  'mint',
  'burn',
  'message',
  'api_call',
  'file_access',
  'mcp_tool',
]);

/** MCP client source enum */
export const MCPClientSourceSchema = z.enum([
  'claude_desktop',
  'cursor',
  'windsurf',
  'vscode',
  'custom',
]);

/** MCP transport type enum */
export const MCPTransportSchema = z.enum(['http', 'stdio', 'websocket']);

/** Risk level enum */
export const RiskLevelSchema = z.enum(['low', 'medium', 'high', 'critical']);

/** Approval action enum */
export const ApprovalActionSchema = z.enum([
  'auto_approve',
  'auto_reject',
  'require_approval',
]);

/** Decision action enum */
export const DecisionActionSchema = z.enum(['approve', 'reject', 'modify']);

/** Rule condition operator enum */
export const RuleConditionOperatorSchema = z.enum([
  'equals',
  'not_equals',
  'greater_than',
  'less_than',
  'greater_than_or_equals',
  'less_than_or_equals',
  'contains',
  'not_contains',
  'in',
  'not_in',
  'matches_regex',
]);

/** Rule condition field enum */
export const RuleConditionFieldSchema = z.enum([
  'source',
  'riskLevel',
  'estimatedValueUsd',
  'agentType',
  'agentTrustLevel',
  'actionType',
  'memoryCompromised',
  'mcpServerTrusted',
  'mcpToolName',
  'mcpSource',
]);

// =============================================================================
// AGENT SHIELD SCHEMAS
// =============================================================================

/** Agent connect payload */
export const AgentConnectPayloadSchema = z.object({
  name: z.string().min(1).max(100),
  type: AgentTypeSchema,
  endpoint: z.string().min(1).max(500),
  metadata: z.record(z.unknown()).optional(),
});

/** Agent intercept action payload */
export const AgentInterceptActionPayloadSchema = z.object({
  agentId: z.string().uuid(),
  type: AgentActionTypeSchema,
  description: z.string().min(1).max(1000),
  params: z.record(z.unknown()),
  estimatedValueUsd: z.number().nonnegative().optional(),
  memoryEntries: z.array(z.string()).optional(),
});

/** Agent update trust payload */
export const AgentUpdateTrustPayloadSchema = z.object({
  agentId: z.string().uuid(),
  trustLevel: z.number().min(0).max(100),
});

// =============================================================================
// MCP GATEWAY SCHEMAS
// =============================================================================

/** MCP tool schema */
export const MCPToolSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  inputSchema: z.record(z.unknown()).optional(),
});

/** MCP register server payload */
export const MCPRegisterServerPayloadSchema = z.object({
  name: z.string().min(1).max(100),
  endpoint: z.string().min(1).max(500),
  transport: MCPTransportSchema,
  tools: z.array(MCPToolSchema).optional(),
  description: z.string().max(500).optional(),
  trustLevel: z.number().min(0).max(100).optional(),
  isTrusted: z.boolean().optional(),
});

/** MCP intercept tool call payload */
export const MCPInterceptToolCallPayloadSchema = z.object({
  serverId: z.string().uuid(),
  toolName: z.string().min(1).max(100),
  args: z.record(z.unknown()),
  source: MCPClientSourceSchema,
});

/** MCP update trust payload */
export const MCPUpdateTrustPayloadSchema = z.object({
  serverId: z.string().uuid(),
  trustLevel: z.number().min(0).max(100),
});

// =============================================================================
// APPROVAL SCHEMAS
// =============================================================================

/** Rule condition schema */
export const RuleConditionSchema = z.object({
  field: RuleConditionFieldSchema,
  operator: RuleConditionOperatorSchema,
  value: z.union([
    z.string(),
    z.number(),
    z.boolean(),
    z.array(z.string()),
  ]),
});

/** Approval decide payload */
export const ApprovalDecidePayloadSchema = z.object({
  pendingId: z.string().uuid(),
  action: DecisionActionSchema,
  reason: z.string().min(1).max(500),
  modifiedParams: z.record(z.unknown()).optional(),
});

/** Approval create rule payload */
export const ApprovalCreateRulePayloadSchema = z.object({
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  priority: z.number().int().min(0).max(1000),
  enabled: z.boolean(),
  conditions: z.array(RuleConditionSchema),
  action: ApprovalActionSchema,
  reason: z.string().max(500).optional(),
});

/** Approval rule schema (full, for updates) */
export const ApprovalRuleSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  description: z.string().max(500).optional(),
  priority: z.number().int().min(0).max(1000),
  enabled: z.boolean(),
  conditions: z.array(RuleConditionSchema),
  action: ApprovalActionSchema,
  reason: z.string().max(500).optional(),
  createdAt: z.number(),
  updatedAt: z.number(),
});

/** Get history payload */
export const GetHistoryPayloadSchema = z.object({
  limit: z.number().int().min(1).max(1000).optional(),
  offset: z.number().int().min(0).optional(),
});

// =============================================================================
// SETTINGS SCHEMAS
// =============================================================================

/** Language enum */
export const LanguageSchema = z.enum(['en', 'es', 'pt']);

/** Protection level enum */
export const ProtectionLevelSchema = z.enum(['basic', 'recommended', 'maximum']);

/** Agent Shield settings schema */
export const AgentShieldSettingsSchema = z.object({
  enabled: z.boolean(),
  trustThreshold: z.number().min(0).max(100),
  memoryInjectionDetection: z.boolean(),
  maxAutoApproveValue: z.number().min(0),
});

/** MCP Gateway settings schema */
export const MCPGatewaySettingsSchema = z.object({
  enabled: z.boolean(),
  interceptAll: z.boolean(),
  trustedServers: z.array(z.string()),
});

/** Approval settings schema */
export const ApprovalSettingsSchema = z.object({
  enabled: z.boolean(),
  defaultAction: ApprovalActionSchema,
  showNotifications: z.boolean(),
  autoRejectTimeoutMs: z.number().min(0),
});

/** Full settings schema for import validation */
export const SettingsSchema = z.object({
  enabled: z.boolean(),
  protectionLevel: ProtectionLevelSchema,
  platforms: z.array(z.string()),
  notifications: z.boolean(),
  language: LanguageSchema,
  agentShield: AgentShieldSettingsSchema,
  mcpGateway: MCPGatewaySettingsSchema,
  approval: ApprovalSettingsSchema,
});

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Result of validation
 */
export interface ValidationResult<T> {
  success: boolean;
  data?: T;
  error?: string;
}

/**
 * Validates data against a Zod schema and returns a result object.
 *
 * @param schema - The Zod schema to validate against
 * @param data - The data to validate
 * @returns Validation result with success flag and either data or error
 */
export function validate<T>(
  schema: z.ZodType<T>,
  data: unknown
): ValidationResult<T> {
  const result = schema.safeParse(data);

  if (result.success) {
    return {
      success: true,
      data: result.data,
    };
  }

  // Format error message
  const errors = result.error.errors
    .map((e) => `${e.path.join('.')}: ${e.message}`)
    .join('; ');

  return {
    success: false,
    error: `Validation failed: ${errors}`,
  };
}

/**
 * Validates data and throws if invalid.
 *
 * @param schema - The Zod schema to validate against
 * @param data - The data to validate
 * @param context - Context for error message
 * @returns The validated data
 * @throws Error if validation fails
 */
export function validateOrThrow<T>(
  schema: z.ZodType<T>,
  data: unknown,
  context: string
): T {
  const result = validate(schema, data);

  if (!result.success) {
    throw new Error(`[${context}] ${result.error}`);
  }

  return result.data!;
}

// =============================================================================
// EXPORT
// =============================================================================

export const schemas = {
  // Base
  AgentTypeSchema,
  AgentActionTypeSchema,
  MCPClientSourceSchema,
  MCPTransportSchema,
  RiskLevelSchema,
  ApprovalActionSchema,
  DecisionActionSchema,
  RuleConditionOperatorSchema,
  RuleConditionFieldSchema,
  // Agent Shield
  AgentConnectPayloadSchema,
  AgentInterceptActionPayloadSchema,
  AgentUpdateTrustPayloadSchema,
  // MCP Gateway
  MCPToolSchema,
  MCPRegisterServerPayloadSchema,
  MCPInterceptToolCallPayloadSchema,
  MCPUpdateTrustPayloadSchema,
  // Approval
  RuleConditionSchema,
  ApprovalDecidePayloadSchema,
  ApprovalCreateRulePayloadSchema,
  ApprovalRuleSchema,
  GetHistoryPayloadSchema,
  // Settings
  LanguageSchema,
  ProtectionLevelSchema,
  AgentShieldSettingsSchema,
  MCPGatewaySettingsSchema,
  ApprovalSettingsSchema,
  SettingsSchema,
};

export default schemas;
